# MotoDiag Phase 30 — Honda V4: VFR800, RC51/RVT1000R, VFR1200F

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-04-16

## Goal
Build the known-issues knowledge base for Honda's V4 motorcycle lineup: VFR800 Interceptor (1998-2017, with VTEC 2002+), RC51/RVT1000R (2000-2006), and VFR1200F (2010-2017). The V4 configuration is unique among Japanese sport-touring and superbike platforms — gear-driven cams, VTEC, complex fuel injection, and shaft drive (VFR1200F DCT).

CLI: `python -m pytest tests/test_phase30_honda_v4.py -v`

Outputs: `data/knowledge/known_issues_honda_v4.json` (10 issues), 6 tests

## Verification Checklist
- [ ] 10 issues load, 6 tests pass
