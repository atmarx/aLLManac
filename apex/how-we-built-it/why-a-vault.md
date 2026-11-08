---
title: "Why is there a vault?"
description: "Service credentials are still in env files.  The vault exists for the credentials we mint: a key per student, per course, that has to be readable again on request, revocable at any time, and accounted for after the student has left."
audience: builder
also_reaches: [student]
status: draft
owner: piper
tags: [secrets-management, escrow, openbao, key-rotation, audit-logging, encryption-at-rest, backup]
tethered_to:
  - openbao/
  - compose.yml
  - docs/design-walls.md
  - docs/registrar-spec.md
  - justfile
  - registrar/planes/escrow.py
  - registrar/planes/verbs.py
---

# Why is there a vault?

Open `compose.yml` and count the services.  One of them, `alm-openbao`, has no users, no web page, and nothing a student will ever see.  Its whole job is storing secrets.

Every other service in the stack still gets its secrets from an environment file.  The gateway's master key, the sign-in system's admin password, and every course's encryption pair are all in `.env` or a rendered `fleet/<slug>.env`, read at startup, as on any small deployment.

The vault did not replace environment variables.  It answers a narrower question: **what changes when the secrets are ones you mint?**

## The question

The `.env` file has worked for every service here since the first commit.  So why add a second place for secrets, one that has to be backed up, unsealed after every restart, and understood by whoever runs the box?

## The obvious answer, taken seriously

The obvious answer is to keep everything in environment files.

For most deployments, environment files are the right answer.  Every runtime reads environment variables.  They keep secrets out of the image and out of git.  The file is plain text an operator can read, back up, and diff.  For a single operator running a handful of services whose credentials change once a year, a `.env` with tight permissions is adequate.  In that setting, a vault adds work without adding much protection.

If you have shipped projects with `.env` files and they were fine, they probably were.  This platform outgrew that setting in one specific way: it mints a key for every student.

## What broke

Every student in every course gets their own API key to the gateway, for pi or opencode, a notebook, or anything that speaks the OpenAI protocol.  The registrar mints the key when the student is enrolled, and the gateway shows it exactly once, when it is created.

Because the gateway shows a key only once, the platform has to store it.  **A student has to be able to ask for their key again**: on a new laptop, a week later, or after losing the terminal it was printed in.  So the key has to be stored somewhere it can be read back.  For stored minted keys, an environment file falls short in four ways:

- **It changes constantly.**  Enrollment mints, un-enrollment revokes, rotation does both, and closing a course revokes the whole class.  A file rewritten on every roster change needs different handling than a file written once at install.
- **It has no history.**  When a student rotates a leaked key, the old one should stop working, and someone should be able to say afterward which key they held, from when to when.  A file keeps the current line and forgets the rest.
- **It has no access record.**  Anything that can read the file can read every key in it, and nothing records that it did.
- **It is all or nothing.**  A file is readable whole or not at all.  A file cannot express a permission like "this tool may read the caller's key and nobody else's."

Minting keys also caused a second failure.  A key exists in two places: the gateway, where it is used to spend, and the store where it can be read back.  A key that is live at the gateway but stored nowhere is an orphan.  It spends the course's budget, and nobody can find it to revoke it.  An early helper recipe minted keys directly at the gateway, so every key it made was an orphan.  The resulting design wall reads *mint and escrow are one transaction* (`docs/design-walls.md`), and no code path now mints a key without storing it.

## What we did, and the bill

**The platform uses OpenBao as an escrow.**  OpenBao is an open-source fork of HashiCorp Vault, and it runs as one more container.  Only two things use it: the registrar, and a backup role that can take a snapshot and read nothing.  Every other service still reads its environment file.

OpenBao stores one record per key, at a path that names the owner:

```
almanac/courses/<slug>/students/<email>    the key, when it was minted, its budget
almanac/courses/<slug>/service             the course chat's own key
```

