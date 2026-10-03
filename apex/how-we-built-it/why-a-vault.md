---
title: Why is there a vault?
description: Service credentials still ride in env files.  The vault exists for the credentials we mint — a key per student, per course, that has to be readable again on request, revocable at any time, and accounted for after the student has gone.
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

Open `compose.yml` and count the services.  One of them, `alm-openbao`, has no users, no web page, and nothing a student will ever see.  Its whole job is holding secrets.

And right next to it, every other service in the stack still gets its secrets the old way: from an environment file.  The gateway's master key, the sign-in system's admin password, every course's encryption pair — all of it is in `.env` or a rendered `fleet/<slug>.env`, read at startup, exactly as it would be on any small deployment.

So the question isn't "why a vault instead of environment variables."  We didn't replace them.  The question is narrower, and more useful: **what changes when the secrets are ones you mint?**

## The question

The `.env` file works.  It has worked on every service here since the first commit.  Why add a second place for secrets — one that has to be backed up, unsealed after every restart, and understood by whoever runs the box?

## The obvious answer, taken seriously

Keep everything in environment files.

That deserves a fair hearing.  For most deployments it is the right answer.  Every runtime reads environment variables.  They keep secrets out of the image and out of git.  The file is plain text an operator can read, back up, and diff.  For a single operator running a handful of services whose credentials change once a year, a `.env` with tight permissions is adequate.  A vault in that setting is ceremony.

If you have shipped things with `.env` files and they were fine, they probably were.  Everything below is about one specific way this platform stopped being that setting.

## What broke

Every student in every course gets their own API key to the gateway — for opencode, for a notebook, for anything that speaks the OpenAI protocol.  The registrar mints it when they're enrolled, and the gateway shows it exactly once, at the moment of creation.

That last part is what forced the issue.  **A student has to be able to ask for their key again** — on a new laptop, a week later, after they lost the terminal it was printed in.  So the key has to be stored somewhere it can be read back.  And once you're storing minted keys, the environment file stops fitting in several ways at once:

- **It changes constantly.**  Enrollment mints, un-enrollment revokes, rotation does both, and closing a course revokes the whole class.  A file rewritten on every roster change is a different thing from a file written once at install.
- **It has no history.**  When a student rotates a leaked key, the old one should die — and someone should be able to say afterwards which key they held, from when to when.  A file keeps the current line and forgets the rest.
- **It has no receipts.**  Anything that can read the file can read every key in it, and nothing records that it did.
- **It is one secret, shared.**  A file is readable whole or not at all.  "This tool may read the caller's key and nobody else's" is not a permission a file can express.

There's a subtler failure too, and we learned it the hard way.  A key exists in two places — the gateway, where it spends, and wherever it can be read back.  A key that is live at the gateway but stored nowhere is the worst kind of orphan: it spends the course's budget and **nobody can find it to revoke it.**  An early helper recipe minted keys straight at the gateway, and every key it ever made was born that way.  The design wall that came out of it is blunt — *mint and escrow are one transaction* (`docs/design-walls.md`) — and there is no longer any path that mints a key without storing it.

## What we did, and the bill

**OpenBao, used as an escrow** — an open-source fork of HashiCorp Vault, running as one more container.  Its consumer list is short: the registrar, and a backup role that can take a snapshot and read nothing.  Every other service still reads its environment file.

What it holds is one record per key, at a path that says whose it is:

```
almanac/courses/<slug>/students/<email>    the key, when it was minted, its budget
almanac/courses/<slug>/service             the course chat's own key
```

