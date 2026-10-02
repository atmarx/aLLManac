---
title: What can a deployment rename?
description: Every name a student, instructor or operator sees — the platform, the chat model, labels, hostnames — where each is set, and which ones are only safe to choose before the first boot.
audience: operator
status: draft
owner: geordi
tags: [rendered-config, librechat, litellm, keycloak]
tethered_to:
  - .env.example
  - litellm/config.yaml
  - librechat/librechat.yaml
  - registrar/render.py
  - docs/corpus.py
  - docs/mkdocs_hooks.py
---

# What can a deployment rename?

The project is called the aLLManac, and nothing a reader sees has to say so.  An institution running it under its own name sets that name once in `.env`, and the help site, the guides' knowledge, the guides' prompts and the model students type into a harness all follow.

**Decide the names before the first `just up`.**  Most of them can change any time with a rebuild, but four are written into data the moment they're used — conversations, agents, keys, course records — and renaming those on a box with history strands what's already there.  The tables say which is which.  A test box you'll tear down doesn't matter; a production box does.

## What students and faculty see

| Setting | What it names | Default | Change later? |
|---|---|---|---|
| `PLATFORM_NAME` | The platform, everywhere a reader meets it: every help-site page, the guides' knowledge files, their prompts and eval cases, each guide's picker description and owner name, what the tool servers say in their replies and refusals, the subject and sender of the registrar's mail, export downloads (`ai-classroom-<course>-<date>.zip`) and the README inside them, each course's client name in Keycloak, and the upgrade page the edge shows while a service restarts. | `aLLManac` | Yes — `just deploy` rebuilds the site and corpus, refreshes the guides, and restarts the tool servers and the edge.  Two are written once, at creation, so they change on a fresh box only: the guides' owner name and each course's Keycloak client name. |
| `CHAT_MODEL` | The chat model's public name: what LiteLLM serves, what the picker shows, what every harness snippet in the help site says, the model new courses and the guides get. | `almanac-chat` | **Fresh box only.**  Every course record and every minted key carries the name in its model list. |
| `MODEL_PROVIDER_NAME` | The endpoint label in each course chat's picker, and the front door's endpoint the guides run on — the site copy of the front door's config has to name its endpoint this. | `Almanac` | **Fresh box only.**  Conversations remember the endpoint they were held on, and a renamed endpoint leaves them pointing at nothing. |
| `MCP_SERVER_PREFIX` | The tool-server names (`<prefix>-usage`, `<prefix>-courses`): declared in each course's config, where staff can attach them to an agent, and in the front door's, where the guides carry them — the site copy has to use the same two keys. | `almanac` | **Fresh box only.**  An agent stores its tools by server name, so every agent that uses them would lose them. |
| `APP_TITLE` | The front door's browser tab and sign-in page.  Courses are titled with their own course name, always. | `aLLManac` | Yes, at the next restart of the front door. |
| `OPENID_BUTTON_LABEL` | The sign-in button. | `Sign in with Campus SSO` | Yes.  Courses take the button text from the render, so run `just render` too. |
| `ALMANAC_FALLBACK_ASSISTANT` | Where the guides send a question that isn't about the platform — in words your readers recognize, like the general assistant your institution licenses. | a generic description | Yes — `just deploy`. |
| `DOCS_SITE_NAME` | The help site's title, when it should differ from `PLATFORM_NAME`.  Leave it unset otherwise; set to empty, it breaks the site build. | unset — `PLATFORM_NAME` | Yes. |
| `DOCS_SITE_URL` | Where the help site lives, for its canonical links. | `http://localhost/help/` | Yes. |
| `DOCS_COPYRIGHT` | The help site's footer (HTML allowed). | the project's CC BY 4.0 credit | Yes.  If you rewrite the pages, the license asks you to keep the attribution and say they were changed. |
| `SMTP_FROM` | The sender on mail the registrar sends (export links, request updates). | unset — no mail | Yes. |

`DOCS_PRODUCT_NAME` still works as an older spelling of `PLATFORM_NAME`.  `AGENT_MODEL` and `REGISTRAR_BASE_MODELS` both default to `CHAT_MODEL`; set them only when a site serves more than one model.

## Where people find it

