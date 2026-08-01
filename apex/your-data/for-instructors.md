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
---

# If you teach a course

Running a course here generates records about identifiable students — what
they asked, what they built, how much they used, and when.  Those are records
about students, maintained by the university, produced by your coursework.
The obligations that come with them were already yours; the platform just
makes them concrete and gives you switches that affect them.

This page is the short version of what you are holding and what you control.
It makes no claim about what the law requires in your specific situation —
that is a question for the university's counsel and privacy office.

## Where the obligation actually comes from

Three corrections up front, because guidance on this topic circulates widely
and much of it was written for K–12.

**Your students hold the rights, not their parents.**  FERPA rights transfer
from parents to the student when they turn 18 *or enroll in a postsecondary
institution at any age* — so in your classroom, the rights holder is the
student in front of you, including the sixteen-year-old dual-enrollment
student.  Guidance that centers parental consent is describing a different
school system.

**No software is "FERPA compliant."**  FERPA binds schools that receive
Department of Education funding.  It does not bind companies, which means a
product cannot carry FERPA approval.  As the former director of the
Department's Student Privacy Policy and Assistance Division put it, *"there is
no such thing as a 'FERPA seal of approval.'"*  The real question is always
whether a tool **can be used by the institution in a FERPA-compliant
manner** — which is a question about your use, not about the vendor's
marketing.

**FERPA does not give students a right to deletion.**  It gives them the
right to inspect and review their education records, to seek amendment of
records they believe are inaccurate or misleading, and to have some control
over disclosure of personally identifiable information.  There is no
erase-my-data provision.  That instinct comes from GDPR and state consumer
privacy laws, which are different regimes with different triggers.

That last one carries a caveat worth stating: state student privacy statutes
frequently *do* address retention and deletion, and there are well over a
hundred of them.  "FERPA does not require it" is not the same as "nobody
requires it."

### On the standards you may have heard named

NIST **800-53** covers federal information systems under FISMA.  NIST
**800-171** covers Controlled Unclassified Information in nonfederal systems
and arrives through contract flow-down, which is why colleagues with federal
research awards run into it and you may never.  Neither attaches to your
course because student data is sensitive.

The NIST framework that is actually about AI is the **AI Risk Management
Framework** (AI RMF 1.0, 2023), and it is voluntary — a way to organize
thinking about AI risk rather than a compliance obligation.

What governs your course day to day is FERPA, applicable state law, and the
university's own data classification policy.

!!! note "Placeholder — institutional policy reference"
    This section needs the citable Drexel data classification policy and the
    tier that course data sits in.  Pending from @xram; not shipping without
    it.

## What you may put in here

!!! note "Placeholder — classification ceiling"
    Peer institutions publish an explicit ceiling for their AI platforms —
    Harvard's AI Sandbox, for instance, states plainly that it is approved
    for data up to their Level 3 (Medium Risk Confidential).  A one-line
    ceiling is the single most useful thing an instructor can be told, and
    ours needs to come from the university rather than from this page.

Until that line exists, the conservative posture: this platform holds
coursework and the records coursework generates.  It is not the place for
health records, financial aid detail, disability accommodation files, or
anything you would route through a system with its own access review.

## The four switches you control

| Switch | What it does | Worth thinking about |
|---|---|---|
| **Agent actions** | Lets agents in your course call outside web services | The one that can send course content off university hardware.  Off by default.  The domain allowlist is not built yet, so "on" currently means "any address the agent's builder typed." |
| **Sharing** | Lets students share agents with each other | Off by default.  Turning it on makes one student's work visible to others, which is a disclosure decision rather than a convenience setting. |
| **Knowledge files** | What you upload to a course agent | Anything you attach becomes retrievable by everyone who can use that agent.  Rosters, graded work, and student writing are the ones to think twice about. |
| **Roster membership** | Who is enrolled | Enrollment is access.  Removing a student revokes their access; it does not erase what they already wrote. |

Actions and sharing are set per course in the course record — ask the
platform operators to change them, and they will tell you what the change
means before making it.

## If you are using AI to help with grading

Using a model to make or substantially inform decisions about students —
grades, flags, referrals — is a different risk category than using one as a
writing partner, and it is the use case emerging AI regulation is most
interested in.  The general shapes of a defensible approach are a human who
actually reviews each decision, a record of how the decision was reached, and
telling students that the tool is in the loop.

If you are considering this, talk to the university before the term starts
rather than after a grade is contested.

## What the platform does for you

- Your course runs in **its own instance** with its own database.  No other
  course can reach into it.
- Students authenticate with **campus identity** — no separate accounts.
- **Model traffic stays on university hardware** unless your course enables
  actions or uses a hosted endpoint.
- **Nothing is trained on your students' work**, here or by a vendor.
- **Usage is attributed per student**, so budget questions have real answers.
- **Sharing and actions are off** in every new course, so the permissive
  settings require a decision rather than happening by default.

## What it does not do yet

Stated plainly so you do not plan around something that is not there:

- **No scheduled or off-box backup.**  Backups are a documented manual
  procedure run by an operator, and the restore path has not been tested.
- **No automated retention or expiry.**  Conversations stay until someone
  removes them, and that removal is currently a manual act.
- **No per-student deletion path.**  Nothing walks a course database and
  removes one student's material.
- **No domain allowlist on agent actions.**  Covered above.

If any of these matter to how you are planning a course, say so — they are
the platform's open work, and a real course requirement moves things up the
list.

## Questions worth asking before the term starts

- Does this assignment require students to put anything identifying into a
  chat?
- Do agents in this course need to reach outside the university, or does it
  just seem convenient?
- Should students see each other's work — and did I decide that, or inherit
  it?
- What happens to this material when the term ends, and did I tell anyone?
- If a student asks me what is stored about them, where do I send them?

The last one has an answer: [Your data in the aLLManac](index.md), which is
written for them and which you are welcome to assign.
