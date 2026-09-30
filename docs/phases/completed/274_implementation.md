# Phase 274 — Track O batch 1: CRM, reorder points, warranty, financial reporting, variance

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-09-29 (v1.0 2026-09-29)

**Outcome (v1.1).** Shipped as planned, with one stop at Step 0:
- **The stop:** row 290's P&L needed costs the data did not hold. The
  operator picked option B and added two things: record each quote, and
  state one attribution rule per dimension.
- **All five rows have commands, each exercised by a test.** Rows 279,
  280, 290 and 291 close folded into 274.
- **Migration 076 is live** at schema 76, and its live diff equals the
  approved exact diff; no existing row changed.
- **F182** was filed at Step 0 and closed with its fix.

One bug fix (the relationship column). Regression of record: 10109 passed,
0 failed at `3b7528f`, the close-out commit (and at `757b9f4` before it). Deviations and Results are at the end.

## Goal

Track O batch 1, the local shop data with no outside dependency. Phase 274
carries rows 274, 279, 280, 290 and 291, as 261 carried Track N's first.

- **274, Customer CRM:** a communication log, a customer timeline, bike
  transfer and a bike's ownership history, on top of the existing CRM.
- **279, parts inventory with reorder points:** stock, reorder points and
  quantities, and purchase orders generated locally from them.
- **280, warranty validity and claim records** (rewritten at Step 0): the
  validity lookup, local claim records, a printable claim packet.
  Submission to a maker is row 362, paused.
- **290, financial reporting:** the operator's option B. Direct costs are
  recorded; a gross-margin P&L per mechanic, bay and customer, and a shop
  P&L per period with expenses.
- **291, estimate vs actual variance:** labour, parts and quote variance
  per work order, with F182 fixed and each quote recorded.

Step 0 is `274_step0.md`. Every new capability has a `motodiag` command,
exercised by a test. No API route is added or changed. No outbound network
call.

**The operator's pick (2026-09-29), verbatim** (it arrived as pasted text
in the operator's message):

> B. And F182's fix stays in this batch; the estimate takes its rate from
> the same labor_rates lookup the invoice uses, so the quote and the
> invoice agree.
>
> Two additions:
> 1. Record each quote when estimate_ready is queued: hours, rate, parts,
> total and date. Quote accuracy compares the invoice with that record; a
> work order with no recorded quote shows "no quote recorded", never a
> recomputed figure.
> 2. One attribution rule per dimension, stated in the report: a work
> order's revenue and all its costs count for its assigned mechanic (a
> work order with none counts as unassigned); across bays, a work order is
> split by the slot hours it spent in each; per customer, by the invoice's
> customer.
>
> Note in v1.0 that a mechanic's cost rate is pay data: nothing in this
> batch shows it outside the CLI, and any later API route for it is
> owner-only.

## Logic

### Migration 076 (schema 75 → 76)

New tables only, plus one column on `inventory_items` (0 live rows):

| table | what it holds |
|---|---|
| `customer_communications` | one contact: customer, shop, optional work order, `direction` (`inbound`, `outbound`), `channel` (`phone`, `in_person`, `email`, `sms`, `other`), `summary`, who logged it, when it happened |
| `purchase_orders` | one PO: vendor, `po_number`, `status` (`draft`, `sent`, `received`, `cancelled`), dates, notes |
| `purchase_order_lines` | item, quantity, unit cost in cents at generation |
| `inventory_items.reorder_quantity` | `INTEGER NOT NULL DEFAULT 0`; 0 means not set |
| `warranty_claims` | warranty, optional work order, `status` (`draft`, `submitted`, `approved`, `denied`, `paid`), the maker's claim number, description, amounts claimed and approved in cents, dates |
| `mechanic_cost_rates` | shop, user, cents per hour, `effective_from` date; unique per (shop, user, date) |
| `work_order_part_costs` | a work-order part line's purchase cost each, in cents, apart from what the invoice bills |
| `shop_expenses` | shop, `month` (`YYYY-MM`), category, amount in cents, description |
| `work_order_quotes` | work order, the notification that sent it, hours, rate in cents, parts in cents, total in cents, `quoted_at` |

