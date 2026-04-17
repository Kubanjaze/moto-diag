# MotoDiag — Project Implementation

**Version:** 0.6.4 | **Date:** 2026-04-17
**Repo:** https://github.com/Kubanjaze/moto-diag
**Local:** `C:\Users\Kerwyn\PycharmProjects\moto-diag\`
**Roadmap:** `docs/ROADMAP.md` | 352 phases across 21 tracks (A-T)

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

**European brands** (Track K, phases 211–240) — BMW, Ducati, KTM, Triumph, Aprilia, MV Agusta
**Electric motorcycles** (Track L, phases 241–250) — Zero, Harley LiveWire, Energica, Damon
**Scooters & small-displacement** (Track M, phases 251–258) — Vespa, Honda Grom/Ruckus, Kymco, SYM, 50-300cc class

**Target users:** Motorcycle mechanics (solo → shop → multi-location), subscription tiers $19/$99/$299/mo

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
| `pricing` | G | Active | Labor rates (regional/national), repair plan builder (CRUD), cost estimation, prep labor catalog |
| `engine` | C | Active | AI diagnostic engine — client, models, prompts, symptoms, fault codes, workflows, confidence, cost estimation, parts recommendation |
| `media` | C2 | Active | Audio/video diagnostic analysis — 12 modules: capture, spectrogram, signatures, anomaly, video frames, vision, fusion, comparative, realtime, annotation, reports, coaching |
| `cli` | D | Active | Click CLI + subscription tier system ($19/$99/$299), command registry, tier command |
| `auth` | Retrofit 112 | Planned | Users, roles, permissions — users/roles/permissions tables, FK retrofit onto sessions/plans/issues |
| `crm` | Retrofit 113 | Planned | Customers + customer-bikes join — customer_id FK retrofit onto vehicles |
| `hardware` | E | Scaffold | OBD adapter interface — empty, awaiting Phase 134 |
| `advanced` | F | Scaffold | Fleet management — empty, awaiting Phase 148 |
| `shop` | G | Scaffold | Shop management, work orders, triage, scheduling — awaiting Phase 160 |
| `api` | H | Scaffold | REST API — empty, awaiting Phase 175, hard paywall enforcement activates here |
| `billing` | Retrofit 118 / O | Complete | SubscriptionTier + SubscriptionStatus + PaymentStatus enums, Subscription + Payment models, 11 repo functions with Stripe column pre-wiring (stripe_customer_id, stripe_subscription_id, stripe_payment_intent_id) |
| `accounting` | Retrofit 118 / O | Complete | InvoiceStatus + InvoiceLineItemType enums, Invoice + InvoiceLineItem models, 11 repo functions including recalculate_invoice_totals(tax_rate) |
| `inventory` | Retrofit 118 / O | Complete | CoverageType enum, 4 models (InventoryItem/Vendor/Recall/Warranty), 4 repo modules with 25+ functions including adjust_quantity, items_below_reorder, list_recalls_for_vehicle, increment_claim_count |
| `scheduling` | Retrofit 118 / O | Complete | AppointmentType + AppointmentStatus enums, Appointment model, 9 repo functions including cancel_appointment(reason), complete_appointment(actual_end), list_upcoming(from_iso), list_for_user(mechanic_id) |
| `intake` | 122 / D | Complete | Photo-based bike ID via Claude Haiku 4.5 vision. IdentifyKind enum, VehicleGuess + IntakeUsageEntry + IntakeQuota models, VehicleIdentifier orchestrator (quota → hash cache → 1024px resize → vision call → Sonnet escalation on low confidence → usage log → 80% budget alert). Tier caps 20/200/unlimited enforced from `subscriptions.tier`. Image bytes never persist (sha256 only). Pillow optional dep. CLI: `garage add-from-photo`, `intake photo`, `intake quota` |
| `workflows` | Retrofit 114 / N | Planned | PPI, tire service, winterization, break-in templates |
| `i18n` | Retrofit 115 / Q | Complete | Locale enum (7 codes), Translation model, t() translator with locale → en → `[namespace.key]` fallback, string interpolation, translations table, bulk import, locale_completeness reporter — 45 English strings seeded across 4 namespaces |
| `reference` | Retrofit 117 / P | Complete | 4 enums (ManualSource / DiagramType / FailureCategory / SkillLevel), 4 Pydantic models, 4 repo modules × 5 CRUD functions each (20 total), year-range filter pattern reused from known_issues — substrate for Track P content phases |
| `feedback` | Retrofit 116 / R | Complete | FeedbackOutcome + OverrideField enums, DiagnosticFeedback + SessionOverride models, 8 repo functions + FeedbackReader read-only hook (iter_feedback / get_accuracy_metrics / get_common_overrides) — substrate for Track R learning phases |
| `ai_advanced` | R | Planned | Human-in-loop learning, tuning recs, knowledge graph (phases 318-327) |
| `launch` | S | Planned | Signup, onboarding, data migration, community, certification (phases 328-342) |
| `ops` | T | Planned | Telemetry, support, backups, feature flags, admin panel (phases 343-352) |

## Database Tables

| Table | Purpose | Phase |
|-------|---------|-------|
| `vehicles` | Garage — make/model/year/engine/vin/protocol | 03 |
| `dtc_codes` | Fault codes — code/description/category/severity/make | 03 |
| `symptoms` | Symptom taxonomy — name/description/category | 03 |
| `known_issues` | Known problems — make/model/year_range/fix/parts | 03 |
| `diagnostic_sessions` | Session lifecycle — vehicle/symptoms/diagnosis/confidence | 03 |
| `labor_rates` | Regional/national labor rate data by shop type | pricing |
| `prep_labor` | Prep labor catalog (fairing removal, drain/refill, etc.) | pricing |
| `repair_plans` | Per-bike repair plans with status tracking | pricing |
| `repair_plan_items` | Line items within plans (labor, parts, prep, diagnostic) | pricing |
| `translations` | i18n strings — composite PK (locale, namespace, key) + value + optional context | Retrofit 115 |
| `diagnostic_feedback` | Post-diagnosis feedback — AI vs actual, outcome enum, parts used, labor hours | Retrofit 116 |
| `session_overrides` | Field-level overrides on diagnostic sessions (diagnosis/severity/cost/etc.) | Retrofit 116 |
| `manual_references` | Service manual citations (Clymer/Haynes/OEM/forum) with year-range targeting | Retrofit 117 |
| `parts_diagrams` | Exploded views, schematics, wiring, assembly diagrams; optional FK to manual | Retrofit 117 |
| `failure_photos` | Failure-mode photo library by category + year range | Retrofit 117 |
| `video_tutorials` | Tutorial video index (YouTube/Vimeo/internal) with skill_level + topic_tags | Retrofit 117 |
| `subscriptions` | Per-user subscription tier + status, Stripe customer/subscription IDs | Retrofit 118 |
| `payments` | Payment records with Stripe payment_intent_id, status enum | Retrofit 118 |
| `invoices` | Customer invoices (FK customers, optional FK repair_plans), subtotal/tax/total | Retrofit 118 |
| `invoice_line_items` | Line items per invoice (labor/parts/diagnostic/misc), optional FK repair_plan_items | Retrofit 118 |
| `vendors` | Parts/service vendors with contact info, payment terms | Retrofit 118 |
| `inventory_items` | Parts inventory — sku, model_applicable JSON, quantity, reorder point, vendor FK | Retrofit 118 |
| `recalls` | NHTSA-style recall campaigns with year-range targeting | Retrofit 118 |
| `warranties` | Per-vehicle warranties — coverage type, provider, mileage limit, claim count | Retrofit 118 |
| `appointments` | Customer appointments — type/status enums, scheduled ISO times, assigned mechanic | Retrofit 118 |
| `photo_annotations` | Coordinate-normalized shape annotations (circle/rectangle/arrow/text) on images; optional FK to failure_photos | Retrofit 119 |
| `intake_usage_log` | Photo-ID usage ledger — tokens, cost, model_used, image hash, per user per month (quota enforcement + caching) | 122 |
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
| 30 | Honda V4: VFR800, RC51, VFR1200F | 2026-04-16 | 10 issues: VTEC, reg/rec, RC51 TPS, gear cam noise, CBS, fuel pump relay, 6 tests |
| 31 | Honda dual-sport: XR650L, CRF, Africa Twin | 2026-04-16 | 10 issues: XR650L jetting, AT DCT off-road, radiator, water damage, chain, 6 tests |
| — | **Pricing/Repair Plan module** | 2026-04-16 | Labor rates (26 regions), prep labor catalog (18 items), repair plan CRUD, estimate engine, 24 tests |
| 32 | Honda vintage air-cooled CB/Nighthawk | 2026-04-16 | 10 issues: points ignition, carb rebuild, charging, cam chain, petcock, brakes, wiring, 6 tests |
| 33 | Honda electrical systems + PGM-FI | 2026-04-16 | 10 issues: blink codes, HISS, reg/rec, stator, starter, FI sensors, grounds, fuses, 6 tests |
| 34 | Honda common cross-model issues | 2026-04-16 | 10 issues: CCT, starter clutch, coolant, valves, chain, brake fluid, throttle, forks, tires, 6 tests |
| 35 | Yamaha YZF-R1 (1998+) | 2026-04-16 | 10 issues: EXUP, stator, crossplane, YCC-T, YCC-I, fuel pump, CCT, suspension, 6 tests |
| 36 | Yamaha YZF-R6 (1999-2020) | 2026-04-16 | 10 issues: CCT, stator, valve clearance, EXUP, underseat heat, fuel pump, throttle sync, coolant, immobilizer, electronics, 6 tests |
| 37 | Yamaha YZF-R7 + YZF600R Thundercat | 2026-04-16 | 10 issues: Thundercat carbs/petcock/charging/chain/forks + R7 clutch/suspension/QS/heat/lean, 6 tests |
| 38 | Yamaha FZ/MT naked series | 2026-04-16 | 10 issues: MT-09 throttle/valves/fuel, MT-07 charging/chain, FZ6 heat, MT-10 electronics, 6 tests |
| 39 | Yamaha cruisers V-Star/Bolt | 2026-04-16 | 10 issues: V-Star carbs/petcock/stator/shaft drive, starter clutch, ISC surge, Bolt heat/belt, AIS, 6 tests |
| 40 | Yamaha VMAX (1985-2020) | 2026-04-16 | 10 issues: Gen 1 V-Boost/carbs/charging/shaft drive/tank + Gen 2 FI/cooling/brakes/electronics, 6 tests |
| 41 | Yamaha dual-sport WR250R/XT250/Tenere 700 | 2026-04-16 | 10 issues: WR250R stator/suspension/cold start + XT250 carb/chain + Tenere wind/crash/lean, 6 tests |
| 42 | Yamaha vintage XS650/RD350/SR400 | 2026-04-16 | 10 issues: XS650 points/charging/oil + RD Autolube/chambers + SR kickstart/carb/valves, 6 tests |
| 43 | Yamaha electrical systems + diagnostics | 2026-04-16 | 10 issues: self-diagnostic, stator connector, MOSFET, grounds, harness, fuses, immobilizer, LED, batteries, 6 tests |
| 44 | Yamaha common cross-model issues | 2026-04-16 | 10 issues: CCT, ethanol, valves, EXUP, brakes, chain, coolant, tires, winterization, exhaust mods, 6 tests |
| 45 | Kawasaki Ninja 250/300/400 | 2026-04-16 | 10 issues: carbs, drops, charging, fuel pump, chain, valves, ABS, coolant, header crack, oil neglect, 6 tests |
| 46 | Kawasaki ZX-6R (1995+) | 2026-04-16 | 10 issues: 636/599, stator, CCT, KLEEN, valves, fuel pump, cooling, KTRC, forks, QS, 6 tests |
| 47 | Kawasaki ZX-7R / ZX-7RR (1996-2003) | 2026-04-16 | 10 issues: carbs, fuel system, charging, FCR, CCT, wiring, rubber, suspension, brakes, ignition, 6 tests |
| 48 | Kawasaki ZX-9R (1998-2003) | 2026-04-17 | 10 issues: carbs, early FI, charging, CCT, cooling, fuel pump, forks, brakes, valves, ignition switch, 6 tests |
| 49 | Kawasaki ZX-10R (2004+) | 2026-04-17 | 10 issues: headshake, charging, IMU, CCT, fuel pump, valves, KLEEN, crash, QS, cooling, 6 tests |
| 50 | Kawasaki ZX-12R / ZX-14R (2000-2020) | 2026-04-17 | 10 issues: ram air, charging, consumables, FI tuning, ABS/KTRC, chain, CCT, cooling, suspension, 6 tests |
| 51 | Kawasaki Ninja H2 / H2R (2015+) | 2026-04-17 | 10 issues: supercharger, cooling, electronics, paint, chain, oil, fuel, H2 SX, brakes, valves, 6 tests |
| 52 | Kawasaki Z naked series | 2026-04-17 | 10 issues: radiator, throttle, connectors, charging, Z H2 heat, chain, KTRC, CCT, beginner, headlights, 6 tests |
| 53 | Kawasaki Vulcan cruisers | 2026-04-17 | 10 issues: carbs, ISC surge, shaft drive, starter, Vulcan 2000, belt, heat, 1700 EFI, Vulcan 500, exhaust mods, 6 tests |
| 54 | Kawasaki dual-sport KLR650/KLX/Versys | 2026-04-16 | 10 issues: doohickey, overheating, FI lean surge, valves, suspension, TBW, subframe, jetting, chain, stator, 6 tests |
| 55 | Kawasaki vintage KZ/GPz | 2026-04-16 | 10 issues: CCT, charging, carb rebuild, fuel system, points ignition, forks, oil leaks, brakes, wiring, chain, 6 tests |
| 56 | Kawasaki electrical + FI dealer mode | 2026-04-16 | 10 issues: dealer mode, stator/reg-rec, KLEEN, KIPASS, LED, grounds, starter, parasitic draw, KTRC/KIBS, connectors, 6 tests |
| 57 | Suzuki GSX-R600 (1997+) | 2026-04-16 | 10 issues: stator, CCT, PAIR, fuel pump, forks, valves, cooling, S-DMS/TC, brakes, clutch, 6 tests |
| 58 | Suzuki GSX-R750 (1996+) | 2026-04-16 | 10 issues: 2nd gear, stator, CCT, fuel pump, SRAD coolant, linkage, TPS, chain, master cyl, headstock, 6 tests |
| 59 | Suzuki GSX-R1000 (2001+) | 2026-04-16 | 10 issues: K5-K8 case cracking, stator, IMU/TCS, CCT, SET servo, fuel relay, valves, QS, cooling, wheel bearings, 6 tests |
| 60 | Suzuki GSX-R1100 (1986-1998) | 2026-04-16 | 10 issues: air/oil overheating, carbs, charging, CCT, suspension, CDI ignition, petcock/tank, brakes, wiring, chain, 6 tests |
| 61 | Suzuki SV650/1000 + Gladius | 2026-04-16 | 10 issues: reg/rec, carb tuning, CCT, clutch, fuel pump, suspension, SV1000 STPS, Gladius, forks, exhaust mods, 6 tests |
| 62 | Suzuki V-Strom 650/1000/1050 | 2026-04-16 | 10 issues: lean surge, CCT, windscreen, suspension loading, 1050 electronics, charging, chain, valves, side stand, ABS, 6 tests |
| 63 | Suzuki Bandit 600/1200/1250 | 2026-04-16 | 10 issues: overheating, carbs, FI, charging, CCT, suspension, petcock, brakes, chain, wiring, 6 tests |
| 64 | Suzuki GSX-S/Katana (2015+) | 2026-04-16 | 10 issues: TBW, CCT, Katana heat, charging, fuel relay, chain, mirrors, valves, TC/ABS, forks, 6 tests |
| 65 | Suzuki cruisers Intruder/Boulevard | 2026-04-16 | 10 issues: carbs, FI surge, shaft drive, M109R clutch, starter clutch, charging, heat, fuel pump, exhaust, brakes, 6 tests |
| 66 | Suzuki dual-sport DR-Z400/DR650 | 2026-04-16 | 10 issues: jetting, valves, SM brakes, DR650 carb/oil, chain, electrical, suspension, kick start, DR650 starter, 6 tests |
| 67 | Suzuki vintage GS/Katana 1100 | 2026-04-16 | 10 issues: CCT, charging, carbs, ignition, fuel system, suspension, brakes, oil leaks, wiring, chain, 6 tests |
| 68 | Suzuki electrical + FI dealer mode | 2026-04-16 | 10 issues: C-mode, stator/reg-rec, PAIR, grounds, starter, parasitic draw, TC/ABS, LED, connectors, FI relay, 6 tests |
| 69 | Suzuki common cross-model | 2026-04-16 | 10 issues: stator connector fire risk, CCT pattern, fuel relay, PAIR, coolant, valves, chain, brakes, forks, exhaust mods, 6 tests |
| 70 | Carburetor troubleshooting (cross-platform) | 2026-04-16 | 10 issues: CV diaphragm, pilot jet, float height, sync, enrichment, vacuum leaks, pilot screw, overflow, rejetting, EFI conversion, 6 tests |
| 71 | Fuel injection troubleshooting (cross-platform) | 2026-04-16 | 10 issues: fuel pump, TPS, MAP, O2, ECT, injectors, ISC, throttle body, fuel pressure, ECU reset, 6 tests |
| 72 | Charging system diagnostics (cross-platform) | 2026-04-17 | 10 issues: stator, reg/rec, connector, rotor, batteries, parasitic draw, 3-step test, grounds, accessories, alternator belt, 6 tests |
| 73 | Starting system diagnostics (cross-platform) | 2026-04-17 | 10 issues: relay, motor, sprag, clutch switch, kickstand switch, kill switch, cables, tip-over, neutral, compression, 6 tests |
| 74 | Ignition system diagnostics (cross-platform) | 2026-04-17 | 10 issues: plugs, coils, CDI, pickup, wires, points, timing, kill switch, misfires, COP, 6 tests |
| 75 | Cooling system diagnostics (cross-platform) | 2026-04-17 | 10 issues: thermostat, fan, coolant, water pump, radiator, air-cooled, hoses, head gasket, cap, track coolant, 6 tests |
| 76 | Brake system diagnostics (cross-platform) | 2026-04-17 | 10 issues: fluid, calipers, pads, rotors, master cyl, stainless lines, ABS sensors, ABS bleeding, drum, bolt torque, 6 tests |
| 77 | Drivetrain diagnostics (cross-platform) | 2026-04-17 | 10 issues: chain, sprockets, lube, belt, shaft, clutch drag, cable/hydraulic, transmission, countershaft seal, alignment, 6 tests |
| 78 | Gate 2 — Knowledge base integration test | 2026-04-17 | 21 integration tests, 650+ issues, all 5 makes, cross-platform systems verified, **GATE 2 PASSED** |
| 79 | Claude API integration + base client | 2026-04-17 | DiagnosticClient, TokenUsage, SessionMetrics, system prompts, context builders, 32 tests |
| 80 | Symptom analysis prompt engineering | 2026-04-17 | SymptomAnalyzer, categorize_symptoms, assess_urgency, two-pass KB→AI approach, 28 tests |
| 81 | Fault code interpretation prompts | 2026-04-17 | FaultCodeInterpreter, 8 DTC format classifiers, 51 local code entries, quick_lookup, 36 tests |
| 82 | Multi-step diagnostic workflows | 2026-04-17 | DiagnosticWorkflow, 3 predefined templates (no-start/charging/overheating), AI step generation, 26 tests |
| 83 | Confidence scoring | 2026-04-17 | ConfidenceScore, 8 evidence types, normalization, 5 labels, rank_diagnoses, 23 tests |
| 84 | Repair procedure generator | 2026-04-17 | RepairProcedureGenerator, RepairStep/RepairProcedure models, SkillLevel assessment, 41 tests |
| 85 | Parts + tools recommendation | 2026-04-17 | PartsRecommender, PartRecommendation with cross-refs, ToolRecommendation, 13+ brands, 35 tests |
| 86 | Cost estimation | 2026-04-17 | CostEstimator, ShopType comparison (dealer/independent/DIY), format_estimate, 34 tests |
| 87 | Safety warnings + critical alerts | 2026-04-17 | SafetyChecker, 18 SAFETY_RULES, 12 REPAIR_SAFETY_KEYWORDS, AlertLevel, format_alerts, 37 tests |
| 88 | Diagnostic history + learning | 2026-04-17 | DiagnosticHistory, add/get/search/statistics, find_similar for RAG context, 45 tests |
| 89 | Similar case retrieval | 2026-04-17 | CaseRetriever, Jaccard symptom similarity, vehicle/year matching, ranked results, 32 tests |
| 90 | Multi-symptom correlation | 2026-04-17 | SymptomCorrelator, 15+ predefined rules, partial match support, ranked by quality, 38 tests |
| 91 | Intermittent fault analysis | 2026-04-17 | IntermittentAnalyzer, 10+ patterns (cold/hot/rain/load/RPM/random), condition extraction, 43 tests |
| 92 | Wiring diagram reference | 2026-04-17 | 5 circuit references (charging/starting/FI/ignition/ABS), wire colors, test points, 29 tests |
| 93 | Torque specs + service data | 2026-04-17 | 20 torque specs, 14 service intervals, 8 valve clearances, auto Nm→ft-lbs, 39 tests |
| 94 | AI evaluation + accuracy tracking | 2026-04-17 | EvaluationTracker, ADR-005 scorecard (Q:40%+C:40%+L:20%), model comparison, 21 tests |
| 95 | Gate 3 — AI engine integration test | 2026-04-17 | 39 integration tests, 16 modules verified, 1163 total tests, **GATE 3 PASSED** |
| 96 | Audio capture + preprocessing | 2026-04-17 | AudioPreprocessor, WAV management, synthetic generators, 36 tests |
| 97 | Audio spectrogram analysis | 2026-04-17 | Pure Python DFT, 6 motorcycle frequency bands, Hann windowing, 30 tests |
| 98 | Engine sound signature database | 2026-04-17 | 7 engine types, RPM-to-firing-frequency, profile matching, 25 tests |
| 99 | Audio anomaly detection | 2026-04-17 | 9 anomaly signatures (knock, misfire, valve tick, etc.), 29 tests |
| 100 | Video frame extraction | 2026-04-17 | Frame extraction plan, keyframes, metadata models, 34 tests |
| 101 | Visual symptom analysis | 2026-04-17 | Claude Vision prompts, smoke/fluid color guides, 34 tests |
| 102 | Multimodal fusion | 2026-04-17 | Weighted evidence combination, conflict detection, 30 tests |
| 103 | Comparative audio analysis | 2026-04-17 | Before/after comparison, improvement scoring, 30 tests |
| 104 | Real-time audio monitoring | 2026-04-17 | Session lifecycle, RPM estimation, alert generation, 26 tests |
| 105 | Video annotation + timestamps | 2026-04-17 | Timestamped annotations, timeline, auto-annotate, 27 tests |
| 106 | Media-enhanced diagnostic reports | 2026-04-17 | Reports with media attachments, text formatting, 26 tests |
| 107 | AI audio coaching | 2026-04-17 | 5 capture protocols, quality evaluation, symptom mapping, 30 tests |
| 108 | Gate 4 — Media diagnostics integration test | 2026-04-17 | 24 integration tests, 12 modules, 1575 total, **GATE 4 PASSED** |
| 109 | CLI foundation + 3-tier subscription | 2026-04-17 | Click CLI, SubscriptionTier enum, $19/$99/$299 pricing, requires_tier decorator (soft/hard modes), tier command, 41 tests, 1616 total |
| — | **Roadmap expansion planning** | 2026-04-17 | Expanded roadmap from 198 to 352 phases. Inserted 12-phase Retrofit track (110-121). Renumbered Tracks D-J. Appended Tracks K-T. 18 new packages planned. 20 gates + Gate R. |
| 110 | Retrofit: vehicle registry + protocol expansion | 2026-04-17 | Migration framework (reusable for phases 111-120), PowertrainType/EngineType/BatteryChemistry enums, European CAN protocols (BMW_K_CAN/DUCATI_CAN/KTM_CAN), 5 new VehicleBase fields, schema v2→v3, 35 tests, 1651 total passing, zero regressions |
| 111 | Retrofit: knowledge base schema expansion | 2026-04-17 | Migration 004, DTCCategory enum (20 members: 7 ICE + 7 chassis/safety + 6 electric), dtc_category_meta table, 6 OEM DTC classifiers (BMW ISTA / Ducati DDS / KTM KDS / Triumph TuneECU / Aprilia / Electric HV), 3 new repo functions, schema v3→v4, 43 tests, 1694 total passing, zero regressions |
| 112 | Retrofit: user/auth layer introduction | 2026-04-17 | Migration 005, auth/ package (5 Pydantic models + users_repo + roles_repo), 5 new tables (users/roles/permissions/user_roles/role_permissions), seeded system user + 4 roles + 12 permissions + 31 role-permission mappings, retrofit user_id FKs onto diagnostic_sessions/repair_plans/known_issues, schema v4→v5, 40 tests, 1734 total passing, zero regressions |
| 113 | Retrofit: customer/CRM foundation | 2026-04-17 | Migration 006, crm/ package (Customer + CustomerBike models + CustomerRelationship enum + 14 repo functions), 2 new tables (customers + customer_bikes), 4 indexes, unassigned placeholder customer (id=1) owns pre-retrofit vehicles, ownership transfer workflow (atomic demote + assign), backward compat preserved via DEFAULT 1, schema v5→v6, 35 tests, 1769 total passing, zero regressions (2 phase-112 tests relaxed for migration dependency ordering) |
| 114 | Retrofit: workflow template substrate | 2026-04-17 | Migration 007, workflows/ package (WorkflowCategory enum 13 members + WorkflowTemplate + ChecklistItem models + 10 repo functions), workflow_templates + checklist_items tables with CASCADE delete, 2 seed templates (generic PPI + winterization) with 9 starter checklist items, foundation for Track N phases 259-272, schema v6→v7, 32 tests, 1801 total passing, zero regressions |
| 115 | Retrofit: i18n substrate | 2026-04-17 | Migration 008, i18n/ package (Locale enum 7 codes en/es/fr/de/ja/it/pt + Translation model + t() translator with locale→en→`[namespace.key]` fallback + string interpolation + current_locale/set_locale env-var handling + 8 repo functions), translations table with composite PK `(locale, namespace, key)` + 2 indexes, 45 English strings seeded across 4 namespaces (11 cli + 12 ui + 11 diagnostics + 11 workflow), foundation for Track Q phases 308-310, schema v7→v8, 40 tests, 1841 total passing, zero regressions |
| 116 | Retrofit: feedback/learning hooks | 2026-04-17 | Migration 009, feedback/ package (FeedbackOutcome enum 4 values + OverrideField enum 6 values + DiagnosticFeedback + SessionOverride models + 8 repo functions + FeedbackReader read-only hook with iter_feedback generator / get_accuracy_metrics / get_common_overrides), diagnostic_feedback + session_overrides tables with FK CASCADE on session / SET DEFAULT on user, 4 indexes, feedback records immutable once submitted (preserves training signal), foundation for Track R phases 318-327, schema v8→v9, 26 tests, 1867 total passing, zero regressions |
| 117 | Retrofit: reference data tables | 2026-04-17 | Migration 010, reference/ package (4 enums: ManualSource/DiagramType/FailureCategory/SkillLevel with 5+4+7+4 members, 4 Pydantic models, 4 repo modules with 5 CRUD functions each = 20 total), 4 new tables (manual_references + parts_diagrams + failure_photos + video_tutorials) with 8 indexes, year-range filter pattern (year_start<=target<=year_end, NULL=universal) reused from known_issues, parts_diagrams.source_manual_id ON DELETE SET NULL, failure_photos.submitted_by_user_id ON DELETE SET DEFAULT, foundation for Track P phases 293-302, schema v9→v10, 28 tests, 1895 total passing, zero regressions |
| 118 | Retrofit: ops substrate (billing+accounting+inventory+scheduling) | 2026-04-17 | Migration 011, 4 new packages (billing, accounting, inventory, scheduling), 8 enums (34 members total), 9 Pydantic models, ~55 repo functions across 8 repo modules. 9 new tables: subscriptions/payments (billing with Stripe column pre-wiring), invoices/invoice_line_items (accounting with recalculate_invoice_totals+tax), inventory_items/vendors/recalls/warranties (inventory with adjust_quantity/items_below_reorder), appointments (scheduling with cancel/complete/list_upcoming). 14 indexes. FK strategy: CASCADE on user/customer/vehicle/invoice parents, SET NULL on vendor/repair_plan/mechanic references. Foundation for Track O phases 273-289 (Stripe, QuickBooks, calendar sync) and Track S phases 328-329 (customer billing portal). Schema v10→v11, 37 tests, 1932 total passing, zero regressions |
| 119 | Retrofit: photo annotation layer | 2026-04-17 | Migration 012, media/photo_annotation module (AnnotationShape enum 4 members — circle/rectangle/arrow/text), PhotoAnnotation Pydantic model with 3 validators (coord bounds [0.0, 1.0], hex color `#RRGGBB` regex with auto-uppercase, size bounds supporting negative arrow deltas), media/photo_annotation_repo with 8 functions (CRUD + list-by-image + list-by-failure-photo + count + bulk_import). photo_annotations table with 3 indexes. Dual-mode annotation: FK-linked (CASCADE on failure_photos delete) OR orphan-safe (by image_ref, survives photo delete). Coordinate normalization survives image resize/crop. Foundation for Track Q phase 307. Schema v11→v12, 22 tests, 1954 total passing, zero regressions |
| 120 | Retrofit: engine sound signature library expansion | 2026-04-17 | Extended media/sound_signatures.py with 4 new EngineType enum members (ELECTRIC_MOTOR, DUCATI_L_TWIN, KTM_LC8_V_TWIN, TRIUMPH_TRIPLE) and 4 new SIGNATURES entries with physics-grounded frequencies, rich characteristic_sounds, and diagnostic notes. New helper motor_rpm_to_whine_frequency(motor_rpm, pole_pairs) for electric signature computation. ELECTRIC_MOTOR uses firing_freq_* fields as motor whine fundamental (documented reinterpretation). DUCATI_L_TWIN documents dry clutch rattle as NORMAL to prevent mechanic misdiagnosis. 3 Phase 98 test fixes for forward-compat (superset check + ELECTRIC_MOTOR exemption from combustion-specific assertions). No migration — pure code expansion. 38 new tests, 1992 total passing, zero regressions. Key finding: existing SoundSignature model handles non-combustion powertrains without architectural change (critical for Track L electric phases) |
| 121 | Retrofit: Gate R integration test | 2026-04-17 | **GATE R PASSED** — retrofit track (phases 110-121) closed. Single integration test file with 10 tests: (A) one end-to-end workflow test exercising all 12 retrofit packages on a shared DB fixture (users + RBAC → customer → LiveWire electric bike → HV_BATTERY DTC → session + feedback + override → workflow template → i18n fallback → reference data → photo annotations with CASCADE → ops substrate with invoice+tax recalc + subscription + appointment + inventory + recall + warranty → sound signature lookup), (B) 5 migration integrity tests including fresh-init determinism (two independent fresh DBs produce identical table sets) and rollback-to-baseline (all retrofit-added tables removed), (C) 2 CLI smoke tests (subprocess `motodiag.cli.main --help` + in-process import of all 12 retrofit packages). One known limitation documented: migration 005's rollback does not DROP the ALTER-added `user_id` column (pre-3.35 SQLite lacks DROP COLUMN), so in-place rollback-and-replay is unsafe. Fresh init is fully deterministic. 10 new tests, 2002 total passing, zero regressions |
| 122 | Vehicle garage management + photo-based bike intake | 2026-04-17 | First post-retrofit user-facing phase. Migration 013 adds intake_usage_log table. New src/motodiag/intake/ package: IdentifyKind enum, VehicleGuess + IntakeUsageEntry + IntakeQuota models, VehicleIdentifier orchestrator (quota → sha256 hash → cache → 1024px Pillow resize → Claude Haiku 4.5 vision → Sonnet escalation if confidence < 0.5 → usage log → 80% budget alert). Tier caps: individual 20/mo, shop 200/mo, company unlimited — enforced from subscriptions.tier (Phase 118 retrofit now load-bearing). Image bytes never persist (only sha256). Pillow as optional dep. CLI expanded: `garage add/list/remove` + `garage add-from-photo <path>` (commit flow) + `intake photo <path>` (preview-only) + `intake quota` (status). 49 new tests, all vision calls mocked, zero tokens burned during build. 2051 total passing, zero regressions. Schema v12→v13. |
| 123 | Interactive diagnostic session (CLI) | 2026-04-17 | No migration — pure orchestration on existing Phase 03 `diagnostic_sessions` substrate. New `src/motodiag/cli/diagnose.py` (~450 LoC) + 4 CLI subcommands: `diagnose start` (Q&A loop, up to 3 clarifying rounds, terminates at confidence ≥ 0.7 / empty input / hard cap), `diagnose quick` (one-shot), `diagnose list` (rich table with status filter), `diagnose show <id>` (render stored diagnosis). Tier-based model access: individual → Haiku forced; shop/company → Sonnet unlocked via `--model sonnet`. HARD paywall mode raises with upgrade hint; SOFT falls back with warning. One session row per user-visible interaction; interactive rounds accumulate `tokens_used`. `_default_diagnose_fn` injected via `patch()` in tests — zero live API tokens burned. `_FakeUsage` shim lets `_persist_response` handle accumulated multi-round totals. 39 new tests. 2090 total passing, zero regressions. Schema v13 unchanged — Phase 118's `subscriptions.tier` now load-bearing for both quota (Phase 122) and model access (Phase 123). |
| 124 | Fault code lookup (CLI) | 2026-04-17 | No migration — pure orchestration on Phase 03 `dtc_codes` + Phase 111 `dtc_category_meta` substrates. New `src/motodiag/cli/code.py` (392 LoC) replaces Phase 01's inline `code` command via `register_code(cli)` with an explicit legacy-command eviction guard. Single `motodiag code` command with three modes: (1) default DB lookup with fallback chain make-specific → generic → `classify_code()` heuristic (yellow "no DB entry" banner + "run with --explain" hint on fallback); (2) `--category hv_battery` lists all DTCs in a category via `get_dtcs_by_category`; (3) `--explain --vehicle-id N [--symptoms ...] [--model haiku|sonnet]` runs `FaultCodeInterpreter` with tier-gated model access (same `_resolve_model` as Phase 123). `_default_interpret_fn` injected via `patch()` — zero live tokens burned. `_render_explain` handles 7 conditional sections (header, safety-critical banner, causes table, tests, related symptoms, repair steps, hours/cost, notes). Phase 05 `test_code_help` updated to use `--help` since the new command correctly errors on missing args. 33 new tests. 2123 total passing, zero regressions. Schema v13 unchanged — DB-first default means the highest-frequency diagnostic workflow stays free. |
| 125 | Quick diagnosis mode (bike slug + shortcut) | 2026-04-17 | Pure UX sugar on Phase 123's `diagnose quick` — no new substrate, no migration. Extended `src/motodiag/cli/diagnose.py` (+180 LoC) with `_parse_slug` (last-hyphen year split, SLUG_YEAR_MIN=1980 / SLUG_YEAR_MAX=2035 bounds), `_resolve_bike_slug` (4-tier match: exact model → exact make → partial model LIKE → partial make LIKE, deterministic by `created_at, id`), `_list_garage_summary` (UX helper for unknown-slug error). Added `--bike SLUG` option on `diagnose quick` alongside `--vehicle-id`; both-given prefers ID with yellow warning; neither-given errors with hint; unknown slug errors listing the garage. New top-level `motodiag quick "<symptoms>" [--bike | --vehicle-id] ...` via `register_quick(cli_group)` that pulls `diagnose quick` from the registered subgroup and delegates via Click `ctx.invoke()` — single source of truth, no duplication. First agent-delegated phase: Builder-A produced clean code but couldn't self-test (sandboxed agent runtime blocked Python); Architect ran 34 Phase 125 tests as trust-but-verify — all passed. 34 new tests (9 parse + 11 resolve + 5 diagnose-bike + 6 top-level-quick + 3 regression). 2157 total passing, zero regressions. Zero live tokens. |

