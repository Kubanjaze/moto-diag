# MotoDiag Phase 76 — Brake System Diagnostics (Cross-Platform)

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-17

## Goal
Universal brake system diagnostics — fluid contamination, caliper rebuild, pad selection, rotor inspection, master cylinder, stainless lines, ABS sensors, ABS bleeding, rear drum, and caliper bolt torque across all makes.

CLI: `python -m pytest tests/test_phase76_cross_platform_brakes.py -v`

Outputs: `data/knowledge/known_issues_cross_platform_brakes.json` (10 issues), 6 tests

## Key Concepts
- Brake fluid contamination: DOT 4 absorbs 2-3% water per year, 2-year flush cycle critical for safety
- Caliper piston seizure: rebuild procedure (seals, pistons, dust boots), when pitting means replacement
- Brake pad selection: sintered (HH) for sport/wet, organic for low dust, semi-metallic for balance
- Rotor warping: minimum thickness stamped on rotor, runout measurement with dial indicator
- Master cylinder: internal seal wear causes spongy lever, rebuild kit vs replacement decision
- Stainless braided lines: best bang-for-buck brake upgrade, model-specific kits, proper bleeding
- ABS wheel speed sensor: cleaning at every tire change, gap setting 0.5-1.5mm, brake dust contamination
- ABS modulator bleeding: requires specific sequence different from standard bleeding, service manual essential
- Rear drum brake: adjustment, shoe replacement, spring orientation, return spring fatigue
- Caliper mounting bolt torque: Loctite 243, safety wire on track bikes, cross-make torque specs

## Verification Checklist
- [x] All 6 tests pass
- [x] Multi-make coverage verified (Honda 3, Kawasaki 2, Suzuki 2, Yamaha 2, Harley 1)

## Results
| Metric | Value |
|--------|-------|
| Known issues | 10 |
| Tests | 6/6 |
| Severity breakdown | 3 critical, 4 high, 2 medium, 1 low |
| Year coverage | 1980-2026 |
| Makes covered | Honda, Yamaha, Kawasaki, Suzuki, Harley-Davidson |
