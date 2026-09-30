# Phase 274 — Track O batch 1: CRM, reorder points, warranty, financial reporting, variance — phase log

**Status:** ✅ Complete (2026-09-29)
**Branch:** `phase-274` (Opus session, main checkout, the only writer)

---

### 2026-09-29 — Opened: Track O batch 1

The prompt is `docs/prompts/274_track_o_batch1.txt` (merged in
`1baba00`). The operator's decision of 2026-09-28, verbatim:

> 1, 2, 3, 5 as recommended.

For this batch that means the order batch 1 → 2 → 3 → 4 → Gate 16; batch
1 is rows 274, 279, 280, 290 and 291, the local shop data with no outside
dependency; the supplier rows 282–286 and the OEM parts of 280 and 281
are paused, each with its reason; the backend stays tailnet-only.

Read first: the 361 handoff (`docs/handoffs/2026-09-29_361_closed.md`),
the triage report (`docs/reports/2026-09-28_track_o_triage.md`), rows
274, 279, 280, 290 and 291, and row 261 with its handoff
(`docs/handoffs/2026-09-25_261_closed.md`) for how a batch closes: the
carrying row closes with its CLOSED date and the regression line, the
others close ✅ "folded into" it with no date of their own, one history
row, one handoff.

The first commit:
- **Row 274 🚧**, carrying the batch.
- **Rows 282–286 ⏸️**, each with the reason decision 2 gives: it needs a
  dealer or B2B account with the supplier, and no public API is known.
- `roadmap_check.py`: ok.

### 2026-09-29 — Step 0, and the stop on row 290

`274_step0.md`. What it found:
- **274:** `customer_notifications` is the outbound template queue (ten
  system events, three channels, no inbound, no free text), not a
  communication log. The log adds free-text contacts in either direction
  on any channel, and one timeline per customer. `transfer_ownership`
  and a bike's owner list have no command. `shop customer bikes` and
  `show` print `?` for every relationship: a defect on this row's
  surface, to be fixed as a bug fix.
- **279:** no order quantity is stored; `reorder_quantity` is added. POs
  are local drafts per vendor; `sent` is set by the user; `receive` adds
  stock.
- **280:** validity by date and mileage over `warranties`; a claims table;
  a plain-text claim packet.
- **291:** computable from the work order's own estimate. On the way,
  **F182** was filed with the `finding` skill: the estimate a customer is
  sent is the hours times a hard-coded $100, parts left out (measured:
  2.0 h and $549.91 of parts renders $200.00).
- **290:** revenue is stored; parts purchase cost, a mechanic's labour
  cost, overheads and bay costs are not. A part's stored cost is the price
  the invoice bills, so a parts margin is 0 by construction.

The ledger, in this commit:
- **Row 280 rewritten** to what this batch builds: validity lookup, local
  claim records, printable packet.
- **Row 362 ⏸️**, "OEM warranty claim submission", split from 280: it
  needs each maker's dealer portal. 362 was free: no ROADMAP row, phase
  document or handoff named it.
- The ROADMAP header reads 362 numbered.
- `roadmap_check.py` ok; row 280 is 61 words, row 362 56.

**Stopped for the operator (rule 1: a real fork).** A P&L per mechanic,
per bay and per customer cannot be computed from stored data, the
condition the prompt set. The options, with what each ships, are in
`274_step0.md` ("Questions for the operator"): (A) revenue reporting and
the P&L paused, (B) record direct costs for a gross-margin P&L with
expenses at shop level, recommended, (C) B with expenses allocated by
labour hours. A second question asks whether F182's fix stays in this
batch.

### 2026-09-29 — The operator's pick, and v1.0

The operator's answer arrived as pasted text in their message. Verbatim:

> B. And F182's fix stays in this batch; the estimate takes its rate from the same labor_rates lookup the invoice uses, so the quote and the invoice agree.
>
> Two additions:
> 1. Record each quote when estimate_ready is queued: hours, rate, parts, total and date. Quote accuracy compares the invoice with that record; a work order with no recorded quote shows "no quote recorded", never a recomputed figure.
> 2. One attribution rule per dimension, stated in the report: a work order's revenue and all its costs count for its assigned mechanic (a work order with none counts as unassigned); across bays, a work order is split by the slot hours it spent in each; per customer, by the invoice's customer.
>
> Note in v1.0 that a mechanic's cost rate is pay data: nothing in this batch shows it outside the CLI, and any later API route for it is owner-only.

