# MotoDiag Phase 42 — Yamaha Vintage: XS650, RD350/400, SR400/500

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-04-17

## Goal
Yamaha's vintage and classic models: XS650 (1968-1985) — the iconic parallel twin; RD350/400 (1973-1980) — two-stroke sport bikes; and SR400/500 (1978-2021) — the kickstart-only thumper. These bikes are heavily represented in the custom/café racer scene and have unique maintenance needs.

CLI: `python -m pytest tests/test_phase42_yamaha_vintage.py -v`

Outputs: `data/knowledge/known_issues_yamaha_vintage.json` (10 issues), 6 tests

## Logic
- Create 10 known issues: ~4 XS650, ~3 RD350/400, ~3 SR400/500
- XS650: points ignition, charging, oil leaks, cam chain
- RD: two-stroke specific (oil injection, reed valves, expansion chambers)
- SR: kickstart-only starting, carb, valve adjustment
- Include forum-sourced fixes with real mechanic knowledge

## Key Concepts
- XS650 is the most popular vintage Yamaha for custom builds — electrical conversion is common
- RD series are two-strokes — completely different diagnostic approach (premix, oil injection, port timing)
- SR400 was sold until 2021 in some markets — a modern bike with vintage technology
- Points ignition timing requires dwell meter and timing light
- Two-stroke diagnostics: plug reading, port inspection, expansion chamber condition

## Verification Checklist
- [ ] 10 issues load correctly
- [ ] Year range queries return correct results
- [ ] Critical severity issues present
- [ ] Symptom searches work (loss of power, won't start)
- [ ] Forum tips present in fix procedures
- [ ] All tests pass

## Risks
- Two-stroke diagnostics are fundamentally different from four-stroke — must explain clearly
- Vintage parts availability varies — include aftermarket/reproduction sources
