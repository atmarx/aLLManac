---
title: Who can see it
description: Access control from the front door inward — sign-in, course isolation, per-student keys, sharing defaults, and the one path that leaves the building.
audience: student
also_reaches: [faculty]
status: scaffold
owner: piper
tags: [access-control, sso, oidc, identity-broker, tenancy, isolation, egress-control, allowlist, faculty-duty, keycloak, globus]
regimes: [ferpa]
tethered_to:
  - docs/design-walls.md#the-classroom-posture
  - registrar/reconcile.py
  - registrar/render.py
---

# Who can see it

<!-- SCAFFOLD.  Work outward-in: door, room, key, sharing, egress. -->

## Signing in

<!-- Keycloak SSO.  Campus identity — today local accounts, with the Globus
     broker one toggle from live.

     IMPORTANT for accuracy: Globus here is an identity broker only.  It
     authenticates the person.  No almanac data lives in a Globus
     collection, nothing transfers over Globus, and there are no Globus
     group ACLs on any of this.  Students arriving from research computing
     will assume otherwise — say it plainly. -->

## Your course is its own room

<!-- Instance-per-course tenancy, in a sentence a freshman gets: your course
     runs its own copy of the chat with its own database.  Another course
     cannot see into yours because there is no shared room to partition.

     Link to how-we-built-it/keeping-courses-apart.md for the why. -->

## Who has reach, honestly

<!-- List, no hedging:
     - your instructor, within your course
     - platform operators, who hold the infrastructure
     - nobody in another course
     State that operator access is a function of running the servers, and
     that the honest control on it is institutional policy rather than a
     technical barrier.  Do not imply otherwise. -->

## Sharing is off until someone turns it on

<!-- Default posture: agents.share=false, people-picker off.  Out of the box
     students cannot share agents with each other.  Faculty opt in per
     course.

     FACULTY MIRROR: this is where a professor learns that turning sharing on
     is a decision with consequences, by reading what their students are
     told about the default. -->

## The path that leaves the building

<!-- Agent Actions.  An agent with `actions` enabled can call any URL its
     builder points it at, which means course content can be sent outside
     the university's hardware by design of the feature.

     Per-course `capabilities:` controls whether the course has it at all.
     `actions` is excluded from the default on purpose.

     !!! warning "Open gap"
         The domain allowlist (`actions.allowedDomains`) is not built yet.
         Where a course enables actions, the destination is whatever the
         agent's builder typed.

     This section carries `faculty-duty` — it is the single most consequential
     switch a professor controls. -->