The rollback drops the tables and rebuilds `inventory_items` without the
column. No existing live row changes: the dry run must show additions to
`schema_version` only, and the schema objects named in the scope file.

### Row 274: the CRM

New `crm/communication_repo.py`; commands under `motodiag shop customer`:
- `log-contact CUSTOMER --channel … --direction … --summary … [--wo ID]
  [--at WHEN]` records a contact.
- `history CUSTOMER [--json]`: one timeline, newest first, of logged
  contacts and queued notifications (`customer_notifications`), each
  labelled with its source.
- `transfer-bike --bike B --from C1 --to C2 [--notes]`: wraps
  `transfer_ownership`. Refused unless C1 is the bike's current owner.
- `bike-owners BIKE`: every customer linked to the bike, current owner
  first, with the relationship and the date linked.
- `transfer_ownership` is made safe for a customer who was already a
  previous owner of the bike (today the UPDATE would break the primary
  key).
- **Bug fix (planned):** `bikes` and `show` print the relationship, not
  `?`.

### Row 279: inventory and purchase orders

`motodiag shop inventory`, over `inventory/item_repo.py` and
`vendor_repo.py`, and a new `inventory/purchase_orders.py`:
- `vendor add`, `vendor list`;
- `add`, `list [--low]`, `show SKU`, `adjust SKU --by N`, `set SKU`
  (reorder point, reorder quantity, vendor, costs, location);
- `reorder`: every item at or below its reorder point, with what a PO
  would order, or why it would not (no reorder quantity; no vendor; already
  on an open PO);
- `po generate`: one draft PO per vendor from `reorder`'s orderable lines;
  prints what it skipped and why;
