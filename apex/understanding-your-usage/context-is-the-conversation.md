---
title: What context actually is
description: Context is the whole conversation, re-sent from the beginning on every turn.  Re-sending explains why the fortieth message costs eighty times the first, and why the assistant forgets the start of a long conversation and not the middle.
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

Most people work out eventually that something called *context* exists, that it has a size, and that running out of it is bad.  Almost nobody is told what context is, so most people build a mental model from the symptoms.

## The picture almost everyone builds

The common mental model goes like this.  The model has a working memory that keeps what you have been discussing.  That memory has a capacity and fills up as you talk.  When it is full, older things fall out, and that would explain why the assistant forgets what you said at the start of a long session.

The working-memory picture is a good guess.  It explains the forgetting and the limit, and it matches how memory works everywhere else you have met it, including in your own head.  The same picture is behind phrases like "the context got full" and "it lost the thread."  The working-memory picture is also wrong, and almost everything confusing about your usage numbers follows from it.

## What happens

**The model has no memory at all.**  Between one message and the next, the model retains nothing about you or your conversation.

When you send your fortieth message, the chat software sends the model the entire conversation from message one, with your new message on the end, and asks it to continue.  The model reads all of it, writes a reply, and forgets every word.  When you type again, the whole conversation is sent once more, one exchange longer.

A better picture than a tank is a stack of paper that is photocopied and handed over in full on every turn, and grows by one page each round.

Re-sending the whole conversation explains two things you have probably noticed: later messages cost much more than early ones, and a long conversation loses its beginning.

## Why the fortieth message costs so much more than the first

The fortieth message costs more because of what gets sent with it.

Suppose each exchange (your question plus the reply) runs about 500 tokens.  The amount sent grows like this:

| At turn | The conversation is | You send |
|---|---:|---:|
| 1 | 500 tokens | ~250 |
| 10 | 5,000 tokens | ~4,750 |
| 40 | 20,000 tokens | ~19,750 |

Added up across all forty turns, the "You send" column comes to roughly **400,000 tokens sent, for a conversation that is 20,000 tokens long**.  That is twenty times the length of the conversation itself.  None of it was waste.  The model had no other way to know what you had been discussing.

The total grows much faster than the number of turns:

> **Twice as many turns is roughly four times the cost, not twice.**

In the same example, a conversation of eighty turns runs about 1.6 million tokens.  The way cost grows with conversation length is the most important fact about using these tools well.  The growth is invisible from inside the chat window.  It is the reason for the first lever in [what actually costs something](what-actually-costs.md): start a new conversation when the subject changes.

The figures in the table are token counts, and the ledger records them that way.  Some hosted providers discount input they have seen recently.  OpenAI's [prompt caching](https://developers.openai.com/api/docs/guides/prompt-caching) is on by default and takes up to 95% off reused tokens.  In dollars, the cost of a long conversation can grow more gently as a result, but it still grows faster than the number of turns.

## Why it forgets the beginning specifically

Every model's server has a ceiling on how much it will take at once.  Each course on this platform sets its own limit too: a cap on how many tokens of one conversation are sent with each request, which is not always below what the server takes.  Past the server's ceiling, some servers refuse the request and some drop the oldest turns and answer anyway.

When your re-sent conversation grows past the limit, part of it has to be dropped, and the part dropped is **the oldest part**.  The oldest turns are removed outright.  They are not faded, compressed or deprioritized.

Dropping the oldest turns gives the assistant's forgetting a particular shape.  A human memory loses the middle, the boring parts, the things that did not matter.  A long conversation loses its beginning, precisely and completely, including the part where you explained what you were trying to do.  If an assistant has worked well for an hour and suddenly seems to have lost track of the task, the oldest turns have usually been dropped.  Start a new conversation and say the important part again.

## The part that surprises people about attached documents

An agent's knowledge files are not stored inside the model either.

The agent decides to search its documents and writes the search itself.  The search is a request of its own, and the passages that look relevant are **pasted into the conversation** as extra context that you do not see.  A well-targeted question retrieves a paragraph.  A vague question retrieves a lot more, because more passages looked equally relevant.

As a result, precise questions to the guides are cheap and vague questions are expensive.  The difference comes from the retrieved passages and has nothing to do with the length of what you typed.

## What is still confusing about this

We are not yet sure whether you can watch your context use while you work.  The version of the chat we run includes a context gauge in the composer (the box you type into), switched on by default, and we do not switch it off.  The gauge is probably there, above the box you type into.  We worked that out from a configuration file, and you are the one looking at the screen.  If you can see the gauge, it shows how close the conversation is to the limit.  If you cannot see it, tell us.

Nothing warns you when a conversation hits the limit.  The chat does not announce that it just dropped your opening message.  The model stops seeing that message and goes on confidently.

An agent's own instructions are kept when the oldest turns are dropped.  The chat and the servers we know of keep the instructions and drop your early messages instead.  One exception: on some servers, a single message so large that the instructions plus that message overflow the window can push the instructions out too.  What you lose is what you said at the start: the constraints you set, the document you pasted, the correction you made on turn three.  You get no error.  You get answers that ignore what you established, or repeat a mistake you already fixed.

**The sign of a dropped beginning is a model that works fine in a new conversation and strangely in a long one.**  If you see that, the model is fine and the conversation has outgrown its window.  Start a new conversation, and mention it to us.  The course's limit is a setting on our side, and you will notice the problem long before we do.

## Try it yourself

Ask the **Usage Guide** in the {{PLATFORM}} chat for **your usage** and compare the two token figures, the "in" number against the "out" number.

On almost any real account, "in" is ten to fifty times larger than "out."  The size of that ratio comes from your conversations being re-sent on every turn.
