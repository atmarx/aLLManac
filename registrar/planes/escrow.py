"""OpenBao — the escrow.  Custody of every key this registrar ever minted.

Holds the AppRole.  Unlike the keycloak and gateway planes, these functions
open their own short-lived client: escrow reads happen from tool calls that
have no reconcile run around them (`my_key` is one GET), and threading a
connection through for that is ceremony without a payoff.
"""

import time

import httpx

from .config import BAO_ADDR, BAO_MOUNT, BAO_ROLE_ID, BAO_SECRET_ID

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
