---
title: Which coding harness should I use?
description: The wrong question, and the research that says so — the same model can gain or lose tens of points depending on the harness around it, and which harness wins depends on the model.  How to choose a pairing for what you are actually trying to do, and how to measure it yourself.
audience: student
also_reaches: [faculty, builder]
status: draft
owner: piper
tags: [harness, agentic-coding, tool-calling, openai-compatible, critical-evaluation, ai-literacy]
tethered_to:
  - apex/building-with-code/harnesses.md
  - litellm/config.yaml
---

# Which harness should I use?

Here is one model, GPT-5, run through four different harnesses on the same benchmark of terminal tasks:

| Harness | Score |
|---|---|
| Codex CLI | 49.6% |
| OpenHands | 41.5% |
| Terminus 2 | 35.2% |
| Mini-SWE-Agent | 33.9% |

Same model, same tasks, a sixteen-point spread.  In the same table, the best GPT-5 pairing and the best Claude Opus 4.5 pairing are about eight points apart.  **For that model on that benchmark, the choice of harness moved the result further than the choice between two frontier models did.**  ([Terminal-Bench 2.0, Merrill et al., Jan 2026](https://arxiv.org/pdf/2601.11868), Table 2.)

So "which model should I use?" and "which harness should I use?" are both incomplete.  The question that has an answer is **which pairing, for what goal.**

## What the research says

**The harness can move one model a long way.**  The earliest careful result held GPT-4 Turbo fixed and changed only the interface the harness gave it — how files are viewed, how edits are made, whether a linter checks them.  Its bug-fixing score went from 11% to 18%, a 64% relative gain from the harness alone ([SWE-agent, Yang et al., NeurIPS 2024](https://arxiv.org/html/2405.15793v3)).  Since then the gaps have grown: on a benchmark of reproducing scientific results, one 2026 study found Codex CLI outscoring the benchmark's own reference harness by about 44 points with the same model, GPT-5.4 ([Nadgir et al., Jun 2026](https://arxiv.org/pdf/2606.26158)).

**Which harness wins depends on the model.**  The Holistic Agent Leaderboard ran many models through many harnesses and concluded that "optimal agent design requires carefully matching models to scaffolds" — one family did better with one harness, another with a different one ([HAL, Kapoor et al., Oct 2025](https://arxiv.org/pdf/2510.11977)).  And the maker's own harness is not guaranteed to be the best home for its own model: in the Terminal-Bench table above, Claude Opus 4.5 scored 57.8% in a neutral harness and 52.1% in Claude Code, and Gemini 2.5 Pro scored 32.6% in a neutral harness against 19.6% in Gemini CLI.

**Models are trained toward particular harnesses.**  This is the mechanism, and the vendors say so.  OpenAI describes GPT-5-Codex as "optimized for agentic coding tasks in Codex or similar environments," and its guide to the Codex models says of the file-editing format that "the model has been trained to excel at this diff format" ([OpenAI](https://developers.openai.com/cookbook/examples/gpt-5/codex_prompting_guide)).  Anthropic's file-editing tool has a schema that is "built into Claude's model and can't be modified" ([Anthropic](https://platform.claude.com/docs/en/agents-and-tools/tool-use/text-editor-tool)).  A harness that asks a model to edit files in a format it wasn't trained on is asking it to work with its off hand.

**Even the tool list changes the result.**  Two studies held the models fixed and changed only the tools on offer: offering fewer improved how well models called them ([Less is More, 2024](https://arxiv.org/abs/2411.15399)), and renaming them gained up to 17% ([Lee et al., ACL 2026](https://arxiv.org/abs/2510.07248)).  Neither was about coding agents specifically, but the lesson carries: a harness is, among other things, a decision about what the model is shown.

## What it does not say

It does not say the model stops mattering.  The same Terminal-Bench paper that shows the sixteen-point spread concludes that "model selection is usually more important than agent scaffold when optimizing for performance."  METR, measuring how long a task a model can finish, found that "neither Claude Code nor Codex outperform the default scaffolds METR uses" for the models it tested ([METR, Feb 2026](https://metr.org/notes/2026-02-13-measuring-time-horizon-using-claude-code-and-codex/)).

The fair reading: **the model sets the ceiling, and the harness decides how much of it you reach** — and how much you reach can vary by more than the distance between two good models.  That is why the pairing is what you choose, rather than either half.

**And a pairing has a version on both sides.**  Harnesses ship weekly, and a release can change the instructions the model sees, the tools it is offered, and the format it edits in — everything the research above says moves the score.  It runs the other way too: when a vendor releases a new model, it can arrive supported only by the newest release of the vendor's own harness, so last month's install can't run this month's model at all.  "opencode with model X" is not quite a pairing.  "opencode 1.18 with model X, served at a 32k context" is.

These are also benchmarks: fixed tasks, frontier models, measured on a date.  Your task is not on any leaderboard, and the numbers will be stale by the time you read them.  What transfers is the shape, not the scores.

## Small models are a different problem

Most of that research is about frontier models.  A model small enough to run on your institution's own hardware has two further troubles in a harness, and they pull in different directions:

- **Harnesses are built for big models.**  Small models "typically fall short when swapped into a harness designed for a frontier LLM" ([Yang et al., Jul 2026](https://arxiv.org/abs/2607.08938)), and they are the ones most likely to invent a tool name that doesn't exist ([Lee et al.](https://arxiv.org/abs/2510.07248)).  A harness's own instructions also take up room in a context window that is smaller to begin with.
- **But less structure is not automatically better.**  A 2026 study of harness design found that predefined tools help models that are weak with a raw shell, while strong models do fine with the shell alone ([Fan et al., Sep 2026](https://arxiv.org/abs/2609.20804)).  A minimal harness is easier on the context window and harder on a model that needed the help.

And neither rescues a model that is simply too small: a 20-billion-parameter open model scored about 3% on Terminal-Bench in each of two different harnesses.

## Three harnesses that work here

All three speak to the gateway with your key; setup for each is on [coding harnesses](harnesses.md).  Facts checked against each project's own documentation on 2026-09-22 — these projects move fast, so check again.

| | opencode | Codex CLI | pi |
|---|---|---|---|
| **Philosophy** | Provider-agnostic, full-featured | OpenAI's own harness, tuned alongside its Codex models | Deliberately minimal: four tools (read, write, edit, bash), extend it yourself |
| **Its own instructions + tools** | Several thousand tokens before you type | Several thousand tokens before you type | Under a thousand, by its author's count (Nov 2025) |
| **What it needs from the gateway** | Chat Completions (or Responses) | **Responses API only** — Chat Completions support was removed in Feb 2026 | Chat Completions (or Responses) |
| **Asks before running a command?** | **No** — bash and edits default to allowed; `"permission": {"bash": "ask"}` turns asking on | Only at its sandbox edge — it can write inside your project, and needs approval to go outside it or touch the network | **No** — it has no permission system, and its docs recommend a container or VM |
| **License** | MIT | Apache-2.0 | MIT |

That "asks before running a command" row matters more than it looks, and [supervising an agent](supervising-an-agent.md) is about why.

## How to choose

Start from what you are trying to do, not from the tool.

- **You want to understand how an agent works.**  Start with the smallest harness, because you can read everything it sends.  pi's instructions are short enough to read in a minute; watching a four-tool agent solve something teaches you more about the loop than a polished one that hides it.
- **You want to get work done with a frontier model.**  Start with the harness that model's maker tunes for — it is the pairing the vendor tested — and treat that as a default, not a verdict.  The numbers above show it is often beaten.
- **You are on a campus model.**  The pairing matters most here and is least studied.  What decides it is whether the model calls tools reliably *in that harness* — which you find out by trying, not by reading.  A lighter harness leaves more room in a small context window; a fuller one gives a weaker model more to hold on to.  There is no general answer yet.
- **The agent will run while you aren't watching.**  Pick where it runs before you pick what runs.  Only one of these three fences itself by default.  → [Supervising an agent](supervising-an-agent.md)

## Try it yourself

The benchmarks can't tell you about your task.  An afternoon can.

1. Pick a small, real task in a project under git — fix a bug, add a test, rename something across files.  Commit first, so the working tree is clean.  **Write down both harnesses' versions** (`opencode --version` and `codex --version`; pi's `--help` lists its flag) and the model name.  A result without them can't be compared with anyone else's, including yours next month.
2. Ask your course's chat for your usage, and note it.
3. Run the task in harness A.  When it says it is done, run your tests yourself and read `git diff`.  Note whether it worked, how many steps it took, and your usage afterwards.
4. `git stash` or `git checkout .` to put the tree back.
5. Same model, same wording, harness B.  Same notes.

Compare four things: **did it work, what did it touch, how many tokens did it read, how many did it write.**  The third is usually the surprise — it is the harness's instructions and every file it opened, re-sent on every step.

Then try it once with a different model in the same harness.  You will have measured, on your own task, the two halves of the pairing — which is more than any of the leaderboards can tell you.

## Versions this page was checked against

| | Version | Released |
|---|---|---|
| Codex CLI (`@openai/codex`) | 0.155.1 | 2026-09-18 |
| opencode (`opencode-ai`) | 1.18.32 | 2026-09-21 |
| pi (`@earendil-works/pi-coding-agent`) | 0.87.0 | 2026-09-21 |

Checked 2026-09-22 against each project's own documentation and source, not run against this platform's models.  The research results above used whatever versions each study ran; where a paper names its harness version, it is in the paper, not here.  **If your version is newer than this table, the facts in the comparison table may have moved** — the permission defaults and API requirements especially.

## What we don't know yet

- **Nobody has measured these pairings on the models this platform serves.**  The research is about frontier models on benchmark tasks.  If you run the experiment above, your result is data we don't have — tell us through the front door's report tool.
- **Codex through this gateway is untested.**  Codex speaks only the Responses API, and the gateway has to translate that for models whose servers only speak Chat Completions.  Whether tool calls survive that translation, on our models, is exactly the kind of thing that works on paper and fails in the loop.
- **The numbers on this page have a date.**  Harness releases land weekly, and every model generation reshuffles the table.  The finding that has survived every reshuffle so far is the one this page is about: it is the pairing that performs.
