# MotoDiag Phase 66 — Suzuki Dual-Sport: DR-Z400S/SM, DR650SE

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-16

## Goal
Suzuki's thumper dual-sport lineup — DR-Z400S, DR-Z400SM supermoto, and the legendary DR650SE.

CLI: `python -m pytest tests/test_phase66_suzuki_dual_sport.py -v`

Outputs: `data/knowledge/known_issues_suzuki_dual_sport.json` (10 issues), 6 tests

## Key Concepts
- DR-Z400 jetting: 3x3 mod (air box lid + rejet + fuel screw) is legendary, Dynojet Stage 1 kit
- DR-Z400 valve clearance: single cylinder = easy check, kick start getting harder = tight valves
- DR-Z400SM supermoto brakes: 300mm front disc, caliper rebuild, annual fluid flush for stunt/track
- DR650SE carburetor: altitude-sensitive thumper, carry main jets for elevation changes
- DR650SE oil consumption: valve stem seals (startup smoke) vs piston rings (constant smoke)
- Off-road chain wear: mud/sand acts as abrasive, clean and lube after every ride, Maxima Chain Wax
- DR-Z400 weak charging: minimal stator output, LED conversion + switched circuits for accessories
- DR650SE suspension: Race Tech emulators + Cogent Dynamics rear shock, stock shock not rebuildable
- Kick start mechanism: return spring, pivot bolt, proper kick technique prevents gear damage
- DR650SE starter system: relay is cheapest check, high compression demands strong battery

## Verification Checklist
- [x] All 6 tests pass (1.57s)

## Results
| Metric | Value |
|--------|-------|
| Known issues | 10 |
| Tests | 6/6, 1.57s |
| Severity breakdown | 0 critical, 2 high, 8 medium |
| Year coverage | 1996-2026 |
