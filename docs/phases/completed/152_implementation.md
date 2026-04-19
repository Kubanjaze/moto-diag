# MotoDiag Phase 152 — Service History Tracking + vehicles.mileage

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-19

## Goal

Fifth Track F phase. Persistent service-history log per bike. Closes Phase 148 mileage deferral by adding `vehicles.mileage` column as source of truth. Every oil/tire/valve/brake/diagnostic/recall event logged. Wires DB-sourced mileage into Phase 148 predictor (`+0.05` confidence bonus) and Phase 151 `schedule complete` mileage default.

CLI: `motodiag advanced history {add, list, show, show-all, by-type}` + `garage update --bike SLUG [--mileage N] [--notes] [--vin]`.

**Design rule:** additive migration, no seed content, no AI, zero tokens. Phase 148 regression untouched.

Outputs:
- Migration 020 (next available integer): `ALTER vehicles ADD COLUMN mileage INTEGER NULL` + new `service_history` table + 3 indexes.
- `advanced/models.py` +~30 LoC — `ServiceEvent` Pydantic v2 with Literal event_type.
- `advanced/history_repo.py` (~220 LoC) — 7 CRUD functions. `add_service_event` monotonically bumps `vehicles.mileage`.
- `cli/advanced.py` +~250 LoC — nested `history` subgroup (5 subcommands).
- `cli/main.py` +~60 LoC — new `garage update` subcommand with monotonic-mileage guard (decrease requires `--yes`).
- `vehicles/registry.py` +~5 LoC — "mileage" added to `update_vehicle.allowed`.
- `advanced/predictor.py` +~15 LoC — `+0.05` confidence bonus when `vehicle["mileage_source"] == "db"`.
- `tests/test_phase152_history.py` (~35 tests, 5 classes).

## Logic

### Migration 020

```sql
ALTER TABLE vehicles ADD COLUMN mileage INTEGER NULL;

CREATE TABLE service_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vehicle_id INTEGER NOT NULL,
    event_type TEXT NOT NULL,
    at_miles INTEGER,
    at_date TEXT NOT NULL,            -- ISO-8601
    notes TEXT,
    cost_cents INTEGER,
    mechanic_user_id INTEGER,
    parts_csv TEXT,
    completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (vehicle_id) REFERENCES vehicles(id) ON DELETE CASCADE,
    FOREIGN KEY (mechanic_user_id) REFERENCES users(id) ON DELETE SET NULL,
    CHECK (event_type IN ('oil-change','tire','valve-adjust','brake',
                          'diagnostic','recall','chain','coolant',
                          'air-filter','spark-plug','custom'))
);
CREATE INDEX idx_service_history_vehicle ON service_history(vehicle_id, at_date DESC);
CREATE INDEX idx_service_history_type ON service_history(event_type, at_date DESC);
CREATE INDEX idx_service_history_date ON service_history(at_date DESC);
```

Rollback: DROP service_history + indexes. `vehicles.mileage` stays (SQLite pre-3.35 DROP COLUMN caveat — inert, documented).

### Models

```python
class ServiceEvent(BaseModel):
    id: int | None = None
    vehicle_id: int
    event_type: Literal["oil-change","tire","valve-adjust","brake",
                        "diagnostic","recall","chain","coolant",
                        "air-filter","spark-plug","custom"]
    at_miles: int | None = None
    at_date: date
    notes: str | None = None
    cost_cents: int | None = None
    mechanic_user_id: int | None = None
    parts_csv: str | None = None
    completed_at: datetime | None = None
```

### history_repo.py

7 functions: `add_service_event` (insert + monotonic bump `vehicles.mileage` in same txn via `UPDATE vehicles SET mileage=? WHERE id=? AND (mileage IS NULL OR mileage<?)`), `get_service_event`, `list_service_events` (filters: since/until/event_type/limit), `list_all_service_events` (cross-bike), `list_by_type`, `count_service_events`, `delete_service_event`.

### CLI

Nested `history` group inside `register_advanced`. 5 subcommands with Rich Table (Date/Type/Miles/Cost/Mechanic/Parts/Notes) + `--json`. `history add` supports `--type`, `--at-miles`, `--at-date` (default today), `--notes`, `--cost-cents`, `--mechanic` (resolves username via `auth.user_repo` if available; NULL fallback), `--parts` (comma SKUs).

