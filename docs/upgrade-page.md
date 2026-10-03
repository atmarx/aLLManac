---
title: What do people see while we upgrade?
description: A page the edge serves whenever a service behind it is down — on its own for any restart, and with a live step list while `just deploy` runs — so a student mid-upgrade gets "back in a few minutes" instead of a bare 502.
audience: operator
status: draft
owner: geordi
tags: [deployment, docker-compose, chokepoint, operator-duty]
tethered_to:
  - caddy/Caddyfile
  - caddy/upgrade/index.html
  - caddy/upgrade/lines.txt
  - registrar/render.py
  - justfile
  - compose.yml
  - scripts/deploy_status.py
  - docs/corpus.py
---

# What do people see while we upgrade?

A student refreshes the chat at 2:14 in the afternoon, ten minutes before a lab is due, and gets `502 Bad Gateway` in Caddy's plain type.  Nothing on the screen says whether the platform is gone, whether their work is gone, or whether to wait.  In the early weeks we deploy often, and every `just deploy` and `just render` restarts something.  That screen is the one we were showing most.

This page describes what replaced it.  It is built and measured on a throwaway stack (the evidence is in [design-walls.md](design-walls.md), "The upgrade page"); it has not yet run through a deploy on a real box, which is why it is a draft.

## Two layers

**The passive layer is most of the value.**  The edge already sits in front of every service, so it already knows when one isn't answering.  Caddy's `handle_errors` catches the 502, 503 or 504 that Caddy itself raises when an upstream refuses the connection, doesn't resolve, or times out, and serves the upgrade page in its place.  That covers every restart, announced or not: a course coming back after `just render`, the front door losing its OIDC race after a reboot, someone running `just up` by hand.  It needs no hook in the deploy and works per course, because each course vhost has its own upstream.

**The active layer is the status board.**  While `just deploy` is in its disruptive stretch, the edge serves the page on purpose, and the page shows the deploy's steps ticking off with a rough time remaining.  When the stretch ends the page reloads itself into the chat.

## The passive layer

