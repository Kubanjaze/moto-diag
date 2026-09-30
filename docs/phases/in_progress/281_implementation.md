# Phase 281 — Track O batch 3: recalls, VIN decoding, tax rates and exchange rates

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-09-30

## Goal

Track O batch 3. Phase 281 carries rows 281, 287, 288 and 289, as 275
carried batch 2. They are the first calls to public data services.

- **281, recalls from NHTSA:** refresh a make, model and year (or a bike,
  a VIN, or every garage bike) from NHTSA's recall service; look recalls
  up with the date they were fetched; track completion per bike.
- **287, VIN decoding by vPIC:** decode a VIN to make, model, model year
  and vehicle type, stored per VIN; the offline maker-and-year decode as
  the labelled fallback.
- **288, sales tax by jurisdiction:** a shop is in a jurisdiction; rates
  and line-type rules are stored per jurisdiction with effective date,
  valid-until date and source; Massachusetts ships verified from the
  DOR's text; every other shop enters its own; invoices take their tax
  only from the record, are refused without it, and record what they used
  (F184).
- **289, exchange rates:** the ECB's daily reference rates for
  conversions shown to the user; a shop's own rates for invoicing in
  another currency; every conversion prints its rate, date and source.

Step 0 is `281_step0.md`; the sources are quoted in `281_sources.md`.

**The operator's pick (2026-09-30), verbatim:**

