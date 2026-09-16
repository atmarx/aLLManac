"""Keycloak admin — course OIDC clients and the door roles.

Holds the Keycloak admin password.  Every function takes the httpx client
from its caller: the verbs own the connection so one reconcile run is one
pool, and the token cache below is process-wide on purpose (a batch of 200
enrollments is one admin login, not two hundred).
"""

import time

import httpx

from .config import ALMANAC_DOMAIN, KC_ADMIN, KC_ADMIN_PASSWORD, KC_REALM, KC_URL

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
    """None = no realm user yet.  Read-only lookup; the roster path uses
    kc_ensure_user so the door can be granted before first sign-in."""
    r = await _kc(cx, "GET", f"/users?email={email}&exact=true")
    r.raise_for_status()
    users = r.json()
    return users[0]["id"] if users else None


async def kc_ensure_user(cx: httpx.AsyncClient, email: str) -> tuple[str, bool]:
    """The realm user for an email — found, or PRE-CREATED (username = email,
    no credentials).  -> (id, created)

    Why pre-create: the door to a course is a client role, and a role can
    only be granted to a user that exists.  Before this, a user only came
    into being on first brokered sign-in, so a rostered student's first
    visit was bounced at the door until someone re-ran the roster (found by
    @xram walking the Instructor Guide, 2026-09-15).  Email is the join key
    everywhere else in the spec; here it becomes the join key at the
    identity layer too.  kc_ensure_autolink is the other half: it makes the
    IdP's first login land on THIS account instead of asking the student to
    confirm a link or minting a second user.

    A pre-created user has no password.  On a box without an IdP (the lab
    box's username/password realm) an operator sets one by hand — the demo
    users in the realm import are exactly that.
    """
    uid = await kc_user_id(cx, email)
    if uid:
        return uid, False
    body = {"username": email, "email": email, "enabled": True,
            # emailVerified: the IdP asserts the email; without this the
            # auto-link authenticator may still stop to verify it.
            "emailVerified": True}
    r = await _kc(cx, "POST", "/users", json=body)
    if r.status_code == 201:
        return r.headers["Location"].rstrip("/").rsplit("/", 1)[-1], True
    if r.status_code != 409:          # 409 = raced another reconcile; re-read
        r.raise_for_status()
    uid = await kc_user_id(cx, email)
    if not uid:
        raise RuntimeError(f"keycloak: could not create or find user {email}")
    return uid, False


AUTOLINK_FLOW = "almanac first broker login"
_AUTOLINK_STEPS = ("idp-detect-existing-broker-user", "idp-auto-link")


async def kc_ensure_autolink(cx: httpx.AsyncClient) -> str:
    """A first-broker-login flow that links an IdP login to the existing
    realm user with the same email — no "account already exists" prompt,
    no second account — and every identity provider pointed at it.
    Idempotent; run on every ensure_course.  -> flow alias

    Keycloak's stock flow ends in "Confirm link existing account" +
    "Verify existing account by email", which is right for a public realm
    and wrong for a roster: we made that account on purpose, from the
    roster, and the IdP already vouched for the email.  The two steps used
    instead are Keycloak's own: detect the existing user by email, then
    set it — both REQUIRED, in that order.
    """
    r = await _kc(cx, "GET", "/authentication/flows")
    r.raise_for_status()
    if not any(f["alias"] == AUTOLINK_FLOW for f in r.json()):
        rr = await _kc(cx, "POST", "/authentication/flows",
                       json={"alias": AUTOLINK_FLOW, "providerId": "basic-flow",
                             "topLevel": True, "builtIn": False,
                             "description": "aLLManac: link IdP logins to the "
                                            "roster-created realm user by email"})
        if rr.status_code not in (201, 409):
            rr.raise_for_status()
    path = f"/authentication/flows/{AUTOLINK_FLOW.replace(' ', '%20')}/executions"
    r = await _kc(cx, "GET", path)
    r.raise_for_status()
    have = {e.get("providerId"): e for e in r.json()}
    for provider in _AUTOLINK_STEPS:
        if provider not in have:
            rr = await _kc(cx, "POST", path + "/execution", json={"provider": provider})
            if rr.status_code not in (201, 204, 409):
                rr.raise_for_status()
    r = await _kc(cx, "GET", path)
    r.raise_for_status()
    for e in r.json():
        if e.get("providerId") in _AUTOLINK_STEPS and e.get("requirement") != "REQUIRED":
            rr = await _kc(cx, "PUT", path, json={"id": e["id"], "requirement": "REQUIRED"})
            if rr.status_code not in (202, 204):
                rr.raise_for_status()
    r = await _kc(cx, "GET", "/identity-provider/instances")
    r.raise_for_status()
    for idp in r.json():
        if idp.get("firstBrokerLoginFlowAlias") != AUTOLINK_FLOW:
            idp["firstBrokerLoginFlowAlias"] = AUTOLINK_FLOW
            rr = await _kc(cx, "PUT", f"/identity-provider/instances/{idp['alias']}", json=idp)
            if rr.status_code != 204:
                rr.raise_for_status()
    return AUTOLINK_FLOW


async def kc_set_client_role(cx: httpx.AsyncClient, user_id: str, client_uuid: str,
                             role: dict, grant: bool) -> None:
    method = "POST" if grant else "DELETE"
    r = await _kc(cx, method,
                  f"/users/{user_id}/role-mappings/clients/{client_uuid}",
                  json=[{"id": role["id"], "name": role["name"]}])
    if r.status_code not in (204, 409):
        r.raise_for_status()


# ---- the census: read-only views for the fleet tools --------------------------

async def kc_client_uuid(cx: httpx.AsyncClient, slug: str) -> str | None:
    """The course client's internal id, or None if it was never provisioned.
    Read-only twin of kc_ensure_client — the census must not create."""
    r = await _kc(cx, "GET", f"/clients?clientId={slug}")
    r.raise_for_status()
    found = r.json()
    return found[0]["id"] if found else None


async def kc_role_holders(cx: httpx.AsyncClient, client_uuid: str, role: str) -> list[str]:
    """Emails holding a client role — the door as Keycloak actually has it,
    as opposed to the roster as the registrar wishes it."""
    out: list[str] = []
    first = 0
    while True:
        r = await _kc(cx, "GET", f"/clients/{client_uuid}/roles/{role}/users",
                      params={"first": first, "max": 200})
        if r.status_code == 404:          # role never created
            return out
        r.raise_for_status()
        page = r.json()
        out += [(u.get("email") or u.get("username") or "").lower() for u in page]
        if len(page) < 200:
            return sorted(e for e in out if e)
        first += 200


async def kc_active_sessions(cx: httpx.AsyncClient, client_uuid: str) -> list[str]:
    """Emails with a live session on this client right now.  Session
    metadata only — Keycloak's session record carries no content."""
    r = await _kc(cx, "GET", f"/clients/{client_uuid}/user-sessions",
                  params={"first": 0, "max": 500})
    if r.status_code == 404:
        return []
    r.raise_for_status()
    emails = {(s.get("username") or "").lower() for s in r.json()}
    return sorted(e for e in emails if e)
