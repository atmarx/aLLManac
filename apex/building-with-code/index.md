---
title: Building with code
description: Chat needs nothing but a sign-in.  Code needs a key, an address, and a clear idea of what is and isn't limiting it — this section is that idea, for scripts, notebooks, and coding harnesses alike.
audience: student
also_reaches: [faculty, builder]
status: draft
owner: piper
tags: [api-key, openai-compatible, harness, agentic-coding, tool-calling, gateway, attribution, metering]
tethered_to:
  - registrar/server.py
  - registrar/planes/gateway.py
  - registrar/planes/verbs.py
  - docs/design-walls.md
---

# Building with code

The chat window is one way in.  Everything else — a Python script, a notebook, a coding agent running in your terminal — comes in through the same door the chat does: the **gateway**, one address that every model on the platform sits behind.  The chat window simply knocks for you.  Code has to knock for itself, and that is what the key is for.

Three things change the moment you leave the chat window, and they are worth knowing before you write a line:

- **You need a key, and it is yours.**  One per person per course.  Everything it spends is recorded under your name, in that course.  → [Your API key](your-key.md)
- **The limits are different.**  In chat, a long conversation gets trimmed at the course's context window.  Through a key, nothing trims your requests at the gateway — what stops you is the budget on the key.  Anyone who learns the chat rule and assumes it applies to code will predict a limit that does not exist.  → [The gateway](the-gateway.md)
- **A harness spends differently from a person.**  A coding agent re-sends its whole working context on every step of its loop, dozens of times per task, without you watching each one.  → [Coding harnesses](harnesses.md)

When something goes wrong, the errors are rarely self-explanatory, and several of them look like a broken key when they aren't.  → [When it breaks](when-it-breaks.md)

And the part no config file covers — what it means to hand an agent your repository and your name, and how to supervise it rather than trust it.  → [Supervising an agent](supervising-an-agent.md)

## What this section assumes

That you can open a terminal, set an environment variable, and run a script.  Nothing beyond that.  If you have never used an API before, start with [the gateway](the-gateway.md) — the first example there is four lines long and proves the whole chain works.
