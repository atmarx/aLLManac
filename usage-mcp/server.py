"""The aLLManac usage service.

Spend stats as MCP tools, so "how much have I used?" is a chat question
instead of a second dashboard login.  LibreChat connects here per user and
injects WHO IS ASKING as trusted headers; every tool scopes its answer by
those headers and nothing else.  Identity is never a tool argument — a
prompt can pick the date range, but never whose data comes back.

Trust model, in one breath: this container is reachable only on the compose
network (plus a 127.0.0.1 bind for smoke tests), LibreChat proves itself
with a bearer token, and the database role (usage_ro) can read the ledger
but touch nothing.  The LiteLLM master key never enters this process.
"""

import hmac
import json
import os
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

import asyncpg
import yaml
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.server.dependencies import get_http_headers
from starlette.requests import Request
from starlette.responses import JSONResponse

TOKEN = os.environ.get("USAGE_MCP_TOKEN", "")
# What readers call this place (PLATFORM_NAME, docs/customizing.md).  A
# string a person can read says this, never the project's name.
PLATFORM = (os.environ.get("PLATFORM_NAME") or os.environ.get("DOCS_PRODUCT_NAME")
            or "aLLManac").strip()
# quote(): `just secrets` generates hex, but .env.example ships
# USAGE_DB_PASSWORD as an operator-editable value, and an @ / : or # in it
# silently builds a DSN pointing somewhere else.
DB_URL = os.environ.get("USAGE_DB_URL") or (
    "postgresql://usage_ro:%s@litellm-db:5432/litellm"
    % quote(os.environ.get("USAGE_DB_PASSWORD", ""), safe="")
)
ROSTER_PATH = os.environ.get("USAGE_ROSTER", "/app/roster.yaml")

# mask_error_details: fastmcp defaults it to False, which puts the text of
# any UNHANDLED exception into the tool response — and a tool response is
# read by a student.  Every message in this file that is meant for a human
# is a ToolError, and ToolError is exempt from masking.  So this flag
# costs us nothing and stops `asyncpg.InvalidPasswordError: ... usage_ro`
# and friends from being answers.
mcp = FastMCP("almanac-usage", mask_error_details=True)


# ---- roster: courses, faculty, students --------------------------------------
# One YAML file, mounted read-only, re-read whenever it changes on disk — no
# restart to add a student.  The roster only powers the course-level tools;
# my_usage works with no roster at all.

_roster_cache: dict = {"mtime": None, "data": None, "error": None}
_EMPTY = {"courses": {}, "admins": []}


def _load_roster() -> dict:
    try:
        mtime = os.stat(ROSTER_PATH).st_mtime
    except OSError:
        return _EMPTY
    if _roster_cache["mtime"] == mtime and _roster_cache["data"] is not None:
        return _roster_cache["data"]
    try:
        with open(ROSTER_PATH) as f:
            raw = yaml.safe_load(f) or {}
        courses = {}
        for slug, c in (raw.get("courses") or {}).items():
            c = c or {}
            courses[str(slug).strip().lower()] = {
                "name": str(c.get("name") or slug),
                "faculty": [str(e).strip().lower() for e in (c.get("faculty") or [])],
                "students": [str(e).strip().lower() for e in (c.get("students") or [])],
                # email -> [litellm user_ids], for keys minted under a
                # user_id that is not the email:
                "aliases": {
                    str(k).strip().lower(): [str(a).strip().lower() for a in (v or [])]
                    for k, v in (c.get("aliases") or {}).items()
                },
            }
        data = {
            "courses": courses,
            "admins": [str(e).strip().lower() for e in (raw.get("admins") or [])],
        }
        _roster_cache.update(mtime=mtime, data=data, error=None)
    except Exception as e:  # bad YAML must degrade, not crash the tools
        # The class only — a YAML parse error quotes the offending line,
        # which in a roster is a student's email, and /health is public.
        _roster_cache.update(mtime=mtime, data=_EMPTY, error=type(e).__name__)
    return _roster_cache["data"]


# ---- identity: from the headers LibreChat injects, never from arguments ------

