"""The aLLManac registrar — the reconcile plane.

The ONLY code that holds minting credentials: the LiteLLM master key (mint
and revoke virtual keys, course teams), the Keycloak admin password (course
OIDC clients, the admin/member client roles that gate each instance's
door), and the OpenBao AppRole (the escrow).  The tool plane (server.py)
calls into these functions with identities it took from trusted headers —
it never touches a credential itself.  Keep it that way: this seam is what
makes the blast-radius statement in docs/registrar-spec.md true.

**This module is now a facade.**  The implementation lives in `planes/`,
one module per system we talk to; this file is the plane's public API and
the only import surface server.py and course_admin.py are meant to use.
That is deliberate rather than tidy: the credential boundary is the thing
worth auditing, and one import surface means one list to read.

    planes/config    env + constants (no credentials used, only named)
    planes/courses   registrar/courses.yaml — no network, no secrets
    planes/keycloak  the admin password
    planes/gateway   the LiteLLM master key
    planes/escrow    the OpenBao AppRole
    planes/chatdb    the chat databases, envelope only (no credential)
    planes/nominations  registrar/nominations.yaml — no network, no secrets
    planes/reports   registrar/reports.yaml — no network, no secrets
    planes/verbs     composition — the only place the planes meet

Everything in the verbs is IDEMPOTENT on purpose — a failed half-apply is
repaired by applying again, and `just course` can be re-run until it's
boring.
"""

# ruff: noqa: F401  — re-exports are the point of this file.

from planes.config import (
    ALMANAC_DOMAIN,
    BASE_MODELS,
    BAO_MOUNT,
    CHAT_HOST,
    DEFAULT_CAPABILITIES,
    DEFAULT_COURSE_BUDGET,
    DEFAULT_FUSE,
    KC_REALM,
    KNOWN_CAPABILITIES,
    MAX_FUSE,
    MIN_FUSE,
    SLUG_RE,
)
from planes.courses import (
    CoursesError,
    course_models,
    load_courses,
    load_raw_courses,
    save_courses,
    validate_courses,
)
from planes.escrow import (
    bao_configured,
    escrow_delete,
    escrow_read,
    escrow_status,
    escrow_write,
)
from planes.gateway import (
    ll_delete_key,
    ll_ensure_team,
    ll_key_spend,
    ll_mint_key,
    ll_team_remaining,
)
from planes.keycloak import (
    kc_ensure_client,
    kc_ensure_client_roles,
    kc_set_client_role,
    kc_user_id,
)
from planes.notify import (
    configured as notify_configured,
    desk as notify_desk,
    person as notify_person,
)
from planes.requests import (
    KINDS as REQUEST_KINDS,
    MAX_OPEN_PER_PERSON,
    front_door_text,
    open_count,
)
from planes.verbs import (
    MeterUnreadable,
    PoolExhausted,
    answer_request,
    apply_roster,
    close_report,
    courses_for,
    decide_request,
    decline_nomination,
    ensure_course,
    evals_fixture,
    export_nomination,
    file_report,
    file_request,
    fleet_access,
    fleet_exposure,
    fleet_inventory,
    mint_key,
    nominate_agent,
    nominations,
    reconcile_students_cmd,
    reports,
    requests_list,
    rotate_student_key,
    set_course_budget,
    set_staff,
    upsert_course,
)
