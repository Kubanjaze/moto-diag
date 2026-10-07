# Phase 376 — Warranty claim settlements in the accounting export (F190)

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-10-07 (v1.0 the same day)

**Outcome (v1.1).** F190 and F194 closed; migration 083 live. Each
settlement is in both files against the claim's receivable, proven to
balance to the cent for a denial and a part approval, billed and
absorbed. Regression 10645 passed / 0 failed at `e452b99`.

---

## Goal

Row 376: a claim denied or paid short is settled by the shop (`claim
settle`): the shortfall billed to the customer or absorbed. Since 373 the
export books the claim as a receivable from its provider and nothing
after it, so the books show the provider owing the full claim. 376 puts
each settlement in both export files, against the claim's receivable, and
closes F190.

The operator's choices at Step 0 (verbatim in the phase log): **1A, 2A
(and the use-tax finding, F195), 3A, 4A, 5A**, with four additions:
1. the expected-tax line covers every credit note, absorbed ones too;
2. an absorbed claim that carried no tax prints that tax on the parts'
   cost may be due, naming F195;
3. 083's dry run changes no existing row, and no schema object beyond the
   two rebuilt tables and the new ones; every index, and the foreign keys
   of `accounting_export_invoices` and `accounting_export_claims`, come
   through unchanged. Anything else: stop and show the operator;
4. the export's record keeps each file's name and hash.

## What each settlement books (1A)

Against the claim's own entry (373): QuickBooks journal `<invoice>-W<claim>`,
Xero sales invoice of that number to the provider.

| | QuickBooks | Xero |
|---|---|---|
| billed | journal `…-W<claim>-CR`: Dr each kind's share, Dr the claim's tax inside the shortfall; Cr A/R (provider) the shortfall. Then the shortfall invoice as an ordinary invoice journal, A/R in the customer's name | credit note `…-W<claim>-CR` to the provider, one line per shortfall line, tax-inclusive; the shortfall invoice to the customer in the invoices file |
| absorbed | journal `…-W<claim>-CR`: Dr the absorbed account, Cr A/R (provider), the shortfall | credit note `…-W<claim>-CR` to the provider, one line, the absorbed account at its mapped rate, tax-inclusive |

- **The shares come from what is stored.** Billed: each kind's share is
  the shortfall invoice's lines of that kind (373 split them); the claim's
  tax inside the shortfall is the shortfall less the shortfall invoice's
  subtotal. Absorbed: the shortfall, whole, its tax inside it (2A).
- **The Xero credit notes are tax-inclusive (5A):** no `TaxAmount`
  column; each line's `UnitAmount` is the negative of its share plus its
  share of the claim's tax (spread over the lines of the types the claim's
  invoice taxed, as 373 spreads it). Xero works out the tax inside.
- **Every entry balances to the cent.** By construction, each credit is
  the shortfall invoice's lines plus the claim's tax inside the shortfall,
  and that tax is defined as the shortfall less those lines. The one check
  that can fire is in code: that tax must lie between 0 and the claim's
  tax, else the export is refused (v1.0 planned two more checks, which
  could never fire; Deviations 2). The D11 cent is the difference between
  the credit's tax and the shortfall invoice's tax.

## Logic

### Migration 083 (schema 82 → 83)

Through the deploy skill. Rebuilds two tables, adds three; live holds 0
rows in both rebuilt tables, so no existing row changes.
- **`accounting_accounts`, rebuilt:** `kind` CHECK gains `absorbed`
  ("warranty shortfall absorbed"). Same columns, same UNIQUE.
- **`accounting_exports`, rebuilt:** `invoice_count >= 0`, a new
  `settlement_count INTEGER NOT NULL DEFAULT 0 CHECK (>= 0)`, and
  `CHECK (invoice_count + settlement_count > 0)`. `file_name` and
  `file_sha256` stay: the first file the export wrote.
- **`accounting_export_files`** (new): `export_id`, `holds`
  (`journal_entries`, `invoices`, `credit_notes`), `file_name`,
  `file_sha256`, `row_count`; one row per file written (addition 4).
- **`accounting_export_settlements`** (new): `export_id`, `claim_id`;
  which export carried which settlement, per target.
