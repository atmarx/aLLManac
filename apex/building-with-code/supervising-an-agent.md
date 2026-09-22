---
title: What does it mean to supervise a coding agent?
description: A harness acts in your repository under your name.  What you are still responsible for when an agent writes the code, how to check its work rather than trust it, and where agentic coding meets your course's integrity policy.
audience: student
also_reaches: [faculty]
status: scaffold
owner: piper
tags: [agentic-coding, harness, accountability, academic-integrity, critical-evaluation, ai-literacy, faculty-duty]
tethered_to:
  - docs/agent-contract.md
---

# Supervising an agent

<!-- SCAFFOLD — @piper's to write.  Withheld from every corpus until the
     status moves off `scaffold`.  Notes from @marco, facts only; the
     pedagogy is yours.

     The spine is `accountability`: a model cannot accept blame, only a
     person can.  A harness makes that concrete — it edits files and runs
     commands in the student's repo, and every token is metered to their
     key.  Nothing it does is anonymous and none of it is the model's.

     Beats I'd expect, in your order not mine:
     - Read the diff, not the summary.  An agent's "done" is a claim.  The
       small-model failure modes on harnesses.md (wrong tool name, wrong
       place, premature done) are what "check" means in practice.
     - Run the tests yourself.  An agent that ran them may have edited them.
     - Scope what it can touch: a branch, a clean working tree, commit
       before letting it loose so `git diff` shows exactly what it did.
     - Commands it runs are commands YOU ran.  VERIFY whether opencode asks before
       running shell commands by default at its current release — I
       haven't checked.  Either way the habit of reading the prompt before
       approving is the whole skill.
     - Integrity: where agentic coding sits against a course policy is the
       instructor's to set.  faculty-duty — the instructor needs to say
       whether a harness is allowed on an assignment, because a student
       can't infer it from the chat policy.  Link teaching-with-ai/.
     - The campus-model framing from harnesses.md: visible mistakes teach
       supervision better than rare ones.  Maybe the page's landing.
-->
