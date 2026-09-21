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
# The channel is the set of image pins this box runs — channels/<name>.env,
# tracked, chosen by ALMANAC_CHANNEL in .env (stable when unset).  It goes to
# compose as an env file AHEAD of .env, so a pin set in .env still wins; and
# it goes on every compose call, because a `just` that forgot it would
# resolve the compose.yml defaults instead and quietly deploy the wrong
# LibreChat.  A missing channel file fails at parse time, loudly.
channel := env_var_or_default("ALMANAC_CHANNEL", "stable")
channel_env := "channels/" + channel + ".env"
env_files := if path_exists(channel_env) == "true" {
    "--env-file " + channel_env + " --env-file .env"
} else {
    error("ALMANAC_CHANNEL=" + channel + " but " + channel_env + " does not exist")
}
compose := "docker compose " + env_files + " -f compose.yml" + (
    if path_exists("site/compose.yml") == "true" { " -f site/compose.yml" } else { "" }
)
# The vLLM stack is separate on purpose (model stays loaded across app
# deploys) AND site-local on purpose (inference is behind INFERENCE_BASE_URL;
# a box with no GPU shouldn't carry a GPU stack).  --project-directory .
# makes it share the root .env.
vllm_compose := "site/inference/vllm.compose.yml"
vllm := "docker compose " + env_files + " --project-directory . -f site/inference/vllm.compose.yml"
# SBOM generator — pinned like everything else:
syft := "anchore/syft:v1.46.0@sha256:473a60e3a58e29aca3aedb3e99e787bb4ef273917e44d10fcbea4330a07320bb"
# Static docs builder. The edge serves the generated files; MkDocs' preview
# server never becomes part of the production stack.
mkdocs := "squidfunk/mkdocs-material:9.7.1@sha256:3bba0a99bc6e635bb8e53f379d32ab9cecb554adee9cc8f59a347f93ecf82f3b"

# List recipes
default:
    @{{just_executable()}} --list --unsorted

# Which channel this box runs, and the images that resolves to.  Also names
# any pin .env sets itself: that pin wins over the channel, which is right
# for a hotfix and wrong for an .env that predates channels and still carries
# the old image lines — a box like that never leaves the pins it was born with.
channel: _fleet
    #!/usr/bin/env bash
    set -euo pipefail
    echo "channel: {{channel}}  ({{channel_env}})"
    {{compose}} config --images 2>/dev/null | grep -E "librechat|litellm|rag-api|admin-panel|opencode|mongo|meili|postgres|pgvector" | sort -u | sed 's/^/  /'
    for v in $(grep -oE '^[A-Z_]+_IMAGE=' {{channel_env}} | tr -d =); do
        if grep -qE "^$v=" .env; then
            echo "  WARN: .env sets $v itself — that overrides the channel.  Delete the line unless it is a deliberate hotfix."
        fi
    done

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
    fill SBOM_TOKEN           "$(openssl rand -hex 24)"
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
up: _roster _fleet _site _sbom-dir docs-build && usage-role bao-unseal
    {{compose}} up -d --remove-orphans

# The edge bind-mounts sbom/ — make sure it exists as OURS before compose
# creates it as root's and the next `just sbom` can't replace latest/.
_sbom-dir:
    @mkdir -p sbom/latest sbom/archive

# Build the human-readable site from apex/, which remains the RAG corpus too.
# The output is a read-only bind in the edge container; there is no docs daemon.
docs-build:
    @mkdir -p site-dist
    docker run --rm --user "$(id -u):$(id -g)" \
      --env DOCS_SITE_NAME --env DOCS_SITE_URL --env DOCS_PRODUCT_NAME \
      --volume "$PWD:/docs" {{mkdocs}} build --clean --strict

# Render the per-audience RAG corpora from front matter.  A guide is a query,
# not a directory — see docs/audience-projection.md.  corpus/ is a RENDER:
# gitignored, never edited, regenerable.  Reuses the pinned mkdocs image
# because it already carries PyYAML; no second dependency to track.
docs-corpus:
    docker run --rm --user "$(id -u):$(id -g)" \
      --volume "$PWD:/docs" --entrypoint python3 {{mkdocs}} /docs/docs/corpus.py
    @echo "corpus/ rendered — read corpus/README.md for what landed where and why"

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

