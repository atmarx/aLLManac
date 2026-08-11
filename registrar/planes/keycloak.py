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
