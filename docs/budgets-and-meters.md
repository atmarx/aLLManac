---
title: What is the meter for, and who is allowed to say the number?
description: A proposed rule for what a student sees of their own budget, where they see it, and what happens when they run out — grounded in what LibreChat's balance code actually does at our pin.
audience: operator
also_reaches: [faculty, builder]
status: proposed
owner: marco
tags: [metering, attribution, gateway, equity, accountability, ai-literacy, litellm, librechat, mongodb]
tethered_to:
  - usage-mcp/server.py
  - registrar/planes/gateway.py
  - registrar/courses.example.yaml
---

# Budgets and meters — what the number is for, and who is allowed to say it

**Status: proposed, 2026-09-10.**  Not ruled.  The budget layers described here already exist (`course` as the hard term cap, `key_fuse` as per-key blast radius, `advisory_weekly` as pacing that never blocks — stored and validated, but nothing reads it yet — see [registrar-spec.md](registrar-spec.md)); what is proposed is a rule for *what a student sees*, where they see it, and what happens when they run out.  Everything under [What the pin actually does](#what-the-pin-actually-does) is verified against `ghcr.io/danny-avila/librechat:v0.8.7` and is fact, not proposal.

!!! info "Ruled 2026-09-22 (@xram) — what happens when a student runs out.  Not built."
    **Chat runs in audit mode.**  There is no global per-student limit, and nobody sees an "over quota" error.  A student over their share *of one course* is redirected to the institution's general assistant on every request until the accounting clears them.  The per-course service key stays: it is what makes the per-student numbers attributable.

    **The redirect is a canned reply at the gateway, not a system-prompt instruction.**  A LiteLLM pre-call hook checks the registrar's over-quota list and answers through `mock_response`, so the request never reaches a model — it costs $0, it reads the same every time, and it can't be argued with.  A system-prompt version fails twice over, on grounds this repo already measured: front-trimming drops the instruction on exactly the long threads heavy users have ([design-walls.md](design-walls.md), "A context window larger than the endpoint serves deletes the system prompt"), and a student who wants past it is running the injection case the guides already fail.

    **API keys keep hard fuses.**  A script can't be redirected — it retries — so a budget error is the honest answer to a program.  The course cap stays as a high circuit breaker against bugs, not as policy.

    The advisory-pool proposal of 2026-09-22 is **withdrawn**.  It assumed dropping the team's `max_budget` made chat advisory; the service key carries the course number as its own ceiling, so it didn't ([design-walls.md](design-walls.md), "A key carries what it was born with").  First build step is the rig: a mocked reply streaming through LibreChat, and what the ledger records for it.

---

## The rule

**The meter exists to make cost intuition acquirable.  Metering is the side effect.**

That inverts how we have been describing `usage-mcp`, and it changes what "good" looks like.  A tool that bills accurately and teaches nothing has failed at its job; a tool that teaches well and is approximately right has succeeded.

A second rule falls out of the first, and it is the one with engineering consequences:

**An ambient number must be deterministic and free.  A conversational number may cost tokens, because you asked for it.**

## Why a meter at all

Three arguments, none of them "because we have to bill someone."

**The commons problem.**  Every individual query is negligible and the aggregate is not; the reasoning that produces the harm is individually valid at every step.  The usual objection to pricing as a response is that the information isn't available and providers don't charge that way — but inside our own boundary we *are* the provider, we *do* have the number, and the equity objection has an answer (see [Running out](#running-out)).  We are unusually well placed to run the one response to this problem that doesn't require political will.

**The toll is unknowable in advance.**  You cannot know what a question will cost until you have already asked it.  The rabbit hole does not publish its depth.  This means all the decision-making happens under maximum uncertainty and all the information arrives after the decision is irreversible — which makes quota anxiety *correct reasoning*, not neurosis.  The remedy for correct reasoning under uncertainty is never reassurance.  It is information.

**Cost intuition is a real skill and it is nearly unteachable.**  You acquire it empirically — ask, watch the meter, adjust — but the feedback is delayed and the mechanism is invisible, which is exactly the pair of properties our tool is in a position to change.  This is the whole justification for the meter: not that students should spend less, but that they should be able to *tell* what things cost, which they currently cannot.

Norms are the other half.  The standard objection to norms as a response is that they can't form around distributed, private behavior — and a course is precisely the setting that isn't.  Bounded cohort, shared instructor, one term, everyone looking at the same instrument.  If norms of appropriate use can form anywhere, it is there.

## What we cannot measure

**We hold a denominator and no numerator.**  We can say what a query cost.  We can never say what it was worth.

Judging value at scale would mean pushing every exchange through a second model — and the disqualifying objection is not the expense, it is that scoring transcripts means *reading* transcripts, which is the surveillance the commons exists to prevent.  A free, perfect judge would still be refused.  It would also be wrong on the merits: in coursework the relation between efficiency and value is frequently inverted, and a judge scoring "was this answered efficiently" would systematically mark down productive struggle, which is what the assignment was for.

Three rules follow, and they bind the tool's output, not just its policy:

- **"Efficient" is a word the tool may never use.**  Not in a label, not in output, not implied by an ordering.  `usage-mcp` reports what was spent and never what it was worth.
- **No leaderboards.**  A list of students ranked by spend invites two readings — high as overuse, low as disengagement — and both are unsupported.  The course-level view lists each student alphabetically, never by spend, with dollars only as a course total — "who hasn't started yet?" needs names, and an order that isn't a ranking answers it without answering the question it cannot.
- **Budgets can never be merit-based.**  There is no measurement to hang it on, and the first person to try will reach for spend as the proxy, which measures the opposite of what they think.

What survives is description.  *"Your questions range from 300 to 12,000 tokens."*  *"Your 90th percentile is 12× your median."*  *"This exchange cost more than your last twenty."*  All true, all useful for building the intuition, none of them a claim about anybody's worth.  **The tool describes; it never scores.**

## Two surfaces, two rooms

The ambient/conversational split is not a choice between designs.  It is a map.

| Where | What the question is | Instrument |
|---|---|---|
| **Inside a room** (`course`, `office`) | one allocation, one number | ambient, deterministic, free — LibreChat's balance display, written from LiteLLM |
| **The vestibule** | N allocations across N rooms — a table, not a number | `usage-mcp`, asked conversationally, paying tokens in proportion to the question |

A student in three courses plus a project has four allocations and no single honest figure.  The vestibule is where that reckoning belongs, and it is the one place where the model paraphrasing the answer is acceptable — because you asked a question with many rows, not because we routed *the* number through a language model.

**The number must never come from the LLM in a room.**  Routing it through the model means the meter consumes the resource it measures, fires only when the model decides to call the tool, and can misreport the figure.  For a number whose entire job is to be trusted and free, that is the wrong instrument.

**LiteLLM is the sole authority, and this is structural, not risk management.**  A student can burn course quota through a coding harness on their virtual key, producing zero chat completions.  LibreChat's own accounting is therefore not approximately wrong — it is blind to an entire spend channel.

## What the pin actually does

Verified in `ghcr.io/danny-avila/librechat:v0.8.7`.

**The balance is externally writable and survives.**  `updateBalance` (`packages/data-schemas/src/methods/transaction.ts:205-292`) is a compare-and-swap `$set` of an absolute value read fresh — not `$inc`, and **not derived from the Transaction ledger**.  Nothing in the image ever rebuilds the balance from transactions; the ledger is append-only and read only by the assistants pre-flight check.  An externally written value is never recomputed away.

**There is no read-only mode.**  `balance.enabled` is one boolean gating enforcement *and* the debit, checked in four places.  `transactions.enabled: false` does not help — it is force-flipped back on when balance is enabled (`packages/api/src/app/config.ts:43-49`).

**`endpointTokenConfig` is the lever.**  Per-model `{prompt, completion, write, read}` rates on the endpoint config short-circuit all pricing.  Setting them to `0` makes `tokenValue` always zero, so `updateBalance` becomes a no-op — which is the correct configuration for us, since LibreChat cannot see all our spend.  It also zeroes LibreChat's own cutoff, which is fine: the LiteLLM team budget is the real cap.

**Hazard — the unmatched-model default.**  `getMultiplier` matches on `modelName.includes(key)` and falls back to `defaultRate = 6` — $6 per million, both directions — when nothing matches (`packages/data-schemas/src/methods/tx.ts:29`).  Our aliases (`almanac-chat`, `almanac-office`) match nothing in that table.  **Enabling `balance` without `endpointTokenConfig` silently prices every model at roughly 7.5× Claude's prompt rate**, with plausible-looking figures and no warning.

**The write door is Mongo, and the key is not the email.**  Collection `balances`; `balances.user` is the LibreChat user document's `ObjectId` (`packages/data-schemas/src/schema/balance.ts`).  There is no HTTP write path — every admin route was checked.  So a sync job must resolve email → `_id` against each instance's `users` collection, which means **the registrar becomes a writer into LibreChat's private database.**  That is not a fork, but it is the same class of risk: coupling to an internal detail with no API contract, in a system we pin so upgrades stay boring.  The config-sync middleware will not stomp us — with `autoRefillEnabled: false` it writes nothing to an existing row.

**Freshness is already solved.**  `useGetUserBalance` sets `refetchOnMount/Focus/Reconnect: true` (deliberately — the sibling banner query sets all three false), and both SSE hooks call `balanceQuery.refetch()` on every `final` and every `error` (`client/src/hooks/SSE/useResumableSSE.ts:556, 842`).  Any consumer of that hook is current within one turn, for free.

**The number already renders one click away.**  `client/src/components/Nav/AccountSettings.tsx:148-156` puts it in the account dropdown as `Balance: {Intl.NumberFormat().format(Math.round(tokenCredits))}` — note the `Math.round`, so the peg must put typical usage well above 1.  The settings row (`SettingsTabs/Balance/TokenCreditsItem.tsx:22`) uses `toFixed(2)`.  Nowhere else.

**A per-turn cost widget already exists in the composer.**  `Chat/Input/TokenUsage/`, mounted at `ChatForm.tsx:394`, gated on `interface.contextUsage` (default **true**) and `interface.contextCost` (default **false**), with an `interface.currency {code, rate}`.  It shows *conversation context* cost, not balance, and it prices off LibreChat's own table — so the `defaultRate` hazard applies and the figure should not be trusted until someone verifies whether `costKnown` declines to render an unmatched model.

**Banner is not an option for anything per-user.**  `getBanner` is a bare `findOne` with no user scoping — one banner per instance.  A course-level aggregate is the wrong number anyway: it turns a shared allocation into a race.

## The unit

**Upstream already had this argument and shipped an answer: 1 `tokenCredit` = 1 micro-dollar** (USD × 10⁻⁶), confirmed three ways in the image.  The stock `startBalance: 20000` is two cents.  It is an SU — an abstract unit pegged to a fixed fraction of a dollar — which is what we were reaching for.

Two things settle the rest of the debate:

**The HPC convention does not transfer on its own terms.**  An SU is honest there because no defensible dollar figure exists for a node-hour; the SU is the truth and dollars would be the fiction.  Here LiteLLM computes a real dollar from real list prices, so an SU pegged at a penny is a pure relabeling — dollars in a costume, which is exactly what reads as hiding.  An SU pegged to *compute* would be a different and better argument, because price does not track footprint: a vendor price cut moves the dollar and not one joule, and house metal at `$0` says zero for the compute we are most responsible for.

**But once we zero LibreChat's rates, `tokenCredits` is an opaque integer only we write.**  LibreChat stops interpreting it, so the peg is entirely ours — micro-dollar, cent, or compute-weighted.  The only display constraints are `Math.round` in the dropdown and `toFixed(2)` in settings.

**`interface.currency` cannot carry an invented unit.**  `formatCost` runs the code through `isSupportedCurrency` and falls back to USD at rate 1 if it doesn't recognize it.  Real ISO codes only.

**Whatever the unit, it must have resolution at the low end.**  Cost intuition is built from ratios — this kind of question costs 10× that kind — and `$0.00` versus `$0.01` cannot express a 10× difference.  Upstream's `formatCost` already solves this better than anything we proposed: below a cent it renders `<$0.01` rather than `$0.00`, and between a cent and a dollar it gives four decimals.

**Ruled 2026-09-15: dollars, no SU.**  The real world runs on dollars, so the meter shows them — no invented unit, no costume.  The compute-weighted argument above stays on the record as the one version of an SU that would have meant something; it is not a build.

**Killed the `> 0.005` gate in `usage-mcp/server.py`** *(done 2026-09-15; the spend line now always prints, with `formatCost`'s low-end shape — `<$0.01`, four places under a dollar)*.  The gate rendered nothing until the number stopped being negligible — which is the individual-reasoning trap written into our own code.  It also hides efficiency from the efficient: the narrow, focused student, whose economy is already invisible to them, gets it confirmed that nothing is happening.  The number should be present from message one, small and boring, so it never has a debut.

## Getting it on screen

| Path | Cost | Verdict |
|---|---|---|
| Do nothing | zero | The number is already one click behind the sidebar avatar and already fresh every turn.  If "persistent" is negotiable, this ships today. |
| `interface.contextCost: true` | config only | Persistent, per-turn, in the composer — but it is context cost, not balance, and the `defaultRate` hazard applies. |
| Patch the client | ~40 lines: one component + one line at `ChatForm.tsx:394` | Rides the existing `['balance']` query and the existing per-turn refetch.  Sits in a slot upstream already built.  Survives upgrades as a rebase. |
| Inject at the reverse proxy | a script and a standing worry | Genuinely viable — no CSP anywhere in the image, `index.html` served `no-store`, and upstream itself does a `</head>` replace for its devtools.  But it guesses at someone else's HTML and fails silently when the guess goes stale.  Unverified risk: the PWA service worker precaching `index.html`. |

The forty-line patch is smaller and less fragile than the proxy hack.  That reverses the reflex that forking is always the expensive option — here it is the cheap one.

## Running out

**The insufficient-funds experience is currently the whole pedagogy, and it is one hardcoded English sentence.**  `client/src/components/Messages/Content/Error.tsx:103-127` renders `Insufficient Funds! Balance: 12345. Prompt tokens: 800. Cost: 900.` in a red bubble inside the message stream — unlocalized, no toast, no banner, no composer lockout, no mention of the fallback.  A student sends a question and gets that.  Everything else in this document is downstream of that string, and it is one line in the same patch as the display.

**A course budget caps the course's spend, never a student's access.**  This holds wherever the institution already licenses a general-purpose assistant campus-wide at no incremental cost — state the dependency rather than assuming it.  That converts an equity objection into a routing question — but only if the student learns it *before* they hit the wall.  Discovered at the boundary, it reads as a brush-off.

**Honest gap:** the fallback covers *asking* and not *building*.  A student halfway through an agent for Friday cannot finish it in a general chat box.  The running-low message is the only place we would ever know which of the two they were doing.

### Grants, not resets

**A "weekly reset" resets nothing.**  `advisory_weekly` never blocks — it is pacing.  The only thing that stops a student is the course term cap, so what looks like a weekly reset is really a **top-up against the hard cap**, drawn from the course's pool.  Either weekly becomes a soft block and the reset is cheap and mostly symbolic, or the grant costs the course real money.  The design does not compose until that is picked.

**Make it a grant, not a reset.**  Restoring a week is worth nothing on Sunday night and everything on Monday morning, which is a clock to game.  A fixed grant of N units is timing-neutral.

**Self-serve, once per term, unjudged.**  Misjudgment is the *predicted* outcome of an unknowable toll, not a lapse — charging a social cost for a mistake our own opacity guarantees makes students apologize for our design.  Once per term is self-limiting; nobody farms it.

**The grant is the best teaching moment in the system.**  It is the one instant a student has felt, personal evidence about their own consumption and actively cares about the number.  Spend it silently and it teaches nothing; spend it ceremoniously and it shames.  Show them what they spent and where, at the moment they ask for more.

**Faculty control the course allocation, not per-student grants.**  An instructor cannot adjudicate an individual request — that is the missing numerator again, and approval would rest on confidence and relationship, distributing exactly along the lines that make prompting literacy an access problem.  The student who doesn't want to be a bother goes without.  But an instructor *can* judge that an assignment needs more headroom than they budgeted, because they know the assignment.  Put their lever one level up.

**Do not adjudicate — measure.**  Grant freely and count the grants.  A high grant rate in a course means **the course budget was sized wrong**, and the fix is next term's number, not a queue of exceptions.  Faculty cannot predict usage distributions because curiosity has different depth profiles; grants are how we learn the distribution instead of guessing at it again.

### Two things the copy must carry

**The number includes spend the chat never saw.**  A student running a harness against their key can open the vestibule and find a balance their entire visible chat history cannot explain.  Unstated, that is not a surprise — it is a bug report, or a suspicion that we are charging them for something they didn't do.  Every readout says what it counts.

**Weekly and term are different kinds of number.**  Advisory pace never blocks; the term cap does.  Rendered as two similar figures in one table, a student will treat the one that cannot stop them as a wall, or the one that can as a suggestion.

A related consequence worth stating on every key page: **a LiteLLM key belongs to one team, so a student in three courses has three keys.**  "My API key" is already not a thing — it is "my key for this course."  If that isn't obvious at mint time, harness spend lands in whichever course they happened to copy a key from.

## What this amends

[rooms-and-visibility.md](rooms-and-visibility.md) argues that budgets are not a reason to mint an instance, because attribution happens at the gateway.  That is still true for *attribution*.

But **ambient display is not attribution**, and display is instance-bound in a way attribution is not: the store is the instance's own Mongo.  Instance-per-course therefore gives us database-per-course, and a student sitting in a course instance sees that course's allocation and only that — correct scoping for free, out of a decision made for an entirely different reason.

That only holds where instance and room are **1:1**, which is `course` and `office`.  Standalone projects, sandboxes and the commons share one instance, one database, and one balance row per user, with no way to say which of a student's rooms the number refers to.  So: budgets are not a reason to mint an instance; an *ambient budget readout* is one, or you accept its absence.  The rooms note lists the honest costs of sharing and this is not on the list.

The commons is the exception that proves it useful: the resolution there is **number present, countdown absent.**  You can see what you spent; nothing is running out.  Metering chills exploration independently of who is watching, so removing the audience was only half an answer.

## Open, unruled

- Whether weekly becomes a soft block, or the grant is a term-cap top-up.
- The peg, given `Math.round` in the dropdown: micro-dollar, cent, or compute-weighted.
- Whether the registrar may write into LibreChat's private Mongo at all — the coupling, not the mechanism, is the question.
- Whether `interface.contextCost` renders a wrong figure for our aliases, or declines to render one.
- Whether the PWA service worker precaches `index.html` (only matters if the proxy path is chosen).

## For the walls

Two findings here are trap-shaped and belong in [design-walls.md](design-walls.md) once ruled: **`defaultRate = 6` for unmatched model names**, and **`balance.enabled` is a single boolean with no read-only mode**.  Separately for the plumbing lane, not a wall but an exposure: the image ships **no Content-Security-Policy and no `helmet`**, and mounts a bare `cors()` with no origin restriction — which makes what the Caddy edge is doing in front of it critical.
