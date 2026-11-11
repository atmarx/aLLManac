"""The draft: the fields an agent drafted from a conversation, which the
person reviews, changes, confirms and asserts on a page outside the chat.

Counsel's list is the whole of it (docs/staff-portal.md, "What leaves the
chat is fields, never the conversation"): per field the agent's draft, the
value, when the person confirmed it by this server's clock, and whether the
value they confirmed differs from the draft.  No conversation, no question
and answer, nothing the agent said.  A submission is assembled from those
alone, by `submission`.

Two writers, kept apart:
  * the agent (`agent_write`): drafts fields, never a person-only one, never
    one the person has already changed or confirmed, and an empty call or an
    empty value writes nothing, so exploring makes no record;
  * the person, through the page (`person_set`, `confirm`, `put_draft_back`,
    `delete`, `submit`): the only one who can confirm, and the only one who
    can send.

An unsent draft is deleted on its own after INTAKE_DRAFT_DAYS; a missing,
expired and deleted draft are one answer ("no such draft").  A sent draft is
the office's record and is kept as the office's retention says, not here.
"""

import datetime as dt
import secrets
import sqlite3

from . import words
from .fields import choices

SCHEMA = """
CREATE TABLE IF NOT EXISTS draft (
  id TEXT PRIMARY KEY,              -- unguessable; the page's address
  owner TEXT NOT NULL,              -- the email the chat stamped when it was opened
  created_at TEXT NOT NULL,
  expires_at TEXT NOT NULL,         -- deleted on its own after this, unless sent
  sent_at TEXT,                     -- set once, by the person's assertion
  reference TEXT                    -- what the office and the person quote
);
CREATE TABLE IF NOT EXISTS field (
  draft_id TEXT NOT NULL REFERENCES draft(id) ON DELETE CASCADE,
  field_id TEXT NOT NULL,
  draft_value TEXT,                 -- what the agent drafted, or NULL
  value TEXT,                       -- what the page holds now
  confirmed_at TEXT,                -- this server's clock, never the browser's
  changed INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (draft_id, field_id)
);
"""


class Gone(Exception):
    """No such draft for this person: missing, expired, deleted, or theirs
    to see only if they are its owner.  One answer for all of them."""


class Blocked(Exception):
    """The person's action can't go through yet; the message says why."""


def connect(path: str) -> sqlite3.Connection:
    c = sqlite3.connect(path, isolation_level=None)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys=ON")
    c.executescript(SCHEMA)
    return c


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def _norm(s: str | None) -> str:
    return " ".join((s or "").split())


def sweep(c, at: str | None = None) -> int:
    """Delete every unsent draft past its expiry.  Run before every read, so
    an expired draft is never shown, whatever a timer did."""
    return c.execute("DELETE FROM draft WHERE sent_at IS NULL AND expires_at<=?", (at or now(),)).rowcount


def open_draft(c, owner: str) -> sqlite3.Row | None:
    sweep(c)
    return c.execute("SELECT * FROM draft WHERE owner=? AND sent_at IS NULL ORDER BY created_at DESC LIMIT 1",
                     (owner,)).fetchone()


def _new(c, owner: str, days: int) -> sqlite3.Row:
    at = dt.datetime.now(dt.timezone.utc).replace(microsecond=0)
    did = secrets.token_urlsafe(18)
    c.execute("INSERT INTO draft (id, owner, created_at, expires_at) VALUES (?,?,?,?)",
              (did, owner, at.isoformat(), (at + dt.timedelta(days=days)).isoformat()))
    return c.execute("SELECT * FROM draft WHERE id=?", (did,)).fetchone()


def agent_write(c, owner: str, fields: list[dict], values: dict, days: int) -> dict:
    """Draft the fields the agent was given.  Returns what was saved, what
    was refused and why, and the draft (None when nothing was saved, so an
    empty call, or one that only names refused fields, opens nothing)."""
    by_id = {f["id"]: f for f in fields}
    saved, refused, pending = [], [], {}
    for fid, v in (values or {}).items():
        f = by_id.get(str(fid).strip())
        text = "" if v is None else str(v).strip()
        if f is None:
            refused.append((str(fid), "isn't a field on the list"))
        elif f["person_only"]:
            refused.append((f["id"], "is the person's alone to choose, on the page"))
        elif not text:
            continue                                            # an empty value writes nothing
        elif len(text) > 4000:
            refused.append((f["id"], "is longer than a field holds (4,000 characters)"))
        elif f["kind"] == "date" and words.parse(text) is None:
            refused.append((f["id"], "is a date field: give the full date as YYYY-MM-DD, or leave it to the person"))
        elif f["kind"] == "choice" and text not in choices(f):
            refused.append((f["id"], "takes only one of its listed choices"))
        else:
            pending[f["id"]] = text
    d = open_draft(c, owner)
    if d is not None:
        for fid in list(pending):
            r = c.execute("SELECT * FROM field WHERE draft_id=? AND field_id=?", (d["id"], fid)).fetchone()
            if r is not None and (r["confirmed_at"] or r["changed"]):
                del pending[fid]
                refused.append((fid, "has been changed or confirmed by the person on the page, so it is theirs now"))
    if not pending:
        return {"saved": [], "refused": refused, "draft": d, "opened": False}
    opened = d is None
    if opened:
        d = _new(c, owner, days)
    for fid, text in pending.items():
        c.execute("INSERT INTO field (draft_id, field_id, draft_value, value) VALUES (?,?,?,?) "
                  "ON CONFLICT(draft_id, field_id) DO UPDATE SET draft_value=excluded.draft_value, "
                  "value=excluded.value, confirmed_at=NULL, changed=0", (d["id"], fid, text, text))
        saved.append(fid)
    return {"saved": saved, "refused": refused, "draft": d, "opened": opened}


