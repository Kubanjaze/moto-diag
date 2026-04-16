# MotoDiag Phase 70 — Carburetor Troubleshooting (Cross-Platform)

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-16

## Goal
Universal carburetor diagnostics covering all carbureted motorcycles across Honda, Yamaha, Kawasaki, Suzuki, and Harley-Davidson — CV carb operation, failure modes, rebuild procedures, and tuning.

CLI: `python -m pytest tests/test_phase70_cross_platform_carbs.py -v`

Outputs: `data/knowledge/known_issues_cross_platform_carbs.json` (10 issues), 6 tests

## Key Concepts
- CV diaphragm failure: the most overlooked carb component — OEM preferred, aftermarket 30-40% failure rate
- Pilot jet clogging: #1 reason carb bikes won't start after storage, 0.4-0.7mm orifice blocked by ethanol varnish
- Float height maladjustment: 1mm off changes fuel level enough to cause problems, clear tube method most accurate
- Carb synchronization: transforms rough idle to sewing machine, Carbtune Pro or Motion Pro gauges
- Enrichment circuit (choke): cable stretch, plunger varnish, O-ring leak — 3 separate failure modes
- Intake manifold vacuum leaks: spray test definitive, OEM boots worth the premium, replace all together
- Pilot screw adjustment: the free tune-up, EPA cap removal, 2.0-2.5 turns out typical starting point
- Float bowl overflow: fire hazard — worn needle/seat is #1 cause, always replace as a SET
- Main jet rejetting: mandatory with exhaust changes, lean = detonation = melted piston, err rich
- Carb-to-EFI conversion: 90% of cases, proper carb maintenance is cheaper and simpler than conversion

## Verification Checklist
- [x] All 6 tests pass (0.74s)
- [x] Multi-make coverage verified (Honda, Kawasaki, Suzuki, Yamaha)

## Results
| Metric | Value |
|--------|-------|
| Known issues | 10 |
| Tests | 6/6, 0.74s |
| Severity breakdown | 1 critical, 3 high, 5 medium, 1 low |
| Year coverage | 1969-2015 |
| Makes covered | Honda, Yamaha, Kawasaki, Suzuki |
