"""The chat databases — one Mongo, one database per instance, read as a census.

Holds no credential (Mongo is unauthenticated on the compose network and
reachable by nothing else), but it is the plane with the most to be careful
about, because it can see everything a course ever typed.  So the rule of
this file is written into its function signatures: **the census stops at
the envelope.**  Every query here returns counts, names, sizes, owners, and
timestamps — who has what, how big, how shared, when last touched.  No
message text, no conversation titles, no agent instructions.  Titles are
excluded deliberately even though they look like metadata: LibreChat
generates them from the first exchange, so a title is the content, shorter.

Two reads cross the line, and each crosses it on the owner's own request.
`agent_template`: a nomination is the author saying "copy this," and a
template without the instructions would be a name and a colour.
`owner_export` (2026-09-25): a person asking for their own conversations
and agents back — keyed on the email from the trusted headers, so the only
data it can ever select is the asker's.  Nobody else's content, and no
content for anyone but its owner.

Sync pymongo behind `asyncio.to_thread` — the registrar is an async
process, the driver's async flavour is another dependency to pin, and every
call here is a handful of aggregations against small collections.
"""

import asyncio
import re
from datetime import datetime

from pymongo import MongoClient

from .config import MONGO_URI

# The flagship's database has no suffix; a course's carries its slug —
# exactly what render.py writes into each instance's MONGO_URI.
FLAGSHIP_DB = "LibreChat"

_client: MongoClient | None = None


def _db(slug: str | None):
    global _client
    if _client is None:
        _client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=4000,
                              connectTimeoutMS=4000)
    return _client[FLAGSHIP_DB if slug is None else f"LibreChat_{slug}"]


def db_name(slug: str | None) -> str:
    return FLAGSHIP_DB if slug is None else f"LibreChat_{slug}"


def _iso(d) -> str | None:
    return d.strftime("%Y-%m-%d %H:%M UTC") if isinstance(d, datetime) else None


# ---- the census -----------------------------------------------------------------

