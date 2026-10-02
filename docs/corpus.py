#!/usr/bin/env python3
"""Render the per-audience RAG corpora from front matter.

A guide is a QUERY, not a directory — see docs/audience-projection.md.  This
script is the query, and `corpus/` is its render: never edited, never
committed, regenerable from the tree at any time.

The vocabulary this reads (`audience`, `also_reaches`, `status`, `tags`,
`tethered_to`) is declared in docs/pedagogy-authoring.md.  That file is the
authority; if the two disagree, the schema is right and this script is wrong.
"""
import os
import pathlib
import re
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "corpus"

# The agent's own instructions are not part of the agent's knowledge — it is
# told them, it does not look them up.  Read specially, excluded from every
# corpus, and never a page.
CONTRACT = ROOT / "docs" / "agent-contract.md"

# What each guide is FOR.  One line, appended to the shared preamble — the
# only per-guide text in the prompt, so the guides differ in scope and in
# nothing else.
SCOPE = {
    "student-guide":
        "You are the Student Guide: using {{PLATFORM}} in your courses — "
        "signing in, building agents, knowledge files, API keys, and what "
        "the budget numbers mean.  Asked which courses they are on, call "
        "my_courses and read back what it says.  A student can ask for a "
        "project or club room with course_request: it first returns a "
        "question that you put to them in its own words, and you file only "
        "if they say yes.  Never ask them for a budget; the admins set it.  "
        "my_requests shows where a request stands and what the admins wrote "
        "back; if it was returned, course_request_reply answers them.",
    "instructor-guide":
        "You are the Instructor Guide: running a course on {{PLATFORM}} — "
        "enrollment, class configuration, shared agents, what students can "
        "see, and what you are responsible for.  You can manage enrollment "
        "for a course the person teaches: who may sign in to its chat and "
        "hold a key.  Always in two steps.  Stage it — enroll or unenroll "
        "for a few people, roster_stage for a whole class list, which "
        "removes anyone it leaves out — then show them the staged change "
        "exactly as it came back and call roster_apply only after they say "
        "yes to that change.  Never stage and apply in one turn.  If you do "
        "not know the course, call my_courses first.  Who teaches a course "
        "is not something you can change; the platform operator sets it.  "
        "Anyone can ask for a new course with course_request: it first "
        "returns a question that you put to them in its own words, and you "
        "file only if they say yes.  Never ask them for a budget; the admins "
        "set it.  The admins approve it, return it with questions, or turn "
        "it down with a reason; my_requests shows which, with their notes "
        "and, once approved, the new chat's address.  A returned request is "
        "answered with course_request_reply, not filed again.",
    "platform-guide":
        "You are the Platform Guide: how {{PLATFORM}} is built and why — "
        "the architecture, the decisions, and the trade-offs they cost.",
    "dev-guide":
        "You are the Dev Guide: operating {{PLATFORM}} — deployment, "
        "runbooks, verification, and what breaks.  You are also the "
        "operator's desk: the request tickets — approve with a budget, "
        "return with questions, or reject with a reason — creating courses, "
        "changing who teaches them and their pools.  Those tools answer "
        "platform admins only and refuse anyone "
        "else, and every one that changes something first describes the "
        "change.  Call it without confirm, show them the description as it "
        "came back, and call it again with confirm=true only after they say "
        "yes to that description — never in the same turn.",
    "security-guide":
        "You are the Security Guide: {{PLATFORM}}'s security posture — the "
        "controls, the boundaries, and the blue-team and purple-team "
        "exercises that test them.",
    "usage-guide":
        "You are the Usage Guide: what the numbers mean — tokens, context, "
        "what actually moves a bill, and how to read your own usage.  You "
        "explain; you never grade.  Every figure you state came back from a "
        "tool call verbatim, and you do no arithmetic on those figures — a "
        "number you computed is a number the reader cannot check.",
    "coder-guide":
        "You are the Coder Guide: building with code — API keys, the "
        "gateway, coding harnesses, and what limits code that does not "
        "limit chat.  You cannot fetch or rotate a key from here: keys "
        "belong to courses, so `my_key` and `rotate_my_key` are asked for "
        "in the person's own course chat, and you say so — my_courses "
        "gives the address of each chat they have.  Never ask for, "
        "repeat, or accept a key pasted into this conversation.  Asked "
        "which harness to use, you never answer with a name alone: the "
        "answer is a pairing of model and harness for a goal, and you ask "
        "for the goal.",
}

