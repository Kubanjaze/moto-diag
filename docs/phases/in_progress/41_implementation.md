# MotoDiag Phase 41 — Yamaha Dual-Sport: WR250R/X, XT250, Tenere 700

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-04-17

## Goal
Yamaha's dual-sport and adventure lineup: WR250R/X (2008-2020), XT250 (2008-2023), and Tenere 700 (2021+). The WR250R is a premium lightweight dual-sport; the XT250 is a budget commuter/trail bike; the Tenere 700 is Yamaha's CP2-powered adventure bike. Different price points, different missions, all off-road capable.

CLI: `python -m pytest tests/test_phase41_yamaha_dualsport.py -v`

Outputs: `data/knowledge/known_issues_yamaha_dualsport.json` (10 issues), 6 tests

## Logic
- Create 10 known issues: ~3 WR250R/X, ~3 XT250, ~4 Tenere 700
- WR250R: premium dual-sport issues (suspension, fuel injection on a small engine, stator)
- XT250: budget bike issues (carbureted, basic suspension, low power limitations)
- Tenere 700: CP2 adventure issues (wind protection, off-road crashes, navigation electronics)
- Include forum-sourced fixes with real mechanic knowledge

## Key Concepts
- WR250R is EFI with a high-revving 250cc single — advanced for its class
- XT250 is carbureted and air-cooled — simplest Yamaha in production
- Tenere 700 uses the MT-07's CP2 engine — reliable but in an adventure chassis
- Off-road use creates unique damage patterns: radiator hits, lever bends, skid plate needs
- Tenere 700 has minimal electronics compared to competitors (no IMU, basic TC)

## Verification Checklist
- [ ] 10 issues load correctly
- [ ] Year range queries return correct results
- [ ] Critical severity issues present
- [ ] Symptom searches work (loss of power, won't start)
- [ ] Forum tips present in fix procedures
- [ ] All tests pass

## Risks
- Three distinct bikes in one phase — need clear model identification
- Off-road issues differ from street — crash damage vs mechanical wear
