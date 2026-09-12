---
title: What do we already know not to try?
description: A catalogue of walls — questions already answered the expensive way, from the Actions allowlist whose empty default permits the entire internet to the single-file mount that served stale config through a green reload.
audience: operator
also_reaches: [builder, student]
status: draft
owner: geordi
tags: [egress-control, allowlist, access-control, least-privilege, secrets-management, key-rotation, encryption-in-transit, rendered-config, chokepoint, gateway, tenancy, isolation, attribution, metering, docker-compose, kubernetes, librechat, litellm, openbao, keycloak, vllm]
tethered_to:
  - compose.yml
  - justfile
  - registrar/render.py
  - registrar/planes/config.py
  - librechat/librechat.yaml
  - litellm/config.yaml
  - caddy/Caddyfile
  - openbao/config.hcl
---

# Design walls — do not re-derive

*Every line below cost something to learn: two research agents, an empirical rig, and a handful of red pipelines.  These are **walls**, not preferences — places where the obvious approach is wrong and someone already paid to find out.  If you are about to research one of these questions, stop.  It's answered here.*

Provenance: this list was assembled during the 2026-07 campus deploy and lived for a while in a *different* project's memory directory — a launch directory accident from before instance-scoped sessions.  It is home now.  The repo is the only copy that should exist, so it inherits into every session and every worktree regardless of where anyone started.

**How to use this file:** if a wall is wrong, fix it *here* in the same commit that fixes the system — a stale wall is worse than no wall, because it gets trusted.  If you add one, say what it cost.

---

## Dated state — verify before trusting

Unlike the walls below, this is an **observation with a date on it**.  Check it against the running system before you build on it.

As of the **2026-07-16 campus deploy**:

- A100 fleet serving qwen coder + gpt-oss 120b + devstral 2.
- opencode confirmed working end to end.
- LiteLLM ledger seeing everything.
- **Azure endpoint NOT connected** — suspected network restriction on the resource, not a config error on our side.  Signatures for chasing it were left with Andrew.

---

## vLLM — tool parsers are per model family

There is no universal tool parser.  The parser must match the family or tool calling silently degrades:

| Family | Parser |
|---|---|
| Qwen instruct | `hermes` |
| Qwen **coder** | `qwen3_coder` |
| Devstral | `mistral` |
| gpt-oss | *(none — speaks harmony natively)* |

This is exactly why `VLLM_TOOL_PARSER` is a **per-box `.env` value** and not a repo constant.  A box serving a different family needs a different parser, and there is no value that is right for all of them.

---

## LibreChat (v0.8.7)

### Shareable groups never come from Keycloak

Agent-share groups resolve from `local` or `entra` sources **only**.  The Keycloak/OIDC `groups` claim never reaches LibreChat's ACL system — upstream [#10006](https://github.com/danny-avila/LibreChat/issues/10006) is open, and the sync PR (#10015) died unmerged.  Do not spend another afternoon wiring the claim through; it has nowhere to land.

Share-groups are managed in the bundled **admin panel on `:3082`**.  Not 3081 — the panel's default port collides with `CHAT_PORT` overrides on xdocker03, and a red pipeline (#11) is how we found it.

### The tenancy machinery is already in our pin — undocumented, env-only, and header-driven *(2026-09-09)*

**`v0.8.7` reads `TENANT_ISOLATION_STRICT`, `DEFAULT_TENANT_ID` and `CODEAPI_JWT_SINGLE_TENANT_ID` from the environment, and handles `x-tenant-id` in `api/server/index.js`.**  `tenantId` appears in 86 files under `/app/api`.  None of the three variables appears in that version's `.env.example`, and the `librechat.yaml` schema exposes no tenancy at all — so this is a **live env-only surface with no documentation in the release we run.**  Measured against the pinned image itself, not the repo tag; the tag's `.env.example` is clean, which is exactly why reading it would have misled you.

Two consequences, and they point opposite ways.

