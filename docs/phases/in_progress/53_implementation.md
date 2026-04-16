# MotoDiag Phase 53 — Kawasaki Vulcan Cruisers

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-04-17

## Goal
Kawasaki's cruiser lineup: Vulcan 500 (1990-2009), Vulcan 750 (1986-2006), Vulcan 800/Classic (1995-2006), Vulcan 900 (2006+), Vulcan 1500/1600 (1987-2008), Vulcan 1700 (2009-2020), and Vulcan 2000 (2004-2010). Spans carbureted V-twins, EFI V-twins, inline-twins, shaft drive and belt drive.

CLI: `python -m pytest tests/test_phase53_kawasaki_vulcan.py -v`

Outputs: `data/knowledge/known_issues_kawasaki_vulcan.json` (10 issues), 6 tests

## Verification Checklist
- [ ] 10 issues load correctly
- [ ] Year range queries return correct results
- [ ] Critical severity issues present
- [ ] Symptom searches work
- [ ] Forum tips present
- [ ] All tests pass

## Risks
- Huge model range — clear model identification in each issue title
