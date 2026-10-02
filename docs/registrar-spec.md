---
title: How a course gets provisioned
description: The internal record for the registrar — how an instructor's roster becomes a course's own LibreChat instance, a managed group, one minted key per student, and an escrow entry for each.
audience: operator
also_reaches: [builder]
status: draft
owner: marco
tags: [tenancy, isolation, multi-tenant, gateway, attribution, metering, rendered-config, escrow, secrets-management, key-rotation, rbac, course-rollover, openbao, keycloak, litellm, librechat, globus]
tethered_to:
  - registrar/server.py
  - registrar/reconcile.py
  - registrar/render.py
  - registrar/planes/
  - registrar/courses.example.yaml
  - fleet/
  - justfile
---
# The Registrar — rosters, keys, and the escrow

*Spec, not code.  Written 2026-07-22, before any implementation, on purpose.*  Phase 1 and a thin Phase 2a are built since; the notes marked **Built** say where the code went another way, and where this text and the code disagree, the code is the truth.

The usage-mcp service answered "what happened?"  The registrar answers "who's enrolled, and what do they hold?"  Same office, other window.

**The shape in one paragraph:** an instructor is marked as teaching a course — that single act gives the course **its own LibreChat instance** at its own hostname, with the instructor as its admin, and lets them paste their class roster at an agent in the chat they already use.  The registrar (a new MCP service, sibling of usage-mcp) parses it, shows them exactly what it understood, and on their confirmation: syncs the course's **managed group** (Globus in production, the mock realm in demo), mints one **LiteLLM virtual key per student per course**, and **escrows every key in OpenBao**.  Students retrieve their own key by asking the chat.  Spend rolls up per-user-per-course through the one shared ledger.  There is no separate site to manage — for the instructor or anyone else.  **The chat is the admin surface**, and each course gets its own.

This stands up fully separate from Root Cellar.  The original plan had the cellar's capability substrate minting these; that docking is deferred, not dead — the seams (group id + email) are marked below so the cellar can plug in later without rework.

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
| **registrar** (`alm-registrar`) | Chat-facing MCP tools: roster staging/apply, key retrieval, budgets — and, for platform admins, the **census** (`fleet_*`) and agent **nominations**.  Contains the reconciler — the only code path that ever holds minting credentials — and the fleet renderer (instance env, Keycloak client, Caddy vhost, the inventory page). | yes |
| **LibreChat fleet** (`alm-chat-<slug>`) | One instance per course — the course's own chat, panel, Meili, and Mongo *database*, at its own hostname.  Registrar-rendered, one loop rolls them all.  See **Tenancy**. | yes |
| **OpenBao** (`alm-openbao`) | Key custody.  KV v2 mount `almanac/`, file audit device, AppRole for the registrar.  Custody, not metering. | yes |
| **Groups backend** | Where the roster truth lives.  Driver interface: `file` (demo), `globus` (production — the managed-group pattern).  *As built there is no driver: the roster is `students:` in `courses.yaml`, and nothing reads `GROUPS_BACKEND` — the Globus half is Phase 2.* | yes |
| **LiteLLM** | Mints and enforces the virtual keys; meters everything into the ledger.  Unchanged except key traffic. | no |
| **usage-mcp** | Keeps answering usage questions.  **Zero code changes** — the registrar renders its `roster.yaml` for it. | no |

Division of labor, one line each: **bao = custody, LiteLLM = metering, usage-mcp = reporting, registrar = enrollment.**  OpenBao is never in the stats path — per-user-per-course tracking comes from the ledger (user_id × owner tag), which we already proved live.

---

## Identity & trust — the contract, extended not invented

Identical to usage-mcp, because it survived contact with production and a red-team pass — plus one header tenancy makes possible:

