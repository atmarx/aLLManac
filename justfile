# The aLLManac — deployment contract.
# Every recipe here runs the same on a laptop, xdocker03, or your cloud box.
# CI (Woodpecker/GitLab/GitHub) is just a thin wrapper that ssh's in and calls
# these — see .woodpecker/deploy.yml and docs/ci.md.

set shell := ["bash", "-euo", "pipefail", "-c"]
set dotenv-load := true

# The core stack, plus this box's own layer if it has one.  site/ is
# gitignored and seeded from site.example/ by `just _site`; the conditional
# is what makes it OPTIONAL rather than required — a box with no site/ runs
# core and nothing complains.  Evaluated once at parse time, so a site/ that
# appears mid-run isn't picked up until the next `just` (which is why _site
# runs before anything that would care).
site_compose := "site/compose.yml"
compose := "docker compose -f compose.yml" + (
    if path_exists("site/compose.yml") == "true" { " -f site/compose.yml" } else { "" }
)
# The vLLM stack is separate on purpose (model stays loaded across app
# deploys) AND site-local on purpose (inference is behind INFERENCE_BASE_URL;
# a box with no GPU shouldn't carry a GPU stack).  --project-directory .
# makes it share the root .env.
vllm_compose := "site/inference/vllm.compose.yml"
vllm := "docker compose --project-directory . -f site/inference/vllm.compose.yml"
# SBOM generator — pinned like everything else:
syft := "anchore/syft:v1.46.0@sha256:473a60e3a58e29aca3aedb3e99e787bb4ef273917e44d10fcbea4330a07320bb"

# List recipes
default:
    @{{just_executable()}} --list --unsorted

# First-time setup: create .env from the example + generate every secret
setup: _env _site secrets
    @echo
    @echo "Now edit .env — set ALMANAC_HOST, INFERENCE_BASE_URL, and OPENID_ISSUER."
    @echo "This box's own compose layer (if it needs one) is site/compose.yml."

_env:
    @test -f .env || (cp .env.example .env && echo ".env created from .env.example")

# This deployment's own layer — gitignored, cloned from the template on
# first run so there is somewhere to put box-specific compose before you
# need it.  Never overwrites: a site/ that exists is the operator's.
_site:
    @test -d site || (cp -r site.example site \
      && echo "site/ created from site.example/ — this box's compose layer and infra live there")

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
    fill REGISTRAR_MCP_TOKEN  "$(openssl rand -hex 32)"
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

# _site seeds site/ if it's missing, and the seeded layer is EMPTY — so the
# one run where `compose` was resolved before the folder existed is also the
# one run where the folder had nothing to say.  Every run after it layers.
#
# Bring the stack up (profiles come from COMPOSE_PROFILES in .env)
up: _roster _fleet _site && usage-role bao-unseal
    {{compose}} up -d --remove-orphans

# The live roster is deployment data (student emails) — gitignored, seeded
# from the example on first up.  It is a RENDER now: the registrar rewrites
# it from registrar/courses.yaml on every roster change.
_roster:
    @test -f usage-mcp/roster.yaml || (cp usage-mcp/roster.example.yaml usage-mcp/roster.yaml \
      && echo "usage-mcp/roster.yaml created from the example — put your real courses in it")

# The fleet dir is all registrar-rendered (gitignored) — but compose parses
# the include on EVERY invocation, so fresh clones need the stubs first:
_fleet:
    @mkdir -p fleet/caddy
    @test -f fleet/fleet.yml || printf '# seeded by `just _fleet` — the registrar renders the real one\nservices: {}\n' > fleet/fleet.yml
    @test -f fleet/caddy/_stub.caddy || printf '# seeded stub — keeps the edge import glob non-empty before the first course\n' > fleet/caddy/_stub.caddy
    @test -f registrar/courses.yaml || (cp registrar/courses.example.yaml registrar/courses.yaml \
      && echo "registrar/courses.yaml created from the example — the demo courses live there")

