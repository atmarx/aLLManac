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

The instinct when a new tool can produce coursework is to look for a tool that detects it.  The evidence on AI detectors is unusually clear, and it shows an equity problem.

The detection framing is a dead end in any case.  Detection asks *how was this produced*, and that question is already unanswerable and getting harder to answer.  Faculty and staff use these tools daily, and a standard that nobody applies to themselves will not hold up in a classroom.  The question that still works is *do you stand behind this*.  See [the accountability principle](index.md#the-principle-underneath-all-of-it).

The detector evidence still matters for a narrower reason.  Many institutions tried detection first, and knowing exactly why it failed is more useful than being told to skip it.

## What the evidence shows

Stanford researchers ran seven widely used GPT detectors against TOEFL essays written by non-native English speakers, and against essays by native English writers ([Liang et al., *Patterns*, 2023](https://pmc.ncbi.nlm.nih.gov/articles/PMC10382961/)).

- Averaged across the seven detectors, **61.3%** of the non-native writers' essays were flagged as AI-generated.
- **97.8%** were flagged by at least one of the seven detectors.
- Around **a fifth** were unanimously misclassified by every detector tested.
- On essays by US eighth-graders writing in their first language, the detectors were **near-perfect**.

The detectors' failure on non-native writers is not random noise that better models will remove.  The failure follows from how the detectors work: they score text as machine-generated when word choice is predictable and sentence construction is simple.  That is a reasonable proxy for machine text, and it is also an accurate description of competent second-language writing.  For detectors that work this way, the bias is structural.

Scale makes the problem worse.  Even at a **1% false-positive rate**, which is about what [the leading vendor claims](https://www.turnitin.com/blog/understanding-the-false-positive-rate-for-sentences-of-our-ai-writing-detection-capability) for its own product, an institution processing 75,000 submissions a year flags **750 submissions that were the students' own work**.  Those flags do not fall evenly across the student body.

!!! note "The finding is contested, and by whom matters"
    Detector vendors have published rebuttals arguing the study's methodology is flawed.  Weigh those as you would any product manufacturer's critique of research finding the product does not work.  Independent reporting has found the same pattern.  Later scholarship is mixed: an ETS study found that detectors trained on a broad sample of non-native writing did not show the bias ([Jiang et al., *Computers & Education*, 2024](https://doi.org/10.1016/j.compedu.2024.105070)).  The detectors a course can switch on are not those.

## What follows for your course

**A detector score is a reason to have a conversation.  It is never proof.**  Treating the score that way is the position you can defend if a grade is contested or a case reaches a hearing.

In practice, handle a detector score like this:

- Do not open an integrity case on a detector score alone.
- Do not tell a student a machine says they cheated.  You will sometimes be wrong, and the students you will be wrong about most often are the ones with the least standing to argue.
- If your institution requires detector use, treat the output as a flag for human review and document that you did the review.

## What replaces it

The practice that replaces a detector is **verifying the sources**: confirming that cited publications exist and that they say what the citation claims they say.

Source verification is a better instrument than a detector.  It evaluates the work and makes no judgment about the author.  It assumes nothing about how the text was produced, and it cannot be biased by a student's sentence rhythm or first language.  Asking someone to support a claim is ordinary scholarship, so nobody is being accused.  Verification also catches failures that have nothing to do with AI.

The citation failure rates justify the effort.  Published studies put the share of fabricated citations anywhere from **18%** to over **90%** depending on model and task, and in one study, **45.4%** of the citations that pointed at real papers contained bibliographic errors.  [Verifying sources](verifying-sources.md#how-often-this-bites) has the studies.

[Verifying sources](verifying-sources.md) covers the practice in full: the three failure modes, the checks that take seconds and the ones that take reading, and how to grade verification as a skill.

## And the rest of assessment design

Source verification is the sharpest single instrument.  The rest of assessment design follows one approach: **make the process visible** and stop policing the product.

- **Ask for the work behind the artifact, assess in conditions you control, or make the AI use part of the assignment.**  [Designing assignments](designing-assignments.md#when-an-assignment-is-in-category-one) has each option and what it costs.
- **Ask for what a model does badly.**  Specific local context, material from the last two weeks of class, personal reasoning about their own choices, connections to a discussion nobody transcribed.

Visible-process assessment takes more work to design and more work to grade.  Decide which assignments justify the cost, and don't convert a whole course at once.

## When AI use is allowed, require attribution

Where you permit AI assistance, ask students to say what they used and how.  There are two reasons to require attribution, and the second is the stronger one:

1. Attribution makes the boundary enforceable without surveillance.
2. Attribution is what professional practice increasingly looks like, and documenting tool use is a skill you can grade in its own right.

A one-line disclosure at the end of a submission is usually enough.  [Your syllabus policy](syllabus-policy.md#disclosure-that-people-actually-use) has the format and how to ask for it.

## The conversation to have in week one

Students arrive with wildly different assumptions about what is allowed, and some of them are frightened of being accused and won't say so.  Saying out loud that you know detectors are unreliable, that you will not run their work through one and act on the result, and that you would rather talk to them than accuse them, gets you more candor than a policy paragraph will.

The week-one conversation also models what you are trying to teach: judgment about a tool, stated openly, with its limits named.

**Sources:** the detector figures are from Liang et al., [*GPT detectors are biased against non-native English writers*](https://pmc.ncbi.nlm.nih.gov/articles/PMC10382961/) (Stanford, published in *Patterns*, 2023), with [independent reporting by The Markup](https://themarkup.org/machine-learning/2023/08/14/ai-detection-tools-falsely-accuse-international-students-of-cheating).
