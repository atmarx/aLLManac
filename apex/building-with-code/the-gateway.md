---
title: What is the gateway, and how do I call it?
description: One OpenAI-compatible address in front of every model.  How to point code at it, how to see which models your key can use, and which limits apply to code that don't apply to chat — and the other way round.
audience: student
also_reaches: [faculty, builder]
status: draft
owner: piper
tags: [gateway, openai-compatible, api-key, attribution, metering, context-window]
tethered_to:
  - litellm/config.yaml
  - caddy/Caddyfile
  - registrar/planes/gateway.py
  - docs/design-walls.md
---

# The gateway

One address, the **gateway**, fronts every model on the platform.  Chat calls it for you; code calls it directly, with your key.  The gateway checks the key, checks that the key is allowed to use that model, records the request against your name, and passes it on.

It speaks the **OpenAI API**.  That is a format, not a company, and nearly every AI library and tool can talk to it.  Anything that says "OpenAI-compatible" works here once you change two settings — the address and the key.

The gateway's address comes with your key — the Coder Guide's [`my_key`](your-key.md) prints it in the same reply.  It usually looks like `https://gateway.<your platform's domain>`, and the API lives under `/v1`.

## Prove the chain works

```bash
export CAMPUS_API_KEY=sk-...                    # from my_key
export CAMPUS_BASE_URL=https://gateway.example.edu/v1

curl -s "$CAMPUS_BASE_URL/models" -H "Authorization: Bearer $CAMPUS_API_KEY"
```

That lists **the models your key can call** — not every model on the platform, the ones your course allows.  If the list is empty or the call fails, nothing further will work either; see [when it breaks](when-it-breaks.md).

Then ask one of them something:

```python
import os
from openai import OpenAI

client = OpenAI(base_url=os.environ["CAMPUS_BASE_URL"],
                api_key=os.environ["CAMPUS_API_KEY"])
r = client.chat.completions.create(
    model="{{MODEL}}",        # use a name from the /models list
    messages=[{"role": "user", "content": "Name your model in one line."}],
)
print(r.choices[0].message.content)
print(r.usage)                   # the tokens this call cost, in and out
```

`r.usage` is the same count the ledger records.  Printing it while you work is the fastest way to build an intuition for what a request costs — see [Understanding your usage](../understanding-your-usage/index.md).

## Chat and code are limited by different things

This is the one to remember.

| | In chat | Through your key |
|---|---|---|
| **What stops a long conversation** | The course's context window — LibreChat trims the oldest turns before sending | Nothing at the gateway.  You send what you send |
| **What stops spending** | The course's budget | Your key's own fuse, inside the course's budget |
| **Who is recorded** | You, by your sign-in | You, by your key |

So a rule you learned in the chat window — "long conversations get trimmed, so there's a ceiling" — does not apply here.  Through a key, your code decides how much context it sends, and the gateway forwards all of it.

What happens when you send more than the model's server will take depends on the server.  Some refuse with an error, which is the good case.  **Some drop the front of the prompt and answer anyway, with no error** — and the front is where your instructions are.  A script that works on short inputs and goes strange on long ones is usually showing you this; the model is fine.  Keep your requests inside the context length the model is served with; ask your instructor if nobody has told you the number.

## Everything is attributed

Every request through your key is recorded against you, in your course — tokens in, tokens out, which model, when.  By default the gateway's ledger keeps those counts and not the text of what you sent.  An operator controls that setting, and [your data](../your-data/index.md) is where a deployment says what it keeps.  You can see your own numbers any time by asking the **Usage Guide** in the {{PLATFORM}} chat for your usage.
