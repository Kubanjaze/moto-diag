# MotoDiag Phase 32 — Honda Vintage Air-Cooled: CB550/650/750, Nighthawk

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-16

## Goal
Build the known-issues knowledge base for Honda's vintage air-cooled lineup. 25-50+ year old bikes with age-specific failure modes.

CLI: `python -m pytest tests/test_phase32_honda_vintage.py -v`

Outputs: `data/knowledge/known_issues_honda_vintage.json` (10 issues), 6 tests

## Key Concepts
- Points ignition → electronic conversion (Pamco, Dyna) is the #1 reliability upgrade
- Every vintage Honda 4-carb setup needs a full rebuild — not cleaning, rebuilding (replace all rubber)
- Charging system: generators (early K0-K1) vs stators (K2+), both fail from insulation breakdown
- Cam chain endless replacement technique avoids crankcase splitting
- Vacuum petcock diaphragm failure causes either flooding or fuel starvation
- Fork tube pitting: re-chroming ($200-300/pair) is a worthwhile investment
- Wiring harness: reproduction replacement beats chasing 40-year-old intermittent faults
- Every gasket leaks — do a complete re-gasket, not one at a time

## Verification Checklist
- [x] 10 issues load
- [x] Year range correct for 1975 (5+ issues)
- [x] Critical severity present (2: charging system, brakes)
- [x] Won't start and oil leak symptoms find relevant issues
- [x] Forum tips in all procedures
- [x] All 6 tests pass (1.22s)

## Results
| Metric | Value |
|--------|-------|
| Known issues | 10 (points ignition, carb rebuild, charging, cam chain, petcock, brakes, exhaust rust, fork pitting, wiring harness, gasket weeping) |
| Tests | 6/6, 1.22s |
| Severity breakdown | 2 critical, 4 high, 3 medium, 1 low |
| Year coverage | 1969-2003 |

Vintage Honda diagnostics are fundamentally about aging materials — rubber, insulation, chrome, gaskets, and steel all have finite lifespans. The mechanic's job is triage: what needs replacing now vs what can wait.
