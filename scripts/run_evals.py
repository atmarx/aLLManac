#!/usr/bin/env python3
"""Run the guide-agent eval cases against the agents actually running on this box.

`docs/agent-contract.md` is the source for both the prompts and the cases;
this drives the cases at the live agents and writes down what they said.  It
scores nothing — a human reads the transcript against the passing conditions,
because "answers from the roster documentation" is not a string match.

    just evals                  # every guide, every case
    just evals --guide student-guide --case F1,M1

**It talks to the box the way seed_agents.py does, and for the same reasons.**
A JWT minted inside the container from the container's own `JWT_SECRET`, a
browser User-Agent because `uaParser` rejects anything else on `/api/agents`
with an SSE "Illegal request" body, and no credential ever leaves the host.

The chat route is `POST /api/agents/chat/`, which returns a `streamId` and
generates asynchronously.  We do NOT read the stream: the contract says to
score the message the person sees and never the thinking, and the persisted
message in Mongo *is* what the person sees.  So: post, then poll the
conversation until an assistant message lands or the timeout expires.

**A guide that returns nothing fails every case.**  That is a real result, not
a harness error — a reasoning model can spend its whole completion budget
inside an unclosed thinking block and hand back an empty message.  An empty
reply is recorded as an empty reply.  What is NOT a result is the model being
unreachable, so that is checked once, up front, and refuses to run.
"""
import argparse
import json
import os
import pathlib
import re
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent

# Container names, not compose service names: this shells `docker exec`
# directly so it works from anywhere on the box.
LIBRECHAT = "alm-librechat"
MONGO = "alm-mongo"
REGISTRAR = "alm-registrar"
CONTRACT = ROOT / "docs" / "agent-contract.md"
OUT = ROOT / "site" / "evals"

# Which corpus slug each live agent name corresponds to.  The names have moved
# before (SecurityBot3000 -> Security Guide, Welcome -> Front Desk), so match
# on the corpus slug in the agent's instructions where we can and fall back to
# the name.  A box whose agents predate a rename is a box due a re-seed, and
# the run says so rather than quietly testing yesterday's platform.
SLUG_BY_NAME = {
    "Front Desk": "welcome", "Welcome": "welcome",
    "Student Guide": "student-guide",
    "Instructor Guide": "instructor-guide",
    "Platform Guide": "platform-guide",
    "Dev Guide": "dev-guide",
    "Security Guide": "security-guide", "SecurityBot3000": "security-guide",
    "Usage Guide": "usage-guide",
    "Coder Guide": "coder-guide",
}

# The welcome desk carries no knowledge files and answers nothing, so the
# corpus cases do not apply to it -- only its own two.  Everything else takes
# the whole table.
WELCOME_ONLY = {"W1", "W2"}


def dc(container: str, *args: str) -> str:
    r = subprocess.run(["docker", "exec", container, *args],
                       capture_output=True, text=True)
    if r.returncode:
        sys.exit(f"docker exec {container} failed:\n{r.stderr.strip()}")
    return r.stdout


def parse_yaml(text: str):
    """js-yaml inside the flagship, not PyYAML on the host.

    A deploy box has no business growing a Python dependency so a check can
    run on it: the docker host's python is PEP668-managed with no pip, so
    `import yaml` made this whole runner unrunnable exactly where it matters
    and nobody found out for weeks (2026-09-21).  scripts/agents_check.py
    already reads the flagship's config this way and for this reason; the
    parser we want is in a container we already talk to.
    """
    r = subprocess.run(
        ["docker", "exec", "-i", LIBRECHAT, "node", "-e",
         "const y=require('js-yaml');let s='';process.stdin.on('data',d=>s+=d)"
         ".on('end',()=>process.stdout.write(JSON.stringify(y.load(s)||[])))"],
        input=text, capture_output=True, text=True)
    if r.returncode:
        sys.exit(f"could not parse the contract's YAML fence in {LIBRECHAT}:\n"
                 f"{r.stderr.strip()}")
    return json.loads(r.stdout)


