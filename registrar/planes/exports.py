"""Owner exports — one person's data from one course, as a zip on the state
volume, reachable for EXPORT_TTL_HOURS by a link nobody can guess.

The file is the deliverable and the token is the key: whoever holds the
link can download it, which is why the link is only ever handed to the
person the export is OF (in their own chat, or mailed to their own
address), why it dies after a day, and why nothing here can be asked for
someone else — the email comes from the trusted headers, never an argument.
No network, no credential; the census plane reads, verbs composes, this
writes, serves and forgets.
"""

import io
import json
import os
import re
import secrets as pysecrets
import time
import zipfile
from datetime import datetime, timezone

import yaml

from .config import EXPORT_TTL_HOURS, EXPORTS_PATH, PLATFORM

TOKEN_RE = re.compile(r"^[A-Za-z0-9_-]{24,64}$")
# Asking twice in a few minutes is a retry, not a second export — hand back
# the same link instead of writing the same semester to disk again.
REUSE_SECONDS = 10 * 60

# The download is named for the platform the person knows, not the project
# underneath it — PLATFORM_NAME, made safe for a filename ("AI Classroom" →
# ai-classroom-<course>-<date>.zip).
FILE_PREFIX = (re.sub(r"[^a-z0-9]+", "-", PLATFORM.lower())
               .strip("-") or "export")


def _paths(token: str) -> tuple[str, str]:
    return (os.path.join(EXPORTS_PATH, f"{token}.zip"),
            os.path.join(EXPORTS_PATH, f"{token}.json"))


