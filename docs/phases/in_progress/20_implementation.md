# MotoDiag Phase 20 — Harley Revolution Max (2021+)

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-04-16

## Goal
Build the known-issues knowledge base for the Harley-Davidson Revolution Max platform (2021+). This is Harley's modern liquid-cooled DOHC engine — used in the Sportster S, Nightster, and Pan America. Unlike the old Revolution (V-Rod), the Rev Max has variable valve timing, ride-by-wire, cornering ABS/TC, and a TFT instrument cluster. These bikes are still new so many issues are emerging patterns rather than 20-year-proven failures.

CLI: `python -m pytest tests/test_phase20_harley_revmax.py -v`

Outputs: `data/knowledge/known_issues_harley_revmax.json` (10 issues), 6 tests

## Logic
- Create 10 known issues for the Revolution Max platform
- Focus on early-production issues, software/electronics, and new-technology growing pains
- Each issue follows established schema with forum tips from HDForums and Sportster S owner groups

Data flow: JSON file -> load_known_issues_file() -> SQLite known_issues table -> query via issues_repo

## Key Concepts
- Revolution Max 1250/1250T engine: liquid-cooled DOHC 60-degree V-twin, VVT
- Models: Sportster S (RH1250S), Nightster (RH975), Pan America 1250/Special
- Modern electronics: TFT dash, ride modes, cornering ABS, traction control, cruise control
- Ride-by-wire throttle (no cable)
- Mid-mount controls on Sportster S (unusual for Harley)
- Oil change procedure different from all prior Harleys (spin-on filter, separate primary)

## Verification Checklist
- [ ] 10 issues load into database
- [ ] Year range queries return correct results for 2023
- [ ] DTC search finds relevant codes
- [ ] Critical severity issues present
- [ ] Forum tips present in fix procedures
- [ ] All 6 tests pass

## Risks
- Platform is only ~5 years old — failure patterns still emerging
- Some issues may be resolved by TSBs or software updates already
- Smaller owner community than established Harley platforms means fewer forum data points
