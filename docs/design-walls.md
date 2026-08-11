# Design walls — do not re-derive

*Every line below cost something to learn: two research agents, an empirical
rig, and a handful of red pipelines.  These are **walls**, not preferences —
places where the obvious approach is wrong and someone already paid to find
out.  If you are about to research one of these questions, stop.  It's
answered here.*

Provenance: this list was assembled during the 2026-07 campus deploy and
lived for a while in a *different* project's memory directory — a launch
directory accident from before instance-scoped sessions.  It is home now.
The repo is the only copy that should exist, so it inherits into every
session and every worktree regardless of where anyone started.

**How to use this file:** if a wall is wrong, fix it *here* in the same
commit that fixes the system — a stale wall is worse than no wall, because
it gets trusted.  If you add one, say what it cost.

---

## Dated state — verify before trusting

Unlike the walls below, this is an **observation with a date on it**.  Check
it against the running system before you build on it.

As of the **2026-07-16 campus deploy**:

- A100 fleet serving qwen coder + gpt-oss 120b + devstral 2.
- opencode confirmed working end to end.
- LiteLLM ledger seeing everything.
- **Azure endpoint NOT connected** — suspected network restriction on the
  resource, not a config error on our side.  Signatures for chasing it were
  left with Andrew.

---

## vLLM — tool parsers are per model family

There is no universal tool parser.  The parser must match the family or tool
calling silently degrades:

| Family | Parser |
|---|---|
| Qwen instruct | `hermes` |
| Qwen **coder** | `qwen3_coder` |
| Devstral | `mistral` |
| gpt-oss | *(none — speaks harmony natively)* |

This is exactly why `VLLM_TOOL_PARSER` is a **per-box `.env` value** and not
a repo constant.  A box serving a different family needs a different parser,
and there is no value that is right for all of them.

---

## LibreChat (v0.8.7)

### Shareable groups never come from Keycloak

