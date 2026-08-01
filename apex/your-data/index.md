---
title: Your data in the aLLManac
description: What the platform stores about you, where it lives, who can see it, how long it stays, and what you can ask for.
audience: student
also_reaches: [faculty]
status: scaffold
owner: piper
tags: [ferpa, education-record, data-inventory, student-right, faculty-duty]
regimes: [ferpa]
tethered_to:
  - docs/admin-guide.md#backups
  - registrar/reconcile.py
---

# Your data in the aLLManac

<!-- SCAFFOLD.

     GOVERNING RULE for this whole section: describe what the system does.
     Do not make compliance claims.  "We store X in Y and Z can read it" is
     a factual statement about a running system and ships today.  "We are
     FERPA compliant" is a legal representation and needs counsel review.

     Every page in your-data/ names its gaps.  See docs/pedagogy-authoring.md
     rule 2. -->

## The short version

<!-- Five or six bullets a student can read in thirty seconds:
     - your conversations live in your course's own database
     - your instructor and the platform operators can reach them
     - your usage (which model, how many tokens, what it cost) is recorded
       against your email
     - nothing you type leaves university hardware unless you build an agent
       that sends it somewhere
     - sharing is off unless your instructor turns it on
     Each bullet links down to the page that explains it. -->

## Why this page exists

<!-- Coursework generates records about students, and records about students
     carry obligations.  Say plainly that we would rather you know the shape
     of it than assume it.

     This is also the paragraph that quietly reaches faculty — a professor
     reading what their students are told learns what they are holding. -->

## In this section

- [What we store](what-we-store.md) — the actual inventory, by system
- [Who can see it](who-can-see-it.md) — access control, top to bottom
- [How long we keep it](how-long-we-keep-it.md) — retention, archival, and
  what happens when a course ends
- [Asking about your data](asking-about-your-data.md) — your rights under
  FERPA, and what we can act on today
- [If you teach a course](for-instructors.md) — the faculty page

## What we have not built yet

<!-- Named up front rather than buried.  As of scaffold:
     - no scheduled or offsite backup (manual procedure only)
     - no tested restore
     - no per-student deletion path
     - no automated retention expiry
     Link each to the page that explains it.  Update in the same commit as
     the plumbing that closes it. -->
