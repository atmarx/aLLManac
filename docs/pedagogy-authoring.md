# Authoring the reader-facing pages

*Owner: @piper (pedagogy lane).  Operator/author-facing — this file stays in
`docs/` and out of `apex/` on purpose; see "The corpus boundary" below.*

Everything a student or professor reads lives in `apex/`.  This file is how
it gets written: the page shapes, the controlled vocabulary, and the two
rules that keep the words from drifting away from the system.

---

## The corpus boundary

The apex site and Ask the Almanac's knowledge files are the **same
directory** — one source, two renderers (mkdocs for the web, embeddings for
the chat).  That is the design and it is worth keeping: there is no second
copy to drift.

The consequence is the rule:

> **Anything inside `apex/` is in the help agent's mouth.**  Not "unless we
> leave it out of `nav:`" — nav curates the website, the corpus eats the
> tree.  A page dropped from nav is still a file in the directory, still
> embedded, still quotable by the agent to any student who asks.

So the boundary is a **directory** boundary:

| pile | lives in | in the corpus |
|---|---|---|
| Public + taught — guides, how-tos, `your-data/`, `how-we-built-it/` | `apex/` | yes |
| Operator — admin guide, CI, design walls, **this file** | `docs/` | no |
| Internal record — the registrar spec | `docs/` | no — quoted by `how-we-built-it/`, never published wholesale |

The third pile matters most for the show-the-work track.  Those pages are
*written from* the spec.  They are not the spec relocated.  Curation is the
work, and it is the reason the boundary can stay strict without hiding
anything we meant to teach.

---

## Who is actually reading

The stated audience for most of `apex/` is students.  The audience we are
most trying to reach is **faculty**, who carry duties students do not: they
decide what goes into a course instance, who can see it, whether agent
`actions` are on, and what happens to the class's work at term end.

Lecturing faculty about compliance does not land.  So most pages use the
same technique:

> **Write the system's behavior and the student's rights.  The faculty duty
> falls out as the mirror.**

A page that tells a student "your instructor can see the conversations in
this course, and here is what they are expected to do with them" teaches the
professor their obligation while they are reading something addressed to
someone else.  They are overhearing, not being corrected.

`your-data/for-instructors.md` is the exception and addresses faculty
directly.  Get them in the door with the overheard pages; give them one page
they can be pointed at.

Front matter carries both: `audience:` is who the page speaks to,
`also_reaches:` is who we mean to teach.

---

## Front matter schema

Every page in `apex/` opens with:

```yaml
---
title: Why is there a vault?
description: One sentence — used by mkdocs, the tag index, and the RAG chunker.
audience: student          # student | faculty | builder | operator
also_reaches: [faculty]    # the overhearing audience; omit if none
status: scaffold           # scaffold | draft | published
owner: piper
tags: [secrets-management, escrow, openbao, encryption-at-rest]
regimes: [ferpa]           # data pages only; omit elsewhere
tethered_to:               # claims this page makes about the running system
  - registrar/reconcile.py
  - docs/design-walls.md#the-classroom-posture
---
```

`description` earns its keep twice: mkdocs uses it for meta tags and the
corpus uses it as chunk context.  Write it as a sentence, not a keyword pile.

`tethered_to` is the machine-readable half of the drift rule.  It lists the
files whose behavior this page describes, so a future check can flag pages
whose sources moved.

**Build note for @geordi:** the tag index assumes mkdocs-material's `tags`
plugin with `tags_file: tags.md`.  Custom keys (`audience`, `regimes`,
`tethered_to`) are inert metadata and need no plugin.

---

## The seven beats — show-the-work pages

A normal ADR is written for a maintainer who already shares your vocabulary.
These are written for a reader who does not, and who is being taught on
purpose.

1. **The question a student would actually ask.**  The title.  "Why is there
   a vault?" — not "ADR-003: Secret Management Strategy."
2. **The obvious answer, taken seriously.**  Readers arrive holding it.  Skip
   it and they conclude we never considered it.  Steelman it.
3. **What broke.**  Named error, real symptom, real date where we have one.
   Scar tissue goes here.
4. **What we did, and the bill.**  Every decision costs something.  Showing
   the cost is what separates a teaching document from a brochure.
5. **What is still wrong with it.**  The open edge, stated plainly.
6. **How this looks on other stacks.**  The same decision on Azure, AWS, and
   Kubernetes.  This is the beat that transfers — most readers will never run
   our stack, and the shape of the problem outlives our particular answer.