def _census_sync(slug: str | None) -> dict:
    db = _db(slug)
    if db.name not in db.client.list_database_names():
        return {"db": db.name, "exists": False}

    users = {str(u["_id"]): u for u in db.users.find(
        {}, {"email": 1, "role": 1, "provider": 1, "createdAt": 1})}

    # Activity by user: conversations and their last touch.  Message text
    # is never selected; the messages collection is only ever counted.
    convos_by_user = {r["_id"]: r for r in db.conversations.aggregate([
        {"$group": {"_id": "$user", "conversations": {"$sum": 1},
                    "last_active": {"$max": "$updatedAt"}}}])}
    msgs_by_user = {r["_id"]: r for r in db.messages.aggregate([
        {"$group": {"_id": "$user", "messages": {"$sum": 1},
                    "tokens": {"$sum": {"$ifNull": ["$tokenCount", 0]}}}}])}

    people = []
    for uid, u in users.items():
        cv, ms = convos_by_user.get(uid, {}), msgs_by_user.get(uid, {})
        people.append({
            "email": (u.get("email") or "").lower(),
            "role": u.get("role") or "USER",
            "provider": u.get("provider"),
            "first_seen": _iso(u.get("createdAt")),
            "conversations": cv.get("conversations", 0),
            "messages": ms.get("messages", 0),
            "tokens": int(ms.get("tokens", 0) or 0),
            "last_active": _iso(cv.get("last_active")),
        })
    people.sort(key=lambda p: p["email"])

    # Files: name, size, owner, whether the RAG embedded it.  `user` is a
    # string user id on the file document.
    files = []
    for f in db.files.find({}, {"file_id": 1, "filename": 1, "bytes": 1, "user": 1,
                                "embedded": 1, "type": 1, "createdAt": 1}):
        owner = users.get(str(f.get("user")), {})
        files.append({
            "file_id": f.get("file_id"),
            "filename": f.get("filename"),
            "bytes": int(f.get("bytes") or 0),
            "owner": (owner.get("email") or str(f.get("user") or "")).lower(),
            "embedded": bool(f.get("embedded")),
            "type": f.get("type"),
            "created": _iso(f.get("createdAt")),
        })
    files.sort(key=lambda f: -f["bytes"])

    # Agents and their share scope.  Visibility is the ACL, not the author:
    # an entry with principalType public/role/group widens the audience past
    # the owner; extra user entries are named grants.
    acl: dict[str, dict] = {}
    for e in db.aclentries.find({"resourceType": "agent"},
                                {"resourceId": 1, "principalType": 1, "principalId": 1}):
        row = acl.setdefault(str(e["resourceId"]),
                             {"public": False, "roles": [], "groups": 0, "users": 0})
        pt = (e.get("principalType") or "").lower()
        if pt == "public":
            row["public"] = True
        elif pt == "role":
            row["roles"].append(str(e.get("principalId")))
        elif pt == "group":
            row["groups"] += 1
        elif pt == "user":
            row["users"] += 1
    agents = []
    for a in db.agents.find({}, {"id": 1, "name": 1, "author": 1, "model": 1,
                                 "provider": 1, "tools": 1, "actions": 1,
                                 "tool_resources": 1, "updatedAt": 1}):
        scope = acl.get(str(a["_id"]), {"public": False, "roles": [], "groups": 0, "users": 0})
        tr = a.get("tool_resources") or {}
        n_files = sum(len((v or {}).get("file_ids") or []) for v in tr.values()
                      if isinstance(v, dict))
        owner = users.get(str(a.get("author")), {})
        if scope["public"]:
            share = "public"
        elif scope["roles"]:
            share = "role:" + ",".join(scope["roles"])
        elif scope["groups"]:
            share = f"groups:{scope['groups']}"
        elif scope["users"] > 1:
            share = f"users:{scope['users'] - 1}"
        else:
            share = "private"
        agents.append({
            "agent_id": a.get("id"),
            "name": a.get("name"),
            "owner": (owner.get("email") or str(a.get("author") or "")).lower(),
            "model": a.get("model"),
            "provider": a.get("provider"),
            "tools": sorted(a.get("tools") or []),
            "actions": len(a.get("actions") or []),
            "files": n_files,
            "share": share,
            "updated": _iso(a.get("updatedAt")),
        })
    agents.sort(key=lambda a: (a["share"] == "private", a["name"] or ""))

    # Config overrides — what an ADMIN wrote through /api/admin/config.  The
    # edge refuses those writes now (render.py, ADMIN_CONFIG_WALL), but one
    # saved before the wall still applies at every request, and a base-scope
    # override is how a course's env leaves the box (design-walls.md, "A
    # server staff add in the chat UI never sees the container's
    # environment").  Section NAMES only: the aggregation turns `overrides`
    # into its key list inside Mongo, so a value — which may be a header
    # holding a secret — never reaches this process.  Tombstones are field
    # paths (names, not values) and are reported by their top-level section.
    config_overrides = []
    for d in db.configs.aggregate([
            {"$project": {
                "_id": 0, "principalType": 1, "principalId": 1, "isActive": 1,
                "updatedAt": 1,
                "sections": {"$map": {
                    "input": {"$objectToArray": {"$ifNull": ["$overrides", {}]}},
                    "as": "kv", "in": "$$kv.k"}},
                "tombstones": {"$ifNull": ["$tombstones", []]}}}]):
        removed = sorted({str(t).split(".")[0] for t in d.get("tombstones") or []})
        config_overrides.append({
            "principal": f"{d.get('principalType')}/{d.get('principalId')}",
            "active": d.get("isActive", True) is not False,
            "sections": sorted(d.get("sections") or []),
            "removes": removed,
            "updated": _iso(d.get("updatedAt")),
        })
    config_overrides.sort(key=lambda o: o["principal"])

    stats = db.command("dbStats")
    return {
        "db": db.name,
        "exists": True,
        "users": people,
        "files": files,
        "agents": agents,
        "config_overrides": config_overrides,
        "totals": {
            "users": len(people),
            "conversations": sum(p["conversations"] for p in people),
            "messages": sum(p["messages"] for p in people),
            "tokens": sum(p["tokens"] for p in people),
            "files": len(files),
            "file_bytes": sum(f["bytes"] for f in files),
            "agents": len(agents),
            "agents_shared": sum(1 for a in agents if a["share"] != "private"),
            "config_overrides": len(config_overrides),
            "data_bytes": int(stats.get("dataSize") or 0),
            "storage_bytes": int(stats.get("storageSize") or 0),
        },
    }


async def list_databases() -> list[str]:
    return await asyncio.to_thread(lambda: _db(None).client.list_database_names())


async def census(slug: str | None) -> dict:
    """Everything the fleet view knows about one instance — envelope only."""
    return await asyncio.to_thread(_census_sync, slug)


# ---- nominations: the one read past the envelope -------------------------------

