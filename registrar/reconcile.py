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
    planes/requests  registrar/requests.yaml — no network, no secrets
    planes/notify    SMTP_PASSWORD and the desk webhook URL (a credential)
    planes/verbs     composition — the only place the planes meet

Everything in the verbs is IDEMPOTENT on purpose — a failed half-apply is
repaired by applying again, and `just course` can be re-run until it's
boring.
"""

# ruff: noqa: F401  — re-exports are the point of this file.

from planes.config import (
    ALMANAC_DOMAIN,
    CHAT_HOST,
    DEFAULT_COURSE_BUDGET,
    GATEWAY_HOST,
    REHEARSAL_DOMAIN,
    SLUG_RE,
)
from planes.courses import (
    CourseClosed,
    CoursesError,
    address_map,
    course_state,
    load_courses,
    name_taken,
    slug_error,
    validate_courses,
    window_ends,
)
from planes.escrow import (
    EscrowUnavailable,
    bao_configured,
    escrow_read,
    escrow_status,
)
from planes.keycloak import (
    kc_ensure_client,
)
from planes.notify import (
    configured as notify_configured,
    desk as notify_desk,
    person as notify_person,
)
from planes.requests import (
    KINDS as REQUEST_KINDS,
    MAX_OPEN_PER_PERSON,
    claim_course as claim_request_course,
    front_door_text,
    open_count,
)
from planes.verbs import (
    MeterUnreadable,
    PoolExhausted,
    answer_request,
    apply_roster,
    archive_course,
    close_course,
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
    reopen_course,
    reports,
    requests_list,
    rotate_student_key,
    set_address,
    set_course_budget,
    set_staff,
    upsert_course,
)
