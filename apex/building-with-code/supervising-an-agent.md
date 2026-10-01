---
title: What does it mean to supervise a coding agent?
description: An agent almost always tells you what it is about to do.  Supervision is reading that, understanding it well enough to say no, and checking the work afterward — not pressing enter.  How to do that with the harnesses here, and what to check before running one we haven't tested.
audience: student
also_reaches: [faculty]
status: draft
owner: piper
tags: [agentic-coding, harness, accountability, academic-integrity, critical-evaluation, ai-literacy, faculty-duty]
tethered_to:
  - docs/agent-contract.md
  - apex/building-with-code/choosing-a-harness.md
  - apex/building-with-code/your-key.md
  - apex/building-with-code/before-the-agent.md
---

# Supervising an agent

The tests were failing, and the agent explained why in one plain sentence: *"The failure is the date check in `test_invoice.py` — I'll remove that assertion so the suite passes."*  Then it asked to edit the test file.  The student pressed enter.  The suite went green, the agent reported success, and the bug the test existed to catch shipped with a passing grade.

Nothing was hidden.  The agent said exactly what it was going to do, in English, before it did it.  The failure happened at the moment someone approved a sentence they hadn't read.

## Read everything

That's the whole secret, and it isn't a tool.  An agent narrates its work: the plan before it starts, each command before it runs, the file it is about to change and why.  Most of the time it tells you exactly what it's going to do.  Problems come from people approving what they don't understand, not from agents hiding things.

So read:

- **The plan.**  Before the first tool call, most agents say how they intend to approach the task.  This is the cheapest place to catch a wrong turn, because nothing has happened yet.
- **Every command, before it runs.**  What does it touch?  Does it delete, install, push, or reach the network?  Is it inside your project, or somewhere else on your machine?
- **The reason it gives.**  "So the suite passes" is a reason to stop.  An agent that is trying to make a check pass is not the same as one trying to make the code correct, and it will tell you which one it's doing.
- **Its "done."**  That's a claim, and the next section is how you check it.

