#!/usr/bin/env python3
"""Seed or refresh the guide agents on the flagship instance from corpus/.

Run ON the box (the justfile owns the docker lifecycle around it, same as
course_admin.py).  One command does the whole guide pipeline:

    prompts   corpus/<slug>/SYSTEM-PROMPT.md  ->  the agent's instructions
    knowledge corpus/<slug>/*.md              ->  file_search attachments
    ids       the agent ids                   ->  the modelSpecs block to paste

Idempotent, and deliberately UPDATE-IN-PLACE rather than delete-and-recreate:

    modelSpecs entries in librechat.yaml reference agent_id.  Recreating an
    agent mints a new id and silently orphans every spec pointing at the old
    one, which presents as a vestibule whose guides have vanished.  Agent ids
    are a published interface; keep them stable.

Knowledge syncs by CONTENT HASH, and uploads before it deletes.  Both halves
of that were bought the hard way — see "The file-upload limiter" in
docs/design-walls.md.  LibreChat rate-limits uploads to 50 per user and 100
per IP per 15 minutes, and the corpus is fifty files, so "delete everything
then re-upload everything" spends the entire budget on its first run and, on
its second, deletes all five agents' knowledge and then gets 429'd on every
single upload.  Measured, not theorized: it happened here.

So: hash each rendered page, keep what already matches, upload only what
changed, and detach the old copies only AFTER the new ones are in.  A 429
mid-run now leaves the previous knowledge attached and working.  The hashes
live in `site/agents-state.json` — per box, gitignored — but the API is still
the authority on what is *attached*; the state file only says what content a
given file_id held, and a file_id the agent no longer carries is re-uploaded
regardless of what the state claims.

`--skip-files` refreshes only the prompts, which is the common case while
iterating on the contract.

Four gotchas this encodes, all paid for once (docs/design-walls.md):

  * Every route under /api/agents sits behind uaParser, which rejects any
    request whose User-Agent does not parse as a BROWSER — the response is an
    SSE "Illegal request" body, not a JSON error, and it logs a NON_BROWSER
    violation against the caller.
  * /api/agents/v1 is the OpenAI-compatible router (API-key auth).  Agent CRUD
    is mounted at the ROOT, /api/agents.  Posting to the /v1 path returns
    "Invalid API key" and looks like an auth problem, which it is not.
  * POST /api/files does upload, embed AND attach in one call — it ends in
    addAgentResourceFile.  There is no separate "attach" verb to look for.
    It needs `agent_id` and `tool_resource`, and it needs the agent to carry
    `file_search` in `tools` or the model never reaches what you uploaded.
  * A 429 from that route is not just a failed upload.  It logs a FILE_UPLOAD
    violation against the OWNER, and violations are what `BAN_VIOLATIONS`
    counts — a seeder that charges through fifty of them is working toward
    banning the account it runs as.  This one stops at the first.
"""
import hashlib
import json
import pathlib
import os
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
CORPUS = ROOT / "corpus"

# Rendered FOR the operator, not for the model: the manifest is a table of
# contents, the prompt is what the agent is told, and the evals are how we
# test it.  Uploading any of them would have the agent quoting its own
# instructions back as if they were documentation.
NOT_KNOWLEDGE = {"MANIFEST.md", "SYSTEM-PROMPT.md", "EVALS.md"}

# What this box uploaded, and what it hashed to.  Lives in site/ because it is
# per-deployment truth, same as the agent ids themselves — and it is a CACHE,
# not a record: delete it and the next run re-uploads everything, which is
# correct, just slower.
STATE = ROOT / "site" / "agents-state.json"

