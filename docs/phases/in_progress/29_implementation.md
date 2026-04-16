# MotoDiag Phase 29 — Honda Standards: CB750/919, CB1000R, Hornet

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-04-16

## Goal
Build the known-issues knowledge base for Honda's standard/naked lineup: CB750 (1991-2003), CB900F/919 (2002-2007), CB1000R (2008+), and Hornet 600/900 (various years). These bikes share engines with the CBR sport bikes but in detuned, upright-riding configurations — they inherit the sport bike weaknesses plus unique issues from their chassis and ergonomics.

CLI: `python -m pytest tests/test_phase29_honda_standards.py -v`

Outputs: `data/knowledge/known_issues_honda_standards.json` (10 issues), 6 tests

## Verification Checklist
- [ ] 10 issues load, 6 tests pass
