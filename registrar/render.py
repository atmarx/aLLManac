"""The aLLManac registrar — the render plane.

Everything the fleet runs FROM is written here, by code, idempotently:
fleet/fleet.yml (the compose include with one chat+meili+rag+panel set per
course), fleet/<slug>.env (instance secrets — generated once, PRESERVED
forever: regenerating CREDS_KEY orphans every stored credential, ask the
.env.example comment how we know), fleet/conf/<slug>/librechat.yaml (the
instance config with the X-Course literal), fleet/caddy/<slug>.caddy (the
vhosts), and usage-mcp/roster.yaml (the render usage-mcp reads — humans
edit courses.yaml, never this file).

No credentials are HELD here — the two that pass through (OIDC client
secret, course service key) arrive as arguments from the reconcile plane
and land only in gitignored files on the fleet volume.
"""

import json
import os
import secrets as pysecrets
import tempfile

# The one thing render shares with the reconcile planes.  planes.config
# holds no credential and calls nothing — importing it here is a constant
# lookup, not a plane reaching across the seam.
from planes.config import DEFAULT_CAPABILITIES, DEFAULT_CONTEXT_TOKENS

OUT_FLEET = os.environ.get("OUT_FLEET", "/out/fleet")
OUT_USAGE = os.environ.get("OUT_USAGE", "/out/usage-mcp")

ALMANAC_DOMAIN = os.environ.get("ALMANAC_DOMAIN", "localhost")
AUTH_HOST = os.environ.get("AUTH_HOST", "auth.localhost")
KC_REALM = os.environ.get("KC_REALM", "classroom")
EDGE_TLS = os.environ.get("EDGE_TLS", "internal")
OPENID_BUTTON_LABEL = os.environ.get("OPENID_BUTTON_LABEL", "Sign in with Campus SSO")
USAGE_MCP_TOKEN = os.environ.get("USAGE_MCP_TOKEN", "")
REGISTRAR_MCP_TOKEN = os.environ.get("REGISTRAR_MCP_TOKEN", "")
MODEL_PROVIDER_NAME = os.environ.get("MODEL_PROVIDER_NAME", "Almanac")
MCP_SERVER_PREFIX = os.environ.get("MCP_SERVER_PREFIX", "almanac")


# ---- dry run -------------------------------------------------------------------
# Every write in this plane goes through _atomic_write, so one flag at the
# choke point makes the whole module read-only.  That is what lets
# `course_admin.py render --check` run in the middle of a deploy: a guard that
# can never be the thing that changed the box.
_DRY_RUN = False
_DRIFT: list[tuple[str, str]] = []


def begin_dry_run() -> None:
    """Render into memory and record what would have changed."""
    global _DRY_RUN
    _DRY_RUN = True
    _DRIFT.clear()


def end_dry_run() -> list[tuple[str, str]]:
    """Stop rendering into memory.  Returns [(path, "missing"|"differs")]."""
    global _DRY_RUN
    _DRY_RUN = False
    return list(_DRIFT)


def rendered_credentials(slug: str) -> tuple[str, str]:
    """The OIDC client secret and service key as the LAST render left them.

    A drift check must not call Keycloak or read escrow — both mutate or
    audit — so it sources the two pass-through credentials from the render
    it is checking.  ("", "") means the course has no render yet.
    """
    env = _read_env(f"{OUT_FLEET}/{slug}.env")
    return env.get("OPENID_CLIENT_SECRET", ""), env.get("COURSE_SERVICE_KEY", "")


def _atomic_write(path: str, content: str) -> None:
    if _DRY_RUN:
        try:
            with open(path) as f:
                current = f.read()
        except OSError:
            _DRIFT.append((path, "missing"))
        else:
            if current != content:
                _DRIFT.append((path, "differs"))
        return
    d = os.path.dirname(path) or "."
    os.makedirs(d, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=d, prefix=".render.")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(content)
        os.chmod(tmp, 0o644)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _read_env(path: str) -> dict:
    out: dict = {}
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    out[k.strip()] = v
    except OSError:
        pass
    return out