> 1: A. Also file a finding: with the field gone, a tax-exempt sale (a resale or exempt-organization certificate, for example a town's police bikes) can't be invoiced. It waits until a real shop needs it.
> 2(a): 12 months, as proposed, and every invoice and `tax status` print the date the rate must be re-checked by.
> 2(b): through the 5th calendar day, not the 4th. After Easter the next ECB rate comes out Tuesday at 16:00 CET, which is Tuesday morning in Massachusetts and the 5th day after Thursday's rate.
> 3: A.
> 4: no route, as the default.
> The diagnostic-fee rule is the build's own reading, not a stated rule. Ship it with that said in its source, so `tax status` shows it as a reading of 64H.1.1(2)(a)1.

F185 is filed for the tax-exempt sale. Paused: recall reimbursement
claims (367) and automatic rates for every address (368).

Every new capability has a `motodiag` command, exercised by a test. No
route is added. One API model changes (below), so gate 11 goes red until
the mobile snapshot is refreshed: a planned stop.

## The API change (for the mobile session)

| schema | field | before | after |
|---|---|---|---|
| `InvoiceGenerateRequest` | `tax_rate` | `number`, 0 to 1, default 0 | **removed** |

`POST /v1/shop/{shop_id}/invoices/generate` then computes tax from the
shop's jurisdiction on record, exactly as the CLI does, and answers 409
when the shop has no jurisdiction, no rate valid on the invoice date, or
no rule for a line type the invoice carries, naming what is missing. The
request's other fields and every response are unchanged in the OpenAPI
document (the route returns an untyped `dict`, so the invoice's new tax
fields do not appear in the schema). The app does not call this route;
its generated types lose the field. The mobile session also closes F103
in the mobile file (S0-2).

## Logic

### The outbound client — `core/outbound.py`

- `fetch(service, url, *, expect)` with `expect` in `json`, `xml`:
  `urllib.request`, User-Agent `motodiag/<version> (+https://github.com/Kubanjaze/moto-diag)`,
  timeout 20 s, one request, no retry.
- Returns a `Response` (status, body bytes, URL, fetched-at UTC). Raises
  `ServiceUnavailable(service, kind, detail)`; `kind` is `unreachable`
  (DNS, refused, timeout), `blocked` (403, or an HTML body where JSON or
  XML was expected), `error` (any other non-2xx the caller does not
  accept), or `malformed` (a body that does not parse).
- A caller may accept a named non-2xx status with a parseable body (the
  recall service's 400 with `{"Count":0}`).
- `str(ServiceUnavailable)` names the service ("NHTSA recalls", "NHTSA
  vPIC", "ECB reference rates") and never an internal reference.
- The transport is one function (`_open`) so tests swap it for a
  recorded fixture.

### The network guard (tests)

`tests/support/network_guard.py`, installed by `tests/conftest.py` at
import: `socket.socket.connect`, `connect_ex`, `socket.create_connection`
and `socket.getaddrinfo` refuse any address that is not loopback
(`127.0.0.0/8`, `::1`, `localhost`) or a Unix socket, raising
`NetworkBlockedInTests` naming the host. Its test runs a planted
known-bad test (a `urlopen` of a public host, written to `tmp_path`) in a
pytest subprocess with the guard loaded, and requires it to fail with the
guard's message; and a loopback connection to pass.

### Migration 078 (schema 77 → 78)

| change | what it holds |
|---|---|
| `tax_jurisdictions` | `code` (unique, e.g. `US-MA`), `name`, `currency` (3 letters) |
| `shop_tax_jurisdictions` | `shop_id` (primary key), `jurisdiction_id`, who set it, when. Not a column on `shops` |
| `tax_rates` | jurisdiction, `shop_id` (NULL for a regulation row, the shop for its own), `rate` (0 ≤ r < 1), `effective_from`, `valid_until`, `source_title`, `source_url`, `checked_on`, `provenance` (`regulation` or `shop`; `regulation` exactly when `shop_id` is NULL), who entered it, when |
| `tax_line_rules` | as `tax_rates`, with `line_type` (`labor`, `parts`, `diagnostic`, `misc`), `taxable` (0/1), `basis` (`stated` or `reading`: stated by the source, or the build's reading of it) and `source_clause` |
| `exchange_rates` | `base`, `quote`, `rate` (> 0), `rate_date`, `valid_until`, `source` (`ecb` or `shop`), `shop_id` (NULL for ECB), `source_url`, `source_note`, who entered it, `fetched_at`; ECB rows unique per (base, quote, rate_date) |
| `recall_fetches` | the make, model and year asked, when, the URL, the HTTP status, the result count, `outcome` (`ok`, `failed`), the error |
| `recall_vehicles` | `recall_id`, make, model, model year, as NHTSA lists them; unique per (recall, make, model, year) |
| `vin_decodes` | `vin` (primary key), make, model, model year, manufacturer, vehicle type, vPIC's error code and text, the response, the URL, when |
| `recalls` + columns | `source` (`nhtsa` for fetched; NULL for rows as before), `fetched_at`, `component`, `consequence` |
| `invoices` + columns | `tax_rate`, `tax_rate_id`, `tax_source`, `tax_recheck_by`, `taxed_line_types`, `fx_from_currency`, `fx_rate`, `fx_rate_id`, `fx_rate_date`, `fx_source` |
| rows inserted | `US-MA` (Massachusetts, USD); its rate; its three line rules |

**Massachusetts's rows:**
- rate 0.0625, effective 2009-08-01, checked 2026-09-30, valid until
  2027-09-30 (the operator's 12 months from the check); source the DOR's
  "Sales and Use Tax" guide and TIR 09-11, with their URLs;
- parts: taxable, `stated`, 830 CMR 64H.1.1(2)(b)1 and (5)(a);
- labour: not taxable, `stated`, 64H.1.1(2)(a)1 and (5)(a), and the
  guide's "Car repairs";
- diagnostic: not taxable, **`reading`**, "a reading of 830 CMR
  64H.1.1(2)(a)1: a service with no transfer of property; the regulation
  does not name a diagnostic fee";
- shop supplies: no row.

Live holds 0 recalls and 0 invoices, so the new columns change no row.
Rollback drops the new tables and the new columns.

### Row 288: tax — `accounting/tax.py`

- `resolve_tax(shop_id, on_date, line_types)` → a `TaxDecision` (rate,
  rate row, source text, recheck-by date, taxable line types, each rule's
  basis), or raises `TaxNotOnRecord` naming each thing missing and the
  command that records it. For each item, the shop's own valid row wins
  over the regulation row; "valid" means `effective_from ≤ on_date ≤
  valid_until`.
- `tax_status(shop_id, today)`: every current rate and rule with its
  source, basis and recheck-by date, and the failures (past validity,
  missing). It fails (the command exits 1) on any failure.
- `REGULATION_RECHECK_MONTHS = 12`: `confirm` sets a regulation row's
  `valid_until` 12 months after the new check date, by inserting new rows
  (the old ones stay as history).
- Commands, `motodiag shop tax`:
  - `jurisdiction add --code --name --currency`, `jurisdiction list`;
  - `jurisdiction set --shop S --code C` (which one the shop is in);
  - `rate set --shop S --rate R --effective D --valid-until D --source-title T [--source-url U] --checked-on D` (the shop's own rate for its jurisdiction; all but the URL required);
  - `rule set --shop S --line-type L (--taxable | --not-taxable) --effective --valid-until --source-title [--source-url] [--clause] --checked-on [--reading]`;
  - `confirm --jurisdiction C --checked-on D --source-url U` (a regulation re-check);
  - `status --shop S` (prints every item's recheck-by date; exit 1 on a failure).
- Rates are entered as percentages on the command line (`6.25`) and stored
  as fractions; the command echoes both.

**Invoices** (`shop/invoicing.py`):
- `generate_invoice_for_wo` loses `tax_rate`. Before writing anything it
  works out the line types the invoice will carry and calls
  `resolve_tax(shop, invoice date, types)`; `TaxNotOnRecord` becomes
  `InvoiceGenerationError` with the same message, so nothing is written.
- Tax is the rate times the sum of the **taxable** lines, rounded to the
  cent. The invoice records `tax_rate`, `tax_rate_id`, `tax_source`,
  `tax_recheck_by` and `taxed_line_types`.
- The invoice's currency is the jurisdiction's. `currency=` another one:
  every amount is converted at the shop's own rate from its currency
  (question 3A), valid on the invoice date, and the invoice records it
  (`fx_*`); with no such rate, refused naming `shop currency set`.
- `shop invoice generate` loses `--tax-rate` and gains `--currency`; it
  and `shop invoice show` print the rate, its source, the taxed line
  types, and "rate must be re-checked by D"; a converted invoice prints
  its rate, date and source.
- The API route drops `tax_rate` and maps `InvoiceGenerationError` from a
  tax refusal to 409.
- `InvoiceSummary` gains the tax and conversion fields, so `--json` and
  the API's response carry them.

### Row 289: exchange rates — `accounting/exchange.py`

- `refresh_ecb()`: fetches `https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml`,
  parses the one `Cube time=…` and its `Cube currency= rate=` entries,
  stores EUR→X rows with `valid_until = rate_date + 5 days` (the
  operator's 2(b): through the 5th calendar day), and returns what it
  stored. A rate date already stored is not duplicated.
- `convert(amount, from, to, on_date, shop_id=None)`: the shop's own
  valid rate for that pair if `shop_id` is given and one exists, else the
  ECB's: direct from EUR, the inverse to EUR, or a **cross rate through
  the euro** from two ECB rates of the same date, labelled so. Returns the
  result, the rate, its date, its source and whether it is a cross or an
  inverse. No valid rate: refused naming the refresh or set command.
- Commands, `motodiag shop currency`: `refresh`, `rates [--base]`,
  `set --shop S --from A --to B --rate R --rate-date D --valid-until D
  --source TEXT`, `convert AMOUNT FROM TO [--shop S]`. Every ECB-based
  output prints: "ECB reference rate, published for information purposes
  only."
- ECB down: says so, names the service, and lists the stored rates with
  their dates.

### Row 281: recalls — `advanced/recall_repo.py` and `advanced/nhtsa.py`

`advanced/nhtsa.py` holds the two clients:
- `fetch_recalls(make, model, year)`: `https://api.nhtsa.gov/recalls/recallsByVehicle?make=…&model=…&modelYear=…`.
  200 with results, or **400 with a body that parses as `{"Count": 0,
  "results": []}`**, are answers; anything else raises
  `ServiceUnavailable`. A 200 whose `Count` disagrees with its results is
  `malformed`.
- `decode_vin_vpic(vin, year)`: `https://vpic.nhtsa.dot.gov/api/vehicles/DecodeVinValues/{vin}?format=json[&modelyear=Y]`.

`advanced/recall_repo.py` gains:
- `refresh_recalls(make, model, year)`: fetches; on success upserts each
  campaign into `recalls` (`campaign_number` and `nhtsa_id` the campaign;
  `source='nhtsa'`; summary, remedy, component, consequence, report date
  as ISO; severity `critical` when `parkIt` or `parkOutSide`, else
  `unrated`), adds `recall_vehicles` rows, and records the fetch. On
  failure it records a failed fetch and changes nothing else.
- `recall_state(make, model, year)`: the latest successful fetch for that
  name (compared upper-case, spaces and hyphens removed), and the stored
  campaigns covering it.
- The existing lookups read fetched campaigns through `recall_vehicles`
  (make, normalised model, year) and older rows by their own make, model
  and year, as before: `inventory.recall_repo.list_recalls_for_vehicle`
  (under `check_vin` and `lookup`) and `list_open_for_bike` (under the
  predictor). A fetched row's NULL model and years never match a whole
  make.
- `refresh_all_bikes()`: the F103 check first (PIAGGIO, MP3 500, 2020
  must return 20V524000, or the run stops), then each garage bike with a
  make, model and year, one at a time with a 1-second pause; returns
  refreshed and failed bikes. Any failure: exit 1, the failed bikes
  listed, their stored data unchanged.

Commands, `motodiag advanced recall`:
- `refresh (--make M --model N --year Y | --bike SLUG | --vin VIN | --all-bikes)`.
  `--vin` decodes with vPIC first (stored or fetched).
- `check-vin VIN [--refresh]`, `lookup`: the four answers of S0-5: found
  (each "may apply; whether this VIN is included, check nhtsa.gov/recalls
  or the maker"), none as named (never "Clear"; "this is not an
  all-clear"), never fetched (with the refresh command), service down
  (the failure, then what is stored). `check-vin` uses the stored vPIC
  decode for its model; without one it says the model is unknown and
  names `advanced vin decode`.
- `list --bike SLUG`: that bike's open and resolved recalls.
- The recall table shows `unrated` as "not rated by NHTSA" and the date
  each campaign was fetched.

### Row 287: VIN decoding

- `advanced/recall_repo.py`: `decode_vin_online(vin, refresh=False)`
  returns the stored decode or fetches, stores and returns it; with vPIC
  down it raises, and the command then prints the offline decode labelled
  "offline: maker and year only".
- `motodiag advanced vin decode VIN [--refresh] [--bike SLUG --save]`:
  prints make, model, year, manufacturer, vehicle type, vPIC's error code
  and text when it reports one (non-zero is labelled partial), and the
  date. `--save` writes the VIN to the bike only when it has none, never
  changes its make, model or year, and prints any disagreement.

### Wiring and text

- New modules reachable from commands; the integration-gap allowlist and
  its pinned counts move with their history lines.
- No internal reference in any user-facing text (F158).

## Decisions

- **D1.** The operator's pick: 1A, 2(a) 12 months with the recheck-by
  date printed, 2(b) 5 days, 3A, 4 no route; the diagnostic rule shipped
  as a reading.
- **D2.** Standard-library HTTP only; one outbound module; no retry.
- **D3.** A failure is never an empty result; NHTSA's 400 is an answer
  only with the zero-result body (F103).
- **D4.** Recalls refresh only on request; each fetch recorded; lookups
  print the fetch date; no staleness threshold.
- **D5.** Severity only from NHTSA's park flags; otherwise `unrated`.
- **D6.** Zero results are never an all-clear.
- **D7.** A shop's jurisdiction in its own table; `shops` unchanged.
- **D8.** A shop's own valid row wins over the regulation row, per item.
- **D9.** One combined rate per jurisdiction (parts of a tax: row 368).
- **D10.** Tax only on taxable lines; the invoice records rate, source,
  recheck-by and taxed types.
- **D11.** The shop's currency is its jurisdiction's; an invoice in
  another currency uses only the shop's own rate (3A).
- **D12.** Smoke calls through the app's own commands, on a scratch
  database, logged.
- **D13.** No refute pass: code, schema, tests and three regulator
  rows whose quotes are in `281_sources.md` and pinned by a test (the
  seed's URLs and clauses equal the sources file's).
- **D14.** The live deploy changes no existing row; otherwise, a rule-1
  stop.

## Non-goals

- Any route; any app screen. Customer or invoice tax exemption (F185).
- Automatic rates by address; itemised tax parts (368).
- Recall reimbursement claims (367); whether a VIN is inside a campaign.
- A scheduler or background refresh of any service.
- ECB rates converting an invoice (3A).

## Planned items

1. This v1.0, and rows 281, 287, 288, 289 rewritten; committed and pushed
   before code.
2. The network guard and its planted known-bad test.
3. Migration 078 and `tests/test_phase281_migration.py` (tables, seed,
   rollback, planted rows unchanged; head pinned only as `>= 78` and
   `== max(MIGRATIONS)`). `wholetree.sh --full` before its commit.
4. `core/outbound.py`; row 288 (`tests/test_phase281_tax.py`) and the
   invoice changes, updating the invoicing tests that relied on the zero
   default; row 289 (`tests/test_phase281_exchange.py`); rows 281 and 287
   (`tests/test_phase281_recalls.py`, `tests/test_phase281_vin.py`).
5. The three smoke calls, logged; their responses become fixtures.
6. The allowlist and its pins; F158 scan.
7. Mutations (`281_mutate.py`), each seen red.
8. **The planned stop:** gate 11 red on exactly the table above; the
   held work as `281_wip.patch`; the operator writes the mobile session's
   prompt.
9. After the snapshot: 244G's scanner; `wholetree.sh --full` on the
   committed HEAD; the regression of record; `COLLECTED_TEST_FLOOR`.
10. The deploy: scope, dry run and its committed diff, `apply-live`.
11. Close-out: v1.1; rows 287–289 ✅ folded into 281; row 281 ✅; F184
    closed; the fold pin; the regression again on the close-out commit;
    the history row; the handoff; `verify_phase.sh`.
