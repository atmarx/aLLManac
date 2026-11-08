---
title: "{{PLATFORM}}"
description: An institutional AI sandbox.  Use large language models in your courses, build with them, and read how the platform underneath was put together.
audience: student
also_reaches: [faculty]
status: draft
owner: piper
tags: [librechat, tenancy, ai-literacy, student-right, faculty-duty]
---

# {{PLATFORM}}

Sign in with the account you already use for everything else on campus, and in about five minutes you can have an assistant that has read your syllabus and will answer questions about it.

Each course on {{PLATFORM}} has its own AI service: an instance with the course's name on it, running on hardware your institution owns.  A whole project team can build **one shared assistant together**, and every token spent is recorded on a ledger your course can see.

The sign-in button is on the front page of your course's instance.  If you do not know that address yet, ask the Front Desk in the {{PLATFORM}} chat which courses you're on.  The Front Desk lists each of your courses with its address.  You can also ask your instructor.

## Start here

**I'm taking a course that uses this.**
Start with [Using it in a course](user-guide.md).  It walks through building your first agent, working on one as a team, and pointing your own code at the campus gateway with an API key.

**I teach, and I'm deciding what to do about all this.**
Start with [Teaching with AI](teaching-with-ai/index.md), which is about course design.  When you are ready for the mechanics, [Teaching a course](teaching-a-course.md) is the walkthrough for rosters, shared agents, and watching your course's spend, all from the browser.  If you are trying the platform out before committing a class to it, [read this first](evaluating-it.md).

**I want to know what happens to my work.**
[Your data](your-data/index.md) covers what gets stored, who can see it, how long it stays, and which parts we have not built yet.

## Learning to use it

Much of the skill in using an agent is *curation*: choosing what to give it.  An agent is a block of instructions plus the files you hand it.  The difference between an agent that helps and one that wastes your afternoon is almost always which files you chose.

[Using it in a course](user-guide.md) covers the mechanics: your first agent, a team-built one with co-editors, your API key, and the coding harness.  [Verifying sources](teaching-with-ai/verifying-sources.md) covers the habit that makes any of it trustworthy.

You can also ask the platform about itself.  The guides are agents in the {{PLATFORM}} chat, which you pick from the selector at the top, and each guide has part of this documentation attached.  A guide will tell you when a question is outside what it knows.  Most assistants never tell you that, so pay attention when a guide does.

## Teaching with it

Your students already have access to AI.  That access changes some of your assignments and leaves others alone, and deciding which is which is a teaching question.

[Teaching with AI](teaching-with-ai/index.md) covers that work.  It starts from one principle: **a student is fully responsible for what they submit.  A model cannot accept blame.**  With that principle in place, most of the hard questions get easier.  The question stops being *did you use AI*, which can't be answered and matters less and less, and becomes *do you stand behind this*, the question scholarship has always asked.

The Teaching with AI pages:

- [Designing assignments](teaching-with-ai/designing-assignments.md): what to change, and what to leave alone
- [Your syllabus policy](teaching-with-ai/syllabus-policy.md): language you can use as written
- [Integrity and detection](teaching-with-ai/integrity-and-detection.md): what the evidence says, including about detectors
- [AI literacy](teaching-with-ai/ai-literacy.md): treating it as a learning objective
- [If you teach a course](your-data/for-instructors.md): the duties that come with the roster

## Learning to build it

The platform is also course material.  The reasons behind every significant decision in it are written down.  The reasoning transfers: you will meet the same trade-offs on a stack that looks nothing like this one.

[How we built it](how-we-built-it/index.md) collects those write-ups, and new ones are added as the build settles.  Start with [How do you keep the courses apart?](how-we-built-it/keeping-courses-apart.md), which is about tenancy and ends on a gap we have not closed yet.

## Your data

Coursework generates records about you, and records about students come with obligations.

Your conversations are stored in your own course's database, and nobody in another course can read them.  Your usage is recorded against your email address: which model, how many tokens, and when, but not what you said.  Nothing expires on its own except a temporary chat, which is deleted after 30 days.  Nothing you build is shared until you share it.

The full account, including the parts that are not built yet, is in [Your data](your-data/index.md).

---

*To find every page on one topic, such as retention, access control, or academic integrity, use [Browse by topic](tags.md).*
