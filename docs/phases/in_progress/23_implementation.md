# MotoDiag Phase 23 — Honda CBR Supersport: 900RR/929RR/954RR (1992-2003)

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-04-16

## Goal
Build the known-issues knowledge base for the Honda FireBlade family: CBR900RR (1992-1999), CBR929RR (2000-2001), and CBR954RR (2002-2003). The original supersport that redefined the class — lightweight, powerful, and aggressively engineered. These bikes are now 20-30 years old and have age-specific failure modes on top of their original design compromises.

CLI: `python -m pytest tests/test_phase23_honda_cbr_supersport.py -v`

Outputs: `data/knowledge/known_issues_honda_cbr_supersport.json` (10 issues), 6 tests

## Logic
- Create 10 known issues for the CBR900RR/929RR/954RR platform family
- Cover both design-era issues and aging-related failures
- Include HISS immobilizer (929/954), PGM-FI (929/954 vs carbs on early 900RR)

Data flow: JSON file -> load_known_issues_file() -> SQLite known_issues table -> query via issues_repo

## Key Concepts
- CBR900RR (1992-1999): carbureted, no immobilizer, 893cc then 919cc
- CBR929RR (2000-2001): EFI (PGM-FI), HISS immobilizer, 929cc
- CBR954RR (2002-2003): EFI, HISS, 954cc, improved electronics
- Regulator/rectifier failures plague all Honda sport bikes of this era
- Cam chain tensioner (CCT) is a known Honda weak point

## Verification Checklist
- [ ] 10 issues load into database
- [ ] Year range queries return correct results for 2001
- [ ] DTC/symptom search works
- [ ] Forum tips present in fix procedures
- [ ] All 6 tests pass

## Risks
- Three distinct submodels (900/929/954) — need to specify which years each issue applies to
