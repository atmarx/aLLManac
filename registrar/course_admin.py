"""Operator CLI for the registrar — what `just course` execs in-container.

    python course_admin.py create <slug> <name> <instructor...> [--budget N]
                                  [--college X] [--ta EMAIL]...
    python course_admin.py reconcile <slug>     re-run everything, idempotent
    python course_admin.py render               re-render all files (template bumps)
    python course_admin.py render --check       report render drift, change nothing
    python course_admin.py validate             check courses.yaml, touch nothing
    python course_admin.py mint <slug> <email> [--budget N]   mint + escrow, prints no key
    python course_admin.py show-key <slug> <email>   break-glass escrow read (audited)
    python course_admin.py list
    python course_admin.py inventory        the census: fleet/inventory.md + .json
    python course_admin.py nominations      nominated agents, every course
    python course_admin.py template <id>    export a nomination as a template file
    python course_admin.py reports [--status X] [--course S]   problem reports
    python course_admin.py report-close <id> [--note ...]     mark one closed

Runs INSIDE the registrar container (the credentials live there and only
there); the justfile owns docker lifecycle around it — up the new services,
reload the edge.  Chat-side roster upload is the instructors' path; this is
the operator's.
"""

import argparse
import asyncio
import json
import sys

import reconcile
import render


def _upsert(args) -> None:
    data = reconcile.load_courses()
    slug = args.slug.strip().lower()
    c = data["courses"].get(slug) or {
        "name": args.name, "instructors": [], "tas": [],
        "budgets": {"course": reconcile.DEFAULT_COURSE_BUDGET,
                    "key_fuse": reconcile.DEFAULT_FUSE,
                    "advisory_weekly": 2.0},
        "college": None, "models": list(reconcile.BASE_MODELS),
        "group": "", "students": [], "aliases": {},
    }
    c["name"] = args.name
    for i in [e.strip().lower() for e in args.instructors]:
        if i not in c["instructors"]:
            c["instructors"].append(i)
    for t in [e.strip().lower() for e in (args.ta or [])]:
        if t not in c["tas"]:
            c["tas"].append(t)
    if args.budget is not None:
        c["budgets"]["course"] = float(args.budget)
    if args.college:
        c["college"] = args.college.strip().lower()
    data["courses"][slug] = c
    reconcile.save_courses(data)


def _report(errors: list, warnings: list) -> None:
    for w in warnings:
        print(f"warn:  {w}", file=sys.stderr)
    for e in errors:
        print(f"ERROR: {e}", file=sys.stderr)


def _preflight() -> int:
    """Warn before we act, refuse before we half-act.

    Every mutating verb runs this first, so a typo surfaces on the run the
    operator is already watching — a validator you have to remember to run
    is a validator that catches things after the fact.
    """
    errors, warnings = reconcile.validate_courses()
    _report(errors, warnings)
    if errors:
        print(f"\n{len(errors)} error(s) — nothing was changed.",
              file=sys.stderr)
    return 1 if errors else 0


