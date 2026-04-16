# MotoDiag Phase 37 — Yamaha YZF-R7 + YZF600R Thundercat

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-04-16

## Goal
Budget sport platforms: YZF600R Thundercat (1996-2007) — Yamaha's sport-touring 600 with a detuned engine and comfortable ergonomics; and YZF-R7 (2021+) — the modern CP2 twin-cylinder sport bike built on the MT-07 platform. Two very different bikes that share the "budget sport" positioning in Yamaha's lineup.

CLI: `python -m pytest tests/test_phase37_yamaha_r7_thundercat.py -v`

Outputs: `data/knowledge/known_issues_yamaha_r7_thundercat.json` (10 issues), 6 tests

## Logic
- Create 10 known issues: ~5 for the YZF600R Thundercat (carbureted sport-touring), ~5 for the YZF-R7 (modern CP2 twin)
- Thundercat issues focus on carb-era problems: carb sync, petcock, chain, charging
- R7 issues focus on CP2 platform: clutch chatter, suspension limitations, quick shifter calibration
- Include forum-sourced fixes with real mechanic knowledge

## Key Concepts
- YZF600R Thundercat is carbureted — no FI diagnostics, but 4-carb sync is critical
- The Thundercat shares many components with the FZR600 — parts interchangeability
- 2021+ R7 uses the CP2 twin from the MT-07 — reliable engine but budget suspension/brakes
- R7 is positioned as a track-day learner bike — common first-time track issues
- CP2 engine has minimal electronics — no IMU, basic TC only

## Verification Checklist
- [ ] 10 issues load correctly
- [ ] Year range queries return correct results
- [ ] Critical severity issues present
- [ ] Symptom searches work (loss of power, won't start)
- [ ] Forum tips present in fix procedures
- [ ] All tests pass

## Risks
- Two different bikes in one phase — need clear differentiation in title/description
- Thundercat is less common — fewer forum sources, but well-documented issues
