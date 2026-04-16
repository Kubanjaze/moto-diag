# MotoDiag Phase 36 — Yamaha YZF-R6 (1999-2020)

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-04-16

## Goal
Second Yamaha phase. YZF-R6 across all generations: Gen 1 carbureted (1999-2002), Gen 2 fuel-injected (2003-2005), Gen 3 underseat exhaust (2006-2007), Gen 4 (2008-2016), and Gen 5 (2017-2020). The R6 is Yamaha's 600cc supersport — the dominant club racer and one of the most common bikes in the shop.

CLI: `python -m pytest tests/test_phase36_yamaha_r6.py -v`

Outputs: `data/knowledge/known_issues_yamaha_r6.json` (10 issues), 6 tests

## Logic
- Create 10 known issues covering R6-specific problems across all generations
- Focus on generation-specific problems: carb sync (Gen 1), CCT (Gen 2), stator (Gen 3-4), valve clearance
- Include forum-sourced fixes with real mechanic knowledge
- Load via existing knowledge loader, test via existing search/symptom/DTC APIs

## Key Concepts
- CCT failure is the #1 R6 problem — the 2003-2005 models are notorious, causes catastrophic valve damage
- Stator/charging failure same pattern as R1 but the R6 runs hotter due to smaller fairings and less airflow
- Valve clearance checking is critical — the R6 has shim-under-bucket valves that tighten with wear
- EXUP valve system shared with R1 — same failure modes
- Throttle sync on Gen 1 carbs requires vacuum gauge balancing
- 2006-2007 underseat exhaust causes extreme heat — melts tail plastics and fries electronics
- 2017+ R6 shares the R1's electronics suite (IMU, TC) in a 600cc package

## Verification Checklist
- [ ] 10 issues load correctly
- [ ] Year range queries return correct results
- [ ] Critical severity issues present
- [ ] Symptom searches work (loss of power, won't start)
- [ ] Forum tips present in fix procedures
- [ ] All tests pass

## Risks
- R6 and R1 share some issues (EXUP, stator) — differentiate with R6-specific year ranges and details
- Gen 1 carbureted models need different diagnostic approach than FI models
