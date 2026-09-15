"""The reconcile verbs — the only place the planes are composed.

Everything here is IDEMPOTENT on purpose — a failed half-apply is repaired
by applying again, and `just course` can be re-run until it's boring.

A verb is allowed to know about courses + keycloak + gateway + escrow at
once; a plane is not allowed to know about its siblings.  That asymmetry is
the whole reason this file exists separately from the four below it.
"""

import asyncio
import contextlib
from datetime import datetime, timezone

import httpx

from .config import ALMANAC_DOMAIN, MIN_FUSE
from .courses import course_models, load_courses, save_courses
from .escrow import escrow_delete, escrow_read, escrow_write
from .gateway import (
    ll_delete_key,
    ll_ensure_team,
    ll_key_spend,
    ll_mint_key,
    ll_team_remaining,
)
from .keycloak import (
    kc_ensure_autolink,
    kc_ensure_client,
    kc_ensure_client_roles,
    kc_ensure_user,
    kc_set_client_role,
    kc_user_id,
)


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


class PoolExhausted(Exception):
    """Not enough budget left to mint a key that could actually do anything."""


async def _fuse_for(cx: httpx.AsyncClient, slug: str, want: float) -> float:
    """The fuse a new key may actually carry — never more than the pool can pay.

    A key's number is a promise, and a $5 fuse against a course pool with
    $2 left is a key that stops at $2 and never says why.  The pool is the
    hard cap and LiteLLM enforces it regardless, so clamping here buys
    honesty rather than enforcement: what the key says and what the key can
    do become the same number.

    And when that number is too small to fund a working session, **refuse.**
    Handing someone a credential that is dead on arrival costs them a
    debugging session and teaches them the platform is broken; a refusal
    that names the reason costs them one sentence.
    """
    left = await ll_team_remaining(cx, slug)
    fuse = want if left is None else min(want, left)
    if fuse < MIN_FUSE:
        raise PoolExhausted(
            f"{slug}: a new key would carry ${fuse:.2f}, under the "
            f"${MIN_FUSE:.2f} a working session needs "
            f"(this key's remainder ${want:.2f}; course pool "
            f"{'unreadable' if left is None else f'${left:.2f}'} left)."
        )
    return fuse


async def _mint_escrowed(cx: httpx.AsyncClient, slug: str, who: str,
                         models: list[str], budget: float,
                         user_id: str | None, alias: str,
                         extra: dict | None = None) -> dict:
    """Mint at the gateway and escrow in the same breath — the only way a
    durable key is created.

    A key that is minted but not escrowed is worse than no key at all: it is
    live at the gateway spending the course pool, and nobody — not the
    student, not the operator — can ever read it back to revoke it
    deliberately.  So when the escrow write fails, revoke before raising and
    let the caller see a clean failure instead of a silent orphan.

    A process death *between* the two calls still leaves one, and no ordering
    closes that window — it can only be detected.  The deterministic alias
    (`<slug>:<email>`) is what an audit joins the ledger to the escrow on.
    """
    key = await ll_mint_key(cx, slug, models, budget, user_id, alias=alias)
    rec = {"key": key, "minted_at": _now(), "budget": budget, **(extra or {})}
    try:
        await escrow_write(slug, who, rec)
    except Exception:
        # Best effort: the escrow failure is the error worth reporting.
        with contextlib.suppress(Exception):
            await ll_delete_key(cx, key)
        raise
    return rec


