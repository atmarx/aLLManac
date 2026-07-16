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
# SBOM generator — pinned like everything else:
syft := "anchore/syft:v1.46.0@sha256:473a60e3a58e29aca3aedb3e99e787bb4ef273917e44d10fcbea4330a07320bb"

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
    fill() {  # fill VAR VALUE — generate if placeholder, APPEND if the var is
              # missing entirely (an .env older than the var), never touch a
              # value that's set.  This is how old .envs migrate on deploy.
        if grep -q "^${1}=.*change-me" "$f"; then
            sed -i "s|^${1}=.*|${1}=${2}|" "$f"
            echo "  ${1}  — generated"
        elif ! grep -q "^${1}=" "$f"; then
            echo "${1}=${2}" >> "$f"
            echo "  ${1}  — missing (new since this .env was created), added"
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
    fill ADMIN_PANEL_SESSION_SECRET "$(openssl rand -hex 32)"
    fill USAGE_MCP_TOKEN      "$(openssl rand -hex 32)"
    fill USAGE_DB_PASSWORD    "$(openssl rand -hex 16)"
    fill KC_ADMIN_PASSWORD    "$(openssl rand -hex 12)"
    fill KC_DB_PASSWORD       "$(openssl rand -hex 16)"
    # Fixed-value vars introduced after older .envs were created — appended if
    # missing, same never-touch rule.  Values mirror .env.example:
    fill OPENID_ADMIN_ROLE                "faculty"
    fill OPENID_ADMIN_ROLE_PARAMETER_PATH "realm_access.roles"
    fill OPENID_ADMIN_ROLE_TOKEN_KIND     "access"
    echo
    echo "CREDS_KEY/CREDS_IV are now PINNED — never regenerate them on a live"
    echo "instance or every user's saved key becomes undecryptable."

# Bring the stack up (profiles come from COMPOSE_PROFILES in .env)
up: _roster && usage-role
    {{compose}} up -d --remove-orphans

# The live roster is deployment data (student emails) — gitignored, seeded
# from the example on first up, edited in place after (picked up live):
_roster:
    @test -f usage-mcp/roster.yaml || (cp usage-mcp/roster.example.yaml usage-mcp/roster.yaml \
      && echo "usage-mcp/roster.yaml created from the example — put your real courses in it")

# The usage service reads the ledger through usage_ro — the master key never
# enters that container.  USAGE_DB_PASSWORD is hex, so inlining is quote-safe.
# Provision usage_ro, the SELECT-only ledger role (idempotent; rides `just up`)
usage-role:
    #!/usr/bin/env bash
    set -euo pipefail
    if [ -z "${USAGE_DB_PASSWORD:-}" ]; then
        echo "usage-role: USAGE_DB_PASSWORD not in .env yet — run: just secrets"
        exit 0
    fi
    # </dev/null matters: CI pipes this whole deploy over ssh as a heredoc,
    # and a bare `exec -T` would eat the remaining script as its stdin
    # (the psql below is safe — its stdin IS the SQL heredoc):
    for i in $(seq 1 18); do
        {{compose}} exec -T litellm-db pg_isready -U litellm -q </dev/null 2>/dev/null && break
        sleep 5
    done
    {{compose}} exec -T litellm-db psql -q -U litellm -d litellm <<SQL
    SELECT 'CREATE ROLE usage_ro LOGIN'
      WHERE NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'usage_ro') \gexec
    ALTER ROLE usage_ro LOGIN PASSWORD '${USAGE_DB_PASSWORD}';
    GRANT CONNECT ON DATABASE litellm TO usage_ro;
    GRANT USAGE ON SCHEMA public TO usage_ro;
    GRANT SELECT ON ALL TABLES IN SCHEMA public TO usage_ro;
    ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO usage_ro;
    SQL
    echo "usage_ro — provisioned (SELECT-only on the ledger)"

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

# What CI runs on the box: refresh images, build, complete .env, restart, verify
# (`secrets` here is the .env migration path: vars introduced by an upgrade get
# appended/generated; values you've set are never touched.)
deploy: pull build secrets up smoke

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
    check "admin panel"        "http://localhost:${ADMIN_PANEL_PORT:-3081}/"
    check "litellm (gateway)"  "http://localhost:${GATEWAY_PORT:-4000}/health/liveliness"
    check "usage-mcp (stats)"  "http://127.0.0.1:${USAGE_MCP_PORT:-8090}/health"
    check "keycloak (realm)"   "http://localhost:${AUTH_PORT:-8080}/realms/${KC_REALM:-northwinds}/.well-known/openid-configuration"
    exit $fail

# Show container status
ps:
    {{compose}} ps
    @{{vllm}} ps 2>/dev/null || true

