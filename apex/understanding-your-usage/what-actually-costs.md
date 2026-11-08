---
title: What actually costs something
description: The levers that move your usage, ranked by size, including whether writing in clipped, telegraphic sentences is worth it (mostly no, and in one specific place yes).
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

Advice about using these tools economically mixes things that matter enormously with things that are rounding error, and presents them all with the same confidence.  The levers that change your usage, ranked largest first, are: starting a new conversation when the subject changes, not pasting more than the question needs, choosing the model, and phrasing the question.

Each lever follows from one fact, explained in [what context actually is](context-is-the-conversation.md): the whole conversation is re-sent to the model on every turn.

## 1. Starting a new conversation when the subject changes

Starting a new conversation when the subject changes saves more than all the other levers combined, by a wide margin.

A conversation costs roughly the square of its length.  Forty turns in one thread costs about twice what the same forty turns cost split into two threads of twenty, and about four times what they cost split into four threads of ten.  The work, the questions and the answers are identical in each case.

Starting fresh feels wasteful.  You lose the setup, you have to re-explain, and the thread you were in still works fine.  So people keep going, and a conversation that began as a question about a citation is still running four hours later.  By then it has covered three unrelated topics and sends all of them on every turn.

> **When you change subject, start a new conversation.**  If the last ten exchanges have nothing to do with the next one, you are paying to send them for nothing.

There is a real exception to starting fresh.  When the earlier context matters, such as a document you worked through together or a problem you have been narrowing down, keeping that context is what you are paying for, and the money is well spent.  The test is whether the old material is still needed for the next answer.  Length alone doesn't decide it.

## 2. Not pasting more than the question needs

Attaching a forty-page PDF to ask about one table is a large, invisible cost, and the cost repeats.  The PDF [goes into every later turn of that conversation](context-is-the-conversation.md), not only the turn where you attached it.

Pasting only the paragraph you mean is usually better as well as cheaper.  The model does not have to weigh thirty-nine irrelevant pages while it works out what you want, so the answer is more focused.

## 3. Which model you point at

Models differ in price by more than an order of magnitude, and the most capable model is not automatically the right one for a simple task like reformatting a list.

Model choice is a real lever, and it ranks third because its effect is bounded.  Choosing well saves a fraction of each request.  Starting a new conversation, the first lever, changes the number of tokens in each request by multiples.  Choose a sensible model, and don't spend long on the decision.

## 4. How you phrase the question

Phrasing is the lever people ask about most.  Writing in clipped, telegraphic sentences, with articles and pronouns stripped out (sometimes called "caveman speak"), does reduce tokens.  You can take perhaps a quarter off the length of what you type, and the model will usually understand you fine.  The instinct is reasonable.

In a normal conversation, writing tersely is also **almost entirely pointless**.  Your question is not the expensive part of a request.  On turn twenty of a conversation, what you typed might be two percent of what gets sent.  The other ninety-eight percent is the conversation behind it, which you did not retype and cannot shorten by writing tersely.  Shaving a quarter off two percent saves you half of one percent.

Terse phrasing also has a failure mode that costs more than it saves.  Terse instructions tend to be ambiguous, an ambiguous instruction can produce an answer to the wrong question, and correcting that answer costs a whole extra turn.  The extra turn re-sends the entire conversation again.  One misunderstanding wipes out the savings from a hundred clipped sentences.

> **With forty turns of history behind a question, the wording of the question makes almost no difference to its cost.**

### Where terseness pays

Tight wording pays off in text that repeats.  A sentence you type once is sent as part of that conversation from then on.  Some text is sent on *every turn of every conversation, forever*.  Text that repeats this way includes:

- an agent's instructions
- a document attached to an agent that gets consulted constantly
- a system prompt somebody wrote once and never revisited

Removing ten words from an agent's instructions removes ten words from every request anyone ever makes to that agent.  The one edit saves tokens on thousands of requests, and agent instructions are where tight wording repays the effort.

If you build agents, write their instructions briefly.  When you are asking a question, write in ordinary sentences.  You will get a better answer, and the extra words cost you essentially nothing.

## What none of this can tell you

The four levers are all about how much a question costs.  Nothing in the usage pages, and nothing in any ledger on this platform, can tell you whether a question was worth asking.

The ledger records the price of a question, and nothing records its value.  In coursework, price and value frequently run in opposite directions.  An expensive, circling, inefficient-looking conversation where you finally understood something is often the one that did its job.  A tool that flagged that conversation as waste would be confidently wrong about what matters most.

Use the four levers to stop spending money by accident.  Do not use them to talk yourself out of asking a question.
