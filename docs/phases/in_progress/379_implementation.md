# Phase 379 — Small fixes from the open-findings triage

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-10-08

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

- [ ] F197, F176, F193, F154, F155, F131, F140, F173, F144, each with its test
- [ ] gate 14 and 255B pins inverted; F199 filed
- [ ] mutations, the floor, the regression, the close-out, the handoff
