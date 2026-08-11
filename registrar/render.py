"""The aLLManac registrar — the render plane.

Everything the fleet runs FROM is written here, by code, idempotently:
fleet/fleet.yml (the compose include with one chat+meili+panel trio per
course), fleet/<slug>.env (instance secrets — generated once, PRESERVED
forever: regenerating CREDS_KEY orphans every stored credential, ask the
.env.example comment how we know), fleet/<slug>.librechat.yaml (the
instance config with the X-Course literal), fleet/caddy/<slug>.caddy (the
vhosts), and usage-mcp/roster.yaml (the render usage-mcp reads — humans
edit courses.yaml or the group, never this file).

No credentials are HELD here — the two that pass through (OIDC client
secret, course service key) arrive as arguments from the reconcile plane
and land only in gitignored files on the fleet volume.
"""

import os
import secrets as pysecrets
import tempfile

# The one thing render shares with the reconcile planes.  planes.config
# holds no credential and calls nothing — importing it here is a constant
# lookup, not a plane reaching across the seam.
from planes.config import DEFAULT_CAPABILITIES

OUT_FLEET = os.environ.get("OUT_FLEET", "/out/fleet")
OUT_USAGE = os.environ.get("OUT_USAGE", "/out/usage-mcp")

ALMANAC_DOMAIN = os.environ.get("ALMANAC_DOMAIN", "localhost")
AUTH_HOST = os.environ.get("AUTH_HOST", "auth.localhost")
KC_REALM = os.environ.get("KC_REALM", "northwinds")
EDGE_TLS = os.environ.get("EDGE_TLS", "internal")
OPENID_BUTTON_LABEL = os.environ.get("OPENID_BUTTON_LABEL", "Sign in with Campus SSO")
USAGE_MCP_TOKEN = os.environ.get("USAGE_MCP_TOKEN", "")
REGISTRAR_MCP_TOKEN = os.environ.get("REGISTRAR_MCP_TOKEN", "")


def _atomic_write(path: str, content: str) -> None:
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
  almanac-usage:
    type: streamable-http
    url: http://usage-mcp:8080/mcp
    headers:
      Authorization: "Bearer ${{USAGE_MCP_TOKEN}}"
      X-User-Email: "{{{{LIBRECHAT_USER_EMAIL}}}}"
      X-User-Role: "{{{{LIBRECHAT_USER_ROLE}}}}"
  almanac-registrar:
    type: streamable-http
    url: http://registrar:8080/mcp
    headers:
      Authorization: "Bearer ${{REGISTRAR_MCP_TOKEN}}"
      X-User-Email: "{{{{LIBRECHAT_USER_EMAIL}}}}"
      X-User-Role: "{{{{LIBRECHAT_USER_ROLE}}}}"
      X-Course: "{slug}"

endpoints:
  custom:
    - name: "Almanac"
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
      modelDisplayLabel: "{name}"

  # `actions` is absent unless the course record opts in (capabilities:) —
  # arbitrary-URL tool calls are the one path around the gateway; see the
  # spec's "The floor" section before enabling:
  agents:
    capabilities: [{caps}]
"""
    _atomic_write(f"{OUT_FLEET}/{slug}.librechat.yaml", content)


# ---- fleet/caddy/<slug>.caddy --------------------------------------------------

def render_course_vhost(slug: str) -> None:
    content = f"""# GENERATED by the registrar — {slug}'s rooms behind the one door.
{slug}.{{$ALMANAC_DOMAIN:{ALMANAC_DOMAIN}}} {{
    tls {{$EDGE_TLS:internal}}
    reverse_proxy chat-{slug}:3080
}}
{slug}-admin.{{$ALMANAC_DOMAIN:{ALMANAC_DOMAIN}}} {{
    tls {{$EDGE_TLS:internal}}
    reverse_proxy panel-{slug}:3000
}}
"""
    _atomic_write(f"{OUT_FLEET}/caddy/{slug}.caddy", content)


# ---- fleet/fleet.yml -----------------------------------------------------------

def render_fleet(courses: dict) -> None:
    """One chat+meili+panel trio per course that has a rendered env (a
    course record alone isn't enough — `just course` renders the env when
    the client secret and service key exist).  Paths are relative to
    fleet/ (compose include resolves them there)."""
    ready = [s for s in sorted(courses["courses"])
             if os.path.exists(f"{OUT_FLEET}/{s}.env")]
    parts = ["# GENERATED by the registrar — the course fleet.",
             "# One LibreChat+Meili+panel trio per course; shared control plane",
             "# (mongo, rag, litellm, keycloak) lives in the root compose.",
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
      RAG_API_URL: "http://rag_api:8000"
      CONFIG_PATH: "/app/librechat.yaml"
    volumes:
      - ./{slug}.librechat.yaml:/app/librechat.yaml:ro
      - chat-{slug}-images:/app/client/public/images
      - chat-{slug}-logs:/app/api/logs
      - caddy-data:/caddy-data:ro
    depends_on:
      mongodb:
        condition: service_healthy
      meili-{slug}:
        condition: service_started
      rag_api:
        condition: service_started
      litellm:
        condition: service_started
      keycloak:
        condition: service_healthy
    restart: unless-stopped

  meili-{slug}:
    image: getmeili/meilisearch:v1.12
    container_name: alm-meili-{slug}
    env_file:
      - {slug}.env
    environment:
      MEILI_NO_ANALYTICS: "true"
    volumes:
      - meili-{slug}-data:/meili_data
    restart: unless-stopped

  panel-{slug}:
    image: ${{ADMIN_PANEL_IMAGE:-registry.librechat.ai/clickhouse/librechat-admin-panel:latest@sha256:9a78851f84f448eab780ac658c4d17db51974c240492affc789a72d61e35f678}}
    container_name: alm-panel-{slug}
    env_file:
      - {slug}.env
    environment:
      PORT: "3000"
      API_SERVER_URL: "http://chat-{slug}:3080"
      SESSION_COOKIE_SECURE: "false"
    depends_on:
      chat-{slug}:
        condition: service_started
    restart: unless-stopped""")
    if ready:
        parts.append("\nvolumes:")
        for slug in ready:
            parts += [f"  chat-{slug}-images:", f"  chat-{slug}-logs:",
                      f"  meili-{slug}-data:"]
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
        lines.append(f"    name: {c['name']!r}")
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


# ---- the per-course umbrella ---------------------------------------------------

def render_course(courses: dict, slug: str, oidc_secret: str,
                  service_key: str) -> None:
    from planes.courses import course_models  # data helper, no credentials
    course = courses["courses"][slug]
    models = course_models(course, courses)
    render_course_env(slug, course, models, oidc_secret, service_key)
    render_course_librechat(slug, course, models)
    render_course_vhost(slug)
