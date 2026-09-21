#!/usr/bin/env python3
"""Prove the vestibule is what we think it is.

`just agents-seed` makes the guides; this asks the running instance whether
they actually landed, and whether the config points at them.  Seven
questions, in the order they go wrong:

  1. Does the flagship serve a `modelSpecs` list at all?  A box that never
     got the hand-written block (docs/admin-guide.md, "The vestibule") serves
     `modelSpecs: {}` and looks fine until you open the picker.
  2. Is `enforce: true`?  Without it the specs are suggestions and the raw
     model list is still there.
  3. Does every spec's `agent_id` exist?  This is the orphan failure — an
     agent recreated instead of updated mints a new id, and the spec silently
     points at nothing.
  4. Does every guide carry `file_search` and some files?  An agent with the
     tool and no knowledge answers from the base model, which is exactly the
     fabrication the contract exists to stop.  The front desk is the one
     deliberate exception — it routes rather than answers, so it gets no
     corpus and no `file_search`, and `corpus/<slug>/` is what says which
     case a guide is in.
  5. Does the attached knowledge MATCH the rendered corpus?  This is the
     third door in the render-check family and it cost a real find
     (2026-09-21): a green deploy does not re-seed the guides, so a prompt
     or corpus change is inert on the box and NOTHING says so.  Five guides
     were serving knowledge weeks older than the tree while every other
     check was green.  Counts, not contents — cheap, and drift this class
     always moves the count.  Red means run `just agents-seed`.
  6. Can anyone actually tell us something is broken?  `report_problem` is
     an MCP tool, and MCP tool names fail closed and SILENT when they are
     wrong — the feature does not error, it just isn't there.  So this asks
     the agents whether they carry it rather than trusting the seeder ran.
  7. Can a signed-in person SEE any of this?  Every question above reads the
     agents collection with no ACL filter, which answers "does it exist" and
     is silent on "can anyone reach it."  Visibility in 0.8.x is the ACL, and
     an agent granted only to its owner sits in the picker's config while
     being invisible to the entire realm — the specs load, the client then
     resolves the agents behind them, and the ones it cannot read drop out.
     What a person sees is a label that flashes and is replaced by an empty
     selector, with no error anywhere.  Found from the outside, by signing
     in (2026-09-21), while all six checks above were green.

It reads the config **from inside the container**, with LibreChat's own YAML
parser, because `/api/config` will lie to you: unauthenticated requests get a
pre-login payload that simply omits `modelSpecs`, with a 200 and an otherwise
plausible body.  Curling it and seeing no specs proves nothing about whether
the config loaded — ask the file the container is actually reading.

Read-only.  Nothing here writes, mints, or restarts.
"""
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent

# Imported, never retyped: the whole failure this check exists to catch is
# two copies of this string drifting apart.
sys.path.insert(0, str(ROOT / "scripts"))
from seed_agents import REGISTRAR_MCP  # noqa: E402

OK, BAD, MEH = "  ok   ", "  FAIL ", "  warn "

# Rendered for the operator, not the model — the same list seed_agents.py
# holds.  A corpus directory with only these in it has no knowledge in it.
NOT_KNOWLEDGE = {"MANIFEST.md", "SYSTEM-PROMPT.md", "EVALS.md"}


def dc(*args: str) -> str:
    return subprocess.run(["docker", "compose", "exec", "-T", *args], cwd=ROOT,
                          capture_output=True, text=True,
                          stdin=subprocess.DEVNULL).stdout


def chat_config() -> dict:
    """The flagship's config as the container sees it — override and all.

    js-yaml inside the container, not PyYAML on the host: it is the parser
    LibreChat itself uses, it needs nothing installed on a deploy box, and it
    reads whatever is mounted (so a `site/` override is picked up for free).
    """
    js = ("const y=require('js-yaml'),f=require('fs');"
          "process.stdout.write(JSON.stringify("
          "y.load(f.readFileSync(process.env.CONFIG_PATH||'/app/librechat.yaml','utf8'))"
          "||{}))")
    out = dc("librechat", "node", "-e", js).strip()
    if not out:
        sys.exit(f"{BAD}could not read the flagship's config — is librechat up?")
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        sys.exit(f"{BAD}the flagship's config is not valid YAML: {out[:200]}")


