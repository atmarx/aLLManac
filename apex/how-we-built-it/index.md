---
title: "How we built it"
description: "The decisions behind this platform, written as teaching documents: what we tried, what broke, what it cost, and what is still wrong with it."
audience: builder
also_reaches: [faculty, student]
status: draft
owner: piper
tags: [rendered-config, tenancy, secrets-management, isolation, accountability]
---

# How we built it

## Why this section exists

The platform you are signed in to is also course material.

This platform runs a vault, an extra service whose only job is storing secrets.  The vault was added to solve a specific problem, and the story of that problem teaches more than the architecture diagram does.  Stories like that are usually left out of documentation.  The How we built it pages record them.

Students here learn to use language models, and some also learn to build and run the systems that serve them.  For that second group, these pages are the primary sources, with the mistakes left in.

<!-- ORIGINAL BRIEF: The platform you are using is also the course material.  Students here
     learn to use language models; students here also learn to build and run
     the systems that serve them, and the second group gets the primary
     sources.

     Concrete opening, not a mission statement.  Something like: the vault in
     this stack exists because of a specific afternoon that went badly, and
     that afternoon is more useful to you than the architecture diagram. -->

## How to read these

Every How we built it page follows the same six beats (sections) in the same order, so you can skip to the one you need.  Most working engineers want beat 5.

1. **The question**, as someone would ask it
2. **The obvious answer, taken seriously**: the strongest case for the usual design, which is often a reasonable one
3. **What broke**
4. **What we did, and the bill**: the design we chose, with its costs listed
5. **What is still wrong with it**
6. **Try it yourself**

Beat 5 is kept up to date against the running system.  When we fix an open problem, the page changes with it.  **If a beat 5 describes a problem that has clearly been fixed, that is a documentation bug.  Please report it.**

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

- [How do you keep the courses apart?](keeping-courses-apart.md): tenancy by giving each course its own instance of the chat software, instead of one shared application with permission checks.
- [Why is there a vault?](why-a-vault.md): secrets, escrow, and what changes when the credentials are ones you mint.
- [Why the chatbot never asks who you are](identity-is-not-an-argument.md): the user's identity comes with the request from the signed-in session, never from a tool parameter the model fills in.
- [How do you protect data you cannot delete?](protecting-data-you-cant-delete.md): data classification, legal regimes, and the list of open gaps.

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
       verify a guardrail is actually doing its job.  Offered by the
       registrar author; get the citable detail from design-walls.md. -->

## A note on the gaps

The How we built it pages name what is broken and unfinished in a system that serves real courses.

A case study with no open problems suggests that mature systems have none, and an engineer starting a first job is badly served by that belief.  Every How we built it page closes its case with the problems we have not solved yet.

<!-- ORIGINAL BRIEF: These pages name what is broken and unfinished in a production system
     serving real courses.  That is deliberate.  A case study with no open
     edges teaches that mature systems do not have any, which is the least
     useful thing an engineer can believe going into their first job. -->
