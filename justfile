# The aLLManac — deployment contract.
# Every recipe here runs the same on a laptop, xdocker03, or your cloud box.
# CI (Woodpecker/GitLab/GitHub) is just a thin wrapper that ssh's in and calls
# these — see .woodpecker/deploy.yml and docs/ci.md.

set shell := ["bash", "-euo", "pipefail", "-c"]
set dotenv-load := true

compose := "docker compose"
# The vLLM stack is separate on purpose (model stays loaded across app
# deploys).  --project-directory . makes it share the root .env.
vllm := "docker compose --project-directory . -f vllm/compose.yml"

# List recipes
default:
    @{{just_executable()}} --list --unsorted

# First-time setup: create .env from the example + generate every secret
setup: _env secrets
    @echo
    @echo "Now edit .env — set ALMANAC_HOST, INFERENCE_BASE_URL, and OPENID_ISSUER."

_env:
    @test -f .env || (cp .env.example .env && echo ".env created from .env.example")

# Generate secrets for any value still reading "change-me" (NEVER touches set values)
secrets:
    #!/usr/bin/env bash
    set -euo pipefail
    f=.env
    test -f "$f" || { echo "no .env — run: just setup"; exit 1; }
    fill() {  # fill VAR VALUE — only if VAR is still a change-me placeholder
        if grep -q "^${1}=.*change-me" "$f"; then
            sed -i "s|^${1}=.*|${1}=${2}|" "$f"
            echo "  ${1}  — generated"
        else
            echo "  ${1}  — already set, left alone (pinned)"
        fi
    }
    fill LITELLM_MASTER_KEY   "sk-$(openssl rand -hex 24)"
    fill LITELLM_DB_PASSWORD  "$(openssl rand -hex 16)"
    fill JWT_SECRET           "$(openssl rand -hex 32)"
    fill JWT_REFRESH_SECRET   "$(openssl rand -hex 32)"
    fill CREDS_KEY            "$(openssl rand -hex 32)"
    fill CREDS_IV             "$(openssl rand -hex 16)"
    fill MEILI_MASTER_KEY     "$(openssl rand -hex 16)"
    fill RAG_DB_PASSWORD      "$(openssl rand -hex 16)"
    fill OPENID_SESSION_SECRET "$(openssl rand -hex 32)"
    fill KC_ADMIN_PASSWORD    "$(openssl rand -hex 12)"
    fill KC_DB_PASSWORD       "$(openssl rand -hex 16)"
    echo
    echo "CREDS_KEY/CREDS_IV are now PINNED — never regenerate them on a live"
    echo "instance or every user's saved key becomes undecryptable."

# Bring the stack up (profiles come from COMPOSE_PROFILES in .env)
up:
    {{compose}} up -d --remove-orphans

# Stop the stack (data survives)
down:
    {{compose}} down

# Stop + WIPE ALL DATA (volumes included) — asks first
nuke:
    #!/usr/bin/env bash
    read -r -p "This deletes ALL almanac data (chats, keys, users, model cache). Type 'yes': " a
    [ "$a" = "yes" ] && {{compose}} down -v || echo "aborted"

# Pull current images
pull:
    {{compose}} pull

# Build local images (the edge Caddy, when that profile is on)
build:
    {{compose}} build

# What CI runs on the box: refresh images, build, restart, verify
deploy: pull build up smoke

# Sync the checkout to origin/main (destructive to local edits — it's a deploy box)
sync:
    git fetch origin
    git reset --hard origin/main
    @echo "synced to $(git rev-parse --short HEAD)"

# Prove the stack is actually serving (not just "containers exist")
smoke:
    #!/usr/bin/env bash
    set -uo pipefail
    fail=0
    check() {  # check NAME URL — retries ~90s so cold boots (Keycloak realm
               # import, first pulls) don't read as failures
        for i in $(seq 1 18); do
            if curl -fso /dev/null --max-time 10 "$2"; then
                echo "  ok    $1"
                return
            fi
            sleep 5
        done
        echo "  FAIL  $1  ($2)"
        fail=1
    }
    echo "smoke:"
    check "librechat (UI)"     "http://localhost:${CHAT_PORT:-3080}/"
    check "litellm (gateway)"  "http://localhost:${GATEWAY_PORT:-4000}/health/liveliness"
    check "keycloak (realm)"   "http://localhost:${AUTH_PORT:-8080}/realms/${KC_REALM:-northwinds}/.well-known/openid-configuration"
    exit $fail

# Show container status
ps:
    {{compose}} ps
    @{{vllm}} ps 2>/dev/null || true

# ---- Local inference (its own stack: vllm/compose.yml) -----------------------
# Separate so the model stays loaded while the app stack deploys/bounces.
# Needs the NVIDIA Container Toolkit.  Same .env drives it (VLLM_* vars).

# Start local vLLM (first boot downloads the model — be patient)
vllm-up:
    {{vllm}} up -d

# Stop local vLLM (unloads the model; app stack is untouched)
vllm-down:
    {{vllm}} down

# Tail vLLM logs (watch a cold model load here)
vllm-logs:
    {{vllm}} logs -f --tail=100

# Pull the pinned vLLM image
vllm-pull:
    {{vllm}} pull

# Prove inference is actually serving (health + the model list)
vllm-smoke:
    #!/usr/bin/env bash
    set -uo pipefail
    for i in $(seq 1 18); do
        if curl -fso /dev/null --max-time 10 "http://localhost:${VLLM_PORT:-8000}/health"; then
            echo "  ok    vllm /health"
            curl -fs "http://localhost:${VLLM_PORT:-8000}/v1/models" | python3 -m json.tool
            exit 0
        fi
        sleep 5
    done
    echo "  FAIL  vllm (http://localhost:${VLLM_PORT:-8000}/health) — cold model loads take minutes: just vllm-logs"
    exit 1

# Tail logs (all services, or one: just logs librechat)
logs svc="":
    {{compose}} logs -f --tail=100 {{svc}}

# ---- Keys & accounting -------------------------------------------------------
# `owner` is REQUIRED: the org unit that answers for the spend (class/lab slug,
# e.g. engr301 or coe-materials-vexlab).  It's stamped into the key's metadata +
# spend tags so monthly usage rolls up to an owner — the join key the
# accounting/FOCUS export will consume later.  No owner, no key.

# Mint a per-user virtual key:  just key stu.amaya engr301 [budget]
# NOTE: the owner tag lives in metadata.tags — top-level `tags` is a LiteLLM
# ENTERPRISE feature (403 license wall).  metadata.tags rolls up to
# /spend/tags in OSS, a beat behind realtime (spend logs aggregate async).
key user owner budget="5":
    @curl -sf http://localhost:${GATEWAY_PORT:-4000}/key/generate \
      -H "Authorization: Bearer ${LITELLM_MASTER_KEY}" \
      -H "Content-Type: application/json" \
      -d '{"models": ["almanac-chat"], "max_budget": {{budget}}, "user_id": "{{user}}", "metadata": {"owner": "{{owner}}", "tags": ["owner:{{owner}}"]}}' \
      | python3 -m json.tool
    @echo "minted for {{user}} — owner {{owner}}, budget \${{budget}}"

# Spend grouped by owner tag (the month-to-date "who used what")
spend:
    @curl -sf "http://localhost:${GATEWAY_PORT:-4000}/spend/tags" \
      -H "Authorization: Bearer ${LITELLM_MASTER_KEY}" \
      | python3 -m json.tool || echo "(older LiteLLM builds: use the admin UI -> Usage)"
