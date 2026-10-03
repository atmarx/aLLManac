---
title: What actually costs something
description: The levers that move your usage, ranked by size — including whether writing in clipped, telegraphic sentences is worth it (mostly no, and in one specific place yes).
audience: student
also_reaches: [faculty]
status: draft
owner: piper
tags: [cost-intuition, token-economy, context-window, metering, ai-literacy, equity]
tethered_to:
  - usage-mcp/server.py
  - registrar/render.py
---

# What actually costs something

Advice about using these tools economically mixes things that matter enormously with things that are rounding error, all in the same confident tone.  The ranking below sorts them by size.

It assumes you have read [what context actually is](context-is-the-conversation.md).  Every item follows from that one fact.

## 1. Starting a new conversation when the subject changes

**This one is worth more than all the others combined**, by a wide margin.

A conversation costs roughly the square of its length.  Forty turns in one thread costs about twice what the same forty turns cost split into two threads of twenty, and about four times what they cost split into four threads of ten — for identical work, identical questions, identical answers.

The catch is that starting fresh feels wasteful.  You lose the setup, you have to re-explain, and the thread you were in still works fine.  So people don't, and the conversation that began as a question about a citation is still running four hours later having covered three unrelated topics, sending all of it on every turn.

> **When you change subject, change conversation.**  If the last ten exchanges have nothing to do with the next one, you are paying to send them for nothing.

There is a real exception.  When the earlier context matters — a document you worked through together, a problem you have been narrowing down — keeping it is what you are paying for, and that is money well spent.  The test is whether the old material is still doing work.  Length alone doesn't decide it.

## 2. Not pasting more than the question needs

Attaching a forty-page PDF to ask about one table is a large, invisible cost, and it repeats — [it goes into every subsequent turn of that conversation](context-is-the-conversation.md), not just the one where you attached it.

A few seconds of thought here pays for itself many times over.  The paragraph you mean, pasted directly, is usually better as well as cheaper.  The model isn't weighing thirty-nine irrelevant pages while it works out what you want, so the answer is more focused.

## 3. Which model you point at

Models differ in price by more than an order of magnitude, and the most capable one is not automatically the right one for reformatting a list.

It is a real lever, and it sits third because it is bounded.  Choosing well saves a fraction of each request; the first item on this list changes the number of tokens in the request by multiples.  Do it, and don't agonise over it.

## 4. How you phrase the question

The one everybody asks about.  Caveman speak — clipped, telegraphic, articles and pronouns stripped out — does reduce tokens.  You can take perhaps a quarter off the length of what you type, and the model will usually understand you fine.  The instinct is not silly.

In a normal conversation it is also **almost entirely pointless**.  The arithmetic:

Your question is not the expensive part.  On turn twenty of a conversation, what you typed might be two per cent of what gets sent; the other ninety-eight per cent is the conversation behind it, which you did not retype and cannot shorten by writing tersely.  Shaving a quarter off two per cent saves you half of one per cent.

And it has a failure mode that costs more than it saves.  Terse instructions are ambiguous instructions, ambiguity produces an answer to the wrong question, and correcting it costs **a whole extra turn** — which re-sends the entire conversation again.  One misunderstanding wipes out the savings from a hundred clipped sentences.

> **Worrying about the wording of your question with forty turns of history behind it is fussing over the stamp on a parcel you are shipping by air freight.**

### Where terseness genuinely pays

**Trim what repeats, not what you say once.**

A sentence you type once is sent as part of that conversation from then on.  But some text is sent on *every turn of every conversation, forever*:

- an agent's instructions
- a document attached to an agent that gets consulted constantly
- a system prompt somebody wrote once and never revisited

Ten words removed from an agent's instructions is ten words removed from every request anyone ever makes to it.  That one edit is applied thousands of times, and it is where tight wording repays the effort.

So if you build agents, be brisk in the instructions.  When you are just asking a question, write like a person — you will get a better answer and it will cost you essentially nothing.

## What none of this can tell you

Every item above is about how much a question costs.  Nothing here, and nothing in any ledger on this platform, can tell you whether the question was worth asking.

We have the price and nobody has the value, and in coursework the relationship between the two is frequently inverted.  The expensive, circling, inefficient-looking conversation where you finally understood something is often the one that did its job, and a tool that flagged it as waste would be confidently wrong about the thing that matters most.

Use the ranking above to stop spending money accidentally, and not to talk yourself out of asking.