- `po list`, `po show ID [--out FILE]` (a printable PO), `po mark-sent ID`
  (the user sent it by their own means; nothing leaves the machine),
  `po receive ID` (adds each line's quantity to stock), `po cancel ID`.

Status moves: draft → sent → received; draft or sent → cancelled. Anything
else is refused.

### Row 280: warranty

`motodiag shop warranty`, over `inventory/warranty_repo.py` and a new
`inventory/warranty_claims.py`:
- `add --bike … --coverage … [--provider --start --end --mileage-limit
  --terms]`, `list --bike`;
- `check --bike B [--on DATE] [--mileage N]`: per coverage, **valid**,
  **not valid** with the reason ("ended 2026-03-01", "12,400 mi is over
  the 12,000 mi limit", "starts 2027-01-01"), or **cannot tell** when a
  needed figure is not recorded. The mileage is `--mileage`, else the
  bike's recorded mileage, else unknown. A limit that is not recorded is
  never read as a pass.
- `claim open --warranty W [--wo ID] --description … [--claimed-cents N]`
  (increments `warranties.claim_count`), `claim list`, `claim show`,
  `claim status ID --to … [--claim-number] [--approved-cents]`,
  `claim packet ID [--out FILE]`.
- Claim status moves: draft → submitted → approved or denied; approved →
  paid. Anything else is refused.
- The packet is plain text from stored data: shop, customer, bike and VIN,
  coverage and its validity on the work order's date, the work order,
  its issues, parts and labour hours, the claim's status and amounts.

### Row 290: financial reporting (option B)

**Recording the costs** (new `shop/shop_costs.py`):
- `motodiag shop member cost-rate --shop S --user U --cents-per-hour N
  --from DATE`, and `cost-rates --shop S`.
- `motodiag shop parts-needs cost LINE_ID --cents-each N`: the purchase
  cost of a part line.
- `motodiag shop expense add --shop S --month YYYY-MM --category …
  --cents N [--description]`, `expense list --shop S [--month]`.

**A mechanic's cost rate is pay data.** Nothing in this batch shows it
outside the CLI: no API route, no notification, no report other than the
CLI's own. Any later API route for it is owner-only.

**The report**, `motodiag shop analytics pnl --shop S --by
mechanic|bay|customer|shop --period month|quarter|year --for PERIOD
[--json]`, a new function in `shop/analytics.py` (the existing
`RevenueRollup` and `DashboardSnapshot` are not touched: the API serves
them):
- **Revenue:** invoices not cancelled, issued in the period, their subtotal
  before tax, split into labour, parts, diagnostic and supplies.
- **Parts cost:** each billed part line's recorded purchase cost × its
  quantity.
- **Labour cost:** each closed time entry's hours × the logging user's
  cost rate in force on the entry's date.
- **The attribution rules, stated in the report's own output:**
  - by mechanic: a work order's revenue and all its costs count for its
    assigned mechanic; a work order with none counts as unassigned;
  - by bay: a work order is split across bays by the slot hours it spent
    in each (actual times when recorded, else scheduled); a work order
    with no slot counts as "no bay";
  - by customer: the invoice's customer.
- **Gross margin** = revenue − parts cost − labour cost, per group. A cost
  that was not recorded reads "not recorded (n of m work orders)", and the
  margin is not computed for that group. Nothing unrecorded is shown as
  zero.
- **By shop:** gross margin − expenses = net for the period. Expenses are
  never allocated to a mechanic, bay or customer. Net is computed only when
  every month in the period has at least one expense recorded; otherwise it
  names the months with none.

### Row 291: variance, the quote record, and F182

**F182's fix.** The `estimate_ready` total is the work order's estimated
hours × the rate from `_lookup_labor_rate_cents` (the lookup
`generate_invoice_for_wo` uses) + its estimated parts cost. With no
estimated hours, or no rate, the notification is refused with the reason;
nothing is invented. The old branch that showed an existing invoice's total
as the estimate goes.

**Setting the rate.** No command writes `labor_rates` today; the table is
empty live, so the fixed estimate would always refuse.
`motodiag shop labor-rate set --hourly-cents N [--state XX] [--source …]
[--from DATE]` and `labor-rate list` reuse `pricing/labor_rates.py`
(`add_labor_rate`, `list_all_rates`). The lookup is not changed, so the
quote and the invoice keep agreeing.

**The quote record.** When `estimate_ready` is queued (`queue`, not
`preview`), a `work_order_quotes` row stores the hours, the rate, the parts,
the total and the date, with the notification's id.

**The report**, `motodiag shop analytics variance --shop S [--since 30d]
[--json]`, per completed work order in the window:
- labour: estimated vs actual hours, and the difference in hours and %;
- parts: estimated parts cost vs the billed part lines;
- quote: the latest recorded quote's total vs the invoice's subtotal
  before tax. With no quote recorded: "no quote recorded", never a
  recomputed figure; with no invoice: "not invoiced".
- A work order with no estimate is listed as such, not scored. Totals: how
  many were scored on each, and the median differences.

### Wiring and the allowlist

- `inventory.models`, `item_repo`, `vendor_repo`, `warranty_repo` leave
  `MODULE_ISLANDS`; `motodiag.pricing` and `pricing.labor_rates` leave
  `UNREACHABLE_MODULES`; `transfer_ownership` leaves `ORPHANS`. Whatever
  the gate then names as a new orphan is listed with its reason. The pinned
  counts in `tests/support/integration_gaps_counts.py` move with the lists,
  each with its history line.
- `inventory/__init__.py`'s stale "Track O phases 282-287" is corrected.
- New user-facing text carries no internal reference; the group docstrings
  this batch edits lose theirs.

## Decisions

- **D1.** Option B, the operator's pick; and the two additions.
- **D2.** `customer_notifications` is not the log (S0-2); a new table.
- **D3.** `reorder_quantity` is stored, never inferred; no quantity means
  not ordered, with the reason.
- **D4.** A PO is only ever local. `mark-sent` records that the user sent
  it; sending is a supplier integration, paused with 282–286.
- **D5.** Validity reads "cannot tell" for a figure not recorded.
- **D6.** Quote accuracy uses the latest quote recorded before the
  invoice; "no quote recorded" otherwise (the operator's addition 1).
- **D7.** `shop labor-rate` is added because the fixed estimate needs a
  rate a user can set (K8). The lookup's order (the shop's state, then
  `rate_type = 'national'`, then the newest row) is left as the invoice
  uses it.
- **D8.** Labour cost comes from time entries, not `actual_hours`: the
  entries say who worked and when, which the rate needs.
- **D9.** No refute pass: the phase ships code and schema, no content rows.
- **D10.** The live deploy changes no existing row; if the dry run shows
  otherwise, that is a rule-1 stop.

## Non-goals

- Sending a PO or a claim anywhere; any outbound call.
- An API route for any of this; the mobile app.
- Linking inventory items to a work order's parts (two catalogues).
- Allocating expenses below the shop.
- Changing the labour-rate lookup's order.
- F158's remaining help-text references outside the groups this batch
  edits.

## Planned items

1. This v1.0, committed and pushed before code.
2. Migration 076 and its test (`tests/test_phase274_migration.py`): every
   table and column, the rollback, a planted existing row unchanged; the
   head pinned only as `>= 76` and `== max(MIGRATIONS)`. `wholetree.sh
   --full` before its commit.
3. Row 274 and the bug fix, `tests/test_phase274_crm.py`.
4. Row 279, `tests/test_phase274_inventory.py`.
5. Row 280, `tests/test_phase274_warranty.py`.
6. F182, the quote record, `shop labor-rate`, row 291,
   `tests/test_phase274_quotes_variance.py`.
7. Row 290, `tests/test_phase274_pnl.py`.
8. The allowlist and its pins; the docstring.
9. Mutations, `274_mutate.py`, each seen red.
10. 244G's scanner over the new tests; `wholetree.sh --full`; the
    regression of record by `regression.sh`; `COLLECTED_TEST_FLOOR` raised.
11. The deploy: scope, dry run and its committed diff, `apply-live`.
12. Close-out: v1.1; rows 279, 280, 290, 291 ✅ folded into 274; row 274 ✅
    with its CLOSED date; F182 closed; the history row; the handoff;
    `verify_phase.sh`.

## Verification Checklist

- [x] v1.0 committed and pushed before code (`fa750c8`)
- [x] Migration 076: tables, column, rollback; no existing row changed (`test_phase274_migration.py`; the dry run)
- [x] Every new capability reached through a `motodiag` command in a test
- [x] `customer bikes` / `show` print the relationship (bug fix #1, `3f9afdd`)
- [x] PO generation skips with its reason; `receive` adds stock
- [x] Validity never reads an unrecorded limit as a pass
- [x] The estimate is hours × the invoice's rate + parts; refused without a rate; each queued estimate recorded
- [x] Quote accuracy reads "no quote recorded" when none is
- [x] The P&L states its three attribution rules; nothing unrecorded shown as zero
- [x] The mechanic cost rate appears in no API route (`test_no_api_code_reads_the_cost_rates`)
- [x] Mutations all red (33/33)
- [x] 244G scanner; `wholetree.sh --full`; regression of record; floor raised (10018 → 10109)
- [x] Dry-run diff committed (`e358111`); apply-live equals it
- [x] F182 closed; handoff; `verify_phase.sh` (its result is in the handoff)

## Deviations from Plan

- **`shop labor-rate` was added at v1.0, not at Step 0.** Planning the
  F182 fix found that no command writes `labor_rates`, so a fixed estimate
  would always refuse. The verb gap was found and closed before any code
  (D7).
- **`transfer_ownership` was fixed on the way.** It had no caller until
  this batch wired it. A bike sold back to a previous owner and then sold
  on made its UPDATE collide with the primary key. It is not in the
  bug-fix register, since the defect was never reachable before.
- **244W's real-tree control moved to a synthetic tree.** Wiring
  `inventory/item_repo` ended the real case of the island scan's one seed.
  The same shape is now built in a scratch tree, and mutation G1 removes
  the seed and sees it go red.
- **The API's notification route changed behaviour, not schema.** It calls
  the same function, so an `estimate_ready` there is now refused (422)
  without a rate or estimated hours, and records its quote. Gate 11 is
  unaffected.
- **The P&L's API scan made its test a whole-tree member:** `--full` ran
  84 files, where 361's ran 83.
- **Three slips, each caught before anything shipped:**
  - v1.0's first commit command chained `git push` after `git commit`,
    and the push guard refused it before either ran;
  - one P&L expectation was wrong (the test, not the code);
  - three test counts in the log were wrong, and `b0613fa`'s message says
    "22 new" where it added 20. All three are corrected in the log.
- **The regression of record was run again on the close-out commit**,
  because the close-out changed a test. Its first run lost one test to a
  pytest-xdist worker crash that did not reproduce (F183); the second run
  passed.
- **The deploy ran before the merge**, on the phase branch, as 357's,
  360's and 361's did.
- `inventory/__init__.py`'s stale Track O numbers were corrected. The
  triage report named only `accounting/` and `scheduling/`, and this batch
  edits neither, so their docstrings are left for batch 2.

## Results

| | |
|---|---|
| Migration | 076: eight tables, six indexes, `inventory_items.reorder_quantity`; schema 75 → 76; no row changed |
| 274 CRM | `shop customer log-contact`, `history`, `transfer-bike`, `bike-owners`; `test_phase274_crm.py` 10 |
| Bug fix #1 | `shop customer bikes`/`show` print the relationship; `test_phase274_relationship_column.py` 2 |
| 279 inventory | `shop inventory` (vendors, stock, `reorder`, `po generate/list/show/mark-sent/receive/cancel`); `test_phase274_inventory.py` 16 |
| 280 warranty | `shop warranty add/list/check`, `claim open/list/show/status/packet`; `test_phase274_warranty.py` 19 |
| F182 and quotes | the estimate at the invoice's rate plus parts, refused without either; `work_order_quotes`; `shop labor-rate`; `test_phase274_quotes_variance.py` 17 (with 291) |
| 291 variance | `shop analytics variance` |
| 290 P&L | `shop member cost-rate(s)`, `shop parts-needs cost`, `shop expense`, `shop analytics pnl`; `test_phase274_pnl.py` 21 |
| Migration tests | `test_phase274_migration.py` 10 |
| Allowlist | MODULE_ISLANDS 13 → 9, UNREACHABLE 34 → 32, ORPHANS 106 → 112; 244X's list 52 → 51 |
| Mutations | 33/33 red (`274_mutate.py`) |
| Whole tree | `--full` at `757b9f4`: 84 files, 3961 passed |
| Regression | 10109 passed, 0 failed, 0 skipped at `757b9f4` (27 min 22 s) and at `3b7528f`, the close-out commit (30 min 4 s), `-n auto --dist load`; the first run at `3b7528f` lost one test to a worker crash (F183) |
| Floor | `COLLECTED_TEST_FLOOR` 10018 → 10109 |
| Deploy | dry run committed `e358111`; apply-live `[76]`; live 5845 → 5846 rows, 90 → 98 tables, integrity ok; equals the approved exact diff; F158 census 36 |
| Findings | F182 filed and closed; F183 filed (a worker crash, not reproduced) |
| Ledger | 274 ✅; 279, 280, 290, 291 ✅ folded; 282–286 ⏸️; 280 rewritten; 362 ⏸️ |