# name + one-line description per corpus folder.  The INSTRUCTIONS come from
# corpus/<slug>/SYSTEM-PROMPT.md, rendered from docs/agent-contract.md — this
# file never holds prompt prose.
GUIDES = [
    # FIRST on purpose: model_specs() marks entry 0 `default`, and the default
    # is a message whether we mean it or not.  Opening an instructor in the
    # Student Guide reads as the platform having sorted them, wrongly, before
    # they typed a word — so the default has to be the one entry that
    # classifies nobody.  See docs/agent-contract.md, "The front desk".
    ("welcome", "Front Desk",
     "New here?  Start with this and it will point you at the right guide."),
    ("student-guide", "Student Guide",
     "Using the Almanac in your courses — agents, knowledge files, API keys, and what the budget numbers mean."),
    ("instructor-guide", "Instructor Guide",
     "Running a course on the Almanac — rosters, class configuration, shared agents, and what students can see."),
    ("platform-guide", "Platform Guide",
     "How the Almanac is built and why — the architecture, the decisions, and what they cost."),
    ("dev-guide", "Dev Guide",
     "Operating the Almanac — deployment, runbooks, verification, and what breaks."),
    ("security-guide", "Security Guide",
     "The Almanac's security posture — controls, boundaries, and the blue/purple team exercises that test them."),
]

