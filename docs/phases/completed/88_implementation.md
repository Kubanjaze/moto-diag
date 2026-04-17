# MotoDiag Phase 88 — Diagnostic History + Learning

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-17

## Goal
Build a DiagnosticHistory class that stores and retrieves past diagnostic sessions for RAG-style learning. Enables recording completed diagnostics with outcomes, filtered retrieval by vehicle/symptoms, statistical summaries, and similar-case lookup for AI prompt injection.

CLI: `python -m pytest tests/test_phase88_history.py -v`

Outputs: `src/motodiag/engine/history.py`, `tests/test_phase88_history.py` (30 tests)

## Logic
- DiagnosticRecord Pydantic model: record_id, timestamp (UTC), make, model, year, symptoms, diagnosis, confidence, resolution, cost, duration_minutes, notes, parts_used, system_category
- HistoryStatistics Pydantic model: total_records, avg_confidence, avg_cost, avg_duration, most_common_diagnoses/makes/symptoms (top-N tuples), resolution_rate
- DiagnosticHistory class with in-memory list storage + dict index for O(1) ID lookup:
  - add_record(): store record, raise ValueError on duplicate ID
  - get_record(): O(1) lookup by record_id
  - get_records(): filtered retrieval with AND-combined filters (make, model, year_min/max, symptom_keywords, diagnosis_keywords, system_category, min_confidence, limit), results sorted newest-first
  - get_recent(): last N records by timestamp
  - get_statistics(): compute total, averages, frequency-ranked top-N lists, resolution rate
  - find_similar(): heuristic scoring (vehicle match +3/+1, year proximity +1/+0.5, symptom word overlap *2) for RAG context
  - clear(), remove_record(), export_records() (JSON-serializable dicts), import_records() (skip duplicates and invalid)
- Keyword matching is case-insensitive substring matching throughout
- Symptom keyword filter uses ANY-match (at least one keyword in at least one symptom)

## Key Concepts
- Pydantic BaseModel with Field validators (ge, le) for confidence and cost bounds
- In-memory dual storage: list for ordered access + dict for O(1) ID lookup
- Case-insensitive substring matching for make/model filters
- ANY-match semantics for symptom/diagnosis keyword filters (at least one keyword must match)
- AND-combination of all provided filters (each filter is a gate)
- Timestamp-descending sort for all retrieval methods
- Heuristic similarity scoring with vehicle match, year proximity, and symptom word overlap
- Export/import using model_dump(mode="json") for round-trip serialization
- Duplicate detection on both add_record (ValueError) and import_records (skip)
- Statistics computed on-demand, not maintained incrementally

## Verification Checklist
- [x] DiagnosticRecord creates with all fields (1 test)
- [x] DiagnosticRecord default timestamp is UTC (1 test)
- [x] DiagnosticRecord symptoms list works (1 test)
- [x] DiagnosticRecord optional fields accept None (1 test)
- [x] DiagnosticRecord confidence bounds validated (2 tests)
- [x] DiagnosticRecord year bounds (1 test)
- [x] DiagnosticRecord parts_used defaults empty (1 test)
- [x] DiagnosticRecord system_category stored (1 test)
- [x] Empty history count is 0 (1 test)
- [x] add_record increments count (1 test)
- [x] get_record by ID returns correct record (1 test)
- [x] get_record missing returns None (1 test)
- [x] Duplicate ID raises ValueError (1 test)
- [x] clear removes all records (1 test)
- [x] remove_record success (1 test)
- [x] remove_record not found returns False (1 test)
- [x] Filter by make (1 test)
- [x] Filter by model (1 test)
- [x] Filter by year range (1 test)
- [x] Filter by symptom keywords (1 test)
- [x] Filter by diagnosis keywords (1 test)
- [x] Filter by system category (1 test)
- [x] Filter by min confidence (1 test)
- [x] Filter with limit (1 test)
- [x] Combined filters (1 test)
- [x] No match returns empty (1 test)
- [x] Results ordered newest first (1 test)
- [x] get_recent default (1 test)
- [x] get_recent limited (1 test)
- [x] get_recent empty history (1 test)
- [x] Statistics on empty history (1 test)
- [x] Statistics total_records (1 test)
- [x] Statistics avg_confidence (1 test)
- [x] Statistics avg_cost (1 test)
- [x] Statistics most_common_diagnoses (1 test)
- [x] Statistics resolution_rate (1 test)
- [x] find_similar exact vehicle match (1 test)
- [x] find_similar symptom overlap (1 test)
- [x] find_similar empty history (1 test)
- [x] find_similar top_n (1 test)
- [x] export returns list of dicts (1 test)
- [x] import into empty history (1 test)
- [x] import skips duplicates (1 test)
- [x] import skips invalid records (1 test)
- [x] All 30 tests pass

## Risks
- **Memory growth**: In-memory storage means history grows unbounded — acceptable for current scope since a mechanic generates maybe 10-50 records/day. Future enhancement: SQLite persistence (Phase 88+ or Track D).
- **Statistics recomputation**: get_statistics() scans all records on every call — O(N). Acceptable for <10K records but would need caching if history grows large.
- **find_similar heuristic**: Word-level symptom matching is coarse — "battery not charging" and "battery dead" share only "battery". The CaseRetriever in Phase 89 uses Jaccard similarity for a more principled approach.

## Results
| Metric | Value |
|--------|-------|
| Files created | 2 (history.py, test_phase88_history.py) |
| Module size | ~280 lines |
| Tests written | 30 |
| Tests passing | 30 |
| API calls | 0 |
| Models defined | 2 (DiagnosticRecord, HistoryStatistics) |
| History methods | 10 (add, get, get_records, get_recent, get_statistics, find_similar, clear, remove, export, import) |

In-memory diagnostic history store with dual list+dict storage for both ordered access and O(1) ID lookup. The find_similar heuristic provides a quick-and-dirty RAG lookup that Phase 89's CaseRetriever refines with Jaccard similarity and configurable weights.