def _render_check(courses: dict) -> int:
    """Read-only: render every course into memory and diff against the volume.

    The gap this closes: `just deploy` builds the registrar image, so a
    changed render.py is sitting IN the container and inert — fleet/ still
    holds the old render and compose recreates nothing, because from its side
    nothing changed.  A Secure-cookie fix landed on the flagship and silently
    skipped every course panel exactly that way (2026-09-18).  It is
    config-refresh one level up: the source is current and the ARTIFACT is not.

    It reports and never repairs.  Recreating a course instance in the middle
    of a routine deploy is a bigger surprise than a red pipeline, and this
    class of bug is one you want told to you.

    The two pass-through credentials come from the render being checked
    (fleet/<slug>.env), never from Keycloak or escrow — so the guard is safe
    to run mid-deploy and can never be the thing that changed the box.
    """
    unrendered = []
    render.begin_dry_run()
    try:
        for slug in sorted(courses["courses"]):
            secret, key = render.rendered_credentials(slug)
            if not secret or not key:
                # No render yet — that's a course awaiting `just course`, not
                # drift.  Reported, not red: chem101 sitting in courses.yaml
                # unprovisioned must not fail every deploy.
                unrendered.append(slug)
                continue
            render.render_course(courses, slug, oidc_secret=secret,
                                 service_key=key)
        render.render_fleet(courses)
        render.render_roster(courses)
    finally:
        drift = render.end_dry_run()

    for slug in unrendered:
        print(f"  unrendered  {slug} — no fleet/{slug}.env (run: just course ...)")
    for path, how in drift:
        print(f"  {how:<10}  {path}")

    checked = len(courses["courses"]) - len(unrendered)
    if drift:
        print(f"\nrender-check — {len(drift)} file(s) STALE on the fleet volume.")
        print("The registrar image is current and the render is not.  On the box:")
        print("  just render")
        return 1
    tail = f" ({len(unrendered)} unrendered)" if unrendered else ""
    print(f"render-check — {checked} course(s), every rendered file current{tail}")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(prog="course_admin")
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("create", help="create/update a course + provision everything")
    c.add_argument("slug")
    c.add_argument("name")
    c.add_argument("instructors", nargs="+")
    c.add_argument("--budget", type=float, default=None,
                   help=f"course pool, USD/term (default {reconcile.DEFAULT_COURSE_BUDGET:g})")
    c.add_argument("--college", default=None, help="model-pack key in colleges:")
    c.add_argument("--ta", action="append", help="TA email (repeatable)")

    r = sub.add_parser("reconcile", help="re-run provisioning + enroll listed students")
    r.add_argument("slug")

    rr = sub.add_parser("render",
                        help="re-render fleet + roster files for all courses")
    rr.add_argument("--check", action="store_true",
                    help="report render drift and change NOTHING (exit 1 if stale)")

    sub.add_parser("validate", help="check courses.yaml and change nothing")

    m = sub.add_parser("mint", help="mint + escrow one key through the registrar transaction")
    m.add_argument("slug")
    m.add_argument("email")
    m.add_argument("--budget", type=float, default=None,
                   help="fuse for this key, USD (default: the course's key_fuse)")

    s = sub.add_parser("show-key", help="break-glass: print an escrowed key (bao audits the read)")
    s.add_argument("slug")
    s.add_argument("email")

    sub.add_parser("list")

    sub.add_parser("inventory", help="the fleet from above — writes fleet/inventory.md + .json")
    sub.add_parser("nominations", help="nominated agents on file")
    t = sub.add_parser("template", help="export a nomination as fleet/templates/<id>-<name>.yaml")
    t.add_argument("nomination_id")

    rp = sub.add_parser("reports", help="problem reports filed from the chat")
    rp.add_argument("--status", default="open",
                    help="open|triaged|closed|all (default open)")
    rp.add_argument("--course", default=None, help="only this slug")
    rc = sub.add_parser("report-close", help="mark a report triaged or closed")
    rc.add_argument("report_id")
    rc.add_argument("--note", default="", help="what was done about it")
    rc.add_argument("--status", default="closed", help="triaged|closed")

    args = p.parse_args()

    if args.cmd == "validate":
        errors, warnings = reconcile.validate_courses()
        _report(errors, warnings)
        n = len(reconcile.load_courses()["courses"])
        print(f"{n} course record(s) — {len(errors)} error(s), "
              f"{len(warnings)} warning(s).")
        return 1 if errors else 0

    if (args.cmd in ("create", "reconcile", "render")
            and not getattr(args, "check", False) and _preflight()):
        return 1

    if args.cmd == "create":
        _upsert(args)
        summary = asyncio.run(reconcile.ensure_course(args.slug.strip().lower()))
        results = reconcile.reconcile_students_cmd(args.slug.strip().lower())
        print(json.dumps(summary, indent=2))
        if results:
            ok = sum(1 for x in results if x["ok"])
            print(f"students: {ok}/{len(results)} enrolled clean")
            for x in results:
                if not x["ok"]:
                    print(f"  FAIL {x['who']}: {x['note']}")
        print(f"\nnext:  just course-up    (starts the instance + reloads the edge)")
        return 0

    if args.cmd == "reconcile":
        slug = args.slug.strip().lower()
        summary = asyncio.run(reconcile.ensure_course(slug))
        results = reconcile.reconcile_students_cmd(slug)
        print(json.dumps(summary, indent=2))
        print(f"students: {sum(1 for x in results if x['ok'])}/{len(results)} clean")
        return 0

    if args.cmd == "render":
        courses = reconcile.load_courses()
        if args.check:
            return _render_check(courses)
        # env/librechat/vhost renders need the two live credentials — reuse
        # what's escrowed/issued rather than re-minting:
        async def _rerender():
            import httpx
            async with httpx.AsyncClient(timeout=30) as cx:
                for slug in courses["courses"]:
                    svc = await reconcile.escrow_read(slug, "service")
                    if svc is None:
                        print(f"skip {slug}: no service key escrowed (run: create/reconcile)")
                        continue
                    _uuid, secret = await reconcile.kc_ensure_client(cx, slug)
                    render.render_course(courses, slug, oidc_secret=secret,
                                         service_key=svc["key"])
                    print(f"rendered {slug}")
        asyncio.run(_rerender())
        render.render_fleet(courses)
        render.render_roster(courses)
        print("fleet.yml + roster.yaml rendered")
        return 0

    if args.cmd == "mint":
        slug, email = args.slug.strip().lower(), args.email.strip().lower()
        try:
            rec = asyncio.run(reconcile.mint_key(slug, email, args.budget))
        except KeyError as e:
            print(f"ERROR: {e.args[0]}", file=sys.stderr)
            return 1
        except reconcile.PoolExhausted as e:
            print(f"REFUSED: {e}", file=sys.stderr)
            return 1
        # Metadata only — the key stays in the escrow.  Reading it back is a
        # deliberate, audited act, not a side effect of minting.
        print(json.dumps({k: v for k, v in rec.items() if k != "key"}, indent=2))
        if rec["already"]:
            print(f"\nalready escrowed for {email} in {slug} — nothing minted.")
        else:
            print(f"\nminted + escrowed for {email} in {slug}.")
        print(f"read it back (break-glass, bao audits the read):"
              f"\n  just key-show {slug} {email}")
        return 0

    if args.cmd == "show-key":
        rec = asyncio.run(reconcile.escrow_read(args.slug.strip().lower(),
                                                args.email.strip().lower()))
        if rec is None:
            print("no escrow record", file=sys.stderr)
            return 1
        print(rec["key"])
        return 0

    if args.cmd == "inventory":
        rep = asyncio.run(reconcile.fleet_inventory())
        fl = rep["flagship"]
        print(f"{fl['host']:40} {'answers' if fl['reachable'] else 'NO ANSWER':10} "
              f"users={fl['census'].get('totals', {}).get('users', 0)}")
        for c in rep["courses"]:
            t = c["census"].get("totals", {})
            pool = c.get("pool")
            ps = f"${pool['spend']:.2f}" if pool else "no team"
            state = "answers" if c["reachable"] else ("NO ANSWER" if c["rendered"] else "unrendered")
            print(f"{c['host']:40} {state:10} users={t.get('users', 0)} convos={t.get('conversations', 0)} "
                  f"agents={t.get('agents', 0)}/{t.get('agents_shared', 0)}shared files={t.get('files', 0)} "
                  f"pool={ps} roster={c['roster']['students']}")
        if rep["orphan_databases"]:
            print("orphan databases: " + ", ".join(rep["orphan_databases"]))
        print("\nwritten: fleet/inventory.md, fleet/inventory.json")
        return 0

    if args.cmd == "nominations":
        rows = reconcile.nominations()
        for r in rows:
            print(f"{r['id']}  {r['status']:9} {r['course']:20} {r['name']} ({r['agent_id']})  "
                  f"by {r['by']} {r['at']}  {r['note']}")
        if not rows:
            print("(no nominations)")
        return 0

    if args.cmd == "template":
        try:
            r = asyncio.run(reconcile.export_nomination(args.nomination_id, "operator"))
        except KeyError as e:
            print(f"ERROR: {e.args[0]}", file=sys.stderr)
            return 1
        print(r["path"])
        return 0

    if args.cmd == "reports":
        want = None if args.status.strip().lower() == "all" else args.status.strip().lower()
        rows = reconcile.reports(args.course, status=want)
        for r in rows:
            print(f"{r['id']}  {r['status']:8} {r['at']}  {r['by']}")
            print(f"    about: {r['about'] or 'UNROUTED'} (via {r['route']})"
                  f"  from: {r['from_room']}"
                  + (f"  enrolled: {', '.join(r['enrolled'])}" if r['enrolled'] else "")
                  + (f"  they said: {r['said_course']}" if r.get("said_course") else ""))
            print(f"    what:  {r['what']}")
            t = r.get("trace") or {}
            # The half that makes a report debuggable — printed in full,
            # because the operator reading this is looking for the corpus gap.
            if t.get("asked"):
                print(f"    asked: {t['asked']}")
            if t.get("answered"):
                print(f"    got:   {t['answered']}")
            if t.get("sources"):
                print(f"    cited: {', '.join(t['sources'])}")
            if r.get("resolution"):
                print(f"    done:  {r['resolution']} ({r.get('decided_by')})")
            print()
        if not rows:
            print(f"(no {want or ''} reports)".replace("  ", " "))
        else:
            unrouted = sum(1 for r in rows if not r["about"])
            no_trace = sum(1 for r in rows if "trace" not in r)
            print(f"{len(rows)} report(s) — {unrouted} unrouted, "
                  f"{no_trace} with no exchange attached.")
        return 0

    if args.cmd == "report-close":
        r = reconcile.close_report(args.report_id.strip(), "operator", args.note,
                                   status=args.status.strip().lower())
        if r is None:
            print(f"no report {args.report_id}", file=sys.stderr)
            return 1
        print(f"{r['id']} -> {r['status']}")
        return 0

    if args.cmd == "list":
        data = reconcile.load_courses()
        for slug, c in sorted(data["courses"].items()):
            print(f"{slug}  {c['name']}  staff={len(c['instructors']) + len(c['tas'])}"
                  f"  students={len(c['students'])}  pool=${c['budgets']['course']:g}")
        if not data["courses"]:
            print("(no courses — just course <slug> \"<name>\" <instructor@email>)")
        return 0

    return 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except reconcile.CoursesError as e:
        # The roster file itself is unreadable — an operator needs the reason,
        # not a traceback, and nothing downstream should have run.
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(2)
