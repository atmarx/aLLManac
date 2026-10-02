---
title: If you have to sign off on this
description: A brief for the CIO, CISO and Provost — why this was built instead of bought, what it does that a licensed product does not, what makes it defensible in front of students, what it will cost to run, and where it is currently weak.
audience: operator
also_reaches: [faculty, builder]
status: draft
owner: piper
tags: [tenancy, isolation, access-control, sso, oidc, gateway, chokepoint, metering, attribution, retention, backup, disaster-recovery, ferpa, state-privacy-law, egress-control, supply-chain, accountability, transparency-notice, student-right]
regimes: [ferpa, gdpr]
tethered_to:
  - README.md
  - docs/design-walls.md
  - docs/registrar-spec.md
  - docs/budgets-and-meters.md
  - apex/your-data/how-long-we-keep-it.md
  - apex/how-we-built-it/keeping-courses-apart.md
---

# If you have to sign off on this

A professor uploads a syllabus and a reading list, writes a paragraph of instructions, and forty minutes later the class has an assistant that has read the course material.  Every question it answers is metered against that course's budget, attributed to the student who asked it, and stored in a database that belongs to that course and no other.

That is the product.  Everything below is about what it took to make that sentence true, and what is still not true about it.

Three people sign different parts of the same form.  The CIO inherits the operational load, the CISO inherits the risk, and the Provost inherits the academic consequences.  What works and what is not built yet get the same flat tone below, since a brief that only contains the first kind is a sales document, and you have read enough of those to discount them.

---

## Why build it instead of licensing a product

**We did not build this instead of anything.**  A campus-wide general-purpose assistant and this platform solve different problems, and the design assumes both exist — the ruled design sends a student who has used up their share of a course to the licensed assistant the institution already pays for.  That redirect is not built yet; today a spent course budget is a hard stop.  If you are weighing this as a replacement for that, the comparison is wrong in a way that will produce a bad decision.

What a licensed product does not sell, at any tier, is the thing a *course* needs:

**An allocation with a boundary around it.**  Seat licensing charges for enrollment; courses consume by assignment.  A seminar of twelve running a research-methods unit can consume more than a lecture of two hundred that touches the tool twice.  Per-seat pricing gets that backwards in both directions, and no tier corrects it — the unit being sold is the person, and what a course consumes is work.

**A ledger the institution can read by course.**  Every request on this platform passes one gateway, and that gateway is the only route to a model.  There is no second path, no shadow spend, and no vendor dashboard standing between the institution and its own consumption data.  Ask what a course spent this term and the answer comes out of a database you run.

**A group that co-edits one assistant.**  Commercial custom assistants have an author.  Here a project team holds editor rights on a single agent — instructions, attached documents, tools — and maintains it together.  That is the difference between a novelty and a piece of course infrastructure, and it is the first thing we test on a new deployment.

**The ability to change your mind about the model.**  Inference sits behind one interface.  Swapping providers, adding a second, or moving a course onto institutional GPUs is a configuration change.  Nothing migrates.  The alternative is that your AI strategy and one vendor's product roadmap become the same document.

One reason is not commercial at all, and for a Provost it may be the strongest: **the platform is course material.**  Every significant decision in it is written up with the reasoning and the cost — tenancy, key custody, what happens to data nobody can delete.  Students in a systems or security course read the argument and then attack the running system under a signed scope letter.  You cannot buy that.  What is being taught is the reasoning, and a vendor has no incentive to publish theirs.

---

## What it does that the licensed products do not