def cases() -> list[dict]:
    """Single-turn cases from the contract's table, multi-turn from its fence."""
    platform = (os.environ.get("PLATFORM_NAME") or os.environ.get("DOCS_PRODUCT_NAME")
                or "aLLManac").strip()
    body = CONTRACT.read_text().replace("{{PLATFORM}}", platform)
    out = []

    table = body.split("## The evals", 1)[1].split("\n---", 1)[0]
    for line in table.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) == 4 and re.fullmatch(r"[A-Z]\d+", cells[0]):
            out.append({"id": cells[0], "pattern": cells[1],
                        "turns": [cells[2].strip('"')], "passes_when": cells[3]})

    # Two YAML sections, same shape.  The tool cases add `guides:` (which
    # agents the case is for — a desk case means nothing to the Coder Guide)
    # and `as:` (which persona is asking — see personas()).
    for heading in ("## The multi-turn cases", "## The tool cases"):
        section = body.split(heading, 1)
        if len(section) == 2:
            fence = section[1].split("```yaml", 1)[1].split("```", 1)[0]
            for c in parse_yaml(fence):
                c["passes_when"] = c["passes_when"].strip()
                out.append(c)

    if not out:
        sys.exit(f"{CONTRACT}: parsed no eval cases")
    return out


def agents() -> list[dict]:
    q = "db.agents.find({},{id:1,name:1,model:1,_id:0}).toArray()"
    # mongosh prints JS-ish object literals, not JSON — ask it to stringify.
    raw = dc(MONGO, "mongosh", "--quiet", "LibreChat",
             "--eval", f"JSON.stringify({q})")
    found = []
    for a in json.loads(raw):
        slug = SLUG_BY_NAME.get(a["name"])
        if not slug:
            print(f"  warn: live agent {a['name']!r} matches no known guide — skipped")
            continue
        found.append({"slug": slug, "name": a["name"], "id": a["id"],
                      "model": a.get("model")})
    return found


DRIVER = r"""
const jwt = require('jsonwebtoken');
const crypto = require('crypto');
const IN = JSON.parse(require('fs').readFileSync('/app/api/.evals-in.json', 'utf8'));
const BASE = 'http://127.0.0.1:3080';
// uaParser demands a browser UA on every /api/agents route.
const UA = 'Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0';
const token = jwt.sign({ id: IN.owner }, process.env.JWT_SECRET, { expiresIn: '120m' });
const H = { Authorization: `Bearer ${token}`, 'User-Agent': UA, 'Content-Type': 'application/json' };

(async () => {
  const r = await fetch(`${BASE}/api/agents/chat/`, {
    method: 'POST', headers: H, body: JSON.stringify({
      text: IN.text,
      endpoint: 'agents',
      // The vestibule runs `modelSpecs.enforce: true`, so a request with no
      // `spec` is refused before it reaches a model -- as HTTP 200 with an
      // SSE `event: error` body, which is why this cost a whole run to find.
      spec: IN.spec,
      agent_id: IN.agent_id,
      conversationId: IN.conversationId,
      parentMessageId: IN.parentMessageId || '00000000-0000-0000-0000-000000000000',
      messageId: crypto.randomUUID(),
      isContinued: false,
      isRegenerate: false,
    }),
  });
  const t = await r.text();
  console.log(JSON.stringify({ status: r.status, body: t.slice(0, 2000) }));
})();
"""


def personas() -> dict:
    """{persona: LibreChat user id}, after resetting the registrar's fixture.

    The tool cases need someone the roster KNOWS — an instructor on a course,
    a student, an admin — or every enrollment and desk tool just refuses and
    the case tests nothing.  The registrar's `evals-fixture` resets a sandbox
    course and two request tickets for four personas on the reserved .invalid
    TLD, and the tool plane REHEARSES every write they attempt, so a guide
    that applies without asking is recorded doing so and changes nothing.

    Here we give each persona a LibreChat user document — no password, no
    identity-provider link, so nobody can sign in as one; the JWT below is the
    only way in, and it needs the flagship's own secret.  Same shape as the
    guides' service account (scripts/seed_agents.py).
    """
    r = subprocess.run(["docker", "exec", REGISTRAR, "python", "course_admin.py",
                        "evals-fixture"], capture_output=True, text=True)
    if r.returncode:
        sys.exit(f"the registrar could not reset the eval fixture:\n{r.stderr.strip()}")
    emails = json.loads(r.stdout.strip().splitlines()[-1])["personas"]
    ids = {}
    for who, email in emails.items():
        q = (f'var u = db.users.findOne({{email:"{email}"}}, {{_id:1}}); '
             f'if (!u) {{ var r = db.users.insertOne({{email:"{email}", '
             f'username:"{email.split("@")[0]}", name:"Eval {who}", '
             f'provider:"local", role:"USER", emailVerified:true, '
             f'createdAt:new Date(), updatedAt:new Date()}}); '
             f'print(String(r.insertedId)); }} else {{ print(String(u._id)); }}')
        ids[who] = dc(MONGO, "mongosh", "--quiet", "LibreChat", "--eval", q).strip()
    return ids


