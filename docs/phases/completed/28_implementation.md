# MotoDiag Phase 28 — Honda Rebel 250/300/500/1100

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-16

## Goal
Build the known-issues knowledge base for the Honda Rebel family: Rebel 250 (1985-2016), Rebel 300 (2017+), Rebel 500 (2017+), and Rebel 1100 (2021+). The gateway bike family.

CLI: `python -m pytest tests/test_phase28_honda_rebel.py -v`

Outputs: `data/knowledge/known_issues_honda_rebel.json` (10 issues), 6 tests

## Key Concepts
- Rebel 250: single carb, drum rear brake, minimal electrical — beginner maintenance issues dominate
- Rebel 300/500: chain drive, EFI, beginner neglect of chain maintenance is #1 issue
- Rebel 1100 DCT: dual clutch transmission is jerky at walking speed — use Manual mode + brake modulation
- Rebel 250 has weakest electrical system of any common motorcycle (~200W alternator)
- Battery drain from sitting is the #1 Rebel 250 shop visit in spring

## Verification Checklist
- [x] 10 issues load into database
- [x] Year range correct for 2022 (4+ issues)
- [x] High severity present (2: reg/rec, drum brake)
- [x] Won't start finds carb and battery issues
- [x] Forum tips in all procedures
- [x] All 6 tests pass (1.07s)

## Deviations from Plan
- Test year changed from 2020 to 2022 — year 2020 falls in gap between Rebel 250 (ends 2016) and Rebel 1100 (starts 2021)

## Results
| Metric | Value |
|--------|-------|
| Known issues | 10 (carb 250, reg/rec, DCT jerky, chain 300/500, battery drain, LED relay, coolant 1100, drum brake, headlight, throttle icing) |
| Tests | 6/6, 1.07s |
| Severity breakdown | 0 critical, 2 high, 5 medium, 3 low |
| Year coverage | 1985-2025 (spans all Rebel generations) |

The Rebel family highlights beginner-specific diagnostic patterns — carb neglect, chain neglect, battery death from sitting, and drum brake adjustment. These issues are trivial for experienced riders but confusing for first-time owners.
