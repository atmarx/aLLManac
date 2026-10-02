"""Course state — registrar/courses.yaml, read/normalize/validate/write.

The operator's file AND the file-backend roster truth.  The only plane
that makes no network call and holds no credential: everything here is
this process, that file, and a schema opinion.
"""

import os
import re
import tempfile
from datetime import date, timedelta

import yaml

from .config import (
    DEFAULT_CONTEXT_TOKENS,
    BASE_MODELS,
    COURSES_PATH,
    DEFAULT_CAPABILITIES,
    DEFAULT_COURSE_BUDGET,
    DEFAULT_FUSE,
    EMAILISH_RE,
    EXPORT_WINDOW_DAYS,
    KNOWN_CAPABILITIES,
    MAX_FUSE,
    SLUG_RE,
    ALMANAC_DOMAIN,
    CHAT_HOST,
)


class CoursesError(Exception):
    """registrar/courses.yaml could not be read as course records.

    This is deliberately fatal rather than a degrade-to-empty.  The file is
    the authority for enrollment, budgets, and every door role: an empty
    course set doesn't mean "no courses," it means "we can't see the
    courses," and the two look identical to every caller downstream.
    """


# Writes are atomic (tmp + rename) — courses.yaml is bind-mounted as a
# directory-relative path precisely so renames are visible.

_CONTROL = re.compile(r"[\x00-\x1f\x7f]")


def clean_name(s) -> str:
    """A course name as every render may safely carry it: one line, no
    control characters.  Names now arrive from chat — a requester types
    one, an admin approves it — and the name lands in the instance's .env
    (APP_TITLE, COURSE_NAME) and its librechat.yaml.  A newline there is a
    line of config nobody wrote on purpose (2026-09-23 sweep)."""
    return " ".join(_CONTROL.sub(" ", str(s)).split())


def slug_error(slug: str) -> str | None:
    """Why `slug` can't be a course id, or None.  One check for both the
    file validator and every path that creates a course — chat included,
    which used to check the pattern and nothing else."""
    if not SLUG_RE.match(slug):
        return (f"'{slug}' must be lowercase letters, digits and hyphens, "
                "starting and ending with a letter or digit (it becomes the "
                f"hostname {slug}.{ALMANAC_DOMAIN}, the container names, and "
                "the Keycloak clientId)")
    if slug.endswith("-admin"):
        # Every course renders TWO vhosts: <slug> and <slug>-admin (the
        # panel).  So a course actually named "<x>-admin" claims the
        # hostname x's panel already answers on — two site blocks, one
        # name, in two different generated files.  Cheap to refuse, and
        # expensive to find once it is baked into a SAN certificate.
        return (f"a slug ending in '-admin' collides with the panel hostname "
                f"of course {slug[:-6]!r} — both render {slug}.{ALMANAC_DOMAIN}")
    return None


def deployment_error() -> str | None:
    """Deployment, not roster — but every mutating verb must pass it.
    `just deploy` append-migrates a NAMED list of .env vars, and
    ALMANAC_DOMAIN isn't on it (it has no sane universal default), so an
    older box can be serving a real CHAT_HOST while the fleet domain
    silently fell back to localhost: every course would render at
    <slug>.localhost, the OIDC client would get a localhost redirect URI,
    and the registrar would report success.  Refuse instead."""
    if ALMANAC_DOMAIN == "localhost" and not (
            CHAT_HOST == "localhost" or CHAT_HOST.endswith(".localhost")):
        return (f"ALMANAC_DOMAIN is unset (defaulting to localhost) but "
                f"CHAT_HOST is {CHAT_HOST!r} — courses would render at "
                "<slug>.localhost on a box that isn't one.  Set ALMANAC_DOMAIN "
                "in .env (usually the part of CHAT_HOST after 'chat.') and "
                "restart the registrar.")
    return None


