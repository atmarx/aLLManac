"""Environment requests — registrar/requests.yaml, read/append/mark.

The front office's intake queue (docs/registrar-spec.md, "Phase 2a — the
front office").  Anyone who can sign in may ask for a room; nothing
provisions until an admin approves, which is what makes the wide-open door
safe.  The request is a tool argument rather than a ticket because a tool
argument is a schema — nobody copies course details out of an email.

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
STATUSES = ("open", "approved", "declined")

# Model-authored text arriving over HTTP, read back on a terminal.
LIMITS = {"name": 200, "purpose": 2000, "term": 60, "note": 1000,
          "attested": 4000}
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
               if r.get("by") == by and r.get("status") == "open")


def add_request(*, by: str, kind: str, name: str, purpose: str,
                instructors: list[str], term: str, headcount: int,
                budget: float, parent: str | None, slug: str | None,
                attested: str) -> dict:
    rows = load_requests()
    rec = {
        "id": "rq-" + pysecrets.token_hex(3),
        "filed": _now(),
        "by": by,
        "kind": kind,
        "name": _clip(name, LIMITS["name"]),
        "purpose": _clip(purpose, LIMITS["purpose"]),
        "instructors": instructors,
        "term": _clip(term, LIMITS["term"]),
        "headcount": max(0, int(headcount or 0)),
        "budget_ask": max(0.0, float(budget or 0)),
        "parent": parent,
        "slug_wanted": slug,
        # What they were asked, verbatim, and that they said yes.  Never
        # filed without it — the tool refuses to.
        "attestation": {"asked": _clip(attested, LIMITS["attested"]),
                        "answer": "yes", "at": _now()},
        "status": "open",
    }
    rows.append(rec)
    _save(rows)
    return rec


def mark_request(rid: str, status: str, by: str, note: str = "",
                 course: str | None = None) -> dict | None:
    rows = load_requests()
    for r in rows:
        if r.get("id") == rid:
            r["status"] = status
            r["decided_by"] = by
            r["decided_at"] = _now()
            if note:
                r["note"] = _clip(note, LIMITS["note"])
            if course:
                r["course"] = course
            _save(rows)
            return r
    return None
