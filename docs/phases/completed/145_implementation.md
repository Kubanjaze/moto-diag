# MotoDiag Phase 145 — Adapter Compatibility Database

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-18

## Goal

Seed + query a knowledge base of OBD adapter capabilities vs motorcycle compatibility. Mechanic asks "will my $30 ELM327 Bluetooth clone actually work on my 2011 Road Glide?" → this phase answers: `partial — Mode 03 works via CAN, bi-directional + HD-proprietary PIDs do not. Dynojet Power Vision ($400) gives full bidirectional on same bike.` Foundation for Phase 146 `diagnose --bike` hints.

CLI: `motodiag hardware compat {list,recommend,check,show,note add,note list,seed}`

Outputs:
- Migration 017 (schema v16 → v17) — 3 tables + 6 indexes.
- `src/motodiag/hardware/compat_repo.py` (~280 LoC) — CRUD + query API + `protocols_to_skip_for_make`.
- `src/motodiag/hardware/compat_loader.py` (~120 LoC) — idempotent JSON seeder with line-aware errors.
- `src/motodiag/hardware/compat_data/{adapters,compat_matrix,compat_notes}.json` — 20-30 adapters, 100+ matrix rows, ~10 curated notes.
- `src/motodiag/cli/hardware.py` +~350 LoC (new `compat` subgroup). Additive only.
- `src/motodiag/hardware/ecu_detect.py` +~15 LoC — one new `compat_repo=None` kwarg on `AutoDetector.__init__` + filter hook.
- `tests/test_phase145_compat.py` (~57 tests across 7 classes).

Schema version 16 → 17 (assumes 142 ships 016 first; amend if slips).

## Logic

### Migration 017

```sql
CREATE TABLE obd_adapters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    slug TEXT NOT NULL UNIQUE,
    brand TEXT NOT NULL, model TEXT NOT NULL,
    chipset TEXT NOT NULL,                 -- ELM327/STN1110/STN2100/ELS27/native-CAN/proprietary
    transport TEXT NOT NULL,               -- bluetooth/usb/wifi/obd-dongle/bridge
    price_usd_cents INTEGER NOT NULL DEFAULT 0,
    purchase_url TEXT,
    supported_protocols_csv TEXT NOT NULL, -- 'ISO 15765,ISO 14230,J1850 VPW,ISO 9141'
    supports_bidirectional INTEGER NOT NULL DEFAULT 0,  -- 0/1
    supports_mode22 INTEGER NOT NULL DEFAULT 0,
    reliability_1to5 INTEGER NOT NULL DEFAULT 3,
    known_issues TEXT, notes TEXT,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CHECK (reliability_1to5 BETWEEN 1 AND 5),
    CHECK (price_usd_cents >= 0),
    CHECK (supports_bidirectional IN (0, 1)),
    CHECK (supports_mode22 IN (0, 1))
);
CREATE INDEX idx_obd_adapters_slug    ON obd_adapters(slug);
CREATE INDEX idx_obd_adapters_chipset ON obd_adapters(chipset);

CREATE TABLE adapter_compatibility (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    adapter_id INTEGER NOT NULL,
    vehicle_make TEXT NOT NULL,
    vehicle_model_pattern TEXT NOT NULL,   -- SQL LIKE: 'CBR%', 'touring%'
    year_min INTEGER, year_max INTEGER,    -- both nullable = applies to all years
    status TEXT NOT NULL,                  -- full|partial|read-only|incompatible
    notes TEXT, verified_by TEXT,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (adapter_id) REFERENCES obd_adapters(id) ON DELETE CASCADE,
    CHECK (status IN ('full','partial','read-only','incompatible'))
);
CREATE INDEX idx_compat_make_model ON adapter_compatibility(vehicle_make, vehicle_model_pattern);
CREATE INDEX idx_compat_make_year  ON adapter_compatibility(vehicle_make, year_min, year_max);
CREATE INDEX idx_compat_adapter    ON adapter_compatibility(adapter_id);

CREATE TABLE compat_notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    adapter_id INTEGER NOT NULL,
    vehicle_make TEXT NOT NULL,            -- lowercase; '*' for any
    note_type TEXT NOT NULL,               -- quirk|workaround|known-failure|tip
    body TEXT NOT NULL,
    source_url TEXT, submitted_by_user_id INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (adapter_id) REFERENCES obd_adapters(id) ON DELETE CASCADE,
    FOREIGN KEY (submitted_by_user_id) REFERENCES users(id) ON DELETE SET DEFAULT,
    CHECK (note_type IN ('quirk','workaround','known-failure','tip'))
);
CREATE INDEX idx_compat_notes_adapter_make ON compat_notes(adapter_id, vehicle_make);
```

