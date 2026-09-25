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

from . import exports
from .chatdb import agent_template, census, db_name, list_databases, owner_export
from .config import (
    ALMANAC_DOMAIN,
    BASE_MODELS,
    CHAT_HOST,
    DEFAULT_COURSE_BUDGET,
    DEFAULT_FUSE,
    MIN_FUSE,
    REHEARSAL_DOMAIN,
)
from .courses import (
    address_map,
    clean_name,
    course_models,
    course_state,
    deployment_error,
    load_courses,
    open_or_raise,
    save_courses,
    window_ends,
)
from .escrow import (
    escrow_delete,
    escrow_holders,
    escrow_read,
    escrow_ready,
    escrow_write,
)
from .gateway import (
    ll_block_team,
    ll_delete_key,
    ll_ensure_team,
    ll_key_spend,
    ll_mint_key,
    ll_team_census,
    ll_team_remaining,
    ll_update_key,
)
from .keycloak import (
    kc_active_sessions,
    kc_client_uuid,
    kc_ensure_autolink,
    kc_ensure_client,
    kc_ensure_client_roles,
    kc_ensure_user,
    kc_role_holders,
    kc_set_client_enabled,
    kc_set_client_role,
    kc_user_id,
)
from .nominations import add_nomination, load_nominations, mark_nomination
from .reports import add_report, load_reports, mark_report
from .requests import (
    add_request,
    load_requests,
    mark_request,
    reply_request,
    reset_rehearsal,
)


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


class MeterUnreadable(Exception):
    """The gateway wouldn't say what a key has spent.

    Its own error type because the only safe response is to REFUSE: the
    caller wanted the number in order to subtract it from a fuse, and
    guessing zero hands back a full one.
    """


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
        if rec and rec.get("key") and not await ll_delete_key(cx, rec["key"]):
            # The escrow record is the only handle on a live key.  Deleting
            # it after a failed revoke would leave a key spending the pool
            # that nobody can find again — the orphan the mint path goes
            # out of its way never to make.  Keep it; retry revokes it.
            return {"op": "remove", "who": email, "ok": False,
                    "note": "the gateway didn't confirm the key revoke — "
                            "nothing changed; safe to retry"}
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
    open_or_raise(slug, course)
    await escrow_ready()  # sealed: stop before the first door opens
    results: list[dict] = []
    async with httpx.AsyncClient(timeout=30) as cx:
        client_uuid, _secret = await kc_ensure_client(cx, slug)
        roles = await kc_ensure_client_roles(cx, client_uuid)
        for email in adds:
            results.append(await _enroll_one(cx, slug, course, courses, email,
                                             roles, client_uuid))
        for email in removes:
            results.append(await _unenroll_one(cx, slug, email, roles, client_uuid))
    # File-backend truth: successful ops land in courses.yaml — onto the
    # file as it is NOW.  The loop above awaited Keycloak, the gateway and
    # the escrow once per student; saving the snapshot from before it would
    # silently undo anything written meanwhile (an approval, a staff change,
    # another apply).  Only this course's students move.
    ok_adds = {r["who"] for r in results if r["op"] == "add" and r["ok"]}
    ok_rm = {r["who"] for r in results if r["op"] == "remove" and r["ok"]}
    courses = load_courses()
    course = courses["courses"].get(slug)
    if course is not None:
        students = [e for e in course["students"] if e not in ok_rm]
        students += [e for e in ok_adds if e not in students]
        course["students"] = students
        save_courses(courses)
    render.render_roster(courses)
    return results


