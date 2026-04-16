# MotoDiag Phase 20 — Harley Revolution Max (2021+)

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-16

## Goal
Build the known-issues knowledge base for the Harley-Davidson Revolution Max platform (2021+). This is Harley's modern liquid-cooled DOHC engine — used in the Sportster S, Nightster, and Pan America. Unlike the old Revolution (V-Rod), the Rev Max has variable valve timing, ride-by-wire, cornering ABS/TC, and a TFT instrument cluster. These bikes are still new so many issues are emerging patterns rather than 20-year-proven failures.

CLI: `python -m pytest tests/test_phase20_harley_revmax.py -v`

Outputs: `data/knowledge/known_issues_harley_revmax.json` (10 issues), 6 tests

## Logic
- Created 10 known issues for the Revolution Max platform
- Focus on early-production issues, software/electronics, and new-technology growing pains
- Each issue follows established schema with forum tips from HDForums and Sportster S owner groups

Data flow: JSON file -> load_known_issues_file() -> SQLite known_issues table -> query via issues_repo

## Key Concepts
- Revolution Max 1250/1250T/975 engine: liquid-cooled DOHC 60-degree V-twin, VVT
- Models: Sportster S (RH1250S), Nightster (RH975), Pan America 1250/Special
- Modern electronics: TFT dash (freeze/reboot issues), ride modes, cornering ABS with IMU, traction control
- Ride-by-wire throttle — no cable, software throttle mapping per mode
- Chain final drive on Sportster S/Nightster (belt on Pan America) — first chain-drive Harley in modern era
- Hydraulic clutch (like V-Rod, unlike traditional cable Harleys)
- Higher parasitic battery draw from always-on security, Bluetooth, TFT standby
- Oil change procedure different from all prior Harleys — smaller capacity, specific check procedure

## Verification Checklist
- [x] 10 issues load into database
- [x] Year range queries return correct results for 2023
- [x] DTC search finds coolant issue (P0128)
- [x] High severity issues present (3: coolant leak, side stand sensor, chain maintenance)
- [x] Forum tips present in fix procedures
- [x] All 6 tests pass (1.16s)

## Risks
- Platform is only ~5 years old — failure patterns still emerging. Mitigated by focusing on most commonly reported issues across multiple owner forums.
- Some issues may be resolved by TSBs or software updates. Noted in fix procedures where applicable.

## Results
| Metric | Value |
|--------|-------|
| Known issues | 10 (TFT freeze, throttle hesitation, water pump gasket, oil consumption, side stand sensor, cornering ABS false intervention, exhaust heat shield, chain maintenance, battery drain, mid-mount ergonomics) |
| Tests | 6/6, 1.16s |
| Severity breakdown | 0 critical, 3 high, 5 medium, 2 low |
| DTC codes covered | U0155, P0128, P0520, P0562 |
| Year coverage | 2021-2025 (ongoing production) |

The Revolution Max is the most electronics-heavy Harley ever built. Half the issues are software/electronics (TFT, ride-by-wire, ABS/TC, battery drain) vs. mechanical — a fundamental shift from air-cooled Harley troubleshooting where 80% of problems are gaskets, seals, and charging systems.
