---
title: How we built it
description: The decisions behind this platform, written as teaching documents — what we tried, what broke, what it cost, and what the same decision looks like on Azure, AWS, or Kubernetes.
audience: builder
also_reaches: [faculty, student]
status: scaffold
owner: piper
tags: [rendered-config, tenancy, secrets-management, kubernetes, azure, aws]
---

# How we built it

<!-- SCAFFOLD.  Section landing for the show-the-work track. -->

## Why this section exists

<!-- The platform you are using is also the course material.  Students here
     learn to use language models; students here also learn to build and run
     the systems that serve them, and the second group gets the primary
     sources.

     Concrete opening, not a mission statement.  Something like: the vault in
     this stack exists because of a specific afternoon that went badly, and
     that afternoon is more useful to you than the architecture diagram. -->

## How to read these

<!-- Every page follows the same seven beats.  Naming them up front lets a
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

- [Why is there a vault?](why-a-vault.md) — secrets, escrow, and the
  afternoon that made env vars untenable
- [How do you keep the courses apart?](keeping-courses-apart.md) — tenancy by
  instance rather than by fence
- [Why the chatbot never asks who you are](identity-is-not-an-argument.md) —
  identity as context, never as a tool parameter
- [How do you protect data you cannot delete?](protecting-data-you-cant-delete.md)
  — classification, regimes, and the gap list

<!-- Queued, not written:
     - compose-now-k3s-later.md — held until the migration actually happens,
       so the page can carry a real before and after -->

## A note on the gaps

<!-- These pages name what is broken and unfinished in a production system
     serving real courses.  That is deliberate.  A case study with no open
     edges teaches that mature systems do not have any, which is the least
     useful thing an engineer can believe going into their first job. -->
