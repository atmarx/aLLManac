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

The honest answer, first: **indefinitely, unless someone removes it by hand.**  Your conversations from a course that ended two terms ago are still in that course's database.

**With one exception, and it is the one thing on this page you can act on today.**  The chat window has a *temporary chat* mode, and a conversation you start in it is not kept — the database is told to delete it after a set period and does so on its own, without anyone deciding.  It is switched on by default here, deliberately, because it is a privacy affordance rather than a feature.  If you want a conversation not to persist, that is the way to get it, and it is the only conversation that deletes itself anywhere in this platform.  (Copies delete themselves too — an export link after a day, a backup after its schedule runs out — but the conversation they copied stays.)

Two honest caveats attached to that.  We have confirmed the expiry is real on a running instance — the database carries the rule that does the deleting — and we have **not** set the window ourselves, so it is whatever the chat software ships with.  Read in the version we run, that shipped default is **30 days**.

We are telling you the number rather than withholding it, and telling you where it comes from in the same breath: it was read out of the software's own source at the version pinned here, not measured by watching a conversation disappear.  That is good enough to plan a term around and not good enough to be a promise — so if something genuinely must be gone by a particular date, **delete it yourself and do not wait for the timer.**  An earlier draft of this page declined to name any figure at all, which felt careful and was not: *"it goes away on a timer we have not published"* leaves you unable to plan while sounding like we are protecting you from something.

The rest of this page is about everything that is *not* a temporary chat, which is almost all of it.

## Why there is no clock

Retention is a policy question before it is an engineering one.  Deciding that coursework should disappear after eighteen months means deciding what happens to a student's work when they want to look back at it, what an instructor can still reference, and what the institution is obliged to keep for its own reasons.

That policy does not exist here yet, so neither does the timer that would enforce it.  Building the timer first would mean guessing at the answer, and a deletion job is a bad place to guess.

!!! warning "Not built yet"
    No retention policy and no expiry for ordinary conversations.  Removal is a manual act by an operator.  The temporary-chat expiry above is the single exception, and it is the chat software's own behaviour rather than a policy we set.

## Backups

The backup is built to run every night, copying everything that holds your work — conversations, agents, the files you uploaded, the usage ledger, the key escrow — to storage that is not the machine it protects.  Copies are kept on a schedule: one for each of the last 7 days, the last 4 weeks, and the last 6 months.

!!! warning "Half built"
    The copying half exists.  The **restore** half does not — there is no tested way yet to bring those copies back — and a backup nobody has restored from is a rumor, so by our own rule there are no backups yet.  What is real today is a second place your work lives.

Both halves of that matter to you and they point in opposite directions.  A backup is protection against losing your work, and it is also a second place your work lives, which is a longer tail than most people picture when they delete something.  **A conversation you delete today is still in the backups for about six months**, until the last monthly copy holding it ages out.  Any honest retention policy has to account for both.

It is worth being clear about what a backup is *not*, because the word promises more than it delivers.  **A restore, as designed, is all-or-nothing.**  It returns the whole platform — every course at once — to the moment the copy was taken, which means it undoes everyone's work back to that moment, not just the thing someone wishes they still had.  That is why a copy of your material is a real protection against the machine failing and a poor protection against a mistaken click — and why keeping your own copy of anything you would hate to lose is the advice that does not depend on any of this being built.

This is the platform's most visible gap, and it is the one where a high-risk posture is most explicit about what it expects: scheduled backups, kept off the machine they protect, with restores that have actually been exercised.

## Leaving a course

When you are removed from a course — dropping it, or the roster changing — two things happen, on different clocks:

- **Your key for that course is revoked at once.**  You can no longer make requests against it.
- **Your access to the course chat closes at your next sign-in.**  A chat you already have open is not cut off mid-sentence; the next time you sign in, that course turns you away.

One more is not automatic: if an instructor put you in a sharing group inside the course, you stay in it until someone removes you by hand.  With the chat closed to you it reaches nothing, but it is there.

Two things do not happen:

- **Your conversations stay** in that course's database.
- **The custody record of keys issued to you stays**, on purpose.  The escrow keeps a versioned history of what was issued to whom, and un-enrollment does not erase it.  A system that hands out credentials should be able to say what it handed out.

The distinction worth carrying away: **revoking access and erasing data are different acts**, and only the first one happens when you leave.

## When the term ends

A course ends in two steps, a couple of weeks apart, and an operator runs each one.

- **Closing** stops the spending.  Keys and the course chat stop answering, but you can still sign in, read your history, and open your agents for **14 days** — that window is for taking your work with you.
- **Archiving** comes after the window.  Every key for the course is revoked, its sign-in is switched off, and the course's chat goes away.  The old web address lands on a page that says the course is finished and points you to your instructor and to this site.

**Archiving is not deleting.**  The course's database is still there; what changed is that nobody can get into it through the chat.  Your own conversations and agents can still be exported from an archived course — see [What you can actually ask for](asking-about-your-data.md).

If your course has a stable address — `engr301.` rather than `engr301-2026fall.` — that address moves to the next term's course when this one closes, so a syllabus link keeps working.

## Asking for your data to be deleted

The part people come to this page for, so here it is plainly: **there is no per-student deletion path.**  Nothing walks a course database and removes one student's material.

There is a reason that is not simply an oversight, and it is worth understanding because it corrects an assumption most people carry.

**FERPA does not include a right to erasure.**  It gives students the right to inspect and review their education records, to seek amendment of records they believe are inaccurate or misleading, and to have some control over disclosure.  There is no delete-my-data provision in it.  That instinct comes from GDPR and state consumer privacy laws, which are different regimes with different triggers.

So per-student deletion here is a **policy choice an institution may make** rather than an obligation it is currently failing.  Worth adding immediately: state student privacy statutes frequently *do* address retention and deletion, and there are well over a hundred of them.  "FERPA does not require it" is not "nobody requires it," and which rules reach a given deployment is a question for the institution running it.

[What you can actually ask for](asking-about-your-data.md) covers the requests that do have answers today.

## What would have to change

Deletion is harder than it looks once backups exist, which is the honest engineering reason it has not been quietly added.  Removing a record from a live database is easy; removing it from every archive of that database is not, and an archive you can selectively edit is an archive you cannot trust.

The technique mature systems use is **crypto-shredding** — encrypt each subject's data under its own key and destroy the key rather than hunting the data.  It is written up in [How do you protect data you can't delete?](../how-we-built-it/protecting-data-you-cant-delete.md), which is where this page's problem gets treated as an engineering subject rather than a disclosure.
