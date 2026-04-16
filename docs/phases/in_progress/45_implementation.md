# MotoDiag Phase 45 — Kawasaki Ninja 250/300/400

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-04-17

## Goal
First Kawasaki phase. The Ninja beginner bikes: Ninja 250R (1988-2012), Ninja 300 (2013-2017), and Ninja 400 (2018+). The best-selling beginner sport bikes in North America. Covers carbureted (250R pre-2008), EFI (250R 2008+, 300, 400), parallel twin engines, and the issues that come from being first bikes — drops, neglect, and new-rider mistakes.

CLI: `python -m pytest tests/test_phase45_kawasaki_ninja_small.py -v`

Outputs: `data/knowledge/known_issues_kawasaki_ninja_small.json` (10 issues), 6 tests

## Logic
- Create 10 known issues spanning the Ninja 250/300/400 range
- Carbureted 250R: carb sync, petcock, choke issues
- EFI models: fuel pump, FI codes, sensor issues
- All models: beginner drop damage, chain neglect, valve clearance
- Include forum-sourced fixes with real mechanic knowledge

## Key Concepts
- Ninja 250R is the most popular beginner bike ever — massive aftermarket and forum knowledge
- Ninja 300 introduced slipper clutch and ABS option to the beginner class
- Ninja 400 is the current champion — lightest, most powerful, best electronics in class
- Parallel twin engines are reliable but need valve checks at 15K miles
- First-bike damage patterns: parking lot drops, chain neglect, oil change ignorance

## Verification Checklist
- [ ] 10 issues load correctly
- [ ] Year range queries return correct results
- [ ] Critical severity issues present
- [ ] Symptom searches work (loss of power, won't start)
- [ ] Forum tips present in fix procedures
- [ ] All tests pass

## Risks
- Three generations spanning 35+ years — clear model differentiation needed
- Beginner owner audience — fix procedures should be accessible
