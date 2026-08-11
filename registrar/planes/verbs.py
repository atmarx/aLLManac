"""The reconcile verbs — the only place the planes are composed.

Everything here is IDEMPOTENT on purpose — a failed half-apply is repaired
by applying again, and `just course` can be re-run until it's boring.

A verb is allowed to know about courses + keycloak + gateway + escrow at
once; a plane is not allowed to know about its siblings.  That asymmetry is
the whole reason this file exists separately from the four below it.
"""

import asyncio
from datetime import datetime, timezone

import httpx

from .config import ALMANAC_DOMAIN
from .courses import course_models, load_courses, save_courses
from .escrow import escrow_delete, escrow_read, escrow_write
from .gateway import ll_delete_key, ll_ensure_team, ll_key_spend, ll_mint_key
from .keycloak import (
    kc_ensure_client,
    kc_ensure_client_roles,
    kc_set_client_role,
    kc_user_id,
)


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


async def _enroll_one(cx: httpx.AsyncClient, slug: str, course: dict,
                      courses: dict, email: str, roles: dict,
                      client_uuid: str) -> dict:
    """Grant the door role, mint the key, escrow it.  Idempotent."""
    try:
        uid = await kc_user_id(cx, email)
        if uid:
            await kc_set_client_role(cx, uid, client_uuid, roles["member"], True)
        note = "" if uid else "(no realm user yet — door opens on next sync after first login)"
        if await escrow_read(slug, email) is None:
            fuse = course["budgets"]["key_fuse"]
            key = await ll_mint_key(cx, slug, course_models(course, courses),
                                    fuse, email, alias=f"{slug}:{email}")
            await escrow_write(slug, email, {
                "key": key, "minted_at": _now(), "budget": fuse,
            })
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
    """Revoke + re-mint with the fuse's REMAINDER — rotation is not a
    budget reset (spend read from the ledger via /key/info)."""
    courses = load_courses()
    course = courses["courses"][slug]
    async with httpx.AsyncClient(timeout=30) as cx:
        old = await escrow_read(slug, email)
        fuse = course["budgets"]["key_fuse"]
        remaining = fuse
        if old and old.get("key"):
            spent = await ll_key_spend(cx, old["key"])
            remaining = round(max(0.5, fuse - spent), 2)
            await ll_delete_key(cx, old["key"])
        key = await ll_mint_key(cx, slug, course_models(course, courses),
                                remaining, email, alias=f"{slug}:{email}")
        rec = {"key": key, "minted_at": _now(), "budget": remaining,
               "rotated_from": (old or {}).get("minted_at")}
        await escrow_write(slug, email, rec)
        return rec


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
            key = await ll_mint_key(cx, slug, models, course["budgets"]["course"],
                                    None, alias=f"svc-{slug}")
            svc = {"key": key, "minted_at": _now(), "kind": "service"}
            await escrow_write(slug, "service", svc)
            summary["service_key"] = "minted + escrowed"
        else:
            summary["service_key"] = "already escrowed"
        client_uuid, client_secret = await kc_ensure_client(cx, slug)
        roles = await kc_ensure_client_roles(cx, client_uuid)
        summary["oidc_client"] = slug
        granted, waiting = [], []
        for email in course["instructors"] + course["tas"]:
            uid = await kc_user_id(cx, email)
            if uid:
                await kc_set_client_role(cx, uid, client_uuid, roles["admin"], True)
                await kc_set_client_role(cx, uid, client_uuid, roles["member"], True)
                granted.append(email)
            else:
                waiting.append(email)
        summary["staff"] = {"granted": granted, "no_realm_user_yet": waiting}
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
