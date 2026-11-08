---
title: How do I build with my course's AI?
description: The walkthrough for the people in a course, covering building your own agent, maintaining one as a team of co-editors, and pointing your own code at the campus gateway with an API key.
audience: student
also_reaches: [faculty]
status: draft
owner: piper
tags: [sso, access-control, rbac, secrets-management, key-rotation, attribution, metering, assessment-design, ai-literacy, accountability, faculty-duty, student-right, librechat, litellm]
tethered_to:
  - docs/design-walls.md
  - registrar/render.py
  - registrar/server.py
  - registrar/planes/gateway.py
  - usage-mcp/server.py
  - justfile
  - docs/admin-guide.md
---

# Using {{PLATFORM}} in a course

*For the people teaching with {{PLATFORM}}, and the students building on it.*

Your class has its own AI service on {{PLATFORM}}, run by your campus on campus models.  A whole team can build **one shared assistant together**, and every token is recorded on a ledger your course can see.  Working in a course on {{PLATFORM}} comes down to three things:

1. Build an agent (everyone)
2. Build an agent as a group, and share it with the class (the main goal)
3. Use the models from code with your API key (pi)

Faculty should also read [Teaching a course](teaching-a-course.md).  The operators keep their own guide to how the platform runs.

---

## Part 1: Your first agent

An **agent** is what other tools call a custom GPT: a system prompt, knowledge files and tools, saved under a name.  Anyone in a course can make one.

Sign in at the chat URL your instructor gave you, using the SSO button and your campus credentials.  There's no separate account to create.  Enrolling you created your account, and your first sign-in links your campus login to it.

**To create an agent:**

1. In the model/endpoint menu at the top of a new chat, select **My Agents**.
2. Open the **Side Panel** (right edge) → **Agent Builder**.
3. Fill in:
   - **Name**: what the class will see (`ENGR 301 Lab TA`)
   - **Description**: one line on what it's for
   - **Instructions**: the system prompt.  Give it a role, its boundaries, and its tone.  Concrete instructions work better than clever ones.  For example:

     > You are the lab assistant for ENGR 301 (Materials Characterization).  Help students reason through XRD and SEM sample-prep problems using the attached lab manual.  Ask what they've already tried before offering steps.  Never give final answers to the numbered pre-lab questions.  Guide students toward the answers instead.
   - **Model**: `{{MODEL}}` (the campus model; your instructor may add more)
4. **Save**.  The agent now appears in your agent dropdown, and you can call it into any chat by typing `@` followed by its name.

To attach knowledge to an agent, upload files in the Agent Builder under one of two options:

- **File Search**: the usual choice.  Files are indexed for retrieval, and the agent quotes and cites from them when relevant.  Use File Search for course readings, lab manuals and syllabi.
- **File Context**: short reference text added directly to the agent's instructions, such as rubrics, formula sheets, or a style guide.  Keep File Context small.  It is sent with every request.  **File Context is off unless your course has it switched on**, so if you don't see it in the builder, use File Search.

Uploads are capped at course-materials scale: 10 files per upload, 25 MB each.  If you're hitting the caps, you're probably attaching the wrong thing.

Charts and diagrams open in a panel.  Ask an agent for a chart, a diagram, a table you can sort or a small web page, and a panel opens beside the chat with the result in it.  You can switch between the result and the code that made it.  The panel works for every agent on {{PLATFORM}}, with nothing to switch on.  The panel is a preview, not a saved file, so copy out anything you want to keep.  A chart is lost when the conversation it was drawn in is gone.

Improve an agent by talking to it.  When it answers wrong, add an instruction that fixes that answer.  Getting from a working assistant to a good one takes about fifteen rounds of this.

---

## Part 2: Group projects (one agent, whole team)

In a group project, the team shares **one agent**, and everyone with **Editor** access maintains the same instructions and the same files.

### What your instructor sets up

Your instructor makes your team's group for you.  You do not need the admin panel, and there is nothing to install.  **Log in at least once before your instructor adds you to a group.**  Your sign-in account exists from the moment you are enrolled, but the people picker searches the chat's own list of users, and you only appear there after your first sign-in.  If your instructor can't find your name in the people picker, a missing first sign-in is almost always the reason.

### Sharing the agent to the team

To share an agent with the team, whoever created it (faculty or a team member) does the following:

1. Open the agent in the **Agent Builder** → **Share**.
2. Search for the team's group name.
3. Grant a role:

   | Role | What it means |
   |---|---|
   | **Viewer** | Can chat with the agent.  Can't see or change how it works. |
   | **Editor** | Can change instructions, model, tools, **and knowledge files**.  This is the co-editing role.  Give it to the team. |
   | **Owner** | Everything an Editor can do, plus delete and re-share.  Keep this role to one or two people. |