def say(agent_id: str, spec: str, text: str,
        convo: str | None, parent: str | None, owner: str | None = None) -> dict:
    payload = {"owner": owner or OWNER, "agent_id": agent_id, "spec": spec, "text": text,
               "conversationId": convo, "parentMessageId": parent}
    (ROOT / "site" / ".evals-in.json").write_text(json.dumps(payload))
    subprocess.run(["docker", "cp", str(ROOT / "site" / ".evals-in.json"),
                    f"{LIBRECHAT}:/app/api/.evals-in.json"],
                   check=True, capture_output=True)
    raw = dc(LIBRECHAT, "node", "/app/api/.evals-driver.js")
    return json.loads(raw.strip().splitlines()[-1])


def reply(convo: str, after: int, timeout: int) -> tuple[str, str | None, list, list]:
    """Poll the conversation for the next assistant message.
    Returns (text, id, tool calls, content block types)."""
    # An agent's visible reply is NOT `text` -- that field stays empty and the
    # message carries a `content[]` array of blocks: `think`, `tool_call`, and
    # `text`.  Only the `text` blocks are what the person sees, which is also
    # exactly what the contract says to score and the thinking it says to
    # ignore.  Reading `text` scored every answering guide as silent.
    q = ("JSON.stringify(db.messages.find({conversationId:%r,isCreatedByUser:false},"
         "{text:1,content:1,messageId:1,_id:0}).sort({createdAt:1}).toArray()"
         ".map(function(m){return {messageId:m.messageId, text:"
         "(m.content||[]).filter(function(c){return c.type==='text'})"
         ".map(function(c){return (c.text && c.text.value) || c.text || ''})"
         ".join('\\n').trim() || m.text || '', tools:"
         "(m.content||[]).filter(function(c){return c.type==='tool_call'})"
         ".map(function(c){var t=c.tool_call||{};return {name:t.name, args:t.args,"
         " output:String(t.output||'').slice(0,600)};}),"
         " types:(m.content||[]).map(function(c){return c.type;})};}))" % convo)
    deadline = time.time() + timeout
    while time.time() < deadline:
        msgs = json.loads(dc(MONGO, "mongosh", "--quiet", "LibreChat", "--eval", q))
        if len(msgs) > after:
            m = msgs[after]
            # The types ride along because the block shape is read, not
            # documented: if LibreChat ever renames it, "no tool calls"
            # would score as a guide that behaved.  score() refuses that.
            return ((m.get("text") or ""), m.get("messageId"),
                    m.get("tools") or [], m.get("types") or [])
        time.sleep(3)
    return "", None, [], []


# ---- mechanical scoring: the tool cases' `expect:` -----------------------------
# Only calls are scored here — the name, and any arguments the case pins.
# Everything about the prose is a human's read of the transcript.

def _args(tc: dict) -> dict:
    a = tc.get("args")
    if isinstance(a, str):
        try:
            a = json.loads(a)
        except ValueError:
            a = {}
    return a if isinstance(a, dict) else {}


def _same(want, got) -> bool:
    if want == "*":
        return got not in (None, "", 0, False)
    if isinstance(want, bool) or isinstance(got, bool):
        return str(want).lower() == str(got).lower()
    try:
        return float(want) == float(got)
    except (TypeError, ValueError):
        return str(want).strip().lower() == str(got).strip().lower()


def _hit(item, calls: list[dict]) -> bool:
    if isinstance(item, str):
        name, want = item, {}
    else:
        (name, want), = item.items()
        want = want or {}
    return any(c["name"] == name and all(_same(v, _args(c).get(k))
                                         for k, v in want.items())
               for c in calls)


def _fmt(item) -> str:
    if isinstance(item, str):
        return item
    (name, want), = item.items()
    return f"{name}({', '.join(f'{k}={v}' for k, v in (want or {}).items())})"