def agents() -> dict:
    """id -> {name, tools, files} straight from Mongo.

    Not the API: this runs as nobody, and /api/agents wants a user's JWT and
    a browser User-Agent.  The database is the honest read for a check.
    """
    q = ('db.agents.find({}, {id:1, name:1, tools:1, tool_resources:1, _id:0})'
         '.toArray().forEach(a => print(JSON.stringify({'
         'id: a.id, name: a.name, tools: a.tools || [], '
         'files: ((a.tool_resources||{}).file_search||{}).file_ids || []})))')
    found = {}
    for line in dc("mongodb", "mongosh", "--quiet", "LibreChat", "--eval", q).splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        a = json.loads(line)
        found[a["id"]] = a
    return found


def visibility() -> dict:
    """agent id -> the principal types that grant access to it.

    `agents()` above reads the collection with no ACL filter, which is the
    honest read for "does this agent exist" and says NOTHING about whether a
    signed-in person can see it.  Those are different questions and the
    second one is the one a user experiences: specs render from the config,
    the client then resolves the agents behind them, and a guide the viewer
    cannot read drops out of the picker.  The symptom is a label that flashes
    and is replaced by an empty selector — not an error, anywhere.

    Visibility in 0.8.x is the ACL, not the author field.  `principalType`
    is one of user / group / role / public (PrincipalType in the pinned
    image); only the last two can reach a whole realm.
    """
    q = ('var m = {}; db.agents.find({}, {_id:1, id:1}).toArray()'
         '.forEach(a => m[a._id.toString()] = a.id); '
         'db.aclentries.find({resourceType:"agent"}, '
         '{resourceId:1, principalType:1, _id:0}).toArray()'
         '.forEach(e => print(JSON.stringify({'
         'agent: m[e.resourceId.toString()] || null, p: e.principalType})))')
    out = {}
    for line in dc("mongodb", "mongosh", "--quiet", "LibreChat",
                   "--eval", q).splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        e = json.loads(line)
        if e.get("agent"):
            out.setdefault(e["agent"], set()).add(e.get("p"))
    return out