def load_raw_courses() -> dict:
    """The file as YAML gave it to us — no normalization, no defaults.

    Missing file is legitimately empty (a fresh box before the first
    `just up` seeds it).  Anything else — a parse error, a top level that
    isn't a mapping — is FATAL: see CoursesError.  This is the seam where
    "bad YAML degrades" used to live, and degrading here meant `_upsert`
    could read an empty course set, add one course, and `save_courses` the
    result straight over every other course's roster.  courses.yaml is
    gitignored (real student emails), so that write had nothing behind it.
    """
    try:
        with open(COURSES_PATH) as f:
            raw = yaml.safe_load(f)
    except OSError:
        return {}
    except yaml.YAMLError as e:
        raise CoursesError(
            f"{COURSES_PATH} is not valid YAML — refusing to proceed with an "
            f"empty course set.  Fix the file (or restore it) and try again.\n"
            f"  {e}"
        ) from e
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise CoursesError(
            f"{COURSES_PATH} must be a mapping with `courses:` at the top "
            f"level — got {type(raw).__name__}."
        )
    for key, want in (("courses", dict), ("colleges", dict), ("admins", list),
                      ("devs", list)):
        val = raw.get(key)
        if val is not None and not isinstance(val, want):
            raise CoursesError(
                f"{COURSES_PATH}: `{key}:` must be a {want.__name__}, "
                f"got {type(val).__name__}."
            )
    return raw


def _int_or(v, default: int) -> int:
    """Loading is best-effort on a field's TYPE; `validate_courses` is what
    reports a bad one.  A garbage value must not turn `just course-check`
    into a traceback — the operator needs the sentence that names the course
    and the key, which validate already prints, and a crash on the way to
    printing it is how they lose it.
    """
    if v is None:
        return default
    try:
        return int(v)
    except (TypeError, ValueError):
        return default



def _money_or_zero(v, default: float) -> float:
    """Same best-effort loading as `_int_or`, but a bad value fails CLOSED.

    `_int_or` falls back to its default because a wrong context window only
    shortens a conversation.  Money is the other way round: silently
    substituting DEFAULT_COURSE_BUDGET for a typo would hand a course a
    spending limit nobody wrote, and the symptom would be an absence — the
    same failure as a model that meters at $0.  So a value we cannot read
    becomes 0, which is loud, harmless, and already has a sentence in
    `validate_courses`: "that course spends nothing until it's raised."

    A missing key is not a bad value and still takes the default; this only
    fires on something present and unreadable.
    """
    if v is None:
        return default
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def load_courses() -> dict:
    raw = load_raw_courses()
    out = {
        # Keys lowercased like each course's `college:` is below — else
        # `colleges: {CCI: …}` passes validate and the pack never applies.
        "courses": {}, "colleges": {str(k).strip().lower(): v for k, v in
                                    (raw.get("colleges") or {}).items()},
        "admins": [str(e).strip().lower() for e in (raw.get("admins") or [])],
        # Platform devs — the report queue, and nothing else.  Deliberately
        # NOT admins: a report is something a person CHOSE to send you; the
        # fleet view is everyone who chose nothing.  See registrar-spec.md,
        # "Reports".  Admins are devs implicitly (they already see more).
        "devs": [str(e).strip().lower() for e in (raw.get("devs") or [])],
    }
    for slug, c in (raw.get("courses") or {}).items():
        c = c or {}
        budgets = c.get("budgets") or {}
        out["courses"][str(slug).strip().lower()] = {
            "name": clean_name(c.get("name") or slug),
            "instructors": [str(e).strip().lower() for e in (c.get("instructors") or [])],
            "tas": [str(e).strip().lower() for e in (c.get("tas") or [])],
            # Bare float() here turned a typo in ANY course's budget into a
            # traceback out of load_courses — including on the way to printing
            # the validate errors that name it, so the operator lost the one
            # sentence that said which course and which key.
            "budgets": {
                "course": _money_or_zero(budgets.get("course"), DEFAULT_COURSE_BUDGET),
                "key_fuse": min(_money_or_zero(budgets.get("key_fuse"), DEFAULT_FUSE),
                                MAX_FUSE),
                "advisory_weekly": _money_or_zero(budgets.get("advisory_weekly"), 2),
            },
            "college": (str(c.get("college")).strip().lower()
                        if c.get("college") else None),
            "models": list(c.get("models") or BASE_MODELS),
            # What one conversation may grow to before LibreChat trims it.
            # Per course because the answer is per MODEL, and only the
            # operator knows what `models:` actually resolves to here.
            "context_tokens": _int_or(c.get("context_tokens"),
                                      DEFAULT_CONTEXT_TOKENS),
            # Agent capabilities: `actions` (arbitrary-URL tool calls) is
            # deliberately NOT in the default — it's the one path around the
            # gateway (spec: "The floor").  Enable per course, eyes open.
            # `or` is wrong here on purpose-of-omission: an explicit empty
            # list means "this course gets none," and collapsing it to the
            # default would fail OPEN on the one knob where that matters.
            "capabilities": (list(DEFAULT_CAPABILITIES)
                             if c.get("capabilities") is None
                             else [str(x).strip() for x in c["capabilities"]]),
            # Where this course's agent Actions may reach.  Renders to
            # LibreChat's TOP-LEVEL `actions.allowedDomains` — the last plank
            # of the spec's "The floor" remedy.  Empty = no allowlist, which
            # in LibreChat means the whole public internet (private IPs stay
            # SSRF-blocked either way); the validator says so out loud when a
            # course has `actions` and no list.
            "allowed_domains": [str(x).strip() for x in (c.get("allowed_domains") or [])
                                if str(x).strip()],
            # Where MCP servers staff add in this course's chat may connect.
            # Renders into mcpSettings.allowedDomains AFTER the platform's own
            # two hosts, so an empty list here is closed, not open — unlike
            # allowed_domains, the render always has something to put first
            # (design-walls.md, "MCP servers staff add").
            "mcp_domains": [str(x).strip().lower() for x in (c.get("mcp_domains") or [])
                            if str(x).strip()],
            "group": str(c.get("group") or ""),
            "students": [str(e).strip().lower() for e in (c.get("students") or [])],
            "aliases": {str(k).strip().lower(): [str(a).strip().lower() for a in (v or [])]
                        for k, v in (c.get("aliases") or {}).items()},
            # The term lifecycle (registrar-spec.md, "The term").  `address`
            # is the stable name that redirects to whichever term claims it;
            # `closed`/`archived` are the dates course-close and
            # course-archive stamp.  NOT `aliases:` above — that one is usage
            # attribution for legacy user_ids, and predates this.
            "address": (str(c.get("address")).strip().lower() or None
                        if c.get("address") else None),
            "closed": _stamp(c.get("closed")),
            "archived": _stamp(c.get("archived")),
        }
    return out


