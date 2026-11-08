---
title: If you're evaluating this for your course
description: What we are asking early instructors to look for, including the easiest failure to miss, a guide that politely refuses when it should have helped.
audience: faculty
also_reaches: [operator]
status: draft
owner: piper
tags: [ai-literacy, accountability, hallucination, critical-evaluation, faculty-duty, source-verification]
tethered_to:
  - docs/agent-contract.md
---

# If you're evaluating this for your course

Thank you for trying {{PLATFORM}} with your course.  We ask you to read only this guidance before you start.

**Use the platform the way you would use it for real:** with your real course, your real syllabus, and the questions you would ask in an ordinary week.  A scripted evaluation only finds the problems the script expects.

## The failure we most need you to report

When something goes wrong with an AI system, the report people file is *it told me something false.*  That kind of report matters, and false answers are also the failure we are best equipped to catch ourselves.

The failure we cannot see from our side is a guide refusing when it should have helped:

> **A guide told you it could not help, and you think it should have.**

A wrong refusal can cost us a course, and it never produces a complaint.  It looks like caution, so nobody reports it as a malfunction.  For example, you ask how to add a student to your class, the assistant explains politely that it can't help with that, and you close the tab believing the platform can't do it.  In fact the platform can, and the guide failed to find its own documentation.

We have seen a wrong refusal happen.  One of our guides sent an instructor to the university Registrar's Office.  The word "registrar" means something different inside this platform than it does on campus.  Each step of the guide's answer was reasonable on its own, and the outcome was completely wrong.  The platform's tools for that work are now called the course service to avoid the confusion.

**If a guide redirected you, refused, or told you something was out of scope, and you think it should have known the answer, report it as a bug.**  Please send the report even if you are not sure it is a bug.  The uncertain cases are the ones we most need.

## The other one worth catching

The second failure to watch for is a guide that is confident and wrong, in the same voice it uses when it is confident and right.

The guides are instructed to answer only from the documentation attached to them, and to say so when something is not in their files.  When a guide follows those instructions, it works well.  When a guide slips, the sign is usually a specific detail that sounds authoritative, such as a port number, a price, a file path, or a procedure with steps.  If a number or a path in a guide's answer looks oddly precise, check it.

## What to send

Send the exchange with the guide, copied verbatim.  A summary loses the evidence we need.

A report is much more useful when it includes:

1. **Which guide you were talking to.**  There are several, and each has different documents.
2. **What you asked just before.**  Some failures only appear in the second or third turn.  A conversation that was fine at the start and drifted somewhere strange is a more interesting report than a single bad answer.
3. **What you expected instead.**  A rough description is enough.  You know your course, and we can only guess at it.

**You can also report a problem in the {{PLATFORM}} chat, which is easier and works better.**  Tell the guide what went wrong, for example *"that answer was wrong"* or *"this should work differently,"* and the guide will offer to file a report for you.  Every guide except the Front Desk can file reports.  The Front Desk only sends you to the right guide.  Agents in your course's chat can't file reports unless staff attach a report tool to them.  If you say yes, the guide files the report itself, with your question and its answer already attached.  The guide asks once and files in one step, with no draft for you to approve, so say anything you want in the report when you say yes.

Reporting through a guide works better than email.  A report is only actionable if it includes what was asked and what came back, and nobody wants to assemble that by hand at the moment they are annoyed.  The guide already has both.

A guide will not offer to file a report until it has searched its documentation.  The guides are not allowed to offer escalation in place of an answer they could have given.  If a guide answers you properly and *then* asks whether to pass something on, that is the intended order.

Filing a report through a guide sends you no email, no ticket number, and no notifications from a second system.  Ask the guide for **your reports** any time, and it tells you the status of each one: still open, being looked at, or closed with what was done about it.

If you would rather not use the chat, send your report to whoever pointed you at this platform.

## What we already know

We already know about the following problems, so you do not need to spend time reporting them:

- **Backups are half built.**  They run nightly, but a restore is not built.  [Backups](your-data/how-long-we-keep-it.md#backups) has the details.
- **Nothing expires on its own** except a temporary chat, which is deleted after 30 days.  There is no per-student deletion path.
- **Some pages on this site are unfinished**, and say so on the page.
- **Knowledge files belong to the course they were uploaded in.**  If you build an agent in one course and want it in another, the documents have to be attached again in the other course.  This follows from how courses are kept apart, and it is not going to change.
- **Agent knowledge files were broken until September 18**, with no visible error: the upload appeared to succeed, and the agent never used the document.  The bug is fixed, and every course now runs its own document service.  If your course was set up before that date and attaching a file still does nothing, tell us immediately.  That symptom means your course has not been re-rendered.  The whole episode is [written up](how-we-built-it/keeping-courses-apart.md).

If any of these known problems would block the course you have in mind, tell us that too.  Blockers change what gets built first.

## What we are not asking you to do

We are not asking you to try to break the platform.

You are welcome to try, and you will not hurt anything.  Probing the boundaries is another group's assignment.  The most useful thing you can do is be an ordinary, demanding user with a real course to run.  If you happen to find something alarming, please report it.

The exception is the staff cohort.  The first group on this platform is a staff cohort whose course is to take the platform apart, and their findings are the point of that course.  If you are in that cohort, the other requests for evaluators still apply to you: a polite refusal is still the report we most need.  Send it even when a more dramatic finding sits right next to it.
