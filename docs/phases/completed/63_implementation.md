# MotoDiag Phase 63 — Suzuki Bandit 600/1200/1250 (1995-2012)

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-16

## Goal
Suzuki's standard/sport-touring workhorse — air/oil-cooled Bandit 600/1200 and liquid-cooled Bandit 1250.

CLI: `python -m pytest tests/test_phase63_suzuki_bandit.py -v`

Outputs: `data/knowledge/known_issues_suzuki_bandit.json` (10 issues), 6 tests

## Key Concepts
- Air/oil-cooled Bandit 600/1200 overheating: full-synthetic oil, aftermarket oil cooler for commuters
- Carb bank rebuild and sync: Keyster kits, vacuum sync is critical for smooth idle
- Bandit 1250 FI issues: TPS drift, STPS secondary throttle, idle air control carbon
- Charging system: same Suzuki inline-4 weakness, naked bike has better reg/rec airflow
- Bandit 600 CCT: same GSX-R600 engine and tensioner, APE manual replacement
- Budget suspension: Race Tech emulators + YSS/Hagon rear shock, Bandit-specific dimensions
- Fuel petcock diaphragm failure: floods carbs and dilutes oil, Pingel manual petcock
- Brake system: Tokico calipers, stainless lines, Bandit 1200S calipers swap to 1200N
- Chain and sprocket: commuter wear patterns, Scottoiler for daily riders
- Wiring and ground corrosion: naked bike design exposes everything to weather

## Verification Checklist
- [x] All 6 tests pass (1.62s)

## Results
| Metric | Value |
|--------|-------|
| Known issues | 10 |
| Tests | 6/6, 1.62s |
| Severity breakdown | 0 critical, 4 high, 6 medium |
| Year coverage | 1995-2012 |
