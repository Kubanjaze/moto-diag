# MotoDiag Phase 150 — Fleet Management

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-04-18

## Goal

Third Track F phase. Manage multiple bikes as named fleets (rental shops, demo fleets, race teams). Bikes can belong to 0+ fleets. `fleet status` rolls up Phase 148 predictions + Phase 149 wear (soft-guarded) + open diagnostic sessions.

CLI subgroup under existing `advanced` (nested `fleet` group):
- `fleet create <name> [--description]`, `list`, `show`, `rename`, `delete`
- `fleet add-bike <fleet> --bike SLUG [--role rental|demo|race|customer]`
- `fleet remove-bike <fleet> --bike SLUG`
- `fleet status <fleet> [--json] [--horizon-days 180] [--min-severity medium]`

**Design rule:** zero AI, zero tokens, one migration (018).

Outputs:
- Migration 018 (~90 LoC): `fleets` + `fleet_bikes` + 2 indexes.
- `advanced/fleet_repo.py` (~250 LoC) — 12 CRUD functions + 3 exceptions.
- `advanced/fleet_analytics.py` (~200 LoC) — `fleet_status_summary()`.
- `cli/advanced.py` +~350 LoC — nested `fleet` subgroup (8 subcommands).
- `advanced/__init__.py` +6 LoC exports.
- `tests/test_phase150_fleet.py` (~35 tests, 4 classes).

## Logic

### Migration 018

```sql
CREATE TABLE fleets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    owner_user_id INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (owner_user_id) REFERENCES users(id) ON DELETE SET DEFAULT,
    UNIQUE (owner_user_id, name)
);
CREATE INDEX idx_fleets_owner_name ON fleets(owner_user_id, name);

CREATE TABLE fleet_bikes (
    fleet_id INTEGER NOT NULL,
    vehicle_id INTEGER NOT NULL,
    role TEXT NOT NULL DEFAULT 'customer',
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (fleet_id, vehicle_id),
    FOREIGN KEY (fleet_id) REFERENCES fleets(id) ON DELETE CASCADE,
    FOREIGN KEY (vehicle_id) REFERENCES vehicles(id) ON DELETE CASCADE,
    CHECK (role IN ('rental','demo','race','customer'))
);
CREATE INDEX idx_fleet_bikes_vehicle ON fleet_bikes(vehicle_id);
```

Rollback: DROP junction then DROP fleets.

**CASCADE asymmetry:** vehicles has no FK to fleets → deleting a fleet drops junction rows but bikes survive (spec non-negotiable #3).

### fleet_repo.py

`create_fleet(name, description=None, owner_user_id=1, db_path=None) -> int` (raises `FleetNameExistsError` on duplicate), `get_fleet`, `get_fleet_by_name`, `list_fleets` (with `bike_count` via LEFT JOIN), `rename_fleet`, `update_fleet_description`, `delete_fleet`, `add_bike_to_fleet(fleet_id, vehicle_id, role='customer')` (raises `BikeAlreadyInFleetError`), `remove_bike_from_fleet`, `set_bike_role`, `list_bikes_in_fleet` (JOIN vehicles — returns vehicle dict + role + added_at), `list_fleets_for_bike`.

Exceptions: `FleetNotFoundError`, `FleetNameExistsError`, `BikeAlreadyInFleetError` (all `ValueError` subclasses).

`_resolve_fleet(identifier)` accepts int (id) or str (name).

### fleet_analytics.py

`fleet_status_summary(fleet_id, horizon_days=180, min_severity=None, db_path=None) -> dict`:

```python
{
  "fleet": {id, name, description, bike_count},
  "bikes": [{vehicle_id, make, model, year, role, mileage,
             prediction_count, critical_prediction_count,
             top_prediction, wear_percent, open_sessions}, ...],
  "totals": {total_predictions, critical_predictions, bikes_with_open_sessions,
             bikes_with_critical, average_wear_percent},
  "horizon_days", "min_severity", "phase149_available": bool
}
```

Flow: for each bike → call Phase 148 `predict_failures` → count; Phase 149 soft-guarded via `importlib.util.find_spec("motodiag.advanced.wear")` cached at module-load; open sessions via `SELECT COUNT(*) FROM diagnostic_sessions WHERE vehicle_id=? AND status='open'`.

### CLI subgroup

Append inside existing `register_advanced`:
```python
@advanced_group.group("fleet")
def fleet_group(): ...
```

8 subcommands. Each: `init_db()`, resolve, call repo/analytics, render Rich Table + Panel OR `--json`. `delete --force` skips confirm prompt. Role uses `click.Choice`.

`fleet status` Rich output: per-bike table (Bike / Role / Predictions / Critical / Top issue / Wear% / Open sessions) + totals Panel. Red critical, dim `—` on wear when Phase 149 absent.

## Key Concepts

- **Junction PK** `(fleet_id, vehicle_id)` enforces non-duplicate (bike, fleet) pairs while allowing bikes in multiple fleets.
- **CASCADE asymmetry** preserves bikes on fleet delete.
- **Phase 149 soft-guard** via `find_spec` — Phase 150 ships before 149; 149 lights up automatically when it lands.
- **UNIQUE (owner_user_id, name)** scopes fleet names per user without global collision.
- **Click nested group** `@advanced_group.group("fleet")` — append-only pattern Phase 148 established.

## Verification Checklist

- [ ] Migration 018 bumps v17→v18; rollback drops both tables.
- [ ] `fleets.UNIQUE(owner, name)` violation → IntegrityError.
- [ ] Delete fleet → junction rows gone, vehicles survive.
- [ ] Delete vehicle → junction rows gone, fleet survives.
- [ ] `role` CHECK rejects invalid values.
- [ ] `add_bike_to_fleet` twice → `BikeAlreadyInFleetError`.
- [ ] `list_fleets_for_bike` returns ≥2 for shared bike.
- [ ] `fleet_status_summary` Phase 149 soft-guard: False today, True when 149 lands.
- [ ] CLI happy paths + mutex + invalid role + empty panel.
- [ ] `fleet delete --force` skips prompt; without force prompts.
- [ ] Phase 148 + Phase 112 regressions green.

## Risks

- **`current_user` scoping placeholder.** `owner_user_id=1` default replicates migrations 005/011/015/016 pattern. Phase 112 session threading is long-term fix.
- **Phase 149 soft-guard** is dead code until 149 lands. Test via monkeypatch of `_HAS_WEAR` + stub.
- **Phase 148 cost per bike × fleet size.** Acceptable for N≤50; caching in Phase 155+.
- **Migration 018 collision** with Phase 149. Communicate "150 owns 018" to 149 planner.
