# The aLLManac — Course Guide

*For the people teaching with it, and the students building on it.*

Your class has its own AI service.  Not a rented seat on somebody's cloud — a
service your campus runs, on campus models, where the whole team can build
**one shared assistant together** and every token is on a ledger your course
can see.  This guide covers the three things you'll actually do:

1. **Build a custom GPT** (everyone)
2. **Build one as a group** — and share it with the class (the whole point)
3. **Use the models from code** with your API key (opencode)

Faculty: [Part 5](#part-5--teaching-a-course-on-this-faculty) is your
playbook, and the [admin guide](admin-guide.md) covers the machinery behind
it.

---

## Part 1 — Your first custom GPT

A "custom GPT" here is a LibreChat **Agent**: a system prompt + knowledge
files + tools, wrapped in a name.  Anyone can make one.

**Sign in** at the chat URL your instructor gave you — use the SSO button
(your campus credentials).  There's no separate account to create; logging
in *is* creating your account.

**Create the agent:**

1. In the model/endpoint menu at the top of a new chat, select **Agents**.
2. Open the **Side Panel** (right edge) → **Agent Builder**.
3. Fill in:
   - **Name** — what the class will see (`ENGR 301 Lab TA`)
   - **Description** — one line on what it's for
   - **Instructions** — the soul of the thing.  Give it a role, its
     boundaries, and its tone.  Concrete beats clever:

     > You are the lab assistant for ENGR 301 (Materials Characterization).
     > Help students reason through XRD and SEM sample-prep problems using
     > the attached lab manual.  Ask what they've already tried before
     > offering steps.  Never just give final answers to the numbered
     > pre-lab questions — guide toward them.
   - **Model** — `almanac-chat` (the campus model; your instructor may add
     more)
4. **Save**.  It now appears in your agent dropdown, and you can summon it
   in any chat by typing `@` + its name.

**Attach knowledge.**  In the builder, upload files where they'll do the
right job:

- **File Search** — the usual choice.  Files are indexed for retrieval, and
  the agent quotes and cites from them when relevant.  Course readings, lab
  manuals, syllabi.
- **File Context** — short reference text injected directly into the
  agent's instructions.  Rubrics, formula sheets, a style guide.  Keep it
  small; it rides along on every request.

Uploads are capped at course-materials scale (10 files per go, 25 MB each) —
if you're bumping the caps, you're probably attaching the wrong thing.

**Iterate.**  Talk to it.  When it answers wrong, that's not failure —
that's your next instruction line.  The gap between "an assistant" and "a
good assistant" is fifteen rounds of this.

---

## Part 2 — Group projects: one GPT, whole team

Emailing prompt revisions around is how group projects die.  Here, the team
shares **one agent**, and everyone with **Editor** access maintains it —
same instructions, same files, one body.

### What faculty set up (once per team)

Group sharing uses groups that live **in the chat platform's admin panel**
(`:3082` — same SSO button), not in the campus directory.  Two things
matter:

1. **People must log in once before they can be added to a group** —
   accounts are created at first login.  Make "everyone signs in" a
   day-one task.
2. In the **admin panel → Groups**: create one group per team
   (`engr301-team-gust`), add the members.  Takes a minute per team.

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

That's the whole trick: **Editor to the team's group.**  Every member can
now open the same agent in the builder and work on it.

### Working as co-editors

The agent has one body — edits overwrite, last save wins, and there's no
merge button.  Treat the instructions like a shared document: talk before
you rewrite, and keep a copy of the instructions in your team's repo or doc
if you want history.  (Your team chat *conversations* stay your own; it's
the agent itself that's shared.)

### Sharing with the class

- **The Agent Marketplace** (sidebar → Agent Marketplace) is where shared
  agents get discovered — browse by category, find what teams have
  published.
- To make a team's agent visible class-wide, share it **Viewer** to the
  course-wide group (faculty set one up, e.g. `engr301-all`) — or ask your
  instructor to promote it in the marketplace.
- Making an agent fully public (every user on the platform) is a faculty
  decision, deliberately not a student button.

**A caution worth repeating from the platform docs:** anyone who can chat
with an agent can eventually coax out what's in its files.  Attach
materials you'd hand the class anyway — never answer keys, never solutions,
never anything private.

---

## Part 3 — Your API key

Chat needs no key — sign in and go; the ledger already knows who you are.
The API key is for **code**: your own scripts, notebooks, and the coding
harness in Part 4.

- Keys are minted by your instructor or the admin, and every key belongs
  to an **owner** — your course or lab.  That's who the usage rolls up to.
- Each key carries a **budget**.  Campus models mean nobody's charging your
  card — the budget is there so a runaway loop gets caught and so the
  course can see what things *would* cost on commercial AI.  Visibility,
  not a paywall.
- **Treat the key like a password.**  It arrives via your instructor
  (LMS message, not a group chat).  Don't commit it to a repo, don't paste
  it into a shared doc.  If it leaks or you lose it, say so — the old one
  is retired and a new one minted in about a minute, no ceremony.
- If you hit your budget, requests start failing with a budget-exceeded
  error.  That's a conversation, not a punishment — ask for a bump.

The key works with **any OpenAI-compatible tool** pointed at the campus
gateway URL.  Which brings us to —

## Part 4 — The coding harness (opencode)

[opencode](https://opencode.ai) is an open-source coding agent that lives
in your terminal: it reads your project, edits files, runs commands — the
agentic-coding loop, on campus models, metered to your key.

**Install** (pick one):

```bash
curl -fsSL https://opencode.ai/install | bash    # the easy way
npm install -g opencode-ai                       # if you live in npm
brew install anomalyco/tap/opencode              # macOS
```

**Configure.**  Create `~/.config/opencode/opencode.json` (applies
everywhere) or `opencode.json` in a project folder (that project only):

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

**Give it your key** — either as an environment variable (matches the
config above):

```bash
export ALMANAC_API_KEY=sk-...     # add to your shell profile to keep it
```

or store it once with `opencode auth login` → **Other** → provider ID
`almanac` → paste the key (then drop the `apiKey` line from the config).

**Prove it works:**

```bash
opencode run -m almanac/almanac-chat "Say hello and name your model."
```

Then `cd` into a project and run `opencode` for the full TUI.

**Honest expectations.**  A 7B-class campus model runs the coding loop and
teaches you the workflow, but it is not a frontier model: expect occasional
stumbles — a mis-named tool, a premature "done."  That's part of the
lesson — you're learning to supervise an agent, not to trust one.  When the
campus gateway grows bigger models, your same config gets better for free.

*(Faculty/admins: `just workbench <key>` runs this exact setup in a
container on the box — handy for demos and for verifying a student's key
end to end.)*

---

## Part 5 — Teaching a course on this (faculty)

You sign in with the same SSO button — the platform recognizes faculty and
hands you the sharing controls, the people picker, the marketplace curation
tools, and the admin panel (`:3082`).

**Day-zero checklist:**

1. **Everyone logs in once.**  Accounts exist only after first login, and
   nothing below works without accounts.  Make it the first five minutes of
   the first lab.
2. **Groups** (admin panel → Groups): one course-wide group
   (`engr301-all`), one per team (`engr301-team-gust`, ...).  Membership
   edits propagate immediately — late adds are painless.
3. **Keys**: hand the admin your roster; keys are minted with
   `owner=<your course>` and a per-student budget (the default is modest
   and adjustable).  Distribute via individual LMS messages.
4. **Verify one student end to end** — login, open a shared agent, paste a
   key into opencode — before the assignment goes out.

**Course patterns that work:**

- **The course TA agent.**  You build it, attach the syllabus and lab
  manual, share **Viewer** to `engr301-all`.  Twenty questions about the
  late policy answer themselves.
- **Team-built agents as coursework.**  Each team gets Editor on their own
  agent (or creates it themselves — students can).  The assignment is the
  agent: instructions are graded prose, knowledge-file curation is graded
  research, and the iteration log is the lab notebook.
- **Peer review via the marketplace.**  Teams share final agents to
  `engr301-all` as Viewer; classmates stress-test each other's work.  You
  promote the best.
- **Watching the ledger.**  Month-to-date usage rolls up by course owner
  tag, and every chat request is attributed to the student who made it.
  What you can see directly vs. what to ask the admin for is laid out in
  the [admin guide](admin-guide.md#faculty-analytics--what-you-can-see) —
  short version: a read-only dashboard login is one invitation link away.
- **Term end.**  Ask the admin to sweep the course's keys.  Agents keep;
  keys retire.

The almanac's rule is the farm's rule: everything gets written down, and
the book stays on the shelf where the whole class can reach it.
