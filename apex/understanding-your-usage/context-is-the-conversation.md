---
title: What context actually is
description: The whole conversation, re-sent from the beginning on every turn — why the fortieth message costs eighty times the first, and why what the assistant forgets is the start, not the middle.
audience: student
also_reaches: [faculty]
status: draft
owner: piper
tags: [context-window, token-economy, cost-intuition, metering, ai-literacy, librechat]
tethered_to:
  - registrar/render.py
  - docs/design-walls.md
---

# What context actually is

## The question

Everyone works out eventually that something called *context* exists, that it has a size, and that running out of it is bad.  Almost nobody is told what it is, so everyone builds a mental model from the symptoms.

## The picture almost everyone builds

The model has a working memory.  It holds what you have been discussing.  It has a capacity, and as you talk, it fills up.  When it is full, older things fall out — which is why the assistant forgets what you said at the start of a long session.

This is a good guess.  It explains the forgetting, it explains the limit, and it matches how memory works in every other context you have encountered, including your own.  It is also the reason people say things like "the context got full" and "it lost the thread," which are the phrases a tank produces.

It is wrong, and almost everything confusing about your usage numbers follows from it.

## What is actually happening

**The model has no memory at all.**  Not a short one — none.  Between one message and the next it retains nothing whatsoever about you or your conversation.

So when you send your fortieth message, the software sends the model **the entire conversation from message one**, with your new message on the end, and asks it to continue.  The model reads all of it, writes a reply, and forgets every word.  Then you type again, and the whole thing is sent once more, one exchange longer.

There is no tank.  There is a stack of paper that gets photocopied and handed over in full, every single time, and grows by one page each round.

That stack explains two things you have probably already noticed.

## Why the fortieth message costs so much more than the first

The difference is what gets sent with it.

Suppose each exchange — your question plus the reply — runs about 500 tokens.  Then:

| At turn | The conversation is | You send |
|---|---:|---:|
| 1 | 500 tokens | ~250 |
| 10 | 5,000 tokens | ~4,750 |
| 40 | 20,000 tokens | ~19,750 |

Add up that last column across all forty turns and you get roughly **400,000 tokens sent, to hold a conversation that is 20,000 tokens long.**  Twenty times the length of the thing itself.  None of it was waste: the model had no other way to know what you had been discussing.

Remember the shape of that growth:

> **Twice as many turns is roughly four times the cost, not twice.**

A conversation of eighty turns in this example runs about 1.6 million tokens.  This is the single most important fact about using these tools well, it is invisible from inside the chat window, and it explains the advice at the top of [what actually costs something](what-actually-costs.md).

## Why it forgets the beginning specifically

Every model's server has a ceiling on how much it will take at once, and each course on this platform sets its own limit too — a cap on what one conversation can spend, which is not always below what the server takes.  Past the server's ceiling, some servers refuse the request and some drop the front of it and answer anyway.

When your re-sent conversation grows past the limit, something has to go — and what goes is **the oldest part**.  Not faded, not compressed, not deprioritised.  Removed.

That gives the forgetting its shape.  A human memory loses the middle, the boring parts, the things that did not matter.  This loses the beginning, precisely and completely, including the part where you explained what you were trying to do.  If an assistant has been sharp for an hour and suddenly seems to have lost the plot, that is usually what happened.  Start fresh and say the important part again.

## The part that surprises people about attached documents

If you are talking to an agent with knowledge files, those files are not sitting in the model's head either.

What happens is that the agent decides to search its documents, writes the search itself, and the passages that look relevant get **pasted into the conversation** — invisibly, as extra context, and as a request of its own.  A well-targeted question pulls in a paragraph.  A vague one pulls in a lot more, because more things looked equally plausible.

So the guides are cheap to ask precise questions of and expensive to ask woolly ones, for a reason that has nothing to do with the length of what you typed.

## What is still confusing about this

Whether you can watch the number while you work, we are not yet sure.  The version of the chat we run ships a context gauge in the composer, switched on by default, and we do not switch it off — so it is probably there, above the box you type into.  We have reasoned about that from a config file, and you are looking at the screen.  If you can see it, that gauge answers everything below.  If you cannot, tell us.

Nothing warns you before the limit bites.  The conversation does not announce that it just dropped your opening message.  It stops knowing it and goes on confidently, which is the worst possible way to find out.

What falls off the front may not be yours, either.  Everything above describes losing the beginning of *your* conversation.  But an agent's own instructions sit in front of the first thing you ever typed — that is what makes it a guide and not a general chatbot — so they are first in the queue to go.  You get no error when that happens.  You get a guide that starts answering questions it would have declined, inventing details it would have refused to guess at, or sounding like something else.  **The tell is that it is fine in a new conversation and strange in a long one.**  If you see that, the model is fine; the conversation outgrew its window.  Start a fresh one, and mention it to us — it is a setting on our side, and you will notice it long before we do.

## Try it yourself

Ask the **Usage Guide** in the {{PLATFORM}} chat for **your usage** and look at the two token figures side by side — the "in" number against the "out" number.

On almost any real account, "in" is ten to fifty times larger.  That ratio is your conversations being re-sent, in one number.
