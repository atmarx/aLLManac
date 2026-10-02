---
title: Where do you pick up a key, if not in the chat?
description: A proposed credential hatch on its own hostname — why a plaintext key can never be returned by an MCP tool, why the registrar can't be the browser surface, and what the pickup page has to show so nobody mistakes an empty budget for a broken key.
audience: operator
also_reaches: [builder, faculty]
status: proposed
owner: marco
tags: [secrets-management, escrow, key-rotation, access-control, least-privilege, oidc, audit-logging, attribution, metering, chokepoint, openbao, litellm, librechat, mongodb, caddy]
tethered_to:
  - registrar/server.py
  - registrar/planes/verbs.py
  - registrar/planes/escrow.py
  - caddy/Caddyfile
  - docs/budgets-and-meters.md
  - docs/rooms-and-visibility.md
---

# The mailroom — where a key is picked up, and why it can't be the chat

**Status: proposed, 2026-09-11.**  Not ruled.  The escrow this depends on is built and running (`registrar/planes/escrow.py`, `verbs.py`); what is proposed is a browser surface that hands a key to the person it belongs to without the key passing through a model.  The defect it fixes is **verified, not hypothetical** — see [What the chat actually does with a key](#what-the-chat-actually-does-with-a-key).

Origin: a specification brought back from a Codex session (2026-09-11), evaluated against this repo and cut down hard.  [What this drops from the source spec](#what-this-drops-from-the-source-spec) says what was removed and why, so the reasoning survives the deletions.

---

## The rule

**A plaintext key never enters a model-visible channel.**

Not a prompt, not a tool result, not an assistant message, not a conversation record, not a request to a model provider.  Masking the key in the assistant's *next* message does not undo the disclosure — by then it is already in the transcript and already went upstream.

The corollary is the whole design: **if the chat can't say it, somewhere else has to.**  That somewhere is a page, on its own hostname, that authenticates the person and hands them the key directly.

## What the chat actually does with a key

Verified in this repo, not inferred:

`registrar/server.py:167` puts `rec['key']` — the plaintext virtual key, straight out of OpenBao — into the string `my_key()` returns.  `:186` does it again for `rotate_my_key()`.  An MCP tool result is model input, so every key a student has ever asked for has travelled: into the active context, out to the model provider, and into MongoDB as a message document that persists for the life of the conversation.

This is the normal path.  It is what the admin guide tells students to do.

We already reasoned about this hole once and guarded the other side of it: Decision 20 *(2026-07-24, [registrar-spec.md](registrar-spec.md))* covers a secret coming **in** — someone pasting an endpoint provider's key at an agent, where it would land in chat history — and defers a one-time drop token for it.  The identical argument applies to a key going **out**, and nothing guarded that.

## Why the registrar can't be the browser surface

The obvious economy is to hang a page off the registrar: it already holds the OpenBao AppRole, already reads the roster, already serves HTTP, and `@mcp.custom_route` works on our fastmcp pin (`server.py:327` uses it for `/health`).

**Don't.**  The registrar's identity model is header-trust: `_ident()` (`server.py:41`) checks a shared service token and then *believes* `X-User-Email`.  That is sound where it lives — the token is rendered server-side into each instance's MCP config and never reaches a browser — but it means anything holding that token can impersonate any user in any course.  Putting a browser-reachable route in that process leaves full impersonation one routing mistake away.

**Two identity models in one process, where one of them is "trust this header," is not a seam worth having.**

## Why its own hostname

The cheap options are the vestibule's host (`chat.<domain>`, which exists today) or a path on the apex (which does not exist at all — the Caddyfile has chat, auth, gateway, and the rendered fleet; the docs site lives in the untracked `site/` overlay).

Both are wrong, for one reason: **same origin means LibreChat's JavaScript can call the hatch.**  The session cookie would be `HttpOnly`, so no script reads it — but the browser attaches it automatically to a same-origin `fetch()`, so one XSS in LibreChat reaches the pickup endpoint from inside the room the hatch exists to stay out of.

That is not a theoretical concern on our pin.  The image ships **no CSP and no `helmet`, and mounts bare `cors()` with no origin restriction** ([budgets-and-meters.md](budgets-and-meters.md)).  A separate origin is the mitigation that holds in a codebase we don't control and can't harden.

It stopped being theoretical the same day this was written.  `preAuthTenantMiddleware` in the pinned image **trusts any well-formed client-supplied `X-Tenant-Id`** on `/oauth` and `/api/auth`, scoping every query in the request to it, strict mode or not — found on 2026-09-11 and now stripped at the edge ([design-walls.md](design-walls.md#librechat-v087)).  That is the same class of defect this section is guarding against, in the same image, discovered by looking rather than by reasoning.  **The argument for a separate origin is not that LibreChat is badly written; it is that we cannot audit it faster than it changes.**

The vestibule has a second problem: it is the demo environment, the instance most likely to be poked at by whoever is in the room and most likely to be torn down between demos.  A credential hatch pinned to that origin inherits both.

A new subdomain is also *cheaper* than the apex, not dearer.  The Caddyfile already assumes wildcard DNS at `*.{ALMANAC_DOMAIN}` with one wildcard cert covering the fleet (`caddy/Caddyfile`, the fleet import comment); a new name is covered the moment it exists, and on `tls internal` it costs nothing either.  About six lines, and no decision about what the apex serves.

## Why "mailroom"

A mailroom holds everyone's mail and hands you only what is addressed to you, after you show ID.  That is the authorization model in one word, which is most of why it beats the alternatives.

It is also a place you physically go to — which is the entire point, since going somewhere else is the thing the chat cannot do for you.

And it works in **both directions.**  Decision 20's inbound drop — a student handing the system a secret without it landing in Mongo — is a parcel drop-off at the same window, under the same identity check, on the same origin.  Naming the surface `mailroom` leaves room for it; naming it for key pickup means naming a second thing later.

`dispenser` is the one to rule out: a vending machine implies press-button-get-key with no clerk, which is the wrong picture of what happens here.

## The shape

```text
browser ──TLS──▶ Caddy  mailroom.{ALMANAC_DOMAIN}
                   └──▶ oauth2-proxy ──▶ mailroom:8080
                                              │
                                              │ Bearer (internal token)
                                              ▼
                                        registrar:8080/internal/*
                                        roster check · escrow read · rotate
```

Three decisions make this small:

**The mailroom holds no credentials of its own.**  The source spec gives it a read-only OpenBao AppRole; instead it asks the registrar for everything over an internal route, so it holds exactly one secret — a bearer token — and no OpenBao role, no LiteLLM master key, no Keycloak admin password.  This deletes a policy, an AppRole, a `bao-init` extension, two env vars, and the whole "can it reach the service path?" test matrix.  It also keeps `reconcile.py`'s opening claim literally true: *"The ONLY code that holds minting credentials."*  The spec's version quietly makes that false.

**We don't write the OIDC.**  Authorization Code flow, PKCE, state, nonce, JWKS caching, server-side sessions, CSRF — that is the bulk of the source spec's implementation, and it is security code that has to be right.  `oauth2-proxy` is one pinned container that does all of it and forwards a verified email header.

That is header-trust again, deliberately.  It is safe for the same reason the registrar's is: the mailroom publishes no port, and Caddy routes only to the proxy.  The difference from putting this *in* the registrar is that here header-trust is the only model in the process, so there is no second one to confuse it with.

**The student is already signed in.**  They reached LibreChat through Keycloak, so the redirect out to the mailroom and back is silent.  No second login is most of what makes a "go somewhere else for your key" flow tolerable.

Four routes:

| Route | Purpose | Returns a key? |
|---|---|---:|
| `GET /` | every room this person holds a key in | no |
| `GET /<slug>` | masked key, budgets, gateway URL, buttons | no |
| `POST /<slug>/env` | the `.env` file, as an attachment | yes |
| `POST /<slug>/rotate` | confirm, then rotate | yes |

The index is the part `my_key()` structurally cannot do.  It takes zero arguments *because* `X-Course` pins it to one instance — correct inside a course, useless to a person who holds four keys and wants to see them.

**Download first, reveal second.**  Someone pointing opencode at the gateway needs a `.env`, not a string on a screen.  The source spec builds a reveal component with a mask, a clipboard call, removal from the DOM after sixty seconds, and clearing on tab-hide — a lot of JavaScript defending a value the person is about to write to disk anyway.  Keep reveal as a plain secondary button without the timer theatre; the file is the real path.

## No roster, no key

**A room that cannot say who is in it cannot mint a key**, because there is nothing to authorize against.

This is not a policy choice, it is what falls out of the authorization model, and it settles the vestibule cleanly: the one room everyone in the realm can enter has no membership list, so there is nothing the mailroom could check.  It already fails closed today — `my_key()` tests `email not in course["students"]` and the office record has no students — and it stays consistent all the way down, because the front office runs the `$0` house-metal pack (`registrar-spec.md:343`): no spend, no key, no meter.

Rooms that **do** get mailroom access: `course`, `project` (standalone and course-linked), and a granted `sandbox`.  Each has a member list because each was requested and provisioned for named people.

Rooms that **don't**: `office` / the vestibule.  A developer deploying against the platform uses their own course or project key from a direct harness, not a key minted in the room everyone shares.

> **Open, and a consequence rather than a ruling:** an open *commons* — the shared everybody-room proposed in [rooms-and-visibility.md](rooms-and-visibility.md) — is to a sandbox what the vestibule is to a course.  If it is genuinely open to all, it has no roster and therefore no keys, by the same invariant.  A sandbox that someone *requested* is different: it has members, so it has keys.  The commons is unruled, so this is flagged, not decided.

After cutover the refusal text has to change with it.  `my_key()` currently tells a non-member to ask their instructor about the roster; from the vestibule that sends people hunting for a roster that will never exist.  It needs to say *you don't pick up keys here.*

## What the page shows, and why it is not decoration

A student whose budget is exhausted gets a rejection from the gateway.  Nothing in that rejection says "you are out of money" — so the reasonable conclusion is **the key is broken**, and the reasonable next move is to get a new one.  The pickup page is where that misreading is either prevented or manufactured.

Two numbers can stop a key working, and they fail identically at the gateway:

- **Fuse remaining** — this key's own cap (`key_fuse`).  Red when low.  When it is gone, name it: *the fuse is spent*, because that is the one condition rotation is actually for.
- **Course pool remaining** — the hard term cap (the LiteLLM team budget).  Red when low.  When it is gone, name it: *the pool is spent*, because rotation does nothing whatsoever for this one.

A third goes on the page and **must not be red**: `advisory_weekly` never blocks, and colouring a pacing number like a wall is a lie the reader can catch.  That is [budgets-and-meters.md](budgets-and-meters.md)'s rule — an ambient number has to be honest about what it can do.

All three come from LiteLLM.  Nothing is computed locally, so the mailroom cannot drift from the ledger.  `ll_key_spend()` already reads the fuse side; the pool needs a small team-info reader that does not exist yet.

### A key's number must never promise more than the pool can pay *(ruled 2026-09-11)*

Rotation used to carry the remainder forward with a floor (`verbs.py`):

```python
remaining = round(max(0.5, fuse - spent), 2)
```

Rotate at exhaustion and the replacement arrived with **$0.50**.  Rotate again, another $0.50 — a fuse that refills on demand bounds nothing, which is the one job `key_fuse` has.  Today that takes a chat request and nobody does it twice; a Rotate button on a page every student visits makes it the obvious move for exactly the population that thinks their key is broken.

But the floor was the wrong instrument for a wider reason, and the wider rule is what got ruled:

> **A key may never carry a fuse larger than what is actually available, and a fuse too small to fund a working session is not minted at all.**

The floor guaranteed a *minimum*.  What this needs is a **gate**.  Those have similar shapes and opposite effects.

The first half applies well beyond rotation.  Enroll a student late into a course whose pool is nearly spent and today they receive a $5 key against $2 of pool — a key that stops at $2 and never says why.  The pool is the hard cap and LiteLLM enforces it whatever we write, so clamping the fuse to the pool remainder buys no enforcement; **it makes what the key says and what the key can do the same number**, which is the entire reason the mailroom shows a number at all.

The second half is the refusal.  Handing someone a dead-on-arrival credential costs them a debugging session and teaches them the platform is broken.  A refusal that names the reason costs one sentence.

Implemented in `_fuse_for()` (`planes/verbs.py`) across all three mint paths — enrollment, rotation, and the operator's `just key`.  Rotation clamps *before* it revokes, so a refusal leaves the caller exactly as they were, still holding a working key.  An unreadable pool mints optimistically rather than refusing: failing closed on a transient gateway blip would strand a whole roster in exchange for protection LiteLLM already provides.

**`REGISTRAR_MIN_FUSE` is a placeholder.**  Nobody has measured what a short opencode session actually costs against our packs.  It is measurable — run one and read the ledger — and until someone does, the default of $1 is taste, not evidence.

## Who gets a key

**Students, instructors, and TAs** — anyone on the room's roster, in either direction.

Today `my_key()` refuses staff and sends them to `just key`.  That was an artifact of keys being a student-provisioning side effect, and it is wrong: faculty and TAs demo in front of the room, and that demo is metered cloud spend like any other.  **It should be attributed to them, in their course, under their own name** — not untracked, and not folded into some student's line.  `mint_key()` already escrows any roster member at the same path, so the machinery is there.

The consequence is a budget one: staff usage lands in the course pool, so the pool has to be sized for it.

### The pool has two components that scale differently

This is worth stating now because it shapes an institutional decision later.

**Staff demo usage is roughly fixed per course** — an instructor demonstrates the same things to fourteen students as to sixty.  **Student usage scales with enrollment.**  A single flat number cannot be right for both: a flat $3k over-serves a seminar and starves a large lecture on the student side, while a pure per-student allotment under-funds the teaching component of small courses.

So the shape a future policy probably wants is **a base plus a per-student allotment**, not one or the other.  Round numbers are fine for now; naming the two components now means the eventual decision is a matter of setting two figures rather than rediscovering that one figure was never going to work.

That decision is institutional, not ours, and it is out of scope here.

## What this drops from the source spec

Recorded so the reasoning survives, rather than looking like oversight:

- **The read-only OpenBao AppRole, its policy, and the `bao-init` extension.**  The registrar does the read; the mailroom holds no vault credential at all.
- **Escrow schema v2 — `state`, `key_id`, `last4`.**  `revoke_pending` already carries the only state that matters, and `last4` is `key[-4:]` at render time.
- **The `copy_acknowledged` audit event.**  You cannot observe a clipboard.
- **A `readyz` separate from `healthz`.**  `just smoke` is our readiness story; a second one drifts from it.
- **The sixty-second DOM removal and visibility-change clearing.**  Guarding against shoulder-surfing on a page opened deliberately, while handing over a file with the same secret in it.

Kept, despite looking skippable:

- **`just key-audit`.**  The only thing that ever detects the mint↔escrow orphan window, which [design-walls.md](design-walls.md) records as permanently open — no ordering closes it, it can only be found, by joining `/key/list` to the escrow on `key_alias`.  Without it that wall describes a problem with no instrument.
- **Origin check and POST-only on the secret routes.**  The proxy's `SameSite=Lax` cookie already blocks cross-site POST; five more lines on the one route that emits a secret is cheap.
- **The `no-store` header set.**  Trivial, and essential.

## The two lighter designs, and why not

**OpenBao's own UI with an OIDC auth method.**  This is already documented as the break-glass path (`registrar-spec.md:216`) and costs no new service: a policy templated on the identity's email, student reads their own path.  Rejected because it lands students in an operator console, and because the authorization becomes a templated policy string written once and never exercised — where the failure mode is one student reading another's key.  The mailroom's authorization is code, and code can be tested.

**A one-time signed link handed out in chat.**  Lighter still, and it is Decision 20 inverted.  Rejected because the token lands in the transcript, which degrades the invariant from *no secret-shaped thing ever enters the chat* to *a short-lived one does*.  The first is explainable to a security review and the second is an argument every time.  The invariant is the reason to build this at all.

## Sequencing

1. Registrar internal routes (`/internal/key`, `/internal/rotate`) with their own token, separate from the MCP service token, each re-checking the roster independently.  Testable with no browser machinery in existence.
2. The team-info reader for pool remaining, and `just key-audit`.
3. `mailroom.{ALMANAC_DOMAIN}` in the Caddyfile; the `oauth2-proxy` and `mailroom` services; one Keycloak client.
4. The rotation-floor ruling, then the Rotate button.
5. Cut over `my_key()` and `rotate_my_key()` to link-only, update the rendered agent instructions, and fix the vestibule refusal text.

**Do not do 5 before 3.**  Changing the tools first leaves a window with no retrieval path at all.  The tools and the docs cut over in the same release that exposes the mailroom.

## Open, unruled

- What `REGISTRAR_MIN_FUSE` should actually be.  Needs one measured session, not a judgement call.
- Whether the open commons has a roster, and therefore whether it has keys.
- Whether a course-linked project mints its own key or rides the parent course's ([rooms-and-visibility.md](rooms-and-visibility.md) puts it inside the parent's instance; it does not say whose key).
- Flat course pool vs. base-plus-per-student.  Institutional, and named here only so the two components are on record.
- Whether the inbound drop (Decision 20) ships at the same window, and whether that changes the identity requirements for pickup.
