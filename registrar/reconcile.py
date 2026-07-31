"""The aLLManac registrar — the reconcile plane.

The ONLY code that holds minting credentials: the LiteLLM master key (mint
and revoke virtual keys, course teams), the Keycloak admin password (course
OIDC clients, the admin/member client roles that gate each instance's
door), and the OpenBao AppRole (the escrow).  The tool plane (server.py)
calls into these functions with identities it took from trusted headers —
it never touches a credential itself.  Keep it that way: this seam is what
makes the blast-radius statement in docs/registrar-spec.md true.

Everything here is IDEMPOTENT on purpose — a failed half-apply is repaired
by applying again, and `just course` can be re-run until it's boring.
"""

import asyncio
import json
import os
import tempfile
import time
from datetime import datetime, timezone

import httpx
import yaml

COURSES_PATH = os.environ.get("REGISTRAR_COURSES", "/app/courses.yaml")

KC_URL = os.environ.get("KC_URL", "http://keycloak:8080")
KC_REALM = os.environ.get("KC_REALM", "northwinds")
KC_ADMIN = os.environ.get("KC_ADMIN", "admin")
KC_ADMIN_PASSWORD = os.environ.get("KC_ADMIN_PASSWORD", "")

LITELLM_URL = os.environ.get("LITELLM_URL", "http://litellm:4000")
LITELLM_MASTER_KEY = os.environ.get("LITELLM_MASTER_KEY", "")

BAO_ADDR = os.environ.get("BAO_ADDR", "http://openbao:8200")
BAO_ROLE_ID = os.environ.get("BAO_REGISTRAR_ROLE_ID", "")
BAO_SECRET_ID = os.environ.get("BAO_REGISTRAR_SECRET_ID", "")
BAO_MOUNT = os.environ.get("BAO_MOUNT", "almanac")

ALMANAC_DOMAIN = os.environ.get("ALMANAC_DOMAIN", "localhost")

DEFAULT_FUSE = float(os.environ.get("REGISTRAR_DEFAULT_FUSE", "5"))
MAX_FUSE = float(os.environ.get("REGISTRAR_MAX_FUSE", "25"))
DEFAULT_COURSE_BUDGET = float(os.environ.get("REGISTRAR_DEFAULT_COURSE_BUDGET", "1000"))
BASE_MODELS = ["almanac-chat"]

# Agent-builder powers a course's instance gets.  `actions` (arbitrary-URL
# tool calls) is EXCLUDED — it's the one path around the gateway's
# guardrails and metering (docs/registrar-spec.md, "The floor").  The render
# plane keeps its own copy of this list as a hand-built-dict fallback; this
# is the source of truth, so change both together.
DEFAULT_CAPABILITIES = ["file_search", "tools", "artifacts"]


# ---- course state: registrar/courses.yaml --------------------------------------
# The operator's file AND the file-backend roster truth.  Writes are atomic
# (tmp + rename) — courses.yaml is bind-mounted as a directory-relative path
# precisely so renames are visible.

_EMPTY = {"courses": {}, "colleges": {}, "admins": []}


def load_courses() -> dict:
    try:
        with open(COURSES_PATH) as f:
            raw = yaml.safe_load(f) or {}
    except OSError:
        return dict(_EMPTY)
    except Exception:
        return dict(_EMPTY)  # bad YAML degrades; course_admin validate catches it
    out = {
        "courses": {}, "colleges": raw.get("colleges") or {},
        "admins": [str(e).strip().lower() for e in (raw.get("admins") or [])],
    }
    for slug, c in (raw.get("courses") or {}).items():
        c = c or {}
        budgets = c.get("budgets") or {}
        out["courses"][str(slug).strip().lower()] = {
            "name": str(c.get("name") or slug),
            "instructors": [str(e).strip().lower() for e in (c.get("instructors") or [])],
            "tas": [str(e).strip().lower() for e in (c.get("tas") or [])],
            "budgets": {
                "course": float(budgets.get("course", DEFAULT_COURSE_BUDGET)),
                "key_fuse": min(float(budgets.get("key_fuse", DEFAULT_FUSE)), MAX_FUSE),
                "advisory_weekly": float(budgets.get("advisory_weekly", 2)),
            },
            "college": (str(c.get("college")).strip().lower()
                        if c.get("college") else None),
            "models": list(c.get("models") or BASE_MODELS),
            # Agent capabilities: `actions` (arbitrary-URL tool calls) is
            # deliberately NOT in the default — it's the one path around the
            # gateway (spec: "The floor").  Enable per course, eyes open.
            # `or` is wrong here on purpose-of-omission: an explicit empty
            # list means "this course gets none," and collapsing it to the
            # default would fail OPEN on the one knob where that matters.
            "capabilities": (list(DEFAULT_CAPABILITIES)
                             if c.get("capabilities") is None
                             else [str(x).strip() for x in c["capabilities"]]),
            "group": str(c.get("group") or ""),
            "students": [str(e).strip().lower() for e in (c.get("students") or [])],
            "aliases": {str(k).strip().lower(): [str(a).strip().lower() for a in (v or [])]
                        for k, v in (c.get("aliases") or {}).items()},
        }
    return out


