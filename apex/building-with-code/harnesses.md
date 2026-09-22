---
title: What is a coding harness, and how do I run one here?
description: A harness is the program that turns a model into an agent — it runs the loop, executes the tools, and re-sends everything every step.  What that loop costs, how to point opencode at the gateway, and what a campus model will and won't do inside it.
audience: student
also_reaches: [faculty, builder]
status: draft
owner: piper
tags: [harness, agentic-coding, tool-calling, openai-compatible, api-key, context-window, token-economy]
tethered_to:
  - docs/design-walls.md
  - litellm/config.yaml
  - registrar/render.py
---

# Coding harnesses

A model on its own can only produce text.  It cannot open a file, run your tests, or see what happened when it did.  A **harness** is the program that gives it hands: it hands the model a list of tools ("read a file," "run a command," "edit these lines"), and when the model answers with *"call this tool with these arguments"* instead of prose, the harness does it and sends the result back.

That exchange repeats until the model says it is finished.  The repetition is the whole idea, and it is also where every surprise comes from.

## The loop, and why it spends

One step of the loop looks like this:

1. The harness sends the model **everything so far** — its own instructions, the tool descriptions, your request, and every tool call and result from every previous step.
2. The model replies with a tool call.
3. The harness runs it and appends the result.
4. Back to 1.

Step 1 is the conversation-is-the-context rule from [Understanding your usage](../understanding-your-usage/context-is-the-conversation.md), running on its own with nobody pressing enter.  A task that takes thirty steps sends the growing transcript thirty times.  A single file read that dumps two thousand lines into the context rides along on every step after it.

Two things follow:

- **A harness's instructions and tool list cost you on every step before you have said anything.**  For opencode that is roughly eight thousand tokens of its own, which is why it needs a model served with **at least 16k of context** — anything smaller and it spends its whole window on itself.
- **"In" tokens dwarf "out" tokens.**  Your usage will show a harness reading enormously more than it writes.  That is the loop, not a bug.

## opencode

[opencode](https://opencode.ai) is an open-source harness that runs in your terminal, and the one this page walks through in full.  It is not a recommendation — [which harness to use](choosing-a-harness.md) depends on the model and the goal.  Any harness that speaks the OpenAI API works the same way: the address and the key.

**Install** one of these ways:

```bash
curl -fsSL https://opencode.ai/install | bash    # the easy way
npm install -g opencode-ai                       # if you live in npm
brew install anomalyco/tap/opencode              # macOS
```

**Configure.**  `~/.config/opencode/opencode.json` applies everywhere; an `opencode.json` in a project folder applies to that project only:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "provider": {
    "almanac": {
      "npm": "@ai-sdk/openai-compatible",
      "name": "Almanac (campus gateway)",
      "options": {
        "baseURL": "https://GATEWAY-ADDRESS/v1",
        "apiKey": "{env:ALMANAC_API_KEY}"
      },
      "models": {
        "almanac-chat": {
          "name": "Almanac Chat",
          "tool_call": true,
          "limit": { "context": 16384, "output": 4096 }
        }
      }
    }
  },
  "model": "almanac/almanac-chat"
}
```

Four things about that config are load-bearing:

- **`tool_call: true`** on each model.  Without it opencode never offers the model any tools, and you have a chat window in a terminal.
- **Permissions default to allowed** — opencode runs shell commands and edits files without asking.  Add `"permission": { "bash": "ask" }` at the top level if you want it to ask first, and read [supervising an agent](supervising-an-agent.md) either way.
- **`limit.context`** is what opencode believes it can send.  Set it to what the model is **served** with — ask your instructor — and never to what the model's documentation says it supports.  Too high and some servers silently drop the front of the prompt, which is where opencode's instructions live.  Too low and it trims your work early.  16384 is the floor, not a recommendation.
- **`{env:ALMANAC_API_KEY}`** keeps the key out of the file, so the file can be committed and the key can't.

**Prove it works:**

```bash
export ALMANAC_API_KEY=sk-...
opencode run -m almanac/almanac-chat "Say hello and name your model."
```

Then `cd` into a project and run `opencode` for the full interface.

## Codex and pi

The same two settings — address and key — in each one's own format.  Every config on this page was checked against the releases listed in [the versions table](choosing-a-harness.md#versions-this-page-was-checked-against); config formats are exactly the kind of thing a new release renames.  Which one suits you is [a question about the pairing](choosing-a-harness.md), not about the harness alone.

**Codex CLI** (`npm install -g @openai/codex`), in `~/.codex/config.toml`:

```toml
model = "almanac-chat"
model_provider = "almanac"

[model_providers.almanac]
name = "Almanac (campus gateway)"
base_url = "https://GATEWAY-ADDRESS/v1"
env_key = "ALMANAC_API_KEY"
wire_api = "responses"
```

Codex speaks **only** the Responses API — `wire_api = "chat"` has been an error since February 2026.  The gateway translates, but **Codex against campus models is untested here**: whether tool calls survive that translation is the open question.  The provider can't be named `openai`, `ollama`, or `lmstudio`; those are reserved.  Set `model_context_window` to the number the model is served with, for the same reason as opencode's `limit.context`.

**pi** (`npm install -g --ignore-scripts @earendil-works/pi-coding-agent`, Node 22.19 or later — the older `@mariozechner/pi-coding-agent` package is deprecated), in `~/.pi/agent/models.json`:

```json
{
  "providers": {
    "almanac": {
      "baseUrl": "https://GATEWAY-ADDRESS/v1",
      "api": "openai-completions",
      "apiKey": "$ALMANAC_API_KEY",
      "models": [ { "id": "almanac-chat" } ]
    }
  }
}
```

pi has no permission system: it runs whatever the model asks.  Its own docs recommend a container or a VM, and they mean it.

## What to expect from a campus model

A model small enough to run on institutional hardware will run the loop and teach you the workflow.  It is not a frontier model, and inside a harness the gap shows: a tool called by the wrong name, a file edited in the wrong place, a confident "done" on work that isn't.

**Tool calling is the fragile part.**  Whether a model can call tools at all depends on the model *and* on how its server is configured — the server has to be told how that model family writes a tool call, and there is no universal setting.  When it isn't, the model writes something that looks like a tool call into ordinary text, the harness doesn't recognise it, and the loop stalls.  That is a server configuration problem, not yours to fix; [report it](when-it-breaks.md).

The rest of it — the stumbles — is the lesson.  You are learning to supervise an agent, and a model that makes visible mistakes is a better teacher of supervision than one whose mistakes are rare enough to stop checking for.  → [Supervising an agent](supervising-an-agent.md)
