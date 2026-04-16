# MotoDiag Phase 22 — Harley Common Cross-Era Issues

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-04-16

## Goal
Build a cross-era mechanical issues knowledge base covering the problems that plague multiple Harley generations: compensator, intake leaks, heat soak, oil leaks, clutch, suspension, brakes, and tire/wheel issues. Phase 21 covered electrical; this phase covers the mechanical side that every Harley mechanic sees weekly regardless of which era bike rolls in.

CLI: `python -m pytest tests/test_phase22_harley_cross_era.py -v`

Outputs: `data/knowledge/known_issues_harley_cross_era.json` (10 issues), 6 tests

## Logic
- Create 10 known mechanical issues that span multiple Harley generations
- Focus on the "every Harley does this eventually" problems
- Complements era-specific phases (13-20) and electrical phase (21)

Data flow: JSON file -> load_known_issues_file() -> SQLite known_issues table -> query via issues_repo

## Key Concepts
- Compensator: sprocket assembly that absorbs drivetrain shock — wears on all Twin Cam and M8 models
- Intake manifold leaks: affects every V-twin with a shared intake manifold
- Heat soak: air-cooled V-twins run hot in traffic — universal problem
- Primary chain/belt tensioner: wears on all models
- Oil leaks: "if it's not leaking, it's empty" — common leak points by era

## Verification Checklist
- [ ] 10 issues load into database
- [ ] Year range queries return cross-era results
- [ ] Symptom search finds intake leak and heat soak
- [ ] Forum tips present in fix procedures
- [ ] All 6 tests pass

## Risks
- Some overlap with era-specific phases — focus on cross-era diagnostic pattern rather than era-specific fix details