- **Every proxied site gets the handler:** the front door, sign-in, the gateway, and, through the render, every course vhost and every course panel vhost.  It is one snippet, `(upgrade_page)`, defined at the top of the Caddyfile and imported by each site, the rendered ones included.  The chat site's `handle_errors 404` for `/help/` stays; the new handler names `502 503 504`, and the two sit side by side.  The panels' internal listener (`:8079`) has no browser on the other end and is left alone.
- **Only errors Caddy raises.**  A 5xx the upstream *answers* with is that service's own reply and passes through untouched, so the gateway's error JSON still reaches the program that asked.  (Measured: an upstream that answers 503 is not replaced.)
- **Browsers get the page; programs get JSON.**  A request whose `Accept` includes `text/html` gets the page.  Anything else (opencode against the gateway, the chat app's own `/api/` calls, an MCP client) gets `{"error": "...", "retry_after": 30}`.  Both are status **503** with `Retry-After: 30` and `Cache-Control: no-store`, never 200: monitoring has to see an outage as an outage, and no browser or proxy may cache the page in place of the chat.  Both carry `X-Almanac-Page: upgrade`, which is how the page's script tells its own copy from the app.
- **The help site keeps working.**  `/help/` is static files the edge serves itself, so it is up whenever the edge is.  The page links to it on the chat host by absolute URL, because course hosts have no `/help/` of their own.
- **The admin-config wall is untouched.**  A write to `/api/admin/config` on a course host still gets the edge's own 403, with the chat up or down and with the flag on or off.

## The active layer

**Where the status lives.**  A `status/` directory at the repo root, gitignored, mounted read-only into the edge at `/srv/status`.  The deploy writes `status/status.json`; the edge serves it at `/_status.json` on every host that imports the snippet, so the page's poll is same-origin wherever it's shown.  Before any deploy has run, `/_status.json` answers `{"state": "idle"}`.

```json
{
 "state": "upgrading",
 "started": "2026-10-02T18:04:11Z",
 "updated": "2026-10-02T18:05:40Z",
 "eta_seconds": 93,
 "steps": [
  {"name": "pull",  "label": "Preparing the new version", "state": "done", "seconds": 30},
  {"name": "up",    "label": "Restarting services",       "state": "running"},
  {"name": "smoke", "label": "Checking it's serving",     "state": "waiting"}
 ]
}
```

`state` is `upgrading`, `done` or `failed`; a finished run adds `finished`.  Labels are written for students, not operators: "Restarting services", not `config-refresh`.  Fifteen recipes map to six labels (`LABELS` in [`scripts/deploy_status.py`](../scripts/deploy_status.py)), and the page shows consecutive steps with the same label as one line.  The file never carries an error message, a log line, a hostname, an image tag or a version.  Every write is a temp file renamed into place, because the edge serves it while the deploy writes it.

**Who writes it.**  The justfile, because that is where deploy logic lives ([ci.md](ci.md)).  `deploy` is a script now, not a dependency list: it runs the same recipes in the same order, each as its own `just` invocation, and calls `scripts/deploy_status.py` around each one to record its start, finish and duration.  The recipes themselves don't change.  A failing step stops the run and `just deploy` exits with that step's code, as before.  The board can never fail a deploy: a status write that fails prints a warning, and a `status/` the deploying user can't write turns the board off for that run.

Running each step as its own `just` has two side effects, both harmless.  Every step re-reads `.env`, so a variable `secrets` appends is visible to the steps after it (inside one invocation it wasn't — the `just` wall).  And a step's own prior dependencies (`_fleet`) run once per step instead of once per deploy; they are all idempotent.

**When the page is on.**  The flag is the file `status/upgrading`.  The wrapper creates it just before `up` and removes it after `oidc-settle`.  `pull`, `build` and `secrets` change nothing that's running, so the page doesn't cover them.  The checks after `oidc-settle` (`egress-check`, `course-tokens-check`, `render-check` and the rest) have to test the real system, not the page, so they run with the flag already gone.  Anything still restarting by then is the passive layer's to catch.  `up` rebuilds the help site before it restarts anything, so the first few seconds under the flag are the docs build.

**A `trap EXIT` writes the final state and clears the flag on any exit** — a failed step, Ctrl-C, a closed terminal, a SIGTERM to the process group.  Measured for all four.  Two cases it can't reach:

- **SIGKILL**, which no trap sees.  The flag stays until someone removes it ([post-deploy.md](post-deploy.md#the-upgrade-page)); the next deploy clears it either way.
- **SIGTERM to the `just` process alone.**  `just` 1.40 does not pass it to the running recipe; it waits for the recipe to finish and then exits 130.  So the deploy runs to the end, the flag comes down on schedule, and `status.json` says `done` while `just` says 130.  Nothing is left behind the page, but the exit code and the board disagree.

**What the flag covers.**  `GET` and `HEAD` navigations (`Accept: text/html`) on the chat host and every course chat host.  Not sign-in, not the gateway, not a course panel; not `/_status.json`, not `/help/`; not a `POST`, so a form submission or an admin-config write meets exactly what it would meet without the flag; and not a request carrying the header `X-Almanac-Bypass` (any value).  The bypass is for an operator who wants to look behind the page, and for any probe that runs inside the window.  It is not a secret and doesn't need to be: the page is a courtesy, not a wall, and getting past it reaches exactly what would be there without it.  None of the deploy's own checks need it — `smoke` and `oidc-settle` talk to the services directly, never through the edge.

**Time remaining.**  The wrapper appends each run's step durations to `status/history.json` and keeps the last ten; a step counts only when it finished cleanly.  `eta_seconds` is the sum of the medians of the steps still to run *up to and including `oidc-settle`* while the window is ahead, because that is when the page lets people back in; after it, to the end of the run.  Until every remaining step has history it is `null`, and the page says "a few minutes".  Otherwise it says "about two minutes", never a countdown that can reach zero and keep going.

**When it fails.**  `state: failed` clears the flag like any other exit.  Whatever is still down shows the passive page, which reads `failed` and changes its words: "This is taking longer than planned.  The team knows."  What makes "the team knows" true: a step that fails sends the desk a notice (webhook, else email to `admins:`) naming the step, the exit code and the commit, through the same registrar call `just backup` uses.  A signal isn't reported, because whoever sent it already knows.  If the registrar is the thing that broke, the notice can't go, and the deploy says so; CI's red is the record then.

**Old news is ignored.**  An `upgrading` file that hasn't been updated in an hour is a deploy that died without its trap, and a `failed` more than two hours old is not why the platform is down now.  The page shows its plain message for both.

## The page

- **One file**, [`caddy/upgrade/index.html`](../caddy/upgrade/index.html), served through Caddy's `templates` so it can say `PLATFORM_NAME` (and link to `CHAT_HOST`'s help site).  Compose passes both to the edge.  No CDN, no web fonts, no external anything: an upgrade is precisely when an outside dependency is least welcome.  Light and dark follow `prefers-color-scheme`, and it is laid out for a phone first.
- **Works without JavaScript.**  The plain version says the platform is being upgraded and will be back in a few minutes, links to the help site, and refreshes itself every 30 seconds (a meta refresh inside `<noscript>`).
- **With JavaScript** it polls `/_status.json` every three seconds and shows the step list, a progress bar and the time remaining.  On the same tick it asks its own URL, with `HEAD`, whether a plain navigation would still get the page: the moment the answer comes back without `X-Almanac-Page`, it reloads into the app.  That is the exact form of "reload when the state is `done` or the flag is gone" — reading `done` alone would loop forever on a service that is still down after a deploy finished.  An answer that never comes (the edge itself restarting) means wait.
- **Reassures about the one thing people fear.**  "Your conversations and files are safe."
- **The rotating line.**  Under the progress bar, a line that changes every four seconds: "Reticulating splines" earns its place beside our own.  They live in [`caddy/upgrade/lines.txt`](../caddy/upgrade/lines.txt), one per line, and Caddy inlines the file into the page, so they can be edited without touching the HTML.
- **The page and the lines are student-facing text**, so `just docs-corpus` holds them to the same banned-word list and no-brand-name rule as `apex/`: the visible text and the script's strings of the page, and every non-comment line of `lines.txt`.  The step labels in `deploy_status.py` are checked the same way, as one of the corpus's `SPOKEN` files.

## What it can't cover

**The edge itself.**  If `up` recreates the edge container (when its definition changed — this feature's own first deploy is one), nothing serves for those seconds, and the browser shows its own error.  So does `config-refresh` restarting it, which now happens only when the edge's real config changed (the Caddyfile, the page itself, a rendered vhost) — its content mounts, `/srv/docs`, `/srv/sbom` and `/srv/status`, are skipped.  A second or two, and the page's poll rides it out, but a navigation in that second gets the browser's error.

**A request already in flight.**  A chat reply streaming when its container stops is cut off; the page can't rescue it.  LibreChat keeps the conversation, so a reload shows what was saved.

## Lanes

The edge config, the wrapper, `status.json` and the render changes are plumbing (@geordi).  The page's words, the step labels and the rotating lines are pedagogy (@piper) — the copy in this first cut is deliberately plain and waiting for her pass.

## What was measured, and what still has to be

On a throwaway compose project — the edge built from `./caddy` on 2.11.4, stub upstreams under the real service names, and a course vhost rendered by `render.py` — all six of the original checks:

1. A course's chat stopped: a browser navigation gets the page with 503; `Accept: application/json` gets the JSON 503; `/help/` still serves.
2. The same for the front door, sign-in, the gateway and a course panel.
3. With the flag on: navigations on the chat and course hosts get the page; `/_status.json`, `/help/`, a `POST`, an API call and a request with `X-Almanac-Bypass` reach the upstream; sign-in, the gateway and the panel are not covered.
4. The real `deploy` script against stub steps: steps recorded in order, the flag up for exactly `up` through `oidc-settle`; a failing step, SIGINT, SIGTERM and SIGHUP to the group, and SIGTERM to the script all leave no flag and `state: failed`, and a failing step's exit code comes out of `just deploy`.
5. `egress-check`'s edge layer (the admin-config wall, both ways in) replayed request for request, flag on and off: unchanged.  The rest of `egress-check` and `course-tokens-check` never go through the edge.
6. `handle_errors 502 503 504` adapts to a `{http.error.status_code} in [...]` expression on 2.11.4 and sits beside the chat site's `/help/` 404 handler.

In a headless browser: the step list and ETA render, the page reloads into the app within a poll of the flag coming down or the upstream coming back, the failure wording shows, and the page renders at phone width in light and in dark, and without JavaScript.

**Still owed, on the first real deploy:** that `egress-check` and `course-tokens-check` go green through the wrapper on a box with real LibreChats, and that a student-shaped browser sees the page during `up`.  Then this moves to `active`.