# The directory of guides, rendered into BOTH the shared preamble (as the
# first escape hatch) and the front desk's own fence.  One authority on
# purpose: a guide that names a sibling guide wrongly is a redirect that
# points nowhere, which is the failure the hatch list exists to prevent.
# Routing lines, not SCOPE's agent-voice lines — the reader is choosing.
DIRECTORY = """\
      Student Guide      using {{PLATFORM}} in a course you are taking
      Instructor Guide   running a course on it — enrollment, class setup,
                         shared agents, and asking for a new course
      Platform Guide     how {{PLATFORM}} is built, and why
      Dev Guide          deploying and operating it, and the operator's
                         desk for courses and requests
      Security Guide     the security posture, and the exercises that test it
      Usage Guide        what the numbers mean — tokens, context, and cost
      Coder Guide        API keys, the gateway, and coding harnesses\
"""

# Deployment config, not code: a different institution names a different
# fallback (docs/registrar-spec.md, Decision 18 — boundary verbiage is
# config).  Generic default so tracked files name no institution.
# What the readers call this platform.  Every reader-facing source says
# {{PLATFORM}} rather than a name, and this fills it — the same way for the
# project's own deployment as for an institution's, so no name is the special
# case.  DOCS_PRODUCT_NAME is the older, site-only spelling of the same knob.
PLATFORM = (os.environ.get("PLATFORM_NAME") or os.environ.get("DOCS_PRODUCT_NAME")
            or "aLLManac").strip()

# The chat model's public name, which a student types into a harness config.
# CHAT_MODEL names it at the gateway (litellm/config.yaml), so the pages say
# {{MODEL}} and get the name this deployment actually serves.
MODEL = os.environ.get("CHAT_MODEL", "almanac-chat").strip()

# A name written into a reader-facing source is a name every deployment's
# guides recite, so it is a build error, not a style note.  So is the default
# model name, and the old ALMANAC_* variable names pages once told students to
# export.  Other hyphenated, dotted and slashed forms are operator identifiers
# (`almanac/courses`, `almanac.invalid`, `almanac-declined`) and stay.
BRAND = re.compile(r"\b(?:aLLManac|[Aa]lmanac)\b(?![-_/]|\.[a-z])"
                   r"|\balmanac-chat\b|\bALMANAC_[A-Z_]+")

FALLBACK = os.environ.get(
    "ALMANAC_FALLBACK_ASSISTANT",
    "the general-purpose assistant your institution already licenses")

# Held back from every corpus.  `scaffold` is unfinished; `proposed` is
# finished but unratified — an agent quoting an unruled rule as policy is the
# specific failure this gate exists to prevent.
WITHHOLD = {"scaffold", "proposed"}

# The four guides are the four declared audience values, finally used.
GUIDES = {
    "student-guide": "student",
    "instructor-guide": "faculty",
    "platform-guide": "builder",
    "dev-guide": "operator",
}

# The Security Guide is a CROSS-CUT, not an audience — it queries tags instead,
# which is what keeps the audience enum from becoming a junk drawer.  These
# are the Controls group plus the architecture tags that describe the
# chokepoint (docs/pedagogy-authoring.md).
SECURITY_TAGS = {
    "access-control", "rbac", "least-privilege", "secrets-management",
    "escrow", "key-rotation", "encryption-at-rest", "encryption-in-transit",
    "audit-logging", "egress-control", "allowlist", "sso", "oidc",
    "identity-broker", "tenancy", "isolation", "multi-tenant", "gateway",
    "chokepoint", "supply-chain",
}
SECURITY_MIN = 3   # below this it's a passing mention, not a security page

# The Usage Guide is the SECOND cross-cut, and it exists for the same reason
# the first one does: "what the numbers mean" is a subject, not an audience,
# and giving it an `audience:` value would put a fifth entry in an enum whose
# whole job is to stay small.  Kept deliberately tight — these are the tags a
# page about tokens, context and cost carries, and nothing else does.
USAGE_TAGS = {
    "metering", "attribution", "context-window", "token-economy",
    "cost-intuition",
}
USAGE_MIN = 3

