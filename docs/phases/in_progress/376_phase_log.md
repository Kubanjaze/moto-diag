# Phase 376 — Warranty claim settlements in the accounting export (F190) — phase log

**Status:** 🚧 In progress
**Branch:** `phase-376` (Opus session, main checkout)

---

### 2026-10-07 — Opened

The operator's prompt is `docs/prompts/376_claim_settlements_in_the_export.txt`
(merged `23ff246`). The last session's state is
`docs/handoffs/2026-10-07_377_closed.md`. Row 376 went 🚧 before Step 0
(`0897f14`):
- 376 was written by 373 (split from it, 2026-10-06);
- `roadmap_check.py` passed;
- `wholetree.sh` fast exited 0 (1555 passed, 36.9 s);
- pushed.

### 2026-10-07 — Step 0, and the stop

The record is `376_step0.md`; the sources are `376_sources.md`. Every
measured fact in the prompt re-verifies, on code and on a copy of live
(`live_376_step0.db`, SQLite's backup API from a read-only connection).

**The invoice-number finding is F194**, filed with the finding skill
before this entry cites it; `finding_check.py` exit 0. The frozen-zone
check it cites, run with `TZ=America/New_York`:

```
number's day 20261101 shop's day 2026-10-31
```

for `datetime(2026, 11, 1, 1, 0, tzinfo=timezone.utc)`, 2026-10-31
21:00 EDT: `now.strftime('%Y%m%d')`, as `_format_invoice_number` writes
it, against `core/timestamps.local_day`.

**How the sources were read.** Headless Chrome, as 373. Intuit's two pages
came back empty twice and curl failed, so they were read through WebFetch,
and the sources file says so. Three pages are blocked and recorded as
such: G.L. c. 64H § 33 (no connection by any route), 830 CMR 64H.1.4 (403
to Chrome twice and to WebFetch), and Form ST-BDR (not opened). No format
or rule is taken past a blocked page.

**Two tool events, recorded:**
- The edit guard blocked `sed -i` on a script in the session scratchpad
  ("blocked wherever it points"). The Edit tool was used instead; the
  guard was not touched.
- My first edit to that script put the alarm's seconds inside perl's
  single-quoted program, so no alarm was set and one Chrome hung for about
  seven minutes. I stopped the Chrome processes I had started (their
  `--user-data-dir` was in the scratchpad) and passed the seconds as an
  argument.

The questions put to the operator, with options and recommendations, are
S0-4 in `376_step0.md`: Q1 what each settlement books (1A), Q2 the tax on
an absorbed shortfall (2A), Q3 where it is booked (3A), Q4 F194 (4A), and
Q5, a fork the sources raised, the tax on a Xero credit note (5A). The
operator's answers will be recorded here verbatim.

**The operator's answer, verbatim:** "1A, 2A (and file the use-tax
finding), 3A, 4A, 5A. Four additions:
- The expected-tax line covers every credit note, absorbed ones too (0 tax
  under 2A), so a taxable rate mapped to the absorbed account shows before
  the shop approves the draft.
- When the export books an absorbed claim that carried no tax, the CLI
  says tax on the parts' cost may be due and names the use-tax finding.
- 083's dry run changes no existing row, and no schema object beyond the
  two rebuilt tables and the new ones: every index, and the foreign keys in
  accounting_export_invoices and accounting_export_claims, come through
  unchanged. If anything else changes, stop and show me.
- The export's record keeps each file's name and hash, since a Xero export
  can now write two.
Carry on to v1.0 and the build."

**The use-tax finding is F195**, filed with the finding skill before this
entry cites it; `finding_check.py` exit 0.

**What the third addition sets, read literally:** the phase stops and
shows the operator if 083's dry run changes any existing row, or any
schema object other than `accounting_accounts` and `accounting_exports`
(rebuilt) and the new tables and their indexes. Without such a change,
083 is new tables, two rebuilt tables holding 0 live rows, one new rule
row and its `schema_version` row, which CLAUDE.md rule 1 does not stop
for. No approval is inferred from this beyond that.

**One reading of the second addition, recorded:** the line is printed for
an absorbed claim with no tax that covers parts. A labour-only claim
transfers no parts, so "tax on the parts' cost" does not apply to it, and
printing it there would be wrong information.

### 2026-10-07 — v1.0

`376_implementation.md` v1.0: the choices and additions, what each
settlement books, migration 083, the export and the CLI, F194, the tests
and the checklist.

### 2026-10-07 — The build (`ff6d9c0`)

Migration 083, `tax_settlement_rules` with `shop tax settlement-rule set`,
`confirm` and `status`, the export's settlements in both files, the CLI,
F194, `tests/test_phase376_settlement_export.py` (27) and `376_mutate.py`.
373's `test_a_shortfall_invoice_is_left_out_and_said_so` became
`test_a_shortfall_invoice_is_exported_with_its_settlement` (the intended
inversion: the one failure the related suites showed, 474 passed beside it).