- **`tax_settlement_rules`** (new, 2A): the shape of
  `tax_warranty_rules`, keyed on `settlement` (`absorb`), with
  `absorbed_tax` CHECK `stays_owed` only. One US-MA regulation row: basis
  `reading`, effective 1999-01-01, checked 2026-10-07, valid 12 months
  (281's rule), source TIR 00-3, notes naming ST-BDR, IRC § 166 and the two
  unsettled points (part approval; F195).
- **The rebuild** follows migration 052's shape: `PRAGMA
  foreign_keys=OFF`, create, copy, drop, rename, recreate indexes. A test
  (addition 3) compares every `sqlite_master` row other than the two
  rebuilt tables and the new objects, before and after, on a database
  holding rows in every accounting table; and `foreign_key_check` is
  empty. The rollback rebuilds both back and drops the new tables.

### The tax rule (2A)

`tax_settlement_rules` is resolved like 373's warranty rules (the shop's
own row, else the regulation row, valid on the settlement's day).
- `shop tax settlement-rule set --shop` records a shop's own reading,
  with its source;
- `shop tax confirm` re-checks it with the rest;
- `shop tax status` lists it.
The export refuses an absorbed settlement whose claim carried tax when no
reading is on record (or it has lapsed), naming the command, as 281 and
373 refuse.

### The export

- **Selection:** settlements of the shop's claims whose `settled_at`, read
  parsed (`datetime()`), falls on a shop's day in the range; less those
  an earlier export to the same target carried, unless
  `--include-exported`.
- **D1 (Step 0): the claim must be in the target's books:** carried by an
  earlier export to the target or by this one. Otherwise the export is
  refused, naming the claim and the day its invoice was issued.
- **QuickBooks:** one file, journal entries: the invoices' (as today),
  then each settlement's, in settlement order.
- **Xero:** the invoices file at `--out` (invoices, claims, billed
  shortfall invoices) and, when there are credit notes,
  `<stem>_credit_notes<suffix>` beside it, in the columns X1 names:
  `ContactName`, `EmailAddress`, `InvoiceNumber`, `Reference` (the claim's
  number, for allocating by hand), `InvoiceDate` and `DueDate` (the
  settlement's day), `InventoryItemCode`, `Description`, `Quantity`,
  `UnitAmount`, `Discount`, `AccountCode`, `TaxType`, `TrackingName1`,
  `TrackingOption1`, `TrackingName2`, `TrackingOption2`, `Currency`,
  `BrandingTheme`. A file with no rows is not written.
- **The absorbed account (3A)** is required, like any kind, only when an
  absorbed settlement is in the run; Xero needs its tax rate name.
- **A range with settlements and no invoices exports**; a range with
  neither is refused as today. A run with no settlements writes the same
  bytes as before 376 (D4).
- **The record:** `accounting_exports` with both counts;
  `accounting_export_files` per file (addition 4);
  `accounting_export_invoices` now also carries billed shortfall invoices;
  `accounting_export_settlements`.
- `shortfall_invoices_in_range` and the "left out" message go: shortfall
  invoices are exported with their settlement.

### The CLI (`shop accounting export`)

- "Wrote N invoice(s), M warranty claim(s) and K settlement(s)" and, per
  file, its path, what it holds and its rows.
- **Every credit note, absorbed ones too, gets an expected-tax line**
  (addition 1): number, total, the tax Xero should show; with the advice to
  check it before approving the draft, and that an absorbed credit note
  should show 0.00.
- By hand: QuickBooks, apply each `-CR` journal's credit to the claim's
  journal in Receive payment; Xero, choose tax-inclusive when importing the
  credit notes, approve them, and allocate each to the provider's invoice
  named in `Reference`.
- An absorbed settlement whose claim carried tax: the tax stays owed (the
  rule's source named). An absorbed claim that carried no tax and covered
  parts: tax on the parts' cost may be due, see F195 (addition 2). A
  labour-only claim transfers no parts, so the line is not printed for it.
- `shop accounting exports` lists each export's files.
- `map set --kind absorbed` is documented in its help.

### F194 (4A)

`_format_invoice_number` and the shortfall invoice's number date the
number by the shop's day of the same instant (`core/timestamps.local_day`).

## Tests (`tests/test_phase376_settlement_export.py`)

On a fixed clock in New York (370's frozen clock), 373's job: covered
15000 + 8000, tax 500, claimed 23500.
- **Balance, both files:** denial and part approval (20000), billed and
  absorbed; each QuickBooks journal's debits equal its credits; each
  credit note's lines sum to minus the shortfall; the D11 cent appears as
  tax payable 501; revenue by kind is unchanged from the claim paid in
  full (no double count).
- The worked example's figures, row by row.
- 21:00 EDT on a month's last day: the settlement lands in that month's
  export, not the next; the shortfall invoice's number carries that
  month's day (F194).
- Once per target: a second export leaves it out; the other target still
  takes it.
- D1: a settlement whose claim was never exported is refused.
- A range with settlements only exports; a run with no settlements is
  byte-identical to the export before 376 (D4).
- The absorbed account unmapped: refused, naming the command; no reading
  on record for a taxed absorbed claim: refused, naming `settlement-rule
  set`.
- The CLI: expected tax for every credit note; F195's line for an
  absorbed untaxed parts claim and not for labour only; each file's name
  and hash in `accounting_export_files`.
- Migration 083: addition 3's schema comparison and FK check; the
  rollback.
- The inverted 373 test: the shortfall invoice is exported, not left out.
- Mutations in `376_mutate.py`.

## Non-goals

The provider's payment and its reconciliation (365, paused); deductibles
(375); any API route; a cost basis for F195.

## Planned items

- [x] Migration 083, its rollback, the schema comparison test
- [x] `tax_settlement_rules`: resolve, `settlement-rule set`, `confirm`, `status`
- [x] the export: settlements selected, D1, QuickBooks journals, Xero credit notes file, the record
- [x] the CLI's output: files, expected tax, by-hand steps, F195 line
- [x] F194: the number's day
- [x] tests; the 373 test inverted; a mutation file
- [x] the deploy (dry run; no stop, since addition 3's condition held), live from the branch
- [x] the regression, the close-out, F190 and F194 closed

## Deviations from Plan

1. **Removing the "left out" path changed one 373 test**, as intended:
   `test_a_shortfall_invoice_is_left_out_and_said_so` is now
   `test_a_shortfall_invoice_is_exported_with_its_settlement`.
2. **Two planned balance checks were not shipped** (log D7): a whole-file
   journal check and a credit-note sum check. Both hold by construction,
   so neither could ever fail (S2, S4). The check that can fire refuses a
   shortfall invoice out of step with its claim; a test and mutation Q4
   cover it.
3. **A void shortfall invoice refuses the export** (D6), which v1.0 did
   not plan.
4. **`accounting_export_files.row_count` allows 0** (D9), where v1.0 said
   `> 0`.
5. **The seeded rule's notes do not cite F195** (D10): the F158 ratchet
   refuses build references in text a shop sees. The CLI line cites it.
6. **`accounting_exports.invoice_count` counts billed shortfall invoices**
   (D8), since `accounting_export_invoices` records them.
7. **The D4 control is a hash from master's code** (D11), measured in a
   worktree, not a comparison inside the test.
8. **The F195 line is printed for an absorbed untaxed claim that covers
   parts**, not a labour-only one; the reading is recorded in the log.

Not deviations, recorded for the reader:
- no bug fix was needed after a commit, so there is no register;
- no refute pass ran: the phase ships code, tests, one rule row read from
  its source, and a schema migration, not content rows.

## Results

| what | result |
|---|---|
| the worked example (373's case: claimed 23500) | part approval at 20000, billed: QuickBooks `-CR` Dr labour 22.34, parts 11.92, tax 0.74, Cr A/R (plan) 35.00; then the shortfall invoice, Dr A/R (customer) 35.01, Cr labour 22.34, parts 11.92, tax 0.75. Absorbed: Dr Warranty Write-offs 35.00, Cr A/R (plan) 35.00. Xero: credit note labour −22.34, parts −12.66 (tax-inclusive; expected tax 0.74); absorbed, one line −35.00 at the absorbed rate, expected tax 0.00 |
| where it ends (whole file, with the customer's 7656 invoice) | revenue labour 20000, parts 10500 in every case; tax payable 657 billed part (D11's cent), 656 otherwise; A/R plan 20000 or 0; customer +3501 or +23500 billed; write-offs 3500 or 23500 absorbed |
| tests | `tests/test_phase376_settlement_export.py` 27; 373's test inverted; `test_phase255B` floor |
| mutations | 22/22 red (`376_mutate.py`) |
| 244G scanner | all of `tests/`: 0 hits; its planted control reported |
| D4 | no-settlement export byte-identical to master `23ff246`: QuickBooks `81c1918f…`, Xero `432cd338…` |
| `wholetree.sh --full` | 4047 passed at `e452b99` |
| `COLLECTED_TEST_FLOOR` | 10617 → 10645 (+27 new, +1 gate 15's rollback case for 083) |
| migration 083 | dry run: `schema_version` +1, `tax_settlement_rules` +1, no row changed; two tables rewritten (0 live rows), five objects added, none removed; children and their index unchanged. **Live:** equals the exact diff; 5862 rows, 120 tables, integrity ok, schema 83; backup `motodiag_pre376_20261007_183425.db` |
| findings | F190, F194 closed; F195 filed (use tax on parts given away) |

Regression of record: 10645 passed, 0 failed, 0 skipped, 0 errors at `e452b99` (26 min 45 s wall, `python -m pytest -n auto --dist load`, exit 0)

## Risks

- **No file has been tried in a real QuickBooks or Xero company**
  (275). The credit-note format is read from Xero's page; its tax sign
  is avoided, not known. Intuit's pages were read through WebFetch.
- **Xero's rounding of inclusive tax** can differ from the claim's tax by
  a cent; the expected-tax line makes it visible.
- **The tax on an absorbed shortfall is a reading** (2A), and F195 is
  open.
