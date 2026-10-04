---
title: How do you keep the courses apart?
description: The obvious answer is permissions inside one application.  We ran a separate instance per course instead — what that trade buys, what it costs, and the one shared room we did not notice we had kept.
audience: builder
also_reaches: [student, faculty]
status: draft
owner: piper
tags: [tenancy, isolation, multi-tenant, rendered-config, librechat, mongodb, access-control, chokepoint]
tethered_to:
  - registrar/render.py
  - registrar/reconcile.py
  - compose.yml
  - docs/design-walls.md#rag_api-fails-open-without-jwt_secret-2026-09-12
  - docs/registrar-spec.md
---

# How do you keep the courses apart?

> *"How do you keep the courses apart?"*  *"That's the neat part — we don't."*
>
> — whiteboard, 2026

## The question

A dozen courses, a few hundred students, one platform.  Course A must not see course B's conversations, its agents, or its uploaded files.

That is the entire requirement, and it reads like a permissions problem.  It isn't one.

## The obvious answer, taken seriously

One application.  A tenant column on every row.  A permission check at every read.

This is what most software does, and it deserves better than a strawman.  There is one deployment to patch and one database to back up.  Resource use is efficient in a way a per-tenant design will never match.  And cross-tenant features stay cheap: nothing is apart, so a report spanning every course is a query with one fewer condition on it.

What decides the argument is that in this design **every read is a place where the boundary has to be re-established** — correctly, by whoever wrote that line, on a day when they were thinking about something else.  The isolation is the sum of every check anybody remembered, and it is exactly as good as the least careful one.

The failure mode makes that worse.  A missing condition does not make the feature wrong in a way a test would catch.  The page renders.  The query returns rows.  It returns somebody else's rows, and nothing anywhere reports an error.

## What broke

We did not reason our way out of the shared design.  We tried to build it and hit a wall.

Sharing an agent with a class means putting people in a group, and the identity system already knows those groups — the roster built them.  But **LibreChat's share-groups resolve only from its own local source or from Entra.**  The Keycloak `groups` claim arrives in the token and goes nowhere: the ACL system cannot see it.  Upstream [#10006](https://github.com/LibreChat-AI/LibreChat/issues/10006) is open, and the sync PR that would fix it ([#13008](https://github.com/LibreChat-AI/LibreChat/pull/13008)) is open but unmerged.

So a shared instance would have meant maintaining every course's membership by hand, in a second place, forever — with the authoritative copy in the identity provider, unreadable.

That shape recurs, and it is rarely the part anyone plans for: the identity system knew the answer and the application could not hear it.  Neither side would call it their bug.

## What we did, and the bill

**Course equals instance.**  Each course gets its own LibreChat container, its own Mongo database, its own search index, its own admin panel, and its own hostname.  The registrar renders all of it from one course record.

The design is a shared control plane and a per-course data plane.

| Plane | What lives there | How many |
|---|---|---|
| Control — never fragments | Keycloak, LiteLLM and the ledger, OpenBao, the registrar, usage-mcp, the Caddy edge, the Mongo server | one each |
| Data — per course | LibreChat, its database inside that Mongo server, its search index, its document store, its admin panel | one per course |

What that buys is the absence of a check.  No query the chat software makes crosses courses.  Each instance is only ever told the name of its own database, so there is no shared table to write that query against.  Nobody has to remember the boundary.

Some things follow for free.  An instance has only its own course's credentials — its gateway key, its sign-in client, its encryption pair, its search and document-store secrets — so cross-course access through any of those is ruled out structurally, with no visibility toggle involved.  Each course's instructors are administrators of their own course and have no credential for anyone else's.

**One credential is missing from that list, and it matters.**  The database server asks for none.  Every course's database sits in one Mongo server, and an instance finds its own by name, with no password.  So the chat software never crosses — but anything that gets code running on the internal network could open every course's database, and the platform's own tools are built to read across them (the census counts what is in each course; the export fetches your own work from any of them).  The blast radius of a leaked *secret* is one course.  The blast radius of a compromised *container* is, today, every course's chat history.

The bill:

- **Five containers per course**, not one — chat, search, admin panel, and a document service with its own database.  Only the embedding model's files are shared, because those are identical for everybody and large.
- **Upgrades are a fleet operation.**  A LibreChat CVE means rolling N containers.  The same pinned image and rendered config make that one loop instead of N snowflakes, but it is still N.
- **Anything cross-course has to be built for the purpose.**  That is the cost of the thing that makes it safe.
- **A rendering layer now exists**, and it is itself a thing that can break.

The rendering layer is the cost that matters most.  We did not remove complexity; we moved it somewhere we can see it: templates in git, rendered by the registrar into files on the box, rolled by one loop.  That is a better place for it.  It is not nowhere.

## What is still wrong with it

Here the epigraph stops being a joke.

For most of this platform's life, one room was still shared, and it was the one for files.  Agent knowledge files were not in the per-course instance.  They went to a single document service and a single vector database that the entire fleet used — so every course's uploaded documents sat in one store whose boundary was an identity read out of a token, compared against a row.  A permission check.  Exactly the design beat 2 argues against, sitting inside the platform that argues it.

Nobody decided that.  It arrived as one service in the box, and nobody made it per-course; the question we were answering was about conversations.

The design document knew.  The tenancy decision, written in July, contained the line *"pgvector/RAG likely shared (verify file-id isolation)"* — inside a parenthesis, as an aside, in a document that was otherwise right about everything.  It was true when it was written and it stayed true, and nobody verified it.  If you take one operational habit from this essay, take that one: **the caveats you write in parentheses are the ones that outlive you.**

It came due twice in one week, and nobody went looking either time.

First the store turned out to be readable by anything on the internal network.  The document service treats a missing secret as *no authentication configured*, not as a reason to refuse to start.  One warning line in its log, which reads like a note about an optional feature.  Found by measurement, closed the same day.

Then — while someone was checking a claim on *this page* — it turned out each course signs its requests with a secret of its own that the shared service did not have.  Nothing was leaking; every call was being rejected.  Knowledge files had never worked on any course instance, and the health check does not take the same path as real requests, so every course booted announcing the document service was up and then refused every real call.  Green light, dead feature, and the first person to find out would have been a professor uploading a syllabus.

The fix was to stop having the shared room.  Each course now gets its own document service and its own vector database, with its own secret and its own volume, beside its own chat and search — only the embedding model's files are shared, and those are the same bytes for everyone.  The bill went from three containers per course to five.

Precisely: inside one course the store is still a permission check.  Between courses it is now a container wall.  Nothing about how the document service decides who may read a file has changed — it still reads an identity out of a request and compares it.  A mistake in that logic can now only expose the one course whose documents are in that container.  Buying structure doesn't eliminate checks.  It caps what a wrong one can cost.

The lesson isn't *"instance-per-course wins."*

**Structural isolation has to be kept up across every component, and the place it breaks is never the component you were thinking about.**  We got it right for conversations and agents — those were the subject of the question.  We got a permission check for files — for free, without a decision, from a dependency that came that way.  It survived a design review, a full end-to-end provision, and months of running, and what finally turned it up was somebody verifying a sentence in a documentation page.

Two gaps remain: the database server that asks for no password, and the cost — five containers per course is a real ceiling on one box, and we will meet it before we meet any of the others.

## Try it yourself

If you are in two courses, sign in to both.  No view shows you both sets of conversations — and there is no setting that would, because there is no query that could.

Then notice the contrast.  **Your usage tools cross courses by design.**  Ask about your own usage and the answer spans every course you are in: it reads the ledger by your email address, and the ledger is control plane.  Separation is a choice made per surface.

For the last step, open `registrar/render.py` — the template every course's configuration is rendered from — and find the line that gives an instance its own database.  It is the Mongo URI, and the course's name is the last thing in it.

One line.  That is the wall.  And notice what is not in it: a username or a password.  That is the gap two sections up.

Skip the rendered `librechat.yaml`, the tempting place to look.  Several lines differ per course there — the name, the model, the context size — and the one that sounds like a boundary is a header stamped on outgoing tool calls.  That is scoping.  Isolation is the Mongo line.  Telling those two apart on sight is most of the skill.