# The THIRD cross-cut, and the first to use CROSS_CUTS as intended.  Code is
# a subject, not an audience: a student's first script, an instructor
# checking what a harness costs, and a builder reading the gateway contract
# all want the same pages.  The five tags are the "Code and harnesses" group
# in docs/pedagogy-authoring.md.  The threshold is TWO, not the others'
# three, and on purpose: security and usage borrow general tags (`gateway`,
# `metering`) that pages carry in passing, so they need three to mean it.
# None of the five new ones is ever carried in passing — the key page and
# the gateway page are the section's core and each honestly carries two.
#
# `key-rotation` is borrowed from Controls, the one general tag here: using a
# key and replacing one are the same page.  At two it pulls in nothing that
# carries it alone (the vault page, the Course Guide) — checked, not assumed.
CODER_TAGS = {
    "api-key", "openai-compatible", "harness", "agentic-coding",
    "tool-calling", "key-rotation",
}
CODER_MIN = 2

# One place that knows every cross-cut, so adding a third does not mean
# remembering to touch the report at the bottom of this file too.
CROSS_CUTS = {"security-guide": SECURITY_MIN, "usage-guide": USAGE_MIN,
              "coder-guide": CODER_MIN}


def welcome(body: str) -> str:
    """The front desk's prompt — its own fence, not the shared preamble.

    It carries no knowledge files, so the preamble's anchor ("your files are
    the only thing you know") has nothing to point at.  See the "The welcome
    desk" section of docs/agent-contract.md for why that makes it the agent
    most exposed to fabrication rather than least.
    """
    try:
        section = body.split("## The front desk", 1)[1]
        return section.split("```text", 1)[1].split("```", 1)[0].strip()
    except IndexError:
        raise SystemExit(f"{CONTRACT}: no ```text fence under '## The front desk'")


def contract() -> tuple[str, str]:
    """(preamble, evals, body) pulled out of docs/agent-contract.md.

    The prose lives in the doc so the pedagogy lane can edit it without
    touching this file; the parse is deliberately dumb — the first ```text
    fence is the preamble, the "## The evals" section is the eval table.
    If the doc is restructured this raises rather than silently rendering
    an empty prompt, which is the failure worth being loud about.
    """
    text = CONTRACT.read_text()
    body = text.split("---", 2)[2]
    try:
        preamble = body.split("```text", 1)[1].split("```", 1)[0].strip()
    except IndexError:
        raise SystemExit(f"{CONTRACT}: no ```text fence — where is the preamble?")
    if "## The evals" not in body:
        raise SystemExit(f"{CONTRACT}: no '## The evals' section")
    evals = body.split("## The evals", 1)[1].split("\n---", 1)[0].strip()
    return preamble, evals, body


def brand(text: str) -> str:
    return text.replace("{{PLATFORM}}", PLATFORM).replace("{{MODEL}}", MODEL)


def unbranded(label: str, text: str) -> list[str]:
    """Every line of a reader-facing source that names the platform outright."""
    return [f"{label}:{n}: {line.strip()[:80]}"
            for n, line in enumerate(text.splitlines(), 1) if BRAND.search(line)]


def fill(text: str, vocab: str = "") -> str:
    """Deployment + directory + vocabulary substitution.  Loud if a token survives.

    VOCABULARY is per-guide, so this runs once per guide rather than once for
    the shared preamble — which is why contract() hands the preamble back raw.
    """
    text = brand(text.replace("{{FALLBACK_ASSISTANT}}", FALLBACK)
                     .replace("{{GUIDE_DIRECTORY}}", DIRECTORY)
                     .replace("{{VOCABULARY}}", vocab))
    if "{{" in text:
        stray = text[text.index("{{"):][:40]
        raise SystemExit(f"{CONTRACT}: unsubstituted template token {stray!r}")
    return text


def vocabulary(body: str) -> list[str]:
    """The platform's nouns, from the contract's own list.  One per line."""
    try:
        section = body.split("## The vocabulary", 1)[1]
        fence = section.split("```text", 1)[1].split("```", 1)[0]
    except IndexError:
        raise SystemExit(f"{CONTRACT}: no ```text fence under '## The vocabulary'")
    terms = [ln.strip() for ln in fence.splitlines() if ln.strip()]
    if not terms:
        raise SystemExit(f"{CONTRACT}: '## The vocabulary' fence is empty")
    return terms


