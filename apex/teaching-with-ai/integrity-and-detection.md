---
title: Integrity and detection
description: AI detectors flag non-native English writers as AI-generated most of the time. Why the failure is structural, why the whole detection framing is a dead end, and what replaced it.
audience: faculty
also_reaches: [student]
status: draft
owner: piper
tags: [accountability, academic-integrity, detection, equity, assessment-design, disclosure, source-verification, faculty-duty]
---

# Integrity and detection

The instinct when a new tool can produce coursework is to look for a tool that detects it.  That instinct is worth following far enough to learn where it leads, because the evidence on AI detectors is unusually clear and it arrives with an equity problem attached.

It is also worth naming why the whole framing is a dead end before getting to the numbers.  Detection asks *how was this produced*, and that question is already unanswerable and getting more so — faculty and staff use these tools daily, and a standard nobody applies to themselves does not survive contact with a classroom.  The question that holds up is *do you stand behind this*.  See [the principle](index.md#the-principle-underneath-all-of-it).

The evidence below matters for a narrower reason: a lot of institutions tried detection first, and it is worth knowing precisely why it failed rather than being told to skip it.

## What the evidence shows

Stanford researchers ran seven widely used GPT detectors against TOEFL essays written by non-native English speakers, and against essays by native English writers.

- **61.3%** of the non-native writers' essays were flagged as AI-generated.
- **97.8%** were flagged by at least one of the seven detectors.
- Around **a fifth** were unanimously misclassified by every detector tested.
- On native English writers' essays, the detectors were **near-perfect**.

The failure is not random noise that better models will sand down.  It follows from how the detectors work: they score text as machine-generated when word choice is predictable and sentence construction is simple.  That is a reasonable proxy for machine text, and it is also an accurate description of competent second-language writing.  The bias is structural.

Scale makes it worse rather than better.  Even at a **1% false-positive rate** — far better than anything measured — an institution processing 75,000 submissions a year produces **750 wrongly accused students**.  Those accusations do not distribute evenly across the student body.

!!! note "The finding is contested, and by whom matters" Detector vendors have published rebuttals arguing the study's methodology is flawed.  Weigh those as you would any product manufacturer's critique of research finding the product does not work.  The direction of the result has been corroborated by independent reporting and subsequent scholarship.

## What follows for your course

**A detector score is a reason to have a conversation.  It is never proof.**  That is the defensible position, and it is the one you want to be standing on if a grade is contested or a case reaches a hearing.

Practically:

- Do not open an integrity case on a detector score alone.
- Do not tell a student a machine says they cheated.  You will sometimes be wrong, and the students you will be wrong about most often are the ones with the least standing to argue.
- If your institution requires detector use, treat the output as a flag for human review and document that you did the review.

## What replaces it

The practice institutions are moving to as they retire detectors is **verifying the sources** — confirming that cited publications exist and that they say what the citation claims they say.

It is a better instrument for a specific reason: it evaluates the work rather than guessing at the author.  It carries no assumption about how the text was produced, it cannot be biased by a student's sentence rhythm or first language, and asking someone to support a claim is ordinary scholarship rather than an accusation.  It also catches failures that have nothing to do with AI.

The rates justify it.  Studies of LLM-generated literature reviews report fabrication rates from roughly **18% to 95%** depending on model and method, and among citations pointing at genuinely real papers, **45.4% carry bibliographic errors**.

**[Verifying sources](verifying-sources.md)** is the full treatment — the three failure modes, the checks that take seconds versus the ones that take reading, and how to make it a gradeable skill rather than a policing chore.

## And the rest of assessment design

Verification is the sharpest single instrument.  Around it, the general shape is to **make the process visible rather than policing the product**.

- **Ask for the work, not just the artifact.**  Outlines, annotated sources, drafts, revision history.  A finished essay is easy to generate; a believable trail of thinking behind it is considerably harder and more useful to grade.
- **Assess in conditions you control** where the stakes justify it — in-class writing, oral defense, a five-minute conversation about the submission.  A student who did the work can talk about it.
- **Make the AI use part of the assignment.**  Requiring students to submit their prompts, the output they got, and their critique of it converts an integrity problem into a skills assessment, and it is a better read on their judgment than the essay was.
- **Ask for what a model does badly.**  Specific local context, material from the last two weeks of class, personal reasoning about their own choices, connections to a discussion nobody transcribed.

None of this is free.  It is more work to design and more work to grade, and it is worth being honest with yourself about which assignments justify it rather than converting a whole course at once.

## When AI use is allowed, require attribution

Where you permit AI assistance, ask students to say what they used and how.  Two reasons, and the second is the better one:

1. It makes the boundary enforceable without surveillance.
2. It is what professional practice increasingly looks like, and having students document their tool use is a skill worth grading in its own right.

A one-line disclosure at the end of a submission is usually enough: what tool, what for, and what they changed about the output.

## The conversation to have in week one

Students arrive with wildly different assumptions about what is allowed, and a number of them are quietly frightened of being accused.  Saying out loud that you know detectors are unreliable, that you will not run their work through one and act on the result, and that you would rather talk to them than accuse them, buys more honesty than a policy paragraph will.

It also models the thing you are trying to teach: judgment about a tool, stated openly, with its limits named.

**Sources:** the detector figures are from Liang et al., *GPT detectors are biased against non-native English writers* (Stanford, published in *Patterns*, 2023), with independent reporting by The Markup.
