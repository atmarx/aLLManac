# The Registrar — rosters, keys, and the escrow

*Spec, not code.  Written 2026-07-22, before any implementation, on purpose.*

The usage-mcp service answered "what happened?"  The registrar answers "who's
enrolled, and what do they hold?"  Same office, other window.

**The shape in one paragraph:** an instructor is marked as teaching a course —
that single act gives the course **its own LibreChat instance** at its own
hostname, with the instructor as its admin, and lets them paste their class
roster at an agent in the chat they already use.  The registrar (a new MCP
service, sibling of usage-mcp) parses it, shows them exactly what it
understood, and on their confirmation: syncs the course's **managed group**
(Globus in production, the mock realm in demo), mints one **LiteLLM virtual
key per student per course**, and **escrows every key in OpenBao**.  Students
retrieve their own key by asking the chat.  Spend rolls up per-user-per-course
through the one shared ledger.  There is no separate site to manage — for the
instructor or anyone else.  **The chat is the admin surface**, and each course
gets its own.

This stands up fully separate from Root Cellar.  The original plan had the
cellar's capability substrate minting these; that docking is deferred, not
dead — the seams (group id + email) are marked below so the cellar can plug
in later without rework.

---

## The cast

```
                        Browser (chat — the ONLY surface)
                           │
                     ┌─────┴─────┐   per-user trusted headers
                     │LibreChat×N│──────────────┬──────────────┐
                     └─────┬─────┘              ▼              ▼
                           │              ┌──────────┐   ┌───────────┐
                    OIDC   │              │ usage-mcp│   │ registrar │ NEW
                           ▼              │ (reads   │   │ (rosters, │
                     ┌──────────┐         │  ledger) │   │  minting, │
                     │ Keycloak │         └──────────┘   │  custody) │
                     │ (Globus  │                        └─────┬─────┘
                     │  broker) │             ┌────────────────┼────────────────┐
                     └──────────┘             ▼                ▼                ▼
                                        ┌──────────┐    ┌──────────┐    ┌────────────┐
                                        │ LiteLLM  │    │ OpenBao  │    │ Globus     │
                                        │ /key/*   │    │ escrow   │    │ Groups API │ NEW
                                        └────┬─────┘    │ (NEW svc)│    │ (Phase 2)  │
                                             ▼          └──────────┘    └────────────┘
                                    one central upstream credential:
                                    Azure AI Foundry · campus vLLM · Ollama
```

| Piece | Job | New? |
|---|---|---|
| **registrar** (`alm-registrar`) | Chat-facing MCP tools: roster staging/apply, key retrieval, budgets.  Contains the reconciler — the only code path that ever holds minting credentials — and the fleet renderer (instance env, Keycloak client, Caddy vhost). | yes |
| **LibreChat fleet** (`alm-chat-<slug>`) | One instance per course — the course's own chat, panel, Meili, and Mongo *database*, at its own hostname.  Registrar-rendered, one loop rolls them all.  See **Tenancy**. | yes |
| **OpenBao** (`alm-openbao`) | Key custody.  KV v2 mount `almanac/`, file audit device, AppRole for the registrar.  Custody, not metering. | yes |
| **Groups backend** | Where the roster truth lives.  Driver interface: `file` (demo), `globus` (production — the managed-group pattern).  | yes |
| **LiteLLM** | Mints and enforces the virtual keys; meters everything into the ledger.  Unchanged except key traffic. | no |
| **usage-mcp** | Keeps answering usage questions.  **Zero code changes** — the registrar renders its `roster.yaml` for it. | no |

Division of labor, one line each: **bao = custody, LiteLLM = metering,
usage-mcp = reporting, registrar = enrollment.**  OpenBao is never in the
stats path — per-user-per-course tracking comes from the ledger (user_id ×
owner tag), which we already proved live.

---

## Identity & trust — the contract, extended not invented

Identical to usage-mcp, because it survived contact with production and a
red-team pass — plus one header tenancy makes possible:

- LibreChat injects **`X-User-Email` / `X-User-Role`** per user into MCP
  headers, plus a bearer token (`REGISTRAR_MCP_TOKEN`) proving the call comes
  from the chat itself.
- **`X-Course: <slug>`** — a *literal* the registrar renders into each
  instance's config, so every MCP call carries which course's house it came
  from.  Same trust class as the bearer token: students can't touch the
  rendered YAML.  The header is **context, not authorization** — the roster
  is still checked; the header just means nobody types a course slug again.
- **Identity is never a tool argument — and now neither is the course.**
  A prompt can pick a date range; it can never pick whose keys come back or
  which course's door it's standing in.
