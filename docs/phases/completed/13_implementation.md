# MotoDiag Phase 13 — Harley Evo Big Twin (1984–1999)

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-16

## Goal
Populate the knowledge base with diagnostic data for the Harley-Davidson Evolution Big Twin engine (1984–1999) — the 1340cc V-twin powering FXR, Softail, Dyna, and Touring. Covers carbureted era through first EFI models. Forum-sourced fixes from HDForums and V-Twin Forum.

CLI: Data loaded via `motodiag db init`

Outputs: `data/knowledge/known_issues_harley_evo_bigtwin.json` (10 issues), 7 tests

## Logic
1. Created 10 known issues covering the most common Evo Big Twin problems:
   - Base gasket oil leak (the inevitable Evo leak)
   - Starter clutch failure (grinding on start)
   - Rocker box oil leak (dripping on jugs)
   - Cam cover leak (oil pooling in the V)
   - CV carburetor slide diaphragm tear (hesitation/bog)
   - Weak charging system (22-amp stator marginal for accessories)
   - Ignition module heat failure (intermittent no-start when hot)
   - Oil pump check valve failure (wet sumping)
   - Pushrod tube O-ring leaks
   - Voltage regulator overheating/melted connector (CRITICAL — fire hazard)
2. Every issue includes forum tips, aftermarket upgrade recommendations, and specific part numbers
3. Year ranges span the full Evo era (1984-1999) with variations noted

## Key Concepts
- Evo Big Twin: 1340cc, 45-degree V-twin, air-cooled, chain primary, 5-speed
- Carbureted (CV40 Keihin) with late EFI transition
- Self-diagnostic via blink codes (pre-CAN, no OBD port)
- Known for oil leaks at every gasket surface — prioritize by severity
- Forum consensus upgrades: Cycle Electric 32-amp stator, Dyna 2000i ignition, James Gasket everything

## Verification Checklist
- [x] 10 known issues load without errors
- [x] Issues searchable by year range (1995 returns 5+ issues)
- [x] Issues don't match outside year range (2020 returns 0)
- [x] Oil leak symptoms return 3+ matching issues
- [x] Forum tips present in fix procedures
- [x] Aftermarket part numbers included
- [x] Critical severity flagged for fire hazard (regulator connector)
- [x] 7 tests pass in 1.38s

## Results
| Metric | Value |
|--------|-------|
| Known issues | 10 |
| Severity breakdown | 1 critical, 2 high, 5 medium, 2 low |
| Forum tips | 10 (one per issue) |
| Part numbers | 15+ (OEM + aftermarket) |
| Year coverage | 1984-1999 |
| Tests | 7 |

First Track B phase complete. The Evo Big Twin is one of the most common engines in any Harley shop — these 10 issues cover the majority of diagnostic scenarios.
