# Phase 275 — Track O batch 2: staff booking, iCal, QuickBooks and Xero export files — phase log

**Status:** 🚧 In progress
**Branch:** `phase-275` (Opus session, main checkout, the only writer)

---

### 2026-09-29 — Opened: Track O batch 2

The prompt is `docs/prompts/275_track_o_batch2.txt` (merged in
`7d9676f`). The operator's decision of 2026-09-28, verbatim:

> 1, 2, 3, 5 as recommended.

For this batch that means: batch 2 is rows 275 (booking by shop staff),
276 (iCal), 277 (a QuickBooks export file) and 278 (a Xero export file);
customer self-booking and Google Calendar two-way sync are paused, each
with its reason; the backend stays tailnet-only.

Read first: the 274 handoff (`docs/handoffs/2026-09-29_274_closed.md`),
the triage report (`docs/reports/2026-09-28_track_o_triage.md`), rows
275–278, and 274's documents in `docs/phases/completed/`.

The first commit: **row 275 🚧**, carrying the batch.

### 2026-09-29 — Step 0, and the stop

`275_step0.md`; the vendors' pages, quoted with their URLs and dates, in
`275_format_sources.md`. What it found:
- **Every measured fact in the prompt holds** (S0-1). Two more: the
  appointments table has no shop and no work order, and no record of a
  customer paying an invoice exists beyond `status = 'paid'`.
- **The two calendars (decided, S0-3):** an appointment and a bay slot
  are different facts, linked through the work order an appointment's
  check-in opens; one calendar is read live from both tables, so nothing
  is copied and nothing can drift.
- **QuickBooks (found here):** Intuit's own page says QuickBooks Online's
  invoice import refuses any company with sales tax set up. The fork
  below is sharper than Online against Desktop.
- **Xero's template header** is behind a Xero login; the page names the
  columns, and the default uses those names.
- The Xero page renders only in a browser: it was read with headless
  Chrome's `--dump-dom`. The first attempt left Chrome running after the
  dump, and it was stopped by hand.

The ledger, in this commit:
- **Rows 363–366 ⏸️**, split from 275 (customer self-booking), 276
  (Google two-way sync), 277 (QuickBooks API sync and payment
  reconciliation) and 278 (Xero API sync), each with its reason. The
  numbers were free: no row in either ROADMAP, no phase document and no
  handoff names them; the same search finds row 362 and 274's seven
  documents.
- The header reads 366 numbered.
- Rows 275–278 are rewritten after the operator's answers, since the
  answers decide what 276 and 277 build.

**Stopped for the operator (rule 1: real forks).** Three, with what each
ships, are in `275_step0.md` ("Questions for the operator"): (1) iCal as
a file or a feed; (2) confirmations through a new outbox event with the
API, the same under a lint opt-out, or sent by the shop and recorded in
the contact log; (3) the QuickBooks file: Online's journal-entry import,
Online's invoice import, or Desktop's IIF. A fourth item is a note with a
default: Xero's header row.
