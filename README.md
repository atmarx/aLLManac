# The aLLManac

*a·**LLM**·anac — look again, it was there the whole time.*

A farmhouse almanac is the book on the kitchen shelf you consult all season —
planting dates, frost warnings, the accumulated judgment of people who did this
before you. The aLLManac is that book for a class or a lab: **a self-hosted
custom-GPT service** where a course builds its own assistant on **your models,
your GPUs, your identity system, your ledger** — and the large language model
is baked right into the middle of the name, because hiding it would be lying.

It is the sister project of [Root Cellar](https://github.com/atmarx/root-cellar),
the research-data governance platform. The cellar keeps things cold, safe, and
provable. The almanac is the book you actually open every day. Same farmhouse,
two rooms.

**What a group gets:** a shared assistant ("custom GPT") that the *whole team
co-edits* — instructions, knowledge files, tools — with per-user API keys,
per-key budgets, and every token metered to an owner who can see exactly what
their class used this month. No data leaves campus unless you point it there.

---

## Architecture

```
                Browser
                   │  OIDC
                   ▼
             ┌──────────┐        ┌───────────┐       ┌──────────┐
             │ Keycloak │◀───────│ LibreChat │──────▶│ LiteLLM  │──▶ inference
             │ (+Globus │        │  the UI   │       │ keys ·   │    ├─ vLLM (vllm/ stack)
             │  broker) │        └─────┬─────┘       │ metering │    ├─ campus GPU box
             └──────────┘              │             └──────────┘    └─ cloud (if you must)
                                       │
                          Mongo · Meilisearch · RAG API · pgvector
```

Seven moving parts, each doing one job:

| Part | Job |
|---|---|
| **LibreChat** | The chat UI. "Custom GPTs" are LibreChat **Agents**: a system prompt + knowledge files (RAG) + tools, shareable to a group with an **Editor** ACL — so the group co-edits ONE agent instead of emailing prompts around. |
| **Admin panel** | LibreChat's bundled management GUI (`:3082`). The **local groups** agent sharing needs live here (Keycloak's groups claim doesn't reach LibreChat's ACLs — upstream [#10006](https://github.com/danny-avila/LibreChat/issues/10006)), plus role permissions and per-group config overrides. Faculty are ADMINs automatically (the realm's `faculty` role) and sign in with the same SSO button. |
| **LiteLLM** | The gateway and **the ledger**. Every user gets a virtual API key with a budget; every request is metered. Models are routed here, so which GPU (or cloud) serves a request is nobody else's business. |
| **usage-mcp** | The ledger, served back into the chat as tools: students ask their own usage, faculty ask their course's — no dashboard login, no Enterprise license. LibreChat stamps who's asking into trusted headers; the service reads through a SELECT-only DB role and scopes every answer by the roster (`usage-mcp/roster.yaml`). |
| **Keycloak** | The front door. OIDC identity provider; ships with a mock campus realm (`northwinds`) — local demo accounts standing in for real campus groups. Later, it **brokers Globus** (or any SAML/OIDC IdP) without LibreChat changing at all. |
| **vLLM** *(its own stack: `vllm/`)* | Local inference on this box's GPUs — deliberately a **separate compose project** (`just vllm-up`) so a loaded model survives app deploys. Optional — the gateway can just as easily point at a campus inference server or a cloud endpoint. |
| **Mongo · Meili · pgvector · RAG API** | LibreChat's data plane: conversations, search, and embeddings for agent knowledge files. |
| **Caddy** *(edge profile)* | The front door's front door: one hostname per surface, TLS included — internal CA for the LAN, real ACME (HTTP-01 or DNS-01/Azure) for the world. |

### How a request flows

1. **Login** — LibreChat bounces you to Keycloak ("Sign in with Northwinds
   SSO"). Keycloak authenticates you (local account now, Globus later) and
   returns your **groups** in the token.
2. **Chat** — LibreChat calls LiteLLM with an API key; LiteLLM checks the
   key's budget, routes to the model, meters the tokens, and writes the spend
   row.
3. **Custom GPT** — a faculty member creates an Agent, attaches course
   materials (indexed into pgvector), and grants the class group **Editor** —
   now the whole team maintains the assistant together.

---

## Quick start

Prereqs: Docker + Compose v2, [`just`](https://just.systems)
(`apt install just`), and — only for local GPU inference (the `vllm/` stack) —
the NVIDIA Container Toolkit.

```bash
git clone <this-repo> almanac && cd almanac
just setup          # creates .env, generates every secret
$EDITOR .env        # set ALMANAC_HOST, INFERENCE_BASE_URL, OPENID_ISSUER
just vllm-up        # local GPU box only — inference is its own stack
just up
just smoke          # prove it's serving, not just running
```

The three `.env` lines that matter:

- **`ALMANAC_HOST`** — the box's LAN IP or DNS name (not `localhost`), so your
  browser and the containers agree on where Keycloak lives.
- **`INFERENCE_BASE_URL`** — where tokens come from.
  `http://host.docker.internal:8000/v1` for the local `vllm/` stack on the
  same box (`just vllm-up`); an Ollama/vLLM URL for a campus inference box; a
  cloud endpoint if you must. The model name in
  [`litellm/config.yaml`](litellm/config.yaml) must match what that endpoint
  serves.
- **`OPENID_ISSUER`** — must be **HTTPS** (LibreChat ≥ v0.8 refuses plain-http
  issuers). No DNS on your LAN? The edge's internal CA mints IP certs — copy
  the **"LAN HTTPS"** block from [`.env.example`](.env.example) and you're
  done: `https://<box-ip>:8443/realms/northwinds`.

Surfaces (direct-port mode): **LibreChat** `:3080` · **admin panel** `:3082`
(faculty SSO) · **LiteLLM admin** `:4000/ui` (login = `LITELLM_MASTER_KEY`) ·
**Keycloak admin** `:8080` (`KC_ADMIN` / `KC_ADMIN_PASSWORD`).

### First boot: wire the OIDC client secret (one time)

Keycloak imports the `northwinds` realm on first boot and generates a secret
for the `librechat` client. Hand it to LibreChat:

1. Keycloak admin → Clients → **librechat** → Credentials → copy the secret.
2. Paste into `.env` as `OPENID_CLIENT_SECRET`.
3. `just up` (recreates librechat).

The realm ships three demo users (password `Demo123!`): **prof.vex**
(faculty), **stu.amaya** and **stu.bram** (both in `/engr301-team-gust`).
If a login bounces with a redirect-URI error, add your host's callback
(`http://<ALMANAC_HOST>:3080/oauth/openid/callback`) to the client in the
Keycloak admin.

### The make-or-break test (do this first)

The whole point is a **group co-editing one GPT**. Prove it:

1. Log in once as each demo user (`prof.vex`, `stu.amaya`, `stu.bram`) —
   LibreChat creates accounts at first login, and groups need accounts that
   exist.
2. As `prof.vex` (ADMIN automatically, via the `faculty` realm role): open
   the **admin panel** (`:3082`, same SSO button) → Groups → create
   `engr301-team-gust` with amaya + bram as members.  Why here and not
   Keycloak?  Agent sharing uses **LibreChat-local groups** — the Keycloak
   groups claim never reaches the ACL system in v0.8.7 (upstream
   [#10006](https://github.com/danny-avila/LibreChat/issues/10006)).
   Keycloak still owns *who you are*; the panel owns *who's in the share
   dialog*.
3. Still as `prof.vex`, back in the chat: create an **Agent**, give it
   instructions, attach a file.  **Share** → find `engr301-team-gust` →
   grant **Editor** (not Viewer).
4. Log in as `stu.amaya` → open the agent → confirm you can **edit its
   instructions and knowledge**, not just chat with it.

If step 4 works, the core promise is real.

---

## The guides

- **[Course guide](docs/user-guide.md)** — for faculty and students:
  building a custom GPT, group projects (one GPT, whole team), API keys,
  and the opencode coding harness.  Start here if you teach.
- **[Admin guide](docs/admin-guide.md)** — Keycloak and LiteLLM operations:
  identity and the Globus flip, the key contract, per-student attribution,
  faculty analytics (with its honest Enterprise boundary), backups,
  troubleshooting.
- **[CI notes](docs/ci.md)** — the three-line pipeline on other CI systems,
  plus SBOM generation for infosec.

---

## Keys, owners, and the invoice (the accounting spine)

Every user gets a **virtual API key**, and every key is minted with an
**owner** — the class or lab that answers for the spend:

```bash
just key stu.amaya engr301 5     # user, owner, budget ($)
just spend                       # month-to-date, grouped by owner
```

`owner` is required — no owner, no key. It's stamped into the key's metadata
and spend tags, so usage always rolls up to an organizational unit: **the
owner is who gets the invoice**, even when the subsidy takes it to zero. A
class sees exactly what it used this month, what it would have cost on
commercial cloud AI, and what the campus rate saved them. Free-but-visible is
the point: cost consciousness without a paywall.

The month-end export — LiteLLM spend → **FOCUS**-format billing rows with
OpenChargeback tags, rolled up the org tree — is Root Cellar's accounting
coupling, and a story for another day. The contract that makes it possible
starts now: **no key without an owner.**

---

## Day 2

```text
just                # list every recipe
just up / down      # start / stop the app stack (data survives)
just vllm-up / vllm-down / vllm-logs / vllm-smoke   # the inference stack
just logs librechat # tail one service
just deploy         # what CI runs: pull + build + up + smoke
just nuke           # stop + WIPE ALL DATA (asks first)
```

**Profiles** (`COMPOSE_PROFILES` in `.env`): `edge` adds the Caddy front
door; `workbench` is the opencode coding harness (run-on-demand — `just
workbench <key>` — it never starts with `just up`).  Local vLLM is **not a
profile** — it's its own compose project
([`vllm/compose.yml`](vllm/compose.yml)), so `just deploy` bounces the app
without unloading a model that took ten minutes to warm.  Run it on the same
box (the default `INFERENCE_BASE_URL` reaches it via `host.docker.internal`)
or clone this repo on a GPU box and run only `just vllm-up` there.

**Switching models:** local GPU → edit `VLLM_MODEL` / `VLLM_SERVED_NAME` in
`.env`, match `litellm/config.yaml`, `just vllm-up` again; remote/cloud →
edit the `model_list` block or add models live in the LiteLLM admin UI (they
persist to the DB).  vLLM wants **safetensors** (GGUF is Ollama's format); on
H200-class GPUs prefer an FP8 checkpoint.  Tool calling is ON by default
(`VLLM_TOOL_PARSER=hermes` fits the Qwen 2.5 family) — coding harnesses and
agent tools need it.

**Real identity:** the realm ships a *disabled* Globus identity provider.
Register a Globus Auth app, paste its client ID/secret into Keycloak →
Identity Providers → **globus** → Enable — now campus identities federate
through the same front door, and LibreChat never knows the difference. Any
other campus IdP (SAML/OIDC) works the same way. Group sync from your SIS/LMS
roster is deliberately out of scope here — that's the platform's job.

---

## Deploying for real

The [`justfile`](justfile) is the deployment contract; **CI is a three-line
wrapper around it.** Ours is Woodpecker
([`.woodpecker/deploy.yml`](.woodpecker/deploy.yml)): push to `main` → ssh to
the deploy box → `just sync && just deploy`. The same wrapper in GitLab CI or
GitHub Actions — plus notes on k8s and Azure container environments — is in
[`docs/ci.md`](docs/ci.md).

**TLS at the edge:** `EDGE_TLS=internal` gives you Caddy's local CA on the
LAN. For real certs on an RFC 1918 box, enable the `acme_dns azure` block in
[`caddy/Caddyfile`](caddy/Caddyfile) — the full pattern (zone delegation,
TXT-only role, the Networking pitch) is documented in Root Cellar's
[DNS delegation guide](https://github.com/atmarx/root-cellar/blob/main/docs/guides/northstar-dns-delegation-guide.md).

**Already have a front door?** If a reverse proxy with real certs (a campus
wildcard, a homelab Caddy) already exists, skip the `edge` profile entirely
and point two names at the direct ports — chat → `:3080`, and Keycloak gets
its **own hostname** (not a port) → `:8080`:

```caddyfile
aiclassroom.example.edu       { reverse_proxy almanac-box:3080 }
auth-aiclassroom.example.edu  { reverse_proxy almanac-box:8080 }
```

Then in `.env`: `OPENID_ISSUER=https://auth-aiclassroom.example.edu/realms/northwinds`,
`KC_HOSTNAME=https://auth-aiclassroom.example.edu`, `KC_PROXY_HEADERS=xforwarded`,
`DOMAIN_CLIENT`/`DOMAIN_SERVER` to the chat URL. Public CA means the
`NODE_EXTRA_CA_CERTS` machinery isn't needed. (One hard-won note: if your
front proxy bind-mounts its config as a single file, editors that rewrite
inodes leave the container reading the **old** file — validate-and-reload
will happily no-op. `grep` the file *inside* the container before trusting a
reload.)

### Cautions

- **`CREDS_KEY`/`CREDS_IV` are pinned for life.** They encrypt every user's
  saved API key at rest; rotating them orphans every stored key ("invalid key
  provided"). `just secrets` will never touch a value that's already set —
  that's a feature, learned the hard way.
- The bundled realm is a **mock**: demo passwords, `sslRequired: none`,
  Keycloak in `start-dev`. Fine on a LAN behind a firewall; put real identity
  and `start` mode in front before real users.
- Images are **pinned** (compose defaults + `.env.example`). Bump
  deliberately: edit the pin, deploy, verify, commit. The LiteLLM and RAG API
  pins are digests because their channels are moving tags.
- Backups are yours: the named volumes (`mongo-data`, `litellm-db`,
  `keycloak-db`, `vector-data`) are the state.

## Honest ledger: real vs. not

| Thing | Status |
|---|---|
| Custom GPT = prompt + knowledge files | **Real** — LibreChat Agents + RAG |
| Group co-edits ONE shared GPT | **Real** — Editor ACL to a **local** group (admin panel; Keycloak-groups→ACL sync is upstream-open [#10006](https://github.com/danny-avila/LibreChat/issues/10006)) |
| Local models on your GPUs | **Real** — vLLM, its own stack (or any endpoint you point at) |
| Per-user keys, budgets, metering | **Real** — LiteLLM virtual keys + spend |
| Owner on every key | **Real** — enforced at mint (`just key`) |
| Who-spent-what per student | **Real** — LibreChat stamps every request (`x-litellm-end-user-id`); spend rows carry the student |
| Students ask their own usage, in chat | **Real** — the usage-mcp tools; self-scoped by construction (identity rides trusted headers, never tool arguments) |
| Keys work in a real coding harness | **Real** — opencode: `just workbench <key>` on the box, same config on laptops |
| Faculty see their course's usage | **Real** — ask in chat: rollup, per-student activity, who-hasn't-started, roster-scoped to their course.  Raw dashboards stay one invite link away; the only wall left is per-team self-serve views *inside the LiteLLM UI* (Enterprise — admin guide has the table) |
| SSO via campus identity | **Real** — Keycloak; Globus broker one toggle away |
| SBOMs on file with infosec | **Real** — `just sbom`, SPDX per pinned image |
| Group *sync* from rosters | **Not here** — share-groups are clicks in the admin panel; roster sync stays the platform's job |
| FOCUS/OpenChargeback billing export | **Not yet** — the owner tags are the hook it lands on |

---

The almanac never claimed to grow the crops. It tells you what was planted,
what it cost, and what the people before you learned — and it sits on the
shelf where everyone can reach it. 🌾
