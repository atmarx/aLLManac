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
---

# Reading your own numbers

Ask the **Usage Guide** at the front door for **your usage** and you get something in this shape:

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

**Not always, and this trips people up:** a few requests are made on your behalf without you typing anything.  Naming a new conversation is the common one — when a thread acquires a title by itself, that was a small extra request against your account.  They are tiny and they are real, and if your request count runs slightly ahead of the messages you remember sending, that is almost certainly why.

## Tokens in, and tokens out

**"In"** is everything sent to the model: your message, the conversation behind it, any passages pulled from attached documents, and the agent's own instructions.

**"Out"** is what the model wrote back.

On virtually every real account, **"in" is ten to fifty times larger than "out."**  That ratio is not a problem and it is not something to fix — it is [the conversation being re-sent](context-is-the-conversation.md), which is how these systems work.

What the ratio is genuinely useful for is noticing change in yourself over time.  If it climbs steeply over a term, you are probably running longer threads than you used to, which is the most common way usage grows without anyone deciding anything.

## Chat, and API keys

The split between the two ways you can reach a model.

**Chat** is the browser.  **API keys** is everything else — your own editor, a script, a coding tool pointed at the platform gateway.

These are limited by different things, which is worth holding onto: [the chat window is capped in length](context-is-the-conversation.md) and your key is capped in money.  A coding session will not be trimmed the way a chat conversation is; it will simply spend, and stop when the key's budget is gone.

If you have never set up a key, this line reads `API keys: 0` and you can ignore it.  If you use one, expect it to dominate — coding tools send a great deal of context by design, because that is what makes them useful.

## The per-model table

Which models you used, and how much of your total went to each.

The useful reading is concentration.  If nearly everything sits against one expensive model, there may be a cheaper one that would have done for some of it.  That is a nudge rather than an instruction — [model choice is the third lever, not the first](what-actually-costs.md).

## Spend

Dollars, always shown, even when it rounds to nothing.

**It is printed at zero on purpose.**  The number is there so you can build a sense of what things cost, and hiding it until it gets large teaches exactly the wrong lesson to the person who most deserves to know their habits are economical.

Two things it counts that people do not expect:

- **Spending you did outside the chat window.**  A coding session on your key lands in this number, so your balance can move in a way your visible chat history does not explain.  Nothing is wrong when that happens.
- **Nothing at all, for some models.**  Models running on institutional hardware carry no per-token price, so they add tokens and no dollars.  On a course using those, token counts are the real measure and the dollar figure will look implausibly small.

## The three things this cannot tell you

**What you talked about.**  The ledger records model, counts, cost and time.  It does not store your messages, and no usage report has ever read one.

**Whether a question was worth asking.**  We have the price and nobody has the value.  This is a permanent limit rather than a feature waiting to be built.

**How you compare to anyone else.**  There is no ranking.  Your instructor's view of the course does list each student — requests, tokens, and when each was last active — because "who hasn't started yet?" is a question only names can answer.  But the list runs alphabetically, never by who used the most, dollars appear only as a course total, and it shows counts, not content; what your instructor can read is a separate question, answered in [Who can see it](../your-data/who-can-see-it.md).  Nobody is scored on the number, because it answers whether the budget was sized right and nothing about whether the work was any good.

## Two data notes

**The ledger runs about ten seconds behind.**  A request you just made may not be in the total yet.  Ask again in a moment rather than concluding it was not counted.

**A key belongs to one course.**  If you are enrolled in three courses you have three keys, and each spends its own course's budget.  "My API key" is not really a thing here — it is "my key for this course," and pasting the wrong one into a tool means a different course pays for your afternoon.
