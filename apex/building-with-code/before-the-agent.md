---
title: What has to be in place before an agent touches your code?
description: "Version control, tests you trust, and one command that deploys the same way every time.  They matter more to working with an agent than the choice of model or harness, and without them you pay twice: once in tokens checking things by hand, and again digging through logs for what the code used to say."
audience: student
also_reaches: [faculty, builder]
status: draft
owner: piper
tags: [agentic-coding, harness, version-control, automated-testing, ci-cd, deployment, accountability]
tethered_to:
  - docs/ci.md
  - justfile
---

# Before the agent

Something broke after the agent's third session, and the question was simple: what did that function say yesterday?  The answer existed in exactly one place, the terminal transcript of a session two days gone.  So the evening went to scrolling, searching, and asking a model to reconstruct its own earlier output from a log.  It got it mostly right, and nobody could say which parts weren't.

With version control, finding yesterday's version of the function takes `git log` and one more command.  Set up version control first.  **Version control, tests and a deployment pipeline matter more to working with an agent than any choice of model or harness.**  The research on [choosing a harness](choosing-a-harness.md) is about which pairing scores best on a benchmark, and those benchmarks mostly hand the agent a prepared repository and score its work with tests.  The benchmarks assume the repository and the tests exist.  In your own work, they exist only if you create them.

## Why this comes first

A coding agent changes a lot of things quickly, and it will be wrong some of the time.  Whether a wrong change is cheap or expensive to fix depends on what you have in place:

- **Without version control**, you can't see exactly what it changed, and you can't undo it.  You're left reading logs and transcripts to reconstruct what the code used to say.
- **Without tests**, the only way to know whether it worked is to check by hand, or to ask the agent to check, which means more steps, more file reads, and more tokens.  In a harness every one of those reads [is re-sent on every later step](harnesses.md#the-loop-and-why-it-spends).  A test suite answers in a few lines of pass and fail.
- **Without a pipeline**, deploying is a sequence of steps someone remembers, and an agent asked to deploy will improvise that sequence differently each time.

Version control, tests and pipelines are not new with agents.  Software engineering developed them for *people* who change code quickly and are wrong some of the time.  With an agent, the cost of skipping them shows up sooner.

## Scale it to the work

Homework doesn't need a deployment pipeline.  The principle is the same at every size: **before an agent touches your work, have a way back and a way to check.**  How much machinery that takes depends on what you're building.

| What you're working on | What to have first |
|---|---|
| **Homework in a notebook** | A copy you can go back to, and the check cells you were given |
| **A script or a small project** | Git, and a test for what you're about to change |
| **Something other people use or run** | Git, tests, one command to deploy, and CI to run it |

In a notebook, the way back is a copy.  Before you let an assistant or an agent rewrite cells, duplicate the notebook from the file browser.  Jupyter's own checkpoint is not a substitute: it stores one earlier version, and each save can replace it, so it covers the last few minutes and keeps no history.  You can keep notebooks in git too, if your hub has a terminal.  Their diffs are noisy (a notebook is JSON, outputs included), so clear the outputs before you commit.

In a notebook, the way to check is the cells that check you.  If your course gives you test or autograder cells, those are your tests.  Run them yourself, and treat an agent's edit to one of them the way you'd treat an edit to a test anywhere else ([Supervising an agent](supervising-an-agent.md) has the story).

Git, tests and a pipeline are for the second and third rows: scripts, small projects, and anything other people use or run.  Once your work is more than one notebook, learn version control.  It's the first thing you'll be asked about on any team that ships software.

## Version control: git, at the minimum that matters

If you've never used git, the commands here are enough to start.  Your repositories can go on your institution's hosted version control system (e.g. GitHub, GitLab, Forgejo, Azure DevOps) or a free personal GitHub account.  Keep coursework private unless your instructor says otherwise.  Anyone, including other students, can copy solutions from a public repository.  Run this in your project folder:

```bash
git init                          # once per project
git add -A
git commit -m "before the agent"  # a checkpoint you can always return to
```

Then, every time you hand the agent a task:

```bash
git switch -c agent/fix-date-check   # a branch for this attempt
# ... let the agent work ...
git status                           # which files did it touch?
git diff                             # exactly what changed, line by line
```

Then, depending on what you find:

```bash
git add -A && git commit -m "fix the date check"   # keep it
git stash -u          # not sure — set it all aside; `git stash pop` brings it back
git revert <commit>   # undo a commit you already kept, as a new commit
```

To throw a whole attempt away, set aside or commit what's on the branch first, then `git switch main` and `git branch -D agent/fix-date-check`.  If you switch branches with uncommitted changes, git brings those changes along to the new branch, so nothing is thrown away.

Git habits that matter when you work with an agent:

- **Commit before every agent run.**  Then `git diff` shows the agent's work and nothing else, and the checkpoint is one command away.
- **Small commits, with messages that say why.**  A month from now, `git log` is the only record of why something changed that doesn't depend on a session transcript.
- **Never commit your key.**  Put `.env` (or wherever your key is stored) in `.gitignore` before the first commit.  A key in git history stays leaked after you delete the file.  If it happened, [rotate it](your-key.md#replacing-it).

## Tests: checks you don't have to redo by hand

A test is a check you wrote once and can run forever.  It turns "does it still work?" from an afternoon into a command, and it gives the agent a short, unambiguous answer instead of a reason to go read more files.

- **Write or read the tests that matter yourself.**  Tests define what "working" means.  If an agent writes both the code and the tests, nothing independent checks its work.
- **Run them yourself, after the agent says it's done.**  An agent that ran them may also have edited them ([the story on Supervising an agent](supervising-an-agent.md)).  `git diff` on the test files tells you in seconds.
- **Start small.**  One test for the thing you're about to change is worth more than a plan to write a suite later.

## A pipeline: one command, the same way every time

A pipeline is the deployment written down as code, so it happens the same way every time, whoever or whatever starts it.  At its smallest it's a script or a `Makefile` target.  At its fullest, a CI system runs that same command on every push.

Once deploying is one command, an agent doesn't improvise it, you don't spend tokens walking it through the steps, and **a rollback is a revert plus the same command.**

{{PLATFORM}} itself deploys with one command.  All of its deployment logic is in one `justfile`.  Its CI pipeline is three lines: connect to the server, sync, run `just deploy`.  Every change, by a person or an agent, is a commit with a reason.  When a fix turns out to have its own bug, the next commit fixes the fix, and the history shows both.  The operators' version is in the repository.

## The order

If you're setting up to work with an agent, do it in this order:

1. **Git**, with a first commit and your key in `.gitignore`.
2. **A test** for the thing you're about to change.
3. **One command** that runs the tests, and one that deploys, if you deploy.  For notebook homework, a copy of the notebook and the check cells you were given are the whole list.
4. *Then* a [harness](harnesses.md), and a [model](choosing-a-harness.md).

People spend the most time choosing the harness and model, and that choice matters least.  A good model in a folder with no git and no tests can still make changes quickly that you can't see or undo.  A modest model in a repository with tests and a pipeline is something you can [supervise](supervising-an-agent.md).

In the opening example, yesterday's version of the function existed only in a terminal transcript.  With git, it would have been in the history, one command away.