- LibreChat injects **`X-User-Email` / `X-User-Role`** per user into MCP headers, plus a bearer token proving the call comes from the chat itself — and, since decision 32, *which* chat: each course holds a token good only for its own `X-Course`, and the front door's token is good only with none ("Service tokens — one per course," below).
- **`X-Course: <slug>`** — a *literal* the registrar renders into each instance's config, so every MCP call carries which course's house it came from.  Same trust class as the bearer token: students can't touch the rendered YAML.  The header is **context, not authorization** — the roster is still checked; the header just means nobody types a course slug again.
- **Identity is never a tool argument.**  A prompt can pick a date range; it can never pick whose keys come back.  The course was never an argument either, until decision 25: at the front door the staff and admin tools take it by name, because there the header was only ever *choosing* which course — the roster and the `admins:` list decide who may act, as they always did.
- Reachable only on the compose network + a `127.0.0.1` bind for smoke.
- `mcpSettings.allowedAddresses` gets `registrar:8080` (the SSRF guard — ask pipeline #14 why we remember this).

Authority is layered on top of identity:

| Act | Who | Checked against |
|---|---|---|
| retrieve / rotate a key | its owner only | header email == escrow path |
| stage / apply a roster | instructor or TA of THAT course | `instructors:`/`tas:` (file) or group **manager** role (globus) — ADMIN role alone is not enough |
| create a course | platform admins, or the operator | `course_approve` / `course_create` at the desk (`admins:`), or `just course` on the box |
| close / reopen / archive a course | operator | `just course-close` · `course-reopen` · `course-archive` — see "The term," below |

**Nobody but the owner ever sees a key — including faculty.**  Instructors get custody *status* (minted / rotated-at / fetched-at), never secrets.

---

## The managed-group pattern (the Root Cellar idea, standalone)

Projects own data; **groups own people**.  A course is a group with a syllabus.

- The registrar gets its **own Globus confidential client** — *not* the Keycloak broker client.  The broker authenticates humans; the registrar administers groups.  Different jobs, different blast radii, independently revocable.
- `just course engr301 "ENGR 301" prof.vex@example.edu` → the registrar client **creates** group `almanac-engr301`, holds the admin role itself, and invites the instructor as group **manager**.  That manager role IS the "marked as instructor" act — it's what unlocks roster upload in chat.  The same act provisions the course's tenancy: LiteLLM team + service key, Keycloak client (with the instructor mapped to its `admin` client role), the instance render, and the Caddy vhost — finished with a graceful edge reload.  One command, a course exists.
- `roster_apply` reconciles membership: invites the missing (Globus emails them; they accept with the same campus identity Keycloak brokers for login), removes the dropped.  **The group is the roster truth.**
- Email is the join key across all three worlds: group member ↔ `LIBRECHAT_USER_EMAIL` ↔ LiteLLM `user_id`.  Same rule usage-mcp already lives by (`trustEmail` is on at the broker).
- Adopting an existing campus/SIS-fed group instead of creating one: later mode, same seam — `group:` in the course record is just a UUID, however it got there.

**Demo realm (`GROUPS_BACKEND=file`):** no Globus account required to run the make-or-break test.  The course record's `students:` list is the truth, and everything downstream (mint, escrow, render) behaves identically.  The driver interface is three verbs: `members(group)`, `add(group, email)`, `remove(group, email)`.

---

## Course records — `registrar/courses.yaml`

Registrar-owned, gitignored (real rosters are student emails), seeded from a committed example on first `up` — the roster.yaml pattern, reused:

```yaml
courses:
  engr301:
    name: "ENGR 301 — Engineering Design"
    instructors:                    # several from day one — the first real course
      - prof.vex@example.edu     # has two, and every course has TAs
    tas: []                         # same authority as instructors in v1 (see below)
    budgets:
      course: 1000                  # THE cap — per term, hard, chat + keys, one pool
      key_fuse: 5                   # per vAPI key hard ceiling (leak blast radius)
      advisory_weekly: 2            # what "on pace" means in usage tools; never blocks
    college: cci                    # optional — unions the college's model pack in
    models: [almanac-chat]          # what this course's keys + instance may call
    capabilities: [...]             # agent-builder powers; omit for the default,
                                    # [] for none.  `actions` is OFF by default
    allowed_domains: []             # where this course's Actions may reach —
                                    # only meaningful when `actions` is enabled
    group: ""                       # globus backend: group UUID (course-create fills)
    students: []                    # file backend only; globus derives from the group
    aliases: {}                     # legacy non-email user_ids, passthrough to render
    address: engr301                # optional — the stable name that 302s to
                                    # whichever term claims it (see The term)
    closed: 2026-12-18              # set by course-close; archived: by course-archive

colleges:                           # a college is a MODEL PACK, not an org chart —
  cci:                              # the registrar needs their models, not their deans
    models: [cci-llama]             # registered once at the gateway; see Model routing
```

**The file is the authority, so it is never assumed.**  `load_courses()` refuses on unparseable YAML instead of degrading to an empty course set — an empty set and an unreadable file look identical to every caller, and the difference is the whole fleet.  The degrade used to reach `save_courses()` through `course_admin create`, which would write one course over every other course's roster; the file is gitignored, so nothing was behind it.  `course_admin validate` (`just course-check`) is the read-only version of the same checks, and every mutating verb runs them first and refuses on errors.

**TAs are instructors in v1.**  Both lists land as group managers with roster and usage authority — every course has TAs, and inventing a fourth permission tier before anyone's asked for one is how admin panels are born.  If a TA-shaped abuse case ever shows up, splitting the role is a list rename.

**`usage-mcp/roster.yaml` becomes a render.**  After every reconcile the registrar writes it (shared volume; usage-mcp live-reloads — that's why it needs zero changes).  The render's header says "generated by the registrar — edit courses.yaml or the group, not this file."  Existing hand-edits get absorbed into `courses.yaml` once at migration.

---

## Roster upload — paste first, and why

The instructor's contract is **paste**: copy the column out of Banner / Canvas / a spreadsheet, paste it at the agent.  Tool arguments arrive verbatim — deterministic, no retrieval in the path.  A few hundred emails fits comfortably.

Parsing is liberal on purpose: the registrar extracts every email-shaped token from whatever arrives (CSV with headers, TSV, newlines, commas, Banner's junk columns) and **reports what it ignored**.  Don't demand a format from someone who exports one spreadsheet a semester.

**Dropped files:** LibreChat uploads land in RAG — chunked retrieval, which may hand the agent a *lossy* view.  A roster that silently drops row 47 is worse than no upload.  So file-drop isn't blocked (text reaches the tool however it reaches), but the safety is structural:

**Two-phase, always.**

1. `roster_stage(roster_text)` → the course comes from the instance's `X-Course` header — an instructor can only stage the course whose house they're standing in.  *(Since decision 25 it also takes `course` at the front door, by name or id; inside a course the header still wins.)*  Parses, diffs against current membership, returns the exact plan — *adds (n), removes (n), unchanged (n), ignored lines (n, with samples)* — and a `stage_id` (15-min TTL, in-memory).  **Nothing changes.**
2. `roster_apply(stage_id)` → executes that plan and nothing else, then reports per-student outcomes (invited / minted / escrowed / failed-why).

**The yes has to come from a person, and until 2026-09-25 nothing but the model enforced that.**  In a course chat with no agent prompt around the tools, a thinking model staged and applied in the same turn twice on camera — "just enroll these three *instead*" read as consent, and the stage's own closing line (`If that's exactly right: roster_apply(...)`) read as the next step.  A `confirm=true` flag wouldn't help: the model sets it.  The gate is the **turn**: the stage records which chat turn made it (`X-Chat-Turn`, from LibreChat's per-call `{{LIBRECHAT_BODY_PARENTMESSAGEID}}`), and `roster_apply` refuses in that same turn, so an apply needs a message from the person after they have seen the plan.  The stage text now tells the model to stop.  *The server side is built; the header is not yet rendered, because a missing body field makes LibreChat fail the whole call (design-walls.md, MCP gotchas) — it ships after a probe on the canary docker host.  Until then, the gate stands aside and the words are the only fence.*

The instructor confirms what the registrar *parsed*, not what they *meant to paste*.  `course_usage`'s "not started yet" anti-join backstops stragglers a week later.

Removals revoke the student's key for that course (`/key/delete`) and drop group membership.  Escrow versions are retained — custody history survives un-enrollment.

---

## Keys & budgets — three layers, one pool

The budget model, decided 2026-07-22:

| Layer | Enforced by | Blocks? | What it's for |
|---|---|---|---|
| **Course-semester cap** | LiteLLM **team budget** (one team per course) | **yes — the real cap** | The actual money.  Chat AND vAPI keys drain this one pool. |
| **Key fuse** | per-key `max_budget` | yes | Blast radius of a leaked/runaway vAPI key — *not* a pacing tool. |
| **Weekly advisory** | usage tools (reporting only) | never | What "on pace" feels like to a student.  Easier to hold in your head than a semester number. |

**The reconciler creates one LiteLLM team per course** (teams and team budgets are OSS — rig-probed; *team-admin role* is the Enterprise part, and we don't need it because the registrar administers via master key).  Every credential the course generates joins that team, so the semester cap is enforced across modalities in one place.

**One vAPI key per (student × course)**, minted into the course team:

```json
{
  "user_id":   "amaya@example.edu",          // joins to chat spend
  "team_id":   "engr301",                       // drains the course pool
  "models":    ["almanac-chat"],
  "max_budget": 5,                              // the fuse, not the budget
  "metadata":  { "owner": "engr301", "tags": ["owner:engr301"] }
}
```

Same shape `just key` mints today plus `team_id`.  The Enterprise walls stay routed-around (rig-probed on our pins): `metadata.tags` not top-level tags; **rotation = delete + re-mint** (`/key/regenerate` is licensed); students never touch the LiteLLM UI (the 5-DB-user SSO wall stays irrelevant).

- **Mint at apply**, not at first login.  Email is the user_id; the key works the moment they accept the invite.  No-shows surface in the anti-join, not in mint failures.
- **Fuse defaults:** $5 (`REGISTRAR_DEFAULT_FUSE`), clamped by `REGISTRAR_MAX_FUSE` ($25) server-side — a course may ask for a larger `key_fuse` in `courses.yaml`, and the registrar clamps it on load while `validate` names the course it clamped.  No prompt, however persuasive, mints past the ceiling.  There is **no live-bump tool** — raising an existing key's fuse (`key_fuse_set`) is Phase 3 work; today a bigger fuse means a rotation.
- **Rotation preserves the fuse meter:** re-mint sets `max_budget = key_fuse − ledger_spend_so_far`, so rotating a key isn't a fuse reset, and the remainder is clamped again by what the course pool can still pay.  There is **no floor** on that remainder.  A floor meant rotating at exhaustion handed back the floor every time — a fuse that refills on demand bounds nothing.  What bounds it is a *gate*: `REGISTRAR_MIN_FUSE` ($1) **refuses** the rotation when the remainder can't fund a working session, rather than minting a credential that looks broken.  That $1 is a placeholder — nobody has measured what a real half-hour session costs against our packs; set it from the ledger, not from taste.  And if the gateway won't report spend at all, rotation refuses (`MeterUnreadable`) rather than reading an unreadable meter as zero spend and handing back a full fuse.  Ledger history is untouched either way.
- **Two numbers, two tools, and they are not the same tool.**  `budgets.course` is the **pool** the whole class draws from; `budgets.key_fuse` is the **fuse** on one person's key.  Setting the pool is operator work at the front desk (`course_budget_set`, Phase 2a); raising one student's fuse is lifecycle work on a key that already exists (`key_fuse_set`, Phase 3).  They are recorded separately because the spec once had **one** number called `budget` and both tools were named against it — which is how a roadmap ended up carrying `budget_set` and `set_budget` as if they were rivals for the same job.  Name the number, not the verb, and the collision can't come back.
- **Weekly advisory** is computed from the ledger (`end_user` + owner tag — data usage-mcp already reads); `my_usage` learns to say *"$1.40 of your ~$2/week pace"*.  *Not built: `my_usage` reports spend only, and nothing reads `advisory_weekly` yet.*  If our pin's `soft_budget` + `budget_duration: 7d` prove out in OSS, the gateway can also emit pace alerts — verify at implementation, but the advisory layer never depends on it.

---

## The escrow — OpenBao

New compose service (`alm-openbao`, digest-pinned at implementation), **integrated (raft) storage** on its own volume — single node, but raft is the backend with the online snapshot API (`bao operator raft snapshot save`), and the one-VM backup story below leans on it.  `127.0.0.1:8200` for the operator CLI.

**Paths (KV v2, mount `almanac/`):**

```
almanac/courses/<slug>/students/<email>   {key, minted_at, budget, key_id}
almanac/system/litellm-master             Phase 3 — see below
```

**`just bao-init`** — the once-per-box ritual: init (single share) → unseal → enable the file **audit device** → mount kv2 → write policies → enable AppRole → mint the registrar's role.  The unseal key and the registrar's `role_id`/`secret_id` land in `.env` via the existing `fill` pattern.  The **root token prints once** and goes in the operator's password manager — it does not live in `.env`.

**Unattended restarts:** static auto-unseal from `BAO_UNSEAL_KEY` if our OpenBao pin supports the static seal stanza (verify at implementation); otherwise `just up` gains a `bao-unseal` dependency that reads the same var.  Either way the box reboots without a human.

**Honesty box.**  Escrow on the same box, unseal key in the same `.env` — this is not an HSM and we will not pretend otherwise.  What it actually buys, and why it's still worth a container:

1. **Chat-facing code holds zero minting credentials** — the tool plane can read the caller's own escrow path and nothing else.
2. **Custody is policy-scoped and audit-logged** — every key read is a line in the audit device with who/what/when.  `.env` files don't keep receipts.
3. **Rotation is versioned** — KV v2 history is the custody trail.
4. **It's where the LiteLLM master key goes to stop living in `.env`** (Phase 3): reconciler fetches it at boot via AppRole; `.env` keeps only bootstrap creds.

Students never talk to bao directly — `my_key` is mediated by the registrar (one surface, the whole point).  The bao-native alternative (OIDC auth method against Keycloak + a policy templated on the identity's email, so a student can only ever read `almanac/courses/+/students/<their-email>`) is documented here as the break-glass path if key retrieval must survive the chat being down.  Not built in v1.

---

## The mint boundary — one container, two planes

The registrar is one service with a hard internal seam:

- **Tool plane** (chat-reachable): parses, stages, diffs, reads the *caller's* escrow paths.  Holds the MCP bearer secret and a bao token scoped to read-by-identity.  **No LiteLLM master key.  No Globus client secret.**
- **Reconcile plane**: consumes confirmed stages.  The only code that loads the minting credential, the Globus client, and the bao write role.

v1 keeps both in one process (module seam, credentials loaded only inside the reconciler); splitting into a worker container later is mechanical because the interface is already "a queue of confirmed plans."

**Blast radius, stated plainly:** a fully hostile prompt that reaches the tools can stage a roster (inert until an instructor confirms it), read the caller's own keys, and spend the caller's own budget.  It cannot read anyone else's key (path is derived from headers), mint outside a confirmed stage, exceed the budget clamp, or claim to be someone else.  That sentence is about prompts.  Whoever holds a service token *is* the chat as far as these services know, and can put any email in the header — so a token is worth exactly the course it can speak for, which is why each course gets its own (decision 32).  Roster text is data: email extraction by pattern, everything else discarded and reported — a CSV cell reading "ignore previous instructions" parses to zero emails.  Standing invitation to council-redteam before v1 ships; they've caught real ones in this repo.

---

## Service tokens — one per course *(2026-10-02, decision 32)*

**The problem.**  Both tool servers check one bearer token each (`REGISTRAR_MCP_TOKEN`, `USAGE_MCP_TOKEN`) and then believe the headers: `X-Course`, `X-User-Email`, `X-User-Role`.  Every course container holds both tokens, because `render_course_env` copies them from the root `.env` — the one root value in a function whose docstring promises "no other course's anything."  So anything that can read one course container's environment can call either service as any person, in any course, at any role: fetch any student's key with `my_key`, stage and apply any roster.  Nothing outside reaches it today (the services listen only on the compose network, and `mcpSettings.allowedDomains` keeps staff-added tool servers closed).  But one leaked course is the whole platform, and the number of courses is the number of places it can leak from.

**The fix: a course's token speaks for that course and no other.**

- **Derived, not stored.**  A new root secret, `COURSE_MCP_SECRET`, held only by the registrar and usage-mcp.  A course's token is `HMAC-SHA256(COURSE_MCP_SECRET, "<service>|<slug>")`, hex — `service` is `courses` or `usage`, so a course's registrar token is no good at usage-mcp and the reverse.  Verifying is recomputing: neither service needs a table, the escrow, or a call to the other.  usage-mcp stays without an OpenBao credential, which is the point of keeping it this small.
- **The front door keeps its own token.**  `REGISTRAR_MCP_TOKEN` and `USAGE_MCP_TOKEN` stay in the root `.env` and in the flagship's environment, unchanged, so the front door's `librechat.yaml` (and every `site/` copy of it) needs no edit.  What changes is what they're good for: **the front-door token is accepted only on a call with no `X-Course` header.**  It can no longer claim a course.
- **The rule both services apply**, before anything else:
    - `X-Course` absent → the bearer must equal the front-door token.  (`_ident()` still refuses here, as it does now: no course, no course tool.)
    - `X-Course` present → the bearer must equal that course's derived token, and the slug must be one the service knows — `courses.yaml` for the registrar, `roster.yaml` for usage-mcp — and not archived.  An archived course's container is gone; its token should go with it.  `roster.yaml` never said which courses were archived, so the render now writes `archived: "<date>"` under an archived course there; usage-mcp still answers that course's history to its staff and refuses only its token.
    - Either failure is the same refusal as a wrong token today, through `hmac.compare_digest`.  No message says which half was wrong.
- **The render writes it.**  `render_course_env` writes the course's two derived tokens under the same variable names, `REGISTRAR_MCP_TOKEN` and `USAGE_MCP_TOKEN`, so the course's `librechat.yaml` template doesn't change — except that the usage server's headers gain `X-Course: "<slug>"`, which usage-mcp needs to know which token to expect.  They are recomputed every render, never kept: derived values have nothing to preserve.  The root tokens never enter a course env again.
- **`COURSE_MCP_SECRET` is generated by `just secrets`**, which `deploy` already runs — an older `.env` gets it appended.  Compose passes it to `registrar` and `usage-mcp` only.  If it's unset, the render refuses to write course envs and both services refuse every course token: closed, never a fallback to the shared one.
- **Rotation is the secret, platform-wide.**  Change `COURSE_MCP_SECRET`, restart both services, `just render`; every course restarts with new tokens.  A per-course epoch (`"<service>|<slug>|<n>"`, `n` kept in the course record) would let one course rotate alone; nothing has needed it yet, so it isn't built.
- **A probe that proves it, from inside.**  The prod-probe pattern, so no token moves: a check run in the registrar container reads each `fleet/<slug>.env` it already mounts and asserts the course's token is accepted with its own `X-Course`, refused with another course's, refused with none, and that the front-door token is refused with any `X-Course`.  It joins `deploy` beside `egress-check`.

**Deploying it.**  The services turn strict at `just deploy`'s `up`, and the courses hold the shared token until `just render` rewrites their envs, so the courses' tools refuse in between.  `course-tokens-check` and `render-check` are both red over exactly that window — the first runs first, and names each course whose env "still holds the FRONT DOOR's token" — and the step after a deploy that changes `render.py` is already `just render`.  Run them back to back.  The flagship is unaffected.  The registrar keeps the front door's `USAGE_MCP_TOKEN` in its environment for one reason only: so the check can prove usage-mcp refuses it alongside an `X-Course`.  It no longer renders it anywhere.

**What it doesn't fix.**  A course's token can still claim any email *in its course*: a leaked course container can impersonate that course's students, and so fetch their keys.  The header is the only witness of who's asking, and that's LibreChat's to give.  Per-course tokens make a leak one course wide, which is the blast radius a course already has.  Binding the person too would need a signed identity from LibreChat (an ID token passed through to the MCP call), which LibreChat 0.8.7 doesn't send.  Recorded here so the next person doesn't think it was missed.

**To measure while building it.**  Can a tool server an instructor adds in the UI put `${REGISTRAR_MCP_TOKEN}` in its headers and get the container's value substituted?  If 0.8.7 resolves environment variables for staff-added servers, then any course with an `mcp_domains` entry can mail its own token to a host the instructor controls — today the platform's whole token, after this decision just that course's.  Measure it on a throwaway stack, not a live box, and record the answer as a wall in `design-walls.md` either way.  **Measured 2026-10-02:** not through the chat UI — a staff-added server's `${...}` and `{{...}}` placeholders are never filled in — but yes through the admin config API, where a base-scope override can add both a server that gets the env and the domain that lets it out.  Details and method: [design-walls.md](design-walls.md), "A server staff add in the chat UI never sees the container's environment — but the admin config API does."  Open, and a design call.

---

## The census — the fleet from above *(2026-09-16)*

Every tool above starts with "THIS course": the caller's identity picks the course and the tool refuses to look sideways.  Right for a professor, useless for the person who has to answer "what is deployed, how big is it, and who can get in?"  Those answers were scattered across five systems that each know one column — the course record, Keycloak's door, the ledger's pool, the instance's Mongo database, and the container itself — and nobody joined them.  The registrar is the only thing in the room that already talks to all of them, so the census is a second face on it: **read-only composition of every plane, one row per course.**

| Tool | Answers | Who |
|---|---|---|
| `fleet_inventory` | every instance: answering or not, users, conversations, agents (and how many are shared), files and their bytes, database size, pool spent against cap, roster counts; plus findings — rendered-but-silent, Actions with no allowlist, a pool past 90%, unrostered people at the door, databases with no course record | platform admins |
| `fleet_access <course>` | the roster, the Keycloak door, everyone who has actually signed in with first-seen and last-active, who is signed in now — and the three diffs a review asks for: rostered but never seen, seen but not rostered, at the door but not rostered | platform admins |
| `fleet_exposure <course>` | every agent with its share scope (public, role, group, named users, private), tools, Actions count, knowledge count; every file by size and owner; the capabilities and allowlist the record grants | platform admins |

"Platform admin" is the `admins:` list in `courses.yaml`, **not** the instance's ADMIN role.  A course instance makes its own staff ADMIN, and that is authority over one house; the fleet view is every house at once, so it answers only to the operator's list — the same test usage-mcp applies.

Two outputs from one function.  The tool answer is for the person asking in chat.  The same call rewrites `fleet/inventory.md` and `fleet/inventory.json` on the box (`just fleet` does it from the CLI), because a security team does not want an MCP — they want a page that lands in the docs index like everything else, and a JSON twin for whatever they already stare at.

**The census stops at the envelope.**  It reports that a conversation exists, whose it is, when, and how many tokens — never a message.  Not a title either: LibreChat generates titles from the first exchange, so a title is the content, shorter.  Not an agent's instructions.  A student burning a fuse at 3 a.m., an agent shared public that shouldn't be, a four-megabyte file in someone's knowledge — all visible from the envelope, and that is everything a fleet view legitimately needs.  Reading a transcript is a conduct investigation: a human with a process going into one course's database on purpose, never a tool in the fleet view.  The plane that reads Mongo (`planes/chatdb.py`) enforces this in its projections, and the wall in [design-walls.md](design-walls.md) says why it stays that way.

What the census deliberately cannot see: container state.  The registrar holds no docker socket (that would be root on the box in a service that already holds three credentials), so "answering" is an HTTP health probe over the compose network, and volume sizes are Mongo's `dbStats` plus the sum of file bytes.  Honest, and one credential short of the alternative.

## Nominations — the other direction

The census looks down.  Nominations send something up.  A student who built an agent worth copying — or an instructor who spotted one — says so from inside the course: `nominate_agent <agent_id> "<why>"`.  Your own agents, or any in the course if you're staff — and staff don't need the author's say-so, by decision: the norm is to ask, as with any student work, but the platform can't enforce it and doesn't try (design-walls.md, "The census stops at the envelope").  Nothing is copied at that moment.  A platform admin sees it in `nominations`, and `nomination_export` turns it into a **file** on the fleet volume: `fleet/templates/<id>-<name>.yaml` — name, description, instructions, model, tools, and the knowledge files *by name*, with a provenance block naming the course, the author, the nominator, and the note.

The file is the point.  The course marketplace already lets a class share agents by clicking; what it teaches is clicking.  A template is an agent as a reproducible artifact: readable, diffable, forkable, seedable with the same script that seeds the guides.  Knowledge is listed rather than carried, and Actions are counted rather than copied, because both are the parts that *should* be re-attached deliberately by whoever seeds it — a file that could silently carry a course's uploads into another course would be the exposure the census exists to catch.  The student's name stays on the template as author; that is the credit, and it is the lesson: you didn't reinvent the wheel, you built one other people can bolt on.

Nominations live in `registrar/nominations.yaml` beside the course records — same volume, gitignored for the same reason (it names people).  States: nominated, exported, declined; nominating the same agent twice returns the open nomination instead of a duplicate.

---

## The context window is rendered, not inherited *(2026-09-21)*

Every course instance renders `maxContextTokens` into its `endpoints.custom` block.  It did not, until now, and the absence was invisible: LibreChat falls back to its own default for a model it does not recognise — around 28k on our pin — so courses got a number nobody chose, out of a dependency, that moves on a version bump.  That is a floating value wearing the costume of a default, and this repo pins those.

**It is per course because the right answer is per model, and the registrar is the only part of the system that knows which models a course gets** — `models:` is in the course record.  The flagship's window can't work that way and is correctly `site/`: that config is generic, a fresh box serves whatever `INFERENCE_MODEL` points at, and a blanket number there would hand a backend a window it may not serve.

**It is deliberately NOT a model → window table.**  `almanac-chat` is an *alias*: `litellm/config.yaml` maps it to `os.environ/INFERENCE_MODEL`, so the same name means a different model on every deployment.  A table keyed on it would be the registrar claiming knowledge about a model chosen on the far side of `INFERENCE_BASE_URL` — the seam the platform is not allowed to cross ([design-walls.md](design-walls.md), "The Almanac consumes inference; it does not manage it").  The operator knows what their endpoint serves; the course record is where they say so.

**Err low, and the asymmetry is sharper than "one of them errors."**  Too small trims a conversation sooner — degraded, still working.  Too large is the **quiet** one: some backends refuse an over-long prompt, but **Ollama — what `INFERENCE_BASE_URL` points at by default — drops the FRONT of the prompt and answers anyway.**  The front of the prompt is the system prompt.  So a course agent loses its instructions, its vocabulary and its boundary mid-conversation and keeps talking, with nothing in any log an operator reads.  That is not a shorter answer, it is the classroom posture leaving the room — and it manufactures exactly the fabrication [the agent contract](agent-contract.md) exists to prevent, from a config number nobody would think to suspect.  `validate` warns below 4k and above 200k, and refuses zero.

**Set it from what the endpoint SERVES, never from what the model supports.**  On Ollama those differ silently and by a lot: the docker host's endpoint was measured at 32768 while the loaded model allowed 262144, because the ceiling is the *server's*, not the model's.  `/api/ps` on a loaded model is the honest read; `/api/show` reports what the architecture allows, which is the number that misleads.  And leave room for the answer — Ollama's `num_ctx` covers prompt *and* completion, so the input bound sits below the served window (that box runs 24000 against 32768).

**The default is `REGISTRAR_DEFAULT_CONTEXT_TOKENS`, and it is 128000** — the operator's number, set 2026-09-21 after the knob shipped at 28000 to match LibreChat's own fallback.  It is a **cost cap, not a capability claim**: a bound on what one conversation can spend on a metered model, comfortably under what the large hosted models serve, and far above the ~28k that a model serving 922k was silently getting.

That makes the default **deliberately not the cautious one**, and the consequence has to be stated rather than discovered: 128k is larger than many self-hosted endpoints serve, so **a course whose models resolve to a small local model must set `context_tokens:` itself**.  The err-low rule moved from the constant into the course record — which is a trade, knowingly made, and the only place it *can* live, because the registrar cannot resolve an alias it does not own.  Note that this failure is not new at any default: a backend serving under 28k was already exposed to it.  Raising the number widens the window in which it bites; it does not create it.

Raising it is **not** a no-op, unlike the commit that introduced the field.  Every rendered course is stale until `just render`, and `render-check` goes red saying so.

---

## Reports — the complaint that carries its own evidence *(2026-09-21)*

`report_problem` files "this didn't work" from the chat: what broke, and — when the report is about an answer a guide gave — the question that went wrong, the answer that came back, and the knowledge files it cited.  That second half is the entire justification for it being a tool rather than an email address.  A complaint on its own is a mood.  The same complaint with the exchange attached is a **retrieval trace**, which is a thing someone can take to the corpus and act on.

**It works from the front door, and that is the design, not a convenience.**  A report tool living inside a course is down whenever that course is, which is exactly the hour a person wants it.  The vestibule is the one room with no roster — everyone in the realm can enter, the same invariant that means it hands out no keys — so it is the room that still answers when the room being complained about doesn't.  The registrar is therefore wired into the flagship **without an `X-Course` header**, and the absence is the access control: the tools that need a course to *be* the room (`my_key`, `rotate_my_key`, `nominate_agent`) open with `_ident()`, which refuses without that header, so they go on refusing there with no policy written anywhere.  (The staff tools later learned to take the course by name instead — decision 25 — and the admin tools followed, decision 27.)  The full argument is a wall — [design-walls.md](design-walls.md), "The front door is the one room that can take a complaint."

**Routing comes from the roster.**  In a course, `X-Course` names the course.  In the vestibule, `courses.yaml` does: one course is an answer (`route: roster`), several or none is recorded as `unknown` and a human picks.  Nobody is guessed at, because a report filed against the wrong course wastes the one instructor who reads it.  A course the person *names* routes only if they are on it — otherwise the slug is kept as `said_course` on an unrouted record, since a name that routed nowhere is either a typo or someone who believes they're enrolled and isn't, and both are worth knowing.  Every record carries the reporter's full enrollment regardless, because at triage the question is always "where else should I look."

**The trace is self-reported and says so.**  There is no retrieval log to read, so `asked` / `answered` / `sources` are the agent's account of its own turn; the record carries `reported_by_agent: true` so it is never mistaken for an audit of the retriever.  Imperfect and present beats rigorous and hypothetical.

**Who works the queue is its own list, and the line is not seniority.**  `devs:` in `courses.yaml` grants the report queue — `reports`, `report_triage` — and nothing else.  It is deliberately **not** `admins:`, because the distinction that matters is *who chose to be seen*: a report is something a person sat down and sent you, while `fleet_access` is every student who chose nothing.  Those should not share a gate merely because both are platform-wide, or handing a student worker the bug queue hands them every roster on the box.  Admins triage implicitly — they already see more — and `validate` warns when a name is on both lists, since the `devs:` line then grants nothing and would mislead whoever later removes them from `admins:`.  Teaching staff read their own course's reports from inside that course, and no further.

**Closing a report requires a note, and the reporter can read it.**  `my_reports` shows a person what became of what they filed — pull, not push, because there is no notification channel the platform owns and inventing one would be a second inbox nobody reads.  Asking is the channel.  `report_triage` refuses to close without a note for the same reason the whole tool exists: the note is the only thing the person who filed it ever gets back, and closing in silence is what teaches people the tool does nothing.

**The words are Piper's, the record is Marco's.**  When a guide offers to file a report, and how it asks, is agent instruction — it lives in [agent-contract.md](agent-contract.md) and reaches the box through `just agents-seed`, like every other thing a guide says.  The tool's shape doesn't change when the wording does.

Reports live in `registrar/reports.yaml` beside the course records — same volume, gitignored for the same reason, and more so: this file quotes what people typed.  States: open, triaged, closed.  Unlike nominations they never dedupe — two people hitting the same wall is the signal, not a duplicate.  Operator side: `just reports [status]` prints the full text and the exchange; `just report-close <id> "<what was done>"`.  From chat it is `reports`, `report_triage` and `my_reports` — the queue is workable from the vestibule, so fixing the platform doesn't require a shell on the box.

---

## Model routing — one upstream credential, many keys

Unchanged in architecture, extended in config.  The central credential lives at the gateway; virtual keys only ever name **model names**:

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

Two blocks with the same `model_name` = load-balanced group; different names (`almanac-chat` / `almanac-cloud`) = per-course model lists decide who may call cloud.  Either way: **swap the upstream, minted keys never notice** — they're pinned to names, not endpoints.  Foundry spend meters into the same ledger rows as local tokens, so per-user-per-course tracking is identical whether the tokens came from a campus GPU or Azure.

**Costs are the gateway's job and it's good at it:** cloud models price from LiteLLM's model map (Azure included, when the metadata's there); campus models carry whatever we say they cost — `input_cost_per_token`/`output_cost_per_token` in the model block.  Price local tokens at an amortized GPU rate (or $0.— and let token counts be the measure) and every budget layer above works identically for both.

**College endpoints — bring your own inference.**  A college with its own GPU box for its own courses is three knobs, no new machinery:

1. **Register once** at the gateway: `cci-llama` → their api_base, their key (a credential — escrow path `almanac/system/models/<name>`).
2. **Scope by course**: the college's model pack unions into its courses' `models:` lists (the `college:` field above); the reconciler stamps the list onto the course **team and every key in it** — the gateway refuses the model to anyone else, which is enforcement, not visibility.
3. **Visibility is free** — tenancy already did it.  The instance's endpoint renders its course's model list, so `cci-llama` *appears as an option* only inside CCI courses' instances.  In the shared-instance design this would have been another gating project; here it's a render detail.

The one policy question per college endpoint: **does their metal charge the pool?**  Price it $0 (their gift to their courses — the dollar cap protects the *paid* upstreams, token counts still meter) or price it real (chargeback recovery).  Per-model knob, college's call, registrar indifferent.

---

## Tenancy — one LibreChat instance per course

*Decided 2026-07-22 (Andrew's proposition, and it wasn't insane).*

> "How do you keep the courses apart in LibreChat?"  "That's the neat part — we don't."  — Andrew, explaining the architecture to a colleague, 2026-07-23

The question that decides whether the semester cap is real: how does a *LibreChat conversation* get a course?  Injecting each student's per-course key into chat means `user_provided` endpoints — freshmen pasting secrets into settings panels.  Sharing one instance means course context by agent selection plus an endpoint-visibility fence we'd have to verify held.  The actual answer is tenancy: **course = instance.**

**The important sentence: shared control plane, per-course data plane.**

| Plane | Services | Count |
|---|---|---|
| Control (never fragments) | Keycloak (+ Globus broker), LiteLLM + ledger, OpenBao, usage-mcp, registrar, Caddy edge | **one each** |
| Data (per course) | LibreChat + its Mongo *database* + its Meili + its RAG API and pgvector + admin panel | **one per course** |

Mongo runs one container, N databases.  pgvector/RAG is per course — a `rag-<slug>` + `vectordb-<slug>` pair in the fleet render, because LibreChat signs RAG calls with its session secret and a shared RAG would mean shared sessions (ruled 2026-09-18; design-walls.md has the measurement).  **Meilisearch is the awkward child** — LibreChat's index names don't namespace, so it's one small Meili per course (~100MB) or search off per instance.  *As built, search is always on (`SEARCH: "true"` in the render); a per-course knob is future work.*

What the container boundary buys, versus the fences it replaces:

- **Cross-course endpoint access dies structurally.**  An instance only *contains* its own course's credential.  No panel-gating verify, no ledger-side freeloader detection as a security layer (it stays as telemetry).  A container boundary beats a visibility toggle.
- **Faculty admin scoping fixes itself.**  The shared design made every faculty member ADMIN of the one instance (`OPENID_ADMIN_ROLE=faculty` — realm-wide).  Per-instance, each course's OIDC client carries an `admin` **client role**, mapped to that course's instructors and TAs only: `OPENID_ADMIN_ROLE_PARAMETER_PATH=resource_access.<client>.roles`.  Full control of *their* house, no key to anyone else's.
- **Enrollment gates the front door.**  Any realm user can *authenticate* to any client by default — which would let an un-enrolled student sign into a course instance and chat on its service key.  Closed at login: each course client also carries a `member` client role, granted and revoked by roster reconcile, and the instance requires it (`OPENID_REQUIRED_ROLE`, the LibreChat-native gate — verify var at our pin).  Not on the roster → bounced at the door, not caught at the till.  The registrar's roster sync thus maintains three things per student: group membership, the vAPI key, and the `member` grant.  **The grant needs a realm user, so the roster creates one** *(built 2026-09-15)*: `kc_ensure_user` pre-creates the account (username = email, no credentials) at enrollment, and `kc_ensure_autolink` gives every identity provider a first-broker-login flow that links the IdP login to that account by email — no confirm-link prompt, no second account.  Before this, a rostered student's first visit was bounced at the door until the next roster sync, and nothing ran one.
- **Blast radius**: a hostile agent tool, a leaked JWT secret, a bad plugin — one course's conversations, not the campus's.
- **Drift is the feature, not the bug.**  Instructors get their hands dirty deep in their own weeds — their agents, their marketplace, their share-groups (which are now just their course's teams), their interface toggles, their own admin panel — the same freedom we're building for students.  The rails: everything **DB-stored is theirs**; everything **rendered is the registrar's** (image pins, YAML, env, routes — uniform, in git, rolled by one loop).  Sovereign tenants, standardized plumbing.
- Students already live this model: Canvas is per-course.  Course conversations don't commingle — FERPA-flavored bow included.

**What it costs, stated plainly:** uniform operational fan-out.  ~500–600MB per course all-in (chat + Meili + panel share), N containers to roll on a LibreChat CVE — but same pinned image + rendered config = one `just` loop, not N snowflakes.  Twenty courses ≈ 12–15GB on the app box.  Policy fan-out inside one shared instance was the alternative, and that's the kind that generates tickets.

**The money layer survives untouched.**  One LiteLLM, one ledger.  Each instance's endpoint carries its course's **team-scoped service key** — "one master key per course," minted by the registrar like any other key, escrowed in bao like any other key.  Chat spend and vAPI-key spend drain the same course-team pool; the semester cap governs everything.  The per-user header stamps `end_user` on every chat request exactly as shipped, so per-student advisory numbers fold chat + vAPI spend — and the instance implies the course even before the header names the student.  usage-mcp reads across the whole fleet without a line changing.

**Auth fan-out is free because the broker exists.**  Each instance is one more OIDC client in the realm we already script (registrar mints clients via the Keycloak admin API; exact redirect URIs, no wildcards).  Globus stays **one** registration — Keycloak's.  Without the broker this idea costs N manual registrations at developers.globus.org; with it, a for-loop.

---

## The front office — where courses come from

*Envisioned 2026-07-24: "where am I logging in to provision a course?"*

The doctrine holds at the top of the org chart too: **there is no course management website.**  The flagship instance (`chat.<domain>`) — no longer a leftover from the pre-fleet design but the **front office**: the one room that isn't a course, where faculty-at-large exist before they have rooms of their own.  Students never need it; faculty visit once a term; the operator runs the platform from it.

**The operator's desk** — a "Course Provisioning" agent on the flagship, holding admin-gated registrar tools:

| Tool | Does |
|---|---|
| `course_requests()` | the pending queue, oldest first |
| `course_approve(request_id, budget, slug?, tas?, note?)` | request → `ensure_course` → instance live; the budget is required and is the admin's |
| `course_create(slug, name, instructors, tas?, budget?)` | direct provision, skipping the queue |
| `course_budget_set(course, amount)` | adjust a course **pool** — the class's shared ceiling, not anyone's key (gateway team update) |
| `course_list()` | the fleet at a glance — pools, enrollment, health |

Gate: email in the `admins:` list (courses.yaml) — the same list usage-mcp already honors.  One deliberate contract difference from course tools: **admins pass the course as an argument** (they span courses; there's no X-Course where they sit), and the admins list is the authority.  Identity stays header-only, always.

**Built 2026-09-22 — a thin slice, and where it differs from the plan above:**

- **The desk is the Operator Guide, not a separate "Course Provisioning" agent.**  The plan assumed tools list per user; a seeded agent is visible to everyone who can open the vestibule, so the gate is server-side (`_admin_or_refuse`) and an agent carrying the tools grants nothing.  The Operator Guide's corpus — the admin guide and this spec — is what an admin approving a course wants on hand anyway.
- **`course_list` is `fleet_inventory`**, which already existed and already answers "the fleet at a glance."
- **Every desk write is two calls**: without `confirm=true` it describes what it would do; with it, it acts.  Same idea as `roster_stage`/`roster_apply`, without a stage id, because the arguments are short enough to repeat.
- **`course_staff`** is new — add instructors or TAs, remove staff — because "who teaches this" was the one thing an admin still needed a shell for.  `ensure_course` now revokes the course `admin` role from anyone `courses.yaml` doesn't name.
- **A request is a ticket, worked like a problem report** *(@xram, 2026-09-22)*: approve, **return with notes**, or **reject with notes**, and the requester reads the answer in `my_requests` and answers a return with `course_request_reply` on the same ticket — the thread is the history.  **The request carries no budget**; the admin sets the pool at approval (`course_approve` requires one), because the pool is the platform's money and a requester can't meaningfully name a number.  That, plus approval, is what keeps the open door from being an open-ended course generator.
- **Notifications** *(2026-09-22)*: email to the requester on every decision (note in full), and the desk hears about new tickets by webhook (Teams Workflows by default) or email to `admins:`.  SMTP is optional — unauthenticated relay, authenticated, or none, in which case mail is appended to `registrar/outbox.log`.  The desk gets the envelope only; [design-walls.md](design-walls.md), "A notification is a pointer, not the content."
- **The request agent is the Instructor and Student guides**, carrying `course_request` / `my_requests` / `course_request_reply`, rather than its own agent.  The front-door text is **served by the tool**, not injected into a prompt: the first call returns the question and the second files it, so `front-door.md` stays deployment config that takes effect without a reseed.  Kinds are `course`, `project` (needs a parent course) and `standalone`.
- **Not built yet:** the `endpoint` kind and its one-time key drop, `course_import`, `kind:`/`parent:` on the course record itself (an approved project room is an ordinary course for now; the request keeps the link), and the office-as-tenant hardening.
- **Starting the instance** is the fleet watcher (`just fleet-watch-install`), because the registrar holds no docker socket — [design-walls.md](design-walls.md), "A course made in chat is rendered, not running."
- **From the 2026-09-23 sweep:** `course_return` and `course_reject` describe first and act on `confirm=true` like every other desk write, because both email a person word for word.  The census and nomination tools moved to the front door (decision 27) — `fleet_inventory` had been on the desk while refusing every call there.  An approval that stops in provisioning can be approved again: the ticket records its course before provisioning, and the retry finishes it instead of refusing the slug as taken.  Course names are folded to one line wherever they enter, because they land in the instance's `.env` and `librechat.yaml`.

**The self-service request** — a "Request an Environment" agent on the same flagship, open to **anyone with a campus login** *(2026-07-24: not faculty-only — student project requests are half the traffic)*.  The agent collects the details conversationally, and the first thing it sorts is **what kind of ask this is** — the checkbox, rendered as a question:

- **course** — "I'm the instructor" (name, term, headcount — *no budget ask since 2026-09-22: the admin sets the pool*)
- **project** — a project room under an existing course (which course, who's sponsoring)
- **standalone** — club, competition team, thesis prep (who's the responsible party)
- **endpoint** *(2026-07-24)* — bring-your-own-LLM: base URL, model name(s), which course(s) may see it, pricing intent ($0 gift vs.  chargeback — the college-pack knob), and who answers for the box.  **The API key is NOT collected in chat** — see the custody note below.  Approval registers it at the gateway as a model pack scoped to exactly the named courses; the endpoint goes live only when its key lands.

**Endpoint-key custody — nothing transits the conversation.**  A secret pasted at an agent rides the model context and lands in Mongo chat history — residue in two places before escrow ever sees it.  So the endpoint request files *without* the key; on approval, the registrar issues a **one-time drop token**, and the requester runs one command:

```
curl -X POST https://frontdesk.<domain>/drop/<one-time-token> \
     --data-urlencode 'key=sk-their-key'
```

The drop route is the registrar's own HTTP surface (a custom route beside `/health`), path-routed through the frontdesk vhost — not a website, one POST.  The key goes straight to `almanac/system/models/<name>` in the escrow, the token dies, reconcile finishes the registration.  **Not even the operator handles the key** — which is a better promise to a faculty member than "we store it carefully."

Then the **front-door question**: the agent confirms this is for *coursework, not research* — and records the answer.  The request that lands in `registrar/requests.yaml` carries the requester type AND the attestation, dated.  When the slippery-slope question ever comes back ("did they know the boundary?"), the answer is in the record: they were asked at the door, in plain language, and said yes.

**The plain language is deployment config, not code.**  The boundary verbiage lives in `registrar/front-door.md` (example-shipped, deployment-edited) and is served by `course_request` itself — the first call returns the question — and echoed into every filed request.  The example policy says coursework belongs here; sponsored research goes to the research environment, full stop; the traditional gray zone (non-sponsored master's "academic research" commingled with coursework) is tolerated but named, so nobody discovers the line by crossing it.  **Another deployment can rewrite that file to say "research welcome here"** — the software is a room-renderer and doesn't care; a research-dedicated deployment is just a separate fleet on a separate box with different front-door text.  The per-instance separation that keeps courses apart keeps *missions* apart at the deployment level for free.

Requests are typed, attested, and queued — nothing provisions without the desk's nod, which is what makes the wide-open door safe.  Gated to start; auto-approval rules (e.g. faculty + within default budget → straight through) are a policy knob for later, not a rebuild.  In the machinery, a project room or a sandbox is the same primitive as a course — a `kind:` field on the record (`course | project | sandbox | office`), optionally `parent:`-linked for spend rollup — rooms all the way down.

Nobody copies course info out of tickets: the "ticket" files itself into the queue, structured, because a tool argument is a schema.  Batch intake falls out of the same shape — the registrar's office emails the term's course list, the operator pastes the CSV at the desk (`course_import`, staged and echoed like everything else).  And when SIS integration ever happens, it feeds the same tool surface through `course_admin.py` — the CLI on the box stays the break-glass and batch path either way.

What a web form would have added: a login page, a session store, a CSP review, a framework dependency, and a second place to check.  What it would not have added: anything the echo doesn't already do.

**The office runs on house metal** *(2026-07-24)*: the front office's endpoint pins to an **office model pack** — an on-prem model (`almanac-office` at the gateway, priced **$0**) — so faculty can question it all day and the meter never moves.  That turns the one non-course room into three things at once:

1. **The demo floor** — the office marketplace holds the exemplar agents (Ask the Almanac, Almanac Usage, Request a Course; Course Provisioning visible only to admins, because tools list per-user).  *As built: the eight seeded guides, and the desk is the Operator Guide — visible to everyone, gated server-side.*  Faculty meet working agents before they build their own.  The platform demos itself, literally.
2. **The learning environment** — tinker freely, zero budget anxiety, nothing real at stake.  The sandbox instinct, satisfied before anyone requests a sandbox course.
3. **The help desk** — "Ask the Almanac," an agent whose knowledge files ARE this repo's docs (user guide, admin guide, this spec).  Honest answers are a function of feeding it real text — which we maintain in git anyway, so re-feeding on release is a chore, not a project (automating docs→agent sync is a Phase 3 nicety).

Two consequences worth their own lines: the office becomes just another tenant in the machinery — its own team, its own **service key**, its own model pack — which means **the master key finally leaves the flagship's config too** (the last chat-facing container holding it; a Phase 2a hardening item).  And the office door *(revised 2026-07-24)*: it opens to **any campus login** — students request project rooms too, and the demo floor teaches whoever walks in.  Safe because the room runs $0 house metal, every request is attested + operator-approved before anything provisions, and attribution still names everyone.  `member`-gating stays what it is: a *course-room* mechanism.

---

## The floor — what the Almanac handles FOR you

*Opened 2026-07-24, pending counsel review (Nora).  This section states the enforcement architecture and names the questions that are counsel's to answer — it does not answer them.*

Faculty get full control of their rooms.  **They do not get control of the floor** — the guardrails and audit posture the institution is required (or strongly advised) to provide, which no course configuration can lower.  The floor's enforcement point is chosen by the architecture we already have: **every credentialed path to every model — chat service keys, student vAPI keys, laptops, all of it — passes through the one gateway.**  What the gateway enforces, nobody routes around with a config knob.

**Enforcement layers, strongest first:**

1. **The gateway interceptor** (LiteLLM custom callback hooks — pre-call and post-call, OSS; managed guardrail providers vary, verify at implementation).  Runs on every request and response regardless of course, key, model, or surface.  This is where "cannot get around" lives: crisis-signal detection, response shaping (resources-forward, never sycophantic agreement with self-harm — the exact failure mode currently in litigation elsewhere), PII handling if required.
2. **The floor prompt** — a platform-level preamble the gateway injects ahead of every course's own instructions: honesty-with-care norms, crisis-resource behavior, academic-advice boundaries (the "should I drop out" question gets steered to human advisors, not answered by a completion).  Norm-setting, not enforcement — layer 1 backs it.  Like front-door.md, **the words are deployment config** (`registrar/floor-prompt.md`) — counsel owns the language, code owns the injection point.
3. **Training + attestation** — the front door, the docs site, the Ask-the-Almanac agent: where residual liability shifts to informed users, and only works if layers 1–2 exist first.

**Crisis response posture** (the hard one, stated conservatively): the platform DETECTS and SHAPES — responses to crisis signals must carry crisis resources and must not assist or agree.  Whether the system also *alerts a human* is not an engineering decision: it's a duty-of-care / privacy / FERPA question with a counseling-ethics dimension, and the answer is a **counsel-decided escalation config**, off by default until decided.  The hooks exist; the policy is Nora's to write.

**The honest bypass audit** — "could an instructor wire up an endpoint that doesn't go through LiteLLM?":

- **Chat model path: locked.**  Custom endpoints live only in the rendered `librechat.yaml` — read-only mount, registrar-written; instance admins cannot add model endpoints from the UI on our pin.
- **Agent Actions: the porous edge — CLOSED.**  Our first Phase-1 render enabled `actions` (OpenAPI tool calls to arbitrary URLs) for every agent builder — an Action pointed at an external LLM API is exactly the bypass, as a *tool* if not as the chat model, and an ungoverned data-egress path besides.  All three remedies now ship: **actions-OFF by default** (`DEFAULT_CAPABILITIES`), a per-course **`capabilities:`** knob where an explicit `[]` means none, and a per-course **`allowed_domains:`** that renders to LibreChat's top-level `actions.allowedDomains`.  Two limits to state plainly rather than discover later: an **empty allowlist is no allowlist** (private IPs stay SSRF-blocked, the public internet does not), so the only real off switch is omitting `actions`; and **LibreChat never validates capability names** — a typo fails closed and silently, which is why `course_admin validate` exists to say so.
- **Admin-panel config overrides: verify.**  The panel's per-group override machinery must be confirmed unable to inject endpoint definitions; constrain if it can.
- **The steer, not just the wall**: someone with a legitimate outside model doesn't hack an Action — they ask, and the **college-endpoint mechanism already built for this** registers their endpoint at the gateway, scoped to their course, metered like everything else.  The right path is easier than the workaround, on purpose.

**Audit posture, for the review**: the ledger records *usage* (who, which model, tokens, spend) — not conversation *content*.  Content lives per-course in Mongo, under LibreChat's own retention.  What the institution MUST retain, MUST NOT retain, and who may read what under which process is a counsel question with FERPA weight — the layers above determine what's *possible*; the review determines what's *required*.

**Questions carried to counsel** (the section's whole point): required vs. recommended guardrails for student-facing AI; crisis-escalation duty and its privacy interplay; content retention obligations and limits; whether the front-door attestation shape is sufficient; whether actions-off-by-default is required or merely wise; what the floor prompt must say.  **Sequencing commitment: the floor ships before the fifth course does.**

---

**The two lanes, side by side** — a student in `engr301-2026fall.aisandbox.example.edu` spends either way:

| Lane | Credential | Student attribution | Course attribution |
|---|---|---|---|
| Stays in chat | the instance's **service key** | `end_user` header (as shipped) | the key's team + tag |
| Asks `my_key()`, goes to opencode | their **personal vAPI key** | the key's `user_id` | the key's team + tag |

`my_key()` takes **zero arguments** — the instance's `X-Course` header already knows whose house the ask came from, so the key that comes back is for *this* course, no slug typed, no cross-course confusion possible.  Both lanes drain the same course-team pool and fold into the same per-student numbers in usage-mcp (which already splits chat vs API in `my_usage`).  Chat never needs the personal key.

---

## Routing — one door, many rooms

Hostname-based, Caddy, wildcard DNS — ports are for compose files, not syllabi.

- **DNS**: `*.{ALMANAC_DOMAIN}` → the box.  One wildcard record.
- **TLS**: one wildcard cert via **DNS-01** (wildcards require it; the Azure `acme_dns` block already sketched in `caddy/Caddyfile` graduates from comment to config — root-cellar's delegated-zone guide is the pattern).  Public boxes without wildcard DNS can fall back to per-vhost HTTP-01; LAN stays on the internal CA.  All three modes already exist in the edge profile — this extends, not invents.
- **Vhosts**: the registrar renders one small file per course into a shared volume the edge imports (`import /etc/caddy-fleet/*.caddy`):

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

  Rendered files over hostname-label placeholder tricks, deliberately: a vhost you can `cat` at 3am beats cleverness, and label-index math breaks the moment the domain depth changes between campus and lab deployments.
- **Reload**: course creation is an operator act, and the justfile already owns docker — `just course` finishes with a graceful `compose exec edge caddy reload`.  **No docker socket ever enters the registrar** (or any chat-adjacent container); the registrar renders files, the justfile does lifecycle.  *(2026-09-22: a course can now be created from chat, so the host watches `fleet/fleet.yml` and runs `just course-up` itself — still the justfile doing lifecycle, triggered by a file the registrar writes.)*
- Shared surfaces keep their names: `auth.` (Keycloak), `gateway.`  (LiteLLM admin).  The apex and the front door: next section.

---

## The public face — the apex, the front desk, and the strangers

*Envisioned 2026-07-24.*

**The apex (`aisandbox.example.edu`) is an mkdocs site** — how-tos, guides, model selection, LLM pedagogy — thick with CTAs to sign in and try it.  Served by the edge itself (a `root`/`file_server` block over the built site; `just docs-build` runs a pinned mkdocs-material container → `site-dist/`; CI rebuilds on docs commits).  No new daemon — Caddy was already standing there.

**The same markdown serves twice.**  The docs directory is BOTH the public site and Ask the Almanac's RAG corpus — one source, two renderers (mkdocs for the web, embeddings for the chat).  "Literally the same info" is structural, not aspirational: there is no second copy to drift.  A how-to fixed on the website is a how-to fixed in the agent's mouth at the next re-feed.

**The front desk gets its name**: `frontdesk.<domain>` — and it falls out of Phase 2a's office-as-tenant work for free.  The office record renders with slug `frontdesk` like any course renders; the flagship container is its instance; the standalone `CHAT_HOST` variable retires into the fleet render.  One less special case.

**Strangers get a landing, not a handshake error.**  Wildcard DNS sends *every* subdomain to the edge, so a catch-all vhost (lowest priority — Caddy prefers exact hostnames, course vhosts always win) 302s unknown names to `https://<apex>/instance-not-found/` *(superseded 2026-09-22: the edge serves the no-course page itself, as a 404 — [design-walls.md](design-walls.md) has why)* — an mkdocs page: "no course lives at this address — the term may have rolled over; here's how to request an environment," CTA included.  TLS note: the catch-all rides the **wildcard cert** (DNS-01) in production — per-name issuance on arbitrary garbage subdomains would eat ACME rate limits; the internal CA doesn't care on LAN.

The quiet payoff is semester rollover: `course-close` (Phase 3) removes the vhost render, and last term's bookmark degrades — automatically — to a friendly page explaining where things went and how to come back.  Rollover UX by subtraction.

---

## The term — close, archive, and the address that outlives it *(2026-09-24)*

**A course is one term** — decision 15 made slugs term-qualified (`engr301-2026fall`) in July, and this section is what that implies.  ENGR 301 next fall is `engr301-2027fall`, a new instance beside the old one: its own database (`LibreChat_engr301-2027fall`), its own team, its own pool.  The budget model already assumed it — the team budget *is* the semester cap — and a slug reused across terms would carry last term's spend into the new pool and hand returning students and TAs last term's chats.  So a slug is **never reused**, and a closed course stays in `courses.yaml` to hold its slug.

**The address is what students remember** (Andrew, 2026-09-24).  `address: engr301` on a course record renders `engr301.<domain>` — and `engr301-admin.` beside it — as a redirect to that course, whichever term currently claims it.  A syllabus link written once works every year.  It is a **302**, not a 301, on purpose: browsers cache a 301 indefinitely, and this one moves every term.  One address, one live claimant: an **open** course wins it; a **closed** course keeps it through its export window only if no open course claims it; an **archived** course's claim is history.  Two open courses claiming one address is a `course-check` error, and the render leaves that address out rather than guess.  An address lives in the slug namespace, so it can never also be a course slug.

**Closing is two steps, and only the second is irreversible** (ruled 2026-09-24).

- **`just course-close <slug>`** freezes the course.  Its LiteLLM team is **blocked** (`/team/block`, free on our pin — probed on the canary docker host): every key on the team stops, the service key included, so chat can't spend either.  The record gains `closed:`.  Everything else stays — sign-in, history, agents — for a **14-day export window**, in which students take their own conversations out with LibreChat's export.  `just course-reopen <slug>` unblocks the team and clears the date, because a wrong close should cost a sentence, not a restore.
- **`just course-archive <slug>`** ends it.  Every escrowed key is revoked at the gateway (the escrow records stay — custody survives, as it does for un-enrollment), the course's OIDC client is **disabled** so nobody signs in, and the course leaves the fleet render and the edge.  The fleet watcher's `course-up --remove-orphans` stops its containers, and the old hostname falls to the no-course page.  Refused on a course that isn't closed, and refused inside the window without `--force`.
- **The export window is only as good as LibreChat's export, and it has no bulk export** — one conversation at a time, from each conversation's menu ([LibreChat-AI/LibreChat#3768](https://github.com/LibreChat-AI/LibreChat/issues/3768), open as of 2026-09-25).  A student with eighty chats has eighty exports.  The close-out routine gets its polish over the coming months; opening and running courses comes first (Andrew, 2026-09-25).
- **Nothing is deleted.**  The Mongo database, the `vector-<slug>-data` volume and `fleet/<slug>.env` — the CREDS pair that decrypts it — all stay.  How long they stay is an institutional retention policy, and there is no `course-purge` until there is a policy for it to enforce (ruled 2026-09-24).  `course-check` warns when a closed course has passed its window unarchived.

**What a closed course still answers.**  usage-mcp keeps its roster entry — an instructor reading final spend after the term is the normal case, not an edge.  The registrar refuses every write on a closed or archived course (roster, staff, budget, keys, re-provision) and says why, with the dates.  An archived course's vector store is in the last backup taken before the archive: its volume persists, but nothing dumps a stopped container.

---

## Your own data — the owner's export *(2026-09-25)*

**Anyone can take their own work out of any course, in any state, from any room** (Andrew, 2026-09-25).  `export_my_data(course)` packages the asker's conversations — both sides, every message — and the agents they own into a zip, and returns a link that works for 24 hours; `email_my_export` mails that link to their own address if they want it for later.  It is the bulk export LibreChat doesn't have (#3768), and because the database outlives the course, it works on closed and archived courses too — the registrar's answer to "inspect and review," not a courtesy of the export window.

- **Whose:** the email from the trusted headers, and nothing else.  There is no argument that names a person, so there is no way to ask for someone else's.  The Mongo read matches `user` on the conversation *and* on each message.
- **Agents:** authored, or holding LibreChat's owner role (`permBits` 15) — an agent can have several owners, and each gets a copy whose provenance names every one of them.  An editor's grant is not ownership.
- **Files:** listed in the README, not carried — the registrar mounts no course's uploads volume.  Andrew's line: useful if it fits the same archive, not required.
- **The link:** an unguessable token, a 24-hour life, one route through the edge (`/exports/<token>` on the chat host — the only registrar path the edge serves; `/mcp` stays internal).  Every miss is the same 404.  The zips live in `registrar/exports/` at 0600, gitignored, purged as they expire, and **excluded from backups** — each one is a copy of data the backups already hold.
- **The wall:** this is the census wall's second deliberate crossing, and why it isn't a breach is written there ([design-walls.md](design-walls.md), "The census stops at the envelope").

---

## The venue — one VM on Azure Local

*Decided 2026-07-22: the research compute facility is off the table; the almanac lands on Azure Local as a standalone Linux VM (Debian) with Docker, running everything **except inference**.*

This costs the plan nothing, and that was the point all along — the justfile's deployment contract has always been "a box with Docker."  The venue is a variable, not an architecture:

- **Inference was never coming aboard.**  The vLLM stack is deliberately its own compose project on GPU metal elsewhere; `INFERENCE_BASE_URL` / the Foundry block point wherever the tokens actually live.  The VM needs zero GPUs.
- **CI retargets, not rewrites**: Woodpecker's deploy step ssh's to a hostname.  New box, new variable, same pipeline.
- **Azure Container Apps, rejected for the right reason**: per-course containers with rendered configs and local volumes map miserably onto managed platforms — Mongo becomes Cosmos-with-a-mongo-accent, the ledger becomes managed Postgres, Meili becomes a problem, and the bill becomes a committee.  One VM keeps the data gravity in volumes, the deploy contract in the justfile, and the whole thing restorable by one person on one bad morning.
- **DNS-01 is now on home turf** — the wildcard cert's Azure `acme_dns` block was built for exactly this RFC-1918 shape, and the DNS zone is already in the neighborhood.

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

Provision **8 vCPU / 32 GB / 256 GB** and forget about it until ~20 courses; it's a VM — resize is a reboot, not a migration.

**Backups — the whole point of one VM:**

*Half built.  `just backup` shipped 2026-09-29 and ran on the canary docker host, and the operator's sequence is in the [admin guide](admin-guide.md#running-them).  `just restore` and the drill have not, so by this section's own rule there are no backups yet.*  `just backup` (nightly, a lingering user timer installed the way `fleet-watch-install` installs its units) produces **two bundles, never one**:

- **The data bundle** — `mongodump --archive` (every course DB in one pass) · `pg_dump` of litellm (**the ledger**), keycloak, the flagship `vectordb` and every course's `vectordb-<slug>` (rebuildable only by every author re-uploading, so it rides) · `bao operator raft snapshot save` (**the escrow**, online, consistent) · the uploads volumes (`librechat-uploads`, every `chat-<slug>-uploads` — plain files, the originals of every agent knowledge file) · `registrar/courses.yaml`, the registrar's queues (`reports`, `requests`, `nominations`), `front-door.md` and `site/agents-state.json` · caddy data (certs — cheap to keep, annoying to reissue).
- **The secrets bundle** — `.env` (every secret, and the unseal key), every `fleet/<slug>.env` (the course's pinned `CREDS_KEY`/`CREDS_IV`), and `site/`, this box's own config, which can hold credentials of its own.

They are separate on purpose, which is the correction this paragraph owed: it used to say *one tarball*, while the [admin guide](admin-guide.md#backups) says `.env` is kept apart from `bao-data` so a stolen copy of one is useless without the other.  One tarball would have been the stolen copy of both.  So they go to **two restic repositories under two passwords**, and neither password lives *only* on the box.  A restic password kept in `.env` dies with the box it was meant to outlive.  The nightly run has to read them from somewhere, so each comes from a file or a password manager's command, and the off-box copy is what makes a restore possible.  The target is a per-box setting in `site/`, not a tracked constant: on campus it is the secure file share, mounted on the box and handed to restic as a path (ruled 2026-09-24), and the lab boxes point wherever the lab keeps things.  restic runs from its container image, so the box installs nothing.  **Meili is excluded on purpose** — it's derived from Mongo and rebuilds on boot — and so are the hf-caches, which re-download (an air-gapped box names that as its own risk).

**A backup that stops must say so.**  A failed run pings the desk the way `notify` does; a timer that fails quietly is how a box ends up with six months of confidence and no copies.  Retention is 7 daily · 4 weekly · 6 monthly, which is also a **privacy number**: a deleted chat lives in the backups until the last copy holding it ages out, and the reader pages owe students that number the day this ships ([how-long-we-keep-it](../apex/your-data/how-long-we-keep-it.md)).

`just restore <snapshot>` is the mirror image on a fresh VM: pull both bundles, compose up, load dumps, restore the raft snapshot, unseal, smoke.  **Built means the drill passed, not that the recipe exists.**  The drill is a round trip between two live instances, which is also the production shape (ruled 2026-09-24): on campus a second VM restores from the share and a DNS flip makes it the box; in the lab, the `latest` canary and a third instance on another docker host back up into each other.  The restore therefore lands on a box that already runs a stack, and it takes the source's **identity** along with its data — the secrets bundle brings the source's `.env`, domain included — so the drill ends in a DNS flip (or a hosts-file entry on the test client), never in rewriting a domain.  Then a rehearsal persona logs in, sees its chat history, `my_key` returns the *same* key it had before, and `just evals-check` goes green.  Once both directions pass, export/import *is* the backup system; there is no separate one to trust.

A standby that has been restored stays **quiet** until the flip — no timers that mail, no traffic — and the flip is one-way: the old box is re-seeded from the new one before it serves again, or two registrars hold the same keys against two diverging ledgers.  **The restore drill is scheduled work, not documentation theater** — see Phase 2.  A backup that's never been restored is a rumor.

---

## Phasing

**Phase 1 — standalone, demo realm, end-to-end** *(built — the rig under "Verify at implementation")* (the make-or-break, now two acts: `prof.vex` pastes the mock roster into *the engr301 instance*, `stu.amaya` asks `my_key`, the key hits the gateway from the workbench — then a second demo course spawns and **the wall holds**: chem's instructor can't see engr301's chats, panel, or pool; the mock realm grows a second course for exactly this): compose + bao-init + registrar with `file` backend · **instance render** (chat + panel + Meili + Mongo db + Keycloak client + team + service key + vhost) · stage/apply · mint · escrow · `my_key` · roster.yaml render · per-instance MCP wiring (`mcpServers.almanac-registrar`, allowedAddresses) · smoke checks that walk the fleet · admin guide recipe for the "Course Setup" agent.

**Phase 2a — the front office** *(thin slice built 2026-09-22; see its Built notes — not yet: the endpoint kind and key drop, `course_import`, office-as-tenant)* (thin slice, before or alongside Globus — the tools wrap reconcile verbs that already exist and shipped in Phase 1): `course_requests` / `course_approve` / `course_create` / `course_budget_set` / `course_list` + open-door `course_request` (typed intake incl. the **endpoint** kind + the one-time key-drop route), requests.yaml queue, front-door.md, the two flagship agents (desk + request), admin-guide recipes.  Plus the office-as-tenant hardening: office team + service key (**master key out of the flagship config** — the last one), `almanac-office` $0 model at the gateway, and the "Ask the Almanac" RAG agent fed from docs/.

**Phase 2 — Globus + the drill:** the registrar's confidential client, managed-group create/invite/reconcile, manager-role authority, `--adopt` mode.  Flip `GROUPS_BACKEND=globus`; the login side already has the broker runbook in the admin guide.  Plus `just backup`/`just restore` and the **restore drill on a scratch VM** — proven once before fall's five courses enroll, not promised.

**Phase 3 — lifecycle & hardening:** ~~rotation with budget carryover~~ *(shipped — `rotate_my_key`, remainder carried, `MeterUnreadable` refuses rather than guessing)* · `key_fuse_set` live updates · ~~`just course-close` (revoke all, final render, archive group)~~ *(shipped 2026-09-24 as close → archive, with a 14-day export window between them and a stable `address:` — see The term)* · master key moves into bao · ~~chat-side `course_create` for platform admins~~ *(shipped with the desk, 2026-09-22)* · redteam pass.

**Root Cellar docking (deferred, by design):** the cellar's project groups and these course groups are the same primitive.  When docking day comes, either side can consume the other's groups — the interface is a group id and member emails, nothing almanac-internal.

Out of scope, permanently unless vetoed: a separate admin website (the entire point is not having one) · SIS API integration (paste beats a Banner integration project) · per-message rate limits (budgets are the governor).

---

## Decisions made here (veto anytime)

1. Key retrieval is **chat-only, registrar-mediated**; no student-facing bao UI in v1.
2. **Mint at apply**, not at first login.
3. Managed groups are **created by the registrar** (`almanac-<slug>`); adopting existing groups is a later mode.
4. The registrar gets its **own Globus client** — the Keycloak broker client is never reused for group administration.
5. **One container, hard module seam** between tool plane and reconcile plane; worker split deferred until needed.
6. **`roster.yaml` becomes a render**; humans edit `courses.yaml` (file backend) or the group (globus backend), never the render.
7. **No one but the owner ever retrieves a key** — instructors see custody status only.
8. *(2026-07-22, Andrew)* **Budget hierarchy**: course-semester team budget is the one true cap; per-key `max_budget` is a leak fuse ($5/$25 stands); per-student weekly numbers are advisory and never block.
9. *(2026-07-22, Andrew)* **Multi-instructor from day one** — the first course has two, and every course has TAs.  `tas:` list ships in v1 with instructor-equivalent authority.
10. *(2026-07-22)* **Chat gets no per-student keys.**  The course instance's endpoint carries the team-scoped service key; students pick the course by walking into its chat.  `user_provided` is the documented fallback, not the plan.
11. *(2026-07-22, Andrew)* **Tenancy: one LibreChat instance per course.**  Shared control plane (Keycloak, LiteLLM, bao, usage-mcp, registrar, edge — one each); per-course data plane (chat, panel, Meili, Mongo database, RAG API + pgvector).  Instructor drift inside the rendered rails is a feature — the same hands-dirty freedom we're building for students.
12. *(2026-07-22, Andrew)* **Routing: Caddy, hostname-based, wildcard DNS.**  Wildcard cert via DNS-01; registrar-rendered vhost imports (greppable at 3am) over hostname-label tricks; reload rides `just course`; no docker socket in any service.
13. *(2026-07-22, Andrew)* **Venue: one Debian VM + Docker on Azure Local**, inference external, container-app platforms rejected (managed DB sprawl).  One VM to back up, one VM to restore.
14. *(2026-07-22)* **The instance is the course context.**  `X-Course` rendered into each instance's MCP config; tools drop their course arguments (`my_key()`, `roster_stage(text)`); enrollment gates login itself via the `member` client role.  Header = context, roster = authz.  *(Partly superseded by 25: at the front door the course is an argument.)*
15. *(2026-07-22, by example)* **Slugs are term-qualified, code-first** — `engr301-2026fall`, straight from Andrew's own hostname example.  Rollover = a new course record each term; spend rollups sort chronologically for free.  Flag if the example wasn't a decision.

## Verify at implementation

*Phase-1 rig (2026-07-22, this box, exact pins): two courses provisioned end-to-end — teams at $1000, service + student keys minted into teams and escrowed (kv2 + AppRole + audit live), instances up behind the edge with OIDC registered ("configured successfully"), vhosts serving, roster render live-reloaded by usage-mcp, smoke + fleet-smoke all green.  Items below marked ✓ closed there.*

- ~~OpenBao static-seal~~ **RESOLVED**: skipped static seal; `just bao-unseal` rides `just up` (rig-verified), and since 2026-09-23 a boot-time user unit from `just fleet-watch-install` (reboot-verified on the docker host).  Raft snapshot round-trip still owed in Phase 2's backup work.
- ~~`/key/update` live budget changes~~ ✓ free on our pin — `ensure_course` uses it to keep the service key on the course pool (design-walls.md).
- **Team budget enforcement at exhaustion** — pool-drain blocking still owed (needs live inference spend); team create/update + membership ✓ rig-verified.
- ~~Team/key model-list semantics~~ ✓ **rig-verified**: a team-minted student key lists exactly the course models and gets **403** on anything else — refusal is gateway-side, which is what college-endpoint scoping needs.
- **Fleet identity shape** ✓ rig-verified and documented (.env.example): `KC_HOSTNAME=https://auth.<domain>` + `KC_PROXY_HEADERS=xforwarded` + edge network alias + `NODE_EXTRA_CA_CERTS` (internal CA) — without them instance OIDC discovery fails on issuer mismatch.
- ~~Compose include mechanics~~ ✓ rig-verified on v5.1.4 (`include:` of the rendered fleet.yml, stub-seeded by `just _fleet`).
- `soft_budget` + `budget_duration: 7d` in OSS for gateway-side pace alerts (the advisory layer works from the ledger regardless).
- **Client-role admin mapping** on our LibreChat pin: `OPENID_ADMIN_ROLE_PARAMETER_PATH=resource_access.<client>.roles` per instance (the realm-role variant is deployed and working; the client-role variant is the same machinery, one path deeper).
- ~~`OPENID_REQUIRED_ROLE` (login gate)~~ **VERIFIED 2026-07-22** against LibreChat's docs: `OPENID_REQUIRED_ROLE` + `_PARAMETER_PATH` + `_TOKEN_KIND` exist, Keycloak client-role shape documented (roles "can be managed within the client or realm settings").  Browser click-test still owed at our pin.
- **Raft snapshot save/restore** round-trip on our OpenBao pin (single node) — the backup story leans on it.
- **Meili per-course footprint** and the search-off knob; **admin panel** against a per-course Mongo database; **RAG API / pgvector** — settled per course (2026-09-18), so the footprint question now includes a pgvector per course.
- **Wildcard DNS-01** against the campus DNS provider (the Azure block exists; other providers = other caddy-dns plugins in the edge build; delegation pattern per root-cellar's guide).
- Globus Groups API invite semantics for emails with no Globus identity yet.
- Practical tool-argument ceiling for jumbo rosters on our LibreChat pin (fallback: `roster_stage` accepts chunks, stages merge).

## Decisions since (veto anytime)

*The open questions of 2026-07-22 were all settled; everything decided after is numbered on from the list above.*

16. *(2026-07-22, Andrew)* **Course cap default: $1000 per term.**  Overridable per course at `just course` time; the registrar enforces, the funding reality decides.
17. *(2026-07-24)* **The front office is the flagship instance** — course provisioning, requests, and budget administration are admin-gated MCP tools on the same registrar; no course-management website, ever.  Admin tools take the course as an argument (admins span courses); the `admins:` list is the authority.  Self-service requests are conversations that file themselves.
18. *(2026-07-24, Andrew)* **Anyone can request; the door asks what and attests why.**  Requests are typed (course / project / standalone), carry a dated coursework-not-research attestation, and queue for operator approval.  The boundary verbiage is **deployment config** (`registrar/front-door.md`), never code — a research-dedicated deployment rewrites the text, not the software.  Rooms are one primitive: `kind: course | project | sandbox | office`.
19. *(2026-07-24, Andrew)* **The apex is an mkdocs site; the docs serve twice** (public web + the help agent's RAG — one source, no drift).  The office answers at `frontdesk.<domain>` via the normal fleet render (`CHAT_HOST` retires); unknown subdomains catch-all-redirect to `/instance-not-found/` on the wildcard cert.  *(The redirect became a served 404 page on 2026-09-22.)*  Closed courses degrade to that page — rollover UX by subtraction.
20. *(2026-07-24, Andrew)* **AlmanacBot + MCP handles ALL requests** — rooms and endpoints alike, one queue, one desk, one approve verb.  Endpoint keys never transit chat or the operator: request files keyless, approval issues a one-time drop straight into escrow, the model pack scopes to exactly the named courses.
21. *(2026-07-24, Andrew)* **The floor is not faculty-configurable.**  Platform guardrails enforce at the gateway (the one chokepoint every credential passes); the floor prompt and crisis-escalation behavior are deployment config written WITH counsel, not improvised in code.  Agent Actions flagged as the bypass edge — allowlist + per-course capability knob, actions-off recommended until it ships.  The floor ships before the fifth course does.
22. *(2026-09-21, Marco)* **Budget tools are named for the number they write.**  `course_budget_set` moves the **pool** (`budgets.course`, the class's shared ceiling); `key_fuse_set` raises the **fuse** on one existing key (`budgets.key_fuse`).  They read as near-duplicates only because the spec once had a single number called `budget` and each tool was named against it in a different year — `budget_set` for the desk, `set_budget` for the key.  `course_budget_set` shipped with the desk on 2026-09-22; `key_fuse_set` is still unbuilt.  Recording the split cost a sentence; discovering it at implementation would have cost a tool surface.  The rule that prevents the repeat: **name the number, not the verb.**
23. *(2026-09-21, Marco)* **The room that takes the complaint is the room that is still up.**  `report_problem` lives in the vestibule, not in each course, because a report tool inside a course is down whenever the course is.  The rejected alternative was a platform-wide instruction teaching every agent to handle errors: there is no such injection point, and course agents are **faculty-owned** — anything written into someone else's agent is theirs to delete.  Wiring the registrar into the flagship costs nothing because the flagship renders no `X-Course` and every course tool already refuses without it; the missing header **is** the access control, and adding one there would hand the realm a course's roster tools.  Routing falls out of the roster, which the front door already has.  *(The staff and admin tools later moved to the front door — 25 and 27 — because for them the header was choosing, not deciding.)*  And the record carries the **exchange**, not just the complaint — a trace is debuggable, a mood is not.
24. *(2026-09-21, Andrew + Marco)* **Platform devs are a list, and the line they draw is consent, not rank.**  `devs:` grants the report queue and nothing else — not the fleet view, not a roster, not a key.  The separation exists because a report is *self-disclosed* (someone chose to send it) while `fleet_access` is *surveillance* (every student who chose nothing), and a single "platform-wide" gate would let the first imply the second.  It is what makes the bug queue safe to hand to a student worker.  Admins triage implicitly.  Paired with it: closing a report requires a note, because `my_reports` shows that note to the person who filed it, and a queue that answers nobody trains people to stop filing.
25. *(2026-09-22, Marco)* **Enrollment works from the front door, because the header was choosing, not deciding.**  The staff tools (`roster_show`, `enroll`, `unenroll`, `roster_stage`, `roster_apply`, `course_keys`) take `course` as an argument when there is no `X-Course`, infer it when the caller teaches exactly one, and check `_staff_or_refuse` against the roster exactly as before; inside a course the header still wins and a disagreeing argument is refused.  `enroll`/`unenroll` stage adds or removes only — `roster_stage` replaces the whole list, which is right for a class export and wrong for "add Pat."  Every path still ends in `roster_apply` on a stage the person has read.  `my_courses` answers anyone, about themselves, and "no courses" is an ordinary answer because the front door is open to the whole realm.  Who is *staff* stays operator-set (`instructors:`/`tas:`), and the realm `faculty` role no longer gates anything an instructor does — `course_usage` reads the roster instead.
26. *(2026-09-22, Andrew + Marco)* **The front office opens: anyone may ask, admins decide, and the host starts what the registrar renders.**  Phase 2a's thin slice — request tickets with a recorded front-door attestation, worked like problem reports (approve with a budget the admin sets, return with notes, reject with notes), the admin desk with describe-then-confirm writes, and `course_staff` so who-teaches-what needs no shell.  `courses.yaml` stays the store for now; it is live state on the registrar's volume, not deployed config, so a new term needs no redeploy — only these verbs.  A database becomes worth it when we need edit history or a second registrar, and `planes/courses.py` is the one seam that changes then.
27. *(2026-09-23, Marco, from @xram's repo sweep)* **Every admin tool answers at the desk, and every desk write that reaches a person is shown first.**  The census (`fleet_inventory`, `fleet_access`, `fleet_exposure`) and the nomination queue (`nominations`, `nomination_export`, `nomination_decline`) take `_ident_open` — the `admins:` list decides and the header never did; `fleet_inventory` sat on the Operator Guide's desk refusing every call, and no eval covered it.  `course_return` and `course_reject` gained `confirm`, because a note emailed word for word is the one write that can't be undone by a second call.  And a course created from chat now passes the same slug and deployment checks as `just course` (`slug_error`, `deployment_error` in `planes/courses.py`) — before, chat checked the pattern and nothing else.
28. *(2026-09-24, Andrew + Marco)* **A course is a term; its address is not.**  Slugs were already per term (decision 15); now they are also never reused, because the team budget is the semester cap and a reused database is last term's chats; the stable `address:` redirects to whichever term claims it, so students and syllabi only ever learn `engr301`.  Closing is two steps — a reversible freeze (team blocked, 14-day export window) and an irreversible archive (keys revoked, client disabled, instance down) — and neither deletes anything: retention is the institution's policy to set, and `course-purge` waits for one.  The name `address` and not `alias`, because `aliases:` already means usage attribution for legacy `user_id`s.
29. *(2026-09-25, Andrew + Marco)* **A person can always take their own work out.**  `export_my_data` gives anyone their conversations and owned agents from any course, closed or archived included, behind a 24-hour link shown in chat and optionally mailed to their own address.  It crosses the census wall on purpose and only for the owner — the email is the trusted header, never an argument.  Uploaded files are listed rather than carried until a course's uploads can ride the same archive.
30. *(2026-09-28, Marco, from @piper's find — **superseded by 31**)* **A course chat opens with its tools in reach.**  Each course instance renders one model spec, `course-chat`: the course's first model with the usage and registrar servers preselected, marked `softDefault`, so a student's first "give me my key" works without two clicks.  The server applies the spec's `mcpServers` on every turn, so on that spec the tools can't be unticked.  `enforce` stays off, so the raw models and agents are still in the picker.  Adding any spec flips three interface defaults to false, which is why the render sets them explicitly.  See design-walls.md, "A `modelSpecs` list silently turns off…".
31. *(2026-10-02, @xram)* **Keys, usage and exports live in the front office; a course chat is for coursework.**  Decision 30 put both tool servers on every course-chat turn, and a spec's `mcpServers` ride every turn whether the person asks for a key or not: 35 tool schemas, about 4,200 tokens on every coursework request, billed to the course — and on a 16–32k local model, a real share of the window the student's own conversation needed.  Bookkeeping shouldn't spend coursework's budget.  So `course-chat` stays the default but carries no tools, and its description points at the front office.  `my_key` and `rotate_my_key` work there now: the course is an argument (or the caller's only course), which only *chooses*; the roster still *decides* (`_my_course` in `registrar/server.py`, the same split as `_staff_scope`).  In a course chat the header still wins and a disagreeing argument is refused.  The Coder Guide owns keys, the Usage Guide reads numbers, the Instructor Guide enrolls — all at the front door, on its budget.  The tool servers stay declared in each course's config, so staff can attach them to an agent deliberately.  The Dev Guide became the **Operator Guide** in the same change: "Dev" read as "developer", which is the Coder Guide's reader.
32. *(2026-10-02, @xram + Marco)* **A course's service token speaks for that course and no other.**  Every course container held the platform's two MCP tokens, and the services believe whatever course and person a token-holder's headers name — so one leaked course was every course.  Course tokens are now derived (`HMAC(COURSE_MCP_SECRET, "<service>|<slug>")`), checked by recomputing, and accepted only with their own `X-Course`; the front door keeps the root tokens, now accepted only with no `X-Course`.  No storage, no escrow, no change to the flagship's config.  It shrinks a leak to one course; it does not bind the person, which needs a signed identity LibreChat doesn't send.  Section: "Service tokens — one per course."
