# MotoDiag Phase 38 — Yamaha FZ/MT Naked Series

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-04-17

## Goal
Yamaha's naked/standard lineup: FZ6/FZ6R (2004-2017), FZ8 (2011-2013), FZ-09/MT-09 (2014+), FZ-10/MT-10 (2016+), MT-03 (2020+), MT-07/FZ-07 (2015+). These are Yamaha's highest-volume models — the MT-07 is the best-selling motorcycle in Europe. Covers CP2, CP3, and crossplane-4 engine platforms in naked configuration.

CLI: `python -m pytest tests/test_phase38_yamaha_fz_mt.py -v`

Outputs: `data/knowledge/known_issues_yamaha_fz_mt.json` (10 issues), 6 tests

## Logic
- Create 10 known issues spanning the FZ/MT lineup
- Focus on platform-specific issues: CP3 fueling (MT-09), CP2 characteristics (MT-07), crossplane-4 (MT-10)
- FZ6/FZ6R share R6 engine — some crossover issues but different ergonomic/cooling concerns
- Include forum-sourced fixes with real mechanic knowledge

## Key Concepts
- MT-09/FZ-09 is notorious for snatchy throttle — ride-by-wire calibration is too aggressive
- MT-07 CP2 twin is the most reliable Yamaha engine in current production
- MT-10 shares R1 crossplane engine — same electronics complexity in a naked package
- FZ6 detuned R6 engine overheats in traffic (same heat issues, less fairing airflow management)
- Name change: FZ→MT happened in 2018 for US market (always MT in Europe)

## Verification Checklist
- [ ] 10 issues load correctly
- [ ] Year range queries return correct results
- [ ] Critical severity issues present
- [ ] Symptom searches work (loss of power, won't start)
- [ ] Forum tips present in fix procedures
- [ ] All tests pass

## Risks
- Large model range in one phase — must differentiate clearly per model in issue titles
- FZ-09→MT-09 naming overlap — use both names in descriptions for searchability