# ---- fleet/<slug>.env ----------------------------------------------------------

def render_course_env(slug: str, course: dict, models: list[str],
                      oidc_secret: str, service_key: str) -> None:
    """The instance's whole environment — and NOTHING from the root .env:
    no master key, no other course's anything.  Fill-preserving: values
    that exist are never touched (CREDS_KEY/IV above all)."""
    path = f"{OUT_FLEET}/{slug}.env"
    have = _read_env(path)

    def keep(k: str, gen) -> str:
        return have[k] if have.get(k) else gen()

    host = f"{slug}.{ALMANAC_DOMAIN}"
    vals: dict[str, str] = {
        # -- pinned-once secrets (regenerating = orphaned data; never touch) --
        "JWT_SECRET": keep("JWT_SECRET", lambda: pysecrets.token_hex(32)),
        "JWT_REFRESH_SECRET": keep("JWT_REFRESH_SECRET", lambda: pysecrets.token_hex(32)),
        "CREDS_KEY": keep("CREDS_KEY", lambda: pysecrets.token_hex(32)),
        "CREDS_IV": keep("CREDS_IV", lambda: pysecrets.token_hex(16)),
        "MEILI_MASTER_KEY": keep("MEILI_MASTER_KEY", lambda: pysecrets.token_hex(16)),
        # The course's OWN vector store (rag-<slug> + vectordb-<slug>, below in
        # fleet.yml) — POSTGRES_* is what both images read.  Pinned-once like
        # the rest: a regenerated password strands the course's knowledge.
        "POSTGRES_DB": "vectordb",
        "POSTGRES_USER": "rag",
        "POSTGRES_PASSWORD": keep("POSTGRES_PASSWORD", lambda: pysecrets.token_hex(16)),
        "OPENID_SESSION_SECRET": keep("OPENID_SESSION_SECRET", lambda: pysecrets.token_hex(32)),
        "SESSION_SECRET": keep("SESSION_SECRET", lambda: pysecrets.token_hex(32)),
        # -- authoritative from the reconcile plane (rewritten each render) --
        "OPENID_CLIENT_SECRET": oidc_secret,
        "COURSE_SERVICE_KEY": service_key,
        # -- identity: this course's own client, this course's own door --
        "OPENID_ISSUER": f"https://{AUTH_HOST}/realms/{KC_REALM}",
        "OPENID_CLIENT_ID": slug,
        "OPENID_SCOPE": "openid profile email",
        "OPENID_CALLBACK_URL": "/oauth/openid/callback",
        "OPENID_BUTTON_LABEL": OPENID_BUTTON_LABEL,
        "OPENID_ADMIN_ROLE": "admin",
        "OPENID_ADMIN_ROLE_PARAMETER_PATH": f"resource_access.{slug}.roles",
        "OPENID_ADMIN_ROLE_TOKEN_KIND": "access",
        # The door: no `member` client role, no login (see the spec — the
        # roster grants it, un-enrollment revokes it):
        "OPENID_REQUIRED_ROLE": "member",
        "OPENID_REQUIRED_ROLE_PARAMETER_PATH": f"resource_access.{slug}.roles",
        "OPENID_REQUIRED_ROLE_TOKEN_KIND": "access",
        # -- login posture: SSO only, same as the flagship instance --
        "ALLOW_EMAIL_LOGIN": "false",
        "ALLOW_REGISTRATION": "false",
        "ALLOW_SOCIAL_LOGIN": "true",
        # -- what the tab and the login page call this place.  Found on the
        # first real end-to-end provision (2026-09-15): without it every
        # course is "LibreChat", and a student with three courses open has
        # three identical tabs. --
        "APP_TITLE": course["name"],
        # -- where this instance lives --
        "DOMAIN_CLIENT": f"https://{host}",
        "DOMAIN_SERVER": f"https://{host}",
        "VITE_API_BASE_URL": f"https://{host}",
        # -- service tokens the instance's librechat.yaml substitutes --
        "USAGE_MCP_TOKEN": USAGE_MCP_TOKEN,
        "REGISTRAR_MCP_TOKEN": REGISTRAR_MCP_TOKEN,
        # -- the course itself, for anything that wants to say its name --
        "COURSE_SLUG": slug,
        "COURSE_NAME": course["name"],
    }
    if EDGE_TLS == "internal":
        # Node must trust the edge's internal CA for its one-shot OIDC
        # discovery (same mount the flagship instance uses):
        vals["NODE_EXTRA_CA_CERTS"] = "/caddy-data/caddy/pki/authorities/local/root.crt"

    lines = [f"# GENERATED by the registrar for course {slug} — fill-preserving:",
             "# secrets persist across renders; edit courses.yaml, not this file."]
    lines += [f"{k}={v}" for k, v in vals.items()]
    _atomic_write(path, "\n".join(lines) + "\n")


