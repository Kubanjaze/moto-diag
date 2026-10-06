# Phase 292 — Gate 16: one job walked from booking to the accounting export — phase log

**Status:** ✅ Complete (2026-10-06)
**Branch:** `phase-292` (Opus session, main checkout)

---

### 2026-10-06 — Opened: Gate 16, test-only

The operator's prompt is `docs/prompts/292_gate16.txt` (committed
`9016d54`). The last session's state is
`docs/handoffs/2026-10-06_273_closed.md`. Tests and documents only, the
shape of Gate 15: no production code, no migration, no change to the live
database, no Stripe key. Row 292 went 🚧 before Step 0.

### 2026-10-06 — Step 0

`292_step0.md`. Every measured fact in the prompt re-verifies (S0-1). The
payment-command count is 3 files by the operator's vocabulary and 5 when
`mark-paid` is counted; no file runs booking, payment and export.

A dry walk of one job on a scratch database (S0-3) ran every step
through the real commands. It found two wrong assumptions in the walk
itself before the gate was written: customer id 1 is the "Unassigned"
placeholder, and `factory` is not a coverage type.

**Three hand-offs that do not exist or do not hold** (S0-4): H1, the Xero
export spreads the invoice's tax over untaxed labour; H2, a warranty
claim and the invoice do not know about each other; H3, check-in opens a
work order with no intake, and none can be attached afterwards. Closing
any of them takes production code, so per the prompt this was a fork,
and the session stopped and asked.

**The operator's choices, verbatim (2026-10-06):**

> H1: "Fix in 292 (Recommended)"
> H2: "Finding + row (Recommended)"
> H3: "Finding + row (Recommended)"

So rows 373 (warranty work on the invoice) and 374 (check-in with an
intake) were added, both 🔲, and then F188 and F189 were filed with the
finding skill, so the rows were in place before the findings cited
them. `roadmap_check.py` and `finding_check.py` exit 0. H1 is bug fix #1
of this phase.

**Decisions taken here, not stops** (S0-5): D1, the mechanic is user 1,
the seeded system user, because no command creates a user and nothing is
seeded; D2, the clock; D3, two card walks with a cash job in each.

**The live database was not read.** A read-only query of
`data/motodiag.db` to count Xero exports already written (H1's live
exposure) was refused by the session's permission classifier as a
production read. It was not retried by any other route. The question is
left to the operator; the query is in the handoff.

**The edit guard** blocked `sed -i` on a scratch script in the session
scratchpad: "`sed -i` edits a file in place, and is blocked wherever it
points". That is its documented scope (CHANGELOG, Phase 360), not a
misfire. The script was edited with the Edit tool. The guard was not
changed.

### 2026-10-06 — v1.0 committed and pushed

`a302771`: Step 0, v1.0, row 292 🚧 with its K8 text, rows 373 and 374,
F188 and F189. `wholetree.sh` exit 0 before the commit (1523 passed).
Pushed as `phase-292`.

## Bug-fix register

### Bug fix #1 — 2026-10-06 — the Xero file put untaxed labour's share of the tax on its row

- **Issue:** on a Massachusetts invoice (labour 18000 cents, not taxed;
  parts 9198, taxed; tax 575), the Xero export wrote TaxAmount 3.80 on the
  labour row and 1.95 on the parts row (Step 0, S0-4 H1).
- **Root cause:** `accounting/export.py` spread the invoice's tax over
  every line in proportion to its amount (Phase 275). Phase 281 later made
  the tax fall on some line types only and recorded them on the invoice
  (`taxed_line_types`), and the export never read that column. The sum
  still equalled the invoice's tax, so 275's and 281's tests stayed green.
- **Fix:** `_taxed_types` reads the record; `_line_taxes` spreads the tax
  over lines of a taxed type only. An invoice made before 281 (no record)
  keeps the spread over every line; one carrying tax but no line of a taxed
  type is refused with the reason. QuickBooks was right and is unchanged.
- **Files:** `src/motodiag/accounting/export.py`,
  `tests/test_phase292_xero_tax.py`.