The storage is versioned (OpenBao's key-value engine, version 2), and that is most of the point:

- **Rotation is a new version, not an overwrite.**  `rotate_my_key` mints the replacement *first*, writes it with a note saying which old key still owes a revoke, kills the old key at the gateway, then writes again with the debt cleared.  An interrupted rotation leaves a visible debt instead of two silently live keys.
- **Un-enrolling is a soft delete.**  The key is revoked at the gateway, and the record is marked deleted — but its history stays.  Custody survives the student leaving, which is what lets someone answer "who held which key, and when" after the term is over.
- **Ending a course** happens in two steps.  Closing it blocks every key at the gateway at once, while students still have a window to export their work.  Archiving it at the end of that window revokes each key, soft-deletes the student records, and marks the course's own record revoked instead of removing it.

The registrar logs in with its own role, gets a token that lives for an hour, and can touch `almanac/courses/*` and nothing else.  The root token is printed once, at setup, for a password manager — it's never written to disk on the box.

The bill:

- **Another stateful service** — to run, to back up, and to understand.  An operator now needs a second security model in their head: tokens, policies, seals.
- **It can be the reason things are down.**  If it isn't answering, nobody can enroll, fetch a key, or rotate one.
- **It has its own sharp edges, and we hit them.**  OpenBao's storage has to live in exactly one directory the image already owns.  Point it anywhere else and the data ends up owned by root, the database can't be opened, and the container crash-loops on first boot.  Then the config: a single file bind-mounted into a container pins the file's inode, so when `git` replaces that file by rename, the container goes on reading the old one forever.  Both are walls now, and both were paid for.
- **Unsealing is an operational event.**  This one is a story.

Every time OpenBao restarts, it comes back **sealed** — up, answering, and unable to read anything until someone hands it the unseal key.  That's by design.  For the first few weeks, only a deploy unsealed it.

On 2026-09-23, the docker host rebooted on its own for the first time.  Every container came back.  Chat answered: the course chat's key was already sitting in its rendered config.  The health check was green, because "sealed" is a normal boot state and the check had been written to say so.  And every path that needed the escrow was shut: enrolling a student, fetching a key, rotating one, approving a new course.

Nothing looked down.  **A vault that fails closed fails silently for everything that doesn't need a new secret** — and on any given minute, most things don't.  It was found by someone checking, not by anything alarming.

The fix is a boot-time unit that unseals from `.env` as soon as Docker is up, and the health check now prints a warning line when the escrow is sealed instead of passing it silently.  Five days later the same unit grew a second line, because a reboot turned out to break sign-in with no more warning — a separate story, the same lesson.  Reboots are where "healthy" and "working" part ways.

## What is still wrong with it

**The unseal key is in `.env`, on the same disk.**  The boot unit reads it from there, which is what lets the box reboot without a person.  So the first question anyone in IT asks is fair: then what does the seal protect?

The answer is narrow.  A copy of the vault's storage that leaves the box *without* `.env` — a stolen backup, a detached disk, a shared snapshot — is ciphertext.  Someone who owns the running box gets everything.  This is not a hardware security module, and the design spec (`docs/registrar-spec.md`) says so in its list of known limits.

That protection only holds while `.env` and the vault's storage are backed up **apart**.  Checking it caught the backup design putting both in one tarball — which is to say, the stolen copy of both.  The design now writes two bundles to two separate repositories under two passwords, and neither password lives only on the box.  That correction is the argument in miniature: the seal protected the storage, and the backup would have handed over the key with it.

Moving the key off the box is the upgrade path.  Its price is that every reboot waits for a person.  We chose "reboots without a human" over "a human holds the key."  That is a decision with a price, not a feature we haven't got to.

**One credential does all of the registrar's work.**  The spec describes two planes inside the registrar: a chat-facing one that may read only the caller's own key, and a reconcile plane that mints.  In the code the separation exists as a module boundary.  The vault sees one role for both planes, and that role can read every key in every course.  The design for a student-scoped policy, where the vault itself refuses to hand anyone else's key over, is written down and not built.

**The gateway's master key still lives in `.env`.**  Moving it into the escrow is planned and not shipped.  So the most powerful secret on the box is the one the vault doesn't hold yet.

**For its first three months, the receipts were never written.**  The setup recipe asked OpenBao to turn on its audit log, and the design, the compose file and the break-glass tool all said reads were audited.  But the OpenBao version we pin refuses to enable an audit log through its API — it wants one declared in the config file — and the recipe discarded that error and printed *"audit on"* anyway.  Both boxes we checked had an empty log directory.  This was found by checking a sentence on this page, which is becoming a habit.  The declaration is in `openbao/config.hcl` now, and the unseal step fails if the log isn't being written.  Nothing from before the fix can be recovered.  For those months, the only trail is the version history itself.

## Try it yourself

**If you're a student in a course here,** ask the Coder Guide in the {{PLATFORM}} chat for your key, then ask it to rotate your key, then ask for your key again.  The key is different, your remaining budget came along with it, and the old one now fails at the gateway.  Somewhere, a record of the old one still exists.  You just watched custody happen.

**If you want to see the mechanism,** run a throwaway OpenBao in dev mode — no setup, nothing kept:

```bash
docker run --rm -d --name bao-try --cap-add IPC_LOCK \
  openbao/openbao:2.4.1 server -dev -dev-root-token-id=root
b() { docker exec -e BAO_ADDR=http://127.0.0.1:8200 -e BAO_TOKEN=root bao-try bao "$@"; }

b kv put -mount=secret courses/demo/students/you key=sk-first    # enrolled
b kv put -mount=secret courses/demo/students/you key=sk-second   # rotated
b kv delete -mount=secret courses/demo/students/you              # un-enrolled
b kv metadata get -mount=secret courses/demo/students/you        # ...and yet
b kv get -mount=secret -version=1 courses/demo/students/you

docker rm -f bao-try
```

The `delete` succeeds.  Then the metadata lists both versions, the second one stamped with a deletion time, and the last command hands back `sk-first` — the key from before the rotation, still in custody after the "student" is gone.

That's the difference in one screen.  A `.env` file would have kept one line and forgotten the rest.  The vault keeps the history, and the history is the whole reason it's here.
