# Phase 275 — Track O batch 2: staff booking, iCal, QuickBooks and Xero export files — phase log

**Status:** ✅ Complete (2026-09-30)
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

### 2026-09-29 — The operator's pick, and v1.0

The operator's answer, verbatim:

> 1A, 2C, 3A, and the default for 4. For 3A, the export command says plainly when it writes the file that these are journal entries: they carry no line items and don't reach QuickBooks' sales-tax reports. The log records that neither file was tried in a real QuickBooks or Xero company.

**Recorded, as asked: neither export file was tried in a real
QuickBooks or Xero company.** Each is built to the vendor's page as read
on 2026-09-29 (`275_format_sources.md`) and tested against that page's
rules, not against the product.

**A correction to Step 0.** Question 4 listed the columns "the page
names" and included `Reference`, `Description` and `Quantity`. Counting
each name in the page's extracted text: those three appear 0 times; the
other names at least once. `POAddress` appears only as a group name, with
no field names. So the header is:
- the names the page gives: `ContactName`, `EmailAddress`,
  `InvoiceNumber`, `InvoiceDate`, `DueDate`, `InventoryItemCode`,
  `UnitAmount`, `Discount`, `AccountCode`, `TaxType`, `TaxAmount`,
  `TrackingName`, `TrackingOption`, `Currency`, `BrandingTheme`;
- plus `Description` and `Quantity`, which the page does not name. A line
  cannot be described without them. They are flagged in the test and the
  source file as not from the page;
- no `Reference` and no address fields.

This departs from the default as worded ("exactly these names"), because
the list it was worded on was wrong. It is reported to the operator at
the end.

v1.0 is `275_implementation.md`.

### 2026-09-30 — Migration 077 and the four rows (`4bbf262`)

- **Migration 077** (schema 76 → 77): `appointments.shop_id` and
  `work_order_id`, `idx_appointments_shop_start`, `accounting_accounts`,
  `accounting_exports`, `accounting_export_invoices`.
  `test_phase275_migration.py`, 9: the columns, index and tables, the
  rollback, planted rows in eight tables and one appointment unchanged
  either way, the CHECKs. SQLite 3.53.2 drops a column declared with
  `REFERENCES` (tried on a scratch table first), so the rollback uses
  `DROP COLUMN` as 076's does. The 81 test files that touch the schema
  version or the migrations: 2708 passed.
- **Row 275:** `scheduling/booking.py`; `shop appointment book, list,
  show, slots, reschedule, confirm, check-in, cancel, no-show, complete`
  (`cli/shop_booking.py`). `test_phase275_booking.py`, 26.
- **Row 276:** `scheduling/calendar.py`; `shop calendar show, export`.
  `test_phase275_calendar.py`, 13. No iCal library is installed and none
  was added: the test unfolds and splits the file itself.
- **Rows 277 and 278:** `accounting/export.py`; `shop accounting map
  set/list, export, exports` (`cli/shop_accounting.py`).
  `test_phase275_accounting_export.py`, 19. The column tests read the
  lists from `275_format_sources.md`. One expected figure in the test was
  wrong on first writing (the receivable total, 406.54): the test, not
  the code.
- **Decisions made while building:**
  - a confirmed appointment can be confirmed again: it logs the contact
    again, and the status stays `confirmed` (a resent confirmation is an
    ordinary thing to record);
  - the refusal for missing hours names the command that records them,
    `shop profile update --set hours_json=…` (checked: `profile update`
    takes `--set KEY=VALUE`);
  - `shop accounting exports` lists the recorded exports, so the record
    has a reader;
  - both file writers refuse to overwrite an existing file.
- The docstrings of `scheduling/__init__.py` and `accounting/__init__.py`
  lose their stale Track O numbers.
- **F158 scan:** the five new source files hold no "Phase", "Track X" or
  F-number; the same pattern finds 21 in `cli/shop.py` (the control).
- **The allowlist:** `motodiag.scheduling` and its two modules left
  UNREACHABLE_MODULES (32 → 29); six `appointment_repo` CRUD helpers
  became live orphans and are listed (112 → 118). The five
  integration-gap files: 304 passed.
- 244G's scanner over `tests/`: 0 findings.
- `wholetree.sh --full` on the staged tree: 3982 passed, record written.

### 2026-09-30 — Mutations, and the floor

- **Mutations: 28/28 red** (`275_mutate.py`: migration 2, booking 10,
  calendar 6, the export files 10). `git status` afterwards shows only
  the new script.