One more verb gap was found while planning: no command writes
`labor_rates` (only `_lookup_labor_rate_cents` reads it), and the table
is empty live. The fixed estimate refuses without a rate, so v1.0 adds
`shop labor-rate set/list`, reusing `pricing/labor_rates.py` (D7).

v1.0 is `274_implementation.md`.

### 2026-09-29 — Migration 076 and row 274 (`b0613fa`)

- **Migration 076** (schema 75 → 76): eight tables and
  `inventory_items.reorder_quantity`. `test_phase274_migration.py`, 10:
  every table and the column, the rollback, and a planted row in each
  touched table reading back the same after upgrade and rollback. The 79
  test files that touch the schema version: 2673 passed.
- **Row 274:** `crm/communication_repo.py`; `shop customer log-contact`,
  `history`, `transfer-bike`, `bike-owners` (`cli/shop_crm.py`, attached
  from the end of `register_shop`). `test_phase274_crm.py`, 10 (12 before
  the relationship tests moved to their own file; `b0613fa`'s message
  says "22 new", where it added 20).
- **`transfer_ownership` fixed on the way:** a bike sold back to a
  previous owner and on again made the UPDATE collide with the
  `(customer, bike, previous_owner)` key. The test fails without the fix.
  It is not a register bug fix: the function had no caller until this
  batch wired it.
- The allowlist: `transfer_ownership` left ORPHANS (106 → 105); 244X's
  list of multi-line re-export orphans 52 → 51.
- The `customer` group's help lost "wraps Phase 113 CRM layer".
- `wholetree.sh --full` before the commit: 3943 passed.

### 2026-09-29 — The relationship column (`3f9afdd`)

See the register below: `test_phase274_relationship_column.py`, 2, both
red before the fix. `wholetree.sh`: 1478 passed; the fast count fell by 2
because two whole-tree tests are parametrised over ORPHANS, which lost an
entry. `wholetree.sh --full` on the clean tree at `3f9afdd`: 3943
passed, record written; pushed `fa750c8..3f9afdd`.

### 2026-09-29 — Rows 279 and 280

- **279:** `inventory/purchase_orders.py` (the reorder plan, one draft PO
  per vendor, status moves, the printable PO) and `shop inventory`
  (`vendor add/list`, `add`, `list [--low]`, `show`, `adjust`, `set`,
  `reorder`, `po generate/list/show/mark-sent/receive/cancel`).
  `InventoryItem` and `add_item` carry `reorder_quantity`.
  `test_phase274_inventory.py`, 16.
- **280:** `warranty_repo.coverage_status` (valid, not valid, or cannot
  tell, with reasons), `inventory/warranty_claims.py` (claims, status
  moves, the packet) and `shop warranty` (`add`, `list`, `check`, `claim
  open/list/show/status/packet`). `test_phase274_warranty.py`, 19.
- `inventory/__init__.py`'s stale "Track O phases 282-287" corrected.
- **The allowlist:** inventory's `models`, `item_repo`, `vendor_repo` and
  `warranty_repo` left MODULE_ISLANDS (13 → 9). Five repo helpers and the
  `Recall` model became live orphans and are listed (105 → 111).
- **244W's control moved.** `test_item_repo_is_seen_past_the_dead_collision`
  used `inventory/item_repo` as the real-tree case of the one seed (a dead
  module's same-named `add_item` hiding a second dead module). Wiring
  item_repo ended that case, so the control is now a synthetic tree of
  the same shape (`test_a_module_is_seen_past_a_dead_modules_name_collision`);
  the mutation script removes the seed and checks it goes red.

### 2026-09-29 — F182, the quote record, rows 291 and 290

- **F182 fixed** (`shop/notifications.py`): the `estimate_ready` total is
  the estimated hours at `_lookup_labor_rate_cents`'s rate plus the
  estimated parts; refused with the reason when there is no work order, no
  estimated hours or no rate; the extra context may not replace
  `estimate_total` or `estimate_labor_hours`. The old branch that showed
  an existing invoice's total as the estimate is gone. F182 is closed in
  `docs/FOLLOWUPS.md`.
- **The quote record:** `trigger_notification` writes a `work_order_quotes`
  row for each queued `estimate_ready`, in the same transaction as the
  notification. A preview records nothing. A resend copies the rendered
  message and records no second quote: the quote already recorded is the
  one it repeats.
- **`shop labor-rate set/list`** (`cli/shop_finance.py`, over
  `pricing/labor_rates.py`), D7.
- **Row 291:** `analytics.estimate_variance` and `shop analytics
  variance`. Timestamps: the quote's `quoted_at` carries a `T`, the
  invoice's `issued_at` a space, so the comparison normalises both (a
  quote from earlier the same day would otherwise sort after the invoice).
