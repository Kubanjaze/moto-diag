# MotoDiag Phase 35 — Yamaha YZF-R1 (1998+)

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-16

## Goal
First Yamaha phase. YZF-R1 across all generations: Gen 1-4, crossplane crank (2009+), and R1M/R1S (2015+).

CLI: `python -m pytest tests/test_phase35_yamaha_r1.py -v`

Outputs: `data/knowledge/known_issues_yamaha_r1.json` (10 issues), 6 tests

## Key Concepts
- EXUP valve servo failure: cable fraying is more common than motor failure — lube annually
- Stator/charging failure on 1998-2008 models — same fix pattern as Honda (MOSFET + hard-wire)
- Crossplane crank sound (2009+) is normal — educate owners, don't chase a phantom problem
- YCC-T ride-by-wire is race-aggressive — B-mode for street use
- YCC-I variable intake (2007-2008 only) — can be eliminated with fixed funnels
- 2015+ R1M/R1S electronics (IMU, ERS) require dealer-level tools — Woolich Racing is the shop alternative
- R1 is the most common track day bike — subframe and crash damage inspection is routine

## Verification Checklist
- [x] 10 issues load, year range correct, critical present, symptoms match, forum tips present
- [x] All 6 tests pass (1.46s)

## Results
| Metric | Value |
|--------|-------|
| Known issues | 10 (EXUP, stator, crossplane sound, YCC-T, YCC-I, fuel pump, CCT, suspension, R1M electronics, track crash) |
| Tests | 6/6, 1.46s |
| Severity breakdown | 1 critical, 3 high, 5 medium, 1 low |
| Year coverage | 1998-2025 |
