---
title: How we built it
description: The decisions behind this platform, written as teaching documents — what we tried, what broke, what it cost, and what is still wrong with it.
audience: builder
also_reaches: [faculty, student]
status: draft
owner: piper
tags: [rendered-config, tenancy, secrets-management, isolation, accountability]
---

# How we built it

<!-- SCAFFOLD, AND PARKED (2026-08-01, xram).  Hold depth on this track until
     the build settles — the registrar is still landing changes, and a
     teaching page written against a moving system is the drift this whole
     doctrine exists to prevent.  The banked prior art and the queued
     artifacts below keep their value; nothing here needs rewriting when work
     resumes, it needs finishing.

     Priority meanwhile is apex/teaching-with-ai/ — responsible use of AI in
     teaching, which does not depend on the build at all. -->

## Why this section exists

The platform you are signed in to is also course material.

There is a vault in this stack — a whole extra service whose only job is holding secrets — and it is there because of a specific afternoon that went badly, not because an architecture diagram called for one.  That afternoon is more useful to you than the diagram, and it is the kind of thing that almost never survives into documentation.  These pages are an attempt to keep it.

Students here learn to use language models.  Students here also learn to build and run the systems that serve them, and that second group gets the primary sources rather than a sanitised retelling.

<!-- ORIGINAL BRIEF: The platform you are using is also the course material.  Students here
     learn to use language models; students here also learn to build and run
     the systems that serve them, and the second group gets the primary
     sources.

     Concrete opening, not a mission statement.  Something like: the vault in
     this stack exists because of a specific afternoon that went badly, and
     that afternoon is more useful to you than the architecture diagram. -->

## How to read these

Every page follows the same six beats, so you can skip to the one you came for.  Most working engineers want beat 5.

1. **The question**, as someone would actually ask it
2. **The obvious answer, taken seriously** — steelmanned, because it is usually a reasonable design
3. **What broke**
4. **What we did, and the bill** — the costs stated plainly, not buried
5. **What is still wrong with it**
6. **Try it yourself**

Beat 5 is maintained against the running system.  When we close an open edge, the page changes with it.  **If you find a beat 5 describing a problem we have clearly fixed, that is a bug and it is worth reporting.**

<!-- ORIGINAL BRIEF, and note beat 6 (other stacks) was CUT 2026-09-18 on
     xram's call: unless a deployment detail is germane to how this platform
     operates, it does not earn the space, and that section was the one most
     likely to rot into generic cloud-architecture filler.  Six beats now.
     Pages still carrying azure/aws/kubernetes tags should lose them as they
     are written.

     Every page follows the same seven beats.  Naming them up front lets a
     reader skip to the beat they want — most working engineers want beat 5.

     1. The question, as someone would actually ask it
     2. The obvious answer, taken seriously
     3. What broke
     4. What we did, and the bill
     5. What is still wrong with it
     6. How this looks on other stacks — Azure, AWS, Kubernetes
     7. Try it yourself

     Beat 5 is maintained against the running system.  When we close an open
     edge, the page changes with it.  If you find a beat 5 describing a
     problem we have clearly fixed, that is a bug and it is worth reporting. -->

## The decisions

- [How do you keep the courses apart?](keeping-courses-apart.md) — tenancy by instance rather than by fence.  **Finished.**
- [Why is there a vault?](why-a-vault.md) — secrets, escrow, and what changes when the credentials are ones you mint.  *Being written.*
- [Why the chatbot never asks who you are](identity-is-not-an-argument.md) — identity as context, never as a tool parameter.  *Being written.*
- [How do you protect data you cannot delete?](protecting-data-you-cant-delete.md) — classification, regimes, and the gap list.  *Being written.*

<!-- Queued, not written:
     - compose-now-k3s-later.md — held until the migration actually happens,
       so the page can carry a real before and after
     - the-guardrail-that-does-nothing.md — CANDIDATE, and a strong one.
       The egress allowlist has to be declared at the config's top level,
       as a sibling of `endpoints:`.  Nested under `endpoints.agents` —
       which is where everyone puts it, because that is where the agents
       block lives — it parses cleanly, validates, and silently does
       nothing.  Found by reading the pinned image's own schema rather
       than the vendor docs.  The lesson generalizes past this stack:
       configuration that parses is not configuration that runs, and a
       security control nobody verified is a control nobody has.  Better
       than any invented example, and it comes with a second beat — how to
       verify a guardrail is actually load-bearing.  Offered by the
       registrar author; get the citable detail from design-walls.md. -->

## A note on the gaps

These pages name what is broken and unfinished in a system that serves real courses, and they do it on purpose.

A case study with no open edges teaches that mature systems do not have any — which is close to the least useful thing an engineer can believe walking into their first job.  The finished page in this section ends on a problem we have not solved.  That is the shape, not an accident of timing.

<!-- ORIGINAL BRIEF: These pages name what is broken and unfinished in a production system
     serving real courses.  That is deliberate.  A case study with no open
     edges teaches that mature systems do not have any, which is the least
     useful thing an engineer can believe going into their first job. -->
