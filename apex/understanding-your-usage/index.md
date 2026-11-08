---
title: Understanding your usage
description: What the numbers on your usage mean, where they come from, and which of them you can do something about, starting with the one misunderstanding almost everybody arrives with.
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

Most people start with the same wrong idea about context, and that idea makes the rest of the usage numbers confusing.

The common belief is that context is a container somewhere inside the model: a tank, or a working memory you cannot see, which fills up as you talk and occasionally has to be emptied.  The tank picture explains a lot of what people see.  The assistant does seem to forget things from earlier, long conversations do get more expensive, and something does appear to be filling up.

The tank picture is wrong.  What happens is this:

> **The context is the conversation.  All of it is sent again, from the top, every time you press enter.**

The model has no tank and no memory.  It reads your entire conversation from the beginning on every turn.  The model has no other way to know what you were talking about.  After it replies, it forgets the conversation completely, and your next message sends the whole conversation again.

Once you know that the context is the whole conversation re-sent, every number in your usage report follows from simple arithmetic.  The four usage pages listed under "Start here" cover that arithmetic and which parts of it deserve your attention.

## Start here

The usage pages, in reading order:

- [Why is it measured in tokens?](tokens.md) explains what a token is, and why a token is a piece of text and not a word.
- [What context actually is](context-is-the-conversation.md) explains that the whole conversation is re-sent on every turn, with the arithmetic that shows why your fortieth message costs so much more than your first.
- [What actually costs something](what-actually-costs.md) ranks the levers that change your usage by size.  Some common advice makes a real difference and some of it is rounding error.  Know which is which before you change how you write.
- [Reading your own numbers](reading-your-numbers.md) goes through every figure on your usage report, one at a time, and what changes each one.

## Nobody is grading this

Your usage numbers are yours.  There is no ranking, no comparison against your classmates, and no budget anywhere on this platform that gets larger or smaller based on how someone judges your questions.  We chose that design.  **We can tell you exactly what a question cost, and we can never tell you what it was worth.**

A student who asks twenty careful questions and a student who asks two hundred scattered ones may have learned the same amount, or very different amounts.  Nothing in any usage ledger can tell the difference.  Scoring students on their usage numbers would measure cost precisely and learning not at all.

The usage pages describe your numbers and do not evaluate them.  Cost intuition is a useful skill, and almost nobody gets to build it.  The feedback is invisible and delayed, and it arrives after the decision can no longer be undone.  You cannot know what a question will cost until you have asked it.  The most useful response is information about what your past questions cost, and the usage report gives you that.
