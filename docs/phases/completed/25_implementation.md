# MotoDiag Phase 25 — Honda CBR600RR (2003-2024)

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-16

## Goal
Build the known-issues knowledge base for the Honda CBR600RR — race-focused 600cc supersport spanning 2003-2024.

CLI: `python -m pytest tests/test_phase25_honda_cbr600rr.py -v`

Outputs: `data/knowledge/known_issues_honda_cbr600rr.json` (10 issues), 6 tests

## Key Concepts
- HESD (Honda Electronic Steering Damper) on 2007+: $800 OEM replacement, most owners convert to aftermarket manual damper
- C-ABS on 2009+: heavy, complex, expensive — most failures are just dirty wheel speed sensors
- Reg/rec improved from F-series but 2003-2006 still uses weak shunt design
- Valve clearance check every 16K miles is critical — intake valves tighten as seats wear
- Stator failures more common on track bikes from sustained high RPM
- Subframe cracking from paddock stand spool use is underappreciated

## Verification Checklist
- [x] 10 issues load into database
- [x] Year range queries correct for 2010
- [x] Critical severity present (2: HESD, reg/rec)
- [x] Handling and charging symptoms find relevant issues
- [x] Forum tips in all fix procedures
- [x] All 6 tests pass (1.01s)

## Results
| Metric | Value |
|--------|-------|
| Known issues | 10 (HESD, reg/rec, C-ABS, CCT, fuel pump, valve clearance, LCD fade, fork oil, stator, subframe) |
| Tests | 6/6, 1.01s |
| Severity breakdown | 2 critical, 4 high, 3 medium, 1 low |
| Year coverage | 2003-2024 |

The CBR600RR has more electronics complexity than the F-series (HESD, C-ABS, later ride modes) but shares the same Honda inline-4 platform weaknesses (reg/rec, CCT, stator). Track use is a major factor in failure rates.
