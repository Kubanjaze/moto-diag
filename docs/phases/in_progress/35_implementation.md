# MotoDiag Phase 35 — Yamaha YZF-R1 (1998+)

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-04-16

## Goal
Build the known-issues knowledge base for the Yamaha YZF-R1 across all generations: Gen 1 (1998-2001), Gen 2 (2002-2003), Gen 3 (2004-2006), Gen 4 (2007-2008), crossplane crank (2009-2014), and the R1M/R1S (2015+) with IMU, YCC-T, YCC-I. The R1 evolved from a raw sport bike to a MotoGP-derived electronics platform.

CLI: `python -m pytest tests/test_phase35_yamaha_r1.py -v`

Outputs: `data/knowledge/known_issues_yamaha_r1.json` (10 issues), 6 tests

## Verification Checklist
- [ ] 10 issues load, 6 tests pass
