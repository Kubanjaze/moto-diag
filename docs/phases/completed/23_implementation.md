# MotoDiag Phase 23 — Honda CBR Supersport: 900RR/929RR/954RR (1992-2003)

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-16

## Goal
Build the known-issues knowledge base for the Honda FireBlade family: CBR900RR (1992-1999), CBR929RR (2000-2001), and CBR954RR (2002-2003). First Honda phase — begins Japanese motorcycle coverage.

CLI: `python -m pytest tests/test_phase23_honda_cbr_supersport.py -v`

Outputs: `data/knowledge/known_issues_honda_cbr_supersport.json` (10 issues), 6 tests

## Logic
- Created 10 known issues covering the CBR900RR/929RR/954RR platform family
- Covers design-era issues and 20+ year aging failures
- Includes HISS immobilizer (929/954), PGM-FI (929/954), and carb-era (early 900RR) specifics

Data flow: JSON file -> load_known_issues_file() -> SQLite known_issues table -> query via issues_repo

## Key Concepts
- Regulator/rectifier is the #1 Honda sport bike failure — MOSFET upgrade mandatory
- CCT (cam chain tensioner) automatic unit is a known weak point — manual tensioner conversion recommended
- HISS immobilizer on 929/954 requires dealer tool for key programming — no DIY
- PGM-FI blink codes are self-diagnostic — no dealer tool needed for reading
- Linkage bearings: "maintenance-free" = never serviced = guaranteed worn on 20+ year old bikes

## Verification Checklist
- [x] 10 issues load into database
- [x] Year range queries return correct results for 2001 (5+ issues)
- [x] Critical severity present (2: regulator, CCT)
- [x] Won't start symptom finds HISS and starter clutch issues
- [x] Forum tips present in all fix procedures
- [x] All 6 tests pass (1.12s)

## Results
| Metric | Value |
|--------|-------|
| Known issues | 10 (reg/rec, CCT, HISS immobilizer, carb sync, fork seals, starter clutch, coolant leak, PGM-FI, rear linkage, fairing bolts) |
| Tests | 6/6, 1.12s |
| Severity breakdown | 2 critical, 4 high, 3 medium, 1 low |
| Year coverage | 1992-2003 (CBR900RR/929RR/954RR) |

First Honda phase complete. The CBR FireBlade family shares many issues with other Honda inline-4 sport bikes — reg/rec failure, CCT, starter clutch — which will recur across phases 24-26.
