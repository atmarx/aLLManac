# The aLLManac — Admin Guide

*Keycloak decides **who**.  LiteLLM decides **how much**.  This guide is those two consoles, the seams between them, and the honest boundaries of the free tier — verified against the exact pinned builds this stack runs.*

## The map (read this first)

| Surface | Where | Login | What lives there |
|---|---|---|---|
| Keycloak admin | `:8080` | `KC_ADMIN` / `KC_ADMIN_PASSWORD` | Identity: users, realm roles, the Globus broker, OIDC clients |
| LiteLLM admin | `:4000/ui` | `LITELLM_MASTER_KEY` | The ledger: models, keys, budgets, spend |
| LibreChat admin panel | `:3082` | faculty SSO (same button) | **Local groups** for agent sharing, role permissions, config overrides |
| LibreChat | `:3080` | SSO | The chat itself — mostly runs itself |

Three things in this stack are called "groups," and confusing them costs an afternoon:

- **Keycloak groups/roles** — identity facts.  The `faculty` realm role is the one that matters: it makes someone a LibreChat ADMIN at login.
- **LibreChat local groups** (admin panel) — the ONLY groups the agent-share dialog can see.  Keycloak's groups claim never reaches LibreChat's ACL system at v0.8.7 (upstream [#10006](https://github.com/danny-avila/LibreChat/issues/10006)).
- **LiteLLM teams** — optional ledger structure.  Usable, but see [the boundary table](#faculty-analytics--what-you-can-see) before you build a course on them.

---

## Keycloak

### Getting around

Admin console at `:8080`, then **switch the realm** (top-left dropdown) from `master` to `northwinds` — everything course-related lives there.  `master` is Keycloak's own housekeeping realm; stay out of it except to manage the admin account itself.

### Users

- **Local (demo/mock) users:** Users → Add user (set email, mark email verified) → Credentials → set a password (temporary off).  The bundled realm ships `prof.vex`, `stu.amaya`, `stu.bram` (password `Demo123!`).
- **Federated users (production):** you don't create them.  When identity brokering is on, a person's first SSO login creates their Keycloak user automatically (`syncMode: IMPORT`).  Your job is what happens *after* arrival: role assignment.

### Roles: the faculty switch

The realm has two roles, `faculty` and `student`.  The one with teeth is `faculty`: LibreChat maps it to its ADMIN role at login via

```
OPENID_ADMIN_ROLE=faculty
OPENID_ADMIN_ROLE_PARAMETER_PATH=realm_access.roles
OPENID_ADMIN_ROLE_TOKEN_KIND=access
```

(Keycloak puts realm roles at `realm_access.roles` in access tokens by default — no mapper needed.)  **To make someone faculty:** Users → pick the user → Role mapping → Assign role → `faculty`.  Takes effect at their next login.  This works identically for local and Globus-federated users.

### Groups

Keycloak groups organize identity (`/engr301-faculty`, `/engr301-team-gust`) and flow into tokens as a `groups` claim — useful for your own audits and future integrations.  **They are not the share-dialog groups** — those are clicks in the admin panel (`:3082` → Groups).  Keep the same names in both places and nobody gets confused.

### The librechat client

- **Secret rotation:** Clients → `librechat` → Credentials → Regenerate → paste into `.env` as `OPENID_CLIENT_SECRET` → `just up`.  Same dance as first boot.
- **Redirect URIs:** login bouncing with a redirect-URI error means the callback (`https://<chat-host>/oauth/openid/callback`) isn't in the client's Valid redirect URIs list.  Add it; no restart needed.

### The Globus flip (production identity)

The realm ships a **disabled** Globus identity provider so going live is a paste, not a build:

1. Register an app at [developers.globus.org](https://developers.globus.org) (Advanced registration).  Redirect URL: `https://<your-auth-host>/realms/northwinds/broker/globus/endpoint` Scopes: `openid profile email`.
2. Keycloak → Identity providers → **globus** → paste the Client ID and Secret → **Enabled: on**.
3. Test in a private window: the login page now offers **Globus**.  Students authenticate through it (their campus IdP behind Globus does the real work), land in Keycloak as federated users, and LibreChat never knows the difference.

After the flip, day-to-day admin work is: new semester → students arrive by logging in → you assign `faculty` to instructors → done.  Optional polish: to skip Keycloak's login page entirely (straight to Globus), set the realm's browser flow's Identity Provider Redirector to default to `globus` — do this only after local demo accounts are retired.

**What Globus does not carry:** groups or rosters.  Group membership stays manual (or waits for the platform's roster sync — deliberately out of scope here).

### Posture and upkeep

- The bundled realm is a **mock**: `sslRequired: none`, Keycloak in `start-dev`, demo passwords.  Fine on a LAN behind a firewall.  Before real users: real TLS in front, `start` (not `start-dev`) with a proper `KC_HOSTNAME`, demo users disabled, `KC_ADMIN_PASSWORD` rotated.
- **Realm import only happens on first boot** (empty database).  Later changes to `keycloak/realm-northwinds.json` do NOT apply to a running install — make changes in the admin console, and export if you want them captured: `docker exec alm-keycloak /opt/keycloak/bin/kc.sh export --dir /tmp/export --realm northwinds`
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

**No key without an owner.**  Every key is minted against the org unit that answers for the spend:

```bash
just key stu.amaya engr301 5      # user, owner, budget ($)
```

That stamps `metadata.owner` and `metadata.tags: ["owner:engr301"]` into the key; the tag lands in every spend row (`request_tags`), which is what `just spend` and the future FOCUS export roll up.  A whole roster is a loop:

```bash
while read -r user; do just key "$user" engr301 5; done < roster.txt
```

Each mint prints the key JSON once — that `sk-...` is the student's copy; hand it over individually (LMS message).  It is not retrievable later, only replaceable.

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
just invite prof.vex@northwinds.edu                    # read-only everything
just invite ta.jones@northwinds.edu internal_user      # own usage only
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

Course scoping lives in `usage-mcp/roster.yaml` on the box — gitignored, because a student roster is deployment data, not code.  First `just up` seeds it from the example; edits after that are picked up live:

```yaml
courses:
  engr301:
    name: "ENGR 301 — Engineering Design"
    faculty: [prof.vex@northwinds.edu]
    students: [amaya@northwinds.edu, bram@northwinds.edu]
admins: []          # platform folks who may pull EVERY course
```

- The course slug is the SAME owner slug you mint keys with (`just key ... engr301`) — that's what folds vAPI-key spend into the course rollup.
- `students:` powers both the chat-usage join and the "who hasn't started yet" answer.  No roster, no anti-join.
- Mint keys with the person's **sign-in email** as the user (`just key amaya@northwinds.edu engr301`) and their chat + key usage join automatically.  A key minted under any other user_id needs an `aliases:` entry (email → `[user_ids]`) to fold back onto the student.
- Faculty need BOTH the `faculty` realm role (that's what makes the role header say ADMIN) and a roster listing (that's what narrows it to *their* course).

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

## The course fleet (the registrar)

Every course gets **its own LibreChat instance** at its own hostname — `engr301-2026fall.<your-domain>` — with the teaching staff as its admins and the roster gating its door.  The full design (and every decision's why) is `docs/registrar-spec.md`; this is the operator's path.

### Once per box: open the escrow

```
just bao-init
```

Initializes OpenBao, mounts the `almanac/` kv2 store, turns on the audit device, and provisions the registrar's AppRole.  It writes the unseal key and role credentials into `.env` and prints the **root token exactly once** — password manager, not a sticky note.  After any restart, `just up` re-unseals automatically.

### Per course: one command

```
just course engr301-2026fall "ENGR 301 (Fall 2026)" prof.vex@northwinds.edu
```

That single act provisions everything the spec promises: the LiteLLM **team** (the course's $1000/term pool — override with `--budget`), the team-scoped **service key** (escrowed), the course's **OIDC client** with its `admin`/`member` door roles, staff grants, the **instance render** (chat + Meili + panel + vhost under `fleet/`), and finishes by starting the containers and gracefully reloading the edge.  Extra flags pass through: `--ta ta@x.edu`, `--college cci`, `--budget 1500`.  Run it twice — it's idempotent; that's the point.

DNS: point `*.<ALMANAC_DOMAIN>` at the box once and every future course is covered (wildcard cert via the DNS-01 block in `caddy/Caddyfile` for real deployments; `*.localhost` needs nothing at all).

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

All gitignored, all regenerable (`just` `course`/`reconcile`/`render`) — except the secrets in `fleet/<slug>.env`, which persist across renders for the same reason `CREDS_KEY` in `.env` does.

---

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
| Share dialog can't find a group | It's looking at **LibreChat-local** groups — create it in the admin panel (`:3082`); and the person must have logged in once |
| Faculty missing admin controls | `faculty` realm role not assigned, or assigned after login → assign, re-login |
| `just spend` / tags look empty | Aggregation lag (~10 s batch + async rollup) → wait a beat |
| Invitation link dead | 7-day expiry → `just invite` again |
| Users suddenly get "invalid key provided" | `CREDS_KEY`/`CREDS_IV` changed on a live instance → restore the old pair if you have it; otherwise users re-save keys |
| LiteLLM UI SSO returns 403 about ">5 users" | The free-tier SSO wall (counts **all** DB users) → use `just invite` (email+password), or license |
| A key 403s with a license message | You've touched an Enterprise feature (top-level `tags`, `/key/regenerate`, team `role: admin`) → the OSS paths in this guide |
| Usage tools missing from the agent-builder tool list | usage-mcp down or the mcpServers block/token mismatched → `just smoke`, then compare `USAGE_MCP_TOKEN` in .env against librechat.yaml's header |
| Usage tool answers "couldn't tell who's asking" | The call didn't come through LibreChat's per-user connection (or placeholders didn't resolve) → re-login; check the two `{{...}}` headers in librechat.yaml |
| `usage-mcp (stats)` FAILs in smoke / health says db unreachable | The `usage_ro` role is missing (first boot on an old checkout) → `just usage-role` |
| Course rollup misses a student's key usage | Key minted under a user_id that isn't their email → add an `aliases:` entry in roster.yaml, or re-mint with the email |
| Faculty gets "not listed as faculty for..." | They're ADMIN (realm role) but not in that course's `faculty:` list → edit roster.yaml (live, no restart) |
