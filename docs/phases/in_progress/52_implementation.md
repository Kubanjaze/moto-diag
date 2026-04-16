# MotoDiag Phase 52 — Kawasaki Z Naked Series

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-04-17

## Goal
Kawasaki's naked/standard lineup: Z400 (2019+), Z650 (2017+), Z750/Z750S (2004-2012), Z800 (2013-2016), Z900 (2017+), Z1000 (2003-2019), and Z H2 (2020+, supercharged). These share engines with the Ninja line but in naked chassis with different cooling, ergonomic, and electronic considerations.

CLI: `python -m pytest tests/test_phase52_kawasaki_z_naked.py -v`

Outputs: `data/knowledge/known_issues_kawasaki_z_naked.json` (10 issues), 6 tests

## Key Concepts
- Z models share engines with corresponding Ninja: Z400=Ninja 400, Z650=Ninja 650, Z900=Ninja series
- Naked chassis exposes components to weather — sensor/connector corrosion more common
- Z H2 uses the supercharged engine from the H2 in a naked streetfighter chassis
- Exposed radiators on all Z models need guards
- Z1000 was the flagship naked for 16 years — large community

## Verification Checklist
- [ ] 10 issues load correctly
- [ ] Year range queries return correct results
- [ ] Critical severity issues present
- [ ] Symptom searches work
- [ ] Forum tips present
- [ ] All tests pass

## Risks
- Large model range — must differentiate clearly per model