async def _enroll_one(cx: httpx.AsyncClient, slug: str, course: dict,
                      courses: dict, email: str, roles: dict,
                      client_uuid: str) -> dict:
    """Grant the door role, mint the key, escrow it.  Idempotent."""
    try:
        uid, created = await kc_ensure_user(cx, email)
        await kc_set_client_role(cx, uid, client_uuid, roles["member"], True)
        note = "(realm user pre-created — first sign-in links to it)" if created else ""
        if await escrow_read(slug, email) is None:
            fuse = await _fuse_for(cx, slug, course["budgets"]["key_fuse"])
            await _mint_escrowed(cx, slug, email,
                                 course_models(course, courses), fuse, email,
                                 alias=f"{slug}:{email}")
            note = (note + " minted+escrowed").strip()
        else:
            note = (note + " already escrowed").strip()
        return {"op": "add", "who": email, "ok": True, "note": note}
    except Exception as e:
        return {"op": "add", "who": email, "ok": False,
                "note": f"{type(e).__name__}: {e}"}


async def _unenroll_one(cx: httpx.AsyncClient, slug: str, email: str,
                        roles: dict, client_uuid: str) -> dict:
    try:
        rec = await escrow_read(slug, email)
        if rec and rec.get("key"):
            await ll_delete_key(cx, rec["key"])
        await escrow_delete(slug, email)
        uid = await kc_user_id(cx, email)
        if uid:
            await kc_set_client_role(cx, uid, client_uuid, roles["member"], False)
        return {"op": "remove", "who": email, "ok": True,
                "note": "key revoked, door closed"}
    except Exception as e:
        return {"op": "remove", "who": email, "ok": False,
                "note": f"{type(e).__name__}: {e}"}


async def apply_roster(slug: str, adds: list[str], removes: list[str]) -> list[dict]:
    """The confirmed-stage executor: exactly the diff, nothing else.
    Updates courses.yaml (file-backend truth) and re-renders usage-mcp's
    roster view when done."""
    import render  # late import — render has no credentials, but keep planes tidy
    courses = load_courses()
    course = courses["courses"][slug]
    results: list[dict] = []
    async with httpx.AsyncClient(timeout=30) as cx:
        client_uuid, _secret = await kc_ensure_client(cx, slug)
        roles = await kc_ensure_client_roles(cx, client_uuid)
        for email in adds:
            results.append(await _enroll_one(cx, slug, course, courses, email,
                                             roles, client_uuid))
        for email in removes:
            results.append(await _unenroll_one(cx, slug, email, roles, client_uuid))
    # File-backend truth: successful ops land in courses.yaml
    ok_adds = {r["who"] for r in results if r["op"] == "add" and r["ok"]}
    ok_rm = {r["who"] for r in results if r["op"] == "remove" and r["ok"]}
    students = [e for e in course["students"] if e not in ok_rm]
    students += [e for e in ok_adds if e not in students]
    course["students"] = students
    save_courses(courses)
    render.render_roster(courses)
    return results


async def rotate_student_key(slug: str, email: str) -> dict:
    """Mint the replacement FIRST, then revoke — with the fuse's REMAINDER,
    because rotation is not a budget reset (spend read from the ledger via
    /key/info).

    The order is the fix, not a style choice.  Revoking first meant a failed
    mint left the student with no working key *and* an escrow record still
    pointing at the dead one, so the next read handed them a credential the
    gateway had already rejected.  Minting first makes the worst case two
    live keys — and `revoke_pending` records which one still owes a death,
    so an interrupted rotation is a debt we can see rather than a quietly
    doubled fuse.

    There used to be a `max(0.5, ...)` floor here, which meant rotating at
    exhaustion handed back $0.50 every time — a fuse that refills on demand
    bounds nothing.  The floor was the wrong instrument: what this needs is a
    *gate*, not a minimum.  See `_fuse_for`.
    """
    courses = load_courses()
    course = courses["courses"][slug]
    async with httpx.AsyncClient(timeout=30) as cx:
        old = await escrow_read(slug, email) or {}

        # An earlier rotation that died before its revoke landed left this
        # behind — settle the old debt before taking on a new one.
        if old.get("revoke_pending"):
            await ll_delete_key(cx, old["revoke_pending"])

        fuse = course["budgets"]["key_fuse"]
        remaining = fuse
        old_key = old.get("key")
        extra = {"rotated_from": old.get("minted_at")}
        if old_key:
            spent = await ll_key_spend(cx, old_key)
            remaining = round(max(0.0, fuse - spent), 2)

        # Clamp and gate BEFORE revoking anything: a refusal has to leave the
        # caller exactly as they were, still holding a working key.
        remaining = await _fuse_for(cx, slug, remaining)
        if old_key:
            extra["revoke_pending"] = old_key

        rec = await _mint_escrowed(cx, slug, email,
                                   course_models(course, courses), remaining,
                                   email, alias=f"{slug}:{email}", extra=extra)
        if old_key and await ll_delete_key(cx, old_key):
            del rec["revoke_pending"]
            await escrow_write(slug, email, rec)  # kv-v2 v2: debt cleared
        return rec


