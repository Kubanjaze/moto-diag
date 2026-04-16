# MotoDiag Phase 19 — Harley V-Rod / VRSC (2002-2017)

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-04-16

## Goal
Build the known-issues knowledge base for the Harley-Davidson V-Rod / VRSC platform (2002-2017). The Revolution engine is liquid-cooled, DOHC, 60-degree V-twin — co-developed with Porsche and fundamentally different from every other Harley engine. This phase captures the unique failure modes that air-cooled Harley experience doesn't prepare mechanics for.

CLI: `python -m pytest tests/test_phase19_harley_vrsc.py -v`

Outputs: `data/knowledge/known_issues_harley_vrsc.json` (10 issues), 6 tests

## Logic
- Create 10 known issues specific to the VRSC/V-Rod platform
- Each issue follows the established schema: title, description, make, model, year_start, year_end, severity, symptoms, dtc_codes, causes, fix_procedure (with forum tips), parts_needed, estimated_hours
- Load via existing `load_known_issues_file()` infrastructure
- Test data integrity, searchability, and forum-tip inclusion

Data flow: JSON file -> load_known_issues_file() -> SQLite known_issues table -> query via issues_repo

## Key Concepts
- Revolution engine: liquid-cooled 1130cc/1250cc DOHC 60-degree V-twin
- Unique to VRSC: radiator/coolant system, hydraulic clutch, perimeter frame, underseat fuel cell, alternator (not stator)
- VRSC models: VRSCA, VRSCB, VRSCD, VRSCX, VRSCDX, VRSCF (Night Rod, Night Rod Special, V-Rod Muscle)
- ECU system distinct from air-cooled Harleys — different DTCs, different tuning approach
- Forum sources: V-Rod Forum (1130cc.com), HDForums VRSC section

## Verification Checklist
- [ ] 10 issues load into database
- [ ] Year range queries return correct results for 2010 V-Rod
- [ ] DTC search finds coolant/charging issues
- [ ] Critical severity issues present
- [ ] Forum tips present in fix procedures
- [ ] All 6 tests pass

## Risks
- Revolution engine issues are less widely documented than air-cooled Harleys — smaller production volume
- Some VRSC-specific DTCs may not be well-documented in public sources
- Hydraulic clutch and coolant system are unique failure domains not seen in prior phases