- **Row 290:** `shop/shop_costs.py`; `shop member cost-rate` and
  `cost-rates`, `shop parts-needs cost`, `shop expense add/list`;
  `analytics.financial_report` and `shop analytics pnl`. The report
  carries its attribution rule and the three cost rules in its own output.
  The analytics group's help lost "Track G".
- **An API behaviour change, not a schema change.** The API's
  `POST /v1/shops/{id}/notifications/trigger` calls the same function, so
  an `estimate_ready` there is now refused (422, `notification-context`)
  without a labour rate or estimated hours, and records its quote when
  queued. No request or response model changed; gate 11 is unaffected.
- **The allowlist:** `motodiag.pricing` and `pricing.labor_rates` left
  UNREACHABLE_MODULES (34 → 32); `load_labor_rates_file` became a live
  orphan and is listed (111 → 112).
- Tests: `test_phase274_quotes_variance.py` 17,
  `test_phase274_pnl.py` 21 (counted by `--collect-only`). One P&L expectation was wrong on first run,
  not the code: WO1's quarter share in Lift B is 6250 − 750 − 2000 =
  3500, where the test had 2150.
- The 33 related existing test files (notifications, analytics,
  invoicing, members, parts-needs): 904 passed.
- **Mutations: 33/33 red** (`274_mutate.py`: migration 2, CRM 5,
  inventory 4, warranty 6, F182 and the quote 4, variance 3, P&L 8, the
  244W seed 1).
- 244G's scanner over `tests/`: clean.

### 2026-09-29 — The floor

`COLLECTED_TEST_FLOOR` 10018 → 10109, measured by diffing the collected
IDs against a `master` worktree (`--collect-only -q -o addopts=`; the
project's `addopts` carries `-v`, which cancels `-q`, and a first count
without the override listed 162 lines of tree instead of IDs). 214 IDs
added and 123 removed; most of the removed are the allowlist checks'
parametrised IDs, renumbered when entries left the lists. Net +91: the
seven `test_phase274_*` files (95), gate 15's peel for 076 (+1), 209B +4,
244W −8, 244X −1.

### 2026-09-29 — The regression of record

`wholetree.sh --full` on the clean tree at `757b9f4`: 84 files, 3961
passed, record written. (84, one more than 361's 83: the P&L test's scan
of `src/motodiag/api` made it a whole-tree member.)

Regression of record: 10109 passed, 0 failed, 0 skipped, 0 errors at `757b9f4` (27 min 22 s wall, `python -m pytest -n auto --dist load`, exit 0)

### 2026-09-29 — The deploy: the dry run

- **Scope** (`274_deploy_scope.json`): `schema_version` +1; the six
  indexes and eight tables added; `table inventory_items` changed;
  nothing else.
- **`deploy.py dryrun 274`:**
  - live 5845 rows, 90 tables, integrity ok;
  - backup `~/backups/motodiag/motodiag_pre274_20260929_210135.db`
    (retain-5 removed `motodiag_pre262_20260926_163221.db`);
  - applied `[76]` on the copy; scope problems: none; F158 census 36.
- **The diff (`274_dryrun_diff.md`):**
  - one `schema_version` row added (76);
  - 14 schema objects added, as the scope names them;
  - `table inventory_items` changed: its SQL gains `reorder_quantity`.
    Live holds 0 inventory items (Step 0), so no row carries the column;
  - **no existing row changed or removed** in any table.
- **Not a rule-1 stop.** No existing row changes. The table that gains a
  column has no rows, so the prompt's "a new column on a table that has
  rows" does not apply. The diff is committed before apply-live.

### 2026-09-29 — The deploy: apply-live

