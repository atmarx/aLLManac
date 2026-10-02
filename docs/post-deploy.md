---
title: What do I run after a deploy?
description: The post-deploy runbook — what `just deploy` already did, the four things it deliberately does not do, and the order they have to run in.  Written for whoever (or whatever) has a shell on the box and needs a sequence rather than a reference.
audience: operator
also_reaches: [builder]
status: draft
owner: geordi
tags: [deployment, operator-duty, rendered-config, doc-drift, docker-compose]
tethered_to:
  - justfile
  - docs/upgrade-page.md
  - docs/design-walls.md
  - docs/admin-guide.md
  - docs/ci.md
  - scripts/seed_agents.py
  - scripts/agents_check.py
---

# After the deploy — the sequence, not the reference

[The Admin Guide](admin-guide.md) is organised by subsystem, which is the right shape when you know what you're looking for and the wrong shape at 11pm after a push.  This page is the other shape: **run these, in this order, and here is what red means.**

Everything here assumes you are on the deploy box, in the checkout, and `just` resolves.  The whole surface is the [`justfile`](../justfile) — nothing in this document is a command you have to compose yourself.

## The short version

```bash
just sync && just deploy      # what CI runs
just render                   # ONLY if render-check or course-tokens-check went red
just fleet-smoke              # prove the courses answer, not just the control plane
```

One of those three is conditional, and **the condition is printed by the deploy itself.**  The guides re-seed themselves inside the deploy now, so a docs push needs nothing from you.  If you ran a green deploy, you are done — the rest of this page is why.

## What `just deploy` already did

```
channel  pull  build  secrets  up  config-refresh  bao-unseal
smoke  oidc-settle  egress-check  course-tokens-check  render-check  docs-corpus
agents-refresh  agents-check
```

Read that as two halves.  The first seven **change the box**: resolve the image pins from `channels/<name>.env`, pull them, build what's local, fill in any secret still reading `change-me`, bring the stack up, restart containers whose mounted config changed since they booted, and unseal the escrow.  Of the last eight, six **ask the box questions** and change nothing.  The two exceptions repair.  `oidc-settle` restarts any LibreChat whose sign-in route answers 500 instead of 302, the state a reboot leaves behind.  `agents-refresh` re-seeds the guides from the docs you just shipped, on any box that has been seeded before.

Two of those are worth knowing by name because people re-run them by hand and get confused:

- **`docs-build` rides on `up`**, so a deploy always rebuilds `site-dist/` from `apex/`.  The help site is built, mounted, and served at `/help/` on the chat host on every box — the route is in the tracked Caddyfile since `471e4f4`.
- **`secrets` never touches a value that is already set.**  It is safe on every deploy and it is not a rotation.

`deploy` runs each of those as its own `just`, with the upgrade page's status board written around it.  Same steps, same order, same exit code when one fails.  The next section is what that means for you.

**A green deploy is a green control plane, not a green fleet.**  `smoke` proves LibreChat, Keycloak, LiteLLM and the escrow are answering.  It says nothing about whether `engr301-2026fall.<domain>` resolves, holds a cert, and returns a login page — that's `fleet-smoke`, and it is deliberately not in the deploy.

## The upgrade page

While a service is down, the edge shows students a "being upgraded, back in a few minutes" page instead of a bare 502 ([upgrade-page.md](upgrade-page.md)).  It has two triggers, and only one of them is yours to manage:

- **Passive, always on.**  Any site whose upstream isn't answering gets the page (a browser) or a JSON 503 (anything else).  Nothing to run.
- **Active, during `just deploy`.**  The deploy holds the flag file `status/upgrading` from `up` through `oidc-settle`, and while it exists every page load on the chat host and the course hosts gets the page, even though the services behind it are up.  `status/status.json` (served at `/_status.json`) is the step list the page shows; `status/history.json` keeps the last ten runs' step times for its "about N minutes".

**To look behind the page while the flag is up**, send the header `X-Almanac-Bypass` with any value — `curl -H 'X-Almanac-Bypass: 1' ...`, or a header extension in a browser.  It is not a secret: it reaches exactly what would be there without the page.  API calls, `POST`s, `/help/` and `/_status.json` are never behind the flag.

**If students are still seeing the page after a deploy has finished**, check for the flag:

```bash
ls -l status/upgrading      # there, and no deploy running?
rm status/upgrading         # takes effect on the next page load — no reload of anything
```

The deploy's exit trap removes it on any ending it can see — success, a failed step, Ctrl-C, a dropped terminal — so a stuck flag means the deploy was killed outright (SIGKILL, an OOM, a host crash).  The next `just deploy` clears it too.  No flag and still the page: a service really is down — `just ps`.

**The first deploy that brings this** recreates the edge once (it gains the `status/` mount and `PLATFORM_NAME`), so the edge itself is gone for a few seconds of `up`.  It also leaves **`render-check` red** for every course, because each course vhost gains the page in `registrar/render.py` and the live render predates it: run `just render`, which is the usual fix below.  Until you do, the courses still work — they just show a bare 502 when they restart, as before.

**`status/` must belong to the deploying user.**  The deploy and `just up` create it; if something else made it first (a bare `docker compose up` creates a missing bind source as root), the deploy prints that the board is off and carries on.  `sudo chown "$USER" status` fixes it.

## The four things it does not do

Every one of these is an **inert change**: the deploy shipped the new code and something else has to make it true.  That family is the longest section of [design-walls.md](design-walls.md), and these are its four live instances.

### 1.  `just render` — when a render template changed

`just deploy` ships `registrar/render.py`.  It does not re-render the fleet, so a change to a template is sitting in the image doing nothing until you run the verb.

`render-check` is the guard that tells you that you owe it a run, and it runs **after** `build`, `up` and `config-refresh` for a reason: everything before it has to have happened for its answer to mean anything.  (`docs-corpus`, `agents-refresh` and `agents-check` run after it now; it is no longer the very last step.)  Red looks like this:

```
  differs     /out/usage-mcp/roster.yaml

render-check — 1 file(s) STALE on the fleet volume.
```

The fix is one command and it is not `deploy` again:

```bash
just render
```

That re-renders every course from `courses.yaml` using the templates in the registrar you just deployed, recreates what changed, reloads the edge gracefully, and restarts any instance whose config file changed under it (`config-refresh`).  That last step used to be missing.  A change that lands only in a course's `librechat.yaml` recreates nothing, so the instance kept serving the old config while `render-check` went green: it diffs files, not processes.  **`render-check` reports and never repairs** — no course instance is recreated mid-deploy, which is why a red render-check is a note to you rather than an outage.

An **unrendered** line is not red.  A course record with no `fleet/<slug>.env` has never been provisioned on this box; that's `just course`, not `just render`.

**`course-tokens-check` goes red over the same window, and runs first.**  Each course holds its own two MCP tokens, derived from `COURSE_MCP_SECRET` and accepted only with that course's `X-Course`; the check asks both tool servers, per course, whether that holds.  A course whose env predates the derived tokens — or whose secret was rotated since its last render — fails before any call is made:

```
  FAIL  courses  fleet/engr301.env still holds the FRONT DOOR's token — the render predates decision 32.  Run: just render
```

That one is a stale render, and those courses' tools are refusing until `just render` runs.  Run it, then `just course-tokens-check` again.  Any other FAIL — a token **accepted** where it should be refused — is not a render problem: it is the boundary not holding, and it needs a person before the next deploy.

**`egress-check` goes red over the same window too, and runs before both.**  Its Layer 5 asks the edge to refuse writes to each course's admin config API — on the course's host and on the way its panel calls the API — and since 2026-10-02 the panel's way runs through the edge.  A course rendered before that still has its panel pointed straight at its chat:

```
  FAIL  the panel's API_SERVER_URL does not go through the edge — it walks around the wall
  FAIL  browser: a base-scope override        PUT    -> 401   (reached LibreChat — the edge let it through)
```

Stale render again: `just render`, then `just egress-check`.  Because `egress-check` stops the deploy, the checks after it — `course-tokens-check`, `render-check`, the guide refresh — didn't run on that pass; `just deploy` again once it's green.  A Layer 5 FAIL on a box whose render is current means the wall itself isn't holding, and it needs a person.  Overrides an instructor saved *before* the wall still apply; `just fleet` lists them as a finding, and removing one is your call ([design-walls.md](design-walls.md), "...but the admin config API does").

### 2.  `just agents-seed` — the first time, and when the deploy couldn't

