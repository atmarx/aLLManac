"""Environment and constants — the settings every other plane reads.

Read once at import, exactly as they were when this lived at the top of
reconcile.py.  Nothing here *uses* a credential; it only names where one
comes from, which is why this is the one plane that everything else may
import.
"""

import os
import re

COURSES_PATH = os.environ.get("REGISTRAR_COURSES", "/app/courses.yaml")
# Nominations live beside the course records: the same state volume, the
# same "gitignored because it names people" reason.
NOMINATIONS_PATH = os.environ.get(
    "REGISTRAR_NOMINATIONS",
    os.path.join(os.path.dirname(COURSES_PATH), "nominations.yaml"))
# Problem reports, same volume and the same reason — the record quotes a
# person and names their course.
REPORTS_PATH = os.environ.get(
    "REGISTRAR_REPORTS",
    os.path.join(os.path.dirname(COURSES_PATH), "reports.yaml"))
# Environment requests from the front office's open door — same volume,
# same reason (they name the person asking).
REQUESTS_PATH = os.environ.get(
    "REGISTRAR_REQUESTS",
    os.path.join(os.path.dirname(COURSES_PATH), "requests.yaml"))
# The boundary question the request desk asks before filing.  Deployment
# config: front-door.md if the operator wrote one, else the shipped example
# (both sit on the state volume, which is ./registrar on the host).
FRONT_DOOR_PATHS = [
    os.path.join(os.path.dirname(COURSES_PATH), "front-door.md"),
    os.path.join(os.path.dirname(COURSES_PATH), "front-door.example.md"),
]

# Notifications (planes/notify.py).  All optional: with nothing set, mail is
# appended to the outbox file on the state volume and the desk is "emailed"
# there too — nothing is lost, and nothing leaves the box.
#   SMTP_TLS: none (plain, e.g. a campus relay that trusts the box's IP),
#   starttls, or ssl (implicit TLS, usually port 465).  Defaults to starttls
#   when a user is set, none otherwise.
SMTP_HOST = os.environ.get("SMTP_HOST", "").strip()
SMTP_PORT = int(os.environ.get("SMTP_PORT", "") or 25)
SMTP_USER = os.environ.get("SMTP_USER", "").strip()
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
SMTP_TLS = (os.environ.get("SMTP_TLS", "").strip().lower()
            or ("starttls" if SMTP_USER else "none"))
OUTBOX_PATH = os.environ.get(
    "REGISTRAR_OUTBOX",
    os.path.join(os.path.dirname(COURSES_PATH), "outbox.log"))
# teams (a Workflows "when a webhook request is received" URL) or text
# (anything that takes {"text": ...} — Slack, Mattermost).  The URL is a
# credential: anyone holding it can post to the channel.
NOTIFY_WEBHOOK_URL = os.environ.get("NOTIFY_WEBHOOK_URL", "").strip()
NOTIFY_WEBHOOK_FORMAT = (os.environ.get("NOTIFY_WEBHOOK_FORMAT", "").strip().lower()
                         or "teams")

KC_URL = os.environ.get("KC_URL", "http://keycloak:8080")
KC_REALM = os.environ.get("KC_REALM", "classroom")
KC_ADMIN = os.environ.get("KC_ADMIN", "admin")
KC_ADMIN_PASSWORD = os.environ.get("KC_ADMIN_PASSWORD", "")

LITELLM_URL = os.environ.get("LITELLM_URL", "http://litellm:4000")
LITELLM_MASTER_KEY = os.environ.get("LITELLM_MASTER_KEY", "")

# The chat databases — one Mongo, one database per instance.  No credential
# (unauthenticated on the compose network, reachable by nothing else); the
# census plane reads it and reads only the envelope.  See planes/chatdb.py.
MONGO_URI = os.environ.get("MONGO_URI", "mongodb://mongodb:27017")

BAO_ADDR = os.environ.get("BAO_ADDR", "http://openbao:8200")
BAO_ROLE_ID = os.environ.get("BAO_REGISTRAR_ROLE_ID", "")
BAO_SECRET_ID = os.environ.get("BAO_REGISTRAR_SECRET_ID", "")
BAO_MOUNT = os.environ.get("BAO_MOUNT", "almanac")

ALMANAC_DOMAIN = os.environ.get("ALMANAC_DOMAIN", "localhost")
# Who notification mail is from.  A campus relay that trusts the box's IP
# usually still wants a From in a domain it recognises — set it if so.
SMTP_FROM = (os.environ.get("SMTP_FROM", "").strip()
             or f"aLLManac <noreply@{ALMANAC_DOMAIN}>")
# The flagship's hostname — the front door every notification links to,
# and what validate_courses checks to refuse minting courses at
# <slug>.localhost on a box that clearly isn't one.
CHAT_HOST = os.environ.get("CHAT_HOST", "chat.localhost")
# The gateway's public name — what a student points opencode at.  my_key
# says it, so nobody has to find it on a page.
GATEWAY_HOST = os.environ.get("GATEWAY_HOST", "").strip()
# Evaluation identities (scripts/run_evals.py) live on the reserved .invalid
# TLD, which no IdP can assert.  The tool plane rehearses their writes, the
# fixture resets their tickets, and notifications never go to them.
REHEARSAL_DOMAIN = "@almanac.invalid"