# Build local images (registrar, usage-mcp, the edge Caddy when that profile
# is on) — and then the SBOM, because what we just built is exactly the part
# of the dependency tree no upstream pin describes.
build: _fleet && sbom
    {{compose}} build

# `secrets` here is the .env migration path: vars introduced by an upgrade get
# appended/generated; values you've set are never touched.
#
# egress-check runs LAST and it CAN FAIL THE DEPLOY.  That is the intent: the
# floor is policy, and policy nothing enforces is policy that drifts — which is
# exactly how the front office carried `actions` with no allowlist until a
# machine looked.
#
# config-refresh runs between `up` and `smoke`, and it is not optional.  `up`
# recreates a container when its DEFINITION changes — image, env, mount spec —
# and a bind-mounted config file's CONTENTS are none of those.  So editing
# librechat.yaml and deploying gets the new file into the container (that is
# what the directory mounts bought) and leaves the process holding the old one.
# Pipeline #46 failed exactly here, on a comment-only edit, which is the check
# doing its job: it cannot know a diff is harmless and must not guess.
#
# bao-unseal appears TWICE and the second one is load-bearing: `up` ends with
# an unseal, but config-refresh may then RESTART openbao (its config changed),
# and a restarted bao comes back sealed.  smoke can't catch it — its health
# probe passes sealedcode=200 because sealed is a normal boot state, not an
# outage.  Without the re-unseal, an openbao config change deploys green and
# leaves the escrow sealed until a human notices the registrar can't mint.
#
# render-check runs DEAD LAST, after egress-check, and it can fail the deploy.
# It is config-refresh one level up: config-refresh catches a changed FILE that
# a running process never re-read; render-check catches a changed TEMPLATE that
# never reached the file.  `deploy` builds the registrar image, so a new
# render.py is IN the container and inert — fleet/ still holds the old render
# and compose recreates nothing.  A Secure-cookie fix landed on the flagship
# and silently skipped every course panel exactly this way (2026-09-18).
#
# Last on purpose, for two reasons.  A stale render doesn't make the box
# unhealthy — it makes it not-what-you-shipped — so it must not rob you of
# smoke and egress-check output on its way to red.  And it must sit after the
# second bao-unseal: a guard that aborts the deploy before that one leaves the
# escrow sealed, which is a worse outcome than the drift it was reporting.
#
# The THIRD render door, and it cost the same find twice.  `render-check`
# guards the fleet render; nothing guarded the one the GUIDES eat.  A deploy
# ships a prompt or a corpus change and the agents go on serving whatever the
# last `agents-seed` attached — inert, and silent about it.  Five guides on
# xdocker03 were weeks stale while `agents-check` itself was green
# (2026-09-21).  `docs-corpus` renders first so the comparison is against the
# tree you just shipped, not against whatever corpus/ happened to hold; it
# writes only the gitignored render, never the box.  Red means
# `just agents-seed` — this reports and never repairs, for render-check's
# reasons: re-seeding six agents mid-deploy is the bigger surprise.
#
# What CI runs on the box: images, build, .env, restart, re-read config, verify
deploy: channel pull build secrets up config-refresh bao-unseal smoke egress-check render-check docs-corpus agents-check

