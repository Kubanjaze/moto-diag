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
