# MotoDiag Phase 151 — Service-Interval Scheduling

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-04-18

## Goal

Fourth Track F phase. Track OEM-recommended maintenance intervals per bike (oil/valve/chain/coolant/brake-fluid etc.) — dual-axis (miles OR months, whichever first). Surface upcoming + overdue items.

CLI: `motodiag advanced schedule {init, list, due, overdue, complete, history}`.

**Design rule:** pure SW + SQL + static JSON. Zero AI. One migration (019).

Outputs:
- Migration 019 (v18→v19): `service_intervals` + `service_interval_templates` + 3 indexes.
- `advanced/data/service_interval_templates.json` — ~44 canonical rows (Harley 10, Honda 7, Yamaha 6, Kawasaki 5, Suzuki 4, KTM 3, Ducati 2, BMW 2, universal 5).
- `advanced/models.py` +~40 LoC: `ServiceInterval` Pydantic v2.
- `advanced/schedule_repo.py` (~220 LoC): CRUD + `load_templates_from_json` + `seed_from_template`.
- `advanced/scheduler.py` (~150 LoC): `next_due_calc`, `due_items`, `overdue_items`, `record_completion`.
- `cli/advanced.py` +~300 LoC: nested `schedule` subgroup (6 commands).
- `tests/test_phase151_schedule.py` (~35 tests, 4 classes).

## Logic

### Migration 019

```sql
CREATE TABLE service_intervals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vehicle_id INTEGER NOT NULL,
    item_slug TEXT NOT NULL,          -- "oil-change"
    description TEXT NOT NULL,
    every_miles INTEGER,              -- NULL = time-only
    every_months INTEGER,             -- NULL = mileage-only
    last_done_miles INTEGER,
    last_done_at TEXT,                -- ISO-8601
    next_due_miles INTEGER,
    next_due_at TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (vehicle_id) REFERENCES vehicles(id) ON DELETE CASCADE,
    UNIQUE (vehicle_id, item_slug),
    CHECK (every_miles IS NOT NULL OR every_months IS NOT NULL)
);
CREATE INDEX idx_svc_int_vehicle ON service_intervals(vehicle_id);
CREATE INDEX idx_svc_int_next_due ON service_intervals(next_due_at);

CREATE TABLE service_interval_templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    make TEXT NOT NULL,               -- "harley-davidson" / "*" wildcard
    model_pattern TEXT NOT NULL,      -- SQL LIKE: "Sportster%" / "%"
    item_slug TEXT NOT NULL,
    description TEXT NOT NULL,
    every_miles INTEGER,
    every_months INTEGER,
    notes TEXT,
    CHECK (every_miles IS NOT NULL OR every_months IS NOT NULL)
);
CREATE INDEX idx_svc_tpl_make_model ON service_interval_templates(make, model_pattern);
```

### Templates JSON (anchor examples)

```json
[
  {"make": "harley-davidson", "model_pattern": "%",
   "item_slug": "oil-change", "description": "Engine + primary oil change",
   "every_miles": 5000, "every_months": 12,
   "notes": "HD 2017+ service manual — 20W-50 HD oil."},
  {"make": "yamaha", "model_pattern": "YZF-R1%",
   "item_slug": "valve-check", "description": "Valve clearance inspection",
   "every_miles": 26600, "every_months": null,
   "notes": "Yamaha R1 service manual — 42,800 km."},
  {"make": "kawasaki", "model_pattern": "KLR%",
   "item_slug": "doohickey-check", "description": "Balancer doohickey inspection",
   "every_miles": 15000, "every_months": null,
   "notes": "KLR650 forum consensus — critical failure."},
  {"make": "*", "model_pattern": "%",
   "item_slug": "brake-fluid-flush", "description": "Brake fluid flush",
   "every_miles": null, "every_months": 24,
   "notes": "Universal DOT-4 hygroscopic 2-year rule."},
  {"make": "*", "model_pattern": "%",
   "item_slug": "chain-clean-lube", "description": "Chain clean + lube",
   "every_miles": 1000, "every_months": null,
   "notes": "Universal — skip for belt/shaft drive."}
]
```

Builder fleshes to 44 total.

### scheduler.py

`next_due_calc(interval, *, done_miles, done_at, current_miles) -> tuple[int|None, str|None]` — computes next_due via miles + month arithmetic. Month addition via `datetime.replace(month=...)` with `calendar.monthrange` day-clamp (Feb 28 + 2 months = Apr 28, Jan 31 + 1 month = Feb 28/29).

`due_items(vehicle_id, *, horizon_miles=500, horizon_days=30, current_miles=None, db_path=None)` — includes rows where `miles_remaining <= horizon_miles` OR `days_remaining <= horizon_days`, excludes overdue.

`overdue_items(vehicle_id, *, current_miles=None, db_path=None)` — negative remaining, most-overdue first.

`record_completion(vehicle_id, item_slug, *, at_miles=None, at_date=None, db_path=None) -> dict`:
- If neither `at_miles` nor `at_date`, read `vehicles.mileage` via try/except `OperationalError` (Phase 152 soft-dep).
- Update `last_done_*` + recompute `next_due_*`.
- Try `INSERT INTO service_history` (Phase 152 soft-dep, swallow table-missing exception).

### CLI

Append inside `register_advanced`:
```python
@advanced_group.group("schedule")
def schedule_group(): ...
```

6 subcommands. Each: `init_db()` → resolve bike via `_resolve_bike_slug` → call scheduler → Rich Table + `--json`. Rich columns for due/overdue: Item / Description / Every / Last done / Next due / Miles to go / Days to go. Red negative values, cyan imminent (< 20% of interval).

**Zero `cli/main.py` delta** — appends inside existing Phase 148 `register_advanced`.

## Key Concepts

- **Template → instance materialization** mirrors Phase 145 `obd_adapters → adapter_compatibility`.
- **Dual-axis due arithmetic** (miles OR months, first-reached wins).
- **Phase 152 soft-dep via try/except** (no import guards). Free persistence when 152 lands.
- **Month-end day-clamp** via `calendar.monthrange`.
- **Zero cli/main.py churn.**

## Verification Checklist

- [ ] Migration 019 bumps v18→v19; rollback drops both tables.
- [ ] `load_templates_from_json` loads 44 rows idempotently.
- [ ] `seed_from_template` skips existing slugs on re-run.
- [ ] `next_due_calc` miles-only / months-only / dual-axis.
- [ ] Month-end clamp: Feb 28 + 2 months = Apr 28, Jan 31 + 1 month = Feb 28/29.
- [ ] `due_items` + `overdue_items` never overlap.
- [ ] `record_completion` without mileage source raises clear error.
- [ ] All 6 subcommands work + Phase 125 remediation on unknown bike.
- [ ] `--json` round-trip.
- [ ] Phase 148 + Phase 145 regressions green.

## Risks

- **Migration numbering race** with Phase 150. Builder claims next-available integer at build time.
- **Phase 152 soft-dep shape mismatch** — if 152's `service_history` schema differs, try/except INSERT silently fails. Cross-check in 152 review.
- **Month arithmetic corner cases** (Jan 31 + 1 month). `calendar.monthrange` clamp tested.
- **Template coverage uneven** — European OEMs thin. Content, not bug.
- **CLI LoC ~300** tight — if stretches to 400, split into `cli/schedule.py` + helper registrar.
