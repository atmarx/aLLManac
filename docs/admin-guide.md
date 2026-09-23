---
title: How do I run the aLLManac?
description: The operator's path through the two consoles that run this stack — Keycloak for who, LiteLLM for how much — plus the chat usage tools, the course fleet, backups, and the free-tier walls you will hit.
audience: operator
status: draft
owner: geordi
tags: [keycloak, litellm, librechat, sso, oidc, identity-broker, rbac, key-rotation, escrow, metering, attribution, backup]
tethered_to:
  - justfile
  - scripts/seed_agents.py
  - scripts/agents_check.py
  - librechat/librechat.yaml
  - litellm/config.yaml
  - keycloak/realm-classroom.json
  - usage-mcp/server.py
  - registrar/planes/gateway.py
  - registrar/render.py
---

# The aLLManac — Admin Guide

*Keycloak decides **who**.  LiteLLM decides **how much**.  This guide is those two consoles, the seams between them, and the honest boundaries of the free tier — verified against the exact pinned builds this stack runs.*

## The map (read this first)

*Looking for a sequence rather than a reference — what to run after a deploy, and what red means?  That's [post-deploy.md](post-deploy.md).  This page is organised by subsystem, which is the right shape when you know what you're looking for and the wrong shape at 11pm after a push.*

| Surface | Where | Login | What lives there |
|---|---|---|---|
| Keycloak admin | `:8080` | `KC_ADMIN` / `KC_ADMIN_PASSWORD` | Identity: users, realm roles, the Globus broker, OIDC clients |
| LiteLLM admin | `:4000/ui` | `LITELLM_MASTER_KEY` | The ledger: models, keys, budgets, spend |
| LibreChat admin panel | `:3082` (flagship) / `{slug}-admin.` (a course) | SSO (same button), that instance's ADMINs | **Local groups** for agent sharing, role permissions, config overrides — per instance |
| LibreChat | `:3080` | SSO | The chat itself — mostly runs itself |

**Those four ports bind loopback** (`PUBLISH_BIND`, default `127.0.0.1`) — they are admin surfaces and a bypass of every rule the edge enforces, so from anywhere but the box itself they need a tunnel:

```bash
ssh -L 3082:127.0.0.1:3082 -L 4000:127.0.0.1:4000 -L 8080:127.0.0.1:8080 <box>
```

Then reach them at `http://localhost:<port>`.  Chat is the exception that needs no tunnel: it has a front door at `CHAT_HOST`, which is the whole point of the edge.

**`:3082` is the flagship's panel, and it is the operator's.  A course's panel has a front door of its own** — `render_course_vhost` gives every course `{slug}-admin.$ALMANAC_DOMAIN` beside its `{slug}.` chat, so if students chat at `engr301-2026fall.aiclassroom.dev.xram.net`, that course's panel is `engr301-2026fall-admin.aiclassroom.dev.xram.net`, same SSO button, no tunnel.  That difference is deliberate rather than drift: faculty administer their own course and have no shell on the box, while the flagship's panel governs the vestibule everyone shares.  Send faculty to their course's vhost — [teaching-a-course.md](teaching-a-course.md) does — and keep `:3082` in operator hands.

Both panels carry a `Secure` session cookie (`ADMIN_PANEL_SESSION_COOKIE_SECURE`, default true).  The tunnel above is unaffected, `http://localhost` being a trustworthy origin; what the flag rules out is a browser reaching a panel over plain HTTP at the box's *IP*, which needs `PUBLISH_BIND=0.0.0.0` anyway.

Three things in this stack are called "groups," and confusing them costs an afternoon:

- **Keycloak groups/roles** — identity facts.  The roles that matter are the ones the registrar sets on each course's own client (`admin`, `member`); the realm's `faculty` role reaches only the front door — see [who is an instructor](#roles-who-is-an-instructor).
- **LibreChat local groups** (admin panel) — the ONLY groups the agent-share dialog can see.  Keycloak's groups claim never reaches LibreChat's ACL system at v0.8.7 (upstream [#10006](https://github.com/danny-avila/LibreChat/issues/10006)).
- **LiteLLM teams** — optional ledger structure.  Usable, but see [the boundary table](#faculty-analytics--what-you-can-see) before you build a course on them.

---

## Keycloak

### Getting around

Admin console at `:8080`, then **switch the realm** (top-left dropdown) from `master` to `classroom` — everything course-related lives there.  `master` is Keycloak's own housekeeping realm; stay out of it except to manage the admin account itself.

### Users

- **Local (demo/mock) users:** Users → Add user (set email, mark email verified) → Credentials → set a password (temporary off).  The bundled realm ships `prof.vex`, `stu.amaya`, `stu.bram` (password `Demo123!`).
- **Federated users (production):** you don't create them.  When identity brokering is on, a person's first SSO login creates their Keycloak user automatically (`syncMode: IMPORT`), and a rostered person lands on the account the registrar already made for them.  There is no role to assign on arrival — see below.

### Roles: who is an instructor

**An instructor is whoever `registrar/courses.yaml` lists under `instructors:` or `tas:` for a course.  Nothing in Keycloak makes someone one, and nothing you click there should.**  Every reconcile turns those lists into two roles on *that course's own* OIDC client — `member` opens the course's chat, `admin` makes the person a LibreChat ADMIN in that course and nowhere else (`render.py` points `OPENID_ADMIN_ROLE` at `resource_access.<slug>.roles`).  The lists are also what the registrar's staff tools and `course_usage` check before they answer, which is why the file is the authority rather than the role: the role is a copy the registrar keeps in step with it.

To add an instructor or TA to a course, run the course verb again — it appends and never removes, so repeating it is safe.  It wants at least one instructor every time, so name an existing one when you're only adding a TA:

```
just course engr301-2026fall "ENGR 301 (Fall 2026)" new.prof@example.edu
just course engr301-2026fall "ENGR 301 (Fall 2026)" prof.vex@example.edu --ta ta@example.edu
```

It takes effect at their next sign-in, and they don't need to have signed in before; the registrar pre-creates their account.  **Removing** someone: take them off `instructors:`/`tas:` and run `just course` for that course again — reconcile now takes the course's `admin` role back from anyone the file doesn't name, and if they aren't also a student, their access and key go with it.  Or skip the shell entirely: from the Dev Guide at the front door, `course_staff` adds and removes staff in one sentence (see [the front office](#from-chat-the-front-office)).

**That reconcile revokes as well as grants is new (2026-09-22), and it is worth a look before the first run on a live box.**  Anyone you gave a course's `admin` role by hand in Keycloak, without listing them in `courses.yaml`, loses it on the next `just course` for that course.  That is the file being the authority, which is the design — but it will be a surprise if you didn't know you were relying on a hand grant.

Once someone is on the list, they manage who else gets into their course without you — from their course's chat, or from the Instructor Guide at the front door ("add pat@example.edu to my course").  That is enrollment, and it lives with them; [registrar-spec.md](registrar-spec.md) has the two-step stage-and-apply it runs on.

**The realm's `faculty` role is for operators only.**  It is still wired on the flagship —

```
OPENID_ADMIN_ROLE=faculty
OPENID_ADMIN_ROLE_PARAMETER_PATH=realm_access.roles
OPENID_ADMIN_ROLE_TOKEN_KIND=access
```

— so whoever holds it is ADMIN **at the front door**, which is the vestibule's admin panel on `:3082` and not much else, since the vestibule's lockdown is seeded into ADMIN as well.  Instructors used to be told to take it; that advice predates per-course clients, and it handed every instructor the one panel [the map](#the-map-read-this-first) says to keep in operator hands.  Nothing an instructor does needs it any more: `course_usage` stopped asking for it on 2026-09-22 and reads the roster instead.  Give it to the people who run the box, and take it off anyone else who has it.

### Groups

Keycloak groups organize identity (`/engr301-faculty`, `/engr301-team-gust`) and flow into tokens as a `groups` claim — useful for your own audits and future integrations.  **They are not the share-dialog groups** — those are clicks in the admin panel (→ Groups): `:3082` for the flagship, `{slug}-admin.$ALMANAC_DOMAIN` for a course.  Keep the same names in both places and nobody gets confused.

### The librechat client

- **Secret rotation:** Clients → `librechat` → Credentials → Regenerate → paste into `.env` as `OPENID_CLIENT_SECRET` → `just up`.  Same dance as first boot.
- **Redirect URIs:** login bouncing with a redirect-URI error means the callback (`https://<chat-host>/oauth/openid/callback`) isn't in the client's Valid redirect URIs list.  Add it; no restart needed.

### The Globus flip (production identity)

The realm ships a **disabled** Globus identity provider so going live is a paste, not a build:

1. Register an app at [developers.globus.org](https://developers.globus.org) (Advanced registration).  Redirect URL: `https://<your-auth-host>/realms/classroom/broker/globus/endpoint` Scopes: `openid profile email`.
2. Keycloak → Identity providers → **globus** → paste the Client ID and Secret → **Enabled: on**.  Its first-login flow is already `almanac first broker login` — the registrar sets it on every provision — so a rostered student's first Globus sign-in lands on the account the roster created for them, by email, with no "account already exists" prompt.

   **Until an identity provider is on**, a pre-created user has no password: on a username/password lab realm, set one by hand (Users → the user → Credentials) or nobody rostered after the realm import can sign in.
3. Test in a private window: the login page now offers **Globus**.  Students authenticate through it (their campus IdP behind Globus does the real work), land in Keycloak as federated users, and LibreChat never knows the difference.

After the flip, day-to-day admin work is: new semester → `just course` with each course's instructors → they enroll their own students from chat → done.  Optional polish: to skip Keycloak's login page entirely (straight to Globus), set the realm's browser flow's Identity Provider Redirector to default to `globus` — do this only after local demo accounts are retired.

**What Globus does not carry:** groups or rosters.  Group membership stays manual (or waits for the platform's roster sync — deliberately out of scope here).

### Posture and upkeep

- The bundled realm is a **mock**: `sslRequired: none`, Keycloak in `start-dev`, demo passwords.  Fine on a LAN behind a firewall.  Before real users: real TLS in front, `start` (not `start-dev`) with a proper `KC_HOSTNAME`, demo users disabled, `KC_ADMIN_PASSWORD` rotated.
- **Realm import runs on every boot, and skips any realm that already exists** (`IGNORE_EXISTING`).  So later changes to `keycloak/realm-classroom.json` do NOT apply to a running install — make changes in the admin console, and export if you want them captured: `docker exec alm-keycloak /opt/keycloak/bin/kc.sh export --dir /tmp/export --realm classroom`.  The flip side: a realm file whose `realm:` name the database hasn't seen **is** imported, demo users and all, into a running install.  Renaming the realm file is minting a second realm, not renaming the first.
- State = the `keycloak-db` volume (see [Backups](#backups)).

---

## LiteLLM

### Getting in

`:4000/ui`.  Username `admin`, password = your `LITELLM_MASTER_KEY` (or set `UI_USERNAME`/`UI_PASSWORD` in `.env` for separate UI creds).  The gateway surface is admin-facing — don't put it on the public front door; if it must be reachable, consider `DISABLE_ADMIN_UI=True` or `general_settings.ui_access_mode: admin_only`.

### Models

Two homes, and precedence matters:

- **`litellm/config.yaml`** — the pinned, in-git truth.  The `almanac-chat` entry routes to whatever `INFERENCE_BASE_URL` serves.  More models = more blocks (`almanac-code`, an embeddings model, a cloud escape hatch).
- **The admin UI** (Models → Add) — persists to the database (`STORE_MODEL_IN_DB=True`) and survives restarts.  Handy for experiments; move keepers into the yaml so git stays the record.

The model name students see is the `model_name`; where it actually runs is nobody else's business.  That's the point of the gateway.

### The key contract

**No key without an owner, and no key without an escrow.**  Every key is minted against the course that answers for the spend, and written into OpenBao in the same transaction:

```bash
just key engr301 stu.amaya@example.edu      # course, email, [budget]
```

That stamps `metadata.owner` and `metadata.tags: ["owner:engr301"]` into the key; the tag lands in every spend row (`request_tags`), which is what `just spend` and the future FOCUS export roll up.

**A whole roster is not a loop** — it's the roster upload, in chat or via `just course`.  The registrar mints and escrows one key per student as a side effect of enrollment, so the hand-mint recipe is for staff test keys and one-off repairs, not for provisioning a class.

The recipe prints **metadata, never the key**.  The key is retrievable — that's what the escrow is for — but reading it back is a deliberate, audited act (`just key-show`), not a line of terminal scrollback you have to go find later.  Rotation preserves the remaining fuse; it is not a budget reset.

**Lifecycle** (all verified against our pinned build):

| Action | How |
|---|---|
| List keys | UI → Virtual Keys, or `GET /key/list?return_full_object=true` |
| Retire a key | UI, or `POST /key/delete {"keys": ["sk-..."]}` |
| Rotate a key | **delete + mint** — `/key/regenerate` is Enterprise-walled at our pin |
| Adjust a budget | UI, or `POST /key/update {"key": "sk-...", "max_budget": 10}` |

### Per-student chat attribution

Chat traffic rides one service key (LibreChat's), but every request carries `x-litellm-end-user-id: <student email>` — a standard header LiteLLM honors with zero gateway config.  The student lands in the spend row's `end_user` column.  Where to look: UI → Usage, or `GET /spend/logs`.

Optional hard caps on chat (rarely needed — the GPUs are yours): `POST /customer/new {"user_id": "<email>", "max_budget": 5}` gives an end-user a budget, or set `litellm_settings.max_end_user_budget` for a global default.  Both are free-tier features.

### Faculty analytics — what you can see

The direct answer to "can faculty get analytics out of LiteLLM?": **yes — with one honest boundary.**  Verified empirically against our pinned build:

| Want | Free? | How |
|---|---|---|
| Faculty asks "how's my course doing?" **in chat** | ✓ | the usage tools — see "Usage in the chat" below.  Scoped to their course, self-serve, no extra login |
| Course rollup, month-to-date | ✓ | `just spend` (owner tags) — admin-run |
| Faculty logs into the LiteLLM UI | ✓ | **invitation link** (email + password): `just invite prof@x.edu` |
| Faculty sees *their own* keys/usage | ✓ | invite with role `internal_user` |
| Faculty sees *everything*, read-only | ✓ | invite with role `proxy_admin_viewer` (default of `just invite`) |
| Faculty sees exactly their course *in the LiteLLM UI*, self-serve | ✗ **Enterprise** | the team-admin role is license-walled (`team/member_add` with `role: admin` → 403) |
| Faculty logs in via campus SSO | ✗ effectively Enterprise | UI SSO is free only up to **5 total DB users** — the counter is every row in the user table, so one class roster blows it |

```bash
just invite prof.vex@example.edu                    # read-only everything
just invite ta.jones@example.edu internal_user      # own usage only
```

Each prints a one-time onboarding link (7-day expiry) where they set a password.

**The recommended shape for a department:** courses are **owner tags**, and faculty's front door is the **chat itself** — the usage tools answer "how's my course tracking?" and "who hasn't started yet?" scoped to exactly their course, license-free (next section).  The LiteLLM UI stays what it's good at: the admin's raw ledger, plus `proxy_admin_viewer` invites for faculty who want dashboards — knowing trusted-viewer sees ALL courses.  LiteLLM **teams** still work in OSS (creation, budgets, `team_id` on keys — all free), but nobody below proxy-admin holds a team-scoped admin view in that UI without Enterprise; the chat tools are how we sidestep that wall instead of paying it.

### Spend mechanics (so you don't chase ghosts)

- Spend rows are batch-written (~10 s) and tag rollups aggregate a beat behind realtime.  "Empty right after a request" is lag, not loss.
- Don't set `disable_spend_logs` — the ledger IS the product here.
- `/global/spend/report` is Enterprise; everything `just spend` uses is free.

### Upgrades

The pin is a digest for a reason.  When you bump it: read the release notes first — behavior moves between minors (the very next release after our pin tightened which key parameters non-admins may set).  Then: edit pin → deploy → verify (`just smoke`, mint a test key, check a spend row) → commit.  Same discipline as every other image in the stack.

---

## Usage in the chat (usage-mcp)

The friendliest analytics surface isn't a dashboard — it's the chat the class already lives in.  The `usage-mcp` service serves LiteLLM's ledger back into LibreChat as three tools:

| Tool | Who can call it | Answers |
|---|---|---|
| `my_usage` | everyone | "What did I burn this week?" — chat + API keys, tokens/requests/models |
| `course_usage` | faculty of that course, admins | totals, per-student table, **who hasn't started yet**, model mix |
| `list_courses` | everyone | what the caller is allowed to see |

No LiteLLM login, no Enterprise license, no fourth console.  Students only ever see themselves; faculty see the courses the roster grants them.

### How it trusts (60 seconds)

LibreChat connects per user and stamps two headers on every tool call — who is asking (`{{LIBRECHAT_USER_EMAIL}}`) and whether they're faculty (`{{LIBRECHAT_USER_ROLE}}`) — plus a bearer token (`USAGE_MCP_TOKEN`) proving the call comes from LibreChat at all.  **Identity is never a tool argument**: a prompt can pick the date range, never whose data comes back.  The service reads the ledger through `usage_ro`, a SELECT-only Postgres role `just up` provisions — the LiteLLM master key never enters the container.  It listens on the compose network plus a 127.0.0.1 bind for `just smoke`; nothing off-box reaches it.

### The roster

Course scoping lives in `usage-mcp/roster.yaml` on the box — gitignored, because a student roster is deployment data, not code.  **It is a render, not the file you edit**: the registrar rewrites it from `registrar/courses.yaml` on every roster change ([below](#the-roster-is-a-chat-message-now)).  The shape below is what the service reads, so you can tell what a rollup is doing; first `just up` seeds it, and changes are picked up live:

```yaml
courses:
  engr301:
    name: "ENGR 301 — Engineering Design"
    faculty: [prof.vex@example.edu]
    students: [amaya@example.edu, bram@example.edu]
admins: []          # platform folks who may pull EVERY course
```

- The course slug is the SAME owner slug you mint keys with (`just key engr301 ...`) — that's what folds vAPI-key spend into the course rollup.
- `students:` powers both the chat-usage join and the "who hasn't started yet" answer.  No roster, no anti-join.
- Mint keys with the person's **sign-in email** as the user (`just key engr301 amaya@example.edu`) and their chat + key usage join automatically.  A key minted under any other user_id needs an `aliases:` entry (email → `[user_ids]`) to fold back onto the student.
- Faculty need only the roster listing — the registrar renders `instructors:` + `tas:` from `courses.yaml` into `faculty:` here.  The ADMIN role header used to be required as well, which at the front door meant the realm `faculty` role; since 2026-09-22 the roster alone decides.

### The "Almanac Usage" agent (one-time, two minutes)

The tools exist as soon as the stack is up; an agent is how the class meets them.  From any faculty/admin account:

1. Chat → **Agents** → new agent, name it **Almanac Usage**.
2. Model: `almanac-chat` (it must be tool-capable — this is where the hermes tool parser earns its keep).
3. Instructions — paste:

   > You are the aLLManac usage assistant.  Answer questions about AI usage on this platform by calling your tools — never estimate or invent numbers.  Use my_usage for personal questions and course_usage for course-wide ones (faculty only — the service enforces this; if it declines, relay that gracefully).  Call list_courses when unsure of a course slug.  Report tokens and requests as the real measure — spend shows $0 for campus-hosted models.  Numbers trail live traffic by about ten seconds.

4. Add tools → pick the three **almanac-usage** MCP tools.
5. Share it to everyone (or to course groups) — the marketplace makes it discoverable.

The first custom GPT students meet is a live demo of exactly what they're about to build.  The platform demos itself.

---

## The vestibule (the flagship instance)

The flagship at `chat.<ALMANAC_DOMAIN>` is the room everyone can reach — the one place a student or an instructor can ask *how does this platform work* without spending course tokens to find out.  What it offers is **the five guide agents**, not a model picker: a raw model list here is a general-purpose chatbot on a central budget, which is a different product with a different bill.

**The vestibule is locked down on purpose.**  `librechat/librechat.yaml` turns off the agent builder, sharing, the people picker, the marketplace, prompts, bookmarks, presets, memories (and the memory subsystem itself), multi-convo, model parameters, code execution, web search, composer file search, shared links, skills and user-added MCP servers.  What is left is the picker of guide agents and a place to ask them questions.  Course instances are unaffected — they render their own, classroom-shaped config from `registrar/render.py`.  If your `site/librechat/librechat.yaml` predates 2026-09-15, copy the `interface:` and `memory:` blocks and `endpoints.agents.disableBuilder` across; the modelSpecs block is the only thing that should differ.

**Two tools, and the second one needs a merge on boxes with a `site/` override.**  The vestibule carries `almanac-usage` (spend questions) and, since 2026-09-21, `almanac-registrar` — wired **without** an `X-Course` header.  At the front door that means the report tools answer, `my_courses` answers, and the enrollment tools answer for whoever the roster lists as staff on the course they name; `my_key` and the other course-bound tools go on refusing.  That block lives in the tracked `librechat/librechat.yaml`, which means **a box running `site/librechat/librechat.yaml` will not get it** until someone copies the `mcpServers.almanac-registrar` entry and the `registrar:8080` line under `mcpSettings.allowedAddresses` across by hand.  Nothing breaks without it; the front door just silently has no way to take a complaint, which is the kind of missing thing nobody notices.  The token is already in the container (`env_file: .env`), so no compose change is needed.  Verify with `just reports` after someone files one — and see [design-walls.md](design-walls.md), "The front door is the one room that can take a complaint," before adding an `X-Course` line to make something work.

**Working the queue without a shell.**  `devs:` in `courses.yaml` is the platform team's bug queue — `reports` and `report_triage` from the vestibule, and nothing else: no fleet view, no roster, no key.  That separation is the point, so the queue is safe to hand to a student worker; the reasoning is in [registrar-spec.md](registrar-spec.md), "Reports."  Admins triage implicitly, and `just course-check` warns if you list someone who's already an admin.  `just devs` shows both lists.  Closing a report needs a note, because `my_reports` shows that note back to whoever filed it.

### The guide agents (once per box, and again whenever the docs change)

```
just agents-seed
```

The guides are owned by a **service account** the seeder creates on first run — `guides@almanac.invalid`, a user document with no password and no identity-provider link, so nobody can sign in as it.  Never seed them under a person: whoever owns an agent sees its knowledge files under *Manage files* and can delete them, and LibreChat will let them — a faculty owner did exactly that to the Security Guide on 2026-09-15.  Boxes seeded under a human before that date are adopted into the service account automatically on the next run.  The account carries its own role, `ALMANAC_GUIDES`, which the seeder creates from ADMIN's shape with its own grants forced on (agents use/create/share, file search, file citations).  That matters because the vestibule seeds its lockdown into ADMIN and USER at every boot, LibreChat gates agent *updates* on `AGENTS.CREATE`, and 0.8.8 gates an agent's *knowledge uploads* on `FILE_SEARCH.USE` — which the lockdown turns off, with no roles-API route to open.  A third role is simply never visited by the lockdown.  (Seeding under a human ADMIN, the legacy path, still opens a `CREATE` window through the roles API for the run; it cannot open file search, so on 0.8.8 that path uploads nothing.)  One command does the whole pipeline:

1. renders `corpus/` from front matter (`just docs-corpus`),
2. creates or **updates in place** the five agents, with instructions from `corpus/<slug>/SYSTEM-PROMPT.md`,
3. syncs each agent's knowledge to that guide's corpus — by content hash, uploading what changed before retiring what it replaces,
4. prints the `modelSpecs` block for this box.

**Update-in-place is the whole reason this is a script.**  `modelSpecs` entries reference `agent_id`; recreating an agent mints a new id and silently orphans every spec pointing at the old one, which presents as a vestibule whose guides have vanished.  Agent ids are a published interface.  Never edit an agent's instructions in the UI either — the next run overwrites them, and the version that matters is the one in `docs/agent-contract.md`.

**Knowledge syncs by hash, and the first seed is close to a limit.**  LibreChat rate-limits uploads to **50 per user and 100 per IP per 15 minutes**, and the corpus is fifty files — so the first run on a fresh box spends the owner's whole budget, and a second full run inside that window will be refused.  After that first seed it's cheap: a doc edit costs one or two uploads, because only changed pages are re-embedded.  If you do get rate-limited, the run stops at the first 429 and leaves the previous knowledge attached — wait out the window and run it again.  (Raise `FILE_UPLOAD_USER_MAX` in `.env` if a box genuinely needs a bigger corpus in one pass; it's an abuse control, so raise it deliberately.)

The hashes live in `site/agents-state.json` — per box, gitignored, and a cache rather than a record.  Delete it and the next run re-uploads everything, which is correct, just slower.

While iterating on the prompts, `just agents-seed --skip-files` refreshes only the instructions and touches no files at all.

### The `modelSpecs` block is hand-written, once per instance

Three facts collide here, and the collision is the design:

- `modelSpecs` needs a **literal** `preset.agent_id`, and agent ids are minted per deployment.
- `librechat.yaml` gets **no general env substitution** — `loadCustomConfig` never calls `extractEnvVariable` on the document, so `agent_id: ${AGENT_ID}` reaches LibreChat as that literal string.
- `librechat/librechat.yaml` is **tracked**, and `just sync` is `git reset --hard origin/main`.  A box-local edit to it has a deploy-shaped expiry date.

So a per-box agent id has nowhere to live in the platform's copy, and this is one of the things `site/` exists for.  Copy the config across once:

```
mkdir -p site/librechat
cp librechat/librechat.yaml site/librechat/librechat.yaml
```

Paste the block `just agents-seed` printed at the bottom of its run, and point the mount at your copy in `site/compose.yml`:

```yaml
services:
  librechat:
    volumes:
      # This box's flagship config — it carries agent ids, which are per-box.
      # See docs/admin-guide.md, "The vestibule".
      - ./site/librechat:/app/conf:ro
```

From here on, bring this box up with **`just`** — `just up`, `just deploy`.  A bare `docker compose up -d librechat` merges only `compose.yml`, silently recreates the container without your override, and leaves you a healthy flagship serving the platform's config instead of yours.  (Learned the same afternoon it was written.)

A DIRECTORY mount, matching core — never bind a single file that gets rewritten.  Compose merges `volumes:` by target, so this one line replaces the core bind and inherits the rest — `just config librechat` shows you the merged result rather than making you guess at compose's merge rules.  Then `just up`, and the flagship reads your copy.

### Then check it, because every step here fails quietly

```
just agents-check
```

Read-only, and it asks the four questions in the order they go wrong: is there a `modelSpecs` list on this box at all, is `enforce` set, does every spec point at an agent that exists, and does every guide actually carry knowledge.  The orphan case is the one worth running it for — a spec pointing at an id that no longer exists doesn't error, it just quietly serves a vestibule with a guide missing.

**The cost, stated plainly:** this box no longer inherits platform changes to `librechat.yaml`.  When a release touches it, merge by hand —

```
diff -u site/librechat/librechat.yaml librechat/librechat.yaml
```

— which is the honest trade for a file that has to know something only this box knows.  A course instance never has this problem: the registrar *renders* `fleet/<slug>.librechat.yaml`, so per-instance values have a template to come from.  The flagship is the one hand-written instance, and it stays that way until there's a second reason to render it.

### `enforce: true` is what hides the raw models

`modelSpecs.enforce: true` restricts the picker to the specs you listed.  `interface.modelSelect: false` is the *other* control people reach for and it is not the same thing — agents are an endpoint in LibreChat, so that flag may hide the agent picker along with the model list.  Verify it against the running instance before trusting either reading.

---

## The course fleet (the registrar)

Every course gets **its own LibreChat instance** at its own hostname — `engr301-2026fall.<your-domain>` — with the teaching staff as its admins and the roster gating its door.  The full design (and every decision's why) is `docs/registrar-spec.md`; this is the operator's path.

### Staging the embedding model (before the box has no internet)

The RAG service embeds knowledge files with a local CPU model, and it downloads that model the first time something needs embedding.  On a box with internet you will never notice.  On an air-gapped one the failure is quiet and nasty: agents come up, answer, and know nothing, because no knowledge file can be embedded.

Stage it on purpose instead:

```bash
just embed-check                      # what is staged?  reads the cache, no network
just embed-stage                      # download it now — needs egress for this command only
```

For a site that will never have egress, do it on a staging box and carry the tarball:

```bash
just embed-export hf-cache.tar        # on the box with internet  (129 MB)
# copy it over
just embed-import hf-cache.tar        # on the air-gapped one
```

`embed-check` exits non-zero when the cache is cold, so it is safe in a pre-flight script.  It is deliberately **not** part of `just deploy` — a fresh install with internet works fine without staging, and failing the deploy there would be wrong.

The rule behind it: **nothing fetches a model at runtime.**  Approved weights are put on the box by a person, which is the only way "we know what is on this box" stays true.

---

### Which model the guides run on

The guides' job is narrow — regurgitate the attached documentation, hold a boundary, call one or two constrained tools, never invent.  That reads like the easiest workload on the platform and it is not: it needs **grounding and instruction-hierarchy at the same time**, and those turn out to be separate capabilities.  Four local models were measured against it and none held it; one jailbroke on the first try, one invented a storage architecture it had never read about, one returned an empty message.  The numbers are in [design-walls.md](design-walls.md#the-guide-agents-need-a-small-frontier-model-not-a-small-local-one-measured-2026-09-12).

So the vestibule is where a **small hosted model** earns its keep, and it is the cheapest place on the platform to put one: six agents, low volume, and a knowledge corpus that is this repository's own published documentation, so nothing that leaves the box is unpublished text.  Course instances are a separate decision with a different answer — student conversations are not published text.

To switch:

1. Uncomment the `almanac-office` block in `litellm/config.yaml`.
2. Set `OFFICE_MODEL`, `OFFICE_BASE_URL`, `OFFICE_API_KEY` in `.env`.  Prefer the **Azure AI Foundry** shape (`azure_ai/<deployment>`) where you have it: LiteLLM reads the real per-deployment rates when it polls the endpoint, so the ledger carries true pricing instead of a figure somebody typed.  The vendor's own API (`openai/<id>`) falls back to LiteLLM's pinned cost map.
3. `just deploy`.
4. `AGENT_MODEL=almanac-office just agents-seed` — `AGENT_MODEL` must be explicit or the seeder preserves whatever model each agent already has, which is the behaviour you want every other time you run it.
5. Paste the reprinted `modelSpecs` block (the `model:` line changes on every row) and check with `just agents-check`.

**Then confirm a spend row actually lands**, with real dollars on it:

```bash
just spend | head            # a $0.00 row for almanac-office is a failure, not a bargain
```

A model newer than our LiteLLM pin and *not* behind Foundry is in neither price source.  It answers perfectly and meters at zero, and zero is an absence rather than an error — the same failure that once moved every guide onto an unpriced alias and quietly stopped attributing the vestibule to anybody.

---

### Set the context window, because nothing does it for you

`maxContextTokens` is **not set anywhere in the tracked config**, and LibreChat does not read a window off the gateway.  A custom deployment name is not a model LiteLLM can look up, so an unrecognised model falls back to LibreChat's own default — measured at about **28k on a model that serves 922k** (2026-09-21).  Nothing warns you.  A long conversation simply starts losing its early turns.

Set it on the endpoint in your instance's `librechat.yaml`:

```yaml
      maxContextTokens: 64000
```

**The number is a budget, not a capability, and it belongs to your deployment.**  At $0.20/Mtok a fully packed 922k request is roughly $0.18 before a token comes back, and the guides will fill whatever they are given — a two-turn "how do I" already runs ~16k on retrieval alone.  64k is about eight turns of real depth against a bounded worst case.  Take more if your pools are sized for it; take less on a tight budget.

**Do not copy a number from another box.**  The window has to match the model actually being served: set it above what your backend accepts and you convert today's silent truncation into a request-time error, which is worse — a conversation that quietly forgets is still a working room, and the smallest boxes are the ones most likely to be somebody's first install.  This is why the value lives in *your* config and not in the tracked one.

**Set it from what your endpoint SERVES, not from what the model supports** — on Ollama those differ silently and by a lot.  `/api/show` reports the architecture's ceiling, which is the number that misleads; `/api/ps` reports what a loaded model was actually given.  Measured on this fleet's inference host (Ollama 0.31.2): a llama3.1-8B that natively supports 128k, served at `context_length: 32768`, with no `num_ctx` set on any model — a server-wide cap, invisible from the model side.

```bash
curl -s http://<inference-host>:11434/api/ps | python3 -m json.tool   # what is actually served
```

And Ollama's `num_ctx` covers the prompt **and** the completion, so the input bound has to sit under it with room for the answer — 24000 against a served 32768, not 32768.

**Overshooting here does not fail loudly.**  Ollama truncates the front of the prompt and answers anyway, and the front of the prompt is the system prompt: an agent quietly loses its instructions mid-conversation and keeps talking, with nothing in any log an operator reads.  That is why this knob errs low.  On the course fleet the per-box lever is `REGISTRAR_DEFAULT_CONTEXT_TOKENS` in `.env`, and any single course can override it with `context_tokens:` in its record.

While you are on that endpoint, check `models.default` lists every model you actually serve.  The guides reach their model by direct reference, so a missing entry works anyway — which is exactly why nobody notices the endpoint has no idea what it is talking to.

### Once per box: open the escrow

```
just bao-init
```

Initializes OpenBao, mounts the `almanac/` kv2 store, turns on the audit device, and provisions the registrar's AppRole.  It writes the unseal key and role credentials into `.env` and prints the **root token exactly once** — password manager, not a sticky note.  After any restart, `just up` re-unseals automatically.

### Per course: one command

```
just course engr301-2026fall "ENGR 301 (Fall 2026)" prof.vex@example.edu
```

That single act provisions everything the spec promises: the LiteLLM **team** (the course's $1000/term pool — override with `--budget`), the team-scoped **service key** (escrowed), the course's **OIDC client** with its `admin`/`member` door roles, staff grants, the **instance render** (chat + Meili + panel + vhost under `fleet/`), and finishes by starting the containers and gracefully reloading the edge.  Extra flags pass through: `--ta ta@x.edu`, `--college cci`, `--budget 1500`.  Run it twice — it's idempotent; that's the point.

DNS: point `*.<ALMANAC_DOMAIN>` at the box once and every future course is covered (wildcard cert via the DNS-01 block in `caddy/Caddyfile` for real deployments; `*.localhost` needs nothing at all).

### From chat: the front office

Everything `just course` does, a platform admin can do from the **Dev Guide** at the front door — and anyone at all can *ask* for a room.  [registrar-spec.md](registrar-spec.md), "Phase 2a — the front office," is the design; this is the operating view.

- **The open door is a ticket, not a generator.**  Anyone who can sign in can say "I'd like a course for BIO 210 next term" to the Instructor or Student Guide.  `course_request` puts the deployment's front-door question to them first — coursework, not sponsored research — and files only on a yes, recording the exact wording they agreed to.  They describe what they need; they never name a budget.  Tickets land in `registrar/requests.yaml` (gitignored; it names people).  `my_requests` shows them where theirs stands and everything the admins wrote back.
- **The desk** answers the `admins:` list and nobody else, and works a ticket three ways, like a problem report: `course_approve` (requires a **budget** — the pool is the platform's to set — plus an optional note), `course_return` (a note saying what you need; they answer with `course_request_reply` and it comes back to the open queue), or `course_reject` (a note saying why; closed).  `course_requests` is the queue with the whole thread on each ticket.  Beside those: `course_create` (skip the queue), `course_staff`, `course_budget_set`, and `fleet_inventory`.  Every one that changes a course describes the change first and acts only when called again with `confirm=true` — the guide is told to wait for a yes in between.
- **The wording is yours.**  The front-door question comes from `registrar/front-door.md` if you write one, and the tracked `front-door.example.md` if you don't.  Edit it on the box; it's read on every request, no restart and no reseed.
- **A new course isn't running until the host starts it** — see the next section.  Without the watcher, `just course-up` after an approval finishes the job.

### Before you show it to anyone: the tool evals

The guides now *do* things, and a guide that applied a roster nobody agreed to reads exactly like one that didn't.  So the tool cases in [agent-contract.md](agent-contract.md#the-tool-cases) score what each guide **called**, and the transcript shows every call above every reply:

```
just evals --case E1,E2,E3,E4,Q1,Q2,Q3,D1,D2,W3,W4
```

Run it after `just agents-seed`, on the model the guides actually use, and read `site/evals/<stamp>.md` against each case's *passes when*.  Nothing scores itself.

**What it adds to the box, so it doesn't surprise you.**  The run resets a fixture first: an `evals-sandbox` course in `courses.yaml` (a record only — never provisioned, so no team, key, client or instance; `render` skips it), four personas on `@almanac.invalid`, one of them on `admins:`, and two request tickets, `rq-eval01` and `rq-eval02`.  Nobody can sign in as an `.invalid` address, and **the registrar rehearses every write those identities attempt**: every gate and refusal runs for real, and the change itself is replaced with a message saying what would have happened.  No roster, key, course, ticket, email or Teams post comes out of an eval run.  The admin persona can *read* what an admin reads — the queue, the fleet — so transcripts in `site/evals/` carry the same data `courses.yaml` does, and stay on the box for the same reason.

### Who hears about it: notifications

Tickets move without anyone being told unless you set this up, and every piece of it is optional.

- **The person** who filed a request gets an email when it's approved, returned or rejected, with the admin's note in full — plus the chat address on approval, sent to the instructors and any TAs as well.
- **The desk** hears about new requests and replies.  With `NOTIFY_WEBHOOK_URL` set, that's one post to your admins' channel — a Teams Workflows "when a webhook request is received" URL by default, or anything that takes `{"text": ...}` with `NOTIFY_WEBHOOK_FORMAT=text`.  Decisions and new problem reports go to the channel too, so whoever is on the desk sees what the others did.  With no webhook, new requests and replies are emailed to the `admins:` list, and decisions and reports aren't sent anywhere, since each would be one more email to everyone.
- **Mail** goes through `SMTP_HOST`.  A campus relay that trusts the box's address needs only the host, port and a `SMTP_FROM` it accepts; `SMTP_USER`/`SMTP_PASSWORD` switch on authentication (and STARTTLS by default — `SMTP_TLS=ssl` for port 465).  **With no `SMTP_HOST`, every message is appended to `registrar/outbox.log`** instead, which is the home-lab answer: nothing is lost and nothing leaves the box.  A relay that's down never fails the tool — the message lands in the outbox and the admin is told.

**What leaves the box is the envelope, never the content** — ticket id, kind, name, who, term.  The purpose, the details, the thread and every word of a problem report stay in the queue, where the desk reads them.  The only full text that travels is an admin's note to a requester, which the admin wrote to be sent.  [design-walls.md](design-walls.md), "A notification is a pointer, not the content," has the reasoning.

After setting any of it, `just deploy` (the registrar reads these at start), then `just notify-test` — it prints what's configured without printing a secret, sends a test email to the `admins:` list (or `just notify-test you@example.edu`), and posts once to the webhook.

### The fleet watcher

The registrar never holds the docker socket, so a course created from chat is provisioned and rendered but not started.  Once per box:

```
just fleet-watch-install
```

That installs a systemd `--user` path unit on `fleet/fleet.yml`; every provision rewrites that file last, and the unit runs `just course-up`, which starts new instances and reloads the edge.  It runs as whoever installs it, which should be the repo owner — the uid the registrar renders as.  It needs lingering on (`sudo loginctl enable-linger <user>`) or it stops when that user logs out; the recipe warns if it's off.  `journalctl --user -u almanac-fleet` shows each run.  The reasoning, and why it isn't the socket, is a wall: [design-walls.md](design-walls.md), "A course made in chat is rendered, not running."

### The roster is a chat message now

Instructors don't get a console; they get their own chat.  In their course instance, the staff paste the class list at the **Course Setup** agent (recipe below) in any format their SIS exports:

1. `roster_stage` — the registrar extracts the emails, shows exactly what would change (adds/removes/ignored junk), changes **nothing**.
2. `roster_apply` — executes that plan: every student gets the `member` door role (no roster, no login), a minted vAPI key inside the course team, and an escrow record in OpenBao.  Removals revoke and close.

Students ask **`my_key`** in chat for their take-home key (opencode, laptops); **`rotate_my_key`** if it leaks — remaining budget carries over.  Staff get `roster_show` and `course_keys` (custody status — never the keys themselves; nobody but the owner ever sees a key).

The `usage-mcp/roster.yaml` you used to edit by hand is now a **render** the registrar rewrites on every roster change — edit `registrar/courses.yaml` (or run `just course`) instead.

### The "Course Setup" agent (one-time per course, two minutes)

Same pattern as the usage agent, made from a staff account **in the course's instance**: new agent → model `almanac-chat` → add the **almanac-registrar** MCP tools (and the usage tools — one agent can hold both) → instructions:

> You are this course's setup assistant.  When staff paste a class roster, call roster_stage with the pasted text, show them the plan, and only call roster_apply with the stage id after they confirm.  When students ask for their key, call my_key.  Never invent keys or enrollment state — the tools are the truth.  If a tool declines, relay its message; the service enforces who may do what.

Share it to the course.  Enrollment is now a conversation.

### What lives where (the fleet files)

| Path | What | Who writes it |
|---|---|---|
| `registrar/courses.yaml` | course records, budgets, rosters | you + the registrar |
| `fleet/fleet.yml` | the instances (compose include) | the registrar |
| `fleet/<slug>.env` | instance secrets (CREDS pinned forever) | the registrar |
| `fleet/<slug>.librechat.yaml` | instance config (X-Course lives here) | the registrar |
| `fleet/caddy/<slug>.caddy` | the vhost pair | the registrar |
| `usage-mcp/roster.yaml` | usage scoping (a render) | the registrar |
| `fleet/inventory.md`, `.json` | the census — every instance on one page | the registrar (`just fleet`, `fleet_inventory`) |
| `registrar/nominations.yaml` | agents nominated as templates | the registrar |
| `fleet/templates/<id>-<name>.yaml` | an exported nomination — an agent as a file | the registrar (`just template`, `nomination_export`) |

All gitignored, all regenerable (`just` `course`/`reconcile`/`render`) — except the secrets in `fleet/<slug>.env`, which persist across renders for the same reason `CREDS_KEY` in `.env` does.

### Seeing the fleet from above

`just fleet` prints one line per instance and writes `fleet/inventory.md` (a page for people) and `fleet/inventory.json` (a feed for whoever wants one): answering or not, users, conversations, agents and how many are shared, files and their bytes, database size, the pool spent against its cap, and the roster counts — plus findings: an instance rendered but not answering, Actions enabled with no allowlist, a pool past 90%, people at a course's door who aren't on its roster, a database left behind by a deleted course.

The same census answers in chat.  Add the **almanac-registrar** tools to an agent in any course instance where you're staff (the "Course Setup" agent above already has them) and, if your email is on the `admins:` list in `registrar/courses.yaml`, three more tools answer: `fleet_inventory`, `fleet_access <course>` (roster vs. door vs. who actually signed in, with the diffs), and `fleet_exposure <course>` (every agent's share scope, every file's size and owner, the allowlist).  Course staff who aren't platform admins get a refusal that points them at their own course's tools.

What you will not see, from either path: a message, a conversation title, or an agent's instructions.  The census stops at the envelope on purpose — the why is a wall in [design-walls.md](design-walls.md), and the short version is that a transcript read is an investigation, not a dashboard.

### Nominations: an agent worth copying

A student or instructor in a course can say `nominate_agent <agent_id> "<why>"` about an agent they built (staff: any agent in the course).  Nothing moves until you look.  `just nominations` (or the `nominations` tool) lists them; `just template <id>` (or `nomination_export`) writes `fleet/templates/<id>-<name>.yaml` — name, instructions, model, tools, and the knowledge files *by name*, with provenance.  Read it.  If it belongs on the flagship or in another course, seed it there the way the guides are seeded; re-attach knowledge deliberately, since the template lists files and never carries them.  The author's name stays on it.

---

## Channels: stable and latest

There are two kinds of aLLManac box: the one courses run on, and the one where the next version gets broken first.  A **channel** is what tells them apart, and it is one file of image pins — `channels/stable.env` or `channels/latest.env`, both tracked.  `.env` picks one with `ALMANAC_CHANNEL` (stable when unset), and `just` hands that file to compose ahead of `.env` on every call, so `just channel` on any box says which channel it runs and the exact images that resolves to.

The rule that makes this worth having: **a pin moves to `latest` first, gets deployed to a box nobody teaches on, gets walked as a student and a professor, and only then moves to `stable`.**  What differs between the two files is exactly the upgrade under test, and the comment on each `latest` line says what is being watched and since when.  Release candidates go to `latest`.  A course never sees one.

Two traps, both loud on purpose:

- **An `.env` that predates channels still carries its own image lines, and a pin set in `.env` wins over the channel.**  That is the right precedence for a hotfix and the wrong one for a box that never leaves the pins it was born with.  `just channel` warns on every such line; delete them.
- **`ALMANAC_CHANNEL` naming a file that does not exist fails at parse time**, before any recipe runs.  Nothing falls back to compose's defaults silently.

**What `latest` finds goes upstream.**  We are a downstream of LibreChat, and it is largely one person's project; a release candidate on a box nobody teaches on is the cheapest place anyone will ever reproduce a bug in it.  When `latest` breaks, the deliverable is not only our workaround: it is a minimal reproduction — the pinned tag, the `librechat.yaml` keys involved, the exact request, the log line — filed as an issue (or a pull request, when the fix is small) on [danny-avila/LibreChat](https://github.com/danny-avila/LibreChat), and linked from the `latest.env` comment for that pin so the next person knows it is known.  Suggestions count too: if a feature we rely on has an obviously better shape, say so there, not only here.  Treat the upstream as a colleague, not weather.

The datastores are in the channel too — Mongo, Meilisearch, Postgres, pgvector — because they were the gap: `mongo:7` is a floating tag and a `just pull` could move it a patch release with no commit saying so.  Moving one of those on `stable` is a data migration, not an image bump: Mongo wants its featureCompatibilityVersion stepped, Meilisearch wants a dump and restore.  `latest` already runs Mongo 8 and Meilisearch 1.35 because 0.8.8 needs them; when stable follows, it follows with a plan.

Everything else is the same box.  Same `.env` shape, same `site/`, same `just deploy` — the dev playground is a full stack, not a lighter one, because the point is to find what the upgrade breaks in the plumbing, and half a stack has half the plumbing.  Inference is a URL either way: almanac only consumes an endpoint, so a dev box points at whatever the stable box points at, or at something cheaper.

## Backups

The named volumes are the state.  What each holds, and how much it would hurt:

| Volume | Contents | Hurt level |
|---|---|---|
| `mongo-data` | LibreChat: users, conversations, **agents**, ACLs | High — the class's work |
| `vector-data` | pgvector: agent knowledge-file embeddings | Medium — rebuildable by re-uploading files |
| `litellm-db` | Keys, budgets, **spend history** | High — the ledger |
| `keycloak-db` | Users, roles, the Globus broker config | High — identity |
| `meili-data` | Search index | Low — rebuilds itself |
| `bao-data` | **The escrow** — every minted key, versioned | High — but online-snapshotable (`bao operator raft snapshot save`) |
| `chat-<slug>-*` / `meili-<slug>-*` | each course instance's images/logs/search | Mongo holds the real data (one DB per course inside `mongo-data`) |
| `hf-cache` (vllm stack) | Model weights | Low — re-downloads |

Consistent dumps without stopping anything:

```bash
docker exec alm-litellm-db  pg_dump -U litellm  litellm  > litellm.sql
docker exec alm-keycloak-db pg_dump -U keycloak keycloak > keycloak.sql
docker exec alm-vectordb    pg_dump -U rag      vectordb > vectordb.sql
docker exec alm-mongo       mongodump --archive           > mongo.archive
```

And the facts that outrank everything: **`.env` is not in git** (it holds every secret — back it up separately, permissions tight, and `usage-mcp/roster.yaml` deserves the same ride: also gitignored, also on-disk), and **`CREDS_KEY`/`CREDS_IV` are pinned for life** — restore a Mongo backup with a different pair and every stored key decrypts to garbage.

---

## Troubleshooting quick hits

| Symptom | Cause → fix |
|---|---|
| Login bounces with a redirect-URI error | Callback URL missing from the `librechat` client → add it (Keycloak → Clients) |
| `[openidStrategy] only requests to HTTPS are allowed` | Plain-http `OPENID_ISSUER` — LibreChat ≥0.8 refuses it → README "LAN HTTPS" |
| Share dialog can't find a group | It's looking at **LibreChat-local** groups — create it in that instance's own admin panel (`:3082` for the flagship, `{slug}-admin.` for a course); and the person must have logged in once |
| Faculty missing admin controls in their course | Not in that course's `instructors:`/`tas:`, or added after their last sign-in → `just course <slug> "<name>" <email>`, then sign out and back in |
| `just spend` / tags look empty | Aggregation lag (~10 s batch + async rollup) → wait a beat |
| Invitation link dead | 7-day expiry → `just invite` again |
| Users suddenly get "invalid key provided" | `CREDS_KEY`/`CREDS_IV` changed on a live instance → restore the old pair if you have it; otherwise users re-save keys |
| LiteLLM UI SSO returns 403 about ">5 users" | The free-tier SSO wall (counts **all** DB users) → use `just invite` (email+password), or license |
| A key 403s with a license message | You've touched an Enterprise feature (top-level `tags`, `/key/regenerate`, team `role: admin`) → the OSS paths in this guide |
| Usage tools missing from the agent-builder tool list | usage-mcp down or the mcpServers block/token mismatched → `just smoke`, then compare `USAGE_MCP_TOKEN` in .env against librechat.yaml's header |
| Usage tool answers "couldn't tell who's asking" | The call didn't come through LibreChat's per-user connection (or placeholders didn't resolve) → re-login; check the two `{{...}}` headers in librechat.yaml |
| `usage-mcp (stats)` FAILs in smoke / health says db unreachable | The `usage_ro` role is missing (first boot on an old checkout) → `just usage-role` |
| Course rollup misses a student's key usage | Key minted under a user_id that isn't their email → add an `aliases:` entry in roster.yaml, or re-mint with the email |
| Faculty told the course view is "a faculty view" | Not in that course's `instructors:`/`tas:` → `just course <slug> "<name>" <email>`; roster.yaml is a render, never edit it |
