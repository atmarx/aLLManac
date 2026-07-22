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
    instructors:                    # may be several; all get manager + upload
      - prof.vex@northwinds.edu
    budget: 5                       # per-student USD, clamped server-side
    models: [almanac-chat]          # what minted keys may call
    group: ""                       # globus backend: group UUID (course-create fills)
    students: []                    # file backend only; globus derives from the group
    aliases: {}                     # legacy non-email user_ids, passthrough to render
```

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

## Keys — mint shape, budgets, rotation

**One key per (student × course).**  A student in two courses holds two
keys; spend attributes to the right course because the tag differs:

```json
{
  "user_id":   "amaya@northwinds.edu",          // joins to chat spend
  "models":    ["almanac-chat"],
  "max_budget": 5,
  "metadata":  { "owner": "engr301", "tags": ["owner:engr301"] }
}
```

Same shape `just key` mints today — the registrar automates it, not
reinvents it.  The Enterprise walls stay routed-around (rig-probed on our
pins): `metadata.tags` not top-level tags; **rotation = delete + re-mint**
(`/key/regenerate` is licensed); students never touch the LiteLLM UI (the
5-DB-user SSO wall stays irrelevant).

- **Mint at apply**, not at first login.  Email is the user_id; the key
  works the moment they accept the invite.  No-shows surface in the
  anti-join, not in mint failures.
- **Budgets:** course default (`budget:`), clamped by
  `REGISTRAR_MAX_BUDGET` server-side — no prompt, however persuasive, mints
  past the clamp.  `set_budget` applies to future mints; live bumping of
  existing keys via `/key/update` is a verify-at-implementation.
- **Rotation preserves the meter:** re-mint sets
  `max_budget = course_budget − ledger_spend_so_far` (floor $0.50), so
  rotating a key isn't a budget reset.  Ledger history is untouched either
  way.

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

---

## Phasing

**Phase 1 — standalone, demo realm, end-to-end** (the make-or-break:
`prof.vex` pastes the mock roster in chat, `stu.amaya` asks `my_key`, the
key hits the gateway from the workbench):
compose + bao-init + registrar with `file` backend · stage/apply · mint ·
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

## Verify at implementation

- OpenBao static-seal support at our pin (else: `bao-unseal` recipe path).
- `/key/update` live budget changes on our LiteLLM pin (else: budgets apply
  at next mint/rotation).
- Globus Groups API invite semantics for emails with no Globus identity yet.
- Practical tool-argument ceiling for jumbo rosters on our LibreChat pin
  (fallback: `roster_stage` accepts chunks, stages merge).

## Open questions (Andrew's call)

1. **Budget defaults** — $5/student default, $25 clamp: right numbers?
   Lifetime-per-semester, or monthly reset (`budget_duration`)?
2. **Course slugs** — free-form (`engr301`) or term-prefixed
   (`2026fa-engr301`)?  Semester rollover and the spend rollup's tidiness
   both hang off this.
3. **Multi-instructor day one** — `instructors:` is already a list; any
   reason to restrict to one?
