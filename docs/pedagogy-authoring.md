---
title: How do I write a page students will read?
description: The page shapes, the controlled tag vocabulary, and the front matter every reader-facing page carries — plus the two rules that keep the words from drifting away from the running system.
audience: operator
also_reaches: [builder]
status: published
owner: piper
tags: [doc-drift, ai-literacy, accountability, faculty-duty, student-right, data-classification]
tethered_to:
  - docs/corpus.py
  - apex/tags.md
  - mkdocs.yml
  - docs/design-walls.md
---

# Authoring the reader-facing pages

*Owner: @piper (pedagogy lane).  Author-facing: it is addressed to whoever is writing the pages, which is why it carries `audience: operator` and stays off the reader-facing site — see "The corpus boundary" below for what that does and does not keep it out of.*

Everything a student or professor reads lives in `apex/`, which is both the website's `docs_dir` and the tree the corpus queries.  This file is how those pages get written: the page shapes, the controlled vocabulary, and the two rules that keep the words from drifting away from the system.

---

## The corpus boundary

The apex site and Ask the Almanac's knowledge files are the **same source** — one tree, two renderers (mkdocs for the web, embeddings for the chat).  That is the design and it is worth keeping: there is no second copy to drift.

The boundary is **front matter, not directory.**  `docs/corpus.py` walks `apex/` *and* `docs/`, and what decides whether a page lands in an agent's shelf is the metadata it carries:

| field | what it decides |
|---|---|
| `status:` | `scaffold` and `proposed` are withheld from every corpus.  Everything else ships. |
| `audience:` + `also_reaches:` | which of the four guides the page lands in — `student`, `faculty`, `builder`, `operator`. |
| `tags:` | the Security Guide is a cross-cut, not an audience; three or more Controls tags pull a page in regardless of who it addresses. |

So the rule an author has to hold is the wider one:

> **A page with front matter and a shippable status is in some agent's mouth, wherever it sits on disk.**  Not "unless we leave it out of `nav:`" — nav curates the website, the corpus queries the tree.  `docs/admin-guide.md` is in the Dev Guide's shelf and the Security Guide's today, and it never moved directories to get there.

There is exactly one file the render excludes by name: [agent-contract.md](agent-contract.md), because an agent is *told* its instructions and does not look them up.

**The status field is the gate, so use it as one.**  A page that should not be quoted yet is `scaffold` if it is unfinished and `proposed` if it is finished but unruled — filing it in `docs/` hides it from nobody.  That cuts the other way too: marking a page `published` to tidy up the front matter puts it in front of students, and `docs/registrar-spec.md` reaching three corpora through `also_reaches: [builder]` was a front-matter decision, not a filing accident.  If we want the spec quoted only through `how-we-built-it/`, the fix is its metadata.

Curation is still the work.  The show-the-work pages are *written from* the spec rather than being the spec relocated, and that is what lets the boundary stay strict without hiding anything we meant to teach.

---

## Who is actually reading

The stated audience for most of `apex/` is students.  The audience we are most trying to reach is **faculty**, who carry duties students do not: they decide what goes into a course instance, who can see it, whether agent `actions` are on, and what happens to the class's work at term end.

Lecturing faculty about compliance does not land.  So most pages use the same technique:

> **Write the system's behavior and the student's rights.  The faculty duty falls out as the mirror.**

A page that tells a student "your instructor can see the conversations in this course, and here is what they are expected to do with them" teaches the professor their obligation while they are reading something addressed to someone else.  They are overhearing, not being corrected.

`your-data/for-instructors.md` is the exception and addresses faculty directly.  Get them in the door with the overheard pages; give them one page they can be pointed at.

Front matter carries both: `audience:` is who the page speaks to, `also_reaches:` is who we mean to teach.

---

## Front matter schema

Every reader-facing page opens with:

```yaml
---
title: Why is there a vault?
description: One sentence — used by mkdocs, the tag index, and the RAG chunker.
audience: student          # student | faculty | builder | operator
also_reaches: [faculty]    # the overhearing audience; omit if none
status: scaffold           # scaffold | draft | proposed | published
owner: piper
tags: [secrets-management, escrow, openbao, encryption-at-rest]
regimes: [ferpa]           # data pages only; omit elsewhere
tethered_to:               # claims this page makes about the running system
  - registrar/reconcile.py
  - docs/design-walls.md#the-classroom-posture-is-opt-in
---
```

