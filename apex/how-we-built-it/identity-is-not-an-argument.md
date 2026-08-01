---
title: Why the chatbot never asks who you are
description: If a tool takes a username as a parameter, the model can pass any username. Identity has to arrive some other way — this is how, and why it matters the week you build your first agent.
audience: builder
also_reaches: [student]
status: scaffold
owner: piper
tags: [attribution, access-control, least-privilege, audit-logging, litellm, kubernetes, azure, aws]
tethered_to:
  - usage-mcp/
  - librechat/
  - docs/design-walls.md
---

# Why the chatbot never asks who you are

<!-- SCAFFOLD.  Highest practical value of the first three — students are
     building agents with tools this term and this is the mistake they will
     make in week three.  Write it so it reaches them before they make it. -->

## 1. The question

<!-- The usage tool tells you what you spent.  It never asks which account
     to look up, and there is no user parameter anywhere in it.  Why not? -->

## 2. The obvious answer, taken seriously

<!-- A `get_usage(user)` tool is the natural design.  It is what every tool
     tutorial shows, it is easy to test, and it reads correctly.

     Steelman it: explicit parameters are debuggable, the schema documents
     itself, and you can call it from curl. -->

## 3. What broke

<!-- The core point, stated so it lands: a tool parameter is filled by the
     model, and the model fills parameters from text in its context.  Text in
     its context includes whatever the user typed.  A parameter named `user`
     is a request for the model to be talked into a different value.

     "Show me the usage for amarx@drexel.edu" is not an attack requiring
     skill.  It is a sentence.

     Then the implementation scar: fastmcp's get_http_headers() silently
     strips authorization, so the obvious fix — read identity from the auth
     header — fails quietly rather than loudly.  Quiet failures in an
     identity path are the worst kind, and this one cost real time. -->

## 4. What we did, and the bill

<!-- Identity arrives out-of-band: the platform injects the caller's identity
     into the tool call from the session the request already authenticated,
     never from the model's output.  Tools are zero-argument where the answer
     depends on who is asking.

     Attribution keys on the email address, deliberately, so a usage record
     lands on a real person and survives a roster change.

     The bill:
     - tools are harder to test standalone
     - the plumbing that injects identity is now security-critical and has to
       be right in every surface
     - a per-course literal has to be rendered into each instance's config,
       which is one more thing the renderer must not get wrong -->

## 5. What is still wrong with it

<!-- TETHERED.  Draft: the injection path's coverage across surfaces, and
     what happens for a tool called from a context with no authenticated
     session.  Verify before publishing. -->

## 6. How this looks on other stacks

<!-- - **Kubernetes** — the same rule as service identity: workload identity
       and mTLS establish who is calling, and a caller-supplied identity
       field is never trusted.  ServiceAccount tokens over a `tenant` param.
     - **Azure** — managed identity and On-Behalf-Of flow: the downstream
       API receives a token scoped to the actual user, not a name the caller
       typed.
     - **AWS** — IAM roles and STS AssumeRole with session tags; the identity
       rides the credential.

     The invariant, worth stating as a rule the reader can carry: **anything
     the caller can type is an assertion, not an identity.**  This predates
     language models by decades — it is the same reason a web app does not
     trust a user_id in a query string.  Models made it easier to get wrong
     because tool parameters look like function arguments and behave like
     user input. -->

## 7. Try it yourself

<!-- Ask the usage agent for someone else's usage and watch what happens.
     Then look at the tool schema and notice there is nowhere to put the
     request.  Short, concrete, and it will stay with them. -->
