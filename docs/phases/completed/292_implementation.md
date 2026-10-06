# Phase 292 — Gate 16: one job walked from booking to the accounting export

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-10-06 (v1.0 the same day)

---

## Goal

Row 292, as it read before this phase: "Gate 16 — Business
infrastructure integration test. Customer books → intake → warranty
check → repair → invoice → payment → accounting export". Track O's
closing gate.

The operator's prompt (`docs/prompts/292_gate16.txt`) sets a test-only
gate, the shape of Gate 15: tests and documents only, no migration, no
change to the live database, no Stripe key. Step 0 (`292_step0.md`)
found three hand-offs that do not exist or do not hold, and stopped on
them. The operator's choices, 2026-10-06:

- **H1, the Xero export's tax spread:** "Fix in 292". The one piece of
  production code in this phase.
- **H2, a warranty claim and the invoice:** "Finding + row". F188,
  row 373.
- **H3, check-in and the intake:** "Finding + row". F189, row 374.

## Logic

One test file, `tests/test_phase292_gate16.py`. Each walk runs on its
own freshly migrated database in the test's temporary directory, never
`data/motodiag.db`, through `CliRunner` against the real CLI root, with
Stripe answering from 273's fixtures (`FixtureHTTP`).

1. **The shop, by command:** `shop profile init` (with Thursday's hours),
   `shop member add --user 1`, `shop tax jurisdiction set --code US-MA`,
   `shop tax status`, `shop labor-rate set`, `advanced parts seed --yes`,
   `shop payments connect` and `status`, `shop terminal setup
   --simulated`, `shop accounting map set` for both targets.
2. **Job A, the card job, in the row's order:**
   - customer, bike, owner link and coverage: `shop customer add`,
     `garage add`, `shop customer link-bike`, `shop warranty add`;
   - **book:** `appointment slots`, `book`, `confirm`;
   - **intake:** `intake create --mileage`;
   - **work order:** `work-order create --intake`, then `appointment
     check-in --wo`;
   - **warranty check:** `warranty check --bike --on --mileage --json`,
     covered; `warranty claim open --warranty --wo`;
   - **repair:** `work-order start`, a catalogue part found by `advanced
     parts search --json`, `parts-needs add`, `mark-ordered`,
     `mark-received`, `work-order complete --actual-hours`, `appointment
     complete`;
   - **invoice:** `invoice generate`;
   - **payment:** `invoice pay-link` in one walk, `terminal pay` in the
     other; then the signed `payment_intent.succeeded` posted to
     `/v1/billing/webhooks/stripe` through the API test client.
3. **Job B, the cash job,** the same order on a second customer and
   bike, whose warranty has expired on the day: `warranty check` reports
   it not valid, and no claim is opened. Paid by `invoice mark-paid`.
4. **Export:** `accounting export` for QuickBooks Online and for Xero,
   over the walk's day, carrying both invoices; then the same QuickBooks
   export again, which must refuse.
5. **The hand-off checks,** each read from the database or the printed
   output after its step: the appointment's work order is the one
   created from the intake; the work order carries the intake's shop,
   customer and bike; the claim is on that work order and bike; the
   invoice is on that work order and `sent`; the payment row is for that
   invoice; the export carries exactly the two invoices.
6. **The money, in integer cents:** the work order's labour (hours ×
   the recorded rate) and parts (each line's quantity × unit cost) →
   the invoice's lines, subtotal, tax (the taxable lines × the rate
   `shop tax status --json` prints, half up) and total → the amount
   Stripe was asked for and the payment row → the event → QuickBooks'
   receivable, income and tax lines → Xero's line amounts and per-line
   tax. Each link equals the one before it, and the known values are
   also pinned.
7. **Paid only through the webhook:** after `pay-link` or `terminal pay`
   the invoice is `sent` and its payment `started`; after the event it is
   `paid`, its `paid_at` is the event's time, and the payment's outcome
   is `paid_invoice`.
8. **The clock:** 2026-10-15 12:00 in America/New_York (S0-5 D2). The
   invoice's date is asserted to be that day, so a freeze that does not
   take hold fails on any other day. After the walk, no `motodiag`
   module that the walk loaded may still hold the real `datetime` or
   `date`.
9. **No key, no network:** the Stripe key is 273's test-only value; every
   expected Stripe request was made and no other; the network guard is
   installed; the walk's database is not the production path.
10. **The printed output** of every walk command names no phase, track
    or F-number (F158), with a planted control.
11. **H2 and H3 pinned as they are,** as executable documentation that
    passes today and fails the day rows 373 and 374 change them: the
    covered job's invoice total equals its full labour and parts plus
    tax, and the claim's amount is not recorded; a check-in with no
    `--wo` opens a work order with no intake.