def vocab_block(terms: list[str], entries, tags: set) -> tuple[str, set]:
    """One guide's vocabulary: its own terms, and the files of ITS OWN that use them.

    A term is listed only where the guide can actually follow it up.  That is
    the whole safety property — a guide is never handed a word whose page it
    was not given, so "start with the file named beside the term" is always a
    reachable instruction rather than a dead pointer.

    Returns the rendered block and the terms that landed, so main() can fail
    the render on a term no corpus uses at all.
    """
    rows, found = [], set()
    for term in terms:
        hits = []
        for rel, _fm, body in entries:
            n = body.lower().count(term.lower())
            if n:
                hits.append((n, flat_name(rel)))
        if not hits:
            continue
        found.add(term)
        hits.sort(key=lambda x: (-x[0], x[1]))
        rows.append(f"  {term:<24} {', '.join(name for _n, name in hits[:3])}")
    block = "\n".join(rows)
    if tags:
        block += ("\n\n  Concepts these same files cover:\n    "
                  + ", ".join(sorted(tags)))
    return block, found


def load(path: pathlib.Path):
    text = path.read_text()
    if not text.startswith("---\n"):
        return None, text
    _, fm, body = text.split("---", 2)
    return yaml.safe_load(fm) or {}, body.lstrip("\n")


def flat_name(rel: pathlib.Path) -> str:
    """apex/your-data/who-can-see-it.md -> your-data--who-can-see-it.md"""
    parts = list(rel.parts)
    if parts[0] in ("apex", "docs"):
        parts = parts[1:]
    return "--".join(parts)


