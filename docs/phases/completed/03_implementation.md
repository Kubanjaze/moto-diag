# MotoDiag Phase 03 — Database Schema + SQLite Setup

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-15

## Goal
Set up the SQLite database with full schema for all core entities: vehicles, DTC codes, symptoms, known issues, and diagnostic sessions. Includes connection management with WAL mode, auto-rollback, row factory, and schema versioning for future migrations.

CLI: Database is initialized automatically on first use. No CLI command yet.

Outputs: `core/database.py` with schema, connection manager, schema versioning. 12 tests.

## Logic
1. Created `core/database.py` with `SCHEMA_SQL` defining 6 tables:
   - `vehicles` — make/model/year/engine_cc/vin/protocol/notes, indexed on make+model and year
   - `dtc_codes` — code/description/category/severity/make/common_causes/fix_summary, unique on (code, make)
   - `symptoms` — name/description/category/related_systems, unique on (name, category)
   - `known_issues` — title/description/make/model/year_range/severity/symptoms/dtc_codes/causes/fix_procedure/parts/hours
   - `diagnostic_sessions` — vehicle reference/status/symptoms/fault_codes/diagnosis/repair_steps/confidence/severity/cost/ai_model/tokens
   - `schema_version` — version tracking for future migrations
2. `init_db(db_path)` — creates parent dirs, executes schema SQL, records schema version
3. `get_connection(db_path)` — context manager yielding `sqlite3.Connection` with:
   - `row_factory = sqlite3.Row` (dict-like access)
   - `PRAGMA journal_mode=WAL` (concurrent reads)
   - `PRAGMA foreign_keys=ON`
   - Auto-commit on success, auto-rollback on exception
4. `get_schema_version()` — reads current version, returns None if DB doesn't exist
5. `table_exists()` — checks sqlite_master for table presence

## Key Concepts
- SQLite WAL mode for concurrent read performance
- `sqlite3.Row` row factory for dict-style column access
- Context manager with try/commit/except/rollback/finally/close pattern
- Schema versioning via `schema_version` table (future migration support)
- JSON arrays stored as TEXT for flexible lists (common_causes, symptoms, etc.)
- Foreign key constraint: diagnostic_sessions.vehicle_id → vehicles.id

## Verification Checklist
- [x] `init_db()` creates database file and all tables
- [x] `init_db()` creates parent directories if missing
- [x] `init_db()` is idempotent (safe to call twice)
- [x] Schema version recorded as 1
- [x] All 6 tables exist after init
- [x] `get_connection()` provides dict-like row access
- [x] Rollback on exception (no partial writes)
- [x] Can insert and query vehicles, DTCs, sessions
- [x] `get_schema_version()` returns None for non-existent DB
- [x] 12 tests pass in 0.67s

## Risks
- ~~SQLite concurrent write limitations~~ — mitigated by WAL mode, single-user CLI tool
- JSON-in-TEXT columns lose query efficiency — acceptable for initial version, can add normalized tables later if needed

## Results
| Metric | Value |
|--------|-------|
| Tables | 6 (vehicles, dtc_codes, symptoms, known_issues, diagnostic_sessions, schema_version) |
| Indexes | 5 (vehicles make+model, year; dtc code, make; sessions status, vehicle) |
| Schema version | 1 |
| Tests | 12 |
| Test time | 0.67s |

Database foundation is solid. All entities from the data model have tables, connection management handles errors gracefully, and schema versioning is ready for future migrations.
