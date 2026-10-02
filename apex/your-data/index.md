---
title: Your data in {{PLATFORM}}
description: What the platform stores about you, where it lives, who can see it, how long it stays, and what you can ask for.
audience: student
also_reaches: [faculty]
status: draft
owner: piper
tags: [ferpa, education-record, data-inventory, student-right, faculty-duty, retention]
regimes: [ferpa]
tethered_to:
  - docs/admin-guide.md#backups
  - registrar/reconcile.py
  - justfile
---

# Your data in {{PLATFORM}}

Coursework generates records about you, and records about students carry obligations.  This section is the plain account of what those records are — we would rather you know the shape of it than assume.

## The short version

- **Your conversations live in your own course's database**, separate from every other course.  [What we store](what-we-store.md)
- **Your instructor and the platform's operators can reach them.**  Nobody in another course can.  [Who can see it](who-can-see-it.md)
- **Your usage is recorded against your email address** — which model, how many tokens, what it cost, when.  Not what you said.  [The ledger](what-we-store.md#the-ledger-which-is-the-one-that-surprises-people)
- **Where model traffic goes is a deployment choice.** A locally hosted model
  can keep it on institutional hardware; a hosted model receives the prompts
  and files needed to answer. Agent actions can send material to additional
  services. [The paths that can leave the building](who-can-see-it.md#paths-that-can-leave-the-building)
- **Agent sharing is available, and nothing is shared until you share it.**  [Sharing](who-can-see-it.md#sharing-is-available-and-nothing-is-shared-until-you-share-it)
- **Nothing expires on its own — except a temporary chat, after 30 days.**  [How long we keep it](how-long-we-keep-it.md)

## In this section

- **[What we store](what-we-store.md)** — the actual inventory, by system
- **[Who can see it](who-can-see-it.md)** — access control, top to bottom
- **[How long we keep it](how-long-we-keep-it.md)** — retention, backups, and what happens when a course ends
- **[Asking about your data](asking-about-your-data.md)** — what FERPA gives you, and what we can act on today
- **[If you teach a course](for-instructors.md)** — the faculty page

## What is not built yet

These pages name gaps rather than hiding them, so here they are in one place:

- **No restore.**  A nightly backup copies everything off the machine, but there is no tested way yet to bring it back — and a backup nobody has restored from is not one yet.
- **No retention policy.**  The one automatic deletion is a temporary chat, after 30 days; everything else stays until someone removes it.
- **No per-student deletion path.**  Removing a student revokes access without erasing what they wrote.
- **Export covers your own work, not everything.**  You can take your conversations and agents out of any course yourself; the usage ledger, your identity record and a formal records request still go through a person.
- **No way to block all outbound domains** for courses that enable agent actions — leaving actions off is the only complete answer.

Each is explained where it belongs, and each disappears from this list in the same change that closes it.

## Why the gaps are published

A page claiming protections a system does not have is worse than no page, because someone will plan around it.  It is also the less useful document: knowing that retention is unbuilt, and why the policy question comes before the deletion job, tells you more about how to think about your own data than a reassuring paragraph would.
