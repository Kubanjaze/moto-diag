# Phase 375 — Warranty deductibles

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-10-07 (v1.0 the same day)

**Outcome (v1.1).** A deductible is recorded on the warranty, charged on
the customer's invoice by covered kind, taxed by a reading per
jurisdiction and payer, and taken off the claim, in both export files and
in every settlement. F196 widened and closed. Migration 084 live.
Regression 10685 passed / 0 failed at `c49db73`.

---

## Goal

Row 375: a warranty plan may charge the customer a deductible for each
covered repair, as LR 79-19's plan did ($25.00). Nothing records one.
Today a deductible can be charged only after the fact, as a short payment
billed to the customer (376), and only when the plan decides. 375 records
the deductible on the warranty. The customer's invoice charges it, and the
claim is reduced by it, both derived. Its tax follows a reading per
jurisdiction and payer. Both export files and the settlements carry it.

The operator's choices at Step 0 (verbatim in the phase log): **1A, 2A,
3A, 4A**, with three additions:
1. each `tax_deductible_rules` row's notes say what its sources leave
   open, for the accountant:
   - for the maker's warranty, 03-8's condition;
   - for a shop contract, whether a deductible is a "separate charge"
     under (5)(g), and 80-17's adjustment;
2. the handoff names what 1A and 2A leave out: a plan whose deductible is
   per visit, or includes tax;
3. F196 is widened to every test that turns the real clock into a day or
   month. Each is checked at 21:00 EDT on a month's last day with a fixed
   clock, and fixed as bug fix #1 was, or F196 stays open naming it.

## The worked example (373's case, a 2500 deductible), in cents

Covered labour 15000 and parts 8000, payer `other`, 6.25 % on parts. The
deductible splits over the covered lines by amount (largest remainder):
labour 1630, parts 870.

| | customer | claim | together |
|---|---|---|---|
| labour | 1630 | 13370 | 15000 |
| parts | 870 | 7130 | 8000 |
| tax | 54 (870 × 6.25 %) | 446 (500 − 54) | 500 |
| total | 2554 | 20946 | 23500 |

Under `maker_with_bike` and `shop_contract`, the claim carries no tax and
claims 20500. The customer pays 54 on the deductible's parts share.

## Logic

### Migration 084 (schema 83 → 84): new columns and one new table

- `warranties.deductible_cents`: NULL means not recorded, 0 means none;
  CHECK ≥ 0.
- `warranty_claims` gains:
  - `deductible_cents`: the deductible applied, after the cap;
  - `deductible_tax_cents`: its tax;
  - `deductible_tax_source`.
- `warranty_claim_lines.deductible_cents`: each covered line's share.
- `tax_deductible_rules`: the shape of `tax_warranty_rules`, keyed on
  `payer`. `deductible_tax` CHECK `taxable_share` only (as 376 allowed only
  `stays_owed`), with basis, validity, source, clause, provenance and
  notes.
