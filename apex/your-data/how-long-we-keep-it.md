---
title: How long we keep it
description: Retention, backups, what survives leaving a course, what happens at the end of term, and an honest account of the parts that are not built yet.
audience: student
also_reaches: [faculty]
status: draft
owner: piper
tags: [retention, backup, restore, archival, secure-deletion, course-rollover, escrow, disaster-recovery, ferpa, state-privacy-law, student-right]
regimes: [ferpa, gdpr]
tethered_to:
  - justfile
  - docs/admin-guide.md#backups
  - registrar/reconcile.py
---

# How long we keep it

The honest answer, first: **indefinitely, unless someone removes it by hand.**  There is no automatic expiry on this platform.  Your conversations from a course that ended two terms ago are still in that course's database.

The rest of this page is what that means and what is being done about it.

## Why there is no clock

Retention is a policy question before it is an engineering one.  Deciding that coursework should disappear after eighteen months means deciding what happens to a student's work when they want to look back at it, what an instructor can still reference, and what the institution is obliged to keep for its own reasons.

That policy does not exist here yet, so neither does the timer that would enforce it.  Building the timer first would mean guessing at the answer, and a deletion job is a bad place to guess.

!!! warning "Not built yet"
    No automated retention or expiry.  Removal is currently a manual act by an operator.

## Backups

Copies of the databases exist, made by an operator running a documented procedure.

!!! warning "Not built yet"
    The scheduled version — a nightly archive copied off the machine it protects — is designed and not implemented.  Today there is no schedule, no off-box copy, and no restore that has been tested end to end.

Both halves of that matter to you and they point in opposite directions.  A backup is protection against losing your work, and it is also a second place your work lives, which is a longer tail than most people picture when they delete something.  Any honest retention policy has to account for both.

This is the platform's most visible gap, and it is the one where a high-risk posture is most explicit about what it expects: scheduled backups, kept off the machine they protect, with restores that have actually been exercised.

## Leaving a course

When you are removed from a course — dropping it, or the roster changing — two things happen immediately:

- **Your key for that course is revoked.**  You can no longer make requests against it.
- **Your group membership is dropped.**  You lose access to the course instance.

Two things do not happen:

- **Your conversations stay** in that course's database.
- **The custody record of keys issued to you stays**, on purpose.  The escrow keeps a versioned history of what was issued to whom, and un-enrollment does not erase it.  A system that hands out credentials should be able to say what it handed out.

The distinction worth carrying away: **revoking access and erasing data are different acts**, and only the first one happens when you leave.

## When the term ends

Closing a course revokes its keys, renders a final configuration, and archives the group.  The course's web address stops resolving, and a bookmark from last term lands on a page explaining where things went and how to request a new environment.

**Archiving is not deleting.**  The material is still there; what changed is that nobody is using it.

!!! note "Not built yet"
    The course-close routine is planned and not yet implemented.  Courses that have ended are currently closed by hand.

## Asking for your data to be deleted

The part people come to this page for, so here it is plainly: **there is no per-student deletion path.**  Nothing walks a course database and removes one student's material.

There is a reason that is not simply an oversight, and it is worth understanding because it corrects an assumption most people carry.

**FERPA does not include a right to erasure.**  It gives students the right to inspect and review their education records, to seek amendment of records they believe are inaccurate or misleading, and to have some control over disclosure.  There is no delete-my-data provision in it.  That instinct comes from GDPR and state consumer privacy laws, which are different regimes with different triggers.

So per-student deletion here is a **policy choice an institution may make** rather than an obligation it is currently failing.  Worth adding immediately: state student privacy statutes frequently *do* address retention and deletion, and there are well over a hundred of them.  "FERPA does not require it" is not "nobody requires it," and which rules reach a given deployment is a question for the institution running it.

[What you can actually ask for](asking-about-your-data.md) covers the requests that do have answers today.

## What would have to change

Deletion is harder than it looks once backups exist, which is the honest engineering reason it has not been quietly added.  Removing a record from a live database is easy; removing it from every archive of that database is not, and an archive you can selectively edit is an archive you cannot trust.

The technique mature systems use is **crypto-shredding** — encrypt each subject's data under its own key and destroy the key rather than hunting the data.  It is written up in [How do you protect data you can't delete?](../how-we-built-it/protecting-data-you-cant-delete.md), which is where this page's problem gets treated as an engineering subject rather than a disclosure.
