# MotoDiag Phase 24 — Honda CBR600: F2/F3/F4/F4i (1991-2006)

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-04-16

## Goal
Build the known-issues knowledge base for the Honda CBR600 F-series: F2 (1991-1994), F3 (1995-1998), F4 (1999-2000), and F4i (2001-2006). These bikes span the carb-to-EFI transition and are among the most common sport bikes ever sold. Many are now daily riders, commuters, and first bikes — so reliability issues are high-impact.

CLI: `python -m pytest tests/test_phase24_honda_cbr600f.py -v`

Outputs: `data/knowledge/known_issues_honda_cbr600f.json` (10 issues), 6 tests

## Logic
- Create 10 known issues spanning F2 through F4i generations
- Cover carb-era issues (F2/F3), EFI transition (F4/F4i), and age-related failures common to all
- Regulator/rectifier and CCT recur from Phase 23 but with CBR600-specific details

Data flow: JSON file -> load_known_issues_file() -> SQLite known_issues table -> query via issues_repo

## Key Concepts
- F2/F3: carbureted, conventional forks, no immobilizer
- F4: carbureted, updated chassis, HISS on some markets
- F4i: fuel-injected (PGM-FI), HISS immobilizer standard
- All share Honda inline-4 platform failures: reg/rec, CCT, starter clutch

## Verification Checklist
- [ ] 10 issues load into database
- [ ] Year range queries return correct results
- [ ] Symptom and severity searches work
- [ ] Forum tips present
- [ ] All 6 tests pass

## Risks
- Four sub-generations with different details — need to be specific about which years
