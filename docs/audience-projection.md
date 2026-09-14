---
title: Audience projection — four guides, one tree
description: The RAG corpora for the Student, Instructor, Platform and Dev guides are projections over front matter, not four copies of the docs.
audience: operator
also_reaches: [builder]
status: proposed
owner: marco
tags: [rendered-config, attribution, ai-literacy, accountability]
tethered_to:
  - docs/pedagogy-authoring.md
  - mkdocs.yml
---

# Audience projection — four guides, one tree

**Status: proposed, 2026-09-11.**  Not ruled.  Nothing here invents a schema: [pedagogy-authoring.md](pedagogy-authoring.md) already declares the front matter and the controlled tag vocabulary, and that file remains the authority for both.  What is proposed is that the *help agents* be projections over it, and that `docs/` finally carry the same metadata `apex/` has carried all along.

---

## The rule

**Four guides, four audiences, one tree.  A guide is a query over front matter, never a directory.**

| Guide | `audience:` | What it is |
|---|---|---|
| **Student Guide** | `student` | Using the thing: courses, custom agents, vAPI keys, what happens to your work |
| **Instructor Guide** | `faculty` | Running a class: LibreChat's advanced features, configuring a course, rosters, groups, agents |
| **Platform Guide** | `builder` | The theory and the ideas — why it is shaped this way, what we tried first |
| **Dev Guide** | `operator` | The runbook: deploys, pins, escrow, the walls |

Those are the four values [pedagogy-authoring.md](pedagogy-authoring.md) has declared since the corpus began.  The guides are not a new taxonomy; they are the existing one, finally used.

`also_reaches:` carries the overlap.  A page belongs to exactly one primary audience and is *reachable* by others — which is how `for-students.md` can sit in both the Student and Instructor corpora without being copied, and how a page written for students teaches faculty their duty by being overheard.

## Why projection, not four hierarchies

Because a second copy is the drift.  The registrar spec already makes this argument about the docs serving twice — *"one source, two renderers... there is no second copy to drift"* — and it is the same rule that governs `fleet/` and `usage-mcp/roster.yaml`: **renders are never edited, sources are.**  Four audience directories would be four places for the same sentence to rot at different rates.

It also dissolves the filing problem rather than solving it.  `docs/user-guide.md` is student-facing prose living in the operator directory; with `audience: student` in its front matter, its directory stops mattering and nothing has to move.

## Three things that will bite the filter

**Use a denylist, not an allowlist.**  Almost nothing carries `published`, and nothing in `apex/` does — the corpus there is twelve `draft` and eight `scaffold`.  A filter that admits only published pages ships a near-empty corpus and the agents answer nothing.  The ratio is not a transient state to be fixed, either: a living corpus is mostly draft by nature, so the gate has to assume draft is the normal case.  Gate on exclusion (`scaffold`, `proposed`) so new pages are visible by default and only the deliberately-unfinished are held back.

**`proposed` is a new status value, and it is not `draft`.**  Draft means unfinished.  Proposed means finished but unratified — a complete argument that has not been ruled on.  They deserve different handling: a draft will improve, a proposal needs a decision.  Both stay out of the RAG copy, for different reasons.

The two notes that forced this — [budgets-and-meters.md](budgets-and-meters.md) and [rooms-and-visibility.md](rooms-and-visibility.md) — announce their status in **prose, on line three**, where no filter will ever see it.  A machine-readable status is the whole point: *if the disclaimer is not in front matter, the chunker drops it and the agent quotes an unratified rule as policy.*

**Projection is file-granular.**  `docs/admin-guide.md` genuinely holds both faculty recipes and operator runbook, and front matter admits one primary audience.  The answer is to split the file, not to build a section-range extractor — an extractor is a build step that rots the first time someone renames a heading.

## What the Dev Guide is for

Not admin-only.  Nothing in the operator docs is secret from a student; it is merely boring to most of them — and *not* boring to the ones who matter most here.  [design-walls.md](design-walls.md) is a list of places the obvious approach was wrong and someone paid to find out, which is close to an ideal handout for a student group playing blue or purple team.  Tag it `audience: operator, also_reaches: [builder, student]` and it lands in the Dev Guide while staying reachable by the enterprising.

Self-selection does the rest.  A student who wants the runbook picks the Dev Guide; nobody is gated, and nobody is bored by default.

## Not every bot is an audience

**The Security Guide** — the blue-team/purple-team corpus — is the case that keeps the schema honest.  It is not a fifth `audience:` value, and making it one would start the enum's career as a junk drawer.  Security material is a **cross-cut**: the vault page speaks to builders, the egress wall speaks to operators, and a tenancy page speaks to students, but all three belong in a defender's corpus.

So the generalisation is one line: **a corpus is a query over front matter, and the field it queries is a choice.**  The four guides query `audience:`.  The Security Guide queries `tags:` — the Controls group in [pedagogy-authoring.md](pedagogy-authoring.md) (`access-control`, `least-privilege`, `secrets-management`, `escrow`, `key-rotation`, `encryption-at-rest`, `audit-logging`, `egress-control`, `allowlist`, `rbac`, `sso`, `oidc`) plus the architecture tags that describe the chokepoint (`tenancy`, `isolation`, `gateway`, `chokepoint`).

Which means it is buildable before its own content exists.  Those tags are already carried by thirteen pages across `apex/`, and [design-walls.md](design-walls.md) is the densest security text in the repo once it is labelled — a catalogue of the SSRF allowlist's inverted default, the `actions.allowedDomains` trap, the single-file mount that served a stale config through a green reload.  A defender learns more from that file than from anything we would write on purpose.

**The exercises themselves are unwritten.**  Nothing in the tree is blue- or purple-team content today; the matches are incidental prose.  The Security Guide is therefore a corpus definition waiting on a corpus, and the useful order is: label what exists, see what the tag query already returns, then write into the gaps it exposes.

## The byproduct

`tethered_to:` lists the code paths a page makes claims about.  The same front-matter pass that builds the audience projection can answer a second question for free: **which guide goes stale when `registrar/planes/gateway.py` changes.**  That is the machine-readable half of the drift rule, and it has been sitting unused in `apex/` this whole time.

## What is left

- `docs/` carries no front matter at all — nine files, and `audience: operator` is declared in the vocabulary and used exactly zero times.  The Dev Guide's corpus is, definitionally, the set nobody has labelled yet.
- The enum in [pedagogy-authoring.md](pedagogy-authoring.md) needs `proposed`.
- The projection itself — a query, a denylist, and an upload — is unbuilt.  `just docs-build` already renders the same markdown to the help site; this is the embeddings half.
