# MotoDiag Phase 21 — Harley Electrical Systems (All Eras)

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-04-16

## Goal
Build a cross-era electrical systems knowledge base covering charging, starting, ignition, and wiring harness issues across all Harley-Davidson generations. This phase captures the electrical problems that transcend specific engine platforms — every Harley era has its own electrical architecture but many failure patterns recur.

CLI: `python -m pytest tests/test_phase21_harley_electrical.py -v`

Outputs: `data/knowledge/known_issues_harley_electrical.json` (10 issues), 6 tests

## Logic
- Create 10 known issues spanning Harley electrical systems from Shovelhead through Milwaukee-Eight
- Cover charging system evolution: generator → stator → alternator
- Cover starting system: solenoid, starter motor, starter clutch
- Cover ignition: points → electronic → CAN bus
- Cover wiring: bullet connectors, Deutsch connectors, CAN bus

Data flow: JSON file -> load_known_issues_file() -> SQLite known_issues table -> query via issues_repo

## Key Concepts
- Charging evolution: Shovelhead generator → Evo stator/rotor → TC96+ stator upgrade → M8 higher-output stator → Rev Max alternator
- Regulator/rectifier: most common Harley electrical failure across all eras
- CAN bus (2011+): multiplexed wiring, BCM, TSSM, ECM communication
- Wiring harness degradation: heat, vibration, oil exposure
- Battery types: conventional → AGM → lithium (each has different charging needs)

## Verification Checklist
- [ ] 10 issues load into database
- [ ] Year range queries span multiple eras
- [ ] DTC search finds charging-related codes
- [ ] Critical severity issues present
- [ ] Forum tips present in fix procedures
- [ ] All 6 tests pass

## Risks
- Cross-era phase covers a very wide year range — need to be specific about which eras each issue applies to
- Some issues overlap with era-specific phases (13-20) — focus on the electrical-specific angle