DEFAULT_FUSE = float(os.environ.get("REGISTRAR_DEFAULT_FUSE", "5"))
MAX_FUSE = float(os.environ.get("REGISTRAR_MAX_FUSE", "25"))
# Below this a key can't fund a short working session, so minting one just
# produces a credential that looks broken.  PLACEHOLDER — nobody has measured
# what a real half-hour opencode session costs against our packs; measure it
# and set this from the ledger rather than from taste.
MIN_FUSE = float(os.environ.get("REGISTRAR_MIN_FUSE", "1"))
DEFAULT_COURSE_BUDGET = float(os.environ.get("REGISTRAR_DEFAULT_COURSE_BUDGET", "1000"))

# The context window rendered into every course instance.  Without it
# LibreChat falls back to its own default for a model it does not recognise
# — measured at ~28k against a model that actually serves 922k
# (docs/admin-guide.md) — an undocumented number, nobody's choice, free to
# move on a version bump.  Same shape as a floating image tag.
#
# 128k is the operator's number (@xram, 2026-09-21), and it is a CAP rather
# than a capability claim: it bounds what a single conversation can spend on
# a metered model, well under what the large hosted models serve.
#
# Deliberately NOT a model -> window table.  `almanac-chat` is an ALIAS
# resolved per deployment (`litellm/config.yaml` maps it to
# os.environ/INFERENCE_MODEL), so the registrar cannot know the real window
# from the name, and a table keyed on it would be this service claiming
# knowledge about a model chosen on the far side of INFERENCE_BASE_URL.
# That is the seam the platform is not allowed to cross (design-walls.md,
# "The Almanac consumes inference; it does not manage it").  The operator
# knows what their endpoint serves; a course record can say so.
#
# NOTE THE DIRECTION, because this default is deliberately NOT the cautious
# one.  Too small truncates a conversation sooner — degraded, still working.
#
# Too large is worse than it first looks, and NOT reliably an error.  Some
# backends reject an over-long prompt, which is loud and fine.  **Ollama —
# what INFERENCE_BASE_URL points at by default — silently truncates the
# FRONT of the prompt and answers anyway**, and the front of the prompt is
# the system prompt.  A course agent quietly loses its instructions and its
# boundary mid-conversation and keeps talking, with nothing in any log an
# operator reads.  That is not a degraded answer, it is the guardrails
# leaving and the fabrication the agent contract exists to prevent.  Measured
# on xdocker03 2026-09-21: the endpoint serves 32768 while the model itself
# allows 262144, so the ceiling is the SERVER's, not the model's.
# At 128k this default is larger than many self-hosted models serve, so **a
# course whose models resolve to a small local endpoint must set
# `context_tokens:` in its own record** — the err-low rule now lives per
# course rather than in this constant, which is the trade the operator made
# knowingly.  The registrar cannot make it for them: `almanac-chat` is an
# alias and what it resolves to is on the far side of INFERENCE_BASE_URL.
#
# This was 28000 until 2026-09-21, chosen to match LibreChat's own fallback
# so the change was a no-op.  It is no longer a no-op: raising it makes every
# rendered course stale until `just render`, and render-check says so.
DEFAULT_CONTEXT_TOKENS = int(
    os.environ.get("REGISTRAR_DEFAULT_CONTEXT_TOKENS", "128000"))
BASE_MODELS = [
    model.strip()
    for model in os.environ.get("REGISTRAR_BASE_MODELS", "almanac-chat").split(",")
    if model.strip()
]

# Agent-builder powers a course's instance gets.  `actions` (arbitrary-URL
# tool calls) is EXCLUDED — it's the one path around the gateway's
# guardrails and metering (docs/registrar-spec.md, "The floor").  This is
# the single source of truth: the render plane imports it from here rather
# than keeping the hand-built copy it used to carry.
DEFAULT_CAPABILITIES = ["file_search", "tools", "artifacts"]

# What LibreChat accepts in `endpoints.agents.capabilities` on our pin.  This
# is NOT a whitelist we enforce — the legal set is LibreChat's and moves per
# version, so a registrar that blocked unknown names would be the thing
# stopping an operator from using a capability their image already supports.
# It exists so `course_admin validate` can SAY "file_serach isn't a thing."
# A typo fails closed (the capability simply doesn't appear), which is safe
# and completely silent — silence is the bug this list fixes, not
# permissiveness.  Bump it when the LIBRECHAT_IMAGE pin moves.
KNOWN_CAPABILITIES = [
    "file_search", "tools", "artifacts", "actions", "ocr",
    "execute_code", "web_search", "memory", "context", "chain",
]

# Course slugs become hostnames (`<slug>.<domain>`), container names, and the
# Keycloak clientId.  The hostname is the strictest of the three, so it sets
# the rule — catching this at validate time beats catching it halfway through
# a provisioning run that already minted a key.
SLUG_RE = re.compile(r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?$")
EMAILISH_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$")