# The usage service reads the ledger through usage_ro — the master key never
# enters that container.  USAGE_DB_PASSWORD is hex, so inlining is quote-safe.
# Provision usage_ro, the SELECT-only ledger role (idempotent; rides `just up`)
usage-role:
    #!/usr/bin/env bash
    set -euo pipefail
    # Read the password from the FILE, not the environment: dotenv-load
    # snapshots .env when just starts, and on a first deploy `secrets`
    # appends this var DURING the same `just deploy` run — the env var is
    # stale-empty exactly when it matters most (ask pipeline #13).
    pw=$(grep '^USAGE_DB_PASSWORD=' .env 2>/dev/null | head -1 | cut -d= -f2-)
    if [ -z "$pw" ]; then
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
    ALTER ROLE usage_ro LOGIN PASSWORD '$pw';
    GRANT CONNECT ON DATABASE litellm TO usage_ro;
    GRANT USAGE ON SCHEMA public TO usage_ro;
    GRANT SELECT ON ALL TABLES IN SCHEMA public TO usage_ro;
    ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO usage_ro;
    SQL
    echo "usage_ro — provisioned (SELECT-only on the ledger)"

# Stop the stack (data survives)
down: _fleet
    {{compose}} down

# Stop + WIPE ALL DATA (volumes included) — asks first
nuke:
    #!/usr/bin/env bash
    read -r -p "This deletes ALL almanac data (chats, keys, users, model cache). Type 'yes': " a
    [ "$a" = "yes" ] && {{compose}} down -v || echo "aborted"

# Pull current images
pull: _fleet
    {{compose}} pull

# Build local images (the edge Caddy, when that profile is on)
build: _fleet
    {{compose}} build

# `secrets` here is the .env migration path: vars introduced by an upgrade get
# appended/generated; values you've set are never touched.
#
# egress-check runs LAST and it CAN FAIL THE DEPLOY.  That is the intent: the
# floor is policy, and policy nothing enforces is policy that drifts — which is
# exactly how the front office carried `actions` with no allowlist until a
# machine looked.  It runs after `smoke`, so instances are up and healthy and
# no container is still holding pre-deploy config.
#
# What CI runs on the box: refresh images, build, complete .env, restart, verify
deploy: pull build secrets up smoke egress-check

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
    check "registrar (rosters)" "http://127.0.0.1:${REGISTRAR_PORT:-8091}/health"
    # sealed/uninitialized read as 200 here — a sealed bao is a boot state,
    # not an outage (just bao-unseal / bao-init):
    check "openbao (escrow)"   "http://127.0.0.1:${BAO_PORT:-8200}/v1/sys/health?uninitcode=200&sealedcode=200"
    check "keycloak (realm)"   "http://localhost:${AUTH_PORT:-8080}/realms/${KC_REALM:-northwinds}/.well-known/openid-configuration"
    exit $fail

