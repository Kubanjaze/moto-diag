# Phase 275 — Track O batch 2: staff booking, iCal, QuickBooks and Xero export files

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-09-30 (v1.0 2026-09-29)

**Outcome (v1.1).** Shipped as planned, after one stop at Step 0:
- **The stop:** three forks (iCal file or feed; how a confirmation is
  sent; which QuickBooks file). The operator picked 1A, 2C, 3A and the
  default for Xero's header.
- **All four rows have commands, each exercised by a test.** Rows 276,
  277 and 278 close folded into 275; rows 363–366 are paused.
- **Migration 077 is live** at schema 77, and its live diff equals the
  approved exact diff; no existing row changed.
- **Neither export file was tried in a real QuickBooks or Xero company.**

No bug fix, no finding. Regression of record: 10179 passed, 0 failed at
`5dc9251`, re-run on the close-out commit (see Results). Deviations and
Results are at the end.

## Goal

Track O batch 2. Phase 275 carries rows 275, 276, 277 and 278, as 274
carried batch 1.

- **275, booking by shop staff:** book, move, confirm, check in, cancel
  and complete appointments; free time slots within the shop's hours; one
  mechanic per appointment, never double-booked.
- **276, iCal:** one calendar of appointments and bay slots, shown in the
  terminal and written as an `.ics` file the user imports (operator's 1A).
- **277, a QuickBooks Online journal-entry file:** each invoice as one
  balanced journal entry, to the shop's mapped accounts (operator's 3A).
- **278, a Xero sales-invoice file:** each invoice line as a row, with
  the mapped account, tax rate name, tax amount and currency.

Step 0 is `275_step0.md`; the vendors' pages are quoted in
`275_format_sources.md`. Every new capability has a `motodiag` command,
exercised by a test. No API route is added or changed, so gate 11 is
unaffected and no mobile session is needed. No outbound network call. The
export files are written locally; nothing is uploaded.

**The operator's pick (2026-09-29), verbatim:**

> 1A, 2C, 3A, and the default for 4. For 3A, the export command says
> plainly when it writes the file that these are journal entries: they
> carry no line items and don't reach QuickBooks' sales-tax reports. The
> log records that neither file was tried in a real QuickBooks or Xero
> company.

Paused, each on its own row: customer self-booking (363), Google
Calendar two-way sync (364), QuickBooks API sync and payment
reconciliation (365), Xero API sync (366).

## Logic

### Migration 077 (schema 76 → 77)

| change | what it holds |
|---|---|
| `appointments.shop_id` | the shop the appointment is at (`REFERENCES shops ON DELETE SET NULL`) |
| `appointments.work_order_id` | the work order its check-in opened or linked (`ON DELETE SET NULL`) |
| index `idx_appointments_shop_start` | `(shop_id, scheduled_start)` |
| `accounting_accounts` | per shop and target (`quickbooks_online`, `xero`), the account for each kind (`labor`, `parts`, `diagnostic`, `misc`, `tax`, `receivable`), and for Xero the tax rate's display name; unique per (shop, target, kind) |
| `accounting_exports` | one row per file written: shop, target, range, file name, its sha256, invoice count, when |
| `accounting_export_invoices` | which invoices each export carried; unique per (export, invoice) |

Live holds 0 appointments, so the two columns change no row. The rollback
drops the new tables and the index, then the two columns. The dry run must
show additions to `schema_version` only, and the schema objects the scope
names.

### Row 275: booking by shop staff

New `scheduling/booking.py` over `appointment_repo`; `Appointment` and
`create_appointment` carry `shop_id` and `work_order_id`. Commands under
`motodiag shop appointment`:
- `book --shop S --customer C --bike B --start WHEN (--end WHEN |
  --minutes N) [--type …] [--mechanic U] [--notes]`. Refused: an end not
  after the start; a bike not linked to the customer (`shop customer
  link-bike` first); a mechanic who is not an active member of the shop;
  a mechanic who already has an active appointment overlapping it.
  Booked with a printed warning when it overlaps a bay slot of a work
  order assigned to the same mechanic.
- `list --shop S [--from D --to D] [--mechanic U] [--status …] [--json]`,
  `show ID`.
