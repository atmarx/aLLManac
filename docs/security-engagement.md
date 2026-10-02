---
title: What should a student team try to break first?
description: A reusable engagement brief for a student blue/purple team probing the aLLManac — rules of engagement first, then the boundaries the platform claims to hold, what would disprove each one, and what a finding has to contain to be worth acting on.
audience: builder
also_reaches: [operator]
status: draft
owner: geordi
tags: [access-control, rbac, least-privilege, oidc, identity-broker, secrets-management, escrow, egress-control, allowlist, audit-logging, tenancy, isolation, chokepoint, gateway, supply-chain, attribution, metering, rendered-config, hallucination, critical-evaluation, accountability]
tethered_to:
  - compose.yml
  - caddy/Caddyfile
  - registrar/server.py
  - registrar/render.py
  - registrar/planes/courses.py
  - registrar/planes/config.py
  - usage-mcp/server.py
  - librechat/librechat.yaml
  - docs/design-walls.md
  - docs/agent-contract.md
---

# Security engagement — a student team, a real platform, and the boundaries it claims

**Engagement 001.**  This document is the brief, not the authorization.  Nobody tests anything until an operator has signed and dated a scope letter naming this engagement, the window, and the deployment — see [Rules of engagement](#rules-of-engagement).

This is a teaching exercise that happens to be real.  The platform is running, the operator owns it, and the findings change the code.  That combination is rare and it is the whole point: you are not attacking a deliberately vulnerable VM built to be beaten, you are attacking something someone believes is correct.

**The skill being taught is not tooling.**  It is the ability to read a claim about a system, work out what would have to be true for that claim to hold, and then go and check.  Every section below is shaped that way — a boundary, what would disprove it, and what a finding looks like.  If you finish the engagement able to do that to a system nobody briefed you on, the exercise worked.

---

## Rules of engagement

Read this section twice.  Everything else is optional; this is not.

### Authorization

Testing is authorized **only** against the deployment named in your signed scope letter, **only** within the window it names, and **only** by the people it names.  No scope letter, no testing.

The platform is open source and you may stand up your own copy — `just setup && just up` — and that copy is yours to destroy.  **Do that first.**  Most of what is worth learning here can be learned against your own instance, and a finding reproduced on your own box before you touch the shared one is a better finding, because you understood it rather than tripped over it.

### Out of bounds — no exceptions

- **No denial of service, load testing, or resource exhaustion** against shared infrastructure.  Other people's coursework runs on it.  If you believe you have found a resource-exhaustion path, **describe it and stop** — a written argument that a limit is missing is worth full credit, and proving it by taking the box down is worth none.
- **No third-party services.**  The identity broker may front an external provider; model inference may route off-box.  Those are not yours and not in scope, ever, regardless of what the platform makes reachable.
- **No real student data.**  If you encounter a real person's conversation, roster entry, or file, stop reading it immediately, do not copy it, and report that you reached it.  *Reaching* it is the finding.  Reading further is the offence.
- **No persistence.**  No backdoors, no added accounts, no scheduled jobs, no modified images, nothing left behind.  Anything you change, you change back and say so.
- **No pivoting off-platform.**  The host, the campus network, and anything reachable from the box that is not the platform are out of scope even if the platform hands you a route to them.  Finding that route is an excellent finding.  Following it is the end of the engagement.
- **No social engineering** of staff, faculty, or other students.  The system is the target, not people.
- **No credential reuse.**  A credential you recover during the engagement is used only to demonstrate the boundary it crosses, once, and is then reported.  It is never used to reach something else.

### The stop condition

**Stop and report immediately, before doing anything else, if you:**

- reach another person's data, key, or conversation;
- obtain administrative control of anything;
- find a path off the platform;
- break something, or suspect you have;
- are unsure whether what you are about to do is in scope.

"I stopped and asked" is never the wrong call, and it is not a mark against the team.  The instinct to escalate a finding until it is undeniable is exactly the instinct this rule exists to interrupt.

### Timeboxing

Engagements are timeboxed, and the box is in your scope letter.  When it expires, testing stops even if you are mid-thread — write up what you have.  An unfinished thread, documented honestly as unfinished, is a legitimate deliverable and often the most useful one.

### Coordinated disclosure

Findings go to the named operator contact in your scope letter, and **nowhere else**, until the operator says otherwise.  Not a public repository issue, not a class channel, not a conference talk, not a screenshot in a group chat.

The repository is public.  A finding filed publicly before it is fixed is a live exploit published against a running system with other people's work in it.

The operator commits to acknowledging a report, telling you whether it is being fixed, and crediting the team when the fix ships.  If a finding turns out to affect the upstream projects rather than this platform, the operator handles that disclosure — you will be credited there too, but you do not file it yourself.

### Point of contact

Your scope letter names one person, one address, and one out-of-hours path.  If the brief you were handed does not name them, you do not have a scope letter — you have a draft.

---

## What you should be able to do afterwards

1. **Read a system's own claims and turn them into tests.**  Every section below models this; by the end you should be generating the tests yourself from a README you have never seen.
2. **Tell a boundary from a speed bump.**  Some controls do real work and some are decoration.  You should be able to say which is which and defend it.
3. **Reason about a trust model.**  Who believes what, on whose word, and what happens when that word is wrong.
4. **Distinguish a vulnerability from a defect.**  Not everything that is broken is exploitable, and not everything exploitable is broken.  Both are worth reporting; conflating them wastes everyone's time.
5. **Attack an LLM-mediated system specifically** — where the interesting failures are not memory corruption but *authority confusion*: text that arrives as data being acted on as instruction.
6. **Write a report someone can act on** without you in the room.
7. **Stop.**  Knowing when you have proved enough is a professional skill and it is assessed.

---

## Orientation

Read these before you start, in this order:

- **[README.md](../README.md)** — the architecture, the seven parts, how a request flows.
- **[docs/design-walls.md](design-walls.md)** — what is already known, and *why*.  See [Already known](#already-known--do-not-spend-your-time-here).
- **[docs/registrar-spec.md](registrar-spec.md)** — the provisioning model and the trust model it assumes.
- **[docs/agent-contract.md](agent-contract.md)** — what the guide agents are told, and the two failure patterns already observed.

The shape in one paragraph: **one shared control plane, one chat instance per course.**  Identity is Keycloak.  The gateway (LiteLLM) is the only route to a model and the only place spend is metered.  The registrar provisions courses and holds the credentials that mint things.  OpenBao escrows keys.  Caddy is the edge.  Everything else hangs off those.

**The single most useful orientation question:** for each of those parts, what is shared between courses and what is per-course?  Work that out from `compose.yml` and `registrar/render.py` before you read the target areas below, and you will have found half of them yourself.

---

## Already known — do not spend your time here

[docs/design-walls.md](design-walls.md) is a catalogue of questions already answered the expensive way.  Re-deriving one earns nothing.

It also contains, stated plainly, several places where the platform knows it is weak — including gaps that are open right now.  **Those are not free findings.**  A report that restates a wall is a reading comprehension exercise.  A report that takes a wall and demonstrates a *consequence* the wall does not mention is a real finding, and the walls are written to invite exactly that.

Two of them are worth reading as invitations rather than as closed doors:

- The `actions.allowedDomains` section documents a control whose empty default permits the entire internet, and a rule syntax that fails *open* in a way the person writing it would not expect.  The wall says what the control does.  It does not say what a course could do with it.
- The tenancy section documents a header the pinned image trusts and the edge now strips, and says in as many words that **the edge is not the only door.**  That sentence is a target area, not a disclaimer.

---

## Target areas

Organized by **boundary**, because that is the concept being taught.  Each one states what the platform claims, what would disprove it, and what a finding looks like.

Where a section asks a question rather than stating a fact, that is deliberate: the answer is either something you should establish yourself, or something the operator is not going to publish in a public repository.  **Assume nothing below is complete.**

### 1. Identity — the front door

**The claim.**  Keycloak authenticates; the chat trusts the OIDC result and nothing else.  Faculty become chat administrators via a realm role read from `realm_access.roles`, on a token of kind `access` — all three have to line up ([design-walls.md](design-walls.md), "The classroom posture is opt-in").

**What would disprove it.**  Holding a session as someone you are not.  Holding administrative rights without the role.  Retaining access after the roster says you should not have it.

**Ask:**

- Enrollment gates login via a client role.  When enrollment is revoked, what happens to a session that is *already open*?  Is authorization re-checked per request, per token refresh, or only at login?  What is the longest window between "removed from the roster" and "cannot use the platform," and who would notice?
- Which parts of the token are asserted by the identity provider and which are influenced by anything the user controls — profile fields, display names, self-service registration if it is on?
- Is signing out of the application the same as signing out of the identity provider?  What does the back button do?
- If the deployment brokers an external identity provider, what does the broker assert about an account that the external provider does not?  Account linking on a matching email address is a classic seam; is it on?

**A finding looks like:** a sequence of requests, from a named starting state, ending in a capability the starting state should not have had.  Include the timeline if timing is the mechanism.

### 2. The gateway — the spend chokepoint

**The claim.**  Every request to a model goes through the gateway; every request is attributed to a person and charged to a pool; a key cannot spend past its budget or outside its model list.  Chat spend and API-key spend drain the *same* course pool.

This is the most important claim on the platform, because the budget model is the only thing standing between a course and an unbounded bill.

**What would disprove it.**  Spending that is attributed to nobody.  Spending attributed to somebody else.  Spending past a stated cap.  Reaching a model that was not granted.

**Ask:**

- Per-user attribution rides a request header set in the instance's rendered configuration (`registrar/render.py`, the `x-litellm-end-user-id` line).  What happens when a client sets that header *as well*?  Which value wins, and does the gateway have any way to tell the difference?
- Take the list of published ports in `compose.yml` and ask, for each one: does this service answer on an interface that never meets the edge, and what does the edge do for it that would be lost?  This is a two-minute exercise and it is the highest-yield one in this document.
- A key states a budget.  Does it match what the key can actually spend?  Construct the case where the number on the key and the money behind it disagree — and note which direction the disagreement runs, because they have very different consequences.
- Rotation is documented as carrying the remaining budget forward rather than resetting it.  Test that.  Then test it at the boundaries: at exhaustion, at zero, and repeatedly.
- A key is scoped to a model list.  Is the scope enforced at the gateway, or only reflected in what the UI offers?
- Does anything in the platform talk to the gateway with a credential broader than it needs?  Enumerate what would happen if each such credential leaked.

**A finding looks like:** a request that succeeded, the spend row it produced (or did not), and a statement of which of the four claims above it breaks.  **Keep the volume trivial** — one request proves a metering failure exactly as well as ten thousand, and ten thousand is a denial-of-service finding you were told not to produce.

### 3. The registrar — the trust model

**The claim**, from the module's own docstring (`registrar/server.py:10-17`): reachable only on the compose network plus a loopback bind; the chat proves itself with a bearer token; the course identity comes from configuration the registrar itself rendered and students cannot touch; the roster file is the authorization for everything an instructor does.

**What would disprove it.**  Reaching it from somewhere it says it cannot be reached from.  Making it believe an identity you asserted.  Acting on a course you are not staff of.

**Ask:**

- Identity arrives as headers, trusted because a shared bearer token vouches for the sender (`_ident()`, `registrar/server.py:41`).  Enumerate every place that token exists, at rest and in transit.  What is the blast radius if one of them leaks?  This is stated openly in the repo; the exercise is working out the *consequences*, which are not.
- The course comes from a rendered literal.  Trace the full path from "operator types a slug" to "that string is in a running config."  How many places is it validated, and is it validated on *every* path that writes it, or only on the one an operator normally uses?
- Roster changes are two-phase: stage, then apply with an identifier.  What does a stage bind to — the course, the person who created it, both?  Construct the case where that distinction matters.
- The roster parser is deliberately liberal, extracting email-shaped tokens from anything pasted (`registrar/server.py:107-119`).  Liberal parsers are where surprises live.  What does it do with a very large paste?  With addresses that are valid by the pattern but not by any sane reading?  With the same address in several forms?
- Staged plans live in memory with a time-to-live.  What happens at the boundary — at expiry, across a restart, with a stale identifier, with an identifier from a different course?

**A finding looks like:** the exact request, the identity the registrar believed, the identity you actually had, and what changed as a result.

### 4. The tool surface — where text becomes authority

**The claim.**  Tools enforce authorization server-side, from trusted headers, never from tool arguments.  The guide agents are additionally steered by a system prompt ([docs/agent-contract.md](agent-contract.md)).

**These are two different boundaries and telling them apart is the entire lesson.**  A prompt is a hope with a track record.  A server-side authorization check is a wall.  A failure at the prompt layer that the tool layer catches anyway is a *quality* finding.  A failure the tool layer does not catch is a *security* finding.  Label yours correctly and say why.

**What would disprove it.**  A tool acting beyond the caller's authority.  Content that arrives as data being executed as instruction.

**Ask:**

- Two failure patterns are already named in [agent-contract.md](agent-contract.md): **the fabrication** (inventing a procedure and delivering it in the same voice as the truth) and **the pretext** (wrapping an off-topic request inside an on-topic one).  Both were found by using the thing.  **Find a third.**  A new named pattern, with a reproduction and a proposed eval case, is the highest-value deliverable in this engagement.
- Indirect injection is the richer seam.  The models read text that other people wrote — knowledge files, pasted rosters, uploaded documents, tool output, retrieved chunks.  Can text that arrives as *data* be read as *instruction*?  What is the longest path you can build between "someone else put this somewhere" and "the model acted on it"?
- The over-refusal cases in `agent-contract.md` (R1-R3) exist because an over-tightened scope rule is a real failure too.  A guide that refuses legitimate questions is a finding and should be reported as one.
- Retrieval is shared where the chat is not.  Work out which stores are per-course and which are not, then ask what could cross.
- The usage tools scope answers by a roster file (`usage-mcp/server.py`).  What happens when the roster and the gateway's own records disagree about who someone is?

**A finding looks like:** the exact input, the output, and a clear statement of which layer failed — prompt or authorization — and what the other layer did about it.

### 5. Instance isolation — the fleet

**The claim.**  One chat instance per course, so an instructor administers their own course and nobody else's.  A shared control plane sits underneath.

**What would disprove it.**  Seeing another course's data.  Changing another course's configuration.  Administrative rights on an instance you are not staff of.

**Ask:**

- Build the inventory first: for every store in `compose.yml` and `registrar/render.py`, is it per-course or shared?  Some are separate processes, some are separate logical databases inside one process, and **at least one is shared outright**.  Find which is which before forming a hypothesis — the answer is in the repo and it is the whole section.
- For each shared thing, ask what it holds and what would identify a tenant inside it.  If the answer is "nothing does," that is the finding.
- Each course carries its own management panel.  What can it change, does that change stay inside the course, and what is it authenticated by?
- The fleet is generated from templates.  If two courses can influence the same generated artifact, what happens on the next render?
- Course rollover and teardown: what survives a course ending, and who can still reach it?

**A finding looks like:** data or control from course A, reached from course B, with the path.  **Reaching it is the finding — stop there**, per the stop condition.

### 6. The escrow — where keys live

**The claim.**  OpenBao is the only durable store of a plaintext key; the registrar is the only component holding the credential that reads it; a key never reaches a model-visible channel.

That last clause is currently **aspirational, and openly so** — [docs/mailroom.md](mailroom.md) documents the gap and proposes the fix.  Testing it is still worthwhile, because the interesting question is not "is there a gap" but "how many surfaces does one key actually reach?"

**What would disprove it.**  A plaintext key anywhere else.  Reading a key that is not yours.

**Ask:**

- Run the enumeration: mint a key in a test course and find **every** surface it lands on — logs, databases, search indexes, rendered files, configuration, environment, backups, browser storage, model-provider requests.  Predict the list first, then check, then compare.  The gap between your prediction and reality is the lesson.
- A mint and an escrow write are two operations.  What is the state of the world between them, and can you produce it?  ([design-walls.md](design-walls.md) documents this window as permanently open — the exercise is producing one and proposing how it would be *detected*, since it cannot be prevented.)
- Which components can read which escrow paths?  Is any credential broader than the thing holding it needs?
- What is recoverable after a key is revoked, and by whom?

**A finding looks like:** a named surface, how you reached it, and what authorization was required to get there.  **Report the key as compromised; do not use it.**

### 7. The edge

**The claim.**  Caddy terminates TLS, fronts each surface on its own hostname, and strips at least one header the backend would otherwise trust (`caddy/Caddyfile`).

**What would disprove it.**  Reaching a backend without meeting the edge.  Getting a stripped header through.  Getting a hostname to serve something it should not.

**Ask:**

- Which services can be reached without going through Caddy?  `compose.yml` answers this and the answer is not "none."  For each, what protection is lost?
- The strip is applied per site block, and course vhosts are generated.  Is the generated form identical to the hand-written one?  Would anyone notice if a future template dropped it?
- Certificate behaviour under failure is documented in [docs/tls.md](tls.md) and it does not fail closed.  What is observable from outside about a deployment in that state?
- What does the edge do with a request for a hostname it does not recognize?

### 8. Rendered configuration

**The claim.**  Generated files are rendered from validated inputs and written atomically.

This is a real injection surface and it is the one most like classic application security: operator-controlled values flow into files that are then interpreted by other software — a web server config, a compose file, a chat configuration.

**What would disprove it.**  Any input that changes the *structure* of a generated file rather than filling a slot in it.

**Ask:**

- Enumerate every field that reaches a rendered artifact.  For each: what validates it, where, and is that validation on the path the roster tools use as well as the path the operator CLI uses?
- The slug is validated against a strict pattern (`registrar/planes/config.py:67`, enforced at `registrar/planes/courses.py:180`).  What about the other fields that reach the same files?
- Validation that runs in a pre-flight check protects the callers that run the pre-flight check.  Which callers are those?
- A generated file says it is generated.  What happens if someone edits one anyway — is it detected, or silently overwritten, and does either answer create a window?

**A finding looks like:** an input value, the generated file it changed the shape of, and what that file's consumer then did.

### 9. Supply chain

**The claim.**  Images are pinned deliberately, because a floating tag means behaviour can change on a rebuild nobody thought was a change (`caddy/Dockerfile` says exactly this).

**Ask:**

- Go through every image reference in the repository.  Which are pinned by content digest, and which by a tag that could be re-pointed?  They are not all the same and the difference is the finding.
- Which images are built locally, and from what base?
- What would it take for a dependency of a *built* image to change without any file in the repository changing?
- What is the platform's story for finding out that a pinned image has a published vulnerability?  If there is not one, say so — a missing process is a legitimate finding.

---

## What counts as a finding

A finding is **a boundary crossed, or a boundary that cannot be shown to hold.**

That second half matters.  "I could not break this, and here is the set of things I tried" is a real contribution, especially with a clear statement of what you could *not* test and why.  Negative results are only worthless when they are vague.

Severity, in the terms that matter here rather than a borrowed corporate scale:

| Severity | Means |
|---|---|
| **Critical** | Another person's data, keys, or conversations; or administrative control of the platform. |
| **High** | Acting as someone else, spending outside attribution, or crossing the course boundary. |
| **Medium** | A control that does not do what it claims, where something else happens to catch it. |
| **Low** | A defect with no clear path to abuse, or an error that reveals more than it should. |
| **Quality** | Over-refusal, misleading errors, guidance that sends someone the wrong way.  **Not lesser** — a misleading error message costs real hours and this platform has a stated position on that. |

An **assumption you disproved** is its own category and is graded highly.  This document, the walls, and the specifications are full of claims.  Any of them may be wrong.  Showing that one is — with evidence — is worth more than a finding, because it corrects the map everyone else is navigating by.

### Report template

One file per finding.

```text
TITLE        One sentence.  The boundary, and that it was crossed.

SEVERITY     Critical | High | Medium | Low | Quality
             Plus one sentence of argument.  Argue it down if that is honest.

BOUNDARY     Which claim this breaks, quoted, with where you found it stated.
             If nothing states it, say that — an unstated boundary is a
             finding about the documentation.

PRECONDITION What access did you start from?  Anonymous?  Enrolled student?
             Staff on a different course?  Be exact.  A finding that requires
             administrator access is a different finding.

REPRODUCTION Numbered steps, from that starting state, that someone who is
             not you can follow.  Exact requests.  Exact responses.  If it
             is timing-dependent or intermittent, say so and say how often.

IMPACT       What can someone actually do with this?  Resist the urge to
             inflate it, and resist the urge to be modest.  Both are wrong
             in the same way.

EVIDENCE     Minimum sufficient.  Redact anything belonging to a real
             person.  If you reached real data, say that you reached it
             and DO NOT attach it.

SCOPE NOTE   What you did not do, and why.  "I stopped here because of the
             stop condition" belongs in every report where it is true.

FIX          Optional, and welcome.  You have read the code.  If you have a
             view on the right fix, say it — including "this is a design
             decision, not a bug, and here is the trade-off."
```

The **SCOPE NOTE** field is not filler.  A report that says where it stopped and why is a report from someone who can be trusted with access again.

---

## After the engagement

Every confirmed finding lands in one of three places, and the team is told which:

1. **A fix**, in the code, in the same commit as the documentation change it forces.
2. **A wall** in [design-walls.md](design-walls.md), when the answer is "the obvious approach is wrong and here is what it cost to learn."
3. **A named pattern** in [agent-contract.md](agent-contract.md) with an eval case, when it is a model-behaviour failure.

Findings that are *not* fixed get written down anyway, with the reason.  An accepted risk that nobody recorded is an accepted risk nobody will remember accepting.

**This is engagement 001.**  Later engagements should assume the boundaries here have moved, and should start by asking which of the questions above now have different answers — including the ones a previous team was confident about.