## Completion Gates

| Gate | Target Phase | Status | Criteria |
|------|-------------|--------|----------|
| Gate 1 | 12 | ✅ | Vehicle → symptoms → session → DTCs → search → diagnose → close |
| Gate 2 | 78 | ✅ | Query any target bike → get DTCs, symptoms, known issues, fixes |
| Gate 3 | 95 | ✅ | Full symptom-to-repair flow with confidence + cost |
| Gate 4 | 108 | ✅ | Media diagnostics: audio + video + multimodal fusion pipeline |
| Gate R | 121 | ✅ | Retrofit: all 10 migrations + 12 new packages + 23 new tables integrate cleanly. 1616 → 2002 tests (+386), zero regressions across 12 phases. One known limitation documented (migration 005 ALTER columns don't drop on rollback). |
| Gate 5 | 133 | 🔲 | Full CLI mechanic workflow: garage → diagnose → code → history → export |
| Gate 6 | 147 | 🔲 | Simulated ECU → adapter → read codes → AI diagnosis (Hardware) |
| Gate 7 | 159 | 🔲 | Fleet + history + prediction end-to-end (Advanced Diagnostics) |
| Gate 8 | 174 | 🔲 | Shop: intake → triage → parts → schedule → repair → invoice |
| Gate 9 | 184 | 🔲 | Full API workflow: auth → vehicle → diagnose → shop → report (hard paywall activates) |
| Gate 10 | 204 | 🔲 | Mobile: film bike → diagnose → share report |
| Gate 11 | 240 | 🔲 | European brand coverage: BMW/Ducati/KTM/Triumph/Aprilia/MV full diagnostic |
| Gate 12 | 250 | 🔲 | Electric motorcycle: BMS + motor controller + regen + thermal analysis |
| Gate 13 | 258 | 🔲 | Scooter / small displacement: CVT + electrical + carb workflow |
| Gate 14 | 272 | 🔲 | Specialized workflows: PPI + tire service + winterization + valve adjust + brake |
| Gate 15 | 292 | 🔲 | Business infrastructure: customer → intake → warranty → invoice → payment → accounting |
| Gate 16 | 302 | 🔲 | Reference data: manual + diagram + torque + tool + video per any bike/repair |
| Gate 17 | 317 | 🔲 | Extended UX: multi-user → voice → photo annotation → Spanish UI → print |
| Gate 18 | 327 | 🔲 | Advanced AI: feedback → learning → prediction → anomaly → customer draft |
| Gate 19 | 342 | 🔲 | Launch readiness: billing → signup → onboarding → migration → paid first diagnostic |
| Gate 20 | 352 | 🔲 | Operational readiness: telemetry + support + backup + multi-location + audit |
