---
title: How do I build with my course's AI?
description: The walkthrough for the people in a course — building your own agent, maintaining one as a team of co-editors, and pointing your own code at the campus gateway with an API key.
audience: student
also_reaches: [faculty]
status: draft
owner: piper
tags: [sso, access-control, rbac, secrets-management, key-rotation, attribution, metering, assessment-design, ai-literacy, accountability, faculty-duty, student-right, librechat, litellm]
tethered_to:
  - docs/design-walls.md
  - registrar/render.py
  - registrar/planes/gateway.py
  - usage-mcp/server.py
  - justfile
  - docs/admin-guide.md
---

# The aLLManac — Course Guide

*For the people teaching with it, and the students building on it.*

Your class has its own AI service.  Not a rented seat on somebody's cloud — a service your campus runs, on campus models, where the whole team can build **one shared assistant together** and every token is on a ledger your course can see.  This guide covers the three things you'll actually do:

1. **Build a custom GPT** (everyone)
2. **Build one as a group** — and share it with the class (the whole point)
3. **Use the models from code** with your API key (opencode)

Faculty: [Teaching a course](teaching-a-course.md) is your playbook, and whoever operates your deployment holds the admin guide that covers the machinery behind it.

---

## Part 1 — Your first custom GPT

A "custom GPT" here is a LibreChat **Agent**: a system prompt + knowledge files + tools, wrapped in a name.  Anyone can make one.

**Sign in** at the chat URL your instructor gave you — use the SSO button (your campus credentials).  There's no separate account to create; logging in *is* creating your account.

**Create the agent:**

1. In the model/endpoint menu at the top of a new chat, select **Agents**.
2. Open the **Side Panel** (right edge) → **Agent Builder**.
3. Fill in:
   - **Name** — what the class will see (`ENGR 301 Lab TA`)
   - **Description** — one line on what it's for
   - **Instructions** — the soul of the thing.  Give it a role, its boundaries, and its tone.  Concrete beats clever:

     > You are the lab assistant for ENGR 301 (Materials Characterization).  Help students reason through XRD and SEM sample-prep problems using the attached lab manual.  Ask what they've already tried before offering steps.  Never just give final answers to the numbered pre-lab questions — guide toward them.
   - **Model** — `almanac-chat` (the campus model; your instructor may add more)
4. **Save**.  It now appears in your agent dropdown, and you can summon it in any chat by typing `@` + its name.

**Attach knowledge.**  In the builder, upload files where they'll do the right job:

- **File Search** — the usual choice.  Files are indexed for retrieval, and the agent quotes and cites from them when relevant.  Course readings, lab manuals, syllabi.
- **File Context** — short reference text injected directly into the agent's instructions.  Rubrics, formula sheets, a style guide.  Keep it small; it rides along on every request.

Uploads are capped at course-materials scale (10 files per go, 25 MB each) — if you're bumping the caps, you're probably attaching the wrong thing.

**Things it draws, it draws in a panel.**  Ask an agent for a chart, a diagram, a table you can sort, a small web page, and it does not hand you a wall of code — a panel opens beside the chat with the finished thing in it, and you can flip between the result and the code that made it.  This is on for every agent here and you do not have to switch it on.  One thing worth knowing the first time it happens: the panel is a preview, not a saved file.  Anything you want to keep, copy out — a chart you liked is gone with the conversation it was drawn in.

**Iterate.**  Talk to it.  When it answers wrong, that's not failure — that's your next instruction line.  The gap between "an assistant" and "a good assistant" is fifteen rounds of this.

---

## Part 2 — Group projects: one GPT, whole team

Emailing prompt revisions around is how group projects die.  Here, the team shares **one agent**, and everyone with **Editor** access maintains it — same instructions, same files, one body.

### What your instructor sets up

Your team's group is made for you — you do not need the admin panel, and there is nothing to install.  One thing is on you, though: **log in at least once before your instructor adds you to a group.**  Accounts only exist after a first login, so if your name cannot be found in the people picker, that is almost always why.

### Sharing the agent to the team

Whoever creates the agent (faculty or a team member):

1. Open the agent in the **Agent Builder** → **Share**.
2. Search for the team's group name.
3. Grant a role:

   | Role | What it means |
   |---|---|
   | **Viewer** | Can chat with the agent.  Can't see or change how it works. |
   | **Editor** | Can change instructions, model, tools, **and knowledge files**.  This is the co-editing role — give it to the team. |
   | **Owner** | Editor + can delete and re-share.  Keep this to one or two people. |

