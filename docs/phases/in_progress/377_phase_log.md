# Phase 377 — Times stored in UTC across the shop's tables (F186, F191) — phase log

**Status:** 🚧 In progress
**Branch:** `phase-377` (Opus session, main checkout)

---

### 2026-10-07 — Opened

The operator's prompt is `docs/prompts/377_times_in_utc.txt` (merged
`4f47832`). The last session's state is
`docs/handoffs/2026-10-07_374_closed.md`. Row 377 went 🚧 before Step 0
(`991d54c`):
- 377 is the next free number;
- `roadmap_check.py` passed;
- `wholetree.sh` fast exited 0 (1523 passed);
- pushed.

### 2026-10-07 — Step 0, and the stop

The record is `377_step0.md` (`a92fe1e`). Every measured fact in the prompt
re-verifies. The prompt asks for three questions at Step 0. They were put
with options, recommending 1B, 2A and 3A:
1. the format and how comparisons are done;
2. the live rows;
3. the app.

**The operator's answer, verbatim:** "1B, 2A, 3A. Two conditions: "the
shop's day" is the server's zone today, since shops carry no timezone, so
say so in the log and file a finding for a per-shop timezone; the product
is meant for every state. And turnaround must not drop a work order
silently on a caught TypeError: make it fail loudly, or test that it can't
happen."

**Condition 1, recorded:** "the shop's day" in this phase is the server's
zone, because `shops` has no time-zone column. That covers every local
display, every day or month window, and every typed date read as local. It
is `astimezone()` with no argument in Python and `TZ` in tests. Filed as
**F192**, a per-shop time zone, before this entry cites it.

**Condition 2:** both, in v1.0 Logic step 5:
- turnaround and mechanic performance parse both times by one rule, so the
  mixed pair cannot raise;
- the catch-and-skip is removed, so a value that cannot be parsed raises,
  naming the work order;
- a test covers each.

**What 2A approves, read literally:** the choice to convert the 40 shop
fields with migration 082 and to leave known_issues. It does not approve a
diff. The deploy's exact dry-run diff, with 082's `schema_version` row, goes
to the operator before `apply-live`.

### 2026-10-07 — v1.0

`377_implementation.md` v1.0: the operator's choices and conditions, the
format, Logic steps 1–9 and the checklist.

### 2026-10-07 — The build

The API connection dropped at 09:22, mid-build; the operator reported it,
and nothing had been committed since v1.0 (`421d592`). Before carrying on,
`git diff` was checked against the plan: 15 files under `src/`, the writers
and the three repos' cutoffs, as planned. The only unzoned `datetime.now()`
lines left were the two docstrings and the four pinned appointment lines.
Every changed module imported.

What was built, against v1.0's Logic steps:
- **Step 1, `core/timestamps.py`:**
  - `stored_instant`, `utc_cutoff`, `local_day_start` and `local_day`;
  - `with_utc_times`;
  - `local_display` now reads SQLite's space shape as UTC;
  - `SHOP_TIME_FIELDS_082` and `convert_shop_times_082`;
  - `to_utc` now calls `stored_instant`, with the same rule.
- **Step 2:** 40 stamps call `utc_now()`.
- **Step 3:**
  - `_since_cutoff` is removed, and its four users take `utc_cutoff` and
    `datetime(col)`;
  - `_parse_date_window` returns `utc_cutoff`, and analytics' 15
    comparisons are wrapped. The 13 Step 0 counted by line, plus the two
    bay-slot `COALESCE` lines, which that count's pattern missed.
- **Step 4:** the P&L window, the export window and its invoice date, and
  throughput's days are all in the shop's day.
- **Step 5:** both silent skips raise naming the work order:
  - turnaround's `continue`;
  - `mechanic_performance`'s `except (ValueError, TypeError): pass`, the
    same pattern, found while editing.
