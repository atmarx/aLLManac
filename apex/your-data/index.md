---
title: Your data in the aLLManac
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

# Your data in the aLLManac

Coursework generates records about you, and records about students carry
obligations.  This section is the plain account of what those records are —
we would rather you know the shape of it than assume.

## The short version

- **Your conversations live in your own course's database**, separate from
  every other course.  [What we store](what-we-store.md)
- **Your instructor and the platform's operators can reach them.**  Nobody in
  another course can.  [Who can see it](who-can-see-it.md)
- **Your usage is recorded against your email address** — which model, how
  many tokens, what it cost, when.  Not what you said.
  [The ledger](what-we-store.md#the-ledger-which-is-the-one-that-surprises-people)
- **Nothing you write becomes training data**, and nothing leaves
  institutional hardware unless your course enables an agent that sends it
  somewhere.  [The path that leaves the building](who-can-see-it.md#the-path-that-leaves-the-building)
- **Sharing is off** unless your instructor turns it on.
- **Nothing expires on its own.**  [How long we keep it](how-long-we-keep-it.md)

## In this section

- **[What we store](what-we-store.md)** — the actual inventory, by system
- **[Who can see it](who-can-see-it.md)** — access control, top to bottom
- **[How long we keep it](how-long-we-keep-it.md)** — retention, backups, and
  what happens when a course ends
- **[Asking about your data](asking-about-your-data.md)** — what FERPA gives
  you, and what we can act on today
- **[If you teach a course](for-instructors.md)** — the faculty page

## What is not built yet

These pages name gaps rather than hiding them, so here they are in one place:

- **No scheduled or off-machine backup**, and no restore that has been tested
  end to end.
- **No automated retention or expiry** — nothing deletes itself.
- **No per-student deletion path.**  Removing a student revokes access without
  erasing what they wrote.
- **No self-service export.**  Requests are handled by hand.
- **No way to block all outbound domains** for courses that enable agent
  actions — leaving actions off is the only complete answer.

Each is explained where it belongs, and each disappears from this list in the
same change that closes it.

## Why the gaps are published

A page claiming protections a system does not have is worse than no page,
because someone will plan around it.  It is also the less useful document:
knowing that retention is unbuilt, and why the policy question comes before
the deletion job, tells you more about how to think about your own data than
a reassuring paragraph would.
