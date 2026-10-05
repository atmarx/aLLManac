---
title: Asking about your data
description: What FERPA gives you, what it does not, and how to ask this platform for what it can currently provide.
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

What follows describes a law in general terms and what this platform can currently do.  It is not advice about your particular situation, and nothing here says the platform is compliant with anything — those are determinations for your institution and its counsel, not for a help site.

## What FERPA gives you

The Department of Education [lists these rights](https://studentprivacy.ed.gov/ferpa); the regulation itself is [34 CFR Part 99](https://www.ecfr.gov/current/title-34/subtitle-A/part-99).

- **You can inspect and review your education records.**
- **You can ask to have a record amended** if you believe it is inaccurate or misleading.
- **You must generally consent before the school discloses personally identifiable information** from those records — with a list of exceptions, one of which covers school officials with a legitimate educational interest.
- **You can file a complaint** with the U.S. Department of Education if you believe your rights have been violated.

What nearly everybody has backwards:

> **There is no right to deletion in FERPA.**

You can look, and you can argue that something is wrong and ask for it to be corrected.  There is no provision that makes the institution erase your records because you would prefer they were gone.

The instinct to expect one is learned, and reasonable.  GDPR has a right to erasure, and several state consumer privacy laws have something like one — about twenty states have passed comprehensive consumer privacy laws ([IAPP's tracker](https://iapp.org/resources/article/us-state-privacy-legislation-tracker/) keeps the current count).  Those regimes are different: different triggers, different obligations, different people covered.  Knowing which regime grants which right is the useful skill.  A right you assume you have is a right you will not ask for correctly.

"FERPA does not require it" is not "nobody requires it," though.  State student-privacy statutes frequently *do* address retention and deletion, and there are well over a hundred of them — the Future of Privacy Forum [counted almost 120 by 2019](https://fpf.org/press-releases/future-of-privacy-forum-releases-policymakers-guide-to-student-data-privacy/), most of them written for K-12.  Which ones apply to a given deployment is a question for the institution running it.

## Are chat conversations an education record?

Records that are directly related to a student and maintained by the institution are education records.  Course conversations tied to your identity look very much like that.

!!! note "Under review"
    Whether these conversations are formally education records is a determination for university counsel, and it has not been made.  In the meantime, the platform treats them as though they are.

That is a working assumption, not a legal conclusion, and it errs in the conservative direction.  Treating them as records and later learning they are not costs us some care we did not owe.  Guessing the other way and being wrong costs somebody else something they cannot get back.

## What you can do today

**See your own usage.**  Ask the **Usage Guide** in the {{PLATFORM}} chat about your own activity and it will tell you which models you used, how many tokens, and when.  It reads the ledger by your email address, so it covers every course you are in.

**See your own conversations.**  While a course is running — and for 14 days after it closes — they are in your account, in the course's chat.  Nobody has to send them to you.

**Take a copy of your own work.**  Ask the **Student Guide** in the {{PLATFORM}} chat to export your data, naming the course.  You get a zip of every conversation you had in that course, both sides, and every agent you own, behind a link that works for 24 hours.  It works on a course that has closed or been archived, too.  Files you uploaded are listed in it but not included, and conversations with the guides in the {{PLATFORM}} chat are not part of it.

**Ask your instructor** what their course's own practice is.  There is no retention setting for them to change — retention is the institution's policy, and it has not set one — but they may have said something in the syllabus about what they keep and why.

**For a formal records request, go to your university's Registrar's Office** — the campus office that handles student records.  (This platform's course service keeps course rosters, but it is not a records office.  You want the office.)  The formal FERPA process belongs to the institution and runs on paper, not through this software.

!!! warning "Not built yet"
    The export above is your conversations and agents.  It is not everything the platform holds about you — not your usage records, your identity record, the history of keys issued to you, or your chats with the guides in the {{PLATFORM}} chat — and there is no per-student deletion.  A request for those is currently handled by a person, by hand.  [How long we keep it](how-long-we-keep-it.md) explains why, and what would have to change.

## If you go on to build systems like this

The mistake to avoid is the one in the FERPA section above, and it is easier to make as a builder than as a student: **assuming that one privacy regime's rights apply to another regime's data.**

It produces two opposite failures, and both are expensive.  You build an erasure feature nobody required, in a system where erasure is hard, and it becomes the thing you cannot truthfully promise about your backups.  Or you skip one that was required, because the regime you had in mind did not ask for it.

The engineering version of this problem — what it takes to delete something from a system that keeps copies of itself — is [How do you protect data you can't delete?](../how-we-built-it/protecting-data-you-cant-delete.md).
