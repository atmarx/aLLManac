---
title: "{{PLATFORM}}"
description: An institutional AI sandbox — use large language models in your courses, build with them, and read how the platform underneath was put together.
audience: student
also_reaches: [faculty]
status: draft
owner: piper
tags: [librechat, tenancy, ai-literacy, student-right, faculty-duty]
---

# {{PLATFORM}}

Sign in with the account you already use for everything else on campus, and in about five minutes you can have an assistant that has read your syllabus and will answer questions about it.

Behind that, your course has its own AI service: an instance with your course's name on it, running on hardware your institution owns.  A whole project team can build **one shared assistant together**, and every token spent goes on a ledger your course can see.

The sign-in button is on the front page of your course's instance.  If you do not know that address yet, ask the Front Desk in the {{PLATFORM}} chat which courses you're on — it lists each one with its address — or ask your instructor.

## Start here

**I'm taking a course that uses this.**
Start with [Using it in a course](user-guide.md).  It walks through building your first agent, working on one as a team, and pointing your own code at the campus gateway with an API key.

**I teach, and I'm deciding what to do about all this.**
Start with [Teaching with AI](teaching-with-ai/index.md), which is about course design.  When you are ready for the mechanics, [Teaching a course](teaching-a-course.md) is the walkthrough — rosters, shared agents, watching your course's spend, all of it from the browser.  If you are trying the platform out before committing a class to it, [read this first](evaluating-it.md).

**I want to know what happens to my work.**
[Your data](your-data/index.md) covers what gets stored, who can see it, how long it stays, and which parts we have not built yet.

## Learning to use it

People underestimate how much of the skill is *curation*.  An agent is a block of instructions plus the files you hand it, and the difference between one that helps and one that wastes your afternoon is almost always which files you chose.

[Using it in a course](user-guide.md) covers the mechanics — your first agent, a team-built one with co-editors, your API key, and the coding harness.  [Verifying sources](teaching-with-ai/verifying-sources.md) covers the habit that makes any of it trustworthy.

You can also ask the platform about itself.  The guides live in the {{PLATFORM}} chat, in the selector at the top, and each is an agent with part of this documentation attached.  They will tell you when a question is outside what they know.  Watch for that — most assistants never say it.

## Teaching with it

Your students already have access.  That changes some of your assignments and leaves others completely alone, and working out which is which is a teaching question, not a technology question.

[Teaching with AI](teaching-with-ai/index.md) is written for that work, and it starts from one principle: **a student is fully responsible for what they submit.  A model cannot accept blame.**  Once that is settled, most of the hard questions get easier.  The subject moves from *did you use AI* — unanswerable, and increasingly beside the point — to *do you stand behind this*, the question scholarship has always asked.

From there:

- [Designing assignments](teaching-with-ai/designing-assignments.md) — what to change, and what to leave alone
- [Your syllabus policy](teaching-with-ai/syllabus-policy.md) — language you can use as written
- [Integrity and detection](teaching-with-ai/integrity-and-detection.md) — what the evidence says, including about detectors
- [AI literacy](teaching-with-ai/ai-literacy.md) — treating it as a learning objective
- [If you teach a course](your-data/for-instructors.md) — the duties that come with the roster

## Learning to build it

The platform is also course material.  Every significant decision here was made for a reason, and the reasons are written down.  The reasons transfer — you will meet the same trade-offs on a stack that looks nothing like this one.

[How we built it](how-we-built-it/index.md) is that track.  It is being written as the build settles; the first piece finished is [How do you keep the courses apart?](how-we-built-it/keeping-courses-apart.md), which is about tenancy.  It ends on a gap we have not closed yet.  A gap you can read about is worth more than one you cannot.

## Your data

Coursework generates records about you, and records about students come with obligations.

Your conversations live in your own course's database, and nobody in another course can get to them; your usage is recorded against your email address — which model, how many tokens, when, but not what you said; nothing expires on its own except a temporary chat, which is deleted after 30 days; and nothing you build is shared until you share it.

The full account, including the parts that are not built yet, is in [Your data](your-data/index.md).  It's linked from the first page so you don't have to go looking for it.

---

*Looking for something specific?  [Browse by topic](tags.md) pulls a thread — retention, access control, academic integrity — across every page here.*
