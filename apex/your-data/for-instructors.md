---
title: If you teach a course
description: What you are holding when a course runs here, the four switches you control, and a few corrections to guidance that circulates widely and is shaped for K–12.
audience: faculty
status: draft
owner: piper
tags: [faculty-duty, ferpa, eligible-student, school-official-exception, education-record, access-control, egress-control, retention, data-classification, allowlist, automated-decision-making, nist-ai-rmf]
regimes: [ferpa, nist-ai-rmf]
tethered_to:
  - registrar/courses.example.yaml
  - registrar/reconcile.py
  - docs/design-walls.md#the-classroom-posture
  - docs/design-walls.md#actionsalloweddomains-is-top-level--and-its-the-only-wall-around-actions
  - registrar/planes/courses.py
---

# If you teach a course

Running a course here generates records about identifiable students — what they asked, what they built, how much they used, and when.  Those are records about students, maintained by the university, produced by your coursework.  The obligations that come with them were already yours; the platform just makes them concrete and gives you switches that affect them.

This page is the short version of what you are holding and what you control.  It makes no claim about what the law requires in your specific situation — that is a question for your institution's counsel and privacy office.

## Where the obligation actually comes from

Three corrections up front, because guidance on this topic circulates widely and much of it was written for K–12.

**Your students hold the rights, not their parents.**  FERPA rights transfer from parents to the student when they turn 18 *or enroll in a postsecondary institution at any age* — so in your classroom, the rights holder is the student in front of you, including the sixteen-year-old dual-enrollment student.  Guidance that centers parental consent is describing a different school system.

**No software is "FERPA compliant."**  FERPA binds schools that receive Department of Education funding.  It does not bind companies, which means a product cannot carry FERPA approval.  As the former director of the Department's Student Privacy Policy and Assistance Division put it, *"there is no such thing as a 'FERPA seal of approval.'"*  The real question is always whether a tool **can be used by the institution in a FERPA-compliant manner** — which is a question about your use, not about the vendor's marketing.

**FERPA does not give students a right to deletion.**  It gives them the right to inspect and review their education records, to seek amendment of records they believe are inaccurate or misleading, and to have some control over disclosure of personally identifiable information.  There is no erase-my-data provision.  That instinct comes from GDPR and state consumer privacy laws, which are different regimes with different triggers.

That last one carries a caveat worth stating: state student privacy statutes frequently *do* address retention and deletion, and there are well over a hundred of them.  "FERPA does not require it" is not the same as "nobody requires it."

### On the standards you may have heard named

NIST **800-53** covers federal information systems under FISMA.  NIST **800-171** covers Controlled Unclassified Information in nonfederal systems and arrives through contract flow-down, which is why colleagues with federal research awards run into it and you may never.  Neither attaches to your course because student data is sensitive.

The NIST framework that is actually about AI is the **AI Risk Management Framework** (AI RMF 1.0, 2023), and it is voluntary — a way to organize thinking about AI risk rather than a compliance obligation.

What governs your course day to day is FERPA, applicable state law, and your institution's own data classification policy.

### Risk tiers, and what "high risk" actually buys you

Most institutions maintain a **risk register**.  A system's tier is an entry someone makes in it — a determination about a *system*, rather than a label describing how sensitive the data feels.  The entry is what carries the real obligations, which is why the tier matters more than the adjective.

**These guides treat FERPA-protected coursework as high-risk data.**  That is the conservative posture, and it is not a warning.  A high tier means the handling is deliberate, and typically it requires something like:

- **Encryption** at rest and in transit
- **Backups** on a defined schedule, kept off the machine they protect, with restores that have actually been tested
- **Access review** on a cadence — someone checks who can reach it, on purpose, more than once
- **Documented retention and disposal** — how long records stay, and what happens at the end
- **A named owner** who is accountable for the system

That list is the useful part.  Whatever your institution's register calls this platform, those are the questions its answer will turn into.

**Your institution's register is the authority.**  Tiers, names, and thresholds vary, and the same records can land differently depending on what the system is for — data inside a research project and the same data inside an operational teaching platform are separate entries with separate arguments, and an institution may reasonably put them a tier apart.  If yours classifies this platform differently, the handling standards move with it, and your privacy or compliance office is who tells you.

## What you may put in here

The most useful sentence an instructor can be handed is a **ceiling** — one line naming the highest tier of data this deployment may hold.  It is worth asking your operator for it if this page does not carry one, and it is worth publishing if you are the operator.  Institutions that run AI platforms increasingly do: Harvard's AI Sandbox, for one, states plainly that it is approved for data up to their Level 3, Medium Risk Confidential.

The conservative posture, absent a local ceiling: this platform holds coursework and the records coursework generates.  It is not the place for health records, financial aid detail, disability accommodation files, or anything you would route through a system with its own access review.

## The four switches you control

| Switch | What it does | Worth thinking about |
|---|---|---|
| **Agent actions** | Lets agents in your course call outside web services | An additional route beyond the selected model provider, and the most consequential switch on this page. Off by default, and **that default is the control** — see below. |
| **Sharing** | Lets students share agents with each other | **On** in every course, deliberately — group work needs it and the chat software's own default is the wrong one for a classroom.  Nothing is shared unless someone shares it, and sharing does not cross the course boundary. |
| **Knowledge files** | What you upload to a course agent | Anything you attach becomes retrievable by everyone who can use that agent.  Rosters, graded work, and student writing are the ones to think twice about. |
| **Roster membership** | Who is enrolled | Enrollment is access.  Removing a student revokes their access; it does not erase what they already wrote. |

