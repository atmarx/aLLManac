"""Environment and constants — the settings every other plane reads.

Read once at import, exactly as they were when this lived at the top of
reconcile.py.  Nothing here *uses* a credential; it only names where one
comes from, which is why this is the one plane that everything else may
import.
"""

import os
import re

COURSES_PATH = os.environ.get("REGISTRAR_COURSES", "/app/courses.yaml")

KC_URL = os.environ.get("KC_URL", "http://keycloak:8080")
KC_REALM = os.environ.get("KC_REALM", "northwinds")
KC_ADMIN = os.environ.get("KC_ADMIN", "admin")
KC_ADMIN_PASSWORD = os.environ.get("KC_ADMIN_PASSWORD", "")

LITELLM_URL = os.environ.get("LITELLM_URL", "http://litellm:4000")
LITELLM_MASTER_KEY = os.environ.get("LITELLM_MASTER_KEY", "")

BAO_ADDR = os.environ.get("BAO_ADDR", "http://openbao:8200")
BAO_ROLE_ID = os.environ.get("BAO_REGISTRAR_ROLE_ID", "")
BAO_SECRET_ID = os.environ.get("BAO_REGISTRAR_SECRET_ID", "")
BAO_MOUNT = os.environ.get("BAO_MOUNT", "almanac")

ALMANAC_DOMAIN = os.environ.get("ALMANAC_DOMAIN", "localhost")

DEFAULT_FUSE = float(os.environ.get("REGISTRAR_DEFAULT_FUSE", "5"))
MAX_FUSE = float(os.environ.get("REGISTRAR_MAX_FUSE", "25"))
DEFAULT_COURSE_BUDGET = float(os.environ.get("REGISTRAR_DEFAULT_COURSE_BUDGET", "1000"))
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