**Security first.**  A request header named `x-tenant-id` is parsed at the server entry.  Upstream's own later comment on the knob reads: *"Trust `X-Tenant-Id` on unauthenticated routes... Enable only when a trusted reverse proxy strips any client-supplied value and sets its own."*  **We set none of these variables, so we run whatever the v0.8.7 default is.**  Opened *(2026-09-11)*, in the pinned image's `packages/api/dist/index.cjs`, not the repo: `preAuthTenantMiddleware` sits on `/oauth/*` and `/api/auth/*`, and it **trusts any well-formed client-supplied `X-Tenant-Id`** (≤128 chars, `[-a-zA-Z0-9_.]`, not `__SYSTEM__`) with strict mode on *or* off.  The Mongoose `tenantIsolation` plugin then adds `{tenantId: <that value>}` to every query in the request.  Our documents carry no `tenantId`, so from inside that request the database looks empty.  The chain nobody has ruled out: LibreChat makes the first user it counts an ADMIN, and a count scoped to an empty tenant returns zero.  Unproven, and not something to prove on prod.

- **The edge strips it now** — `header_up -X-Tenant-Id` on the flagship chat block in `caddy/Caddyfile` and on every rendered course vhost (`render_course_vhost`).  Single-tenant means the only correct value is no value.
- **The edge is not the only door.**  `compose.yml` publishes LibreChat on `${CHAT_PORT}` on all interfaces (xdocker03: `:3081`), and a client hitting that port never meets Caddy.  Until the chat port binds to loopback, the strip covers the edge only.  That's a front-door decision, not a one-liner.
- Setting `TENANT_ISOLATION_STRICT` doesn't fix this.  It makes queries *without* a tenant fail; it does nothing about a client *supplying* one.

**Strategy second.**  Upstream is building in-app multi-tenancy (the work spans v0.8.6 → v0.8.8-rc2).  If it lands properly, **instance-per-course stops being the only way to get a tenant boundary** — which is today's headline justification for the fleet.  That would not invalidate the registrar: provisioning, per-course budgets, escrow and identity wiring still have no upstream answer, and the survey found no per-course provisioning tooling anywhere.  But the *tenancy* argument would need rewriting, and we should rewrite it ourselves rather than have it rewritten for us at a pin bump.

**What is NOT true:** LibreChat Projects are not a per-course alternative and never were — they are personal, and other users cannot see your project list.

### The agents API: a browser User-Agent, and ids are an interface *(2026-09-11)*

Three things that each look like a different bug than they are, paid for while seeding the guide agents:

- **Every route under `/api/agents` sits behind `uaParser`** (`api/server/middleware/uaParser.js:20-29`), which rejects any request whose `User-Agent` does not parse as a *browser*.  The response is an SSE body — `event: error data: {"message":"Illegal request"}` — so a client that calls `.json()` on it dies on a syntax error pointing at the parse, not at the request.  It also logs a `NON_BROWSER` violation against the caller each time, so a debugging loop quietly accrues violation score on a real account.  **A script must send a browser UA to reach the agents API at all.**
- **`/api/agents/v1` is the OpenAI-compatible router, not "version 1" of agent CRUD.**  It authenticates with an API key, so posting an agent there returns `{"error": {"message": "Invalid API key"}}` and reads exactly like a broken token.  Agent CRUD is mounted at the **root** (`routes/agents/index.js:331`, `router.use('/', v1)`) — `POST /api/agents`, `GET /api/agents`.
- **Agent ids are a published interface.**  `modelSpecs[].preset.agent_id` in `librechat.yaml` points at them, so delete-and-recreate orphans every spec and the guides disappear from the picker with no error anywhere.  Re-import must `PATCH` in place — which is what `just agents-seed` does.

---

### The classroom posture is opt-in

The default USER role ships `agents.share=false` and `peoplePicker.*=false`.  Out of the box, students cannot share agents with each other — which is the opposite of what a course wants.  The `interface` block in [`librechat/librechat.yaml`](../librechat/librechat.yaml) is what turns the classroom posture **on**.

Faculty become LibreChat ADMIN via `OPENID_ADMIN_ROLE=faculty`, read from `realm_access.roles`, on a token of kind `access`.  All three have to line up.

**But ADMIN does not buy extra agent powers, because the `interface` block flattens both roles.**  `hasExplicitConfig` gives anything written in `librechat.yaml` precedence over LibreChat's per-role defaults, and the seeding loop runs `for (const roleName of [USER, ADMIN])` — so an explicit `interface` key lands on *both* roles identically.  Measured on the running instance rather than reasoned about *(2026-08-11, v0.8.7)*:

```
role ADMIN: AGENTS {USE:true, CREATE:true, SHARE:true, SHARE_PUBLIC:false}
role USER:  AGENTS {USE:true, CREATE:true, SHARE:true, SHARE_PUBLIC:false}
```

Consequence, and it answers a live docs question: **nobody can publish an agent instance-wide from the chat UI — faculty included.**  `public: false` is not a student restriction, it is the whole instance.  Each course carries its own copy (`LibreChat_{slug}` database, rendered from the same block), so this holds per course.  The **only** thing that changes it is the admin panel, which edits the seeded roles at runtime — per instance, since each course has its own panel and its own database.

So "seeds the default USER role" understates it: the block seeds every role, and the seam between student and faculty is Keycloak's role claim plus the admin panel, not the `interface` block.

### TLS and ACME — the full decision guide is [docs/tls.md](tls.md)

That page carries the whole thing (measured against `caddy:2.11.4`, which the edge is now pinned to for exactly this reason).  The three findings most likely to be re-derived the expensive way:

- **A CA that pre-authorizes needs no challenge solver at all.**  `acmez` skips authorizations already in state `valid`, and a Caddy config with HTTP-01 and TLS-ALPN-01 disabled and no DNS provider validates cleanly.  An absent solver is not an error until an identifier arrives `pending`.  **"Wildcards require DNS-01" is CA policy, not a Caddy rule and not an RFC 8555 rule** — a pre-authorized wildcard needs no solver either.
- **Caddy does not fail safe on a broken renewal.**  A statically-configured site whose renewal fails permanently keeps serving its **expired** certificate indefinitely — no fail-closed, no fallback to an internal cert.  On-demand does the opposite and fails the handshake.  There is no admin endpoint listing certificates or expiries, so alerting on the `cert_failed` event is the only thing standing between a lapsed validation and a student finding it.
- **ACME account identity is keyed by directory URL**, silently.  Changing the directory (staging → production) or losing the data volume creates a brand-new account with no error — and since pre-authorizations are account-scoped, that discards your domain validations along with it.  EAB credentials are bound to one directory too, so staging and production need separate ones.

### `actions.allowedDomains` is TOP-LEVEL — and it's the only wall around Actions

Verified against the pinned image's own schema, not the docs:

```
packages/data-provider/src/config.ts:1732   actions: { allowedDomains, allowedAddresses }
api/server/services/ToolService.js          reads appConfig.actions.allowedDomains (4 sites)
```

It is a **sibling of `endpoints:`, not a member of it** — an `actions:` block nested under `endpoints.agents` parses fine and does nothing.  The registrar renders it top-level ([`registrar/render.py`](../registrar/render.py)), and a rendered instance config was round-tripped through v0.8.7's zod schema to prove it.

Semantics — *re-verified 2026-08-11 by calling the pinned image's own `isActionDomainAllowed` against a live instance (`just egress-check`), not by reading the source.  One line below was wrong and is corrected:*

- **Absent or empty ⇒ no allowlist.**  *The entire public internet is reachable.*  There is no way to spell "deny all" — `capabilities:` without `actions` is the only off switch.
- **Private/reserved IPs are SSRF-blocked by default — but naming one in the list UNBLOCKS it.**  `10.10.1.10` against an empty list is refused; against `["10.10.1.10"]` it is permitted.  The SSRF guard is a default, not a ceiling, so an allowlist entry pointing at internal infrastructure is a hole you opened yourself.
- Entries may be bare hostnames, `*.wildcards`, `scheme://host`, or `host:port`; a scheme or port on the rule narrows the match, and the *subject* must carry it too — rule `https://api.example.edu` does not match a bare `api.example.edu`.
- `*.example.edu` **also matches the apex** `example.edu`.  A bare `*` matches nothing.  Matching is case-insensitive and is not a naive suffix test (`api.example.edu.evil.com` does not match `api.example.edu`).
- **CORRECTED — a URL path in an entry does not fail closed, it fails OPEN.**  This file previously said paths "are meaningless — `parseDomainSpec` won't match them," which reads as *the rule is inert*.  It is the opposite: the path is **ignored and the rule permits the whole host**.  A rule of `api.example.edu/v1/chat` permits `api.example.edu/admin/delete`.  Someone writing that rule believes they scoped an agent to one endpoint and has actually handed it the entire service.  The registrar rejects path-shaped rules at validate time, so we fail closed at *our* layer — but the reason is now stated correctly, because "inert" and "silently wider than written" call for opposite reactions when you find one.