def _agent_template_sync(slug: str | None, agent_id: str) -> dict | None:
    db = _db(slug)
    a = db.agents.find_one({"id": agent_id})
    if a is None:
        return None
    owner = db.users.find_one({"_id": a.get("author")}, {"email": 1}) or {}
    tr = a.get("tool_resources") or {}
    knowledge = []
    for kind, v in tr.items():
        ids = (v or {}).get("file_ids") or [] if isinstance(v, dict) else []
        for f in db.files.find({"file_id": {"$in": ids}}, {"filename": 1, "bytes": 1}):
            knowledge.append({"tool": kind, "filename": f.get("filename"),
                              "bytes": int(f.get("bytes") or 0)})
    return {
        "agent_id": a.get("id"),
        "name": a.get("name"),
        "description": a.get("description") or "",
        "instructions": a.get("instructions") or "",
        "provider": a.get("provider"),
        "model": a.get("model"),
        "model_parameters": a.get("model_parameters") or {},
        "tools": sorted(a.get("tools") or []),
        "actions": len(a.get("actions") or []),
        "knowledge": knowledge,
        "owner": (owner.get("email") or "").lower(),
        "updated": _iso(a.get("updatedAt")),
    }


async def agent_template(slug: str | None, agent_id: str) -> dict | None:
    """The portable shape of one agent — instructions included, because the
    author asked for it to be copied.  None if there is no such agent."""
    return await asyncio.to_thread(_agent_template_sync, slug, agent_id)


# ---- the owner's export: the other read past the envelope ---------------------

_OWNER = 15      # LibreChat's agent_owner permBits (view|edit|delete|share)


def _owner_export_sync(slug: str, email: str) -> dict:
    db = _db(slug)
    if db.name not in db.client.list_database_names():
        return {"found": False}
    u = db.users.find_one({"email": {"$regex": f"^{re.escape(email)}$", "$options": "i"}},
                          {"_id": 1})
    if u is None:
        return {"found": False}
    uid, suid = u["_id"], str(u["_id"])
    convos = []
    for c in db.conversations.find({"user": suid},
                                   {"_id": 0, "conversationId": 1, "title": 1, "createdAt": 1,
                                    "updatedAt": 1, "model": 1, "endpoint": 1,
                                    "agent_id": 1}).sort("createdAt", 1):
        # `user` on the message as well as the conversation: belt and braces,
        # so a conversation id can never pull in anyone else's turn.
        c["messages"] = list(db.messages.find(
            {"conversationId": c["conversationId"], "user": suid},
            {"_id": 0, "messageId": 1, "parentMessageId": 1, "sender": 1,
             "isCreatedByUser": 1, "model": 1, "createdAt": 1, "text": 1,
             "content": 1, "error": 1}).sort("createdAt", 1))
        convos.append(c)
    # Owned = authored, or granted the owner role.  An agent can have several
    # owners (@xram, 2026-09-25); each gets a copy, and the copy names them all.
    owned = {a["_id"] for a in db.agents.find({"author": uid}, {"_id": 1})}
    owned |= {e["resourceId"] for e in db.aclentries.find(
        {"resourceType": "agent", "principalType": "user", "principalId": uid,
         "permBits": {"$bitsAllSet": _OWNER}}, {"resourceId": 1})}
    agents = []
    for a in db.agents.find({"_id": {"$in": list(owned)}}, {"id": 1}):
        tpl = _agent_template_sync(slug, a["id"])
        if tpl is None:
            continue
        ids = [e["principalId"] for e in db.aclentries.find(
            {"resourceType": "agent", "resourceId": a["_id"], "principalType": "user",
             "permBits": {"$bitsAllSet": _OWNER}}, {"principalId": 1})]
        tpl["owners"] = sorted({(x.get("email") or "").lower() for x in
                                db.users.find({"_id": {"$in": ids}}, {"email": 1})}
                               | ({tpl["owner"]} if tpl["owner"] else set()))
        agents.append(tpl)
    files = [{"filename": f.get("filename"), "bytes": int(f.get("bytes") or 0),
              "type": f.get("type"), "created": _iso(f.get("createdAt"))}
             for f in db.files.find({"user": {"$in": [suid, uid]}},
                                    {"filename": 1, "bytes": 1, "type": 1, "createdAt": 1})]
    return {"found": True, "conversations": convos, "agents": agents, "files": files}


async def owner_export(slug: str, email: str) -> dict:
    """Everything of `email`'s in one course: conversations with every
    message, agents they own (as templates, owners named), and the list of
    files they uploaded.  {"found": False} when they never used it.  The
    caller must have taken `email` from the trusted headers — this function
    is the wall's one door, and it trusts its argument."""
    return await asyncio.to_thread(_owner_export_sync, slug, email)
