---
title: What actually costs something
description: The levers that move your usage, ranked honestly by size — including a straight answer about whether writing in clipped, telegraphic sentences is worth it, which is mostly no and specifically yes.
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

Advice about using these tools economically is everywhere, and it is a strange mixture of things that matter enormously and things that are rounding error, delivered in the same confident tone.  This page sorts them by size.

The ranking assumes you have read [what context actually is](context-is-the-conversation.md), because every item on it is downstream of that one fact.

## 1. Starting a new conversation when the subject changes

This is not the first item because it is tidy advice.  It is first because **it is worth more than everything else on this page combined**, by a factor that is genuinely hard to overstate.

A conversation costs roughly the square of its length.  Forty turns in one thread costs about twice what the same forty turns cost split into two threads of twenty, and about four times what they cost split into four threads of ten — for identical work, identical questions, identical answers.

The catch is that starting fresh feels wasteful.  You lose the setup, you have to re-explain, and the thread you were in still works fine.  So people don't, and the conversation that began as a question about a citation is still running four hours later having covered three unrelated topics, carrying all of it on every turn.

> **When you change subject, change conversation.**  If the last ten exchanges have nothing to do with the next one, they are pure freight.

The exception is real and worth respecting: when the earlier context genuinely matters — a document you worked through together, a problem you have been narrowing down — keeping it is what you are paying for, and that is money well spent.  The test is not length.  It is whether the old material is still doing work.

## 2. Not pasting more than the question needs

Attaching a forty-page PDF to ask about one table is a large, invisible cost, and it repeats — [it goes into every subsequent turn of that conversation](context-is-the-conversation.md), not just the one where you attached it.

This is the one place where a few seconds of thought pays for itself many times over.  The paragraph you actually mean, pasted directly, is usually better as well as cheaper: it produces a more focused answer, because the model is not weighing thirty-nine irrelevant pages while trying to work out what you want.

## 3. Which model you point at

Models differ in price by more than an order of magnitude, and the most capable one is not automatically the right one for reformatting a list.

This is a real lever and it sits third because it is bounded: choosing well saves a fraction of each request, while the first item on this list changes the number of tokens in the request by multiples.  Worth doing.  Not worth agonising over.

## 4. How you phrase the question

Here is the one everybody asks about, and it deserves a straight answer rather than a diplomatic one.

**Caveman speak — clipped, telegraphic, articles and pronouns stripped out — does genuinely reduce tokens.**  You can take perhaps a quarter off the length of what you type, and the model will usually understand you fine, because meaning survives the loss of small words remarkably well.  The instinct is not silly.

It is also, in a normal conversation, **almost entirely pointless**, and the reason is arithmetic rather than taste.

Your question is not the expensive part.  On turn twenty of a conversation, what you typed might be two per cent of what actually gets sent; the other ninety-eight per cent is the conversation behind it, which you did not retype and cannot shorten by writing tersely.  Shaving a quarter off two per cent saves you half of one per cent.

And it has a failure mode that costs more than it saves.  Terse instructions are ambiguous instructions, ambiguity produces an answer to the wrong question, and correcting it costs **a whole extra turn** — which re-sends the entire conversation again.  One misunderstanding wipes out the savings from a hundred clipped sentences.

> **Worrying about the wording of your question while carrying forty turns of history is fussing over the stamp on a parcel you are shipping by air freight.**

### Where terseness genuinely pays

There is a real exception, and it is worth knowing precisely because the general advice is so weak.

**Trim what repeats, not what you say once.**

A sentence you type once is sent as part of that conversation from then on.  But some text is sent on *every turn of every conversation, forever*:

- an agent's instructions
- a document attached to an agent that gets consulted constantly
- a system prompt somebody wrote once and never revisited

Ten words removed from an agent's instructions is ten words removed from every request anyone ever makes to it.  That is the same edit, applied thousands of times, and it is the one place where being genuinely ruthless about wording repays the effort.

So if you build agents, be brisk in the instructions.  When you are simply asking a question, write like a person — you will get a better answer and it will cost you essentially nothing.

## What none of this can tell you

Every item above is about how much a question costs.  Nothing here, and nothing in any ledger on this platform, can tell you whether the question was worth asking.

That is not modesty.  It is a genuine limit: we have the price and nobody has the value, and in coursework the relationship between the two is frequently inverted.  The expensive, circling, inefficient-looking conversation where you finally understood something is often the one that did its job, and a tool that flagged it as waste would be confidently wrong about the most important thing in the room.

So use this page to stop spending money accidentally.  Do not use it to talk yourself out of asking.
