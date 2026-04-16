# MotoDiag Phase 56 — Kawasaki Electrical Systems + FI Dealer Mode

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-16

## Goal
Cross-model Kawasaki electrical systems — FI self-diagnostic mode, charging, KLEEN/PAIR, KIPASS, LED upgrades, grounds, starter circuit, parasitic draw, KTRC/KIBS electronics, and connector corrosion.

CLI: `python -m pytest tests/test_phase56_kawasaki_electrical.py -v`

Outputs: `data/knowledge/known_issues_kawasaki_electrical.json` (10 issues), 6 tests

## Key Concepts
- FI dealer mode: dash button sequence reads DTC blink codes — free diagnostics on every EFI Kawasaki
- Stator/reg-rec failure: universal diagnosis across all models, MOSFET upgrade, solder stator connector
- KLEEN/PAIR system: block-off plates eliminate decel popping with aftermarket exhaust
- KIPASS immobilizer: CR2032 fob battery, antenna ring failure, key registration procedure
- LED lighting: flasher relay swap (not load resistors), CAN-bus decoder for 2017+ models
- Ground corrosion: frame neck is the #1 ground point to clean — fixes 80% of electrical gremlins
- Starter system: relay → clutch switch → kickstand switch → motor diagnostic path
- Parasitic draw: measure with multimeter, pull fuses to isolate, Battery Tender for storage
- KTRC/KIBS sensor calibration: dirty wheel speed sensors and low voltage cause most faults
- Multi-pin connector corrosion: one bad pin creates cascading symptoms across unrelated circuits

## Verification Checklist
- [x] All 6 tests pass (1.78s)

## Results
| Metric | Value |
|--------|-------|
| Known issues | 10 |
| Tests | 6/6, 1.78s |
| Severity breakdown | 0 critical, 3 high, 5 medium, 2 low |
| Year coverage | 1980-2026 |
