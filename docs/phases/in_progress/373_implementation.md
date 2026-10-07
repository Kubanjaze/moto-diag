# Phase 373 — Warranty work on the invoice (F188)

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-10-06

---

## Goal

Row 373: "Decide which lines a claim covers, derive the claimed amount
from the work order's labour and parts, and leave claimed lines off what
the customer owes." It closes F188: a warranty claim and the invoice for
the same work order do not know about each other, so covered work is
invoiced to the customer in full and the claim's amount is typed by hand.

The operator's choices at Step 0 (verbatim in the phase log):
1. **Staff choose the lines** a claim covers (1a), after the work.
2. **The customer is invoiced the uncovered lines now**, and the claim
   runs separately (2a). A denied or part-approved claim is settled by the
   shop each time (`claim settle`): bill the customer for the shortfall,
   or absorb it. Void and regenerate are tested unchanged; a second
   invoice on a work order is allowed only for a settled claim's
   shortfall.
3. **Tax on covered parts is keyed on who owes the repair** (T2 as
   amended, option (b)):
   - a maker's warranty included in the bike's price: no tax, nothing on
     the claim (LR 03-8);
   - someone else's plan or contract: the covered parts are taxed and the
     tax is added to the claim (LR 79-19, LR 85-1);
   - a contract this shop sold: the shop bears the tax as the consumer,
     nothing on the claim (830 CMR 64H.1.1(5)(g)).
   The warranty records which. Stored as the jurisdiction's rule with its
   sources. **A reading, to be confirmed by the shop's accountant before a
   real warranty job.**
4. **Deductibles: a new row**, 375.
5. **The claim is exported as a receivable** from the provider, in
   QuickBooks and Xero (5a).
6. **Command line only.** No API model changes, so no mobile stop (S0-2
   item 6).

## Logic

### Migration 081 (schema 80 → 81): new tables and columns only

- `warranties.repair_payer`: `maker_with_bike`, `other` or
  `shop_contract`; NULL when not recorded.
- `warranty_claims` gains: `coverage_recorded_at`, `invoice_id`,
  `covered_cents`, `tax_cents`, `tax_source`, `settlement`
  (`bill_customer` or `absorb`), `settled_at`, `shortfall_cents`,
  `shortfall_invoice_id`. Every amount is an integer of cents.
- `warranty_claim_lines`: one row per covered line: the claim, the line
  type (`labor` or `parts`), the work order's part row (parts only), the
  quantity (hours for labour, a count for parts) and `amount_cents` (NULL
  until the invoice prices it).
