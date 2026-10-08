# Phase 379 — Small fixes from the open-findings triage

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-10-08 (v1.0 the same day)

**Outcome (v1.1).** All nine closed, each with a test that fails without it. F199 and F200 filed. Regression 10769 passed / 0 failed at `7be2337`. No live rows, no migration, no mobile session.

---

## Goal

Section B of `docs/reports/2026-10-08_open_findings_triage.md`: nine small
fixes, code and tests only, no live rows. The operator: "379 = the nine
small fixes." Each finding closes with its fix and a test that fails
without it. The decisions are in `379_step0.md`, S0-2.

## Logic

- **F197:** `deploy.py verify-live` exits 3 when live does not equal the
  approved diff, and says whether live's schema version is above the
  phase's own (then a later migration explains it). verify_phase's check 8
  sets a failure on any exit but 0 or 2, and the script exits 1 at its
  end. Test: an approved diff missing one live row turns `verify-live` red
  (3), and check 8's handling is held by a test and a mutation.
- **F176:** `vehicles.registry.vehicle_dependents(vehicle_id)` returns,
  for each table whose foreign key to `vehicles` blocks a delete
  (`RESTRICT` or `NO ACTION`, from the schema), the count of rows naming
  the bike. `delete_vehicle` raises `VehicleInUse` with them; `garage
  remove` prints which and exits 1. Tests: a work order, a saved run, an
  intake, a session; a bike with none deletes as before.
- **F193:** `core.timestamps.column_cutoff(value)` is `utc_cutoff` in the
  columns' shape (`YYYY-MM-DDTHH:MM:SS+00:00`). It is used by
  `list_recordings` and both drift queries. Tests on a fixed clock in New
  York:
  - a typed date means the shop's day;
  - an offset converts;
  - a sample exactly on the bound matches;
  - the query plan still uses the index.
- **F154:** a lookup entry `SYM Fiddle 50` (`fiddle 50`, `fiddle50`), CVT,
  citing the Fiddle 50 service manual's cover and specification table.
  Gate 14's two F154 pins are inverted: the Fiddle 50 resolves
  `model-sourced`/`cvt` and its prompt holds the scoped CVT rows.
- **F155:** `relevance_tokens` stems plurals by S0-2's rule. Gate 14's F155
  pin is inverted: the LX 50 keeps its carburettor row with a belt
  symptom. Ranking before and after is measured and recorded.
- **F131:** `resolve_transmission` also matches each entry's own
  `canonical`. A guard requires every entry's canonical name to resolve to
  that entry. 255B's six-gap pin is inverted. F199 is filed for the Like
  50i and 125.
- **F140:** a test builds the database the loader and migrations build
  (`init_db` plus every seed file) and asserts no `known_issues` row
  declares `manual`. A planted row in a fixture database fails it.
- **F173:** `wholetree.py` writes pytest's whole output to
  `.git/motodiag_wholetree/last_<mode>.log`. On failure it prints every
  FAILED or ERROR line and the log's path. F173 closes on the count of
  regressions of record since 359 in which the test passed.
- **F144:** `VehicleContext.powertrain`, filled by `_build_vehicle_context`
  from the vehicle row. `/ask` passes it. Test: an unset electric vehicle
  resolves `powertrain-default` through `/ask`'s retrieval, and an `ice`
  one resolves as before.

## Non-goals

Sections C–F; any live row; Like 50i/125 coverage (F199); the other
verify_phase checks' exit codes.

## Planned items

- [x] F197, F176, F193, F154, F155, F131, F140, F173, F144, each with its test
- [x] gate 14 and 255B pins inverted; F199 filed
- [x] mutations, the floor, the regression, the close-out, the handoff

## Deviations from Plan

1. **F155's effect was wider than the triage said** ("one line; Gate 14
   pins it"): 51 of 132 measured prompts changed, about 19 swaps better
   and 5 worse. It shipped, because it is the approved fix and its net is
   positive, and the scorer's word-sense noise was filed as F200 (D1 in
   the log).
2. **F154 became its own lookup entry,** cited to a SYM Fiddle 50 service
   manual found on disk, not an alias on the Fiddle III entry (Step 0
   S0-2).
3. **F176 counts five tables, not two,** from the schema.
4. **F131's pin no longer existed,** so the guard over every entry replaces
   it. Its side gap moved to F199 before F131 closed.
5. **Two older pins moved:** 250B's token pin and 256's line-number pin
   (D3).
6. **Step 0 first cited F199 before it was filed;** B2 refused the commit,
   and it was filed first.
7. **F140 has no mutation:** the check is a test, with a planted row as its
   control.

Not deviations: no bug fix after a commit; no migration; no refute pass.

## Results

| finding | closed by | test |
|---|---|---|
| F197 | verify-live exit 3; check 8 fails verify_phase | `test_phase379_verify_live_fails.py` (6) |
| F176 | `vehicle_dependents`, `VehicleInUse`; `garage remove` exits 1 | `test_phase379_garage_remove.py` (8) |
| F193 | `column_cutoff` in the recorder and drift | `test_phase379_sensor_windows.py` (5) |
| F154 | `SYM Fiddle 50` entry | `test_phase379_lookup_and_relevance.py`, gate 14 |
| F155 | `_singular` in `relevance_tokens` | same, gate 14 |
| F131 | canonical names match | same (20 in all) |
| F140 | a built-database check | `test_phase379_no_manual_rows.py` (2) |
| F173 | whole output kept; 19 regressions with 0 failed | `test_phase379_wholetree_output.py` (2) |
| F144 | `VehicleContext.powertrain` | `test_phase379_ask_powertrain.py` (3) |

- Mutations 16/16 red; 244G scanner 0 hits; floor 10723 → 10769.
- `wholetree.sh --full` 4091 passed at `7be2337`.

Regression of record: 10769 passed, 0 failed, 0 skipped, 0 errors at `7be2337` (24 min 31 s wall, `python -m pytest -n auto --dist load`, exit 0)

## Risks

- **F155 moved ranking for many prompts;** five measured swaps are worse
  (F200).
- **verify_phase exits 1 for a past phase whose live state later
  migrations changed;** check 8 says when that is the cause.
