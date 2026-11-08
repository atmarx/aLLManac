---
title: If you have to sign off on this
description: A brief for the CIO, CISO and Provost on why this was built instead of bought, what it does that a licensed product does not, why it can be defended in front of students, what it will cost to run, and where it is currently weak.
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

A professor uploads a syllabus and a reading list, writes a paragraph of instructions, and forty minutes later the class has an assistant that has read the course material.  Every question the assistant answers is metered against that course's budget, attributed to the student who asked it, and stored in a database that belongs to that course and no other.

The product is a course assistant built in under an hour, metered by course and student, and stored in the course's own database.  Making it work took a set of design decisions, and parts of it still do not work.

Three people sign different parts of the same form.  The CIO takes on the operational load, the CISO takes on the risk, and the Provost takes on the academic consequences.  Each section describes what works and what is not built yet in the same plain tone.  A brief that lists only what works is a sales document.

---

## Why build it instead of licensing a product

**{{PLATFORM}} was not built to replace a licensed product.**  A campus-wide general-purpose assistant and {{PLATFORM}} solve different problems, and the design assumes both exist.  The plan is to send a student who has used up their share of a course on to the licensed assistant the institution already pays for.  That redirect is not built yet, and today a spent course budget is a hard stop.  Weighing {{PLATFORM}} as a replacement for the campus assistant is the wrong comparison, and it will lead to a bad decision.

A licensed product does not sell, at any tier, the things a *course* needs:

**An allocation with a boundary around it.**  Seat licensing charges by enrollment, but what a course uses depends on its assignments.  A seminar of twelve running a research-methods unit can use more than a lecture of two hundred that touches the tool twice.  Per-seat pricing gets that wrong in both directions, and no tier corrects it.  A seat license sells access per person, and what a course uses depends on its work.

**A ledger the institution can read by course.**  Every request on {{PLATFORM}} goes through one gateway, and that gateway is the only route to a model.  There is no second path and no unrecorded spending, and no vendor dashboard sits between the institution and its own usage data.  The question of what a course spent this term is answered from a database the institution runs.

**A group that co-edits one assistant.**  Commercial custom assistants have one author.  On {{PLATFORM}}, a project team has editor rights on a single agent, including its instructions, attached documents and tools, and maintains it together.  Shared editing is what makes an agent usable as course infrastructure, and it is the first thing we test on a new deployment.

**The ability to change your mind about the model.**  All inference goes through one interface.  Swapping providers, adding a second, or moving a course onto institutional GPUs is a configuration change, and no data has to be migrated.  Without that interface, the institution's AI strategy would be tied to one vendor's product roadmap.

One reason is not commercial, and for a Provost it may be the strongest: **the platform is course material.**  Every significant decision in the platform is written up with its reasoning and its cost, including tenancy, key custody, and what happens to data nobody can delete.  Students in a systems or security course read the argument and then attack the running system under a signed scope letter.  A licensed product cannot offer that.  The course teaches the reasoning, and a vendor has no incentive to publish its own.

---

## What it does that the licensed products do not

