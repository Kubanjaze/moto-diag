# MotoDiag Phase 21 — Harley Electrical Systems (All Eras)

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-16

## Goal
Build a cross-era electrical systems knowledge base covering charging, starting, ignition, and wiring harness issues across all Harley-Davidson generations. This phase captures the electrical problems that transcend specific engine platforms — every Harley era has its own electrical architecture but many failure patterns recur.

CLI: `python -m pytest tests/test_phase21_harley_electrical.py -v`

Outputs: `data/knowledge/known_issues_harley_electrical.json` (10 issues), 6 tests

## Logic
- Created 10 known issues spanning Harley electrical systems from 1970 through 2025
- Covers charging system (regulator/rectifier, stator), starting system (solenoid), ignition (switch, TSSM), CAN bus, grounds, wiring harness, battery types, and accessory overload
- Cross-era issues use wide year ranges with era-specific details in the descriptions

Data flow: JSON file -> load_known_issues_file() -> SQLite known_issues table -> query via issues_repo

## Key Concepts
- Regulator/rectifier is the #1 Harley electrical failure — MOSFET upgrade recommended for all eras
- Stator failure is #2 — always replace regulator with stator (bad reg kills stator)
- Ground cable corrosion causes more unexplained electrical gremlins than any other single cause
- CAN bus (2011+): single corroded connector can take down entire electrical system — U-codes identify which module
- TSSM (Turn Signal Security Module): controls security + signals, requires dealer tool to reprogram
- Battery type matching is critical: AGM vs lithium have different charging needs and cold-weather behavior
- Accessory electrical load must not exceed 80% of stator output at idle

## Verification Checklist
- [x] 10 issues load into database
- [x] Year range queries span multiple eras (2000 returns 5+ issues)
- [x] DTC search finds charging codes (P0562)
- [x] Critical severity issues present (3: regulator, stator, CAN bus)
- [x] Forum tips present in fix procedures
- [x] All 6 tests pass (1.02s)

## Risks
- Cross-era phase overlaps with era-specific phases (13-20). Mitigated by focusing on the electrical system angle rather than engine-specific issues.
- Wide year ranges may oversimplify — each issue description includes era-specific caveats.

## Results
| Metric | Value |
|--------|-------|
| Known issues | 10 (voltage regulator, stator, starter solenoid, ground cables, CAN bus, ignition switch, TSSM, wiring harness, battery type, lighting overload) |
| Tests | 6/6, 1.02s |
| Severity breakdown | 3 critical, 4 high, 3 medium |
| DTC codes covered | P0562, P0563, U0100, U0121, U0155, U0401, B1004, B1006 |
| Year coverage | 1970-2025 (all eras) |

This is the most practically useful phase so far — electrical problems account for ~40% of motorcycle shop visits and the troubleshooting approach (voltage testing, ground cleaning, connector inspection) is universal across all Harley eras.