**The general lesson, and the reason `just egress-check` exists:** configuration that parses is not configuration that runs, and a security control nobody verified is a control nobody has.  Both of this section's findings — the nesting trap and the path-widening — are invisible to schema validation and to reading the docs.  They are only visible if you ask the running image's own guard function what it will actually permit.

### Capability names are not validated by anything

A typo in `endpoints.agents.capabilities` (`file_serach`) is accepted by the schema and simply never grants the power.  It **fails closed and silent** — the professor believes they enabled a thing they didn't.  The registrar keeps `KNOWN_CAPABILITIES` and *warns*; it deliberately does not block, because the legal set is LibreChat's and moves per version.  Bump that list when the image pin moves.

### MCP gotchas

- **Private hosts need `mcpSettings.allowedAddresses`** — LibreChat's SSRF guard blocks internal addresses by default.
- **The MCP URL is `/mcp` with NO trailing slash.**  A trailing slash gets a 307, and the Node client won't follow it.
- **"0 tools" at boot for user-scoped servers is BY DESIGN.**  Tools are listed per-user at login, so an empty list at container start is correct, not broken.  The registry inspector's 406 in the same situation is cosmetic.  Do not debug either one.

---

## LiteLLM (pin ≈ v1.91.1) — the free/Enterprise line

Drawn empirically against the pinned build.  Vendor docs do not mark these boundaries reliably, which is why the rig exists.

**Free — build on these:**

- Teams and budgets; `team_id` on keys
- Internal users; invitation links (`just invite`)
- `/key/list`, `/key/delete`
- `metadata.tags` owner rollup → `/spend/tags`
- Customer budgets
- `x-litellm-end-user-id` header attribution — zero-config, rig-proven

**Enterprise — do not design around these:**

- Team `admin` role
- `/key/regenerate` — so **rotation is delete + mint**, not regenerate
- Top-level `tags` on keys (only `metadata.tags` is free)
- `/global/spend/report`
- **UI SSO past 5 TOTAL DB users.**  It counts *every row* — one real course roster kills it.  This is the sharpest edge on the list.

Consequences we already committed to:

- **Faculty analytics** = owner tags + `proxy_admin_viewer` invites.  Not teams, not the spend report.
- **Key-mint contract: `user_id` must be the EMAIL**, so key usage joins chat usage on the same identity.  The roster's `aliases:` field exists to cover realm-username strays that don't match their email.

---

## Mint and escrow are one transaction, and the order is load-bearing *(2026-09-11)*

A virtual key exists in two places — the gateway, where it spends, and OpenBao, where it can be read back.  A key in only one of those is a defect, and which one it's missing from decides how bad:

- **Gateway but no escrow** — live, spending the course pool, and *unreadable by anyone*.  No student can use it, no operator can revoke it deliberately, and nothing can attribute it after the fact.  This is the worse orphan.
- **Escrow but no gateway key** — the record hands out a credential the gateway already rejects.  Recoverable, but the student hits a wall with no explanation.

Both were reachable.  Three call sites minted and *then* escrowed with no cleanup on failure (`planes/verbs.py`), and rotation revoked the old key *before* minting the replacement — so a failed mint produced both defects at once.  All minting now goes through `_mint_escrowed()`, which revokes on escrow failure; rotation mints first and records `revoke_pending` in the escrow record so an interrupted rotation is a visible debt rather than a quietly doubled fuse.

**A process death between the mint call and the escrow write still leaves an orphan.  No ordering closes that window** — it can only be detected, by joining the ledger to the escrow on the deterministic `key_alias` (`<slug>:<email>`).  That audit is not built.

**A key's fuse may never exceed the pool remainder, and a fuse below `REGISTRAR_MIN_FUSE` is refused rather than minted** *(2026-09-11)*.  LiteLLM enforces the team budget whatever we write on the key, so the clamp buys honesty, not enforcement — it makes what a key says and what a key can do the same number.  The refusal is the other half: a dead-on-arrival credential costs the holder a debugging session and teaches them the platform is broken.  This replaced a `max(0.5, fuse - spent)` floor in rotation that refilled $0.50 on every rotation, which meant the fuse bounded nothing.  A floor and a gate have similar shapes and opposite effects.