- `slots --shop S --date D --minutes N [--mechanic U] [--open HH:MM
  --close HH:MM]`: free start times on that day, every 15 minutes, within
  the shop's hours for that weekday, clear of the mechanic's appointments
  (or, with no mechanic, listed per active member). Hours come from
  `hours_json` (`{"mon": "08:00-17:00", …}`; a day missing or `"closed"`
  is closed). With no hours recorded for that day, it says so and needs
  `--open`/`--close`; nothing is assumed.
- `reschedule ID --start WHEN (--end | --minutes)`, the same checks.
- `confirm ID --channel phone|sms|email|in_person [--by U]` (operator's
  2C): prints the confirmation text (shop, day and time, bike, mechanic,
  the shop's address and phone) for staff to send by their own means,
  sets the status to `confirmed`, and records an outbound contact with the
  text in `customer_communications`. Nothing is queued or sent.
- `check-in ID [--wo W]`: with `--wo`, links that work order (it must be
  the same customer, bike and shop); without, creates one from the
  appointment (title from the type and notes, mechanic assigned) and opens
  it. The appointment moves to `in_progress` and keeps the link.
- `cancel ID [--reason]`, `no-show ID`, `complete ID`.
- Status moves: scheduled → confirmed; scheduled or confirmed →
  in_progress (check-in), cancelled, no_show; in_progress → completed.
  Anything else is refused with the current status named.

**Times.** The shop records no time zone. Appointment times are the
shop's clock time as entered (`YYYY-MM-DDTHH:MM`, no offset). Bay slots
store an offset: the bay scheduler reads a naive entry as UTC and writes
`+00:00`. So a slot with `+00:00` is read as the clock time it was entered
at; a slot with any other offset is converted to UTC. This is the one rule
the calendar and the overlap check use.

### Row 276: the calendar, and iCal

New `scheduling/calendar.py`:
- `calendar_entries(shop, from, to, mechanic=None, bay=None)`: the
  range's appointments and bay slots, read live, each entry from one row,
  sorted by start. A bay slot shows its bay, its work order and that work
  order's mechanic; an appointment its customer, bike, type, status and
  mechanic. `--mechanic` keeps that mechanic's appointments and the slots
  of their work orders; `--bay` keeps that bay's slots.
- `to_ics(entries, shop)`: RFC 5545. `VCALENDAR` with `VERSION:2.0`,
  `PRODID`, `CALSCALE:GREGORIAN`, `METHOD:PUBLISH`; one `VEVENT` per entry
  with `UID` (`appointment-<id>@motodiag-shop-<shop>`,
  `bay-slot-<id>@motodiag-shop-<shop>`), `DTSTAMP` in UTC, `DTSTART` and
  `DTEND` (clock time without zone, or UTC with `Z`, by the rule above),
  `SUMMARY`, `DESCRIPTION`, `LOCATION` (the shop, or the bay), and
  `STATUS` (`CONFIRMED`, `TENTATIVE` for scheduled and planned,
  `CANCELLED`). Text is escaped (`\\`, `;`, `,`, newlines); lines end in
  CRLF and fold at 75 octets.
- Commands, `motodiag shop calendar`: `show --shop S --from D --to D
  [--mechanic U | --bay B]` and `export … --out FILE.ics`. Cancelled
  entries are written as `STATUS:CANCELLED`, so a re-import updates them.

### Rows 277 and 278: the export files

New `accounting/export.py`, over `invoices` and `invoice_line_items`
(`shop/invoicing.py` builds them). Commands under `motodiag shop
accounting`:
- `map set --shop S --target quickbooks-online|xero --kind K --account
  NAME [--tax-type NAME]`, `map list --shop S [--target]`.
- `export --shop S --target … --from D --to D --out FILE
  [--include-exported]`.

Common rules:
- **Which invoices:** the shop's (through their work order), issued in the
  range, not cancelled. An invoice already carried by an export to the
  same target is left out and named, unless `--include-exported`.
- **Refusals:** a missing mapping for a kind the invoices use (named, with
  the `map set` to run); no invoice in range. No account is invented.
- **Line kinds:** `labor`, `parts`, `diagnostic`, `misc` (shown to the
  user as shop supplies), and the invoice's tax.
- Every export is recorded (`accounting_exports`, with the file's sha256)
  and prints what it wrote.

**QuickBooks Online (277), journal entries** (Intuit's journal-entry
import page):
- Columns, as the page names them: `Journal No.`, `Journal Date`,
  `Account Name`, `Debits`, `Credits`, `Journal/Description`, and `Name`
  (asked for on an Accounts Receivable line).
- Per invoice: `Journal No.` the invoice number; one debit line to the
  mapped receivable account for the invoice total, `Name` the customer;
  one credit line per line kind present, the sum of that kind's lines, to
  its mapped income account; one credit line for the tax, to the mapped
  liability account, when the tax is not zero. Debits equal credits, to
  the cent, for every entry, or the export refuses.
- Dates `MM/DD/YYYY` (the page states none; the import lets the user pick
  the format, and the command says which it used).
- **Said plainly when the file is written** (the operator's wording): the
  file holds journal entries, not invoices; they carry no line items and
  do not reach QuickBooks' sales-tax reports.

**Xero (278), sales invoices** (Xero's "Import customer invoices" page):
- Columns: the names the page gives, plus `Description` and `Quantity`,
  which it does not (see the log). No address columns.
- One row per invoice line; the invoice number repeated on each row.
- `ContactName` the customer's name; `EmailAddress` theirs.
- `UnitAmount` tax-exclusive; `AccountCode` and `TaxType` from the
  mapping (Xero needs a `tax-type` on every mapped kind, else refused).
- `TaxAmount`: the invoice's tax spread over its lines in proportion to
  their amounts, the rounding remainder on the last line, so the lines sum
  to the invoice's tax exactly. The page says to add this column when the
  tax must be exact, with prices tax-exclusive.
- Dates `MM/DD/YYYY` (the page's rule). `DueDate` blank when not recorded.
- `Currency` the invoice's own.
- The command says the file's prices are tax-exclusive, which the import
  screen asks for.

### Wiring, the allowlist, the docstrings

- `motodiag.scheduling` and its two modules leave `MODULE_ISLANDS` (or
  wherever the gate lists them); whatever becomes a live orphan is listed
  with its reason; the pinned counts move with their history lines.
- `scheduling/__init__.py` and `accounting/__init__.py` lose their stale
  Track O numbers.
- New user-facing text carries no internal reference (F158).

## Decisions

- **D1.** 1A, 2C, 3A and the default for 4: the operator's pick.
- **D2.** Appointments and bay slots stay separate facts, linked by the
  work order; the calendar reads both live (S0-3).
- **D3.** Double-booking a mechanic is refused; an overlap with their bay
  work is a warning.
- **D4.** Slots come only from recorded hours or `--open`/`--close`.
- **D5.** One time rule for appointments and slots (above), since the shop
  has no time zone.
- **D6.** A confirmation is a logged contact, not a notification (2C).
- **D7.** The account mapping is the shop's own names; never defaulted.
- **D8.** Tax is spread across Xero lines so the file's tax equals the
  invoice's.
- **D9.** Exports are recorded so an invoice is not posted twice by
  accident.
- **D10.** The Xero header departs from Step 0's list where that list was
  wrong (the log).
- **D11.** No refute pass: code, schema and tests; no content rows.
- **D12.** The live deploy changes no existing row; if the dry run shows
  otherwise, that is a rule-1 stop.

## Non-goals

- Customer self-booking; any endpoint a customer or service reaches.
- A calendar feed or route; Google Calendar.
- Uploading to QuickBooks or Xero; payment reconciliation; QuickBooks
  Online's invoice import; Desktop IIF.
- A new notification event; any API change.
- Currency conversion (row 289).
- F158's remaining references outside the groups this batch edits.

## Planned items

1. This v1.0, and rows 275–278 rewritten, committed and pushed before
   code.
2. Migration 077 and its test (`tests/test_phase275_migration.py`): the
   columns, tables, rollback, a planted existing row unchanged; the head
   pinned only as `>= 77` and `== max(MIGRATIONS)`. `wholetree.sh --full`
   before its commit.
3. Row 275, `tests/test_phase275_booking.py`.
4. Row 276, `tests/test_phase275_calendar.py`.
5. Rows 277 and 278, `tests/test_phase275_accounting_export.py`,
   pinning each file's columns against the source file's list.
6. The allowlist and its pins; the docstrings.
7. Mutations, `275_mutate.py`, each seen red.
8. 244G's scanner over the new tests; `wholetree.sh --full`; the
   regression of record by `regression.sh`; `COLLECTED_TEST_FLOOR` raised.
9. The deploy: scope, dry run and its committed diff, `apply-live`.
10. Close-out: v1.1; rows 276–278 ✅ folded into 275; row 275 ✅ with its
    CLOSED date; the fold pin; the regression again on the close-out
    commit; the history row; the handoff; `verify_phase.sh`.

## Verification Checklist

- [x] v1.0 committed and pushed before code (`65bf479`)
- [x] Migration 077: columns, tables, rollback; no existing row changed (`test_phase275_migration.py`; the dry run)
- [x] Every new capability reached through a `motodiag` command in a test
- [x] Double-booking refused; bay overlap warned; slots never assume hours
- [x] Confirm logs a contact and queues nothing
- [x] Check-in opens or links a work order, and the calendar shows both
- [x] The `.ics` is valid RFC 5545 (CRLF, folding, escaping, UID, DTSTAMP), read back by the test's own unfolder
- [x] QuickBooks entries balance; the plain statement is printed
- [x] Xero tax lines sum to the invoice's tax; columns pinned against `275_format_sources.md`
- [x] A missing mapping refuses; a re-export skips exported invoices
- [x] Mutations all red (28/28)
- [x] 244G scanner; `wholetree.sh --full`; regression of record; floor raised (10109 → 10179)
- [x] Dry-run diff committed (`aeda0c0`); apply-live equals it
- [x] Handoff; `verify_phase.sh` (its result is in the handoff)

## Deviations from Plan

- **Step 0's list of Xero columns was wrong in three names.** It said
  the page names `Reference`, `Description` and `Quantity`; counted in the
  page's text, it names none of them. The file uses the page's names plus
  `Description` and `Quantity`, flagged in the code, the sources file and
  the test; `Reference` and the address fields are left out. This departs
  from the default as worded, because the list it was worded on was wrong.
- **A confirmed appointment can be confirmed again.** v1.0's status moves
  had scheduled → confirmed only; a second confirmation logs another
  contact and leaves the status `confirmed`.
- **`shop accounting exports` was added** so the export record has a
  reader; both writers refuse to overwrite an existing file.
- **No iCal library:** none is installed and none was added; the test
  unfolds and parses the file itself.
- **One test expectation was wrong on first writing** (a receivable
  total), not the code.
- **The regression of record was run again on the close-out commit**,
  because the close-out changed a test (the fold pin).
- **The deploy ran before the merge**, on the phase branch, as 274's did.
- The collected-test floor was measured against a `master` worktree whose
  run imports this checkout's `src` (the editable install); gate 15's
  `[76]` case therefore appears in both lists, and is counted in the +70.
- **The edit guard blocked one close-out command** that chained a Python
  edit with `sed -i` on the phase log; nothing in it ran, and it was
  redone with the Edit tool. The guard was right: `sed -i` is blocked
  wherever it points.

## Results

| | |
|---|---|
| Migration | 077: `appointments.shop_id`, `work_order_id`, two indexes, three tables; schema 76 → 77; no row changed |
| 275 booking | `shop appointment book/list/show/slots/reschedule/confirm/check-in/cancel/no-show/complete`; `test_phase275_booking.py` 26 |
| 276 calendar | `shop calendar show/export`; `test_phase275_calendar.py` 13 |
| 277, 278 files | `shop accounting map set/list`, `export`, `exports`; `test_phase275_accounting_export.py` 19 |
| Migration tests | `test_phase275_migration.py` 9 |
| Allowlist | UNREACHABLE 32 → 29, ORPHANS 112 → 118 |
| Mutations | 28/28 red (`275_mutate.py`) |
| Whole tree | `--full` at `5dc9251`: 3982 passed |
| Regression | 10179 passed, 0 failed, 0 skipped at `5dc9251` (30 min 38 s), `-n auto --dist load`; and at `aa617c9`, the close-out commit (18 min 55 s) |
| Floor | `COLLECTED_TEST_FLOOR` 10109 → 10179 |
| Deploy | dry run committed `aeda0c0`; apply-live `[77]`; live 5846 → 5847 rows, 98 → 101 tables, integrity ok; equals the approved exact diff; F158 census 36 |
| Findings | none filed |
| Ledger | 275 ✅; 276, 277, 278 ✅ folded; rows 275–278 rewritten; 363–366 ⏸️ |
