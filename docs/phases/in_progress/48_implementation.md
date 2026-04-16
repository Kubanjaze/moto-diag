# MotoDiag Phase 48 — Kawasaki ZX-9R (1998-2003)

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-04-17

## Goal
Kawasaki's open-class sport bike: ZX-9R (1998-2003). Bridged the gap between the 750cc ZX-7R and the literbike ZX-10R. The ZX-9R spans carbureted (1998-1999) and early fuel-injected (2000-2003) models. It's now a budget open-class sport bike with a loyal following.

CLI: `python -m pytest tests/test_phase48_kawasaki_zx9r.py -v`

Outputs: `data/knowledge/known_issues_kawasaki_zx9r.json` (10 issues), 6 tests

## Logic
- Create 10 known issues covering the ZX-9R
- Carb models (1998-1999): carb sync, fuel system aging
- EFI models (2000-2003): early Kawasaki FI, fuel pump, TPS
- Both: charging, CCT, cooling, brakes, age-related rubber
- Include forum-sourced fixes

## Key Concepts
- ZX-9R was Kawasaki's attempt at a sport-touring literbike — more comfortable than ZX-7R
- 1998-1999 are carbureted; 2000-2003 are early Kawasaki fuel injection
- Early Kawasaki FI is simpler than later systems — basic TPS-based injection
- The ZX-9R is now 20-25 years old — same age-related issues as the ZX-7R

## Verification Checklist
- [ ] 10 issues load correctly
- [ ] Year range queries return correct results
- [ ] Critical severity issues present
- [ ] Symptom searches work
- [ ] Forum tips present
- [ ] All tests pass

## Risks
- Short production run (6 years) — smaller community but well-documented
