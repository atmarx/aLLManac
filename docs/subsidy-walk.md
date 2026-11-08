# The subsidy walk

A course spends $3,000 in a month.  Its college has said it covers the first $2,000 per course, and its department has said it covers half.  What does the course pay?

It depends on who goes first.  College first: the college pays $2,000, the department half of the remaining $1,000, and the course $500.  Department first: the department pays $1,500, the college $1,500, and the course nothing.  Same two promises, two different bills — so the order is a rule this page states, never the order lines happen to sit in a file.

**Status: design, not built.**  `just focus` bills every row at full cost today ([admin-guide.md](admin-guide.md), "The month-end bill").  This page is what it will do, and the two questions at the bottom are what's still open.

## Where subsidies are applied

**In the export, not in OpenChargeback** *(ruled 2026-11-07)*.  OpenChargeback consumes FOCUS rows that are already split into what the owner pays and what each sponsor covers; it doesn't apply rules of its own.  So `planes/billing` runs the walk after the rollup and before the file is written, and the file carries both kinds of row.

## The tree

Every owner the export bills belongs to a **unit**, and units nest: a department under a college, a college under the institution.  A course record names its owning unit (`unit:`), and the top-level `billing:` block names the platform's.  This is not the course's `college:` — that one is a model pack, and a course can draw a college's models without the college paying for anything.

A unit carries what a statement needs: a name, its parent, a `fund_org` to charge or credit, and a `pi_email` — the contact OpenChargeback mails the statement to, and rejects the row without.

**The walk follows the owning unit, not the instructor's home department.**  A course cross-listed or taught by a visitor is still the unit's course, and a research project is billed where it lives, not where its PI is tenured.

## The rules

A rule says who pays, for what, how much, and when:

```yaml
subsidies:
  - name: provost-pilot
    payer: institution        # the unit that pays; its fund_org is credited
    scope: institution        # whose spend it covers — the payer's subtree by default
    covers: all               # all | percent | first
    from: 2026-09-01
    to: 2027-06-30
  - name: engineering-first-2k
    payer: engineering
    covers: first
    amount: 2000              # first $2,000 ...
    per: life                 # ... per course, over the course's whole term
  - name: chemistry-half
    payer: chemistry
    covers: percent
    percent: 50
    ceiling: 500              # optional: never more than $500 ...
    per: month                # ... per course per month
```

Three verbs cover what's been asked for:

- **`all`** — the payer covers everything left.
- **`percent`** — a share of what's left, with an optional `ceiling` per bucket per period.
- **`first`** — the first `amount` dollars per bucket per period.

The bucket is the owner the export already bills: a course, or `platform`.  Periods are `month`, `year` (fiscal, July start unless configured) and `life`, meaning the bucket's whole existence.  A course record is one term, so `life` is "per course, per term."

## The order

**Top-down.  Each rule takes its share of what's left.**  Central money goes first and units top up beneath it, so "the provost covers it all" means exactly that, and the total can't pass 100% of the charge.  Within a charge, rules apply in order of their payer's depth in the tree, root first.

Two rules whose payers sit at the same depth and whose scopes both reach the same bucket would make the order arbitrary again, so `just course-check` refuses them, as it does two rules from one payer with overlapping dates.  The fix is to say which comes first by putting one payer above the other in the tree, which is a fact about the institution, not about the file.

## Caps need a ledger

`first` and a `percent` ceiling are running totals, and a running total with no record of where it was spent goes wrong in exactly two ways.  Re-run a month and the cap is spent twice, so the owner is billed the difference.  Lower a cap mid-year and the remainder goes negative.  OpenChargeback's own converter shipped both bugs and fixed them the same way this will.

The ledger is `billing/subsidy-ledger.json`, **keyed by month**: for each month, each rule, each bucket, what that rule covered.  Running a month replaces that month's entries and nothing else, so a re-run is harmless.  A cap is the configured amount minus every other month's entries in the same period, clamped at zero.  Re-running a month when later months are already on the ledger changes what was left for them, so the export says so and names the months to re-run.  Within a month, charges consume caps in day order, then owner, then model, which is the order the rows are already in.

## The rows

Reg's shape, which is what OpenChargeback's `docs/user-guide/focus-format.md` expects:

- **One usage row per charge.**  `ListCost` is the full price; `BilledCost` is what's left after every rule.  Tags as today, plus `charge_type: usage`.
- **One subsidy row per rule that paid.**  `ListCost` = `BilledCost` = that rule's share.  `fund_org` and `pi_email` are **the payer's**; `project_id` stays the subsidized owner's, so a payer's statement reads one line per course it covered.  Tags add `charge_type: subsidy` and `subsidy_name`.  `ResourceId` gains `:subsidy:<rule>` so OpenChargeback's dedup key stays unique.
- **Every charge adds up:** usage `BilledCost` + Σ subsidy `BilledCost` = `ListCost`.  The export checks it before writing.

## Allocated vs. invoiced

The ledger prices calls from LiteLLM's model price table, not from the provider's invoice.  Cached-token rates, provisioned capacity, discounts and a stale price table each open a gap between what the export allocates and what the hosted models actually cost, and that gap stays on whichever fund paid the invoice.  `just focus --invoiced <amount>` prints the two figures and the difference, so someone decides about the gap rather than finding it.

## Open

1. **Where the tree lives.**  A box-local `registrar/units.yaml` (example tracked, live file gitignored like `courses.yaml`) is the self-contained answer.  An institution that already keeps an org tree — a SIS export, or another tool's structure file — would rather point at it than copy it.  The proposal is the local file, shaped so an import can fill it later.
2. **`year` and the fiscal start.**  July is the common US academic default; it's a setting either way.
