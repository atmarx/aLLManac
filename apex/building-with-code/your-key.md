---
title: How do I get an API key, and what is it?
description: One key per person per course, fetched from the Coder Guide in the {{PLATFORM}} chat, with its own budget and your name on it.  How to get it, how to replace it, and what it will and won't let you do.
audience: student
also_reaches: [faculty]
status: draft
owner: piper
tags: [api-key, key-rotation, secrets-management, attribution, metering, student-right]
tethered_to:
  - registrar/server.py
  - registrar/planes/verbs.py
  - registrar/planes/gateway.py
  - registrar/planes/config.py
  - registrar/render.py
---

# Your API key

## Getting it

Open the **{{PLATFORM}} chat** — where the guides are, not your course's address — pick the **Coder Guide**, and ask for your key.  If you are in more than one course, it asks which one.

Keys are kept out of your course's chat.  Asking for one is bookkeeping, and bookkeeping tools in the course chat would spend your course's budget and fill the course model's context with tools your coursework never uses.

The guide calls a tool named `my_key` and hands the key back to you in the conversation, along with the **gateway address** your code points at.  Nobody emails it to you and nobody else can fetch it for you.  The tool answers the person who is signed in and nobody else.

If it says you are not on the roster yet, your instructor hasn't added you — the key is minted when you are enrolled, so there is nothing to fetch until then.  Teaching staff get theirs minted the first time they ask.

Copy it somewhere safe, then treat that conversation like it holds a password, because it does.

## What it is

- **Per person, per course.**  In two courses, you have two keys, and each spends against its own course.  Use the right one — the spend goes where the key belongs, not where you meant it to.
- **It has your name on it.**  Every request made with it is recorded against you.  There is no anonymous mode, and a key you share is a key whose spending is still yours.
- **It has a budget of its own**, called the fuse — a few dollars unless your course sets a different number.  It exists to stop a runaway loop: one script stuck retrying all weekend hits its own ceiling long before it can drain anyone else's.
- **It can call the models your course had when it was minted.**  A model added to the course later does not appear on a key that already exists.  Rotating the key (below) picks up the current list.

**Whether the fuse ever trips depends on how your deployment prices its models.**  The fuse counts dollars, and dollars only exist for a model that has a price in the gateway's config.  A model running on your institution's own hardware may be recorded at zero, in which case your key's spend reads $0 and the fuse never moves — the tokens are still counted, under your name, but they cost nothing on that meter.  A hosted model with a real price is where the fuse means something.

## Replacing it

Leaked it, committed it, lost the laptop?  Ask the **Coder Guide** in the {{PLATFORM}} chat to **rotate** your key.  The tool `rotate_my_key` mints a new key, hands it to you, and kills the old one at the gateway.  It takes seconds and needs nobody's permission.

**Rotation is not a refill.**  The new key gets your course's per-key budget minus what you have already spent, and never more than the course has left — so in practice, roughly what the old key had.  If less than about a dollar would carry over, rotation refuses; it won't hand you a key that is dead on arrival.  Its refusal says how much your key had left and how much the course pool has, so you can tell which one ran out.  It will also refuse if it can't read the old key's meter at that moment, because guessing would mean guessing "full."  In both cases your current key is left exactly as it was.

## Keeping it

- Put it in an **environment variable**, not in your code.  `export CAMPUS_API_KEY=...` in your shell profile, and read it from there.
- Never commit it.  If your project has a `.env` file, that file belongs in `.gitignore` before the key goes into it — not after.
- Don't paste it into a shared document, a group chat, or a screenshot.  If you did, rotate.  Rotating costs you nothing; not rotating costs whatever the finder spends, under your name.
