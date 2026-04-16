# MotoDiag Phase 77 — Drivetrain Diagnostics (Cross-Platform)

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-17

## Goal
Universal drivetrain diagnostics — chain stretch, sprocket wear, chain lube, belt drive, shaft drive, clutch drag, clutch cable/hydraulic, transmission shifting, countershaft seal, and final drive alignment across all makes and drive types.

CLI: `python -m pytest tests/test_phase77_cross_platform_drivetrain.py -v`

Outputs: `data/knowledge/known_issues_cross_platform_drivetrain.json` (10 issues), 6 tests

## Key Concepts
- Chain stretch measurement: half-link lift test, 1.5% stretch = replacement, measure under tension
- Sprocket wear: hooked teeth, countershaft wears 2x faster than rear, steel front mandatory
- Chain lubrication: wax (Maxima Chain Wax) vs wet (chain lube) vs auto-oiler (Scottoiler) comparison
- Belt drive: tension check, visual inspection for cracks/missing teeth, Harley/Kawasaki/Suzuki specifics
- Shaft drive service: hypoid gear oil every 6-10K miles, seal inspection, universal joint wear
- Clutch drag and basket notching: V-twin torque pulses accelerate wear, filing vs billet basket
- Clutch cable adjustment: free play spec, hydraulic bleeding (DOT 4 or mineral oil per make)
- Transmission shifting: false neutral from worn shift forks, hard shifting from bent shift lever
- Countershaft seal: leaks when sprocket removed, $5 seal prevents transmission oil loss
- Final drive alignment: string method for chain, laser for precision, belt deflection spec

## Verification Checklist
- [x] All 6 tests pass (0.69s)
- [x] Multi-make coverage verified (Honda 3, Kawasaki 2, Suzuki 2, Yamaha 2, Harley 1)

## Results
| Metric | Value |
|--------|-------|
| Known issues | 10 |
| Tests | 6/6, 0.69s |
| Severity breakdown | 1 critical, 4 high, 5 medium |
| Year coverage | 1980-2026 |
| Makes covered | Honda, Yamaha, Kawasaki, Suzuki, Harley-Davidson |
