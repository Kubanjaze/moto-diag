# MotoDiag Phase 89 — Similar Case Retrieval

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-17

## Goal
Build a case retrieval system that finds past diagnostics similar to the current case. Uses Jaccard similarity on symptom sets, vehicle make/model matching, and year proximity scoring to rank historical cases by relevance. Enables RAG-style context injection of prior diagnostic experience.

CLI: `python -m pytest tests/test_phase89_retrieval.py -v`

Outputs: `src/motodiag/engine/retrieval.py`, 32 tests

## Key Concepts
- SimilarityScore model: symptom_overlap (Jaccard 0-1), vehicle_match (exact/make/none), year_proximity, overall_score
- CaseRetriever.find_similar_cases(): searches diagnostic history, returns ranked similar cases
- Jaccard similarity: |intersection| / |union| of symptom sets
- Vehicle matching tiers: exact make+model = 1.0, same make = 0.5, different = 0.0
- Year proximity: closer model years score higher (decays with distance)
- build_case_context(): formats similar cases into structured text for AI prompt injection
- Configurable top_n and minimum_score thresholds
- Pure logic — no API calls, works with DiagnosticHistory from Phase 88

## Verification Checklist
- [x] Similarity scoring: Jaccard, vehicle match, year proximity (32 tests)
- [x] Case retrieval ranked by overall score
- [x] Context builder produces structured text for AI prompts
- [x] All 32 tests pass (pure logic)

## Results
| Metric | Value |
|--------|-------|
| Files created | 1 (retrieval.py) |
| Tests | 32/32 |
| Similarity dimensions | 3 (symptom overlap, vehicle match, year proximity) |
