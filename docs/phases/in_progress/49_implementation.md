# MotoDiag Phase 49 — Kawasaki ZX-10R (2004+)

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-04-17

## Goal
Kawasaki's flagship superbike: ZX-10R across all generations from the raw 2004 debut to the current electronics-laden model. The ZX-10R replaced the ZX-9R as Kawasaki's literbike and has been the most aggressive, least compromised superbike in the class. Covers Gen 1 (2004-2005), Gen 2 (2006-2007), Gen 3 (2008-2010), Gen 4 (2011-2015), Gen 5 (2016-2020), and Gen 6 (2021+).

CLI: `python -m pytest tests/test_phase49_kawasaki_zx10r.py -v`

Outputs: `data/knowledge/known_issues_kawasaki_zx10r.json` (10 issues), 6 tests

## Key Concepts
- 2004-2005 ZX-10R was dangerously fast — known for tank-slapper headshakes
- KTRC (Kawasaki Traction Control) introduced 2011, IMU-based cornering management 2016+
- KIBS (Kawasaki Intelligent Braking System) = cornering ABS
- KECS (Kawasaki Electronic Control Suspension) on SE models
- The ZX-10R is a track weapon — many issues are track-use related

## Verification Checklist
- [ ] 10 issues load correctly
- [ ] Year range queries return correct results
- [ ] Critical severity issues present
- [ ] Symptom searches work
- [ ] Forum tips present
- [ ] All tests pass

## Risks
- 6 generations means wide variation in electronics complexity
