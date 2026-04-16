# MotoDiag Phase 54 — Kawasaki Dual-Sport: KLR650, KLX250/300, Versys 650/1000

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-16

## Goal
Kawasaki's adventure and dual-sport lineup — the legendary KLR650, the trail-focused KLX250/300, and the road-biased Versys 650/1000.

CLI: `python -m pytest tests/test_phase54_kawasaki_dual_sport.py -v`

Outputs: `data/knowledge/known_issues_kawasaki_dual_sport.json` (10 issues), 6 tests

## Key Concepts
- KLR650 doohickey (balancer chain tensioner) is the #1 known failure — preventive replacement mandatory
- KLR650 overheating: no factory oil cooler on a big single, aftermarket cooler is the #2 mod
- KLR650 Gen 2 (2008+) FI lean surge at cruise — TPS adjustment and Dobeck EJK fuel controller
- KLX250/300 valve clearance tightening — shim-under-bucket, check every 15K miles
- Versys 650 stock suspension inadequate for loaded touring — fork springs + rear shock upgrade transforms the bike
- Versys 1000 ride-by-wire throttle hunting at low speed — ECU flash or Power Commander
- KLR650 subframe cracking under heavy luggage — aluminum cases and subframe braces prevent failure
- KLX250/300 factory lean jetting — free mods (snorkel removal, pilot screw) plus Dynojet kit
- Versys 650 chain wear from 520 spec — upgrade to X-ring chain, maintain every 500 miles
- KLR650 stator/charging failure — marginal system needs MOSFET reg/rec upgrade for accessories

## Verification Checklist
- [x] All 6 tests pass (1.67s)

## Results
| Metric | Value |
|--------|-------|
| Known issues | 10 |
| Tests | 6/6, 1.67s |
| Severity breakdown | 1 critical, 4 high, 5 medium |
| Year coverage | 1987-2026 |