# ---- the person, through the page ------------------------------------------

def get(c, draft_id: str, viewer: str) -> sqlite3.Row:
    sweep(c)
    d = c.execute("SELECT * FROM draft WHERE id=?", (draft_id,)).fetchone()
    if d is None or d["owner"] != viewer:
        raise Gone()
    return d


def rows(c, draft_id: str, fields: list[dict]) -> list[dict]:
    """Every field on the list, in its order, with its state in words: one of
    drafted, changed, confirmed, not answered (screens, section 1)."""
    have = {r["field_id"]: r for r in c.execute("SELECT * FROM field WHERE draft_id=?", (draft_id,))}
    out = []
    for f in fields:
        r = have.get(f["id"])
        value = r["value"] if r else None
        state = ("confirmed" if r is not None and r["confirmed_at"] else
                 "not answered" if not _norm(value) else
                 "changed" if r["changed"] else "drafted")
        out.append({**f, "draft_value": r["draft_value"] if r else None, "value": value,
                    "confirmed_at": r["confirmed_at"] if r else None, "changed": bool(r and r["changed"]),
                    "state": state})
    return out


def _unsent(c, draft_id, viewer):
    d = get(c, draft_id, viewer)
    if d["sent_at"]:
        raise Blocked("This draft has been sent.  A change goes to the office by email, with the reference.")
    return d


def person_set(c, draft_id: str, viewer: str, field: dict, value: str) -> None:
    """The person's value for one field.  It clears that field's confirmation;
    `changed` is whether it now differs from the agent's draft."""
    _unsent(c, draft_id, viewer)
    v = "" if value is None else str(value).strip()
    if field["kind"] == "choice" and v and v not in choices(field):
        raise Blocked(f"{field['label']} takes one of its listed choices.")
    if field["kind"] == "date" and v and words.parse(v) is None:
        raise Blocked(f"{field['label']} takes a full date.")
    r = c.execute("SELECT draft_value FROM field WHERE draft_id=? AND field_id=?", (draft_id, field["id"])).fetchone()
    drafted = r["draft_value"] if r else None
    changed = int(drafted is not None and _norm(v) != _norm(drafted))
    c.execute("INSERT INTO field (draft_id, field_id, value, changed) VALUES (?,?,?,?) "
              "ON CONFLICT(draft_id, field_id) DO UPDATE SET value=excluded.value, confirmed_at=NULL, "
              "changed=excluded.changed", (draft_id, field["id"], v or None, changed))


def confirm(c, draft_id: str, viewer: str, field: dict) -> None:
    """The person says this field is right.  An empty field isn't confirmed:
    it goes as "not answered", which needs nothing from them."""
    _unsent(c, draft_id, viewer)
    r = c.execute("SELECT value FROM field WHERE draft_id=? AND field_id=?", (draft_id, field["id"])).fetchone()
    if r is None or not _norm(r["value"]):
        raise Blocked(f"{field['label']} is empty, and goes as not answered.  There is nothing to confirm.")
    c.execute("UPDATE field SET confirmed_at=? WHERE draft_id=? AND field_id=?", (now(), draft_id, field["id"]))


def put_draft_back(c, draft_id: str, viewer: str, field: dict) -> None:
    _unsent(c, draft_id, viewer)
    c.execute("UPDATE field SET value=draft_value, changed=0, confirmed_at=NULL WHERE draft_id=? AND field_id=? "
              "AND draft_value IS NOT NULL", (draft_id, field["id"]))


def delete(c, draft_id: str, viewer: str) -> None:
    """Delete now, at the person's word.  Nothing was sent."""
    _unsent(c, draft_id, viewer)
    c.execute("DELETE FROM draft WHERE id=?", (draft_id,))


def outstanding(c, draft_id: str, fields: list[dict]) -> list[dict]:
    """What blocks sending: a field that holds a value nobody confirmed.  An
    empty one never blocks."""
    return [r for r in rows(c, draft_id, fields) if r["state"] in ("drafted", "changed")]


def submit(c, draft_id: str, viewer: str, fields: list[dict], asserted: bool) -> str:
    """The person's one assertion.  Returns the reference."""
    _unsent(c, draft_id, viewer)
    if not asserted:
        raise Blocked("Sending needs your assertion, the box above the button.")
    left = outstanding(c, draft_id, fields)
    if left:
        raise Blocked("Not confirmed yet: " + "; ".join(r["label"] for r in left) + ".")
    ref = "IN-" + secrets.token_hex(4).upper()
    c.execute("UPDATE draft SET sent_at=?, reference=? WHERE id=?", (now(), ref, draft_id))
    return ref


def submission(c, draft_id: str, fields: list[dict]) -> list[dict]:
    """What the office receives: every field on the list, with the person's
    value or "not answered", when they confirmed it, and whether it differs
    from the draft.  Never the draft itself, never the conversation."""
    return [{"id": r["id"], "label": r["label"], "value": r["value"] if r["state"] == "confirmed" else None,
             "answered": r["state"] == "confirmed", "confirmed_at": r["confirmed_at"], "changed": r["changed"]}
            for r in rows(c, draft_id, fields)]
