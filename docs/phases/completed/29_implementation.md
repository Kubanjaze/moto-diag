# MotoDiag Phase 29 — Honda Standards: CB750/919, CB1000R, Hornet

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-16

## Goal
Build the known-issues knowledge base for Honda's standard/naked lineup. Shared sport bike engines in detuned, upright-riding configurations — inheriting sport bike weaknesses plus unique naked-bike issues.

CLI: `python -m pytest tests/test_phase29_honda_standards.py -v`

Outputs: `data/knowledge/known_issues_honda_standards.json` (10 issues), 6 tests

## Key Concepts
- Naked bikes make reg/rec failure WORSE — exposed engine heat with no fairing-directed airflow
- CCT suffers more on standards because low-RPM city riding = less oil pressure for tensioner
- CB1000R ride-by-wire has CBR1000RR-aggressive mapping — too snatchy for commuter use
- Standard bike ergonomics shift weight rearward — rear shock degradation faster than sport bikes
- Mirror vibration, handlebar vibes, and headlight aim are naked-bike-specific issues

## Verification Checklist
- [x] 10 issues load
- [x] Year range correct for 2015 (4+ issues)
- [x] Critical severity present (1: reg/rec)
- [x] Vibration symptom finds handlebar and mirror issues
- [x] Forum tips in all procedures
- [x] All 6 tests pass (1.20s)

## Results
| Metric | Value |
|--------|-------|
| Known issues | 10 (reg/rec, CCT, ride-by-wire, carbs CB750, chain, handlebar vibes, tank rust, headlight, rear shock, mirror vibes) |
| Tests | 6/6, 1.20s |
| Severity breakdown | 1 critical, 1 high, 5 medium, 3 low |
| Year coverage | 1991-2025 |

Standard/naked bikes have a unique diagnostic profile — the same engines as sport bikes but different failure patterns from upright riding position, exposed configuration, and commuter use patterns.