- **Three US-MA regulation rows,** basis `reading`, effective 2009-08-01
  (as 373's), checked 2026-10-07, valid until 2027-10-07:
  - `other`: LR 79-19 (ruling 3) and LR 85-8;
  - `maker_with_bike`: LR 03-8 and LR 85-8;
  - `shop_contract`: 830 CMR 64H.1.1(5)(g), LR 80-17 and LR 85-8.
- **Each row's notes say what its sources leave open** (addition 1):
  - no Massachusetts source names a deductible;
  - for `maker_with_bike`: 03-8's no-tax holds only for a repair "with no
    additional consideration from the retail customer";
  - for `shop_contract`: whether a deductible is a "separate charge"
    under (5)(g), and 80-17's deduction of tax already paid on the
    property's cost, which is the accountant's adjustment.
- Live holds 0 warranties and claims, so no existing row changes. The
  rollback drops the table and the columns.

### Recording it (1A)

- `shop warranty add --deductible-cents N` and `shop warranty update W
  --deductible-cents N`. `warranty list` shows it, or "not recorded".
- `claim cover` with lines is refused while the warranty's deductible is
  not recorded, naming `warranty update W --deductible-cents N` (0 for
  none). That is the rule the payer and provider already follow. `--none`
  needs no deductible.

### The invoice (`_price_claims`, `generate_invoice_for_wo`)

For each claim with covered lines:
- **The deductible applied is the warranty's, capped at the claim's
  covered work before tax.** The amount is converted to the invoice's
  currency the way a flat supplies charge is. With no deductible recorded
  at invoicing, the invoice is refused, as with a missing payer.
- **It is split over the claim's lines by amount** (`_split_cents`). Each
  line's share is its `deductible_cents`. Its `amount_cents` is what the
  claim claims for it: the line less its share.
- **The tax.** When the deductible is more than 0, the jurisdiction's
  deductible rule for the warranty's payer must be on record on the
  invoice date. Otherwise the invoice is refused (`InvoiceTaxNotOnRecord`,
  naming `shop tax deductible-rule set --shop S --payer P`). The
  deductible's tax is its taxable share (the lines of the types the
  shop's rules tax) × the rate, rounded half up.
- **The claim:**
  - `covered_cents` is the claimed work (the covered work less the
    deductible);
  - the tax on the claim, when the payer's rule taxes it, is the tax on
    the whole covered taxable work less the deductible's tax. So
    together they are the tax on the entire covered parts charge (79-19);
  - otherwise 0, as today;
  - `amount_claimed_cents` = `covered_cents` + `tax_cents`.
- **The customer's invoice** gains one line per covered kind with a
  share: "Warranty deductible, claim #N: labour" (`labor`) and "…:
  parts" (`parts`). They follow the other lines, and the shop-supplies
  percentage does not apply to them, since covered work is outside its
  base today. They are taxed with the rest of the invoice by the shop's
  line rules. The invoice's note names the deductible, and that it was
  capped when it was.
- **Regenerating after a void derives the same deductible.** A claim past
  draft whose amount would change is refused by the existing check.

### Booking (3A)

No export code changes for the deductible itself:
- The customer's deductible lines are ordinary labour and parts lines,
  on the shop's existing income accounts and tax.
- The claim's lines are stored net, so 373's claim journal and Xero
  invoice credit each kind net of the deductible, and the claim's balance
  check (`export.py:554`) holds as it is.

A test proves the worked example in both files:
- **QuickBooks:**
  - customer: Dr A/R 25.54; Cr labour 16.30, parts 8.70, tax 0.54;
  - plan: Dr A/R 209.46; Cr labour 133.70, parts 71.30, tax 4.46.
- **Xero:**
  - customer: labour 1630 with tax 0, parts 870 with tax 54;
  - plan: labour 13370 with tax 0, parts 7130 with tax 446.

### Settlements (4A)

`generate_shortfall_invoice` reads `covered_cents` and the line amounts,
which are now net of the deductible, so a shortfall bills only what the
customer has not been charged:
- **denial:** 20500 + 446, so 20946, and the customer's total is 23500;
- **part approval at 18000:** 2883 (labour 1880, parts 1003) + 63 = 2946.

376's settlement entries need no change. A test holds the customer's
total across both invoices, on every path, to the repair's total with no
warranty, plus at most D11's cent.

### Tax rules: commands

- `shop tax deductible-rule set --shop S --payer P --effective … --valid-until
  … --source-title … --checked-on … [--reading]` records a shop's own
  reading.
- `shop tax confirm` re-checks the deductible rules with the rest.
- `shop tax status` lists them, and says which payers have none.

### The packet and `claim show`

- Coverage: "Deductible: $25.00 per covered repair", or "not recorded".
- The claim:
  - the covered work;
  - "Deductible (charged to the customer): $25.00, tax on it $0.54
    (source)", with "capped at the covered work" when it was;
  - the claimed work, the tax on the claim, and the amount claimed.
- Each covered line shows its claimed amount and its deductible share.
- Before the invoice: "Deductible: applied when the invoice is
  generated".
- `claim show` adds `deductible_cents` and `deductible_tax_cents`.

### F196, widened (addition 3)

- **The rule:** a test line that reads the real clock (`date.today()`,
  `datetime.now(…)`, `datetime.utcnow()`) and turns the value into a
  calendar day, month or year: a date-only or month `strftime`, `.date()`,
  `.isoformat()` of a date, `.year`, or a `[:10]` slice.
- **On `phase-375` it finds 9 lines in 6 files** (step 0's search found 5
  lines in 3; the operator counted 7 in 4). Each test holding one is run
  with the whole process's clock fixed at 2026-10-31 21:00 EDT. Any that
  fails is fixed as bug fix #1 was, in its own commit, or F196 stays open
  naming it.

## Tests (`tests/test_phase375_deductibles.py`)

Phase 370's frozen clock, in New York, on 373's job:
- the worked example under each payer: customer lines, tax and total; the
  claim's lines, tax and amount;
- both export files, entry by entry; every journal balances; income by
  kind and total tax equal the case with no deductible;
- the cap: a deductible over the covered work makes the claim 0, and the
  export leaves it out;
- refusals:
  - covering with no deductible recorded;
  - invoicing with a deductible and no rule on record (naming the
    command);
  - a rule past its validity;
- a deductible of 0 invoices exactly as before 375;
- settlements:
  - a denial and a part approval, billed and absorbed, in both files;
  - the customer's total never more than the repair without a warranty
    (plus D11's cent);
- regenerating after a void keeps the deductible; a changed deductible on
  a submitted claim is refused;
- the packet and `claim show`; `warranty add`, `update` and `list`;
- `tax deductible-rule set`, `confirm` and `status`; the seeded rows'
  notes (addition 1);
- migration 084: the columns, the table and its three rows; the rollback;
  no existing row changed.

Existing tests: 373's, 376's and Gate 16's warranties record
`--deductible-cents 0`, so their figures do not move. Mutations are in
`375_mutate.py`.

## Non-goals

F195 (use tax on parts given away); the provider's payment (365, paused);
any API route; a per-claim deductible or a deductible per visit (1B, not
chosen); a tax-inclusive deductible (2B, not chosen).

## Planned items

- [x] Migration 084, its rollback, a migration test
- [x] `warranty add/update --deductible-cents`, `list`; `claim cover` refusal
- [x] the invoice: split, cap, the deductible's tax, the claim net, the customer's lines
- [x] `tax_deductible_rules`: resolve, `deductible-rule set`, `confirm`, `status`
- [x] the packet and `claim show`
- [x] tests: both files, settlements, refusals; existing tests on `--deductible-cents 0`
- [x] F196 widened: the census, the month-end check, fixes (F196 closed)
- [x] mutations, 244G scanner, the floor
- [x] the deploy (dry run, live from the branch), the regression, the close-out, the handoff

## Deviations from Plan

1. **Three bug fixes, none planned:**
   - #1 and #2 are F196: two tests turned the real clock into a UTC day
     or month (275's export test, and 274's P&L);
   - #3: 376's migration-083 test applied every later migration too.

   Each has its own commit and register entry. The third prompted the
   working rule's search for a shared cause. #1 and #2 share one, already
   searched by rule. #3 is another family, and its census of 22
   roll-back-then-apply test files found no other.
2. **F196's census is 9 lines in 6 files** by the stated rule, where v1.0
   expected the operator's 7 in 4. The rule counts a year (`281_vin_year`)
   and a day made from a module constant (`274_quotes_variance:106`). It
   does not count 171:233, which is a timestamp, though its test was run.
3. **libfaketime was installed** (Homebrew) to fix the whole process's
   clock. 370's frozen-clock plugin replaces only the session modules'
   `datetime`.
4. **A test was added after the first mutation run.** I9 survived it: a
   claim whose warranty lost its deductible after covering was not
   tested.
5. **Decisions D8–D13, taken while building** (the log): the supplies
   percentage before the deductible lines; the readings' notes kept on a
   re-check; the claim's lines stored net; the deductible's own rounding;
   the packet's currency-free wording; the deductible converted like a
   flat charge.
6. **`regression.sh` refused the staged tree's `--full` record,** so
   `--full` ran a second time on the committed `c49db73`.

Not deviations, recorded for the reader: no export code changed (D10);
no refute pass ran (code, tests and three quoted rule rows, not content
rows).

## Results

| what | result |
|---|---|
| the worked example (`other`) | customer: labour 1630 + parts 870, tax 54, total 2554; claim: 13370 + 7130, tax 446, claimed 20946; together 23500 and tax 500, as without a deductible |
| `maker_with_bike`, `shop_contract` | customer 2554 (tax 54); claim 20500, no tax |
| QuickBooks | customer journal: Dr A/R 25.54; Cr labour 16.30, parts 8.70, tax 0.54. Claim journal: Dr A/R (plan) 209.46; Cr labour 133.70, parts 71.30, tax 4.46. Ledger equals the no-deductible case: A/R 235.00, labour 150.00, parts 80.00, tax 5.00 |
| Xero | customer invoice: 16.30 with tax 0, 8.70 with tax 0.54; plan's invoice: 133.70 with tax 0, 71.30 with tax 4.46 |
| settlements | denial: shortfall invoice 13370 + 7130 + tax 446 = 20946, so the customer pays 23500 in all. Part approval at 18000: 1880 + 1003 + 63 = 2946. QuickBooks `-CR`: Dr 133.70, 71.30, 4.46 / Cr 209.46, or Dr 18.80, 10.03, 0.63 / Cr 29.46; absorbed, Dr write-offs. Xero credit notes: −133.70, −75.76; −18.80, −10.66; absorbed −209.46, −29.46 |
| the cap | a 30000 deductible on 23000 of covered work: the customer pays 23000 + 500; the claim is 0 and is not exported |
| the readings | `tax_deductible_rules`, US-MA, three rows, basis `reading`, effective 2009-08-01, checked 2026-10-07, valid until 2027-10-07: `other` (LR 79-19, 85-8), `maker_with_bike` (LR 03-8, 85-8), `shop_contract` (830 CMR 64H.1.1(5)(g), LR 80-17, 85-8); notes per addition 1 |
| tests | `tests/test_phase375_deductibles.py` 39; three existing helpers record `--deductible-cents 0` |
| mutations | 20/20 red (`375_mutate.out`) |
| 244G scanner | all of `tests/`: 0 hits; its planted control reported |
| F196 | 9 lines in 6 files; under libfaketime at 2026-10-31 21:00 EDT, 8 failed in 274's P&L before bug fix #2, then 137 passed there and at three other moments; closed |
| `wholetree.sh --full` | 4047 passed at `c49db73` |
| `COLLECTED_TEST_FLOOR` | 10645 → 10685 (+39 new, +1 gate 15's rollback case for 084) |
| migration 084 | dry run: `schema_version` +1, `tax_deductible_rules` +3, no row changed or removed. **Live:** equals the approved exact diff; 5866 rows, 121 tables, integrity ok, schema 84; backup `motodiag_pre375_20261007_220325.db` |
| findings | F196 filed and closed |

Regression of record: 10685 passed, 0 failed, 0 skipped, 0 errors at `c49db73` (25 min 45 s wall, `python -m pytest -n auto --dist load`, exit 0)

## Risks

- **The tax on a deductible is a reading** of sources that do not name
  it. For the maker's warranty and a shop contract, it adds tax where
  the sources leave the question open. For the shop's accountant to
  confirm before a real warranty job.
- **The deductible's tax is its own rounding, and the invoice's tax is
  rounded once over all its taxable lines** (D11). On an invoice with
  other taxed lines they can differ by a cent.
- **1A charges every claim once.** A plan charging once per visit, or a
  deductible that includes tax (2B), is not modelled; named in the
  handoff.
- **No test converts a deductible to another currency** (D13).
- **No file has been tried in a real QuickBooks or Xero company** (275).