Rollback: `DROP compat_notes; DROP adapter_compatibility; DROP obd_adapters;` (FK-safe child-first).

SCHEMA_VERSION 16 → 17 (assumes 142 ships 016).

### compat_repo.py API

All functions take optional `db_path=None` last kwarg (dtc_repo pattern).

```python
def add_adapter(slug, brand, model, chipset, transport, price_usd_cents,
                supported_protocols_csv, supports_bidirectional=False,
                supports_mode22=False, reliability_1to5=3, purchase_url=None,
                known_issues=None, notes=None, db_path=None) -> int
def get_adapter(slug, db_path=None) -> dict | None
def list_adapters(chipset=None, transport=None, db_path=None) -> list[dict]
def update_adapter(slug, db_path=None, **fields) -> bool
def remove_adapter(slug, db_path=None) -> bool  # CASCADE wipes compat + notes

def add_compatibility(adapter_slug, make, model_pattern, status,
                      year_min=None, year_max=None, notes=None, verified_by=None,
                      db_path=None) -> int

def list_compatible_adapters(make, model, year=None, min_status='read-only',
                             db_path=None) -> list[dict]
# Normalizes make lowercase; LIKE on model_pattern; year range filter;
# min_status excludes weaker entries (default excludes 'incompatible').
# ORDER BY status_tier (full=0/partial=1/read-only=2/incompatible=3) ASC,
# reliability DESC, price ASC, adapter_id ASC.

def check_compatibility(adapter_slug, make, model, year=None, db_path=None) -> dict | None
# Most-specific match wins: exact-pattern > wildcard; narrower year > wider;
# added_at DESC breaks ties. None = unknown (not same as 'incompatible').

def add_compat_note(adapter_slug, make, note_type, body, source_url=None,
                    submitted_by_user_id=1, db_path=None) -> int
def get_compat_notes(adapter_slug, make=None, db_path=None) -> list[dict]
# When make specified, returns rows matching make OR wildcard '*'.

def protocols_to_skip_for_make(make, db_path=None) -> set[str]
# AutoDetector hook. Returns protocols where NO compat row marks them
# supported + status != 'incompatible' for this make. Conservative:
# empty set when <3 compat rows exist for the make (sparse data, don't filter).
# Maps supported_protocols_csv tokens to {'CAN','KLINE','J1850','ELM327'}.
```

Reliability clamped `[1..5]`; out-of-range → ValueError. `price_usd_cents` int-only; float → TypeError.

### compat_loader.py

```python
def load_adapters_file(path, db_path=None) -> int
def load_compat_matrix_file(path, db_path=None) -> int
def load_compat_notes_file(path, db_path=None) -> int
def seed_all(data_dir=None, db_path=None) -> dict[str, int]
```

Idempotent: `add_adapter` uses INSERT OR IGNORE; `add_compatibility` checks natural-key before insert. Malformed JSON → ValueError with filename:line:col.

Does NOT auto-seed on `init_db` (test-DB pollution avoidance). Explicit `motodiag hardware compat seed` or Python API.

### Seed data coverage (20-30 adapters across 5 price tiers)

Tier 1 ($10-30): 2-3 generic ELM327 clones. Tier 2 ($30-80): OBDLink LX, Vgate iCar Pro, BAFX, ScanTool OBDLink SX. Tier 3 ($80-200): OBDLink MX+, ELS27, Autel AP200BT, Foxwell NT301. Tier 4 ($200-500): Dynojet Power Vision 3, Daytona Twin Tec TCFI, Vance & Hines Fuelpak FP4, SEPro. Tier 5 ($500+): HD Digital Tech II clones, OEM dealer tools. Plus 1 `motodiag-mock` for Phase 144 sim.

