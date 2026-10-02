# The aLLManac

*a·**LLM**·anac — look again, it was there the whole time.*

A farmhouse almanac is the book on the kitchen shelf you consult all season — planting dates, frost warnings, the accumulated judgment of people who did this before you.  The aLLManac is that book for a class or a lab: **a self-hosted custom-GPT service** where a course builds its own assistant on **your models, your GPUs, your identity system, your ledger** — and the large language model is baked right into the middle of the name, because hiding it would be lying.

It is the sister project of Root Cellar, a research-data governance platform.  The cellar keeps things cold, safe, and provable.  The almanac is the book you actually open every day.  Same farmhouse, two rooms.

**What a course gets:** its own chat instance at its own hostname, run by its own instructors.  Inside it, a team builds a shared assistant ("custom GPT") that *the whole team co-edits* — instructions, knowledge files, tools.  Every student can ask the chat for a personal API key to use in a coding harness, every key has a budget, and every token is metered to the course and the person.  No data leaves campus unless you point it there.

---

## Architecture

**Shared control plane, per-course data plane.**  One identity provider, one gateway and ledger, one escrow, one registrar — and one LibreChat per course, rendered from a single course record.  Nothing a chat instance queries can reach another course, because it is only ever told about its own.  The reasoning, and the one room we found still shared, is [How do you keep the courses apart?](apex/how-we-built-it/keeping-courses-apart.md)

```
                        Browser
                           │  HTTPS
                           ▼
                     ┌───────────┐   chat · auth · gateway · /help/
                     │   Caddy   │   <course> · <course>-admin
                     │   edge    │
                     └─────┬─────┘
                           │
   ┌──────────┐  OIDC ┌────┴────────┐  keys  ┌──────────┐
   │ Keycloak │◀──────│  LibreChat  │───────▶│ LiteLLM  │──▶ inference
   └──────────┘       │ front door  │        │ ledger   │    ├─ vLLM (site/inference/)
        ▲             │ + 1/course  │        └──────────┘    ├─ campus GPU box
        │             └──────┬──────┘             ▲          └─ cloud (if you must)
        │                    │ MCP tools          │
        │             ┌──────┴──────┐             │
        └─────────────│  registrar  │─────────────┘
                      │  usage-mcp  │──▶ OpenBao (key escrow)
                      └─────────────┘
```

