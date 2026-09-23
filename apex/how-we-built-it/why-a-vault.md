---
title: Why is there a vault?
description: Service credentials still ride in env files. The vault exists for the credentials we mint — thousands of per-student keys that need custody, versioning, and an answer to who held which key and when.
audience: builder
also_reaches: [student]
status: scaffold
owner: piper
tags: [secrets-management, escrow, openbao, key-rotation, encryption-at-rest, azure, aws, kubernetes]
tethered_to:
  - openbao/
  - compose.yml
  - docs/design-walls.md
  - docs/registrar-spec.md
  - justfile
---

# Why is there a vault?

!!! note "Being written"
    This page is not finished.  The argument and the sources are drafted, and the prose is queued behind the pages instructors need first.  What it will cover is below; in the meantime the short version is that every service here still takes its credentials from an environment file — the vault exists for the credentials the platform *mints*, thousands of per-student keys that need custody, versioning, and an answer to who held which key and when.

<!-- SCAFFOLD.  Beats per docs/pedagogy-authoring.md. -->

## 1. The question

<!-- Frame it as a reader would: there is a whole extra service here whose
     only job is holding secrets.  The .env file worked.  Why the ceremony?

     ACCURACY, and the framing has to respect it: the .env file still works
     and is still what every service uses.  Platform credentials come from
     .env (compose.yml) and each course instance's from a rendered
     fleet/<slug>.env (render.py:85-130); the registrar is OpenBao's only
     consumer.  So the vault did NOT replace environment variables, and a
     page that says it did will be corrected by anyone who opens compose.yml.
     The real question is narrower and more interesting: what changes when
     the secrets are ones you MINT, thousands of them, per student, with a
     custody question attached.  Beats 3 and 4 already say this correctly. -->

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
     - unseal is an operational event.  Every restart comes back SEALED, by
       design, and until 772eb02 (2026-09-23) only `just up`/`deploy`
       unsealed it.  The first unattended reboot (xdocker03, same day) came
       back looking healthy: all 24 containers up, chat answering on the keys
       already rendered, smoke green — and every key path shut: enrollment,
       my_key, rotation, approving a course.  The fix is a boot-time user
       unit that unseals from .env.  The beat: a vault that fails closed
       fails QUIETLY for everything that doesn't need a new secret.  Nothing
       looked down.  (Geordi, board >>01M37APDBC2FSFZSVPW711523D)
     - one more thing that can be the reason the platform is down
     - the operator has to understand a second security model -->

## 5. What is still wrong with it

<!-- TETHERED — update in the same commit that fixes any of it.
     Draft from current state; verify before publishing:
     - the unseal key sits in .env on the same disk (registrar-spec.md,
       "Honesty box" under Unattended restarts), and the boot unit reads it
       from there.  The question an IT reader asks first: then what does
       the seal protect?  A copy of the vault's storage that leaves the box
       WITHOUT .env — a stolen backup, a detached volume, a shared snapshot
       — is ciphertext.  Someone who owns the running box gets everything.
       That holds only while .env is backed up separately from bao-data,
       which admin-guide.md#backups tells operators to do; verify before
       publishing.  "Reboots without a human" was chosen over "a human holds
       the key", on purpose.  Moving the key off the box is the upgrade
       path, and its price is that every reboot waits for a person.  Write
       the vault as a decision with a price, not a feature.
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