# ---- fleet/<slug>.librechat.yaml ----------------------------------------------

def render_course_librechat(slug: str, course: dict, models: list[str]) -> None:
    name = course["name"]
    model_list = ", ".join(f'"{m}"' for m in models)
    # .get, so a record loaded by an older registrar still renders.
    context_tokens = int(course.get("context_tokens") or DEFAULT_CONTEXT_TOKENS)
    # .get with a default (not `or`) — a course record's explicit empty list
    # means "none," and must survive to the render.  The default comes from
    # planes.config, which is the source of truth; this used to be a
    # hand-built copy with a "change both together" comment on it, and the
    # split gave the constant a home neutral enough to just import.
    caps = ", ".join(f'"{c}"' for c in course.get(
        "capabilities", DEFAULT_CAPABILITIES))
    # `actions:` is TOP-LEVEL in librechat.yaml, NOT under endpoints.agents —
    # verified against the v0.8.7 pin's own schema, where ToolService reads
    # appConfig.actions.allowedDomains.  Rendered whenever the course declares
    # domains, even if `actions` is currently off: the allowlist is then
    # already in place the moment someone turns the capability on, rather
    # than one forgotten edit behind it.
    domains = course.get("allowed_domains") or []
    actions_block = ""
    if domains:
        actions_block = ("\n# Where this course's agent Actions may reach — the wall around\n"
                         "# the one path that leaves the gateway (spec: \"The floor\").\n"
                         "actions:\n  allowedDomains:\n"
                         + "".join(f'    - "{d}"\n' for d in domains))
    content = f"""# GENERATED by the registrar for {slug} — edits will be overwritten.
# This is the per-course variant of librechat/librechat.yaml: same classroom
# posture, plus the X-Course literal that makes the registrar's tools
# zero-argument in this instance.
version: 1.2.8
cache: true

registration:
  socialLogins: ["openid"]

interface:
  agents:
    use: true
    create: true
    share: true
    public: false
  peoplePicker:
    users: true
    groups: true
    roles: false
  marketplace:
    use: true

fileConfig:
  endpoints:
    default:
      fileLimit: 10
      fileSizeLimit: 25
      totalSizeLimit: 100

mcpSettings:
  allowedAddresses:
    - "usage-mcp:8080"
    - "registrar:8080"
{actions_block}
# Identity rides trusted headers; the course rides a rendered literal.
# Neither is ever a tool argument — see docs/registrar-spec.md.
mcpServers:
  {MCP_SERVER_PREFIX}-usage:
    type: streamable-http
    url: http://usage-mcp:8080/mcp
    headers:
      Authorization: "Bearer ${{USAGE_MCP_TOKEN}}"
      X-User-Email: "{{{{LIBRECHAT_USER_EMAIL}}}}"
      X-User-Role: "{{{{LIBRECHAT_USER_ROLE}}}}"
  {MCP_SERVER_PREFIX}-registrar:
    type: streamable-http
    url: http://registrar:8080/mcp
    headers:
      Authorization: "Bearer ${{REGISTRAR_MCP_TOKEN}}"
      X-User-Email: "{{{{LIBRECHAT_USER_EMAIL}}}}"
      X-User-Role: "{{{{LIBRECHAT_USER_ROLE}}}}"
      X-Course: "{slug}"

endpoints:
  custom:
    - name: "{MODEL_PROVIDER_NAME}"
      # THIS course's team-scoped service key — chat spend drains the same
      # pool as the students' vAPI keys; the master key never enters here:
      apiKey: "${{COURSE_SERVICE_KEY}}"
      baseURL: "http://litellm:4000/v1"
      headers:
        x-litellm-end-user-id: "{{{{LIBRECHAT_USER_EMAIL}}}}"
      models:
        default: [{model_list}]
        fetch: false
      titleConvo: true
      titleModel: "{models[0]}"
      modelDisplayLabel: {json.dumps(name, ensure_ascii=False)}
      # EXPLICIT on purpose.  Omitted, LibreChat falls back to its own
      # default for a model it doesn't recognise — an undocumented number
      # that moves on a version bump.  Per course because the right answer
      # is per model, and `models:` is in the course record.
      maxContextTokens: {context_tokens}

  # `actions` is absent unless the course record opts in (capabilities:) —
  # arbitrary-URL tool calls are the one path around the gateway; see the
  # spec's "The floor" section before enabling:
  agents:
    capabilities: [{caps}]
"""
    _atomic_write(f"{OUT_FLEET}/conf/{slug}/librechat.yaml", content)


