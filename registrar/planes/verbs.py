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

import os

from .chatdb import agent_template, census, db_name, list_databases
from .config import ALMANAC_DOMAIN, MIN_FUSE
from .courses import course_models, load_courses, save_courses
from .escrow import escrow_delete, escrow_read, escrow_write
from .gateway import (
    ll_delete_key,
    ll_ensure_team,
    ll_key_spend,
    ll_mint_key,
    ll_team_census,
    ll_team_remaining,
)
from .keycloak import (
    kc_active_sessions,
    kc_client_uuid,
    kc_ensure_autolink,
    kc_ensure_client,
    kc_ensure_client_roles,
    kc_ensure_user,
    kc_role_holders,
    kc_set_client_role,
    kc_user_id,
)
from .nominations import add_nomination, load_nominations, mark_nomination


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


# ---- the census: the fleet from above ----------------------------------------
# Read-only composition of every plane.  These verbs create nothing, grant
# nothing, mint nothing — they are the registrar reporting what it already
# reconciles, and the one place all five columns (record, door, pool,
# database, container) land in the same row.  Envelope only: see chatdb.

FLEET_OUT = os.environ.get("OUT_FLEET", "/out/fleet")


async def _reachable(cx: httpx.AsyncClient, host: str) -> bool:
    """Does the instance answer on the compose network?  A health probe
    from inside is the honest signal the registrar can give without a
    docker socket: "answering" rather than "running"."""
    try:
        r = await cx.get(f"http://{host}:3080/health", timeout=4)
        return r.status_code < 500
    except httpx.HTTPError:
        return False


async def _course_row(cx: httpx.AsyncClient, courses: dict, slug: str) -> dict:
    c = courses["courses"][slug]
    row: dict = {
        "slug": slug, "name": c["name"], "host": f"{slug}.{ALMANAC_DOMAIN}",
        "rendered": os.path.exists(f"{FLEET_OUT}/{slug}.env"),
        "roster": {"instructors": len(c["instructors"]), "tas": len(c["tas"]),
                   "students": len(c["students"])},
        "budgets": dict(c["budgets"]),
        "capabilities": list(c["capabilities"]),
        "allowed_domains": list(c["allowed_domains"]),
        "models": course_models(c, courses),
    }
    # Each column degrades alone.  A census that dies because one plane is
    # down tells the operator nothing about the other four — and "the
    # gateway is unreachable" is itself a row worth reading.
    row["errors"] = {}
    row["reachable"] = await _reachable(cx, f"chat-{slug}")
    try:
        row["pool"] = await ll_team_census(cx, slug)
    except httpx.HTTPError as e:
        row["pool"], row["errors"]["pool"] = None, f"gateway: {e.__class__.__name__}"
    row["door"] = None
    try:
        uuid = await kc_client_uuid(cx, slug)
        if uuid:
            row["door"] = {"member": await kc_role_holders(cx, uuid, "member"),
                           "admin": await kc_role_holders(cx, uuid, "admin"),
                           "sessions": await kc_active_sessions(cx, uuid)}
    except httpx.HTTPError as e:
        row["errors"]["door"] = f"keycloak: {e.__class__.__name__}"
    try:
        row["census"] = await census(slug)
    except Exception as e:  # pymongo's own hierarchy; the row still renders
        row["census"] = {"db": db_name(slug), "exists": False}
        row["errors"]["census"] = f"mongo: {e.__class__.__name__}"
    return row


async def fleet_inventory() -> dict:
    """Every instance in one report — and the render of it on disk."""
    import render
    courses = load_courses()
    report: dict = {"generated": _now(), "domain": ALMANAC_DOMAIN, "courses": []}
    async with httpx.AsyncClient(timeout=30) as cx:
        try:
            flag = await census(None)
        except Exception as e:
            flag = {"db": db_name(None), "exists": False, "error": f"mongo: {e.__class__.__name__}"}
        report["flagship"] = {"host": f"chat.{ALMANAC_DOMAIN}", "db": db_name(None),
                              "reachable": await _reachable(cx, "librechat"),
                              "census": flag}
        for slug in sorted(courses["courses"]):
            report["courses"].append(await _course_row(cx, courses, slug))
    # A database with no course record is a finding — it is what a deleted
    # course leaves behind.
    known = {db_name(s) for s in courses["courses"]} | {db_name(None)}
    try:
        names = [n for n in await list_databases() if n.startswith("LibreChat") and n not in known]
    except Exception:
        names = []
    report["orphan_databases"] = sorted(names)
    render.render_inventory(report)
    return report


