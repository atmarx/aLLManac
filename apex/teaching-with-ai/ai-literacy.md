---
title: AI literacy as a learning objective
description: The name is the warning — large language models produce large amounts of language, faster than anyone can read it. Why volume is the real hazard, and how to teach reading, questioning, and checking.
audience: faculty
also_reaches: [student]
status: draft
owner: piper
tags: [ai-literacy, accountability, critical-evaluation, hallucination, source-verification, assessment-design, faculty-duty]
---

# AI literacy as a learning objective

## Start with what the name says

**Large language models produce large amounts of language.**  The name states the whole hazard in one line, and most people read past it now that it is familiar.

The tool's defining characteristic is *volume*: it generates a page in seconds.  Reading that page — properly, with attention, catching what is assumed and what is asserted — takes minutes.  The rates do not match, and they do not match by an order of magnitude.

So if you accept output at the speed it arrives, you are necessarily not reading it.  That is arithmetic, not a character flaw, and telling students to be more careful does not change a rate mismatch.

## Fluency makes it worse

Volume alone would be manageable if the output looked rough.  It does not.  It arrives polished, evenly confident, correctly formatted, and organized with headings — every signal humans normally use to judge whether a text was carefully made.

For human writing, fluency and care correlate.  For generated text they do not correlate at all.  A student should be able to say that sentence out loud.  It is the single most useful thing they can know about the tool.

The two failures compound.  Volume means you skim; fluency means skimming feels sufficient.  You come away believing you have absorbed something you have only scanned.

## Answering for something means having read it

Here the principle from [the section index](index.md#the-principle-underneath-all-of-it) becomes a concrete instruction.

You are responsible for what you submit.  You cannot be responsible for text you have not read.  Therefore, read it.  Not skim — read, at the pace reading takes, trying to understand it.  Confirming that it looks fine is a different activity.

The practical implication removes the tool's apparent advantage, and most people resist it: **generate less.**  A model asked for three paragraphs produces something you can be accountable for.  A model asked for five pages produces something you will skim, whatever you intend at the outset.

## Read to understand

The habits that make a good reader of anything apply here.

**Call out the assumptions.**  Generated text rests on premises it never states.  It will also accept whatever assumption is embedded in your question and build confidently on top of it — ask a leading question and you get a well-argued answer to the wrong problem.  The exercise is to say what the text assumes, out loud, and ask whether those assumptions hold in your case.

**Check elsewhere.**  Corroborate against something independent.

!!! warning "Asking it again is not checking"
    Asking the same model "are you sure?" is not verification.  It will either reassert with equal confidence or fold and apologize, and neither response carries information about whether the original claim was true.  Consistency is not corroboration.  Go to a source that does not share the first one's failure modes — the actual paper, the documentation, a person who knows.

**Question it, and question yourself.**  Do not abandon your own knowledge because a machine sounded certain — expertise you spent years acquiring outranks a confident paragraph, and students give theirs up far too readily.  And hold your own view loosely enough to check it.  Neither humans nor models are infallible, so aim for calibration, with no deference in either direction.

## Teaching it

- **Assign something the model gets confidently wrong**, and grade whether the student caught it.  This teaches faster than any warning.
- **Ask for the assumptions.**  "List three things this answer takes for granted" is a short, gradeable exercise that produces real thinking.
- **Cap the length.**  A word limit is an AI-literacy intervention: it forces the student back to something they can stand behind.
- **Make them defend a paragraph they did not write.**  Five minutes of questions about generated text shows how much was read.
- **Apply your field's own verification standard** to model output.  Whatever your discipline already requires to accept a claim, require it here.  See [Verifying sources](verifying-sources.md).

## Cost as a teachable subject

An unusual advantage of running this on institutional infrastructure: usage is metered and visible, so a student can see what their questions cost.  Most people using AI have no idea it has unit economics.

It also makes the volume point from a different angle — generating five pages to use one paragraph is visibly wasteful once there is a number attached.

## What AI literacy should not become

Steer around these two.

**Prompt-engineering trivia.**  Technique specific to this year's models ages out in months, and teaching it as the core skill dates the course badly.

**Blanket cynicism.**  "Never trust it" is as uncalibrated as "it's usually right," and it stops students from learning what the tool is good at.

The target is calibration: knowing what this tool does well, what it does badly, and how to tell the difference in your own field.  That skill outlives any particular model.
