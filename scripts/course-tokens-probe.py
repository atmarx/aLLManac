# Runs INSIDE the registrar container (`just course-tokens-check`), piped in
# over stdin — the prod-probe pattern: no token leaves the box, and none is
# ever printed.  Decision 32 says a course's MCP token speaks for that course
# and no other; this asks the two live services whether that is true.
#
# Per rendered (non-archived) course, per service:
#   static  — fleet/<slug>.env holds the token the current secret derives
#             (not the front door's, which is what an old render left there)
#   live    — own token + own X-Course       -> accepted
#             own token + another X-Course   -> refused
#             own token + no X-Course        -> refused
#             front-door token + own X-Course -> refused
# Once per service, the GREEN case for the flagship: front-door token with no
# X-Course is still accepted.  And per archived course: its derived token is
# refused, because its container is gone.
#
# Every call is a cheap read that writes nothing (my_courses, list_courses),
# as an identity on the reserved .invalid TLD that no IdP can assert.

import asyncio
import hmac
import os
import re
import sys

sys.path.insert(0, "/app")
import reconcile  # noqa: E402
import render  # noqa: E402
from fastmcp import Client  # noqa: E402
from fastmcp.client.transports import StreamableHttpTransport  # noqa: E402

PROBE_EMAIL = "probe" + reconcile.REHEARSAL_DOMAIN
# The URLs the courses' own librechat.yaml uses — the probe walks the real path.
SERVICES = {
    "courses": ("http://registrar:8080/mcp", "my_courses", "REGISTRAR_MCP_TOKEN"),
    "usage": ("http://usage-mcp:8080/mcp", "list_courses", "USAGE_MCP_TOKEN"),
}
REFUSAL = re.compile(r"only answers the .* chat itself \(missing or wrong service token\)")
EMAIL = re.compile(r"[\w.+-]+@[\w-]+(\.[\w-]+)+")
NO_SUCH = "no-such-course-probe"

failed = 0


def ok(m: str) -> None:
    print(f"  ok    {m}")


def bad(m: str) -> None:
    global failed
    failed += 1
    print(f"  FAIL  {m}")


def _quiet(text: str) -> str:
    """An unexpected answer is shown so a FAIL can be read — trimmed, and with
    every address but the probe's own replaced, since an answer could in
    principle quote a roster."""
    text = EMAIL.sub(lambda m: m.group(0) if m.group(0) == PROBE_EMAIL else "<email>", text)
    return " ".join(text.split())[:160]


async def verdict(service: str, token: str, course: str) -> tuple[str, str]:
    """("accepted" | "refused" | "error", detail)."""
    url, tool, _var = SERVICES[service]
    headers = {"Authorization": f"Bearer {token}", "X-User-Email": PROBE_EMAIL,
               "X-User-Role": "USER"}
    if course:
        headers["X-Course"] = course
    try:
        async with Client(StreamableHttpTransport(url, headers=headers), timeout=20) as c:
            r = await c.call_tool(tool, {}, raise_on_error=False)
    except Exception as e:  # unreachable service, protocol failure
        return "error", type(e).__name__
    text = " ".join(getattr(b, "text", "") for b in (r.content or []))
    if not r.is_error:
        return "accepted", ""
    if REFUSAL.search(text):
        return "refused", ""
    return "error", _quiet(text)


async def expect(service: str, token: str, course: str, want: str, label: str) -> None:
    got, detail = await verdict(service, token, course)
    if got == want:
        ok(f"{service:<8} {label}: {got}")
    else:
        bad(f"{service:<8} {label}: wanted {want}, got {got}" + (f" — {detail}" if detail else ""))


async def main() -> int:
    courses = reconcile.load_courses()
    live = render.live_slugs(courses)
    archived = sorted(s for s in courses["courses"] if s not in live)
    front = {s: os.environ.get(var, "") for s, (_u, _t, var) in SERVICES.items()}
    secret_set = bool(render.COURSE_MCP_SECRET)

    print("\nthe front door (no X-Course)")
    for service, tok in front.items():
        if not tok:
            bad(f"{service:<8} the registrar holds no front-door token for it — check .env / compose")
            continue
        await expect(service, tok, "", "accepted", "front-door token, no X-Course")
        await expect(service, tok, NO_SUCH, "refused", "front-door token, an unknown X-Course")

    if not secret_set:
        bad("COURSE_MCP_SECRET is unset in the registrar — every course token is refused.  "
            "Run: just secrets && just up && just render")

    rendered = [s for s in live if os.path.exists(f"{render.OUT_FLEET}/{s}.env")]
    for s in live:
        if s not in rendered:
            print(f"\n{s}: no fleet/{s}.env yet — unrendered, skipped (run: just course ...)")
    for slug in rendered:
        print(f"\n{slug}")
        env = render._read_env(f"{render.OUT_FLEET}/{slug}.env")
        others = [s for s in rendered if s != slug]
        other = others[0] if others else NO_SUCH
        for service, (_u, _t, var) in SERVICES.items():
            tok = env.get(var, "")
            derived = render.course_mcp_token(service, slug)
            if not tok:
                bad(f"{service:<8} fleet/{slug}.env has no {var} — run: just render")
                continue
            if front[service] and hmac.compare_digest(tok, front[service]):
                bad(f"{service:<8} fleet/{slug}.env still holds the FRONT DOOR's token — the "
                    "render predates decision 32.  Run: just render")
                continue
            if not derived or not hmac.compare_digest(tok, derived):
                bad(f"{service:<8} fleet/{slug}.env holds a token the current secret doesn't "
                    "derive (rotated secret, or an older render).  Run: just render")
                continue
            ok(f"{service:<8} env holds this course's derived token")
            await expect(service, tok, slug, "accepted", "own token, own X-Course")
            await expect(service, tok, other, "refused",
                         "own token, another course's X-Course" if others
                         else "own token, an unknown X-Course (only one course)")
            await expect(service, tok, "", "refused", "own token, no X-Course")
            if front[service]:
                await expect(service, front[service], slug, "refused",
                             "front-door token, this X-Course")

    if archived and secret_set:
        print("\narchived courses (container gone — token should be too)")
        for slug in archived:
            for service in SERVICES:
                await expect(service, render.course_mcp_token(service, slug), slug,
                             "refused", f"{slug}'s derived token")

    print()
    if failed:
        print(f"course-tokens-check — {failed} FAIL.  A course token that reaches past its "
              "own course is decision 32 not holding; a stale env is `just render`.")
        return 1
    print(f"course-tokens-check — {len(rendered)} course(s): every token speaks for its "
          "own course and no other; the front door's speaks for none.")
    return 0


sys.exit(asyncio.run(main()))