- **Isolation by structure, with no permission check to forget.**  Each course runs its own chat instance, its own database, its own search index, and its own document store.  No course's conversations, agents or files share a table with another course's.  As a result, the chat software has no query that could cross between courses, and there is no access check anybody could forget to write.  The usage ledger, the identity system and the platform's own records are shared by design, and so is the database server underneath every course.  The full argument, including what each shared piece costs, is in [How do you keep the courses apart?](how-we-built-it/keeping-courses-apart.md).
- **Students get a key as well as a chat box.**  A student can point their own editor, scripts, or coding harness at the campus gateway with a personal key, metered the same way.  The key lets students use the platform directly in the work they are graded on.
- **The meter is a teaching instrument.**  Cost intuition (knowing roughly what a question costs before you ask it) is a professional skill.  It is currently unteachable, because the cost feedback is invisible and delayed.  {{PLATFORM}} shows the number, lists usage alphabetically and never by who used the most, and does not score anyone on it.  There are no leaderboards, and budgets can never be merit-based.  The meter reports what a query cost, never what it was worth.
- **The guides decline when a question is not in their files.**  The guides on {{PLATFORM}} are instructed to answer from their attached documents and to say so when something is not in their files.  We test that behavior with a scripted evaluation suite and treat a wrong but confident answer as a defect to fix.
- **The failures are published.**  [If you're evaluating this for your course](evaluating-it.md) has a list of what is broken, under "What we already know", and the platform's largest self-inflicted outage is [written up in full](how-we-built-it/keeping-courses-apart.md).

---

## Chat and keys are limited by different things

Most people assume one limit covers both the chat window and personal API keys.  It doesn't, and the mistake costs money.

The chat window is capped in length.  A chat conversation may grow to a set size, about a few hundred pages of text, and past that size the chat software drops the oldest part before sending the rest.  We choose that size per course.  The cap looks like a capability limit, but it is a cost control: it bounds what one conversation can spend against a metered model.

A personal API key is capped in money.  When a student points their own editor or scripts at the gateway, that traffic never goes through the chat software, so the chat length cap does not apply.  The request can use whatever context the model itself serves.  What stops key traffic is the dollar fuse on the key.

**Chat is bounded per conversation in tokens; keys are bounded per key in dollars.**  Chat and keys both also draw on the course's pool, which is a dollar ceiling over all of the course's use.  In practice, a student's conversation gets trimmed in the chat window, while the same student using a harness with a key can send an enormous request and pay for it.  On a priced model, the key's fuse stops the student when the key's dollars run out.  On a campus model with no price, the fuse never moves, and the only limits are the student's own judgment and the model's own context window.

The difference between chat limits and key limits is by design, and it is the part of the platform most likely to be taught wrong.  Cover it in the first hour of any training.

---

## Why it is defensible in front of students

**Identity.**  Students sign in with campus single sign-on, brokered through a standard identity provider.  There is no separate password for a student to create or for us to lose, and no separate account lifecycle beside the institutional one.

**Location.**  Conversations, agents, uploaded course material and the usage ledger are stored in databases on institutional hardware.  If a course uses a hosted model, the text of each request is sent to that provider so the model can answer it.  That route exists and is named, and the deployment publishes which provider it uses and under which terms.  The stored record of the work stays on institutional hardware either way.

**Access.**  A student's work can be read by the student, by their instructor within that course, and by the operators who run the servers.  Nobody in another course can ever read it.  Operator access comes with running any system, commercial ones included, and no design removes it.  On {{PLATFORM}}, the operators are employees of this institution and can be contacted by name.

**Exposure is opt-in at every step.**  Nothing a student builds is shared until they share it, one artifact at a time.  Agent *actions* (the ability to call an outside service) are off unless a course turns them on.  The guides explain that an allowlist only narrows which outside services actions can call.  The only way to block actions completely is to leave them off.

**Records.**  We do not train models on student conversations.  The usage ledger records which model, how many tokens, what it cost, and when.  It does not record what was said.  There is no keystroke, screen or attention telemetry of any kind.

The academic rule the Provost's office needs comes before every integrity question: **a student is fully responsible for what they submit.**  A model cannot accept blame.  That rule changes the question from *did you use AI*, which can't be answered and matters less and less, to *do you stand behind this*, which scholarship has always asked.  The platform's teaching guidance says explicitly that detection tools do not reliably answer the first question and that policy should not be built on them.

The first cohort on {{PLATFORM}} is institutional IT staff, not students.  The staff cohort's course has one subject: taking the platform apart.  Their findings are the deliverable, and the findings come in before a single graded assignment depends on the platform.

---

## What it will cost you to run, and where it is weak

The biggest gap is backup, and it is half closed.  A nightly backup copies every database, the escrow and the uploaded files to storage off the machine it protects, and keeps them for six months.  **There is no restore.**  The recipe to bring a box back from those copies is not built.  The drill that proves a restore works, a full round trip between two live instances, has not run.  By the platform's own rule, these copies are not backups yet.

A rebuild from the backups needs three secrets: the escrow's unseal key and both backup passwords.  Those three secrets are printed on paper, so they survive the loss of the box.  The missing piece is the restore recipe that would use them.  An exercised restore is the largest single piece of work between the platform's current state and one you could sign off on for anything that matters.  Until a restore exists, [the platform's own guidance](your-data/how-long-we-keep-it.md#backups) tells students to keep their own copy of anything they would hate to lose.

There is no retention policy, so nothing expires.  Coursework is kept indefinitely unless someone removes it by hand.  The one exception is a conversation a student chooses to start as a temporary chat, which the chat software deletes after 30 days.  Temporary chat is a privacy feature of the software, and it does not set any policy.  Retention is waiting on a policy decision the institution has not made, not on an engineering task.  Building the deletion job before that decision would mean guessing the answer.

**FERPA contains no right to erasure**, but state law may impose one, and which rules apply to this deployment is a question for counsel.  [What FERPA gives you](your-data/asking-about-your-data.md#what-ferpa-gives-you) has the rights and the regimes.

Capacity is counted per course, not per user.  Each course costs five containers: chat, search, admin panel, document service, and vector database.  The per-course isolation that makes the security argument work also sets the capacity ceiling, and we will meet that ceiling before any other limit in the system.  Growth past a couple of dozen courses is an orchestration project, already scoped and not yet started.

Upgrades are a fleet operation.  A security fix in the chat software means rolling it out to every course instance.  Identical pinned images and generated configuration let the operators upgrade every course in one loop, instead of handling each course by hand.  The loop still runs once per course on every upgrade, which is a standing operational commitment.

The platform depends on upstream projects we do not control.  Images are pinned to specific versions so upgrades are predictable, and bugs we find are filed upstream and linked from the pin.  The risk is the ordinary risk of depending on open source, with one addition: some capabilities we rely on are undocumented upstream behavior that we verified ourselves.  Undocumented behavior can change in a release without anybody calling it a breaking change.

**Key-person risk should be on the form.**  The provisioning layer is bespoke and has one author.  The provisioning layer is the component that creates courses, mints and escrows keys, and generates every per-course configuration.  The rest of the stack is open source and widely operated, and the provisioning layer is not.  Getting a second person who can read and change the provisioning layer is a staffing decision, and it is the cheapest risk reduction available.

The platform's named failure mode is documentation drift, and it has already caused failures that did not look like failures.  Three capabilities were built and working but invisible to users, because the page a reader would consult never got the paragraph describing them.  Nothing was broken and no test would have failed, but instructors concluded the platform could not do things it had done all along.  The countermeasure is procedural: a behavior change must update the documentation in the same commit.  Procedural countermeasures weaken over time, so assume documentation drift will recur and budget attention for it.

The plan for budget enforcement is decided but not built.  Today the course budget is a hard stop for chat and API keys alike, each API key has its own hard fuse, chat has no per-person cap, and the weekly pacing number is recorded but nothing reads it yet.  The decided plan keeps the hard stop for keys.  A script retries, so a budget error is the right answer to a program.  The plan also keeps the course cap as a high circuit breaker.  The change is to chat: a student past their share of one course will be sent to the licensed assistant the institution already pays for, so one student's heavy month stops being the whole class's problem.  **Until that redirect ships, a spent course budget stops the course for everyone at once.**

---

## If we stopped

Ask early what would happen if we stopped running the platform, before courses depend on it.  The answer is one of the platform's strengths.

The stack is open source throughout: chat, gateway, identity, secret storage, and databases.  Conversations are stored in standard databases in standard formats, the ledger is a Postgres table, and the platform's configuration templates are in git.  Each deployment's course records and secrets are stored on its own server and in its backups.  **No data on the platform is readable only by our software.**  An institution that decided to walk away from this design would only need to export its data.  Nobody would have to negotiate for it.

The exception, again, is the provisioning layer, which is ours.  If the platform were abandoned, the courses' data and the running services would stay intact and readable.  The provisioning layer that creates new courses would be a codebase one institution maintains.

---

## What we are asking for

We are not asking for a commitment to replace anything.  We are asking for four things:

1. **Permission to run the staff cohort** (IT employees, with no students, no grades and no credits), and to treat its findings as the acceptance test.
2. **A decision on retention.**  Retention is a policy question we cannot answer, and we are currently blocked by it.  We will build whatever timer you specify, and we will not invent one.
3. **A second engineer who can read the provisioning layer.**  A second engineer is the cheapest item on this list, and it does the most to change the institution's exposure.
4. **A judgment on backups:** what class of coursework may depend on this platform before scheduled off-box backups with a tested restore exist.  We have an opinion, but the decision is not ours.

Every other part of the platform is either working now or documented as not working.  We would rather be asked about the parts that are not working.
