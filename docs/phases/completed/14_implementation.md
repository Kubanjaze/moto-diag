# MotoDiag Phase 14 — Harley Twin Cam 88/88B (1999–2006)

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-16

## Goal
Populate the knowledge base for the Harley-Davidson Twin Cam 88 engine (1999–2006). Covers the infamous cam chain tensioner problem, compensator issues, oil sumping, and EFI transition-era problems.

CLI: Data loaded via `motodiag db init`

Outputs: `data/knowledge/known_issues_harley_tc88.json` (10 issues), 7 tests

## Logic
Created 10 known issues for TC88:
1. Cam chain tensioner shoe failure — tick of death (CRITICAL)
2. Compensator sprocket rattle — primary clunk
3. Oil sumping — crankcase accumulation
4. Intake manifold leak — lean surge
5. Stator failure — charging breakdown
6. Inner cam bearing failure (CRITICAL)
7. EFI TPS calibration drift — surging
8. Primary chain tensioner wear — chain slap
9. Exhaust header bolt seizure — broken bolt in aluminum head
10. Rear cylinder overheating — heat management

## Key Concepts
- TC88: 1450cc, chain-driven cams with plastic tensioner shoes (THE failure point)
- Gear-driven cam conversion is the forum-consensus fix (S&S 510G, Feuling)
- First widespread Delphi EFI on Harleys
- "If you're in for tensioners, do the whole job" — bearing, chain, oil pump, all at once

## Verification Checklist
- [x] 10 issues load, [x] cam tensioner is critical, [x] year range works
- [x] compensator searchable, [x] symptom search finds 2+ ticking issues
- [x] DTC P0562 finds stator, [x] forum tips present, [x] 7 tests pass in 1.11s

## Results
| Metric | Value |
|--------|-------|
| Known issues | 10 |
| Severity | 2 critical, 2 high, 5 medium, 1 low |
| Forum tips | 10 |
| Tests | 7, 1.11s |
