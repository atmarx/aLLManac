# Working in this repo

The **aLLManac** — the institutional AI sandbox.  One shared control plane (Keycloak, LiteLLM + ledger, OpenBao escrow, registrar, usage-mcp, Caddy edge) and one LibreChat instance per course.  See [README.md](README.md) for the architecture and [docs/registrar-spec.md](docs/registrar-spec.md) for how courses get provisioned.

**The name is deliberate on both sides.** The public brand is **aLLManac** (the LLM is baked into the middle on purpose); the board channel is **#almanac**.  Neither is a typo of the other — don't "correct" either direction.  **But no reader-facing page says either.**  `apex/`, the guide prompts and the eval cases write `{{PLATFORM}}`, and `PLATFORM_NAME` in `.env` names it per deployment; `just docs-corpus` fails on a hard-coded name ([pedagogy-authoring.md](docs/pedagogy-authoring.md#the-corpus-boundary)).

---

## Before you research anything: read [docs/design-walls.md](docs/design-walls.md)

That file is a list of **walls** — questions already answered the expensive way (two research agents, an empirical rig, several red pipelines).  If your task touches any of the following, the answer is already written down and re-deriving it is pure waste:

- **vLLM tool parsers** — they are per model family; there is no universal one
- **LibreChat agent-share groups** — they can never come from the Keycloak OIDC `groups` claim
- **The LibreChat admin panel** — why its port isn't 3081, and why its session cookie is `Secure` by default with no `trust proxy` trap
- **The classroom posture** — sharing is off by default; what turns it on
- **MCP wiring** — the trailing-slash 307, the SSRF allowlist, and why "0 tools" at boot is correct
- **A course's `modelSpecs`** — any spec list silently defaults `modelSelect`, `parameters` and `presets` to false, which empties the picker, agents included; the render sets all three explicitly
- **`actions.allowedDomains`** — it is top-level, not under `endpoints`; an empty list is *no allowlist*, not deny-all; capability names are never validated by LibreChat and typos fail closed and silent
- **LiteLLM free vs. Enterprise** — especially **UI SSO dies past 5 total DB users**, and rotation is delete+mint because `/key/regenerate` is paid
- **Key attribution** — `user_id` must be the email, and why
- **opencode** — image org, provider shape, and the ≥16k context floor
- **`fastmcp`** — `get_http_headers()` silently strips `authorization`
- **`just`** — `dotenv-load` snapshots `.env` at invocation start, and it dedents recipe bodies (heredocs must stay indented)
- **Keycloak realm import** — it runs every boot and skips only realms that already exist, so renaming a realm file mints a second realm on a live box
- **Mounts** — never bind-mount a single file that gets rewritten; OpenBao rafts into `/openbao/file` or crash-loops
- **Reboots** — `depends_on` is ignored on a reboot, so LibreChat loses its one-shot OIDC discovery race with Keycloak and sign-in 500s behind a green `smoke`; `just oidc-settle` is the probe and the repair
- **Changing `registrar/render.py`** — `just deploy` does not re-render the fleet, so the change is inert until `just render`; `just render-check` is the guard that goes red when you owe it a run
- **Verifying on the box** — the prod-probe pattern, so no credential moves
- **Orchestration** — compose now, k3s short-term, inference fleet first

If you find a wall is wrong, fix it in `design-walls.md` **in the same commit** that fixes the system.  A stale wall is worse than no wall.

---

## Two leads, one seam

- **Plumbing (@geordi)** — anything that pins, deploys, escrows, or meters: stacks, registrar operation, trust models, capacity, backups.
- **Pedagogy (@piper)** — anything a student or professor *reads*: the guides, front-door verbiage, agent instructions, the Ask-the-Almanac corpus.

Ambiguous artifacts sort **by audience**: reader is an operator → plumbing; reader is faculty or a student → pedagogy.  When doc and system disagree, **the system is the truth and the word changes.**

The failure mode here is **doc-drift**, so the tether runs both ways: a change in behavior (a port, a role, a flow) pings the docs in the same breath, and a wording change that implies behavior pings the plumbing.

The registrar and course fleet are **@marco's** code — he remains author-of-record, and registrar *design* changes go to him.  Operation, deploys, and pins are the plumbing lane.

---

## Conventions

- **All deployment logic lives in the [`justfile`](justfile).**  CI is a thin wrapper — `ssh box && just sync && just deploy`.  Don't put deploy logic in a pipeline file; see [docs/ci.md](docs/ci.md).  **What to run *after* a deploy is [docs/post-deploy.md](docs/post-deploy.md)** — the sequence, the three conditional follow-ups, and what red means.  [docs/admin-guide.md](docs/admin-guide.md) is the reference for when you already know what you're looking for.
- **`fleet/` and `usage-mcp/roster.yaml` are renders**, not sources.  The registrar rewrites them on every reconcile, and they open with a "GENERATED by the registrar" header.  Edit `registrar/courses.yaml` or the templates in `registrar/render.py` — never the output.
- **`registrar/courses.yaml` is the source, not a render.**  It is the operator's file and the authority the registrar reads for every course — who teaches it, who's enrolled, what it may spend (`registrar/server.py`).  It's gitignored because real rosters are student emails, *not* because it's generated; `just up` seeds it from the tracked `registrar/courses.example.yaml`, and the roster tools write `students:` back into it.  Edit it freely — that's the front door — but the registrar rewrites it normalized on every change it makes, so comments and keys it doesn't recognize are discarded; the header it writes says so.
- **Tracked files are the platform; `site/` is one box.**  `site/` is gitignored and cloned from `site.example/` by `just _site`; `just` layers `site/compose.yml` onto the core stack with a second `-f`, so it can add services *and* override core ones.  Editing `site.example/` changes no existing deployment.  If you're about to edit a tracked file to make one box work, you want `site/` — see [docs/design-walls.md](docs/design-walls.md).
- **The registrar's reconcile plane is `registrar/planes/`** — one module per system, `reconcile.py` as the facade.  A verb may compose planes; a plane may never import a sibling plane.
- **Tracked files name no hosts.**  The repo publishes to a public GitHub, so a box is "the docker host" (or "the canary docker host" for the `latest` canary), never its hostname, and examples use RFC1918 or `example.edu` addresses rather than real ones.  Board posts and `site/` can say which box; git can't.
- **Generated files say so in a header comment.**  If you're editing a file that opens with "GENERATED by the registrar," you're in the wrong file.
- Prose style: em dashes, double spaces after periods.  Match the surrounding docs.
- **One line per paragraph — let the editor wrap.**  No hard column breaks in prose; the same rule applies inside list items, blockquotes, and admonition bodies.  What stays on its own line is structure that means something: headings, tables, fences, front matter, and an admonition's `!!! type "title"` marker — its body is indented beneath it, never joined onto it, or the box renders as a literal paragraph.