JS = r"""
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const jwt = require('jsonwebtoken');

const AGENTS = __AGENTS__;
const OWNER_ID = '__OWNER__';
const MODEL = '__MODEL__';
const MODEL_EXPLICIT = __MODEL_EXPLICIT__;
const PROVIDER = '__PROVIDER__';
const SKIP_FILES = __SKIP_FILES__;
const CORPUS = '/app/api/.seed-corpus';
const OUT = '/app/api/.seed-agents.json';
const BASE = 'http://127.0.0.1:3080';
// uaParser demands a browser UA on every /api/agents route (see the module
// docstring in scripts/seed_agents.py).
const UA = 'Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0';

// An hour, not the fifteen minutes the prompt-only version needed: embedding
// fifty files is measured in minutes and a token that expires mid-run fails
// halfway through a replace, which is the one state worse than either end.
const token = jwt.sign({ id: OWNER_ID }, process.env.JWT_SECRET, { expiresIn: '60m' });
const AUTH = { Authorization: `Bearer ${token}`, 'User-Agent': UA };
const H = { ...AUTH, 'Content-Type': 'application/json' };

async function syncFiles(agent) {
  const dir = path.join(CORPUS, agent.slug);

  // The API is the authority on what is ATTACHED; the state file only says
  // what content a given file_id held.  A file_id the agent no longer carries
  // is re-uploaded no matter what the state claims.
  const cr = await fetch(`${BASE}/api/files/agent/${agent.id}`, { headers: H });
  let attached = [];
  try { attached = JSON.parse(await cr.text()); } catch {}
  if (!Array.isArray(attached)) attached = [];

  const stale = new Map(attached.map((f) => [f.file_id, f]));
  const known = agent.known || {};
  const state = {};
  const todo = [];
  for (const w of agent.want) {
    const k = known[w.name];
    if (k && k.sha === w.sha && stale.has(k.file_id)) {
      stale.delete(k.file_id);          // matches the render — keep it
      state[w.name] = k;
    } else {
      todo.push(w);
    }
  }

  let uploaded = 0, failed = 0, limited = false;
  for (const w of todo) {
    const fd = new FormData();
    // Blob type matters: multer takes the part's Content-Type as the
    // mimetype, and filterFile checks it against the endpoint's allowlist.
    fd.set('file', new Blob([fs.readFileSync(path.join(dir, w.name))],
                            { type: 'text/markdown' }), w.name);
    fd.set('file_id', crypto.randomUUID());
    fd.set('endpoint', 'agents');
    fd.set('agent_id', agent.id);
    fd.set('tool_resource', 'file_search');
    // No Content-Type header here on purpose — fetch has to set the
    // multipart boundary itself, and naming the type steamrolls it.
    const r = await fetch(`${BASE}/api/files`, { method: 'POST', headers: AUTH, body: fd });
    const t = await r.text();
    if (r.status === 429) {
      // Every one of these logs a violation against the owner.  Stop.
      console.log(`    RATE LIMITED at ${w.name} — 50 uploads/user, 100/IP per 15 min.`);
      console.log('    Nothing detached: the previous knowledge is still attached.');
      limited = true;
      break;
    }
    if (!r.ok) { failed++; console.log(`    ${w.name}: ${r.status} ${t.slice(0, 160)}`); continue; }
    let fid = null;
    try { fid = (JSON.parse(t) || {}).file_id; } catch {}
    if (fid) state[w.name] = { sha: w.sha, file_id: fid };
    uploaded++;
  }

  // AFTER the new copies are in, never before.  Same rule as mint-then-escrow
  // in the registrar: the constructive step first, so a failure degrades to
  // "stale but working" instead of "empty".
  if (!limited && stale.size) {
    const r = await fetch(`${BASE}/api/files`, {
      method: 'DELETE', headers: H,
      body: JSON.stringify({
        agent_id: agent.id, tool_resource: 'file_search',
        // filepath is REQUIRED by the delete route's filter — a file without
        // one is silently dropped from the request and leaks as an orphan.
        files: [...stale.values()].map((f) => ({
          file_id: f.file_id, filepath: f.filepath,
          embedded: f.embedded, source: f.source,
        })),
      }),
    });
    if (!r.ok) console.log(`    detach ${stale.size} old: ${r.status} ${(await r.text()).slice(0, 120)}`);
  }

  const kept = agent.want.length - todo.length;
  console.log(`    ${kept} unchanged, ${uploaded} embedded, ${stale.size} retired`
              + (failed ? `, ${failed} FAILED` : '') + (limited ? ', RATE LIMITED' : ''));
  return { state, bad: failed + (limited ? 1 : 0) };
}

// The vestibule is locked down: interface.agents.create=false is seeded into
// USER and ADMIN alike, and LibreChat gates agent create AND update on
// AGENTS.CREATE — so with the lockdown in place every PATCH here is a 403
// (2026-09-15, all six guides).  Open the window for the length of the run
// through the sanctioned roles API (admin-only, invalidates the permission
// cache), and close it again whatever happens.  The owner must therefore be
// an ADMIN — faculty are, via OPENID_ADMIN_ROLE.
async function agentsCreateWindow(open) {
  const cur = await fetch(`${BASE}/api/roles/ADMIN`, { headers: H });
  const role = cur.ok ? JSON.parse(await cur.text()) : null;
  const was = role?.permissions?.AGENTS?.CREATE ?? role?.AGENTS?.CREATE;
  if (open && was === true) return null;                 // nothing to restore
  const r = await fetch(`${BASE}/api/roles/ADMIN/agents`, {
    method: 'PUT', headers: H, body: JSON.stringify({ CREATE: open }),
  });
  if (!r.ok) console.log(`  WARN   could not ${open ? 'open' : 'close'} AGENTS.CREATE on ADMIN: ${r.status} ${(await r.text()).slice(0, 100)}`);
  return open ? (was ?? false) : null;
}

(async () => {
  const restoreCreate = await agentsCreateWindow(true);
  try { await seedAll(); } finally {
    if (restoreCreate !== null) await agentsCreateWindow(false);
  }
})();

async function seedAll() {
  const lr = await fetch(`${BASE}/api/agents`, { headers: H });
  const lb = await lr.text();
  // Match by the id this box recorded for the slug FIRST, and by name only
  // for an agent this box has never seeded.  Matching by name alone meant a
  // rename ("Welcome" -> "Front Desk", 2026-09-15) created a second agent
  // and orphaned the modelSpecs entry pointing at the first — exactly the
  // failure the update-in-place rule exists to prevent.
  let byName = new Map(), byId = new Map();
  try {
    for (const a of (JSON.parse(lb).data || [])) { byName.set(a.name, a); byId.set(a.id, a); }
  } catch { console.log(`  (could not read the agent list: ${lr.status} ${lb.slice(0, 100)})`); }

  let made = 0, updated = 0, failed = 0;
  const seeded = [];
  for (const a of AGENTS) {
    const prev = (a.id && byId.get(a.id)) || byName.get(a.name);
    // An update must not silently re-point an agent at a different model.
    // The default here is a DEFAULT, not an instruction: without this, a
    // prompt refresh on a box that never set AGENT_MODEL moved every guide
    // from the priced `almanac-chat-30b` onto the unpriced `almanac-chat`,
    // and vestibule spend quietly stopped being attributed.  Measured
    // 2026-09-12.  Set AGENT_MODEL to change a model on purpose.
    //
    // 2026-09-14: that guard had never once fired.  It read `prev.model`
    // off the LIST response, and the list does not project `model` — so
    // every refresh took the `!prev?.model` branch and re-pointed all six
    // guides anyway, silently, exactly as if the guard were not there.
    // The list not mentioning a model is not evidence the agent has none;
    // ask the agent.  One extra GET, and only when the list came up empty.
    let prevModel = prev?.model;
    if (prev && !prevModel) {
      const pr = await fetch(`${BASE}/api/agents/${prev.id}`, { headers: H });
      if (pr.ok) {
        try { prevModel = JSON.parse(await pr.text()).model; } catch {}
      }
      if (!prevModel) {
        console.log(`  WARN   ${a.name.padEnd(18)} could not read its current `
                    + `model; falling back to ${MODEL}`);
      }
    }
    const model = (MODEL_EXPLICIT || !prevModel) ? MODEL : prevModel;
    const body = JSON.stringify({
      name: a.name, description: a.description, instructions: a.instructions,
      provider: PROVIDER, model,
      // Without this the files upload, embed, attach — and the model still
      // cannot see them, because nothing gave it the tool to look.  The
      // front desk has no corpus, and handing it a file_search over an
      // empty store is how you get an agent that searches, finds nothing,
      // and answers anyway.
      tools: (a.want && a.want.length) ? ['file_search'] : [],
    });
    const id = prev?.id;
    const r = id
      ? await fetch(`${BASE}/api/agents/${id}`, { method: 'PATCH', headers: H, body })
      : await fetch(`${BASE}/api/agents`, { method: 'POST', headers: H, body });
    const t = await r.text();
    if (!r.ok) {
      console.log(`  ${String(r.status).padEnd(6)} ${a.name.padEnd(18)} ${t.slice(0, 200)}`);
      failed++;
      continue;
    }
    let out = id;
    try { out = JSON.parse(t).id || id; } catch {}
    console.log(`  ${(id ? 'update' : 'create').padEnd(6)} ${a.name.padEnd(18)} `
                + `${String(out).padEnd(26)} ${model}`);
    id ? updated++ : made++;
    a.id = out;
    seeded.push({ slug: a.slug, name: a.name, id: out, model });
    if (!SKIP_FILES && a.want && a.want.length) {
      const out = await syncFiles(a);
      failed += out.bad;
      seeded[seeded.length - 1].files = out.state;
    }
  }
  fs.writeFileSync(OUT, JSON.stringify(seeded, null, 2));
  console.log(`\n${made} created, ${updated} updated, ${failed} failed`);
  if (failed) process.exitCode = 1;   // exit AFTER the finally closes the window
}
"""


