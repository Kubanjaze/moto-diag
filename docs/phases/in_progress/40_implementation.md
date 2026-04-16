# MotoDiag Phase 40 — Yamaha VMAX (1985-2020)

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-04-17

## Goal
The Yamaha VMAX — a muscle bike icon spanning two generations: Gen 1 (1985-2007) carbureted V4 with the legendary V-Boost system, and Gen 2 (2009-2020) fuel-injected V4 with modern electronics. The VMAX is unique in the Yamaha lineup — a straight-line performance machine with distinct diagnostic needs.

CLI: `python -m pytest tests/test_phase40_yamaha_vmax.py -v`

Outputs: `data/knowledge/known_issues_yamaha_vmax.json` (10 issues), 6 tests

## Logic
- Create 10 known issues: ~5 for Gen 1 (carbureted, V-Boost), ~5 for Gen 2 (EFI, modern)
- Gen 1 issues focus on V-Boost system, carb maintenance, charging, shaft drive
- Gen 2 issues focus on electronics, fuel system, cooling, weight-related wear
- Include forum-sourced fixes with real mechanic knowledge

## Key Concepts
- V-Boost is the VMAX's signature feature — 4 carbs linked in pairs, opening at high RPM for massive power
- Gen 1 VMAX is carbureted with 4 individual Mikuni carbs — sync is critical
- Gen 2 VMAX is 1679cc — largest displacement production motorcycle V4
- Both generations use shaft final drive
- Gen 1 has known electrical/charging issues
- Gen 2 weighs 683 lbs wet — tire and brake wear are accelerated

## Verification Checklist
- [ ] 10 issues load correctly
- [ ] Year range queries return correct results
- [ ] Critical severity issues present
- [ ] Symptom searches work (loss of power, won't start)
- [ ] Forum tips present in fix procedures
- [ ] All tests pass

## Risks
- V-Boost system is unique to VMAX — requires accurate technical description
- Gen 2 is less common — fewer forum sources but well-documented issues
