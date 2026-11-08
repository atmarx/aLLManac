---
title: "My code can't reach the model: what's wrong?"
description: The errors you will see from the gateway, what each one means, and which of them are yours to fix.  Several look like a broken key when the key is fine.
audience: student
also_reaches: [faculty, builder]
status: draft
owner: piper
tags: [api-key, openai-compatible, harness, tool-calling, key-rotation, context-window]
tethered_to:
  - registrar/server.py
  - registrar/planes/verbs.py
  - registrar/planes/gateway.py
  - litellm/config.yaml
  - docs/design-walls.md
---

# When it breaks

Work down the error tables from the top.  The first row that matches is almost always the answer.  The first table covers errors your code gets from the gateway.  The second covers what the Coder Guide says when you ask for your key.

## Errors from the gateway

| What you see | What it means | What to do |
|---|---|---|
| **401, "invalid key" or "authentication error"** on every call | The key is wrong, or it has been rotated and you are holding the old one | Check that the environment variable is set *in the shell running the code*.  If you rotated recently, ask the Coder Guide for your current key (`my_key`) |
| **An authentication-style error that names a model** | The key is fine, but it isn't allowed to use that model.  Either your course doesn't have the model, or the model was added after your key was minted | List what your key can call (`/v1/models`, see [the gateway](the-gateway.md)).  If the model should be there, rotate your key to pick up the course's current list |
| **"Budget exceeded"** | Your key's fuse has run out, or the course's budget has | The error's wording says which one, so keep the exact text.  Ask the Coder Guide about your key: `my_key` says what it has spent and what's left.  A spent fuse doesn't reset on a schedule.  Rotating won't help either: rotation moves the remainder to the new key and doesn't refill it.  Give your instructor those numbers ([when it runs out](your-key.md#when-it-runs-out)) |
| **429, "rate limit" or "too many requests"** | A 429 is not a limit on you.  The platform never limits how often you send requests, on a key or in the chat.  Your budget is the only limit.  A 429 means the server running the model was busy and turned the request away, after the gateway had already retried it twice | Wait a minute and send it again.  If it keeps happening, report it with the model name and the time |
| **Connection refused, DNS error, or a certificate warning** | Your code is pointed at the wrong address.  A certificate error alone can have a second cause: the platform uses a certificate of its own that your machine doesn't trust yet | Use the gateway address `my_key` gave you, with `/v1` on the end, over `https`.  If the address is right and only the certificate fails, ask whoever runs the platform how to trust it.  Don't switch certificate verification off |
| **Works on short inputs, goes strange on long ones** | You are sending more context than the model is served with, and its server is dropping your oldest messages.  If one message is huge, the server may cut the instructions too | Send less.  In a harness, set its context to the served number: `contextWindow` in pi, `limit.context` in opencode |
| **The harness stalls, or prints something that looks like a tool call as plain text** | The model's server isn't configured for that model's tool-call format | Not yours to fix.  Report it, with the model name |
| **The harness "thrashes"**: it keeps summarizing, forgetting, and starting over | The context window is too small for the harness's own instructions plus your work | Try a lighter harness.  pi's own instructions are a fraction of opencode's, and opencode needs a model served with at least 16k.  Ask which models are ([coding harnesses](harnesses.md#the-loop-and-why-it-spends)) |

## Messages when you ask for your key

| What you see | What it means | What to do |
|---|---|---|
| **`my_key` says you aren't on the roster** | Your instructor hasn't enrolled you in this course yet | Ask your instructor to enroll you.  There is no key to fetch until you are enrolled |
| **`my_key` says the course closed** | The term is over and the course's budget is shut, so every key for the course stopped at once.  Nothing is wrong with yours | Your work is still there.  Ask the Student Guide in the {{PLATFORM}} chat to **export your data**.  Export works after the course closes, too |
| **"Keys can't be handed out for the moment"** | The part of the platform that stores keys is locked, usually right after a restart.  Your key is fine | Wait a few minutes and ask again.  If it lasts, report it |
| **"You're on the roster but no key is escrowed yet"** | You were just enrolled and your key is still being made | Try again in a minute.  If it still says this after a few minutes, ask your instructor to re-apply the roster, which makes any missing key |
| **The chat says it can't fetch your key** | You asked your course's chat, or a guide other than the Coder Guide.  Only the Coder Guide has the key tools | Ask the **Coder Guide** in the {{PLATFORM}} chat.  In more than one course, say which |

## Reporting it

If no row in the error tables fits, or the row says the problem is not yours to fix, tell one of the guides in the {{PLATFORM}} chat.  The guide can file a report to the people who run the platform, marked with your course when the problem is about your course.  The guides still answer when your course is the thing that's down.  Include the model name, the exact error text, and roughly when it happened.  **Never include your key.**  Nobody debugging the problem needs it, and the ledger already records that the requests were yours.