async def fleet_access(slug: str) -> dict:
    """Who can get in, who has, and the three diffs a security review asks
    for: rostered-but-never-seen, seen-but-not-rostered, door-but-not-rostered."""
    courses = load_courses()
    c = courses["courses"][slug]
    async with httpx.AsyncClient(timeout=30) as cx:
        row = await _course_row(cx, courses, slug)
    roster = set(c["students"]) | set(c["instructors"]) | set(c["tas"])
    seen = {u["email"] for u in row["census"].get("users", [])}
    door = set((row["door"] or {}).get("member", []))
    return {
        "slug": slug, "name": c["name"],
        "roster": sorted(roster), "staff": sorted(set(c["instructors"]) | set(c["tas"])),
        "door": sorted(door), "admins": sorted((row["door"] or {}).get("admin", [])),
        "signed_in": row["census"].get("users", []),
        "sessions": (row["door"] or {}).get("sessions", []),
        "never_seen": sorted(roster - seen),
        "seen_not_rostered": sorted(seen - roster),
        "door_not_rostered": sorted(door - roster),
        "rostered_no_door": sorted(roster - door) if row["door"] else [],
    }


async def fleet_exposure(slug: str) -> dict:
    """What a course has that reaches past one person: shared agents, the
    knowledge attached to them, every file by size, and the walls the
    course record puts (or doesn't) around Actions and tools."""
    courses = load_courses()
    async with httpx.AsyncClient(timeout=30) as cx:
        row = await _course_row(cx, courses, slug)
    return {"slug": slug, "name": row["name"], "capabilities": row["capabilities"],
            "allowed_domains": row["allowed_domains"], "models": row["models"],
            "pool": row["pool"], "agents": row["census"].get("agents", []),
            "files": row["census"].get("files", []),
            "totals": row["census"].get("totals", {})}


# ---- nominations: "this one is worth copying" --------------------------------

async def nominate_agent(slug: str, agent_id: str, by: str, note: str,
                         staff: bool) -> dict:
    """Record a nomination.  The author may nominate their own agent; staff
    may nominate any agent in their course.  -> the nomination record, with
    the template attached so the caller can see what would be copied."""
    tpl = await agent_template(slug, agent_id)
    if tpl is None:
        raise KeyError(f"no agent {agent_id} in {slug}")
    if tpl["owner"] != by and not staff:
        raise PermissionError(f"{agent_id} belongs to {tpl['owner'] or 'someone else'}")
    rec = add_nomination(slug, agent_id, tpl["name"] or agent_id, by, note)
    return {"nomination": rec, "template": tpl}


def nominations(slug: str | None = None) -> list[dict]:
    rows = load_nominations()
    return [r for r in rows if slug is None or r["course"] == slug]


async def export_nomination(nid: str, by: str) -> dict:
    """Write the nominated agent as a template file on the fleet volume and
    mark the nomination.  The template is the deliverable: a file someone
    can read, fork, and seed — not a live object only the UI can show."""
    import render
    rec = next((r for r in load_nominations() if r["id"] == nid), None)
    if rec is None:
        raise KeyError(f"no nomination {nid}")
    tpl = await agent_template(rec["course"], rec["agent_id"])
    if tpl is None:
        raise KeyError(f"the nominated agent {rec['agent_id']} no longer exists in {rec['course']}")
    path = render.render_template(rec, tpl)
    mark_nomination(nid, "exported", by, where=path)
    return {"nomination": rec, "path": path, "template": tpl}


def decline_nomination(nid: str, by: str) -> dict | None:
    return mark_nomination(nid, "declined", by)
