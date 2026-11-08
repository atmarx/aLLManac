---
title: What is a coding harness, and how do I run one here?
description: A harness is the program that turns a model into an agent.  It runs the loop, executes the tools, and re-sends everything on every step.  What that loop costs, how to point pi, opencode or Codex at the gateway, and what a campus model will and won't do inside a harness.
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

A model on its own can only produce text.  It cannot open a file, run your tests, or see what happened when it did.  A **harness** is the program that lets it do those things.  It gives the model a list of tools ("read a file," "run a command," "edit these lines"), and when the model answers with *"call this tool with these arguments"* instead of prose, the harness runs the tool and sends the result back.

The harness repeats that exchange until the model says it is finished.  The repetition is what makes a model into an agent, and it is also the source of most of a harness's unexpected costs and behavior.

## The loop, and why it spends

One step of the loop looks like this:

1. The harness sends the model **everything so far**: its own instructions, the tool descriptions, your request, and every tool call and result from every previous step.
2. The model replies with a tool call.
3. The harness runs it and appends the result.
4. The harness goes back to step 1.

Step 1 is the rule from [Understanding your usage](../understanding-your-usage/context-is-the-conversation.md) that the conversation is the context, applied automatically with nobody pressing enter.  A task that takes thirty steps sends the growing transcript thirty times.  A single file read that dumps two thousand lines into the context is re-sent on every step after it.

What the loop means for your usage:

- **A harness's instructions and tool list cost you on every step before you have said anything.**  For pi, the first step of a small task measured about 1,600 tokens here, the task included.  For opencode the instructions and tools are roughly eight thousand tokens, and opencode needs a model served with **at least 16k of context**.  With anything smaller, opencode's own instructions fill the whole window.
- **A harness uses far more "in" tokens than "out" tokens.**  Your usage will show a harness reading much more than it writes.  The loop causes that, and it is expected.

## pi