def _pending(rec: dict) -> list[str]:
    """Keys that still owe a death.  Scalar in records written before
    2026-09-21, a list after — read both, so an old escrow record doesn't
    have its debt silently dropped by the code that came to collect it."""
    v = rec.get("revoke_pending")
    if not v:
        return []
    return [v] if isinstance(v, str) else [k for k in v if k]


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
    open_or_raise(slug, course)
    async with httpx.AsyncClient(timeout=30) as cx:
        old = await escrow_read(slug, email) or {}

        # An earlier rotation that died before its revoke landed left this
        # behind — settle the old debt before taking on a new one.  We only
        # FORGET a debt the gateway confirms it killed: dropping the pointer
        # to a key that is still live is the "gateway but no escrow" orphan
        # the mint-and-escrow wall calls the worse of the two failures, and
        # it was happening here because this call ignored its own return
        # value four lines above one that checks it.
        unsettled: list[str] = []
        for stale in _pending(old):
            if not await ll_delete_key(cx, stale):
                unsettled.append(stale)

        fuse = course["budgets"]["key_fuse"]
        remaining = fuse
        old_key = old.get("key")
        extra: dict = {"rotated_from": old.get("minted_at")}
        if old_key:
            spent = await ll_key_spend(cx, old_key)
            if spent is None:
                # Refuse rather than assume.  `fuse - 0` is a full fuse, so
                # guessing here makes rotation a refill on demand — the exact
                # thing this docstring says the floor was removed to stop.
                raise MeterUnreadable(old_key)
            remaining = round(max(0.0, fuse - spent), 2)

        # Clamp and gate BEFORE revoking anything: a refusal has to leave the
        # caller exactly as they were, still holding a working key.
        remaining = await _fuse_for(cx, slug, remaining)
        if old_key:
            extra["revoke_pending"] = [old_key, *unsettled]
        elif unsettled:
            extra["revoke_pending"] = unsettled

        rec = await _mint_escrowed(cx, slug, email,
                                   course_models(course, courses), remaining,
                                   email, alias=f"{slug}:{email}", extra=extra)
        if old_key and await ll_delete_key(cx, old_key):
            # This key's debt is settled; anything still unsettled stays on
            # the record for the next rotation to collect.
            if unsettled:
                rec["revoke_pending"] = unsettled
            else:
                rec.pop("revoke_pending", None)
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
    open_or_raise(slug, course)
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
    if (e := deployment_error()):
        raise RuntimeError(e)
    courses = load_courses()
    course = courses["courses"][slug]
    open_or_raise(slug, course)
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
            # Chat spends on this key, so it has to follow the course, not
            # the day it was minted.  Before this, `just course --budget`
            # raised the pool and chat still stopped at the old number.
            await ll_update_key(cx, svc["key"], course["budgets"]["course"],
                                models)
            summary["service_key"] = "already escrowed (budget + models synced)"
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
        # Converge the other way too.  Until 2026-09-22 reconcile only ever
        # GRANTED `admin`, so taking someone off `instructors:` ended their
        # registrar and usage tools but left them ADMIN in the course's chat
        # until someone found the role in Keycloak by hand.  The file is the
        # authority; the role is a copy of it, so a holder the file doesn't
        # name loses it here.  Someone who is also a student keeps the door
        # and their key — they were demoted, not removed.
        staff = set(course["instructors"]) | set(course["tas"])
        students = set(course.get("students") or [])
        revoked = []
        for holder in await kc_role_holders(cx, client_uuid, "admin"):
            if holder in staff:
                continue
            uid = await kc_user_id(cx, holder)
            if uid:
                await kc_set_client_role(cx, uid, client_uuid, roles["admin"],
                                         False)
            if holder not in students:
                await _unenroll_one(cx, slug, holder, roles, client_uuid)
            revoked.append(holder)
        summary["staff"] = {"granted": granted, "precreated": precreated,
                            "revoked": revoked}
    # Render from the file as it is now, not as it was before the awaits
    # above — the fleet and roster renders carry every course, not just
    # this one.
    courses = load_courses()
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


# ---- the term: close, reopen, archive ----------------------------------------
# registrar-spec.md, "The term".  Two steps on purpose: close is a freeze a
# sentence can undo, archive is the part that can't be — and neither deletes
# a byte.  Each verb re-reads courses.yaml after its network calls and
# stamps onto the file as it is then, like apply_roster.

def _today() -> str:
    return datetime.now(timezone.utc).date().isoformat()


async def close_course(slug: str) -> dict:
    """Freeze a course.  Its team is blocked at the gateway — every key on
    it, the service key included, so chat can't spend either — and the
    record gains `closed:`.  Sign-in, history and agents stay up for the
    export window.  Blocks first and stamps second, so a failure between
    the two leaves an open-looking course that a second close finishes;
    the other order would leave a "closed" course still spending."""
    import render
    courses = load_courses()
    open_or_raise(slug, courses["courses"][slug])
    async with httpx.AsyncClient(timeout=30) as cx:
        await ll_block_team(cx, slug, True)
    courses = load_courses()
    c = courses["courses"][slug]
    c["closed"] = _today()
    save_courses(courses)
    # The address may move now: an open course claiming it outranks this one.
    render.render_fleet(courses)
    return {"slug": slug, "closed": c["closed"],
            "export_until": window_ends(c).isoformat(),
            "address": ({a: t for a, t in address_map(courses).items()
                         if a == c.get("address")} or None)}


