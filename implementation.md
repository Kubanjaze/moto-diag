# MotoDiag — Project Implementation

**Version:** 0.2.4 | **Date:** 2026-04-16
**Repo:** https://github.com/Kubanjaze/moto-diag
**Local:** `C:\Users\Kerwyn\PycharmProjects\moto-diag\`
**Roadmap:** `docs/ROADMAP.md` | 198 phases across 11 tracks

---

## Overview

MotoDiag is an AI-powered motorcycle diagnostic tool designed for mechanics. It combines symptom-based troubleshooting with an AI reasoning engine and optional hardware OBD adapter integration for live ECU data.

**Target fleet:**

**Harley-Davidson** — all eras
- Sportster family: Evo 883/1200 (1986–2003), Rubber-Mount (2004–2021), Sportster S (2021+)
- Big Twin Evo (1984–1999): FXR, Softail, Dyna, Touring
- Twin Cam 88/96/103/110 (1999–2017): Dyna, Softail, Touring, CVO
- Milwaukee-Eight 107/114/117 (2017+): Softail, Touring, CVO
- V-Rod / VRSC (2002–2017)
- Pan America / Sportster S / Nightster (2021+)

**Honda** — sport bikes, standards, cruisers, dual-sport
- CBR sport bikes: CBR600F2/F3/F4/F4i (1991–2006), CBR600RR (2003–2024), CBR900RR/929RR/954RR (1992–2003), CBR1000RR/RR-R (2004+)
- Standards/naked: CB750 (1991–2003), CB900F/919 (2002–2007), CB1000R (2008+), Hornet 600/900
- Cruisers: Shadow 600/750/1100 (1988–2009), VTX 1300/1800 (2002–2009), Rebel 250/300/500/1100
- Dual-sport/adventure: XR650L (1993+), CRF250L/300L, Africa Twin CRF1000L/1100L
- V4: VFR800 Interceptor (1998+), RC51/RVT1000R (2000–2006), VFR1200F
- Vintage/air-cooled: CB550/650/750 (1970s–80s), Nighthawk 250/650/750

**Yamaha** — sport bikes, standards, cruisers, dual-sport
- YZF sport bikes: YZF-R1 (1998+), YZF-R6 (1999–2020), YZF-R7 (2021+), YZF600R Thundercat (1996–2007)
- FZ/MT naked: FZ6/FZ8/FZ-09/FZ-10, MT-03/07/09/10 (2014+)
- Cruisers: V-Star 250/650/950/1100/1300 (1998+), Bolt (2014+), VMAX (1985–2020)
- Dual-sport/adventure: WR250R/X, XT250, Ténéré 700 (2021+)
- Vintage: XS650, RD350/400, SR400/500

**Kawasaki** — sport bikes, standards, cruisers, dual-sport
- Ninja sport bikes: Ninja 250/300/400 (1988+), ZX-6R (1995+), ZX-7R (1996–2003), ZX-9R (1998–2003), ZX-10R (2004+), ZX-12R (2000–2006), ZX-14R (2006–2020), Ninja H2/H2R (2015+)
- Z naked: Z400, Z650, Z750/Z800, Z900, Z1000, Z H2 (2020+)
- Cruisers: Vulcan 500/750/800/900/1500/1600/1700/2000 (1985+)
- Dual-sport/adventure: KLR650 (1987+), KLX250/300, Versys 650/1000
- Vintage: KZ550/650/750/1000/1100, GPz 550/750/900/1100

**Suzuki** — sport bikes, standards, cruisers, dual-sport
- GSX-R sport bikes: GSX-R600 (1997+), GSX-R750 (1996+), GSX-R1000 (2001+), GSX-R1100 (1986–1998)
- SV/Gladius/V-Strom: SV650/1000 (1999+), V-Strom 650/1000/1050 (2002+)
- Standards/naked: Bandit 600/1200/1250 (1995–2012), GSX-S750/1000 (2015+), Katana (2019+)
- Cruisers: Intruder/Boulevard 800/1500/1800 (1985+), Boulevard C50/M50/C90/M109R
- Dual-sport: DR-Z400S/SM (2000+), DR650SE (1996+)
- Vintage: GS550/750/850/1000/1100, GSX1100 Katana

**Target users:** Motorcycle mechanics helping fellow mechanics

---

## Architecture

```
moto-diag/
├── pyproject.toml              ← project config, deps, entry points
├── implementation.md           ← THIS FILE (project-level overview)
├── phase_log.md                ← project-level change log
├── main.py                     ← CLI fallback entry point
├── src/motodiag/
│   ├── __init__.py             ← v0.1.0
│   ├── core/                   ← config, database, base models (Track A)
│   ├── vehicles/               ← vehicle registry, specs (Track A/B)
│   ├── knowledge/              ← DTC codes, symptoms, known issues (Track B)
│   ├── engine/                 ← AI diagnostic engine (Track C)
│   ├── cli/                    ← terminal interface (Track D)
│   ├── hardware/               ← OBD adapter interface (Track E)
│   ├── advanced/               ← fleet, maintenance, prediction (Track F)
│   └── api/                    ← REST API (Track G)
├── data/
│   ├── dtc_codes/              ← fault code databases
│   ├── vehicles/               ← make/model specs
│   └── knowledge/              ← known issues, repair procedures
├── tests/
├── output/
└── docs/
    └── phases/                 ← per-phase implementation + log docs