`description` earns its keep twice: mkdocs uses it for meta tags and the corpus uses it as chunk context.  Write it as a sentence, not a keyword pile.

`tethered_to` is the machine-readable half of the drift rule.  It lists the files whose behavior this page describes, so a future check can flag pages whose sources moved.

**Build note:** the tag index uses mkdocs-material's `tags` plugin and the
`<!-- material/tags -->` listing directive in `apex/tags.md`. Custom keys
(`audience`, `regimes`, `tethered_to`) are inert metadata and need no plugin.

---

## The seven beats — show-the-work pages

A normal ADR is written for a maintainer who already shares your vocabulary.  These are written for a reader who does not, and who is being taught on purpose.

1. **The question a student would actually ask.**  The title.  "Why is there a vault?" — not "ADR-003: Secret Management Strategy."
2. **The obvious answer, taken seriously.**  Readers arrive holding it.  Skip it and they conclude we never considered it.  Steelman it.
3. **What broke.**  Named error, real symptom, real date where we have one.  Scar tissue goes here.
4. **What we did, and the bill.**  Every decision costs something.  Showing the cost is what separates a teaching document from a brochure.
5. **What is still wrong with it.**  The open edge, stated plainly.
6. **How this looks on other stacks.**  The same decision on Azure, AWS, and Kubernetes.  This is the beat that transfers — most readers will never run our stack, and the shape of the problem outlives our particular answer.
7. **Try it yourself.**  Something the reader can run on the platform they are already signed into.  This beat is what makes the page coursework rather than a blog post.

Beat 6 is why the pages carry backend tags (`azure`, `aws`, `kubernetes`).  A reader who arrives from a k8s background should be able to pull every page that discusses the k8s equivalent.

---

## The two rules

**1.  Beat 5 is tethered.**  "What is still wrong with it" is a claim about the running system, which makes it drift-shaped.  It inherits the walls rule, pointed the other way:

> **When the plumbing closes an open edge, the teaching page changes in the same commit.**

A "what is still wrong" section describing a problem fixed six weeks ago teaches a falsehood with total confidence, and it does it in the help agent's voice as well as on the web.

**2.  Name the gaps.**  Data-protection pages state what we do *not* have.  A page implying scheduled offsite backups we do not run is a liability rather than documentation.  The gaps are also the better curriculum: a reader who sees "we have no per-student deletion path, here is why FERPA does not compel one, and here is why we might build it anyway" learns more than one reading a page that claims we are covered.

**3.  Write for no institution in particular.**  These docs ship with the platform, and another institution can run it.  The repo already works this way — `classroom` is a generic realm, not a customer — and `front-door.md` is deployment config precisely so a different deployment rewrites text rather than software.  The reader-facing pages inherit that.

So: **no institution's name, no institution's tier numbers, no institution's policy quoted as the authority.**  Say "your institution's register"; let the local operator fill it in.

*The posture the docs take:* **treat FERPA-protected coursework as high-risk data, and explain what that means.**  High risk is the conservative default and it is not a problem — it means doing the work deliberately.  The valuable part for the reader is never the label, it is the handling that attaches to it: encryption at rest and in transit, backups on a defined schedule with tested restores, access reviewed on a cadence, documented retention and disposal.  Write those, and a reader at any institution can map them onto whatever their own register says.

*The mechanism is portable; the entry is not.*  Risk classification is a **register** — a tier is an entry someone makes about a *system*, not a property the data has, and the entry is what carries the obligations.  That much is worth teaching everywhere.  What varies is scope and outcome: the same data type registers differently depending on what the system is for, so FERPA-protected data inside a research project and the same records inside an operational teaching platform are separate entries with separate arguments, and a given institution may land them a tier apart.  Teach the mechanism, name no outcome.