**H1, the fix (bug fix #1):** `accounting/export.py`'s Xero rows spread
the invoice's tax only over lines of the types the invoice records as
taxed (`taxed_line_types`, Phase 281). An invoice made before 281
(column empty) keeps the old spread over every line. An invoice that
carries tax but no line of a taxed type is refused with the reason.
Tested on its own (`tests/test_phase292_xero_tax.py`) and by the walk.

## Key Concepts

- **The commands are the evidence.** Every row the walk needs comes
  from a command a user can run; nothing is written to the database by
  hand. The database is read only to check a hand-off.
- **273's fixtures, not 273's seeds.** `FixtureHTTP` answers Stripe;
  `seed_invoice`, `seed_account` and `seed_reader` are not used.
- **A hand-off is checked where it happens,** not inferred from the end
  state.

## Decisions

- **D1.** The mechanic is user 1 (S0-5 D1).
- **D2.** The clock (S0-5 D2).
- **D3.** Two card walks and one cash job in each (S0-5 D3).
- **D4.** The walk takes the order that holds: intake, then work order,
  then check-in with `--wo` (H3, F189).
- **D5. The planted controls are temporary edits** to the walk, each
  run, captured red and removed, with the output in the phase log, as
  272 did. The operator's five: an invoice marked paid with no event; an
  event whose amount differs from the invoice's total; an expired
  warranty reported as covered; the export's tax line differing from the
  invoice's tax; an invoice exported twice to the same target. Plus
  F158's printed-reference plant.
- **D6. The bug fix has its own commit and register entry,** and its
  own test file, so the gate stays one file under its rule-found name.

## Non-goals

- F188 and F189's fixes: rows 373 and 374.
- Customer self-booking (363), OEM claim submission (362), API sync and
  payment reconciliation (365, 366), live payments (371), payment routes
  and screens (372).
- The day and month edges of F186: the walk runs at midday mid-month.
- Any live database change; no migration.

## Planned items

1. Row 292 🚧 before Step 0; corrected per K8 after it.
2. Rows 373 and 374 (🔲), F188 and F189.
3. Bug fix #1: the Xero tax spread, with `tests/test_phase292_xero_tax.py`.
4. `tests/test_phase292_gate16.py`, Logic 1–11.
5. The six planted controls, each red then removed.
6. Mutations of the fix and of the hand-offs the gate relies on, each red.
7. 244G's scanner over the new files; `COLLECTED_TEST_FLOOR` raised.
8. `wholetree.sh --full` on the committed HEAD; the regression of record.
9. Close-out: v1.1, row 292 ✅, handoff.

## Verification Checklist

- [x] Row 292 🚧 before Step 0, corrected per K8, within 120 words
- [x] Rows 373, 374 added; F188, F189 filed; `roadmap_check.py` and `finding_check.py` green
- [x] Bug fix #1 committed with its test (`be1030b`); 275's and 281's tests green
- [x] Both card walks green; the cash job green (67 commands per walk)
- [x] Each hand-off checked at its step
- [x] The money equal at every link, in cents
- [x] Paid only through the webhook
- [x] The clock held; the network guard held; no key
- [x] No build reference printed; its plant red
- [x] The operator's five plants red, then removed
- [x] Mutations 15/15 red
- [x] 244G scanner 0; floor 10401 → 10491; `wholetree.sh` and `--full` green
- [x] Regression of record by `regression.sh`: 10491 passed at `c3fde4e`
- [x] `verify_phase.sh` after the merge (its result is in the handoff)
- [x] Handoff written

## Deviations from Plan

- **Production code in a test-only gate.** The operator chose to fix H1 in
  this phase ("Fix in 292"): bug fix #1, `accounting/export.py`, its own
  commit and test file. No other `src/` change.
- **The estimate differs from the hours worked** (1.0 h against 1.5 h and
  1.25 h). With both equal, an invoice billing the estimate would have
  passed; mutation M1 now catches it.
- **The planted controls stay as tests.** v1.0 planned temporary plants
  only; each also runs as a planted walk the gate's own check must reject
  (`TestThePlantsTurnTheGateRed`), as 272 kept its plants. A sixth plant,
  F158's, was added.
- **The walk builds the API app once before the freeze.** The freeze check
  named 11 modules that `create_app` loaded during the walk.
- **The reader is answered with this shop's label.** The recorded fixture
  carries the smoke run's shop name, which F158's check caught in the
  printed output; a test asserts the request carried the label the walk
  answers with.
- **Gate 16 is not a whole-tree member.** Membership is computed from
  enumerating a repo directory (`wholetree.py`'s docstring), and the gate
  walks a scratch database. The regression of record is what runs it.
- **The live database was not read.** H1's live exposure (Xero files
  already written) was not measured: the read was refused as a production
  read. Left to the operator, with the query, in the handoff.

## Results

| | |
|---|---|
| Test files | `tests/test_phase292_gate16.py` (80), `tests/test_phase292_xero_tax.py` (10) |
| Walks | Checkout and the simulated reader: 67 commands each, all exit 0 but the deliberate second export; 6 and 8 Stripe requests from fixtures, none unanswered |
| Money | A: 18000 + 9998 = 27998, tax 625, total 28623 = Stripe asked = payment = event; B: 15000 + 3150 = 18150, tax 197, total 18347; QuickBooks and Xero equal the invoices line by line |
| Webhook | invoice `sent` after starting; `paid` at `2026-10-15T16:00:00.000+00:00` on the event; one event recorded |
| Bug fix #1 | Xero's tax on taxed lines only: labour (18000, 0), parts (9998, 625), where the old spread gave 401 and 224 |
| Plants | six, each red, each removed; kept as planted walks |
| Mutations | 15/15 red |
| Findings | F188 (row 373), F189 (row 374) |
| Floor | 10401 → 10491 |
| Regression of record | **10491 passed, 0 failed, 0 skipped, 0 errors** at `c3fde4e` (22 min 7 s wall, `python -m pytest -n auto --dist load`, exit 0) |

Key finding: **the seams were between phases, not inside them.** Each
step's own tests passed; the walk found the Xero export written before
per-line tax existed, a warranty claim the invoice never hears of, and a
check-in that cannot carry the intake.

## Risks

- **The freeze replaces names, not the clock.** A module that imports
  `datetime` as a module, or that is first loaded after the freeze,
  escapes it. The post-walk check catches the second; S0 found no
  module on the walk's path doing the first in a way the walk reads.
- **The fixtures are recorded responses.** The walk proves this app's
  side of each Stripe call, not Stripe's; 273's smoke run did that.
- **Xero's import was never tried in a real Xero company** (275). The
  fix makes the file agree with the invoice; whether Xero accepts a
  zero TaxAmount on a line mapped to a taxed rate is the shop's mapping.
