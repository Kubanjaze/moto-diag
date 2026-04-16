# MotoDiag Phase 06 — Symptom Taxonomy + Data Model

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-15

## Goal
Build the symptom repository and taxonomy so mechanics can describe what's wrong with a bike using categorized, structured symptoms. Symptoms are linked to systems (engine, electrical, fuel, etc.) and can be searched/filtered. This is what the AI diagnostic engine will use to map symptoms to diagnoses.

CLI: No new CLI command yet — symptoms are queried programmatically.

Outputs: `knowledge/symptom_repo.py` (CRUD + search), `data/knowledge/symptoms.json` (40 starter symptoms), loader extension, 10 tests

## Logic
1. Created `knowledge/symptom_repo.py` with 5 functions + 1 helper:
   - `add_symptom(name, description, category, related_systems?)` — INSERT OR REPLACE
   - `get_symptom(name)` — retrieves by exact name, parses related_systems JSON
   - `search_symptoms(query?, category?)` — multi-filter LIKE search on name + description
   - `list_symptoms_by_category(category)` — all symptoms in one category
   - `count_symptoms()` — total count
   - `_row_to_dict(row)` — parses JSON related_systems field
2. Created `data/knowledge/symptoms.json` with 40 symptoms across 12 categories:
   - starting (6): won't start, no crank, slow crank, clicks, hard cold start, hard hot start
   - idle (4): stalls, rough, high, surging
   - engine (4): loss of power, misfires, backfires, oil leak, excessive oil consumption
   - cooling (2): overheating, coolant leak
   - exhaust (3): white smoke, black smoke, exhaust leak sound
   - electrical (4): battery not charging, drains overnight, dim headlight, check engine light
   - fuel (2): fuel leak, poor economy
   - brakes (3): spongy, squeal, ABS light
   - drivetrain (3): clutch slipping, hard shifting, chain noise
   - vibration (1): vibration at speed
   - suspension (2): front wobble, bottoming out
   - noise (3): ticking, grinding, whining
   - other (1): burning smell
3. Extended `knowledge/loader.py` with `load_symptom_file()` — same JSON array pattern as DTC loader

## Key Concepts
- Symptoms are the mechanic's input language — natural descriptions of what they observe
- Distinct from DTCs: DTCs come from the ECU, symptoms come from the mechanic
- `related_systems` links symptoms to multiple systems (e.g., "stalls at idle" → fuel + idle + engine)
- Same loader pattern as DTCs: JSON file → Python function → INSERT OR REPLACE → database
- `UNIQUE(name, category)` constraint prevents duplicate symptoms

## Verification Checklist
- [x] `add_symptom()` inserts with related_systems
- [x] `get_symptom()` retrieves by name with parsed JSON
- [x] `search_symptoms(query="idle")` finds matching symptoms
- [x] `search_symptoms(category="idle")` filters correctly
- [x] `list_symptoms_by_category("brakes")` returns brake-related symptoms
- [x] `load_symptom_file()` imports all 40 symptoms from starter file
- [x] related_systems parsed from JSON TEXT column into Python list
- [x] FileNotFoundError raised for missing files
- [x] 10 tests pass in 0.84s

## Risks
- ~~Symptom name uniqueness~~ — handled by UNIQUE(name, category)
- Natural language variability (mechanics describe same problem differently) — handled later by AI engine, not at data layer

## Results
| Metric | Value |
|--------|-------|
| Symptoms loaded | 40 (across 12+ categories) |
| Repo functions | 5 (add, get, search, list_by_category, count) |
| Categories covered | starting, idle, engine, cooling, exhaust, electrical, fuel, brakes, drivetrain, vibration, suspension, noise, other |
| Tests | 10 |
| Test time | 0.84s |

Symptom taxonomy is ready. Mechanics' common complaints are structured and searchable. The AI engine (Track C) will map these symptoms to diagnoses.
