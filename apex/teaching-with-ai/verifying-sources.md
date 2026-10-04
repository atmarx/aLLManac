---
title: Verifying sources
description: The practice that replaced detection — checking that cited publications exist and that they say what the citation claims. What the failure rates look like, how to check quickly, and how to teach it.
audience: faculty
also_reaches: [student, builder]
status: draft
owner: piper
tags: [accountability, source-verification, academic-integrity, critical-evaluation, hallucination, assessment-design, ai-literacy, disclosure, faculty-duty]
---

# Verifying sources

## The principle this rests on

**You are fully responsible for what you submit.  A model cannot accept blame; only a person can.**

That is the whole policy.  Whatever helped you produce a piece of work — a language model, a search engine, a colleague, a tutor — the claims in it are yours the moment you put your name on it.  "The AI said so" is not a defense in a course, and it will not be one in a lab, a courtroom, a clinic, or a newsroom.

Faculty and staff use these tools daily, to write and to automate.  Pretending students should not is a fiction, and it teaches them to hide their process.  The workable expectation is the one professionals are already held to — use what you like, and answer for the result.

## Why verification is the practice that follows

If you are accountable for every claim you make, then checking your claims is not a hoop.  It is the work.

Verification also does something detection cannot: it evaluates **the work** and makes no guess about **the author**.

- It requires no assumption about how the text was produced.
- It cannot be biased against a student's writing style, first language, or sentence rhythm.
- It catches human citation failures too — misrepresented sources, citation padding, and citing an abstract as though it were the paper.
- A student who did the reading survives it trivially.
- It is not an accusation.  Asking someone to support a claim is the ordinary business of scholarship.

"Walk me through this source" is a conversation any scholar can have with any other.  "A detector says you cheated" is not.

## How often this bites

The argument doesn't depend on these numbers — the principle stands whether they are large or small.  They happen to be large.

- In one study of LLM-generated mental health literature reviews, **19.9% of all citations were entirely fabricated** ([Linardon et al., *JMIR Mental Health*, 2025](https://mental.jmir.org/2025/1/e80371)).  Another found **55%** of GPT-3.5's citations and **18%** of GPT-4's fabricated ([Walters & Wilder, *Scientific Reports*, 2023](https://www.nature.com/articles/s41598-023-41032-5)).
- Comparative work on systematic reviews found hallucination rates around **28.6% for GPT-4**, **39.6% for GPT-3.5**, and **91.4% for Bard** ([Chelli et al., *JMIR*, 2024](https://www.jmir.org/2024/1/e53164)).
- In the first study, among citations that pointed at **real** publications, **45.4% contained bibliographic errors** — most often a wrong or invalid DOI.

Read that last figure again.  It drives the technique below: **in that study, most bad citations were not inventions.**  They are real papers with the wrong metadata, or real papers that do not support the claim attached to them.  Checking only for existence catches the smaller half.

## This is not a student problem

After NeurIPS 2025, an audit of accepted papers reported **more than 50 with fabricated citations that had passed peer review.**  (The audit was run by a detector vendor, so weigh the source — but the papers are checkable, and the finding was widely reported and not disputed.)

Say this to a class out loud.  The failure being asked of students is one that professional researchers and a top venue's review process missed at scale.  Verification becomes a discipline everyone now needs, researchers included.

## Three failure modes, in order of how fast they are to catch

**1. The publication does not exist.**  Fabricated title, plausible authors, real-sounding journal.  These are usually the *easiest* to catch and the rarest of the three.

*Check:* search the title in quotation marks.  Nothing, or nothing matching, in about fifteen seconds.

**2. The publication exists, but the citation is wrong.**  Right paper, wrong year, wrong volume, wrong page range, or — most often — a DOI that is correctly formatted and resolves to something else, or to nothing.

*Check:* resolve the DOI and confirm the title that comes back is the title cited.  This is the highest-yield check available and it takes seconds.  A correctly formatted DOI is not a working DOI, and in the study above it was the field models got wrong most often.

**3. The publication exists, is cited correctly, and does not say that.**  The hard one, the most common in practice, and the only one that requires reading.

*Check:* find the specific claim in the source.  Not the abstract — abstracts routinely overstate relative to the paper's own results.  Ask whether the sample, scope, and conditions match what the citing text implies.

Mode three is also where the interesting human failures occur: the telephone-game chain, where a paper cites another paper for a claim that the second paper attributed to a third, which never said it at all.  Once students see one of those traced, they understand the point permanently.

## Teaching it

Verification is a skill, which means it can be assigned, practiced, and graded.

- **Grade the citations as their own artifact.**  Ask for a source list where each entry has a resolving DOI or link and one sentence on what that source specifically supports.  Wrong sources become visible without anyone being accused of anything.
- **Assign a verification exercise.**  Hand out a short passage with five citations, two of them broken in different ways, and have students find them.  This teaches faster than any warning about hallucination.
- **Ask for the quotation as well as the reference.**  Requiring the actual sentence that supports a claim nearly eliminates failure mode three, and it improves human writing regardless of AI.
- **Spot-check.**  Verify two or three citations per submission, chosen by you and not announced in advance.  The deterrent is that the checking is real; it doesn't need to be total.
- **Let them use AI, and hold them to the citations.**  This is the clean version of a permissive policy: use whatever you like, and every claim you make is yours to support.

## What it costs

More time than running a detector, and less time than an integrity hearing.

Be realistic about scope.  Full verification of every citation in every submission is out of reach in a large course, and pretending otherwise produces a policy nobody follows.  Unpredictable spot-checking does most of the work.

For the assignments where it matters most — capstones, theses, anything that will be cited by someone else — full verification earns its cost.

## By discipline

The three failure modes are the same everywhere.  What changes is which check finds them fastest, and most fields already have the tool.

- **Sciences and medicine.**  Resolve the DOI first, then check that the study's sample and population match the claim it is cited for.  Systematic reviews are the riskiest genre — the citation density is enormous, so a few bad entries hide easily.
- **Humanities.**  Check quotations against the primary text.  Editions and translations matter, and page numbers are the tell: a quotation with no page, or a page that doesn't exist in the edition cited, is where to start.
- **Law.**  Citators — Shepard's, KeyCite — exist for exactly this reason and predate the problem by more than a century.  Point students at the discipline's own machinery.
- **Computer science.**  An arXiv ID resolves or it doesn't.  Preprints change between versions, so ask for the version that was read.
- **Quantitative fields.**  The reasoning can be sound and the number wrong.  Recompute the figure instead of rereading it.

## Why this transfers

Citations are not sacred.  The reason to teach this is that "someone is answerable for this output" is a habit, and habits formed under low stakes are the ones people keep when the stakes rise.

Automated systems already make consequential decisions about people, and the accountability question there is considerably less settled than it is in scholarship.  Facial recognition misidentification has produced documented wrongful arrests — people held on the strength of a machine's output that nobody was required to verify ([Williams v. City of Detroit](https://www.aclu.org/cases/williams-v-city-of-detroit-face-recognition-false-arrest)).  The asymmetry is hard to look at directly: we ask a sophomore to confirm that a cited paper says what they claim it says, while systems that can take someone's liberty ran for years under no comparable obligation, and only a settlement and a few state laws have started to impose one.

Students who internalize *I own what I put my name on* are the ones who might build the systems that close that gap, or refuse to ship the ones that widen it.  That is a better reason to run the exercise than catching anyone.

## For students

The student-facing version of this is in [Using AI well in your coursework](for-students.md).  It says the same thing from the other side: every claim you make is yours to support, whatever helped you write it.