def save_courses(data: dict) -> None:
    d = os.path.dirname(COURSES_PATH) or "."
    fd, tmp = tempfile.mkstemp(dir=d, prefix=".courses.")
    try:
        with os.fdopen(fd, "w") as f:
            f.write("# The registrar's course records — see docs/registrar-spec.md.\n"
                    "# Operator-edited AND registrar-maintained (students, group ids).\n"
                    "# Gitignored: real rosters are student emails.\n")
            yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True)
        os.chmod(tmp, 0o644)
        os.replace(tmp, COURSES_PATH)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def course_models(course: dict, courses: dict) -> list[str]:
    """The course's model list ∪ its college's model pack."""
    models = list(course.get("models") or BASE_MODELS)
    college = course.get("college")
    if college:
        pack = (courses.get("colleges") or {}).get(college) or {}
        for m in pack.get("models") or []:
            if m not in models:
                models.append(m)
    return models


# ---- Keycloak admin: course clients, door roles --------------------------------

_kc_tok: dict = {"token": None, "exp": 0.0}


async def _kc_token(cx: httpx.AsyncClient) -> str:
    if _kc_tok["token"] and time.monotonic() < _kc_tok["exp"]:
        return _kc_tok["token"]
    r = await cx.post(
        f"{KC_URL}/realms/master/protocol/openid-connect/token",
        data={"grant_type": "password", "client_id": "admin-cli",
              "username": KC_ADMIN, "password": KC_ADMIN_PASSWORD},
    )
    r.raise_for_status()
    tok = r.json()
    _kc_tok.update(token=tok["access_token"],
                   exp=time.monotonic() + int(tok.get("expires_in", 60)) - 10)
    return _kc_tok["token"]


async def _kc(cx: httpx.AsyncClient, method: str, path: str, **kw) -> httpx.Response:
    tok = await _kc_token(cx)
    r = await cx.request(method, f"{KC_URL}/admin/realms/{KC_REALM}{path}",
                         headers={"Authorization": f"Bearer {tok}"}, **kw)
    if r.status_code == 401:  # token aged out mid-batch — one refresh, one retry
        _kc_tok["token"] = None
        tok = await _kc_token(cx)
        r = await cx.request(method, f"{KC_URL}/admin/realms/{KC_REALM}{path}",
                             headers={"Authorization": f"Bearer {tok}"}, **kw)
    return r


async def kc_ensure_client(cx: httpx.AsyncClient, slug: str) -> tuple[str, str]:
    """The course's OIDC client — created exact, never wildcarded.
    -> (internal uuid, client secret)"""
    r = await _kc(cx, "GET", f"/clients?clientId={slug}")
    r.raise_for_status()
    found = r.json()
    if found:
        uuid = found[0]["id"]
    else:
        body = {
            "clientId": slug,
            "name": f"aLLManac course {slug}",
            "protocol": "openid-connect",
            "publicClient": False,
            "standardFlowEnabled": True,
            "directAccessGrantsEnabled": False,
            "redirectUris": [f"https://{slug}.{ALMANAC_DOMAIN}/oauth/openid/callback"],
            "webOrigins": ["+"],
            "attributes": {"post.logout.redirect.uris": "+"},
        }
        r = await _kc(cx, "POST", "/clients", json=body)
        if r.status_code not in (201, 409):
            r.raise_for_status()
        r = await _kc(cx, "GET", f"/clients?clientId={slug}")
        r.raise_for_status()
        uuid = r.json()[0]["id"]
    r = await _kc(cx, "GET", f"/clients/{uuid}/client-secret")
    r.raise_for_status()
    secret = r.json().get("value") or ""
    if not secret:
        r = await _kc(cx, "POST", f"/clients/{uuid}/client-secret")
        r.raise_for_status()
        secret = r.json().get("value", "")
    return uuid, secret