# ---- fleet/caddy/<slug>.caddy --------------------------------------------------

def render_course_vhost(slug: str) -> None:
    # X-Tenant-Id: stripped for the same reason as the flagship — see the
    # chat block in caddy/Caddyfile.
    content = f"""# GENERATED by the registrar — {slug}'s rooms behind the one door.
{slug}.{{$ALMANAC_DOMAIN:{ALMANAC_DOMAIN}}} {{
    tls {{$EDGE_TLS:internal}}
    reverse_proxy chat-{slug}:3080 {{
        header_up -X-Tenant-Id
    }}
}}
{slug}-admin.{{$ALMANAC_DOMAIN:{ALMANAC_DOMAIN}}} {{
    tls {{$EDGE_TLS:internal}}
    reverse_proxy panel-{slug}:3000
}}
"""
    _atomic_write(f"{OUT_FLEET}/caddy/{slug}.caddy", content)


# ---- fleet/fleet.yml -----------------------------------------------------------

def live_slugs(courses: dict) -> list[str]:
    """Every course that still renders — all but the archived.  A closed
    course is frozen, not gone: its students are inside their export
    window, so it keeps its instance and its vhost until course-archive.
    Every loop that renders courses goes through here, or `just render`
    quietly brings an archived course back online."""
    return sorted(s for s, c in courses["courses"].items() if not c.get("archived"))


def remove_course_vhost(slug: str) -> None:
    """course-archive's half of the edge: the course's vhost file goes, and
    its hostname falls through to the no-course page at the next reload.
    Only the vhost — fleet/<slug>.env holds the CREDS pair that decrypts the
    course's database, and archiving is not deleting."""
    try:
        os.remove(f"{OUT_FLEET}/caddy/{slug}.caddy")
    except FileNotFoundError:
        pass


