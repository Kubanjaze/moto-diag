# Phase 274 — Track O batch 1: CRM, reorder points, warranty, financial reporting, variance — phase log

**Status:** 🚧 In progress
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
  from the end of `register_shop`). `test_phase274_crm.py`, 12.
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
