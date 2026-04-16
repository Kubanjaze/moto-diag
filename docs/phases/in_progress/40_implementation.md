# MotoDiag Phase 40 — Yamaha VMAX (1985-2020)

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-17

## Goal
The Yamaha VMAX — a muscle bike icon spanning two generations: Gen 1 (1985-2007) carbureted V4 with the legendary V-Boost system, and Gen 2 (2009-2020) fuel-injected V4 with modern electronics.

CLI: `python -m pytest tests/test_phase40_yamaha_vmax.py -v`

Outputs: `data/knowledge/known_issues_yamaha_vmax.json` (10 issues), 6 tests

## Key Concepts
- V-Boost is the VMAX's signature feature — butterfly valves linking carb pairs for massive top-end surge
- Gen 1 VMAX charging system requires the "triple upgrade": MOSFET reg + hard-wire connector + relocate
- Gen 1 steel tank (hidden under seat) corrodes internally — recurring carb problems signal tank rust
- Gen 1 shaft drive U-joint develops play at high mileage from VMAX torque loads
- Gen 2 is dual-injection (8 injectors) — secondary injectors clog from infrequent high-RPM use
- Gen 2 weighs 683 lbs — accelerates brake pad and tire consumption dramatically
- Gen 2 electronics are simpler than R1 (no IMU) but TC works hard on a 200hp bike
- Both generations run extreme exhaust temps — copper gaskets mandatory, header bluing is normal

## Verification Checklist
- [x] 10 issues load correctly (5 Gen 1, 5 Gen 2)
- [x] Year range queries return correct results (2000 query returns 4+ Gen 1 hits)
- [x] Critical severity issues present (Gen 1 charging)
- [x] Symptom searches work (loss of power: 2+, won't start: 1+)
- [x] Forum tips present in fix procedures
- [x] All 6 tests pass (1.37s)

## Results
| Metric | Value |
|--------|-------|
| Known issues | 10 (Gen 1: V-Boost, carbs, charging, shaft drive, tank rust; Gen 2: FI, cooling, brakes/tires, electronics, exhaust) |
| Tests | 6/6, 1.37s |
| Severity breakdown | 1 critical, 2 high, 7 medium, 0 low |
| Year coverage | 1985-2020 |

The VMAX is a unique diagnostic challenge — a muscle bike that straddles eras. Gen 1 owners are enthusiasts maintaining 30-40 year old bikes; Gen 2 owners contend with the physics of 200hp and 683 lbs. Both need specialized knowledge that doesn't apply to any other Yamaha.
