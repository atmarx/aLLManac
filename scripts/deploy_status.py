#!/usr/bin/env python3
"""The deploy's status board — status/status.json and status/history.json.

`just deploy` calls this around every step (docs/upgrade-page.md); the edge
serves status.json at /_status.json and the upgrade page reads it.  The
justfile owns the order, the flag and the trap; this only keeps the books.

    deploy_status.py begin STEP...        a new run, every step waiting
    deploy_status.py start STEP           STEP is running
    deploy_status.py end STEP done|failed STEP finished, and how long it took
    deploy_status.py finish done|failed   the run is over; append to history

status.json is read by browsers mid-write unless every write is a rename,
so every write is: a temp file in the same directory, then os.replace.  It
never carries an error, a log line, a hostname, an image tag or a version —
a step's name, a label for a student, a state, and timestamps.

ETA: each step's median over the last HISTORY_KEEP runs in history.json.
Until the flag comes down (ALM_REOPEN_AFTER, the step after which `deploy`
removes status/upgrading), eta_seconds counts to the end of that step,
because that is when the page lets people back in; after it, to the end of
the run.  A step with no history yet makes the ETA unknown (null), and the
page says "a few minutes" rather than guess.

Stdlib only: it runs on the host, like the guides' seeder.
"""

import datetime
import json
import os
import statistics
import sys
import tempfile
import time

STATUS_DIR = os.environ.get("ALM_STATUS_DIR", "status")
STATUS = os.path.join(STATUS_DIR, "status.json")
HISTORY = os.path.join(STATUS_DIR, "history.json")
HISTORY_KEEP = 10
REOPEN_AFTER = os.environ.get("ALM_REOPEN_AFTER", "")

# What a student reads for each recipe.  Consecutive steps with the same label
# show as one line on the page, so the operator's fifteen steps are a student's
# handful.  A step missing here still shows, under the fallback.
LABELS = {
    "channel": "Preparing the new version",
    "pull": "Preparing the new version",
    "build": "Preparing the new version",
    "secrets": "Preparing the new version",
    "up": "Restarting services",
    "config-refresh": "Restarting services",
    "bao-unseal": "Restarting services",
    "smoke": "Checking it's serving",
    "oidc-settle": "Checking sign-in",
    "realm-lock": "Running safety checks",
    "egress-check": "Running safety checks",
    "course-tokens-check": "Running safety checks",
    "render-check": "Running safety checks",
    "docs-corpus": "Updating the guides",
    "agents-refresh": "Updating the guides",
    "agents-check": "Updating the guides",
}
FALLBACK = "Finishing up"


def now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def write(path: str, data) -> None:
    d = os.path.dirname(path) or "."
    fd, tmp = tempfile.mkstemp(dir=d, prefix=".status.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(data, f, indent=1)
            f.write("\n")
        os.chmod(tmp, 0o644)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def read(path: str, default):
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def medians() -> dict:
    runs = read(HISTORY, {}).get("runs", [])
    seen: dict = {}
    for run in runs:
        for name, secs in (run.get("seconds") or {}).items():
            if isinstance(secs, (int, float)):
                seen.setdefault(name, []).append(secs)
    return {k: statistics.median(v) for k, v in seen.items()}


def eta(steps: list) -> "int | None":
    med = medians()
    names = [s["name"] for s in steps]
    # Count to the end of the window while it is still ahead; then to the end.
    end = len(steps)
    if REOPEN_AFTER in names:
        i = names.index(REOPEN_AFTER)
        if steps[i]["state"] != "done":
            end = i + 1
    left = [s for s in steps[:end] if s["state"] in ("waiting", "running")]
    if any(s["name"] not in med for s in left):
        return None
    return int(round(sum(med[s["name"]] for s in left)))


def save(st: dict) -> None:
    st["updated"] = now()
    if st.get("state") == "upgrading":
        st["eta_seconds"] = eta(st["steps"])
    else:
        st.pop("eta_seconds", None)
    # The run's own bookkeeping (each step's start time) lives in .run.json,
    # which the edge never serves; status.json gets the public fields only.
    public = dict(st, steps=[{k: v for k, v in s.items() if not k.startswith("_")}
                             for s in st["steps"]])
    write(STATUS, public)
    write(os.path.join(STATUS_DIR, ".run.json"), st)


def load() -> dict:
    st = read(os.path.join(STATUS_DIR, ".run.json"), None)
    if not st or "steps" not in st:
        raise SystemExit("deploy_status: no run in progress (begin first)")
    return st


def step(st: dict, name: str) -> dict:
    for s in st["steps"]:
        if s["name"] == name:
            return s
    raise SystemExit(f"deploy_status: {name} is not a step of this run")


def main(argv: list) -> int:
    if not argv:
        print(__doc__)
        return 2
    verb, args = argv[0], argv[1:]
    os.makedirs(STATUS_DIR, exist_ok=True)
    if verb == "begin":
        save({"state": "upgrading", "started": now(),
              "steps": [{"name": n, "label": LABELS.get(n, FALLBACK), "state": "waiting"}
                        for n in args]})
    elif verb == "start":
        st = load()
        s = step(st, args[0])
        s["state"], s["_t"] = "running", time.time()
        save(st)
    elif verb == "end":
        st = load()
        s = step(st, args[0])
        s["state"] = "done" if args[1:] == ["done"] else "failed"
        if "_t" in s:
            s["seconds"] = int(round(time.time() - s.pop("_t")))
        save(st)
    elif verb == "finish":
        st = load()
        result = "done" if args[:1] == ["done"] else "failed"
        st["state"], st["finished"] = result, now()
        for s in st["steps"]:
            if s["state"] == "running":       # killed mid-step
                s["state"] = "failed"
                s.pop("_t", None)
        save(st)
        # Only steps that finished cleanly say how long a step takes.
        secs = {s["name"]: s["seconds"] for s in st["steps"]
                if s["state"] == "done" and isinstance(s.get("seconds"), int)}
        hist = read(HISTORY, {})
        runs = (hist.get("runs") or []) + [
            {"started": st.get("started"), "result": result, "seconds": secs}]
        write(HISTORY, {"runs": runs[-HISTORY_KEEP:]})
        try:
            os.unlink(os.path.join(STATUS_DIR, ".run.json"))
        except OSError:
            pass
    else:
        print(f"deploy_status: unknown verb {verb!r}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
