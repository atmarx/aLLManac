#!/usr/bin/env python3
"""Seed or refresh the guide agents on the flagship instance from corpus/.

Run ON the box (the justfile owns the docker lifecycle around it, same as
course_admin.py).  Idempotent, and deliberately UPDATE-IN-PLACE rather than
delete-and-recreate:

    modelSpecs entries in librechat.yaml reference agent_id.  Recreating an
    agent mints a new id and silently orphans every spec pointing at the old
    one, which presents as a vestibule whose guides have vanished.  Agent ids
    are a published interface; keep them stable.

Two gotchas this encodes, both paid for once (docs/design-walls.md):

  * Every route under /api/agents sits behind uaParser, which rejects any
    request whose User-Agent does not parse as a BROWSER — the response is an
    SSE "Illegal request" body, not a JSON error, and it logs a NON_BROWSER
    violation against the caller.
  * /api/agents/v1 is the OpenAI-compatible router (API-key auth).  Agent CRUD
    is mounted at the ROOT, /api/agents.  Posting to the /v1 path returns
    "Invalid API key" and looks like an auth problem, which it is not.
"""
import json
import os
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
CORPUS = ROOT / "corpus"

# name + one-line description per corpus folder.  The INSTRUCTIONS come from
# corpus/<slug>/SYSTEM-PROMPT.md, rendered from docs/agent-contract.md — this
# file never holds prompt prose.
GUIDES = [
    ("student-guide", "Student Guide",
     "Using the Almanac in your courses — agents, knowledge files, API keys, and what the budget numbers mean."),
    ("instructor-guide", "Instructor Guide",
     "Running a course on the Almanac — rosters, class configuration, shared agents, and what students can see."),
    ("platform-guide", "Platform Guide",
     "How the Almanac is built and why — the architecture, the decisions, and what they cost."),
    ("dev-guide", "Dev Guide",
     "Operating the Almanac — deployment, runbooks, verification, and what breaks."),
    ("securitybot3000", "SecurityBot3000",
     "The Almanac's security posture — controls, boundaries, and the blue/purple team exercises that test them."),
]

JS = r"""
const jwt = require('jsonwebtoken');
const AGENTS = __AGENTS__;
const OWNER_ID = '__OWNER__';
const MODEL = '__MODEL__';
const PROVIDER = '__PROVIDER__';
const BASE = 'http://127.0.0.1:3080';
// uaParser demands a browser UA on every /api/agents route (see the module
// docstring in scripts/seed_agents.py).
const UA = 'Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0';

(async () => {
  const token = jwt.sign({ id: OWNER_ID }, process.env.JWT_SECRET, { expiresIn: '15m' });
  const H = { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json',
              'User-Agent': UA };

  const lr = await fetch(`${BASE}/api/agents`, { headers: H });
  const lb = await lr.text();
  let byName = new Map();
  try { for (const a of (JSON.parse(lb).data || [])) byName.set(a.name, a.id); }
  catch { console.log(`  (could not read the agent list: ${lr.status} ${lb.slice(0,100)})`); }

  let made = 0, updated = 0, failed = 0;
  for (const a of AGENTS) {
    const body = JSON.stringify({
      name: a.name, description: a.description, instructions: a.instructions,
      provider: PROVIDER, model: MODEL,
    });
    const id = byName.get(a.name);
    const r = id
      ? await fetch(`${BASE}/api/agents/${id}`, { method: 'PATCH', headers: H, body })
      : await fetch(`${BASE}/api/agents`, { method: 'POST', headers: H, body });
    const t = await r.text();
    if (r.ok) {
      let out = id;
      try { out = JSON.parse(t).id || id; } catch {}
      console.log(`  ${(id ? 'update' : 'create').padEnd(6)} ${a.name.padEnd(18)} ${out}`);
      id ? updated++ : made++;
    } else {
      console.log(`  ${String(r.status).padEnd(6)} ${a.name.padEnd(18)} ${t.slice(0, 200)}`);
      failed++;
    }
  }
  console.log(`\n${made} created, ${updated} updated, ${failed} failed`);
  if (failed) process.exit(1);
})();
"""


def compose(*args: str) -> str:
    return subprocess.run(["docker", "compose", *args], cwd=ROOT,
                          capture_output=True, text=True, check=True).stdout


def owner_id(email: str) -> str:
    q = (f'db.users.findOne({{email:"{email}"}},{{_id:1}})?._id.toString() '
         f'?? "NOTFOUND"')
    out = compose("exec", "-T", "mongodb", "mongosh", "--quiet", "LibreChat",
                  "--eval", q).strip().strip('"')
    if not out or out == "NOTFOUND":
        sys.exit(f"no LibreChat user with email {email} — they must sign in once first.")
    return out


def main() -> int:
    if len(sys.argv) < 2:
        sys.exit("usage: seed_agents.py <owner-email>   (the account that will own the guides)")
    email = sys.argv[1].strip().lower()
    model = os.environ.get("AGENT_MODEL", "almanac-chat")
    provider = os.environ.get("AGENT_PROVIDER", "Almanac")

    agents = []
    for slug, name, desc in GUIDES:
        p = CORPUS / slug / "SYSTEM-PROMPT.md"
        if not p.exists():
            sys.exit(f"{p} missing — run `just docs-corpus` first.")
        text = "\n".join(l for l in p.read_text().splitlines()
                         if not l.startswith("<!--")).strip()
        agents.append({"name": name, "description": desc, "instructions": text})

    js = (JS.replace("__AGENTS__", json.dumps(agents, indent=2))
            .replace("__OWNER__", owner_id(email))
            .replace("__MODEL__", model)
            .replace("__PROVIDER__", provider))

    print(f"seeding {len(agents)} guide agents as {email} "
          f"(provider {provider}, model {model})")
    # Written into /app/api so node resolves jsonwebtoken from the app's
    # node_modules — require() resolves from the SCRIPT's path, not cwd.
    subprocess.run(["docker", "compose", "exec", "-T", "librechat",
                    "sh", "-c", "cat > /app/api/.seed-agents.js"],
                   cwd=ROOT, input=js, text=True, check=True)
    try:
        r = subprocess.run(["docker", "compose", "exec", "-T", "librechat",
                            "node", "/app/api/.seed-agents.js"],
                           cwd=ROOT, stdin=subprocess.DEVNULL)
    finally:
        subprocess.run(["docker", "compose", "exec", "-T", "librechat",
                        "rm", "-f", "/app/api/.seed-agents.js"],
                       cwd=ROOT, stdin=subprocess.DEVNULL,
                       capture_output=True)
    return r.returncode


if __name__ == "__main__":
    sys.exit(main())