7. **Try it yourself.**  Something the reader can run on the platform they
   are already signed into.  This beat is what makes the page coursework
   rather than a blog post.

Beat 6 is why the pages carry backend tags (`azure`, `aws`, `kubernetes`).
A reader who arrives from a k8s background should be able to pull every page
that discusses the k8s equivalent.

---

## The two rules

**1.  Beat 5 is tethered.**  "What is still wrong with it" is a claim about
the running system, which makes it drift-shaped.  It inherits the walls rule,
pointed the other way:

> **When the plumbing closes an open edge, the teaching page changes in the
> same commit.**

A "what is still wrong" section describing a problem fixed six weeks ago
teaches a falsehood with total confidence, and it does it in the help agent's
voice as well as on the web.

**2.  Name the gaps.**  Data-protection pages state what we do *not* have.  A
page implying scheduled offsite backups we do not run is a liability rather
than documentation.  The gaps are also the better curriculum: a reader who
sees "we have no per-student deletion path, here is why FERPA does not compel
one, and here is why we might build it anyway" learns more than one reading a
page that claims we are covered.

**3.  Never assert a risk tier.**  Risk classification at the university is a
**register** — a system's tier is an entry someone makes, not a property the
data has.  The entry is what carries the obligations: backup standards,
encryption, access-review cadence, handling rules.

Two things follow for anyone writing these pages.

*Scope is part of the determination.*  The same data type registers
differently depending on what the system is for.  FERPA-protected data inside
a **research project** is registered high, and that has held against several
attempts to lower it.  This platform is **operational**, which is a separate
entry with a separate argument, and as of 2026-07-31 it has not been
registered — the live conversation puts it plausibly around medium.  Harvard's
comparable platform sits at their Level 3, which reads as medium-plus.

*So pages say what the system does and wait for the entry.*  Naming a tier we
have guessed at gives faculty something to plan against that the register may
contradict.  Describing a control we actually run is true regardless of how
the entry lands.

A useful consequence for the plumbing side: **whatever tier this registers at
hands @geordi a requirements list.**  Backup cadence, encryption posture, and
access review stop being good practice and become the entry's terms.  Several
items on the gap lists in `your-data/` are likely to arrive as obligations
rather than improvements.

---

## Controlled vocabulary

Tags are an index, so they only work if the same idea always gets the same
word.  Add new tags here first, then use them.  Reader-facing tag index lives
at `apex/tags.md`.

**Regimes and legal frameworks**
`ferpa` · `gdpr` · `ccpa` · `hipaa` · `pci-dss` · `fisma` · `nist-800-53` ·
`nist-800-171` · `nist-ai-rmf` · `cui` · `state-privacy-law` · `ppra` ·
`coppa` · `data-processing-agreement`

**Data concepts**
`data-classification` · `high-risk-data` · `education-record` ·
`eligible-student` · `school-official-exception` · `directory-information` ·
`pii` · `data-inventory` · `data-residency` · `data-minimization` ·
`consent` · `transparency-notice` · `automated-decision-making` ·
`privacy-impact-assessment`

**Controls**
`access-control` · `rbac` · `sso` · `oidc` · `identity-broker` ·
`least-privilege` · `secrets-management` · `escrow` · `key-rotation` ·
`encryption-at-rest` · `encryption-in-transit` · `audit-logging` ·
`egress-control` · `allowlist`

**Lifecycle**
`backup` · `restore` · `retention` · `archival` · `secure-deletion` ·
`disaster-recovery` · `rpo-rto` · `course-rollover`

**Architecture**
`tenancy` · `isolation` · `multi-tenant` · `gateway` · `chokepoint` ·
`attribution` · `metering` · `rendered-config`

**Stack and backends**
`openbao` · `keycloak` · `litellm` · `librechat` · `mongodb` ·
`docker-compose` · `kubernetes` · `azure` · `aws` · `globus` · `vllm`

**Duty**
`faculty-duty` · `operator-duty` · `student-right`

The `faculty-duty` tag is load-bearing.  It is how a professor pulls
everything they are responsible for out of pages written for their students.

---

## Voice

Match the surrounding docs: em dashes, double spaces after periods, concrete
opening rather than a thesis statement.  Technical terms are fine when they
are the right word; jargon used as a gate is not.

Two habits to avoid, because they read as filler:

- The "not X, but Y" reversal as a rhetorical move.  State the thing.
- Ending a section by restating what the section just said.

Land sections on something concrete — an example, a number, a consequence.
