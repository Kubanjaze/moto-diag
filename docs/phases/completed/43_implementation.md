# MotoDiag Phase 43 — Yamaha Electrical Systems + Diagnostics

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-17

## Goal
Cross-model Yamaha electrical systems and diagnostic procedures. Covers self-diagnostic blink codes, stator/regulator patterns, wiring harness issues, and diagnostic tools.

CLI: `python -m pytest tests/test_phase43_yamaha_electrical.py -v`

Outputs: `data/knowledge/known_issues_yamaha_electrical.json` (10 issues), 6 tests

## Key Concepts
- Yamaha self-diagnostic mode: FI light blinks — long=tens, short=units (code 12 = TPS, 33 = injector, 46 = immobilizer)
- Universal stator connector failure spans every Yamaha from the 1990s — hard-wire is the permanent fix
- MOSFET regulator upgrade is universal recommendation — SH775 fits most 3-phase Yamaha charging systems
- Ground wire corrosion is the most misdiagnosed fault — clean grounds should be first diagnostic step
- Wiring harness PVC insulation becomes brittle from heat after 10-20 years — inspect near exhaust
- Blown fuses are symptoms, not the problem — always find the underlying short
- YDIS immobilizer: key chip + antenna ring — Woolich Racing can program keys and disable system
- LED upgrades need LED-compatible flasher relay and quality EMI-shielded headlight bulbs
- Lithium batteries need lithium-specific tender — lead-acid chargers destroy lithium cells
- Woolich Racing diagnostic tool ($200) replaces $3000 dealer system for most diagnostic functions

## Verification Checklist
- [x] 10 issues load correctly
- [x] Year range queries return correct results (2015 query returns 7+ hits)
- [x] Critical severity issues present (stator connector)
- [x] Symptom searches work (battery not charging: 2+, won't start: 1+)
- [x] Forum tips present in fix procedures
- [x] All 6 tests pass (1.73s)

## Results
| Metric | Value |
|--------|-------|
| Known issues | 10 (self-diagnostic, stator connector, MOSFET upgrade, grounds, harness, fuses/relays, immobilizer, LED, batteries, Woolich) |
| Tests | 6/6, 1.73s |
| Severity breakdown | 1 critical, 3 high, 6 medium, 0 low |
| Year coverage | 1985-2026 |

The electrical systems phase consolidates the universal Yamaha electrical knowledge that applies across all models — stator connector hard-wiring, MOSFET upgrade, ground cleaning, and diagnostic procedures that every Yamaha mechanic should know.