# The gap this closes: `docker compose up` recreates on a changed DEFINITION,
# never on changed bind-mount CONTENTS.  Directory mounts got the new file into
# the container; nothing made the process re-read it.  Same failure as the
# pinned inode, one level up — the file is current and the process is not.
#
# Every read-only bind mount is treated as config by definition.  Scope is
# `alm-*`, which is both the core stack and the course fleet (they are separate
# compose projects); any other LibreChat on the box is not ours to restart.
#
# Restart containers whose mounted config changed since they booted
config-refresh:
    #!/usr/bin/env bash
    set -uo pipefail
    n=0; checked=0; drifted=0
    # ANCHORED — docker's name filter is a substring match, and a recipe that
    # restarts things has no business matching `foo-alm-bar`:
    for c in $(docker ps --filter "name=^alm-" --format '{{{{.Names}}'); do
      started=$(docker inspect "$c" --format '{{{{.State.StartedAt}}' 2>/dev/null || echo "")
      boot=$(date -d "$started" +%s 2>/dev/null || echo 0)
      [ "$boot" -gt 0 ] || continue
      checked=$((checked+1))
      newest=0; which=""
      # read-only binds only: a rw bind is data, and its mtime means nothing here
      srcs=$(docker inspect "$c" --format '{{{{range .Mounts}}{{{{if and (eq .Type "bind") (not .RW)}}{{{{println .Source}}{{{{end}}{{{{end}}' 2>/dev/null)
      for src in $srcs; do
        [ -e "$src" ] || continue
        # No -type f: a DELETED config file bumps only its parent directory's
        # mtime, and filtering to files made deletions invisible — a course
        # vhost removed by git sync left the edge serving the dead route.
        # Directories ride along in the scan precisely to catch removals.
        m=$(find "$src" -printf '%T@\n' 2>/dev/null | sort -rn | head -1)
        m=${m%%.*}
        [ -n "$m" ] || m=0
        if [ "$m" -gt "$newest" ]; then newest=$m; which=$src; fi
      done
      if [ "$newest" -gt "$boot" ]; then
        # GUARD before restarting: a restart re-resolves bind sources but keeps
        # the container's old DEFINITION.  If compose.yml changed the mount
        # topology since this container was created, the new config was written
        # for the new topology — restarting boots new config into the old shape.
        # (The concrete case: the edge's Caddyfile importing /etc/caddy-fleet,
        # restarted into a container that only mounts /etc/caddy/fleet — empty
        # import glob, fatal, edge down and unable to boot.)  Fail CLOSED: if
        # the definition drifted or can't be checked, refuse the restart and
        # fail the run — `just up` (recreate) is the verb for definition
        # drift, not restart.  In `deploy` this never fires, because `up`
        # reconciles definitions first.
        #
        # The oracle is compose's OWN diff: `up --dry-run` says "Recreate" for
        # a container whose definition moved and "Running" for one that
        # didn't.  It used to be `config --hash` against the config-hash
        # label, and that was a false positive for every service with an
        # env_file: compose 5.3 stamps one hash at create and computes a
        # different one from `config`, for the same files, seconds apart,
        # with or without --no-env-resolution (measured 2026-09-15 on
        # librechat and keycloak; registrar, no env_file, matched).  Pipeline
        # #72 went red on a container `up` had just declined to recreate.
        svc=$(docker inspect "$c" --format '{{{{index .Config.Labels "com.docker.compose.service"}}' 2>/dev/null)
        pdir=$(docker inspect "$c" --format '{{{{index .Config.Labels "com.docker.compose.project.working_dir"}}' 2>/dev/null)
        files=$(docker inspect "$c" --format '{{{{index .Config.Labels "com.docker.compose.project.config_files"}}' 2>/dev/null)
        verdict=""
        if [ -n "$svc" ] && [ -n "$pdir" ] && [ -n "$files" ]; then
          fargs=""; IFS=','; for f in $files; do fargs="$fargs -f $f"; done; unset IFS
          # The env files too, or the dry-run resolves image pins from .env
          # alone, sees a different image than the channel gave the running
          # container, and reports drift that is not there.
          efiles=$(docker inspect "$c" --format '{{{{index .Config.Labels "com.docker.compose.project.environment_file"}}' 2>/dev/null)
          eargs=""; IFS=','; for f in $efiles; do [ -n "$f" ] && eargs="$eargs --env-file $f"; done; unset IFS
          plan=$(docker compose --project-directory "$pdir" $eargs $fargs up -d --dry-run --no-deps "$svc" 2>&1 || true)
          case "$plan" in
            *"$c Recreate"*) verdict="drifted" ;;
            *"$c Running"*|*"$c Started"*|*"$c Healthy"*) verdict="same" ;;
          esac
        fi
        if [ "$verdict" != "same" ]; then
          echo "  SKIP     $c — config changed AND its compose definition drifted (or can't be checked)."
          echo "           A restart would boot the new config into the old container shape."
          echo "           Run \`just up\` to recreate it, then re-run config-refresh."
          drifted=$((drifted+1))
          continue
        fi
        echo "  restart  $c — $which is newer than its boot"
        if docker restart "$c" >/dev/null 2>&1; then
          n=$((n+1))
        else
          echo "  FAIL     $c — restart failed"
          exit 1
        fi
      fi
    done
    if [ "$drifted" -gt 0 ]; then
      echo "config-refresh — $drifted container(s) SKIPPED on definition drift ($n restarted, $checked checked)"
      exit 1
    elif [ "$n" -eq 0 ]; then
      echo "config-refresh — $checked containers, all holding current config"
    else
      echo "config-refresh — restarted $n of $checked"
    fi