A campus model stumbles in ways you can see, if you're reading: a tool called by the wrong name, an edit in the wrong file, a confident "finished" on work that isn't ([what to expect from a campus model](harnesses.md#what-to-expect-from-a-campus-model)).  Every one of those shows up in the transcript before it shows up in your code.

## A human in the loop is not the same as a human paying attention

Having a person press "allow" on every step feels like oversight.  It isn't, on its own.  The thirtieth approval in a session is a reflex, and a reflex is not judgement.

**Supervision means exercising judgement and restraint, based on understanding the work — or at least being curious about it.**  You don't need to know every command by heart.  You need to notice when you don't know one, and treat that as a question rather than a formality.

- **Not understanding is a reason to ask, not a reason to approve.**  Ask the agent: *"Before you run that, explain what it does and what it will change."*  It costs one message.  The explanation is something else to read, and if it doesn't match the command, you've just caught something.
- **"No" is a supervising move.**  So are "stop," "don't touch the tests," and "do only the first part, then show me."  A narrower task is easier to check.
- **Some things deserve a pause every time:** a change to a test so it passes; deleting files or directories; installing a package you didn't ask for; `sudo`; anything piped from the internet into a shell; anything outside your project folder; a `git push`; touching credentials or config files.  The same failing fix tried a third time is a loop — stop it and re-scope.

## Most harnesses won't ask you

Here's the uncomfortable part.  The approval prompt you'd exercise judgement on often doesn't exist.  Of the three harnesses [this platform has tested](choosing-a-harness.md#three-harnesses-that-work-here):

- **opencode** allows file edits and shell commands by default.  It does not ask.  Adding `"permission": {"bash": "ask"}` to its config turns asking on, and its built-in Plan agent is read-only.
- **pi** has no permission system at all, by design, and its own documentation recommends running it in a container or a virtual machine.
- **Codex** asks only at the edge of its sandbox: it can write inside your project without asking, and asks before going outside it or touching the network.

So for two of the three, out of the box, the narration scrolling past *is* the checkpoint.  You have two levers, and you should use at least one of them before you start:

1. **Turn asking on**, where the harness lets you.
2. **Decide where it runs before you start it.**  Work on a fresh branch, in a clean working tree, and commit first, so `git diff` afterward shows exactly what the agent did and nothing else.  New to git?  [Before the agent](before-the-agent.md) has the minimum, and it comes first for a reason.  Never start one from your home directory.  For a harness with no permission system, use the container its authors recommend.

The behaviour above was checked against each project's documentation on 2026-09-22, at the versions listed on [Choosing a harness](choosing-a-harness.md#versions-this-page-was-checked-against).  Harnesses change their defaults; check yours.

## Check the work, not the report

- **Read the diff, not the summary.**  The summary is the agent's description of what it did.  The diff is what it did, and you only have one if the work is under [version control](before-the-agent.md).
- **Run the tests yourself.**  An agent that ran them may also have edited them, which is the story at the top of this page.
- **What it ran, you ran.**  Every command executed in your repository, under your account.  Every token went through [your key](your-key.md), under your name.  None of it is the model's: a model can't take responsibility for anything, so all of it stays with the person who started it.

## A harness we haven't tested

The three harnesses above are the ones that have been tried on this platform.  They aren't the only ones you're allowed to use.  New ones appear every week, many with genuinely good ideas, most of them young.  If you want to try one, go ahead, but read it the way you'd read an agent's plan:

- **Connect it as an "OpenAI-compatible" or "custom" provider**, pointed at [the gateway](the-gateway.md) with `/v1` on the end.  A harness's built-in Anthropic, Gemini or OpenRouter adapter won't work with your key, however many providers its README lists.
- **Find out what it does on its own, before the first run.**  Look for telemetry, cloud sync, session sharing, web search and browsing, and anything that opens a tunnel to the internet.  Turn off what you don't need.  Keep your key in an environment variable, never in a config file the harness might sync.  If the key ever left your machine, [rotate it](your-key.md#replacing-it).
- **Set its context to what the model is served with.**  Young harnesses tend to assume frontier-sized windows, and some servers [quietly drop the front of a prompt](the-gateway.md#chat-and-code-are-limited-by-different-things) that's too long.
- **Turn off memory or "self-learning" features for coursework.**  They change how the agent behaves from one session to the next, so "it worked yesterday" stops meaning anything, and what they store can include your code.
- **Write down what you ran:** harness, version, model.  We can't debug a harness we don't support.  But "harness X, version 1.2, on almanac-chat: tool calls never fire" is exactly the result [nobody has measured yet](choosing-a-harness.md#what-we-dont-know-yet), and the front door's report tool will take it.

!!! warning "On a campus model, nothing stops a runaway loop but you"
    Your key's fuse counts dollars, and a model on your institution's own hardware may be recorded at **$0** ([why](your-key.md#what-it-is)).  On that model the fuse never moves.  A harness stuck retrying all weekend hits no ceiling, and every token is still recorded under your name.  Set the harness's own turn or step limit if it has one, and don't leave a harness you haven't tested running while you're away.

## Your course's rules still apply

Whether you may use a coding agent on a given assignment is your instructor's decision, and the chat policy doesn't settle it: being allowed to ask a chatbot questions is not the same as being allowed to have an agent write the code you hand in.  If the syllabus doesn't say, ask.  [For students](../teaching-with-ai/for-students.md) covers the general case.

**Instructors:** say it explicitly, per assignment if it varies.  A student can't infer a harness policy from a chat policy, and shouldn't have to guess.  [Your syllabus policy](../teaching-with-ai/syllabus-policy.md) has language to start from.

## Why a small model is a good teacher here

A frontier model makes rare mistakes, and rare mistakes teach you to stop checking.  A campus model makes visible ones, often enough that reading becomes a habit.  The habit is what you're here to learn, and it carries over to every model you'll use after this one.

The agent in the story at the top told the student, in plain English, that it was going to delete the check.  Agents almost always tell you.  Your job is to read it.
