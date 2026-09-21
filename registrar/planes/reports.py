"""Problem reports — registrar/reports.yaml, read/append/mark.

A report is a person saying "this didn't work."  The reason it is a tool
and not an email is the second half of the record: what they ASKED and what
came BACK.  A complaint alone ("the guide didn't know about X") is a mood;
the same complaint with the question, the answer, and the sources the guide
cited is a retrieval trace, and a retrieval trace is debuggable.  That is
the whole justification for the file — see docs/registrar-spec.md,
"Reports".

Two things this plane does NOT decide, on purpose:

  * WHO the report is about.  The caller passes a slug or nothing; working
    out which course a person means is the verb's job, because it needs the
    roster and this plane may not import a sibling.
  * WHETHER the trace is true.  `asked`/`answered`/`sources` are the
    agent's account of its own turn, not an audit of the retriever — there
    is no retrieval log to read.  Self-reported and imperfect beats the
    instrument we don't have, but the record says `reported_by_agent` so
    nobody later mistakes it for ground truth.

Like the course records it lives on the state volume and is gitignored,
because it names people and quotes what they typed.  No network, no
credential — the nominations plane's sibling.
"""

import os
import secrets as pysecrets
import tempfile
from datetime import datetime, timezone

import yaml

from .config import REPORTS_PATH

STATUSES = ("open", "triaged", "closed")

# How we learned which course the report is about.  Kept on the record
# because a guess and a fact deserve different trust at triage time:
#   header  — the instance rendered X-Course; this one is certain
#   roster  — they're on exactly one course, so there was nothing to guess
#   stated  — they named it and the roster agrees
#   unknown — several courses or none; a human picks
ROUTES = ("header", "roster", "stated", "unknown")

# Bounds.  A tool argument is model-authored text arriving over HTTP, and
# the file it lands in is read back by an operator on a terminal.
LIMITS = {"what": 2000, "asked": 1000, "answered": 4000}
MAX_SOURCES = 20


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def _clip(s: str | None, n: int) -> str:
    s = (s or "").strip()
    return s if len(s) <= n else s[: n - 1].rstrip() + "…"


def load_reports() -> list[dict]:
    try:
        with open(REPORTS_PATH) as f:
            raw = yaml.safe_load(f) or {}
    except OSError:
        return []
    return list(raw.get("reports") or [])


def _save(rows: list[dict]) -> None:
    d = os.path.dirname(REPORTS_PATH) or "."
    fd, tmp = tempfile.mkstemp(dir=d, prefix=".reports.")
    try:
        with os.fdopen(fd, "w") as f:
            f.write("# Problem reports — see docs/registrar-spec.md, \"Reports\".\n"
                    "# Registrar-maintained; gitignored (names people, quotes them).\n")
            yaml.safe_dump({"reports": rows}, f, sort_keys=False, allow_unicode=True)
        os.chmod(tmp, 0o644)
        os.replace(tmp, REPORTS_PATH)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def add_report(*, by: str, role: str, from_room: str, about: str | None,
               route: str, enrolled: list[str], what: str, said: str = "",
               asked: str = "", answered: str = "",
               sources: list[str] | None = None) -> dict:
    """Append one.  Unlike a nomination this never dedupes: two people
    hitting the same wall is the signal, not a duplicate."""
    assert route in ROUTES
    rec = {
        "id": pysecrets.token_hex(3),
        "at": _now(),
        "by": by,
        "role": role or "USER",
        "from_room": from_room,
        "about": about,
        "route": route,
        # Every course the roster puts them on, even when `about` is certain:
        # at triage the operator wants to know where else to look.
        "enrolled": list(enrolled),
        "what": _clip(what, LIMITS["what"]),
        "status": "open",
    }
    if said:
        # They named a course and it is not where this landed.  Kept verbatim:
        # a slug someone typed that routed nowhere is either a typo worth
        # fixing or a course they think they're on and aren't, and both of
        # those are findings.
        rec["said_course"] = _clip(said, 120)
    trace = {
        "asked": _clip(asked, LIMITS["asked"]),
        "answered": _clip(answered, LIMITS["answered"]),
        "sources": [_clip(s, 200) for s in (sources or [])][:MAX_SOURCES],
    }
    if any(trace.values()):
        # The agent's account of its own turn — labelled, never presented
        # as an audit of the retriever (see the module docstring).
        trace["reported_by_agent"] = True
        rec["trace"] = trace
    rows = load_reports()
    rows.append(rec)
    _save(rows)
    return rec


def mark_report(rid: str, status: str, by: str, note: str = "") -> dict | None:
    assert status in STATUSES
    rows = load_reports()
    for r in rows:
        if r["id"] == rid:
            r["status"] = status
            r["decided_by"] = by
            r["decided_at"] = _now()
            if note:
                r["resolution"] = _clip(note, 500)
            _save(rows)
            return r
    return None
