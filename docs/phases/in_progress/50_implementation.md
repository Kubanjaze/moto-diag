# MotoDiag Phase 50 — Kawasaki ZX-12R / ZX-14R (2000-2020)

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-04-17

## Goal
Kawasaki's hyperbikes: ZX-12R (2000-2005) and ZX-14R (2006-2020). These are the fastest production Kawasaki motorcycles — built for straight-line speed with ram-air assisted power. The ZX-12R was Kawasaki's answer to the Hayabusa; the ZX-14R refined the formula with fuel injection, ABS, and KTRC.

CLI: `python -m pytest tests/test_phase50_kawasaki_hyperbike.py -v`

Outputs: `data/knowledge/known_issues_kawasaki_hyperbike.json` (10 issues), 6 tests

## Key Concepts
- ZX-12R: 1199cc inline-4 with ram air, 178hp — the fastest Kawasaki until the H2
- ZX-14R: 1441cc inline-4, 210hp with ram air — sport-touring hyperbike
- Ram air system is unique to these models — pressurized airbox above ~100mph
- Both are heavy (500+ lbs) — tire and brake wear patterns differ from lighter sport bikes
- ZX-14R was often used for sport-touring — high-mileage maintenance patterns

## Verification Checklist
- [ ] 10 issues load correctly
- [ ] Year range queries return correct results
- [ ] Critical severity issues present
- [ ] Symptom searches work
- [ ] Forum tips present
- [ ] All tests pass

## Risks
- Two different bikes spanning 20 years — clear model differentiation needed
