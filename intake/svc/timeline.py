"""The dated table of obligations, answered by a tool so no model does date
math (docs/staff-portal.md, "A timeline tool, not a model doing date
math").

The table is research compliance's file, outside this repository
(INTAKE_OBLIGATIONS).  Each row carries one or two scheduled dates (counted
from the policy's issuance and from its release, where the two differ), a
status as of the last check, and that check's date.  The tool:
  * always says what today is, first, so a loose date ("the 17th of next
    month") can be resolved by the agent and said back;
  * writes every date in words, with the month named;
  * keeps what was scheduled apart from what had happened at the last check,
    and says how old that check is;
  * marks a row whose scheduled date has passed since the check while its
    status still says pending: the table is behind, and the row is
    unconfirmed, not met and not missed.
It answers the rows as written and draws no conclusion from them.
"""

import datetime as dt
import re

import yaml

from . import words

STATUS = {"published": "published", "pending": "pending", "overdue_unconfirmed": "past its date, not confirmed either way",
          "never_done": "never done", "superseded": "superseded"}


def load(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        text = f.read()
    rows = yaml.safe_load(text) or []
    # The file's own header carries its review date as a comment line
    # ("#   review_by: 2026-11-24"); read it from there, not from memory.
    m = re.search(r"^#\s*review_by:\s*(\d{4}-\d{2}-\d{2})", text, re.M)
    return {"rows": rows, "review_by": dt.date.fromisoformat(m.group(1)) if m else None}


def _d(v) -> dt.date | None:
    if v is None or v == "":
        return None
    return v if isinstance(v, dt.date) else dt.date.fromisoformat(str(v))


def _when(r) -> list[tuple[str, dt.date]]:
    a, b = _d(r.get("date_from_issuance")), _d(r.get("date_from_release"))
    if a and b and a != b:
        return [("counting from issuance", a), ("counting from release", b)]
    return [("", a or b)] if (a or b) else []


def answer(table: dict, asked: dt.date | None, today: dt.date) -> str:
    rows = table["rows"]
    checks = sorted({_d(r.get("as_of")) for r in rows if r.get("as_of")})
    out = [f"Today is {words.weekday(today)}."]
    if asked and asked != today:
        out.append(f"You asked about {words.weekday(asked)}.")
    on = asked or today
    if checks:
        last = checks[-1]
        line = f"The table was last checked on {words.day(last)}, {words.ago(last, today)}."
        if table.get("review_by"):
            rb = table["review_by"]
            line += (f"  It is past its review date, {words.day(rb)}, and may be behind." if rb < today else
                     f"  It is due for review by {words.day(rb)}.")
        out.append(line)
    out.append("What is scheduled is not what has happened.  Each row says both, and the status is as of the "
               "last check.")
    behind = 0
    for r in rows:
        when = _when(r)
        out += ["", f"{r.get('id', '')} · {r.get('obligation', '').strip()}"]
        if r.get("who"):
            out.append(f"  Who: {r['who']}")
        if r.get("clock"):
            out.append(f"  Clock: {r['clock']}")
        if when:
            out.append("  Scheduled: " + ", or ".join(f"{words.day(d)}{' ' + how if how else ''}" for how, d in when))
            out.append(f"  On {words.day(on)}: " + _relation([d for _, d in when], on))
        else:
            out.append("  Scheduled: no date has been set.")
        if r.get("earliest_possible"):
            out.append(f"  No earlier than {words.day(_d(r['earliest_possible']))}, a floor and not a scheduled date.")
        status, as_of = r.get("status", ""), _d(r.get("as_of"))
        said = STATUS.get(status, status)
        if status == "pending" and when and min(d for _, d in when) < today:
            said = "past its date since the last check, not confirmed either way: the table is behind on this row"
            behind += 1
        out.append(f"  At the last check{', on ' + words.day(as_of) if as_of else ''}: {said}.")
        if r.get("status_note"):
            out.append(f"  Note: {_dates_in_words(str(r['status_note']).strip())}")
        if r.get("source"):
            out.append(f"  Source: {r['source']}")
    if behind:
        out += ["", f"{behind} row{'s' if behind != 1 else ''} passed {'their' if behind != 1 else 'its'} date "
                    "after the last check.  Ask the office what has happened since."]
    return "\n".join(out)


def _relation(dates: list[dt.date], on: dt.date) -> str:
    """Where `on` falls against the scheduled dates.  Schedule only: whether
    it happened is the status line's to say."""
    if any(d == on for d in dates):
        return "that is a scheduled date." if len(dates) == 1 else "that is one count's scheduled date."
    past = sum(d < on for d in dates)
    if past == len(dates):
        return "the scheduled date has passed." if len(dates) == 1 else "both counts' dates have passed."
    if past == 0:
        return "the scheduled date is still ahead." if len(dates) == 1 else "both counts' dates are still ahead."
    return "one count's date has passed and the other's has not."


def _dates_in_words(s: str) -> str:
    """A note written with an ISO date gets it in words too."""
    return re.sub(r"\b(\d{4}-\d{2}-\d{2})\b", lambda m: words.day(dt.date.fromisoformat(m.group(1))), s)