```

## Package Inventory

| Package | Track | Status | Description |
|---------|-------|--------|-------------|
| `core` | A | Active | Config (pydantic-settings + validators + profiles), database (SQLite + WAL + 6 tables), base models |
| `vehicles` | A/B | Active | Vehicle registry — CRUD operations (add, get, list, update, delete, count) |
| `knowledge` | B | Active | DTC repo (40 codes), symptom repo (40 symptoms), issues repo (10 Harley known issues), JSON loaders |
| `engine` | C | Scaffold | AI diagnostic engine — empty, awaiting Phase 79 |
| `media` | C2 | Scaffold | Video/audio diagnostic analysis — awaiting Phase 96 |
| `cli` | D | Scaffold | Click CLI with 5 subcommands (placeholder stubs) |
| `hardware` | E | Scaffold | OBD adapter interface — empty, awaiting Phase 59 |
| `advanced` | F | Scaffold | Fleet management — empty, awaiting Phase 123 |
| `shop` | G | Scaffold | Shop management, work orders, triage, scheduling — awaiting Phase 135 |
| `api` | H | Scaffold | REST API — empty, awaiting Phase 150 |

## Database Tables

| Table | Purpose | Phase |
|-------|---------|-------|
| `vehicles` | Garage — make/model/year/engine/vin/protocol | 03 |
| `dtc_codes` | Fault codes — code/description/category/severity/make | 03 |
| `symptoms` | Symptom taxonomy — name/description/category | 03 |
| `known_issues` | Known problems — make/model/year_range/fix/parts | 03 |
| `diagnostic_sessions` | Session lifecycle — vehicle/symptoms/diagnosis/confidence | 03 |
| `schema_version` | Migration tracking | 03 |

## CLI Commands

| Command | Status | Phase |
|---------|--------|-------|
| `motodiag --version` | ✅ Working | 01 |
| `motodiag --help` | ✅ Working | 01 |
| `motodiag info` | ✅ Working | 01 |
| `motodiag config show` | ✅ Working | 02 |
| `motodiag config paths` | ✅ Working | 02 |
| `motodiag config init` | ✅ Working | 02 |
| `motodiag search <query>` | ✅ Working | 09 |
| `motodiag db init` | ✅ Working | 12 |
| `motodiag diagnose` | Stub | 79+ |
| `motodiag code <DTC>` | ✅ Working | 05 |
| `motodiag garage` | Stub | 04 |
| `motodiag history` | Stub | 07 |

## Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Build style | Monorepo with subpackages | Single repo, shared models, one .venv |
| CLI framework | Click + Rich | Subcommand architecture, formatted terminal output |
| Config | pydantic-settings | .env support, typed settings, validation |
| Data models | Pydantic v2 | Validation, serialization, type safety |
| Database | SQLite (planned) | Local-first, no server, same as COS |
| AI Engine | Claude API (planned) | Haiku for cost, Sonnet for complex diagnostics |
| Hardware | Optional OBD adapters | CAN (Harley 2011+), K-line (Japanese 90s/2000s), J1850 (older Harley) |

## Dependencies

**Base:** click, rich, pydantic, pydantic-settings
**Dev:** pytest, pytest-cov, ruff
**AI (optional):** anthropic
**API (optional):** fastapi, uvicorn
**Hardware (optional):** pyserial

## Phase History

| Phase | Title | Date | Key Changes |
|-------|-------|------|-------------|
| 01 | Project scaffold + monorepo setup | 2026-04-15 | Initial monorepo, 8 subpackages, CLI, base models, 24 tests |
| 02 | Configuration system | 2026-04-15 | Environment profiles, field validators, ensure_directories, config CLI, 13 tests |
| 03 | Database schema + SQLite setup | 2026-04-15 | 6 tables, WAL mode, connection manager, schema versioning, 12 tests |
| 04 | Vehicle registry data model | 2026-04-15 | CRUD operations (add/get/list/update/delete/count), 14 tests |
| 05 | DTC schema + loader | 2026-04-15 | DTC repo, JSON loader, 40 codes (generic + Harley), code CLI, 15 tests |
| 06 | Symptom taxonomy + data model | 2026-04-15 | Symptom repo, 40 symptoms across 12+ categories, loader, 10 tests |
| 07 | Diagnostic session model | 2026-04-15 | Session lifecycle (9 functions), status transitions, 16 tests |
| 08 | Knowledge base schema | 2026-04-15 | Known issues repo (6 functions), 10 Harley issues with forum tips, loader, 16 tests |
| 09 | Search + query engine | 2026-04-15 | Unified search across 5 stores, search CLI, 7 tests |
| 10 | Logging + audit trail | 2026-04-16 | Structured logging, session audit trail, file handler, 9 tests |
| 11 | Test framework + fixtures | 2026-04-16 | Shared conftest.py, populated_db fixture, 136/136 regression pass |
| 12 | Gate 1 — Integration test | 2026-04-16 | Full mechanic workflow E2E, db init CLI, 140/140 pass, **Gate 1 PASSED** |
| 13 | Harley Evo Big Twin (1984-1999) | 2026-04-16 | 10 known issues, forum tips, aftermarket recs, 7 tests |
| 14 | Harley Twin Cam 88 (1999-2006) | 2026-04-16 | 10 issues: cam tensioner, compensator, sumping, 7 tests |
| 15 | Harley Twin Cam 96/103/110 (2007-2017) | 2026-04-16 | 10 issues: ABS, TBW, ECM tuning, fuel pump, 7 tests |
| 16 | Harley Milwaukee-Eight (2017+) | 2026-04-16 | 10 issues: oil cooler, infotainment, intake carbon, 7 tests |
| 17 | Harley Sportster Evo (1986-2003) | 2026-04-16 | 10 issues: shared oil, clutch cable, carb enrichener, 7 tests |
| 18 | Harley Sportster RB (2004-2021) | 2026-04-16 | 10 issues: fuel pump, stator connector, fork seals, 6 tests |
| 19 | Harley V-Rod / VRSC (2002-2017) | 2026-04-16 | 10 issues: coolant system, hydraulic clutch, fuel cell delamination, alternator rotor nut, frame cracks, 6 tests |
| 20 | Harley Revolution Max (2021+) | 2026-04-16 | 10 issues: TFT freeze, ride-by-wire, water pump, chain drive, battery drain, 6 tests |
| 21 | Harley electrical systems (all eras) | 2026-04-16 | 10 issues: regulator, stator, solenoid, grounds, CAN bus, TSSM, wiring, battery types, 6 tests |
| 22 | Harley common cross-era issues | 2026-04-16 | 10 issues: compensator, intake seals, heat soak, primary leak, clutch, shocks, wheel bearings, 6 tests |
| 23 | Honda CBR supersport 900RR/929RR/954RR | 2026-04-16 | 10 issues: reg/rec, CCT, HISS, carb sync, fork seals, starter clutch, 6 tests |
| 24 | Honda CBR600 F2/F3/F4/F4i (1991-2006) | 2026-04-16 | 10 issues: reg/rec, carbs, CCT, F4i injectors, clutch cable, radiator fan, 6 tests |
| 25 | Honda CBR600RR (2003-2024) | 2026-04-16 | 10 issues: HESD, reg/rec, C-ABS, CCT, fuel pump, valve clearance, 6 tests |
| 26 | Honda CBR1000RR / RR-R (2004+) | 2026-04-16 | 10 issues: reg/rec, HSTC, CCT, HESD, quickshifter, exhaust servo, brakes, 6 tests |
| 27 | Honda cruisers Shadow/VTX | 2026-04-16 | 10 issues: reg/rec, shaft drive, carbs, VTX starter, fuel pump, clutch drag, 6 tests |
| 28 | Honda Rebel 250/300/500/1100 | 2026-04-16 | 10 issues: carb 250, reg/rec, DCT jerky, chain 300/500, battery drain, drum brake, 6 tests |
| 29 | Honda standards CB750/919, CB1000R, Hornet | 2026-04-16 | 10 issues: reg/rec, CCT, ride-by-wire, carbs, chain, vibes, tank rust, 6 tests |

## Completion Gates

| Gate | Target Phase | Status | Criteria |
|------|-------------|--------|----------|
| Gate 1 | 12 | ✅ | Vehicle → symptoms → session → DTCs → search → diagnose → close |
| Gate 2 | ~78 | 🔲 | Query any target bike → get DTCs, symptoms, known issues, fixes |
| Gate 3 | ~95 | 🔲 | Full symptom-to-repair flow with confidence + cost |
| Gate 4 | ~108 | 🔲 | Full mechanic workflow through CLI |
| Gate 5 | ~122 | 🔲 | Simulated ECU → adapter → read codes → AI diagnosis |
| Gate 6 | ~134 | 🔲 | Fleet + history + prediction end-to-end |
| Gate 7 | ~144 | 🔲 | Full API workflow: auth → vehicle → diagnose → report |
| Gate 8 | ~159 | 🔲 | Full API + shop management workflow |
| Gate 9 | ~179 | 🔲 | Full mobile flow: scan VIN → diagnose → share report |
