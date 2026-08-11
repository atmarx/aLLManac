"""LiteLLM — teams (the course pool) and keys (the fuses).

Holds the LiteLLM master key, which is the mint.  Named `gateway` rather
than `litellm` for one boring reason: a module named after the pip package
is a shadowing trap waiting for the day something in here imports the real
one.
"""

import httpx

from .config import LITELLM_MASTER_KEY, LITELLM_URL


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
