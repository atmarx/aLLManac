"""Nominations — registrar/nominations.yaml, read/append/mark.

A nomination is an author saying "this agent is worth copying" about an
agent in their own course.  The record is small on purpose: who, which
course, which agent, one sentence of why, and what became of it.  Like the
course records it lives on the state volume and is gitignored, because it
names people.  No network, no credential — the courses plane's sibling.
"""

import os
import secrets as pysecrets
import tempfile
from datetime import datetime, timezone

import yaml

from .config import NOMINATIONS_PATH

STATUSES = ("nominated", "exported", "declined")


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def load_nominations() -> list[dict]:
    try:
        with open(NOMINATIONS_PATH) as f:
            raw = yaml.safe_load(f) or {}
    except OSError:
        return []
    return list(raw.get("nominations") or [])


def _save(rows: list[dict]) -> None:
    d = os.path.dirname(NOMINATIONS_PATH) or "."
    fd, tmp = tempfile.mkstemp(dir=d, prefix=".nominations.")
    try:
        with os.fdopen(fd, "w") as f:
            f.write("# Agent nominations — see docs/registrar-spec.md, \"The census\".\n"
                    "# Registrar-maintained; gitignored (names people).\n")
            yaml.safe_dump({"nominations": rows}, f, sort_keys=False, allow_unicode=True)
        os.chmod(tmp, 0o644)
        os.replace(tmp, NOMINATIONS_PATH)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def add_nomination(course: str, agent_id: str, name: str, by: str, note: str) -> dict:
    """Append one — or return the open nomination that already exists for
    this agent, so nominating twice is a no-op rather than a duplicate."""
    rows = load_nominations()
    for r in rows:
        if r["course"] == course and r["agent_id"] == agent_id and r["status"] == "nominated":
            return r
    rec = {"id": pysecrets.token_hex(3), "course": course, "agent_id": agent_id,
           "name": name, "by": by, "note": note.strip()[:500], "at": _now(),
           "status": "nominated"}
    rows.append(rec)
    _save(rows)
    return rec


def mark_nomination(nid: str, status: str, by: str, where: str | None = None) -> dict | None:
    assert status in STATUSES
    rows = load_nominations()
    for r in rows:
        if r["id"] == nid:
            r["status"] = status
            r["decided_by"] = by
            r["decided_at"] = _now()
            if where:
                r["exported_to"] = where
            _save(rows)
            return r
    return None
