"""The month-end bill — the gateway ledger, rolled up to FOCUS rows that
OpenChargeback ingests.

One row per day × owner × model.  The owner is the course the spend rolls
up to (the `owner:<slug>` tag every key carries, or the course team chat
spends on), and the course record says who gets the invoice: its
`billing:` block, falling back to its first instructor.  Spend on the
master key is owned by `platform` — the front door's chat, until the office
is a tenant with its own service key (registrar-spec, Phase 2a) — and the
top-level `billing:` in courses.yaml says who pays for that.  Students never
appear — a bill goes to a PI and a finance office, and who-in-the-class-
used-what is the course's own business (`course_usage`), not theirs.

The money is the ledger's.  ListCost is LiteLLM's `spend`, which is
whatever rate the campus set for the model (`input_cost_per_token` in
litellm/config.yaml), so a model with no price bills $0 with its tokens
still counted.  That is the free-but-visible posture, not a bug, and the
summary says which models it was so nobody mistakes it for missing data.
Subsidies are OpenChargeback's job, applied on its side; every row here
bills what it cost.

Pure: rows in, rows out.  No network, no credential, no file — the census
reads the ledger (`just focus` pipes a psql COPY in), the caller hands us
the course records, and this decides only the shape.
"""

import csv
import io
import json
import re
from calendar import monthrange
from datetime import date

from .config import BILLING_KEYS

# The columns the ledger query in the justfile emits, in its order.
LEDGER_COLUMNS = ("day", "owner", "model", "requests",
                  "input_tokens", "output_tokens", "spend")

# FOCUS column names.  The cost and period columns are the ones
# OpenChargeback reads; the rest are FOCUS's own and cost it nothing.
FOCUS_COLUMNS = (
    "BillingPeriodStart", "BillingPeriodEnd",
    "ChargePeriodStart", "ChargePeriodEnd",
    "ChargeCategory", "ChargeDescription",
    "ProviderName", "ServiceName", "ServiceCategory",
    "ResourceId", "ResourceName", "SkuId",
    "ConsumedQuantity", "ConsumedUnit",
    "ListCost", "ContractedCost", "EffectiveCost", "BilledCost",
    "BillingCurrency", "Tags",
)

# The owner the ledger query gives master-key spend.  Not a slug a course
# can have: course slugs are term-suffixed, and this one is checked first.
PLATFORM_OWNER = "platform"

MONTH_RE = re.compile(r"^(\d{4})-(0[1-9]|1[0-2])$")


def month_bounds(month: str) -> tuple[date, date]:
    """'2026-10' -> (first day, last day).  ValueError on anything else."""
    m = MONTH_RE.match(month or "")
    if not m:
        raise ValueError(f"{month!r} isn't a month — want YYYY-MM")
    y, mo = int(m.group(1)), int(m.group(2))
    return date(y, mo, 1), date(y, mo, monthrange(y, mo)[1])


def invoicee(slug: str, course: dict | None) -> dict:
    """The tags that say who pays for `slug`.  Empty when the owner isn't a
    course this box knows — the caller reports that, it doesn't guess."""
    if not course:
        return {}
    tags = {k: v for k, v in (course.get("billing") or {}).items()
            if k in BILLING_KEYS and v}
    if "pi_email" not in tags and course.get("instructors"):
        tags["pi_email"] = course["instructors"][0]
    tags.setdefault("project_id", slug)
    return tags


def _num(v, cast):
    try:
        return cast(v) if v not in (None, "") else cast(0)
    except (TypeError, ValueError):
        return cast(0)


