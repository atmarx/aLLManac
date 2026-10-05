---
title: Who can see it
description: Access control from sign-in inward — how you sign in, why your course is its own room, who can get to your work, and the paths that can send course content off institutional hardware.
audience: student
also_reaches: [faculty]
status: draft
owner: piper
tags: [access-control, sso, oidc, identity-broker, tenancy, isolation, egress-control, allowlist, faculty-duty, keycloak, globus, transparency-notice]
regimes: [ferpa]
tethered_to:
  - docs/design-walls.md#the-classroom-posture-is-opt-in
  - docs/design-walls.md#actionsalloweddomains-is-top-level--and-its-the-only-wall-around-actions
  - registrar/reconcile.py
  - registrar/render.py
  - compose.yml
---

# Who can see it

Four groups can see what you write here: you, your instructor, the people who run the servers, and anyone you or your instructor chooses to let in.  Two more can in specific cases: the company behind a hosted model, if your course uses one, and — when you file a problem report that quotes your exchange — the platform operators, who read the full report on the server.

## Signing in

You reach {{PLATFORM}} through your institution's single sign-on.  There is no separate password to create — you authenticate with campus identity.  The platform keeps an account for you, created when you are added to a course's roster: your email and name from the campus sign-in, and which courses its own roster says you are in.

The identity layer is Keycloak, and it can broker your campus identity provider — including Globus — without any of the chat software knowing the difference.

**If you come from research computing:** Globus here is only a way to log in.  In research settings Globus also moves data around, with collections and group permissions attached to real datasets.  None of that applies here.  No {{PLATFORM}} data is stored in a Globus collection, nothing transfers over Globus, and there are no Globus group permissions on your conversations.  Globus establishes who you are and plays no further part.

## Your course is its own room

Every course on this platform runs its own copy of the chat, with its own database.  Your course does not share a table with another course, or a filter, or a permission check that has to be written correctly.

In practice, someone in another course cannot see your conversations, your agents, or your uploaded files: no query crosses from one course's database to another.  Instructors of other courses cannot either.

The reasoning behind that choice — and what it costs us — is written up in [How do you keep the courses apart?](../how-we-built-it/keeping-courses-apart.md).

## Who can get to it

**You** — everything in your own account.

**Your instructor**, within your course.  The chat software gives them no screen for reading your conversations — a link you share reaches one, and so does an operator with access to the database.  They can see and manage the agents in their course.  Still assume your instructor can read what you write in their course, the same way you would assume it about anything you submit for a grade.

**The people who run the platform.**  Operators run the infrastructure — the servers, the databases, the backups.  Technical access follows from running the system.  What controls it is institutional policy and professional obligation; nothing in the software stops them.  Any platform you use works this way, including the commercial ones.  Here, the people in question work for your institution and you can find out who they are.

**Nobody in another course.**  See above.

**The model provider.**  A model running on institutional hardware adds no outside recipient.  A hosted model provider receives the prompts and other material needed to answer.  Your instructor or operator should be able to tell you which route and provider your course uses.

## What we do not do with it

The platform does not use your conversations to fine-tune models.  That promise does not automatically cover a hosted provider: its retention and training terms come from the deployment's agreement with that provider and should be published alongside the model choice.

We also do not collect keystrokes, screen activity, or attention telemetry.  What we record about your usage is [the ledger](what-we-store.md#the-ledger-which-is-the-one-that-surprises-people) — which model, how many tokens, what it cost, when — and nothing about how you sat at the keyboard.

## Sharing is available, and nothing is shared until you share it

You can share an agent you built with other people in your course, and they can share theirs with you.  Agent sharing is switched on in every course here.  Group work needs it, and the chat software's own default is off, which is the wrong setting for a classroom.

None of your work is visible by default.  An agent you build is yours until you share it, and sharing is something you do to one specific agent.  No setting exposes your work behind your back.  One path does not involve you: your instructor can nominate an agent of yours as a template for other courses, and if a platform admin exports it, its name, instructions and the names of its knowledge files are copied out of the course.

A conversation can be shared too, as a link.  Unless your instructor has turned it off for your course, you can make a link to one of your own conversations and send it to someone — a TA, a classmate reviewing your work.  The link opens only for someone signed in to your course, never for the open web, and a conversation has no link until you make one.

Before you share an agent: **a shared agent shares its knowledge files.**  Anyone who can chat with it can eventually get it to reveal what you attached, so attach things you would be comfortable handing over directly.

Either way, you can only share with people in *your* course.  Another course is a separate instance, so there is nothing to share into.

Someone chose to make sharing possible, and you choose each time you use it.

Sharing an agent, step by step, is in [Using it in a course](../user-guide.md).

## Paths that can leave the building

There are two intentional outbound routes: hosted inference and agent actions.  If the selected model is hosted, the request goes to that provider so it can answer.  The deployment's model notice should name that provider and its data terms.

Agents can be given **actions** — the ability to call an outside web service as part of answering.  An agent with actions can send whatever it is working with to whatever address it was pointed at.  That is what the feature is for: an agent that looks up live data has to send its query somewhere.

Actions are **off unless a course turns them on.**  The platform's default capability set gives courses file search, tools, and artifacts, and leaves actions out.  Turning them on is a per-course setting in the platform's course record — an instructor asks for it, and the operator who runs the platform sets it, along with the list of addresses those actions may call.  A course that leaves actions off has no *additional action route* beyond whichever model route the deployment selected.

A course that enables them can also declare a list of domains agents may call.  Know what the list does before you rely on it:

!!! warning "An allowlist narrows; it cannot close"
    If a course enables actions and declares no domains, agents can call anything on the public internet.  An empty list is no list at all, and there is no way to write "allow nothing."  The only switch that closes the path is leaving actions off.

Internal university addresses are refused by default, and **naming one in the list permits it.**  [How the list is read](for-instructors.md#on-actions-and-the-allowlist-precisely) is on the instructors' page.

If you are building an agent with actions in a course that allows them, you are the one deciding where course material goes.  Point it at something you would be comfortable naming out loud.

## If something looks wrong

Access problems, an agent you did not expect to see, a course you should not have: ask any guide in the {{PLATFORM}} chat to file a report, or tell your instructor.  The boring explanation is usually right, and if it isn't, the sooner someone looks the better.