async def reopen_course(slug: str) -> dict:
    """Undo a close: unblock the team, clear the date.  Refuses an archived
    course — its keys are gone and its sign-in is shut, and pretending a
    reopen restores that would hand people a course that doesn't work."""
    import render
    courses = load_courses()
    c = courses["courses"][slug]
    state = course_state(c)
    if state == "archived":
        open_or_raise(slug, c)
    if state == "open":
        raise ValueError(f"{slug} isn't closed — nothing to reopen")
    svc = await escrow_read(slug, "service")
    if svc and svc.get("revoked_at"):
        # An archive that stopped part-way already killed the key chat
        # spends on; a reopened course would sign people in to a chat that
        # can't answer.  Finish the archive — the next term is a new course.
        raise ValueError(f"{slug}'s keys were revoked by an archive on "
                         f"{svc['revoked_at']} that didn't finish — it can't be "
                         f"reopened.  `just course-archive {slug} --force` "
                         f"finishes it")
    async with httpx.AsyncClient(timeout=30) as cx:
        await ll_block_team(cx, slug, False)
    courses = load_courses()
    courses["courses"][slug]["closed"] = None
    save_courses(courses)
    render.render_fleet(courses)
    return {"slug": slug, "reopened": _today()}


async def archive_course(slug: str, force: bool = False) -> dict:
    """End a closed course.  Every escrowed key is revoked at the gateway
    and its record soft-deleted (kv-v2 keeps the versions — custody
    survives, as it does for un-enrollment), the OIDC client is disabled,
    and the course leaves the fleet render and the edge.  The database, the
    vector volume and fleet/<slug>.env stay.

    Stamps `archived:` only when every revoke landed.  A key the gateway
    wouldn't confirm keeps its record — the only handle anyone has on it —
    and the course stays closed-not-archived, so running this again picks
    up exactly what's left.  The team stays blocked throughout, so a key
    that survives a failed pass still can't spend."""
    import render
    courses = load_courses()
    c = courses["courses"][slug]
    state = course_state(c)
    if state == "archived":
        open_or_raise(slug, c)
    if state == "open":
        raise ValueError(f"{slug} is open — close it first (`just course-close "
                         f"{slug}`); archiving skips no one's export window")
    ends = window_ends(c)
    today = datetime.now(timezone.utc).date()
    if not force and (ends is None or today <= ends):
        until = (f"runs to {ends.isoformat()}" if ends else
                 f"can't be read from closed: {c['closed']!r}")
        raise ValueError(f"{slug}'s export window {until} — students may still be "
                         f"taking their work out.  --force archives it anyway")
    await escrow_ready()
    revoked, failed = [], []
    async with httpx.AsyncClient(timeout=30) as cx:
        for who in await escrow_holders(slug) + ["service"]:
            rec = await escrow_read(slug, who)
            if not rec or rec.get("revoked_at"):
                continue                      # already revoked, or never minted
            keys = [k for k in [rec.get("key"), *_pending(rec)] if k]
            dead = [k for k in keys if await ll_delete_key(cx, k)]
            if len(dead) < len(keys):
                failed.append(who)
                continue
            if who == "service":
                # Kept readable and marked, not soft-deleted: escrow_delete
                # is shaped for student paths, and the service record is the
                # course's own custody line.  The mark is what makes a
                # re-run skip a key the gateway already killed.
                await escrow_write(slug, "service", {**rec, "revoked_at": _today()})
            else:
                await escrow_delete(slug, who)
            revoked.append(who)
        summary = {"slug": slug, "revoked": len(revoked), "failed": failed}
        if failed:
            # Sign-in stays as it was: a pass that didn't finish changes
            # nothing a person can see, and the blocked team already stops
            # the surviving keys from spending.
            summary["archived"] = None
            return summary
        uuid = await kc_client_uuid(cx, slug)
        if uuid:
            await kc_set_client_enabled(cx, uuid, False)
        summary["sign_in"] = "disabled" if uuid else "no client (never provisioned)"
    courses = load_courses()
    courses["courses"][slug]["archived"] = _today()
    save_courses(courses)
    render.remove_course_vhost(slug)
    render.render_fleet(courses)       # leaves the fleet; --remove-orphans stops it
    render.render_roster(courses)
    summary["archived"] = courses["courses"][slug]["archived"]
    return summary


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
        report["flagship"] = {"host": CHAT_HOST, "db": db_name(None),
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


class NothingToExport(LookupError):
    """The person never used this course — no user, or nothing they own."""


async def export_owner_data(slug: str, email: str) -> dict:
    """One person's data from one course, packaged: their conversations and
    the agents they own, as a zip behind a 24-hour link.  `email` MUST come
    from the trusted headers — it is the only thing that picks whose data
    this is.  Any course state, archived included: the database outlives
    the course, and so does the right to what's in it.  A second ask
    inside ten minutes gets the same link back."""
    import render
    if (rec := exports.recent(email, slug)):
        return {**rec, "reused": True}
    course = load_courses()["courses"][slug]
    data = await owner_export(slug, email)
    if not data.get("found") or not (data["conversations"] or data["agents"]):
        raise NothingToExport(slug)
    docs = [render.template_doc(t, {
                "course": slug, "agent_id": t["agent_id"], "author": t["owner"],
                "owners": t["owners"], "exported_for": email,
                "exported_at": _now(), "actions_on_source": t["actions"]})
            for t in data["agents"]]
    return {**exports.write({"slug": slug, "name": course["name"]}, email, data, docs),
            "reused": False}


def export_meta(token: str) -> dict | None:
    return exports.meta(token)


def decline_nomination(nid: str, by: str) -> dict | None:
    return mark_nomination(nid, "declined", by)


# ---- reports: "this didn't work" ---------------------------------------------
# The routing question, and it is the whole reason this is a verb rather than
# a straight write: a report filed from a COURSE knows its course (the
# instance rendered X-Course into its own config, and a student can't touch
# it).  A report filed from the VESTIBULE knows nothing — the vestibule is
# the one room with no roster, which is exactly why it is the room that still
# answers when the room you're complaining about doesn't.
#
# So the vestibule asks the roster instead.  Same question, different
# instrument: courses.yaml already knows every course this email is on.  One
# course is an answer; several or none is a question for a human, and the
# record says which of those happened rather than quietly picking.


def courses_for(email: str) -> list[str]:
    """Every course slug this person is on, as student or staff.

    The roster is the routing table.  It is also the ONLY routing table the
    vestibule has, and it is already there — usage-mcp answers the same
    question from the rendered copy (usage-mcp/server.py, list_courses).
    """
    email = (email or "").strip().lower()
    out = []
    for slug, c in load_courses()["courses"].items():
        people = (c.get("students") or []) + (c.get("instructors") or []) \
            + (c.get("tas") or [])
        if email in [str(e).strip().lower() for e in people]:
            out.append(slug)
    return sorted(out)


def file_report(*, by: str, role: str, from_room: str, course: str | None,
                about: str | None, what: str, asked: str = "",
                answered: str = "", sources: list[str] | None = None) -> dict:
    """Record one problem report, working out who it belongs to.

    `course` is the X-Course literal (None in the vestibule); `about` is what
    the person named, if they named anything.  Precedence is certainty:
    the header beats what was typed, because the header is rendered config
    and what was typed is a person remembering a slug.
    """
    enrolled = courses_for(by)

    if course:
        target, route = course, "header"
    elif about and (a := about.strip().lower()) in enrolled:
        # Their own courses only, and deliberately NOT "any course that
        # exists": a stated slug is the one routing input a person types, so
        # taking it at face value lets anyone in the realm drop text on any
        # instructor's pile.  Naming a course they're not on isn't refused,
        # it just doesn't route — the report still lands, on the operator's.
        target, route = a, "stated"
    elif len(enrolled) == 1:
        target, route = enrolled[0], "roster"
    else:
        # Several courses or none.  Nobody is guessed at: a report filed
        # against the wrong course wastes the one instructor who reads it,
        # and an unrouted report at least lands somewhere a human looks.
        target, route = None, "unknown"

    stated = (about or "").strip().lower()
    return add_report(by=by, role=role, from_room=from_room, about=target,
                      route=route, enrolled=enrolled, what=what,
                      said=stated if stated and stated != target else "",
                      asked=asked, answered=answered, sources=sources)


def reports(slug: str | None = None, status: str | None = None) -> list[dict]:
    rows = load_reports()
    if slug is not None:
        rows = [r for r in rows if r.get("about") == slug]
    if status is not None:
        rows = [r for r in rows if r.get("status") == status]
    return rows


def close_report(rid: str, by: str, note: str = "",
                 status: str = "closed") -> dict | None:
    return mark_report(rid, status, by, note)


# ---- the front office: courses, staff, budgets, requests ----------------------
# The Phase 2a desk (docs/registrar-spec.md, "Phase 2a — the front office").
# These write courses.yaml and nothing else; the caller then runs
# ensure_course, which is the one place a course's systems are made to match
# its record.  `course_admin.py create` goes through upsert_course too, so the
# CLI and the chat desk cannot drift into two ideas of a new course.


def upsert_course(slug: str, name: str, instructors: list[str],
                  tas: list[str] | None = None, budget: float | None = None,
                  college: str | None = None) -> dict:
    """Create the record, or add to it.  Appends staff, never removes —
    removal is set_staff, on purpose, so a create can't demote anyone."""
    data = load_courses()
    if slug in data["courses"]:
        open_or_raise(slug, data["courses"][slug])
    c = data["courses"].get(slug) or {
        "name": clean_name(name), "instructors": [], "tas": [],
        "budgets": {"course": DEFAULT_COURSE_BUDGET,
                    "key_fuse": DEFAULT_FUSE,
                    "advisory_weekly": 2.0},
        "college": None, "models": list(BASE_MODELS),
        "group": "", "students": [], "aliases": {},
    }
    c["name"] = clean_name(name)
    for i in [e.strip().lower() for e in instructors]:
        if i and i not in c["instructors"]:
            c["instructors"].append(i)
    for t in [e.strip().lower() for e in (tas or [])]:
        if t and t not in c["tas"]:
            c["tas"].append(t)
    if budget is not None:
        c["budgets"]["course"] = float(budget)
    if college:
        c["college"] = college.strip().lower()
    data["courses"][slug] = c
    save_courses(data)
    return c


def set_staff(slug: str, add_instructors: list[str], add_tas: list[str],
              remove: list[str]) -> dict:
    """Edit who teaches a course.  A person is in at most one of the two
    lists — adding someone as a TA moves them out of instructors, and the
    other way round.  Staff aren't students, so an added staffer leaves
    `students:` (their key is theirs either way).  Refuses to leave a
    course with no instructor: every course has someone who answers for it."""
    data = load_courses()
    c = data["courses"][slug]
    open_or_raise(slug, c)
    ins, tas = list(c["instructors"]), list(c["tas"])
    for e in add_instructors:
        if e in tas:
            tas.remove(e)
        if e not in ins:
            ins.append(e)
    for e in add_tas:
        if e in ins:
            ins.remove(e)
        if e not in tas:
            tas.append(e)
    ins = [e for e in ins if e not in remove]
    tas = [e for e in tas if e not in remove]
    if not ins:
        raise ValueError(f"{slug} would have no instructor left")
    c["instructors"], c["tas"] = ins, tas
    staff = set(ins) | set(tas)
    c["students"] = [e for e in c.get("students") or [] if e not in staff]
    save_courses(data)
    return c


def set_address(slug: str, address: str | None) -> dict:
    """Point a stable address at this course, or take it off (None).  The
    new term claims the address its predecessor had; while both are open
    that is a conflict `validate` names, so the usual order is: create the
    new term, close the old one, then move the address — or move it first,
    since the old term keeps it only while no open course claims it."""
    import render
    from .courses import slug_error
    data = load_courses()
    c = data["courses"][slug]
    if course_state(c) == "archived":
        open_or_raise(slug, c)
    if address:
        address = address.strip().lower()
        if (why := slug_error(address)):
            raise ValueError(why.replace("slug", "address"))
        if address in data["courses"] or f"{address}-admin" in data["courses"]:
            raise ValueError(f"{address!r} is a course id — an address can't also "
                             "be one, since both are hostnames")
    c["address"] = address or None
    save_courses(data)
    render.render_fleet(data)
    return {"slug": slug, "address": c["address"],
            "points_to": address_map(data).get(address) if address else None}


def set_course_budget(slug: str, amount: float) -> dict:
    data = load_courses()
    c = data["courses"][slug]
    open_or_raise(slug, c)
    c["budgets"]["course"] = float(amount)
    save_courses(data)
    return c


def file_request(**kw) -> dict:
    return add_request(**kw)


def requests_list(status: str | None = None, by: str | None = None) -> list[dict]:
    rows = load_requests()
    if status is not None:
        rows = [r for r in rows if r.get("status") == status]
    if by is not None:
        rows = [r for r in rows if r.get("by") == by]
    return rows


def decide_request(rid: str, status: str, by: str, note: str = "",
                   course: str | None = None,
                   budget: float | None = None) -> dict | None:
    return mark_request(rid, status, by, note, course, budget)


def answer_request(rid: str, by: str, text: str) -> dict | None:
    return reply_request(rid, by, text)


# ---- the eval fixture ---------------------------------------------------------
# What scripts/run_evals.py drives the guides against.  The personas are on
# the reserved .invalid TLD, so nobody can sign in as one, and the tool plane
# rehearses every write they attempt (server.py, `_rehearse`) — which is what
# makes it safe to put one on `admins:`.  The course is a record and nothing
# else: never provisioned, so it has no team, key, client or instance, and
# `render` skips it for want of a service key.  Reset on every eval run.

EVAL_DOMAIN = REHEARSAL_DOMAIN
EVAL_PERSONAS = {
    "instructor": "evals-instructor@almanac.invalid",
    "student": "evals-student@almanac.invalid",
    "admin": "evals-admin@almanac.invalid",
    "nobody": "evals-nobody@almanac.invalid",
}
EVAL_COURSE = "evals-sandbox"


def evals_fixture() -> dict:
    data = load_courses()
    data["courses"][EVAL_COURSE] = {
        "name": "Evals sandbox — not a real course, never provisioned",
        "instructors": [EVAL_PERSONAS["instructor"]], "tas": [],
        "budgets": {"course": DEFAULT_COURSE_BUDGET, "key_fuse": DEFAULT_FUSE,
                    "advisory_weekly": 2.0},
        "college": None, "models": list(BASE_MODELS), "group": "",
        "students": [EVAL_PERSONAS["student"]], "aliases": {},
    }
    if EVAL_PERSONAS["admin"] not in data["admins"]:
        data["admins"].append(EVAL_PERSONAS["admin"])
    save_courses(data)
    # usage-mcp's roster carries admins: and every course, so a fixture that
    # skipped this left the next deploy's render-check red (CI #169).
    import render
    render.render_roster(data)
    who = EVAL_PERSONAS["instructor"]
    stamp = _now()
    base = {"by": who, "filed": stamp, "instructors": [who], "parent": None,
            "attestation": {"asked": "(eval fixture)", "answer": "yes",
                            "at": stamp}}
    reset_rehearsal(EVAL_DOMAIN, [
        {**base, "id": "rq-eval01", "kind": "course",
         "name": "BIO 210 — Genetics (Winter 2027)",
         "purpose": "A lab assistant agent for two genetics sections.",
         "details": "Two sections of about 40.  We'd like a Punnett-square "
                    "tutor and the lab manual as knowledge.",
         "term": "Winter 2027", "headcount": 80, "slug_wanted": None,
         "status": "open", "thread": []},
        {**base, "id": "rq-eval02", "kind": "standalone",
         "name": "Materials Science reading group",
         "purpose": "A shared agent for a weekly paper-reading group.",
         "details": "", "term": "", "headcount": 12,
         "slug_wanted": "matsci-reading", "status": "returned",
         "thread": [{"at": stamp, "by": EVAL_PERSONAS["admin"], "as": "admin",
                     "text": "Is this tied to a course, or is it a club?  "
                             "And who is the faculty sponsor?"}]},
    ])
    return {"course": EVAL_COURSE, "personas": EVAL_PERSONAS,
            "requests": ["rq-eval01 (open)", "rq-eval02 (returned)"]}

