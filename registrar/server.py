"""The aLLManac registrar — the tool plane.

Rosters, key custody, and course enrollment served as MCP tools, so
"here's my class list" and "give me my key" are chat sentences instead of
tickets.  LibreChat connects here per user and injects WHO IS ASKING as
trusted headers; each course INSTANCE additionally injects WHICH COURSE
(X-Course) as a literal the registrar itself rendered into that instance's
config.  Identity is never a tool argument — and neither is the course.

Trust model, in one breath: reachable only on the compose network (plus a
127.0.0.1 bind for smoke), LibreChat proves itself with a bearer token,
the course comes from rendered config students can't touch, and the roster
(registrar/courses.yaml) is the authorization for everything an instructor
does.  This file is the TOOL PLANE: it parses, stages, diffs, and reads
the caller's own escrow paths.  Everything that holds a minting credential
lives across the seam in reconcile.py — see docs/registrar-spec.md,
"The mint boundary".
"""

import hmac
import os
import re
import secrets as pysecrets
import time

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.server.dependencies import get_http_headers
from starlette.requests import Request
from starlette.responses import JSONResponse

import reconcile

TOKEN = os.environ.get("REGISTRAR_MCP_TOKEN", "")

mcp = FastMCP("almanac-registrar")


# ---- identity: from the headers LibreChat injects, never from arguments ------

def _ident() -> tuple[str, str, str]:
    """(email, role, course) — all three from trusted headers."""
    h = get_http_headers(include={"authorization"})
    auth = h.get("authorization", "")
    supplied = auth[7:] if auth[:7].lower() == "bearer " else ""
    if not TOKEN or not hmac.compare_digest(supplied, TOKEN):
        raise ToolError(
            "This service only answers the aLLManac chat itself "
            "(missing or wrong service token)."
        )
    email = h.get("x-user-email", "").strip().lower()
    if not email or email.startswith("{{"):
        raise ToolError(
            "I couldn't tell who's asking — these tools only work from inside "
            "a course's chat, where signing in identifies you."
        )
    role = h.get("x-user-role", "").strip().upper()
    course = h.get("x-course", "").strip().lower()
    if not course:
        raise ToolError(
            "This instance didn't say which course it is (no X-Course header) "
            "— the registrar only serves course instances it rendered itself."
        )
    return email, role, course


def _course_or_refuse(slug: str) -> dict:
    c = reconcile.load_courses()["courses"].get(slug)
    if c is None:
        raise ToolError(
            f"No course '{slug}' in registrar/courses.yaml — this instance "
            "predates its course record, which shouldn't happen.  Tell the "
            "platform operator."
        )
    return c


def _staff_or_refuse(email: str, course: dict, slug: str) -> None:
    """Instructors and TAs — the courses.yaml lists ARE the authority (the
    file-backend equivalent of the managed group's manager role)."""
    if email not in course.get("instructors", []) and email not in course.get("tas", []):
        raise ToolError(
            f"Roster operations are for the teaching staff of {slug}.  Your "
            "own key and usage are always available — ask for my_key or "
            "my_usage."
        )


# ---- roster parsing: liberal on purpose ---------------------------------------
# Instructors paste whatever their SIS exports — CSV with headers, TSV,
# newlines, Banner's junk columns.  We extract every email-shaped token and
# REPORT what we ignored; we never demand a format from someone who exports
# one spreadsheet a semester.

_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


def _parse_roster(text: str) -> tuple[list[str], list[str]]:
    """-> (emails in first-seen order, ignored non-empty lines)"""
    seen: dict[str, None] = {}
    ignored: list[str] = []
    for line in text.splitlines():
        found = _EMAIL_RE.findall(line)
        for e in found:
            seen.setdefault(e.lower(), None)
        if not found and line.strip():
            ignored.append(line.strip())
    return list(seen), ignored


# ---- stages: two-phase, always ------------------------------------------------
# A stage is the exact plan roster_apply will execute — nothing more.  It
# lives in memory with a short TTL: the instructor confirms what we PARSED,
# not what they meant to paste.

_STAGE_TTL = 15 * 60
_stages: dict[str, dict] = {}


def _purge_stages() -> None:
    now = time.monotonic()
    for sid in [s for s, v in _stages.items() if now - v["created"] > _STAGE_TTL]:
        del _stages[sid]


