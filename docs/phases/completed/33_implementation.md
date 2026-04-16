# MotoDiag Phase 33 — Honda Electrical Systems + PGM-FI

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-16

## Goal
Cross-model Honda electrical systems knowledge base. PGM-FI self-diagnostics, HISS immobilizer, stator/regulator across eras, Honda-specific electrical patterns.

CLI: `python -m pytest tests/test_phase33_honda_electrical.py -v`

Outputs: `data/knowledge/known_issues_honda_electrical.json` (10 issues), 6 tests

## Key Concepts
- PGM-FI blink codes: no dealer tool needed, count long/short blinks for 2-digit code
- HISS immobilizer: dealer-only key programming, carry both keys separately, antenna ring is common failure
- Reg/rec is THE Honda reliability issue — MOSFET upgrade + stator connector hard-wire is the definitive fix
- Always replace stator AND regulator together — a bad reg kills stators
- 80% of no-start calls: dead battery, kill switch, side stand switch, or clutch switch
- Bank angle sensor (tip sensor, code 54) triggers after any drop — reset procedure is turn off/wait/restart
- Annual 5-minute charging test catches failures weeks before they strand you

## Verification Checklist
- [x] 10 issues load
- [x] Cross-era coverage for 2010 (7+ issues)
- [x] Critical severity present (2: reg/rec, stator)
- [x] Won't start and CEL symptoms find relevant issues
- [x] Forum tips in all procedures
- [x] All 6 tests pass (1.23s)

## Results
| Metric | Value |
|--------|-------|
| Known issues | 10 (PGM-FI blink codes, HISS, reg/rec, stator, starter relay, FI sensor faults, ground corrosion, headlight/bulbs, fuse diagnosis, annual charge test) |
| Tests | 6/6, 1.23s |
| Severity breakdown | 2 critical, 3 high, 3 medium, 2 low |
| Year coverage | 1985-2025 (all Honda eras) |

The most practically useful Honda phase — PGM-FI blink code reading and the annual charging test protocol alone justify this phase for any shop working on Hondas.