`just key` used to call `/key/generate` straight at the gateway: no `team_id` (so it drew on no pool), no escrow, no audit — a fresh orphan on every run, including the roster loop the admin guide used to recommend.  **There is no unescrowed mint path any more**, and `just key` prints metadata, never the key.

---

## opencode

- Official image is **`ghcr.io/anomalyco/opencode`** — the org moved from `sst`.  Old paths are stale.
- Custom provider = `@ai-sdk/openai-compatible`, `{env:VAR}` for `apiKey`, and **`tool_call: true` per model**.
- Needs **≥16k context**.  Its own prompt plus tool schemas eat ~8k before the user says anything; anything smaller thrashes.
- Qwen2.5 tool calling needs vLLM `--enable-auto-tool-choice --tool-call-parser hermes`.  **Coder variants ignore hermes — avoid that pairing** (see the parser table above).

---

## fastmcp 3.x

`get_http_headers()` **strips `authorization`** unless you ask for it explicitly:

```python
get_http_headers(include={"authorization"})
```

Silent by design, and it looks exactly like a client that forgot to send the header.

---

## just

`dotenv-load` **snapshots `.env` at invocation start.**  A recipe that appends a variable to `.env` and then consumes it in the same run reads the *old* snapshot — the value is on disk and still invisible.  Recipes consuming freshly-appended vars must **grep the FILE**, not the environment.

Pipeline #13 went red teaching us this.

---

## Keycloak — realm import is per realm NAME, not per database *(2026-09-11)*

`--import-realm` runs on **every** boot with strategy `IGNORE_EXISTING`: each file in `/opt/keycloak/data/import` is imported unless a realm with that `realm:` name already exists.  The admin guide used to say "first boot only (empty database)," and that model predicted the wrong thing the one time it mattered.

The `northwinds` → `classroom` rename (`9208fc2`) reached xdocker03 with `KC_REALM=northwinds` still pinned in `.env` — correctly, so LibreChat and the registrar never moved.  But Keycloak saw a realm name it had never met and imported it: `Realm 'classroom' imported`, five demo users on the public-repo password, two of them `faculty`, sitting beside the live realm.  Nothing trusted it, since the issuer names `northwinds`, and `auth-*` resolves LAN-only.  It's **disabled, not deleted**, which is enough: it exists now, so `IGNORE_EXISTING` will never re-mint it.

- **The realm name lives in two places seeded at different times** — the file's `realm:` (read by Keycloak at every boot) and `KC_REALM` / `OPENID_ISSUER` in `.env` (seeded once from `.env.example`, never clobbered).  On an existing box they drift apart silently; on a fresh box built from a stale `.env`, Keycloak serves `classroom` while the issuer asks for `northwinds` and login breaks with nothing looking wrong.
- **To rename a live realm, don't rename the file.**  Export, change `realm:`, and treat it as a migration — or leave the live name alone and pin it, which is what xdocker03 does.
- **Check what a box is actually serving:** `kcadm.sh get realms --fields realm,enabled` inside the container, prod-probe style.  A disabled realm still answers its `.well-known` with 200; the auth endpoint returning 400 is the real test.

---

## Container & mount scars (Phase 1, paid in crash loops)

