---
title: What we store
description: The actual inventory — conversations, agents, usage records, and identity — listed by the system that holds each one.
audience: student
also_reaches: [faculty, builder]
status: scaffold
owner: piper
tags: [data-inventory, education-record, pii, mongodb, litellm, keycloak, openbao, ferpa]
regimes: [ferpa]
tethered_to:
  - docs/admin-guide.md#backups
  - compose.yml
---

# What we store

<!-- SCAFFOLD.

     SOURCE: the admin guide's backup table is already a data inventory —
     it enumerates every named volume and what it holds.  Rewrite it for a
     student reader.  Do not link students to the admin guide itself
     (operator pile, out of the corpus). -->

## The inventory

<!-- Table, student-legible.  Columns: what it is / where it lives / tied to
     your identity?  Drafted from the volume map:

     - Conversations and agents you build → your course's own database
       (one database per course inside mongo-data).  Tied to you.
     - Agent knowledge-file embeddings → pgvector.  Tied to the agent, and
       the files you uploaded to it.
     - Usage records — which model, how many tokens, what it cost, when →
       the ledger (litellm-db).  Tied to your email.
     - Your account, roles, course membership → identity (keycloak-db).
     - Search index → derived, rebuilds itself, holds nothing original.
     - API keys minted for you → escrow (OpenBao), versioned. -->

## The one that surprises people

<!-- The ledger.  Usage records are not conversation content, and they still
     describe behavior in detail: which model you chose, how much you used
     it, at what hour, across the term, keyed to your email address.

     Say why the email is the key rather than an opaque ID — attribution has
     to survive a roster change and land on a real person for billing.  That
     is a deliberate trade and students should know it was made. -->

## What we do not store

<!-- Concrete and checkable:
     - conversation content is not in the ledger
     - nothing goes to a third-party model provider unless the course uses a
       hosted endpoint — name where the course can find out which
     - no keystroke, screen, or attention telemetry
     Only claim what the code actually does. -->

## For builders

<!-- Short beat, tagged for the build audience: "data inventory" is the
     first artifact of every compliance regime, and this page is one.  You
     cannot classify what you have not enumerated.  Point at
     how-we-built-it/protecting-data-you-cant-delete.md. -->
