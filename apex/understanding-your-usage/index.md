---
title: Understanding your usage
description: What the numbers on your usage mean, where they come from, and which of them you can do something about — starting with the one misunderstanding almost everybody arrives with.
audience: student
also_reaches: [faculty]
status: draft
owner: piper
tags: [metering, attribution, context-window, token-economy, cost-intuition, ai-literacy, student-right]
tethered_to:
  - usage-mcp/server.py
  - docs/budgets-and-meters.md
---

# Understanding your usage

Most people arrive believing the same thing, and it is wrong in a way that makes everything else confusing.

The belief is that **context** is a container somewhere inside the model — a tank, a working memory, something you cannot see, which fills up as you talk and occasionally has to be emptied.  That picture explains a lot of what people see, so it survives.  The assistant does seem to forget things from earlier.  Long conversations do get more expensive.  Something does appear to be filling up.

What happens instead:

> **The context is the conversation.  All of it.  Sent again, from the top, every single time you press enter.**

There is no tank.  There is no memory.  The model reads your entire conversation from the beginning on every turn.  It has no other way to know what you were talking about — and then it forgets it completely, and you send it again.

Once that clicks, every number in your usage report is arithmetic.  The pages below cover that arithmetic and which parts of it deserve your attention.

## Start here

**[Why is it measured in tokens?](tokens.md)** — what a token is, why it is not a word, and why it is not a subway token either.

**[What context actually is](context-is-the-conversation.md)** — the point above, at length, with the arithmetic that explains why your fortieth message costs so much more than your first.

**[What actually costs something](what-actually-costs.md)** — the levers, ranked by size.  Some of the advice you have heard is real and some of it is rounding error.  Know which is which before you change how you write.

**[Reading your own numbers](reading-your-numbers.md)** — every figure on your usage report, one at a time, and what each one responds to.

## Nobody is grading this

Your usage numbers are yours.  There is no ranking, no comparison against your classmates, and no budget anywhere on this platform that gets larger or smaller based on how someone judges your questions.  We chose that.  **We can tell you exactly what a question cost, and we can never tell you what it was worth.**

A student who asks twenty careful questions and a student who asks two hundred scattered ones may have learned the same amount, or opposite amounts, and nothing in any ledger anywhere can tell the difference.  Anyone who tried to score you on this number would be scoring the wrong thing with great precision.

This section describes and does not evaluate.  Cost intuition is a useful skill and almost nobody gets to build it.  The feedback is invisible, delayed, and arrives after the decision can no longer be undone.  You cannot know what a question will cost until you have asked it, and the only useful response to that is information.