def render_addresses(courses: dict) -> None:
    """fleet/caddy/_addresses.caddy — each stable `address:` as a redirect
    to the term that claims it today (planes.courses.address_map decides).

    302, never 301: a browser caches a 301 indefinitely, and this target
    moves every term — a student who visited last fall would be sent to
    last fall's course by their own browser, with nothing on our side to
    correct it.  The panel address rides along, so `engr301-admin.` is the
    instructor's stable bookmark the way `engr301.` is the class's."""
    from planes.courses import address_map  # data helper, no credentials
    dom = f"{{$ALMANAC_DOMAIN:{ALMANAC_DOMAIN}}}"
    parts = ["# GENERATED by the registrar — stable course addresses.",
             "# Each `address:` in courses.yaml redirects (302) to the term that",
             "# claims it.  Edit courses.yaml, never this file."]
    for addr, slug in address_map(courses).items():
        for suffix in ("", "-admin"):
            parts.append(f"""
{addr}{suffix}.{dom} {{
    tls {{$EDGE_TLS:internal}}
    redir https://{slug}{suffix}.{dom}{{uri}} 302
}}""")
    _atomic_write(f"{OUT_FLEET}/caddy/_addresses.caddy", "\n".join(parts) + "\n")


def render_fleet(courses: dict) -> None:
    """One chat+meili+rag+vectordb+panel set per course that has a rendered env (a
    course record alone isn't enough — `just course` renders the env when
    the client secret and service key exist).  Paths are relative to
    fleet/ (compose include resolves them there)."""
    ready = [s for s in live_slugs(courses)
             if os.path.exists(f"{OUT_FLEET}/{s}.env")]
    # Before fleet.yml, which is what the fleet watcher fires on: a reload
    # triggered by this render must already see the addresses it carries.
    render_addresses(courses)
    parts = ["# GENERATED by the registrar — the course fleet.",
             "# One LibreChat+Meili+RAG+pgvector+panel set per course; the shared",
             "# control plane (mongo, litellm, keycloak) lives in the root compose.",
             "# RAG is per course ON PURPOSE: LibreChat signs its RAG calls with",
             "# the same JWT_SECRET it signs sessions with, so a shared rag_api",
             "# means shared sessions — see design-walls.md, 2026-09-18.",
             "# Edit courses.yaml and run `just course` — never this file.",
             "services:"]
    if not ready:
        parts[-1] = "services: {}"
    for slug in ready:
        parts.append(f"""
  chat-{slug}:
    image: ${{LIBRECHAT_IMAGE:-ghcr.io/danny-avila/librechat:v0.8.7}}
    container_name: alm-chat-{slug}
    env_file:
      - {slug}.env
    environment:
      HOST: 0.0.0.0
      MONGO_URI: "mongodb://mongodb:27017/LibreChat_{slug}"
      MEILI_HOST: "http://meili-{slug}:7700"
      SCHEDULES_SINGLE_PROCESS: "true"   # see compose.yml
      # See compose.yml: unset SEARCH means the per-course Meili indexes
      # nothing and search never appears.  Not a knob yet — making it one is a
      # course-record field, which is registrar design and @marco's call.
      SEARCH: "true"
      RAG_API_URL: "http://rag-{slug}:8000"
      CONFIG_PATH: "/app/conf/librechat.yaml"
    volumes:
      # A per-course DIRECTORY, not the single file: this render is an
      # atomic tmp+rename, so a single-file bind would pin the old inode
      # and a re-rendered allowlist would never reach the running
      # instance.  Per-COURSE because fleet/ holds every course's .env —
      # mounting the fleet root here would hand one course the rest of
      # the fleet's secrets.
      - ./conf/{slug}:/app/conf:ro
      - chat-{slug}-images:/app/client/public/images
      # Every non-image upload — agent knowledge files, attachments — lands
      # here, and until 2026-09-25 it was the container's writable layer:
      # gone at every recreate, which every image bump and `just render`
      # is.  The embeddings survived in vectordb-{slug}; the originals did
      # not.  The image ships /app/uploads owned by node, so a fresh named
      # volume inherits the right owner.
      - chat-{slug}-uploads:/app/uploads
      - chat-{slug}-logs:/app/api/logs
      - caddy-data:/caddy-data:ro
    depends_on:
      mongodb:
        condition: service_healthy
      meili-{slug}:
        condition: service_started
      rag-{slug}:
        condition: service_started
      litellm:
        condition: service_started
      keycloak:
        condition: service_healthy
    restart: unless-stopped

  meili-{slug}:
    image: ${{MEILI_IMAGE:-getmeili/meilisearch:v1.12}}
    container_name: alm-meili-{slug}
    env_file:
      - {slug}.env
    environment:
      MEILI_NO_ANALYTICS: "true"
    volumes:
      - meili-{slug}-data:/meili_data
    restart: unless-stopped

  # The course's own knowledge store.  env_file hands both containers the
  # course's env — the course's secrets, which is the same grant meili-{slug}
  # already has, and nothing of any other course's.  JWT_SECRET is the one
  # that matters: it is this instance's session secret, and rag_api verifies
  # every call against it.
  vectordb-{slug}:
    image: ${{PGVECTOR_IMAGE:-pgvector/pgvector:pg16}}
    container_name: alm-vectordb-{slug}
    env_file:
      - {slug}.env
    volumes:
      - vector-{slug}-data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U rag -d vectordb"]
      interval: 10s
      timeout: 5s
      retries: 10
    restart: unless-stopped

  rag-{slug}:
    image: ${{RAG_API_IMAGE:-ghcr.io/danny-avila/librechat-rag-api-dev:latest@sha256:c3e1a05bdd576b5000fa0e8a84a476e9858fa9219b2b5d78432ddce12c9fcf23}}
    container_name: alm-rag-{slug}
    env_file:
      - {slug}.env
    environment:
      DB_HOST: vectordb-{slug}
      DB_PORT: "5432"
      RAG_PORT: "8000"
      # Same local embeddings as the flagship's rag_api in compose.yml; the
      # model files come from the shared hf-cache volume (`just embed-stage`).
      EMBEDDINGS_PROVIDER: huggingface
      EMBEDDINGS_MODEL: "BAAI/bge-small-en-v1.5"
    volumes:
      - hf-cache:/root/.cache/huggingface
    depends_on:
      vectordb-{slug}:
        condition: service_healthy
    restart: unless-stopped

  panel-{slug}:
    image: ${{ADMIN_PANEL_IMAGE:-registry.librechat.ai/clickhouse/librechat-admin-panel:latest@sha256:9a78851f84f448eab780ac658c4d17db51974c240492affc789a72d61e35f678}}
    container_name: alm-panel-{slug}
    env_file:
      - {slug}.env
    environment:
      PORT: "3000"
      API_SERVER_URL: "http://chat-{slug}:3080"
      SESSION_COOKIE_SECURE: "${{ADMIN_PANEL_SESSION_COOKIE_SECURE:-true}}"
    depends_on:
      chat-{slug}:
        condition: service_started
    restart: unless-stopped""")
    if ready:
        parts.append("\nvolumes:")
        for slug in ready:
            parts += [f"  chat-{slug}-images:", f"  chat-{slug}-uploads:",
                      f"  chat-{slug}-logs:",
                      f"  meili-{slug}-data:", f"  vector-{slug}-data:"]
    _atomic_write(f"{OUT_FLEET}/fleet.yml", "\n".join(parts) + "\n")


