# MotoDiag Phase 91 — Intermittent Fault Analysis

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-17

## Goal
Analyze "sometimes it does X" faults that only occur under specific conditions. Predefined patterns for temperature-dependent, load-dependent, weather-dependent, RPM-dependent, and random intermittent faults. Condition extraction from freeform mechanic descriptions, pattern matching, and an AI prompt for complex intermittent reasoning.

CLI: `python -m pytest tests/test_phase91_intermittent.py -v`

Outputs: `src/motodiag/engine/intermittent.py`, 43 tests

## Key Concepts
- IntermittentPattern model: pattern_id, description, trigger_keywords, likely_causes, diagnostic_approach, affected_systems
- 10+ predefined patterns: cold start, hot/heat soak, under load, in rain, high RPM, low fuel, idle, vibration-related, altitude, random/no pattern
- extract_conditions(): parses freeform text for environmental triggers (cold, hot, rain, load, RPM, idle, fuel level)
- IntermittentAnalyzer.analyze(): matches symptom + conditions against patterns, returns ranked results with match scores
- Keyword hit tracking: shows which words in the description triggered each pattern match
- get_pattern_by_id(), get_patterns_by_system(): lookup functions for direct access
- INTERMITTENT_PROMPT: specialized AI prompt for complex intermittent faults that don't match predefined patterns
- Pattern scoring: keyword hits / total trigger keywords = match quality

## Verification Checklist
- [x] 10+ predefined intermittent patterns with trigger keywords and diagnostic approaches (43 tests)
- [x] Condition extraction from freeform text (temperature, weather, load, RPM)
- [x] Pattern matching with keyword hit scoring
- [x] Analyzer returns ranked results sorted by score
- [x] Lookup functions for pattern access
- [x] INTERMITTENT_PROMPT for AI escalation of complex cases
- [x] All 43 tests pass (pure logic)

## Results
| Metric | Value |
|--------|-------|
| Files created | 1 (intermittent.py) |
| Tests | 43/43 |
| Intermittent patterns | 10+ predefined |
| Condition extractors | 8 (cold, hot, rain, load, high RPM, idle, fuel level, altitude) |
