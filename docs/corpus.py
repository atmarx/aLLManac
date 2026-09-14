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
        "You are the Student Guide: using the Almanac in your courses — "
        "signing in, building agents, knowledge files, API keys, and what "
        "the budget numbers mean.",
    "instructor-guide":
        "You are the Instructor Guide: running a course on the Almanac — "
        "rosters, class configuration, shared agents, what students can see, "
        "and what you are responsible for.",
    "platform-guide":
        "You are the Platform Guide: how the Almanac is built and why — "
        "the architecture, the decisions, and the trade-offs they cost.",
    "dev-guide":
        "You are the Dev Guide: operating the Almanac — deployment, "
        "runbooks, verification, and what breaks.",
    "security-guide":
        "You are the Security Guide: the Almanac's security posture — the "
        "controls, the boundaries, and the blue-team and purple-team "
        "exercises that test them.",
}

# The directory of guides, rendered into BOTH the shared preamble (as the
# first escape hatch) and the welcome desk's own fence.  One authority on
# purpose: a guide that names a sibling guide wrongly is a redirect that
# points nowhere, which is the failure the hatch list exists to prevent.
# Routing lines, not SCOPE's agent-voice lines — the reader is choosing.
DIRECTORY = """\
      Student Guide      using the Almanac in a course you are taking
      Instructor Guide   running a course on it — rosters, class setup,
                         shared agents, what students can see
      Platform Guide     how the Almanac is built, and why
      Dev Guide          deploying and operating it
      Security Guide     the security posture, and the exercises that test it\
"""

# Deployment config, not code: a different institution names a different
# fallback (docs/registrar-spec.md, Decision 18 — boundary verbiage is
# config).  Generic default so tracked files name no institution.
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


def welcome(body: str) -> str:
    """The welcome desk's prompt — its own fence, not the shared preamble.

    It carries no knowledge files, so the preamble's anchor ("your files are
    the only thing you know") has nothing to point at.  See the "The welcome
    desk" section of docs/agent-contract.md for why that makes it the agent
    most exposed to fabrication rather than least.
    """
    try:
        section = body.split("## The welcome desk", 1)[1]
        return section.split("```text", 1)[1].split("```", 1)[0].strip()
    except IndexError:
        raise SystemExit(f"{CONTRACT}: no ```text fence under '## The welcome desk'")


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
    return fill(preamble), evals, body


def fill(text: str) -> str:
    """Deployment + directory substitution.  Loud if a token survives."""
    text = (text.replace("{{FALLBACK_ASSISTANT}}", FALLBACK)
                .replace("{{GUIDE_DIRECTORY}}", DIRECTORY))
    if "{{" in text:
        stray = text[text.index("{{"):][:40]
        raise SystemExit(f"{CONTRACT}: unsubstituted template token {stray!r}")
    return text


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
        if len(set(fm.get("tags") or []) & SECURITY_TAGS) >= SECURITY_MIN:
            corpora.setdefault("security-guide", []).append((rel, fm, body))

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
            (d / name).write_text(head + f"> {fm.get('description', '')}\n\n" + body)
            lines.append(f"| `{name}` | `{rel}` | {fm.get('audience')} | "
                         f"{', '.join(fm.get('also_reaches') or []) or '—'} | {fm.get('status')} |")
            for t in fm.get("tethered_to") or []:
                tethers.setdefault(str(t), set()).add(guide)
        (d / "MANIFEST.md").write_text("\n".join(lines) + "\n")
        scope = SCOPE.get(guide)
        if scope:
            (d / "SYSTEM-PROMPT.md").write_text(
                f"<!-- rendered from docs/agent-contract.md by `just docs-corpus` "
                f"— edit the source, not this -->\n\n{scope}\n\n{preamble}\n")
            (d / "EVALS.md").write_text(
                f"# {guide} — eval cases\n\n"
                "<!-- rendered from docs/agent-contract.md — edit the source -->\n\n"
                f"{evals}\n")

    # The welcome desk: a prompt and nothing else.  No pages, so no manifest —
    # `corpus/welcome/` having no knowledge in it is the design, not a bug, and
    # scripts/agents_check.py knows to expect that.
    d = OUT / "welcome"
    d.mkdir(parents=True, exist_ok=True)
    (d / "SYSTEM-PROMPT.md").write_text(
        "<!-- rendered from docs/agent-contract.md by `just docs-corpus` "
        "— edit the source, not this -->\n\n"
        + fill(welcome(contract_body)) + "\n")
    (d / "EVALS.md").write_text(
        "# welcome — eval cases\n\n"
        "<!-- rendered from docs/agent-contract.md — edit the source -->\n\n"
        f"{evals}\n")

    report = ["# corpus/ — rendered, not edited", "",
              "Generated by `just docs-corpus` from front matter.  "
              "See [docs/audience-projection.md](../docs/audience-projection.md).", "",
              "## Corpora", "", "| guide | query | pages |", "|---|---|---|"]
    for guide, entries in sorted(corpora.items()):
        q = (f"`audience: {GUIDES[guide]}` or `also_reaches` contains it"
             if guide in GUIDES else f"≥{SECURITY_MIN} security tags (cross-cut)")
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