# The MERGED compose — core plus site/, with every variable resolved.  The
# honest way to answer "did my site/ override actually take?", which compose
# merge rules make genuinely hard to guess (volumes merge by target, command
# replaces wholesale).
#
# Show the resolved stack:  just config [service]
config svc="":
    @{{compose}} config {{svc}}

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
    check "admin panel"        "http://localhost:${ADMIN_PANEL_PORT:-3082}/"
    check "litellm (gateway)"  "http://localhost:${GATEWAY_PORT:-4000}/health/liveliness"
    check "usage-mcp (stats)"  "http://127.0.0.1:${USAGE_MCP_PORT:-8090}/health"
    check "registrar (rosters)" "http://127.0.0.1:${REGISTRAR_PORT:-8091}/health"
    # sealed/uninitialized read as 200 here — a sealed bao is a boot state,
    # not an outage (just bao-unseal / bao-init):
    check "openbao (escrow)"   "http://127.0.0.1:${BAO_PORT:-8200}/v1/sys/health?uninitcode=200&sealedcode=200"
    check "keycloak (realm)"   "http://localhost:${AUTH_PORT:-8080}/realms/${KC_REALM:-classroom}/.well-known/openid-configuration"
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
        # The mount SOURCE on the host for this instance's config, so Layer 0a
        # can compare its inode against the one the container actually sees.
        # Every template stays on ONE line: `just` dedents recipe bodies, and a
        # continuation sitting at column 0 ends the recipe instead (this file's
        # own wall, walked into once — pipeline #37).
        src=$(docker inspect "$c" --format '{{{{range .Mounts}}{{{{if eq .Destination "/app/conf"}}{{{{.Source}}{{{{end}}{{{{end}}' 2>/dev/null || true)
        if [ -n "$src" ]; then
            hostfile="$src/librechat.yaml"
        else
            # Pre-b258123 shape: the config was bind-mounted as a single FILE.
            # That is the very thing Layer 0a exists to catch, so resolve it and
            # let the probe fail rather than skipping the check.
            hostfile=$(docker inspect "$c" --format '{{{{range .Mounts}}{{{{if eq .Destination "/app/librechat.yaml"}}{{{{.Source}}{{{{end}}{{{{end}}' 2>/dev/null || true)
        fi
        ino=""
        [ -n "$hostfile" ] && [ -e "$hostfile" ] && ino=$(stat -c %i "$hostfile")
        docker exec -i -w /app -e ALM_STARTED_AT="$started" -e ALM_HOST_INO="$ino" \
            "$c" node < scripts/egress-probe.js || fail=1
    done
    echo
    if [ "$fail" = 0 ]; then
        echo "  every aLLManac instance checked: the allowlist is load-bearing."
        echo "  (Scope is this stack — containers named alm-librechat / alm-chat-*."
        echo "   A LibreChat on this box that isn't ours is not ours to vouch for.)"
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

