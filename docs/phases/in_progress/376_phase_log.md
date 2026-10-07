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
