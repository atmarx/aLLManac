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

Coursework generates records about you, and records about students come with obligations.  The pages below list what those records are, so you know instead of assuming.

## At a glance

- **Your conversations live in your own course's database**, separate from every other course.  [What we store](what-we-store.md)
- **The platform's operators can get to them, and anything you share is visible to whoever you share it with.**  Nobody in another course can.  [Who can see it](who-can-see-it.md)
- **Your usage is recorded against your email address** — which model, how many tokens, what it cost, when.  Not what you said.  [The ledger](what-we-store.md#the-ledger-which-is-the-one-that-surprises-people)
- **Where model traffic goes is a deployment choice.**  A locally hosted model can keep it on institutional hardware; a hosted model receives the prompts and files needed to answer.  Agent actions can send material to additional services.  [The paths that can leave the building](who-can-see-it.md#paths-that-can-leave-the-building)
- **Agent sharing is available, and nothing is shared until you share it.**  [Sharing](who-can-see-it.md#sharing-is-available-and-nothing-is-shared-until-you-share-it)
- **Nothing expires on its own — except a temporary chat, after 30 days.**  [How long we keep it](how-long-we-keep-it.md)

## In this section

- **[What we store](what-we-store.md)** — the inventory, by system
- **[Who can see it](who-can-see-it.md)** — access control, top to bottom
- **[How long we keep it](how-long-we-keep-it.md)** — retention, backups, and what happens when a course ends
- **[Asking about your data](asking-about-your-data.md)** — what FERPA gives you, and what we can act on today
- **[If you teach a course](for-instructors.md)** — the faculty page

## What is not built yet

Each is explained on its own page.  Together:

- **No restore.**  Backups run nightly, but there is no tested way yet to bring them back.  [Backups](how-long-we-keep-it.md#backups) has the detail.
- **No retention policy.**  The one automatic deletion is a temporary chat, after 30 days; everything else stays until someone removes it.
- **No per-student deletion path.**  Removing a student revokes access without erasing what they wrote.
- **Export covers your own work, not everything.**  You can take your conversations and agents out of any course yourself; the usage ledger, your identity record and a formal records request still go through a person.

Each one comes off this list in the same change that closes it.  One more can't be built here at all: there is no way to block all outbound domains for courses that enable agent actions, so leaving actions off is the only complete answer.

## Why the gaps are published

Someone will plan around a protection a page claims, whether the system has it or not.  Knowing that retention is unbuilt, and that the policy question has to be settled before anyone writes a deletion job, tells you more about how to think about your own data than a reassuring paragraph would.
