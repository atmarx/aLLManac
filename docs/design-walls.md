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

## Structure decisions (settled — reopen only with cause)

- **vLLM is its own compose project** so models outlive app deploys.
  Restarting the app plane must never evict a loaded model.
- **`just deploy` append-migrates missing `.env` vars** and never touches
  values that are already set.  New config arrives without clobbering a
  box's local truth.
- **`just sbom`** = digest-pinned syft SPDX per image.  Regenerate at
  pin-bump time, not per deploy — see [ci.md](ci.md).

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
