---
title: Why is it measured in tokens?
description: A token is not a word and it is not a subway token — it is a piece of text, and understanding why the unit is that strange is the first step to reading any of your numbers.
audience: student
also_reaches: [faculty]
status: draft
owner: piper
tags: [token-economy, metering, cost-intuition, context-window, ai-literacy]
tethered_to:
  - usage-mcp/server.py
---

# Why is it measured in tokens?

The word is doing you no favours, so let us deal with it first.

**A subway token is a unit of access.**  One token, one ride, and it costs the same whether you go two stops or twenty.  That is a perfectly sensible thing to call a token, and if that is the picture you brought here, it is a reasonable guess that happens to be exactly backwards.

**A language model's token is a unit of text.**  It is a piece of a word.  You are not buying rides; you are paying by the yard, and the token is how the yard gets measured.

## Why not just count words?

Because the model does not read words.

Before any text reaches the model, it is chopped into pieces from a fixed list of tens of thousands to a few hundred thousand fragments, depending on the model.  Common words are usually one piece.  Longer or rarer words get broken into several.  Spaces and punctuation are in there too.  The list was built by looking at an enormous amount of text and finding which chunks repeat, which means it reflects ordinary writing and treats anything unusual as a series of small parts.

The practical consequences are mildly entertaining:

- **`notebook`** is a common enough word to be a piece or two.
- **`nOTEbooK`** is not a word at all, so it gets taken apart into something like `n` + `OTE` + `boo` + `K` — **roughly twice the tokens for the same eight letters**, purely because of the capital letters scattered through it.
- Numbers get split in ways that have nothing to do with how you would say them.  `2026` may be one piece; `20260921` is several.
- Languages other than English, and code, and anything with unusual spacing, all run token counts up relative to their length.

None of that is worth optimising around.  It is worth knowing because it explains why the count never quite matches your intuition, and why "just count the words" was never going to work.

## The numbers you actually need

Two, and they will carry you through everything else:

> **1,000 tokens is about 750 words, or roughly a page and a half of ordinary prose.**

> **A ten-page syllabus is somewhere around 6,500 tokens.**

That is enough precision for every decision you will actually make.  If you find yourself wanting a more exact figure, you are almost certainly optimising the wrong end of the problem — [what actually costs something](what-actually-costs.md) covers which end is which.

## The unit does two jobs, and that is the confusing part

This is where most of the muddle comes from, so it is worth separating carefully.

**Tokens are the billing unit.**  Every request adds up what went in and what came out, applies the model's rate, and writes a line to the ledger.  That is money.

**Tokens are also the capacity unit.**  Every model has a limit on how much text it can consider at once — its *context window* — and that limit is counted in the same tokens.  That is space.

One number, two meanings, and they behave differently.  Money accumulates forever: every token you ever spend is added to a running total that does not reset.  Space does not accumulate at all — it is measured fresh on every single request, and what fills it is the conversation you are currently in.

Confusing the two is what produces the tank picture: people notice the space limit behaving like a container, notice the money number going up, and conclude that one causes the other.  They are related, but not the way it looks — and the relationship is the subject of [the next page](context-is-the-conversation.md).

## Try it yourself

Ask the **Usage Guide** at the front door for **your usage**.  You will get something like:

```
Total: 412 requests · 1,840,220 tokens (1,790,118 in / 50,102 out)
```

Look at those two numbers beside each other.  **You sent thirty-five times more text than you received**, which sounds wrong until you know why, and it is the single most useful thing on the page once you do.
