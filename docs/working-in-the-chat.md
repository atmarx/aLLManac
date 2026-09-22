---
title: How do I get around the chat window?
description: Working the chat itself — picking a model, steering a conversation, reusing what works, and what a long thread actually costs you.
audience: student
also_reaches: [faculty]
status: scaffold
owner: piper
tags: [ai-literacy, librechat, metering, attribution, critical-evaluation, hallucination]
tethered_to:
  - docs/user-guide.md
  - docs/design-walls.md
---

# Getting around the chat window

!!! warning "Scaffold — every claim below is UNVERIFIED"
    This page is an outline, not documentation.  It is `status: scaffold`, so `docs/corpus.py` withholds it from every guide's corpus and no agent can quote it.  **Do not promote it to `draft` until each section has been checked against a running instance at our pinned version** — `LIBRECHAT_IMAGE=ghcr.io/danny-avila/librechat:v0.8.7` (`.env.example:44`).  Nothing here may be written from general knowledge of LibreChat: the UI moves between releases, and a confident wrong answer in the corpus stops being a mistake and becomes policy the moment six agents start quoting it.  The operator-facing precedent for how to hold this kind of knowledge is `docs/design-walls.md`, "LibreChat (v0.8.7)" — version-stamped, and paid for once.

[Building an agent](user-guide.md) is the other half of this.  This page is about the window you build it in.

## Why this page exists

The Student Guide is scoped to LibreChat user functionality — custom agents, sharing with teammates, writing good prompts, and using tokens efficiently.  The first two have a page.  The last two do not, and they cannot be written without the mechanics below: "write a good prompt" and "don't waste tokens" are both advice about a context window, and nothing in the corpus currently describes one.

## What three research passes settled (2026-09-15)

A config audit of tracked files, an inventory of what this repo already asserts, and a source read of the upstream `v0.8.7` tag.  **Config + upstream is a sound chain where our config sets nothing**: if we do not override a key, upstream's default at our pin *is* our behaviour.  That closes a good share of the list below without touching a box.  What it cannot close is what a control is *called* and *where it sits on screen* — that still needs eyes on a running instance.

**Settled — write these from the sources named:**

- **File limits: 10 files, 25 MB each, 100 MB total** (`librechat/librechat.yaml:55-60`, and identically per course in `registrar/render.py:185-190`).  Distinct from LibreChat's *upload rate limiter* — 50/user and 100/IP per 15 min — which our template leaves unset (`.env.example:128-129`).  Two different mechanisms, both true; no page currently states both, and conflating them is the obvious way to get this wrong.
- **Chat file vs. agent knowledge file.**  RAG indexes only what is attached to an agent's `file_search` tool_resource (`scripts/seed_agents.py:44-50`).  A file dropped into a conversation is searched only if the composer's File Search toggle is on (`interface.fileSearch`, default `true`, which we do not override).  They are two switches, not one.
- **Agent capabilities are `file_search`, `tools`, `artifacts`** — `execute_code`, `web_search` and `actions` deliberately excluded on both surfaces (`librechat/librechat.yaml:107-129`, `registrar/planes/config.py:44-47`).  Artifacts are on for both surfaces and now say so to readers (`apex/user-guide.md`, Part 1) — what is still undocumented is where the renderer fetches from, which is a plumbing question nobody has measured.
- **Editing and regenerating do not destroy anything.**  "Save & Submit" and Regenerate both create a *sibling* message under the same parent; the earlier version stays reachable through the `‹ n/m ›` sibling arrows.  Fork is a separate control that copies the thread into a **new conversation**, with three scope options.
- **A Context Usage gauge ships in v0.8.7** — `interface.contextUsage` default `true`, `interface.contextCost` default `false`, and we set neither.  So students already see context consumption and do not see cost.  This is the answer the scope ruling's "use tokens efficiently" needs, and `docs/budgets-and-meters.md:90` already describes it.
- **Presets are per-user and cannot be shared** (no sharing field exists in the schema).  The Prompt library is a separate system with `share`/`public` defaulting **false**.
- **Conversation search works, and it did not before.**  *(closed 2026-09-15 — was the first open question on this page.)*  The guess was right: unset did **not** mean on.  Upstream gates its indexing hook on `SEARCH` being the literal string `true`, so an unset value left every per-course Meilisearch running and empty — two months of a service indexing nothing.  Now set on both surfaces (`compose.yml:181`, `registrar/render.py:358`), and @xram confirmed a working search field from the student's side of the door rather than from a probe.  **The general lesson outlasts the fix: a search box that returns nothing is indistinguishable from a student who has nothing to find**, which is why this sat unnoticed — the empty result was plausible.

**Open, and needs a human on a running instance:**

- [ ] **Temporary chat, and what it does to the retention promise.**  `interface.temporaryChat` defaults `true`, `temporaryChatRetention` defaults **720 hours (30 days)**, `retentionMode` defaults `"temporary"` — and we configure none of them.  Upstream backs this with a real MongoDB TTL index, so temporary conversations are *deleted*, not merely unsaved.  Meanwhile `apex/your-data/how-long-we-keep-it.md:18` tells students: "There is no automatic expiry on this platform."  **Confirm the feature is reachable in our UI, then fix that sentence** — it is on the page students are sent to for data questions, and we document temporary chat nowhere, so anyone using it is unaware their data expires.
- [ ] What LibreChat does when a conversation exceeds `maxContextTokens` on the **Agents** endpoint — legacy sliding-window truncation, the newer `summarization:` block, or logic inside the pinned `@librechat/agents` package.  Not resolvable from source; test empirically with a long thread against a small-context model.  **Half of what this question was really asking is now closed, and it turned out to be a different layer** — see below.
- [ ] Whether `modelSpecs.enforce: true` alone hides raw endpoints.  Upstream says no — it is a *server-side* gate, and hiding endpoints needs `modelSpecs.addedEndpoints` as well.  This bears directly on the open question already flagged at `docs/design-walls.md:101` and `docs/admin-guide.md:304`; resolve them together.
- [ ] Pinned Conversations and Chat Projects are **new in v0.8.7** and have no `interface` toggle, so they cannot be turned off by config.  Confirm how they render before deciding whether to document them.