| Part | Job |
|---|---|
| **LibreChat** | The chat UI, one instance per course plus a locked-down front door.  "Custom GPTs" are LibreChat **Agents**: a system prompt + knowledge files (RAG) + tools, shareable to a group with an **Editor** ACL — so the group co-edits ONE agent instead of emailing prompts around.  The front door offers only the guide agents: ask how the platform works without spending course tokens. |
| **Admin panel** | LibreChat's bundled management GUI, one per instance — `<course>-admin.<domain>` for a course, `:3082` for the front door (operators only).  The **local groups** agent sharing needs live here (Keycloak's groups claim doesn't reach LibreChat's ACLs — upstream [#10006](https://github.com/LibreChat-AI/LibreChat/issues/10006)), plus role permissions.  A course's instructors and TAs are its admins, and nobody else's. |
| **Registrar** | The course fleet as chat tools.  It provisions a course from one record in `registrar/courses.yaml` — LiteLLM team and budget, OIDC client, staff roles, the rendered instance — and runs the term from there: instructors enroll students by asking the Instructor Guide, students ask the Coder Guide for their keys — both at the front door, so bookkeeping never spends a course's budget.  Design and every decision's why: [docs/registrar-spec.md](docs/registrar-spec.md). |
| **OpenBao** | The escrow.  Every minted key is stored and versioned, so a student can get their key back and an operator can answer who held which key and when.  Comes back **sealed** from every restart; `just up`, `just deploy` and the boot unit reopen it. |
| **LiteLLM** | The gateway and **the ledger**.  Every course is a team with a budget, every key carries an owner, every request is metered.  Models are routed here, so which GPU (or cloud) serves a request is nobody else's business. |
| **usage-mcp** | The ledger, served back into the chat as tools: students ask their own usage, faculty ask their course's — no dashboard login, no Enterprise license.  LibreChat stamps who's asking into trusted headers; identity is never a tool argument.  It reads through a SELECT-only DB role. |
| **Keycloak** | The front door's identity provider.  Ships a demo realm (`classroom`) with local accounts standing in for campus users.  Later, it **brokers Globus** (or any SAML/OIDC IdP) without LibreChat changing at all. |
| **Caddy** *(edge profile)* | One hostname per surface, TLS included — internal CA for the LAN, real ACME for the world.  It also serves the help site at `/help/` and the live SBOM at `/sbom/`.  Courses are subdomains, so they need it. |
| **Mongo · Meili · pgvector · RAG API** | LibreChat's data plane.  Search, document service and vector store run per course; the Mongo server is shared, with one database per course. |
| **vLLM** *(site-local: `site/inference/`)* | Local inference on this box's GPUs — deliberately a **separate compose project** (`just vllm-up`) so a loaded model survives app deploys.  Optional by construction: everything past `INFERENCE_BASE_URL` is a deployment's own choice, so a box with no GPU simply doesn't have it. |

### How a request flows

1. **Login** — the course's chat bounces you to Keycloak ("Sign in with Campus SSO").  Each course has its own OIDC client, and the registrar grants its `member` role to whoever the roster names, so the door only opens for the class.
2. **Chat** — LibreChat calls LiteLLM on the course's service key and stamps your email on the request.  LiteLLM checks the course's budget, routes to the model, meters the tokens, and writes a spend row carrying both the course and you.
3. **Custom GPT** — a team creates an Agent, attaches course materials (indexed into that course's pgvector), and grants its group **Editor** — now the whole team maintains the assistant together.
4. **Your own key** — ask the Coder Guide at the front door "what's my key?" and the registrar hands back your escrowed key for that course, minted when you were enrolled.  The same key works in opencode on a laptop, against the same budget.

---

## Quick start

Prereqs: Docker + Compose v2, [`just`](https://just.systems) (`apt install just`), and — only for local GPU inference (`site/inference/`) — the NVIDIA Container Toolkit.  A fresh Linux VM with Docker on it is the assumed starting point; see [`site.example/`](site.example/README.md) for what belongs to one box rather than to the platform.

```bash
git clone <this-repo> almanac && cd almanac
just setup          # creates .env + site/, generates every secret
$EDITOR .env        # see below
just vllm-up        # local GPU box only — inference is its own stack
just up
just smoke          # prove it's serving, not just running
just bao-init       # once per box: open the escrow (prints the root token ONCE)
```

Then the guides: copy the front door's config into `site/`, rename what [docs/customizing.md](docs/customizing.md) lists under "Set somewhere other than `.env`", run `just agents-seed`, paste the ids it prints, and restart the front door.  `just agents-check` says when it's right.  The whole sequence, in order, is customizing.md's "A fresh box, in order" and then [docs/post-deploy.md](docs/post-deploy.md).

What to set in `.env`:

- **`INFERENCE_BASE_URL`** — where tokens come from.  `http://host.docker.internal:8000/v1` for the `site/inference/` stack on the same box (`just vllm-up`); an Ollama/vLLM URL for a campus inference box; a cloud endpoint if you must.  The model name in [`litellm/config.yaml`](litellm/config.yaml) must match what that endpoint serves.
- **Hostnames — the fleet shape.**  Courses live at `<slug>.<ALMANAC_DOMAIN>`, so the real thing needs the `edge` profile and Keycloak behind its own hostname.  Copy the **"FLEET IDENTITY SHAPE"** block from [`.env.example`](.env.example) and set those lines together.  On one machine, `ALMANAC_DOMAIN=localhost` needs no DNS at all — `*.localhost` resolves to loopback by itself.  On a server, point wildcard DNS `*.<ALMANAC_DOMAIN>` at the box once and every future course is covered.
- **Your names, before the first `up`.**  `PLATFORM_NAME` is what students and faculty hear the platform called — on the help site, from the guides, in export downloads — and `CHAT_MODEL` is the model name they pick and type into a harness.  Both default to this project's names.  Those two, the picker labels, and the hostnames are cheap to choose now and costly to change once a box has history: [docs/customizing.md](docs/customizing.md) lists every one and says which.
- **No DNS, just kicking the tires?**  `OPENID_ISSUER` must be **HTTPS** (LibreChat ≥ v0.8 refuses plain-http issuers), and the edge's internal CA can mint IP certs — the **"LAN HTTPS"** block in `.env.example` gets you the front door by IP.  It can't host courses, which need subdomains.

The app ports (chat `:3080`, admin panel `:3082`, LiteLLM `:4000/ui`, Keycloak `:8080`) bind **loopback** by default (`PUBLISH_BIND`), because a client that reaches them directly skips every rule the edge enforces.  From anywhere but the box, use the edge's hostnames, or an `ssh -L` tunnel for the admin surfaces — [the admin guide's map](docs/admin-guide.md#the-map-read-this-first) has the details.

### First boot: wire the front door's OIDC client secret (one time)

Keycloak imports the `classroom` realm on first boot and generates a secret for the front door's `librechat` client.  Hand it to LibreChat:

1. Keycloak admin → Clients → **librechat** → Credentials → copy the secret.
2. Paste into `.env` as `OPENID_CLIENT_SECRET`.
3. `just up` (recreates librechat).

Add `https://<CHAT_HOST>/oauth/openid/callback` to that client's Valid redirect URIs — the realm only ships the direct-port callbacks.  Course clients need none of this: the registrar creates each one with its secret and callback.

The realm ships five demo users (password `Demo123!`): **prof.vex** and **prof.okoye** (faculty), **stu.amaya** and **stu.bram** (both in `/engr301-team-gust`), and **stu.divya**.

### The make-or-break test (do this first)

The whole point is a **group co-editing one GPT**, inside a course.  Prove it:

1. Create a course with prof.vex teaching it:

   ```bash
   just course engr301-2026fall "ENGR 301 (Fall 2026)" prof.vex@example.edu
   ```

   That provisions everything and starts it at `https://engr301-2026fall.<ALMANAC_DOMAIN>`, with its admin panel at `engr301-2026fall-admin.<ALMANAC_DOMAIN>`.
2. Sign in to the front door as `prof.vex`, pick the **Instructor Guide**, and ask it to **enroll amaya@example.edu and bram@example.edu in engr301-2026fall**.  It stages the change and applies it when you confirm.  Then sign in once as each student — LibreChat creates accounts at first login, and groups need accounts that exist.
3. As `prof.vex`, open the course's **admin panel** (same SSO button) → Groups → create `engr301-team-gust` with amaya + bram as members.  Why here and not Keycloak?  Agent sharing uses **LibreChat-local groups** — the Keycloak groups claim never reaches the ACL system (upstream [#10006](https://github.com/LibreChat-AI/LibreChat/issues/10006)).  Keycloak owns *who you are*; the panel owns *who's in the share dialog*.
4. Still as `prof.vex`, back in the chat: create an **Agent**, give it instructions, attach a file.  **Share** → find `engr301-team-gust` → grant **Editor** (not Viewer).
5. Sign in as `stu.amaya` → open the agent → confirm you can **edit its instructions and knowledge**, not just chat with it.

If step 5 works, the core promise is real.  For the rest of a course's life — staff, budgets, closing and archiving at term's end — see [the admin guide's fleet section](docs/admin-guide.md#the-course-fleet-the-registrar).

---

## The guides

- **[Reader-facing site](apex/index.md)** — the public help and teaching pages, served at `/help/` on the chat host.  The guide agents' knowledge is rendered from the same pages, so the website and the help agents can't silently drift apart.  `just docs-build` renders the site to the ignored `site-dist/` directory.
- **[Teaching a course](apex/teaching-a-course.md)** — for instructors: getting a course, the day-zero checklist, your class list, and course patterns that work.  Start here if you teach.
- **[Building with your course's AI](apex/user-guide.md)** — for students and faculty: building a custom GPT, group projects (one GPT, whole team), API keys, and coding harnesses.
- **[Admin guide](docs/admin-guide.md)** — the operator's reference, by subsystem: Keycloak, LiteLLM, the front door, the course fleet, channels, backups, troubleshooting.
- **[After a deploy](docs/post-deploy.md)** — the sequence, not the reference: what to run after `just deploy`, and what red means.
- **[Design walls](docs/design-walls.md)** — questions already answered the expensive way.  Read it before you research anything.
- **[CI notes](docs/ci.md)** — the thin pipeline on other CI systems, keeping your box's details out of a public repo, plus SBOM generation for infosec.
- **[TLS decision guide](docs/tls.md)** — for the implementer: what to ask your certificate authority before you write any config, what each answer costs you, and how Caddy behaves once you have the answers.

---

## Keys, owners, and the invoice (the accounting spine)

Every key is minted with an **owner** — the course that answers for the spend — and escrowed in the same transaction.  Students fetch their own from the Coder Guide at the front door; the operator's path is:

```bash
just key engr301-2026fall amaya@example.edu   # course, email, [budget] — minted AND escrowed
just spend                                    # month-to-date, grouped by owner
```

`owner` is required — no owner, no key.  It's stamped into the key's metadata and spend tags, so usage always rolls up to an organizational unit: **the owner is who gets the invoice**, even when the subsidy takes it to zero.  A class sees exactly what it used, priced at whatever rate the campus sets for its models (`input_cost_per_token` in `litellm/config.yaml`).  Free-but-visible is the point: cost consciousness without a paywall.

The month-end export — LiteLLM spend → **FOCUS**-format billing rows with OpenChargeback tags, rolled up the org tree — is Root Cellar's accounting coupling, and a story for another day.  The contract that makes it possible is already in place: **no key without an owner.**

---

## Day 2

```text
just                    # list every recipe
just up / down          # start / stop the stack (data survives)
just deploy             # what CI runs — docs/post-deploy.md has the sequence
just course <slug> "<name>" <instructor-email>...   # provision a course (idempotent)
just render             # re-render the fleet after a registrar/render.py change
just fleet-smoke        # prove every course answers through the edge
just logs librechat     # tail one service
just vllm-up / vllm-down / vllm-logs / vllm-smoke   # the inference stack
just backup             # back up now (just backup-install for nightly)
just nuke               # stop + WIPE ALL DATA (asks first)
```

**Profiles** (`COMPOSE_PROFILES` in `.env`): `edge` adds the Caddy front door, which courses need; `workbench` is the opencode coding harness (run-on-demand — `just workbench <key>` — it never starts with `just up`).  Local vLLM is **not a profile** — it's its own compose project and it lives under `site/` (`site/inference/vllm.compose.yml`), so `just deploy` bounces the app without unloading a model that took ten minutes to warm.  Run it on the same box (the default `INFERENCE_BASE_URL` reaches it via `host.docker.internal`), clone this repo on a GPU box and run only `just vllm-up` there, or delete `site/inference/` on a box that has no GPUs at all.

**This box vs. the platform:** `site/` is gitignored and holds what is true of exactly one deployment — a compose layer `just` stacks on top of `compose.yml` (it can add services *and* override core ones), the optional inference stack, and whatever brings up the metal.  It's cloned from [`site.example/`](site.example/README.md) on first `just setup`.  If you are about to edit a tracked file to make one box work, that's the folder you want.

**Switching models:** local GPU → edit `VLLM_MODEL` / `VLLM_SERVED_NAME` in `.env`, match `litellm/config.yaml`, `just vllm-up` again; remote/cloud → edit the `model_list` block or add models live in the LiteLLM admin UI (they persist to the DB).  vLLM wants **safetensors** (GGUF is Ollama's format); on H200-class GPUs prefer an FP8 checkpoint.  Tool calling is ON by default, and every course chat depends on it.  The parser is **per model family** — `VLLM_TOOL_PARSER=hermes` fits Qwen 2.5 and nothing is universal; [design-walls.md](docs/design-walls.md) has the table.  A wrong parser fails quietly: the model describes calling a tool instead of calling it.

**Real identity:** the realm ships a *disabled* Globus identity provider.  Register a Globus Auth app, paste its client ID/secret into Keycloak → Identity Providers → **globus** → Enable — now campus identities federate through the same front door, and LibreChat never knows the difference.  Any other campus IdP (SAML/OIDC) works the same way.  Rosters don't come from the IdP: instructors give them to their course's chat and the registrar enrolls them.  Sync from an SIS or LMS is out of scope here.

---

## Deploying for real

The [`justfile`](justfile) is the deployment contract; **CI is a thin wrapper around it.**  Ours is Woodpecker ([`.woodpecker/deploy.yml`](.woodpecker/deploy.yml)): push to `main` → ssh to the deploy box → sync to the commit → `just deploy`.  The box's own details (host, ssh user) are CI secrets rather than repo contents, and the sync is inline `git` rather than `just sync` — a broken justfile must not break the recipe that fetches its fix.  The same wrapper in GitLab CI or GitHub Actions — plus notes on k8s and Azure container environments — is in [`docs/ci.md`](docs/ci.md).  What to run after a deploy, and what red means, is [`docs/post-deploy.md`](docs/post-deploy.md).

**TLS at the edge:** `EDGE_TLS=internal` gives you Caddy's local CA on the LAN, which is the right answer for a lab or a pilot.  For real certificates — and especially for an institutional ACME CA that pre-validates your domain instead of running challenges — start at **[docs/tls.md](docs/tls.md)**: it lays out the questions your CA has to answer, what each answer does to your architecture, and why the fleet being subdomain-per-course is what makes the decision interesting.  If your box needs DNS-01 against a delegated Azure zone, the `acme_dns azure` block in [`caddy/Caddyfile`](caddy/Caddyfile) is the pattern.

**Already have a front door?**  Put a campus load balancer or homelab proxy *in front of* the edge, not in place of it.  The edge routes every course by hostname and strips headers our LibreChat pin must never trust, so pointing a proxy at the app ports skips both.  One wildcard route (`*.<ALMANAC_DOMAIN>`) on your proxy covers chat, auth, the gateway and every future course — but it has to preserve `Host` and SNI, which Caddy ≥ 2.11 does not do by default for an HTTPS upstream.  The working config is in [docs/tls.md](docs/tls.md#behind-a-tls-terminating-proxy).  (One hard-won note: if your front proxy bind-mounts its config as a single file, editors that rewrite inodes leave the container reading the **old** file — validate-and-reload will happily no-op.  `grep` the file *inside* the container before trusting a reload.)

### Cautions

- **`CREDS_KEY`/`CREDS_IV` are pinned for life** — the front door's in `.env`, each course's in `fleet/<slug>.env`.  They encrypt every saved credential at rest; rotating them orphans every stored key ("invalid key provided").  `just secrets` will never touch a value that's already set — that's a feature, learned the hard way.
- The bundled realm is a **mock**: demo passwords, `sslRequired: none`, Keycloak in `start-dev`.  Fine on a LAN behind a firewall; put real identity and `start` mode in front before real users.
- Images are **pinned by channel**: `channels/stable.env` for boxes courses run on, `channels/latest.env` for the box where the next version breaks first.  `ALMANAC_CHANNEL` picks one, and `just channel` shows what a box resolves to.  Bump deliberately: move a pin on `latest`, deploy, walk it as a student and a professor, then move it to `stable`.  The admin guide's [channels section](docs/admin-guide.md#channels-stable-and-latest) has the rules.
- **Backups:** `just backup` takes everything without stopping anything, as two restic repositories under two passwords — the data, and the secrets (`.env`, `fleet/<slug>.env`, `site/`) — and `just backup-install` runs it nightly.  `just restore` isn't built yet, so until a restore drill has passed, treat these as copies rather than backups.  What each volume and file holds, and why the unseal key and the escrow are never in one bundle: [docs/admin-guide.md](docs/admin-guide.md#backups).
- **A reboot needs the boot unit.**  `depends_on` is ignored on a reboot, so the escrow comes back sealed and LibreChat can lose its one-shot sign-in discovery race with Keycloak, both behind a green `smoke`.  `just fleet-watch-install` installs the units that unseal, settle sign-in (`just oidc-settle`), and start courses created from chat.

## Honest ledger: real vs. not

| Thing | Status |
|---|---|
| Custom GPT = prompt + knowledge files | **Real** — LibreChat Agents + RAG |
| Group co-edits ONE shared GPT | **Real** — Editor ACL to a **local** group (admin panel; Keycloak-groups→ACL sync is upstream-open [#10006](https://github.com/LibreChat-AI/LibreChat/issues/10006)) |
| One instance per course | **Real** — `just course`, or approved from chat; instructors administer their own course and nobody else's |
| Rosters and enrollment in chat | **Real** — instructors enroll and unenroll by asking; unenrolling revokes the key in the same step |
| Local models on your GPUs | **Real** — vLLM, its own stack (or any endpoint you point at) |
| Per-course budgets, per-user keys, metering | **Real** — LiteLLM teams, virtual keys + spend |
| Owner on every key | **Real** — enforced at mint, and every key escrowed in OpenBao |
| Who-spent-what per student | **Real** — LibreChat stamps every request (`x-litellm-end-user-id`); spend rows carry the student |
| Students get their own key, in chat | **Real** — the Coder Guide at the front door: `my_key`, and `rotate_my_key` if it leaks |
| Students ask their own usage, in chat | **Real** — the usage-mcp tools; self-scoped by construction (identity rides trusted headers, never tool arguments) |
| Keys work in a real coding harness | **Real** — opencode: `just workbench <key>` on the box, same config on laptops |
| Faculty see their course's usage | **Real** — ask in chat: rollup, per-student activity, who-hasn't-started, scoped to their course.  Raw dashboards stay one invite link away; the only wall left is per-team self-serve views *inside the LiteLLM UI* (Enterprise — admin guide has the table) |
| SSO via campus identity | **Real** — Keycloak; Globus broker one toggle away |
| SBOMs on file with infosec | **Real** — every `just build` rewrites SPDX + CycloneDX per image, served live at `/sbom/` for the scanner |
| Nightly off-box backups | **Real** — `just backup`.  **Restore is not built yet** |
| Per-course database credentials | **Not yet** — every course's database sits in one Mongo server with no auth, so the chat never crosses courses but a compromised container could |
| Group *sync* from rosters | **Not here** — enrolling opens the door, but share-groups are still clicks in the admin panel |
| FOCUS/OpenChargeback billing export | **Not yet** — the owner tags are the hook it lands on |

## License

Two licenses, split by what a file is.  The code and configuration are [Apache-2.0](LICENSE).  The written material — the guides in `apex/`, the operator docs in `docs/`, and this README — is [CC BY 4.0](LICENSE-docs), so another institution can adapt the pages for its own courses with attribution.  Code blocks inside the docs are Apache-2.0 too, so you can paste them without the attribution terms coming along.  [NOTICE](NOTICE) has the details.  Copyright 2026 Andrew T. Marx.

The images this stack runs — LibreChat, LiteLLM, Keycloak, OpenBao, Caddy and the rest — are pulled, not redistributed, and each carries its own license.

---

The almanac never claimed to grow the crops.  It tells you what was planted, what it cost, and what the people before you learned — and it sits on the shelf where everyone can reach it. 🌾
