---
title: What we store
description: The actual inventory — conversations, agents, uploaded files, usage records, and identity — listed by the system that holds each one.
audience: student
also_reaches: [faculty, builder]
status: draft
owner: piper
tags: [data-inventory, education-record, pii, mongodb, litellm, keycloak, openbao, ferpa, attribution, metering]
regimes: [ferpa]
tethered_to:
  - docs/admin-guide.md#backups
  - compose.yml
  - registrar/reconcile.py
---

# What we store

Five systems hold something about you.  Here is each one, what it has, and whether it is tied to your name.

## The inventory

| What | Where it lives | Tied to you |
|---|---|---|
| Your conversations, and the agents you build | Your course's own database | Yes |
| Files you upload to an agent, and the search index built from them | The knowledge store | Through the agent you attached them to |
| Usage records — model, tokens, cost, timestamp | The ledger | **Yes, by email address** |
| Your account, roles, and course membership | The identity system | Yes |
| API keys issued to you | The key escrow, versioned | Yes |
| Chat search index | Per-course search service | Rebuilt from your conversations; holds nothing original |

Two of those deserve more than a table row.

## Your conversations

Everything you type into the chat, and everything the model types back, is stored in **your course's own database** — not a shared one with a column marking which course a row belongs to.  Each course runs its own.

The agents you build live there too, along with any files you attached to them.  When you upload a document to an agent so it can answer questions about it, the text of that document is broken up, indexed, and kept so the agent can search it later.  It stays until the agent is deleted.

## The ledger, which is the one that surprises people

Every request you make writes a usage record: which model you used, how many tokens it took, what it cost, and when.  Those records are keyed to **your email address**.

Worth being direct about what that adds up to.  The ledger does not contain what you *said* — no prompts, no responses, no content.  It does contain a detailed picture of your behavior: which models you prefer, how much you lean on them, at what hours, across the whole term.  For a lot of people that is a more personal record than they expect a billing system to be.

The email is deliberate rather than incidental.  Attribution has to land on a real person and survive a roster change, and an opaque internal ID does neither.  The reasoning and what it cost are in [Why the chatbot never asks who you are](../how-we-built-it/identity-is-not-an-argument.md).

You can see your own usage from inside the chat — ask the usage agent, and it will only ever answer for you.

## What we do not store

- **Conversation content is not in the ledger.**  The two are separate systems and only one of them holds what you wrote.
- **Nothing you write becomes training data.**  The models here run on institutional hardware and are not fine-tuned on course traffic.
- **No keystroke, screen, or attention telemetry.**  There is no record of how long you paused before sending, what else was on your screen, or whether you were reading.
- **No content leaves for an outside company** unless your course uses a hosted model or an agent with actions turned on — both of which are course decisions your instructor can tell you about.  See [Who can see it](who-can-see-it.md#the-path-that-leaves-the-building).

## For anyone building something like this

This page is a **data inventory**, and it is the first artifact of every data protection regime — you cannot classify what you have not enumerated, and you cannot answer "what happens to my data" without a list like this one.

The useful accident worth stealing: this inventory did not start as a privacy document.  It started as a list of what needs backing up.  Working out what you would lose in a disaster turns out to produce the same list as working out what you are holding about people, and most teams write the first one long before anybody asks for the second.

More on that in [How do you protect data you can't delete?](../how-we-built-it/protecting-data-you-cant-delete.md)
