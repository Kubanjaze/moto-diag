# MotoDiag Phase 74 — Ignition System Diagnostics (Cross-Platform)

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-17

## Goal
Universal ignition system diagnostics covering all motorcycles — spark plugs, coils, CDI/ECU, pickup coils, plug wires, points conversion, timing, kill switch, misfires, and coil-on-plug systems across Honda, Yamaha, Kawasaki, Suzuki, and Harley-Davidson.

CLI: `python -m pytest tests/test_phase74_cross_platform_ignition.py -v`

Outputs: `data/knowledge/known_issues_cross_platform_ignition.json` (10 issues), 6 tests

## Key Concepts
- Spark plug fouling and heat range: NGK cross-reference, heat range selection for modified engines
- Ignition coil testing: primary 2-4 ohms, secondary 10-15K ohms, stick coils vs remote coils
- CDI/ECU module failure: swap testing without a scope, NOS availability for vintage models
- Pickup coil (CKP sensor): resistance testing, air gap verification, wiring insulation check
- Plug wire and cap resistance: NGK 5K ohm caps, wire resistance 5-15K per foot
- Points ignition to electronic conversion: Dyna S, Pamco, Boyer Bransden kits by make
- Ignition timing: static with test light, dynamic with strobe, advance mechanism verification
- Kill switch circuit: intermittent open causing random no-spark, contact cleaner fix
- Misfires under load: lean vs ignition differential diagnosis, plug reading technique
- Coil-on-plug (COP) systems: modern bike diagnostics, individual coil swap testing

## Verification Checklist
- [x] All 6 tests pass (0.84s)
- [x] Multi-make coverage verified (Honda 2, Kawasaki 3, Suzuki 3, Yamaha 1, Harley 1)

## Results
| Metric | Value |
|--------|-------|
| Known issues | 10 |
| Tests | 6/6, 0.84s |
| Severity breakdown | 0 critical, 5 high, 4 medium, 1 low |
| Year coverage | 1965-2026 |
| Makes covered | Honda, Yamaha, Kawasaki, Suzuki, Harley-Davidson |
