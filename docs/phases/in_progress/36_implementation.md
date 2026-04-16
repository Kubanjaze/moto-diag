# MotoDiag Phase 36 — Yamaha YZF-R6 (1999-2020)

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-16

## Goal
Second Yamaha phase. YZF-R6 across all generations: Gen 1 carbureted (1999-2002), Gen 2 fuel-injected (2003-2005), Gen 3 underseat exhaust (2006-2007), Gen 4 (2008-2016), and Gen 5 (2017-2020). The R6 is Yamaha's 600cc supersport — the dominant club racer and one of the most common bikes in the shop.

CLI: `python -m pytest tests/test_phase36_yamaha_r6.py -v`

Outputs: `data/knowledge/known_issues_yamaha_r6.json` (10 issues), 6 tests

## Key Concepts
- CCT failure is the #1 R6 problem — 2003-2005 models are notorious, causes catastrophic valve damage if ignored
- Stator/charging failure same pattern as R1 but R6 runs hotter (16,500 RPM redline, smaller fairings)
- Valve clearance checking is critical — shim-under-bucket tightens with wear, 4-hour service job
- EXUP valve system shared with R1 — matters more on the 600 for midrange torque
- 2006-2007 underseat exhaust is the defining problem of that generation — melts electronics, cooks batteries
- Throttle body sync needed for both carb (Gen 1) and FI models — different procedures
- 2017+ R6 shares R1 electronics suite (IMU, TC, QS) — same failure modes at 600cc power level
- Water pump mechanical seal is a common slow leak caught late
- Immobilizer causes more "won't start" dealer visits than any other single issue

## Verification Checklist
- [x] 10 issues load correctly
- [x] Year range queries return correct results (2010 query returns 5+ hits)
- [x] Critical severity issues present (CCT)
- [x] Symptom searches work (loss of power: 2+, won't start: 1+)
- [x] Forum tips present in fix procedures
- [x] All 6 tests pass (1.15s)

## Results
| Metric | Value |
|--------|-------|
| Known issues | 10 (CCT, stator, valve clearance, EXUP, underseat heat, fuel pump, throttle sync, coolant leak, immobilizer, 2017+ electronics) |
| Tests | 6/6, 1.15s |
| Severity breakdown | 1 critical, 3 high, 5 medium, 0 low |
| Year coverage | 1999-2020 |

The R6's most critical issue is the 2003-2005 CCT — a ticking time bomb that causes catastrophic engine damage. The 06-07 underseat exhaust heat problem is the most generation-specific issue in the Yamaha lineup.
