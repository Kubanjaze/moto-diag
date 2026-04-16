# MotoDiag Phase 31 — Honda Dual-Sport: XR650L, CRF250L/300L, Africa Twin

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-16

## Goal
Build the known-issues knowledge base for Honda's dual-sport and adventure lineup. Air-cooled thumpers to modern liquid-cooled adventure bikes with DCT options.

CLI: `python -m pytest tests/test_phase31_honda_dualsport.py -v`

Outputs: `data/knowledge/known_issues_honda_dualsport.json` (10 issues), 6 tests

## Key Concepts
- XR650L factory jetting is intentionally lean for EPA — uncorking is mandatory, not optional
- XR650L oil consumption is by design — check every ride, carry spare oil
- CRF250L/300L is genuinely underpowered for highway — it's a commuter/trail bike, not a sport tourer
- Africa Twin DCT off-road limitations: can't slip clutch, struggles in technical terrain
- Off-road riding creates unique failure modes: radiator puncture, electrical water damage, accelerated chain wear
- Crash protection is not optional for off-road adventure bikes — budget it into purchase price

## Verification Checklist
- [x] 10 issues load
- [x] Year range correct for 2020 (5+ issues)
- [x] High severity present (3: XR650L jetting, radiator damage, water damage)
- [x] Overheating and loss of power find relevant issues
- [x] Forum tips in all procedures
- [x] All 6 tests pass (0.93s)

## Results
| Metric | Value |
|--------|-------|
| Known issues | 10 (XR650L jetting, XR650L oil/valves, CRF power limits, AT DCT off-road, AT radiator, water damage, chain off-road, CRF clutch basket, AT crash protection, XR650L charging) |
| Tests | 6/6, 0.93s |
| Severity breakdown | 0 critical, 3 high, 5 medium, 2 low |
| Year coverage | 1993-2025 |

Dual-sport diagnostics are fundamentally different from street — environmental damage (water, mud, rocks) creates failure modes that don't exist on pavement.
