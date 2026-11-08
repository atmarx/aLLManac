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

**{{PLATFORM}} keeps your data indefinitely, unless someone removes it by hand.**  Your conversations from a course that ended two terms ago are still in that course's database.

The one exception is *temporary chat* mode, and you can use it today.  A conversation you start in temporary chat mode is not kept: the database is told to delete it after a set period and does so on its own, without anyone deciding.  The mode is switched on by default here.  If you want a conversation not to persist, use it.  A temporary chat is the only conversation that deletes itself anywhere in this platform.  (Copies delete themselves too, such as an export link after a day and a backup after its schedule runs out, but the conversation they copied stays.)

We have confirmed on a running instance that the temporary-chat expiry is real: the database has the rule that does the deleting.  We have **not** set the window ourselves, so it is whatever the chat software ships with.  In the version we run, that default is **30 days**.

The 30-day figure was read out of the software's own source at the version pinned here, not measured by watching a conversation disappear.  It is good enough to plan a term around and not good enough to be a promise.  If something must be gone by a particular date, **delete it yourself and do not wait for the timer.**

Almost all conversations are *not* temporary chats.  The sections on retention, backups, leaving a course, the end of term, and deletion are about those ordinary conversations.

## Why there is no clock

Retention is a policy question before it is an engineering one.  Deciding that coursework should disappear after eighteen months means deciding what happens to a student's work when they want to look back at it, what an instructor can still reference, and what the institution is obliged to keep for its own reasons.

A retention policy does not exist here yet, so neither does the timer that would enforce it.  Building the timer first would mean guessing at the policy, and a deletion job is a bad place to guess.

!!! warning "Not built yet"
    No retention policy and no expiry for ordinary conversations.  Removal is a manual act by an operator.  The temporary-chat expiry is the single exception, and it is the chat software's own behavior, not a policy we set.  The software could put every conversation on that same clock.  We have not turned that on, because choosing the number is the policy question nobody has answered.

## Backups

The backup is built to run every night.  It copies everything that contains your work (conversations, agents, the documents and images you uploaded, the usage ledger, the key escrow) to storage that is not the machine it protects.  Copies are kept on a schedule: one for each of the last 7 days, the last 4 weeks, and the last 6 months.

!!! warning "Half built"
    The backup's copying half exists.  The **restore** half does not: there is no tested way yet to bring those copies back.  By our own rule, copies nobody has restored from are not backups yet.  What exists today is a second place your work is stored.

Backups matter to you in two ways, and they pull in opposite directions.  A backup protects you against losing your work.  A backup is also a second copy of your work, kept longer than most people picture when they delete something.  **A conversation you delete today is still in the backups for about six months**, until the last monthly copy containing it ages out.  Any retention policy worth the name has to account for both.

The word "backup" also promises more than the platform's backups deliver.  **A restore, as designed, is all-or-nothing.**  A restore returns the whole platform, every course at once, to the moment the copy was taken.  It undoes everyone's work since then, not just the thing someone wishes they still had.  The backups protect you against the machine failing, and do little for a mistaken click.  Keep your own copy of anything you would hate to lose.  That advice works whether or not any of the missing backup pieces get built.

The missing restore is the platform's most visible gap.  Restores are also where high-risk security baselines are most explicit about what they expect: scheduled backups, kept off the machine they protect, with restores that have been exercised.

## Leaving a course

When you are removed from a course, by dropping it or by the roster changing, your access ends on two different clocks:

- **Your key for that course is revoked at once.**  You can no longer make requests against it.
- **Your access to the course chat closes the next time it asks you to sign in.**  A chat you already have open is not cut off mid-sentence, and if you stay signed in that can be days later.  When it asks again, that course turns you away.

Sharing groups are not updated automatically when you leave a course.  If an instructor put you in a sharing group inside the course, you stay in it until someone removes you by hand.  With the course chat closed to you, the group gives you access to nothing, but your membership is still there.

When you leave a course, your data does not go anywhere:

- **Your conversations stay** in that course's database.
- **The custody record of keys issued to you stays**, by design.  The escrow keeps a versioned history of what was issued to whom, and un-enrollment does not erase it.  A system that hands out credentials should be able to say what it handed out.

**Revoking access and erasing data are different acts**, and only revoking access happens when you leave a course.

## When the term ends

A course ends in two steps, a couple of weeks apart, and an operator runs each one.

- **Closing** stops the spending.  Keys and the course chat stop answering, but you can still sign in, read your history, and open your agents for **14 days**.  The 14-day window is for taking your work with you.
- **Archiving** comes after the window.  Every key for the course is revoked, its sign-in is switched off, and the course's chat goes away.  The old web address then shows the same "there's no course here" page a mistyped address does, with a link to this site.  You can still export your own work from an archived course: ask the Student Guide in the {{PLATFORM}} chat.

Archiving a course is not deleting it.  The course's database is still there, and nobody can get into it through the chat anymore.  [Asking about your data](asking-about-your-data.md) covers exporting your own conversations and agents.

If your course has a stable address (`engr301.` instead of `engr301-2026fall.`), that address moves to the next term's course when the current course closes, so a syllabus link keeps working.

## Asking for your data to be deleted

**There is no per-student deletion path.**  Nothing walks a course database and removes one student's material.

**FERPA does not include a right to erasure**, so per-student deletion here is a **policy choice an institution may make**.  It is not an obligation the institution is currently failing, though state student-privacy laws may impose one.  Which rules apply is a question for the institution running the platform.  [What FERPA gives you](asking-about-your-data.md#what-ferpa-gives-you) has the rights that do exist and the requests that have answers today.

## What would have to change

Per-student deletion is harder than it looks once backups exist, and that is the engineering problem waiting behind the policy one.  Removing a record from a live database is easy.  Removing it from every archive of that database is not, and an archive you can selectively edit is an archive you cannot trust.

The technique mature systems use is **crypto-shredding**: encrypt each subject's data under its own key, and destroy the key instead of hunting for the data.  Crypto-shredding is written up in [How do you protect data you can't delete?](../how-we-built-it/protecting-data-you-cant-delete.md), which treats this problem as engineering.
