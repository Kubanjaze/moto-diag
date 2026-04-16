# MotoDiag Phase 51 — Kawasaki Ninja H2 / H2R (2015+)

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-04-17

## Goal
Kawasaki's supercharged hyperbike: Ninja H2 (street), H2 SX (sport-tourer), and H2R (track-only). The only supercharged production motorcycle. Unique diagnostic needs centered on the supercharger system, extreme heat management, and sophisticated electronics. The H2R produces 310hp — the most powerful production motorcycle ever made.

CLI: `python -m pytest tests/test_phase51_kawasaki_h2.py -v`

Outputs: `data/knowledge/known_issues_kawasaki_h2.json` (10 issues), 6 tests

## Key Concepts
- Centrifugal supercharger is unique to the H2 — no other production motorcycle has one
- Supercharger requires no maintenance but intercooler and boost control are diagnostic items
- H2 runs extremely hot — cooling system is critical
- H2R is track-only with no mirrors, lights, or street equipment
- H2 SX is the sport-touring variant with panniers and relaxed ergonomics
- Dog-ring gearbox (H2R) differs from standard transmission

## Verification Checklist
- [ ] 10 issues load correctly
- [ ] Year range queries return correct results
- [ ] Critical severity issues present
- [ ] Symptom searches work
- [ ] Forum tips present
- [ ] All tests pass

## Risks
- Supercharger diagnostics are unique — no other motorcycle reference exists
- H2R is rare — limited owner community but well-documented by Kawasaki
