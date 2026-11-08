---
title: What we store
description: The inventory of conversations, agents, uploaded files, usage records, and identity data, listed by the system that stores each one.
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

Several {{PLATFORM}} systems store data about you.  The inventory table lists each one, what it stores, and whether it is tied to your name.

## The inventory

| What | Where it is stored | Tied to you |
|---|---|---|
| Your conversations, and the agents you build | Your course's own database | Yes |
| Your conversations with the guides in the {{PLATFORM}} chat | The {{PLATFORM}} chat's own database, shared by everyone who uses it | Yes |
| Files you upload, in a chat or to an agent | Your course's file storage | Yes |
| The search index built from those files | Your course's own knowledge store | Yes, through the file |
| Problem reports you file, including the question and answer they quote | The course service's records | Yes |
| Your email on a course roster | The course service's records | Yes |
| Usage records (model, tokens, cost, timestamp) | The ledger | **Yes, by email address** |
| Your account, roles, and course membership | The identity system | Yes |
| API keys issued to you | The key escrow, versioned | Yes |
| Chat search index | Per-course search service | Rebuilt from your conversations; contains nothing original |
| Backup copies of all of the above | Off-machine storage, about six months | Yes |

Conversations and the usage ledger need more explanation than a table row.  They are covered under [Your conversations](#your-conversations) and [The ledger](#the-ledger-which-is-the-one-that-surprises-people).

## Your conversations

Everything you type into a course's chat, and everything the model types back, is stored in **your course's own database**.  Each course runs its own; there is no shared database with a column marking which course a row belongs to.  The exception is the {{PLATFORM}} chat: conversations with the Front Desk and the guides there are stored in one database shared by everyone who uses it.

The agents you build are stored in your course's database too.  When you upload a document to an agent or into a chat, the platform keeps the original file in the course's file storage and a record of it, tied to you, in the database.  For documents an agent searches, the platform also breaks the text up and indexes it so it can be searched later.  **Deleting an agent does not delete its files.**  An agent's files stay until each file itself is deleted.

## The ledger, which is the one that surprises people

Every request you make writes a usage record to the ledger: which model you used, how many tokens it took, what it cost, and when.  Those records are keyed to **your email address**.

The ledger does not contain what you *said*: no prompts, no responses, no content.  The ledger does contain a detailed picture of your behavior: which models you prefer, how much you use them, at what hours, across the whole term.  For a lot of people that is a more personal record than they expect a billing system to keep.

Keying the ledger to your email address was a design choice.  Attribution has to point at a real person and survive a roster change, and an opaque internal ID does neither.  The reasoning, and what it cost, are in [Why the chatbot never asks who you are](../how-we-built-it/identity-is-not-an-argument.md).

To see your own usage, ask the **Usage Guide** in the {{PLATFORM}} chat.  The Usage Guide only ever answers for you.  Your instructor, your TAs, and the platform's admins see a narrower slice of the same ledger for the course: each person's requests, tokens and last activity listed by email, who hasn't started yet, the model mix, and the course's total spend.  They see counts, never content.

## What we do not store

- **Conversation content is not in the ledger.**  The ledger and the conversation database are separate systems, and only the conversation database stores what you wrote.
- **This platform does not use your conversations to fine-tune its models.**  If a deployment uses a hosted model, that provider's retention and training terms are a separate promise the operator should publish.
- **No keystroke, screen, or attention telemetry.**  There is no record of how long you paused before sending, what else was on your screen, or whether you were reading.
- **Content can leave the institution through a hosted model or an agent action.**  Both routes are configuration choices your instructor or operator should be able to name.  See [Who can see it](who-can-see-it.md#paths-that-can-leave-the-building).

## For anyone building something like this

A table like [the inventory](#the-inventory) is a **data inventory**, the first artifact of every data protection regime.  You cannot classify what you have not enumerated, and you cannot answer "what happens to my data" without a list like it.

The {{PLATFORM}} inventory did not start as a privacy document.  It started as a list of what needs backing up.  Working out what you would lose in a disaster produces the same list as working out what you are storing about people, and most teams write the first list long before anybody asks for the second.

How backups and privacy connect is covered in [How do you protect data you can't delete?](../how-we-built-it/protecting-data-you-cant-delete.md)