The storage is versioned (OpenBao's key-value engine, version 2).  Versioning is the main reason the platform uses OpenBao:

- **Rotation writes a new version and keeps the old one.**  `rotate_my_key` mints the replacement *first* and writes it with a note saying which old key still needs to be revoked.  Then it revokes the old key at the gateway and writes again with the note cleared.  If a rotation is interrupted, the note shows that an old key may still be live, so two keys are never live without a record of it.
- **Un-enrolling is a soft delete.**  The key is revoked at the gateway and the record is marked deleted, but its history is kept.  The record outlasts the student's enrollment, so someone can still answer "who held which key, and when" after the term is over.
- **Ending a course** happens in two steps.  Closing it blocks every key at the gateway at once, while students still have a window to export their work.  Archiving it at the end of that window revokes each key, soft-deletes the student records, and marks the course's own record revoked instead of removing it.

The registrar logs in to OpenBao with its own role, gets a token valid for an hour, and can access `almanac/courses/*` and nothing else.  The root token is printed once, at setup, for the operator to put in a password manager.  The root token is never written to disk on the box.

The costs of running OpenBao:

- **Another stateful service** to run, back up, and understand.  An operator now needs to learn a second security model: tokens, policies, and seals.
- **OpenBao can cause outages.**  If it isn't answering, nobody can enroll, fetch a key, or rotate one.
- **OpenBao has its own pitfalls, and we hit two of them.**  First, OpenBao's storage has to be in exactly one directory, which the image already owns.  Anywhere else, the data ends up owned by root, the database can't be opened, and the container crash-loops on first boot.  Second, a single config file bind-mounted into a container pins the file's inode, so when `git` replaces that file by rename, the container keeps reading the old one forever.  Both are now design walls.
- **Unsealing is an operational task.**

Every time OpenBao restarts, it comes back **sealed**: running and answering, but unable to read anything until it is given the unseal key.  OpenBao is designed to work that way.  For the platform's first few weeks, only a deploy unsealed it.

On 2026-09-23, the docker host rebooted on its own for the first time.  Every container came back.  Chat worked, because the course chat's key was already in its rendered config.  The health check passed, because "sealed" is a normal boot state and the check had been written to treat it as one.  But everything that needed the escrow failed: enrolling a student, fetching a key, rotating one, and approving a new course.

Nothing looked broken.  **A sealed vault fails closed, and the failure is invisible to everything that doesn't need a new secret.**  At any given minute, most of the platform doesn't.  The sealed vault was found by someone checking, and no alarm fired.

The fix is a boot-time unit that unseals OpenBao from `.env` as soon as Docker is up.  The health check now prints a warning line when the escrow is sealed.  Five days later the same unit got a second line, for a separate problem with the same lesson: a reboot also broke sign-in without any warning.

## What is still wrong with it

**The unseal key is in `.env`, on the same disk as the vault.**  The boot unit reads the key from there, so the box can reboot without a person present.  IT staff usually ask next what the seal protects, if the key is on the same disk.

The seal protects copies.  A copy of the vault's storage that leaves the box *without* `.env` (a stolen backup, a detached disk, a shared snapshot) is ciphertext.  Someone who controls the running box gets everything.  The seal is not a hardware security module, and the design spec (`docs/registrar-spec.md`) says so in its list of known limits.

The seal protects copies only while `.env` and the vault's storage are backed up **separately**.  A check of the backup design found both in one tarball, so a stolen backup would have included the unseal key along with the storage it unlocks.  The backup now writes two bundles to two separate repositories under two passwords, and neither password is kept only on the box.

Rebuilding the box also needs the unseal key.  The unseal key and both backup passwords now print on paper (`just dr-sheet`).  The drill that tested the sheet found the most important fact about restores: **a restored escrow opens only with the key it was sealed under.**  A rebuilt box mints a fresh key when it sets up its own vault, and once the old snapshot is restored over it, OpenBao refuses that fresh key.  If you lose the original unseal key, the backup is ciphertext to you as well as to a thief.

Moving the unseal key off the box would make the seal stronger.  The price is that every reboot would wait for a person to unseal the vault.  We chose reboots without a person over a person holding the key.  That choice is a tradeoff with a known cost, and it is not on the list of unfinished work.

**One credential does all of the registrar's work.**  The spec describes two planes inside the registrar: a chat-facing one that may read only the caller's own key, and a reconcile plane that mints.  In the code, the separation is a module boundary.  The vault sees one role for both planes, and that role can read every key in every course.  The design for a student-scoped policy, where the vault itself refuses to return anyone else's key, is written down but not built.

**The gateway's master key is still in `.env`.**  Moving it into the escrow is planned but not shipped.  The most powerful secret on the box is not in the vault yet.

**For the vault's first three months, no audit log was written.**  The setup recipe asked OpenBao to turn on its audit log, and the design, the compose file and the break-glass tool all said reads were audited.  But the OpenBao version we pin refuses to enable an audit log through its API.  It requires the audit log to be declared in the config file.  The recipe discarded that error and printed *"audit on"* anyway.  Both boxes we checked had an empty log directory.  The problem was found by checking a sentence in the documentation against the system.  The declaration is in `openbao/config.hcl` now, and the unseal step fails if the log isn't being written.  Nothing from before the fix can be recovered.  For those months, the only record is the vault's version history.

## Try it yourself

**If you're a student in a course here,** ask the Coder Guide in the {{PLATFORM}} chat for your key, then ask it to rotate your key, then ask for your key again.  The key is different, your remaining budget moved to the new key, and the old key now fails at the gateway.  The escrow still keeps a record of the old key.

**To see the mechanism yourself,** run a throwaway OpenBao in dev mode.  It needs no setup and keeps nothing:

```bash
docker run --rm -d --name bao-try --cap-add IPC_LOCK \
  openbao/openbao:2.6.3 server -dev -dev-root-token-id=root
b() { docker exec -e BAO_ADDR=http://127.0.0.1:8200 -e BAO_TOKEN=root bao-try bao "$@"; }

b kv put -mount=secret courses/demo/students/you key=sk-first    # enrolled
b kv put -mount=secret courses/demo/students/you key=sk-second   # rotated
b kv delete -mount=secret courses/demo/students/you              # un-enrolled
b kv metadata get -mount=secret courses/demo/students/you        # ...and yet
b kv get -mount=secret -version=1 courses/demo/students/you

docker rm -f bao-try
```

The `delete` succeeds.  Then the metadata lists both versions, the second one stamped with a deletion time.  The last command returns `sk-first`, the key from before the rotation, still stored after the "student" is gone.

A `.env` file would have kept only the current line, with no record that `sk-first` ever existed.
