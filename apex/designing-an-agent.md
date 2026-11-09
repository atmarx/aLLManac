---
title: How do I design a good agent?
description: Deciding what an agent is for, writing its instructions and conversation starters, choosing its knowledge files and what to keep out of them, preparing documents so an agent can find what is in them, and testing an agent before anyone else uses it.
audience: student
also_reaches: [faculty]
status: draft
owner: piper
tags: [agent-design, knowledge-files, assessment-design, academic-integrity, librechat]
tethered_to:
  - registrar/render.py
  - registrar/planes/config.py
  - scripts/seed_agents.py
---

# Designing an agent

[Using it in a course](user-guide.md#part-1-your-first-agent) shows where the Agent Builder is and what each of its fields does.  Designing an agent is about what goes into those fields: what the agent is for, what its instructions say, which files it gets, and how to tell whether it works.

The Agent Design Guide can walk you through the design in a conversation.  It is one of the guides in the {{PLATFORM}} chat, in the selector at the top.  The Agent Design Guide asks what your agent is for, then drafts a name, a description, instructions and conversation starters for you to paste into the Agent Builder.  The guide never creates or changes an agent itself.  You paste the draft, and the agent is yours.

## Start with one job

An agent works best with one job and one audience.  "Help ENGR 301 students prepare samples for XRD, using the lab manual" is a job.  "Help with the course" is not, and an agent given that job answers everything vaguely.

Before you open the Agent Builder, write down three things about the agent: who will use it, what they will ask it, and what it must not do for them.  The third item is the one people skip.  If you can't name what the agent must not do, ask what a student could use it to avoid learning.

## Writing the instructions

An agent's instructions are its system prompt.  The agent reads its instructions before every message, so they shape its behavior more than any other setting.  Good instructions usually cover these five things, in plain sentences:

- **Role and audience:** who the agent is and who it talks to.  "You are the lab assistant for ENGR 301.  You talk with undergraduates preparing their first samples."
- **Sources:** which knowledge files to rely on, by name, and what to do when they don't cover a question.  "If the lab manual doesn't cover it, say so and suggest asking the TA."
- **Approach:** how the agent helps.  "Ask what the student has tried before offering a next step."
- **Limits:** what the agent refuses, stated directly.  "Never give final answers to the numbered pre-lab questions."
- **Tone and length:** "Keep answers short.  Use the terms the lab manual uses."

Instructions work best as direct statements the agent can follow.  A specific rule ("never give the final numeric answer") works better than a general wish ("don't make it too easy").  When an agent keeps doing something you don't want, add one sentence to its instructions that names the behavior and says what to do instead.

Keep a copy of an agent's instructions outside {{PLATFORM}}, the way you keep a copy of a syllabus.  With the instructions in hand, rebuilding an agent takes a few minutes.

## Conversation starters

Conversation starters are suggested first messages that appear when someone opens an agent.  Starters show a new user what the agent is good at, so write them as questions a real user would ask: "How do I mount a powder sample for XRD?" works better than "Ask me about XRD!"

## How an agent uses its files

An agent with files under **File Search** does not read whole files.  For each question, the agent searches its files and gets back a handful of short passages, ten at most and each a few paragraphs long, drawn from all of its files together.  The agent answers from those passages alone.  Anything outside them, including the rest of the same page, it does not see for that question.

Two things follow from how File Search works:

- **Each section of a file should make sense on its own.**  A passage that says "as described above" arrives without the description.  Headings help, and so do paragraphs that name their subject instead of starting with "it" or "this."
- **A few focused files work better than many loose ones.**  The ten passages are shared among all of an agent's files.  An agent with a lab manual and twenty unrelated readings finds less of the lab manual.

**File Context** works differently, and only if your course has it switched on.  A File Context file is added whole to the agent's instructions and sent with every message.  File Context suits something short the agent always needs, such as a rubric or a formula sheet.  If File Context isn't in your Agent Builder, your course doesn't have it, and File Search is the option to use.

## What never goes into an agent

Anyone who can chat with an agent can get it to repeat what is in its files.  Asking the right way works, and no instruction reliably stops it.  A shared agent's Editors can also open and change its files directly.  So treat every knowledge file as something every user of the agent can read.

Knowledge files that should never be attached to an agent:

- Answer keys, solutions, and unreleased exams or quizzes
- Graded student work, and any other student's writing
- Rosters, grades, and anything else about identifiable students
- Anything you would not hand to everyone who can use the agent

An agent that needs to check students' answers cannot do that safely with the answers in its files.  Give the agent the method instead: how to set up the problem, what a correct approach looks like, and which mistakes are common.  Instructors will find more on student records in [If you teach a course](your-data/for-instructors.md).

## Preparing documents

An agent can only find what it can read in a file, and file formats differ in how much comes through:

- **Markdown or plain text with headings:** the best case.  Every section keeps its heading, and the agent can find sections by topic.
- **Word documents:** the words come through, and usually the order of the headings and paragraphs too.
- **PDFs made from a document:** the words come through, but the layout often doesn't.  Tables, columns and headings can run together into one stream of text, so a table of due dates can arrive as a list of dates with no labels.
- **Scanned PDFs:** a scan is a picture of each page, with no text in it.  The agent can find nothing in a scanned PDF.

If your source is a PDF, the best fix is to go back to the document the PDF was made from and attach that document instead, or save it as Word or plain text.  If a PDF is all you have, copy its text into a new document, add a heading where each section starts, and rebuild any tables by hand.  Afterward, check every date, number and name against the original.

The Agent Design Guide can help with that cleanup.  Paste the text in, and it will suggest where headings belong and which parts to split.  The Agent Design Guide won't retype your document for you, because retyping is how a date or a policy changes without anyone noticing.  The words in your files stay yours.

## Testing before you share

Test an agent the way its users will use it, before anyone else sees it:

- **Ask the questions you expect most,** and check each answer against the files.
- **Ask something the files don't cover.**  A good agent says it doesn't know, or says what it does cover.  An agent that answers anyway is guessing, and its instructions need a sentence on what to do when the files are silent.
- **Try to make it break its own limits.**  Ask for the answer it should refuse, then ask again a different way, then claim to be the instructor.
- **Ask it to quote a knowledge file.**  If the agent repeats something you didn't want out, take that file out of the agent.

When an answer is wrong, change one instruction that would fix it and ask the same question again.  Changing one thing at a time tells you which change worked.  Getting from a working agent to a good one usually takes about fifteen rounds.

## After it works

To share an agent with your team or your class, see [Sharing the agent to the team](user-guide.md#sharing-the-agent-to-the-team).  Sharing stays inside your course.

An agent that works well beyond your own course can be offered as a template for other courses.  The Student Guide and the Instructor Guide both take nominations.  Each guide needs the agent's id, which is on the agent's edit page, and a line on what the agent does.