# Images already on this box scan from the daemon (fast, no pull); absent
# ones stream from the registry WITHOUT touching the daemon (the vLLM image
# is many GB — generate its SBOM on the GPU box, or budget the stream).
# Rerun at pin-bump time; artifacts land in sbom/ (gitignored) + a tarball.
# SBOMs (SPDX JSON) for every image, both stacks — to file with infosec
sbom:
    #!/usr/bin/env bash
    set -euo pipefail
    rev=$(git describe --always --dirty)
    stamp=$(date -u +%Y-%m-%d)
    outdir="sbom/${stamp}-${rev}"
    mkdir -p "$outdir"
    images=$( (COMPOSE_PROFILES=edge,workbench {{compose}} config --images; \
               {{vllm}} config --images) | sort -u )
    {
        echo "aLLManac SBOM manifest"
        echo "generated: $(date -u +%Y-%m-%dT%H:%M:%SZ)   git: ${rev}"
        echo
    } > "$outdir/MANIFEST.txt"
    for img in $images; do
        safe=$(echo "$img" | tr '/:@' '___')
        if docker image inspect "$img" >/dev/null 2>&1; then
            src="$img"; how="daemon"
            digest=$(docker image inspect --format '{{{{if .RepoDigests}}{{{{index .RepoDigests 0}}{{{{end}}' "$img")
        else
            src="registry:$img"; how="registry"
            digest="(digest recorded inside the SBOM)"
        fi
        echo "scanning [$how]  $img"
        if docker run --rm \
              -v /var/run/docker.sock:/var/run/docker.sock \
              -v "$PWD/$outdir":/out \
              {{syft}} scan "$src" -o spdx-json=/out/"$safe".spdx.json -q; then
            echo "  $img  [$how]  $digest" >> "$outdir/MANIFEST.txt"
        else
            # e.g. the locally-built edge image on a box that never built it
            echo "  $img  [SKIPPED — not local, not fetchable]" >> "$outdir/MANIFEST.txt"
            echo "  ...skipped (not local, not fetchable)"
        fi
    done
    tar czf "sbom/almanac-sbom-${stamp}-${rev}.tar.gz" -C sbom "${stamp}-${rev}"
    echo
    cat "$outdir/MANIFEST.txt"
    echo "hand infosec: sbom/almanac-sbom-${stamp}-${rev}.tar.gz"

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

# Mint a per-user virtual key:  just key amaya@northwinds.edu engr301 [budget]
# Use the person's SIGN-IN EMAIL as the user: that's what joins their key
# spend to their chat spend in the usage tools (a non-email user_id needs an
# aliases: entry in usage-mcp/roster.yaml to fold back onto the student).
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

# Roles: proxy_admin_viewer = read-only everything (the usual faculty pick);
# internal_user = own keys/usage only.  Email+password via a one-time link is
# the FREE path — SSO into this UI is Enterprise past 5 total DB users.
# Invite faculty into the LiteLLM UI:  just invite prof@x.edu [role]
invite email role="proxy_admin_viewer":
    #!/usr/bin/env bash
    set -euo pipefail
    base="http://localhost:${GATEWAY_PORT:-4000}"
    uid=$(curl -sf -X POST "$base/user/new" \
      -H "Authorization: Bearer ${LITELLM_MASTER_KEY}" -H "Content-Type: application/json" \
      -d '{"user_email": "{{email}}", "user_role": "{{role}}", "auto_create_key": false}' \
      | python3 -c "import sys,json; print(json.load(sys.stdin)['user_id'])")
    inv=$(curl -sf -X POST "$base/invitation/new" \
      -H "Authorization: Bearer ${LITELLM_MASTER_KEY}" -H "Content-Type: application/json" \
      -d "{\"user_id\": \"$uid\"}" \
      | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
    echo "send {{email}} this link (expires in 7 days; they set a password there):"
    echo "  http://${ALMANAC_HOST:-localhost}:${GATEWAY_PORT:-4000}/ui/onboarding?id=$inv"
    echo "(edge profile: swap host for your GATEWAY_HOST)"

# ---- Coding harness (opencode, profile: workbench) ----------------------------
# Run-on-demand, never a daemon.  Proves a vAPI key end to end from inside the
# stack; students use the same provider block on their laptops (user guide).
# NOTE: the key lands in shell history — fine for test keys; for real ones,
# pass it from an env var:  just workbench "$MY_KEY"

# Open the opencode TUI wired to the gateway:  just workbench sk-...
workbench key:
    ALMANAC_API_KEY="{{key}}" {{compose}} --profile workbench run --rm workbench

# One-shot proof a key works (mints nothing; spends a few tokens as that key)
workbench-smoke key:
    ALMANAC_API_KEY="{{key}}" {{compose}} --profile workbench run --rm workbench \
      run -m almanac/almanac-chat "Reply with exactly: almanac-ok"