def _ts(epoch: float) -> str:
    return datetime.fromtimestamp(epoch, timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def purge() -> int:
    """Delete every export past its time.  Called on every write and every
    download, so an idle box keeps at most a day of them."""
    n, now = 0, time.time()
    try:
        names = os.listdir(EXPORTS_PATH)
    except FileNotFoundError:
        return 0
    for name in names:
        if not name.endswith(".json"):
            continue
        token = name[:-5]
        z, m = _paths(token)
        try:
            with open(m) as f:
                expires = float(json.load(f)["expires"])
        except (OSError, ValueError, KeyError):
            expires = 0.0            # unreadable meta: the export is unservable anyway
        if expires <= now:
            for p in (z, m):
                try:
                    os.remove(p)
                except FileNotFoundError:
                    pass
            n += 1
    return n


def meta(token: str) -> dict | None:
    """The live export behind a token, or None — expired, unknown, or not
    token-shaped (checked first: the token lands in a path)."""
    token = (token or "").strip()
    if not TOKEN_RE.match(token):
        return None
    z, m = _paths(token)
    try:
        with open(m) as f:
            rec = json.load(f)
    except (OSError, ValueError):
        return None
    if float(rec.get("expires", 0)) <= time.time() or not os.path.exists(z):
        return None
    return {**rec, "token": token, "path": z,
            "expires_at": _ts(float(rec["expires"]))}


def recent(email: str, slug: str) -> dict | None:
    """A live export of this person's data from this course made in the
    last few minutes, if there is one."""
    purge()
    try:
        names = os.listdir(EXPORTS_PATH)
    except FileNotFoundError:
        return None
    now = time.time()
    for name in names:
        if name.endswith(".json"):
            rec = meta(name[:-5])
            if (rec and rec["email"] == email and rec["course"] == slug
                    and now - float(rec["created"]) < REUSE_SECONDS):
                return rec
    return None


# ---- the archive ---------------------------------------------------------------

def _safe(s: str, n: int = 50) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-")[:n] or "untitled"


def _when(v) -> str:
    return v.strftime("%Y-%m-%d %H:%M UTC") if isinstance(v, datetime) else str(v or "")


def _part_text(p: dict) -> str:
    """One LibreChat content part as Markdown.  Text is text; reasoning is
    folded so it doesn't bury the answer; a tool call is one line — its
    name and whether it came back — because the output is often a page of
    JSON the person already saw summarised in the reply."""
    kind = p.get("type")
    val = p.get(kind) if kind else None
    if isinstance(val, dict) and "value" in val:
        val = val["value"]
    if kind == "text":
        return str(val or "")
    if kind == "think":
        return f"<details><summary>Reasoning</summary>\n\n{val or ''}\n\n</details>" if val else ""
    if kind == "tool_call":
        tc = val if isinstance(val, dict) else {}
        return f"> *tool: {tc.get('name', '?')}*"
    return f"> *[{kind}]*" if kind else ""


def _message_md(m: dict) -> str:
    who = "**You**" if m.get("isCreatedByUser") else f"**{m.get('sender') or m.get('model') or 'Assistant'}**"
    parts = m.get("content")
    if isinstance(parts, list) and parts:
        body = "\n\n".join(t for t in (_part_text(p) for p in parts if isinstance(p, dict)) if t)
    else:
        body = m.get("text") or ""
    flag = " *(this reply ended in an error)*" if m.get("error") else ""
    return f"{who} · {_when(m.get('createdAt'))}{flag}\n\n{body}\n"


def _conversation_md(c: dict) -> str:
    head = [f"# {c.get('title') or 'Untitled conversation'}", "",
            f"- started {_when(c.get('createdAt'))}, last touched {_when(c.get('updatedAt'))}",
            f"- model: {c.get('model') or '—'}"
            + (f" · agent: {c['agent_id']}" if c.get("agent_id") else ""), "", "---", ""]
    return "\n".join(head) + "\n---\n\n".join(_message_md(m) for m in c["messages"])


def _readme(course: dict, email: str, data: dict, created: float) -> str:
    L = [f"# Your data from {course['name']} ({course['slug']})", "",
         f"Exported for **{email}** on {_ts(created)} by {PLATFORM}, "
         "because you asked for it.  Only your own data is here — conversations "
         "you had and agents you own.", "",
         f"- **conversations/** — {len(data['conversations'])} conversation(s), one "
         "Markdown file each, both sides of every exchange.  Regenerated replies "
         "appear in the order they were made.  `conversations.json` is the same "
         "thing for a program to read.",
         f"- **agents/** — {len(data['agents'])} agent(s) you own, each as a template "
         "you can read or rebuild from.  An agent with more than one owner is "
         "exported to each of them, and its file names every owner.  Knowledge "
         "files are listed by name, not carried.", ""]
    if data["files"]:
        L += ["## Files you uploaded — listed, not included", "",
              "Download these from the course chat while it's still online.", "",
              "| file | size | uploaded |", "|---|---:|---|"]
        L += [f"| {f['filename']} | {f['bytes']:,} bytes | {f['created'] or ''} |"
              for f in data["files"]]
        L.append("")
    return "\n".join(L)


def write(course: dict, email: str, data: dict, agent_docs: list[dict]) -> dict:
    """Build the zip, write it beside its meta, and return the record the
    tool hands back.  `agent_docs` are already template-shaped (render)."""
    purge()
    os.makedirs(EXPORTS_PATH, mode=0o700, exist_ok=True)
    created = time.time()
    token = pysecrets.token_urlsafe(24)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("README.md", _readme(course, email, data, created))
        for i, c in enumerate(data["conversations"], 1):
            day = _when(c.get("createdAt"))[:10]
            z.writestr(f"conversations/{i:03d}-{day}-{_safe(c.get('title'))}.md",
                       _conversation_md(c))
        z.writestr("conversations.json",
                   json.dumps(data["conversations"], indent=2, default=str,
                              ensure_ascii=False))
        for doc in agent_docs:
            name = _safe(doc["template"]["name"]) + "-" + _safe(doc["provenance"]["agent_id"], 12)
            z.writestr(f"agents/{name}.yaml",
                       f"# Exported for its owner by {PLATFORM}.\n"
                       + yaml.safe_dump(doc, sort_keys=False, allow_unicode=True, width=1000))
    zpath, mpath = _paths(token)
    rec = {"email": email, "course": course["slug"], "created": created,
           "expires": created + EXPORT_TTL_HOURS * 3600,
           "filename": f"{FILE_PREFIX}-{course['slug']}-{_ts(created)[:10]}.zip",
           "conversations": len(data["conversations"]),
           "agents": len(agent_docs), "files_listed": len(data["files"]),
           "bytes": buf.tell()}
    for path, blob in ((zpath, buf.getvalue()),
                       (mpath, json.dumps(rec).encode())):
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "wb") as f:
            f.write(blob)
    return {**rec, "token": token, "expires_at": _ts(rec["expires"])}