def main() -> int:
    preamble, evals, contract_body = contract()
    terms = vocabulary(contract_body)
    seen_terms = set()
    pages, unlabelled = [], []
    for base in ("apex", "docs"):
        for path in sorted((ROOT / base).rglob("*.md")):
            if path == CONTRACT:
                continue
            rel = path.relative_to(ROOT)
            fm, body = load(path)
            if fm is None:
                unlabelled.append(rel)
                continue
            pages.append((rel, fm, body))

    # Every reader-facing source, withheld pages included — a scaffold is a
    # draft away from the corpus.  docs/ is the operators' shelf and names the
    # software it documents; apex/, the prompts and the eval cases are what
    # students and faculty hear, so they say {{PLATFORM}}.
    named = [hit for rel, _fm, body in pages if rel.parts[0] == "apex"
             for hit in unbranded(str(rel), body)]
    named += unbranded(str(CONTRACT.relative_to(ROOT)), CONTRACT.read_text())
    named += unbranded("docs/corpus.py (SCOPE, DIRECTORY)",
                       "\n".join([*SCOPE.values(), DIRECTORY]))
    if named:
        raise SystemExit("these hard-code a name a deployment chooses — write {{PLATFORM}} "
                         "or {{MODEL}} (PLATFORM_NAME and CHAT_MODEL fill them):\n  "
                         + "\n  ".join(named))

    if OUT.exists():
        for p in sorted(OUT.rglob("*"), reverse=True):
            p.unlink() if p.is_file() else p.rmdir()
    OUT.mkdir(parents=True, exist_ok=True)

    corpora, withheld = {}, []
    for rel, fm, body in pages:
        status = fm.get("status", "scaffold")
        if status in WITHHOLD:
            withheld.append((rel, status))
            continue
        reach = {fm.get("audience")} | set(fm.get("also_reaches") or [])
        for guide, audience in GUIDES.items():
            if audience in reach:
                corpora.setdefault(guide, []).append((rel, fm, body))
        tags = set(fm.get("tags") or [])
        if len(tags & SECURITY_TAGS) >= SECURITY_MIN:
            corpora.setdefault("security-guide", []).append((rel, fm, body))
        if len(tags & USAGE_TAGS) >= USAGE_MIN:
            corpora.setdefault("usage-guide", []).append((rel, fm, body))
        if len(tags & CODER_TAGS) >= CODER_MIN:
            corpora.setdefault("coder-guide", []).append((rel, fm, body))

    tethers = {}
    for guide, entries in sorted(corpora.items()):
        d = OUT / guide
        d.mkdir(parents=True, exist_ok=True)
        lines = [f"# {guide} — corpus manifest", "",
                 f"{len(entries)} pages, rendered by `just docs-corpus`.  "
                 "Do not edit anything in this directory — edit the source page.", "",
                 "| page | source | audience | also_reaches | status |",
                 "|---|---|---|---|---|"]
        for rel, fm, body in sorted(entries):
            name = flat_name(rel)
            # The description is the chunker's context; keep it with the text.
            head = f"<!-- source: {rel} | audience: {fm.get('audience')} | status: {fm.get('status')} -->\n"
            # Only apex/ is written with {{PLATFORM}}; a docs/ page that shows
            # the token is explaining it, and filling it would garble that.
            text = f"> {fm.get('description', '')}\n\n" + body
            (d / name).write_text(head + (brand(text) if rel.parts[0] == "apex" else text))
            lines.append(f"| `{name}` | `{rel}` | {fm.get('audience')} | "
                         f"{', '.join(fm.get('also_reaches') or []) or '—'} | {fm.get('status')} |")
            for t in fm.get("tethered_to") or []:
                tethers.setdefault(str(t), set()).add(guide)
        (d / "MANIFEST.md").write_text("\n".join(lines) + "\n")
        scope = SCOPE.get(guide)
        if scope:
            tags = {tg for _r, fm, _b in entries for tg in (fm.get("tags") or [])}
            block, found = vocab_block(terms, entries, tags)
            seen_terms |= found
            (d / "SYSTEM-PROMPT.md").write_text(
                f"<!-- rendered from docs/agent-contract.md by `just docs-corpus` "
                f"— edit the source, not this -->\n\n{brand(scope)}\n\n"
                f"{fill(preamble, block)}\n")
            (d / "EVALS.md").write_text(
                f"# {guide} — eval cases\n\n"
                "<!-- rendered from docs/agent-contract.md — edit the source -->\n\n"
                f"{brand(evals)}\n")

    # The front desk: a prompt and nothing else.  No pages, so no manifest —
    # `corpus/welcome/` having no knowledge in it is the design, not a bug, and
    # scripts/agents_check.py knows to expect that.
    d = OUT / "welcome"
    d.mkdir(parents=True, exist_ok=True)
    (d / "SYSTEM-PROMPT.md").write_text(
        "<!-- rendered from docs/agent-contract.md by `just docs-corpus` "
        "— edit the source, not this -->\n\n"
        + fill(welcome(contract_body)) + "\n")

    # A term no corpus page uses anywhere is a name the platform has stopped
    # using — or never had.  Six agents reciting it is the doc-drift failure
    # this list would otherwise cause, so it is a build error, not a warning.
    dead = [x for x in terms if x not in seen_terms]
    if dead:
        raise SystemExit(f"{CONTRACT}: '## The vocabulary' names "
                         f"{len(dead)} term(s) no corpus page uses: "
                         + ", ".join(repr(x) for x in dead))
    (d / "EVALS.md").write_text(
        "# welcome — eval cases\n\n"
        "<!-- rendered from docs/agent-contract.md — edit the source -->\n\n"
        f"{brand(evals)}\n")

    report = ["# corpus/ — rendered, not edited", "",
              "Generated by `just docs-corpus` from front matter.  "
              "See [docs/audience-projection.md](../docs/audience-projection.md).", "",
              "## Corpora", "", "| guide | query | pages |", "|---|---|---|"]
    for guide, entries in sorted(corpora.items()):
        if guide in GUIDES:
            q = f"`audience: {GUIDES[guide]}` or `also_reaches` contains it"
        else:
            cut = CROSS_CUTS[guide]
            q = f"≥{cut} {guide.removesuffix('-guide')} tags (cross-cut)"
        report += [f"| {guide} | {q} | {len(entries)} |"]
    report += ["| welcome | no query — it routes, it does not answer | 0 |"]
    report += ["", "## Withheld", "",
               "Held back by status — unfinished, or finished but unratified.", "",
               "| page | status |", "|---|---|"]
    report += [f"| `{rel}` | {st} |" for rel, st in sorted(withheld)] or ["| — | — |"]
    if unlabelled:
        report += ["", "## Unlabelled — in no corpus at all", "",
                   "These carry no front matter, so no query can reach them.", ""]
        report += [f"- `{rel}`" for rel in sorted(unlabelled)]
    report += ["", "## Drift index", "",
               "Which corpora go stale when a source path changes "
               "(`tethered_to`, the machine-readable half of the drift rule).", "",
               "| path | corpora |", "|---|---|"]
    report += [f"| `{p}` | {', '.join(sorted(g))} |" for p, g in sorted(tethers.items())]
    (OUT / "README.md").write_text("\n".join(report) + "\n")

    for guide, entries in sorted(corpora.items()):
        print(f"  {guide:22} {len(entries):3} pages")
    print(f"  {'withheld':22} {len(withheld):3} pages")
    if unlabelled:
        print(f"  {'UNLABELLED':22} {len(unlabelled):3} pages -> in no corpus")
        for rel in sorted(unlabelled):
            print(f"      {rel}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
