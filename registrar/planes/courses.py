"""Course state — registrar/courses.yaml, read/normalize/validate/write.

The operator's file AND the file-backend roster truth.  The only plane
that makes no network call and holds no credential: everything here is
this process, that file, and a schema opinion.
"""

import os
import tempfile

import yaml

from .config import (
    BASE_MODELS,
    COURSES_PATH,
    DEFAULT_CAPABILITIES,
    DEFAULT_COURSE_BUDGET,
    DEFAULT_FUSE,
    EMAILISH_RE,
    KNOWN_CAPABILITIES,
    MAX_FUSE,
    SLUG_RE,
    ALMANAC_DOMAIN,
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

_EMPTY = {"courses": {}, "colleges": {}, "admins": []}


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
    for key, want in (("courses", dict), ("colleges", dict), ("admins", list)):
        val = raw.get(key)
        if val is not None and not isinstance(val, want):
            raise CoursesError(
                f"{COURSES_PATH}: `{key}:` must be a {want.__name__}, "
                f"got {type(val).__name__}."
            )
    return raw


def load_courses() -> dict:
    raw = load_raw_courses()
    out = {
        "courses": {}, "colleges": raw.get("colleges") or {},
        "admins": [str(e).strip().lower() for e in (raw.get("admins") or [])],
    }
    for slug, c in (raw.get("courses") or {}).items():
        c = c or {}
        budgets = c.get("budgets") or {}
        out["courses"][str(slug).strip().lower()] = {
            "name": str(c.get("name") or slug),
            "instructors": [str(e).strip().lower() for e in (c.get("instructors") or [])],
            "tas": [str(e).strip().lower() for e in (c.get("tas") or [])],
            "budgets": {
                "course": float(budgets.get("course", DEFAULT_COURSE_BUDGET)),
                "key_fuse": min(float(budgets.get("key_fuse", DEFAULT_FUSE)), MAX_FUSE),
                "advisory_weekly": float(budgets.get("advisory_weekly", 2)),
            },
            "college": (str(c.get("college")).strip().lower()
                        if c.get("college") else None),
            "models": list(c.get("models") or BASE_MODELS),
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
            "group": str(c.get("group") or ""),
            "students": [str(e).strip().lower() for e in (c.get("students") or [])],
            "aliases": {str(k).strip().lower(): [str(a).strip().lower() for a in (v or [])]
                        for k, v in (c.get("aliases") or {}).items()},
        }
    return out


def save_courses(data: dict) -> None:
    # Note the round trip: this writes the NORMALIZED record, so a course
    # touched by any write verb gains explicit `capabilities:` and
    # `allowed_domains:` keys.  That pins it to the defaults in force at
    # that moment — a later change to DEFAULT_CAPABILITIES will not reach
    # it.  That's the behavior we want (a registrar upgrade must not
    # silently widen a course's powers), but it is a surprise if you expect
    # otherwise.
    d = os.path.dirname(COURSES_PATH) or "."
    fd, tmp = tempfile.mkstemp(dir=d, prefix=".courses.")
    try:
        with os.fdopen(fd, "w") as f:
            f.write("# The registrar's course records — see docs/registrar-spec.md.\n"
                    "# Operator-edited AND registrar-maintained (students, group ids).\n"
                    "# Gitignored: real rosters are student emails.\n")
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

    for e in (raw.get("admins") or []):
        if not EMAILISH_RE.match(str(e).strip()):
            warnings.append(f"admins: {e!r} doesn't look like an email address")

    for slug, c in courses.items():
        slug = str(slug)
        where = f"courses.{slug}"
        if not SLUG_RE.match(slug):
            errors.append(
                f"{where}: slug must be lowercase letters, digits and hyphens "
                f"(it becomes the hostname {slug}.{ALMANAC_DOMAIN}, the "
                f"container names, and the Keycloak clientId)")
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