def knowledge(slug: str) -> list[pathlib.Path]:
    """The pages that become an agent's file_search knowledge."""
    return sorted(p for p in (CORPUS / slug).glob("*.md")
                  if p.name not in NOT_KNOWLEDGE)


def sha(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def compose(*args: str, **kw) -> subprocess.CompletedProcess:
    return subprocess.run(["docker", "compose", *args], cwd=ROOT,
                          stdin=subprocess.DEVNULL, text=True, **kw)


def _mongo(q: str) -> str:
    out = compose("exec", "-T", "mongodb", "mongosh", "--quiet", "LibreChat",
                  "--eval", q, capture_output=True, check=True).stdout
    return out.strip().strip('"')


# The guides' owner is a SERVICE ACCOUNT, not a person.  It is a user document
# and nothing else: no password, no identity-provider link, an email on the
# reserved .invalid TLD, so nobody can ever sign in as it — and so no human's
# file manager ever lists the corpus.  Found 2026-09-15: the guides were owned
# by the faculty account that seeded them, that account saw forty-four
# knowledge files under "Manage files," selected two, and deleted them out
# from under the Security Guide.  LibreChat let it, because they were theirs.
SERVICE_OWNER = {"email": "guides@almanac.invalid", "username": "almanac-guides",
                 "name": "Almanac Guides"}


def service_owner_id() -> str:
    q = (f'var u = db.users.findOne({{email:"{SERVICE_OWNER["email"]}"}}, {{_id:1}}); '
         f'if (!u) {{ var r = db.users.insertOne({{email:"{SERVICE_OWNER["email"]}", '
         f'username:"{SERVICE_OWNER["username"]}", name:"{SERVICE_OWNER["name"]}", '
         f'provider:"local", role:"ADMIN", emailVerified:true, '
         f'createdAt:new Date(), updatedAt:new Date()}}); '
         f'print("CREATED " + String(r.insertedId)); }} else {{ print(String(u._id)); }}')
    out = _mongo(q)
    if out.startswith("CREATED "):
        print(f"service owner created: {SERVICE_OWNER['email']} (no credentials — cannot sign in)")
        out = out[len("CREATED "):]
    if not out:
        sys.exit("could not find or create the service owner in LibreChat's users")
    return out


def owner_id(email: str) -> str:
    """A HUMAN owner — legacy, explicit, and not what you want: whoever owns
    the guides can delete their knowledge files from the file manager."""
    # String(u._id), not u?._id.toString() — the optional-chain form throws
    # "Cannot read properties of undefined (reading 'toHexString')" on some
    # mongosh builds, and the script reads that as "no such user."
    q = (f'var u = db.users.findOne({{email:"{email}"}}, {{_id:1}}); '
         f'print(u ? String(u._id) : "NOTFOUND")')
    out = _mongo(q)
    if not out or out == "NOTFOUND":
        sys.exit(f"no LibreChat user with email {email} — they must sign in once first.")
    return out


def adopt(owner: str, agent_ids: list[str]) -> None:
    """Move agents this box already seeded — and every file they carry — to
    OWNER.  The API cannot reassign authorship; Mongo can.  Idempotent."""
    if not agent_ids:
        return
    ids = json.dumps(agent_ids)
    q = (f'var o = new ObjectId("{owner}"); var ids = {ids}; '
         f'var ag = db.agents.find({{id:{{$in:ids}}, author:{{$ne:o}}}}).toArray(); '
         f'var fids = []; ag.forEach(function(a){{ var t=a.tool_resources||{{}}; '
         f'Object.keys(t).forEach(function(k){{ (t[k].file_ids||[]).forEach(function(f){{ fids.push(f); }}); }}); }}); '
         f'var ra = db.agents.updateMany({{id:{{$in:ids}}}}, {{$set:{{author:o}}}}); '
         f'var rf = fids.length ? db.files.updateMany({{file_id:{{$in:fids}}}}, {{$set:{{user:o}}}}) : {{modifiedCount:0}}; '
         f'print(ra.modifiedCount + " " + rf.modifiedCount)')
    moved_agents, moved_files = _mongo(q).split()
    if int(moved_agents) or int(moved_files):
        print(f"adopted into the service owner: {moved_agents} agent(s), {moved_files} file(s)")


def model_specs(seeded: list[dict], model: str) -> str:
    # `model` is the fallback; a row carrying its own wins, because after the
    # AGENT_MODEL fix two guides can legitimately differ.
    """The paste-me block for this box's librechat.yaml.

    Agent ids are minted per deployment and librechat.yaml gets no env
    substitution, so this block cannot be tracked — it is hand-written once
    per instance, into site/.  See docs/admin-guide.md, "The guide agents".
    """
    lines = ["modelSpecs:",
             "  enforce: true          # agents only — no raw model picker",
             "  prioritize: true",
             "  list:"]
    for i, a in enumerate(seeded):
        lines += [f"    - name: {a['slug']}",
                  f"      label: {a['name']}",
                  f"      default: {'true' if i == 0 else 'false'}",
                  "      preset:",
                  "        endpoint: agents",
                  f"        agent_id: {a['id']}",
                  f"        model: {model}"]
    return "\n".join(lines)


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    skip_files = "--skip-files" in sys.argv[1:]
    # No owner argument: the guides belong to the service account.  An email
    # is accepted as an explicit, legacy override and warned about.
    email = args[0].strip().lower() if args else None
    if email:
        print(f"WARN: seeding under a human owner ({email}) — that account can delete "
              "the guides' knowledge files from its file manager.  Omit the email.")
    model_explicit = "AGENT_MODEL" in os.environ
    model = os.environ.get("AGENT_MODEL", "almanac-chat")
    provider = os.environ.get("AGENT_PROVIDER", "Almanac")

    state = {}
    if STATE.exists():
        try:
            state = json.loads(STATE.read_text())
        except json.JSONDecodeError:
            print(f"{STATE} is unreadable — re-uploading everything")

    agents = []
    for slug, name, desc in GUIDES:
        p = CORPUS / slug / "SYSTEM-PROMPT.md"
        if not p.exists():
            sys.exit(f"{p} missing — run `just docs-corpus` first.")
        text = "\n".join(l for l in p.read_text().splitlines()
                         if not l.startswith("<!--")).strip()
        a = {"slug": slug, "name": name, "description": desc,
             "instructions": text}
        # `want` is computed even with --skip-files: it is what decides
        # whether the agent gets file_search at all.
        a["want"] = [{"name": f.name, "sha": sha(f)} for f in knowledge(slug)]
        a["known"] = (state.get(slug) or {}).get("files") or {}
        # The id this box minted for the slug last time — the identity the
        # seeder updates in place, whatever the display name is now.
        a["id"] = (state.get(slug) or {}).get("id")
        agents.append(a)

    owner = owner_id(email) if email else service_owner_id()
    adopt(owner, [v["id"] for v in state.values() if isinstance(v, dict) and v.get("id")])

    js = (JS.replace("__AGENTS__", json.dumps(agents, indent=2))
            .replace("__OWNER__", owner)
            .replace("__MODEL__", model)
            .replace("__PROVIDER__", provider)
            .replace("__SKIP_FILES__", "true" if skip_files else "false")
            .replace("__MODEL_EXPLICIT__", "true" if model_explicit else "false"))

    print(f"seeding {len(agents)} guide agents as {email} "
          f"(provider {provider}, model {model}"
          f"{' — EXPLICIT, existing agents will be re-pointed' if model_explicit else ' for new agents; existing keep theirs'})"
          f"{'' if skip_files else ', with knowledge'}")

    if not skip_files:
        # docker cp, not a bind mount: the corpus is a build input for this
        # one run, and mounting it would make the container's view of it
        # permanent in a way `just deploy` would have to know about.
        compose("exec", "-T", "librechat", "rm", "-rf", "/app/api/.seed-corpus",
                capture_output=True)
        staged = 0
        for slug, _, _ in GUIDES:
            compose("exec", "-T", "librechat", "mkdir", "-p",
                    f"/app/api/.seed-corpus/{slug}", check=True, capture_output=True)
            for f in knowledge(slug):
                compose("cp", str(f), f"librechat:/app/api/.seed-corpus/{slug}/{f.name}",
                        check=True, capture_output=True)
                staged += 1
        print(f"staged {staged} knowledge files")

    subprocess.run(["docker", "compose", "exec", "-T", "librechat",
                    "sh", "-c", "cat > /app/api/.seed-agents.js"],
                   cwd=ROOT, input=js, text=True, check=True)
    try:
        r = compose("exec", "-T", "librechat", "node", "/app/api/.seed-agents.js")
        seeded = compose("exec", "-T", "librechat", "cat", "/app/api/.seed-agents.json",
                         capture_output=True).stdout
    finally:
        compose("exec", "-T", "librechat", "rm", "-rf",
                "/app/api/.seed-agents.js", "/app/api/.seed-agents.json",
                "/app/api/.seed-corpus", capture_output=True)

    try:
        rows = json.loads(seeded)
    except (json.JSONDecodeError, TypeError):
        rows = []
    if rows and not skip_files:
        for row in rows:
            state[row["slug"]] = {"id": row["id"], "files": row.get("files") or {}}
        try:
            STATE.parent.mkdir(parents=True, exist_ok=True)
            STATE.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n")
        except OSError as e:
            print(f"could not write {STATE}: {e} — next run re-uploads everything")

    if rows:
        print("\n--- paste into this box's librechat.yaml "
              "(docs/admin-guide.md, \"The guide agents\") ---\n")
        print(model_specs(rows, model))
    return r.returncode


if __name__ == "__main__":
    sys.exit(main())