- Reachable only on the compose network + a `127.0.0.1` bind for smoke.
- `mcpSettings.allowedAddresses` gets `registrar:8080` (the SSRF guard —
  ask pipeline #14 why we remember this).

Authority is layered on top of identity:

| Act | Who | Checked against |
|---|---|---|
| retrieve / rotate a key | its owner only | header email == escrow path |
| stage / apply a roster | instructor of THAT course | `instructors:` list (file) or group **manager** role (globus) — ADMIN role alone is not enough |
| create / close a course | operator | justfile on the box (chat-admin tool is Phase 3) |

**Nobody but the owner ever sees a key — including faculty.**  Instructors
get custody *status* (minted / rotated-at / fetched-at), never secrets.

---

## The managed-group pattern (the Root Cellar idea, standalone)

Projects own data; **groups own people**.  A course is a group with a
syllabus.

- The registrar gets its **own Globus confidential client** — *not* the
  Keycloak broker client.  The broker authenticates humans; the registrar
  administers groups.  Different jobs, different blast radii, independently
  revocable.
- `just course engr301 "ENGR 301" prof.vex@northwinds.edu` → the registrar
  client **creates** group `almanac-engr301`, holds the admin role itself,
  and invites the instructor as group **manager**.  That manager role IS the
  "marked as instructor" act — it's what unlocks roster upload in chat.
  The same act provisions the course's tenancy: LiteLLM team + service key,
  Keycloak client (with the instructor mapped to its `admin` client role),
  the instance render, and the Caddy vhost — finished with a graceful edge
  reload.  One command, a course exists.
- `roster_apply` reconciles membership: invites the missing (Globus emails
  them; they accept with the same campus identity Keycloak brokers for
  login), removes the dropped.  **The group is the roster truth.**
- Email is the join key across all three worlds: group member ↔
  `LIBRECHAT_USER_EMAIL` ↔ LiteLLM `user_id`.  Same rule usage-mcp already
  lives by (`trustEmail` is on at the broker).
- Adopting an existing campus/SIS-fed group instead of creating one: later
  mode, same seam — `group:` in the course record is just a UUID, however it
  got there.

**Demo realm (`GROUPS_BACKEND=file`):** no Globus account required to run
the make-or-break test.  The course record's `students:` list is the truth,
and everything downstream (mint, escrow, render) behaves identically.  The
driver interface is three verbs: `members(group)`, `add(group, email)`,
`remove(group, email)`.

---

## Course records — `registrar/courses.yaml`

Registrar-owned, gitignored (real rosters are student emails), seeded from a
committed example on first `up` — the roster.yaml pattern, reused:

```yaml
courses:
  engr301:
    name: "ENGR 301 — Engineering Design"
    instructors:                    # several from day one — the first real course
      - prof.vex@northwinds.edu     # has two, and every course has TAs
    tas: []                         # same authority as instructors in v1 (see below)
    budgets:
      course: 1000                  # THE cap — per term, hard, chat + keys, one pool
      key_fuse: 5                   # per vAPI key hard ceiling (leak blast radius)
      advisory_weekly: 2            # what "on pace" means in usage tools; never blocks
    college: cci                    # optional — unions the college's model pack in
    models: [almanac-chat]          # what this course's keys + instance may call
    group: ""                       # globus backend: group UUID (course-create fills)
    students: []                    # file backend only; globus derives from the group
    aliases: {}                     # legacy non-email user_ids, passthrough to render

colleges:                           # a college is a MODEL PACK, not an org chart —
  cci:                              # the registrar needs their models, not their deans
    models: [cci-llama]             # registered once at the gateway; see Model routing
```

**TAs are instructors in v1.**  Both lists land as group managers with roster
and usage authority — every course has TAs, and inventing a fourth
permission tier before anyone's asked for one is how admin panels are born.
If a TA-shaped abuse case ever shows up, splitting the role is a list rename.

**`usage-mcp/roster.yaml` becomes a render.**  After every reconcile the
registrar writes it (shared volume; usage-mcp live-reloads — that's why it
needs zero changes).  The render's header says "generated by the registrar —
edit courses.yaml or the group, not this file."  Existing hand-edits get
absorbed into `courses.yaml` once at migration.

---

## Roster upload — paste first, and why

The instructor's contract is **paste**: copy the column out of Banner /
Canvas / a spreadsheet, paste it at the agent.  Tool arguments arrive
verbatim — deterministic, no retrieval in the path.  A few hundred emails
fits comfortably.

Parsing is liberal on purpose: the registrar extracts every email-shaped
token from whatever arrives (CSV with headers, TSV, newlines, commas,
Banner's junk columns) and **reports what it ignored**.  Don't demand a
format from someone who exports one spreadsheet a semester.

**Dropped files:** LibreChat uploads land in RAG — chunked retrieval, which
may hand the agent a *lossy* view.  A roster that silently drops row 47 is
worse than no upload.  So file-drop isn't blocked (text reaches the tool
however it reaches), but the safety is structural:

**Two-phase, always.**

1. `roster_stage(roster_text)` → the course comes from the instance's
   `X-Course` header, never an argument — an instructor can only stage the
   course whose house they're standing in.  Parses, diffs against current
   membership, returns the exact plan — *adds (n), removes (n), unchanged
   (n), ignored lines (n, with samples)* — and a `stage_id` (15-min TTL,
   in-memory).  **Nothing changes.**
2. `roster_apply(stage_id)` → executes that plan and nothing else, then
   reports per-student outcomes (invited / minted / escrowed / failed-why).

The instructor confirms what the registrar *parsed*, not what they *meant to
paste*.  `course_usage`'s "not started yet" anti-join backstops stragglers a
week later.

Removals revoke the student's key for that course (`/key/delete`) and drop
group membership.  Escrow versions are retained — custody history survives
un-enrollment.

---

## Keys & budgets — three layers, one pool

The budget model, decided 2026-07-22:

| Layer | Enforced by | Blocks? | What it's for |
|---|---|---|---|
| **Course-semester cap** | LiteLLM **team budget** (one team per course) | **yes — the real cap** | The actual money.  Chat AND vAPI keys drain this one pool. |
| **Key fuse** | per-key `max_budget` | yes | Blast radius of a leaked/runaway vAPI key — *not* a pacing tool. |
| **Weekly advisory** | usage tools (reporting only) | never | What "on pace" feels like to a student.  Easier to hold in your head than a semester number. |

**The reconciler creates one LiteLLM team per course** (teams and team
budgets are OSS — rig-probed; *team-admin role* is the Enterprise part, and
we don't need it because the registrar administers via master key).  Every
credential the course generates joins that team, so the semester cap is
enforced across modalities in one place.

**One vAPI key per (student × course)**, minted into the course team:

```json
{
  "user_id":   "amaya@northwinds.edu",          // joins to chat spend
  "team_id":   "almanac-engr301",               // drains the course pool
  "models":    ["almanac-chat"],
  "max_budget": 5,                              // the fuse, not the budget
  "metadata":  { "owner": "engr301", "tags": ["owner:engr301"] }
}
```

Same shape `just key` mints today plus `team_id`.  The Enterprise walls
stay routed-around (rig-probed on our pins): `metadata.tags` not top-level
tags; **rotation = delete + re-mint** (`/key/regenerate` is licensed);
students never touch the LiteLLM UI (the 5-DB-user SSO wall stays
irrelevant).

- **Mint at apply**, not at first login.  Email is the user_id; the key
  works the moment they accept the invite.  No-shows surface in the
  anti-join, not in mint failures.
- **Fuse defaults:** $5, clamped by `REGISTRAR_MAX_BUDGET` ($25)
  server-side — no prompt, however persuasive, mints past the clamp.
  `set_budget` applies to future mints; live bumping of existing keys via
  `/key/update` is a verify-at-implementation.
- **Rotation preserves the fuse meter:** re-mint sets
  `max_budget = key_fuse − ledger_spend_so_far` (floor $0.50), so rotating
  a key isn't a fuse reset.  Ledger history is untouched either way.
- **Weekly advisory** is computed from the ledger (`end_user` + owner tag —
  data usage-mcp already reads); `my_usage` learns to say *"$1.40 of your
  ~$2/week pace"*.  If our pin's `soft_budget` + `budget_duration: 7d`
  prove out in OSS, the gateway can also emit pace alerts — verify at
  implementation, but the advisory layer never depends on it.

---

## The escrow — OpenBao

New compose service (`alm-openbao`, digest-pinned at implementation),
**integrated (raft) storage** on its own volume — single node, but raft is
the backend with the online snapshot API
(`bao operator raft snapshot save`), and the one-VM backup story below
leans on it.  `127.0.0.1:8200` for the operator CLI.

**Paths (KV v2, mount `almanac/`):**

```
almanac/courses/<slug>/students/<email>   {key, minted_at, budget, key_id}
almanac/system/litellm-master             Phase 3 — see below
```

**`just bao-init`** — the once-per-box ritual: init (single share) → unseal
→ enable the file **audit device** → mount kv2 → write policies → enable
AppRole → mint the registrar's role.  The unseal key and the registrar's
`role_id`/`secret_id` land in `.env` via the existing `fill` pattern.  The
**root token prints once** and goes in the operator's password manager — it
does not live in `.env`.

**Unattended restarts:** static auto-unseal from `BAO_UNSEAL_KEY` if our
OpenBao pin supports the static seal stanza (verify at implementation);
otherwise `just up` gains a `bao-unseal` dependency that reads the same var.
Either way the box reboots without a human.

**Honesty box.**  Escrow on the same box, unseal key in the same `.env` —
this is not an HSM and we will not pretend otherwise.  What it actually
buys, and why it's still worth a container:

1. **Chat-facing code holds zero minting credentials** — the tool plane can
   read the caller's own escrow path and nothing else.
2. **Custody is policy-scoped and audit-logged** — every key read is a
   line in the audit device with who/what/when.  `.env` files don't keep
   receipts.
3. **Rotation is versioned** — KV v2 history is the custody trail.
4. **It's where the LiteLLM master key goes to stop living in `.env`**
   (Phase 3): reconciler fetches it at boot via AppRole; `.env` keeps only
   bootstrap creds.

Students never talk to bao directly — `my_key` is mediated by the registrar
(one surface, the whole point).  The bao-native alternative (OIDC auth
method against Keycloak + a policy templated on the identity's email, so a
student can only ever read `almanac/courses/+/students/<their-email>`) is
documented here as the break-glass path if key retrieval must survive the
chat being down.  Not built in v1.

---

## The mint boundary — one container, two planes

The registrar is one service with a hard internal seam:

- **Tool plane** (chat-reachable): parses, stages, diffs, reads the
  *caller's* escrow paths.  Holds the MCP bearer secret and a bao token
  scoped to read-by-identity.  **No LiteLLM master key.  No Globus client
  secret.**
- **Reconcile plane**: consumes confirmed stages.  The only code that loads
  the minting credential, the Globus client, and the bao write role.

v1 keeps both in one process (module seam, credentials loaded only inside
the reconciler); splitting into a worker container later is mechanical
because the interface is already "a queue of confirmed plans."

**Blast radius, stated plainly:** a fully hostile prompt that reaches the
tools can stage a roster (inert until an instructor confirms it), read the
caller's own keys, and spend the caller's own budget.  It cannot read
anyone else's key (path is derived from headers), mint outside a confirmed
stage, exceed the budget clamp, or claim to be someone else.  Roster text
is data: email extraction by pattern, everything else discarded and
reported — a CSV cell reading "ignore previous instructions" parses to
zero emails.  Standing invitation to council-redteam before v1 ships;
they've caught real ones in this repo.

---

## Model routing — one upstream credential, many keys

Unchanged in architecture, extended in config.  The central credential
lives at the gateway; virtual keys only ever name **model names**:

```yaml
model_list:
  - model_name: almanac-chat            # today: INFERENCE_BASE_URL (vLLM/Ollama/…)
    litellm_params:
      model: os.environ/INFERENCE_MODEL
      api_base: os.environ/INFERENCE_BASE_URL
      api_key: os.environ/INFERENCE_API_KEY
  # - model_name: almanac-chat          # Azure AI Foundry variant / addition:
  #   litellm_params:
  #     model: azure_ai/<deployment>
  #     api_base: os.environ/AZURE_FOUNDRY_ENDPOINT
  #     api_key: os.environ/AZURE_FOUNDRY_KEY
```

Two blocks with the same `model_name` = load-balanced group; different
names (`almanac-chat` / `almanac-cloud`) = per-course model lists decide
who may call cloud.  Either way: **swap the upstream, minted keys never
notice** — they're pinned to names, not endpoints.  Foundry spend meters
into the same ledger rows as local tokens, so per-user-per-course tracking
is identical whether the tokens came from a campus GPU or Azure.

**Costs are the gateway's job and it's good at it:** cloud models price
from LiteLLM's model map (Azure included, when the metadata's there);
campus models carry whatever we say they cost —
`input_cost_per_token`/`output_cost_per_token` in the model block.  Price
local tokens at an amortized GPU rate (or $0.— and let token counts be the
measure) and every budget layer above works identically for both.

**College endpoints — bring your own inference.**  A college with its own
GPU box for its own courses is three knobs, no new machinery:

1. **Register once** at the gateway: `cci-llama` → their api_base, their
   key (a credential — escrow path `almanac/system/models/<name>`).
2. **Scope by course**: the college's model pack unions into its courses'
   `models:` lists (the `college:` field above); the reconciler stamps the
   list onto the course **team and every key in it** — the gateway refuses
   the model to anyone else, which is enforcement, not visibility.
3. **Visibility is free** — tenancy already did it.  The instance's
   endpoint renders its course's model list, so `cci-llama` *appears as an
   option* only inside CCI courses' instances.  In the shared-instance
   design this would have been another gating project; here it's a render
   detail.

The one policy question per college endpoint: **does their metal charge
the pool?**  Price it $0 (their gift to their courses — the dollar cap
protects the *paid* upstreams, token counts still meter) or price it real
(chargeback recovery).  Per-model knob, college's call, registrar
indifferent.

---

## Tenancy — one LibreChat instance per course

*Decided 2026-07-22 (Andrew's proposition, and it wasn't insane).*

> "How do you keep the courses apart in LibreChat?"
> "That's the neat part — we don't."
> — Andrew, explaining the architecture to a colleague, 2026-07-23

The question that decides whether the semester cap is real: how does a
*LibreChat conversation* get a course?  Injecting each student's per-course
key into chat means `user_provided` endpoints — freshmen pasting secrets
into settings panels.  Sharing one instance means course context by agent
selection plus an endpoint-visibility fence we'd have to verify held.  The
actual answer is tenancy: **course = instance.**

**The load-bearing sentence: shared control plane, per-course data plane.**

| Plane | Services | Count |
|---|---|---|
| Control (never fragments) | Keycloak (+ Globus broker), LiteLLM + ledger, OpenBao, usage-mcp, registrar, Caddy edge | **one each** |
| Data (per course) | LibreChat + its Mongo *database* + its Meili + admin panel | **one per course** |

Mongo runs one container, N databases.  pgvector/RAG likely shared (verify
file-id isolation).  **Meilisearch is the awkward child** — LibreChat's
index names don't namespace, so it's one small Meili per course (~100MB)
or search off per instance: a knob in the course record, default on.

What the container boundary buys, versus the fences it replaces:

- **Cross-course endpoint access dies structurally.**  An instance only
  *contains* its own course's credential.  No panel-gating verify, no
  ledger-side freeloader detection as a security layer (it stays as
  telemetry).  A container boundary beats a visibility toggle.
- **Faculty admin scoping fixes itself.**  The shared design made every
  faculty member ADMIN of the one instance (`OPENID_ADMIN_ROLE=faculty` —
  realm-wide).  Per-instance, each course's OIDC client carries an `admin`
  **client role**, mapped to that course's instructors and TAs only:
  `OPENID_ADMIN_ROLE_PARAMETER_PATH=resource_access.<client>.roles`.  Full
  control of *their* house, no key to anyone else's.
- **Enrollment gates the front door.**  Any realm user can *authenticate*
  to any client by default — which would let an un-enrolled student sign
  into a course instance and chat on its service key.  Closed at login:
  each course client also carries a `member` client role, granted and
  revoked by roster reconcile, and the instance requires it
  (`OPENID_REQUIRED_ROLE`, the LibreChat-native gate — verify var at our
  pin).  Not on the roster → bounced at the door, not caught at the till.
  The registrar's roster sync thus maintains three things per student:
  group membership, the vAPI key, and the `member` grant.
- **Blast radius**: a hostile agent tool, a leaked JWT secret, a bad
  plugin — one course's conversations, not the campus's.
- **Drift is the feature, not the bug.**  Instructors get their hands
  dirty deep in their own weeds — their agents, their marketplace, their
  share-groups (which are now just their course's teams), their interface
  toggles, their own admin panel — the same freedom we're building for
  students.  The rails: everything **DB-stored is theirs**; everything
  **rendered is the registrar's** (image pins, YAML, env, routes — uniform,
  in git, rolled by one loop).  Sovereign tenants, standardized plumbing.
- Students already live this model: Canvas is per-course.  Course
  conversations don't commingle — FERPA-flavored bow included.

**What it costs, stated plainly:** uniform operational fan-out.  ~500–600MB
per course all-in (chat + Meili + panel share), N containers to roll on a
LibreChat CVE — but same pinned image + rendered config = one `just` loop,
not N snowflakes.  Twenty courses ≈ 12–15GB on the app box.  Policy
fan-out inside one shared instance was the alternative, and that's the
kind that generates tickets.

**The money layer survives untouched.**  One LiteLLM, one ledger.  Each
instance's endpoint carries its course's **team-scoped service key** —
"one master key per course," minted by the registrar like any other key,
escrowed in bao like any other key.  Chat spend and vAPI-key spend drain
the same course-team pool; the semester cap governs everything.  The
per-user header stamps `end_user` on every chat request exactly as
shipped, so per-student advisory numbers fold chat + vAPI spend — and the
instance implies the course even before the header names the student.
usage-mcp reads across the whole fleet without a line changing.

**Auth fan-out is free because the broker exists.**  Each instance is one
more OIDC client in the realm we already script (registrar mints clients
via the Keycloak admin API; exact redirect URIs, no wildcards).  Globus
stays **one** registration — Keycloak's.  Without the broker this idea
costs N manual registrations at developers.globus.org; with it, a for-loop.

**The two lanes, side by side** — a student in
`engr301-2026fall.aisandbox.northwinds.edu` spends either way:

| Lane | Credential | Student attribution | Course attribution |
|---|---|---|---|
| Stays in chat | the instance's **service key** | `end_user` header (as shipped) | the key's team + tag |
| Asks `my_key()`, goes to opencode | their **personal vAPI key** | the key's `user_id` | the key's team + tag |

`my_key()` takes **zero arguments** — the instance's `X-Course` header
already knows whose house the ask came from, so the key that comes back is
for *this* course, no slug typed, no cross-course confusion possible.  Both
lanes drain the same course-team pool and fold into the same per-student
numbers in usage-mcp (which already splits chat vs API in `my_usage`).
Chat never needs the personal key.

---

## Routing — one door, many rooms

Hostname-based, Caddy, wildcard DNS — ports are for compose files, not
syllabi.

- **DNS**: `*.{ALMANAC_DOMAIN}` → the box.  One wildcard record.
- **TLS**: one wildcard cert via **DNS-01** (wildcards require it; the
  Azure `acme_dns` block already sketched in `caddy/Caddyfile` graduates
  from comment to config — root-cellar's delegated-zone guide is the
  pattern).  Public boxes without wildcard DNS can fall back to per-vhost
  HTTP-01; LAN stays on the internal CA.  All three modes already exist in
  the edge profile — this extends, not invents.
- **Vhosts**: the registrar renders one small file per course into a
  shared volume the edge imports (`import /etc/caddy/fleet/*.caddy`):

  ```
  engr301.{$ALMANAC_DOMAIN} {
      tls {$EDGE_TLS}
      reverse_proxy alm-chat-engr301:3080
  }
  engr301-admin.{$ALMANAC_DOMAIN} {     # single label — wildcard-covered
      tls {$EDGE_TLS}
      reverse_proxy alm-panel-engr301:3000
  }
  ```

  Rendered files over hostname-label placeholder tricks, deliberately: a
  vhost you can `cat` at 3am beats cleverness, and label-index math breaks
  the moment the domain depth changes between campus and lab deployments.
- **Reload**: course creation is an operator act, and the justfile already
  owns docker — `just course` finishes with a graceful
  `compose exec edge caddy reload`.  **No docker socket ever enters the
  registrar** (or any chat-adjacent container); the registrar renders
  files, the justfile does lifecycle.
- Shared surfaces keep their names: `auth.` (Keycloak), `gateway.`
  (LiteLLM admin), and the apex or `www.` can hold a course directory page
  eventually — a static render is a Phase 3 nicety.

---

## The venue — one VM on Azure Local

*Decided 2026-07-22: the research compute facility is off the table; the
almanac lands on Azure Local as a standalone Linux VM (Debian) with Docker,
running everything **except inference**.*

This costs the plan nothing, and that was the point all along — the
justfile's deployment contract has always been "a box with Docker."  The
venue is a variable, not an architecture:

- **Inference was never coming aboard.**  The vLLM stack is deliberately
  its own compose project on GPU metal elsewhere; `INFERENCE_BASE_URL` /
  the Foundry block point wherever the tokens actually live.  The VM needs
  zero GPUs.
- **CI retargets, not rewrites**: Woodpecker's deploy step ssh's to a
  hostname.  New box, new variable, same pipeline.
- **Azure Container Apps, rejected for the right reason**: per-course
  containers with rendered configs and local volumes map miserably onto
  managed platforms — Mongo becomes Cosmos-with-a-mongo-accent, the ledger
  becomes managed Postgres, Meili becomes a problem, and the bill becomes a
  committee.  One VM keeps the data gravity in volumes, the deploy contract
  in the justfile, and the whole thing restorable by one person on one bad
  morning.
- **DNS-01 is now on home turf** — the wildcard cert's Azure `acme_dns`
  block was built for exactly this RFC-1918 shape, and the DNS zone is
  already in the neighborhood.

**Capacity math, so growth is a formula instead of a surprise:**

```
RAM  ≈ 8 GB shared stack + 0.6 GB × courses
        2 courses  →  ~10 GB      (today)
        5 courses  →  ~11 GB      (fall)
       20 courses  →  ~20 GB      (the "explosive" case)
vCPU ≈ 8 is comfortable past 20 courses — tokens burn elsewhere; chat
       instances mostly wait on humans and the gateway.
Disk ≈ 128–256 GB SSD.  Mongo per course is modest; the ledger grows with
       requests (prune policy is a Phase 3 chore, not a launch blocker).
```

Provision **8 vCPU / 32 GB / 256 GB** and forget about it until ~20
courses; it's a VM — resize is a reboot, not a migration.

**Backups — the whole point of one VM:**

`just backup` (nightly via cron/systemd timer) produces one timestamped
tarball: `mongodump --archive` (every course DB in one pass) ·
`pg_dump` litellm (**the ledger**) + keycloak ·
`bao operator raft snapshot save` (**the escrow**, online, consistent) ·
`.env` + `registrar/courses.yaml` + the fleet renders + caddy data (certs
— cheap to keep, annoying to reissue).  **Meili is excluded on purpose** —
it's derived from Mongo and rebuilds on boot.  Ship the tarball off-box
with restic to Azure Blob (the hedge rides again); the VM is the working
copy, never the only copy.

`just restore <tarball>` is the mirror image on a fresh VM: compose up,
load dumps, restore the raft snapshot, unseal, smoke.  **The restore drill
is scheduled work, not documentation theater** — see Phase 2.  A backup
that's never been restored is a rumor.

---

## Phasing

**Phase 1 — standalone, demo realm, end-to-end** (the make-or-break, now
two acts: `prof.vex` pastes the mock roster into *the engr301 instance*,
`stu.amaya` asks `my_key`, the key hits the gateway from the workbench —
then a second demo course spawns and **the wall holds**: chem's instructor
can't see engr301's chats, panel, or pool; the mock realm grows a second
course for exactly this):
compose + bao-init + registrar with `file` backend · **instance render**
(chat + panel + Meili + Mongo db + Keycloak client + team + service key +
vhost) · stage/apply · mint · escrow · `my_key` · roster.yaml render ·
per-instance MCP wiring (`mcpServers.almanac-registrar`,
allowedAddresses) · smoke checks that walk the fleet · admin guide recipe
for the "Course Setup" agent.

**Phase 2 — Globus + the drill:** the registrar's confidential client,
managed-group create/invite/reconcile, manager-role authority, `--adopt`
mode.  Flip `GROUPS_BACKEND=globus`; the login side already has the broker
runbook in the admin guide.  Plus `just backup`/`just restore` and the
**restore drill on a scratch VM** — proven once before fall's five courses
enroll, not promised.

**Phase 3 — lifecycle & hardening:** rotation with budget carryover ·
`set_budget` live updates · `just course-close` (revoke all, final render,
archive group) · master key moves into bao · chat-side `course_create` for
platform admins · redteam pass.

**Root Cellar docking (deferred, by design):** the cellar's project groups
and these course groups are the same primitive.  When docking day comes,
either side can consume the other's groups — the interface is a group id
and member emails, nothing almanac-internal.

Out of scope, permanently unless vetoed: a separate admin website (the
entire point is not having one) · SIS API integration (paste beats a Banner
integration project) · per-message rate limits (budgets are the governor).

---

## Decisions made here (veto anytime)

1. Key retrieval is **chat-only, registrar-mediated**; no student-facing
   bao UI in v1.
2. **Mint at apply**, not at first login.
3. Managed groups are **created by the registrar** (`almanac-<slug>`);
   adopting existing groups is a later mode.
4. The registrar gets its **own Globus client** — the Keycloak broker
   client is never reused for group administration.
5. **One container, hard module seam** between tool plane and reconcile
   plane; worker split deferred until needed.
6. **`roster.yaml` becomes a render**; humans edit `courses.yaml` (file
   backend) or the group (globus backend), never the render.
7. **No one but the owner ever retrieves a key** — instructors see custody
   status only.
8. *(2026-07-22, Andrew)* **Budget hierarchy**: course-semester team budget
   is the one true cap; per-key `max_budget` is a leak fuse ($5/$25 stands);
   per-student weekly numbers are advisory and never block.
9. *(2026-07-22, Andrew)* **Multi-instructor from day one** — the first
   course has two, and every course has TAs.  `tas:` list ships in v1 with
   instructor-equivalent authority.
10. *(2026-07-22)* **Chat gets no per-student keys.**  The course
    instance's endpoint carries the team-scoped service key; students pick
    the course by walking into its chat.  `user_provided` is the documented
    fallback, not the plan.
11. *(2026-07-22, Andrew)* **Tenancy: one LibreChat instance per course.**
    Shared control plane (Keycloak, LiteLLM, bao, usage-mcp, registrar,
    edge — one each); per-course data plane (chat, panel, Meili, Mongo
    database).  Instructor drift inside the rendered rails is a feature —
    the same hands-dirty freedom we're building for students.
12. *(2026-07-22, Andrew)* **Routing: Caddy, hostname-based, wildcard
    DNS.**  Wildcard cert via DNS-01; registrar-rendered vhost imports
    (greppable at 3am) over hostname-label tricks; reload rides `just
    course`; no docker socket in any service.
13. *(2026-07-22, Andrew)* **Venue: one Debian VM + Docker on Azure
    Local**, inference external, container-app platforms rejected (managed
    DB sprawl).  One VM to back up, one VM to restore.
14. *(2026-07-22)* **The instance is the course context.**  `X-Course`
    rendered into each instance's MCP config; tools drop their course
    arguments (`my_key()`, `roster_stage(text)`); enrollment gates login
    itself via the `member` client role.  Header = context, roster = authz.
15. *(2026-07-22, by example)* **Slugs are term-qualified, code-first** —
    `engr301-2026fall`, straight from Andrew's own hostname example.
    Rollover = a new course record each term; spend rollups sort
    chronologically for free.  Flag if the example wasn't a decision.

## Verify at implementation

*Phase-1 rig (2026-07-22, this box, exact pins): two courses provisioned
end-to-end — teams at $1000, service + student keys minted into teams and
escrowed (kv2 + AppRole + audit live), instances up behind the edge with
OIDC registered ("configured successfully"), vhosts serving, roster render
live-reloaded by usage-mcp, smoke + fleet-smoke all green.  Items below
marked ✓ closed there.*

- ~~OpenBao static-seal~~ **RESOLVED**: skipped static seal; `just
  bao-unseal` rides `just up` (rig-verified).  Raft snapshot round-trip
  still owed in Phase 2's backup work.
- `/key/update` live budget changes on our LiteLLM pin (else: budgets apply
  at next mint/rotation).
- **Team budget enforcement at exhaustion** — pool-drain blocking still
  owed (needs live inference spend); team create/update + membership ✓
  rig-verified.
- ~~Team/key model-list semantics~~ ✓ **rig-verified**: a team-minted
  student key lists exactly the course models and gets **403** on anything
  else — refusal is gateway-side, which is what college-endpoint scoping
  needs.
- **Fleet identity shape** ✓ rig-verified and documented (.env.example):
  `KC_HOSTNAME=https://auth.<domain>` + `KC_PROXY_HEADERS=xforwarded` +
  edge network alias + `NODE_EXTRA_CA_CERTS` (internal CA) — without them
  instance OIDC discovery fails on issuer mismatch.
- ~~Compose include mechanics~~ ✓ rig-verified on v5.1.4 (`include:` of
  the rendered fleet.yml, stub-seeded by `just _fleet`).
- `soft_budget` + `budget_duration: 7d` in OSS for gateway-side pace alerts
  (the advisory layer works from the ledger regardless).
- **Client-role admin mapping** on our LibreChat pin:
  `OPENID_ADMIN_ROLE_PARAMETER_PATH=resource_access.<client>.roles` per
  instance (the realm-role variant is deployed and working; the client-role
  variant is the same machinery, one path deeper).
- ~~`OPENID_REQUIRED_ROLE` (login gate)~~ **VERIFIED 2026-07-22** against
  LibreChat's docs: `OPENID_REQUIRED_ROLE` + `_PARAMETER_PATH` +
  `_TOKEN_KIND` exist, Keycloak client-role shape documented (roles "can
  be managed within the client or realm settings").  Browser click-test
  still owed at our pin.
- **Raft snapshot save/restore** round-trip on our OpenBao pin (single
  node) — the backup story leans on it.
- **Meili per-course footprint** and the search-off knob; **admin panel**
  against a per-course Mongo database; **RAG API / pgvector** shared-tenancy
  file-id isolation (else pgvector schemas per course).
- **Compose mechanics for rendered instances**: `include:` directive at our
  compose version, vs `-f` stacking in the justfile loop.
- **Wildcard DNS-01** against the campus DNS provider (the Azure block
  exists; other providers = other caddy-dns plugins in the edge build;
  delegation pattern per root-cellar's guide).
- Globus Groups API invite semantics for emails with no Globus identity yet.
- Practical tool-argument ceiling for jumbo rosters on our LibreChat pin
  (fallback: `roster_stage` accepts chunks, stages merge).

## Open questions (Andrew's call)

*None.  All settled 2026-07-22:*

16. *(2026-07-22, Andrew)* **Course cap default: $1000 per term.**
    Overridable per course at `just course` time; the registrar enforces,
    the funding reality decides.
