---
title: AI literacy as a learning objective
description: Large language models produce large amounts of language, faster than anyone can read it.  Why that volume is the main hazard, and how to teach reading, questioning, and checking.
audience: faculty
also_reaches: [student]
status: draft
owner: piper
tags: [ai-literacy, accountability, critical-evaluation, hallucination, source-verification, assessment-design, faculty-duty]
---

# AI literacy as a learning objective

## Start with what the name says

**Large language models produce large amounts of language.**  The name of the tool describes its main hazard.  Most people read past it now that the name is familiar.

A language model's defining characteristic is *volume*: it generates a page in seconds.  Reading that page properly takes minutes, if you read with attention and notice what is assumed and what is asserted.  The two rates differ by an order of magnitude.

If you accept model output at the speed it arrives, you are not reading it.  The cause is arithmetic.  Telling students to be more careful does not change the gap between how fast a model writes and how fast a person reads.

## Fluency makes it worse

The volume of model output would be manageable if the output looked rough.  Model output arrives polished, evenly confident, correctly formatted, and organized with headings.  Those are the signals people normally use to judge whether a text was carefully made.

In human writing, fluency and care go together.  In generated text they do not: a model writes fluently whether or not the content is right.  A student should be able to explain this out loud.  It is the most useful single fact they can know about the tool.

Volume and fluency make each other worse.  Volume means a reader skims, and fluency makes skimming feel sufficient.  The reader comes away believing they have absorbed something they have only scanned.

## Answering for something means having read it

The accountability principle in [Teaching with AI](index.md#the-principle-underneath-all-of-it) becomes a concrete instruction when it is applied to generated text.

You are responsible for what you submit, and you cannot be responsible for text you have not read.  So read generated text at the pace reading takes, trying to understand it.  Skimming to confirm that it looks fine is a different activity.

The practical consequence is to **generate less.**  Most people resist it.  Generating less gives up the tool's apparent advantage.  A model asked for three paragraphs produces something you can be accountable for.  A model asked for five pages produces something you will skim, whatever you intend at the outset.

## Read to understand

The habits that make a good reader of anything also apply to model output.

**Call out the assumptions.**  Generated text rests on premises it never states.  A model will also accept whatever assumption is embedded in your question and build confidently on it.  Ask a leading question and you get a well-argued answer to the wrong problem.  The exercise is to say what the text assumes, out loud, and ask whether those assumptions hold in your case.

**Check elsewhere.**  Corroborate against something independent.

!!! warning "Asking it again is not checking"
    Asking the same model "are you sure?" does not verify anything.  The model will either repeat the claim with equal confidence or apologize and reverse it.  Neither response tells you much about whether the original claim was true.  Go to a source that does not share the model's failure modes: the actual paper, the documentation, or a person who knows.

**Question it, and question yourself.**  Do not abandon your own knowledge because a machine sounded certain.  Expertise you spent years acquiring outranks a confident paragraph, and students give theirs up far too readily.  At the same time, hold your own view loosely enough to check it.  Neither people nor models are infallible, so aim for calibration and do not defer to either one by default.

## Teaching it

- **Assign something the model gets confidently wrong**, and grade whether the student caught it.  An assignment like this teaches faster than any warning.
- **Ask for the assumptions.**  "List three things this answer takes for granted" is a short, gradeable exercise that makes students think.
- **Cap the length.**  A word limit is an AI-literacy intervention.  It keeps the student's submission to an amount they can read closely and stand behind.
- **Make them defend a paragraph they did not write.**  Five minutes of questions about generated text shows how much was read.
- **Apply your field's own verification standard** to model output.  Whatever your discipline already requires to accept a claim, require it here.  See [Verifying sources](verifying-sources.md).

## Cost as a teachable subject

Running AI on institutional infrastructure has an unusual advantage for teaching.  Usage is metered and visible, so a student can see what their questions cost.  Most people using AI have no idea it has unit economics.

Visible cost also teaches the point about volume.  Generating five pages to use one paragraph looks wasteful once there is a number attached.

## What AI literacy should not become

AI literacy teaching tends to slide into one of two things.  Avoid both.

**Prompt-engineering trivia.**  Technique specific to this year's models goes out of date within months.  A course that teaches it as the core skill will date quickly.

**Blanket cynicism.**  "Never trust it" is as uncalibrated as "it's usually right," and it stops students from learning what the tool is good at.

The target is calibration: knowing what this tool does well, what it does badly, and how to tell the difference in your own field.  Calibration stays useful when the models change.
