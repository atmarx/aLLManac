---
title: What does it mean to supervise a coding agent?
description: A coding agent almost always tells you what it is about to do.  Supervising it means reading that, understanding it well enough to say no, and checking the work afterward.  How to do that with the harnesses documented here, and what to check before running one we haven't tested.
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

The tests were failing, and the agent explained why in one sentence: *"The failure is the date check in `test_invoice.py`.  I'll remove that assertion so the suite passes."*  Then it asked to edit the test file.  The student pressed enter.  The suite went green and the agent reported success, but the bug the test was written to catch was still in the code.

The agent hid nothing.  It said exactly what it was going to do, in English, before it did it.  The mistake was approving a sentence nobody had read.

## Read everything

No tool does the reading for you.  A coding agent describes its work as it goes: the plan before it starts, each command before it runs, the file it is about to change and why.  Problems come from people approving steps they don't understand.

Read each of these as the agent shows it:

- **The plan.**  Before the first tool call, most agents say how they intend to approach the task.  The plan is the cheapest place to catch a wrong turn, since nothing has happened yet.
- **Every command, before it runs.**  What does it touch?  Does it delete, install, push, or use the network?  Is it inside your project, or somewhere else on your machine?
- **The reason the agent gives.**  "So the suite passes" is a reason to stop.  Making a check pass and making the code correct are different goals, and the agent's stated reason tells you which one it is working toward.
- **The agent's "done."**  "Done" is a claim to verify.  [Check the work, not the report](#check-the-work-not-the-report) covers how.

A campus model makes mistakes you can see if you're reading: a tool called by the wrong name, an edit in the wrong file, a confident "finished" on unfinished work ([what to expect from a campus model](harnesses.md#what-to-expect-from-a-campus-model)).  Each of those mistakes appears in the transcript before it appears in your code.

## A human in the loop is not the same as a human paying attention

Pressing "allow" on every step feels like oversight, but approval alone is not supervision.  By the thirtieth approval in a session, people press "allow" out of habit, without judging the step.

**Supervision means exercising judgment and restraint, based on understanding the work, or at least being curious about it.**  You don't need to know every command by heart.  You need to notice when you don't know one, and ask about it before you approve.

- **If you don't understand a step, ask before you approve it.**  Ask the agent: *"Before you run that, explain what it does and what it will change."*  That costs one message.  Read the explanation too.  If it doesn't match the command, you've caught a problem.
- **You can say no.**  You can also say "stop," "don't touch the tests," or "do only the first part, then show me."  A narrower task is easier to check.
- **Some actions deserve a pause every time:** a change to a test so it passes; deleting files or directories; installing a package you didn't ask for; `sudo`; anything piped from the internet into a shell; anything outside your project folder; a `git push`; touching credentials or config files.  If the agent tries the same failing fix a third time, it is stuck in a loop.  Stop it and narrow the task.

## Most harnesses won't ask you

Many harnesses don't show an approval prompt by default.  The three harnesses documented on [Choosing a harness](choosing-a-harness.md#three-harnesses-two-tested-here) behave like this:

- **pi**, the suggested harness to start with, has no permission system at all, by design.  pi's own documentation recommends running it in a container or a virtual machine.  You can start pi read-only: `pi --tools read,grep,find,ls` lets the model read and search your project and nothing else.
- **opencode** allows file edits and shell commands by default, without asking.  Adding `"permission": {"bash": "ask"}` to its config turns asking on, and its built-in Plan agent asks before it edits a file or runs a command.
- **Codex** asks only at the edge of its sandbox: it can write inside your project without asking, and asks before going outside it or touching the network.

With pi and opencode at their defaults, reading the agent's output as it scrolls past is your only checkpoint.  Before you start, use at least one of these two safeguards:

1. **Turn asking on** where the harness allows it.  For pi, start read-only and add tools once you've seen how it works.
2. **Decide where it runs before you start it.**  Work on a fresh branch, in a clean working tree, and commit first, so `git diff` afterward shows exactly what the agent did and nothing else.  New to git?  [Before the agent](before-the-agent.md) has the minimum; read it first.  Never start a harness from your home directory.  For a harness with no permission system, use the container its authors recommend.