Matrix coverage (100+ entries): Harley Touring/Sportster/Softail/Dyna/V-Rod × 1996-2025; Honda CBR/VFR/Shadow/Gold Wing; Yamaha R1/R6/FZ/MT; Kawasaki ZX/Ninja/Versys; Suzuki GSX-R/SV/Bandit; BMW S1000RR/R1200GS; Ducati 1199/Monster; KTM 1290/690; Triumph 675/Tiger. Mix of full/partial/read-only/incompatible. Citations in `verified_by` for high-stakes rows.

### Adapter JSON example
```json
{
  "slug": "obdlink-mx-plus",
  "brand": "OBDLink", "model": "MX+ Bluetooth",
  "chipset": "STN2100", "transport": "bluetooth",
  "price_usd_cents": 13999,
  "purchase_url": "https://www.obdlink.com/products/obdlink-mxp/",
  "supported_protocols_csv": "ISO 15765,ISO 14230,ISO 9141,J1850 VPW,J1850 PWM",
  "supports_bidirectional": false, "supports_mode22": true,
  "reliability_1to5": 5,
  "known_issues": "BT pairing flaky on Windows 11 Home — use USB-BT dongle if onboard radio misbehaves.",
  "notes": "STN2100 superset of ELM327. Shop favorite for multi-make work."
}
```

### CLI `compat` subgroup (7 subcommands)

1. **`compat list [--chipset X] [--transport Y] [--json]`** — Rich Table: Brand/Model/Chipset/Transport/Price/BiDir/Mode22/Reliability. Sort by brand, model.
2. **`compat recommend --bike SLUG | (--make M --model Md [--year Y]) [--min-status STATUS] [--limit N]`** — Ranked list grouped by status tier (Full → Partial → Read-only). Bike-slug via `_resolve_bike_slug`. Unknown bike → yellow "No compat entries known; run `compat list` and contribute via `compat note add`."
3. **`compat check --adapter SLUG (--bike SLUG | --make --model [--year])`** — single verdict Rich Panel color-coded (green=full, cyan=partial, yellow=read-only, red=incompatible, dim=unknown). Shows notes + verified_by + "Related notes:" section.
4. **`compat show --adapter SLUG`** — full adapter detail + nested compat table.
5. **`compat note add --adapter SLUG --make MAKE --type TYPE "body" [--source URL]`** — validated via Click `click.Choice` on type. Body positional or `'-'` for stdin.
6. **`compat note list --adapter SLUG [--make MAKE] [--type TYPE]`** — Rich Table.
7. **`compat seed [--data-dir PATH] [--yes]`** — idempotent loader invocation. Summary: "Loaded N adapters, M compat entries, P notes. Skipped Q duplicates."

All subcommands call `init_db()` first, use `get_console()`, `ICON_*`.

### AutoDetector integration

```python
class AutoDetector:
    def __init__(self, port, baud=None, make_hint=None, timeout_s=5.0,
                 compat_repo=None):   # NEW
        self._compat_repo = compat_repo

    def _protocol_order_for_hint(self, make_hint):
        order = _MAKE_HINT_ORDER.get(make_hint, _DEFAULT_ORDER) if make_hint else _DEFAULT_ORDER
        if self._compat_repo is None or make_hint is None:
            return order
        skip = self._compat_repo.protocols_to_skip_for_make(make_hint)
        filtered = tuple(p for p in order if p not in skip)
        return filtered or order  # safety: never empty
```

Typed with string forward-ref + duck typing (just needs `protocols_to_skip_for_make(make) -> set[str]`). Not imported at top — keeps Phase 139's import graph unchanged.

**Backward compat:** `compat_repo=None` preserves Phase 139 behavior exactly. All 31 existing Phase 139 tests unchanged.

## Key Concepts

