---
title: What is the gateway, and how do I call it?
description: One OpenAI-compatible address in front of every model.  How to point code at it, how to see which models your key can use, and how the limits on code differ from the limits on chat.
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

The gateway speaks the **OpenAI API**.  The name refers to a request format, not to the company, and nearly every AI library and tool can use that format.  Anything that says "OpenAI-compatible" works with the gateway once you change two settings: the address and the key.

The gateway's address comes with your key: the Coder Guide's [`my_key`](your-key.md) tool prints both in the same reply.  The address usually looks like `https://gateway.<your platform's domain>`, and the API is under `/v1`.

## Prove the chain works

```bash
export CAMPUS_API_KEY=sk-...                    # from my_key
export CAMPUS_BASE_URL=https://gateway.example.edu/v1

curl -s "$CAMPUS_BASE_URL/models" -H "Authorization: Bearer $CAMPUS_API_KEY"
```

The `curl` command lists **the models your key can call**.  Those are the models your course allows, which may not be every model on the platform.  If the list is empty or the call fails, nothing further will work either; see [when it breaks](when-it-breaks.md).

Then send a request to one of those models:

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

`r.usage` is the same count the ledger records.  Printing it while you work is the fastest way to learn what a request costs.  For more on reading those numbers, see [Understanding your usage](../understanding-your-usage/index.md).

## Chat and code are limited by different things

The limits that apply in chat are different from the limits on requests made through your key:

| | In chat | Through your key |
|---|---|---|
| **What stops a long conversation** | The course's context window.  The chat software trims the oldest turns before sending | Nothing at the gateway.  The gateway forwards whatever your code sends |
| **What stops spending** | The course's budget | Your key's own fuse, inside the course's budget |
| **Who is recorded** | You, by your sign-in | You, by your key |

The chat rule that long conversations get trimmed does not apply to code.  Through a key, your code decides how much context it sends, and the gateway forwards all of it.

When your code sends more than the model's server will take, the result depends on the server.  Some servers refuse with an error, which is the easier case to notice.  **Some servers drop your oldest messages and answer anyway, with no error.**  Those servers keep your system instructions and your latest message.  If those two alone are too long, some servers cut from the front, instructions included.  A script that works on short inputs and gives strange answers on long ones usually has this problem, and the model itself is working normally.  Keep your requests inside the context length the model is served with.  If nobody has told you that number, ask your instructor.

## Everything is attributed

Every request through your key is recorded against you, in your course: tokens in, tokens out, which model, and when.  The gateway's ledger keeps those counts.  The platform's gateway config turns off storing the text of what you sent, so the ledger does not keep it.  An operator controls that setting, and each deployment states what it keeps on [your data](../your-data/index.md).  You can see your own numbers any time by asking the **Usage Guide** in the {{PLATFORM}} chat for your usage.