*Background, and the reason this rule exists* (operator-facing — it reaches the Dev Guide and no further, and it names no institution and no tier on purpose): an earlier draft imported one institution's specifics, including a live and unfinished registration conversation.  Publishing a predicted tier gives faculty something to plan against that the register may contradict, and it front-runs a determination that belongs to a compliance officer rather than a docs page.

A consequence for the plumbing side: **whatever tier a given deployment registers at hands its operator a requirements list.**  Backup cadence, encryption posture, and access review stop being good practice and become the entry's terms.  Several items on the gap lists in `your-data/` are likely to arrive as obligations rather than improvements.

---

## Controlled vocabulary

Tags are an index, so they only work if the same idea always gets the same word.  Add new tags here first, then use them.  Reader-facing tag index lives at `apex/tags.md`.

**Regimes and legal frameworks** `ferpa` · `gdpr` · `ccpa` · `hipaa` · `pci-dss` · `fisma` · `nist-800-53` · `nist-800-171` · `nist-ai-rmf` · `cui` · `state-privacy-law` · `ppra` · `coppa` · `data-processing-agreement`

**Data concepts** `data-classification` · `high-risk-data` · `education-record` · `eligible-student` · `school-official-exception` · `directory-information` · `pii` · `data-inventory` · `data-residency` · `data-minimization` · `consent` · `transparency-notice` · `automated-decision-making` · `privacy-impact-assessment`

**Controls** `access-control` · `rbac` · `sso` · `oidc` · `identity-broker` · `least-privilege` · `secrets-management` · `escrow` · `key-rotation` · `encryption-at-rest` · `encryption-in-transit` · `audit-logging` · `egress-control` · `allowlist`

**Lifecycle** `backup` · `restore` · `retention` · `archival` · `secure-deletion` · `disaster-recovery` · `rpo-rto` · `course-rollover` · `deployment` · `supply-chain`

**Architecture** `tenancy` · `isolation` · `multi-tenant` · `gateway` · `chokepoint` · `attribution` · `metering` · `rendered-config` · `doc-drift`

**Usage and cost** `context-window` · `token-economy` · `cost-intuition` — the Usage Guide cross-cut, alongside `metering` and `attribution` from Architecture.  Three or more of those five pull a page into that guide regardless of who it addresses, on the same principle as the Controls group and the Security Guide.

**Code and harnesses** `api-key` · `openai-compatible` · `harness` · `agentic-coding` · `tool-calling` — the Coder Guide cross-cut.  **Two** or more pull a page into that guide regardless of audience — one fewer than the other cross-cuts, because none of the five new ones is a tag a page carries in passing.  The cross-cut also borrows `key-rotation` from Controls, because using a key and replacing one are the same page; `secrets-management` stays out, because a page about custody is a security page first and reaches the Coder Guide only if it is also about using a key.

**Engineering practice** `version-control` · `automated-testing` · `ci-cd` — what has to be under an agent before the agent, and in the build track how this platform is run.  Not a cross-cut; `deployment` stays in Lifecycle.

**Stack and backends** `openbao` · `keycloak` · `litellm` · `librechat` · `mongodb` · `caddy` · `docker-compose` · `kubernetes` · `azure` · `aws` · `globus` · `vllm`

**Teaching and learning** `assessment-design` · `academic-integrity` · `syllabus-policy` · `detection` · `disclosure` · `ai-literacy` · `critical-evaluation` · `hallucination` · `equity` · `accountability` · `source-verification`

`accountability` is the section's spine — *a model cannot accept blame, only a person can*.  Tag anything that turns on who answers for an output, including the build-track pages where it is a design principle rather than a course policy.

**Duty** `faculty-duty` · `operator-duty` · `student-right`

The `faculty-duty` tag is load-bearing.  It is how a professor pulls everything they are responsible for out of pages written for their students.

---

## Voice

Match the surrounding docs: em dashes, double spaces after periods, concrete opening rather than a thesis statement.  Technical terms are fine when they are the right word; jargon used as a gate is not.

Two habits to avoid, because they read as filler:

- The "not X, but Y" reversal as a rhetorical move.  State the thing.
- Ending a section by restating what the section just said.

Land sections on something concrete — an example, a number, a consequence.