The permission behavior of pi, opencode and Codex was checked against each project's documentation on 2026-09-22, and pi's again on 2026-10-11, at the versions listed on [Choosing a harness](choosing-a-harness.md#versions-this-page-was-checked-against).  Harnesses change their defaults, so check the version you have.

## Check the work, not the report

- **Read the diff, not the summary.**  The summary is the agent's description of what it did.  The diff shows what it did, and you only have a diff if the work is under [version control](before-the-agent.md).
- **Run the tests yourself.**  An agent that ran the tests may also have edited them, like the agent that removed the date check from `test_invoice.py`.
- **You are responsible for what the agent ran.**  Every command ran in your repository, under your account.  Every token went through [your key](your-key.md), under your name.  A model can't take responsibility for anything, so all of it is on the person who started the agent.

## A harness we haven't tested

The harnesses documented here are pi, opencode and Codex, and pi and opencode have been run against this platform.  You are allowed to use others.  New harnesses appear every week, many with good ideas, and most of them are young projects.  If you want to try one, go ahead, but check it the way you'd check an agent's plan.

Before the first run of an untested harness:

- **Connect it as an "OpenAI-compatible" or "custom" provider**, pointed at [the gateway](the-gateway.md) with `/v1` on the end.  A harness's built-in Anthropic, Gemini or OpenRouter adapters are untested here, however many providers its README lists.  The OpenAI-compatible provider is the one known to work.
- **Find out what it does on its own.**  Look for telemetry, cloud sync, session sharing, web search and browsing, and anything that opens a tunnel to the internet.  Turn off what you don't need.  Keep your key in an environment variable, never in a config file the harness might sync.  If the key ever left your machine, [rotate it](your-key.md#replacing-it).
- **Set its context to what the model is served with.**  Young harnesses tend to assume frontier-sized windows, and when a prompt is too long, some servers [drop the oldest part of it without warning](the-gateway.md#chat-and-code-are-limited-by-different-things).

While you use an untested harness for coursework:

- **Turn off memory or "self-learning" features.**  Memory features change how the agent behaves from one session to the next, so a result from yesterday may not repeat today.  What they store can include your code.
- **Write down what you ran:** harness, version, model.  We can't debug a harness we don't support.  But a result like "harness X, version 1.2, on {{MODEL}}: tool calls never fire" is something [nobody has measured yet](choosing-a-harness.md#what-we-dont-know-yet), and the report tool in the {{PLATFORM}} chat accepts it.

!!! warning "On a campus model, nothing stops a runaway loop but you"
    Your key's fuse counts dollars, and a model on your institution's own hardware may be recorded at **$0** ([why](your-key.md#what-it-is)).  On that model the fuse never moves.  A harness stuck retrying all weekend hits no ceiling, and every token is still recorded under your name.  Set the harness's own turn or step limit if it has one, and don't leave a harness you haven't tested running while you're away.

## Your course's rules still apply

Whether you may use a coding agent on a given assignment is your instructor's decision, and the course's chat policy doesn't settle it.  Permission to ask a chatbot questions is not permission to have an agent write the code you hand in.  If the syllabus doesn't say, ask.  [For students](../teaching-with-ai/for-students.md) covers the general case.

**Instructors:** state your coding-agent policy explicitly, per assignment if it varies.  A student can't work out a harness policy from a chat policy, and shouldn't have to guess.  [Your syllabus policy](../teaching-with-ai/syllabus-policy.md) has language to start from.

## Why a small model is a good teacher here

A frontier model makes mistakes rarely, and rare mistakes teach people to stop checking.  A campus model makes visible mistakes often enough that reading the agent's output becomes a habit.  That habit is the skill to learn here, and it applies to every model you'll use after this one.

In the `test_invoice.py` example, the agent told the student in English that it was going to delete the date check.  Reading that one sentence before pressing enter would have kept the bug from going out with a passing test suite.
