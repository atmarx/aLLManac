---
title: Building with code
description: Chat needs only a sign-in.  Code needs a key, the gateway's address, and a clear idea of what limits it and what doesn't.  These pages cover all three, for scripts, notebooks, and coding harnesses alike.
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

The chat window is one way to use the models.  A Python script, a notebook, or a coding agent running in your terminal sends its requests to the same place the chat does: the **gateway**, the one address in front of every model on the platform.  The chat window identifies you to the gateway automatically.  Code has to identify itself with a key.

What changes when you use code instead of the chat window:

- **You need a key, and it belongs to you.**  Each person gets one key per course.  Everything the key spends is recorded under your name, in that course.  → [Your API key](your-key.md)
- **The limits are different.**  In chat, a long conversation gets trimmed at the course's context window.  Through a key, the gateway does not trim your requests.  The budget on the key is what stops you.  If you assume the chat rule applies to code, you'll expect a limit that does not exist.  → [The gateway](the-gateway.md)
- **A coding agent needs version control, tests and a deployment pipeline before it needs anything else.**  Those three matter more than which model or harness you pick.  Without them, every mistake costs you twice: once in tokens spent checking by hand, and again in time spent finding what the code used to say.  → [Before the agent](before-the-agent.md)
- **A harness spends differently from a person.**  A coding agent re-sends its whole working context on every step of its loop, dozens of times per task, without you watching each one.  → [Coding harnesses](harnesses.md)

Research on coding harnesses shows that choosing a harness on its own is the wrong question.  The same model gains or loses tens of points depending on the harness around it, and which harness wins depends on the model.  → [Choosing a harness](choosing-a-harness.md)

Errors from the gateway are rarely self-explanatory, and several of them look like a broken key when the key is fine.  → [When it breaks](when-it-breaks.md)

Running a coding agent means handing it your repository and a key with your name on it.  You are responsible for what it does, so you need to supervise it and check its work.  → [Supervising an agent](supervising-an-agent.md)

## What this section assumes

The coding pages assume you can open a terminal, set an environment variable, and run a script.  If you're going to hand code to an agent, set up git first; [Before the agent](before-the-agent.md) has the minimum.  If you have never used an API before, start with [the gateway](the-gateway.md).  Its first example is three lines long and checks that your key, the address and the gateway all work together.