Run on the phase branch before the merge, as 357's, 360's and 361's were.
The migration applied is the one in `757b9f4`, the commit the regression
tested (`e358111` adds only documents).

`deploy.py apply-live 274`:
- the preflight passed (F172's exact check); applied `[76]`;
- live after: 5846 rows, 98 tables, integrity ok;
- scope problems none; **equals the approved exact diff: yes**
  (`274_live_diff.md`).

By hand, read only, after:
- schema 76; `inventory_items` ends in `reorder_quantity`;
- customers 6, work orders 6, notifications 4, vehicles 10, shops 1, and
  0 inventory items, vendors and warranties: every count as Step 0
  measured it; the new tables are empty;
- `foreign_key_check` is empty;
- against live, `shop inventory reorder` prints "Nothing is at or below
  its reorder point." and `shop analytics pnl` prints "No invoices issued
  in this period" and "Net not computed: no expenses recorded for
  2026-09".
- One of those checks was first run with `MOTODIAG_DB_PATH=` set to an
  empty string, a slip in the command. It crashed in `init_db` ("no such
  table: vehicles") and wrote no file (`git status` and the directory
  listing show none). It was re-run without the variable.

## Bug-fix register

### Bug fix #1 — 2026-09-29

**Issue.** `motodiag shop customer bikes` and `shop customer show`
printed `?` in the Relationship column for every linked bike. Found at
Step 0 (S0-2) and reproduced on a scratch database.

**Root cause.** `list_bikes_for_customer` returns the link's relationship
as `cb_relationship` (the vehicle row has its own columns), and both
tables read `relationship`.

**Fix.** Both tables read `cb_relationship`.

**Files.** `src/motodiag/cli/shop.py`,
`tests/test_phase274_relationship_column.py`.

**Verified.** The test's 2 cases fail with the fix removed and pass with
it; mutation C5 red.

**Commit.** `3f9afdd`

### 2026-09-29 — Close-out

- No refute pass ran: the batch ships code, a migration and tests, and no
  content rows. No claim rests on a document.
- F182 closed in `docs/FOLLOWUPS.md` (in `b474378`, with its fix).
- Rows 279, 280, 290 and 291 ✅ folded into 274, with no CLOSED date of
  their own; row 274 ✅ with its CLOSED date and the regression line
  (92 words). Rows 282–286 and 362 stay ⏸️.
- `implementation.md` 0.13.94 with its history row; v1.1; handoff
  `docs/handoffs/2026-09-29_274_closed.md`.
- The documents move to `completed/`: this log, v1.1, the Step 0, the
  mutation script, the scope and both diffs.
- `wholetree.sh` before the close-out commit failed once, 1 of 1496:
  `test_roadmap_continuity.py` pins the real ledger's folds, and this
  close-out added four (279, 280, 290 and 291 into 274). The test now
  names twelve, and is renamed `test_the_twelve_folds_are_seen_and_pass`.
  The code did not change after the regression; this is a test
  of the ledger, run again below.

### 2026-09-29 — The regression, re-run on the close-out commit

The close-out changed a test (`test_roadmap_continuity.py`'s fold pin),
so the regression of record was run again on `3b7528f`, the commit the
merge carries, after `wholetree.sh --full` there (84 files, 3961 passed,
record written).
- **First run:** 10108 passed, 1 failed at `3b7528f` (28 min 18 s). The
  failure was not an assertion. The pytest-xdist worker `gw2` died
  ("node down: Not properly terminated") while running
  `test_phase359_content_cleanup.py::TestTheMigration::test_the_round_trip_restores_the_workflow_tables`.
  There was no traceback and no crash report.
- **The test alone:** its file 18 passed. With `test_phase274_migration.py`
  and gate 15 under `-n auto --dist load`, five times: 64 passed each.
- **Filed as F183** with the `finding` skill. Rule 3 says a
  parallel-only failure is a bug to fix; this one could not be made to
  fail again, and it is recorded rather than dismissed.
- **Second run, same commit:**

Regression of record: 10109 passed, 0 failed, 0 skipped, 0 errors at `3b7528f` (30 min 4 s wall, `python -m pytest -n auto --dist load`, exit 0)

This is the regression of record for the close-out. The run at
`757b9f4` (10109 passed) stands for the code, which did not change
between the two.