def _stamp(v) -> str | None:
    """A lifecycle date as the file should carry it.  YAML hands back an
    unquoted 2026-12-18 as a date and a quoted one as a str; both become the
    ISO string.  A value that isn't a date is KEPT, not dropped: dropping a
    typo'd `closed:` would quietly reopen the course, which is the one
    direction this field must never fail.  `validate` names it instead."""
    if v is None or v == "":
        return None
    return v.isoformat() if isinstance(v, date) else str(v).strip()


class CourseClosed(Exception):
    """A write aimed at a closed or archived course.  The message is written
    for whoever asked — the tool plane hands it over as-is."""


def open_or_raise(slug: str, course: dict) -> None:
    """Every write verb's first line on an existing course.  A closed course
    is frozen, not broken, and the refusal says which and until when."""
    state = course_state(course)
    if state == "archived":
        raise CourseClosed(
            f"{slug} was archived on {course['archived']} — it is a finished "
            f"term's record, and nothing about it changes.  Next term is a new "
            f"course (a new id, the same `address:`).")
    if state == "closed":
        ends = window_ends(course)
        until = (f"; its students can export their conversations until "
                 f"{ends.isoformat()}" if ends else "")
        raise CourseClosed(
            f"{slug} closed on {course['closed']}{until}.  A closed course is "
            f"frozen — no roster, staff, budget or key changes.  If closing it "
            f"was a mistake, the operator can undo it: `just course-reopen {slug}`.")


def course_state(course: dict) -> str:
    """open | closed | archived — archived wins, because an archived course
    is also closed and the stronger fact is the one every caller needs."""
    if course.get("archived"):
        return "archived"
    return "closed" if course.get("closed") else "open"


def window_ends(course: dict) -> date | None:
    """The last day of a closed course's export window, or None when the
    close date can't be read.  None means "not over": the one caller that
    acts on it (archive) then asks for --force instead of guessing."""
    try:
        return date.fromisoformat(course["closed"]) + timedelta(days=EXPORT_WINDOW_DAYS)
    except (KeyError, TypeError, ValueError):
        return None


def address_map(data: dict) -> dict[str, str]:
    """{address: slug} — who each stable address points at today.

    An OPEN claimant wins; with none, a CLOSED course keeps its address
    through the export window (its students still need the way in); an
    ARCHIVED claim is history.  Two claimants of the same standing get no
    redirect at all — a guess here sends a class to the wrong term, and
    `validate` names the pair.  An address that is also a course slug is
    skipped for the same reason: both would render one hostname."""
    claims: dict[str, dict[str, list[str]]] = {}
    for slug, c in data["courses"].items():
        a, state = c.get("address"), course_state(c)
        if a and state != "archived":
            claims.setdefault(a, {}).setdefault(state, []).append(slug)
    out: dict[str, str] = {}
    for a, by in sorted(claims.items()):
        if a in data["courses"] or f"{a}-admin" in data["courses"]:
            continue
        for state in ("open", "closed"):
            if by.get(state):
                if len(by[state]) == 1:
                    out[a] = by[state][0]
                break
    return out