async def kc_ensure_client_roles(cx: httpx.AsyncClient, uuid: str) -> dict:
    """admin = full control of the instance; member = the door itself
    (OPENID_REQUIRED_ROLE).  -> {name: role representation}"""
    r = await _kc(cx, "GET", f"/clients/{uuid}/roles")
    r.raise_for_status()
    have = {x["name"]: x for x in r.json()}
    for name, desc in (("admin", "course staff — instance admin"),
                       ("member", "enrolled — may sign in")):
        if name not in have:
            rr = await _kc(cx, "POST", f"/clients/{uuid}/roles",
                           json={"name": name, "description": desc})
            if rr.status_code not in (201, 409):
                rr.raise_for_status()
    r = await _kc(cx, "GET", f"/clients/{uuid}/roles")
    r.raise_for_status()
    return {x["name"]: x for x in r.json()}


async def kc_user_id(cx: httpx.AsyncClient, email: str) -> str | None:
    """None = no realm user yet.  With brokered login (Globus later) users
    materialize on FIRST sign-in — grants for them succeed on the next
    reconcile, and the anti-join in course_usage names the stragglers."""
    r = await _kc(cx, "GET", f"/users?email={email}&exact=true")
    r.raise_for_status()
    users = r.json()
    return users[0]["id"] if users else None


async def kc_set_client_role(cx: httpx.AsyncClient, user_id: str, client_uuid: str,
                             role: dict, grant: bool) -> None:
    method = "POST" if grant else "DELETE"
    r = await _kc(cx, method,
                  f"/users/{user_id}/role-mappings/clients/{client_uuid}",
                  json=[{"id": role["id"], "name": role["name"]}])
    if r.status_code not in (204, 409):
        r.raise_for_status()


# ---- LiteLLM: teams (the course pool), keys (the fuses) ------------------------

def _ll_headers() -> dict:
    return {"Authorization": f"Bearer {LITELLM_MASTER_KEY}",
            "Content-Type": "application/json"}


async def ll_ensure_team(cx: httpx.AsyncClient, slug: str, name: str,
                         budget: float, models: list[str]) -> None:
    """One team per course = the ONE pool chat + vAPI keys drain.  team_id
    is the slug itself — greppable in the ledger."""
    r = await cx.get(f"{LITELLM_URL}/team/info", params={"team_id": slug},
                     headers=_ll_headers())
    if r.status_code == 200:
        r = await cx.post(f"{LITELLM_URL}/team/update", headers=_ll_headers(),
                          json={"team_id": slug, "team_alias": name,
                                "max_budget": budget, "models": models})
        r.raise_for_status()
        return
    r = await cx.post(f"{LITELLM_URL}/team/new", headers=_ll_headers(),
                      json={"team_id": slug, "team_alias": name,
                            "max_budget": budget, "models": models})
    r.raise_for_status()


async def ll_mint_key(cx: httpx.AsyncClient, slug: str, models: list[str],
                      budget: float, user_id: str | None,
                      alias: str) -> str:
    body = {
        "team_id": slug,
        "models": models,
        "max_budget": budget,
        "key_alias": alias,
        # metadata.tags, NOT top-level tags — top-level is an Enterprise
        # wall (403 license) on our pin; metadata.tags rolls to /spend/tags:
        "metadata": {"owner": slug, "tags": [f"owner:{slug}"]},
    }
    if user_id:
        body["user_id"] = user_id
    r = await cx.post(f"{LITELLM_URL}/key/generate", headers=_ll_headers(),
                      json=body)
    r.raise_for_status()
    return r.json()["key"]


