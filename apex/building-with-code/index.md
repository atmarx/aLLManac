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

The chat window is one way in.  Everything else — a Python script, a notebook, a coding agent running in your terminal — goes through the same place the chat does: the **gateway**, the one address in front of every model on the platform.  The chat window identifies you to it automatically.  Code has to identify itself with a key.

What changes the moment you leave the chat window:

- **You need a key, and it is yours.**  One per person per course.  Everything it spends is recorded under your name, in that course.  → [Your API key](your-key.md)
- **The limits are different.**  In chat, a long conversation gets trimmed at the course's context window.  Through a key, nothing trims your requests at the gateway — what stops you is the budget on the key.  Assume the chat rule applies to code and you'll predict a limit that does not exist.  → [The gateway](the-gateway.md)
- **An agent needs version control, tests and a pipeline under it before it needs anything else.**  They matter more than which model or harness you pick, and without them every mistake costs you twice.  → [Before the agent](before-the-agent.md)
- **A harness spends differently from a person.**  A coding agent re-sends its whole working context on every step of its loop, dozens of times per task, without you watching each one.  → [Coding harnesses](harnesses.md)

Which harness?  The research says that's the wrong question on its own: the same model gains or loses tens of points depending on the harness around it, and which harness wins depends on the model.  → [Choosing a harness](choosing-a-harness.md)

When something goes wrong, the errors are rarely self-explanatory, and several of them look like a broken key when they aren't.  → [When it breaks](when-it-breaks.md)

No config file covers what it means to hand an agent your repository and your name, or how to supervise it.  → [Supervising an agent](supervising-an-agent.md)

## What this section assumes

That you can open a terminal, set an environment variable, and run a script.  If you're going to hand code to an agent, you'll also want git first, and [Before the agent](before-the-agent.md) has the minimum.  If you have never used an API before, start with [the gateway](the-gateway.md) — the first example there is four lines long and proves the whole chain works.