- **Isolation by structure, with no permission check to forget.**  Each course runs its own chat instance, its own database, its own search index, its own document store.  No course's conversations, agents or files share a table with another's, which means the chat software has no query that could cross one and no check anybody can forget to write.  The usage ledger, the identity system and the platform's own records are shared by design, and so is the database server underneath every course.  The full argument, including what each shared piece costs, is in [How do you keep the courses apart?](how-we-built-it/keeping-courses-apart.md).
- **Students get a key as well as a chat box.**  A student can point their own editor, scripts, or coding harness at the campus gateway with a personal key, metered the same way.  That is how the tool follows them into the work they are graded on.
- **The meter is a teaching instrument.**  Cost intuition — knowing roughly what a question costs before you ask it — is a real professional skill, currently unteachable because the feedback is invisible and delayed.  We show the number, list it alphabetically, never by who used the most, and refuse to score anyone on it.  There are no leaderboards, and budgets can never be merit-based.  We hold a denominator and no numerator: we can say what a query cost, never what it was worth.
- **Assistants that decline.**  The guides here are instructed to answer from their attached documents and to say so when something is not in their files.  We test that behavior with a scripted evaluation suite and treat a wrong-but-confident answer as a defect to fix.
- **The failures are published.**  [If you're evaluating this for your course](evaluating-it.md) has a list of what is broken, under "What we already know", and the platform's largest self-inflicted outage is [written up in full](how-we-built-it/keeping-courses-apart.md).

---

## Chat and keys are limited by different things

Most people assume one rule covers both.  It doesn't, and the mistake runs in the direction that costs money.

The chat window is capped in length.  A conversation may grow to a set size — a few hundred pages of text — and past that the software drops the oldest part before sending the rest.  We choose that number per course.  It looks like a capability limit.  It is a cost control: a bound on what one conversation can spend against a metered model.

A personal key is capped in money.  When a student points their own editor or scripts at the gateway, that traffic never passes through the chat software at all, so the length cap does not apply — the request gets whatever the model itself serves.  What stops it is the dollar fuse on the key.

**Chat is bounded per conversation in tokens; keys are bounded per key in dollars.**  Both also draw on the course's pool, which is a dollar ceiling over everything.  The practical consequence is that a student in the chat window gets trimmed while the same student with a harness can send an enormous request and pay for it.  On a priced model, the fuse stops them when the key's dollars run out.  On a campus model with no price, the fuse never moves, and the only bound is the student's own judgement and the model's own window.

The asymmetry is by design, and it is the thing most likely to be taught wrong.  Put it in the first hour of any training.

---

## Why it is defensible in front of students

**Identity.**  Campus single sign-on, brokered through a standard identity provider.  No separate password for a student to create or for us to lose, and no account lifecycle running beside the institutional one.

**Location.**  Conversations, agents, uploaded course material and the usage ledger live in databases on institutional hardware.  If a course uses a hosted model, the text of a request goes to that provider so it can be answered — that route is real, it is named, and the deployment publishes which provider and under which terms.  The record of the work stays here regardless.

**Access.**  A student's work is reachable by the student, by their instructor within that course, and by the operators who run the servers.  Nobody in another course, ever.  Operator access comes with running any system, commercial ones included, and no design closes it.  The difference here is that the people in question are employees of this institution and are reachable by name.

**Exposure is opt-in at every step.**  Nothing a student builds is shared until they share it, one artifact at a time.  Agent *actions* — the ability to call an outside service — are off unless a course turns them on, and the guides say that an allowlist narrows a path and cannot close one.  The switch that closes it is leaving actions off.

**Records.**  We do not train models on student conversations.  The usage ledger records which model, how many tokens, what it cost, and when.  It does not record what was said.  There is no keystroke, screen or attention telemetry of any kind.

The academic rule the Provost's office needs comes before every integrity question: **a student is fully responsible for what they submit.**  A model cannot accept blame.  That moves the question from *did you use AI* — unanswerable, and increasingly beside the point — to *do you stand behind this*, which is what scholarship has always asked.  Our guidance is explicit that detection tools do not reliably answer the first question and that policy should not be built on them.

The first cohort through this platform is not students.  It is institutional IT staff taking a course whose entire subject is taking the platform apart.  Their findings are the deliverable, and they come in before a single graded assignment depends on any of it.

---

## What it will cost you to run, and where it is weak

**The biggest gap is backup, and it is half closed.**  A nightly backup copies every database, the escrow and the uploaded files to storage off the machine it protects, kept for six months.  **There is no restore.**  The recipe to bring a box back from those copies is not built, and the drill that proves it — a full round trip between two live instances — has not run, so by the platform's own rule these are not backups yet.  An exercised restore is the single largest piece of work between the current state and one you would sign off on for anything that matters.  Until it exists, the platform's own guidance to students is to keep their own copy of anything they would hate to lose.

There is no retention policy, so there is no expiry.  Coursework persists indefinitely unless someone removes it by hand.  The one exception is a conversation a student chooses to start as a temporary chat, which the chat software deletes after 30 days.  That is a privacy feature of the software, and it sets no policy.  What is missing is a policy decision the institution has not made.  No engineering task is waiting for someone to get to it, and building the deletion job first would mean guessing the answer.  Related and frequently misunderstood: **FERPA contains no right to erasure.**  It covers inspection, amendment and disclosure.  The delete-my-data instinct comes from GDPR and from state consumer privacy statutes, and there are well over a hundred of the latter.  "FERPA does not require it" is not "nobody requires it," and which rules apply to this deployment is a question for counsel.

Capacity is per course, not per user.  Each course costs five containers — chat, search, admin panel, document service, vector database.  The isolation that makes the security argument work is the same thing that sets the ceiling, and **we will meet that ceiling before we meet any other limit in the system.**  Growth past a couple of dozen courses is an orchestration project, already scoped and not yet started.

Upgrades are a fleet operation.  A security fix in the chat software means rolling every course instance.  Identical pinned images and generated configuration make that one loop rather than N snowflakes, but it is still N, every time — a standing operational commitment.

We depend on upstream projects we do not control.  Images are pinned so upgrades are boring; bugs we find are filed upstream and linked from the pin.  The exposure is ordinary open-source exposure, with one wrinkle: some capability we rely on is undocumented upstream behavior we verified ourselves, and undocumented behavior can change in a release without anybody calling it a break.

**Key-person risk is real and should be on the form.**  The provisioning layer — the component that creates courses, mints and escrows keys, and generates every per-course configuration — is bespoke and has one author.  The stack it sits on is all open source and widely operated; that layer is not.  Getting a second person who can read and change it is a staffing decision, and it is the cheapest risk reduction available.

The named failure mode is documentation drift, and it has bitten us in the way that does not look like a failure.  Three capabilities were built, working and completely invisible because the page a reader would consult never got the paragraph.  Nothing was broken; nothing would have failed a test; instructors concluded the platform could not do things it had done all along.  The countermeasure is procedural — a behavior change pings the documentation in the same commit — and procedural countermeasures decay.  Assume this recurs and budget attention for it.

Budget enforcement is mid-decision.  Today the course budget is a hard stop for chat and API keys alike, and each API key also has its own hard fuse; chat has no per-person cap, and the weekly pacing number is recorded but nothing reads it yet.  Whether the course-level pool should hard-stop or merely warn is unresolved, and the resolution has a consequence you should hear before it lands: an advisory pool means **somebody has to be willing to be occasionally surprised by a bill.**  At the current scale that is a rounding error.  At forty courses it is a real question.

---

## If we stopped

Ask this one early.  The answer is a feature, and it does not survive being asked late.

The stack is open source throughout — chat, gateway, identity, secret storage, databases.  Conversations sit in standard databases in standard formats, the ledger is a Postgres table, and the platform's configuration templates are in git (each deployment's course records and secrets live on its box and in its backups).  **Nothing here is readable only by our software.**  An institution that decided to walk away from this design would be exporting data.  Nobody would have to negotiate for it.

The asterisk, again: the provisioning layer is ours.  If the platform were abandoned, the courses' data and the running services would be perfectly intact and perfectly readable, and the thing that creates new ones would be a codebase one institution maintains.

---

## What we are asking for

Not a commitment to replace anything.  Concretely:

1. **Permission to run the staff cohort** — IT employees, no students, no grades, no credits — and to treat its findings as the acceptance test.
2. **A decision on retention**, which is a policy question we cannot answer and are currently blocked by.  We will build whatever timer you specify; we will not invent one.
3. **A second engineer who can read the provisioning layer**, which is the cheapest item here and the one that most changes the institution's exposure.
4. **A judgment on backups** — specifically, what class of coursework may depend on this platform before scheduled off-box backups with a tested restore exist.  We have an opinion.  It is not our call.

Everything else here is either working now or written down as not working.  We would rather be asked about the second list.
