# Phase 281 — Track O batch 3: recalls, VIN decoding, tax rates and exchange rates — phase log

**Status:** 🚧 In progress
**Branch:** `phase-281` (Opus session, main checkout, the only writer)

---

### 2026-09-30 — Opened: Track O batch 3

The prompt is `docs/prompts/281_track_o_batch3.txt` (merged in
`5cde0c3`). The operator's words it carries, verbatim:

> 1, 2, 3, 5 as recommended.

> 4: check row 288 — which jurisdiction does it name, and where is the first real shop? tax follows the shop. if it's MA (flat statewide), start there, not CA. either way: every rate stored with its effective date and source, and a check that fails when a rate is past its stated validity.

> note for the batch 3 prompt when you write it: first outbound calls in the app. tests use recorded fixtures, never live endpoints; the app degrades cleanly when a service is down (shown to the user, never silently empty); no live API call during the build except one smoke call per service, logged.

> i will be in MA and i mean, i intend to be in all 50 states or wherever they can download it , idk how that would work

> we will just wait until it reports and then go with whats recommended based on that

Batch 3 is rows 281 (NHTSA recall refresh), 287 (VIN decoder), 288 (tax
rates) and 289 (exchange rates). The tax plan the operator accepted: a
model not tied to one state or country; Massachusetts shipped verified
from the Department of Revenue's own text; every other shop enters its
own rate with its source and effective date; a check fails once a rate is
past its stated validity; automatic rates for every address paused.

Read first: the 275 handoff (`docs/handoffs/2026-09-30_275_closed.md`),
the triage report (`docs/reports/2026-09-28_track_o_triage.md`), rows
281, 287, 288 and 289, and 275's documents in `docs/phases/completed/`.

The first commit: **row 281 🚧**, carrying the batch.

### 2026-09-30 — Step 0, and the stop

`281_step0.md`; the regulators' and services' pages, quoted with URLs and
dates, in `281_sources.md`. No service API was called. What it found:
- **Every measured fact in the prompt holds** (S0-1). Two more: no live
  bike has a VIN, and 36 test calls rely on the zero default.
- **F184 filed** with the `finding` skill (`next_f_number.sh`: F183 in
  this file, F181 in the mobile file): the zero tax default.
- **Two corrections** (S0-2): these are not the app's first outbound
  calls (push, the AI SDKs and Stripe already call out), but the first to
  public data services; and **F103**, filed by Phase 251 in the mobile
  file, is a binding constraint on any recall sync. Its requirements are
  met by the design in S0-4 and S0-5; it is closed in the mobile session.
- **Massachusetts:** 6.25% on parts, effective 2009-08-01 (the DOR guide,
  TIR 09-11); labour and a diagnostic fee not taxable (830 CMR
  64H.1.1(2)(a)1, (5)(a)); **no DOR page names a shop-supplies charge**, so
  none is shipped and a Massachusetts shop records its own rule. No page
  states a validity for the rate.
- **The ECB's page says its rates are "for information purposes only.
  Using the rates for transaction purposes is strongly discouraged."**
- **How the pages were read:** nhtsa.gov and mass.gov refuse curl (403,
  with or without a browser User-Agent). mass.gov was read with headless
  Chrome's `--dump-dom`; nhtsa.gov refused that too, so NHTSA's recall
  service is described from this project's own recorded responses
  (`~/research/motodiag/`, 2026-09-20) and F103. macOS has no `timeout`,
  so Chrome ran under `perl -e 'alarm 60; exec @ARGV'`; no Chrome process
  was left running.
- **The edit guard blocked one command:** a loop writing
  `> $n.dom.html`, a redirect to a path held in a variable. It was redone
  with literal paths. The guard was right to refuse what it cannot
  resolve, and was not loosened.

Decided (with the reasons in `281_step0.md`): stdlib `urllib` and one
outbound module; a network guard in `conftest.py`; recalls refreshed only
on request and stored with their fetch; severity only from NHTSA's own
park flags, else "not rated"; no green all-clear from zero results; VIN
decodes stored per VIN; a shop's jurisdiction in its own table, so
`shops` is not altered; the invoice records its rate and source.