def main() -> int:
    # Without a render there is nothing to compare against, and every guide
    # would read as "no corpus by design" — a green check on a box whose
    # guides are unverifiable.  `just deploy` renders first for this reason;
    # a hand run gets told rather than misled.
    if not (ROOT / "corpus").is_dir():
        sys.exit(f"{BAD}corpus/ has not been rendered on this box, so the "
                 f"knowledge checks below would all pass vacuously.  "
                 f"Run `just docs-corpus` first.")
    cfg = chat_config()
    live = agents()
    specs = (cfg.get("modelSpecs") or {}).get("list") or []
    bad = 0

    print("the vestibule")
    if not specs:
        print(f"{BAD}no modelSpecs — this box never got the hand-written block "
              f"(docs/admin-guide.md, \"The vestibule\")")
        bad += 1
    else:
        print(f"{OK}{len(specs)} model specs")
        if (cfg.get("modelSpecs") or {}).get("enforce"):
            print(f"{OK}enforce: true — the raw model list is off")
        else:
            print(f"{BAD}enforce is not true — raw models are still selectable")
            bad += 1

    print("\nthe guides")
    claimed = set()
    # Guides that ANSWER (they have a corpus).  The front desk routes instead,
    # so it carries no report tool by design — counting it would make a
    # correct box read 5/6.  See scripts/seed_agents.py, GUIDES.
    answering = set()
    for spec in specs:
        aid = (spec.get("preset") or {}).get("agent_id")
        label = spec.get("label") or spec.get("name") or "?"
        if not aid:
            print(f"{BAD}{label:20} spec has no preset.agent_id")
            bad += 1
            continue
        claimed.add(aid)
        a = live.get(aid)
        if not a:
            print(f"{BAD}{label:20} {aid} — ORPHAN: no agent with that id.  "
                  f"Re-run `just agents-seed` and paste the new block.")
            bad += 1
            continue
        n = len(a["files"])
        # A spec's `name` is the corpus slug (model_specs writes it that way),
        # so the render itself says whether this guide is meant to have
        # knowledge.  No guessing from the agent's own state.
        slug = spec.get("name") or ""
        pages = sorted((ROOT / "corpus" / slug).glob("*.md")) if slug else []
        wants_knowledge = any(f.name not in NOT_KNOWLEDGE for f in pages)
        if wants_knowledge:
            answering.add(aid)
        if not wants_knowledge:
            extra = "" if not n else f" — but it has {n}, which is wrong"
            print(f"{OK if not n else BAD}{label:20} {aid}  "
                  f"no corpus by design (routes, does not answer){extra}")
            if n:
                bad += 1
            continue
        if "file_search" not in a["tools"]:
            print(f"{BAD}{label:20} {aid}  no file_search tool — "
                  f"it cannot reach its knowledge")
            bad += 1
        elif not n:
            print(f"{BAD}{label:20} {aid}  0 files — it will answer from the "
                  f"base model, which is the failure the contract exists to stop")
            bad += 1
        else:
            # The drift door: `just deploy` re-renders nothing the guides
            # eat, so `n` is whatever the last `agents-seed` attached and
            # `rendered` is what the tree says today.  Report, never repair —
            # re-seeding six agents mid-deploy is a bigger surprise than a
            # red line, and this is a class of bug you want told to you.
            rendered = sum(1 for f in pages if f.name not in NOT_KNOWLEDGE)
            if n != rendered:
                print(f"{BAD}{label:20} {aid}  {n} files attached but the "
                      f"corpus renders {rendered} — STALE: this guide is "
                      f"answering from knowledge older than the tree.  "
                      f"Run `just agents-seed`.")
                bad += 1
            else:
                print(f"{OK}{label:20} {aid}  {n} files")

    # The report tool is wired in three places that must agree: the server
    # key in librechat.yaml, REGISTRAR_MCP in seed_agents.py, and the tool
    # name on the agent.  Nothing errors when they don't — you just have a
    # front door that quietly can't take a complaint.
    print("\ncan anyone report a problem?")
    want = f"report_problem_mcp_{REGISTRAR_MCP}"
    carries = [a for i, a in live.items() if i in answering and want in a["tools"]]
    if not answering:
        print(f"{MEH}no guides to check")
    elif not carries:
        print(f"{BAD}no guide carries {want} — the front door cannot take a "
              f"complaint.  Re-run `just agents-seed`; if that doesn't fix it, "
              f"the server key under `mcpServers:` in librechat.yaml and "
              f"REGISTRAR_MCP in scripts/seed_agents.py disagree.")
        bad += 1
    else:
        triage = [a for a in carries
                  if f"report_triage_mcp_{REGISTRAR_MCP}" in a["tools"]]
        print(f"{OK}{len(carries)}/{len(answering)} answering guides carry report_problem"
              + (f" · {triage[0]['name']} can work the queue" if triage else ""))
        if not triage:
            print(f"{MEH}no guide carries report_triage — the queue is still "
                  f"readable on the box with `just reports`")

    # The question a green check has never asked: can a real person SEE these?
    print("\ncan a signed-in person see them?")
    acl = visibility()
    REACHES_EVERYONE = {"public", "role"}
    blind = []
    for aid in sorted(claimed):
        grants = acl.get(aid) or set()
        if not (grants & REACHES_EVERYONE):
            blind.append((aid, grants))
    if not claimed:
        print(f"{MEH}no specs to check")
    elif blind:
        for aid, grants in blind:
            name = (live.get(aid) or {}).get("name") or aid
            who = (f"granted to {', '.join(sorted(grants))} only"
                   if grants else "no ACL entry at all")
            print(f"{BAD}{name:20} {aid}  {who} — it is in the picker's config "
                  f"and invisible to everyone who isn't its owner")
        print(f"{BAD}{len(blind)} guide(s) no one can reach.  This is the empty "
              f"picker whose label flashes first: the specs load, then the "
              f"client resolves the agents and drops the ones it can't read.")
        bad += len(blind)
    else:
        print(f"{OK}all {len(claimed)} reachable realm-wide "
              f"({', '.join(sorted(set().union(*(acl.get(a, set()) for a in claimed)) & REACHES_EVERYONE))})")

    loose = [a for i, a in live.items() if i not in claimed]
    if loose:
        print(f"\n{MEH}{len(loose)} agent(s) exist but no spec points at them: "
              f"{', '.join(sorted(a['name'] or a['id'] for a in loose))}")

    print()
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