That's the whole trick: **Editor to the team's group.**  Every member can now open the same agent in the builder and work on it.

### Working as co-editors

The agent has one body — edits overwrite, last save wins, and there's no merge button.  Treat the instructions like a shared document: talk before you rewrite, and keep a copy of the instructions in your team's repo or doc if you want history.  (Your team chat *conversations* stay your own; it's the agent itself that's shared.)

### Sharing with the class

- **The Agent Marketplace** (sidebar → Agent Marketplace) is where shared agents get discovered — browse by category, find what teams have published.
- To make a team's agent visible class-wide, share it **Viewer** to the course-wide group (faculty set one up, e.g. `engr301-all`) — or ask your instructor to share it there for you.
- **Nobody publishes an agent platform-wide from the chat window — not you, and not your instructor either.**  That switch is off for every account on the instance, so the class-wide group above is as wide as an agent goes without the people who run the servers getting involved.  If a course genuinely needs one agent visible to everyone, that is a conversation with them, not a button anybody is missing.

**A caution worth repeating from the platform docs:** anyone who can chat with an agent can eventually coax out what's in its files.  Attach materials you'd hand the class anyway — never answer keys, never solutions, never anything private.

---

## Part 3 — Your API key

Chat needs no key — sign in and go; the ledger already knows who you are.  The API key is for **code**: your own scripts, notebooks, and the coding harness in Part 4.

- Keys are minted by your instructor or the admin, and every key belongs to an **owner** — your course or lab.  That's who the usage rolls up to.
- Each key carries a **budget**.  Campus models mean nobody's charging your card — the budget is there so a runaway loop gets caught and so the course can see what things *would* cost on commercial AI.  Visibility, not a paywall.
- **Treat the key like a password.**  It arrives via your instructor (LMS message, not a group chat).  Don't commit it to a repo, don't paste it into a shared doc.  If it leaks or you lose it, say so — the old one is retired and a new one minted in about a minute, no ceremony.
- If you hit your budget, requests start failing with a budget-exceeded error.  That's a conversation, not a punishment — ask for a bump.
- **Where do I stand?**  Ask the chat.  The **Almanac Usage** agent answers "how much have I used this week?" with your real numbers — chat and API keys combined, tokens and requests (campus models don't bill dollars).  Only ever yours; nobody else's.

The key works with **any OpenAI-compatible tool** pointed at the campus gateway URL.  Which brings us to —

## Part 4 — The coding harness (opencode)

[opencode](https://opencode.ai) is an open-source coding agent that lives in your terminal: it reads your project, edits files, runs commands — the agentic-coding loop, on campus models, metered to your key.

**Install** (pick one):

```bash
curl -fsSL https://opencode.ai/install | bash    # the easy way
npm install -g opencode-ai                       # if you live in npm
brew install anomalyco/tap/opencode              # macOS
```

**Configure.**  Create `~/.config/opencode/opencode.json` (applies everywhere) or `opencode.json` in a project folder (that project only):

```json
{
  "$schema": "https://opencode.ai/config.json",
  "provider": {
    "almanac": {
      "npm": "@ai-sdk/openai-compatible",
      "name": "Almanac (campus gateway)",
      "options": {
        "baseURL": "https://GATEWAY-URL-FROM-YOUR-INSTRUCTOR/v1",
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

**Give it your key** — either as an environment variable (matches the config above):

```bash
export ALMANAC_API_KEY=sk-...     # add to your shell profile to keep it
```

or store it once with `opencode auth login` → **Other** → provider ID `almanac` → paste the key (then drop the `apiKey` line from the config).

**Prove it works:**

```bash
opencode run -m almanac/almanac-chat "Say hello and name your model."
```

Then `cd` into a project and run `opencode` for the full TUI.

**Honest expectations.**  A 7B-class campus model runs the coding loop and teaches you the workflow, but it is not a frontier model: expect occasional stumbles — a mis-named tool, a premature "done."  That's part of the lesson — you're learning to supervise an agent, not to trust one.  When the campus gateway grows bigger models, your same config gets better for free.

---

---

*Teaching a course on this?  See [Teaching a course on the aLLManac](teaching-a-course.md).*
