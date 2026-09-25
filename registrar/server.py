"""The aLLManac registrar — the tool plane.

Rosters, key custody, and course enrollment served as MCP tools, so
"here's my class list" and "give me my key" are chat sentences instead of
tickets.  LibreChat connects here per user and injects WHO IS ASKING as
trusted headers; each course INSTANCE additionally injects WHICH COURSE
(X-Course) as a literal the registrar itself rendered into that instance's
config.  Identity is never a tool argument.  The course is one only at the
front door, where there is no header to take it from — and there it names a
course the roster must already say the caller teaches (_staff_scope).

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
from fastmcp.server.middleware import Middleware
from starlette.requests import Request
from starlette.responses import JSONResponse
import yaml

import reconcile

TOKEN = os.environ.get("REGISTRAR_MCP_TOKEN", "")

# mask_error_details: fastmcp defaults it to False, which puts the text of
# any UNHANDLED exception into the tool response — and a tool response is
# read by a student.  Every message in this file that is meant for a human
# is a ToolError, and ToolError is exempt from masking.  So this flag
# costs us nothing and stops `asyncpg.InvalidPasswordError: ... usage_ro`
# and friends from being answers.
mcp = FastMCP("almanac-registrar", mask_error_details=True)


class _FailureWords(Middleware):
    """Failures with a normal cause get words instead of a bare "Error
    calling tool" that the guide then explains by guessing.

    A sealed vault — every reboot seals it until the unseal unit runs.
    Wording by @piper (2026-09-23); the student is the likeliest reader.
    And an unreadable ticket file (requests / reports / nominations .yaml),
    which courses.yaml already gets words for in _courses_or_refuse."""

    async def on_call_tool(self, context, call_next):
        try:
            return await call_next(context)
        except Exception as e:
            # By the time it reaches here fastmcp has already masked it into
            # a ToolError("Error calling tool …"); what we match is the cause.
            cause = e if not isinstance(e, ToolError) else e.__cause__
            if isinstance(cause, reconcile.CourseClosed):
                # Already written for the person asking (open_or_raise):
                # which state, since when, and until when they can export.
                raise ToolError(str(cause)) from None
            if isinstance(cause, yaml.YAMLError):
                raise ToolError(
                    "One of the registrar's record files can't be read right "
                    "now, so I can't answer that safely.  This is a platform "
                    "fault, not something you did — tell the platform "
                    "admins.") from None
            if not isinstance(cause, reconcile.EscrowUnavailable):
                raise
            raise ToolError(
                "Keys can't be handed out for the moment.  The part of the "
                "platform that holds them is locked, which usually means "
                "the server has just restarted.  Your key is fine and "
                "nothing is lost.  Try again in a few minutes; if it still "
                "says this in an hour, tell your instructor (instructors: "
                "tell the platform admins).") from None


mcp.add_middleware(_FailureWords())


# ---- rehearsal: evaluation identities never write ------------------------------
# The eval runner (scripts/run_evals.py) drives the guides as personas whose
# addresses sit on the reserved .invalid TLD — the same trick that keeps the
# guides' own service account from ever signing in.  No IdP can assert such
# an address and self-registration is off, so the only way to BE one is a
# JWT minted with the flagship's own secret, on the box.
#
# Those callers get every check this file makes — the roster, the staff
# gate, the admin gate, the "no instructor left" refusal — because those are
# what the evals test.  What they never get is the side effect.  The case
# that matters most is "never stage and apply in one turn," and a model that
# fails it would otherwise apply for real.  So at the moment of each write,
# a rehearsal says what would have happened and changes nothing — no roster,
# no key, no course, no ticket, and no Teams post announcing a test.
REHEARSAL_DOMAIN = reconcile.REHEARSAL_DOMAIN


def _rehearse(email: str, would: str) -> str | None:
    if not email.endswith(REHEARSAL_DOMAIN):
        return None
    return (f"REHEARSAL — {email} is an evaluation identity, so nothing was "
            f"executed.  For a real person this call would have {would}.")


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


def _ident_open() -> tuple[str, str, str]:
    """(email, role, course-or-empty) — for the tools that also serve the
    vestibule.

    `_ident()` refuses without an X-Course header, and that refusal is why
    wiring this service into the flagship costs nothing for the tools that
    are about the room you're standing in — my_key, rotate_my_key,
    nominate_agent: the vestibule renders no X-Course, so they go on
    refusing there without a line of policy.  A tool that opts out of that
    has to say so in its own name, which is what this function is for.  The
    test for opting out (docs/design-walls.md, "the front door"): is the
    header CHOOSING which course, or DECIDING who may act?  Only the first
    can move to an argument.

    The token check and the who-is-asking check are unchanged; only the
    course becomes optional, and the caller must then work out the course
    from the roster instead — reconcile.file_report for routing a complaint,
    _staff_scope for enrollment, my_courses for "where am I?".
    """
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
            "I couldn't tell who's asking — this only works from inside the "
            "aLLManac chat, where signing in identifies you."
        )
    return email, h.get("x-user-role", "").strip().upper(), \
        h.get("x-course", "").strip().lower()


def _courses_or_refuse() -> dict:
    """EVERY read of courses.yaml from the tool plane goes through here.

    Three tools used to call load_courses() naked, and `nominations` was one
    of them — reachable by any student in any course.  A CoursesError carries
    the container path and PyYAML's snippet of the offending line, out of a
    file whose entire content is student emails.
    """
    try:
        return reconcile.load_courses()
    except reconcile.CoursesError as e:
        # Distinct from "no such course" on purpose: one is a course that was
        # never created, the other is every course being invisible at once.
        # Telling an instructor the first when it's the second sends them
        # re-uploading a roster against a file we can't read.
        raise ToolError(
            "The registrar can't read its course records right now, so I "
            "can't safely change anything.  This is a platform fault, not "
            "something you did — tell the operator."
        ) from e


def _course_or_refuse(slug: str) -> dict:
    courses = _courses_or_refuse()
    c = courses["courses"].get(slug)
    if c is None:
        raise ToolError(
            f"No course '{slug}' in registrar/courses.yaml — this instance "
            "predates its course record, which shouldn't happen.  Tell the "
            "platform operator."
        )
    return c


def _staff_or_refuse(email: str, course: dict, slug: str,
                     front_door: bool = False) -> None:
    """Instructors and TAs — the courses.yaml lists ARE the authority (the
    file-backend equivalent of the managed group's manager role)."""
    if email not in course.get("instructors", []) and email not in course.get("tas", []):
        # my_key refuses at the front door, so don't send anyone to it there.
        raise ToolError(
            f"Enrollment for {slug} is managed by its teaching staff, and "
            "the roster doesn't list you as one.  my_courses shows what "
            "you're on." if front_door else
            f"Roster operations are for the teaching staff of {slug}.  Your "
            "own key and usage are always available — ask for my_key or "
            "my_usage."
        )


def _staff_scope(course_arg: str = "") -> tuple[str, str, dict]:
    """(email, slug, course) for a teaching-staff tool, from either room.

    In a course instance the header decides, as it always has, and a named
    course that disagrees is refused rather than obeyed: the header is
    config the registrar rendered, the argument is a model repeating what
    somebody typed.  At the front door there is no header, so the course
    has to be named — or, when the caller teaches exactly one, it is that
    one (the same "one course is an answer" rule report routing uses).

    Either way the authority is the line after this: `_staff_or_refuse`
    against the roster.  The header only ever chose WHICH course; it never
    decided who may change it.  That is why taking the course as an
    argument here opens nothing — a student at the front door who names a
    course gets the same refusal a student in that course's chat does.
    """
    email, _role, header = _ident_open()
    courses = _courses_or_refuse()["courses"]
    named = _course_slug(course_arg, courses)
    if header:
        if named and named != header:
            raise ToolError(
                f"This chat belongs to {header}.  To manage {named}, use its "
                "own chat or the front door."
            )
        slug = header
        course = _course_or_refuse(slug)
        _staff_or_refuse(email, course, slug)
        return email, slug, course
    teaching = sorted(s for s, c in courses.items() if _is_staff(email, c))
    if not named:
        if len(teaching) == 1:
            named = teaching[0]
        elif teaching:
            raise ToolError(
                "You teach more than one course — which one?  "
                + ", ".join(teaching) + "."
            )
        else:
            raise ToolError(
                "The roster doesn't list you as teaching staff on any course, "
                "so there's no enrollment for you to manage from here.  "
                "my_courses shows what you're on; who teaches a course is set "
                "by the platform operator."
            )
    course = courses.get(named)
    if course is None:
        mine = ("  The courses you teach: " + ", ".join(teaching) + ".") \
            if teaching else ""
        raise ToolError(f"There's no course called '{named}'.{mine}")
    _staff_or_refuse(email, course, named, front_door=True)
    return email, named, course


def _course_slug(arg: str, courses: dict) -> str:
    """A course as a person (or a model) names it -> its slug.

    The slug if it is one; else the course whose display name matches,
    ignoring case.  my_courses shows both, and a model will pass whichever
    column it read — the eval run caught the Instructor Guide passing the
    name first every time (2026-09-23, @geordi).  Only ever chooses WHICH
    course: authority is still _staff_or_refuse, so resolving a name opens
    nothing a slug wouldn't.  A stable `address:` resolves to its current
    term.  No match, or two courses sharing a name,
    comes back as-is and fails as an unknown slug downstream."""
    named = (arg or "").strip()
    if not named or named.lower() in courses:
        return named.lower()
    # A stable address names whichever term claims it today — the same
    # answer the edge's redirect gives, so "engr301" means one course here
    # and in the browser.
    if (term := reconcile.address_map({"courses": courses}).get(named.lower())):
        return term
    hits = [s for s, c in courses.items()
            if str(c.get("name", "")).strip().casefold() == named.casefold()]
    return hits[0] if len(hits) == 1 else named.lower()


def _is_staff(email: str, course: dict) -> bool:
    return (email in course.get("instructors", [])
            or email in course.get("tas", []))


def _on_roster(email: str, course: dict) -> bool:
    """Anyone the roster names — student, instructor or TA.

    The roster is not a hierarchy.  It decides who may CHANGE the roster
    (_staff_or_refuse) and who may hold a key; those are different
    questions, and conflating them is what made staff unable to get one.
    """
    return email in course.get("students", []) or _is_staff(email, course)


def _admin_or_refuse(email: str) -> None:
    """The platform's `admins:` list — NOT the instance's ADMIN role.  A
    course instance makes its own staff ADMIN, and that is authority over
    one house; the fleet view is every house at once, so it answers only
    to the list the operator keeps in courses.yaml."""
    if email not in _courses_or_refuse()["admins"]:
        raise ToolError(
            "That's the operator's desk — it answers to the `admins:` list in "
            "registrar/courses.yaml.  Course staff: roster_show and "
            "course_usage cover your own course, and anyone can ask for a "
            "new one with course_request."
        )


def _is_dev(email: str, courses: dict) -> bool:
    """May this person work the report queue?

    A separate list from `admins:` on purpose, and the line is not
    seniority — it is **who chose to be seen**.  A report is something a
    person sat down and sent you; `fleet_access` is every student who
    chose nothing.  Those two should not share a gate merely because both
    are platform-wide, or handing someone the bug queue hands them every
    roster on the box.  Admins pass implicitly: they already see more.
    """
    return email in courses["devs"] or email in courses["admins"]


def _dev_or_refuse(email: str) -> dict:
    courses = _courses_or_refuse()
    if not _is_dev(email, courses):
        raise ToolError(
            "Working the report queue is for the platform team (the `devs:` "
            "or `admins:` list in registrar/courses.yaml).  Teaching staff "
            "see their own course's reports from inside that course."
        )
    return courses


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
    laptops (chat never needs it).  Works for anyone the roster names,
    students and teaching staff alike.  The key is per-person-per-course,
    has its own budget fuse, and every token it spends is metered to the
    caller.  Treat it like a password; ask rotate_my_key if it ever leaks."""
    email, _role, slug = _ident()
    course = _course_or_refuse(slug)
    if not _on_roster(email, course):
        raise ToolError(
            f"You're not on the roster for {slug} yet — your instructor "
            "uploads it here in chat, so ask them first."
        )
    if (r := _rehearse(email, "handed back your key for this course")):
        return r
    if reconcile.course_state(course) != "open":
        # The escrow still holds a key here during the export window, and
        # handing it over would give someone a credential the gateway
        # already refuses — the "my key stopped working" loop, started by us.
        ends = reconcile.window_ends(course)
        until = (f"  Your conversations are still here until {ends.isoformat()} "
                 "— export anything you want to keep before then (each "
                 "conversation's menu has Export)." if ends else "")
        raise ToolError(
            f"{course.get('name', slug)} closed on {course['closed']}, and its "
            f"keys stopped working then — the term's budget is shut.{until}")
    rec = await reconcile.escrow_read(slug, email)
    if rec is None and _is_staff(email, course):
        # Staff mint on first ask.  This used to refuse and point at `just
        # key` — a shell command on the box, which is useless advice to the
        # one person in the room who IS their own admin.  The refusal was a
        # leftover from keys being a side effect of student provisioning,
        # not a decision: mint_key is idempotent by escrow, mints into the
        # course team, and is gated by the pool like every other key, so
        # there was never anything for the operator to adjudicate.
        #
        # It bites hardest where seniority and teaching come apart — a
        # cohort where everyone is learning has no real TAs, only senior
        # people, and `tas:` is exactly where that instinct files them.
        try:
            rec = await reconcile.mint_key(slug, email)
        except reconcile.PoolExhausted:
            raise ToolError(
                f"There's nothing left in the {slug} pool to put behind a "
                "key, so minting one would hand you a credential that's "
                "dead on arrival.  `course_usage` shows where the term's "
                "budget went."
            ) from None
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
        + (f"Gateway: https://{reconcile.GATEWAY_HOST}/v1\n"
           if reconcile.GATEWAY_HOST else "")
        + "Point opencode (or any OpenAI-compatible client) at the gateway "
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
    if not _on_roster(email, course):
        raise ToolError(f"No key to rotate — you're not on the {slug} roster.")
    try:
        if (r := _rehearse(email, "revoked your key and minted a fresh one")):
            return r
        new = await reconcile.rotate_student_key(slug, email)
    except reconcile.MeterUnreadable:
        # Refusing leaves the caller exactly as they were, still holding a
        # working key — the same principle as the gate below.
        raise ToolError(
            "I can't read your key's meter right now, so I won't rotate: "
            "rotation carries your remaining budget forward, and guessing "
            "would hand you a full fuse you haven't got.  Your current key "
            "still works.  Try again in a minute."
        ) from None
    except reconcile.PoolExhausted:
        # Rotation carries the remainder forward; it has never been a refill.
        # Say which budget is empty, because "your key stopped working" reads
        # as a broken key and sends people rotating in circles.
        raise ToolError(
            f"Rotating won't help — there's nothing left to carry over for "
            f"{slug}.  A new key would be dead on arrival, so I won't mint "
            "one.  Ask your instructor about more budget; `my_usage` shows "
            "where it went."
        ) from None
    return (
        f"Rotated.  Your new {slug} key:\n\n    {new['key']}\n\n"
        f"Remaining fuse carried over: ${new['budget']}.  The old key is "
        "dead at the gateway; update your laptop config."
    )


# ---- tools: anyone ------------------------------------------------------------

@mcp.tool
async def my_courses() -> str:
    """Which courses the caller is on — as student, TA or instructor — and
    where each one's chat is.  Works from any room, including the front
    door, and only ever answers about the person asking.  Not being on any
    course is a normal answer: the front door and its guides are open to
    everyone who can sign in."""
    email, _role, _here = _ident_open()
    courses = _courses_or_refuse()["courses"]
    rows = []
    for slug in reconcile.courses_for(email):
        c = courses[slug]
        role = ("instructor" if email in c.get("instructors", []) else
                "TA" if email in c.get("tas", []) else "student")
        state = reconcile.course_state(c)
        if state == "archived":
            where = f"archived {c['archived']} — no longer online"
        else:
            where = f"https://{slug}.{reconcile.ALMANAC_DOMAIN}"
            if state == "closed":
                ends = reconcile.window_ends(c)
                where += (f" (closed {c['closed']}; export your conversations by "
                          f"{ends.isoformat()})" if ends else f" (closed {c['closed']})")
        rows.append(f"| {c.get('name', slug)} | {slug} | {role} | {where} |")
    if not rows:
        return (
            f"I don't see {email} on any course's roster.  If you expected "
            "to be, check with your instructor — they add people, and it "
            "takes effect the next time you sign in.  Everything at the "
            "front door is yours either way."
        )
    return "\n".join([f"Courses {email} is on:", "",
                      "| course | id | you are | chat |", "|---|---|---|---|",
                      *rows, "",
                      "The course tools take either the name or the id."])


# ---- tools: teaching staff ----------------------------------------------------
# Every one of these answers in a course's own chat AND at the front door.
# `course` is ignored-unless-it-disagrees in a course (the header wins) and
# names the course at the front door; `_staff_scope` has the reasoning.
# "Enrollment" is the word faculty use for this, and it is the right one for
# the conversation even though it is not the registrar's enrollment: being
# on a roster here opens a door and mints a key, it does not put anyone in
# a class.

@mcp.tool
async def roster_show(course: str = "") -> str:
    """The current roster for a course you teach, as the registrar holds it:
    students, staff, and key-custody status.  Teaching staff only.  In a
    course's own chat leave `course` empty; at the front door name the
    course (my_courses lists them)."""
    email, slug, c = _staff_scope(course)
    students = c.get("students", [])
    out = [f"{c.get('name', slug)} ({slug})", ""]
    out.append("Staff: " + ", ".join(c.get("instructors", []) +
                                     c.get("tas", [])))
    if not students:
        out.append("No students on the roster yet — enroll some, or paste a "
                   "class list at roster_stage.")
        return "\n".join(out)
    custody = await reconcile.escrow_status(slug, students)
    out += ["", f"{len(students)} students:", "",
            "| student | key | minted |", "|---|---|---|"]
    for st in students:
        k = custody.get(st)
        out.append(
            f"| {st} | {'escrowed' if k else 'MISSING'} | "
            f"{k.get('minted_at', '?') if k else '—'} |"
        )
    if any(custody.get(st) is None for st in students):
        out += ["", "MISSING keys usually mean a partial apply — run "
                    "roster_stage + roster_apply again; it's idempotent."]
    return "\n".join(out)


def _stage(email: str, slug: str, course: dict, emails: list[str],
           mode: str, ignored: list[str] | None = None) -> str:
    """Build a stage and describe it.  NOTHING changes here — the stage is
    the exact plan roster_apply will execute, and the description is what
    the person says yes to.

    mode: "replace" (the paste IS the class list — anyone missing from it
    is removed), "add", or "remove".  Staff addresses are never students,
    whichever way they arrive.
    """
    current = set(course.get("students", []))
    staff = set(course.get("instructors", [])) | set(course.get("tas", []))
    wanted = [e for e in emails if e not in staff]
    if mode == "replace":
        adds = [e for e in wanted if e not in current]
        removes = sorted(current - set(wanted))
    elif mode == "add":
        adds, removes = [e for e in wanted if e not in current], []
    else:
        adds, removes = [], sorted(e for e in wanted if e in current)
    already = [e for e in wanted if e in current] if mode != "remove" else \
        [e for e in wanted if e not in current]
    _purge_stages()
    sid = pysecrets.token_hex(4)
    _stages[sid] = {"course": slug, "by": email, "adds": adds,
                    "removes": removes, "created": time.monotonic()}
    out = [f"Staged for {slug} — NOTHING has changed yet.", ""]
    if mode == "replace":
        out.append(f"Parsed {len(emails)} email(s); {len(already)} already "
                   "enrolled.")
    elif already:
        out.append(("Already enrolled: " if mode == "add" else
                    "Not enrolled, so nothing to remove: ") + ", ".join(already))
    if adds:
        out.append(f"ADD ({len(adds)}): " + ", ".join(adds) +
                   "  — each gets access to this course's chat and a key")
    if removes:
        out.append(f"REMOVE ({len(removes)}): " + ", ".join(removes) +
                   "  — access closed and their keys revoked")
    if not adds and not removes:
        out.append("No changes — the roster already matches.")
    if ignored:
        sample = "; ".join(ignored[:3])
        out.append(f"Ignored {len(ignored)} line(s) with no email "
                   f"(e.g. {sample!r}) — headers and junk columns, usually.")
    if staff & set(emails):
        out.append("Staff addresses were skipped (staff aren't students, and "
                   "who teaches a course is the operator's to change): "
                   + ", ".join(sorted(staff & set(emails))))
    if adds or removes:
        out += ["", f"If that's exactly right: roster_apply(\"{sid}\") "
                    f"(stage expires in {_STAGE_TTL // 60} minutes)."]
    return "\n".join(out)


def _emails_or_refuse(text: str) -> tuple[list[str], list[str]]:
    emails, ignored = _parse_roster(text)
    if not emails:
        raise ToolError(
            "I found no email addresses in that.  Access is matched on "
            "sign-in emails, so I need the email, not a name."
        )
    return emails, ignored


@mcp.tool
async def enroll(emails: str, course: str = "") -> str:
    """Stage giving one or more people access to a course you teach — they
    can sign in to its chat and fetch their own API key.  Adds only; nobody
    already enrolled is touched.  Changes NOTHING until roster_apply.
    `emails`: one or more addresses, any separator.  In a course's own chat
    leave `course` empty; at the front door name it.  Teaching staff only."""
    email, slug, c = _staff_scope(course)
    emails_, ignored = _emails_or_refuse(emails)
    return _stage(email, slug, c, emails_, "add", ignored)


@mcp.tool
async def unenroll(emails: str, course: str = "") -> str:
    """Stage removing one or more people from a course you teach — their
    access closes and their API key is revoked.  Removes only.  Changes
    NOTHING until roster_apply.  Teaching staff only."""
    email, slug, c = _staff_scope(course)
    emails_, ignored = _emails_or_refuse(emails)
    return _stage(email, slug, c, emails_, "remove", ignored)


@mcp.tool
async def roster_stage(roster_text: str, course: str = "") -> str:
    """Stage a WHOLE class list for a course you teach: paste it in any
    format (CSV export, one email per line, whatever) and the registrar
    extracts the emails.  The paste becomes the roster — anyone enrolled
    who is missing from it is REMOVED.  To add or remove a few people, use
    enroll / unenroll instead.  Changes NOTHING until roster_apply.
    Teaching staff only."""
    email, slug, c = _staff_scope(course)
    emails_, ignored = _emails_or_refuse(roster_text)
    return _stage(email, slug, c, emails_, "replace", ignored)


@mcp.tool
async def roster_apply(stage_id: str) -> str:
    """Execute a staged enrollment change — and only that change: enroll
    the adds (sign-in access + key minted + escrowed), un-enroll the
    removes (key revoked).  Only after the person has read the stage and
    said yes to it.  Teaching staff only."""
    _purge_stages()
    st = _stages.get(stage_id.strip())
    if st is None:
        _ident_open()     # the token check still comes before any answer
        raise ToolError(
            "That stage doesn't exist (expired or already applied).  Stage "
            "it again — staging is cheap."
        )
    # The stage names its own course, so apply needs no `course` argument
    # at the front door — and _staff_scope re-checks that the person
    # applying teaches it, whoever staged it.  In a course's chat, a stage
    # from another course is refused there as a disagreeing course.
    email, slug, _c = _staff_scope(st["course"])
    if (r := _rehearse(email, f"applied the stage to {slug}: added {len(st['adds'])}, removed {len(st['removes'])}")):
        return r
    results = await reconcile.apply_roster(slug, st["adds"], st["removes"])
    # Only now: a sealed vault or a Keycloak outage raises out of the line
    # above, and the instructor's stage should still be there to retry.
    _stages.pop(stage_id.strip(), None)
    ok = sum(1 for r in results if r["ok"])
    out = [f"Applied to {slug}: {ok}/{len(results)} operations clean.", ""]
    for r in results:
        mark = "ok " if r["ok"] else "FAIL"
        out.append(f"  {mark}  {r['op']:6} {r['who']}  {r.get('note', '')}".rstrip())
    if ok < len(results):
        out += ["", "Failures are safe to retry — stage the same change "
                    "again; every operation is idempotent."]
    out += ["", f"Students sign in at https://{slug}.{reconcile.ALMANAC_DOMAIN} "
                "— access takes effect at their next sign-in, and keys are "
                "ready the moment they ask my_key there."]
    return "\n".join(out)


@mcp.tool
async def course_keys(course: str = "") -> str:
    """Key custody for a course you teach — who's minted, who's missing,
    when.  Shows status only, never the keys themselves: nobody but the
    owner ever retrieves a key.  Spend questions belong to course_usage."""
    _email, slug, course = _staff_scope(course)
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


# ---- tools: the front office ---------------------------------------------------
# Phase 2a (docs/registrar-spec.md, "Phase 2a — the front office").  Two
# doors.  The open one — course_request, my_requests, course_request_reply —
# answers anyone who can sign in, because asking costs nothing: a request is
# a ticket, like a problem report, and nothing provisions until an admin
# approves it and sets its budget.
# The desk — everything else here — answers the `admins:` list only, takes
# the course as an argument (admins span courses), and never acts on the
# first call: without confirm=true every desk tool that changes something
# or tells someone describes what it WOULD do, and that description is what
# the admin says yes to.  Same shape as
# roster_stage/roster_apply, without a stage id, because the arguments are
# short enough to repeat.

_UP_NOTE = ("Its chat comes up when the box next runs `just course-up` — "
            "automatic where the fleet watcher is installed (admin-guide, "
            "\"The fleet watcher\").  Until then the address won't answer.")


def _slug_or_refuse(slug: str, courses: dict, *, new: bool) -> str:
    slug = (slug or "").strip().lower() if new else _course_slug(slug, courses)
    if new and (why := reconcile.slug_error(slug)):
        raise ToolError(f"That won't work as a course id: {why}.  Something "
                        "like engr301-2026fall.")
    if not new and not reconcile.SLUG_RE.match(slug):
        raise ToolError(f"There's no course called '{slug}'.")
    if new and slug in courses and reconcile.course_state(courses[slug]) == "open":
        raise ToolError(
            f"{slug} already exists.  course_staff changes who teaches it; "
            "course_budget_set changes its pool.")
    if new and (why := reconcile.name_taken(slug, {"courses": courses})):
        raise ToolError(f"That id is taken: {why}.")
    if not new and slug not in courses:
        raise ToolError(f"There's no course called '{slug}'.")
    return slug


def _people(text: str) -> list[str]:
    return _parse_roster(text or "")[0]


async def _provision(slug: str) -> dict:
    try:
        return await reconcile.ensure_course(slug)
    except Exception as e:
        raise ToolError(
            f"The record for {slug} is saved, but provisioning stopped "
            f"({type(e).__name__}: {str(e)[:200]}).  It's safe to run again — "
            "every step is idempotent — and `just course` on the box shows "
            "the whole error.  An approval that stopped here can be "
            "approved again: the ticket stays open until the course is up."
            ) from None


def _url(slug: str) -> str:
    return f"https://{slug}.{reconcile.ALMANAC_DOMAIN}"


def _front_door() -> str:
    return f"https://{reconcile.CHAT_HOST}"


def _admins() -> list[str]:
    """Who desk mail goes to.  The eval admin persona sits on `admins:`
    after any eval run; a .invalid address is not a mailbox."""
    try:
        return [a for a in reconcile.load_courses()["admins"]
                if not a.endswith(REHEARSAL_DOMAIN)]
    except reconcile.CoursesError:
        return []


def _told(status: str) -> str:
    """The notification status line an ADMIN sees.  Requesters never see
    one: whether our mail relay is up is not their problem."""
    return f"\n\nNotified: {status}." if status else ""


@mcp.tool
async def course_request(kind: str, name: str, purpose: str,
                         details: str = "", instructors: str = "",
                         term: str = "", headcount: int = 0,
                         parent_course: str = "", slug: str = "",
                         coursework_confirmed: bool = False) -> str:
    """Ask for a new room on the aLLManac — anyone can.  It files a ticket
    for the platform admins, who approve it, return it with questions, or
    reject it with a reason.  Nothing is created until they approve.

    `kind`: "course" (they teach it), "project" (a project room under an
    existing course — set parent_course), or "standalone" (a club, team or
    thesis group).  `purpose`: a sentence on what it's for.  `details`:
    anything else they want the admins to know — sections, dates, what
    they plan to build.  `instructors`: who will run it, as emails; leave
    empty when that's the person asking.  `slug`: a suggested id, optional.
    Never ask them for a budget: the admins set the pool.

    The first call without coursework_confirmed returns a question you must
    put to them in its own words.  File again with coursework_confirmed=true
    only if they said yes to it."""
    email, _role, _here = _ident_open()
    courses = _courses_or_refuse()["courses"]
    kind = (kind or "").strip().lower()
    if kind not in reconcile.REQUEST_KINDS:
        raise ToolError("kind is one of: " + ", ".join(reconcile.REQUEST_KINDS)
                        + ".")
    if not (name or "").strip() or not (purpose or "").strip():
        raise ToolError("A request needs a name and a sentence on what it's "
                        "for — the person approving it has only this to go on.")
    parent = _course_slug(parent_course, courses) or None
    if kind == "project":
        if not parent:
            raise ToolError("A project room hangs off an existing course — "
                            "which one?  (parent_course)")
        if parent not in courses:
            raise ToolError(f"There's no course called '{parent}' to put a "
                            "project under.  my_courses shows theirs.")
    wanted = None
    if (slug or "").strip():
        wanted = _slug_or_refuse(slug, courses, new=True)
    runs = _people(instructors) or [email]
    if reconcile.open_count(email) >= reconcile.MAX_OPEN_PER_PERSON:
        raise ToolError(
            f"You already have {reconcile.MAX_OPEN_PER_PERSON} requests "
            "waiting — my_requests shows them.  Let those be decided first.")
    question = reconcile.front_door_text()
    if not coursework_confirmed:
        return ("NOT FILED YET.  Before this can be filed, put the following "
                "to them in these words, and wait for their answer:\n\n"
                f"{question}\n\n"
                "Only if they say yes, call course_request again with the same "
                "details and coursework_confirmed=true.  If they say no, don't "
                "file it — the text above says where that work belongs.")
    if (r := _rehearse(email, f"filed a {kind} request for {name.strip()!r} and told the admins")):
        return r
    rec = reconcile.file_request(
        by=email, kind=kind, name=name, purpose=purpose, details=details,
        instructors=runs, term=term, headcount=headcount, parent=parent,
        slug=wanted, attested=question)
    # The envelope only — see planes/notify.py.  Purpose and details stay
    # on the box; the desk reads them in course_requests.
    await reconcile.notify_desk(
        _admins(), f"New room request {rec['id']}",
        [f"{kind}: {rec['name']}" + (f" (under {parent})" if parent else ""),
         f"from {email}" + (f" · {rec['term']}" if rec["term"] else "")
         + (f" · ~{rec['headcount']} people" if rec["headcount"] else ""),
         "Read it and decide in the Dev Guide at the front door — ask what's "
         "waiting."],
        _front_door())
    return (f"Filed — request {rec['id']} ({kind}: {rec['name']}).  The "
            "platform admins review each one: they approve it, return it with "
            "questions, or turn it down with a reason, and nothing is created "
            "until they approve.  They set the budget.  my_requests shows "
            "where it stands and anything they've written back.")


@mcp.tool
async def my_requests() -> str:
    """The caller's own room requests: where each stands, and everything the
    admins have written back."""
    email, _role, _here = _ident_open()
    rows = reconcile.requests_list(by=email)
    if not rows:
        return "You haven't asked for a room.  course_request is how."
    out = []
    for r in rows:
        head = f"**{r['id']}** — {r['kind']}: {r['name']} · filed {r['filed']} · **{r['status']}**"
        out.append(head)
        for m in r.get("thread") or []:
            who = "admins" if m["as"] == "admin" else "you"
            out.append(f"- {m['at']}, {who}: {m['text']}")
        if r["status"] == "returned":
            out.append("- Waiting on you: answer with course_request_reply and "
                       "it goes back to the admins.")
        elif r["status"] == "approved" and r.get("course"):
            out.append(f"- Your chat: {_url(r['course'])}")
        out.append("")
    return "\n".join(out).rstrip()


@mcp.tool
async def course_request_reply(request_id: str, message: str) -> str:
    """Answer the admins on one of the caller's own requests — usually one
    they returned with questions.  Sends it back to the admins to review.
    Only the person who filed a request can reply to it."""
    email, _role, _here = _ident_open()
    rid = request_id.strip()
    rec = next((r for r in reconcile.requests_list(by=email)
                if r["id"] == rid), None)
    if rec is None:
        raise ToolError(f"You don't have a request {rid!r} — my_requests "
                        "lists yours.")
    if rec["status"] in ("approved", "rejected"):
        raise ToolError(f"{rid} was already {rec['status']}.  For something "
                        "new, file a new request.")
    if not (message or "").strip():
        raise ToolError("Say what you'd like to add.")
    if (r := _rehearse(email, f"added your reply to {rid} and sent it back to the admins")):
        return r
    reconcile.answer_request(rid, email, message)
    await reconcile.notify_desk(
        _admins(), f"Request {rid} answered — back in the queue",
        [f"{rec['kind']}: {rec['name']}", f"from {email}",
         "Their reply is on the ticket in the Dev Guide."],
        _front_door())
    return f"Added to {rid}, and it's back with the admins."


@mcp.tool
async def course_requests(status: str = "open") -> str:
    """The request tickets, oldest first.  `status`: open (waiting on an
    admin), returned (waiting on the requester), approved, rejected, or
    all.  Platform admins only."""
    email, _role, _here = _ident_open()
    _admin_or_refuse(email)
    want = None if status.strip().lower() == "all" else status.strip().lower()
    rows = reconcile.requests_list(status=want)
    if not rows:
        return f"No {status} requests."
    out = []
    for r in rows:
        out += [f"**{r['id']}** · {r['status']} · filed {r['filed']} by {r['by']}",
                f"- {r['kind']}: {r['name']}"
                + (f" (under {r['parent']})" if r.get("parent") else "")
                + (f" · wants id `{r['slug_wanted']}`" if r.get("slug_wanted") else ""),
                f"- runs it: {', '.join(r['instructors'])}"
                + (f" · {r['term']}" if r.get("term") else "")
                + (f" · ~{r['headcount']} people" if r.get("headcount") else ""),
                f"- why: {r['purpose']}"]
        if r.get("details"):
            out.append(f"- details: {r['details']}")
        out.append(f"- said yes to the front-door question {r['attestation']['at']}")
        for m in r.get("thread") or []:
            out.append(f"- {m['at']}, {m['as']} ({m['by']}): {m['text']}")
        if r.get("course"):
            out.append(f"- became {r['course']} with a ${r.get('budget', 0):g} pool")
        out.append("")
    return "\n".join(out).rstrip()


def _open_ticket_or_refuse(rid: str) -> dict:
    rec = next((r for r in reconcile.requests_list() if r["id"] == rid), None)
    if rec is None:
        raise ToolError(f"No request {rid!r}.  course_requests lists them.")
    if rec["status"] in ("approved", "rejected"):
        raise ToolError(f"{rid} is already {rec['status']}.")
    return rec


@mcp.tool
async def course_approve(request_id: str, budget: float, slug: str = "",
                         tas: str = "", note: str = "",
                         confirm: bool = False) -> str:
    """Approve a request: create the course and provision it.  `budget` is
    the pool, dollars per term — required, because the pool is yours to
    set, never the requester's.  `slug` is the new course's id (defaults
    to the one the request suggested).  `tas`: TA emails to add, often
    from the requester's replies.  `note` is shown to the requester.
    Without confirm=true this only describes what it would create.
    Platform admins only."""
    email, _role, _here = _ident_open()
    _admin_or_refuse(email)
    rid = request_id.strip()
    rec = _open_ticket_or_refuse(rid)
    if rec["status"] == "returned":
        raise ToolError(f"{rid} is waiting on the requester's answer.  "
                        "Approve it once they reply, or reject it.")
    pool = float(budget or 0)
    if pool <= 0:
        raise ToolError("Set a budget — the course's pool in dollars per "
                        f"term.  The platform default is "
                        f"${reconcile.DEFAULT_COURSE_BUDGET:g}.")
    courses = _courses_or_refuse()["courses"]
    if not (slug or rec.get("slug_wanted")):
        raise ToolError("This request didn't suggest an id — pick one "
                        "(it becomes the chat's address) and pass it as slug.")
    wanted = (slug or rec.get("course") or rec["slug_wanted"]).strip().lower()
    # An approval that stopped in _provision left its course on file and
    # the ticket open.  Approving again finishes it; anything else that
    # already holds the slug is still refused.
    retry = bool(rec.get("course")) and wanted == rec["course"] and wanted in courses
    new = wanted if retry else _slug_or_refuse(wanted, courses, new=True)
    ta = [e for e in _people(tas) if e not in rec["instructors"]]
    plan = [f"Would {'finish provisioning' if retry else 'create'} **{new}** — {rec['name']}",
            f"- instructors: {', '.join(rec['instructors'])}"]
    if ta:
        plan.append(f"- TAs: {', '.join(ta)}")
    plan += [f"- pool: ${pool:g} per term",
            f"- chat at {_url(new)}"]
    if note.strip():
        plan.append(f"- note to {rec['by']}: {note.strip()}")
    if not confirm:
        return "\n".join(plan + ["", "Nothing has changed.  If that's right, "
                                  "call course_approve again with "
                                  "confirm=true."])
    if (r := _rehearse(email, f"created {new} from {rid} with a ${pool:g} pool and emailed {rec['by']}")):
        return r
    reconcile.claim_request_course(rid, new)
    reconcile.upsert_course(new, rec["name"], rec["instructors"], tas=ta,
                            budget=pool)
    summary = await _provision(new)
    reconcile.decide_request(rid, "approved", email, note=note.strip(),
                             course=new, budget=pool)
    body = (f"Your request for {rec['name']} ({rid}) is approved.\n\n"
            f"Its chat: {_url(new)}\n"
            f"Its budget for the term: ${pool:g}, shared by everyone in it.\n\n"
            + (f"A note from the platform admins:\n{note.strip()}\n\n" if note.strip() else "")
            + "The address should answer within a few minutes.  Sign in with "
              "your campus account; the instructors can add people from the "
              "Instructor Guide at the front door "
              f"({_front_door()}) or from the course's own chat.\n")
    told = await reconcile.notify_person(
        [rec["by"], *rec["instructors"], *ta], f"{rec['name']} is approved",
        body)
    await reconcile.notify_desk(
        _admins(), f"Request {rid} approved → {new}",
        [f"by {email} · ${pool:g} pool"], email_fallback=False)
    return "\n".join([f"Approved {rid} → {new} is provisioned.",
                      f"- staff granted: {', '.join(summary['staff']['granted'])}",
                      f"- chat: {_url(new)}", "", _UP_NOTE,
                      "", f"{rec['by']} sees this in my_requests."]) + _told(told)


@mcp.tool
async def course_return(request_id: str, note: str,
                        confirm: bool = False) -> str:
    """Send a request back to the person who filed it, with what you need
    from them.  They answer with course_request_reply and it comes back to
    the queue.  The note is emailed to them word for word, so without
    confirm=true this only shows what would be sent.  Platform admins
    only."""
    email, _role, _here = _ident_open()
    _admin_or_refuse(email)
    if not (note or "").strip():
        raise ToolError("Say what you need from them — they'll read it.")
    rid = request_id.strip()
    rec = _open_ticket_or_refuse(rid)
    if not confirm:
        return (f"Would return {rid} ({rec['name']}) to {rec['by']} and "
                f"email them this note, word for word:\n\n> {note.strip()}\n\n"
                "Nothing has been sent.  If that's right, call course_return "
                "again with confirm=true.")
    if (r := _rehearse(email, f"returned {rid} to {rec['by']} with your note and emailed them")):
        return r
    reconcile.decide_request(rid, "returned", email, note=note.strip())
    told = await reconcile.notify_person(
        [rec["by"]], f"Your request {rid} needs a little more",
        f"The platform admins looked at your request for {rec['name']} and "
        f"need a bit more before they can decide:\n\n{note.strip()}\n\n"
        f"To answer, open the aLLManac front door ({_front_door()}), choose "
        f"the Instructor Guide or the Student Guide, and ask it to reply to "
        f"{rid}.  Your answer goes straight back to them.\n")
    await reconcile.notify_desk(
        _admins(), f"Request {rid} returned to {rec['by']}",
        [f"by {email}"], email_fallback=False)
    return (f"Returned {rid} to {rec['by']} with your note.  It's back in "
            "the open queue when they reply.") + _told(told)


@mcp.tool
async def course_reject(request_id: str, note: str,
                        confirm: bool = False) -> str:
    """Turn a request down, with the reason — the person who asked reads it
    in my_requests and gets it by email.  A rejected request is closed;
    they can file a new one.  Without confirm=true this only shows what
    would be sent.  Platform admins only."""
    email, _role, _here = _ident_open()
    _admin_or_refuse(email)
    if not (note or "").strip():
        raise ToolError("Say why — the person who asked will read it.")
    rid = request_id.strip()
    rec = _open_ticket_or_refuse(rid)
    if not confirm:
        return (f"Would reject {rid} ({rec['name']}) — closed for good — and "
                f"email {rec['by']} this note, word for word:\n\n> "
                f"{note.strip()}\n\nNothing has been sent.  If that's right, "
                "call course_reject again with confirm=true.")
    if (r := _rehearse(email, f"rejected {rid} and emailed {rec['by']} your note")):
        return r
    reconcile.decide_request(rid, "rejected", email, note=note.strip())
    told = await reconcile.notify_person(
        [rec["by"]], f"Your request {rid} wasn't approved",
        f"The platform admins looked at your request for {rec['name']} and "
        f"can't approve it:\n\n{note.strip()}\n\n"
        "You're welcome to file a new request if something changes — the "
        f"guides at the front door ({_front_door()}) can help.\n")
    await reconcile.notify_desk(
        _admins(), f"Request {rid} rejected",
        [f"by {email}"], email_fallback=False)
    return (f"Rejected {rid}.  {rec['by']} will see your note in "
            "my_requests.") + _told(told)


@mcp.tool
async def course_create(slug: str, name: str, instructors: str, tas: str = "",
                        budget: float = 0.0, confirm: bool = False) -> str:
    """Create and provision a course directly, skipping the request queue.
    `slug` becomes the chat's address; `instructors` and `tas` are emails.
    Without confirm=true this only describes what it would create.
    Platform admins only."""
    email, _role, _here = _ident_open()
    _admin_or_refuse(email)
    courses = _courses_or_refuse()["courses"]
    new = _slug_or_refuse(slug, courses, new=True)
    ins, ta = _people(instructors), _people(tas)
    if not ins:
        raise ToolError("A course needs at least one instructor, by email.")
    if not (name or "").strip():
        raise ToolError("A course needs a name people will recognise.")
    pool = float(budget or reconcile.DEFAULT_COURSE_BUDGET)
    plan = [f"Would create **{new}** — {name.strip()}",
            f"- instructors: {', '.join(ins)}"]
    if ta:
        plan.append(f"- TAs: {', '.join(ta)}")
    plan += [f"- pool: ${pool:g} per term", f"- chat at {_url(new)}"]
    if not confirm:
        return "\n".join(plan + ["", "Nothing has changed.  If that's right, "
                                  "call course_create again with "
                                  "confirm=true."])
    if (r := _rehearse(email, f"created and provisioned {new}")):
        return r
    reconcile.upsert_course(new, name.strip(), ins, tas=ta, budget=pool)
    summary = await _provision(new)
    return "\n".join([f"Created {new}.",
                      f"- staff granted: {', '.join(summary['staff']['granted'])}",
                      f"- chat: {_url(new)}", "", _UP_NOTE])


@mcp.tool
async def course_staff(course: str, add_instructors: str = "",
                       add_tas: str = "", remove: str = "",
                       confirm: bool = False) -> str:
    """Change who teaches a course: add instructors or TAs, or remove
    staff.  Removing someone takes away their admin rights in that course's
    chat as well as their staff tools; if they aren't also a student, their
    access and key go too.  Without confirm=true this only describes the
    change.  Platform admins only."""
    email, _role, _here = _ident_open()
    _admin_or_refuse(email)
    courses = _courses_or_refuse()["courses"]
    slug = _slug_or_refuse(course, courses, new=False)
    c = courses[slug]
    ai, at, rm = _people(add_instructors), _people(add_tas), _people(remove)
    if not (ai or at or rm):
        raise ToolError("Nothing to change — name someone to add or remove.")
    ins = [e for e in c["instructors"] + ai if e not in rm and e not in at]
    if not ins:
        raise ToolError(f"That would leave {slug} with no instructor.  Add "
                        "the new one in the same call.")
    staff_now = set(c["instructors"]) | set(c["tas"])
    plan = [f"Staff change for **{slug}**"]
    if ai:
        plan.append(f"- add as instructor: {', '.join(ai)}")
    if at:
        plan.append(f"- add as TA: {', '.join(at)}")
    for e in rm:
        if e not in staff_now:
            plan.append(f"- {e} isn't staff here — nothing to remove")
        elif e in (c.get("students") or []):
            plan.append(f"- remove {e} from staff (stays enrolled as a student)")
        else:
            plan.append(f"- remove {e}: staff rights, access and key all end")
    if not confirm:
        return "\n".join(plan + ["", "Nothing has changed.  If that's right, "
                                  "call course_staff again with confirm=true."])
    if (r := _rehearse(email, f"changed the staff of {slug} as described")):
        return r
    try:
        reconcile.set_staff(slug, ai, at, rm)
    except ValueError as e:
        raise ToolError(str(e)) from None
    summary = await _provision(slug)
    st = summary["staff"]
    out = [f"Staff for {slug} updated.",
           f"- staff now: {', '.join(st['granted'])}"]
    if st.get("revoked"):
        out.append(f"- rights removed: {', '.join(st['revoked'])}")
    out.append("Changes take effect at each person's next sign-in.")
    return "\n".join(out)


@mcp.tool
async def course_budget_set(course: str, amount: float,
                            confirm: bool = False) -> str:
    """Set a course's pool — the whole class's shared ceiling for the term,
    chat and API keys together — in dollars.  Not anyone's personal key.
    Without confirm=true this only describes the change.  Platform admins
    only."""
    email, _role, _here = _ident_open()
    _admin_or_refuse(email)
    courses = _courses_or_refuse()["courses"]
    slug = _slug_or_refuse(course, courses, new=False)
    amount = float(amount)
    if amount <= 0:
        raise ToolError("A pool has to be more than $0 — a course with no "
                        "pool can't chat at all.")
    was = courses[slug]["budgets"]["course"]
    if not confirm:
        return (f"Would set the {slug} pool from ${was:g} to ${amount:g} per "
                "term.  Nothing has changed.  If that's right, call "
                "course_budget_set again with confirm=true.")
    if (r := _rehearse(email, f"set the {slug} pool to ${amount:g}")):
        return r
    reconcile.set_course_budget(slug, amount)
    await _provision(slug)
    return (f"{slug} pool is now ${amount:g} per term (was ${was:g}).  The "
            "gateway enforces it from the next request.")


# ---- tools: the fleet from above ----------------------------------------------
# Platform admins only.  Every one of these is a READ: the registrar reporting
# what it already reconciles, joined into one row per course.  Envelope only
# — counts, names, sizes, owners, timestamps — never a message, a title, or
# an instruction.  That line is a wall (docs/design-walls.md); the tools'
# wording promises it because the code keeps it.

def _n(x) -> str:
    return f"{int(x):,}"


def _mb(n: int) -> str:
    return f"{n / 1_048_576:.1f} MB" if n >= 1_048_576 else f"{n / 1024:.0f} KB"


@mcp.tool
async def fleet_inventory() -> str:
    """Every instance in the fleet on one page: is it answering, how many
    people, conversations, agents and files, how big its database is, what
    the course pool has spent against its cap, and how the roster compares
    to the door.  Also rewrites fleet/inventory.md + .json on the box.
    Platform admins only.  Metadata only — no conversation content."""
    # _ident_open: the desk is at the front door, and the header never
    # decided anything here — the admins: list does.  Same for every admin
    # tool below.
    email, _role, _here = _ident_open()
    _admin_or_refuse(email)
    rep = await reconcile.fleet_inventory()
    fl, ft = rep["flagship"], rep["flagship"]["census"].get("totals", {})
    out = [f"Fleet census — {rep['domain']} — {rep['generated']}", "",
           "| instance | answers | users | convos | agents (shared) | files | data | pool | roster |",
           "|---|---|---:|---:|---:|---:|---:|---|---|",
           f"| {fl['host']} | {'yes' if fl['reachable'] else 'NO'} | {ft.get('users', 0)} | "
           f"{_n(ft.get('conversations', 0))} | {ft.get('agents', 0)} ({ft.get('agents_shared', 0)}) | "
           f"{ft.get('files', 0)} · {_mb(ft.get('file_bytes', 0))} | {_mb(ft.get('storage_bytes', 0))} | — | flagship |"]
    for c in rep["courses"]:
        t = c["census"].get("totals", {})
        pool = c.get("pool")
        if pool:
            cap = pool.get("max_budget")
            ps = f"${pool['spend']:.2f}/" + (f"${cap:.0f}" if cap is not None else "∞") + f" · {pool['keys']} keys"
        else:
            ps = "no team"
        r = c["roster"]
        state = "yes" if c["reachable"] else ("NO" if c["rendered"] else "not rendered")
        out.append(f"| {c['host']} | {state} | {t.get('users', 0)} | {_n(t.get('conversations', 0))} | "
                   f"{t.get('agents', 0)} ({t.get('agents_shared', 0)}) | "
                   f"{t.get('files', 0)} · {_mb(t.get('file_bytes', 0))} | {_mb(t.get('storage_bytes', 0))} | "
                   f"{ps} | {r['students']} students / {r['instructors'] + r['tas']} staff |")
    findings = []
    for c in rep["courses"]:
        if c["rendered"] and not c["reachable"]:
            findings.append(f"{c['slug']}: rendered but not answering")
        if "actions" in c["capabilities"] and not c["allowed_domains"]:
            findings.append(f"{c['slug']}: Actions enabled with no allowlist")
        if c["pool"] and c["pool"].get("max_budget") is not None and \
                c["pool"]["spend"] >= 0.9 * float(c["pool"]["max_budget"]):
            findings.append(f"{c['slug']}: pool at {c['pool']['spend'] / float(c['pool']['max_budget']):.0%}")
        d = c.get("door")
        if d:
            roster = set(_courses_or_refuse()["courses"][c["slug"]]["students"])
            extra = set(d["member"]) - roster - set(d["admin"])
            if extra:
                findings.append(f"{c['slug']}: {len(extra)} at the door who aren't rostered (fleet_access)")
    if rep["orphan_databases"]:
        findings.append("databases with no course record: " + ", ".join(rep["orphan_databases"]))
    for c in rep["courses"]:
        for k, v in (c.get("errors") or {}).items():
            findings.append(f"{c['slug']}: could not read {k} — {v}")
    out += ["", "Findings:" if findings else "No findings."]
    out += [f"  - {f}" for f in findings]
    out += ["", "Written: fleet/inventory.md and fleet/inventory.json.  Per course: "
                "fleet_access(slug), fleet_exposure(slug)."]
    return "\n".join(out)


@mcp.tool
async def fleet_access(course: str) -> str:
    """Who can get into one course and who has: the roster, the Keycloak
    door, everyone who has actually signed in (with last activity), who is
    signed in right now — and the three diffs a review asks for: rostered
    but never seen, seen but not rostered, at the door but not rostered.
    Platform admins only."""
    email, _role, _here = _ident_open()
    _admin_or_refuse(email)
    slug = _slug_or_refuse(course, _courses_or_refuse()["courses"], new=False)
    a = await reconcile.fleet_access(slug)
    out = [f"Access — {a['name']} ({slug})", "",
           f"Rostered: {len(a['roster'])} ({len(a['staff'])} staff) · door: {len(a['door'])} may sign in, "
           f"{len(a['admins'])} admins · signed in ever: {len(a['signed_in'])} · right now: {len(a['sessions'])}"]
    if a["signed_in"]:
        out += ["", "| user | role | convos | msgs | tokens | first seen | last active |",
                "|---|---|---:|---:|---:|---|---|"]
        out += [f"| {u['email']} | {u['role']} | {u['conversations']} | {u['messages']} | "
                f"{_n(u['tokens'])} | {u['first_seen'] or '—'} | {u['last_active'] or '—'} |"
                for u in a["signed_in"]]
    for label, key, hint in (
            ("Rostered, never signed in", "never_seen", "normal early in a term"),
            ("Signed in, NOT on the roster", "seen_not_rostered", "how did they get in? check the door"),
            ("At the door, NOT on the roster", "door_not_rostered", "a stale grant — re-apply the roster"),
            ("Rostered, no door yet", "rostered_no_door", "roster sync pending — re-apply")):
        if a[key]:
            out += ["", f"{label} ({len(a[key])}; {hint}): " + ", ".join(a[key])]
    if a["sessions"]:
        out += ["", "Signed in now: " + ", ".join(a["sessions"])]
    return "\n".join(out)


@mcp.tool
async def fleet_exposure(course: str) -> str:
    """What one course has that reaches past a single person: every agent
    with its share scope (public / role / group / named users / private),
    its tools and knowledge count; every file by size and owner; the
    capabilities and Actions allowlist the course record grants; the pool.
    Platform admins only.  Names and sizes — never contents."""
    email, _role, _here = _ident_open()
    _admin_or_refuse(email)
    slug = _slug_or_refuse(course, _courses_or_refuse()["courses"], new=False)
    x = await reconcile.fleet_exposure(slug)
    t = x["totals"]
    out = [f"Exposure — {x['name']} ({slug})", "",
           f"Capabilities: {', '.join(x['capabilities']) or 'none'}",
           "Actions allowlist: " + (", ".join(x["allowed_domains"]) if x["allowed_domains"]
                                    else ("NONE — any public URL" if "actions" in x["capabilities"]
                                          else "n/a (actions off)")),
           f"Models: {', '.join(x['models'])}"]
    if x["pool"]:
        out.append(f"Pool: ${x['pool']['spend']:.2f} spent · {x['pool']['keys']} keys")
    out += ["", f"Agents: {t.get('agents', 0)} ({t.get('agents_shared', 0)} shared)"]
    if x["agents"]:
        out += ["", "| agent | owner | scope | tools | actions | files | updated |",
                "|---|---|---|---|---:|---:|---|"]
        out += [f"| {a['name']} | {a['owner']} | {a['share']} | {', '.join(a['tools']) or '—'} | "
                f"{a['actions']} | {a['files']} | {a['updated'] or '—'} |" for a in x["agents"]]
    out += ["", f"Files: {t.get('files', 0)} · {_mb(t.get('file_bytes', 0))} "
                f"(database {_mb(t.get('storage_bytes', 0))} on disk)"]
    if x["files"]:
        out += ["", "| file | size | owner | embedded | uploaded |", "|---|---:|---|---|---|"]
        out += [f"| {f['filename']} | {_mb(f['bytes'])} | {f['owner']} | "
                f"{'yes' if f['embedded'] else 'no'} | {f['created'] or '—'} |" for f in x["files"][:60]]
        if len(x["files"]) > 60:
            out.append(f"| … {len(x['files']) - 60} more, smallest last | | | | |")
    return "\n".join(out)


# ---- tools: nominations ---------------------------------------------------------
# The other direction: instead of the platform looking down, a course sends
# something up.  "This agent is worth copying" — the author's own, or any in
# the course if staff say so.  What comes out is a FILE (a template on the
# fleet volume), because the lesson is that an agent is a reproducible thing
# and not a button in someone else's UI.

@mcp.tool
async def nominate_agent(agent_id: str, note: str = "") -> str:
    """Nominate an agent from THIS course as a shared template for the
    platform.  Your own agents, or any in the course if you're teaching
    staff.  `agent_id` is on the agent's edit page (agent_…).  Nothing is
    copied yet: a platform admin reviews the nomination and exports it as
    a template file — name, instructions, model, tools, and the list of
    knowledge files by name.  Say in `note` what it does and why it's
    worth sharing."""
    email, _role, slug = _ident()
    course = _course_or_refuse(slug)
    staff = email in course.get("instructors", []) or email in course.get("tas", [])
    try:
        if (r := _rehearse(email, "nominated that agent as a template")):
            return r
        r = await reconcile.nominate_agent(slug, agent_id.strip(), email, note, staff)
    except KeyError:
        raise ToolError(f"No agent {agent_id!r} in {slug} — the id is on the agent's "
                        "edit page and starts with agent_.") from None
    except PermissionError as e:
        raise ToolError(f"{e}.  You can nominate agents you built; staff can nominate "
                        "any agent in the course.") from None
    rec, tpl = r["nomination"], r["template"]
    out = [f"Nominated: {tpl['name']} ({rec['agent_id']}) — nomination {rec['id']}", "",
           "What a template of it would carry:",
           f"  model {tpl['provider']}/{tpl['model']} · tools: {', '.join(tpl['tools']) or 'none'} · "
           f"instructions: {len(tpl['instructions'])} chars · "
           f"knowledge: {len(tpl['knowledge'])} file(s)"
           + (" · Actions: " + str(tpl["actions"]) + " (not portable)" if tpl["actions"] else "")]
    if tpl["knowledge"]:
        out += ["  files: " + ", ".join(k["filename"] for k in tpl["knowledge"])]
    out += ["", "A platform admin reviews it next (`nominations`, then export).  The result "
                "is a file others can read, fork, and seed — your name stays on it as author."]
    return "\n".join(out)


@mcp.tool
async def nominations() -> str:
    """Nominations on file: teaching staff see their own course's; platform
    admins see every course's, with the ids `nomination_export` and
    `nomination_decline` take."""
    email, _role, slug = _ident_open()
    courses = _courses_or_refuse()
    if email in courses["admins"]:
        rows = reconcile.nominations()
    elif not slug:
        raise ToolError("Staff see their course's nominations from inside "
                        "that course's chat.")
    else:
        course = _course_or_refuse(slug)
        _staff_or_refuse(email, course, slug)
        rows = reconcile.nominations(slug)
    if not rows:
        return "No nominations yet."
    out = ["| id | status | course | agent | by | when | note |", "|---|---|---|---|---|---|---|"]
    out += [f"| {r['id']} | {r['status']} | {r['course']} | {r['name']} ({r['agent_id']}) | "
            f"{r['by']} | {r['at']} | {r['note'] or '—'} |" for r in rows]
    return "\n".join(out)


@mcp.tool
async def nomination_export(nomination_id: str) -> str:
    """Export a nominated agent as a template file on the fleet volume
    (fleet/templates/<id>-<name>.yaml) and mark the nomination.  Platform
    admins only.  The operator seeds it where it belongs; the file is the
    handoff."""
    email, _role, _here = _ident_open()
    _admin_or_refuse(email)
    if (r := _rehearse(email, f"exported {nomination_id.strip()} as a template and marked it")):
        return r
    try:
        r = await reconcile.export_nomination(nomination_id.strip(), email)
    except KeyError as e:
        raise ToolError(str(e.args[0])) from None
    tpl = r["template"]
    return (f"Exported {tpl['name']} → {r['path']}\n"
            f"author {tpl['owner']} · model {tpl['provider']}/{tpl['model']} · "
            f"tools {', '.join(tpl['tools']) or 'none'} · knowledge {len(tpl['knowledge'])} file(s) by name.\n"
            "Next on the box: read it, then seed it on the instance you mean it for.")


@mcp.tool
async def nomination_decline(nomination_id: str) -> str:
    """Decline a nomination (kept on file as declined).  Platform admins only."""
    email, _role, _here = _ident_open()
    _admin_or_refuse(email)
    if (r := _rehearse(email, f"declined {nomination_id.strip()}")):
        return r
    r = reconcile.decline_nomination(nomination_id.strip(), email)
    if r is None:
        raise ToolError(f"No nomination {nomination_id!r}.")
    return f"Declined {r['id']} ({r['name']}, {r['course']})."


@mcp.tool
async def report_problem(what: str, course: str = "", asked: str = "",
                         answered: str = "", sources: list[str] | None = None) -> str:
    """File a problem report about the aLLManac — something that didn't work,
    a wrong answer, a step that failed.  Works from any room, including the
    front door.

    Fill `asked` and `answered` with the question that went wrong and the
    answer that came back, and `sources` with the knowledge files you cited,
    whenever the report is about something YOU told them.  A complaint on its
    own is a mood; the same complaint with the exchange attached is
    debuggable.  Set `course` only if they name a course and this instance
    isn't one already."""
    email, role, slug = _ident_open()
    what = (what or "").strip()
    if not what:
        raise ToolError("Say what went wrong — a report with no description "
                        "is a ticket nobody can action.")
    if (r := _rehearse(email, "filed a problem report for the platform team")):
        return r
    try:
        rec = reconcile.file_report(
            by=email, role=role, from_room=slug or "vestibule",
            course=slug or None, about=course or None, what=what,
            asked=asked, answered=answered, sources=sources or [])
    except reconcile.CoursesError:
        raise ToolError(
            "The registrar can't read its course records right now, so I "
            "can't file that against the right course.  This is a platform "
            "fault, not something you did — tell the platform admin."
        ) from None

    # The desk channel only, and the envelope only: a report quotes what a
    # person typed, and none of that leaves the box.  No email fallback —
    # the report queue has its own readers (devs:), and mailing every admin
    # per report would teach them to filter it.
    await reconcile.notify_desk(
        [], f"Problem report {rec['id']}",
        [f"about {rec['about'] or 'no single course — needs routing'} · "
         f"filed from {slug or 'the front door'}",
         "Read it in the Dev Guide (reports) or with `just reports`."],
        _front_door(), email_fallback=False)
    out = [f"Filed — report {rec['id']}."]
    if rec["about"]:
        how = {"header": "this course",
               "stated": "the course you named",
               "roster": "the course you're on"}[rec["route"]]
        out.append(f"It's on the pile for **{rec['about']}** ({how}).")
    elif rec["enrolled"]:
        # Recorded unrouted on purpose — see planes/verbs.file_report.
        out.append("You're on more than one course, so I didn't guess which "
                   "one this is about: " + ", ".join(rec["enrolled"]) + ".  "
                   "Say the name and I'll file a follow-up that names it.")
    else:
        out.append("No course on your roster, so this is filed as a platform "
                   "report — that's the right pile for it.")
    if "trace" not in rec:
        out.append("Filed without the exchange attached.  If this was about an "
                   "answer I gave, what I said is the useful half.")
    return "\n".join(out)


@mcp.tool
async def reports(status: str = "open") -> str:
    """Problem reports on file: teaching staff see their own course's,
    platform admins see every one.  `status` is open, triaged, closed, or
    'all'."""
    email, _role, slug = _ident_open()
    courses = _courses_or_refuse()
    want = None if status.strip().lower() == "all" else status.strip().lower()
    if _is_dev(email, courses):
        rows = reconcile.reports(status=want)
    else:
        if not slug:
            raise ToolError(
                "Reading the report pile is a faculty view of one course, so "
                "it only works from inside that course's chat — unless you're "
                "on the platform team, and you're not.  Filing a report works "
                "anywhere, and `my_reports` shows you your own."
            )
        course = _course_or_refuse(slug)
        _staff_or_refuse(email, course, slug)
        rows = reconcile.reports(slug, status=want)
    if not rows:
        return f"No {want or ''} reports.".replace("  ", " ")
    out = ["| id | when | who | about | what | trace |", "|---|---|---|---|---|---|"]
    for r in rows:
        t = r.get("trace") or {}
        tr = "asked+answer" if t.get("answered") else ("asked" if t.get("asked") else "—")
        out.append(f"| {r['id']} | {r['at']} | {r['by']} | "
                   f"{r['about'] or 'unrouted'} | {r['what'][:120]} | {tr} |")
    out.append("")
    out.append("Full text and the exchange: `just reports` on the box.")
    return "\n".join(out)


@mcp.tool
async def report_triage(report_id: str, status: str = "triaged",
                        note: str = "") -> str:
    """Work a problem report: mark it triaged or closed and say what was done
    about it.  Platform team only (`devs:` or `admins:` in courses.yaml).

    `note` is written where the reporter can read it — `my_reports` shows
    them the resolution — so write it for them, not for the commit log."""
    email, _role, _slug = _ident_open()
    _dev_or_refuse(email)
    want = status.strip().lower()
    if want not in ("triaged", "closed"):
        raise ToolError(f"Status is triaged or closed, not {status!r}.  "
                        "Reports start open by themselves.")
    if want == "closed" and not note.strip():
        # Not pedantry: the note is the ONLY thing the person who filed it
        # ever gets back.  Closing without one is the silence that teaches
        # people the tool does nothing.
        raise ToolError(
            "Closing a report needs a note — it's the only thing the person "
            "who filed it ever sees.  One sentence about what happened."
        )
    if (r := _rehearse(email, f"marked {report_id.strip()} {want}")):
        return r
    r = reconcile.close_report(report_id.strip(), email, note, status=want)
    if r is None:
        raise ToolError(f"No report {report_id!r}.  `reports all` lists them.")
    return (f"{r['id']} → {r['status']}"
            + (f" — {r['resolution']}" if r.get("resolution") else "")
            + f"\n{r['by']} sees this the next time they ask `my_reports`.")


@mcp.tool
async def my_reports() -> str:
    """What happened to the problems you reported.  Works from any room.

    Pull, not push: there is no notification channel we own, and inventing
    one would be a second inbox nobody reads.  Asking is the channel."""
    email, _role, _slug = _ident_open()
    rows = [r for r in reconcile.reports() if r["by"] == email]
    if not rows:
        return ("You haven't filed any reports.  If something isn't working, "
                "`report_problem` is how you tell us — and if it was about an "
                "answer I gave, say so and I'll send what I said along with it.")
    out = []
    for r in sorted(rows, key=lambda x: x["at"], reverse=True):
        head = f"**{r['at']}** — {r['status']}"
        if r["about"]:
            head += f" · {r['about']}"
        out += [head, f"> {r['what']}"]
        if r.get("resolution"):
            out.append(f"Resolution: {r['resolution']}")
        elif r["status"] == "open":
            out.append("_Still open — nobody has picked it up yet._")
        out.append("")
    return "\n".join(out).rstrip()


# ---- liveness ------------------------------------------------------------------
# Unauthenticated on purpose (serves no user data) — what `just smoke` curls.
# 200 even before bao-init so a fresh box's first deploy isn't "down"; the
# body says what's actually wired.

@mcp.custom_route("/health", methods=["GET"])
async def health(request: Request) -> JSONResponse:
    bao = ("configured" if reconcile.bao_configured()
           else "not configured (run: just bao-init)")
    try:
        data = reconcile.load_courses()
    except reconcile.CoursesError as e:
        # Still 200 — the process is up and this endpoint's whole job is to
        # say what's actually wired.  But an unreadable roster file is a
        # genuine fault, so it must never read as "ok": the fleet renders
        # from this file, and `courses: 0` alone looks exactly like a fresh
        # box.  503 would also hide the reason behind a health-check flap.
        # The class, not the message: a YAML parse error quotes the line
        # it choked on, and in this file that line is a student's email.
        # This endpoint answers anyone who can reach it.
        return JSONResponse({"status": "degraded", "courses": None,
                             "courses_error": type(e.__cause__ or e).__name__,
                             "bao": bao})
    return JSONResponse({"status": "ok", "courses": len(data["courses"]), "bao": bao})


if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=8080)