# Prove every rendered course instance answers through the edge (TLS + vhost)
fleet-smoke:
    #!/usr/bin/env bash
    set -uo pipefail
    dom="${ALMANAC_DOMAIN:-localhost}"
    port="${EDGE_HTTPS_PORT:-443}"
    fail=0; found=0
    for envf in fleet/*.env; do
        [ -e "$envf" ] || continue
        found=1
        slug=$(basename "$envf" .env)
        for host in "$slug.$dom" "$slug-admin.$dom"; do
            ok=""
            for i in $(seq 1 18); do
                if curl -fsko /dev/null --max-time 10 --resolve "$host:$port:127.0.0.1" "https://$host:$port/"; then
                    ok=1; break
                fi
                sleep 5
            done
            if [ -n "$ok" ]; then echo "  ok    $host"; else echo "  FAIL  $host"; fail=1; fi
        done
    done
    [ "$found" = 1 ] || echo "  (no course instances rendered yet — just course ...)"
    exit $fail

# ---- Is the egress guardrail load-bearing? -----------------------------------
# `just smoke` proves the stack is serving.  This proves a SECURITY CONTROL is
# doing something, which is a different question and a harder one: a control
# that parses is not a control that runs.
#
# Three layers, and the third is the one that matters:
#   1  placement — is the knob where the enforcing code actually reads it?
#   2  posture   — what does this configuration MEAN? (an empty allowlist is
#                  no allowlist; there is no way to spell deny-all)
#   3  enforcement — ask the pinned image's OWN isActionDomainAllowed, with
#                  this instance's real list.  Not our reimplementation of
#                  the rule, not the vendor's description of it.  The code.
#
# The probe is piped in over stdin and never written to disk inside a running
# container — same spirit as the prod-probe pattern in docs/design-walls.md:
# verify on the box without changing the box.

# Prove the Actions egress allowlist enforces:  just egress-check [slug]
egress-check slug="":
    #!/usr/bin/env bash
    set -uo pipefail
    if [ -n "{{slug}}" ]; then
        targets="alm-chat-{{slug}}"
    else
        targets=$(docker ps --format '{{{{.Names}}' \
            | grep -E '^(alm-librechat|alm-chat-)' | sort || true)
    fi
    [ -n "$targets" ] || { echo "  no LibreChat instances running — just up"; exit 1; }
    fail=0
    for c in $targets; do
        echo
        echo "######## $c ########"
        # No -e CONFIG_PATH: `docker exec` already inherits the container's
        # own environment, so the probe reads the config THAT instance was
        # told to read rather than one we guessed at.  ALM_STARTED_AT is the
        # one thing the probe can't see from inside — it's how Layer 0 tells
        # "fixed" apart from "fixed on disk, not yet restarted."
        started=$(docker inspect --format '{{{{.State.StartedAt}}' "$c" 2>/dev/null || true)
        # The mount SOURCE on the host, resolved from the container's own
        # config path.  Layer 0a compares its mtime against what the container
        # actually sees — that difference is the only way to catch a bind
        # mount pinned to an inode the host has already replaced.
        cpath=$(docker exec "$c" printenv CONFIG_PATH 2>/dev/null || echo /app/librechat.yaml)
        src=$(docker inspect "$c" --format \
            '{{{{range .Mounts}}{{{{.Source}}|{{{{.Destination}}
{{{{end}}' 2>/dev/null \
            | awk -F'|' -v p="$cpath" '
                p==$2 { print $1; exit }
                $2!="" && index(p, $2"/")==1 { print $1 substr(p, length($2)+1); exit }')
        ino=""
        [ -n "$src" ] && [ -e "$src" ] && ino=$(stat -c %i "$src")
        docker exec -i -w /app -e ALM_STARTED_AT="$started" -e ALM_HOST_INO="$ino" \
            "$c" node < scripts/egress-probe.js || fail=1
    done
    echo
    if [ "$fail" = 0 ]; then
        echo "  every instance: the allowlist is load-bearing."
    else
        echo "  at least one instance FAILED — read the layer that reported it."
        echo "  A finding here is a real hole, not a flaky test: the check asks"
        echo "  the running image's own guard, so a FAIL is what an agent would"
        echo "  actually be permitted to reach."
    fi
    exit $fail

# Show container status
ps:
    {{compose}} ps
    @test -f {{vllm_compose}} && {{vllm}} ps 2>/dev/null || true

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
    # The vLLM stack is site-local and optional — a box without it still
    # owes infosec an SBOM for everything it DOES run:
    images=$( (COMPOSE_PROFILES=edge,workbench {{compose}} config --images; \
               [ -f {{vllm_compose}} ] && {{vllm}} config --images || true) | sort -u )
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

# ---- Local inference (site-local: site/inference/vllm.compose.yml) -----------
# Separate stack so the model stays loaded while the app stack
# deploys/bounces.  SITE-local because inference is whatever
# INFERENCE_BASE_URL points at — a box with no GPU deletes site/inference/
# and these recipes say so instead of failing at docker.
# Needs the NVIDIA Container Toolkit.  Same .env drives it (VLLM_* vars).

# Refuse clearly rather than handing docker a path that isn't there.
_vllm-here:
    #!/usr/bin/env bash
    set -euo pipefail
    if [ ! -f {{vllm_compose}} ]; then
        echo "no {{vllm_compose}} — this box doesn't run local inference."
        echo
        echo "That is a supported state, not a broken one.  The gateway uses"
        echo "whatever INFERENCE_BASE_URL points at:"
        grep '^INFERENCE_BASE_URL=' .env 2>/dev/null | sed 's/^/  /' || echo "  (not set in .env)"
        echo
        echo "To run vLLM here after all:  cp -r site.example/inference site/"
        exit 1
    fi

# Start local vLLM (first boot downloads the model — be patient)
vllm-up: _vllm-here
    {{vllm}} up -d

# Stop local vLLM (unloads the model; app stack is untouched)
vllm-down: _vllm-here
    {{vllm}} down

# Tail vLLM logs (watch a cold model load here)
vllm-logs: _vllm-here
    {{vllm}} logs -f --tail=100

# Pull the pinned vLLM image
vllm-pull: _vllm-here
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
logs svc="": _fleet
    {{compose}} logs -f --tail=100 {{svc}}

# ---- The course fleet & the escrow -------------------------------------------
# One LibreChat instance per course (docs/registrar-spec.md).  The registrar
# renders everything; these recipes own the docker lifecycle around it —
# no docker socket ever enters a service container.

# Create/update a course + provision everything:  team, service key, OIDC
# client + door roles, instance render, vhost — then start it.  Idempotent;
# extra flags pass through (e.g. --budget 1500 --ta ta@x.edu --college cci):
#   just course engr301-2026fall "ENGR 301 (Fall 2026)" prof.vex@northwinds.edu
course slug name +instructors:
    {{compose}} exec -T registrar python course_admin.py create "{{slug}}" "{{name}}" {{instructors}} </dev/null
    @{{just_executable()}} course-up

# Start newly rendered instances + reload the edge's vhosts (graceful)
course-up:
    {{compose}} up -d --remove-orphans
    @{{compose}} ps --status=running --services 2>/dev/null | grep -qx edge \
      && {{compose}} exec -T edge caddy reload --config /etc/caddy/Caddyfile </dev/null \
      && echo "edge reloaded" || echo "(edge not running — vhosts load when it starts)"

# List the registrar's course records
courses:
    {{compose}} exec -T registrar python course_admin.py list </dev/null

# Check courses.yaml without touching anything — run it after hand-editing.
# `just course` runs the same checks itself and refuses on errors; this is
# the read-only version for when you want to look before you provision.
course-check:
    {{compose}} exec -T registrar python course_admin.py validate </dev/null

# ---- OpenBao: the escrow ------------------------------------------------------

# The once-per-box ritual: init, unseal, audit device, kv2 mount, policy,
# AppRole — then writes BAO_UNSEAL_KEY + the registrar's role creds into
# .env (fill pattern: never touches set values) and prints the ROOT TOKEN
# EXACTLY ONCE.  Store that token in a password manager; it is not saved.
# Re-provisioning an already-initialized bao: BAO_ROOT_TOKEN=... just bao-init
bao-init:
    #!/usr/bin/env bash
    set -euo pipefail
    b() {  # run bao inside the container; token via env when provisioning
        {{compose}} exec -T ${ROOT_TOKEN:+-e BAO_TOKEN=$ROOT_TOKEN} openbao bao "$@" </dev/null
    }
    for i in $(seq 1 18); do
        {{compose}} exec -T openbao bao status </dev/null >/dev/null 2>&1 && break
        rc=$?; [ $rc -eq 2 ] && break   # sealed = answering
        sleep 5
    done
    st=$({{compose}} exec -T openbao bao status -format=json </dev/null || true)
    initialized=$(printf '%s' "$st" | python3 -c "import sys,json; print(json.load(sys.stdin).get('initialized'))" 2>/dev/null || echo "")
    ROOT_TOKEN="${BAO_ROOT_TOKEN:-}"
    fresh=""
    if [ "$initialized" != "True" ] && [ "$initialized" != "true" ]; then
        out=$({{compose}} exec -T openbao bao operator init -key-shares=1 -key-threshold=1 -format=json </dev/null)
        UNSEAL_KEY=$(printf '%s' "$out" | python3 -c "import sys,json; print(json.load(sys.stdin)['unseal_keys_b64'][0])")
        ROOT_TOKEN=$(printf '%s' "$out" | python3 -c "import sys,json; print(json.load(sys.stdin)['root_token'])")
        {{compose}} exec -T openbao bao operator unseal "$UNSEAL_KEY" </dev/null >/dev/null
        fresh=1
    else
        UNSEAL_KEY=$(grep '^BAO_UNSEAL_KEY=' .env 2>/dev/null | head -1 | cut -d= -f2- || true)
        if [ -z "$ROOT_TOKEN" ]; then
            if grep -q '^BAO_REGISTRAR_ROLE_ID=.' .env 2>/dev/null; then
                echo "bao-init: already initialized and provisioned — nothing to do"
                exit 0
            fi
            echo "bao-init: already initialized but the registrar isn't provisioned."
            echo "re-run with the root token:  BAO_ROOT_TOKEN=... just bao-init"
            exit 1
        fi
    fi
    b audit enable file file_path=/openbao/logs/audit.log 2>/dev/null || true
    b secrets enable -path=almanac kv-v2 2>/dev/null || true
    {{compose}} exec -T ${ROOT_TOKEN:+-e BAO_TOKEN=$ROOT_TOKEN} openbao bao policy write registrar - <<'POL'
    path "almanac/data/courses/*"     { capabilities = ["create", "read", "update", "delete", "list"] }
    path "almanac/metadata/courses/*" { capabilities = ["read", "delete", "list"] }
    POL
    b auth enable approle 2>/dev/null || true
    b write auth/approle/role/registrar token_policies=registrar token_ttl=1h token_max_ttl=4h >/dev/null
    ROLE_ID=$(b read -field=role_id auth/approle/role/registrar/role-id)
    SECRET_ID=$(b write -f -field=secret_id auth/approle/role/registrar/secret-id)
    fill() {  # same contract as `just secrets`: append if missing, never touch set values
        if ! grep -q "^${1}=" .env; then echo "${1}=${2}" >> .env; echo "  ${1}  — written"
        elif grep -q "^${1}=$" .env; then sed -i "s|^${1}=$|${1}=${2}|" .env; echo "  ${1}  — written"
        else echo "  ${1}  — already set, left alone"; fi
    }
    [ -n "${UNSEAL_KEY:-}" ] && fill BAO_UNSEAL_KEY "$UNSEAL_KEY"
    fill BAO_REGISTRAR_ROLE_ID "$ROLE_ID"
    fill BAO_REGISTRAR_SECRET_ID "$SECRET_ID"
    {{compose}} up -d registrar >/dev/null 2>&1 || true
    echo
    echo "the escrow is open: kv2 at almanac/, audit on, registrar AppRole provisioned"
    if [ -n "$fresh" ]; then
        echo
        echo "ROOT TOKEN (shown ONCE — password manager, not .env):  $ROOT_TOKEN"
    fi

# Unseal after a restart (no-op when unsealed, uninitialized, or key unset).
# Reads .env directly — same dotenv-snapshot trap usage-role documents.
bao-unseal:
    #!/usr/bin/env bash
    set -uo pipefail
    key=$(grep '^BAO_UNSEAL_KEY=' .env 2>/dev/null | head -1 | cut -d= -f2-)
    [ -z "$key" ] && exit 0
    for i in $(seq 1 12); do
        {{compose}} exec -T openbao bao status </dev/null >/dev/null 2>&1; rc=$?
        [ $rc -eq 0 ] && exit 0          # already unsealed
        [ $rc -eq 2 ] && break           # sealed and answering — unseal it
        sleep 5
    done
    [ ${rc:-1} -eq 2 ] || exit 0         # not answering (no openbao yet) — leave it
    {{compose}} exec -T openbao bao operator unseal "$key" </dev/null >/dev/null \
      && echo "openbao — unsealed" || echo "openbao — unseal FAILED (check BAO_UNSEAL_KEY)"

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
