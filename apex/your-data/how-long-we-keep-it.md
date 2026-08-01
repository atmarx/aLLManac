---
title: How long we keep it
description: Retention, backups, what survives leaving a course, and what happens when the term ends — including the parts we have not built.
audience: student
also_reaches: [faculty]
status: scaffold
owner: piper
tags: [retention, backup, restore, archival, secure-deletion, course-rollover, escrow, disaster-recovery, ferpa]
regimes: [ferpa]
tethered_to:
  - justfile
  - docs/admin-guide.md#backups
  - docs/registrar-spec.md
---

# How long we keep it

<!-- SCAFFOLD.  The most gap-heavy page in the section.  Write it straight —
     every soft phrase here is a promise the system has to keep. -->

## The honest answer right now

<!-- Lead with it: there is no automated retention expiry.  Conversations
     stay in the course database until someone removes them, and today that
     is a manual act.  Say it in the first paragraph rather than the last. -->

## Backups

<!-- What is real: a documented procedure that dumps each database, run by
     hand by an operator.

     !!! warning "Not built yet"
         `just backup` — the nightly timestamped tarball with off-box copies
         — is designed and not implemented.  There is no schedule, no
         off-box copy, and no tested restore.  Tracked as plumbing work.

     Explain what a backup means for a student: a copy of your work exists,
     which is protection against loss and also a second place the data
     lives.  Both halves are true and students should hear both. -->

## Leaving a course

<!-- Removal revokes your key for that course and drops your group
     membership, so access stops.  Your conversations remain in the course
     database.  Escrow keeps the custody history of keys minted for you —
     deliberately, so there is a record of what was issued to whom.

     Name the distinction that matters: revoking access and erasing data are
     different acts, and only the first one happens today. -->

## When the term ends

<!-- course-close (not built — Phase 3): revoke all keys, final render,
     archive the group.  The course's web address stops resolving and last
     term's bookmark lands on a friendly page.

     Archive is not deletion.  Be explicit. -->

## Deletion on request

<!-- The page students will actually come here for.

     Current state: no path exists that walks the course database and
     removes one student's conversations.

     The reason it is not simply an oversight, and the teaching beat:
     FERPA grants inspection, amendment, and consent-to-disclosure rights.
     It does not grant a right to erasure — that instinct comes from GDPR
     and CCPA.  So per-student deletion is a policy choice the university
     may make rather than an obligation it is currently failing.

     Say what a student can do today (see asking-about-your-data.md) and
     link the builder-facing treatment in
     how-we-built-it/protecting-data-you-cant-delete.md.

     TETHER: when a deletion path ships, this section and the section in
     your-data/index.md change in the same commit. -->