Actions are set per course in the course record — ask the platform operators to change them, and they will tell you what the change means before making it.  Sharing is not a per-course setting: it is on everywhere, by design, and the section below is what you need to know rather than a switch to find.

### On sharing, which is on

Worth stating clearly because guidance for other platforms usually says the opposite: **agent sharing is on in every course here.**  The chat software ships it off, which suits a general-purpose deployment and not a classroom — group projects are the single most requested thing, and a course where nobody can hand anyone else an agent is a course fighting its own tooling.

What that does and does not mean for you:

- **Nothing is shared unless a person shares it.**  There is no state in which a student's agent becomes visible without them acting.
- **Sharing does not cross the course boundary.**  Your course is its own instance, so there is no other course to share into and nothing to misconfigure.
- **A shared agent carries its knowledge files.**  The Editor role can read and change them, and anyone who can merely *chat* with an agent can eventually coax out what is in its files.  Say this to a class out loud: attach materials you would hand them anyway, never answer keys or solutions.
- **Group sharing exists, but campus groups do not flow into it.**  Share-groups have to be created in the platform's own admin panel; your roster and institutional groups are not available as sharing targets.  Sharing with named individuals is the path that works today.

If your course is one where student work should not circulate, that is a conversation with your class and a line on the assignment rather than a switch — and it is worth having in week one, before someone shares something they assumed was private.

### On actions and the allowlist, precisely

If you enable actions, you can also give your course a list of domains agents are permitted to reach.  It is worth knowing exactly what that buys, because the two knobs are not equal options:

- **Leaving actions off closes the action path.** No agent in the course can
  call an arbitrary outside service. The selected model may still be a hosted
  endpoint; that is a separate deployment-level route.
- **Enabling actions opens it.**  A course with actions on and no domain list can reach the entire public internet.
- **The allowlist narrows an open door.  It cannot close one.**  There is no way to write "allow nothing" — an empty list is no list rather than a denial.
- **Internal addresses are blocked by default, and naming one lifts the block.**  University-internal and private addresses are refused unless the list names them, at which point they are permitted.  The default is a floor, not a ceiling.

So the meaningful decision is whether actions are on at all.  Treat the allowlist as a way to reduce a risk you have already accepted rather than a way to avoid accepting it.

Two more things about how entries are read, because both surprise people writing their first list:

- **A path in an entry does not scope anything.**  Writing `api.example.edu/v1/chat` does not restrict an agent to that endpoint — the path is ignored and the rule permits the whole host, including `api.example.edu/admin/delete`.  Give us a path-shaped entry and the registrar refuses it rather than rendering it, which is deliberate: a rule that is silently wider than it reads is worse than one that fails.
- **A wildcard covers the apex too.**  `*.example.edu` matches `example.edu` as well as its subdomains.  Say what you mean and read it back as *"an agent may send course material to anything at this address"* — that is what the entry authorizes.

## If you are using AI to help with grading

Using a model to make or substantially inform decisions about students — grades, flags, referrals — is a different risk category than using one as a writing partner, and it is the use case emerging AI regulation is most interested in.  The general shapes of a defensible approach are a human who actually reviews each decision, a record of how the decision was reached, and telling students that the tool is in the loop.

If you are considering this, talk to your institution's privacy or compliance office before the term starts rather than after a grade is contested.

## What the platform does for you

- Your course runs in **its own instance** with its own database.  No other course can reach into it.
- Students authenticate with **campus identity** — no separate accounts.
- **The model route is explicit:** local deployments keep model traffic on
  institutional hardware; hosted deployments send it to the named provider.
- **The platform does not train on your students' work.** A hosted provider's
  retention and training terms must be evaluated and disclosed separately.
- **Usage is attributed per student**, so budget questions have real answers.
- **Agent actions are off** in every new course, so additional outbound
  destinations require a decision rather than appearing by default.

## What it does not do yet

Stated plainly so you do not plan around something that is not there:

- **No scheduled or off-box backup.**  Backups are a documented manual procedure run by an operator, and the restore path has not been tested.
- **No automated retention or expiry.**  Conversations stay until someone removes them, and that removal is currently a manual act.
- **No per-student deletion path.**  Nothing walks a course database and removes one student's material.
- **No way to deny all outbound domains.**  The allowlist can narrow where agents reach; it cannot express "nowhere."  Leaving actions off is the only complete answer, and that is a property of the underlying chat software rather than a setting waiting to be built.

If any of these matter to how you are planning a course, say so — they are the platform's open work, and a real course requirement moves things up the list.

## Questions worth asking before the term starts

- Does this assignment require students to put anything identifying into a chat?
- Do agents in this course need to reach outside the university, or does it just seem convenient?
- Should students see each other's work — and did I decide that, or inherit it?
- What happens to this material when the term ends, and did I tell anyone?
- If a student asks me what is stored about them, where do I send them?

The last one has an answer: [Your data in the aLLManac](index.md), which is written for them and which you are welcome to assign.
