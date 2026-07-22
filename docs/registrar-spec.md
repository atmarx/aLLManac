# The Registrar — rosters, keys, and the escrow

*Spec, not code.  Written 2026-07-22, before any implementation, on purpose.*

The usage-mcp service answered "what happened?"  The registrar answers "who's
enrolled, and what do they hold?"  Same office, other window.

**The shape in one paragraph:** an instructor is marked as teaching a course —
that single act lets them sign into the chat they already use and paste their
class roster at an agent.  The registrar (a new MCP service, sibling of
usage-mcp) parses it, shows them exactly what it understood, and on their
confirmation: syncs the course's **managed group** (Globus in production, the
mock realm in demo), mints one **LiteLLM virtual key per student per course**,
and **escrows every key in OpenBao**.  Students retrieve their own key by
asking the chat.  Spend rolls up per-user-per-course through the ledger we
already read.  There is no separate site to manage — for the instructor or
anyone else.  **The chat is the admin surface.**

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
                     │ LibreChat │──────────────┬──────────────┐
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
| **registrar** (`alm-registrar`) | Chat-facing MCP tools: roster staging/apply, key retrieval, budgets.  Contains the reconciler — the only code path that ever holds minting credentials. | yes |
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
red-team pass:

- LibreChat injects **`X-User-Email` / `X-User-Role`** per user into MCP
  headers, plus a bearer token (`REGISTRAR_MCP_TOKEN`) proving the call comes
  from the chat itself.
- **Identity is never a tool argument.**  A prompt can pick a course slug;
  it can never pick whose keys come back.
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
      course: 300                   # THE cap — semester, hard, chat + keys, one pool
      key_fuse: 5                   # per vAPI key hard ceiling (leak blast radius)
      advisory_weekly: 2            # what "on pace" means in usage tools; never blocks
    models: [almanac-chat]          # what minted keys may call
    group: ""                       # globus backend: group UUID (course-create fills)
    students: []                    # file backend only; globus derives from the group
    aliases: {}                     # legacy non-email user_ids, passthrough to render
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

1. `roster_stage(course, roster_text)` → parses, diffs against current
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

New compose service (`alm-openbao`, digest-pinned at implementation), file
storage backend on its own volume, `127.0.0.1:8200` for the operator CLI.

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

---

## The chat path — which course is this conversation?

The question that decides whether the semester cap is real: chat traffic
today rides **one shared service credential** (attributed per-student by the
`x-litellm-end-user-id` header, but budgeted by nothing).  The vAPI keys
cover opencode and scripts — so how does a *LibreChat conversation* get a
course?  Do we inject each student's per-course key into their chats?

**We don't.**  LibreChat has no "pick your course at login" concept, and
per-student key injection would mean `user_provided` endpoints — every
student pasting (and re-pasting, per course) secrets into a settings panel.
Wrong friction for freshmen.  Instead, three pieces that already exist do
the job:

1. **The course agent IS the course picker.**  The product premise was
   always "each course co-edits its shared agent" — group-ACL'd, found in
   the marketplace.  A student doesn't declare a course at login; they open
   the course's agent when they start a conversation.  Switching courses =
   switching agents.  Login stays untouched.
2. **One custom endpoint per course, carrying a course service key.**  The
   registrar mints one extra key per course — a *service* key, no student
   `user_id`, `team_id` = the course team — and renders a per-course
   endpoint block (`Almanac — ENGR 301`) into the LibreChat config.  The
   course agent pins to its course's endpoint.  New course = render +
   chat restart, an operator-time event that `just course` already owns.
3. **Attribution keeps working exactly as shipped.**  The per-user header
   stamps `end_user` on every chat request regardless of which key carried
   it — so per-student advisory numbers fold chat + vAPI spend, same as
   usage-mcp does today.

What this buys: **chat spend drains the same course-team pool as the vAPI
keys** — the semester cap governs everything with no per-student secret
handling in the browser, no login flow surgery, and course context that's
visible in the UI (you're talking *to* your course, not configuring it).

The loose thread, named honestly: endpoints defined in the config are
visible to every signed-in user, so a chem student could manually select
the ENGR 301 endpoint and drain a pool they're not enrolled in.  Three
fences, in order: the admin panel's **per-group config overrides** may gate
endpoint visibility properly (verify at implementation — it's the same
panel that already owns share-groups); the registrar can **detect**
cross-course spend from the ledger (an `end_user` outside the roster
wearing the course's tag) and tell the instructors; and course_usage puts a
name on every row anyway — freeloading on a metered, attributed service is
a short career.  If the panel gate proves weak AND detection finds real
abuse, the fallback is `user_provided` per-course endpoints for real
per-student chat budgets — documented, not built.

`my_key` stays what it was: the take-home credential for opencode, scripts,
and laptops.  Chat never needs it.

---

## Phasing

**Phase 1 — standalone, demo realm, end-to-end** (the make-or-break:
`prof.vex` pastes the mock roster in chat, `stu.amaya` asks `my_key`, the
key hits the gateway from the workbench):
compose + bao-init + registrar with `file` backend · course team + service
key + per-course endpoint render (the chat path) · stage/apply · mint ·
escrow · `my_key` · roster.yaml render · librechat.yaml wiring
(`mcpServers.almanac-registrar`, allowedAddresses) · smoke checks · admin
guide recipe for the "Course Setup" agent.

**Phase 2 — Globus:** the registrar's confidential client, managed-group
create/invite/reconcile, manager-role authority, `--adopt` mode.  Flip
`GROUPS_BACKEND=globus`; the login side already has the broker runbook in
the admin guide.

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
10. *(2026-07-22)* **Chat gets no per-student keys.**  Course agents on
    per-course endpoints carrying team-scoped service keys; students pick
    the course by picking its agent.  `user_provided` is the documented
    fallback, not the plan.

## Verify at implementation

- OpenBao static-seal support at our pin (else: `bao-unseal` recipe path).
- `/key/update` live budget changes on our LiteLLM pin (else: budgets apply
  at next mint/rotation).
- **Team budget enforcement mechanics** on our pin: blocking behavior at
  exhaustion, and that a service key + member keys drain one pool the way
  the rig says they should.
- `soft_budget` + `budget_duration: 7d` in OSS for gateway-side pace alerts
  (the advisory layer works from the ledger regardless).
- **Admin panel per-group config overrides** as the endpoint-visibility
  fence (the cross-course loose thread above).
- Globus Groups API invite semantics for emails with no Globus identity yet.
- Practical tool-argument ceiling for jumbo rosters on our LibreChat pin
  (fallback: `roster_stage` accepts chunks, stages merge).

## Open questions (Andrew's call)

1. **Course slugs** — free-form (`engr301`) or term-prefixed
   (`2026fa-engr301`)?  Semester rollover, team names, and the spend
   rollup's tidiness all hang off this.  (Last one standing.)
2. **Course cap default** — the semester pool needs a number at
   `just course` time ($300 in the example is a placeholder).  Per-course
   funding reality is yours to name; the registrar just enforces it.