`garage update --bike SLUG [--mileage N]` in `cli/main.py` (NOT in advanced.py — stays with other garage commands). Decrease guard: N < current requires `--yes`.

### Phase 148 integration

In `cli/advanced.py::predict_cmd`:
```python
if bike:
    db_mileage = vehicle.get("mileage")
    if current_miles is not None:
        vehicle["mileage"] = int(current_miles)
        vehicle["mileage_source"] = "flag"  # user-asserted wins
    elif db_mileage is not None:
        vehicle["mileage_source"] = "db"    # verified source (+0.05 bonus)
```

In `advanced/predictor.py::_build_prediction`, after existing mileage bonus:
```python
if current_mileage is not None and vehicle.get("mileage_source") == "db":
    score += 0.05
```

**Compatibility:** flag wins over DB (user override for cluster replacements). Phase 148 44-test regression identical when flag passed (source="flag" → no bonus).

### Phase 151 integration

Phase 152 does NOT touch `scheduling/` code. Phase 152 exposes `vehicles.mileage` for Phase 151 to read via `get_vehicle(vid)["mileage"]` default for `--at-miles`.

## Key Concepts

- **Persistent mileage = source of truth.** `vehicles.mileage` monotonically bumped by service_history inserts.
- **Flag wins over DB.** User override preserved.
- **Event type CHECK-gated.** 11 values in both Literal model + CHECK constraint.
- **Monotonic guard.** Service history never decreases; garage update decrease requires `--yes`.
- **FK cascade policy.** vehicle_id CASCADE, mechanic_user_id SET NULL (Phase 145 pattern).
- **No seed data.** Empty on day 1; populates organically.
- **Phase 148 regression untouched.** Source="flag" → no bonus → identical scores.

## Verification Checklist

- [x] Migration 020 applies cleanly to Phase 148-state DB.
- [x] `vehicles.mileage` INTEGER NULL, accepts 0 and 999999.
- [x] CHECK rejects unknown event types.
- [x] FK cascade: delete vehicle → history gone; delete user → mechanic NULL.
- [x] `add_service_event` at_miles > current bumps vehicles.mileage.
- [x] `add_service_event` at_miles < current does NOT decrease.
- [x] `garage update --mileage` persists; decrease requires `--yes`.
- [x] CLI happy paths + remediation + `--json` round-trip.
- [x] Phase 148 `--current-miles` identical to Phase 148 baseline.
- [x] Phase 148 `--bike` with DB mileage shows +0.05 bonus in JSON.
- [x] Phase 148 + Phase 140 + Phase 12 + Phase 08 regressions green.

## Risks

- **Migration slot** — next integer at build time.
- **`+0.05` bonus double-count risk** with future Phase 149 verified_by filter. Acceptable — orthogonal signals.
- **Mechanic username lookup** soft-couples to Phase 112 auth. NULL fallback with yellow warning.
- **Monotonic rule breaks cluster replacements.** `--yes` escape. Alternative `garage reset-mileage` Phase 153+.
- **Phase 151 not land-synchronized.** Phase 152 doesn't import from scheduling/; exposes column for 151 to read.
- **Empty table on day 1** — expected; `diagnose` auto-log deferred to Phase 153.
- **Event type list evolution** — 11 values baseline. Growth requires paired migration + Literal update.

## Deviations from Plan

- Test count 35 on target (TestMigration020×4, TestHistoryRepo×10, TestHistoryCLI×12, TestPhase148IntegrationBonus×5, TestRegression×4).
- Bug fix #1: `TestPhase148IntegrationBonus` fixture was using `exact_model` match tier that saturated at the [0.0, 1.0] clamp ceiling, making the +0.05 DB bonus invisible. Fixture rewritten to use family-make tier so the bonus is observable as a clean 0.05 delta.

## Results

| Metric | Value |
|--------|-------|
| Tests | 35 GREEN |
| LoC delivered | ~541 (history_repo.py 291 + cli/advanced.py +250) |
| Bug fixes | 1 |
| Commit | `68f65f4` |

Phase 152 closes Phase 148's mileage deferral by adding a persistent `vehicles.mileage` column (source of truth) and a service-history event log. The +0.05 DB-sourced mileage bonus in the Phase 148 predictor makes DB-verified mileage observably preferable to user-flag assertion, giving mechanics a quiet reward for keeping the log populated.
