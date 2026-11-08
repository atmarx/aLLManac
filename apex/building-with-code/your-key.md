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

Open the **{{PLATFORM}} chat**, where the guides are.  This is a different address from your course's chat.  Pick the **Coder Guide** and ask for your key.  If you are in more than one course, the guide asks which one.

The key tools are not available in your course's chat.  Bookkeeping tools there would spend your course's budget and fill the course model's context with tools your coursework never uses.

The guide calls a tool named `my_key` and returns the key in the conversation, along with the **gateway address** your code points at.  Nobody emails the key to you.  `my_key` answers only the person who is signed in, so nobody else can fetch your key.

If the Coder Guide says you are not on the roster yet, your instructor hasn't added you.  Your key is minted when you are enrolled, so there is nothing to fetch until then.  Teaching staff get theirs minted the first time they ask.

Copy the key somewhere safe.  The key works like a password, and the conversation now contains it, so treat that conversation like a password too.

## What it is

- **One key per person, per course.**  If you are in two courses, you have two keys, and each spends against its own course.  Use the right key.  The spending is charged to the key's course, whichever course you meant it for.
- **The key has your name on it.**  Every request made with it is recorded against you.  There is no anonymous mode.  If you share your key, its spending is still recorded as yours.
- **The key has a budget of its own**, called the fuse.  The fuse is $20 unless your deployment or your course sets a different number.  The fuse stops a runaway loop: one script stuck retrying all weekend hits its own key's ceiling long before it can use up anyone else's budget.
- **The key can call the models your course had when the key was minted.**  A model added to the course later does not appear on a key that already exists.  Rotating the key ([Replacing it](#replacing-it)) picks up the current list.

**Whether the fuse ever trips depends on how your deployment prices its models.**  The fuse counts dollars, and dollars only exist for a model that has a price in the gateway's config.  A model running on your institution's own hardware may be recorded at zero.  On that model your key's spend reads $0 and the fuse never moves.  The tokens are still counted under your name, but they cost nothing on the fuse's meter.  The fuse only limits spending on a hosted model with a real price.

## When it runs out

**A spent fuse stays spent.  The fuse does not reset on a schedule**: not overnight, not weekly, and not at the start of a month.  Waiting will not bring the key back, and neither will rotating it ([Replacing it](#replacing-it)).  To get the key working again, your instructor asks the course's admin to raise the fuse.  Once that change is applied, the key you already have works again with the difference added, and you don't need to paste in a new key.

If your harness starts answering with a budget error, ask the **Coder Guide** about your key.  `my_key` says what the key has spent and what's left, so you can give your instructor the numbers.  If the guide ever names a time when your key will come back by itself, the guide is wrong.  The fuse never resets on its own.

If the whole course stopped at once, chat included, the course's budget pool has run out, and your fuse is not the cause.  Raising the course pool is also your instructor's decision; [teaching a course](../teaching-a-course.md) covers it.

## Replacing it

If your key leaked, was committed to a repository, or was on a laptop you lost, ask the **Coder Guide** in the {{PLATFORM}} chat to **rotate** your key.  The tool `rotate_my_key` mints a new key, returns it to you, and disables the old one at the gateway.  Rotation takes seconds and needs nobody's permission.

**Rotation does not refill your budget.**  The new key gets your course's per-key budget minus what you have already spent, and never more than the course has left.  In practice, that is roughly what the old key had.  If less than about a dollar would carry over, rotation refuses, so you never get a new key that can't make a request.  The refusal says how much your key had left and how much the course pool has, so you can tell which one ran out.  Rotation also refuses if it can't read the old key's meter at that moment.  Without that reading it would have to guess, and the guess would be a full budget.  In both cases your current key is left exactly as it was.

## Keeping it

To keep your API key safe:

- Put the key in an **environment variable** and keep it out of your code.  Add `export CAMPUS_API_KEY=...` to your shell profile, and have your code read it from there.
- Never commit the key.  If your project has a `.env` file, add that file to `.gitignore` before you put the key in it.
- Don't paste the key into a shared document, a group chat, or a screenshot.  If you did, rotate it.  Rotating costs you nothing.  Not rotating means anyone who found the key can spend with it, under your name.