- `invoices.shortfall_claim_id`: set only on a shortfall invoice.
- `tax_warranty_rules`: the shape of 281's `tax_line_rules`, keyed on
  `payer` instead of a line type, with `taxed_on_claim` (0 or 1), basis,
  validity, source and provenance. Three regulation rows for `US-MA`,
  checked 2026-10-06, valid 12 months (281's rule), each citing its source
  and clause in `373_sources.md`:
  - `maker_with_bike`: 0, `stated` (LR 03-8);
  - `other`: 1, `reading` (LR 79-19 and LR 85-1; the reading that the
    tax goes on the claim);
  - `shop_contract`: 0, `stated` (830 CMR 64H.1.1(5)(g)).
- `accounting_export_claims`: which export carried which claim.

Live holds 0 warranties, 0 claims and 0 invoices, so no existing row
changes. Through the deploy skill.

### Who owes the repair

`shop warranty add --payer {maker_with_bike,other,shop_contract}`, and
`shop warranty set-payer WARRANTY --payer …` for one already recorded.
`warranty list` and the packet show it.

### Covering lines: `shop warranty claim cover`

`shop warranty claim cover CLAIM [--labour-hours H] [--part PART_ROW[=QTY]]… | --none`

- The claim must be a draft on a work order, and the work order must have
  no live invoice. Covering again replaces the claim's lines.
- A part row must be on the claim's work order and not cancelled; its
  covered quantity across every claim on the order is at most its
  quantity. Covered labour hours across the order's claims are at most the
  order's hours (actual, else estimated), when known.
- Covering any line needs the warranty's payer on record; refused
  otherwise, naming `set-payer`.
- `--none` records that the claim covers nothing.
- `claim open --claimed-cents` is removed (S0-6 D2).

### The invoice: `generate_invoice_for_wo`

- A claim on the order that is not denied and has no coverage recorded
  stops the invoice, naming `claim cover`. Covered work is never invoiced
  to the customer without anyone deciding so.
- The covered hours and quantities come off the customer's lines: a
  labour line for the remaining hours, a parts line for each remaining
  quantity. The invoice's notes name the claim and what it covers.
- The claim's lines are priced at the same rate and part prices, in the
  invoice's currency, in integer cents. The claim's tax comes from
  `tax_warranty_rules` for the warranty's payer on the invoice date: when
  `taxed_on_claim`, the rate times the covered lines of the types the
  jurisdiction taxes, rounded half up; else 0. A jurisdiction with no rule
  for the payer refuses the invoice (`TaxNotOnRecord`, naming `shop tax
  warranty-rule set`), as 281 refuses an unknown line type.
- The claim records `invoice_id`, `covered_cents`, `tax_cents`,
  `tax_source` and `amount_claimed_cents` = covered + tax.
- An invoice with nothing left for the customer is issued with no lines,
  total 0, and paid at issue.
- Regenerating after a void prices the claim again; it is refused if a
  claim past draft would change amount.
- `shop tax warranty-rule set` records a shop's own rule; `shop tax
  confirm` re-checks warranty rules with the rest; `shop tax status` lists
  them.

### The claim's decision and settlement

- `claim status --to approved --approved-cents N` is refused when N is
  more than the amount claimed.
- `shop warranty claim settle CLAIM --bill-customer | --absorb`, once, for
  a claim invoiced and then denied, or approved or paid for less than
  claimed. The shortfall is claimed − approved (0 approved when denied).
  - **absorb:** recorded on the claim.
  - **bill the customer:** a shortfall invoice to the work order's
    customer, `shortfall_claim_id` set. Its lines are the claim's lines in
    proportion: the pre-tax shortfall is all of `covered_cents` when
    denied, else `covered_cents` × shortfall ÷ claimed, rounded half up,
    split over the lines by amount (largest remainder). Its tax is the
    customer's, from 281's rules on the day. The one-invoice-per-order
    rule ignores shortfall invoices, and only `settle` writes one.

### The packet

`render_claim_packet` lists the covered lines with their cents, the tax on
the claim and its source, and the amount claimed; before the invoice it
says the lines are priced when the invoice is generated.

### The export

- **QuickBooks:** for each exported invoice with a claim carrying an
  amount, one more journal entry, `<invoice number>-W<claim id>`: debit
  the receivable account for the amount claimed, in the provider's name;
  credit labour and parts income for the covered lines, and sales tax for
  the claim's tax. Refused unless it balances to the cent.
- **Xero:** a sales invoice to the provider, `<invoice number>-W<claim
  id>`, one row per covered line, the claim's tax on its taxed lines.
- A claim needs its warranty's provider on record to be exported.
- An invoice with no lines and total 0 is recorded as exported and writes
  no row.
- Shortfall invoices are left out, and the export says how many (F190,
  row 376).

### Gate 16, inverted

Job A's warranty gets `--payer other` (a maker's plan, 79-19's facts).
After the repair, `claim cover` covers 1.0 h and the two pads; 0.5 h
stays the customer's. Then the claim is submitted, approved at the amount
claimed, and paid. `KNOWN` and the money tests follow, in cents:
- customer: labour 6000, no parts, tax 0, total 6000; Stripe asked 6000;
- claim: labour 12000 + parts 9998 = 21998 covered, tax 625, claimed
  22623, approved 22623;
- QuickBooks: A/R 60.00 (Dana Rider), labour 60.00; claim A/R 226.23
  (Honda Protection Plan), labour 120.00, parts 99.98, tax 6.25;
- Xero: the customer's labour 6000 (tax 0); the provider's labour 12000
  (tax 0) and parts 9998 (tax 625).
`test_f188_…` becomes the inverted test: the claimed amount derived, the
covered lines off the customer's invoice, the packet listing them, and
the export carrying the claim.

## Decisions

S0-6 D1–D5 in `373_step0.md`, and:
- **D6. The provider is a name on an ordinary A/R line in QuickBooks**,
  not a new account kind; that is how QuickBooks books what a third party
  owes, and it needs no rebuild of `accounting_accounts` (whose `kind` has
  a CHECK).
- **D7. Settlements are not exported** (F190, row 376): the shortfall
  invoice exported as an ordinary invoice would count the covered work's
  revenue twice, and the right entries differ by target (a journal; a
  Xero credit note, a different import file).
- **D8. A claim denied before its invoice** is ignored by the invoice
  (its lines go to the customer) and cannot be settled.

## Non-goals

Submitting a claim anywhere (362, paused); deductibles (375); settlements
in the export (376); payment reconciliation (365, paused); any API route.

## Planned items

- [ ] Migration 081, its rollback and a migration test
- [ ] `warranty add --payer`, `warranty set-payer`
- [ ] `claim cover`, and `--claimed-cents` removed
- [ ] the invoice: coverage required, covered lines off, the claim priced and taxed
- [ ] `tax_warranty_rules`, `shop tax warranty-rule set`, `confirm` and `status`
- [ ] `claim settle`, the shortfall invoice, void and regenerate unchanged
- [ ] the packet
- [ ] the export: the claim as a receivable in both files; shortfall invoices left out
- [ ] Gate 16 inverted; 274's claim tests moved off `--claimed-cents`
- [ ] tests for each, a mutation file, the deploy, the regression, the close-out