**Decisions taken while building, not stops:**
- **D6. A billed settlement whose shortfall invoice was voided is refused**,
  naming it: booking the customer for a void invoice would be wrong, and
  nothing in 376 decides what a void shortfall invoice means.
- **D7. The checks that cannot fire were removed before the commit.** I
  first wrote a whole-file journal balance check and a credit-note sum
  check. Both hold by construction: each credit is the shortfall
  invoice's lines plus the claim's tax inside the shortfall, defined as
  the shortfall less those lines. So they could never go red (S2, S4).
  The check that can fire stays: the claim's tax inside the shortfall
  must lie between 0 and the claim's tax, which a shortfall line out of
  step with its claim breaks. The test raises one line by 3 cents and
  both files refuse (mutation Q4). Balance is proven by the tests'
  ledgers: every QuickBooks journal nets to 0 and every credit note sums
  to minus its shortfall.
- **D8. `accounting_exports.file_name` and `file_sha256` stay**, as the
  first file written; `accounting_export_files` holds every file
  (addition 4). `invoice_count` now counts billed shortfall invoices too,
  since `accounting_export_invoices` records them.
- **D9. `accounting_export_files.row_count` allows 0.** v1.0 planned
  `> 0`. No case I know of writes a file with no rows: an invoice with
  nothing owed always carries a claim with an amount (373). The CHECK
  records what was written, so it should not refuse a file already on
  disk. Changed before the commit.
- **D10. The F158 ratchet caught my seeded rule's notes** citing "(F195)":
  a build reference in text a shop sees (`shop tax status` prints the
  rule's source). The notes now describe the open point without the
  number. The CLI line still names F195, as the operator asked.
- **D11. The D4 control is a hash taken from the old code:** the no-
  settlement export of 373's job, run in a `git worktree` of master
  `23ff246` (schema 82, no settlement code: printed), gives
  QuickBooks `81c1918f…` (892 bytes) and Xero `432cd338…` (711 bytes); the
  branch gives the same. The test pins both.

**My own mistakes, caught by the tests before any commit (not register
entries):** the Xero "no double count" test summed `UnitAmount` without
`Quantity` (labour is 0.5 h); and the migration test's cascade assertion
used the test helper's raw connection, where foreign keys are off, so it
could never see a cascade. It now deletes through `get_connection`, and
mutation M2 (the rebuild without `PRAGMA foreign_keys=OFF`) goes red on it.

**The edit guard**, a second time: a Python heredoc batching CLI help edits
into `src/` was refused ("a Python script body writes src/…"). Rightly: the
edits went in one at a time with the Edit tool. Not loosened.

**Mutations:** 22/22 red (`376_mutate.py`, output in the session
scratchpad and below in Results).

**244G's scanner** over `tests/`: 0 hits. Its positive control, a planted
`Path("….py").read_text()` assertion in a scratch directory, is reported
(`test_ctl.py:5`); a `.csv` read is not raw source, by the scanner's rule.

**`wholetree.sh --full`** on the staged build: first run 9 failed, all
the F158 ratchet (D10); after the fix, exit 0, 4047 passed.

No refute pass ran.

### 2026-10-07 — Migration 083 live

- **Scope:** `376_deploy_scope.json`.
- **Dry run:** `376_dryrun_diff.md` (`47e922a`), backup
  `~/backups/motodiag/motodiag_pre376_20261007_183425.db`, sha256
  `5539d08e…`. `schema_version` +1, `tax_settlement_rules` +1, no existing
  row changed or removed; `accounting_accounts` and `accounting_exports`
  rewritten (0 live rows each); five objects added, none removed;
  `accounting_export_invoices`, `accounting_export_claims` and
  `idx_accounting_export_invoices_invoice` not in the diff. Scope problems:
  none. F158 census 36.
- **No stop:** the operator's third addition stops the phase only if
  anything beyond that changes. Nothing did, and no existing row changed,
  so CLAUDE.md rule 1 has no stop here.
- **Applied from the branch:** "preflight passed; applying live: [83]";
  after: 5862 rows, 120 tables, integrity ok, scope problems none;
  `376_live_diff.md`: equals the approved exact diff, yes. Read back
  read-only: schema 83, the rule row `absorb / stays_owed / reading /
  2027-10-07`, `foreign_key_check` empty.

### 2026-10-07 — The floor

10617 → 10645, +28, by a diff of collected ids against a worktree of
master `23ff246` (10617 there): the 27 new tests, gate 15's
`test_rolling_back_peels_every_successor[82]` (migration 083), and 373's
renamed test (−1 +1).
