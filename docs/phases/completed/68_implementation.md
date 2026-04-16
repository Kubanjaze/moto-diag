# MotoDiag Phase 68 — Suzuki Electrical Systems + FI Dealer Mode

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-16

## Goal
Cross-model Suzuki electrical systems — C-mode self-diagnostic, charging, PAIR, grounds, starter circuit, parasitic draw, TC/ABS sensors, LED conversion, connector corrosion, and FI relay.

CLI: `python -m pytest tests/test_phase68_suzuki_electrical.py -v`

Outputs: `data/knowledge/known_issues_suzuki_electrical.json` (10 issues), 6 tests

## Key Concepts
- C-mode self-diagnostic: ground dealer mode connector to read FI blink codes — free diagnostics on every EFI Suzuki
- Stator/reg-rec: universal diagnosis across all models (voltage at RPM → stator AC → reg/rec diode check)
- PAIR system: block-off plates eliminate decel popping with aftermarket exhaust, model-specific bolt patterns
- Ground corrosion: frame neck is the most critical ground point, clean with wire brush + dielectric grease
- Starter system: universal diagnostic path — battery → relay → safety switches → motor
- Parasitic draw: measure with multimeter, Battery Tender for storage, aftermarket accessories are #1 cause
- S-DMS / TC / ABS sensors: dirty wheel speed sensors cause most faults, clean at every tire change
- LED conversion: flasher relay swap (not load resistors), quality headlight brands only
- Wiring connector corrosion: one bad pin creates cascading symptoms across unrelated circuits
- FI relay: $15 part that strands more riders than anything, carry a spare

## Verification Checklist
- [x] All 6 tests pass (0.68s)

## Results
| Metric | Value |
|--------|-------|
| Known issues | 10 |
| Tests | 6/6, 0.68s |
| Severity breakdown | 0 critical, 3 high, 5 medium, 2 low |
| Year coverage | 1977-2026 |
