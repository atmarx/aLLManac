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
    planes/verbs     composition — the only place the four meet

Everything in the verbs is IDEMPOTENT on purpose — a failed half-apply is
repaired by applying again, and `just course` can be re-run until it's
boring.
"""

# ruff: noqa: F401  — re-exports are the point of this file.

from planes.config import (
    ALMANAC_DOMAIN,
    BASE_MODELS,
    BAO_MOUNT,
    DEFAULT_CAPABILITIES,
    DEFAULT_COURSE_BUDGET,
    DEFAULT_FUSE,
    KC_REALM,
    KNOWN_CAPABILITIES,
    MAX_FUSE,
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
)
from planes.keycloak import (
    kc_ensure_client,
    kc_ensure_client_roles,
    kc_set_client_role,
    kc_user_id,
)
from planes.verbs import (
    apply_roster,
    ensure_course,
    reconcile_students_cmd,
    rotate_student_key,
)
