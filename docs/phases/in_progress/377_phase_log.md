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