async def mint_key(slug: str, email: str, budget: float | None = None) -> dict:
    """The operator's mint — a staff test key, escrowed like every other.

    Idempotent by escrow: an existing record comes back untouched rather
    than minting a second key onto the same alias.  There is no unescrowed
    mint path any more, which is the whole point — the recipe this replaced
    called `/key/generate` directly, so every key it ever made was born
    orphaned, outside the course team, and invisible to the pool.
    """
    courses = load_courses()
    course = courses["courses"].get(slug)
    if course is None:
        raise KeyError(f"no such course: {slug}")
    existing = await escrow_read(slug, email)
    if existing is not None:
        return {**existing, "already": True}
    async with httpx.AsyncClient(timeout=30) as cx:
        fuse = await _fuse_for(
            cx, slug, budget if budget else course["budgets"]["key_fuse"])
        rec = await _mint_escrowed(cx, slug, email,
                                   course_models(course, courses), fuse,
                                   email, alias=f"{slug}:{email}")
    return {**rec, "already": False}


async def ensure_course(slug: str) -> dict:
    """The `just course` engine: team + service key + OIDC client + door
    roles + staff grants + renders.  Run it until it's boring."""
    import render
    courses = load_courses()
    course = courses["courses"][slug]
    models = course_models(course, courses)
    summary: dict = {"slug": slug}
    async with httpx.AsyncClient(timeout=30) as cx:
        await ll_ensure_team(cx, slug, course["name"],
                             course["budgets"]["course"], models)
        summary["team"] = f"{slug} (${course['budgets']['course']:g} pool)"
        svc = await escrow_read(slug, "service")
        if svc is None:
            svc = await _mint_escrowed(cx, slug, "service", models,
                                       course["budgets"]["course"], None,
                                       alias=f"svc-{slug}",
                                       extra={"kind": "service"})
            summary["service_key"] = "minted + escrowed"
        else:
            summary["service_key"] = "already escrowed"
        client_uuid, client_secret = await kc_ensure_client(cx, slug)
        roles = await kc_ensure_client_roles(cx, client_uuid)
        summary["oidc_client"] = slug
        summary["first_login"] = await kc_ensure_autolink(cx)
        granted, precreated = [], []
        for email in course["instructors"] + course["tas"]:
            uid, created = await kc_ensure_user(cx, email)
            await kc_set_client_role(cx, uid, client_uuid, roles["admin"], True)
            await kc_set_client_role(cx, uid, client_uuid, roles["member"], True)
            granted.append(email)
            if created:
                precreated.append(email)
        summary["staff"] = {"granted": granted, "precreated": precreated}
    render.render_course(courses, slug,
                         oidc_secret=client_secret, service_key=svc["key"])
    render.render_fleet(courses)
    render.render_roster(courses)
    summary["hostnames"] = [f"{slug}.{ALMANAC_DOMAIN}",
                            f"{slug}-admin.{ALMANAC_DOMAIN}"]
    return summary


def reconcile_students_cmd(slug: str) -> list[dict]:
    """Sync helper for course_admin: enroll everyone currently listed."""
    courses = load_courses()
    course = courses["courses"][slug]
    return asyncio.run(apply_roster(slug, list(course["students"]), []))
