"""The field list the person reviews, confirms and asserts.

It is research compliance's file, kept beside its notes and outside this
repository (INTAKE_FIELDS), because the fields follow the rules.  Its shape
is the screens page's, section 1: id, label, asks, kind (text | long | date
| choice), person_only, options in order, and an optional
options_always_last tail.  A field whose options are to be copied from a
primary text carries `options_from` instead, and until they are, the tool
says they aren't loaded rather than guess.
"""

import yaml

KINDS = ("text", "long", "date", "choice")


def load(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        raw = yaml.safe_load(f) or []
    out, seen = [], set()
    for x in raw:
        fid = str(x.get("id", "")).strip()
        if not fid or fid in seen:
            raise ValueError(f"field list: a field with no id, or {fid!r} twice")
        if x.get("kind") not in KINDS:
            raise ValueError(f"field {fid}: kind must be one of {', '.join(KINDS)}")
        seen.add(fid)
        out.append({"id": fid, "label": str(x.get("label", fid)), "asks": str(x.get("asks", "")),
                    "kind": x["kind"], "person_only": bool(x.get("person_only", False)),
                    "options": [str(o) for o in x.get("options") or []],
                    "options_from": x.get("options_from"),
                    "always_last": [str(o) for o in x.get("options_always_last") or []]})
    return out


def choices(f: dict) -> list[str]:
    """Every choice in the order the page shows it."""
    return f["options"] + f["always_last"]
