"""Environment requests — registrar/requests.yaml, read/append/mark.

The front office's intake queue (docs/registrar-spec.md, "Phase 2a — the
front office").  Anyone who can sign in may ask for a room; nothing
provisions until an admin approves, which is what makes the wide-open door
safe.  The request is a tool argument rather than an email because a tool
argument is a schema — nobody copies course details out of a message.

It works like a problem report, because it is one kind of ticket: the
person says what they need, an admin reads it and answers — approve,
RETURN with notes (we need more before we can say yes), or REJECT with
notes — and the person reads the answer in my_requests.  A returned request
is answered in the same ticket, not refiled: the thread is the history.

What a request never carries is a budget.  The pool is the platform's
money and the admin sets it at approval; a requester asking for a number
is being asked a question they can't answer (2026-09-22, @xram).

The record carries the ATTESTATION as well as the ask: the exact
front-door text the person was shown, and that they said yes to it, dated.
When "did they know the boundary?" comes back, the answer is in the file.

Like reports and nominations it lives on the state volume and is
gitignored, because it names people.  No network, no credential.
"""

import os
import secrets as pysecrets
import tempfile
from datetime import datetime, timezone

import yaml

from .config import FRONT_DOOR_PATHS, REQUESTS_PATH

KINDS = ("course", "project", "standalone")
# open — waiting on an admin.  returned — waiting on the requester.
# approved / rejected — decided; a rejected ticket is not reopened.
STATUSES = ("open", "returned", "approved", "rejected")

# Model-authored text arriving over HTTP, read back on a terminal.
LIMITS = {"name": 200, "purpose": 2000, "details": 4000, "term": 60,
          "note": 2000, "attested": 4000}
MAX_THREAD = 40
# The door is open to the realm, so one person's pile is bounded.  A real
# need for a sixth open request is a conversation with the operator.
MAX_OPEN_PER_PERSON = 5


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def _clip(s: str | None, n: int) -> str:
    s = (s or "").strip()
    return s if len(s) <= n else s[: n - 1].rstrip() + "…"


def front_door_text() -> str:
    """The boundary question, in this deployment's words.

    `front-door.md` on the state volume if the operator wrote one, else the
    shipped example.  Deployment config, not code: another deployment can
    make it say "research welcome here" and the software does not care.
    """
    for p in FRONT_DOOR_PATHS:
        try:
            with open(p) as f:
                text = f.read().strip()
        except OSError:
            continue
        # Operator notes in HTML comments are for the operator, not the person.
        while "<!--" in text and "-->" in text:
            a = text.index("<!--")
            text = (text[:a] + text[text.index("-->", a) + 3:]).strip()
        if text:
            return text
    return ("This platform is for coursework.  Is this request for "
            "coursework rather than sponsored research?")


def load_requests() -> list[dict]:
    try:
        with open(REQUESTS_PATH) as f:
            raw = yaml.safe_load(f) or {}
    except OSError:
        return []
    return list(raw.get("requests") or [])


def _save(rows: list[dict]) -> None:
    d = os.path.dirname(REQUESTS_PATH) or "."
    fd, tmp = tempfile.mkstemp(dir=d, prefix=".requests.")
    try:
        with os.fdopen(fd, "w") as f:
            f.write("# Environment requests — see docs/registrar-spec.md, "
                    "\"Phase 2a — the front office\".\n"
                    "# Registrar-maintained; gitignored (names people).\n")
            yaml.safe_dump({"requests": rows}, f, sort_keys=False,
                           allow_unicode=True)
        os.chmod(tmp, 0o644)
        os.replace(tmp, REQUESTS_PATH)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def open_count(by: str) -> int:
    return sum(1 for r in load_requests()
               if r.get("by") == by and r.get("status") in ("open", "returned"))


def add_request(*, by: str, kind: str, name: str, purpose: str,
                details: str, instructors: list[str], term: str,
                headcount: int, parent: str | None, slug: str | None,
                attested: str) -> dict:
    rows = load_requests()
    rec = {
        "id": "rq-" + pysecrets.token_hex(3),
        "filed": _now(),
        "by": by,
        "kind": kind,
        "name": _clip(name, LIMITS["name"]),
        "purpose": _clip(purpose, LIMITS["purpose"]),
        "details": _clip(details, LIMITS["details"]),
        "instructors": instructors,
        "term": _clip(term, LIMITS["term"]),
        "headcount": max(0, int(headcount or 0)),
        "parent": parent,
        "slug_wanted": slug,
        # What they were asked, verbatim, and that they said yes.  Never
        # filed without it — the tool refuses to.
        "attestation": {"asked": _clip(attested, LIMITS["attested"]),
                        "answer": "yes", "at": _now()},
        "status": "open",
        # Everything said after filing, both directions, in order.
        "thread": [],
    }
    rows.append(rec)
    _save(rows)
    return rec


def _say(r: dict, by: str, who: str, text: str) -> None:
    thread = r.setdefault("thread", [])
    thread.append({"at": _now(), "by": by, "as": who,
                   "text": _clip(text, LIMITS["note"])})
    del thread[:-MAX_THREAD]


def mark_request(rid: str, status: str, by: str, note: str = "",
                 course: str | None = None, budget: float | None = None) -> dict | None:
    """An admin's answer.  The note goes on the thread, where the requester
    reads it; approval also records the course it became and the pool the
    admin gave it."""
    rows = load_requests()
    for r in rows:
        if r.get("id") == rid:
            r["status"] = status
            r["decided_by"] = by
            r["decided_at"] = _now()
            if note:
                _say(r, by, "admin", note)
            if course:
                r["course"] = course
            if budget is not None:
                r["budget"] = float(budget)
            _save(rows)
            return r
    return None


def reply_request(rid: str, by: str, text: str) -> dict | None:
    """The requester answers.  Reopens a returned ticket, and adds to an
    open one — "oh, and it's two sections" shouldn't need a new request."""
    rows = load_requests()
    for r in rows:
        if r.get("id") == rid:
            _say(r, by, "requester", text)
            r["status"] = "open"
            _save(rows)
            return r
    return None


def reset_rehearsal(domain: str, fixture: list[dict]) -> None:
    """Drop every request filed by an identity on `domain` and put the
    fixture back.  Only the eval runner's personas live there, so this can
    never touch a real person's ticket."""
    rows = [r for r in load_requests()
            if not str(r.get("by", "")).endswith(domain)]
    _save(rows + fixture)