def _ident() -> tuple[str, str]:
    # include= because get_http_headers strips authorization by default
    # (it's meant for forwarding; we're the ones checking it):
    h = get_http_headers(include={"authorization"})
    auth = h.get("authorization", "")
    supplied = auth[7:] if auth[:7].lower() == "bearer " else ""
    if not TOKEN or not hmac.compare_digest(supplied, TOKEN):
        raise ToolError(
            f"This service only answers the {PLATFORM} chat itself "
            "(missing or wrong service token)."
        )
    email = h.get("x-user-email", "").strip().lower()
    role = h.get("x-user-role", "").strip().upper()
    if not email or email.startswith("{{"):
        raise ToolError(
            "I couldn't tell who's asking — these stats only work from inside "
            f"the {PLATFORM} chat, where signing in identifies you."
        )
    return email, role


# ---- the ledger ---------------------------------------------------------------

_pool: asyncpg.Pool | None = None


async def _db() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            DB_URL, min_size=0, max_size=4, command_timeout=30
        )
    return _pool


def _clamp_days(days: int) -> int:
    return max(1, min(int(days), 366))


def _since(days: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")



def _usd(d: float) -> str:
    """Dollars with resolution at the low end, the way upstream's formatCost
    does it: cost intuition is built from ratios, and "$0.00" vs "$0.01"
    can't express a 10x difference.  Below a cent says so; under a dollar
    keeps four places; from a dollar up, the two everyone expects."""
    if d <= 0:
        return "$0.00"
    if d < 0.01:
        return "<$0.01"
    if d < 1:
        return f"${d:.4f}"
    return f"${d:,.2f}"

def _n(v) -> str:
    return f"{int(v or 0):,}"


def _ts(v) -> str:
    return v.strftime("%Y-%m-%d %H:%M UTC") if v else "—"


def _my_ids(email: str) -> list[str]:
    """Every LiteLLM user_id that is this person: the email itself, plus any
    roster aliases (keys minted under a non-email user_id)."""
    ids = {email}
    for c in _load_roster()["courses"].values():
        ids.update(c["aliases"].get(email, []))
    return sorted(ids)


def _course_or_refuse(email: str, role: str, course: str) -> tuple[str, dict]:
    r = _load_roster()
    slug = course.strip().lower()
    if slug not in r["courses"]:
        # By display name too — the registrar's my_courses shows both, and
        # a model passes whichever column it read.
        hits = [s for s, x in r["courses"].items()
                if str(x.get("name", "")).strip().casefold()
                == course.strip().casefold()]
        slug = hits[0] if len(hits) == 1 else slug
    c = r["courses"].get(slug)
    if c is None:
        if _roster_cache["error"]:
            raise ToolError(
                "The course roster can't be read right now, so I can't answer "
                "for any course.  This is a platform fault — tell the "
                "platform admins.")
        # Only the courses this caller could ask about — a student gets the
        # same answer for a real course as for a typo, and never the list.
        mine = sorted(s for s, x in r["courses"].items()
                      if email in r["admins"] or email in x["faculty"])
        raise ToolError(f"No course '{course}' that you teach."
                        + (f"  Yours: {', '.join(mine)}." if mine else ""))
    # The roster decides, not the instance's ADMIN role.  The role used to be
    # required too, and at the front door ADMIN comes only from the realm's
    # `faculty` role — which instructors don't need for anything else, and
    # which hands its holder the flagship's admin panel.  The registrar
    # gates its staff tools on the roster alone for the same reason.
    # `role` stays in the signature so the callers read the same.
    if email not in r["admins"] and email not in c["faculty"]:
        raise ToolError(
            f"Course-wide stats are a faculty view, and the roster doesn't "
            f"list you as teaching staff on {slug}.  Your own numbers are "
            "always available — ask for my_usage."
        )
    return slug, c


# ---- tools ---------------------------------------------------------------------

@mcp.tool
async def my_usage(days: int = 7) -> str:
    """The caller's own usage: requests, tokens, and models — chat
    and API keys combined.  Always and only the caller's numbers.  Data
    notes: the ledger trails live traffic by ~10 seconds, and campus-hosted
    models carry no dollar price, so token counts are the real measure."""
    email, _role = _ident()
    days = _clamp_days(days)
    pool = await _db()
    rows = await pool.fetch(
        """
        SELECT COALESCE(NULLIF(model_group, ''), NULLIF(model, ''), 'unknown') AS m,
               count(*)                                     AS reqs,
               count(*) FILTER (WHERE lower(end_user) = $1) AS chat_reqs,
               COALESCE(sum(prompt_tokens), 0)              AS toks_in,
               COALESCE(sum(completion_tokens), 0)          AS toks_out,
               COALESCE(sum(total_tokens), 0)               AS toks,
               COALESCE(sum(spend), 0)                      AS dollars,
               max("startTime")                             AS last_seen
        FROM "LiteLLM_SpendLogs"
        WHERE "startTime" >= (now() AT TIME ZONE 'utc') - make_interval(days => $2)
          AND (lower(end_user) = $1 OR lower("user") = ANY($3::text[]))
        GROUP BY 1 ORDER BY toks DESC
        """,
        email, days, _my_ids(email),
    )
    head = f"Usage for {email} — last {days} days (since {_since(days)})"
    if not rows:
        return f"{head}\n\nNothing in the ledger for this window."
    reqs = sum(r["reqs"] for r in rows)
    chat = sum(r["chat_reqs"] for r in rows)
    toks_in = sum(r["toks_in"] for r in rows)
    toks_out = sum(r["toks_out"] for r in rows)
    dollars = sum(r["dollars"] for r in rows)
    out = [head, ""]
    out.append(
        f"Total: {_n(reqs)} requests · {_n(toks_in + toks_out)} tokens "
        f"({_n(toks_in)} in / {_n(toks_out)} out)"
    )
    out.append(f"Chat: {_n(chat)} requests · API keys: {_n(reqs - chat)} requests")
    out += ["", "| model | requests | tokens (in / out) | last used |",
            "|---|---:|---|---|"]
    for r in rows:
        out.append(
            f"| {r['m']} | {_n(r['reqs'])} | {_n(r['toks'])} "
            f"({_n(r['toks_in'])} / {_n(r['toks_out'])}) | {_ts(r['last_seen'])} |"
        )
    # Always printed, even when it rounds to $0.00: the meter exists so a
    # student can *tell* what things cost, and the light user is exactly
    # who a hidden line teaches nothing (docs/budgets-and-meters.md).
    out += ["", f"Spend: {_usd(dollars)}"]
    return "\n".join(out)


@mcp.tool
async def course_usage(course: str, days: int = 30) -> str:
    """Course-wide usage — a faculty view: totals, per-student activity, who
    hasn't started yet, and the model mix.  `course` is the course's id or its
    name (my_courses or list_courses when unsure).  Covers this course's chat
    and the API keys minted for it — nothing a student did in another course
    or in the platform's own chat."""
    email, role = _ident()
    days = _clamp_days(days)
    slug, c = _course_or_refuse(email, role, course)
    emails = c["students"]
    tag = json.dumps([f"owner:{slug}"])
    # The COURSE decides which rows count, never the person.  This used to
    # match any row whose end_user or user was one of the course's students —
    # and a student's email rides every chat turn they make anywhere, so an
    # instructor saw that student's other courses and front-door use too, and
    # "not started yet" read a student active in course B as started in A.
    # Every row this course produces carries its team (the service key and
    # every minted key are team-scoped, registrar/planes/gateway.py) and its
    # owner tag; the tag also catches a key minted outside the team.
    where = """
        "startTime" >= (now() AT TIME ZONE 'utc') - make_interval(days => $1)
          AND (team_id = $2 OR request_tags @> $3::jsonb)
    """
    pool = await _db()
    per_ident = await pool.fetch(
        f"""
        SELECT COALESCE(NULLIF(lower(end_user), ''), NULLIF(lower("user"), ''),
                        '(untagged key)')  AS ident,
               count(*)                        AS reqs,
               COALESCE(sum(total_tokens), 0)  AS toks,
               COALESCE(sum(spend), 0)         AS dollars,
               max("startTime")                AS last_seen
        FROM "LiteLLM_SpendLogs" WHERE {where}
        GROUP BY 1
        """,
        days, slug, tag,
    )
    mix = await pool.fetch(
        f"""
        SELECT COALESCE(NULLIF(model_group, ''), NULLIF(model, ''), 'unknown') AS m,
               count(*) AS reqs, COALESCE(sum(total_tokens), 0) AS toks
        FROM "LiteLLM_SpendLogs" WHERE {where}
        GROUP BY 1 ORDER BY toks DESC
        """,
        days, slug, tag,
    )
    # Fold key-user aliases back onto the student's email:
    rev = {a: e for e in emails for a in c["aliases"].get(e, [])}
    folded: dict[str, dict] = {}
    for r in per_ident:
        who = rev.get(r["ident"], r["ident"])
        f = folded.setdefault(
            who, {"reqs": 0, "toks": 0, "dollars": 0.0, "last_seen": None}
        )
        f["reqs"] += r["reqs"]
        f["toks"] += r["toks"]
        f["dollars"] += r["dollars"]
        if f["last_seen"] is None or (r["last_seen"] and r["last_seen"] > f["last_seen"]):
            f["last_seen"] = r["last_seen"]

    head = (f"{c['name']} ({slug}) — last {days} days (since {_since(days)})")
    if not folded:
        started = 0
    else:
        started = sum(1 for e in emails if e in folded)
    out = [head, ""]
    out.append(
        f"Total: {_n(sum(f['reqs'] for f in folded.values()))} requests · "
        f"{_n(sum(f['toks'] for f in folded.values()))} tokens · "
        f"{started} of {len(emails)} students active"
        if folded else "No activity in the ledger for this window."
    )
    if folded:
        out += ["", "| who | requests | tokens | last active |", "|---|---:|---:|---|"]
        for who, f in sorted(folded.items()):  # by who, never by how much — no rankings
            out.append(
                f"| {who} | {_n(f['reqs'])} | {_n(f['toks'])} | {_ts(f['last_seen'])} |"
            )
        dollars = sum(f["dollars"] for f in folded.values())
        out += ["", f"Spend: {_usd(dollars)}"]
    not_started = [e for e in emails if e not in folded]
    if not_started:
        out += ["", f"Not started yet: {', '.join(not_started)}"]
    if mix:
        out += ["", "Model mix: " + " · ".join(
            f"{r['m']} {_n(r['reqs'])} req / {_n(r['toks'])} tok" for r in mix
        )]
    return "\n".join(out)


@mcp.tool
async def list_courses() -> str:
    """Which courses the caller can see usage for, and how.  Start here when
    unsure of a course slug."""
    email, _role = _ident()
    r = _load_roster()
    is_admin = email in r["admins"]
    out = []
    vis = sorted(
        s for s, c in r["courses"].items() if is_admin or email in c["faculty"]
    )
    if vis:
        out.append("Courses you can pull usage for:")
        for s in vis:
            c = r["courses"][s]
            out.append(f"- {s} — {c['name']} ({len(c['students'])} students)")
        out.append("")
        out.append("Ask course_usage with a slug, e.g. course_usage('%s')." % vis[0])
    enrolled = sorted(s for s, c in r["courses"].items() if email in c["students"])
    if enrolled:
        out.append("You're on the roster for: " + ", ".join(enrolled) + ".")
    if not r["courses"]:
        out.append("The roster has no courses yet (usage-mcp/roster.yaml).")
    out.append("Your own numbers are always available — ask for my_usage.")
    return "\n".join(out)


# ---- liveness ------------------------------------------------------------------
# Unauthenticated on purpose (it serves no user data) — this is what
# `just smoke` curls on the 127.0.0.1 bind.  Not-ok DB => 503 so a missing
# usage_ro role reads as a failed smoke, not a silent one.

@mcp.custom_route("/health", methods=["GET"])
async def health(request: Request) -> JSONResponse:
    r = _load_roster()
    body = {"status": "ok", "db": "ok", "courses": len(r["courses"])}
    if _roster_cache["error"]:
        body["roster_error"] = _roster_cache["error"]
    try:
        pool = await _db()
        await pool.fetchval("SELECT 1")
    except Exception as e:
        body.update(status="degraded", db=f"unreachable ({type(e).__name__})")
        return JSONResponse(body, status_code=503)
    return JSONResponse(body)


if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=8080)
