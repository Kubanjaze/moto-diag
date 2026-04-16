# MotoDiag Phase 24 — Honda CBR600: F2/F3/F4/F4i (1991-2006)

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-16

## Goal
Build the known-issues knowledge base for the Honda CBR600 F-series: F2 (1991-1994), F3 (1995-1998), F4 (1999-2000), and F4i (2001-2006). The most popular sport bike family ever sold — many are daily riders now.

CLI: `python -m pytest tests/test_phase24_honda_cbr600f.py -v`

Outputs: `data/knowledge/known_issues_honda_cbr600f.json` (10 issues), 6 tests

## Logic
- Created 10 known issues spanning F2 through F4i generations
- Covers carb-era issues (F2/F3/F4), EFI issues (F4i), and age-related failures
- Reg/rec and CCT recur from Phase 23 with CBR600-specific details

## Key Concepts
- Same Honda inline-4 platform failures: reg/rec (MOSFET upgrade), CCT (manual conversion), starter clutch
- Carb-to-EFI transition at F4i (2001): pilot jets clog on carb models, injectors clog on F4i
- Clutch cable failure on cable models (F2-F4) — carry a spare
- Radiator fan failure causes rapid overheating in traffic — relay is $5 fix
- Chain/sprocket wear on commuter bikes — X-ring chain + auto oiler doubles life

## Verification Checklist
- [x] 10 issues load into database
- [x] Year range queries return correct results for 2003 (5+ issues)
- [x] Critical severity present (1: reg/rec)
- [x] Overheating symptom finds radiator fan issue
- [x] Rough idle finds carb and injector issues
- [x] Forum tips present in all fix procedures
- [x] All 6 tests pass (1.01s)

## Results
| Metric | Value |
|--------|-------|
| Known issues | 10 (reg/rec, carbs, CCT, F4i injectors, ignition coils, clutch cable, radiator fan, chain/sprockets, speedo cable, exhaust rust) |
| Tests | 6/6, 1.01s |
| Severity breakdown | 1 critical, 3 high, 4 medium, 2 low |
| Year coverage | 1991-2006 (F2/F3/F4/F4i) |

The CBR600F family is the gateway sport bike — millions sold, many still on the road as commuters. Issues are a mix of Honda inline-4 platform failures (shared with CBR900 series) and age-related degradation on 20-30 year old bikes.