[pi](https://pi.dev) is an open-source (MIT) harness that runs in your terminal, and the suggested harness to start with on this platform.  pi is designed to be small: four tools by default (read, write, edit, run a command), and instructions short enough that you can read everything it sends the model.  The small size leaves a campus model most of its context window for your work, and lets you see every step of the loop.  pi has been run against this platform's gateway on two campus-size models, fixing a failing test end to end.  The research doesn't name a best harness.  [Which one suits you](choosing-a-harness.md) depends on the model and the goal, so treat pi as a place to start.

**Install** one of these ways (the npm route needs Node 22.19 or later):

```bash
curl -fsSL https://pi.dev/install.sh | sh                          # the easy way
npm install -g --ignore-scripts @earendil-works/pi-coding-agent    # if you live in npm
```

The older `@mariozechner/pi-coding-agent` package is deprecated.  If a tutorial names it, install `@earendil-works/pi-coding-agent` instead.

**Configure** in `~/.pi/agent/models.json`:

```json
{
  "providers": {
    "campus": {
      "baseUrl": "https://GATEWAY-ADDRESS/v1",
      "api": "openai-completions",
      "apiKey": "$CAMPUS_API_KEY",
      "models": [
        { "id": "{{MODEL}}", "contextWindow": 16384, "maxTokens": 4096 }
      ]
    }
  }
}
```

What to know about pi and its `models.json` config:

- **pi never asks before it acts.**  pi has no permission system: it runs whatever command the model asks for, under your account.  pi's own documentation recommends a container or a virtual machine for unattended work.  Before you trust pi with a task, start it read-only.  `pi --tools read,grep,find,ls` lets the model read and search, with no tool that writes or runs commands.  Either way, read [supervising an agent](supervising-an-agent.md).
- **`contextWindow`** is what pi believes the model can hold.  Set it to the context length the model is **served** with (ask your instructor), never to what the model's documentation says it supports.  If it is set too high, some servers silently drop the oldest messages; [opencode's `limit.context`](#opencode) has the details.
- **`$CAMPUS_API_KEY`** keeps the key out of the file.  pi reads it from your environment when it makes a request.

**Prove it works:**

```bash
export CAMPUS_API_KEY=sk-...
pi --print --model campus/{{MODEL}} "Say hello and name your model."
```

Then `cd` into a project and run `pi` for the full interface.  `pi --version` prints the version.  Write it down: [a pairing has a version on both sides](choosing-a-harness.md).

## opencode

[opencode](https://opencode.ai) is a fuller open-source harness, with more tools, more built in, and several thousand tokens of its own on every step.  opencode is also the harness inside the platform's own workbench, the container its operators use to try the gateway from code, so it is the most-run harness on this platform.  Any harness that speaks the OpenAI API is set up the same way, with the gateway address and your key.

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
    "campus": {
      "npm": "@ai-sdk/openai-compatible",
      "name": "{{PLATFORM}} (campus gateway)",
      "options": {
        "baseURL": "https://GATEWAY-ADDRESS/v1",
        "apiKey": "{env:CAMPUS_API_KEY}"
      },
      "models": {
        "{{MODEL}}": {
          "name": "{{PLATFORM}} chat",
          "tool_call": true,
          "limit": { "context": 16384, "output": 4096 }
        }
      }
    }
  },
  "model": "campus/{{MODEL}}"
}
```

What to know about the opencode config:

- **`tool_call: true`** on each model.  opencode assumes it when the line is missing; it's here so the setting is visible.  Set it to `false` and opencode offers the model no tools, so it works only as a chat in your terminal.
- **Permissions default to allowed.**  opencode runs shell commands and edits files without asking.  Add `"permission": { "bash": "ask" }` at the top level if you want it to ask first, and read [supervising an agent](supervising-an-agent.md) either way.
- **`limit.context`** is what opencode believes it can send.  Set it to the context length the model is **served** with (ask your instructor), never to what the model's documentation says it supports.  If it is too high, some servers silently drop the oldest messages, which are the earlier steps of the task, and a single oversized message can push out opencode's instructions too.  If it is too low, opencode trims your work early.  16384 is the minimum opencode needs, not a recommended value.
- **`{env:CAMPUS_API_KEY}`** keeps the key out of the file, so the file can be committed and the key can't.

**Prove it works:**

```bash
export CAMPUS_API_KEY=sk-...
opencode run -m campus/{{MODEL}} "Say hello and name your model."
```

Then `cd` into a project and run `opencode` for the full interface.

## Codex CLI

Codex CLI takes the same two settings, the gateway address and your key, in its own config format.  The pi, opencode and Codex configs were checked against the releases listed in [the versions table](choosing-a-harness.md#versions-this-page-was-checked-against), and a new release can rename config formats.  Which harness suits you depends on [the pairing](choosing-a-harness.md) of harness and model.

Install with `npm install -g @openai/codex`; configure in `~/.codex/config.toml`:

```toml
model = "{{MODEL}}"
model_provider = "campus"

[model_providers.campus]
name = "{{PLATFORM}} (campus gateway)"
base_url = "https://GATEWAY-ADDRESS/v1"
env_key = "CAMPUS_API_KEY"
wire_api = "responses"
```

Codex speaks only the Responses API.  `wire_api = "chat"` has been an error since February 2026.  The gateway translates between the two APIs, but **Codex against campus models is untested here**.  Nobody has checked whether tool calls survive that translation.  The provider can't be named `openai`, `ollama`, or `lmstudio`; those names are reserved.  Set `model_context_window` to the context length the model is served with.  A higher number risks the same silent loss of old messages described for opencode's `limit.context`.

## What to expect from a campus model

A model small enough to run on institutional hardware will run the loop and teach you the workflow.  A campus model is not a frontier model, and inside a harness the difference shows: a tool called by the wrong name, a file edited in the wrong place, a confident "done" on unfinished work.

**Tool calling is the part most likely to fail.**  Whether a model can call tools at all depends on the model *and* on how its server is configured.  The server has to be told how that model family writes a tool call, and there is no universal setting.  When the server hasn't been told, the model writes something that looks like a tool call into ordinary text, the harness doesn't recognize it, and the loop stalls.  A stall like that is a server configuration problem, and not yours to fix; [report it](when-it-breaks.md).

A campus model's mistakes are useful practice.  You are learning to supervise an agent, and a model that makes visible mistakes teaches supervision better than one whose mistakes are rare enough that you stop checking.  → [Supervising an agent](supervising-an-agent.md)