- **OpenBao must raft into `/openbao/file`** — the image owns that directory.  Point storage anywhere else and the data lands root-owned and the container crash-loops.
- **Never bind-mount a single file that gets rewritten.**  Atomic writes (tmp + rename) break twice over a single-file mount: `EBUSY`, then a pinned inode where the container keeps reading the old content forever.  `usage-mcp` and the registrar both ride **directory** mounts precisely for this, which is also why `courses.yaml` is bind-mounted as a directory-relative path.

  **We then violated this wall in three places and it cost us a live security hole** *(found 2026-08-11)*.  `compose.yml` single-file-mounted both `librechat/librechat.yaml` and `litellm/config.yaml`, and `render.py` did the same for every course's rendered `librechat.yaml`.  Every one of those files is replaced by **rename** — by `just sync` (git) for the first two, by `_atomic_write` for the third.  So:

  - Closing the front office's `actions` hole changed the file on disk and **the running container never saw it.**  Host said fixed; container served the Jul-16 inode git had already unlinked.
  - Worse, it generalizes: **a course's `allowed_domains` could be tightened, re-rendered, and never reach the running instance.**  The registrar would report success and be telling the truth about the file.

  All three are directory mounts now (`/app/conf/…`), and the fleet's are **per-course** subdirectories — `fleet/` holds every course's `.env`, so mounting its root into a course container would hand one course the rest of the fleet's secrets.  `just egress-check` Layer 0a compares the host inode against the container's and fails loudly on any recurrence.

  **A wall being written down is not a wall being held.**  This one was correct, prominent, and cited in the very file that broke it.  What caught it was a machine comparing two inodes, not a person re-reading the rule.

  The sweep for the rest *(2026-08-11)* found three more single-file mounts — `caddy/Caddyfile`, `openbao/config.hcl`, `keycloak/realm-classroom.json` — all tracked, so all replaced by rename on every `git reset --hard`.  The Caddyfile was the live one and the worst shape of the bug: `just deploy` ends with `caddy reload`, which faithfully reloaded the **pinned original inode** and reported success.  An edge config could change in git, deploy green, and serve the old routes. All three are directory mounts now.

  **A `:ro` bind mount cannot host a nested mount.**  Docker has to `mkdir` the mountpoint inside the parent, and a read-only parent refuses — so `./caddy:/etc/caddy:ro` plus `./fleet/caddy:/etc/caddy/fleet:ro` dies at container create with `read-only file system`, *unless* `caddy/fleet/` exists on the host as a tracked placeholder.  That placeholder is an invisible dependency one tidy-up away from breaking the edge, so the fleet vhosts moved to a **sibling** path (`/etc/caddy-fleet`) instead.  Nesting binds is legal when the mountpoint already exists and compose orders by path depth — it just buys a second thing that has to stay true.
- **`docker restart` re-resolves bind sources but keeps the container's old DEFINITION** — restarting after a compose.yml mount change boots the *new* config into the *old* topology.  The concrete failure: the edge's Caddyfile importing `/etc/caddy-fleet/*.caddy`, restarted into a container that only mounts `/etc/caddy/fleet` — empty import glob, fatal, edge down and unable to boot.  Recreate (`just up`) is the verb for definition drift; restart is only for content drift.  `config-refresh` enforces this itself by comparing compose's `config-hash` label against the hash the current files produce, and fails closed on a mismatch.
- **`just` dedents recipe bodies**, so heredocs inside a recipe must stay indented or the delimiter stops matching.
- **`docker image inspect` cannot see buildkit base digests** — use `docker buildx imagetools inspect`.
- **Woodpecker's piped-ssh heredoc eats stdin.**  Any `compose exec` inside one needs `</dev/null` or it hangs on a step that looks correct.

---

## `config-refresh`'s drift guard can never pass for a service with `env_file:` *(2026-09-11)*

**`docker compose config --hash <svc>` and the `com.docker.compose.config-hash` label compose stamps at create are not the same computation — they diverge for every service that uses `env_file:`.**  `config-refresh` compares the two and fails closed on a mismatch, so any `env_file` service whose read-only bind mtime moves will be SKIPPED forever and take the pipeline red with it.