# ---- usage-mcp/roster.yaml (the render) ---------------------------------------

def render_roster(courses: dict) -> None:
    lines = ["# GENERATED by the registrar — edit registrar/courses.yaml (or the",
             "# course's managed group), never this file.  usage-mcp re-reads it",
             "# live; the registrar rewrites it on every roster change.",
             "courses:"]
    if not courses["courses"]:
        lines[-1] = "courses: {}"
    for slug in sorted(courses["courses"]):
        c = courses["courses"][slug]
        lines.append(f"  {slug}:")
        # json.dumps, NOT repr(): Python and YAML disagree about escaping a
        # single quote.  A name holding both quote kinds reprs to
        # 'Prof\'s "lab"', which PyYAML REFUSES to parse -- and usage-mcp
        # degrades its whole roster to empty on a parse error, so one course
        # name silently takes course-level usage down for every course.  A
        # JSON string is always valid YAML.
        lines.append(f"    name: {json.dumps(c['name'], ensure_ascii=False)}")
        staff = c["instructors"] + c["tas"]
        lines.append("    faculty:" if staff else "    faculty: []")
        lines += [f"      - {e}" for e in staff]
        lines.append("    students:" if c["students"] else "    students: []")
        lines += [f"      - {e}" for e in c["students"]]
        if c["aliases"]:
            lines.append("    aliases:")
            for k, v in c["aliases"].items():
                lines.append(f"      {k}: [{', '.join(v)}]")
    lines.append("admins:" if courses["admins"] else "admins: []")
    lines += [f"  - {e}" for e in courses["admins"]]
    _atomic_write(f"{OUT_USAGE}/roster.yaml", "\n".join(lines) + "\n")