The guide agents on the flagship carry the docs as knowledge and the contract as their prompt.  **The deploy refreshes them itself**: `agents-refresh` re-runs the seeder on any box that has been seeded before, and `agents-check` then **fails the deploy** if a guide's knowledge or prompt is still older than the tree.  The refresh is content-hashed, so a page edit costs one upload, and it updates in place, so no agent id moves.

What the deploy never does is the *first* seed.  That run mints the agent ids you paste into `librechat.yaml`, so it's yours ([Admin Guide](admin-guide.md), "The guide agents"):

```bash
just agents-seed                 # corpus + prompts + knowledge files
just agents-seed --skip-files    # prompts only — seconds, not minutes
```

`agents-refresh` knows a box has guides by `site/agents-state.json`, the seeder's own record of their ids.  No file, no refresh — the deploy says so and steps aside.  Delete that file and the deploy stops refreshing until the next hand seed.

**So `agents-check` red after a deploy means the refresh didn't land**, not that you owe one.  The two usual causes: the box was never seeded (the deploy said so, just above the check), or the upload rate limit — 50 per user per 15 minutes — stopped the refresh partway.  The second clears itself; wait out the window and `just agents-seed`.

### 3.  `just fleet-smoke` — prove the courses answer

```bash
just fleet-smoke
```

One request per course vhost, through the edge, over TLS, by hostname — both `<slug>.<domain>` and `<slug>-admin.<domain>`.  It retries for ninety seconds per host, so a cold instance reads as slow rather than broken.

Run it after `just render`, after `just course`, and before anyone outside the team is told a course is ready.  **It is the only check in the repo that exercises the path a student actually takes.**

### 4.  `just evals` — after a prompt or model change

```bash
just evals
just evals --guide student-guide --case F1,M1
```

Asks every guide every case in `docs/agent-contract.md` and writes the transcript to `site/evals/` (per box, gitignored).  The prose cases **score nothing** — a human reads them, because "answers from the roster documentation" is not a string match.  The tool cases (`expect:` in the contract) score themselves: `just evals-check` runs only those and exits 1 on any wrong call, and it's what the nightly `guide-evals` cron runs ([ci.md](ci.md)).

Results are per *model*, not per prompt.  A smaller local model fails these more often than a frontier one, so a run against a box pointed at a different `INFERENCE_MODEL` is not comparable to the last one.

## The one ordering trap

**A hand-run `render-check` used to lie.**  It renders inside the registrar container and diffs against the fleet volume — so when that container predates a change to `render.py`, it renders the old template, compares it to files the old template wrote, and reports two stale things agreeing as current.

It now refuses instead:

```
  FAIL the deployed registrar is NOT this working tree.
       Anything it says about renders describes the OLD templates,
       including a green render-check.  Run `just deploy` first.
```

That FAIL means *do a deploy*, not *do a render*.  Inside `just deploy` it cannot happen, because `build` and `up` run first.  It is only the hand run that needs the guard — which is exactly the run [the verify-on-the-box wall](design-walls.md) tells you to make, and the one you trust most because you watched it happen.

## Before the first test users

Andrew's actual list, in order.  Steps 1–3 are commands; steps 4 and 5 are not, and no check in this repo can cover them.

```bash
just sync && just deploy      # 1.  green, top to bottom
just agents-check             # 2.  eight specs, enforce: true, knowledge matches
                              #     (red on a never-seeded box: just agents-seed, paste the block)
just fleet-smoke              # 3a. every course answers through the edge
just courses                  # 3b. the roster is who you think it is
```

4. **Sign in as a person.**  Browser, through Keycloak, into the flagship.  A probe proves the endpoint answers; it does not prove a human can get in.
5. **Ask a guide for help, accept the offer to file a report, then `just reports`.**  Pick any guide but the Front Desk, tell it something in your course is broken, and check that the record lands with your question *and* the answer attached.  That trace is the whole point of the tool and it has never been walked end to end.

If step 5 never offers, the wording is the pedagogy lane's.  If it offers and nothing lands, that's the registrar.  If it never gets that far, that's the edge.

## What only a human runs

Never put these in a pipeline, a health check, or anything an agent can reach.