def score(case: dict, turns: list[dict]) -> tuple[str | None, list[str]]:
    """-> (PASS | FAIL | UNSCORED, reasons), or (None, []) for a case with no
    `expect:`.  UNSCORED is red too: a turn we could not read is not a pass."""
    if not case.get("expect"):
        return None, []
    why, unreadable = [], False
    for i, e in enumerate(case["expect"], 1):
        if i > len(turns) or not turns[i - 1]["reply"]:
            why.append(f"turn {i}: returned nothing")
            continue
        t = turns[i - 1]
        calls = [{"name": c["name"].split("_mcp_")[0], "args": c.get("args")}
                 for c in t.get("tools") or [] if c.get("name")]
        if (len(calls) < len(t.get("tools") or [])
                or (not calls and "tool_call" in (t.get("types") or []))):
            unreadable = True
            why.append(f"turn {i}: tool blocks present but unreadable "
                       f"({t.get('types')})")
            continue
        for it in e.get("calls") or []:
            if not _hit(it, calls):
                why.append(f"turn {i}: expected {_fmt(it)}")
        if e.get("any") and not any(_hit(it, calls) for it in e["any"]):
            why.append(f"turn {i}: expected one of "
                       + ", ".join(_fmt(it) for it in e["any"]))
        for it in e.get("never") or []:
            if _hit(it, calls):
                why.append(f"turn {i}: called {_fmt(it)}")
    if unreadable:
        return "UNSCORED", why
    return ("FAIL" if why else "PASS"), why