- **Step 6:**
  - `cli/shop.py`: work-order show, intake show and list, issue show and
    list;
  - the work-order report's Intake row;
  - the shop API's customer, intake, work-order and issue responses, and
    `VehicleResponse`.
- **Step 7:** migration 082, with `SCHEMA_VERSION` 81 → 82. On a scratch
  copy of live it changed exactly 40 fields and reached schema 82.

**Decisions taken during the build:**
- **The typed-`since` sites outside the shop's tables:**
  - sensor recordings and drift are left out (5 comparisons in
    `hardware/recorder.py`, `advanced/drift.py` and `cli/advanced.py`).
    Their columns hold one aware shape, a typed date compares as a prefix,
    and `sensor_samples` can be large, so wrapping the column would stop
    the index being used. They are filed as **F193**;
  - `feedback/learning_hook.py` is fixed. It compared `since.isoformat()`
    (a `T`) with a `CURRENT_TIMESTAMP` column, which is 191B's bug, and the
    table is small.
- **`revenue_rollup`'s cutoff:** the dashboard passed analytics' computed
  UTC cutoff into `revenue_rollup`, and `utc_cutoff` would read that naive
  string as local a second time. The dashboard now passes its `since`
  token, and `invoicing.py` converts it. Every other caller (the CLI, the
  API) passes a typed value.
- **The dashboard's utilization days** are the shop's days (`astimezone()`).
  Before, they were the UTC date, which on a US evening is tomorrow.