def name_taken(slug: str, data: dict) -> str | None:
    """Why a NEW course can't take `slug`, beyond its shape: the name is a
    course already (any state — a closed course holds its slug forever, or
    next term reopens last term's database), or some course's `address:`.
    Addresses and slugs share one namespace because both are hostnames."""
    if slug in data["courses"]:
        c = data["courses"][slug]
        if course_state(c) != "open":
            return (f"'{slug}' was a course that is now {course_state(c)} — a slug "
                    f"is never reused, because it names that term's database.  "
                    f"Name the new term (e.g. engr301-2027fall) and give both the same "
                    f"`address:`")
        return f"'{slug}' is already a course"
    for other, c in data["courses"].items():
        if c.get("address") == slug:
            return (f"'{slug}' is the stable address of {other} — addresses and "
                    f"slugs are both hostnames, so one name can't be both")
    return None


def save_courses(data: dict) -> None:
    # Note the round trip: this writes the NORMALIZED record, so a course
    # touched by any write verb gains explicit `capabilities:` and
    # `allowed_domains:` keys.  That pins it to the defaults in force at
    # that moment — a later change to DEFAULT_CAPABILITIES will not reach
    # it.  That's the behavior we want (a registrar upgrade must not
    # silently widen a course's powers), but it is a surprise if you expect
    # otherwise.
    d = os.path.dirname(COURSES_PATH) or "."
    # The lifecycle keys are written only when set, so an open course with
    # no address reads the way the operator typed it — not as three nulls.
    data = {**data, "courses": {
        slug: {k: v for k, v in c.items()
               if not (k in ("address", "closed", "archived") and v is None)}
        for slug, c in data["courses"].items()}}
    fd, tmp = tempfile.mkstemp(dir=d, prefix=".courses.")
    try:
        with os.fdopen(fd, "w") as f:
            # The file is written NORMALIZED — ruled 2026-09-23 (@xram): a
            # round-trip that preserved comments and unknown keys isn't worth
            # its code, as long as the file says so where the operator looks.
            f.write("# The registrar's course records — see docs/registrar-spec.md.\n"
                    "# REWRITTEN BY THE REGISTRAR on every change it makes (enroll,\n"
                    "# approve, staff, budget), in normalized form.  Hand edits to\n"
                    "# known keys are kept; COMMENTS AND UNRECOGNIZED KEYS ARE\n"
                    "# DISCARDED at the next write.  Check a hand edit with\n"
                    "# `just course-check`.  Gitignored: real rosters are student emails.\n")
            yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True)
        os.chmod(tmp, 0o644)
        os.replace(tmp, COURSES_PATH)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


# ---- validation: the check `load_courses` used to claim existed ---------------
# Two severities, and the split is the whole point.  ERRORS are things that
# will half-provision or render a broken instance — a slug that can't be a
# hostname, a budget that isn't a number.  WARNINGS are things that are
# legal, load fine, and are almost certainly not what the operator meant: a
# capability typo (fails closed, silently), a college that doesn't exist (the
# model pack silently doesn't union), `actions` with no allowlist.  Warnings
# never block, because the registrar is not the authority on any of them —
# it's just the only thing in the room that noticed.