Agent-share groups resolve from `local` or `entra` sources **only**.  The
Keycloak/OIDC `groups` claim never reaches LibreChat's ACL system — upstream
[#10006](https://github.com/danny-avila/LibreChat/issues/10006) is open, and
the sync PR (#10015) died unmerged.  Do not spend another afternoon wiring
the claim through; it has nowhere to land.

Share-groups are managed in the bundled **admin panel on `:3082`**.  Not
3081 — the panel's default port collides with `CHAT_PORT` overrides on
xdocker03, and a red pipeline (#11) is how we found it.

### The classroom posture is opt-in

The default USER role ships `agents.share=false` and `peoplePicker.*=false`.
Out of the box, students cannot share agents with each other — which is the
opposite of what a course wants.  The `interface` block in
[`librechat/librechat.yaml`](../librechat/librechat.yaml) is what turns the
classroom posture **on**.

Faculty become LibreChat ADMIN via `OPENID_ADMIN_ROLE=faculty`, read from
`realm_access.roles`, on a token of kind `access`.  All three have to line
up.

### `actions.allowedDomains` is TOP-LEVEL — and it's the only wall around Actions

Verified against the pinned image's own schema, not the docs:

```
packages/data-provider/src/config.ts:1732   actions: { allowedDomains, allowedAddresses }
api/server/services/ToolService.js          reads appConfig.actions.allowedDomains (4 sites)
```

It is a **sibling of `endpoints:`, not a member of it** — an `actions:` block
nested under `endpoints.agents` parses fine and does nothing.  The registrar
renders it top-level ([`registrar/render.py`](../registrar/render.py)), and
a rendered instance config was round-tripped through v0.8.7's zod schema to
prove it.

Semantics — *re-verified 2026-08-11 by calling the pinned image's own
`isActionDomainAllowed` against a live instance (`just egress-check`), not by
reading the source.  One line below was wrong and is corrected:*

- **Absent or empty ⇒ no allowlist.**  *The entire public internet is
  reachable.*  There is no way to spell "deny all" — `capabilities:` without
  `actions` is the only off switch.
- **Private/reserved IPs are SSRF-blocked by default — but naming one in the
  list UNBLOCKS it.**  `10.10.1.10` against an empty list is refused; against
  `["10.10.1.10"]` it is permitted.  The SSRF guard is a default, not a
  ceiling, so an allowlist entry pointing at internal infrastructure is a
  hole you opened yourself.
- Entries may be bare hostnames, `*.wildcards`, `scheme://host`, or
  `host:port`; a scheme or port on the rule narrows the match, and the
  *subject* must carry it too — rule `https://api.example.edu` does not match
  a bare `api.example.edu`.
- `*.example.edu` **also matches the apex** `example.edu`.  A bare `*` matches
  nothing.  Matching is case-insensitive and is not a naive suffix test
  (`api.example.edu.evil.com` does not match `api.example.edu`).
- **CORRECTED — a URL path in an entry does not fail closed, it fails OPEN.**
  This file previously said paths "are meaningless — `parseDomainSpec` won't
  match them," which reads as *the rule is inert*.  It is the opposite: the
  path is **ignored and the rule permits the whole host**.  A rule of
  `api.example.edu/v1/chat` permits `api.example.edu/admin/delete`.  Someone
  writing that rule believes they scoped an agent to one endpoint and has
  actually handed it the entire service.  The registrar rejects path-shaped
  rules at validate time, so we fail closed at *our* layer — but the reason
  is now stated correctly, because "inert" and "silently wider than written"
  call for opposite reactions when you find one.

**The general lesson, and the reason `just egress-check` exists:**
configuration that parses is not configuration that runs, and a security
control nobody verified is a control nobody has.  Both of this section's
findings — the nesting trap and the path-widening — are invisible to schema
validation and to reading the docs.  They are only visible if you ask the
running image's own guard function what it will actually permit.

### Capability names are not validated by anything

A typo in `endpoints.agents.capabilities` (`file_serach`) is accepted by the
schema and simply never grants the power.  It **fails closed and silent** —
the professor believes they enabled a thing they didn't.  The registrar keeps
`KNOWN_CAPABILITIES` and *warns*; it deliberately does not block, because the
legal set is LibreChat's and moves per version.  Bump that list when the
image pin moves.

### MCP gotchas

- **Private hosts need `mcpSettings.allowedAddresses`** — LibreChat's SSRF
  guard blocks internal addresses by default.
- **The MCP URL is `/mcp` with NO trailing slash.**  A trailing slash gets a
  307, and the Node client won't follow it.
- **"0 tools" at boot for user-scoped servers is BY DESIGN.**  Tools are
  listed per-user at login, so an empty list at container start is correct,
  not broken.  The registry inspector's 406 in the same situation is
  cosmetic.  Do not debug either one.

---

## LiteLLM (pin ≈ v1.91.1) — the free/Enterprise line

Drawn empirically against the pinned build.  Vendor docs do not mark these
boundaries reliably, which is why the rig exists.

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
- **UI SSO past 5 TOTAL DB users.**  It counts *every row* — one real course
  roster kills it.  This is the sharpest edge on the list.

Consequences we already committed to:

- **Faculty analytics** = owner tags + `proxy_admin_viewer` invites.  Not
  teams, not the spend report.
- **Key-mint contract: `user_id` must be the EMAIL**, so key usage joins
  chat usage on the same identity.  The roster's `aliases:` field exists to
  cover realm-username strays that don't match their email.

---

## opencode

- Official image is **`ghcr.io/anomalyco/opencode`** — the org moved from
  `sst`.  Old paths are stale.
- Custom provider = `@ai-sdk/openai-compatible`, `{env:VAR}` for `apiKey`,
  and **`tool_call: true` per model**.
- Needs **≥16k context**.  Its own prompt plus tool schemas eat ~8k before
  the user says anything; anything smaller thrashes.
- Qwen2.5 tool calling needs vLLM `--enable-auto-tool-choice
  --tool-call-parser hermes`.  **Coder variants ignore hermes — avoid that
  pairing** (see the parser table above).

---

## fastmcp 3.x

`get_http_headers()` **strips `authorization`** unless you ask for it
explicitly:

```python
get_http_headers(include={"authorization"})
```

Silent by design, and it looks exactly like a client that forgot to send the
header.

---

## just

`dotenv-load` **snapshots `.env` at invocation start.**  A recipe that
appends a variable to `.env` and then consumes it in the same run reads the
*old* snapshot — the value is on disk and still invisible.  Recipes
consuming freshly-appended vars must **grep the FILE**, not the environment.

Pipeline #13 went red teaching us this.

---

## Container & mount scars (Phase 1, paid in crash loops)

- **OpenBao must raft into `/openbao/file`** — the image owns that directory.
  Point storage anywhere else and the data lands root-owned and the
  container crash-loops.
- **Never bind-mount a single file that gets rewritten.**  Atomic writes
  (tmp + rename) break twice over a single-file mount: `EBUSY`, then a
  pinned inode where the container keeps reading the old content forever.
  `usage-mcp` and the registrar both ride **directory** mounts precisely
  for this, which is also why `courses.yaml` is bind-mounted as a
  directory-relative path.
- **`just` dedents recipe bodies**, so heredocs inside a recipe must stay
  indented or the delimiter stops matching.
- **`docker image inspect` cannot see buildkit base digests** — use
  `docker buildx imagetools inspect`.
- **Woodpecker's piped-ssh heredoc eats stdin.**  Any `compose exec` inside
  one needs `</dev/null` or it hangs on a step that looks correct.

---

## Verifying on the box without moving a token

The prod-probe pattern: run the check **inside** the container so the
credential never leaves the host.

```bash
docker compose exec -T usage-mcp python - < prod-probe.py
```

The probe itself is a fastmcp `Client` over
`StreamableHttpTransport("http://localhost:8080/mcp", headers={Authorization,
X-User-Email, X-User-Role})` asserting three things: `list_tools` returns,
a scoped call succeeds as a known faculty user, and a **bad bearer is
rejected**.  That third assertion is the one that matters — the first two
pass on a service with no auth at all.

(The original probe script and the 15/15 rig lived in a session scratchpad
and are gone.  Rewriting it from this paragraph is minutes; that's why the
shape is written down and the file isn't.)

---

## Structure decisions (settled — reopen only with cause)

- **vLLM is its own compose project** so models outlive app deploys.
  Restarting the app plane must never evict a loaded model.  It is also
  **site-local** (`site/inference/`) — see the platform/site line below.
- **`just deploy` append-migrates missing `.env` vars** and never touches
  values that are already set.  New config arrives without clobbering a
  box's local truth.
- **`just sbom`** = digest-pinned syft SPDX per image.  Regenerate at
  pin-bump time, not per deploy — see [ci.md](ci.md).
- **The registrar's reconcile plane is `registrar/planes/`**, one module per
  system it talks to, with `reconcile.py` as the facade and the single
  import surface.  The invariant: **a verb may compose planes; a plane may
  never import a sibling plane.**  Credentials stay auditable because
  there's exactly one list to read.

---

## `site/` vs. the platform *(2026-08-11)*

Everything tracked in git is **the platform** — the same bytes on a laptop,
xdocker03, and a campus VM.  `site/` is **this box**, and it is gitignored.

Four things that will bite if you don't know them:

- **`site.example/` is a template, not config.**  Editing it changes nothing
  on any existing deployment — `just _site` clones it once and never
  overwrites.  To change a live box, edit that box's `site/`.
- **`site/compose.yml` is layered with a second `-f`, not `include:`.**  That
  is deliberate and it is the difference that matters: `-f` can **override**
  core services, `include:` can only add.  A campus VM that needs the
  ledger's volume on a SAN mount needs override.  Consequence: relative
  paths in it resolve from the **repo root** (`./site/foo`), because the
  first `-f` sets the project directory.
- **The overlay is conditional at `just` PARSE time** (`path_exists`).  A
  `site/` created during a run isn't picked up until the next `just`
  invocation.  Harmless as shipped — the seeded layer is empty — but do not
  build anything that depends on same-run pickup.
- **`site/` survives `just sync`.**  Sync is `git reset --hard origin/main`,
  which does not touch ignored files.  That is the whole point: a
  deployment's local truth outlives every deploy, and nobody has to
  re-apply it.

Inference belongs on the site side because `INFERENCE_BASE_URL` is the
seam — everything past that URL is a deployment's own choice, so a box
with no GPU carries no GPU stack.  Deleting `site/inference/` is the
supported way to say so; `just vllm-*` reports it instead of failing.

`site/infra/` is deliberately unexemplified.  Bringing up the metal varies
so much between institutions that a sample would read as a default.  The
repo's assumed starting point is **a fresh Linux VM with Docker on it**.

---

## Orchestration — compose now, k3s short-term *(2026-07-17)*

The **inference fleet migrates first**; `INFERENCE_BASE_URL` is the seam
that makes that possible.  The app plane moves only on trigger conditions,
not on enthusiasm.

Disciplines to hold in the meantime, so the move stays cheap:

- **No new host-path mounts.**
- **No new boot-order assumptions.**

The k8s-day landmine already identified: **LibreChat performs OIDC discovery
once at boot.**  An issuer that isn't up yet when the pod starts is a failure
that looks like a config error.

Homelab k3s is the **rehearsal**.  The campus endgame is an institutional
k8s chart — not a bespoke one we maintain forever.

---

*Footnote for anyone who finds stray references: mydoulapage's xdroplet03
hosting is a different fleet entirely.  Unrelated to this stack, and it
stays where it is.  It appears in the history here only because this list
was rescued from that project's memory directory.*
