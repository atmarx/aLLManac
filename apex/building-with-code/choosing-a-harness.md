---
title: Which coding harness should I use?
description: Research shows that the same model can gain or lose tens of points depending on the harness around it, and which harness wins depends on the model.  How to choose a pairing of model and harness for what you're trying to do, and how to measure it yourself.
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

Terminal-Bench 2.0 ran one model, GPT-5, through four different harnesses on the same benchmark of terminal tasks:

| Harness | Score |
|---|---|
| Codex CLI | 49.6% |
| OpenHands | 41.5% |
| Terminus 2 | 35.2% |
| Mini-SWE-Agent | 33.9% |

With the same model and the same tasks, the scores spread over sixteen points.  In the same table, the best GPT-5 pairing and the best Claude Opus 4.5 pairing are about eight points apart.  For that model on that benchmark, the choice of harness moved the result further than the choice between two frontier models did.  ([Terminal-Bench 2.0, Merrill et al., Jan 2026](https://arxiv.org/pdf/2601.11868), Table 2.)

Asking only which model to use, or only which harness, leaves out half the choice.  The question that has an answer is **which pairing of model and harness, for what goal.**

## What the research says

The harness can move one model a long way.  The earliest careful result held GPT-4 Turbo fixed and changed only the interface the harness gave it: how files are viewed, how edits are made, and whether a linter checks them.  GPT-4 Turbo's bug-fixing score went from 11% to 18%, a 64% relative gain from the harness alone ([SWE-agent, Yang et al., NeurIPS 2024](https://arxiv.org/html/2405.15793v3)).  Since then the gaps have grown: on a benchmark of reproducing scientific results, one 2026 study found Codex CLI outscoring the benchmark's own reference harness by about 44 points with the same model, GPT-5.4 ([Nadgir et al., Jun 2026](https://arxiv.org/pdf/2606.26158)).

Which harness wins depends on the model.  The Holistic Agent Leaderboard ran many models through many scaffolds and concluded that "optimal agent design requires carefully matching models to scaffolds."  On its web-browsing tasks, one model family did better with one scaffold, and another family with a different one ([HAL, Kapoor et al., Oct 2025](https://arxiv.org/pdf/2510.11977)).  A maker's own harness isn't guaranteed to be the best one for its own model.  In the Terminal-Bench 2.0 table, Claude Opus 4.5 scored 57.8% in a neutral harness and 52.1% in Claude Code, and Gemini 2.5 Pro scored 32.6% in a neutral harness against 19.6% in Gemini CLI.

Models are trained toward particular harnesses, and the vendors document it.  OpenAI describes GPT-5-Codex as "optimized for agentic coding tasks in Codex or similar environments" ([OpenAI](https://developers.openai.com/api/docs/models/gpt-5-codex)), and its guide to the Codex models says of the file-editing format that "the model has been trained to excel at this diff format" ([OpenAI](https://developers.openai.com/cookbook/examples/gpt-5/codex_prompting_guide)).  Anthropic's file-editing tool has a schema that is "built into Claude's model and can't be modified" ([Anthropic](https://platform.claude.com/docs/en/agents-and-tools/tool-use/text-editor-tool)).  A harness that asks a model to edit files in a format it wasn't trained on puts the model at a disadvantage.

The list of tools a harness offers also changes the result.  Two studies held the models fixed and changed only the tools on offer: offering fewer improved how well models called them ([Less is More, 2024](https://arxiv.org/abs/2411.15399)), and renaming them gained up to 17% ([Lee et al., ACL 2026](https://arxiv.org/abs/2510.07248)).  Neither study was about coding agents, but the finding applies to them: a harness decides, among other things, what the model is shown.

## What it does not say

The research does not say the model stops mattering.  The same Terminal-Bench paper that shows the sixteen-point spread concludes that "model selection is usually more important than agent scaffold when optimizing for performance."  METR, measuring how long a task a model can finish, found, with a hedge of its own, that "neither Claude Code nor Codex outperform the default scaffolds METR uses" for the models it tested ([METR, Feb 2026](https://metr.org/notes/2026-02-13-measuring-time-horizon-using-claude-code-and-codex/)).

A fair reading of the research: **the model sets the upper limit, and the harness decides how much of that limit you get.**  The difference between harnesses can be larger than the difference between two good models, so choose the pairing.

A pairing of model and harness also has a version on both sides.  Harnesses ship weekly, and a release can change the instructions the model sees, the tools it is offered, and the format it edits in.  Those are the things the research found move the score.  Model releases matter too: a vendor's new model can arrive supported only by the newest release of the vendor's own harness, so last month's install can't run this month's model at all.  A complete pairing names the versions and the context, such as "pi 1.1 with model X, served at a 32k context," and not only "pi with model X."

The studies are also benchmarks: fixed tasks and frontier models, measured on a date.  Your task is not on any leaderboard, and the numbers will be out of date by the time you read them.  What carries over to your own work is the pattern that the pairing matters, not the specific scores.

## Small models are a different problem

Most of the harness research is about frontier models.  A model small enough to run on your institution's own hardware has two further problems in a harness, and they pull in different directions:

- **Harnesses are built for big models.**  Small models "typically fall short when swapped into a harness designed for a frontier LLM" ([Yang et al., Jul 2026](https://arxiv.org/abs/2607.08938)), and they often invent a tool name that doesn't exist ([Lee et al.](https://arxiv.org/abs/2510.07248)).  A harness's own instructions also take up room in a context window that is smaller to begin with.
- **Less structure is not automatically better.**  A 2026 study of harness design found that predefined tools help models that are weak with a raw shell, while models that are good with a shell do fine with it alone ([Fan et al., Sep 2026](https://arxiv.org/abs/2609.20804)).  A minimal harness is easier on the context window and harder on a model that needed the help.

Neither approach rescues a model that is too small.  A 20-billion-parameter open model scored about 3% on Terminal-Bench in each of two different harnesses.

## Three harnesses, two tested here

pi, opencode and Codex CLI are all built to speak an OpenAI-compatible API, so all three should work with the gateway and your key; setup for each is on [coding harnesses](harnesses.md).  **pi and opencode have run against this platform's gateway.**  opencode is the harness inside the platform's own workbench, the container its operators use to try the gateway from code.  On 2026-10-11, pi fixed a failing test end to end on two campus-size models: a 27-billion-parameter general model and a 9-billion-parameter coding model.  Codex is documented from its own sources and has not been run here.  The facts in the comparison table were checked against each project's own documentation on 2026-09-22, and pi's again on 2026-10-11.  These projects change quickly, so check again.

| | pi | opencode | Codex CLI |
|---|---|---|---|
| **Philosophy** | Minimal by design: four tools (read, write, edit, bash), extend it yourself | Provider-agnostic, full-featured | OpenAI's own harness, tuned alongside its Codex models |
| **Its own instructions + tools** | About 1,600 tokens on a task's first step, task included (measured here) | Roughly eight thousand tokens before you type | Several thousand tokens before you type |
| **What it needs from the gateway** | Chat Completions (or Responses) | Chat Completions (or Responses) | **Responses API only.**  Chat Completions support was removed in Feb 2026 |
| **Asks before running a command?** | **No.**  pi has no permission system, and its docs recommend a container or VM.  `--tools read,grep,find,ls` starts it read-only | **No.**  Bash and edits default to allowed.  `"permission": {"bash": "ask"}` turns asking on | Only at its sandbox edge.  Codex can write inside your project, and needs approval to go outside it or touch the network |
| **License** | MIT | MIT | Apache-2.0 |

The "asks before running a command" row matters most; [supervising an agent](supervising-an-agent.md) explains why.

## How to choose

Before you choose a harness, set up version control, tests and a way to deploy.  An agent needs them before the choice of harness makes any difference.  → [Before the agent](before-the-agent.md)

**If you don't know where to start, start with pi.**  pi's instructions leave a campus model the most room, you can read everything it sends, and it is one of the two harnesses run on this platform.  The drawback is that pi never asks before it acts.  Start it read-only or in a container, and read [supervising an agent](supervising-an-agent.md) first.

Beyond that, choose by what you're trying to do:

- **You want to understand how an agent works.**  Start with the smallest harness, where you can read everything it sends.  pi's instructions are short enough to read in a minute.  Watching a four-tool agent solve something teaches you more about the loop than a polished harness that hides it.
- **You want to get work done with a frontier model.**  Start with the harness that model's maker tunes it for, since that is the pairing the vendor tested.  Treat it as a default to compare against.  In the Terminal-Bench 2.0 results, the maker's own harness was often beaten.
- **You are on a campus model.**  On a campus model the pairing matters most and has been studied least.  The deciding question is whether the model calls tools reliably *in that harness*, and you find that out by trying it.  A lighter harness leaves more room in a small context window.  A fuller one gives a weaker model more structure to work with.  On this platform so far, pi finished a small task on both campus-size models we tried, in five and six steps.  That is two data points, not a general answer.

**If the agent will run while you aren't watching**, decide where it runs before you choose which harness to run.  Of pi, opencode and Codex, only Codex sandboxes itself by default.  → [Supervising an agent](supervising-an-agent.md)

## Try it yourself

The benchmarks can't tell you how a pairing does on your task, but an afternoon of testing can.  To compare two harnesses on the same model:

1. Pick a small, real task in a project under git, such as fixing a bug, adding a test, or renaming something across files.  Commit first, so the working tree is clean.  **Write down both harnesses' versions** (`pi --version`, `opencode --version`, `codex --version`) and the model name.  A result without them can't be compared with anyone else's, including yours next month.
2. Ask the Usage Guide in the {{PLATFORM}} chat for your usage, and note it.
3. Run the task in harness A.  When it says it is done, run your tests yourself and read `git diff`.  Note whether it worked, how many steps it took, and your usage afterward.
4. Run `git stash -u` to put the working tree back.  The `-u` also sets aside new files the agent created, which plain `git stash` and `git checkout .` leave behind.
5. Run the same task in harness B, with the same model and the same wording, and take the same notes.

Compare the two runs on four things: **did it work, what did it touch, how many tokens did it read, how many did it write.**  The number of tokens read is usually the surprise.  That number includes the harness's instructions and every file the agent opened, re-sent on every step.

Then run the task once with a different model in the same harness.  You will then have measured both halves of the pairing, harness and model, on your own task.

## Versions this page was checked against

| | Version | Released |
|---|---|---|
| Codex CLI (`@openai/codex`) | 0.155.1 | 2026-09-18 |
| opencode (`opencode-ai`) | 1.18.32 | 2026-09-21 |
| opencode, the platform's workbench | 1.18.2 | Run here, end to end |
| pi (`@earendil-works/pi-coding-agent`) | 1.1.0 | 2026-10-07 |
| pi, run here end to end | 1.1.0 | Two campus-size models, 2026-10-11 |

The versions were checked on 2026-09-22 against each project's own documentation and source, and pi's again on 2026-10-11.  Only the two "run here" rows have been run against this platform's gateway.  The studies cited under [What the research says](#what-the-research-says) used whatever versions each study ran; where a paper names its harness version, look there.  **If your version is newer than this table, the facts in the comparison table may have changed**, especially the permission defaults and API requirements.

## What we don't know yet

- **Beyond one small task, nobody has measured these pairings on the models this platform serves.**  The research is about frontier models on benchmark tasks.  If you run the experiment in [Try it yourself](#try-it-yourself), your result is data we don't have.  Tell us through the report tool in the {{PLATFORM}} chat.
- **Codex through this gateway is untested.**  Codex speaks only the Responses API, and the gateway has to translate that for models whose servers only speak Chat Completions.  Nobody has checked whether tool calls survive that translation on our models.  A translation like that can look correct in the documentation and still fail in the agent loop.
- **The research numbers are dated.**  Harnesses release weekly, and every model generation reshuffles the rankings.  So far, every reshuffle has kept one finding: performance depends on the pairing of model and harness.
