---
title: Why is it measured in tokens?
description: A token is a piece of text, often part of a word.  Knowing what a token is, and why it is not a word, is the first step to reading any of your usage numbers.
audience: student
also_reaches: [faculty]
status: draft
owner: piper
tags: [token-economy, metering, cost-intuition, context-window, ai-literacy]
tethered_to:
  - usage-mcp/server.py
---

# Why is it measured in tokens?

The word *token* suggests the wrong picture, so start with what it does not mean.

A subway token is a unit of access.  One token buys one ride, and it costs the same whether you go two stops or twenty.  A language model's token does not work that way.

**A language model's token is a unit of text.**  A token is a piece of text, often part of a word.  You pay by the amount of text, and tokens are how that amount is measured.

## Why not just count words?

The model does not read words, so a word count does not match what the model processes.

Before any text reaches the model, the text is split into pieces from a fixed list of tens of thousands to a few hundred thousand fragments, depending on the model.  Common words are usually one piece.  Longer or rarer words get broken into several.  Spaces and punctuation are in the list too.  The list was built by looking at an enormous amount of text and finding which fragments repeat.  As a result, ordinary writing splits into few pieces, and anything unusual becomes a series of small parts.

Some examples of how text splits into tokens:

- `notebook` is a common enough word to be a piece or two.
- `nOTEbooK` is not a word at all, so it gets taken apart into something like `n` + `OTE` + `boo` + `K`.  The scattered capital letters make it roughly twice the tokens for the same eight letters.
- Numbers get split in ways that have nothing to do with how you would say them.  `2026` may be one piece or two, and `20260921` is several.
- Languages other than English, code, and text with unusual spacing all use more tokens relative to their length.

You do not need to optimize around how text splits.  Tokenization explains why a token count never quite matches your sense of how long a text is, and why counting words does not work.

## The numbers you need

Two rough conversions cover everything else:

> **1,000 tokens is about 750 words, or roughly a page and a half of ordinary prose.**

> **A ten-page syllabus is somewhere around 6,500 tokens.**

Those two conversions are precise enough for every decision you will make about usage.  If you want a more exact token figure, you are almost certainly focusing on the wrong part of the cost.  [What actually costs something](what-actually-costs.md) ranks which parts matter.

## The unit does two jobs, and that is the confusing part

Tokens are the **billing unit**.  For every request, the platform adds up the tokens that went in and the tokens that came out, applies the model's input and output rates, and writes a line to the ledger.  In this sense tokens measure money.

Tokens are also the **capacity unit**.  Every model has a limit on how much text it can consider at once, called its *context window*, and that limit is counted in the same tokens.  In this sense tokens measure space.

The two uses of tokens behave differently.  Spending accumulates forever: every token you spend is added to a running total that does not reset.  Capacity does not accumulate at all.  The context window is measured fresh on every request, and what fills it is the conversation you are currently in.

Confusing billing and capacity produces the common picture of context as a tank.  People notice the capacity limit behaving like a container, notice the spending total going up, and conclude that one causes the other.  The two are related, but not in that way.  [What context actually is](context-is-the-conversation.md) explains how they are related.

## Try it yourself

Ask the **Usage Guide** in the {{PLATFORM}} chat for **your usage**.  The report includes a total line like this one:

```
Total: 412 requests · 1,840,220 tokens (1,790,118 in / 50,102 out)
```

Compare the "in" and "out" token figures.  In this example, you sent thirty-five times more text than you received.  The reason is that every turn re-sends the whole conversation to the model, as [What context actually is](context-is-the-conversation.md) explains.