def reachable(model: str) -> str | None:
    """Ask the gateway for a short completion on the model the guides use.

    Without this the whole run scores as "returned nothing," which is a real
    failure condition for a model and a lie about a stack whose inference
    backend is simply down.  Distinguishing the two is the entire point.

    The cap is 64 rather than 1 because a reasoning model spends tokens
    thinking before it emits any: `max_tokens: 1` comes back 400 *"Could not
    finish the message because max_tokens or model output limit was
    reached"*, and a probe that fails on a perfectly healthy model is worse
    than no probe -- it refuses the run and blames the stack.
    """
    probe = (
        "import json,urllib.request,os\n"
        "req=urllib.request.Request('http://127.0.0.1:4000/v1/chat/completions',\n"
        "  data=json.dumps({'model':%r,'max_tokens':64,\n"
        "    'messages':[{'role':'user','content':'hi'}]}).encode(),\n"
        "  headers={'Content-Type':'application/json',\n"
        "           'Authorization':'Bearer '+os.environ['LITELLM_MASTER_KEY']})\n"
        "try:\n"
        "    urllib.request.urlopen(req,timeout=30); print('OK')\n"
        "except Exception as e:\n"
        "    print('ERR', type(e).__name__, str(e)[:200])\n" % model
    )
    r = subprocess.run(["docker", "exec", "alm-litellm", "python", "-c", probe],
                       capture_output=True, text=True)
    out = (r.stdout + r.stderr).strip()
    return None if out.startswith("OK") else out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--guide", help="comma-separated corpus slugs; default all")
    ap.add_argument("--case", help="comma-separated case ids; default all")
    ap.add_argument("--timeout", type=int, default=180, help="seconds per turn")
    ap.add_argument("--check", action="store_true",
                    help="only the cases that score themselves (`expect:`); "
                         "exit 1 on any FAIL or UNSCORED — for the nightly run")
    ap.add_argument("--skip-precheck", action="store_true",
                    help="run even if the gateway cannot reach the guides' model")
    args = ap.parse_args()

    global OWNER
    raw = dc(MONGO, "mongosh", "--quiet", "LibreChat", "--eval",
             "JSON.stringify(db.agents.findOne({},{author:1,_id:0}))")
    OWNER = json.loads(raw)["author"]["$oid"] if "$oid" in raw else json.loads(raw)["author"]

    live = agents()
    if not live:
        sys.exit("no guide agents on this box — run `just agents-seed` first")

    model = live[0]["model"]
    if not args.skip_precheck:
        why = reachable(model)
        if why:
            sys.exit(
                f"the guides answer with {model!r} and the gateway cannot reach it:\n"
                f"  {why}\n"
                "Every case would score as 'returned nothing', which would be a lie\n"
                "about the prompts.  Bring inference up, or pass --skip-precheck if\n"
                "you really mean to record a dead stack.")

    if args.guide:
        want = set(args.guide.split(","))
        live = [a for a in live if a["slug"] in want]
    picked = cases()
    if args.case:
        want = set(args.case.split(","))
        picked = [c for c in picked if c["id"] in want]
    if args.check:
        picked = [c for c in picked if c.get("expect")]

    who = personas() if any(c.get("as") for c in picked) else {}

    (ROOT / "site").mkdir(exist_ok=True)
    (ROOT / "site" / ".evals-driver.js").write_text(DRIVER)
    subprocess.run(["docker", "cp", str(ROOT / "site" / ".evals-driver.js"),
                    f"{LIBRECHAT}:/app/api/.evals-driver.js"],
                   check=True, capture_output=True)

    stamp = time.strftime("%Y-%m-%dT%H%M")
    OUT.mkdir(parents=True, exist_ok=True)
    results = []

    for a in live:
        for c in picked:
            if c.get("guides"):
                applies = a["slug"] in c["guides"]
            else:
                applies = (c["id"] in WELCOME_ONLY) if a["slug"] == "welcome" \
                    else (c["id"] not in WELCOME_ONLY)
            if not applies:
                continue
            print(f"  {a['slug']:<18} {c['id']}", flush=True)
            convo = parent = None
            turns = []
            for i, text in enumerate(c["turns"]):
                started = say(a["id"], a["slug"], text, convo, parent,
                              who.get(c.get("as")))
                # A rejected request is NOT a failed case.  The reachability
                # precheck guards the model being down; nothing guarded the
                # request being refused, and an SSE `event: error` scored as
                # 102 silent "returned nothing" rows that read exactly like a
                # contract failure.  Silence is not a result -- stop and say so.
                body = started.get("body") or ""
                if "event: error" in body or started.get("status") != 200:
                    sys.exit(
                        f"\nthe chat route refused the request "
                        f"({a['slug']}, status {started.get('status')}):\n"
                        f"  {body.strip()[:300]}\n"
                        "Nothing was scored -- recording these as failures "
                        "would be a lie about the prompts."
                    )
                try:
                    convo = json.loads(body)["conversationId"]
                except Exception:
                    turns.append({"ask": text, "reply": "", "error": started})
                    break
                got, parent, tools, types = reply(convo, i, args.timeout)
                turns.append({"ask": text, "reply": got, "tools": tools,
                              "types": types})
                if not got:
                    break
            verdict, why = score(c, turns)
            if verdict:
                print(f"  {'':<18} {verdict}" + (f" — {'; '.join(why)}" if why else ""),
                      flush=True)
            results.append({"guide": a["slug"], "agent": a["name"], "model": a["model"],
                            "case": c["id"], "pattern": c["pattern"],
                            "as": c.get("as"), "verdict": verdict, "why": why,
                            "passes_when": c["passes_when"],
                            "breaks_at": c.get("breaks_at"),
                            "conversationId": convo, "turns": turns})

    (OUT / f"{stamp}.json").write_text(json.dumps(results, indent=2))

    lines = [f"# Eval run {stamp}", "",
             "Scored by a human against each case's passing condition.  "
             "An empty reply fails every case.", ""]
    for r in results:
        lines += [f"## {r['guide']} — {r['case']} ({r['pattern']})", ""]
        if r.get("as"):
            lines += [f"*Asked as:* the eval {r['as']} persona", ""]
        if r.get("verdict"):
            lines += [f"**Calls: {r['verdict']}**"
                      + (" — " + "; ".join(r["why"]) if r["why"] else "")
                      + "  *(the prose is still yours to read)*", ""]
        lines += [f"*Passes when:* {r['passes_when']}", ""]
        for i, t in enumerate(r["turns"], 1):
            lines += [f"**Turn {i} — asked:** {t['ask']}", ""]
            # What it DID, before what it said.  For the tool cases the
            # call is the score: roster_stage where enroll belonged, or a
            # roster_apply nobody said yes to, reads fine in the prose.
            for tc in t.get("tools") or []:
                name = (tc.get("name") or "(unreadable)").split("_mcp_")[0]
                lines += [f"- called `{name}` with `{tc.get('args')}` → "
                          f"{(tc.get('output') or '').strip()[:300]!r}"]
            if r.get("as") and not t.get("tools"):
                lines += [f"- *(no tool calls — content blocks: {t.get('types')})*"]
            if t.get("tools") or r.get("as"):
                lines += [""]
            lines += ["**Replied:**", "",
                      "> " + (t["reply"].replace("\n", "\n> ") if t["reply"]
                              else "*(nothing — this fails)*"), ""]
    (OUT / f"{stamp}.md").write_text("\n".join(lines) + "\n")
    print(f"\n  {len(results)} cases -> site/evals/{stamp}.md")
    scored = [r for r in results if r.get("verdict")]
    if scored:
        bad = [r for r in scored if r["verdict"] != "PASS"]
        print(f"  calls: {len(scored) - len(bad)}/{len(scored)} pass"
              + ("" if not bad else " — " + ", ".join(
                  f"{r['guide']}/{r['case']} {r['verdict']}" for r in bad)))
        if args.check and bad:
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