- **F192 gained a paragraph from the census.** A bay slot's scheduled times
  are clock times stored with `+00:00` (275's rule), so the overrun
  window's edge is off by the offset for a slot with no `actual_end`. This
  is pre-existing and needs a per-shop zone to fix, so it is recorded
  there, not fixed.
- **The census test's prose:** a first draft skipped lines starting with a
  quote, and so dropped a real code line, `appointment_repo.py:122`. Its
  own test went red on that, which is how it was found. The skip was
  removed; the three prose lines (a docstring and the descriptions of 079
  and 082) are pinned by name.
- **Phase 171's `test_iso_input`** asserted that a naive typed time is read
  as UTC. v1.0 reads it as the shop's time, so the test now types an
  explicit offset. The local reading is tested in 377's `TestHelpers`.

### 2026-10-07 — The first whole-suite run, and four older tests

The whole suite ran on the work in progress before the new test file
existed: 10579 passed, 6 failed. Each failure was read:
- **171's `test_iso_input`** expects a naive typed time to be read as UTC
  (changed above).
- **275's Xero test:** a due date stored as UTC midnight came out a day
  early, because the export's date formatter now gives an instant's day in
  the shop's zone. A due date is a calendar date, not an instant, and only
  the legacy invoice model writes it. The export now formats `DueDate` by
  its own date as written (`_us_due_date`, the old rule). `InvoiceDate`
  (`issued_at`, an instant) takes the shop's day. This is a fix to 377's
  own new code before any commit, not a bug-fix entry.
- **256's chokepoint pins `file:line`** of every dynamic-table query.
  `intake_repo.py` moved from 90 to 91, and 082's converter is a fifth
  query. Its table names come only from `SHOP_TIME_FIELDS_082`, which has
  no `known_issues`; 377's test asserts that. The pin list and its
  docstring were updated.
- **Gate 16's frozen-day check** read `completed_at` as noon local. It is
  now noon EDT stored in UTC, `2026-10-15T16:00:00.000+00:00`, the same
  check its `issued_at` line already made.
- **370's `local_display` test** pinned a space-shaped value as returned
  unchanged. v1.0 Logic step 1 changes that on purpose: SQLite's shape is
  UTC, so it is shown local. The test now pins the new reading, and a
  naive `T` value still unchanged.

The six files then: 259 passed.

### 2026-10-07 — Mutations, the scanner, the dry run, the regression

- **Mutations:** `377_mutate.py`, 26/26 red (`377_mutate.out`). M1, the
  planted return to local time in `complete_work_order`, is red.
- **244G's scanner** over all of `tests/`: 0 hits.
- **Deploy dry run:**
  - `377_deploy_scope.json` was generated from
    `377_live_rows_preview.out`;
  - `deploy.py dryrun 377` gave scope problems "none", a census of 36 and
    backup `motodiag_pre377_20261007_112806.db`;
  - compared by script, the exact diff equals the preview's 40 fields in
    customers 3–6, vehicles 1–5 and 10, and work orders 1–5, plus 082's
    `schema_version` row, with no schema change.
  - Committed in `5ad8c3e`.
- **`wholetree.sh --full`** on the staged build: 4020 passed, gate 11
  included, so the snapshot did not move. Committed as `5ad8c3e`.
- **Floor:** 10584 → 10617 (`87f1fc8`), from a diff of collected ids
  against master: the new file's 32, and gate 15's rollback case `[81]`,
  which 082 adds.
- **`wholetree.sh --full`** on the committed HEAD `87f1fc8`: 4020 passed.
- **What a user sees,** on a scratch copy of live with 082 applied:
  `shop work-order show 3` prints `Opened: 2026-09-04T15:35:46`, the same
  local time as before. The stored value is now
  `2026-09-04T19:35:46.883+00:00`.

Regression of record: 10617 passed, 0 failed, 0 skipped, 0 errors at `87f1fc8` (25 min 38 s wall, `python -m pytest -n auto --dist load`, exit 0)

### 2026-10-07 — The planned stop: the live diff, and the mobile session

Two things wait for the operator. Nothing in this checkout is held: every
change is committed and pushed at `87f1fc8`, so no patch backup is needed.
The only uncommitted file is the mobile prompt, in the other repository.
1. **The live apply (rule 1).** `377_dryrun_diff.md` is committed. Its
   exact diff changes the 40 fields of the preview and adds 082's
   `schema_version` row. `apply-live` waits for the operator's own words
   on that diff.
2. **The mobile session (3A).** Its prompt is
   `moto-diag-mobile/docs/prompts/2026-10-07_work_order_times_local_377.txt`,
   left uncommitted for that session to commit. The session makes the
   work-order screen's five lifecycle rows show the phone's local time.
   The snapshot did not move, so master is not tied to this branch by gate
   11. The merge still waits for the mobile session, as v1.0 says.

### 2026-10-07 — The deploy: apply-live

**The operator's approval, verbatim:** "Approved, mine: apply migration 082
live. Exactly these 40 fields, each converted from New York local time to
UTC in 370's format: customers 3-6 (created_at, updated_at); vehicles 1-5
and 10 (created_at, updated_at); work orders 1-5 (opened_at 5, started_at
4, completed_at 3, closed_at 3, updated_at 5). Plus 082's own
schema_version row (82). No schema change and no other table. If the fresh
dry run differs from the committed diff in anything, or live has changed
since the backup, stop and show me. After the apply, confirm live equals
the approved diff, then wait for the mobile session before merging."

`deploy.py apply-live 377`:
- **Preflight passed:** live equal to the backup, and a fresh dry run
  equal to the committed exact diff. So neither stop condition arose.
- **Applied:** `[82]`. After: 5860 rows, 117 tables, integrity ok, scope
  problems none.
- **The live diff:** `377_live_diff.md` reads "Equals the approved exact
  diff: yes".

**Checked independently**, by a script comparing backup
`motodiag_pre377_20261007_112806.db` with live, every table by rowid:
- 40 fields changed, equal to the approved values;
- one row added, `schema_version` 82;
- nothing removed;
- `sqlite_master` unchanged;
- integrity ok.

Live is at schema 82. Work order 1's `opened_at` is
`2026-09-02T20:29:25.409+00:00`. known_issues has no `+00:00` stamp.

The merge waits for the mobile session, as the operator says.
