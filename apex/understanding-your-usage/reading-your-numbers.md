---
title: Reading your own numbers
description: Every figure on your usage report, one at a time.  What it counts, what moves it, what a surprising value usually means, and the three things the ledger can never tell you.
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

Each part of the usage report has its own heading: Requests, Tokens in and tokens out, Chat and API keys, the per-model table, and Spend.

## Requests

One request is one time the platform asked a model for something.  Usually one request is one message you sent.

Some requests are made on your behalf without you typing anything.  Naming a new conversation is one: when a thread gets a title by itself, that was a small extra request against your account.  The bigger source is an agent looking something up.  Searching its knowledge files or calling a tool is a request of its own, made before the request that writes your answer.  If your request count runs ahead of the messages you remember sending, these extra requests are almost certainly why.

## Tokens in, and tokens out

**"In"** is everything sent to the model: your message, the conversation behind it, any passages pulled from attached documents, the agent's own instructions, and the descriptions of any tools the agent has.

**"Out"** is what the model wrote back.

On virtually every real account, "in" is ten to fifty times larger than "out."  The size of that ratio comes from [the conversation being re-sent](context-is-the-conversation.md) on every turn.  A high ratio is how these systems work, and there is nothing to fix.

The in-to-out ratio is useful for noticing change over time.  If the ratio climbs steeply over a term, you are probably running longer threads than you used to.  Longer threads are the most common way usage grows without anyone deciding anything.

## Chat, and API keys

The usage report splits your requests between the two ways you can reach a model.

**Chat** is the browser.  **API keys** covers everything else: your own editor, a script, or a coding tool pointed at the platform gateway.

Chat and API keys are limited by different things.  The chat [trims a conversation to the course's length limit](context-is-the-conversation.md) and draws on the course's budget.  A key skips the course's length limit and gets whatever the model's server will take.  A key stops when the key's own budget or the course's budget runs out.

Neither chat nor an API key limits how often you send.  There are no per-message rate limits on this platform, in the chat or on a key.  The budget is the limit.  The chat does keep a few counters against abuse (on attaching files, on importing and copying conversations, and on voice), and ordinary use stays well under them.  If a coding tool reports a 429, the model's server is busy.  [When it breaks](../building-with-code/when-it-breaks.md) explains what to do.

If you have never set up a key, the API keys figure reads `API keys: 0 requests` and you can ignore it.  If you use a key, expect it to account for most of your usage.  Coding tools send a great deal of context by design, and that context is what makes them useful.

## The per-model table

The per-model table shows which models you used, and how much of your total went to each.

The useful thing to look for in the per-model table is concentration.  If nearly everything sits against one expensive model, there may be a cheaper one that would have done for some of it.  Take that as a suggestion.  [Model choice is the third lever, not the first](what-actually-costs.md).

## Spend

Spend is shown in dollars, always, even when it rounds to nothing.  The spend figure is there so you can build a sense of what things cost.  If the figure were hidden until it got large, the people whose habits are already economical would never learn that they are.

The spend figure also counts things people do not expect:

- **Spending you did outside the chat window.**  A coding session on your key shows up in the spend figure, so your balance can move in a way your visible chat history does not explain.  Nothing is wrong when that happens.
- **Your conversations with the guides.**  The {{PLATFORM}} chat counts as chat here, so asking the Usage Guide for these numbers is itself in them.  The {{PLATFORM}} chat pays for those conversations, not your course.
- **Nothing at all, for some models.**  Models running on institutional hardware have no per-token price, so they add tokens and no dollars.  On a course using those models, token counts are the real measure and the dollar figure will look implausibly small.

## The three things this cannot tell you

**What you talked about.**  The usage ledger records model, counts, cost and time.  The ledger does not store your messages, and no usage report has ever read one.

**Whether a question was worth asking.**  The ledger records what a question cost, and nothing records what it was worth.  That limit is permanent, and no planned feature will fix it.

**How you compare to anyone else.**  The usage reports have no ranking.  Your instructor's view of the course does list each student, with requests, tokens, and when each was last active.  The list includes names because "who hasn't started yet?" is a question only names can answer.  The list runs alphabetically, never by who used the most.  Dollars appear only as a course total, and the instructor's view shows counts, not content.

What your instructor can read is a separate question, answered in [Who can see it](../your-data/who-can-see-it.md).  Nobody is scored on usage numbers.  The instructor's view answers whether the course budget was sized right, and says nothing about whether the work was any good.

## Two data notes

**The ledger runs about ten seconds behind.**  A request you just made may not be in the total yet.  Ask again in a moment before deciding it was not counted.

**A key belongs to one course.**  If you are enrolled in three courses you have three keys, and each key spends its own course's budget.  There is no single personal API key on this platform, only a key for each course.  Pasting the wrong course's key into a tool means a different course pays for that work.
