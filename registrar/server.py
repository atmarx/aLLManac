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

# mask_error_details: fastmcp defaults it to False, which puts the text of
# any UNHANDLED exception into the tool response — and a tool response is
# read by a student.  Every message in this file that is meant for a human
# is a ToolError, and ToolError is exempt from masking.  So this flag
# costs us nothing and stops `asyncpg.InvalidPasswordError: ... usage_ro`
# and friends from being answers.
mcp = FastMCP("almanac-registrar", mask_error_details=True)


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
    """(email, role, course-or-empty) — for the ONE tool that also serves the
    vestibule.

    Every other tool in this file calls `_ident()`, which refuses without an
    X-Course header.  That refusal is why wiring this service into the
    flagship costs nothing: the vestibule renders no X-Course, so thirteen
    course tools go on refusing there without a line of policy — the shape
    already says it.  A tool that opts out of that has to say so in its own
    name, which is what this function is for.

    The token check and the who-is-asking check are unchanged; only the
    course becomes optional, and the caller must then work out routing from
    the roster instead (reconcile.file_report).
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


def _staff_or_refuse(email: str, course: dict, slug: str) -> None:
    """Instructors and TAs — the courses.yaml lists ARE the authority (the
    file-backend equivalent of the managed group's manager role)."""
    if email not in course.get("instructors", []) and email not in course.get("tas", []):
        raise ToolError(
            f"Roster operations are for the teaching staff of {slug}.  Your "
            "own key and usage are always available — ask for my_key or "
            "my_usage."
        )


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
            "The fleet view is for platform admins (the `admins:` list in "
            "registrar/courses.yaml).  Course staff: roster_show and "
            "course_usage cover your own course."
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
    if not _on_roster(email, course):
        raise ToolError(f"No key to rotate — you're not on the {slug} roster.")
    try:
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
    email, _role, _slug = _ident()
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
    email, _role, _slug = _ident()
    _admin_or_refuse(email)
    slug = course.strip().lower()
    _course_or_refuse(slug)
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
    email, _role, _slug = _ident()
    _admin_or_refuse(email)
    slug = course.strip().lower()
    _course_or_refuse(slug)
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
    email, _role, slug = _ident()
    courses = _courses_or_refuse()
    if email in courses["admins"]:
        rows = reconcile.nominations()
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
    email, _role, _slug = _ident()
    _admin_or_refuse(email)
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
    email, _role, _slug = _ident()
    _admin_or_refuse(email)
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
    if email in courses["admins"]:
        rows = reconcile.reports(status=want)
    else:
        if not slug:
            raise ToolError(
                "Reading the report pile is a faculty view of one course, so "
                "it only works from inside that course's chat.  Filing a "
                "report works anywhere — that's report_problem."
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
        return JSONResponse({"status": "degraded", "courses": None,
                             "courses_error": str(e), "bao": bao})
    return JSONResponse({"status": "ok", "courses": len(data["courses"]), "bao": bao})


if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=8080)
