# Phase 377 — Times stored in UTC across the shop's tables (F186, F191)

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-10-07 (v1.0 2026-10-07)

**Outcome (v1.1).** F186 and F191 fixed, proven on the clock, and live.
- **Writers:** the 40 stamps write `YYYY-MM-DDTHH:MM:SS.mmm+00:00`;
  appointments' clock times keep 275's rule.
- **Comparisons:** every shop cutoff and window compares
  `datetime(col) >= ?` against a UTC cutoff. Days and months are the shop's
  day, which is the server's zone (F192).
- **Turnaround and mechanic performance** raise, naming the work order, on
  a value that is not a time; neither drops one in silence.
- **Readers:** the CLI and the work-order report show local time. The API
  sends 370's format, and the app formats it (moto-diag-mobile `0074eb9`).
  No API schema change.
- **Live:** migration 082 changed exactly the 40 approved fields, plus its
  `schema_version` row. The live diff equals the approved diff.
- **Proof:** 32 tests on 370's frozen clock in New York; mutations 26/26
  red, M1 the planted return to local time.

Regression of record: 10617 passed, 0 failed at `87f1fc8`. F186 and F191
are closed; F192 and F193 are filed.

---

## Goal

Row 377, F10's family after Phase 370 fixed diagnostic sessions:
- **F186:** work-order, issue, intake, repair-plan, booking and other shop
  times are stamped in naive local time, while `shop/analytics.py`
  compares them with a UTC cutoff in another shape;
- **F191:** `--since` compares a local cutoff, in the `T` shape, with UTC
  stamps in the space shape.

Every time this phase's writers stamp is UTC in 370's format. Every cutoff
and window compares parsed times, in one clock. Every reader shows the
shop's local time. The 40 live shop fields in the defect shape are
converted by migration 082. Proven on 370's frozen clock in New York, with
a planted return to local time that turns the proof red.

The operator's choices at Step 0 (verbatim in the phase log): **1B, 2A, 3A**,
with two conditions:
- **"The shop's day" is the server's zone today**, because shops carry no
  time zone. The log says so, and F192 is filed for a per-shop zone.
- **Turnaround must not drop a work order silently** on a caught
  TypeError.

