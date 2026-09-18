---
title: If you're evaluating this for your course
description: What we are actually asking early instructors to look for — including the failure that is easiest to miss, because it looks like the platform behaving politely.
audience: faculty
also_reaches: [operator]
status: draft
owner: piper
tags: [ai-literacy, accountability, hallucination, critical-evaluation, faculty-duty, source-verification]
tethered_to:
  - docs/agent-contract.md
---

# If you're evaluating this for your course

Thank you for taking the time.  This page is short on purpose, and it is the only thing we are asking you to read before you start.

**Use it the way you would actually use it.**  Not a test script — your real course, your real syllabus, the question you would genuinely have asked on a Tuesday.  Scripted evaluation finds scripted problems.

## The failure we most need you to report

When something goes wrong with an AI system, the report people file is *it told me something false.*  That one matters, and it is also the one we are best equipped to catch ourselves.

The failure we cannot see from here is the opposite:

> **A guide told you it could not help, and you think it should have.**

That is the one that costs us a course, and it never generates a complaint, because it does not look like a malfunction.  It looks like caution.  You ask how to add a student to your class, the assistant explains politely that this is not something it can help with, and you close the tab having concluded the platform does not do that — when in fact it does, and the guide simply failed to find its own documentation.

We have watched this happen.  One of our guides sent an instructor to the university Registrar's Office because the word "registrar" means something different inside this platform than it does on campus.  Everything it said was locally reasonable and the outcome was completely wrong.

So: **if you were redirected, refused, or told something was out of scope, and your instinct was that it should have known — that is a bug report.**  Please send it even if you are not sure.  Especially then.

## The other one worth catching

Confident and wrong, delivered in the same voice as confident and right.

The guides are instructed to answer only from the documentation attached to them, and to say plainly when something is not in their files.  When that holds, it works well.  When it slips, the tell is usually a specific detail that sounds authoritative — a port number, a price, a file path, a procedure with steps.  If a number or a path looks oddly precise, it is worth a second glance.

## What to send

The exchange, copied verbatim.  Not a summary — the summary is where the evidence goes.

Three things make a report much more useful:

1. **Which guide you were talking to.**  There are several, and they hold different documents.
2. **What you asked just before.**  Some failures only appear in the second or third turn; a conversation that was fine at the start and drifted somewhere strange is a more interesting report than a single bad answer.
3. **What you expected instead.**  Even roughly.  You know your course; we are guessing at it.

Send it to whoever pointed you at this platform.

## What we already know

So you do not spend your time on things that are on our list:

- **Backups are thin.**  Copies are made by hand, there is no off-box schedule yet, and no restore has been tested end to end.  [How long we keep it](your-data/how-long-we-keep-it.md) is honest about this.
- **Nothing expires on its own**, and there is no per-student deletion path.
- **Some pages on this site are unfinished**, and say so where you land on them.
- **Knowledge files belong to the course they were uploaded in.**  They do not follow an agent between courses — if you build an agent in one course and want it in another, the documents get attached again on the other side.  This is a consequence of how courses are kept apart and it is not going to change.
- **Agent knowledge files were broken until 18 September**, silently — the upload appeared to succeed and the agent never used the document.  It is fixed, and every course now runs its own document service rather than sharing one.  If your course was set up before that and attaching a file still does nothing, say so immediately; it means your course has not been re-rendered, and that is worth knowing fast.  The whole episode is [written up](how-we-built-it/keeping-courses-apart.md) rather than hidden.

If something on that list is a blocker for the course you have in mind, that is worth telling us too — it changes what gets built first.

## What we are not asking you to do

Try to break it.

You are welcome to, and you will not hurt anything.  But deliberately probing the boundaries is a later phase with student teams whose actual assignment is to find the holes, and it is their job rather than yours.  If you happen to trip over something alarming, by all means say so.  Otherwise, the most useful thing you can do is be an ordinary demanding user with a real course to run.