# ---- fleet/inventory.md + .json — the census, rendered -------------------------
# Two outputs from one report: the page is for a person (it lands in mkdocs
# and the index like everything else); the JSON is for whatever the
# security team already stares at.  Envelope only, same as the source.

def _mb(n: int) -> str:
    return f"{n / 1_048_576:.1f} MB" if n >= 1_048_576 else f"{n / 1024:.0f} KB"


def render_inventory(report: dict) -> None:
    _atomic_write(f"{OUT_FLEET}/inventory.json", json.dumps(report, indent=2) + "\n")
    L = ["# GENERATED by the registrar — the fleet from above.",
         "",
         f"Census taken {report['generated']} for `{report['domain']}`.  Metadata only: "
         "counts, names, sizes, owners, and timestamps.  No message, title, or "
         "instruction is read to make this page — see docs/design-walls.md, "
         "\"The census stops at the envelope\".",
         ""]
    fl = report.get("flagship") or {}
    ft = (fl.get("census") or {}).get("totals") or {}
    L += ["## Instances", "",
          "| instance | answers | users | conversations | agents (shared) | files | data | pool spent / cap | roster |",
          "|---|---|---:|---:|---:|---:|---:|---|---|",
          f"| `{fl.get('host', 'chat')}` (flagship) | {'yes' if fl.get('reachable') else 'NO'} | "
          f"{ft.get('users', 0)} | {ft.get('conversations', 0)} | "
          f"{ft.get('agents', 0)} ({ft.get('agents_shared', 0)}) | "
          f"{ft.get('files', 0)} · {_mb(ft.get('file_bytes', 0))} | {_mb(ft.get('storage_bytes', 0))} | — | — |"]
    for c in report.get("courses", []):
        t = (c.get("census") or {}).get("totals") or {}
        pool = c.get("pool") or {}
        cap = pool.get("max_budget")
        spent = f"${pool.get('spend', 0):.2f} / {'$' + format(cap, '.0f') if cap is not None else 'no cap'}" if pool else "no team"
        r = c["roster"]
        state = "yes" if c.get("reachable") else ("NO" if c.get("rendered") else "not rendered")
        L.append(f"| `{c['host']}` | {state} | {t.get('users', 0)} | {t.get('conversations', 0)} | "
                 f"{t.get('agents', 0)} ({t.get('agents_shared', 0)}) | "
                 f"{t.get('files', 0)} · {_mb(t.get('file_bytes', 0))} | {_mb(t.get('storage_bytes', 0))} | "
                 f"{spent} | {r['students']} students, {r['instructors'] + r['tas']} staff |")
    L.append("")
    if report.get("orphan_databases"):
        L += ["**Databases with no course record:** " +
              ", ".join(f"`{n}`" for n in report["orphan_databases"]) +
              " — a deleted course leaves its data behind; drop it on purpose or restore the record.", ""]
    L += ["## Per course", ""]
    for c in report.get("courses", []):
        door = c.get("door") or {}
        L += [f"### {c['name']} (`{c['slug']}`)", "",
              f"- models: {', '.join(c['models'])}",
              f"- capabilities: {', '.join(c['capabilities']) or 'none'}"
              + (f"; Actions may reach: {', '.join(c['allowed_domains'])}" if c['allowed_domains']
                 else ("; **Actions enabled with no allowlist**" if "actions" in c["capabilities"] else "")),
              f"- door (Keycloak): {len(door.get('member', []))} may sign in, "
              f"{len(door.get('admin', []))} admins, {len(door.get('sessions', []))} signed in now"
              if door else ("- door (Keycloak): unreadable" if (c.get("errors") or {}).get("door")
                            else "- door (Keycloak): client not provisioned"),
              f"- pool: {c['pool']['keys']} keys" if c.get("pool") else "- pool: no team",
              ""]
        if c.get("errors"):
            L += ["- **could not read:** " + "; ".join(f"{k} ({v})" for k, v in c["errors"].items()), ""]
        agents = (c.get("census") or {}).get("agents") or []
        shared = [a for a in agents if a["share"] != "private"]
        if shared:
            L += ["| shared agent | owner | scope | tools | files | updated |", "|---|---|---|---|---:|---|"]
            L += [f"| {a['name']} | {a['owner']} | {a['share']} | {', '.join(a['tools']) or '—'} | "
                  f"{a['files']} | {a['updated'] or '—'} |" for a in shared]
            L.append("")
    _atomic_write(f"{OUT_FLEET}/inventory.md", "\n".join(L) + "\n")


