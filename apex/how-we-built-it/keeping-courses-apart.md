---
title: How do you keep the courses apart?
description: The usual answer is permission checks inside one shared application.  We run a separate instance per course instead.  What that buys, what it costs, and the shared document store we kept without noticing.
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

## The question

The platform serves a dozen courses and a few hundred students.  Course A must not see course B's conversations, agents, or uploaded files.

Keeping courses apart looks like a permissions problem, and most software solves it that way.  This platform solves it with a separate instance for each course.

## The obvious answer, taken seriously

The usual design is one application, with a tenant column on every database row and a permission check on every read.

Most software works this way, and the shared design has real strengths.  There is one deployment to patch and one database to back up.  It uses resources more efficiently than any per-tenant design can.  Cross-tenant features are cheap: a report across every course is the same query with one fewer condition.

The weakness of the shared design is that **every read has to re-apply the course boundary**.  Whoever writes each query has to include the check correctly, even on a day they are focused on something else.  The isolation is only as good as the least careful check in the codebase.

A missing check is also hard to detect.  The feature still appears to work, so an ordinary test does not catch it: the page renders and the query returns rows.  The rows belong to another course, and nothing reports an error.

## What broke

The team did not reject the shared design on paper.  We tried to build it and hit a limit in the chat software.

Sharing an agent with a class means putting the students in a group.  The identity system (Keycloak) already has those groups, because the roster created them.  But **LibreChat's share groups come only from its own local groups or from Entra.**  The Keycloak `groups` claim arrives in the sign-in token, and LibreChat's access-control system cannot see it.  Upstream [#10006](https://github.com/LibreChat-AI/LibreChat/issues/10006) is open, and the sync PR that would fix it ([#13008](https://github.com/LibreChat-AI/LibreChat/pull/13008)) is open but unmerged.

With one shared LibreChat instance, someone would have had to maintain every course's membership by hand inside LibreChat, indefinitely, while the authoritative copy sat in the identity provider where LibreChat could not read it.

This kind of gap is common and rarely planned for: the identity system has the information, and the application cannot read it.  Neither project treats the gap as its own bug.

## What we did, and the bill

**Each course is its own instance.**  Each course gets its own LibreChat container, its own Mongo database, its own search index, its own admin panel, and its own hostname.  The registrar renders all of it from one course record.

The design has a shared control plane and a per-course data plane:

| Plane | Components | How many |
|---|---|---|
| Control (shared, never split per course) | Keycloak, LiteLLM and the ledger, OpenBao, the registrar, usage-mcp, the Caddy edge, the Mongo server | one each |
| Data (per course) | LibreChat, its database inside that Mongo server, its search index, its document store, its admin panel | one per course |

With one instance per course, the boundary between courses needs no permission check.  No query the chat software makes crosses courses.  Each instance is given only the name of its own database, so there is no shared table a cross-course query could read.  Nobody has to remember to add the boundary.

Each course instance also has only its own course's credentials: its gateway key, its sign-in client, its encryption pair, and its search and document-store secrets.  None of those credentials can be used to reach another course, and no visibility setting is involved.  Each course's instructors are administrators of their own course and have no credential for any other course.

**The database server is the exception: it requires no credential.**  Every course's database is on one Mongo server, and an instance finds its own database by name, with no password.  The chat software never reads another course's database.  But anything that gets code running on the internal network could open every course's database, and the platform's own tools are built to read across them (the census counts what is in each course, and the export fetches your own work from any of them).  A leaked *secret* exposes one course.  A compromised *container* exposes, today, every course's chat history.

The costs of one instance per course:

- **Five containers per course** instead of one: chat, search, admin panel, and a document service with its own database.  Only the embedding model's files are shared, since they are large and identical for every course.
- **Upgrades are a fleet operation.**  A LibreChat CVE means rolling out a new image to N containers.  Because every course uses the same pinned image and rendered config, the rollout is one loop with no per-course special cases.  It is still N containers.
- **Any cross-course feature has to be built specifically for it.**  The same separation that keeps courses safe makes those features extra work.
- **The platform now has a rendering layer**, and the rendering layer can break too.

The rendering layer is the largest cost.  Per-course instances do not remove complexity.  They move it into templates in git, which the registrar renders into files on the box and rolls out with one loop.  Complexity in templates is easier to see and review, but it still has to be maintained.

## What is still wrong with it

For most of this platform's life, one component was still shared across courses: the storage for agent knowledge files.  Agent knowledge files were not stored in the per-course instance.  They went to a single document service and a single vector database used by the whole fleet.  Every course's uploaded documents were in one store, and the boundary between courses was an identity read from a token and compared against a database row.  That is a permission check, the design that [The obvious answer, taken seriously](#the-obvious-answer-taken-seriously) argues against, inside the platform that argues against it.

Nobody chose the shared document store.  It came as one service in the stack, and nobody made it per-course.  The tenancy question the team was answering at the time was about conversations.

The design document had flagged the shared document store.  The tenancy decision, written in July, contained the line *"pgvector/RAG likely shared (verify file-id isolation)"* as an aside in parentheses.  The line was accurate when it was written and stayed accurate, and nobody did the verification it asked for.  **Treat every caveat in your own design notes as an open task, and verify it.**  Caveats written as asides in parentheses tend to stay unresolved the longest.

The shared document store caused two problems in one week, and both were found while people were doing something else.

First, the store turned out to be readable by anything on the internal network.  When its secret is missing, the document service starts anyway with no authentication configured, instead of refusing to start.  It logs one warning line, which reads like a note about an optional feature.  The team found the problem by measuring and closed it the same day.

Second, while someone was checking a statement in the documentation against the system, it turned out that each course signs its document requests with its own secret, and the shared service did not have those secrets.  Nothing was leaking.  Every call was being rejected.  Knowledge files had never worked on any course instance.  The health check does not use the same path as real requests, so every course reported the document service as up and then refused every real call.  The first person to notice would have been a professor uploading a syllabus.

The fix was to remove the shared document store.  Each course now gets its own document service and its own vector database, with its own secret and its own volume, next to its own chat and search.  Only the embedding model's files are shared, and those are identical for every course.  The cost went from three containers per course to five.

Inside one course, the document store still relies on a permission check.  Between courses, separate containers keep the documents apart.  The way the document service decides who may read a file has not changed: it still reads an identity from the request and compares it.  A mistake in that logic can now expose only the one course whose documents are in that container.  Separate instances do not remove permission checks, but they limit how much a wrong check can expose.

**Structural isolation has to be maintained across every component, and it tends to fail in a component nobody was thinking about.**  The platform got isolation right for conversations and agents, the subject of the original question.  Files got a permission check by default, without anyone deciding it, because the dependency shipped that way.  The shared document store survived a design review, a full end-to-end provision, and months of running.  It was found when somebody checked a sentence in a documentation page against the system.

Two gaps in course isolation remain.  The Mongo database server asks for no password.  And five containers per course puts a real limit on how many courses one box can run, and we expect to reach that limit before any other.

## Try it yourself

If you are in two courses, sign in to both.  No view shows both sets of conversations.  No setting could add one, because no query in the chat software reads across course databases.

Then compare the usage tools.  **Your usage tools do cross courses.**  Ask about your own usage and the answer covers every course you are in.  The usage tool reads the ledger by your email address, and the ledger is part of the shared control plane.  Whether data is separated by course is decided separately for each part of the platform.

Last, open `registrar/render.py`, which holds the template every course's configuration is rendered from.  Find the line that gives an instance its own database.  That line is the Mongo URI, and the course's name is at the end of it.

The Mongo URI line is the whole boundary between course databases.  It contains no username or password, which is the database-server gap described in [What we did, and the bill](#what-we-did-and-the-bill).

Don't look for the boundary in the rendered `librechat.yaml`.  Several lines there differ per course (the name, the model, the context size), and the one that sounds like a boundary is a header added to outgoing tool calls.  That header is scoping: it tells a tool which course the call came from.  Isolation is the Mongo line.  Telling scoping and isolation apart on sight is most of the skill.
