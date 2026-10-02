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
| **401, "invalid key" or "authentication error"** on every call | The key is wrong, or it has been rotated and you are holding the old one | Check the environment variable is set *in the shell running the code*.  If you rotated recently, ask the Coder Guide for your current key (`my_key`) |
| **An authentication-style error that names a model** | The key is fine.  It isn't allowed that model — either your course doesn't have it, or it was added after your key was minted | List what your key can call (`/v1/models`, see [the gateway](the-gateway.md)).  If the model should be there, rotate your key to pick up the course's current list |
| **"Budget exceeded"** | Your key's fuse has run out — or the course's budget has | The error's own wording is what says which, so keep it.  Asking the Usage Guide for your usage shows what you've spent, not which limit you hit.  Rotating won't help; it carries the remainder over, it doesn't refill.  Talk to your instructor |
| **Connection refused, DNS error, or a certificate warning** | You are pointed at the wrong address — or, for a certificate error only, the platform uses a certificate of its own that your machine doesn't trust yet | Use the gateway address `my_key` gave you, with `/v1` on the end, over `https`.  If the address is right and only the certificate fails, ask whoever runs the platform how to trust it — don't switch verification off |
| **Works on short inputs, goes strange on long ones** | You are sending more context than the model is served with, and its server is dropping the front — your instructions first | Send less.  In a harness, lower `limit.context` to the served number |
| **The harness stalls, or prints something that looks like a tool call as plain text** | The model's server isn't configured for that model's tool-call format | Not yours to fix.  Report it, with the model name |
| **The harness "thrashes"** — summarising, forgetting, starting over | The context window is too small for the harness's own instructions plus your work | It needs a model served with at least 16k.  Ask which models are |
| **`my_key` says you aren't on the roster** | Your instructor hasn't enrolled you in this course yet | Ask them.  There is no key to fetch until you are |
| **`my_key` says the course closed** | The term is over and the course's budget is shut, so every key for it stopped at once.  Nothing is wrong with yours | Export anything you want to keep before the date it gives you — ask the Student Guide at the front door to **export your data** |
| **"Keys can't be handed out for the moment"** | The part of the platform that holds keys is locked, usually right after a restart.  Your key is fine | Wait a few minutes and ask again.  If it lasts, report it |
| **"You're on the roster but no key is escrowed yet"** | You were just enrolled and your key is still being made | Try again in a minute |
| **The guide says it can't fetch your key** | You are asking at the front door.  Keys live in courses, and the front door belongs to no course | Ask in your course's own chat |

## Reporting it

If nothing above fits, or the answer is "not yours to fix," tell one of the guides at the platform's front door — the main chat — and it can file a report that reaches the people who run the platform, and your course's teaching staff when it is about your course.  Your course's own chat can file one too; the front door is recommended because it still answers when the thing you are reporting is your course being down.  Include the model name, the exact error text, and roughly when it happened.  **Never include your key.**  Nobody debugging this needs it, and the ledger already knows it was you.
