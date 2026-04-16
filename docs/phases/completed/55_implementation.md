# MotoDiag Phase 55 — Kawasaki Vintage: KZ550/650/750/1000/1100, GPz Series

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-16

## Goal
Kawasaki's air-cooled inline-4 classics from the late 1970s through late 1980s — the KZ and GPz series.

CLI: `python -m pytest tests/test_phase55_kawasaki_vintage.py -v`

Outputs: `data/knowledge/known_issues_kawasaki_vintage.json` (10 issues), 6 tests

## Key Concepts
- KZ1000/1100 cam chain tensioner: APE manual tensioner replaces worn automatic units
- KZ650/750 charging system: MOSFET reg/rec upgrade eliminates the #1 reliability issue
- KZ/GPz inline-4 carb rebuild and sync: the most transformative maintenance on any vintage Kawasaki
- GPz900R/1000RX fuel system: petcock diaphragm failure floods crankcase, tank rust clogs jets
- KZ550/650 points ignition: Dyna S electronic conversion eliminates timing drift
- KZ1000/1100 fork and suspension: Race Tech emulators + aftermarket rear shocks modernize handling
- All KZ/GPz oil leaks: cam cover gasket first, Hylomar sealant on rough vintage castings
- GPz550/750 brake system: caliper rebuild + stainless lines, ZX750 dual-disc conversion for real improvement
- KZ/GPz wiring harness: 30-40 year old bullet connectors and grounds cause all electrical gremlins
- KZ/GPz drive chain: O-ring upgrade, always replace countershaft seal with sprocket

## Verification Checklist
- [x] All 6 tests pass (1.61s)

## Results
| Metric | Value |
|--------|-------|
| Known issues | 10 |
| Tests | 6/6, 1.61s |
| Severity breakdown | 1 critical, 4 high, 5 medium |
| Year coverage | 1976-1991 |
