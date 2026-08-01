---
title: Why is there a vault?
description: Every service needs credentials. We started with environment variables, hit the limits, and ended up running OpenBao — including what that cost.
audience: builder
also_reaches: [student]
status: scaffold
owner: piper
tags: [secrets-management, escrow, openbao, key-rotation, encryption-at-rest, azure, aws, kubernetes]
tethered_to:
  - openbao/
  - compose.yml
  - docs/design-walls.md
---

# Why is there a vault?

<!-- SCAFFOLD.  Beats per docs/pedagogy-authoring.md. -->

## 1. The question

<!-- Frame it as a reader would: there is a whole extra service here whose
     only job is holding passwords.  The .env file worked.  Why the ceremony? -->

## 2. The obvious answer, taken seriously

<!-- Environment variables, steelmanned properly.  They are simple, every
     runtime supports them, they keep secrets out of the image, and for a
     single-operator deployment they are genuinely adequate.  Say so.

     A reader who has shipped things with .env files should recognize their
     own reasoning here and feel respected by it. -->

## 3. What broke

<!-- The specifics, which is where this earns its keep:
     - per-student API keys are minted and revoked continuously; a file
       rewritten on every roster change is a different problem than a file
       written once
     - custody: who was issued which key, when, and does that survive
       un-enrollment
     - rotation on a shared secret means coordinating every consumer at once
     - the CREDS_KEY/CREDS_IV pinning trap — restore a database backup with
       a different pair and every stored credential decrypts to garbage

     Include the container scar, because it is the honest cost of the fix:
     OpenBao rafts into /openbao/file or lands root-owned and crash-loops.
     And the mount rule that came out of it — never bind-mount a single file
     that gets rewritten, because atomic tmp-and-rename breaks twice over it. -->

## 4. What we did, and the bill

<!-- OpenBao as escrow: versioned key custody, minted per student, history
     retained through un-enrollment.

     The bill, stated without flinching:
     - another stateful service to run, back up, and unseal
     - unseal is an operational event, which means a reboot is not
       self-healing
     - one more thing that can be the reason the platform is down
     - the operator has to understand a second security model -->

## 5. What is still wrong with it

<!-- TETHERED — update in the same commit that fixes any of it.
     Draft from current state; verify before publishing:
     - unseal handling and what happens on unattended reboot
     - master key custody in the current phase
     - snapshot cadence for bao-data -->

## 6. How this looks on other stacks

<!-- The transfer beat — most readers will never run OpenBao.

     - **Azure** — Key Vault, with managed identity so the app never holds a
       bootstrap credential.  Compare: the unseal problem largely disappears
       and is replaced by a cloud IAM dependency.
     - **AWS** — Secrets Manager or Parameter Store with KMS, IAM roles for
       service access.  Rotation is a managed lambda rather than your code.
     - **Kubernetes** — native Secrets are base64, not encryption; the real
       patterns are External Secrets Operator or CSI driver mounting from a
       backing store, or Vault/OpenBao with Kubernetes auth.

     Close on the invariant that survives all four: the application should
     receive a short-lived credential it did not have to store, and someone
     should be able to answer who held which secret and when. -->

## 7. Try it yourself

<!-- Something runnable on the platform they are signed into, or a small
     local exercise: mint a key, look at its version history, revoke it, and
     observe what remains.  Written so the reader sees custody rather than
     reading about it. -->
