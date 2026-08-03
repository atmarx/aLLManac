---
title: How do you keep the courses apart?
description: The obvious answer is permissions inside one application. We ran a separate instance per course instead — here is what that trade actually buys and costs.
audience: builder
also_reaches: [student, faculty]
status: scaffold
owner: piper
tags: [tenancy, isolation, multi-tenant, rendered-config, librechat, mongodb, kubernetes, azure, aws]
tethered_to:
  - registrar/render.py
  - registrar/reconcile.py
  - compose.yml
---

# How do you keep the courses apart?

> *"How do you keep the courses apart?"*  *"That's the neat part — we don't."*
>
> — whiteboard, 2026

<!-- SCAFFOLD.  Epigraph is Andrew's, banked in the registrar spec's tenancy
     section.  Keep it; it does the work of three paragraphs. -->

## 1. The question

<!-- Twelve courses, hundreds of students, one platform.  Course A must not
     see course B's conversations, agents, or files.  Where does the boundary
     go? -->

## 2. The obvious answer, taken seriously

<!-- One application, tenant IDs on every row, permission checks at every
     read.  This is what most SaaS does and it is a legitimate design.
     Steelman it properly: one deployment to patch, one database to back up,
     resource efficiency, and cross-tenant features stay possible.

     Then the sentence that sets up beat 3: every one of those permission
     checks is a place where a missing WHERE clause becomes a disclosure. -->

## 3. What broke

<!-- Empirical, from the walls:
     - the application's share-group ACLs cannot be driven from the identity
       provider's groups claim (upstream issue open, sync PR died unmerged),
       so the group plumbing we would need for in-app tenancy does not reach
       the ACL system
     - share groups resolve only from local or entra sources
     - which means in-app multi-tenancy would have meant maintaining group
       membership by hand, in a second place, forever

     This is a genuinely good teaching moment and should be named as one:
     the identity system knew the answer and the application could not hear
     it.  That failure shape recurs everywhere. -->

## 4. What we did, and the bill

<!-- One LibreChat instance per course.  Separate container, separate
     database, separate hostname.  Isolation by construction — there is no
     shared room to partition, so there is no query that can cross the line.

     The registrar renders each instance's config from one course record.

     The bill:
     - N containers instead of one, with the memory floor that implies
     - upgrades are a fleet operation
     - anything genuinely cross-course has to be built deliberately
     - a rendering layer now exists and is itself a thing that can break -->

## 5. What is still wrong with it

<!-- TETHERED.  Draft: per-instance overhead sets the practical course
     ceiling on one VM; fleet upgrade story; what happens to an instance
     whose course record is deleted rather than closed.  Verify against
     current state before publishing. -->

## 6. How this looks on other stacks

<!-- - **Kubernetes** — namespace per tenant with NetworkPolicies and
       ResourceQuotas is the direct analogue, and the honest note is that a
       namespace is a soft boundary: shared control plane, shared nodes.
       vcluster or a cluster per tenant is the harder line.
     - **Azure** — resource group or subscription per tenant; the boundary
       people actually rely on tends to be the subscription.
     - **AWS** — account-per-tenant with Organizations, which is the same
       instinct at a different granularity.

     The invariant: isolation you get from *structure* survives a coding
     mistake, and isolation you get from *checks* does not.  Cost scales the
     other way.  That trade is the whole subject. -->

## 7. Try it yourself

<!-- Sign in to two courses if you are in two.  Observe there is no view that
     shows both.  Then look at a rendered per-course config and find the one
     line that makes the instance believe it is alone. -->