| Setting | What it is | Change later? |
|---|---|---|
| `ALMANAC_DOMAIN` | Every course lives at `<course>.<domain>`, and its admin panel at `<course>-admin.<domain>`. | **Fresh box only.**  Sign-in redirect addresses, certificates and every course's rendered config carry it. |
| `CHAT_HOST`, `AUTH_HOST`, `GATEWAY_HOST` | The front door, the sign-in system, and the gateway students point a harness at. | **Fresh box only**, for the same reason.  `AUTH_HOST` is also inside every token's issuer. |
| `KC_REALM` | The sign-in realm's name, which appears in sign-in URLs.  **Leave it at `classroom`** unless you have a reason: the realm file (`keycloak/realm-classroom.json`) and every `OPENID_ISSUER` in `.env` say `classroom` too, and all three have to change together. | **Fresh box only.**  Keycloak imports a realm file it hasn't seen as a *second* realm on a live box (`docs/design-walls.md`, Keycloak realm import). |

The realm's **display name** and the **sign-in page's look** are set in Keycloak itself — Realm settings → General, and Realm settings → Themes.  They can change any time.

## Set somewhere other than `.env`

- **The front door's own config.**  Every deployment with guides keeps its own copy at `site/librechat/librechat.yaml` (`docs/admin-guide.md` has the procedure), and LibreChat doesn't substitute variables into the parts that hold names.  Edit them there: the endpoint's `name`, which must equal `MODEL_PROVIDER_NAME`; its `modelDisplayLabel`; `models.default` and `titleModel`, which must equal `CHAT_MODEL`; and the two `mcpServers` keys, which must be `<MCP_SERVER_PREFIX>-usage` and `<MCP_SERVER_PREFIX>-courses`.  The guides are seeded against those names, and `just agents-check` fails on any that differ.
- **Courses.**  `registrar/courses.yaml` is seeded from the example on first `up`.  Replace the example courses with yours before provisioning any.  A course without a `models:` list gets `CHAT_MODEL` (or `REGISTRAR_BASE_MODELS`), so leave it out unless a course needs a model the others don't.
- **More models.**  Each is an entry in `litellm/config.yaml`.  A name there can come from the environment the same way the chat model's does (`model_name: os.environ/YOUR_VAR`); LiteLLM resolves it anywhere in that file.

## What stays named after the project

Readers never see these, and renaming them buys nothing: container names (`alm-*`), database names, the escrow's mount (`BAO_MOUNT`), Keycloak flow names, the guides' service account (`guides@almanac.invalid`), and the operator docs in `docs/`, which document the software by its name.  The Platform, Security and Operator Guides draw on some of those docs, so their answers can mention the project — that's attribution, not branding.

## How the names stay out of the pages

Pages in `apex/`, the guides' prompts and their eval cases never spell out the platform or the model.  They say `{{PLATFORM}}` and `{{MODEL}}`, and the site build and `just docs-corpus` fill them from `PLATFORM_NAME` and `CHAT_MODEL`.  The tool servers name the platform from `PLATFORM_NAME` in code, and `docs-corpus` reads their strings too: every tool description, refusal, export README and mail subject in `registrar/server.py`, `usage-mcp/server.py`, `registrar/planes/exports.py` and `registrar/planes/notify.py`.  `docs-corpus` refuses to render if any of those sources names either outright, so a slip fails the build on the project's own box instead of reaching another institution's students.  The rule for writers is in [pedagogy-authoring.md](pedagogy-authoring.md#the-corpus-boundary).

## A fresh box, in order

1. Pick the names: `PLATFORM_NAME`, `CHAT_MODEL`, `MODEL_PROVIDER_NAME`, `MCP_SERVER_PREFIX`, `APP_TITLE`, and the hostnames.
2. Set them in `.env` with everything else `just setup` asks for, before the first `just up`.  Quote any value with a space in it (`PLATFORM_NAME="AI Classroom"`) — `just` refuses an `.env` it can't parse, and every recipe fails with it.
3. Replace the example courses in `registrar/courses.yaml` with yours.  Leave out `models:` and they get `CHAT_MODEL`.
4. Make the site copy of the front door's config and rename what's in it to match (the list under "Set somewhere other than `.env`"): endpoint name, label, model names, the two `mcpServers` keys.  Then seed the guides, paste their ids into it, and restart the front door — `docs/admin-guide.md` has the procedure.  `just agents-check` is the proof: it fails on any name that doesn't match.
5. Set the realm's display name and theme in Keycloak.
6. Open the help site and ask the Student Guide what this platform is called.  If the answer is your name, the corpus took it.
