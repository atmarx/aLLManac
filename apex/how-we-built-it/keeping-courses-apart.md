---
title: How do you keep the courses apart?
description: The obvious answer is permissions inside one application. We ran a separate instance per course instead — what that trade buys, what it costs, and the one shared room we did not notice we had kept.
audience: builder
also_reaches: [student, faculty]
status: draft
owner: piper
tags: [tenancy, isolation, multi-tenant, rendered-config, librechat, mongodb, access-control, chokepoint]
tethered_to:
  - registrar/render.py
  - registrar/reconcile.py
  - compose.yml
  - docs/design-walls.md#rag_api-fails-open-without-jwt_secret-and-it-is-shared-by-the-whole-fleet-2026-09-12
  - docs/registrar-spec.md
---

# How do you keep the courses apart?

> *"How do you keep the courses apart?"*  *"That's the neat part — we don't."*
>
> — whiteboard, 2026

## The question

A dozen courses, a few hundred students, one platform.  Course A must not see course B's conversations, its agents, or its uploaded files.

That is the entire requirement, and it reads like a permissions problem.  Most of this page is about why it is not one.

## The obvious answer, taken seriously

One application.  A tenant column on every row.  A permission check at every read.

This is what most software does, and it deserves better than a strawman, because it is genuinely good at several things.  There is one deployment to patch and one database to back up.  Resource use is efficient in a way a per-tenant design will never match.  And cross-tenant features stay cheap, because nothing is really apart — a report spanning every course is just a query with one fewer condition on it.

Then there is the part that decides the argument.

In that design, **every read is a place where the boundary has to be re-established** — correctly, by whoever wrote that line, on a day when they were thinking about something else.  The isolation is not a property the system has.  It is the sum of every check anybody remembered, and it holds exactly as well as the least careful one.

That matters more than it sounds, because of what the failure looks like.  A missing condition does not make the feature wrong in a way a test would catch.  The page renders.  The query returns rows.  It returns somebody else's rows, and nothing anywhere reports an error.

## What broke

We did not reason our way out of the shared design.  We tried to build it and hit a wall.

Sharing an agent with a class means putting people in a group, and the identity system already knows those groups — the roster built them.  But **LibreChat's share-groups resolve only from its own local source or from Entra.**  The Keycloak `groups` claim arrives in the token and reaches nothing: the ACL system cannot see it.  Upstream [#10006](https://github.com/danny-avila/LibreChat/issues/10006) is open, and the sync PR that would have fixed it died unmerged.

So a shared instance would have meant maintaining every course's membership **by hand, in a second place, forever** — with the authoritative copy sitting right there in the identity provider, unreadable.

It is worth naming that shape, because it recurs everywhere and it is rarely the part anyone plans for: **the identity system knew the answer and the application could not hear it.**  Not a missing feature, not a bug either side would call theirs.  Two correct systems with no seam between them.

## What we did, and the bill

**Course equals instance.**  Each course gets its own LibreChat container, its own Mongo database, its own search index, its own admin panel, and its own hostname.  The registrar renders all of it from one course record.

The load-bearing sentence is *shared control plane, per-course data plane.*

| Plane | What lives there | How many |
|---|---|---|
| Control — never fragments | Keycloak, LiteLLM and the ledger, OpenBao, the registrar, usage-mcp, the Caddy edge | one each |
| Data — per course | LibreChat, its Mongo database, its search index, its admin panel | one per course |

What that buys is not a stronger check.  It is the **absence of a check**.  There is no query that reaches across courses on the chat plane, because there is no shared table to write that query against.  Nobody has to remember the boundary, which means nobody can forget it.

A few things fix themselves on the way.  An instance only contains its own course's credential, so cross-course access dies structurally rather than by a visibility toggle.  Each course's instructors are administrators of their own house and hold no key to anyone else's.  And the blast radius of a hostile agent tool or a leaked secret is one course, not the campus.

The bill, stated plainly:

- **Three containers per course**, not one — chat, search, panel — at roughly 500–600MB all in.  Twenty courses is 12–15GB on the app box.
- **Upgrades are a fleet operation.**  A LibreChat CVE means rolling N containers.  The same pinned image and rendered config make that one loop rather than N snowflakes, but it is still N.
- **Anything genuinely cross-course has to be built on purpose.**  That is the cost of the thing that makes it safe.
- **A rendering layer now exists**, and it is itself a thing that can break.

That last one is the honest one.  We did not remove complexity; we moved it somewhere we can see it, into a file the registrar writes, in git, rolled by one loop.  That is a better place for it.  It is not nowhere.

## What is still wrong with it

Here is where the epigraph stops being a joke.

**One room is still shared, and it is the one holding the files.**  Agent knowledge files do not live in the per-course instance — they go to a single `rag_api` and a single vector database that the entire fleet uses.  Every course's uploaded documents are in one store, and the boundary there is an auth token rather than a container wall.

We know it is a real boundary and not a theoretical one because it has already failed once.  On **2026-09-12**, a probe run from the registrar's container — a service with no business reading the vector store and holding no credential for it — asked for a document by id and got back thirty-eight kilobytes of content, with no authorization header, and a `200`.  The RAG service treats a missing secret as *no authentication configured* rather than as a reason to refuse to start, so it had been running wide open behind a single warning line at boot that reads like a note about an optional feature.  It is written up with the measurement in the operators' own notes, and it was closed the same day by passing the secret explicitly.

Two things about it are worth more than the fix.

**The design document knew.**  The tenancy decision, written in July, contains the line *"pgvector/RAG likely shared (verify file-id isolation)"* — inside a parenthesis, as an aside, in a document that was otherwise right about everything.  It was true when it was written and it stayed true, and nobody verified it, because parentheses do not get done.  If you take one operational habit from this page, take that one: the caveats you write inside brackets are the ones that outlive you.

**And it is not closed yet.**  As of **2026-09-18** there is an open question underneath the fix.  The shared service holds the platform's root secret, while every rendered course instance mints a fresh one of its own — so a course instance may be signing its requests with a key the shared service does not have.  Either knowledge files quietly fail for course instances, or the check is not running on that path at all.  We do not know which yet.  It is with the people who operate the platform, and this paragraph changes when they answer.

We are leaving the question here rather than waiting to publish a cleaner page, because a gap you can read about is worth more than one you cannot.

The general form is the part that travels: **structural isolation is a posture you have to hold across every component, and the place it breaks is never the component you were thinking about.**  We got it right for conversations and agents, because those were the subject.  We inherited the shared thing for free, without a decision, because it arrived that way in the box.

## Try it yourself

If you are in two courses, sign in to both.  No view shows you both sets of conversations — and there is no setting that would, because there is no query that could.

Then notice the contrast, which teaches the idea better than the clean claim does.  **Your usage tools cross courses on purpose.**  Ask about your own usage and the answer spans every course you are in, because it reads the ledger by your email address, and the ledger is control plane.  Separation here is a choice made per surface, not a property of the building.

For the last step, open `fleet/fleet.yml` and find the line that gives an instance its own database.  It is the Mongo URI, and the course's name is the last thing in it.

One line.  That is the wall.

Not the rendered `librechat.yaml`, which is the tempting place to look: the line that differs per course there is a header stamped on outgoing tool calls, and that is scoping, not isolation.  Telling those two apart on sight is most of the skill this page is about.
