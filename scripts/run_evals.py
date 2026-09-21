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
    run on it: xdocker03's host python is PEP668-managed with no pip, so
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
    body = CONTRACT.read_text()
    out = []

    table = body.split("## The evals", 1)[1].split("\n---", 1)[0]
    for line in table.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) == 4 and re.fullmatch(r"[A-Z]\d+", cells[0]):
            out.append({"id": cells[0], "pattern": cells[1],
                        "turns": [cells[2].strip('"')], "passes_when": cells[3]})

    section = body.split("## The multi-turn cases", 1)
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


def say(agent_id: str, spec: str, text: str,
        convo: str | None, parent: str | None) -> dict:
    payload = {"owner": OWNER, "agent_id": agent_id, "spec": spec, "text": text,
               "conversationId": convo, "parentMessageId": parent}
    (ROOT / "site" / ".evals-in.json").write_text(json.dumps(payload))
    subprocess.run(["docker", "cp", str(ROOT / "site" / ".evals-in.json"),
                    f"{LIBRECHAT}:/app/api/.evals-in.json"],
                   check=True, capture_output=True)
    raw = dc(LIBRECHAT, "node", "/app/api/.evals-driver.js")
    return json.loads(raw.strip().splitlines()[-1])


def reply(convo: str, after: int, timeout: int) -> tuple[str, str | None]:
    """Poll the conversation for the next assistant message.  Returns (text, id)."""
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
         ".join('\\n').trim() || m.text || ''};}))" % convo)
    deadline = time.time() + timeout
    while time.time() < deadline:
        msgs = json.loads(dc(MONGO, "mongosh", "--quiet", "LibreChat", "--eval", q))
        if len(msgs) > after:
            m = msgs[after]
            return (m.get("text") or ""), m.get("messageId")
        time.sleep(3)
    return "", None


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
            applies = (c["id"] in WELCOME_ONLY) if a["slug"] == "welcome" \
                else (c["id"] not in WELCOME_ONLY)
            if not applies:
                continue
            print(f"  {a['slug']:<18} {c['id']}", flush=True)
            convo = parent = None
            turns = []
            for i, text in enumerate(c["turns"]):
                started = say(a["id"], a["slug"], text, convo, parent)
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
                got, parent = reply(convo, i, args.timeout)
                turns.append({"ask": text, "reply": got})
                if not got:
                    break
            results.append({"guide": a["slug"], "agent": a["name"], "model": a["model"],
                            "case": c["id"], "pattern": c["pattern"],
                            "passes_when": c["passes_when"],
                            "breaks_at": c.get("breaks_at"),
                            "conversationId": convo, "turns": turns})

    (OUT / f"{stamp}.json").write_text(json.dumps(results, indent=2))

    lines = [f"# Eval run {stamp}", "",
             "Scored by a human against each case's passing condition.  "
             "An empty reply fails every case.", ""]
    for r in results:
        lines += [f"## {r['guide']} — {r['case']} ({r['pattern']})", "",
                  f"*Passes when:* {r['passes_when']}", ""]
        for i, t in enumerate(r["turns"], 1):
            lines += [f"**Turn {i} — asked:** {t['ask']}", "",
                      "**Replied:**", "",
                      "> " + (t["reply"].replace("\n", "\n> ") if t["reply"]
                              else "*(nothing — this fails)*"), ""]
    (OUT / f"{stamp}.md").write_text("\n".join(lines) + "\n")
    print(f"\n  {len(results)} cases -> site/evals/{stamp}.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
