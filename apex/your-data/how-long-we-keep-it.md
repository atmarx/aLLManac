---
title: How long we keep it
description: Retention, backups, what survives leaving a course, what happens at the end of term, and the parts that are not built yet.
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

**Indefinitely, unless someone removes it by hand.**  Your conversations from a course that ended two terms ago are still in that course's database.

There is one exception, and you can use it today.  The chat window has a *temporary chat* mode, and a conversation you start in it is not kept — the database is told to delete it after a set period and does so on its own, without anyone deciding.  It is switched on by default here: it is a privacy affordance, and we treat it as one.  If you want a conversation not to persist, use it.  It is the only conversation that deletes itself anywhere in this platform.  (Copies delete themselves too — an export link after a day, a backup after its schedule runs out — but the conversation they copied stays.)

Two caveats.  We have confirmed the expiry is real on a running instance — the database has the rule that does the deleting — and we have **not** set the window ourselves, so it is whatever the chat software ships with.  In the version we run, that shipped default is **30 days**.

That figure was read out of the software's own source at the version pinned here, not measured by watching a conversation disappear.  It is good enough to plan a term around and not good enough to be a promise.  If something must be gone by a particular date, **delete it yourself and do not wait for the timer.**

Everything below is about conversations that are *not* temporary chats, which is almost all of them.

## Why there is no clock

Retention is a policy question before it is an engineering one.  Deciding that coursework should disappear after eighteen months means deciding what happens to a student's work when they want to look back at it, what an instructor can still reference, and what the institution is obliged to keep for its own reasons.

That policy does not exist here yet, so neither does the timer that would enforce it.  Building the timer first would mean guessing at the answer, and a deletion job is a bad place to guess.

!!! warning "Not built yet"
    No retention policy and no expiry for ordinary conversations.  Removal is a manual act by an operator.  The temporary-chat expiry above is the single exception, and it is the chat software's own behaviour, not a policy we set.  The software could put every conversation on that same clock; we have not turned it on, because choosing the number is the policy question nobody has answered.

## Backups

The backup is built to run every night, copying everything that holds your work — conversations, agents, the documents you uploaded (not images — those are not copied yet), the usage ledger, the key escrow — to storage that is not the machine it protects.  Copies are kept on a schedule: one for each of the last 7 days, the last 4 weeks, and the last 6 months.

!!! warning "Half built"
    The copying half exists.  The **restore** half does not — there is no tested way yet to bring those copies back — and by our own rule, copies nobody has restored from are not backups yet.  What exists today is a second place your work lives.

Both halves matter to you, and they pull in opposite directions.  A backup protects you against losing your work.  It is also a second copy of your work, kept longer than most people picture when they delete something.  **A conversation you delete today is still in the backups for about six months**, until the last monthly copy holding it ages out.  Any retention policy worth the name has to account for both.

The word "backup" also promises more than it delivers.  **A restore, as designed, is all-or-nothing.**  It returns the whole platform — every course at once — to the moment the copy was taken.  That undoes everyone's work back to that moment, not just the thing someone wishes they still had.  So a copy of your material protects you against the machine failing, and does little for a mistaken click.  Keeping your own copy of anything you would hate to lose is advice that works whether or not any of this gets built.

This is the platform's most visible gap.  It is also where high-risk security baselines are most explicit about what they expect: scheduled backups, kept off the machine they protect, with restores that have been exercised.

## Leaving a course

When you are removed from a course — dropping it, or the roster changing — your access ends on two different clocks:

- **Your key for that course is revoked at once.**  You can no longer make requests against it.
- **Your access to the course chat closes the next time it asks you to sign in.**  A chat you already have open is not cut off mid-sentence, and if you stay signed in that can be days later.  When it asks again, that course turns you away.

Sharing groups are not automatic: if an instructor put you in one inside the course, you stay in it until someone removes you by hand.  With the chat closed to you, it gives you access to nothing, but it is there.

Your data does not go anywhere:

- **Your conversations stay** in that course's database.
- **The custody record of keys issued to you stays**, by design.  The escrow keeps a versioned history of what was issued to whom, and un-enrollment does not erase it.  A system that hands out credentials should be able to say what it handed out.

**Revoking access and erasing data are different acts**, and only the first one happens when you leave.

## When the term ends

A course ends in two steps, a couple of weeks apart, and an operator runs each one.

- **Closing** stops the spending.  Keys and the course chat stop answering, but you can still sign in, read your history, and open your agents for **14 days** — that window is for taking your work with you.
- **Archiving** comes after the window.  Every key for the course is revoked, its sign-in is switched off, and the course's chat goes away.  The old web address now shows the same page a mistyped one does — there's no course here — with a link to this site.  You can still export your own work from an archived course: ask the Student Guide in the {{PLATFORM}} chat.

Archiving is not deleting.  The course's database is still there; nobody can get into it through the chat any more.  Your own conversations and agents can still be exported from an archived course — see [Asking about your data](asking-about-your-data.md).

If your course has a stable address — `engr301.` instead of `engr301-2026fall.` — that address moves to the next term's course when this one closes, so a syllabus link keeps working.

## Asking for your data to be deleted

**There is no per-student deletion path.**  Nothing walks a course database and removes one student's material.

That is not an oversight, and the reason corrects an assumption most people make.

**FERPA does not include a right to erasure.**  It gives students the right to inspect and review their education records, to seek amendment of records they believe are inaccurate or misleading, and to have some control over disclosure.  There is no delete-my-data provision in it.  That instinct comes from GDPR and state consumer privacy laws, which are different regimes with different triggers.

So per-student deletion here is a **policy choice an institution may make**.  It is not an obligation the institution is currently failing.  State student privacy statutes, though, frequently *do* address retention and deletion, and there are well over a hundred of them.  "FERPA does not require it" is not "nobody requires it," and which rules apply to a given deployment is a question for the institution running it.

[Asking about your data](asking-about-your-data.md) covers the requests that do have answers today.

## What would have to change

Deletion is harder than it looks once backups exist, and that is the engineering reason nobody has slipped it in.  Removing a record from a live database is easy; removing it from every archive of that database is not, and an archive you can selectively edit is an archive you cannot trust.

The technique mature systems use is **crypto-shredding** — encrypt each subject's data under its own key, and destroy the key instead of hunting the data.  It is written up in [How do you protect data you can't delete?](../how-we-built-it/protecting-data-you-cant-delete.md), which treats this problem as engineering.
