---
title: When does a room get its own instance?
description: A proposed rule — mint an instance only when someone other than the user needs administrative visibility — run through every room kind, plus the argument for a commons that the registrar spec does not yet make.
audience: operator
also_reaches: [builder, faculty]
status: proposed
owner: marco
tags: [tenancy, isolation, multi-tenant, access-control, rbac, least-privilege, attribution, metering, course-rollover, transparency-notice, equity, student-right, faculty-duty, librechat]
tethered_to:
  - docs/registrar-spec.md
  - registrar/server.py
  - registrar/render.py
  - registrar/courses.example.yaml
  - site.example/
---

# Rooms and visibility — when to mint an instance, and why the commons is different

**Status: proposed, 2026-09-09.**  Not ruled.  The room primitive described here already exists (`kind: course | project | sandbox | office` with an optional `parent:`, see [registrar-spec.md](registrar-spec.md)); what is proposed is a rule for *when each kind gets its own instance*, and a new argument for why a commons should exist at all.

---

## The rule

**Mint an instance when someone other than the user needs administrative visibility.  Otherwise share.**

That is the whole rule, and it falls out of what the instance boundary actually buys.  Instance-per-course exists so an instructor has visibility over their own course and nobody else's.  The reason it has to be an instance is upstream's design, not ours: you cannot make someone an administrator of one workspace without making them an administrator of the deployment.  Open WebUI states this outright — *"the `admin` role is root-equivalent on the deployment by deliberate design"* — and a community request for workspace-scoped admin was closed with the requester objecting that scoping only works *"if users are granted 'Admin' privileges.  This is exactly what we cannot do in our enterprise setup."*  LibreChat is the same shape.  **A separate instance is how you scope an administrator.**

**Budgets are not a reason to mint an instance.**  Spend attribution happens at the gateway — owner tags, team budgets, and the end-user header — regardless of which instance a request came from.  A shared instance can carry per-project rollup because LiteLLM does that work, not LibreChat.  Conflating "this needs its own budget" with "this needs its own instance" would multiply the fleet for no boundary gained.

## The room kinds, run through the rule

| Kind | Who needs visibility | Verdict |
|---|---|---|
| `course` | the instructor, over their course | **own instance** — unchanged |
| `course-project` | the sponsoring instructor, who already administers the parent course | **inside the parent course's instance** — same person, same trust boundary; `parent:` should govern hosting as well as spend rollup |
| `project` (standalone: club, competition team, thesis prep) | nobody — there is no instructor | **shared instance** |
| `sandbox` / commons | nobody, emphatically | **shared instance** |
| `office` / frontdesk | the operator | **own instance** — it already is one |

Two secondary considerations push the same direction for projects.  **Lifecycle:** a course has a term boundary that makes teardown natural, while a student project has no natural end, so instance-per-project accumulates orphans indefinitely.  **Cost:** every instance is a chat + Meili + panel trio (the control plane is shared, the trio is not), and projects churn constantly while courses are stable per term.

Privacy survives the shared case, which is the thing worth checking before agreeing to it: **LibreChat Projects are personal** — other users do not see your project list.  A shared commons therefore gives each person a private workspace without a per-person instance.

---

## The commons, and the argument for it that the spec does not yet make

The spec already justifies a sandbox on cost grounds — the front office runs `$0` house metal so faculty can *"tinker freely, zero budget anxiety, nothing real at stake."*  That is a money argument, and it is not the strongest one available.

**The stronger argument is that observation changes what people are willing to try.**  If every message is attributed to a course and visible to an instructor, students write for the audience: they ask the safe question, they don't chase the tangent, and the exploratory work that actually teaches them the tool doesn't happen.  A room where the transcript may be read is a room where people perform.  A commons is not a perk; it is the only place where the unperformed version of the work can happen.

This is a recognised tension, not a local hunch.  MIT's Ad Hoc Committee on AI Use in Teaching, Learning, and Research Training (2026-08-13) names it directly: users may expect confidentiality when discussing sensitive matters with AI, while instructors may want to audit classroom usage, and MIT's proposed answer is a *labelling* practice — clearly mark the assignments whose logs are shared with instructors.  **A separate room is the better answer, because it makes the boundary structural rather than asking students to trust a notice.**

### What the commons costs us, stated honestly

The commons collides with something we built deliberately.  Our ledger design says every key has an owner, usage rolls up to the unit that answers for it, and instructors can see per-student consumption in their course.  Those are features, and they are also exactly the mechanism that would chill the commons.

The resolution is to split two things we have been treating as one:

- **Attribution for billing** — somebody pays for commons tokens, so spend remains visible to the operator.  This is unavoidable and should be said plainly rather than implied away.
- **Attribution for pedagogy** — does not apply here.  The commons carries no `parent:`, so its spend rolls up to no course, and **no instructor sees it.**

A student's course usage and their commons usage are different ledgers with different audiences.  That distinction is the design; without it the commons is a course room with a friendlier name.

### The budget shape

A commons wants its own allowance, separate from any course, so that exploring never eats coursework.  In the machinery that is simply a `sandbox` room with no `parent:` — the existing primitive, used as intended.

### Falling back is not the same as being cut off

A student who exhausts a course budget is not without AI, wherever the institution already licenses a general-purpose assistant campus-wide at no incremental cost.  A course budget caps *that course's spend*, never a student's access.  This is worth stating on every page that explains budgets, because it converts an equity objection into a routing question.

**But the fallback does not cover the commons.**  A general-purpose assistant is a chat box; it does not hand a student agent-building, knowledge files, or a persistent custom project.  The capability the commons protects is the *building*, and that is precisely what the general-purpose fallback cannot substitute for.

---

## What a provisioned instance does not teach

A recurring temptation is to justify per-project instances as training — students learning the platform soup to nuts.  **A provisioned instance teaches nothing about provisioning.**  If the registrar mints a student a room, they receive a finished artifact exactly as a course does; the learning lives in *standing one up*, not in having one.

That offering already exists and requires nothing new: the repository is public, `just setup` generates every secret, [`site.example/`](../site.example/) exists so one box's specifics never contaminate the platform, and the docs walk the whole build.  A student who wants the full stack can clone it today.  It belongs in the curriculum, not in the fleet.
