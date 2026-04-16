# MotoDiag Phase 08 — Knowledge Base Schema

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-15

## Goal
Build the known issues repository — the core knowledge base that links specific bikes to their common problems, causes, fixes, and parts needed. This is the data layer that Track B's 55 vehicle-specific phases will populate. A known issue ties together a make/model/year range, symptoms, DTCs, root causes, and repair procedures.

CLI: No new CLI command yet — known issues queried programmatically.

Outputs: `knowledge/issues_repo.py` (6 functions + helper), `data/knowledge/known_issues_harley.json` (10 real issues with forum-level detail), loader extension, 16 tests

## Logic
1. Created `knowledge/issues_repo.py` with 6 functions + 1 helper:
   - `add_known_issue(title, description, make?, model?, year_start?, year_end?, severity?, symptoms?, dtc_codes?, causes?, fix_procedure?, parts_needed?, estimated_hours?)` → issue ID
   - `get_known_issue(issue_id)` → full dict with parsed JSON arrays
   - `search_known_issues(query?, make?, model?, year?, severity?)` → multi-filter search
   - `find_issues_by_symptom(symptom)` → LIKE search on symptoms JSON array
   - `find_issues_by_dtc(code)` → LIKE search on dtc_codes JSON array
   - `count_known_issues(make?)` → count with optional make filter
   - `_row_to_dict(row)` → parses JSON for symptoms, dtc_codes, causes, parts_needed
2. Created `data/knowledge/known_issues_harley.json` with 10 real Harley-Davidson known issues:
   - Stator failure (chronic undercharging) — the #1 Harley electrical issue
   - Cam chain tensioner failure (tick of death) — Twin Cam 88 critical issue
   - Compensator sprocket noise — startup clunk
   - Intake manifold air leak — lean running and backfire
   - Voltage regulator failure — overcharging or no charge
   - Sportster primary chain tensioner wear
   - Turn signal module (TSSM) failure
   - Exhaust header leak — cold tick
   - Fuel injector clogging — ethanol fuel deposits
   - Rear brake switch failure — parasitic battery drain
3. Each issue includes forum-level tips (e.g., "upgrade to Cycle Electric stator", "use James Gasket seals", "check ground wire before buying TSSM")
4. Extended `knowledge/loader.py` with `load_known_issues_file()`
5. Year range queries use `year_start <= ? AND year_end >= ?` with NULL handling

## Key Concepts
- Known issues are expert/forum-level tribal knowledge — not just textbook fixes
- Year range (year_start, year_end) spans model generations — NULL means "all years"
- Symptoms and DTCs stored as JSON arrays, searched via LIKE (cross-references to symptom_repo and dtc_repo)
- Parts include specific part numbers and aftermarket upgrade recommendations from forums
- Estimated hours for labor cost estimation in shop management (Track G)
- Forum tips embedded in fix_procedure — the obscure fixes that differentiate this from a service manual

## Verification Checklist
- [x] `add_known_issue()` returns issue ID
- [x] `get_known_issue()` returns full issue with all JSON arrays parsed
- [x] `search_known_issues(make="Harley")` filters correctly
- [x] `search_known_issues(query="stator")` searches title + description
- [x] `search_known_issues(year=2010)` year range query works
- [x] `search_known_issues(severity="high")` filters correctly
- [x] `find_issues_by_symptom("battery not charging")` returns matching issues
- [x] `find_issues_by_dtc("P0562")` returns matching issues
- [x] `count_known_issues()` with and without make filter
- [x] `load_known_issues_file()` imports all 10 Harley issues
- [x] Issues are searchable after bulk import
- [x] FileNotFoundError for missing files
- [x] 16 tests pass in 0.97s

## Risks
- ~~JSON LIKE searching~~ — works fine at our scale, can add FTS5 later if needed
- ~~Year range edge cases~~ — NULL year_start/year_end means "no bound", handled correctly

## Results
| Metric | Value |
|--------|-------|
| Known issues loaded | 10 (Harley-Davidson starter set) |
| Repo functions | 6 (add, get, search, find_by_symptom, find_by_dtc, count) |
| Forum-level tips | 10+ (embedded in fix procedures) |
| Parts with part numbers | 20+ (OEM + aftermarket recommendations) |
| Tests | 16 |
| Test time | 0.97s |

Knowledge base is ready for Track B to populate. Each vehicle phase will add 10-20 known issues per bike family, building toward hundreds of real diagnostic scenarios with forum-sourced fixes.