# ---- tools: students ----------------------------------------------------------

@mcp.tool
async def my_key() -> str:
    """The caller's own API key for THIS course — for opencode, scripts, and
    laptops (chat never needs it).  The key is per-student-per-course, has
    its own budget fuse, and every token it spends is metered to the caller.
    Treat it like a password; ask rotate_my_key if it ever leaks."""
    email, _role, slug = _ident()
    course = _course_or_refuse(slug)
    if email not in course.get("students", []):
        if email in course.get("instructors", []) or email in course.get("tas", []):
            raise ToolError(
                "Keys are minted per student.  Staff test keys: the operator "
                "can mint one with `just key` (or enroll yourself)."
            )
        raise ToolError(
            f"You're not on the roster for {slug} yet — your instructor "
            "uploads it here in chat, so ask them first."
        )
    rec = await reconcile.escrow_read(slug, email)
    if rec is None:
        raise ToolError(
            "You're on the roster but no key is escrowed yet — the roster "
            "sync that mints it may still be running.  Try again in a "
            "minute, or ask your instructor to re-apply the roster."
        )
    return (
        f"Your {course.get('name', slug)} API key (course: {slug}):\n\n"
        f"    {rec['key']}\n\n"
        f"Budget fuse: ${rec.get('budget', '?')} · minted {rec.get('minted_at', '?')}\n"
        "Point opencode (or any OpenAI-compatible client) at the gateway "
        "with this key — the user guide has the provider block.  This key is "
        "YOURS: it spends your course's pool under your name."
    )


@mcp.tool
async def rotate_my_key() -> str:
    """Revoke the caller's key for THIS course and mint a fresh one —
    remaining budget carries over (rotation is not a budget reset).  Use
    when a key leaked or a laptop walked away."""
    email, _role, slug = _ident()
    course = _course_or_refuse(slug)
    if email not in course.get("students", []):
        raise ToolError(f"No key to rotate — you're not on the {slug} roster.")
    new = await reconcile.rotate_student_key(slug, email)
    return (
        f"Rotated.  Your new {slug} key:\n\n    {new['key']}\n\n"
        f"Remaining fuse carried over: ${new['budget']}.  The old key is "
        "dead at the gateway; update your laptop config."
    )


# ---- tools: teaching staff ----------------------------------------------------

@mcp.tool
async def roster_show() -> str:
    """The current roster for THIS course as the registrar holds it:
    students, staff, and key-custody status.  Teaching staff only."""
    email, _role, slug = _ident()
    course = _course_or_refuse(slug)
    _staff_or_refuse(email, course, slug)
    students = course.get("students", [])
    out = [f"{course.get('name', slug)} ({slug})", ""]
    out.append("Staff: " + ", ".join(course.get("instructors", []) +
                                     course.get("tas", [])))
    if not students:
        out.append("No students on the roster yet — paste one at roster_stage.")
        return "\n".join(out)
    custody = await reconcile.escrow_status(slug, students)
    out += ["", f"{len(students)} students:", "",
            "| student | key | minted |", "|---|---|---|"]
    for s in students:
        c = custody.get(s)
        out.append(
            f"| {s} | {'escrowed' if c else 'MISSING'} | "
            f"{c.get('minted_at', '?') if c else '—'} |"
        )
    if any(custody.get(s) is None for s in students):
        out += ["", "MISSING keys usually mean a partial apply — run "
                    "roster_stage + roster_apply again; it's idempotent."]
    return "\n".join(out)


