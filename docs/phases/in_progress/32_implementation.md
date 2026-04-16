# MotoDiag Phase 32 — Honda Vintage Air-Cooled: CB550/650/750, Nighthawk

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-04-16

## Goal
Build the known-issues knowledge base for Honda's vintage air-cooled lineup: CB550 (1974-1978), CB650 (1979-1982), CB750 (1969-1982), and Nighthawk 250/650/750 (1982-2003). These are the bikes that built Honda's reputation — now 25-50+ years old with age-specific failure modes overlaid on classic Honda engineering.

CLI: `python -m pytest tests/test_phase32_honda_vintage.py -v`

Outputs: `data/knowledge/known_issues_honda_vintage.json` (10 issues), 6 tests

## Verification Checklist
- [ ] 10 issues load, 6 tests pass
