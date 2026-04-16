# MotoDiag Phase 46 — Kawasaki ZX-6R (1995+)

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-04-17

## Goal
Kawasaki's 600cc supersport: ZX-6R across all generations including the unique 636cc displacement. The ZX-6R is Kawasaki's answer to the R6 and CBR600RR, with the distinctive choice to run 636cc instead of 599cc for more midrange torque. Covers carbureted (1995-2002), early EFI (2003-2006), and modern EFI with electronics (2007+).

CLI: `python -m pytest tests/test_phase46_kawasaki_zx6r.py -v`

Outputs: `data/knowledge/known_issues_kawasaki_zx6r.json` (10 issues), 6 tests

## Logic
- Create 10 known issues covering ZX-6R across all generations
- 636cc displacement issues, KLEEN exhaust system, FI dealer mode
- Stator/charging, CCT, valve clearance, cooling
- Include forum-sourced fixes with real mechanic knowledge

## Key Concepts
- ZX-6R alternated between 599cc and 636cc depending on year — affects racing class eligibility
- KLEEN (Kawasaki Low Emission Engine) system is the AIS equivalent — causes decel popping
- Kawasaki FI dealer mode uses jumper wire on diagnostic connector
- The 2009+ ZX-6R has KTRC (traction control) and KIBS (cornering ABS on later models)

## Verification Checklist
- [ ] 10 issues load correctly
- [ ] Year range queries return correct results
- [ ] Critical severity issues present
- [ ] Symptom searches work
- [ ] Forum tips present
- [ ] All tests pass

## Risks
- 636cc vs 599cc displacement changes confuse owners — must clarify which years are which
