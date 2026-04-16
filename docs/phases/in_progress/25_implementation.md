# MotoDiag Phase 25 — Honda CBR600RR (2003-2024)

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-04-16

## Goal
Build the known-issues knowledge base for the Honda CBR600RR — the race-focused 600cc supersport that replaced the F4i. Spans 2003-2024 across multiple generations with significant electronics upgrades over time (HESD, C-ABS, ride modes on later models). The RR is more highly strung than the F-series and has different failure modes.

CLI: `python -m pytest tests/test_phase25_honda_cbr600rr.py -v`

Outputs: `data/knowledge/known_issues_honda_cbr600rr.json` (10 issues), 6 tests

## Key Concepts
- 2003-2006: First gen, HISS, PGM-FI, conventional instrument cluster
- 2007-2012: HESD (Honda Electronic Steering Damper), updated electronics
- 2013-2024: C-ABS (Combined ABS), further electronics, final production years
- All use EFI, HISS immobilizer, and Honda inline-4 platform

## Verification Checklist
- [ ] 10 issues load, 6 tests pass

## Risks
- Long production run (21 years) means some issues are generation-specific