# Every build owes infosec a fresh dependency tree.  Versions move under a
# pin (the images we build here move on every build), so this is not a
# tarball someone remembers to email — it is rewritten by `just build`, and
# the edge serves sbom/latest/ at https://<CHAT_HOST>/sbom/ behind
# SBOM_TOKEN, so the scanner's list holds one live URL per box.
#
# Only images ON THIS BOX are scanned (build runs after pull, so that is the
# whole app stack; the multi-GB vLLM image counts on the GPU box, where it
# already lives).  Absent ones are listed as skipped in index.json — a
# missing entry is visible, never silently streamed from a registry mid-deploy.
# sbom/latest/ is REPLACED by rename (the edge mounts sbom/, the parent, for
# exactly the inode reason in design-walls.md), and each run also leaves a
# dated tarball in sbom/archive/ (last 30 kept).
#
# SBOMs (SPDX + CycloneDX JSON) for every image on this box → sbom/latest/
sbom:
    #!/usr/bin/env bash
    set -euo pipefail
    rev=$(git describe --always --dirty)
    now=$(date -u +%Y-%m-%dT%H:%M:%SZ)
    stamp=$(date -u +%Y%m%dT%H%M%SZ)
    work="sbom/.build-$$"
    rm -rf "$work"; mkdir -p "$work" sbom/archive
    images=$( (COMPOSE_PROFILES=edge,workbench {{compose}} config --images; \
               [ -f {{vllm_compose}} ] && {{vllm}} config --images || true) | sort -u )
    # syft runs as THIS user (plus the socket's group) so the output is ours
    # to replace next build, not root's — which means the image's /tmp is
    # not writable, so it gets a scratch dir of ours mounted there.
    sockgid=$(stat -c %g /var/run/docker.sock)
    mkdir -p "$work/.tmp"
    entries=""; skipped=""
    for img in $images; do
        safe=$(echo "$img" | tr '/:@' '___')
        if ! docker image inspect "$img" >/dev/null 2>&1; then
            echo "  skip (not on this box)  $img"
            skipped="${skipped}${skipped:+,}\"$img\""
            continue
        fi
        id=$(docker image inspect --format '{{{{.Id}}' "$img")
        digest=$(docker image inspect --format '{{{{if .RepoDigests}}{{{{index .RepoDigests 0}}{{{{end}}' "$img")
        echo "scanning  $img"
        docker run --rm --user "$(id -u):${sockgid}" -e HOME=/tmp \
            -v "$PWD/$work/.tmp":/tmp \
            -v /var/run/docker.sock:/var/run/docker.sock \
            -v "$PWD/$work":/out \
            {{syft}} scan "$img" \
              -o spdx-json=/out/"$safe".spdx.json \
              -o cyclonedx-json=/out/"$safe".cdx.json
        spdx_sha=$(sha256sum "$work/$safe.spdx.json" | cut -d' ' -f1)
        cdx_sha=$(sha256sum "$work/$safe.cdx.json" | cut -d' ' -f1)
        entries="${entries}${entries:+,}
    {\"image\": \"$img\", \"image_id\": \"$id\", \"repo_digest\": \"${digest:-}\",
     \"spdx\": \"$safe.spdx.json\", \"spdx_sha256\": \"$spdx_sha\",
     \"cyclonedx\": \"$safe.cdx.json\", \"cyclonedx_sha256\": \"$cdx_sha\"}"
    done
    channel="{{channel}}"
    cat > "$work/index.json" <<JSON
    {
      "generator": "aLLManac just sbom",
      "generated": "$now",
      "git": "$rev",
      "channel": "$channel",
      "syft": "{{syft}}",
      "formats": ["spdx-json", "cyclonedx-json"],
      "images": [$entries
      ],
      "skipped": [$skipped]
    }
    JSON
    rm -rf "$work/.tmp"
    chmod -R a+rX "$work"
    # Replace by rename — a scanner mid-fetch sees the old set or the new
    # set, never a half-written one.  The edge mounts sbom/ (the parent).
    if [ -d sbom/latest ]; then mv sbom/latest "sbom/.old-$$"; fi
    mv "$work" sbom/latest
    rm -rf "sbom/.old-$$"
    tar czf "sbom/archive/almanac-sbom-${stamp}-${rev}.tar.gz" -C sbom latest
    ls -t sbom/archive/*.tar.gz 2>/dev/null | tail -n +31 | xargs -r rm -f
    echo
    echo "sbom/latest: $(ls sbom/latest | grep -c spdx) images  (git ${rev}, ${now})"
    echo "live at: https://${CHAT_HOST:-chat.localhost}/sbom/   (Authorization: Bearer \$SBOM_TOKEN)"

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

# ---- Pre-staged models (nothing is fetched at runtime) -----------------------
# The RAG service embeds with a local CPU model and will DOWNLOAD IT ON FIRST
# USE if the cache is cold.  That is one runtime fetch too many: it is egress
# from a service that should need none, it is a model nobody approved, and on
# an air-gapped box it simply fails — leaving every agent talking and knowing
# nothing, because knowledge files cannot embed.  So stage it deliberately,
# once, as an operator act.  See docs/design-walls.md, "The inference runtime
# gets no egress".

# What is actually staged?  Reads the cache, touches no network.
embed-check:
    #!/usr/bin/env bash
    set -uo pipefail
    {{compose}} run --rm --no-deps -T rag_api sh -c '
        m="${EMBEDDINGS_MODEL:-?}"
        d="/root/.cache/huggingface/hub/models--$(echo "$m" | tr "/" "-" | sed "s/-/--/")"
        echo "  model    $m"
        if [ ! -d "$d" ]; then
            echo "  FAIL     not staged — first embed will try to download it"
            echo "           stage it:  just embed-stage"
            exit 1
        fi
        n=$(find "$d/snapshots" \( -type f -o -type l \) 2>/dev/null | wc -l)
        echo "  ok       staged, $n files, $(du -sh "$d" | cut -f1)"
        find "$d/snapshots" -name "*.safetensors" -o -name "*.bin" | head -3 | sed "s|.*/|           |"
    '

# Air-gapped sites: run this on a staging box, then `just embed-export` there
# and `just embed-import` here.
# Download the embedding model into the cache volume now (needs egress ONCE).
embed-stage:
    #!/usr/bin/env bash
    set -euo pipefail
    echo "staging the embedding model (needs network for this command only)"
    {{compose}} run --rm --no-deps -T rag_api python -c 'import os; from huggingface_hub import snapshot_download; m=os.environ["EMBEDDINGS_MODEL"]; print("  downloading "+m); print("  cached at "+snapshot_download(m))'
    just embed-check

# Tar the staged cache for transport to a box with no internet.
embed-export out="hf-cache.tar":
    #!/usr/bin/env bash
    set -euo pipefail
    d=$(cd "$(dirname "{{out}}")" && pwd); f=$(basename "{{out}}")
    {{compose}} run --rm --no-deps -T -v "$d:/xfer" rag_api \
        tar -C /root/.cache/huggingface -cf "/xfer/$f" .
    echo "  wrote $d/$f  ($(du -h "$d/$f" | cut -f1))"
    echo "  copy it to the target box, then:  just embed-import $f"

# Load a tarball from `just embed-export` into this box's cache volume.
embed-import tarball="hf-cache.tar":
    #!/usr/bin/env bash
    set -euo pipefail
    [ -f "{{tarball}}" ] || { echo "no such file: {{tarball}}"; exit 1; }
    d=$(cd "$(dirname "{{tarball}}")" && pwd); f=$(basename "{{tarball}}")
    {{compose}} run --rm --no-deps -T -v "$d:/xfer" rag_api \
        tar -C /root/.cache/huggingface -xf "/xfer/$f"
    just embed-check

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
#   just course engr301-2026fall "ENGR 301 (Fall 2026)" prof.vex@example.edu
course slug name +instructors:
    {{compose}} exec -T registrar python course_admin.py create "{{slug}}" "{{name}}" {{instructors}} </dev/null
    @{{just_executable()}} course-up

# Start newly rendered instances + reload the edge's vhosts (graceful)
course-up:
    {{compose}} up -d --remove-orphans
    @{{compose}} ps --status=running --services 2>/dev/null | grep -qx edge \
      && {{compose}} exec -T edge caddy reload --config /etc/caddy/Caddyfile </dev/null \
      && echo "edge reloaded" || echo "(edge not running — vhosts load when it starts)"

# Is the fleet running the templates we shipped?  Renders every course into
# MEMORY and diffs against the fleet volume — changes nothing, reads no
# escrow, calls no Keycloak (the two pass-through credentials come out of the
# render being checked), so it is safe in the middle of a deploy.
#
# It reports and never repairs, deliberately: recreating a course instance
# during a routine deploy is a bigger surprise than a red pipeline, and this
# is a class of bug you want told to you.  Red means run `just render`.
#
# A course in courses.yaml with no render yet is listed, not red — an
# unprovisioned record must not fail every deploy on the box.
#
# Refuse to answer a render question with a registrar that isn't this tree.
#
# `render-check` renders INSIDE the container and diffs against the fleet
# volume.  If the container predates a change to render.py, it renders the
# OLD template and compares it to files the OLD template wrote — both sides
# stale, and the check reports green.  It is structurally blind to exactly
# the drift it exists to catch, and it was: on 2026-09-21 the running
# registrar had zero occurrences of `context_tokens` against nine in the
# tree, and `render-check` said "every rendered file current."
#
# Inside `just deploy` this cannot happen — `build` and `up` run first, so
# the container is current by the time render-check runs.  It is the HAND
# run that lies, which is the one the "verify on the box" wall tells you to
# make.  So: prove the deployed registrar is this tree before believing
# anything it says about renders.  The Dockerfile COPYs these verbatim, so
# the bytes are comparable.
_registrar-current:
    #!/usr/bin/env bash
    set -euo pipefail
    # Per-file digests, SORTED — not a concatenation.  `planes/*.py` expands
    # in a different order inside the container (C locale puts __init__.py
    # first; the host's does not), so concatenating compares the sort order
    # as well as the bytes and reports a difference that isn't one.  Cost me
    # a false FAIL on a container that was already correct.
    files="server.py reconcile.py render.py course_admin.py"
    host=$(cd registrar && sha256sum $files planes/*.py \
      | LC_ALL=C sort | sha256sum | cut -d" " -f1)
    cont=$({{compose}} exec -T registrar sh -c \
      "cd /app && sha256sum $files planes/*.py" </dev/null \
      | LC_ALL=C sort | sha256sum | cut -d" " -f1)
    if [ "$host" != "$cont" ]; then
      echo "  FAIL the deployed registrar is NOT this working tree."
      echo "       Anything it says about renders describes the OLD templates,"
      echo "       including a green render-check.  Run \`just deploy\` first."
      exit 1
    fi

# Report (never repair) course renders the deployed templates would change
render-check: _registrar-current
    {{compose}} exec -T registrar python course_admin.py render --check </dev/null

# Re-render every course from courses.yaml with the registrar image you just
# deployed, then recreate what changed and reload the edge.  This is the
# verb the "a render-template change is INERT until something reconciles"
# wall asks for: `just deploy` ships render.py; `just render` makes it true.
# `just render-check` is the guard that tells you when you owe it a run.
#
# Re-render every course from the deployed templates, then recreate + reload
render:
    {{compose}} exec -T registrar python course_admin.py render </dev/null
    @{{just_executable()}} course-up

# List the registrar's course records
courses:
    {{compose}} exec -T registrar python course_admin.py list </dev/null

# The fleet from above: every instance, its people, agents, files, size and
# pool on one page — fleet/inventory.md (+ .json for whoever wants a feed).
# Metadata only; the same census the fleet_* chat tools give platform admins.
fleet:
    {{compose}} exec -T registrar python course_admin.py inventory </dev/null

# Nominated agents ("this one is worth copying") and the export that turns
# one into fleet/templates/<id>-<name>.yaml — a file to read, fork, and seed.
nominations:
    {{compose}} exec -T registrar python course_admin.py nominations </dev/null

template id:
    {{compose}} exec -T registrar python course_admin.py template "{{id}}" </dev/null

# What broke, and — for reports about an answer — the question and the answer
# that came back.  That second half is the point: it turns "the guide didn't
# know about X" into a retrieval trace you can take to the corpus.
# Problem reports filed from the chat: open (default), triaged, closed or all
reports status="open":
    {{compose}} exec -T registrar python course_admin.py reports --status "{{status}}" </dev/null

report-close id note="":
    {{compose}} exec -T registrar python course_admin.py report-close "{{id}}" --note "{{note}}" </dev/null

# The list is operator-edited like the rest of courses.yaml, so this is the
# read-only look at it — add or remove names by editing the file.
# Who may work the report queue from chat (`devs:` in courses.yaml)
devs:
    {{compose}} exec -T registrar python -c "import reconcile as R; d=R.load_courses(); print('devs:  ' + (', '.join(d['devs']) or '(none)')); print('admins:' + (', '.join(d['admins']) or '(none)') + '  (triage implicitly)')" </dev/null

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

# Use the person's SIGN-IN EMAIL: that's what joins their key spend to their
# chat spend in the usage tools (a non-email user_id needs an aliases: entry
# in usage-mcp/roster.yaml to fold back onto the student).  Budget defaults to
# the course's key_fuse.
#
# This prints METADATA, never the key.  It used to call /key/generate straight
# at the gateway, which made a key that was outside the course team (so it drew
# on no pool), outside OpenBao (so nobody could ever read it back), and outside
# every audit — a fresh orphan on every run.  All durable minting now goes
# through the registrar's mint-and-escrow transaction.  See `just key-show`.
#
# Mint a per-user virtual key, escrowed:  just key engr301 amaya@example.edu [budget]
key slug email budget="0":
    {{compose}} exec -T registrar python course_admin.py mint "{{slug}}" "{{email}}" --budget {{budget}} </dev/null

# Prompts AND knowledge, in one pass: instructions from corpus/<slug>/
# SYSTEM-PROMPT.md, knowledge from that guide's corpus (replaced wholesale —
# corpus/ is a render, so what is attached has no authority worth keeping).
# Ends by printing this box's modelSpecs block, which is hand-written once per
# instance into site/ — see docs/admin-guide.md, "The vestibule".
#
# Idempotent, and UPDATE-IN-PLACE on purpose: modelSpecs entries reference
# agent_id, so recreating an agent mints a new id and silently orphans every
# spec pointing at the old one — the guides just vanish from the picker.
# The guides are owned by a SERVICE ACCOUNT the seeder creates in Mongo
# (guides@almanac.invalid — no credentials, cannot sign in).  Never a person:
# whoever owns the guides can delete their knowledge files from "Manage
# files," and a faculty owner did exactly that (2026-09-15).  The seeder
# opens AGENTS.CREATE on the ADMIN role for the run, because the vestibule
# seeds it false for everyone.  Never edit an agent's instructions in the UI — the next
# run overwrites them; the version that matters is docs/agent-contract.md.
#
# --skip-files refreshes only the prompts (seconds, not minutes).
#
# Seed/refresh the guide agents on the flagship:  just agents-seed
agents-seed *flags="":
    @{{just_executable()}} docs-corpus
    python3 scripts/seed_agents.py {{flags}}

# Read-only, and safe to run any time.  The four ways the vestibule goes
# wrong, in the order it goes wrong: no modelSpecs block on this box, enforce
# not set, a spec pointing at an agent id that no longer exists, or a guide
# with no knowledge attached.
#
# Verify the flagship's guides:  just agents-check
agents-check:
    @python3 scripts/agents_check.py

# Ask every guide every case in docs/agent-contract.md and write down what it
# said.  Scores nothing -- a human reads the transcript against each case's
# passing condition, because "answers from the roster documentation" is not a
# string match.  Results land in site/evals/ (per-box, gitignored).
#
# Run it after a prompt change, after a model change, and before anyone
# outside touches the guides.  Results are per MODEL, not per prompt: a
# smaller local model fails these more often than a frontier one.
#
#   just evals
#   just evals --guide student-guide --case F1,M1
evals *flags="":
    @python3 scripts/run_evals.py {{flags}}

# OpenBao audits the read, and this must never run from CI, a health check, or
# anything a model can reach.
#
# Break-glass: print one escrowed key.  just key-show engr301 amaya@example.edu
key-show slug email:
    {{compose}} exec -T registrar python course_admin.py show-key "{{slug}}" "{{email}}" </dev/null

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