async def ll_delete_key(cx: httpx.AsyncClient, key: str) -> bool:
    r = await cx.post(f"{LITELLM_URL}/key/delete", headers=_ll_headers(),
                      json={"keys": [key]})
    return r.status_code == 200


async def ll_key_spend(cx: httpx.AsyncClient, key: str) -> float:
    r = await cx.get(f"{LITELLM_URL}/key/info", params={"key": key},
                     headers=_ll_headers())
    if r.status_code != 200:
        return 0.0
    return float((r.json().get("info") or {}).get("spend") or 0.0)


# ---- OpenBao: the escrow -------------------------------------------------------

_bao_tok: dict = {"token": None, "exp": 0.0}


def bao_configured() -> bool:
    return bool(BAO_ROLE_ID and BAO_SECRET_ID)


async def _bao_token(cx: httpx.AsyncClient) -> str:
    if not bao_configured():
        raise RuntimeError("OpenBao is not configured — run: just bao-init")
    if _bao_tok["token"] and time.monotonic() < _bao_tok["exp"]:
        return _bao_tok["token"]
    r = await cx.post(f"{BAO_ADDR}/v1/auth/approle/login",
                      json={"role_id": BAO_ROLE_ID, "secret_id": BAO_SECRET_ID})
    r.raise_for_status()
    auth = r.json()["auth"]
    _bao_tok.update(token=auth["client_token"],
                    exp=time.monotonic() + int(auth.get("lease_duration", 300)) - 30)
    return _bao_tok["token"]


async def _bao(cx: httpx.AsyncClient, method: str, path: str, **kw) -> httpx.Response:
    tok = await _bao_token(cx)
    r = await cx.request(method, f"{BAO_ADDR}/v1/{path}",
                         headers={"X-Vault-Token": tok}, **kw)
    if r.status_code == 403:  # lease expired mid-batch — one relogin, one retry
        _bao_tok["token"] = None
        tok = await _bao_token(cx)
        r = await cx.request(method, f"{BAO_ADDR}/v1/{path}",
                             headers={"X-Vault-Token": tok}, **kw)
    return r


def _student_path(slug: str, email: str) -> str:
    return f"{BAO_MOUNT}/data/courses/{slug}/students/{email}"


async def escrow_write(slug: str, email_or_svc: str, record: dict) -> None:
    async with httpx.AsyncClient(timeout=20) as cx:
        r = await _bao(cx, "POST", _student_path(slug, email_or_svc)
                       if "@" in email_or_svc else
                       f"{BAO_MOUNT}/data/courses/{slug}/{email_or_svc}",
                       json={"data": record})
        r.raise_for_status()


async def escrow_read(slug: str, email_or_svc: str) -> dict | None:
    if not bao_configured():
        return None
    async with httpx.AsyncClient(timeout=20) as cx:
        path = (_student_path(slug, email_or_svc) if "@" in email_or_svc
                else f"{BAO_MOUNT}/data/courses/{slug}/{email_or_svc}")
        r = await _bao(cx, "GET", path)
        if r.status_code == 404:
            return None
        r.raise_for_status()
        return r.json()["data"]["data"]


async def escrow_delete(slug: str, email: str) -> None:
    """Soft delete — kv-v2 keeps version history; custody survives
    un-enrollment (docs/registrar-spec.md)."""
    async with httpx.AsyncClient(timeout=20) as cx:
        r = await _bao(cx, "DELETE", _student_path(slug, email))
        if r.status_code not in (204, 404):
            r.raise_for_status()


async def escrow_status(slug: str, emails: list[str]) -> dict:
    """{email: escrow record or None} — status for staff views (never keys)."""
    out: dict = {}
    if not bao_configured():
        return {e: None for e in emails}
    async with httpx.AsyncClient(timeout=30) as cx:
        for e in emails:
            r = await _bao(cx, "GET", _student_path(slug, e))
            if r.status_code == 404:
                out[e] = None
            else:
                r.raise_for_status()
                d = r.json()["data"]["data"]
                out[e] = {k: d[k] for k in ("minted_at", "budget") if k in d}
    return out


# ---- the reconcile verbs -------------------------------------------------------

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