**A caution the research itself produced:** current docs.librechat.ai lists `interface.feedback` and `interface.schedules`, and **neither exists at v0.8.7**.  Anything written from "the LibreChat docs" rather than from our pinned tag will import controls our students do not have.

## To verify, then write

Each heading is a question a student actually asks.  The checklist under it is what has to be confirmed in v0.8.7 before the section can be written — names of controls as they appear on screen, and where they live.

### Which model am I talking to, and can I change it?

- [ ] Where the model selector appears, and what it is called on screen
- [ ] Whether a student can change models mid-conversation, or only at the start
- [ ] What our `modelSpecs` actually present to a course instance, and whether the underlying model name is visible (see `docs/design-walls.md`, "`modelSpecs` needs literal agent ids")
- [ ] Whether an agent pins its own model regardless of the selector

### I got a bad answer — do I start over?

- [ ] Editing a message you already sent, and what happens to everything after it
- [ ] Regenerating a response, and whether the old one is recoverable
- [ ] Forking or branching a conversation: exact control name, and where the branches go
- [ ] Whether any of the above is disabled in our configuration

### How do I keep a prompt that worked?

- [ ] Whether the prompt library / saved prompts feature is enabled in our config
- [ ] Presets: what they store, and whether they are per-user or shareable
- [ ] Bookmarks or tags on conversations, if present
- [ ] The honest alternative if none of these are turned on

### Files: in the chat, or on the agent?

- [ ] Uploading a file to a single conversation vs. attaching a knowledge file to an agent
- [ ] Which one persists, which one is searched, which one every classmate with the agent can see
- [ ] Size and count limits at our pin (`docs/design-walls.md` notes 50 uploads per user, 100 per agent — confirm these are the current numbers and what they apply to)
- [ ] What happens to an uploaded file when the conversation is deleted

### Why did my long conversation get slow, expensive, or forgetful?

**This is the section the scope ruling actually needs.**

**There are two trimmings, not one, and only the second is settled.**  LibreChat assembles a conversation up to `maxContextTokens` and trims to fit that — *how* it trims is the open question above.  Whatever it hands over then meets a second ceiling: what the endpoint actually serves.  If that is the smaller of the two, the backend trims again, and **Ollama trims from the front and answers anyway** ([the wall](design-walls.md#a-context-window-larger-than-the-endpoint-serves-deletes-the-system-prompt-2026-09-21) has the mechanism and the measured numbers).

For this page the consequence is a rewrite of the question, not an answer to it.  *"Forgetful"* was drafted here as a student's word for losing the early turns of their own thread.  The second trimming loses something the student never wrote and cannot see — the agent's instructions — so the same word covers a conversation that quietly forgets **what it was told to be.**  That is not a token-efficiency tip; it is why the honest student-facing advice is stronger than "you'll lose the beginning."  **A long thread does not just cost more, it drifts** — and starting a fresh one is the fix for both, which is the rare case where the cheap advice and the correct advice are the same sentence.

- [ ] Whether the context window is surfaced to the user anywhere in the UI.  **Two-minute check, and it is now the highest-value one on this page**: is there a gauge above the composer?  This is settled from source in both directions and never once from a screen — the config read above says the widget ships on by default, and `apex/understanding-your-usage/context-is-the-conversation.md` told students flatly that *"you cannot see the number while you are working"* and built an argument on it.  A `scaffold` and a `draft` in the corpus, disagreeing, both confident, neither looking.  The published page has been softened to say we are unsure (2026-09-22) — **which is the correct state to publish and a bad one to leave**, because a page that admits it does not know is still a page a student reads instead of an answer.  Confirm also whether the gauge reads the window LibreChat assembles or the one the endpoint serves; they are [two different numbers](design-walls.md#a-context-window-larger-than-the-endpoint-serves-deletes-the-system-prompt-2026-09-21).
- [x] ~~What our configuration does when a conversation exceeds it~~ — **settled at the endpoint layer: truncate, silently, from the front.**  Not an error and not a summary.  Still open at the LibreChat layer.
- [ ] Whether a long thread re-sends its whole history every turn, and therefore what a fiftieth message costs relative to a first
- [ ] Whether starting a fresh conversation is the right advice, and when
- [ ] How any of this appears in the student's own budget numbers (`docs/budgets-and-meters.md` is `status: proposed` — this section may be blocked on that ruling)

### Where did that conversation go?

- [ ] Conversation search: what it searches, and how it presents results — **that** it works is settled above; what it covers is not
- [ ] Whether conversations can be archived, exported, or deleted by the student
- [ ] What a temporary chat is, if we expose one, and what it does not save

## The rule for writing this

Every claim gets checked on a running instance before it is written down, and the version it was checked against gets named.  When the pin moves, this page is on the list to re-check — the same discipline `design-walls.md` uses, for the same reason.
