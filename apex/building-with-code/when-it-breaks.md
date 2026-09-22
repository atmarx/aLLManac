---
title: My code can't reach the model — what's wrong?
description: The errors you will actually see from the gateway, what each one really means, and which of them are yours to fix.  Several look like a broken key and aren't.
audience: student
also_reaches: [faculty, builder]
status: draft
owner: piper
tags: [api-key, openai-compatible, harness, tool-calling, key-rotation, context-window]
tethered_to:
  - registrar/server.py
  - registrar/planes/verbs.py
  - registrar/planes/gateway.py
  - docs/design-walls.md
---

# When it breaks

Work down this table from the top.  The first row that matches is almost always the answer.

| What you see | What it actually means | What to do |
|---|---|---|
| **401, "invalid key" or "authentication error"** on every call | The key is wrong, or it has been rotated and you are holding the old one | Check the environment variable is set *in the shell running the code*.  If you rotated recently, fetch the current key with `my_key` |
| **An authentication-style error that names a model** | The key is fine.  It isn't allowed that model — either your course doesn't have it, or it was added after your key was minted | List what your key can call (`/v1/models`, see [the gateway](the-gateway.md)).  If the model should be there, rotate your key to pick up the course's current list |
| **"Budget exceeded"** | Your key's fuse has run out — or the course's budget has | Ask for your usage in the chat to see which.  Rotating won't help; it carries the remainder over, it doesn't refill.  Talk to your instructor |
| **Connection refused, DNS error, or a certificate warning** | You are pointed at the wrong address | Use the gateway address, with `/v1` on the end, over `https` |
| **Works on short inputs, goes strange on long ones** | You are sending more context than the model is served with, and its server is dropping the front — your instructions first | Send less.  In a harness, lower `limit.context` to the served number |
| **The harness stalls, or prints something that looks like a tool call as plain text** | The model's server isn't configured for that model's tool-call format | Not yours to fix.  Report it, with the model name |
| **The harness "thrashes"** — summarising, forgetting, starting over | The context window is too small for the harness's own instructions plus your work | It needs a model served with at least 16k.  Ask which models are |
| **`my_key` says you aren't on the roster** | Your instructor hasn't enrolled you in this course yet | Ask them.  There is no key to fetch until you are |
| **The guide says it can't fetch your key** | You are asking at the front door.  Keys live in courses, and the front door belongs to no course | Ask in your course's own chat |

## Reporting it

If nothing above fits, or the answer is "not yours to fix," tell one of the guides at the platform's front door — the main chat, not your course's — and it can file a report that reaches the people who run the platform.  The front door is on purpose: it still answers when the thing you are reporting is your course being down.  Include the model name, the exact error text, and roughly when it happened.  **Never include your key.**  Nobody debugging this needs it, and the ledger already knows it was you.
