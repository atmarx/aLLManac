# `site.example/` — the template for one deployment's local truth

Copy it to `site/` and edit that.  `just up` does the copy for you the
first time; `site/` is gitignored, `site.example/` is not.

```
cp -r site.example site        # or just let `just up` do it
```

## Why the folder exists

Everything above this directory is **the platform** — the same bytes on a
laptop, on xdocker03, and on a campus VM.  Everything inside `site/` is
**this box**: the services this deployment adds, the core services it
needs to bend, and the infrastructure underneath it.

The seam matters because the two change for different reasons and on
different clocks.  A LibreChat pin bump is a platform change and belongs
in a commit everyone gets.  "This VM's Postgres lives on a SAN mount" is
not; it belongs to exactly one box and should never reach anyone else's.

Before this folder, the only place to put the second kind was `.env` (fine
for scalars, useless for a service definition) or a local edit to
`compose.yml` (which every `git pull` fights).  Now there's a third place,
and it's the right shape: it's compose, so it can say anything compose can
say.

## What's in here

| Path | What it's for |
|---|---|
| `compose.yml` | Layered onto the core stack with `-f`, so it can **add** services and **override** existing ones.  Ships empty. |
| `inference/vllm.compose.yml` | Local GPU inference — its own compose project, run on demand with `just vllm-up`.  Optional by construction: see below. |
| `infra/` | What has to exist *before* docker compose is a sensible thing to run.  Yours to fill; deliberately unexemplified. |

## Inference is not part of the platform

The gateway reaches inference through one variable, `INFERENCE_BASE_URL`.
Everything on the other side of that URL is somebody's implementation
choice — a vLLM container on this box, a GPU server down the hall, a cloud
API.  LiteLLM cannot tell the difference and neither can anything above it.

So the vLLM stack lives here rather than in core, and dropping it is not a
feature we had to build — it's just not running it:

- **This box has GPUs** — `just vllm-up`, and point `INFERENCE_BASE_URL` at
  `http://host.docker.internal:8000/v1`.
- **A GPU box down the hall** — clone the repo *there*, `just setup`, set
  the `VLLM_*` vars, `just vllm-up`.  On the app box, point
  `INFERENCE_BASE_URL` at `http://<gpu-box>:8000/v1` and never run the
  stack at all.
- **No local inference** — delete `inference/`.  Point
  `INFERENCE_BASE_URL` wherever the tokens actually come from.

The third case is the one that made this move worth doing: a single VM with
no GPU in it shouldn't carry a GPU stack around, even an unused one.

**Read [`docs/design-walls.md`](../docs/design-walls.md) before changing the
vLLM flags** — the tool-call parser is per model family, and that wall was
expensive.  The wall stays in the platform docs precisely because it's
knowledge, not configuration.

## `infra/` — empty on purpose

Bringing up the metal is bespoke to a degree that an example would mislead
more than it helps.  One deployment's is a Terraform module against Azure
Local; another's is three lines of `apt`.  Both are correct.

For now the assumption underneath the whole repo is **a fresh Linux VM with
Docker on it** — get to that state however your institution gets to that
state, then `just setup && just up`.

When the shape of the real thing is known, its IaC lands in `site/infra/`,
and whatever generalizes gets promoted back into this folder.
