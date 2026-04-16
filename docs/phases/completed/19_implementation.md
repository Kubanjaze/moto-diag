# MotoDiag Phase 19 — Harley V-Rod / VRSC (2002-2017)

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-16

## Goal
Build the known-issues knowledge base for the Harley-Davidson V-Rod / VRSC platform (2002-2017). The Revolution engine is liquid-cooled, DOHC, 60-degree V-twin — co-developed with Porsche and fundamentally different from every other Harley engine. This phase captures the unique failure modes that air-cooled Harley experience doesn't prepare mechanics for.

CLI: `python -m pytest tests/test_phase19_harley_vrsc.py -v`

Outputs: `data/knowledge/known_issues_harley_vrsc.json` (10 issues), 6 tests

## Logic
- Created 10 known issues specific to the VRSC/V-Rod platform
- Each issue follows the established schema: title, description, make, model, year_start, year_end, severity, symptoms, dtc_codes, causes, fix_procedure (with forum tips), parts_needed, estimated_hours
- Loaded via existing `load_known_issues_file()` infrastructure
- Tested data integrity, searchability, and forum-tip inclusion

Data flow: JSON file -> load_known_issues_file() -> SQLite known_issues table -> query via issues_repo

## Key Concepts
- Revolution engine: liquid-cooled 1130cc/1250cc DOHC 60-degree V-twin (co-developed with Porsche)
- Unique to VRSC: radiator/coolant system, hydraulic clutch, perimeter frame, underseat fuel cell, internal alternator (not external stator)
- VRSC models: VRSCA, VRSCB, VRSCD, VRSCX, VRSCDX, VRSCF (Night Rod, Night Rod Special, V-Rod Muscle)
- ECU completely different from air-cooled platform — runs rich (opposite of air-cooled lean issue), cannot use FP3/Screamin Eagle tuners, needs Power Commander V or TTS MasterTune
- Fuel cell delamination (2002-2007) is platform-specific — plastic liner sends flakes into fuel system
- Alternator rotor nut backing off is an early V-Rod known defect (2002-2008)
- Forum sources: 1130cc.com (V-Rod Forum), HDForums VRSC section

## Verification Checklist
- [x] 10 issues load into database
- [x] Year range queries return correct results for 2010 V-Rod
- [x] DTC search finds coolant issue (P0480)
- [x] Critical severity issues present (3: coolant, alternator rotor nut, frame cracks)
- [x] Forum tips present in fix procedures
- [x] All 6 tests pass (1.09s)

## Risks
- Revolution engine issues are less widely documented than air-cooled Harleys — smaller production volume. Mitigated by focusing on the most common and well-documented failures from 1130cc.com forums.
- Some VRSC-specific DTCs (P0480 fan relay, P0128 thermostat) are shared with automotive — verified they apply to V-Rod coolant system.

## Results
| Metric | Value |
|--------|-------|
| Known issues | 10 (coolant system, hydraulic clutch, fuel cell delamination, exhaust header cracking, alternator rotor nut, perimeter frame cracks, ECU rich mapping, belt tensioner, starter/sprag clutch, rear shock linkage) |
| Tests | 6/6, 1.09s |
| Severity breakdown | 3 critical, 4 high, 3 medium |
| DTC codes covered | P0480, P0128, P0230, P0131, P0562, P0151 |
| Year coverage | 2002-2017 (full VRSC production run) |

The V-Rod is the most mechanically distinct Harley platform — liquid cooling, hydraulic clutch, internal alternator, and underseat fuel cell create failure modes that don't exist on any air-cooled Harley. Mechanics trained only on air-cooled bikes will miss the coolant system and hydraulic clutch issues entirely.