- **Verified:** the new file was 4 failed, 6 passed before the fix and 10
  passed after; 275's export tests and 281's tax tests passed (45). Gate
  16's Xero check is green with it, and red with it reverted (plant 4,
  mutation X1).

**Commit.** `be1030b`

### 2026-10-06 — Build: `tests/test_phase292_gate16.py`

`f3fe270`: the walk, 73 passed at first commit. Two things the first runs
found in the gate, before its first commit, not bug-fix entries:
- **The freeze check named 11 modules that escaped it,** all loaded by
  `create_app` when the webhook's app was built. The walk now builds the app
  once before freezing. The check then reports none.
- **F158's check found "Phase 273" in the printed output.** It came from
  the recorded reader fixture: the smoke run's shop was "Phase 273 Smoke
  Shop", and Stripe returns the label it was sent. The app sends "<shop
  name> simulated reader". The walk answers with this shop's label, and a
  test asserts the request carried exactly that label.

**The walk, both channels, all from commands** (S0-2's table): 67
commands per walk, every one exit 0 except the deliberate second export
(exit 1). Stripe requests answered from fixtures: 6 in the Checkout walk,
8 in the reader walk, none unanswered.

**The money** (pinned as KNOWN, and each link derived from the one
before):

| link | job A (card) | job B (cash) |
|---|---|---|
| work order labour: hours × 12000 | 1.5 h → 18000 | 1.25 h → 15000 |
| work order parts | 2 × 4999 (catalogue) = 9998 | 1 × 3150 (override) = 3150 |
| invoice subtotal | 27998 | 18150 |
| invoice tax: parts × 0.0625, half up | 624.875 → 625 | 196.875 → 197 |
| invoice total | 28623 | 18347 |
| Stripe asked / payment row / event | 28623 | — (`mark-paid`) |
| QuickBooks: A/R debit; labour, parts, tax credits | 286.23; 180.00, 99.98, 6.25 | 183.47; 150.00, 31.50, 1.97 |
| Xero: labour row, parts row (amount, tax) | (18000, 0), (9998, 625) | (15000, 0), (3150, 197) |

The estimate is 1.0 h on both jobs, so an invoice billing the estimate
instead of the hours worked fails (mutation M1).

### 2026-10-06 — The planted controls

One temporary line in the `walked` fixture passed a plant named by an
environment variable to the walk; the gate (less the F189 test, which
does not use the fixture) was run under each of the six plants, then the
line was removed. `git diff` against `f3fe270` afterwards: only the
`PLANTS` definitions (39 lines), no `TEMPORARY` marker. Outputs are in
the session scratchpad (`plant1.txt` … `plant6.txt`).

1. **An invoice marked paid with no event** (`mark-paid` run after
   `pay-link` or `terminal pay`, before the event). Red, **4 failed, 68
   passed**:
   ```
   E   AssertionError: assert {'paid_at': '...atus': 'paid'} == {'paid_at': N...atus': 'sent'}
   E     {'status': 'paid'} != {'status': 'sent'}
   FAILED ...TestPaidOnlyThroughTheWebhook::test_starting_the_payment_does_not_pay_the_invoice[checkout]
   FAILED ...TestPaidOnlyThroughTheWebhook::test_the_signed_event_pays_it[checkout]
   ```
   and the same two for `[terminal]`.
2. **An event whose amount differs from the invoice's total** (one cent
   over). Red, **6 failed, 66 passed**:
   ```
   E   assert 28624 == 28623
   E   AssertionError: assert {'paid_at': N...atus': 'sent'} == {'paid_at': '...atus': 'paid'}
   FAILED ...TestTheMoney::test_the_card_payment_is_the_invoice_total[checkout]
   FAILED ...TestPaidOnlyThroughTheWebhook::test_the_signed_event_pays_it[checkout]
   FAILED ...TestWhatTheGateFound::test_f188_covered_work_is_invoiced_to_the_customer_in_full[checkout]
   ```
   and the same three for `[terminal]`. The app rejected the event and the
   invoice stayed `sent`, as 273 built it.
3. **An expired warranty reported as covered** (`coverage_status` answers
   valid). Red, **2 failed, 70 passed**:
   ```
   E   AssertionError: assert 'valid' == 'not valid'
   FAILED ...TestTheHandOffs::test_the_expired_job_is_not_valid_and_has_no_claim[checkout]
   FAILED ...TestTheHandOffs::test_the_expired_job_is_not_valid_and_has_no_claim[terminal]
   ```
