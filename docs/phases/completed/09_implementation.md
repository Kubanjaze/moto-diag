# MotoDiag Phase 09 — Search + Query Engine

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-15

## Goal
Build a unified search engine that queries across all knowledge stores (vehicles, DTCs, symptoms, known issues, sessions) from a single entry point. A mechanic types "stator" and gets matching DTCs, symptoms, known issues, and past sessions.

CLI: `motodiag search <query>` / `motodiag search <query> --make Harley-Davidson`

Outputs: `core/search.py` (unified search), CLI search command, 7 tests

## Logic
1. Created `core/search.py` with `search_all(query, make?, model?, year?)`:
   - Queries all 5 knowledge stores in parallel: vehicles, dtc_codes, symptoms, known_issues, sessions
   - Each store searched with the query and optional filters
   - Returns grouped results with total count
   - Empty/blank queries return empty results
2. Wired up `motodiag search <query>` CLI command:
   - Rich formatted output grouped by type
   - Top 5 results per category displayed
   - Shows severity, year range, make, category for each result
   - `--make` / `-m` optional filter
3. Delegates to existing repo search functions — no SQL duplication

## Key Concepts
- Single entry point: mechanic types one query, gets cross-store results
- Results grouped by type: DTCs, symptoms, known issues, vehicles, sessions
- Delegates to existing repos: `search_dtcs()`, `search_symptoms()`, `search_known_issues()`, `list_vehicles()`, `list_sessions()`
- Optional vehicle context (make/model/year) narrows all result sets
- Total count for quick "did I find anything" check

## Verification Checklist
- [x] `search_all("stator")` returns results from known issues
- [x] `search_all("P0562")` finds the matching DTC
- [x] `search_all("charging")` finds matching symptoms
- [x] `search_all("stator", make="Harley-Davidson")` narrows results
- [x] Empty query returns total=0
- [x] Non-matching query returns total=0
- [x] `motodiag search <query>` CLI command works
- [x] 7 tests pass in 0.63s

## Risks
- ~~Performance with large datasets~~ — fine at current scale, delegates to indexed queries

## Results
| Metric | Value |
|--------|-------|
| Search function | 1 (search_all — cross-store unified search) |
| Stores searched | 5 (vehicles, dtc_codes, symptoms, known_issues, sessions) |
| CLI commands added | 1 (search) |
| Tests | 7 |
| Test time | 0.63s |

Unified search ties all Phase 04-08 data together. Mechanics have one command to find anything.