def validate_courses() -> tuple[list[str], list[str]]:
    """-> (errors, warnings), both human-readable.  Raises CoursesError if
    the file can't be parsed at all — that's not a finding, that's a wall."""
    raw = load_raw_courses()
    errors: list[str] = []
    warnings: list[str] = []
    colleges = raw.get("colleges") or {}
    courses = raw.get("courses") or {}

    if (e := deployment_error()):
        errors.append(e)

    for e in (raw.get("admins") or []):
        if not EMAILISH_RE.match(str(e).strip()):
            warnings.append(f"admins: {e!r} doesn't look like an email address")

    for e in (raw.get("devs") or []):
        if not EMAILISH_RE.match(str(e).strip()):
            warnings.append(f"devs: {e!r} doesn't look like an email address")
    both = (set(str(e).strip().lower() for e in (raw.get("devs") or []))
            & set(str(e).strip().lower() for e in (raw.get("admins") or [])))
    for e in sorted(both):
        # Harmless, but it reads as though the dev list is doing something
        # for them, and the day someone is removed from admins: expecting
        # that to take their fleet access away, it won't say so anywhere.
        warnings.append(f"devs: {e!r} is already an admin — admins triage "
                        f"reports implicitly, so this line grants nothing")

    for slug, c in courses.items():
        slug = str(slug)
        where = f"courses.{slug}"
        if (e := slug_error(slug)):
            errors.append(f"{where}: {e}")
        if c is None:
            errors.append(f"{where}: empty record — needs at least name + instructors")
            continue
        if not isinstance(c, dict):
            errors.append(f"{where}: must be a mapping, got {type(c).__name__}")
            continue

        if not str(c.get("name") or "").strip():
            warnings.append(f"{where}: no name — the slug will be shown to students instead")

        instructors = [str(e).strip().lower() for e in (c.get("instructors") or [])]
        tas = [str(e).strip().lower() for e in (c.get("tas") or [])]
        students = [str(e).strip().lower() for e in (c.get("students") or [])]
        if not instructors:
            errors.append(f"{where}: no instructors — nobody could run the roster tools")
        for label, lst in (("instructors", instructors), ("tas", tas), ("students", students)):
            for e in lst:
                if not EMAILISH_RE.match(e):
                    errors.append(f"{where}.{label}: {e!r} isn't an email address — "
                                  "sign-in emails are what the roster matches on")
            dupes = sorted({e for e in lst if lst.count(e) > 1})
            if dupes:
                warnings.append(f"{where}.{label}: listed twice — {', '.join(dupes)}")
        both = sorted(set(instructors + tas) & set(students))
        if both:
            warnings.append(
                f"{where}: also listed as students — {', '.join(both)}.  Staff are "
                "skipped by the roster tools, so these get no student key")

        if c.get("context_tokens") is not None:
            try:
                ctx = int(c["context_tokens"])
            except (TypeError, ValueError):
                errors.append(f"{where}.context_tokens: {c['context_tokens']!r} "
                              f"isn't a whole number of tokens")
            else:
                if ctx <= 0:
                    errors.append(f"{where}.context_tokens: {ctx} — a course with "
                                  f"no context window cannot hold a conversation")
                elif ctx < 4000:
                    warnings.append(f"{where}.context_tokens is {ctx} — very small; "
                                    f"conversations will be trimmed almost at once")
                elif ctx > 200000:
                    # Too HIGH is the dangerous direction, and the danger is
                    # that it is QUIET.  Ollama truncates the front of an
                    # over-long prompt and answers anyway — and the front is
                    # the system prompt.
                    warnings.append(f"{where}.context_tokens is {ctx} — larger than "
                                    f"anything we serve.  If the endpoint serves "
                                    f"less, the front of the prompt (the agent's "
                                    f"instructions) is silently dropped, not "
                                    f"refused")

        budgets = c.get("budgets") or {}
        if not isinstance(budgets, dict):
            errors.append(f"{where}.budgets: must be a mapping, got {type(budgets).__name__}")
        else:
            for k, default in (("course", DEFAULT_COURSE_BUDGET),
                               ("key_fuse", DEFAULT_FUSE),
                               ("advisory_weekly", 2)):
                try:
                    v = float(budgets.get(k, default))
                except (TypeError, ValueError):
                    errors.append(f"{where}.budgets.{k}: {budgets.get(k)!r} isn't a number")
                    continue
                if v <= 0:
                    warnings.append(f"{where}.budgets.{k} is {v:g} — that course "
                                    "spends nothing until it's raised")
                if k == "key_fuse" and v > MAX_FUSE:
                    warnings.append(f"{where}.budgets.key_fuse {v:g} exceeds the "
                                    f"registrar's ceiling — it is CLAMPED to {MAX_FUSE:g}")

        college = c.get("college")
        if college and str(college).strip().lower() not in {str(k).lower() for k in colleges}:
            warnings.append(
                f"{where}.college: {college!r} isn't in `colleges:` — the model "
                "pack silently doesn't union, so this course gets base models only")

        if not (c.get("models") or BASE_MODELS):
            errors.append(f"{where}.models: empty — the instance would have no model to call")

        caps = c.get("capabilities")
        caps = DEFAULT_CAPABILITIES if caps is None else [str(x).strip() for x in caps]
        unknown = [x for x in caps if x and x not in KNOWN_CAPABILITIES]
        if unknown:
            warnings.append(
                f"{where}.capabilities: {', '.join(repr(u) for u in unknown)} not "
                f"recognized on this LibreChat pin — a typo fails CLOSED and "
                f"silently, so the power you meant to grant simply won't appear.  "
                f"Known: {', '.join(KNOWN_CAPABILITIES)}")
        domains = [str(x).strip() for x in (c.get("allowed_domains") or []) if str(x).strip()]
        if "actions" in caps and not domains:
            warnings.append(
                f"{where}: `actions` is enabled with no `allowed_domains:` — agent "
                "Actions may call ANY public URL, which is the documented path "
                "around the gateway's metering (spec: \"The floor\").  Add the "
                "domains this course actually needs")
        if domains and "actions" not in caps:
            warnings.append(f"{where}.allowed_domains: set, but `actions` isn't in "
                            "capabilities — the list is inert until it is")
        for d in domains:
            if "/" in d.replace("://", "", 1) or " " in d:
                errors.append(f"{where}.allowed_domains: {d!r} — hostnames (optionally "
                              "with scheme/port or a leading *.), not URL paths")
        # An mcp_domains entry does more than permit: listing a host also lifts
        # LibreChat's private-address block for it (measured on 0.8.7,
        # 2026-10-02).  So only public DNS names belong here — never an IP
        # literal, a bare container name, or localhost, any of which would
        # point an instructor's tool server into the platform's own network.
        for d in [str(x).strip().lower() for x in (c.get("mcp_domains") or []) if str(x).strip()]:
            host = d.split("://", 1)[-1].split(":", 1)[0].removeprefix("*.")
            if "/" in d.replace("://", "", 1) or " " in d:
                errors.append(f"{where}.mcp_domains: {d!r} — hostnames (optionally "
                              "with scheme/port or a leading *.), not URL paths")
            elif ("." not in host or host == "localhost" or host.endswith(".localhost")
                  or host.replace(".", "").isdigit() or ":" in host):
                errors.append(f"{where}.mcp_domains: {d!r} — a public DNS name only.  "
                              "Listing a host lifts LibreChat's private-address block "
                              "for it, so an IP, a container name or localhost here "
                              "would open the platform's own network to tool servers")

        rec = {"closed": _stamp(c.get("closed")), "archived": _stamp(c.get("archived"))}
        for k in ("closed", "archived"):
            if rec[k]:
                try:
                    date.fromisoformat(rec[k])
                except ValueError:
                    errors.append(f"{where}.{k}: {rec[k]!r} isn't a date (YYYY-MM-DD) — "
                                  f"the course is treated as {k} anyway, since reading "
                                  f"it as open is the direction that can't be undone")
        if rec["archived"] and not rec["closed"]:
            warnings.append(f"{where}: archived but never closed — nothing is wrong "
                            "with the course, but its record skips a step")
        if rec["closed"] and not rec["archived"]:
            ends = window_ends(rec)
            if ends and date.today() > ends:
                warnings.append(f"{where}: closed {rec['closed']}; its export window "
                                f"ended {ends.isoformat()} — `just course-archive "
                                f"{slug}` takes it down")
        if c.get("address"):
            a = str(c["address"]).strip().lower()
            if (e := slug_error(a)):
                errors.append(f"{where}.address: {e.replace('slug', 'address')}")
            elif a in {str(s) for s in courses} or f"{a}-admin" in {str(s) for s in courses}:
                errors.append(f"{where}.address: {a!r} is also a course slug — both "
                              "would render the same hostname, so neither redirects")

    # One address, one live claimant — per standing, as address_map decides.
    claims: dict[tuple[str, str], list[str]] = {}
    for slug, c in courses.items():
        if isinstance(c, dict) and c.get("address") and not c.get("archived"):
            state = "closed" if c.get("closed") else "open"
            claims.setdefault((str(c["address"]).strip().lower(), state), []).append(str(slug))
    for (a, state), slugs in sorted(claims.items()):
        # Two closed claimants only matter while no open course outranks them.
        if len(slugs) > 1 and not (state == "closed" and (a, "open") in claims):
            errors.append(f"address {a!r}: claimed by {len(slugs)} {state} courses "
                          f"({', '.join(sorted(slugs))}) — it redirects nowhere until "
                          "one of them lets go")

    return errors, warnings


def course_models(course: dict, courses: dict) -> list[str]:
    """The course's model list ∪ its college's model pack."""
    models = list(course.get("models") or BASE_MODELS)
    college = course.get("college")
    if college:
        pack = (courses.get("colleges") or {}).get(college) or {}
        for m in pack.get("models") or []:
            if m not in models:
                models.append(m)
    return models
