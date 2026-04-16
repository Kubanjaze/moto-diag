# MotoDiag Phase 05 — DTC Schema + Loader

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-15

## Goal
Build the DTC (Diagnostic Trouble Code) repository with CRUD operations and a JSON-based loader for bulk importing fault codes by manufacturer. Mechanics can look up any DTC code and get a plain-English description, severity, common causes, and fix summary. This is the data layer that Track B's vehicle knowledge phases will populate.

CLI: `motodiag code P0115` / `motodiag code P0115 --make Harley-Davidson`

Outputs: `knowledge/dtc_repo.py` (CRUD + query), `knowledge/loader.py` (JSON import), 40 sample DTCs (20 generic + 20 Harley), 15 tests

## Logic
1. Created `knowledge/dtc_repo.py` with 5 functions + 1 helper:
   - `add_dtc(dtc)` — INSERT OR REPLACE for idempotent loading
   - `get_dtc(code, make?)` — manufacturer-specific first, generic fallback, then any match
   - `search_dtcs(query?, category?, severity?, make?)` — multi-filter search with LIKE
   - `list_dtcs_by_make(make)` — all codes for one manufacturer
   - `count_dtcs()` — total count
   - `_row_to_dict(row)` — parses JSON common_causes field
2. Created `knowledge/loader.py` with 2 functions:
   - `load_dtc_file(path)` — parse JSON array, create DTCCode models, insert into DB
   - `load_dtc_directory(dir_path)` — load all *.json files, return {filename: count} dict
3. Created `data/dtc_codes/generic.json` — 20 universal OBD-II P-codes covering fuel, cooling, engine, exhaust, electrical, idle systems
4. Created `data/dtc_codes/harley_davidson.json` — 20 Harley-specific codes including P1001-P1510 (manufacturer codes), U1016 (CAN bus), B1004 (body code)
5. Wired up `motodiag code <DTC>` CLI command with Rich Panel output, severity color coding, common causes list, and fix summary

## Key Concepts
- DTC code format: P (powertrain), B (body), C (chassis), U (network) + 4 digits
- `INSERT OR REPLACE` on UNIQUE(code, make) for idempotent bulk loading
- Make-specific fallback chain: manufacturer-specific → generic (make IS NULL) → any match
- JSON arrays stored as TEXT in SQLite, parsed on read via `_row_to_dict()`
- Rich Panel + severity color coding for mechanic-friendly terminal output
- `SymptomCategory` and `Severity` enums for type-safe DTC construction from JSON

## Verification Checklist
- [x] `add_dtc()` inserts a DTC into the database
- [x] `get_dtc("P0115")` returns correct generic description
- [x] `get_dtc("P0115", make="Harley-Davidson")` returns Harley-specific version
- [x] `get_dtc("P0115", make="Honda")` falls back to generic
- [x] `search_dtcs(category="cooling")` filters correctly
- [x] `search_dtcs(query="coolant")` searches code + description
- [x] `list_dtcs_by_make("Harley-Davidson")` returns 20 codes
- [x] `load_dtc_file()` imports generic.json (20 DTCs)
- [x] `load_dtc_file()` imports harley_davidson.json (20 DTCs)
- [x] `load_dtc_directory()` imports all files in a directory
- [x] `motodiag code` shows usage when no code given
- [x] Common causes parsed from JSON stored in TEXT column
- [x] FileNotFoundError raised for missing files
- [x] 15 tests pass in 1.23s

## Risks
- ~~DTC code uniqueness~~ — handled by UNIQUE(code, make) with INSERT OR REPLACE
- Large DTC datasets — 40 codes load in <1s, bulk performance is fine at this scale

## Results
| Metric | Value |
|--------|-------|
| DTC codes loaded | 40 (20 generic + 20 Harley-Davidson) |
| Repo functions | 5 (add, get, search, list_by_make, count) |
| Loader functions | 2 (load_file, load_directory) |
| CLI commands updated | 1 (code — now functional) |
| Tests | 15 |
| Test time | 1.23s |

DTC lookup is now functional. `motodiag code P0115` returns a formatted diagnostic with causes and fixes. The loader pattern (JSON → DTCCode model → database) is ready for Track B to add hundreds more codes per manufacturer.