- **`COLLECTED_TEST_FLOOR` 10109 → 10179**, by diffing collected IDs
  (`--collect-only -q -o addopts=`) against a `master` worktree: +70 = the
  four `test_phase275_*` files (67) + gate 15's
  `test_rolling_back_peels_every_successor[76]` + 209B's +2 net (28 added,
  26 removed). The worktree's run imports this checkout's `src` through
  the editable install, so gate 15's `[76]` appears in both lists; its
  cause is `range(…, SCHEMA_VERSION)` reaching 76 once 077 exists. The
  worktree was removed after.

### 2026-09-30 — The regression of record

`wholetree.sh --full` on the clean tree at `5dc9251`: 3982 passed,
record written.

Regression of record: 10179 passed, 0 failed, 0 skipped, 0 errors at `5dc9251` (30 min 38 s wall, `python -m pytest -n auto --dist load`, exit 0)

The count equals the new floor. No worker was lost.

### 2026-09-30 — The deploy: the dry run

- **Scope** (`275_deploy_scope.json`): `schema_version` +1; two indexes
  and three tables added; `table appointments` changed; nothing else.
- **`deploy.py dryrun 275`:**
  - live 5846 rows, 98 tables, integrity ok;
  - backup `~/backups/motodiag/motodiag_pre275_20260930_013316.db`
    (retain-5 removed `motodiag_pre359_20260927_172347.db`);
  - applied `[77]` on the copy; scope problems: none; F158 census 36.
- **The diff (`275_dryrun_diff.md`):**
  - one `schema_version` row added (77);
  - five schema objects added, as the scope names them;
  - `table appointments` changed: its SQL gains `shop_id` and
    `work_order_id`. Live holds 0 appointments (Step 0), so no row
    carries the columns;
  - **no existing row changed or removed** in any table.
- **Not a rule-1 stop.** No existing row changes, the condition the
  prompt set. The diff is committed before apply-live.

### 2026-09-30 — The deploy: apply-live

Run on the phase branch before the merge, as 274's was. The migration
applied is the one in `5dc9251`, the commit the regression tested
(`aeda0c0` adds only documents).

`deploy.py apply-live 275`:
- the preflight passed (F172's exact check); applied `[77]`;
- live after: 5847 rows, 101 tables, integrity ok;
- scope problems none; **equals the approved exact diff: yes**
  (`275_live_diff.md`).

By hand, read only, after:
- schema 77; `appointments` ends in `shop_id`, `work_order_id`;
- appointments 0, customers 6, work orders 6, notifications 4, vehicles
  10, shops 1, invoices 0, contacts 0: every count as Step 0 measured
  it; the three new tables are empty;
- `foreign_key_check` is empty;
- against live, `shop calendar show --shop 1` prints "Nothing booked",
  `shop accounting map list --shop 1` "No accounts mapped yet." and
  `shop appointment list --shop 1` "No appointments match."

### 2026-09-30 — Close-out

- **No refute pass ran:** the batch ships code, a migration and tests,
  and no content rows. The two export formats rest on vendor pages; they
  are quoted in `275_format_sources.md` and pinned by tests, not refuted.
- No bug-fix register: no defect was found in code that existed before
  the batch, and none in the batch's own code after it was committed.
- **No finding filed.** Nothing found was left unfixed; every gap is on
  a paused row.
- Rows 276, 277 and 278 ✅ folded into 275, with no CLOSED date of their
  own; row 275 ✅ with its CLOSED date and the regression line (91
  words). Rows 363–366 stay ⏸️.
- The fold pin in `test_roadmap_continuity.py` names fifteen folds (12 +
  276, 277, 278) and is renamed `test_the_fifteen_folds_are_seen_and_pass`.
  The code did not change after the regression; the regression is run
  again on the close-out commit because a test changed.
- `implementation.md` 0.13.95 with its history row; v1.1; handoff
  `docs/handoffs/2026-09-30_275_closed.md`.
- The documents move to `completed/`: this log, v1.1, the Step 0, the
  sources, the mutation script, the scope and both diffs.
- **The edit guard blocked one command** during close-out: a Python edit
  of `275_implementation.md` chained with `sed -i` on this log. The hook
  stops the whole command before it runs, so neither edit happened (the
  checklist still had its 14 open boxes). Both were redone, the log's
  status line with the Edit tool. The guard was right, and was not
  loosened.
