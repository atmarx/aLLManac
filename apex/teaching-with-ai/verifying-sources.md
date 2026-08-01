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

**You are fully responsible for what you submit.  A model cannot accept
blame; only a person can.**

That is the whole policy, and everything below is just what it looks like in
practice.  Whatever helped you produce a piece of work — a language model, a
search engine, a colleague, a tutor — the claims in it are yours the moment
you put your name on it.  "The AI said so" is not a defense in a course, and
it will not be one in a lab, a courtroom, a clinic, or a newsroom.

Worth stating the honest context alongside it: faculty and staff use these
tools daily, to write and to automate.  Pretending students should not is not
a standard, it is a fiction, and it teaches them to hide their process rather
than own it.  The workable expectation is the one professionals are already
held to — use what you like, and answer for the result.

## Why verification is the practice that follows

If you are accountable for every claim you make, then checking your claims is
not a hoop.  It is the work.

Verification also does something detection cannot: it evaluates **the work**
rather than guessing at **the author**.

- It requires no assumption about how the text was produced.
- It cannot be biased against a student's writing style, first language, or
  sentence rhythm.
- It catches human citation failures too — misrepresented sources, citation
  padding, and citing an abstract as though it were the paper.
- A student who did the reading survives it trivially.
- It is not an accusation.  Asking someone to support a claim is the ordinary
  business of scholarship.

"Walk me through this source" is a conversation any scholar can have with any
other.  "A detector says you cheated" is not.

## How often this bites

A data point rather than the argument — the principle holds whether the
numbers are large or small.  They happen to be large.

- In one study of LLM-generated mental health literature reviews, **19.9% of
  all citations were entirely fabricated.**  Across models and elicitation
  methods, published fabrication rates range from roughly **18% to 95%**.
- Comparative work on systematic reviews found hallucination rates around
  **28.6% for GPT-4**, **39.6% for GPT-3.5**, and **91.4% for Bard**.
- Among citations that pointed at **real** publications, **45.4% carried
  bibliographic errors** — with the DOI the single least reliable field.

Read that last figure again, because it drives the technique below: **most
bad citations are not inventions.** They are real papers wearing wrong
metadata, or real papers that do not support the claim attached to them.
Checking only for existence catches the smaller half.

## This is not a student problem

After NeurIPS 2025, an audit of accepted papers reported **53 with fabricated
citations that had passed peer review.**  (The audit was run by a detector
vendor, so weigh the source — but the papers are checkable and the finding
was widely corroborated.)

Worth saying to a class out loud.  The failure being asked of students is one
that professional researchers and a top venue's review process missed at
scale.  It reframes verification as a discipline everyone now needs rather
than a hoop undergraduates jump through.

## Three failure modes, in order of how fast they are to catch

**1. The publication does not exist.**  Fabricated title, plausible authors,
real-sounding journal.  These are usually the *easiest* to catch and the
rarest of the three.

*Check:* search the title in quotation marks.  Nothing, or nothing matching,
in about fifteen seconds.

**2. The publication exists, but the citation is wrong.**  Right paper, wrong
year, wrong volume, wrong page range, or — most often — a DOI that is
correctly formatted and resolves to something else, or to nothing.

*Check:* resolve the DOI and confirm the title that comes back is the title
cited.  This is the highest-yield check available and it takes seconds.  A
correctly formatted DOI is not a working DOI, and models are markedly worse at
this field than any other.

**3. The publication exists, is cited correctly, and does not say that.**
The hard one, the most common in practice, and the only one that requires
actually reading.

*Check:* find the specific claim in the source.  Not the abstract — abstracts
routinely overstate relative to the paper's own results.  Ask whether the
sample, scope, and conditions match what the citing text implies.

Mode three is also where the interesting human failures live: the
telephone-game chain, where a paper cites another paper for a claim that the
second paper attributed to a third, which never said it at all.  Once students
see one of those traced, they understand the point permanently.

## Teaching it

Verification is a skill, which means it can be assigned, practiced, and
graded.

- **Grade the citations as their own artifact.**  Ask for a source list where
  each entry carries a resolving DOI or link and one sentence on what that
  source specifically supports.  Wrong sources become visible without anyone
  being accused of anything.
- **Assign a verification exercise.**  Hand out a short passage with five
  citations, two of them broken in different ways, and have students find
  them.  This teaches faster than any warning about hallucination.
- **Ask for the quotation, not just the reference.**  Requiring the actual
  sentence that supports a claim collapses failure mode three almost
  entirely, and it improves human writing regardless of AI.
- **Spot-check rather than exhaust.**  Verify two or three citations per
  submission, chosen by you and not announced in advance.  The deterrent
  comes from the checking being real, not from it being total.
- **Let them use AI, and hold them to the citations.**  This is the clean
  version of a permissive policy: use whatever you like, and every claim you
  make is yours to support.

## What it costs

More time than running a detector, and less time than an integrity hearing.

Be honest with yourself about scope.  Full verification of every citation in
every submission is not realistic in a large course, and pretending otherwise
produces a policy nobody follows.  Spot-checking that is genuinely
unpredictable does most of the work.

For the assignments where it matters most — capstones, theses, anything that
will be cited by someone else — full verification earns its cost.

## By discipline

<!-- TODO: expand with concrete per-field guidance.  Sketch:
     - sciences/medicine — DOI resolution, then check the sample and
       population match the claim; systematic reviews are the highest-risk
       genre because the citation density is enormous
     - humanities — quotations against the primary text, editions and
       translations matter, page numbers are the tell
     - law — citators exist for exactly this reason and predate the problem
       by a century; point at the discipline's own machinery
     - code/CS — arXiv IDs resolve or they do not, and preprint versions
       shift, so pin the version
     - quantitative fields — the reasoning can be sound and the number
       wrong; recompute rather than re-read -->

## Why this transfers

The reason to teach this is not that citations are sacred.  It is that
"someone is answerable for this output" is a habit, and habits formed under
low stakes are the ones people keep when the stakes rise.

Automated systems already make consequential decisions about people, and the
accountability question there is considerably less settled than it is in
scholarship.  Facial recognition misidentification has produced documented
wrongful arrests — people held on the strength of a machine's output that
nobody was required to verify.  The asymmetry is hard to look at directly: we
ask a sophomore to confirm that a cited paper says what they claim it says,
while systems that can take someone's liberty have faced no comparable
obligation.

Students who internalize *I own what I put my name on* are the ones who might
build the systems that close that gap, or refuse to ship the ones that widen
it.  That is a better reason to run the exercise than catching anyone.

## For students

The student-facing version of this is in
[Using AI well in your coursework](for-students.md).  It says the same thing
from the other side: every claim you make is yours to support, whatever helped
you write it.