The ledger, in this commit:
- **Rows 367 and 368 ⏸️**, split from 281 (recall reimbursement claims)
  and 288 (automatic rates for every address), each with its reason. The
  numbers were free: no row in either ROADMAP, no phase document and no
  handoff names them; the same search finds row 366 in three documents.
- The header reads 368 numbered.
- Rows 281, 287, 288 and 289 are rewritten after the operator's answers,
  since question 3 decides what 289 builds.

**Stopped for the operator (rule 1: real forks and new thresholds).**
Four items in `281_step0.md` ("Questions for the operator"): (1) the
invoice API's `tax_rate`: remove, required, optional, or unchanged; (2)
the validity windows no source states: Massachusetts's rate (12 months
from the last check proposed) and the ECB's rates (through the 4th day
proposed); (3) whether ECB rates may convert an invoice; (4) a note with
a default: no app route for VIN decoding or recalls.

### 2026-09-30 — The operator's pick, F185, and v1.0

The operator's answer, pasted into the session as one block, verbatim:

> 1: A. Also file a finding: with the field gone, a tax-exempt sale (a resale or exempt-organization certificate, for example a town's police bikes) can't be invoiced. It waits until a real shop needs it.
> 2(a): 12 months, as proposed, and every invoice and `tax status` print the date the rate must be re-checked by.
> 2(b): through the 5th calendar day, not the 4th. After Easter the next ECB rate comes out Tuesday at 16:00 CET, which is Tuesday morning in Massachusetts and the 5th day after Thursday's rate.
> 3: A.
> 4: no route, as the default.
> The diagnostic-fee rule is the build's own reading, not a stated rule. Ship it with that said in its source, so `tax status` shows it as a reading of 64H.1.1(2)(a)1.

- **2(b) corrects Step 0's arithmetic.** Thursday's rate; Good Friday
  and Easter Monday are TARGET closing days; the next rate is Tuesday
  16:00 CET, 10:00 in Massachusetts (EDT), day 5 after Thursday. So an
  ECB rate is valid through `rate_date + 5 days`.
- **F185 filed** with the `finding` skill (`next_f_number.sh`: F184 here,
  F181 in the mobile file): a tax-exempt sale cannot be invoiced once
  tax comes only from the record. Not fixed in this batch, as asked.
- **The diagnostic rule** carries `basis = 'reading'` and its clause, and
  `tax status` prints it as a reading of 64H.1.1(2)(a)1.
- Rows 281, 287, 288 and 289 are rewritten to what the batch builds.

v1.0 is `281_implementation.md`.

### 2026-09-30 — Bug fix #1: a VIN's year code decoded to a future model year

- **Issue:** the offline decode (`decode_vin`, Phase 155) read year code
  `7` as 2037, `A` as 2040, and every code from `W` to `7` as 2028–2037,
  measured on 2026-09-30. Found by this phase's local dry run of `advanced
  vin decode 1HD1FRW177Y600001`, which would have asked vPIC for model
  year 2037. `recall check-vin` printed the same wrong year.
- **Root cause:** `_disambiguate_year` picked the 30-year cycle closest to
  today. A model year cannot run more than one year ahead of the
  calendar, so "closest" chooses the future half the time.
- **Fix:** the latest year of the code's cycles that is not after next
  year (`advanced/recall_repo.py`).
- **Files:** `src/motodiag/advanced/recall_repo.py`,
  `tests/test_phase281_vin_year.py` (new, 11: nine codes pinned with the
  clock at 2026, every code by today's clock, the VIN above).
- **Verified:** the new file, `test_phase155_recall.py` (whose only year
  assertion, `L` → 2020, holds), F86's and gate 7's: 62 passed. The batch's
  held work was stashed for this commit and restored after (below).
- **Commit:** this entry's commit.

### 2026-09-30 — The battery, and a trial run stopped

A trial run of the whole suite under the new network guard was stopped at
32% when the machine read 1% battery (0 failures by then). The two drafts
then in the scratchpad (`/private/tmp`, cleared on reboot) were copied to
`docs/phases/in_progress/281_drafts/` and applied once on power. The
drafts folder is removed before the close-out commit; what it held is in
`migrations.py` and `recall_repo.py`.

### 2026-09-30 — The build

- **The network guard** (`tests/support/network_guard.py`, installed at
  `tests/conftest.py` import): a connection or name lookup to anything but
  loopback or a Unix socket raises `NetworkBlockedInTests`, naming the
  host. `test_phase281_network_guard.py`, 7: a planted test that opens a
  URL, run in a pytest subprocess with only the guard loaded, fails on it;
  a planted loopback test passes. Every host the file names is reserved
  (`.invalid`, 192.0.2.0/24), so a broken guard, as the mutation run makes
  it, still reaches no real service.
- **Migration 078** as v1.0 describes; `test_phase281_migration.py`, 8:
  the tables and columns, the rollback, planted rows in eight tables
  unchanged both ways, Massachusetts's rows, the CHECKs, and every shipped
  URL and clause present in `281_sources.md`. `ALTER TABLE … ADD COLUMN`
  with a column CHECK, and `DROP COLUMN` of it, were tried on a scratch
  database first.
- **`core/outbound.py`**: stdlib `urllib`, User-Agent
  `motodiag/0.6.0 (+https://github.com/Kubanjaze/moto-diag)`, 20 s, one
  request, `ServiceUnavailable` with `unreachable`, `blocked`, `error` or
  `malformed`. A 403 is a block; any other status the caller does not
  accept is an error; an HTML page on a success status is a block. (The
  first version called an HTML 503 page a block; changed when its test was
  written, before any commit.)
- **Row 288:** `accounting/tax.py`, `cli/shop_tax.py` (`shop tax
  jurisdiction add/list/set`, `rate set`, `rule set`, `confirm`,
  `status`); `shop/invoicing.py` takes tax only from the record, on the
  taxable lines, rounded half up, and records rate, source, recheck-by and
  taxed types; `shop invoice generate` loses `--tax-rate` and gains
  `--currency`; the invoice panel prints the rate, its source and "Rate
  must be re-checked by D"; the API route drops `tax_rate` and a tax
  refusal is 409 (`InvoiceTaxNotOnRecord`). `test_phase281_tax.py`, 16.
- **Row 289:** `accounting/exchange.py`, `cli/shop_currency.py` (`shop
  currency refresh`, `rates`, `set`, `convert`). `test_phase281_exchange.py`,
  17.
- **Row 281:** `advanced/nhtsa.py`; `recall_repo.py` gains
  `refresh_recalls`, `recall_state`, `refresh_all_bikes`,
  `fetched_coverage_sql`; the three older queries (`inventory`'s
  `list_recalls_for_vehicle`, `list_open_for_bike`, and through them
  `check_vin`, `lookup`, the predictor's feed) keep their own clause for
  older rows, limited to `source IS NULL`, and match fetched campaigns only
  through `recall_vehicles`; `cli/recall_nhtsa.py` (`advanced recall
  refresh`); `recall check-vin --refresh`, `recall list --bike`; the recall
  table shows "not rated by NHTSA" and the fetch date. F86's wording is
  kept per model, so its tests are unchanged. `test_phase281_recalls.py`, 20.
- **Row 287:** `advanced vin decode [--refresh] [--bike --save]`.
  `test_phase281_vin.py`, 11.
- **The tests that relied on the zero default** now state the shop's tax:
  `tests/support/tax_on_record.py` records a test jurisdiction (`ZZ-T`,
  labelled a fixture, valid 2000–2099 so no test reads today's date, every
  line taxable: the old arithmetic). Twelve files, 260 tests: 169, 170,
  174 (gate 8), 180, 182, 184 (gate 9), 202, 205 (gate 11, through the new
  `shop tax` commands), 274 P&L and quotes, 275 export. Where a test sent
  `tax_rate`, it now records that rate on the shop instead.
- **The API model ignores unknown fields**, as every request model here
  does, so a caller that still sends `tax_rate` has it ignored; the
  response states the rate used. Tested (`tax_rate: 0.5` sent, 6.25% used).
- **Decisions made while building:**
  - a shop's own row wins over the regulation row per item, and a
    Massachusetts shop's shop-supplies rule is its own (`shop_id` set), so
    it never becomes the rule for other shops in the state;
  - `tax status` fails on no jurisdiction, no valid rate, or a rule past
    its validity; a line type with no rule at all is listed as not on
    record, because a shop that never charges it is not failing (an
    invoice carrying it is still refused);
  - the recheck-by date of an invoice is the earliest validity among the
    rate and the rules it used;
  - `count_recalls(older_only=True)` replaces a second copy of the count
    in the CLI.
- **Gates that caught the build before any commit:**
  - 209B/244X: `get_resolutions_for_bike` gained a caller (ORPHANS 118 →
    117; 244X's multi-line list 51 → 50), and the new table heading
    `"Recall"` read to the gate as a use of `inventory.models.Recall`, a
    false caller; the heading is now "Recall id";
  - 256's chokepoint gate refused `f"SELECT * FROM {table}"` in
    `tax._pick`; the two tables are now literal query prefixes;
  - 355's gate refused the guard test's subprocess pytest for stating no
    worker mode; it now passes `-p no:xdist`.
- 244G's scanner over `tests/`: 0 findings. F158 scan: the new
  user-facing strings and command docstrings hold no internal reference;
  the four new library modules' module docstrings name phases, and no user
  sees those.

### 2026-09-30 — The smoke calls

One live call per service, each through the app's own command on a
scratch database, recorded by `281_smoke.py` (a tap on
`core.outbound._open` that calls the real transport once). The log and
bodies are in `281_smoke/`. A local dry run with a fake transport came
first, and found bug fix #1.

| service | command | URL | time (UTC) | status | bytes |
|---|---|---|---|---|---|
| NHTSA recalls | `advanced recall refresh --make PIAGGIO --model "MP3 500" --year 2020` | `https://api.nhtsa.gov/recalls/recallsByVehicle?make=PIAGGIO&model=MP3%20500&modelYear=2020` | 2026-09-30T22:36:26 | 200 | 2149 |
| NHTSA vPIC | `advanced vin decode 1HD1FRW177Y600001` | `https://vpic.nhtsa.dot.gov/api/vehicles/DecodeVinValues/1HD1FRW177Y600001?format=json&modelyear=2007` | 2026-09-30T22:36:27 | 200 | 4126 |
| ECB | `shop currency refresh` | `https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml` | 2026-09-30T22:36:28 | 200 | 1547 |

- **NHTSA accepted the app's honest User-Agent.** No browser User-Agent
  is sent, and none was needed.
- NHTSA returned 20V524000 and 22V217000 for the F103 check vehicle, the
  two campaigns Phase 252 recorded for it.
- The VIN is made up (a valid check digit, serial 600001), so no real
  vehicle is named. vPIC decoded it partially (make and model blank,
  error codes 3 and 14), and the command labelled it "Partial decode"
  with vPIC's text.
- The ECB feed held 29 currencies for 2026-09-30.
- All three bodies became fixtures (`tests/fixtures/phase281/`, byte for
  byte, sha256 checked). The others are listed there as recorded or
  built: NHTSA's 400 zero-result body (recorded 2026-09-20), an Akamai
  403 page (recorded at Step 0), a clean vPIC decode and a 503 page
  (built).

### 2026-09-30 — Mutations

**41/41 red** (`281_mutate.py`: guard 2, migration 4, outbound 3, recalls
12, VIN 4, tax and invoices 11, exchange 4, bug fix 1). `git diff --stat`
was the same before and after. The tax group was run again after `_pick`
changed: 11/11.

### 2026-09-30 — A whole-suite run on the held work, and two fixes

`python -m pytest -n auto --dist load` on the uncommitted work (not the
regression of record): 10261 passed, 7 failed, 19 min 3 s.
- **Five are the planned stop:** gate 11's snapshot test, and gates 12, 13
  and 14 re-running it.
- **`test_phase275_migration.py::…test_existing_rows_are_unchanged_either_way`**
  applied every pending migration, then compared `invoices` rows whole;
  078's ten new columns lengthened each row. The test now compares the
  planted rows' own columns and their count. `test_phase281_migration.py`
  had the same trap waiting for migration 079 (it pinned the columns as
  the table's last); it now pins them where they are and the rows by
  prefix. 9 and 8 passed; the migration mutations 4/4 red again.
- **`test_phase78_gate2_integration.py::…test_noise_cross_make`: worker
  gw6 crashed with no traceback.** Recorded against F183 in
  `docs/FOLLOWUPS.md`, as the prompt directs. The file alone: 22 passed.
  The regression of record is run in parallel after the snapshot; a
  second loss there is a stop.
- 244G's scanner over `tests/` again: 0 findings.

### 2026-09-30 — The planned stop: gate 11's contract snapshot

`wholetree.sh --full` (85 files): 3976 passed, **4 failed**, all gate 11:
gate 12's and gate 13's reruns of gate 11, gate 13's rerun of gate 12,
gate 14's rerun of gate 13. Gate 11 itself reports exactly the one change
v1.0's API table names, and nothing else:
`InvoiceGenerateRequest.tax_rate: in the snapshot, absent from the API`.

- **Not committed:** everything in `src/` and `tests/` (42 paths). The
  migration and the code that reads its tables go in together, and a
  commit to `migrations.py` needs a `--full` record, which is red until the
  snapshot is refreshed.
- **Backup:** `281_wip.patch` in this folder (4596 lines, binary-safe, new
  files included). `git apply --check` passes against `b5dbf1f` in a
  scratch worktree, and it reverse-applies to this working tree.
  `git diff HEAD -- src tests` hashes `a21590328d77ed5f…`.
- **Committed:** this log, F183's note, `281_mutate.py`, `281_smoke.py`
  with its log and bodies, and the patch.

**What the mobile session accepts** (v1.0, "The API change"): the snapshot
diff removes `InvoiceGenerateRequest.tax_rate`, and nothing else. The app
does not call invoice generation; its generated types lose the field. The
same session closes **F103** in the mobile repo's FOLLOWUPS: its
requirements for a recall sync are met here (a User-Agent of the app's
own, which NHTSA accepted; a 403 or a web page is a failure, never
empty; NHTSA's 400 is an answer only with its zero-result body; a refresh
of every bike first requires 20V524000 for PIAGGIO MP3 500 2020, and
exits 1 listing any bike that failed). The operator writes that session's
prompt. Until it pushes, this checkout does not switch branches or commit
anything under `src/` or `tests/`.

### 2026-10-01 — Resumed: the mobile snapshot refreshed in moto-diag-mobile e536e60

The operator (2026-10-01): "The mobile push has landed: moto-diag-mobile
e536e60 on origin/main (its prompt is e69e5e0). … The snapshot diff
removes InvoiceGenerateRequest.tax_rate and nothing else; src/api-types.ts
loses only that field. … F103 was noted, not closed: the mobile file says
Phase 281 meets it and it closes when 281 merges. … No new finding was
filed in the mobile repo, so the findings header needs no change."

Checked here, 00:20 EDT:
- `e536e60` is `moto-diag-mobile` `origin/main`, local `main` level with it;
- this checkout as left: HEAD `2112cba`, 42 changed paths, `git diff HEAD
  -- src tests` still hashes `a21590328d77ed5f…`;
- `__pycache__` under `src/` and `tests/` cleared (the mobile session had
  written `.pyc` files here); **gate 11: 21 passed**, run with `-B`.
- The month-end evening window (F10) is over: it is 2026-10-01.

**F103 stays open until 281 merges**; a later mobile session closes it,
citing the merge. The handoff says so.

At the operator's request, an untracked symlink
`moto-diag-mobile/moto-diag-mobile` (to the repository itself, made
2026-09-29) was removed; the link only, the repository is intact.

The held work is committed from the working tree, and `281_wip.patch` is
removed in the same commit, since the commit now holds what it held.

### 2026-10-01 — The held work committed (`07d166f`), and the floor

- `wholetree.sh --full` on the staged tree: **3980 passed, 0 failed**,
  record written. Committed as `07d166f`.
- **`COLLECTED_TEST_FLOOR` 10179 → 10268**, by diffing collected IDs
  (`--collect-only -q -o addopts=`) against a `master` worktree: +89 = the
  seven `test_phase281_*` files (90) + gate 15's
  `test_rolling_back_peels_every_successor[77]` − 209B 1 − 244X 1. The
  worktree's run imports this checkout's `src` through the editable
  install, so `[77]` appears in both lists (master 10,180). The worktree
  was removed after.