**Editor for the team's group** is the setting that matters.  With it, every team member can open the same agent in the builder and work on it.

### Working as co-editors

A shared agent has only one copy.  Edits overwrite each other, the last save wins, and there's no merge button.  Treat the agent's instructions like a shared document: talk with your team before you rewrite them, and keep a copy of the instructions in your team's repo or doc if you want a history.  Your own *conversations* with the team's agent are not shared.  Only the agent itself is shared.

### Sharing with the class

- **The Agent Marketplace** (sidebar → Agent Marketplace) lists shared agents.  You can browse by category and find what teams have published.
- To make a team's agent visible class-wide, share it **Viewer** to the course-wide group that faculty set up (for example, `engr301-all`), or ask your instructor to share it there for you.
- **Nothing you share is visible outside your course.**  Each course runs its own copy of the chat, so even the widest share includes only the people in that course.  There is no platform-wide sharing setting, for you or your instructor.  To share an agent beyond your course, nominate it: ask the Student Guide or the Instructor Guide in the {{PLATFORM}} chat, giving the agent's id from its edit page and a line on what it does.  The people who run the servers review the nomination and turn the agent into a template another course can start from.

**Caution:** anyone who can chat with an agent can eventually get it to reveal what's in its files.  Only attach materials you would hand the class anyway.  Never attach answer keys, solutions, or anything private.

---

## Part 3: Your API key

Chat needs no API key.  You sign in, and the ledger already knows who you are.  The API key is for **code**: your own scripts, notebooks, and the coding harness in Part 4.

- You fetch your API key yourself.  In the {{PLATFORM}} chat (where the guides are, not your course's chat), ask the **Coder Guide** for your key ([step by step](building-with-code/your-key.md)).  If you are in more than one course, the guide asks which one.  The reply includes the gateway address too.  Your key is minted when your instructor enrolls you, so if the guide says you're not on the roster yet, ask your instructor.  Nobody emails the key to you, and nobody else can fetch it for you.
- You get one key per course, with your name on it.  If you are in two courses, you have two keys, each spending against its own course, and every request made with either key is recorded against you.
- Each key has a small budget of its own, which stops a runaway loop before it uses up your course's budget.  The key budget counts dollars, so on a model your deployment records at $0 it never moves.  [Your key](building-with-code/your-key.md#what-it-is) explains.
- **Treat the key like a password.**  Don't commit it to a repo or paste it into a shared doc.  If your key leaks or you lose it, ask the Coder Guide to **rotate** it.  You get a new key, the old one stops working, and whatever was left on the old key's budget moves to the new one.  Rotation takes seconds and needs nobody's permission.
- If you hit your key's budget, requests start failing with a budget-exceeded error.  Hitting the budget is not a punishment.  Talk to your instructor about it.
- To check your usage, ask the **Usage Guide** in the {{PLATFORM}} chat "how much have I used this week?"  It answers with your numbers, chat and API keys combined, without spending your course's budget.  The Usage Guide only ever shows your own numbers, never anyone else's.

[Your API key](building-with-code/your-key.md) has the details: what the key budget counts, why a model added later may not show up on your key, and how to keep the key out of a repo.

The API key works with **any OpenAI-compatible tool** pointed at the campus gateway URL.

## Part 4: The coding harness (pi)

[pi](https://pi.dev) is an open-source coding agent that runs in your terminal.  It reads your project, edits files and runs commands in an agentic-coding loop, using campus models and metered to your key.  pi is the harness to start with on {{PLATFORM}}.  opencode and Codex are covered on the same harnesses page if you prefer them.  pi never asks before it acts, so start it read-only the first time.

Install, configure and test pi using [Coding harnesses](building-with-code/harnesses.md#pi).  The configuration is kept on that page only, so there is one copy to keep up to date.  You'll need the **gateway address**, which comes with your key, and the **context size** the model is served with.  The context size comes from whoever runs your platform, and your instructor can find it out.

A small campus model can run the coding loop and teach you the workflow, but it is not a frontier model.  Expect occasional mistakes, such as a mis-named tool or a premature "done."  Catching those mistakes is part of the lesson: you're learning to supervise an agent, not to trust one.  When larger models are added to the campus gateway, the same pi configuration will work better with no changes.

---

*If you teach a course on {{PLATFORM}}, see [Teaching a course on {{PLATFORM}}](teaching-a-course.md).*
