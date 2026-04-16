# MotoDiag Phase 39 — Yamaha Cruisers: V-Star / Bolt

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-04-17

## Goal
Yamaha's cruiser lineup: V-Star 250 (2008-2021), V-Star 650 (1998-2019), V-Star 950 (2009-2017), V-Star 1100 (1999-2009), V-Star 1300 (2007-2017), and Bolt/R-Spec (2014+). Air-cooled V-twins spanning carbureted and EFI eras. The V-Star 650 is one of the best-selling cruisers of all time. The Bolt is Yamaha's modern answer to the Harley Sportster.

CLI: `python -m pytest tests/test_phase39_yamaha_cruisers.py -v`

Outputs: `data/knowledge/known_issues_yamaha_cruisers.json` (10 issues), 6 tests

## Logic
- Create 10 known issues covering V-Star and Bolt platforms
- V-Star carbureted models: carb issues, petcock, charging
- V-Star EFI models: fuel pump, TPS, idle control
- Bolt: modern EFI cruiser with air-cooled V-twin quirks
- Shaft drive models (V-Star 650/1100/1300): final drive service

## Key Concepts
- V-Star 650 is Yamaha's cruiser workhorse — reliable but carb models need regular maintenance
- V-Star 1100 shares engine architecture with the Virago — parts interchangeability
- V-Star 1300 is shaft drive with EFI — most refined but heaviest
- Bolt uses air-cooled 942cc V-twin — runs hot in traffic like any air-cooled cruiser
- Shaft drive requires periodic fluid changes that many cruiser owners skip

## Verification Checklist
- [ ] 10 issues load correctly
- [ ] Year range queries return correct results
- [ ] Critical severity issues present
- [ ] Symptom searches work (loss of power, won't start)
- [ ] Forum tips present in fix procedures
- [ ] All tests pass

## Risks
- Large model range — need clear model identification in each issue title
- V-Star name covers very different bikes (250cc single to 1300cc V-twin)
