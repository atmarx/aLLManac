"""Every date this service writes is written out in words, with the month
named: "20 July 2026", never 2026-07-20 or 7/20.  A local model copied the
20th as the 2nd from a loose date (docs/staff-portal-agents.md, "The
explainer, against stand-in tools"), so nothing here hands a model digits to
rearrange."""

import datetime as dt
import os
from zoneinfo import ZoneInfo

MONTHS = ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
          "November", "December")
DAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")


def day(d: dt.date) -> str:
    return f"{d.day} {MONTHS[d.month - 1]} {d.year}"


def weekday(d: dt.date) -> str:
    return f"{DAYS[d.weekday()]}, {day(d)}"


def today(tz: str | None = None) -> dt.date:
    """Today where the office is (INTAKE_TZ, an IANA zone; UTC unset)."""
    return dt.datetime.now(ZoneInfo(tz or os.environ.get("INTAKE_TZ") or "UTC")).date()


def parse(s: str) -> dt.date | None:
    """A full date as YYYY-MM-DD, or None.  Nothing looser: resolving "the
    17th of next month" is the agent's, against the today this service says."""
    try:
        return dt.date.fromisoformat((s or "").strip())
    except ValueError:
        return None


def ago(then: dt.date, now: dt.date) -> str:
    n = (now - then).days
    return "today" if n == 0 else f"{n} day{'s' if n != 1 else ''} ago" if n > 0 else f"in {-n} days"
