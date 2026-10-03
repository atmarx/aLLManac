---
title: Reading your own numbers
description: Every figure on your usage report, one at a time — what it counts, what moves it, what a surprising value usually means, and the three things the ledger can never tell you.
audience: student
also_reaches: [faculty]
status: draft
owner: piper
tags: [metering, attribution, cost-intuition, token-economy, student-right, ai-literacy]
tethered_to:
  - usage-mcp/server.py
  - docs/admin-guide.md
  - litellm/config.yaml
  - .env.example
---

# Reading your own numbers

Ask the **Usage Guide** in the {{PLATFORM}} chat for **your usage** and you get something in this shape:

```
Usage for you@university.edu — last 7 days (since 2026-09-15)

Total: 412 requests · 1,840,220 tokens (1,790,118 in / 50,102 out)
Chat: 214 requests · API keys: 198 requests

| model        | requests | tokens (in / out)       | last used        |
|--------------|---------:|-------------------------|------------------|
| {{MODEL}} |      380 | 1,700,400 (1,655,000 / 45,400) | 2026-09-21 14:02 UTC |
| hosted-model   |     32 | 139,820 (135,118 / 4,702)      | 2026-09-20 09:41 UTC |

Spend: $2.41
```

Here is each line.

## Requests

One request is one time the platform asked a model for something.  Usually that is one message you sent.

Not always.  A few requests are made on your behalf without you typing anything.  Naming a new conversation is one — when a thread gets a title by itself, that was a small extra request against your account.  The bigger one is an agent looking something up: searching its knowledge files or calling a tool is a request of its own, before the one that writes your answer.  If your request count runs ahead of the messages you remember sending, that is almost certainly why.

## Tokens in, and tokens out

**"In"** is everything sent to the model: your message, the conversation behind it, any passages pulled from attached documents, the agent's own instructions, and the descriptions of any tools the agent has.

**"Out"** is what the model wrote back.

On virtually every real account, **"in" is ten to fifty times larger than "out."**  That ratio is [the conversation being re-sent](context-is-the-conversation.md).  It is how these systems work, and there is nothing to fix.

The ratio is useful for noticing change over time.  If it climbs steeply over a term, you are probably running longer threads than you used to, which is the most common way usage grows without anyone deciding anything.

## Chat, and API keys

The split between the two ways you can reach a model.

**Chat** is the browser.  **API keys** is everything else — your own editor, a script, a coding tool pointed at the platform gateway.

They are limited by different things.  The chat [trims a conversation to the course's length limit](context-is-the-conversation.md) and draws on the course's budget.  A key skips that length limit — it gets whatever the model's server will take — and stops when the key's own budget or the course's runs out.

Neither one limits how often you send.  There are no per-message rate limits here, in the chat or on a key: the budget is the limit.  The chat does keep a few counters against abuse — on attaching files, on importing and copying conversations, and on voice — and ordinary use stays well under them.  If a coding tool reports a 429, that is the model's server being busy — [When it breaks](../building-with-code/when-it-breaks.md) has what to do.

If you have never set up a key, this line reads `API keys: 0 requests` and you can ignore it.  If you use one, expect it to dominate — coding tools send a great deal of context by design.  That is what makes them useful.

## The per-model table

Which models you used, and how much of your total went to each.

The useful reading is concentration.  If nearly everything sits against one expensive model, there may be a cheaper one that would have done for some of it.  Take that as a nudge — [model choice is the third lever, not the first](what-actually-costs.md).

## Spend

Dollars, always shown, even when it rounds to nothing.  The number is there so you can build a sense of what things cost.  Hiding it until it got large would teach the wrong lesson to the person who most deserves to know their habits are economical.

It also counts things people do not expect:

- **Spending you did outside the chat window.**  A coding session on your key shows up in this number, so your balance can move in a way your visible chat history does not explain.  Nothing is wrong when that happens.
- **Your conversations with the guides.**  The {{PLATFORM}} chat counts as chat here, so asking the Usage Guide for these numbers is itself in them.  The {{PLATFORM}} chat pays for those, not your course.
- **Nothing at all, for some models.**  Models running on institutional hardware have no per-token price, so they add tokens and no dollars.  On a course using those, token counts are the real measure and the dollar figure will look implausibly small.

## The three things this cannot tell you

**What you talked about.**  The ledger records model, counts, cost and time.  It does not store your messages, and no usage report has ever read one.

**Whether a question was worth asking.**  We have the price and nobody has the value.  That limit is permanent; no feature is waiting to fix it.

**How you compare to anyone else.**  There is no ranking.  Your instructor's view of the course does list each student — requests, tokens, and when each was last active — because "who hasn't started yet?" is a question only names can answer.  But the list runs alphabetically, never by who used the most.  Dollars appear only as a course total, and it shows counts, not content.  What your instructor can read is a separate question, answered in [Who can see it](../your-data/who-can-see-it.md).  Nobody is scored on the number.  It answers whether the budget was sized right, and says nothing about whether the work was any good.

## Two data notes

**The ledger runs about ten seconds behind.**  A request you just made may not be in the total yet.  Ask again in a moment before deciding it was not counted.

**A key belongs to one course.**  If you are enrolled in three courses you have three keys, and each spends its own course's budget.  There is no "my API key" here, only "my key for this course," and pasting the wrong one into a tool means a different course pays for your afternoon.
