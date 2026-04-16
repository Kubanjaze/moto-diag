# MotoDiag Phase 42 — Yamaha Vintage: XS650, RD350/400, SR400/500

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-17

## Goal
Yamaha's vintage and classic models: XS650 (1968-1985) — the iconic parallel twin; RD350/400 (1973-1980) — two-stroke sport bikes; and SR400/500 (1978-2021) — the kickstart-only thumper.

CLI: `python -m pytest tests/test_phase42_yamaha_vintage.py -v`

Outputs: `data/knowledge/known_issues_yamaha_vintage.json` (10 issues), 6 tests

## Key Concepts
- XS650 points ignition requires regular adjustment — electronic conversion (Pamco/Boyer) is the #1 reliability upgrade
- XS650 charging system has 40+ year old magnets losing strength — PMA conversion from Hugh's Handbuilt is definitive
- XS650 leaks oil everywhere — Viton O-rings for pushrod tubes, Athena gaskets for cases
- XS650 cam chain is manual tensioner — advantage over modern automatic for precision adjustment
- RD350/400 Autolube oil injection is a 50-year-old ticking time bomb — premix at 32:1 is safer
- RD expansion chambers are TUNED exhaust — dents literally change engine performance
- RD reed valves are the unsung hero of two-stroke performance — Boyesen carbon fiber upgrade
- SR400 kickstart technique is the defining owner experience — piston positioning is the key
- SR400 single carb makes jetting changes simple — one carb, one set of jets
- SR400 valve adjustment every 4000 miles — 10-minute job, accessible on both sides of head

## Verification Checklist
- [x] 10 issues load correctly (4 XS650, 3 RD350/400, 3 SR400/500)
- [x] Year range queries return correct results (1978 query returns 5+ hits)
- [x] Critical severity issues present (XS650 charging, RD Autolube)
- [x] Symptom searches work (loss of power: 2+, won't start: 1+)
- [x] Forum tips present in fix procedures
- [x] All 6 tests pass (1.20s)

## Results
| Metric | Value |
|--------|-------|
| Known issues | 10 (XS650: points/charging/oil/cam chain; RD: Autolube/chambers/reeds; SR: kickstart/carb/valves) |
| Tests | 6/6, 1.20s |
| Severity breakdown | 2 critical, 3 high, 5 medium, 0 low |
| Year coverage | 1968-2021 |

The vintage phase introduces two-stroke diagnostics (RD) alongside the more familiar four-stroke issues. The XS650 and SR400 represent the café racer custom scene — diagnostic knowledge that serves a dedicated owner community willing to maintain 40+ year old machines.