- **Compat data is a mechanic's knowledge base, not product spec.** A $30 ELM327 clone technically supports ISO 15765 per the datasheet — but `reliability_1to5` + curated `notes` reflect shop-floor reality.
- **SQL `LIKE` model patterns.** `'CBR%'` matches all CBRs — one row covers a family. Exact-variant rows still win specificity sort when they exist.
- **Year-range nullability expresses "applies to all".** Avoids sentinel years like 9999.
- **Status tier → reliability DESC → price ASC is the ranking mechanics want.** Full imperfectly-reliable beats partial bulletproof; within same tier, most reliable; within same reliability, cheapest.
- **$30 ELM327 Bluetooth clone explicitly modeled as `partial` on 2011+ Harley.** The load-bearing honesty of the phase. Mechanic gets truth.
- **Notes free-text with just-enough structure.** `note_type` enum for filtering (quirk vs tip) without over-engineering.
- **`compat_repo` optional AutoDetector kwarg.** Added value, not hard dep. Zero Phase 139 test changes.
- **JSON seeds source of truth; DB is query index.** Re-seed is one-command. Mechanic-contributed notes persist (not round-trippable via re-seed).
- **No live API, no scraping.** Manually curated from public specs + service manuals + forum threads (cited in `verified_by`).

## Verification Checklist

- [x] Migration 017 version=17 (assumes 142 ships 016; amend if slips).
- [x] 3 tables + 6 indexes created.
- [x] FK-safe rollback (child-first).
- [x] compat_repo.py exposes all listed functions.
- [x] `reliability_1to5` out of [1..5] raises ValueError.
- [x] `price_usd_cents` float → TypeError.
- [x] Ranking: status tier → reliability DESC → price ASC → adapter_id ASC.
- [x] `list_compatible_adapters` matches SQL LIKE patterns; year range nullable; min_status filters.
- [x] `check_compatibility` most-specific match wins; None for unknown.
- [x] adapters.json ≥ 20 entries across 5 tiers.
- [x] compat_matrix.json ≥ 100 entries.
- [x] Loader idempotent (second seed_all: zero new inserts).
- [x] Malformed JSON → ValueError with filename + line.
- [x] `compat list` runs, shows seeded adapters.
- [x] `compat recommend --bike SLUG` returns ranked results grouped by status.
- [x] `compat check --adapter X --bike Y` color-coded verdict panel.
- [x] `compat show` prints adapter + nested compat table.
- [x] `compat note add/list` round-trip.
- [x] `compat seed --yes` loads all three JSONs.
- [x] `AutoDetector(compat_repo=None)` — Phase 139's 31 tests unchanged.
- [x] `AutoDetector(compat_repo=repo)` filters protocols per `protocols_to_skip_for_make`.
- [x] Filter never empties list (fallback to unfiltered on total skip).
- [x] Notes cascade-delete when adapter removed.
- [x] ~57 tests pass; zero live tokens.

## Risks

- **Migration number collision with Phase 142.** Plans for 017 assuming 142 ships 016 first. If 142 doesn't, Phase 145 takes 016 (amend v1.1). SQL body migration-number-independent.
- **Seed data curation load-bearing.** Builder must cite real specs; fantasy products fail trust. Architect trust-but-verify spot-checks public sources.
- **Ranking tiebreak stability.** `obd_adapters.id ASC` as final tiebreaker prevents test flake across SQLite versions.
- **Specificity scoring in `check_compatibility` non-trivial.** Pure helper `_pattern_specificity(pattern)` returns int; candidate set fetched then Python-side sort. Fighting SQL for this is worse.
- **JSON seed volume (100+ rows) tempts corner-cutting.** CLAUDE.md quality rules prohibit; Architect trust-but-verify spot-checks 10 random rows.
- **`cli/hardware.py` file size** (~900 LoC after +350). Builder may extract to `cli/hardware_compat.py` — acceptable deviation, document in v1.1.
- **Phase 141-144 cli/hardware.py coordination.** Each adds new subgroup via `register_<name>(hardware_group)` — merge conflicts are line-level additions.
- **`AutoDetector` kwarg at end** of signature. Phase 139 tests use keyword args; safe.
- **`protocols_to_skip_for_make` conservatism.** <3 compat rows → empty set. Trust Phase 139 heuristic on sparse data.
- **Mechanic-contributed notes persist but re-seed doesn't touch them.** By design (never destroy user data). Documented; central note-sharing out-of-scope.
- **FK `submitted_by_user_id` → users.id** — users table created Migration 005 (Phase 112). Safe.