Out of scope:
- the per-shop zone (F192);
- known_issues' 1060 live stamps (2A leaves them);
- appointment clock times (Phase 275's rule, S0-4);
- writers that already write UTC in another shape (1B leaves them).

## Step 0 — summary

The full record is `377_step0.md`.
- **Writers:** 45 naive local stamps in 15 files, re-verified.
- **Reproduced** under `TZ=America/New_York`:
  - F191 in the evening (`--since 30m` lists an intake from three hours
    ago);
  - F191 at midday (it lists nothing);
  - F186 at a 30-day window's first day (2 counted, 1 expected).
- **Comparisons:**
  - F186/F191's: intake 2, work order 1, issue 1 and analytics 13;
  - two windows on UTC dates, the P&L month and the accounting export;
  - 15 typed `since` values compared as text.
- **Readers:** `cli/shop.py`, the work-order report, analytics' days, the
  P&L and export dates, and the API's shop dicts and `VehicleResponse`.
  The app's only display is the work-order lifecycle block.
- **Live:** 40 shop fields in 15 rows, and 1060 known_issues stamps.

Extension of 370. No schema change; migration 082 is data only. No API
schema change.

## The format

**What is stored:** this phase's writers store 370's format,
`YYYY-MM-DDTHH:MM:SS.mmm+00:00`, from `utc_now()`. Columns that default to
`CURRENT_TIMESTAMP` keep SQLite's `YYYY-MM-DD HH:MM:SS`, which is UTC.
Other writers that already store UTC keep their shape (1B).

**How they compare:**
- **In SQL,** `datetime(col) >= ?`, against a cutoff in SQLite's canonical
  UTC shape `YYYY-MM-DD HH:MM:SS`. At Step 0, SQLite 3.53.2's `datetime()`
  read all five live shapes and converted each offset to UTC.
- **In Python,** times are parsed by one rule, `to_utc`'s, into aware
  datetimes before any arithmetic.

**The rule for reading a stored value** (370's):
- naive with a `T`: local time, the old `datetime.now().isoformat()`;
- naive with a space: SQLite's `CURRENT_TIMESTAMP`, so UTC;
- with an offset or `Z`: that instant.

**The shop's zone is the server's zone** (the operator's condition 1;
F192). Throughout this document, "local" and "the shop's day" mean that:
- `datetime.astimezone()` with no argument;
- `TZ` in tests.

A typed `since`, `until` or date with no zone is read in it. A typed value
with an offset is converted.

## Logic

1. **`core/timestamps.py`** gains:
   - `stored_instant(value) -> datetime`: a stored time as an aware UTC
     datetime, by the rule above. It raises `ValueError` on anything else;
     there is no fallback.
   - `utc_cutoff(value) -> Optional[str]`:
     - `None` or blank gives `None`;
     - `Nd`, `Nh` and `Nm` give `utc now − N`;
     - an ISO date or date-time with no zone is read in the shop's zone;
     - one with an offset is converted;
     - the result is in SQLite's UTC shape, for `datetime(col) >= ?`;
     - anything else raises `ValueError`.
   - `local_day_start(day) -> str`: the UTC instant at which the shop's
     day `YYYY-MM-DD` begins, in the same shape. Day and month windows are
     `[start(first), start(day after last))`.
   - `local_display(value)`: a space-shaped value is now read as UTC and
     shown local, by the rule. Naive `T` is still returned as written
     (legacy, already local).
   - `convert_shop_times_082(conn) -> int`: migration 082's `post_apply`
     (step 7).
2. **The 40 writers call `utc_now()`.** These are the 45 lines of S0-2,
   less five:
   - `_since_cutoff` (step 3);
   - `list_upcoming`'s cutoff, and the `actual_start` and `actual_end`
     stamps in `booking.py` (2) and `appointment_repo.py` (1), which keep
     275's shop clock.

   `booking.py`'s two `updated_at` stamps move.
3. **Cutoffs:**
   - `intake_repo._since_cutoff` becomes `utc_cutoff`, and its users
     compare `datetime(col) >= ?`: `list_intakes`, `count_intakes`,
     `list_work_orders` and `list_issues`.
   - `analytics._parse_date_window` returns `utc_cutoff(since)`, and its
     13 comparisons wrap the column in `datetime()`. A typed naive date is
     now the shop's day; until now it was read as UTC.
   - The 15 typed-`since` sites of S0-4 take `utc_cutoff` and
     `datetime(col)`. `learning_hook` takes a datetime, which is converted
     the same way.
4. **Windows on days:**
   - `financial_report`'s month, quarter or year;
   - the accounting export's `from_day..to_day`.

   Both become `datetime(issued_at) >= start(first) AND datetime(issued_at)
   < start(day after last)`, with `local_day_start`. The export's invoice
   date is the shop's day of `issued_at`. `throughput`'s
   `completions_by_day` groups in Python by the shop's day of each
   `completed_at`.
5. **Turnaround (condition 2):**
   - `turnaround` and `mechanic_performance` parse `opened_at` and
     `completed_at` with `stored_instant`, so a legacy naive value and a
     new aware one subtract.
   - The `except (ValueError, TypeError): continue` is removed. A value
     that cannot be parsed raises with the work order's id.
   - A test proves the mixed pair is counted, and another that a bad value
     fails loudly.
6. **Readers:**
   - `cli/shop.py`'s work-order, intake and issue show and list go
     through `local_display`;
   - so does the work-order report's Intake row (`reporting/builders.py`).
   - **The API** sends every `…_at` value of the shop dicts it returns in
     370's format, through one helper on the way out. That covers work
     orders, intakes, issues and customers in `api/routes/shop_mgmt.py`,
     and `VehicleResponse`'s two times. The OpenAPI types do not change,
     so gate 11's snapshot does not move.
7. **Migration 082** (`shop_times_utc`):
   - `upgrade_sql` is a comment.
   - `post_apply` is `motodiag.core.timestamps:convert_shop_times_082`. It
     applies `to_utc` to every naive-`T` value of the stamped columns:
     - customers, vehicles and work_orders;
     - issues, intake_visits and repair_plans;
     - appointments' `updated_at`;
     - shops, workflow_templates and customer_bikes;
     - users and performance_baselines.

     Space-shaped values (UTC) are left as written, and so are
     known_issues (2A) and appointments' clock columns. It returns the
     number of fields changed and is idempotent.
   - `rollback_sql` turns each `+00:00` value in those columns back into
     naive local with SQLite's `'localtime'` (370's rollback).
   - `SCHEMA_VERSION` 81 → 82.
8. **The deploy**, through the deploy skill:
   - `377_deploy_scope.json` names the three tables and the 40 fields,
     each with its `to` value from `377_live_rows_preview.out`;
   - `deploy.py dryrun 377`, and the exact diff committed;
   - **the operator approves that diff**, including 082's `schema_version`
     row, before `apply-live`. 2A chose the conversion; the diff is
     approved on its own.
9. **The mobile stop (3A):** a prompt for a mobile session, written to
   `moto-diag-mobile/docs/prompts/` and left uncommitted. In it,
   `buildWorkOrderSections` shows the five lifecycle times in the phone's
   local time with `new Date()`, as `SessionDetailScreen` already does.
   The merge waits for that session.

## Key Concepts

- **A text comparison needs one shape and one clock;** `datetime()` gives
  both, from any of the five shapes. A text comparison that is not wrapped
  is the defect; a census test lists the wrapped sites.
- **The clock seam is `core/timestamps.datetime`.** Every writer and
  cutoff here goes through it, so 370's `frozen_datetime` reaches them
  all.
- **The census test** (`tests/test_phase377_shop_utc.py`): no
  `datetime.now()` without a zone in `src/` outside a pinned list of four
  lines (appointments' clock times), with a planted line as its control.

## Verification Checklist

- [x] `tests/test_phase377_shop_utc.py`, on 370's frozen clock in
      `America/New_York`:
  - [x] `--since 30m` includes the last minute and excludes three hours
        ago, at 2026-10-06 23:26 EDT and at 2026-10-15 12:00 EDT, for
        intakes (list and count), work orders and issues, through the CLI
        and the repos
  - [x] a 30-day window's first day: completed at 09:00 EDT on the cutoff
        day is out, 13:00 EDT is in (throughput, turnaround, labour
        accuracy)
  - [x] completions by day, the P&L month and the export window use the
        shop's day: an invoice at 21:00 EDT on 2026-10-31 is October's
  - [x] every writer stamps 370's format at the frozen moment
  - [x] turnaround counts a legacy naive `opened_at` with a new
        `completed_at`, and an unparseable value raises
  - [x] readers: the CLI's work-order, intake and issue output and the
        report show local time; the API returns 370's format
  - [x] `utc_cutoff` and `local_day_start`: tokens, typed dates and
        offsets, and refusal of garbage
  - [x] migration 082: naive `T` converted, space and `None` untouched,
        known_issues untouched, idempotent, rollback to naive local
  - [x] the census: no unzoned `datetime.now()` outside the pinned four;
        a planted one fails it
- [x] `377_mutate.py`: every mutation red. M1 is the planted return to
      local time in `complete_work_order`.
- [x] 244G's scanner over the new test files
- [x] `wholetree.sh --full` on the committed HEAD; the regression of record
- [x] deploy: dry-run diff committed, the operator's approval, `apply-live`,
      the live diff
- [x] the mobile session's outcome
- [x] F186 and F191 closed

## Risks

- **Index use is lost** on wrapped columns. Live holds 6 work orders and 0
  intakes; a shop's tables are small.
- **A comparison added later without `datetime()`** compares as text
  again. The census test pins today's wrapped sites; it cannot see a new
  file.
- **The shop's zone is the server's** (F192).
- **Existing tests may assert naive shapes or UTC-read typed dates.** Four
  did, and they are listed in Results.
- **Rollback is lossy in microseconds** (370's).
- **F193:** the sensor-recording and drift filters still compare a typed
  value as text (Deviation 1).
- **Bay slots' scheduled times are clock times stored with `+00:00`**
  (275's rule). The overrun window's edge is off by the shop's offset for a
  slot with no `actual_end`; this is recorded in F192.

## Deviations from Plan

1. **Five typed-`since` comparisons left as they are, filed as F193.**
   v1.0 step 3 said all 15 of S0-4 take `utc_cutoff` and `datetime(col)`.
   Ten do. Five do not:
   - recorder 2, drift 2 and cli/advanced 1, which filter
     `sensor_samples` and `sensor_recordings`;
   - those columns hold one aware shape, so a typed date compares as a
     prefix;
   - the tables can be large, and wrapping the column would stop the index
     being used.
2. **Analytics had 15 comparisons, not 13.** Step 0's pattern missed the two
   bay-slot `COALESCE(...)` lines. Both are wrapped.
3. **`mechanic_performance` had the same silent skip as turnaround**
   (`except (ValueError, TypeError): pass`). It was found while editing and
   now raises through the same helper.
4. **The dashboard passes its `since` token to `revenue_rollup`,** not the
   computed cutoff. Otherwise `utc_cutoff` would read a UTC cutoff as local
   a second time. Its utilization days are now the shop's days.
5. **The export's due date keeps its own date.** `_us_date` gives an
   instant's day in the shop's zone. A due date is a calendar date (only
   the legacy invoice model writes it), so `_us_due_date` formats it as
   written. 275's Xero test caught this on 377's own code, before any
   commit.
6. **The census pins seven lines, not four:** the four appointment clock
   stamps, plus three prose lines (a docstring, and the descriptions of
   migrations 079 and 082). A first draft skipped lines starting with a
   quote and so dropped a real code line, `appointment_repo.py:122`; its
   own test went red on that, and the skip was replaced by names.
7. **The API connection dropped mid-build** (09:22). Nothing had been
   committed since v1.0. `git diff` was checked against the plan before
   the build carried on.

Not deviations, recorded for the reader:
- no bug fix was needed after a commit, so there is no register;
- no refute pass ran, because the phase ships code, tests and a data-only
  migration, not content rows.

## Results

| what | result |
|---|---|
| failures reproduced before the fix | F191 evening (3h-ago intake listed), F191 midday (last minute left out), F186 first day (2 counted, 1 expected) |
| writers | 40 stamps → `utc_now()`; 4 appointment clock stamps pinned by 275's rule |
| comparisons parsed | intake 2, work order 1, issue 1, analytics 15, invoicing 2, parts sourcing, labour estimator 2, workflow rules, parts needs, notifications, priority scorer, feedback; P&L and export windows by the shop's day |
| new tests | 32 (`tests/test_phase377_shop_utc.py`) |
| older tests changed (intended) | 171 `test_iso_input` (a typed time is local), 256 chokepoint pins (line moved; 082's converter, no `known_issues`), 292 gate 16 (noon EDT stored in UTC), 370 `local_display` (SQLite's UTC shown local) |
| mutation | 26/26 red (`377_mutate.out`); M1 the planted return to local time |
| 244G scanner | all of `tests/`: 0 hits |
| `wholetree.sh --full` | 4020 passed at `87f1fc8` (gate 11 included: snapshot unmoved) |
| `COLLECTED_TEST_FLOOR` | 10584 → 10617 (+32 new, +1 gate 15's rollback case for 082) |
| migration 082 dry run | 40 fields equal the preview (by script), +1 `schema_version`, no schema change, scope problems none |
| migration 082 live | applied with the operator's approval; live diff equals the approved exact diff; checked again backup-to-live by script; 5860 rows, integrity ok; backup `motodiag_pre377_20261007_112806.db` |
| the app | moto-diag-mobile `0074eb9` (prompt `40ddc4b`): the five lifecycle times through one shared formatter; jest 1197 passed in 99 suites, tsc 0, control red then green, no API types or snapshot changed |
| findings | F186, F191 closed; F192 (per-shop zone) and F193 (sensor and drift filters) filed |

Regression of record: 10617 passed, 0 failed, 0 skipped, 0 errors at `87f1fc8` (25 min 38 s wall, `python -m pytest -n auto --dist load`, exit 0)
