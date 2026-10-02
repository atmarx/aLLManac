---
title: What do people see while we upgrade?
description: A page the edge serves whenever a service behind it is down — on its own for any restart, and with a live step list while `just deploy` runs — so a student mid-upgrade gets "back in a few minutes" instead of a bare 502.
audience: operator
status: proposed
owner: geordi
tags: [deployment, docker-compose, chokepoint, operator-duty]
tethered_to:
  - caddy/Caddyfile
  - registrar/render.py
  - justfile
  - compose.yml
---

# What do people see while we upgrade?

A student refreshes the chat at 2:14 in the afternoon, ten minutes before a lab is due, and gets `502 Bad Gateway` in Caddy's plain type.  Nothing on the screen says whether the platform is gone, whether their work is gone, or whether to wait.  In the early weeks we deploy often, and every `just deploy` and `just render` restarts something.  That screen is the one we are showing most.

This page is the plan for replacing it.  It is a spec: nothing here is built yet.

## Two layers

**The passive layer is most of the value.**  The edge already sits in front of every service, so it already knows when one isn't answering.  Caddy's `handle_errors` catches a 502, 503 or 504 from any upstream and serves the upgrade page in its place.  That covers every restart, announced or not: a course coming back after `just render`, the front door losing its OIDC race after a reboot, someone running `just up` by hand.  It needs no hook in the deploy and works per course, because each course vhost has its own upstream.

**The active layer is the status board.**  While `just deploy` is in its disruptive stretch, the edge serves the page on purpose, and the page shows the deploy's steps ticking off with a rough time remaining.  When the stretch ends the page reloads itself into the chat.

## The passive layer

- **Every proxied site gets the handler:** the front door, sign-in, the gateway, and, through the render, every course vhost and every course panel vhost.  The chat site already has a `handle_errors 404` scoped to `/help/`; the new handler names its status codes so the two sit side by side.
- **Browsers get the page; programs get JSON.**  A request whose `Accept` includes `text/html` gets the page.  Anything else (opencode against the gateway, the chat app's own `/api/` calls, an MCP client) gets `{"error": "...", "retry_after": 30}`.  Both are status **503** with `Retry-After` and `Cache-Control: no-store`, never 200: monitoring has to see an outage as an outage, and no browser or proxy may cache the page in place of the chat.
- **The help site keeps working.**  `/help/` is static files the edge serves itself, so it is up whenever the edge is.  The page links to it.

## The active layer

**Where the status lives.**  A `status/` directory at the repo root, gitignored, mounted read-only into the edge.  The deploy writes `status/status.json`; the edge serves it at `/_status.json` on every host, so the page's poll is same-origin wherever it's shown.

```json
{
  "state": "upgrading",
  "started": "2026-10-02T18:04:11Z",
  "eta_seconds": 140,
  "steps": [
    {"name": "pull",  "label": "Fetching the new version", "state": "done"},
    {"name": "up",    "label": "Restarting services",      "state": "running"},
    {"name": "smoke", "label": "Checking it's serving",    "state": "waiting"}
  ]
}
```

`state` is `upgrading`, `done` or `failed`.  Labels are written for students, not operators: "Restarting services", not `config-refresh`.  The file never carries an error message, a log line, a hostname, an image tag or a version.

**Who writes it.**  The justfile, because that is where deploy logic lives (`docs/ci.md`).  `deploy` becomes a wrapper that runs the same recipes in the same order, and records each step's start and finish in `status.json` around it.  The recipes themselves don't change.  A `trap EXIT` writes the final state and clears the flag on any exit, so neither a failed deploy nor a `Ctrl-C` can leave the site behind the page.

**When the page is on.**  The flag is the file `status/upgrading`.  The wrapper creates it just before `up` and removes it after `oidc-settle`.  `pull`, `build` and `secrets` change nothing that's running, so the page doesn't cover them.  The checks after `oidc-settle` (`egress-check`, `course-tokens-check`, `render-check` and the rest) have to test the real system, not the page, so they run with the flag already gone.  Anything still restarting by then is the passive layer's to catch.

**What the flag covers.**  Navigations (`Accept: text/html`) on the front door and course hosts.  Not `/_status.json`, not `/help/`, and not a request carrying the header `X-Almanac-Bypass`.  The bypass is for an operator who wants to look behind the page, and for any probe that runs inside the window.  It is not a secret and doesn't need to be: the page is a courtesy, not a wall, and getting past it reaches exactly what would be there without it.

**Time remaining.**  The wrapper appends each run's step durations to `status/history.json` and keeps the last ten.  `eta_seconds` is the sum of each remaining step's median.  The page says "about two minutes", never a countdown that can reach zero and keep going.

**When it fails.**  `state: failed` clears the flag like any other exit.  Whatever is still down shows the passive page, which reads `failed` and changes its words: "This is taking longer than planned.  The team knows."  Telling the team is out of scope here; the desk notifier (`planes/notify.py`) is the obvious place for it later.

## The page

- **One file**, `caddy/upgrade/index.html`, served through Caddy's `templates` so it can say `PLATFORM_NAME`.  Compose passes that to the edge.  No CDN, no web fonts, no external anything: an upgrade is precisely when an outside dependency is least welcome.
- **Works without JavaScript.**  The plain version says the platform is upgrading and will be back in a few minutes, links to the help site, and refreshes itself every 30 seconds.  With JavaScript it polls `/_status.json` every three seconds, shows the step list and the time remaining, and reloads into the chat when the state is `done` or the flag is gone.
- **Reassures about the one thing people fear.**  "Your conversations and files are safe" belongs on it, in words Piper chooses.
- **The rotating line.**  Under the progress bar, a line that changes every few seconds: "Reticulating splines" earns its place, beside our own, kept in `caddy/upgrade/lines.txt` so they can be edited without touching the page.  The page and the lines are student-facing text, so `docs-corpus` holds them to the same banned-word list as `apex/`.

## What it can't cover

**The edge itself.**  If `up` recreates the edge container (only when its definition changed; config reloads are graceful), nothing serves for those seconds, and the browser shows its own error.  That is rare enough to accept.

**A request already in flight.**  A chat reply streaming when its container stops is cut off; the page can't rescue it.  LibreChat keeps the conversation, so a reload shows what was saved.

## Building it

Lanes: the edge config, the wrapper, `status.json` and the render changes are plumbing (@geordi).  The page's words and the rotating lines are pedagogy (@piper).

Measure on a throwaway stack before it ships:

1. Stop a course's chat container: a browser navigation gets the page with 503; `curl` with `Accept: application/json` gets the JSON 503; `/help/` still serves.
2. Same for the front door, sign-in, the gateway and a course panel.
3. With the flag on: navigations get the page, `/_status.json` and `/help/` don't, and a request with `X-Almanac-Bypass` reaches LibreChat.
4. A deploy that fails mid-`up` (kill it): the flag is gone afterwards and `status.json` says `failed`.
5. `egress-check` and `course-tokens-check` pass unchanged after a full deploy through the wrapper.
6. The `handle_errors` status-code form works on the pinned Caddy, and coexists with the chat site's `/help/` 404 handler.

Then the wall goes in `design-walls.md`, and this page moves from `proposed` to `draft`.
