---
title: Who can see it
description: Access control from the front door inward — how you sign in, why your course is its own room, who genuinely has reach, and the one path that sends course content off institutional hardware.
audience: student
also_reaches: [faculty]
status: draft
owner: piper
tags: [access-control, sso, oidc, identity-broker, tenancy, isolation, egress-control, allowlist, faculty-duty, keycloak, globus, transparency-notice]
regimes: [ferpa]
tethered_to:
  - docs/design-walls.md#the-classroom-posture
  - registrar/reconcile.py
  - registrar/render.py
  - compose.yml
---

# Who can see it

Four groups can reach what you write here: you, your instructor, the people
who run the servers, and anyone your instructor deliberately lets in.  That
list is short on purpose, and this page walks it from the front door inward.

## Signing in

You reach the aLLManac through your institution's single sign-on.  There is no
separate password to create and no account for us to lose — you authenticate
with campus identity, and the platform learns only that you are you and which
courses you belong to.

The identity layer is Keycloak, and it can broker your campus identity
provider — including Globus — without any of the chat software knowing the
difference.

**One thing worth clearing up if you come from research computing:** Globus
here is only a way to log in.  In research settings Globus also moves data
around, with collections and group permissions attached to real datasets.
None of that applies here.  No aLLManac data lives in a Globus collection,
nothing transfers over Globus, and there are no Globus group permissions on
your conversations.  Globus establishes who you are, then steps out of the
way.

## Your course is its own room

Every course on this platform runs its own copy of the chat, with its own
database.  Your course does not share a table with another course, or a
filter, or a permission check that has to be written correctly.  There is no
shared room to partition.

The practical consequence: someone in another course cannot see your
conversations, your agents, or your uploaded files, because there is no query
that reaches across.  Instructors of other courses cannot either.

The reasoning behind that choice — and what it costs us — is written up in
[How do you keep the courses apart?](../how-we-built-it/keeping-courses-apart.md).

## Who has reach, honestly

**You** — everything in your own account.

**Your instructor**, within your course.  They can see the conversations and
agents in the course instance they run.  Assume your instructor can read what
you write in their course, the same way you would assume it about anything
you submit for a grade.

**The people who run the platform.**  Operators hold the infrastructure —
the servers, the databases, the backups.  Technical access follows from
running the system, and the control on it is institutional policy and
professional obligation rather than a barrier in the software.  Any platform
you use works this way, including the commercial ones; the difference here is
that the people in question work for your institution and are reachable.

**Nobody in another course.**  See above.

**No outside company.**  The models that answer you run on institutional
hardware.  Where a course uses a hosted model instead, that is a property of
the course and your instructor can tell you which one.

## What we do not do with it

We do not train models on your conversations.  Nothing you write becomes
training data for anything — not for our models, not for a vendor's.  This is
straightforward for us to promise because the models we serve run on our own
machines and we do not fine-tune them on course traffic.

We also do not collect keystrokes, screen activity, or attention telemetry.
What we record about your usage is [the ledger](what-we-store.md#the-one-that-surprises-people)
— which model, how many tokens, what it cost, when — and nothing about how
you sat at the keyboard.

## Sharing starts off

By default, students cannot share agents with each other.  Agent sharing and
the people-picker are both switched off in every course when it is created,
which means the custom GPT you build is yours until someone changes that
setting.

Your instructor can turn sharing on for a course — group projects need it,
and Part 2 of the course guide covers how it works once they do.  Worth
knowing that this is a decision someone made rather than a default that
happened to you.

<!-- LINK PENDING: the course guide is reader-facing and still sits in
     docs/user-guide.md.  It belongs in the "public + taught" pile and moves
     into apex/ with the boundary work; link it properly then.  A relative
     link out of the apex tree resolves on disk and dies in the built
     site. -->

## The path that leaves the building

There is one way for course content to leave institutional hardware, and it is
worth understanding because it is a feature rather than a leak.

Agents can be given **actions** — the ability to call an outside web service
as part of answering.  An agent with actions can send whatever it is working
with to whatever address it was pointed at.  That is the entire point of the
feature, and it is genuinely useful: an agent that looks up live data has to
reach something.

Actions are **off unless a course turns them on.**  The platform's default
capability set gives courses file search, tools, and artifacts, and
deliberately leaves actions out.  Enabling them is a per-course decision your
instructor makes, and that decision is the real protection — a course that
never turns actions on has no path out at all.

A course that does enable them can also declare a list of domains agents are
allowed to reach.  Worth understanding what that list does and does not do:

!!! warning "An allowlist narrows; it cannot close"
    If a course enables actions and declares no domains, agents can reach the
    entire public internet.  An empty list is not a closed door — it is no
    list.  The platform blocks private and internal addresses either way, and
    there is no way to write "allow nothing."  The switch that actually
    closes the path is leaving actions off.

If you are building an agent with actions in a course that allows them, you
are the one deciding where course material goes.  Point it at something you
would be comfortable naming out loud.

## If something looks wrong

Access problems, an agent you did not expect to see, a course you should not
have: tell your instructor, and they can reach the platform operators.  The
uninteresting explanation is usually right, and the interesting one is worth
finding quickly.