| Command | Why |
|---|---|
| `just bao-init` | Once per box.  Prints the root token exactly once — password manager, not scrollback. |
| `just key-show <slug> <email>` | Break-glass read of an escrowed key.  OpenBao audits it, and that audit line is the feature. |
| `just nuke` | Stops the stack and wipes every volume.  It asks first; that is the only thing standing between you and the data. |
| `just secrets` after a live start | Safe by construction — it skips set values — but `CREDS_KEY`/`CREDS_IV` are pinned, and regenerating them makes every saved user key undecryptable. |

## What does not travel in git

A box with a `site/` override **stops inheriting for the file it overrides, silently and for everything** — not just for the value you changed.  So a fix landing in a tracked file reaches every box except the ones that most needed it.

Three known instances, all on the flagship's `librechat.yaml`:

1. The `mcpServers.<prefix>-courses` block (`almanac-courses` unless `MCP_SERVER_PREFIX` says otherwise) and `registrar:8080` under `mcpSettings.allowedAddresses` — without them the front door has no way to take a complaint, and nothing looks wrong.
2. `maxContextTokens`, sized to **what that box's endpoint actually serves** (`/api/ps` on a loaded model), never what the model supports.  On Ollama these differ silently and by a lot, and too large does not fail the request — it drops the front of the prompt, which is the system prompt.
3. `almanac-declined` and `content_policy_fallbacks` in that box's `litellm/config.yaml`, if it serves a filtered hosted model.

After editing anything under `site/`, bring the box up with **`just up`** — never a bare `docker compose up -d <service>`, which merges only `compose.yml` and silently recreates the container without your override.

## When something is red

| Symptom | Read this |
|---|---|
| `render-check` red | [`just render`](#1--just-render--when-a-render-template-changed) — above |
| `course-tokens-check` says an env "still holds the FRONT DOOR's token" or a token "the current secret doesn't derive" | `just render`, then re-run it — the courses' tools refuse until you do |
| `egress-check` Layer 5: a panel's `API_SERVER_URL` doesn't go through the edge, or a config write "reached LibreChat" | A render from before 2026-10-02: `just render`, then `just egress-check`.  Still red with a current render: the admin-config wall isn't holding — stop and read [design-walls.md](design-walls.md), "...but the admin config API does" |
| `course-tokens-check` says a token was **accepted** where it should be refused | The per-course boundary isn't holding.  Not a render — stop and read [design-walls.md](design-walls.md), "A course's MCP token speaks for that course alone" |
| `render-check` FAILs on the registrar not matching the tree | `just deploy` first; the check is refusing to guess |
| `agents-check` red on knowledge or prompt (STALE) | The deploy's refresh didn't land — read the `agents-refresh` output above it.  Never seeded: `just agents-seed`.  RATE LIMITED: wait fifteen minutes, then `just agents-seed` |
| `agents-check` reports an orphan spec | A `modelSpecs` entry points at an agent id that no longer exists — re-seed, then paste the reprinted block ([Admin Guide](admin-guide.md)) |
| `smoke` warns openbao is SEALED | Never red — sealed is a boot state, and chat still works on the keys already rendered.  But nothing can mint or fetch a key until `just bao-unseal`.  On a box with `just fleet-watch-install`, a reboot unseals itself; `journalctl --user -u almanac-unseal` says why it didn't |
| `oidc-settle` FAILs on an instance | It restarted it and sign-in still isn't registered.  Check `just logs chat-<slug>` (or `librechat`) for `openidStrategy`: an issuer the container can't reach, not a boot race |
| Nobody can sign in after a reboot, and `smoke` is green | `just oidc-settle`.  `smoke`'s LibreChat and Keycloak lines both pass while every sign-in 500s.  A box whose boot unit predates 2026-09-29 needs `just fleet-watch-install` once to get the boot-time settle |
| Students see the upgrade page after the deploy finished | `ls status/upgrading` — if it's there and no deploy is running, `rm status/upgrading` ([above](#the-upgrade-page)).  If it isn't, the page is the passive one and a service is down: `just ps` |
| The deploy says "status/ is not writable … no upgrade page this run" | Something created `status/` as root.  `sudo chown "$USER" status`; the deploy itself was unaffected |
| `fleet-smoke` red on one host | The instance, not the edge.  `just ps`, then `just logs chat-<slug>` |
| A guide got worse deep in a long thread | Not the prompt.  The window trimmed it — see instance 2 above |
