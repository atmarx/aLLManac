---
title: What context actually is
description: Not a tank that fills up and not a memory that fades — the whole conversation, re-sent from the beginning on every turn, which is why the fortieth message costs twenty times the first and why it forgets the start rather than the middle.
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

So when you send your fortieth message, the software quietly sends the model **the entire conversation from message one**, with your new message on the end, and asks it to continue.  The model reads all of it, writes a reply, and forgets every word.  Then you type again, and the whole thing is sent once more, one exchange longer.

There is no tank.  There is a stack of paper that gets photocopied and handed over in full, every single time, and grows by one page each round.

Two things fall out of that immediately, and both of them explain something you have probably already noticed.

## Why the fortieth message costs so much more than the first

Not because it is late.  Because of what gets sent with it.

Suppose each exchange — your question plus the reply — runs about 500 tokens.  Then:

| At turn | The conversation is | You send |
|---|---:|---:|
| 1 | 500 tokens | ~250 |
| 10 | 5,000 tokens | ~4,750 |
| 40 | 20,000 tokens | ~19,750 |

Add up that last column across all forty turns and you get roughly **400,000 tokens sent, to hold a conversation that is 20,000 tokens long.**  Twenty times the length of the thing itself, and none of it was waste — every re-send was necessary, because the model genuinely had no other way to know what you had been discussing.

The shape of that growth is the part worth carrying away:

> **Twice as many turns is roughly four times the cost, not twice.**

A conversation of eighty turns in this example runs about 1.6 million tokens.  This is the single most important fact about using these tools well, it is invisible from inside the chat window, and it is why the advice at the top of [what actually costs something](what-actually-costs.md) is what it is.

## Why it forgets the beginning specifically

Every model has a ceiling on how much it can be handed at once, and each course on this platform sets its own limit underneath that.

When your re-sent conversation grows past the limit, something has to go — and what goes is **the oldest part**, dropped before the request is sent.  Not faded, not compressed, not deprioritised.  Removed.

That is why the forgetting has the shape it does.  A human memory loses the middle, the boring parts, the things that did not matter.  This loses the beginning, precisely and completely, including the part where you explained what you were trying to do.  If an assistant has been sharp for an hour and suddenly seems to have lost the plot, that is usually what happened, and the fix is not to repeat yourself louder — it is to start fresh and say the important part again.

## The part that surprises people about attached documents

If you are talking to an agent with knowledge files, those files are not sitting in the model's head either.

What happens is that your question is used to search the documents, and the passages that look relevant get **pasted into the conversation** before it is sent — invisibly, as extra context, on that turn.  A well-targeted question pulls in a paragraph.  A vague one pulls in a lot more, because more things looked equally plausible.

So the guides are cheap to ask precise questions of and expensive to ask woolly ones, for a reason that has nothing to do with the length of what you typed.

## What is still confusing about this

Two things, honestly.

**Whether you can watch the number while you work, we are not currently sure.**  This page said flatly that you could not.  That was written from the running total you can ask for, and it went further than anyone had checked: the version of the chat we run ships a context gauge in the composer, switched on by default, and we do not switch it off.  So it is probably there, above the box you type into, and this page was apologising for a missing instrument that may have been in front of you the whole time.  **If you can see it, that gauge is the honest answer to everything below** — and if you cannot, telling us is a genuinely useful thing to do, because you are looking at a screen we have been reasoning about from a config file.

**Nothing warns you before the limit bites.**  The conversation does not announce that it just dropped your opening message.  It simply stops knowing it, and carries on confidently, which is the worst possible way for that to be communicated.

**And what falls off the front may not be yours.**  Everything above describes losing the beginning of *your* conversation.  But an agent's own instructions sit in front of the first thing you ever typed — that is what makes it a guide and not a general chatbot — so they are first in the queue to go.  When that happens you do not get an error.  You get a guide that starts answering questions it would have declined, inventing details it would have refused to guess at, or simply sounding like something else.  **The tell is that it is fine in a new conversation and strange in a long one.**  If you see that, you have not found a bad model; you have found a conversation that outgrew its window.  Start a fresh one, and mention it to us — it is a setting, it is on our side, and it is the kind of thing that is much easier for you to notice than for us.

## Try it yourself

Ask a guide for **your usage** and look at the two token figures side by side — the "in" number against the "out" number.

On almost any real account, "in" is ten to fifty times larger.  That ratio is this entire page, expressed as a single measurement: it is the sound of your conversations being re-sent.