Cost: two red pipelines (#51 and #52) and an hour, on a stack that was serving correctly the entire time.

The measurement, on a 14-container deploy: **12 services matched exactly, 2 differed — `keycloak` and `librechat`, which are the only two in `compose.yml` carrying `env_file:`.**  That is the whole correlation.  The guard's arithmetic is right everywhere else, which is what makes it convincing when it is wrong.

Two traps inside the trap:

- **The remedy it prints does not work.**  "Run `just up` to recreate it" is wrong twice over: `docker compose up -d` will not recreate these containers at all — a targeted `--dry-run` reports them `Running` with no action planned, because compose's *own* up-to-date check agrees the definition is current.  And `--force-recreate` does not help either: the containers were genuinely rebuilt, new hash stamped, and `config --hash` still disagreed.  There is no verb that clears this.
- **It looks like realm drift and isn't.**  This surfaced in the same deploy that renamed `realm-northwinds.json` → `realm-classroom.json`, so the obvious reading is that the realm change broke something.  It didn't.  The rename bumped the `./keycloak` directory's mtime, which is merely what *triggers* the check; the mismatch was always there and would have fired on any config touch.  Keycloak served `northwinds` correctly throughout.

**If you are here because the pipeline is red:** confirm the stack is actually healthy (`just smoke` by hand, and probe the realm from inside the network — see [Verifying on the box](#verifying-on-the-box-without-moving-a-token)), then treat the SKIP as a known false positive rather than recreating anything.  The fix is to the guard, not the box: either exclude `env_file` services from the hash comparison and gate them on something else, or stop using `config --hash` as the oracle.

## Verifying on the box without moving a token

The prod-probe pattern: run the check **inside** the container so the credential never leaves the host.

```bash
docker compose exec -T usage-mcp python - < prod-probe.py
```

The probe itself is a fastmcp `Client` over `StreamableHttpTransport("http://localhost:8080/mcp", headers={Authorization, X-User-Email, X-User-Role})` asserting three things: `list_tools` returns, a scoped call succeeds as a known faculty user, and a **bad bearer is rejected**.  That third assertion is the one that matters — the first two pass on a service with no auth at all.

(The original probe script and the 15/15 rig lived in a session scratchpad and are gone.  Rewriting it from this paragraph is minutes; that's why the shape is written down and the file isn't.)

---

## Structure decisions (settled — reopen only with cause)

- **vLLM is its own compose project** so models outlive app deploys.  Restarting the app plane must never evict a loaded model.  It is also **site-local** (`site/inference/`) — see the platform/site line below.
- **`just deploy` append-migrates missing `.env` vars** and never touches values that are already set.  New config arrives without clobbering a box's local truth.
- **`just sbom`** = digest-pinned syft SPDX per image.  Regenerate at pin-bump time, not per deploy — see [ci.md](ci.md).
- **The registrar's reconcile plane is `registrar/planes/`**, one module per system it talks to, with `reconcile.py` as the facade and the single import surface.  The invariant: **a verb may compose planes; a plane may never import a sibling plane.**  Credentials stay auditable because there's exactly one list to read.

---

## `site/` vs. the platform *(2026-08-11)*

Everything tracked in git is **the platform** — the same bytes on a laptop, xdocker03, and a campus VM.  `site/` is **this box**, and it is gitignored.

Four things that will bite if you don't know them:

- **`site.example/` is a template, not config.**  Editing it changes nothing on any existing deployment — `just _site` clones it once and never overwrites.  To change a live box, edit that box's `site/`.
- **`site/compose.yml` is layered with a second `-f`, not `include:`.**  That is deliberate and it is the difference that matters: `-f` can **override** core services, `include:` can only add.  A campus VM that needs the ledger's volume on a SAN mount needs override.  Consequence: relative paths in it resolve from the **repo root** (`./site/foo`), because the first `-f` sets the project directory.
- **The overlay is conditional at `just` PARSE time** (`path_exists`).  A `site/` created during a run isn't picked up until the next `just` invocation.  Harmless as shipped — the seeded layer is empty — but do not build anything that depends on same-run pickup.
- **`site/` survives `just sync`.**  Sync is `git reset --hard origin/main`, which does not touch ignored files.  That is the whole point: a deployment's local truth outlives every deploy, and nobody has to re-apply it.

Inference belongs on the site side because `INFERENCE_BASE_URL` is the seam — everything past that URL is a deployment's own choice, so a box with no GPU carries no GPU stack.  Deleting `site/inference/` is the supported way to say so; `just vllm-*` reports it instead of failing.

`site/infra/` is deliberately unexemplified.  Bringing up the metal varies so much between institutions that a sample would read as a default.  The repo's assumed starting point is **a fresh Linux VM with Docker on it**.

---

## Orchestration — compose now, k3s short-term *(2026-07-17)*

The **inference fleet migrates first**; `INFERENCE_BASE_URL` is the seam that makes that possible.  The app plane moves only on trigger conditions, not on enthusiasm.

Disciplines to hold in the meantime, so the move stays cheap:

- **No new host-path mounts.**
- **No new boot-order assumptions.**

The k8s-day landmine already identified: **LibreChat performs OIDC discovery once at boot.**  An issuer that isn't up yet when the pod starts is a failure that looks like a config error.

Homelab k3s is the **rehearsal**.  The campus endgame is an institutional k8s chart — not a bespoke one we maintain forever.

---

*Footnote for anyone who finds stray references: mydoulapage's xdroplet03 hosting is a different fleet entirely.  Unrelated to this stack, and it stays where it is.  It appears in the history here only because this list was rescued from that project's memory directory.*