# ---- fleet/templates/<id>-<slug>.yaml — a nominated agent, as a file ------------

def template_doc(tpl: dict, provenance: dict) -> dict:
    """An agent's portable shape — one layout for a nomination's template
    and an owner's export, so a file from either reads the same."""
    return {
        "template": {
            "name": tpl["name"], "description": tpl["description"],
            "provider": tpl["provider"], "model": tpl["model"],
            "model_parameters": tpl["model_parameters"],
            "tools": tpl["tools"],
            "knowledge": [{"tool": k["tool"], "filename": k["filename"], "bytes": k["bytes"]}
                          for k in tpl["knowledge"]],
            "instructions": tpl["instructions"],
        },
        "provenance": provenance,
    }


def render_template(rec: dict, tpl: dict) -> str:
    """The portable shape of an agent.  YAML rather than LibreChat's export
    JSON because a person is meant to read and fork it; the knowledge list
    names files without carrying them — the files stay in the course that
    made them, and re-attaching is a deliberate act."""
    import yaml
    slug = "".join(ch if ch.isalnum() else "-" for ch in (tpl.get("name") or "agent").lower()).strip("-")
    path = f"{OUT_FLEET}/templates/{rec['id']}-{slug}.yaml"
    body = template_doc(tpl, {
        "course": rec["course"], "agent_id": rec["agent_id"], "author": tpl["owner"],
        "nominated_by": rec["by"], "nominated_at": rec["at"], "note": rec["note"],
        "actions_on_source": tpl["actions"]})
    head = ("# EXPORTED by the registrar from a nomination — a student's or\n"
            "# instructor's agent, as a file anyone can read, fork, and seed.\n"
            "# Knowledge is listed by name only; attach the files on purpose.\n")
    _atomic_write(path, head + yaml.safe_dump(body, sort_keys=False, allow_unicode=True,
                                              width=1000))
    return path


# ---- the per-course umbrella ---------------------------------------------------

def render_course(courses: dict, slug: str, oidc_secret: str,
                  service_key: str) -> None:
    from planes.courses import course_models  # data helper, no credentials
    course = courses["courses"][slug]
    models = course_models(course, courses)
    render_course_env(slug, course, models, oidc_secret, service_key)
    render_course_librechat(slug, course, models)
    render_course_vhost(slug)
