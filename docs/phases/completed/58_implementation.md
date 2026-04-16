# MotoDiag Phase 58 — Suzuki GSX-R750 (1996+)

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-16

## Goal
The class-defining GSX-R750 — shared platform with GSX-R600 but with unique issues from the larger displacement and torque.

CLI: `python -m pytest tests/test_phase58_suzuki_gsx_r750.py -v`

Outputs: `data/knowledge/known_issues_suzuki_gsx_r750.json` (10 issues), 6 tests

## Key Concepts
- Second gear failure (K1-K5): engagement dogs round off, MTC undercut gears for permanent fix
- Stator/charging: same as GSX-R600, slightly worse due to higher output demand
- CCT rattle: same manual tensioner fix, wears faster on 750 from higher torque
- Fuel pump relay: $15 part that strands more riders than anything, carry a spare
- SRAD (1996-1999) coolant system: 25+ year old hoses need complete replacement
- Rear shock linkage bearing wear: All Balls Racing kit, service every 15-20K miles
- TPS calibration drift: free fix with multimeter, reset ECU adaptation after
- Chain and sprocket: front sprocket wears fastest, Scottoiler extends chain life
- Brake master cylinder: flush fluid every 2 years, replace banjo bolt crush washers
- Headstock bearing wear: check before buying a steering damper

## Verification Checklist
- [x] All 6 tests pass (1.71s)

## Results
| Metric | Value |
|--------|-------|
| Known issues | 10 |
| Tests | 6/6, 1.71s |
| Severity breakdown | 1 critical, 2 high, 7 medium |
| Year coverage | 1996-2026 |
