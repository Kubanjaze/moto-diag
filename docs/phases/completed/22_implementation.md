# MotoDiag Phase 22 — Harley Common Cross-Era Issues

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-16

## Goal
Build a cross-era mechanical issues knowledge base covering the problems that plague multiple Harley generations: compensator, intake leaks, heat soak, oil leaks, clutch, suspension, brakes, and tire/wheel issues. Phase 21 covered electrical; this phase covers the mechanical side that every Harley mechanic sees weekly regardless of which era bike rolls in.

CLI: `python -m pytest tests/test_phase22_harley_cross_era.py -v`

Outputs: `data/knowledge/known_issues_harley_cross_era.json` (10 issues), 6 tests

## Logic
- Created 10 known mechanical issues spanning multiple Harley generations
- Focused on "every Harley does this eventually" problems
- Complements era-specific phases (13-20) and electrical phase (21)
- Together with Phase 21, completes the Harley-Davidson knowledge base section

Data flow: JSON file -> load_known_issues_file() -> SQLite known_issues table -> query via issues_repo

## Key Concepts
- Compensator: spring-loaded sprocket — wears on all Twin Cam and M8 models, upgrade to SE or Baker Grudge
- Intake manifold seals: universal V-twin problem, spray test is diagnostic gold standard
- Heat soak: inherent to air-cooled V-twins, "not a fault — it's physics"
- Primary leaks: derby cover O-ring is $2 fix for 90% of primary leaks
- Clutch: cable models need regular adjustment, hydraulic models need fluid service
- Wheel bearings: ABS bikes require HD-specific rear bearing with integrated tone ring
- Tire wear patterns are diagnostic — cupping = worn shocks, center wear = overinflation
- Ethanol fuel damage: E10 varnishes carbs in 3 weeks if sitting

## Verification Checklist
- [x] 10 issues load into database
- [x] Year range queries return cross-era results (2005 returns 5+ issues)
- [x] Symptom search finds intake leak (idle surges)
- [x] DTC search finds exhaust leak (P0131)
- [x] High severity present (3: compensator, intake leak, wheel bearings)
- [x] Forum tips present in all fix procedures
- [x] All 6 tests pass (0.96s)

## Risks
- Some overlap with era-specific phases. Mitigated by focusing on cross-era diagnostic patterns and the "mechanic's weekly" perspective.

## Results
| Metric | Value |
|--------|-------|
| Known issues | 10 (compensator, intake seals, heat soak, primary leak, clutch, rear shocks, wheel bearings, exhaust flanges, tire wear, ethanol damage) |
| Tests | 6/6, 0.96s |
| Severity breakdown | 0 critical, 3 high, 7 medium |
| DTC codes covered | P1010, P0131, P0171, C0051, C0056 |
| Year coverage | 1984-2025 (Evo through present) |

This completes the Harley-Davidson knowledge base: 100 known issues across 10 phases (13-22), covering every engine platform from Evo through Revolution Max, plus cross-era electrical and mechanical systems. Total Harley coverage: 100 issues, 64 tests.
