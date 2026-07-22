"""Operator CLI for the registrar — what `just course` execs in-container.

    python course_admin.py create <slug> <name> <instructor...> [--budget N]
                                  [--college X] [--ta EMAIL]...
    python course_admin.py reconcile <slug>     re-run everything, idempotent
    python course_admin.py render               re-render all files (template bumps)
    python course_admin.py show-key <slug> <email>   break-glass escrow read (audited)
    python course_admin.py list

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

    sub.add_parser("render", help="re-render fleet + roster files for all courses")

    s = sub.add_parser("show-key", help="break-glass: print an escrowed key (bao audits the read)")
    s.add_argument("slug")
    s.add_argument("email")

    sub.add_parser("list")

    args = p.parse_args()

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

    if args.cmd == "show-key":
        rec = asyncio.run(reconcile.escrow_read(args.slug.strip().lower(),
                                                args.email.strip().lower()))
        if rec is None:
            print("no escrow record", file=sys.stderr)
            return 1
        print(rec["key"])
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
    sys.exit(main())