4. **The export's tax line differing from the invoice's tax** (Xero's
   spread over every line, i.e. bug fix #1 reverted). Red, **4 failed, 68
   passed**:
   ```
   E     {'parts': (9998, 224)} != {'parts': (9998, 625)}
   E     {'labor': (18000, 401)} != {'labor': (18000, 0)}
   FAILED ...TestTheMoney::test_xero_carries_each_line_and_the_tax_on_the_taxed_lines_only[checkout-A]
   ```
   and `[checkout-B]`, `[terminal-A]`, `[terminal-B]`.
5. **An invoice exported twice to the same target** (the export ignores
   what it carried). Red, **4 failed, 68 passed**:
   ```
   E     {'quickbooks_online': [1, 1, 2, 2]} != {'quickbooks_online': [1, 2]}
   E   AssertionError: Wrote 2 invoice(s), 8 row(s), to .../quickbooks-online-again.csv.
   E   assert 0 == 1
   FAILED ...TestTheHandOffs::test_the_export_carries_exactly_the_two_invoices[checkout]
   FAILED ...TestTheHandOffs::test_an_invoice_is_exported_once_per_target[checkout]
   ```
   and the same two for `[terminal]`.
6. **A build reference in what the walk prints** (F158; " (F188)" added to
   job A's reported problem, which the intake panel prints). Red, **2
   failed, 70 passed**:
   ```
   E   AssertionError: assert ['F188', 'F18...F188', 'F188'] == []
   FAILED ...TestNoBuildReferences::test_the_walk_prints_none[checkout]
   FAILED ...TestNoBuildReferences::test_the_walk_prints_none[terminal]
   ```

Each plant also stays as a permanent test, `TestThePlantsTurnTheGateRed`:
a planted walk on its own database must make the gate's own check raise.
With it the file is 80 tests.

### 2026-10-06 — Mutations: 15/15 red

`292_mutate.py`, 273's form (one exact string per mutation, `-B` after
clearing `__pycache__`, the file restored whatever happens): X1–X3 bug
fix #1; H1–H5 the hand-offs (check-in's link, the intake's, the claim's,
an ended warranty, the export's memory); M1–M3 the money (the estimate
billed, every line taxed, QuickBooks' tax line); P1–P4 payment (paid on
starting, paid at another amount, issued as a draft, cash left unpaid).
**15/15 red**; `git status src/` clean afterwards.

### 2026-10-06 — Floor

`--collect-only -q`: 10491. `COLLECTED_TEST_FLOOR` 10401 → 10491 (+90:
the gate's 80 and the fix's 10). 244G's scanner over `tests/`: 0.

### 2026-10-06 — `--full`, and the regression of record

**`--full` and Gate 16.** `wholetree.sh --full` on `c3fde4e` passed, 3988
tests in 86 files, the same count as at 273's merge. Gate 16 isn't a
whole-tree member at all: membership is computed from enumerating a repo
directory (`wholetree.py`'s docstring), and the gate walks a scratch
database. The regression of record is what runs it.

`.claude/skills/closeout/regression.sh` on a clean tree:

Regression of record: 10491 passed, 0 failed, 0 skipped, 0 errors at `c3fde4e` (22 min 7 s wall, `python -m pytest -n auto --dist load`, exit 0)

No refute pass ran.

### 2026-10-06 — Close-out

v1.1 written, no open boxes (`verify_phase.sh`'s result goes in the
handoff after the merge). The edit guard blocked a Python heredoc that
wrote v1.1 into the implementation document: its body named `src/` and
its write path was not a literal, which the guard blocks by design. The
sections were written with the Edit tool. Row 292 ✅, `**CLOSED 2026-10-06.**`, with the
regression line; history row and version header in `implementation.md`;
the documents moved to `completed/`; handoff
`docs/handoffs/2026-10-06_292_closed.md`. No deploy step: no migration and
no live row; the one production change (`accounting/export.py`) needs
nothing applied to the live database.
