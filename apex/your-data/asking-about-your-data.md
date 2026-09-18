---
title: Asking about your data
description: What FERPA actually gives you, what it does not, and how to ask this platform for what it can currently provide.
audience: student
also_reaches: [faculty]
status: draft
owner: piper
tags: [ferpa, student-right, education-record, consent, gdpr, ccpa, secure-deletion]
regimes: [ferpa, gdpr, ccpa]
tethered_to:
  - usage-mcp/server.py
  - apex/your-data/how-long-we-keep-it.md
---

# Asking about your data

This page describes a law in general terms and describes what this platform can currently do.  It is not advice about your particular situation, and nothing here says the platform is compliant with anything — those are determinations for your institution and its counsel, not for a documentation page.

With that said, most of what people want to know is not complicated.

## What FERPA gives you

Four things, in plain terms.

- **You can inspect and review your education records.**
- **You can ask to have a record amended** if you believe it is inaccurate or misleading.
- **You must generally consent before the school discloses personally identifiable information** from those records — with a list of exceptions, one of which covers school officials with a legitimate educational interest.
- **You can file a complaint** with the U.S. Department of Education if you believe your rights have been violated.

Now the part that carries this page, because it is the one nearly everybody has backwards:

> **There is no right to deletion in FERPA.**

You can look, and you can argue that something is wrong and ask for it to be corrected.  There is no provision that makes the institution erase your records because you would prefer they were gone.

That instinct is not foolish — it is trained.  GDPR has a right to erasure, and several state consumer privacy laws have something like one, and those regimes are genuinely different: different triggers, different obligations, different people covered.  **Knowing which regime grants which right is the actual skill**, and it is worth more than memorising any single one of them.  A right you assume you have is a right you will not ask for correctly.

Worth adding immediately, because "FERPA does not require it" is not "nobody requires it": state student-privacy statutes frequently *do* address retention and deletion, and there are well over a hundred of them.  Which ones reach a given deployment is a question for the institution running it.

## Are chat conversations an education record?

Records that are directly related to a student and maintained by the institution are education records.  Course conversations tied to your identity look very much like that.

!!! note "Under review"
    Whether these conversations are formally education records is a determination for university counsel, and it has not been made.  The platform's posture in the meantime is to treat them as though they are.

That is a posture, not a legal conclusion, and it is the conservative direction on purpose.  Treating them as records and later learning they are not costs us some care we did not owe.  Guessing the other way and being wrong costs somebody else something they cannot get back.

## What you can do today

**See your own usage.**  Ask the usage tool in the chat about your own activity and it will tell you which models you used, how many tokens, and when.  It reads the ledger by your email address, so it spans every course you are in.

**See your own conversations.**  They are in your account, in the course instance where you had them.  Nobody has to send them to you.

**Ask your instructor** what their course's own practice is.  Retention below the platform level is theirs to set, and they may have said something in the syllabus.

**For a formal records request, go to your university's Registrar's Office** — the campus office that handles student records.  (This platform has a service of its own confusingly called the registrar, which provisions courses and rosters.  It is not that.  You want the office.)  The formal FERPA process belongs to the institution and runs on paper, not through this software.

!!! warning "Not built yet"
    There is no self-service path here for a formal request — nothing you can click to package up everything the platform holds about you, and no per-student deletion.  A request like that is currently handled by a person, by hand.  [How long we keep it](how-long-we-keep-it.md) is the honest account of why, and what would have to change.

## If you go on to build systems like this

The mistake to avoid is the one this page opened with, and it is easier to make from the builder's chair than the student's: **assuming that one privacy regime's rights apply to another regime's data.**

It produces two opposite failures and both are expensive.  You build an erasure feature nobody required, in a system where erasure is genuinely hard, and it becomes the thing you cannot honestly promise about your backups.  Or you skip one that was required, because the regime you had in mind did not ask for it.

The engineering version of this problem — what it actually takes to delete something from a system that keeps copies of itself — is [How do you protect data you can't delete?](../how-we-built-it/protecting-data-you-cant-delete.md).
