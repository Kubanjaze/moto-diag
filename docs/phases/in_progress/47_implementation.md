# MotoDiag Phase 47 — Kawasaki ZX-7R / ZX-7RR (1996-2003)

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-04-17

## Goal
Kawasaki's carb-era 750cc supersport: ZX-7R (street) and ZX-7RR (homologation special with flat-slide carbs and close-ratio gearbox). These bikes are now 20-30 years old and represent the last generation of carbureted Kawasaki superbikes. The ZX-7RR is a collector's item; the ZX-7R is an affordable classic supersport.

CLI: `python -m pytest tests/test_phase47_kawasaki_zx7r.py -v`

Outputs: `data/knowledge/known_issues_kawasaki_zx7r.json` (10 issues), 6 tests

## Logic
- Create 10 known issues covering both ZX-7R and ZX-7RR
- Carbureted inline-4 issues: carb sync, jetting, choke, fuel system aging
- Age-related: charging, wiring, rubber degradation, corrosion
- ZX-7RR specific: flat-slide carb maintenance, close-ratio gearbox
- Include forum-sourced fixes with real mechanic knowledge

## Key Concepts
- ZX-7R uses CV (constant velocity) carbs; ZX-7RR uses flat-slide FCR carbs
- Both are 749cc inline-4 with 4 individual carburetors
- No fuel injection, no electronic diagnostics — all mechanical troubleshooting
- ZX-7RR is a homologation special — limited production, valuable, parts scarce
- These bikes are now in the "classic" category — age-related failures dominate

## Verification Checklist
- [ ] 10 issues load correctly
- [ ] Year range queries return correct results
- [ ] Critical severity issues present
- [ ] Symptom searches work
- [ ] Forum tips present
- [ ] All tests pass

## Risks
- ZX-7RR parts scarcity — must note when OEM parts are unavailable
- 20-30 year old bikes — age-related failures differ from modern bike issues