def rollup(ledger_rows, records: dict, month: str, platform: str):
    """-> (focus_rows, summary).  `ledger_rows` are dicts keyed by
    LEDGER_COLUMNS; `records` is load_courses()."""
    courses = records.get("courses") or {}
    platform_bill = {k: v for k, v in (records.get("billing") or {}).items()
                     if k in BILLING_KEYS and v}
    if platform_bill:
        platform_bill.setdefault("project_id", PLATFORM_OWNER)
    first, last = month_bounds(month)
    out: list[dict] = []
    summary = {
        "month": month, "rows": 0, "requests": 0, "tokens": 0, "cost": 0.0,
        "by_owner": {},       # owner -> {"cost", "tokens", "pi_email", "fund_org"}
        "no_invoicee": {},    # owner -> cost: no course record to bill
        "no_fund_org": set(),  # owners billed to a person with no fund code
        "unpriced": set(),    # models that moved tokens at $0
        "outside": 0,         # ledger rows dated outside the month (a bad query)
    }
    for r in ledger_rows:
        day = str(r.get("day") or "")[:10]
        try:
            d = date.fromisoformat(day)
        except ValueError:
            summary["outside"] += 1
            continue
        if not (first <= d <= last):
            summary["outside"] += 1
            continue
        owner = (r.get("owner") or "").strip().lower()
        model = (r.get("model") or "").strip() or "unknown"
        requests = _num(r.get("requests"), int)
        tin = _num(r.get("input_tokens"), int)
        tout = _num(r.get("output_tokens"), int)
        cost = round(_num(r.get("spend"), float), 6)

        label = owner or "unattributed"
        if owner == PLATFORM_OWNER:
            who = dict(platform_bill)
        else:
            who = invoicee(owner, courses.get(owner)) if owner else {}
        if not who.get("pi_email"):
            summary["no_invoicee"][label] = summary["no_invoicee"].get(label, 0.0) + cost
        elif not who.get("fund_org"):
            summary["no_fund_org"].add(label)
        if cost == 0 and (tin or tout):
            summary["unpriced"].add(model)

        tags = {**who, "owner": label, "model": model, "requests": requests,
                "input_tokens": tin, "output_tokens": tout}
        out.append({
            "BillingPeriodStart": first.isoformat(),
            "BillingPeriodEnd": last.isoformat(),
            "ChargePeriodStart": d.isoformat(),
            "ChargePeriodEnd": d.isoformat(),
            "ChargeCategory": "Usage",
            "ChargeDescription": f"{model}: {requests} requests, {tin + tout} tokens",
            "ProviderName": platform,
            "ServiceName": platform,
            "ServiceCategory": "AI and Machine Learning",
            "ResourceId": f"{label}:{model}",
            "ResourceName": f"{label} — {model}",
            "SkuId": model,
            "ConsumedQuantity": tin + tout,
            "ConsumedUnit": "Tokens",
            "ListCost": f"{cost:.6f}",
            "ContractedCost": f"{cost:.6f}",
            "EffectiveCost": f"{cost:.6f}",
            "BilledCost": f"{cost:.6f}",
            "BillingCurrency": "USD",
            "Tags": json.dumps(tags, sort_keys=True),
        })
        o = summary["by_owner"].setdefault(label, {
            "cost": 0.0, "tokens": 0, "requests": 0,
            "pi_email": who.get("pi_email", ""), "fund_org": who.get("fund_org", "")})
        o["cost"] += cost
        o["tokens"] += tin + tout
        o["requests"] += requests
        summary["rows"] += 1
        summary["requests"] += requests
        summary["tokens"] += tin + tout
        summary["cost"] += cost
    out.sort(key=lambda x: (x["ChargePeriodStart"], x["ResourceId"]))
    return out, summary


def read_ledger(text: str) -> list[dict]:
    """The psql COPY ... CSV HEADER output.  Refuses a header that isn't the
    query's, because a silently shifted column bills the wrong number."""
    reader = csv.DictReader(io.StringIO(text))
    got = tuple(reader.fieldnames or ())
    if got != LEDGER_COLUMNS:
        raise ValueError(f"ledger header is {got or 'missing'}, want {LEDGER_COLUMNS}")
    return list(reader)


def write_focus(rows: list[dict]) -> str:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=FOCUS_COLUMNS, lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue()


def describe(summary: dict) -> str:
    """The operator's read of the file: totals, who pays, and every reason
    a row would bounce or surprise at import."""
    s = summary
    lines = [f"{s['month']}: {s['rows']} rows · {s['requests']} requests · "
             f"{s['tokens']:,} tokens · ${s['cost']:.2f}"]
    for owner, o in sorted(s["by_owner"].items(), key=lambda kv: -kv[1]["cost"]):
        pays = o["pi_email"] or "NOBODY"
        fund = f" / {o['fund_org']}" if o["fund_org"] else ""
        lines.append(f"  {owner:<28} ${o['cost']:>9.2f}  {o['tokens']:>12,} tok  "
                     f"→ {pays}{fund}")
    if s["no_invoicee"]:
        lines.append("  NO INVOICEE (OpenChargeback rejects these rows — no pi_email): "
                     + ", ".join(f"{k} (${v:.2f})" for k, v in sorted(s["no_invoicee"].items())))
        if PLATFORM_OWNER in s["no_invoicee"]:
            lines.append("  `platform` is spend on the master key — the front door's chat "
                         "and operator calls.  A top-level `billing:` in courses.yaml "
                         "says who pays for it.")
    if s["no_fund_org"]:
        lines.append("  no fund_org (billed to the person; set `billing.fund_org` "
                     "in courses.yaml): " + ", ".join(sorted(s["no_fund_org"])))
    if s["unpriced"]:
        lines.append("  priced at $0 (no rate in litellm/config.yaml; tokens still "
                     "counted): " + ", ".join(sorted(s["unpriced"])))
    if s["outside"]:
        lines.append(f"  {s['outside']} ledger rows dated outside {s['month']} were "
                     "dropped — the query and the month disagree")
    return "\n".join(lines)