@mcp.tool
async def roster_stage(roster_text: str) -> str:
    """Stage a roster for THIS course: paste your class list in ANY format
    (CSV export, one email per line, whatever) — the registrar extracts the
    emails, shows you exactly what changes, and changes NOTHING until you
    confirm with roster_apply.  Teaching staff only."""
    email, _role, slug = _ident()
    course = _course_or_refuse(slug)
    _staff_or_refuse(email, course, slug)
    emails, ignored = _parse_roster(roster_text)
    if not emails:
        raise ToolError(
            "I found no email addresses in that paste.  The roster is matched "
            "on sign-in emails — export the email column and paste it here."
        )
    current = set(course.get("students", []))
    staff = set(course.get("instructors", [])) | set(course.get("tas", []))
    desired = [e for e in emails if e not in staff]  # staff aren't students
    adds = [e for e in desired if e not in current]
    keeps = [e for e in desired if e in current]
    removes = sorted(current - set(desired))
    _purge_stages()
    sid = pysecrets.token_hex(4)
    _stages[sid] = {"course": slug, "by": email, "adds": adds,
                    "removes": removes, "created": time.monotonic()}
    out = [f"Staged for {slug} — NOTHING has changed yet.", ""]
    out.append(f"Parsed {len(emails)} email(s); {len(keeps)} already enrolled.")
    if adds:
        out.append(f"ADD ({len(adds)}): " + ", ".join(adds))
    if removes:
        out.append(f"REMOVE ({len(removes)}): " + ", ".join(removes) +
                   "  — their keys will be revoked")
    if not adds and not removes:
        out.append("No changes — the roster already matches.")
    if ignored:
        sample = "; ".join(ignored[:3])
        out.append(f"Ignored {len(ignored)} line(s) with no email "
                   f"(e.g. {sample!r}) — headers and junk columns, usually.")
    if staff & set(emails):
        out.append("Staff addresses in the paste were skipped (staff aren't "
                   "students): " + ", ".join(sorted(staff & set(emails))))
    if adds or removes:
        out += ["", f"If that's exactly right: roster_apply(\"{sid}\") "
                    f"(stage expires in {_STAGE_TTL // 60} minutes)."]
    return "\n".join(out)


@mcp.tool
async def roster_apply(stage_id: str) -> str:
    """Execute a staged roster change — and only that change: enroll the
    adds (login access + key minted + escrowed), un-enroll the removes
    (key revoked).  Teaching staff only; stage first with roster_stage."""
    email, _role, slug = _ident()
    course = _course_or_refuse(slug)
    _staff_or_refuse(email, course, slug)
    _purge_stages()
    st = _stages.get(stage_id.strip())
    if st is None or st["course"] != slug:
        raise ToolError(
            "That stage doesn't exist (expired, already applied, or from a "
            "different course).  roster_stage again — staging is cheap."
        )
    del _stages[stage_id.strip()]
    results = await reconcile.apply_roster(slug, st["adds"], st["removes"])
    ok = sum(1 for r in results if r["ok"])
    out = [f"Applied to {slug}: {ok}/{len(results)} operations clean.", ""]
    for r in results:
        mark = "ok " if r["ok"] else "FAIL"
        out.append(f"  {mark}  {r['op']:6} {r['who']}  {r.get('note', '')}".rstrip())
    if ok < len(results):
        out += ["", "Failures are safe to retry — stage the same roster "
                    "again; every operation is idempotent."]
    out += ["", "Students log in at this course's address; keys are ready "
                "the moment they ask my_key."]
    return "\n".join(out)


@mcp.tool
async def course_keys() -> str:
    """Key custody for THIS course — who's minted, who's missing, when.
    Shows status only, never the keys themselves: nobody but the owner
    ever retrieves a key.  Spend questions belong to course_usage."""
    email, _role, slug = _ident()
    course = _course_or_refuse(slug)
    _staff_or_refuse(email, course, slug)
    students = course.get("students", [])
    if not students:
        return f"No students on the {slug} roster yet."
    custody = await reconcile.escrow_status(slug, students)
    minted = [s for s in students if custody.get(s)]
    missing = [s for s in students if not custody.get(s)]
    out = [f"Key custody — {slug}: {len(minted)}/{len(students)} escrowed"]
    if missing:
        out += ["", "Missing: " + ", ".join(missing),
                "(re-apply the roster to mint stragglers — it's idempotent)"]
    return "\n".join(out)


# ---- liveness ------------------------------------------------------------------
# Unauthenticated on purpose (serves no user data) — what `just smoke` curls.
# 200 even before bao-init so a fresh box's first deploy isn't "down"; the
# body says what's actually wired.

@mcp.custom_route("/health", methods=["GET"])
async def health(request: Request) -> JSONResponse:
    data = reconcile.load_courses()
    return JSONResponse({
        "status": "ok",
        "courses": len(data["courses"]),
        "bao": "configured" if reconcile.bao_configured() else "not configured (run: just bao-init)",
    })


if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=8080)
