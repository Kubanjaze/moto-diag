# MotoDiag — Full Roadmap

**Project:** moto-diag — AI-Powered Motorcycle Diagnostic Tool (Hybrid: Software + Hardware)
**Repo:** `Kubanjaze/moto-diag`
**Local:** `C:\Users\Kerwyn\PycharmProjects\moto-diag\`
**Started:** 2026-04-15
**Target Fleet:** Harley-Davidson (all years), Honda, Yamaha, Kawasaki, Suzuki, BMW, Ducati, KTM, Triumph, Aprilia, MV Agusta, Electric (Zero/LiveWire/Energica/Damon), Scooters & small-displacement (all classes — sport, standard, cruiser, dual-sport, vintage, adventure, electric, scooter)
**Target Users:** Motorcycle mechanics, shops (solo → multi-location)
**Total Phases:** 352

---

## Track A — Core Infrastructure (Phases 01–12)

Foundation: monorepo scaffold, config, database, base data models.

| Phase | Title | Status | Notes |
|-------|-------|--------|-------|
| 01 | Project scaffold + monorepo setup | ✅ | pyproject.toml, package structure, CLI entry point |
| 02 | Configuration system | ✅ | Profiles, validators, ensure_directories, config CLI |
| 03 | Database schema + SQLite setup | ✅ | 6 tables, WAL mode, connection manager, schema versioning |
| 04 | Vehicle registry data model | ✅ | CRUD operations (add/get/list/update/delete/count) |
| 05 | DTC (Diagnostic Trouble Code) schema + loader | ✅ | DTC repo, JSON loader, 40 codes, code CLI functional |
| 06 | Symptom taxonomy + data model | ✅ | 40 symptoms, 12+ categories, related_systems linking |
| 07 | Diagnostic session model | ✅ | 9 functions, full lifecycle, accumulation, 16 tests |
| 08 | Knowledge base schema | ✅ | Issues repo, 10 Harley known issues with forum tips, loader |
| 09 | Search + query engine | ✅ | Unified search across 5 stores, search CLI command |
| 10 | Logging + audit trail | ✅ | Structured logging, session audit trail, file handler |
| 11 | Test framework + fixtures | ✅ | Shared conftest.py, populated_db, 136/136 regression pass |
| 12 | Gate 1 — Core infrastructure integration test | ✅ | Full workflow E2E, db init CLI, 140/140 pass, **GATE PASSED** |

## Track B — Vehicle Knowledge Base (Phases 13–62)

Deep domain knowledge for target fleet. Each phase populates the knowledge base with real diagnostic data — common failures, DTCs, symptoms, repair procedures.

### Harley-Davidson (Phases 13–22)

| Phase | Title | Status | Notes |
|-------|-------|--------|-------|
| 13 | Harley Evo Big Twin (1984–1999) | ✅ | 10 issues: base gasket, starter clutch, CV carb, ignition, wet sumping |
| 14 | Harley Twin Cam 88/88B (1999–2006) | ✅ | 10 issues: tick of death, compensator, sumping, cam bearing |
| 15 | Harley Twin Cam 96/103/110 (2007–2017) | ✅ | 10 issues: ABS, TBW, ECM tuning, fuel pump, wheel bearing |
| 16 | Harley Milwaukee-Eight (2017+) | ✅ | 10 issues: oil cooler, infotainment, intake carbon, TBW |
| 17 | Harley Sportster Evo (1986–2003) | ✅ | 10 issues: shared oil, clutch cable, carb, starter, kickstand |
| 18 | Harley Sportster Rubber-Mount (2004–2021) | ✅ | 10 issues: fuel pump, stator connector, fork seals, brake caliper |
| 19 | Harley V-Rod / VRSC (2002–2017) | ✅ | 10 issues: coolant, hydraulic clutch, fuel cell, alternator, frame, ECU, belt tensioner, starter |
| 20 | Harley Revolution Max (2021+) | ✅ | 10 issues: TFT freeze, ride-by-wire, water pump, chain drive, battery drain, ABS/TC |
| 21 | Harley electrical systems (all eras) | ✅ | 10 issues: regulator, stator, solenoid, grounds, CAN bus, ignition switch, TSSM, wiring, battery types, lighting |
| 22 | Harley common cross-era issues | ✅ | 10 issues: compensator, intake seals, heat soak, primary leak, clutch, shocks, tire wear, ethanol |

### Honda (Phases 23–34)

| Phase | Title | Status | Notes |
|-------|-------|--------|-------|
| 23 | Honda CBR supersport: 900RR/929RR/954RR (1992–2003) | ✅ | 10 issues: reg/rec, CCT, HISS, carb sync, fork seals, starter clutch, PGM-FI |
| 24 | Honda CBR600: F2/F3/F4/F4i (1991–2006) | ✅ | 10 issues: reg/rec, carbs, CCT, F4i injectors, clutch cable, radiator fan, chain |
| 25 | Honda CBR600RR (2003–2024) | ✅ | 10 issues: HESD, reg/rec, C-ABS, CCT, fuel pump, valve clearance, stator, subframe |
| 26 | Honda CBR1000RR / RR-R (2004+) | ✅ | 10 issues: reg/rec, HSTC, CCT, HESD, quickshifter, exhaust servo, brakes, winglets |
| 27 | Honda cruisers: Shadow 600/750/1100, VTX 1300/1800 | ✅ | 10 issues: reg/rec, shaft drive, carbs, VTX starter, fuel pump, clutch drag, exhaust |
| 28 | Honda Rebel 250/300/500/1100 | ✅ | 10 issues: carb 250, reg/rec, DCT jerky, chain 300/500, battery drain, drum brake |
| 29 | Honda standards: CB750/919, CB1000R, Hornet | ✅ | 10 issues: reg/rec, CCT, ride-by-wire, carbs, chain, vibes, tank rust, rear shock |
| 30 | Honda V4: VFR800, RC51/RVT1000R, VFR1200F | ✅ | 10 issues: VTEC, reg/rec, RC51 TPS, gear cam noise, CBS, overheating, fuel pump relay |
| 31 | Honda dual-sport: XR650L, CRF250L/300L, Africa Twin | ✅ | 10 issues: XR650L jetting/valves, CRF power, AT DCT off-road, radiator, water, chain |
| 32 | Honda vintage air-cooled: CB550/650/750, Nighthawk | ✅ | 10 issues: points ignition, carb rebuild, charging, cam chain, petcock, brakes, wiring |
| 33 | Honda electrical systems + PGM-FI | ✅ | 10 issues: blink codes, HISS, reg/rec, stator, starter relay, FI sensors, grounds, fuses |
| 34 | Honda common cross-model issues | ✅ | 10 issues: CCT, starter clutch, coolant hoses, valves, chain, brake fluid, throttle, forks, tires |

### Yamaha (Phases 35–44)

| Phase | Title | Status | Notes |
|-------|-------|--------|-------|
| 35 | Yamaha YZF-R1 (1998+) | ✅ | 10 issues: EXUP, stator, crossplane sound, YCC-T, YCC-I, fuel pump, CCT, R1M electronics |
| 36 | Yamaha YZF-R6 (1999–2020) | ✅ | 10 issues: CCT (critical), stator, valve clearance, EXUP, underseat heat, fuel pump, throttle sync, coolant, immobilizer, electronics |
| 37 | Yamaha YZF-R7 + YZF600R Thundercat (1996–2007, 2021+) | ✅ | 10 issues: Thundercat carbs/petcock/charging/chain/forks + R7 clutch/suspension/QS/heat/lean spot |
| 38 | Yamaha FZ/MT naked: FZ6/FZ8/FZ-09/FZ-10, MT-03/07/09/10 | ✅ | 10 issues: MT-09 throttle/valves/fuel, MT-07 charging/chain, FZ6 heat, MT-10 electronics, MT-03 drops, radiator |
| 39 | Yamaha cruisers: V-Star 250/650/950/1100/1300, Bolt | ✅ | 10 issues: V-Star carbs/petcock/stator/shaft drive/starter clutch/ISC + Bolt heat/belt + AIS |
| 40 | Yamaha VMAX (1985–2020) | ✅ | 10 issues: Gen 1 V-Boost/carbs/charging/shaft drive/tank + Gen 2 FI/cooling/brakes/electronics/exhaust |
| 41 | Yamaha dual-sport: WR250R/X, XT250, Ténéré 700 | ✅ | 10 issues: WR250R stator/suspension/cold start + XT250 carb/chain/valves + Tenere wind/crash/lean/shock |
| 42 | Yamaha vintage: XS650, RD350/400, SR400/500 | ✅ | 10 issues: XS650 points/charging/oil/cam chain + RD Autolube/chambers/reeds + SR kickstart/carb/valves |
| 43 | Yamaha electrical systems + diagnostics | ✅ | 10 issues: self-diagnostic/stator connector/MOSFET/grounds/harness/fuses/immobilizer/LED/batteries/Woolich |
| 44 | Yamaha common cross-model issues | ✅ | 10 issues: CCT/ethanol/valves/EXUP/brakes/chain/coolant/tires/winterization/exhaust mods |

### Kawasaki (Phases 45–56)

| Phase | Title | Status | Notes |
|-------|-------|--------|-------|
| 45 | Kawasaki Ninja 250/300/400 (1988+) | ✅ | 10 issues: carbs/drops/charging/fuel pump/chain/valves/ABS/coolant/header crack/oil neglect |
| 46 | Kawasaki ZX-6R (1995+) | ✅ | 10 issues: 636/599 confusion, stator, CCT, KLEEN, valves, fuel pump, cooling, KTRC, forks, QS |
| 47 | Kawasaki ZX-7R / ZX-7RR (1996–2003) | ✅ | 10 issues: carbs/fuel system/charging/FCR carbs/CCT/wiring/rubber/suspension/brakes/ignition |
| 48 | Kawasaki ZX-9R (1998–2003) | ✅ | 10 issues: carbs/early FI/charging/CCT/cooling/fuel pump/forks/brakes/valves/ignition switch |
| 49 | Kawasaki ZX-10R (2004+) | ✅ | 10 issues: headshake/charging/IMU electronics/CCT/fuel pump/valves/KLEEN/crash/QS/cooling |
| 50 | Kawasaki ZX-12R / ZX-14R (2000–2020) | ✅ | 10 issues: ram air/charging/consumables/FI tuning/ABS-KTRC/chain/CCT/cooling/suspension/valves |
| 51 | Kawasaki Ninja H2 / H2R (2015+) | ✅ | 10 issues: supercharger/cooling/electronics/paint/chain/oil/fuel/H2 SX/brakes/valves |
| 52 | Kawasaki Z naked: Z400/Z650/Z750/Z800/Z900/Z1000, Z H2 | ✅ | 10 issues: radiator/throttle/connectors/charging/Z H2 heat/chain/KTRC/CCT/beginner/headlights |
| 53 | Kawasaki Vulcan cruisers: 500/750/800/900/1500/1600/1700/2000 | ✅ | 10 issues: carbs/ISC surge/shaft drive/starter/Vulcan 2000/belt/heat/1700 EFI/Vulcan 500/exhaust mods |
| 54 | Kawasaki dual-sport: KLR650, KLX250/300, Versys 650/1000 | ✅ | 10 issues: doohickey/overheating/FI lean surge/valves/suspension/TBW/subframe/jetting/chain/stator |
| 55 | Kawasaki vintage: KZ550/650/750/1000/1100, GPz series | ✅ | 10 issues: CCT/charging/carb rebuild/fuel system/points ignition/forks/oil leaks/brakes/wiring/chain |
| 56 | Kawasaki electrical systems + FI dealer mode | ✅ | 10 issues: dealer mode/stator/KLEEN/KIPASS/LED/grounds/starter/parasitic draw/KTRC-KIBS/connectors |

### Suzuki (Phases 57–67)

| Phase | Title | Status | Notes |
|-------|-------|--------|-------|
| 57 | Suzuki GSX-R600 (1997+) | ✅ | 10 issues: stator/CCT/PAIR/fuel pump/forks/valves/cooling/S-DMS-TC/brakes/clutch |
| 58 | Suzuki GSX-R750 (1996+) | ✅ | 10 issues: 2nd gear/stator/CCT/fuel pump/SRAD coolant/linkage/TPS/chain/master cyl/headstock |
| 59 | Suzuki GSX-R1000 (2001+) | ✅ | 10 issues: K5-K8 case cracking/stator/IMU-TCS/CCT/SET servo/fuel relay/valves/QS/cooling/bearings |
| 60 | Suzuki GSX-R1100 (1986–1998) | ✅ | 10 issues: air-oil overheating/carbs/charging/CCT/suspension/CDI ignition/petcock/brakes/wiring/chain |
| 61 | Suzuki SV650/1000 + Gladius (1999+) | ✅ | 10 issues: reg-rec/carb tuning/CCT/clutch/fuel pump/suspension/SV1000 STPS/Gladius/forks/exhaust |
| 62 | Suzuki V-Strom 650/1000/1050 (2002+) | ✅ | 10 issues: lean surge/CCT/windscreen/suspension/1050 electronics/charging/chain/valves/side stand/ABS |
| 63 | Suzuki Bandit 600/1200/1250 (1995–2012) | ✅ | 10 issues: overheating/carbs/FI/charging/CCT/suspension/petcock/brakes/chain/wiring |
| 64 | Suzuki GSX-S750/1000 + Katana (2015+) | ✅ | 10 issues: TBW/CCT/Katana heat/charging/fuel relay/chain/mirrors/valves/TC-ABS/forks |
| 65 | Suzuki cruisers: Intruder/Boulevard series | ✅ | 10 issues: carbs/FI surge/shaft drive/M109R clutch/starter clutch/charging/heat/fuel pump/exhaust/brakes |
| 66 | Suzuki dual-sport: DR-Z400S/SM, DR650SE | ✅ | 10 issues: jetting/valves/SM brakes/DR650 carb-oil/chain/electrical/suspension/kick start/DR650 starter |
| 67 | Suzuki vintage: GS550/750/850/1000/1100, Katana 1100 | ✅ | 10 issues: CCT/charging/carbs/ignition/fuel system/suspension/brakes/oil leaks/wiring/chain |

### Cross-Platform Systems (Phases 68–78)

| Phase | Title | Status | Notes |
|-------|-------|--------|-------|
| 68 | Suzuki electrical systems + FI dealer mode | ✅ | 10 issues: C-mode/stator/PAIR/grounds/starter/parasitic draw/TC-ABS/LED/connectors/FI relay |
| 69 | Suzuki common cross-model issues | ✅ | 10 issues: stator connector fire risk/CCT/fuel relay/PAIR/coolant/valves/chain/brakes/forks/exhaust |
| 70 | Carburetor troubleshooting (cross-platform) | ✅ | 10 issues: CV diaphragm/pilot jet/float height/sync/enrichment/vacuum leaks/pilot screw/overflow/rejetting |
| 71 | Fuel injection troubleshooting (cross-platform) | ✅ | 10 issues: fuel pump/TPS/MAP/O2/ECT/injectors/ISC/throttle body/fuel pressure/ECU reset |
| 72 | Charging system diagnostics (cross-platform) | ✅ | 10 issues: stator/reg-rec/connector/rotor/batteries/parasitic draw/3-step test/grounds/accessories |
| 73 | Starting system diagnostics (cross-platform) | ✅ | 10 issues: relay/motor/sprag/clutch switch/kickstand/kill switch/cables/tip-over/neutral/compression |
| 74 | Ignition system diagnostics (cross-platform) | ✅ | 10 issues: plugs/coils/CDI/pickup/wires/points/timing/kill switch/misfires/COP |
| 75 | Cooling system diagnostics (cross-platform) | ✅ | 10 issues: thermostat/fan/coolant/water pump/radiator/air-cooled/hoses/head gasket/cap/track coolant |
| 76 | Brake system diagnostics (cross-platform) | ✅ | 10 issues: fluid/calipers/pads/rotors/master cyl/stainless lines/ABS sensors/ABS bleeding/drum/bolt torque |
| 77 | Drivetrain diagnostics (cross-platform) | ✅ | 10 issues: chain/sprockets/lube/belt/shaft/clutch/cable-hydraulic/transmission/countershaft seal/alignment |
| 78 | Gate 2 — Vehicle knowledge base integration test | ✅ | 21 integration tests, 650+ issues, all 5 makes verified, **GATE 2 PASSED** |

## Track C — AI Diagnostic Engine (Phases 79–95)

Claude API integration, prompt engineering, diagnostic reasoning.

| Phase | Title | Status | Notes |
|-------|-------|--------|-------|
| 79 | Claude API integration + base client | ✅ | DiagnosticClient, model selection, token tracking, 32 tests |
| 80 | Symptom analysis prompt engineering | ✅ | SymptomAnalyzer, categorization, urgency, two-pass approach, 28 tests |
| 81 | Fault code interpretation prompts | ✅ | FaultCodeInterpreter, 8 DTC formats, 51 local codes, 36 tests |
| 82 | Multi-step diagnostic workflows | ✅ | DiagnosticWorkflow, 3 templates (no-start/charging/overheating), 26 tests |
| 83 | Confidence scoring | ✅ | ConfidenceScore, 8 evidence types, normalization, ranking, 23 tests |
| 84 | Repair procedure generator | ✅ | RepairProcedureGenerator, SkillLevel assessment, 41 tests |
| 85 | Parts + tools recommendation | ✅ | PartsRecommender, cross-refs, 13+ brands, 35 tests |
| 86 | Cost estimation | ✅ | CostEstimator, ShopType comparison, format_estimate, 34 tests |
| 87 | Safety warnings + critical alerts | ✅ | SafetyChecker, 18 rules, 12 repair keywords, 37 tests |
| 88 | Diagnostic history + learning | ✅ | DiagnosticHistory, add/get/search/statistics, find_similar, 45 tests |
| 89 | Similar case retrieval | ✅ | CaseRetriever, Jaccard similarity, vehicle/year matching, 32 tests |
| 90 | Multi-symptom correlation | ✅ | SymptomCorrelator, 15+ predefined rules, partial match, 38 tests |
| 91 | Intermittent fault analysis | ✅ | IntermittentAnalyzer, 10+ patterns, condition extraction, 43 tests |
| 92 | Wiring diagram reference | ✅ | 5 circuit references, wire colors, test points, 29 tests |
| 93 | Torque specs + service data lookup | ✅ | 20 torque specs, 14 intervals, 8 clearances, 39 tests |
| 94 | AI evaluation + accuracy tracking | ✅ | EvaluationTracker, ADR-005 scorecard, model comparison, 21 tests |
| 95 | Gate 3 — AI diagnostic engine integration test | ✅ | 39 integration tests, 16 modules, 1163 total tests, **GATE 3 PASSED** |

## Track C2 — Media Diagnostic Intelligence (Phases 96–108)

Video and audio analysis for hands-free diagnostics. A mechanic films a bike starting/running/dying — the AI analyzes engine sound, visible symptoms, and behavior to suggest diagnostic paths.

| Phase | Title | Status | Notes |
|-------|-------|--------|-------|
| 96 | Audio capture + preprocessing | ✅ | AudioPreprocessor, WAV file management, synthetic generators, 36 tests |
| 97 | Audio spectrogram analysis | ✅ | Pure Python DFT, 6 motorcycle frequency bands, 30 tests |
| 98 | Engine sound signature database | ✅ | 7 engine types, RPM-to-firing-frequency, profile matching, 25 tests |
| 99 | Audio anomaly detection | ✅ | 9 anomaly types (knock, misfire, valve tick, etc.), 29 tests |
| 100 | Video frame extraction | ✅ | Frame extraction plan, keyframes, timestamps, 34 tests |
| 101 | Visual symptom analysis (Claude Vision) | ✅ | Vision prompts, smoke/fluid color guides, 34 tests |
| 102 | Multimodal fusion | ✅ | Weighted evidence, conflict detection, 30 tests |
| 103 | Comparative audio analysis | ✅ | Before/after, improvement scoring, 30 tests |
| 104 | Real-time audio monitoring | ✅ | Session lifecycle, RPM estimation, alerts, 26 tests |
| 105 | Video annotation + timestamps | ✅ | Timestamped annotations, timeline, auto-annotate, 27 tests |
| 106 | Media-enhanced diagnostic reports | ✅ | Reports with media attachments, text formatting, 26 tests |
| 107 | AI audio coaching | ✅ | 5 capture protocols, quality evaluation, 30 tests |
| 108 | Gate 4 — Media diagnostics integration test | ✅ | 24 integration tests, 12 modules, 1575 total, **GATE 4 PASSED** |

## Track D — CLI + User Experience (Phases 109, 122–133)

The mechanic's daily driver interface. Phase 109 delivered the foundation; remaining phases shifted to 122-133 after Retrofit track insertion.

| Phase | Title | Status | Notes |
|-------|-------|--------|-------|
| 109 | CLI foundation + command structure | ✅ | Click CLI, subcommands, 3-tier subscription system ($19/$99/$299), tier command, 41 tests |
| 122 | Vehicle garage management | 🔲 | Add/edit/list/remove vehicles from personal garage (was 110) |
| 123 | Interactive diagnostic session | 🔲 | Start session → describe problem → guided Q&A → diagnosis (was 111) |
| 124 | Fault code lookup command | 🔲 | `motodiag code P0115` → plain-English explanation + fix (was 112) |
| 125 | Quick diagnosis mode | 🔲 | One-shot: `motodiag diagnose "won't start when cold" --bike sportster-2001` (was 113) |
| 126 | Diagnostic report output | 🔲 | Formatted terminal report + save to file (txt/json) (was 114) |
| 127 | Session history browser | 🔲 | Browse past diagnostic sessions, re-open, annotate (was 115) |
| 128 | Knowledge base browser | 🔲 | Browse known issues by make/model, search, filter (was 116) |
| 129 | Rich terminal UI (tables, colors, progress) | 🔲 | Pretty output with rich/textual (was 117) |
| 130 | Shell completions + shortcuts | 🔲 | Tab completion, aliases, power-user features (was 118) |
| 131 | Offline mode | 🔲 | Cache AI responses, work without internet for code lookups (was 119) |
| 132 | Export + sharing | 🔲 | Export diagnosis to PDF/HTML, share with customer (was 120) |
| 133 | Gate 5 — CLI integration test | 🔲 | Full mechanic workflow through CLI (was 121) |

## Retrofit Track — Codebase Expansion Preparation (Phases 110–121)

Before any new tracks (Tracks K+) can build, the existing codebase needs refactoring to accommodate expanded scope: European brands, electric bikes, CRM, auth, workflows, i18n, reference data, business infrastructure. This is a non-negotiable prerequisite inserted between Track C2 and the remainder of Track D.

| Phase | Title | Status | Notes |
|-------|-------|--------|-------|
| 110 | Vehicle registry + protocol taxonomy expansion | ✅ | Migration framework (reusable), PowertrainType/EngineType/BatteryChemistry enums, European CAN protocols, 35 tests, 1651 total |
| 111 | Knowledge base schema expansion | ✅ | Migration 004, DTCCategory enum (20), dtc_category_meta table, 6 OEM classifiers (BMW/Ducati/KTM/Triumph/Aprilia/Electric HV), 43 tests, 1694 total |
| 112 | User/auth layer introduction | ✅ | Migration 005, auth/ package (5 models, users_repo, roles_repo), 4 roles + 12 permissions + 31 mappings seeded, system user (id=1) owns pre-retrofit data, 40 tests, 1734 total |
| 113 | Customer/CRM foundation | ✅ | Migration 006, crm/ package (Customer + CustomerBike models, 14 repo functions), customers + customer_bikes tables, ownership history with transfer_ownership(), unassigned placeholder (id=1) owns pre-retrofit vehicles, 35 tests, 1769 total |
| 114 | Workflow template substrate | ✅ | Migration 007, workflows/ package (WorkflowCategory enum 13 members + 2 models + 10 repo functions), workflow_templates + checklist_items tables, 2 seed templates + 9 checklist items, 32 tests, 1801 total |
| 115 | i18n substrate | ✅ | Migration 008 + i18n/ package (Locale enum 7 codes, t() with locale→en→key fallback, string interpolation, bulk import, completeness reporter). 45 English strings across 4 namespaces. Schema v7→v8. 40 tests, 1841 total |
| 116 | Feedback/learning hooks | ✅ | Migration 009 + feedback/ package (FeedbackOutcome enum, OverrideField enum, DiagnosticFeedback + SessionOverride models, 8 repo functions, FeedbackReader read-only hook). diagnostic_feedback + session_overrides tables with FK CASCADE. Schema v8→v9. 26 tests, 1867 total |
| 117 | Reference data tables | ✅ | Migration 010 + reference/ package (4 enums, 4 models, 4 repo modules × 5 CRUD = 20 functions). 4 new tables with 8 indexes, year-range filter reused from known_issues pattern. Schema v9→v10. 28 tests, 1895 total |
| 118 | Billing/invoicing/inventory/scheduling substrate | 🔲 | New packages: billing, accounting, inventory, scheduling. Tables: appointments, payments, invoices, invoice_line_items, inventory_items, vendors, recalls, warranties |
| 119 | Media annotation layer | 🔲 | Extend `media/` with photo_annotations table + annotation model (shapes, arrows, circles, text) |
| 120 | Engine sound signature library expansion | 🔲 | Add electric motor, Ducati L-twin dry clutch, BMW boxer, KTM LC8, Triumph triple signatures |
| 121 | Gate R — Retrofit integration test | 🔲 | All existing tests pass. Schemas migrate cleanly. No breaking CLI changes. New packages import cleanly. Full regression + migration verification |

## Track E — Hardware Interface (Phases 134–147)

OBD adapter integration, live sensor data, ECU communication. Shifted from 122-135 due to Retrofit track insertion.

| Phase | Title | Status | Notes |
|-------|-------|--------|-------|
| 134 | OBD protocol abstraction layer | 🔲 | Interface definition for all protocol adapters (was 122) |
| 135 | ELM327 adapter communication | 🔲 | Serial/Bluetooth ELM327 command protocol (was 123) |
| 136 | CAN bus protocol implementation | 🔲 | ISO 15765 — for 2011+ Harleys, modern bikes (was 124) |
| 137 | K-line/KWP2000 protocol implementation | 🔲 | ISO 14230 — for 90s/2000s Japanese bikes (was 125) |
| 138 | J1850 protocol implementation | 🔲 | For older Harleys (pre-2011) (was 126) |
| 139 | ECU auto-detection + handshake | 🔲 | Detect protocol, establish session, identify ECU (was 127) |
| 140 | Fault code read/clear operations | 🔲 | Read DTCs from ECU, clear after repair (was 128) |
| 141 | Live sensor data streaming | 🔲 | RPM, TPS, coolant temp, battery V, O2 sensor (was 129) |
| 142 | Data logging + recording | 🔲 | Record sensor sessions, replay, analyze (was 130) |
| 143 | Real-time terminal dashboard | 🔲 | Live gauges/graphs in terminal (textual) (was 131) |
| 144 | Hardware simulator | 🔲 | Mock adapter for testing without physical hardware (was 132) |
| 145 | Adapter compatibility database | 🔲 | Which adapters work with which bikes (was 133) |
| 146 | Connection troubleshooting + recovery | 🔲 | Handle disconnects, timeouts, protocol errors (was 134) |
| 147 | Gate 6 — Hardware integration test | 🔲 | Simulated ECU → adapter → read codes → AI diagnosis (was 135) |

## Track F — Advanced Diagnostics (Phases 148–159)

Power features for experienced mechanics. Shifted from 136-147 due to Retrofit track insertion.

| Phase | Title | Status | Notes |
|-------|-------|--------|-------|
| 148 | Predictive maintenance | 🔲 | Mileage/age-based failure prediction per model (was 136) |
| 149 | Wear pattern analysis | 🔲 | Correlate symptoms with known wear patterns (was 137) |
| 150 | Fleet management | 🔲 | Manage multiple bikes, shop inventory (was 138) |
| 151 | Maintenance scheduling | 🔲 | Service intervals, upcoming maintenance alerts (was 139) |
| 152 | Service history tracking | 🔲 | Full repair history per vehicle (was 140) |
| 153 | Parts cross-reference | 🔲 | OEM ↔ aftermarket part number lookup (was 141) |
| 154 | Technical service bulletin (TSB) database | 🔲 | Known manufacturer issues + fixes (was 142) |
| 155 | Recall information | 🔲 | NHTSA recall lookup by VIN/model (was 143) |
| 156 | Comparative diagnostics | 🔲 | Same model, different bikes — spot anomalies (was 144) |
| 157 | Performance baselining | 🔲 | Establish "healthy" sensor baselines per model (was 145) |
| 158 | Degradation tracking | 🔲 | Track sensor drift over time (was 146) |
| 159 | Gate 7 — Advanced diagnostics integration test | 🔲 | Fleet + history + prediction end-to-end (was 147) |

## Track G — Shop Management + Optimization (Phases 160–174)

Shop-level features: log bikes in your shop, track issues across the fleet, triage what to fix first, auto-generate parts lists, optimize workflow. Shifted from 148-162 due to Retrofit track insertion.

| Phase | Title | Status | Notes |
|-------|-------|--------|-------|
| 160 | Shop profile + multi-bike intake | 🔲 | Register shop, log incoming bikes with customer info (was 148) |
| 161 | Work order system | 🔲 | Create/assign/track work orders per bike (was 149) |
| 162 | Issue logging + categorization | 🔲 | Log reported issues per bike, categorize by system/severity (was 150) |
| 163 | Repair priority scoring | 🔲 | AI-ranked priority: safety > ridability > cosmetic, weighted by wait time (was 151) |
| 164 | Automated triage queue | 🔲 | "What to fix first" — sorted by priority, parts availability, bay time (was 152) |
| 165 | Parts needed aggregation | 🔲 | Cross all active work orders → consolidated parts list (was 153) |
| 166 | Parts sourcing + cost optimization | 🔲 | OEM vs aftermarket vs used, vendor price comparison (was 154) |
| 167 | Labor time estimation | 🔲 | AI-estimated wrench time per job, based on model + issue (was 155) |
| 168 | Bay/lift scheduling | 🔲 | Schedule repairs across available bays/lifts, minimize idle time (was 156) |
| 169 | Revenue tracking + invoicing | 🔲 | Parts cost + labor = invoice, track revenue per bike/job (was 157) |
| 170 | Customer communication | 🔲 | Status updates, approval requests, completion notifications (was 158) |
| 171 | Shop analytics dashboard | 🔲 | Revenue, throughput, avg repair time, common issues (was 159) |
| 172 | Multi-mechanic assignment | 🔲 | Assign jobs to mechanics, track who worked on what (was 160) |
| 173 | Workflow automation rules | 🔲 | "If safety issue → priority 1", "if parts > $500 → customer approval" (was 161) |
| 174 | Gate 8 — Shop management integration test | 🔲 | Intake → triage → parts → schedule → repair → invoice flow (was 162) |

## Track H — API + Web Layer (Phases 175–184)

REST API for future mobile app / web dashboard. Paywall enforcement flips to HARD mode here. Shifted from 163-172 due to Retrofit track insertion.

| Phase | Title | Status | Notes |
|-------|-------|--------|-------|
| 175 | FastAPI foundation + project structure | 🔲 | API scaffold, CORS, error handling (was 163) |
| 176 | Auth + API keys | 🔲 | API key management, rate limiting, Stripe integration, hard paywall enforcement (was 164) |
| 177 | Vehicle endpoints | 🔲 | CRUD for garage vehicles (was 165) |
| 178 | Diagnostic session endpoints | 🔲 | Start/update/complete diagnostic sessions (was 166) |
| 179 | Knowledge base endpoints | 🔲 | Search DTCs, symptoms, known issues (was 167) |
| 180 | Shop management endpoints | 🔲 | Work orders, triage, parts, scheduling (was 168) |
| 181 | WebSocket live data | 🔲 | Stream sensor data to web clients (was 169) |
| 182 | Report generation endpoints | 🔲 | Generate PDF/HTML diagnostic reports + invoices (was 170) |
| 183 | API documentation + OpenAPI spec | 🔲 | Auto-generated docs, example requests (was 171) |
| 184 | Gate 9 — API integration test | 🔲 | Full API workflow: auth → vehicle → diagnose → shop → report (was 172) |

## Track I — Mobile App (iOS + Android) (Phases 185–204)

**Distribution:** iOS App Store + Google Play Store (paid app or freemium)
**Framework:** React Native (single codebase → both platforms, broad device support)

Full-featured mobile app for mechanics in the field. Same capabilities as desktop — not a stripped-down version. Designed for dirty hands, loud shops, and outdoor use.

### Device Support Requirements
- **iOS:** iPhone 8 and later (iOS 15+) — covers ~99% of active iPhones
- **Android:** Android 8.0 (Oreo) and later — covers old Samsungs, budget phones, tablets
- **Screen sizes:** 4.7" to 12.9" — phone and tablet layouts
- **Orientation:** portrait default, landscape for live sensor dashboard
- **Performance:** must run smoothly on budget Android devices ($100-200 phones)

### Design Principles (Mobile)
- **Big touch targets** — fat fingers in gloves, greasy hands, minimum 48dp tap areas
- **Voice input** — describe symptoms by talking, not typing
- **Camera + video** — film running bike, photograph parts, scan VINs
- **Offline-first** — works without internet, syncs when connected
- **Bluetooth OBD** — connect to bike adapter directly from phone
- **Low bandwidth** — works on 3G/LTE, not just WiFi — compressed API responses

| Phase | Title | Status | Notes |
|-------|-------|--------|-------|
| 185 | Mobile architecture decision (React Native vs Flutter) | 🔲 | Evaluate framework, decide on shared codebase approach (was 173) |
| 186 | Mobile project scaffold + CI/CD | 🔲 | iOS + Android build pipeline, TestFlight / Play Store beta (was 174) |
| 187 | Auth + API client library | 🔲 | Secure token storage, API wrapper, offline token refresh (was 175) |
| 188 | Vehicle garage screen | 🔲 | Add/edit/view bikes, VIN scanner (camera), big touch targets (was 176) |
| 189 | DTC code lookup screen | 🔲 | Search by code or text, voice input, offline DTC database (was 177) |
| 190 | Interactive diagnostic session (mobile) | 🔲 | Guided Q&A with large buttons, voice input for symptoms (was 178) |
| 191 | Video diagnostic capture (mobile) | 🔲 | Film bike running, auto-extract audio + key frames → AI analysis (was 179) |
| 192 | Diagnostic report viewer | 🔲 | View/share diagnosis, PDF export, AirDrop/Share Sheet (was 180) |
| 193 | Shop dashboard (mobile) | 🔲 | Work order list, triage queue, tap to assign/update (was 181) |
| 194 | Camera + photo integration | 🔲 | Photograph issues, attach to work orders, before/after (was 182) |
| 195 | Voice input for symptom description | 🔲 | Speech-to-text, structured symptom extraction from voice (was 183) |
| 196 | Bluetooth OBD adapter connection | 🔲 | Scan for adapters, pair, connect, protocol handshake (was 184) |
| 197 | Live sensor data dashboard (mobile) | 🔲 | Real-time gauges, swipe between sensors, landscape mode (was 185) |
| 198 | Offline mode + local database | 🔲 | SQLite on device, full DTC database cached, queue API calls (was 186) |
| 199 | Push notifications | 🔲 | Work order updates, diagnostic results, parts arrival alerts (was 187) |
| 200 | Customer-facing share view | 🔲 | Simplified report for bike owners, text/email share (was 188) |
| 201 | Parts ordering from mobile | 🔲 | Browse needed parts, add to cart, order from phone (was 189) |
| 202 | Mechanic time tracking | 🔲 | Clock in/out per job, timer for labor billing (was 190) |
| 203 | Dark mode + shop-friendly UI | 🔲 | High contrast, readable in sunlight and under shop lights (was 191) |
| 204 | Gate 10 — Mobile integration test | 🔲 | Full flow: film bike → diagnose → share report (was 192) |

## Track J — Ship + Scale (Phases 205–210)

Polish, package, launch the core product (pre-expansion). Shifted from 193-198 due to Retrofit track insertion.

| Phase | Title | Status | Notes |
|-------|-------|--------|-------|
| 205 | End-to-end integration testing | 🔲 | All tracks working together (desktop + mobile) (was 193) |
| 206 | Performance optimization | 🔲 | Query speed, API response time, memory usage (was 194) |
| 207 | Security audit | 🔲 | API keys, input validation, SQL injection prevention (was 195) |
| 208 | Documentation + user guide | 🔲 | README, usage guide, mechanic quickstart, app store listing (was 196) |
| 209 | Packaging + distribution | 🔲 | pip install, standalone binary, Docker, App Store, Play Store (was 197) |
| 210 | Launch readiness + full integration | 🔲 | Everything together — the complete MotoDiag platform (was 198) |

---

# Expansion Tracks (Phases 211–352)

The following tracks extend MotoDiag beyond the original 210-phase core product into a complete commercial platform. Planning-only; these phases unlock once the core platform has launched and generated customer feedback to prioritize expansion.

## Track K — European Brand Coverage (Phases 211–240)

European motorcycle brands — BMW, Ducati, KTM, Triumph, Aprilia, MV Agusta. Each brand gets dedicated phases for its model lines, electrical systems, and cross-model common issues, matching the pattern established in Tracks B.

### BMW (Phases 211–215)

| Phase | Title | Status | Notes |
|-------|-------|--------|-------|
| 211 | BMW R-series boxer twin (1969+) | 🔲 | R nineT, R1200GS/R1250GS, R1200/1250RT, oilhead/hexhead/wethead generations |
| 212 | BMW GS adventure line | 🔲 | F650GS/F800GS/F750GS/F850GS/F900GS, ADV accessories, paralever final drive |
| 213 | BMW S1000RR / S1000R / S1000XR | 🔲 | Inline-4 superbike line, electronics, shift assist pro |
| 214 | BMW K-series touring | 🔲 | K1200RS, K1200GT, K1300S, K1600GT/GTL inline-6, Duolever front |
| 215 | BMW electrical + FI dealer mode | 🔲 | ZFE (Central Electronics), GS-911 diagnostic tool integration, BMW-specific DTC format |

### Ducati (Phases 216–220)

| Phase | Title | Status | Notes |
|-------|-------|--------|-------|
| 216 | Ducati Monster / Streetfighter (1993+) | 🔲 | Air-cooled, liquid-cooled generations, trellis frame, Testastretta evolution |
| 217 | Ducati Panigale superbike line | 🔲 | 899/959/1199/1299/V4, Superquadro, V4 engine, Ohlins electronic suspension |
| 218 | Ducati Multistrada | 🔲 | 1200/1260/V4, adventure-touring, skyhook suspension, Ducati Safety Pack |
| 219 | Ducati desmodromic valve service | 🔲 | Desmo 10K-18K mile service intervals, shim-over-bucket opener/closer, cost-intensive |
| 220 | Ducati electrical + FI | 🔲 | Magneti Marelli ECU, DDA+ (data analyzer), Ducati-specific CAN format, DDS diagnostic tool |

### KTM (Phases 221–225)

| Phase | Title | Status | Notes |
|-------|-------|--------|-------|
| 221 | KTM 1290 Super Duke / Super Adventure | 🔲 | LC8 V-twin, R/GT variants, cornering ABS, MSC |
| 222 | KTM Duke naked line (125/390/790/890) | 🔲 | Single + parallel twin, beginner (125/390) through advanced (790/890) |
| 223 | KTM enduro / adventure (EXC/690/450) | 🔲 | Off-road single-cylinder race bikes, hard enduro, 450/500 EXC, 690 Enduro R |
| 224 | KTM LC8 V-twin common issues | 🔲 | Cam chain tensioner, electric start issues, valve clearance intervals |
| 225 | KTM electrical + Keihin FI | 🔲 | Keihin ECU, Tuneboy, PowerParts cross-platform |

### Triumph (Phases 226–230)

| Phase | Title | Status | Notes |
|-------|-------|--------|-------|
| 226 | Triumph Bonneville / T100 / Speed Twin | 🔲 | Parallel twin modern classics, 865/900/1200cc, classic styling modern internals |
| 227 | Triumph Tiger adventure (800/900/1200) | 🔲 | Triple-cylinder adventure, XC/XR/XRt/Rally variants, Ohlins on top trim |
| 228 | Triumph Street Triple / Speed Triple | 🔲 | Triple naked sport, 675/765/1050/1200, factory race-derived |
| 229 | Triumph vintage (pre-Hinckley + early Hinckley) | 🔲 | Classic British triples, T509/T595, early Hinckley carbureted |
| 230 | Triumph electrical + TuneBoy | 🔲 | Triumph-specific DTC format, TuneECU software, dealer mode |

### Aprilia + MV Agusta (Phases 231–235)

| Phase | Title | Status | Notes |
|-------|-------|--------|-------|
| 231 | Aprilia RSV4 / Tuono V4 | 🔲 | V4 superbike/hyper-naked, Ohlins, aPRC electronics, factory race heritage |
| 232 | Aprilia Dorsoduro / Shiver / SR Max | 🔲 | V-twin supermoto (Dorsoduro), naked (Shiver), scooter (SR Max) |
| 233 | MV Agusta 3-cylinder (F3 / Brutale 675/800 / Turismo Veloce) | 🔲 | Counter-rotating crank 675/800cc triples, Italian engineering, known reliability quirks |
| 234 | MV Agusta 4-cylinder (F4 / Brutale 990/1090) | 🔲 | Radial valve inline-4, exotic pricing, limited dealer network |
| 235 | Aprilia + MV electrical + dealer tools | 🔲 | Marelli (Aprilia), Mercuri (MV), diagnostic tool access, parts availability constraints |

### Cross-European (Phases 236–240)

| Phase | Title | Status | Notes |
|-------|-------|--------|-------|
| 236 | European electrical cross-platform | 🔲 | CAN-bus variations, bike-specific OBD adapters, GS-911, TuneECU, Ducati DDS |
| 237 | European common failure patterns | 🔲 | Voltage regulator issues (BMW hexhead), stator (Ducati), cam chain (Triumph), OEM parts pricing |
| 238 | European valve service intervals | 🔲 | Desmo service (Ducati), shim-under-bucket (BMW K/S1000), shim-over (Triumph) |
| 239 | European parts sourcing + pricing | 🔲 | Manufacturer dealer networks, aftermarket availability, OEM-only parts markup |
| 240 | Gate 11 — European brand coverage integration test | 🔲 | Query any European bike → get DTCs, symptoms, known issues, fixes |

## Track L — Electric Motorcycles (Phases 241–250)

Electric motorcycle diagnostics — fundamentally different from ICE: HV safety, BMS, motor controllers, regen, thermal management. Requires foundational safety phases before brand-specific coverage.

| Phase | Title | Status | Notes |
|-------|-------|--------|-------|
| 241 | HV safety + lockout/tagout procedures | 🔲 | Service plug removal, HV discharge verification, insulated tooling, safety PPE, training requirement |
| 242 | Zero Motorcycles (S/DS/SR/FX/FXE) | 🔲 | Z-Force powertrain, Interior Permanent Magnet motor, Zero app diagnostics |
| 243 | Harley LiveWire / LiveWire One | 🔲 | Revelation powertrain, Showa suspension, H-D dealer integration |
| 244 | Energica (Ego/Eva/Esse/Experia) | 🔲 | Italian premium electric, PMAC motor, Öhlins, fast DC charging |
| 245 | Damon HyperSport / HyperFighter | 🔲 | Shift smart suspension, copilot safety system, startup-phase reliability concerns |
| 246 | BMS diagnostics (battery management) | 🔲 | Cell balancing, SOH (state of health), voltage curves, thermal derating, cycle counting |
| 247 | Motor controller / inverter faults | 🔲 | IGBT failures, phase-loss detection, overcurrent faults, controller firmware |
| 848 | Regenerative braking diagnostics | 🔲 | Regen ratios, coast-down behavior, brake light trigger on regen, single-pedal mode |
| 249 | Thermal management (battery + motor) | 🔲 | Liquid cooling loops (battery), air cooling (motor), thermal derating curves, ambient temp effects |
| 250 | Gate 12 — Electric motorcycle integration test | 🔲 | Query electric bike → BMS/motor/regen/thermal analysis end-to-end |

## Track M — Scooters & Small Displacement (Phases 251–258)

50-300cc class: commuter scooters, Honda Grom/Ruckus, Vespa, learner bikes. CVT diagnostics, small-battery electrical, low-cost repair workflows.

| Phase | Title | Status | Notes |
|-------|-------|--------|-------|
| 251 | Vespa / Piaggio (50-300cc) | 🔲 | Italian scooters, air/liquid-cooled, MP3 tilting 3-wheelers, LX/GTS/Primavera |
| 252 | Honda Ruckus / Grom / Metropolitan / PCX | 🔲 | Cult-favorite small Hondas, Grom 125 modding community, Ruckus/Metro 50cc scooters |
| 253 | Yamaha Zuma / Vino + Kymco / SYM / Genuine | 🔲 | Budget scooters, Taiwanese manufacturers, parts availability |
| 254 | Small-displacement CVT diagnostics | 🔲 | Belt wear, variator/clutch bells, roller weights, kickstart backup |
| 255 | Twist-and-go vs manual small bikes | 🔲 | Scooter vs small motorcycle diagnostic differences |
| 256 | Scooter electrical (12V minimal) | 🔲 | Stator-to-battery, no FI on older carb scooters, simple wiring |
| 257 | Small-engine carb service (single/twin-barrel) | 🔲 | Keihin/Mikuni small-bore carbs, seasonal cleaning, emission restrictions |
| 258 | Gate 13 — Scooter / small displacement integration test | 🔲 | Query scooter/small bike → CVT + electrical + carb workflow |

## Track N — Specialized Workflows (Phases 259–272)

Non-diagnostic workflows that shops perform: pre-purchase inspection, tire service, insurance claims, track prep, seasonal protocols, valve adjustments, brake service.

| Phase | Title | Status | Notes |
|-------|-------|--------|-------|
| 259 | Pre-purchase inspection (PPI) — engine | 🔲 | Compression test, leak-down, oil sample, fuel quality, starter/charging health, visual inspection checklist |
| 260 | Pre-purchase inspection — chassis | 🔲 | Frame straightness, fork seals, steering head bearings, swingarm, wheel bearings, brake/tire condition, accident history |
| 261 | Tire service workflow | 🔲 | Wear patterns (cupping, squaring, feathering), DOT date decoding, age cracking, balance, TPMS |
| 262 | Crash / insurance claim support | 🔲 | Photo documentation standards, damage estimation, frame-straightness measurement, salvage vs repair decision |
| 263 | Track-day / race prep checklist | 🔲 | Safety wire, lockwire torque, brake bleed, coolant swap, tech inspection, number plate prep |
| 264 | Winterization protocol | 🔲 | Fuel stabilizer, battery tender, oil change, carb drain (if carbed), cover, storage position |
| 265 | De-winterization protocol | 🔲 | Battery check, brake exercise, fluid inspection, tire pressure, spring test ride |
| 266 | Engine break-in procedures | 🔲 | Rebuilt engine/top-end break-in, RPM restrictions, heat cycles, oil changes schedule |
| 267 | Emissions / smog compliance (CA-first) | 🔲 | California smog requirements, EPA compliance, cat converter status, CARB database |
| 268 | Valve adjustment workflow | 🔲 | Generic workflow + per-engine-type templates (inline-4, V-twin, single, boxer, Desmo) |
| 269 | Brake service workflow | 🔲 | Pad replacement, caliper rebuild, rotor thickness check, fluid flush, bleed procedure |
| 270 | Suspension service workflow | 🔲 | Fork seal replacement, oil change, spring rate selection, rear shock rebuild, sag setup |
| 271 | Chain / belt / shaft service workflow | 🔲 | Chain/sprocket replacement, belt tension/alignment, shaft drive oil, u-joint inspection |
| 272 | Gate 14 — Specialized workflows integration test | 🔲 | Run PPI → tire service → winterization → valve adjust → brake service end-to-end |

## Track O — Business Infrastructure (Phases 273–292)

Payment processing, CRM, booking, accounting, inventory, warranty/recall claims, vendor integrations — the business systems a shop needs beyond Track G's shop management.

| Phase | Title | Status | Notes |
|-------|-------|--------|-------|
| 273 | Payment processing foundation (Stripe) | 🔲 | Stripe Connect, card terminals, invoicing, subscription billing |
| 274 | Customer CRM | 🔲 | Customer profiles, bike ownership history, communication log, notes |
| 275 | Appointment booking system | 🔲 | Online booking, time slots, mechanic assignments, confirmations |
| 276 | Calendar sync (iCal / Google Calendar) | 🔲 | Two-way sync, appointment blocks, mechanic calendars |
| 277 | Accounting export (QuickBooks) | 🔲 | Chart of accounts mapping, invoice export, payment reconciliation |
| 278 | Accounting export (Xero) | 🔲 | Xero-specific export format, tax handling, multi-currency |
| 279 | Parts inventory with reorder points | 🔲 | Stock levels, reorder points, automatic PO generation, distinct from per-job sourcing |
| 280 | OEM warranty claim processing | 🔲 | Warranty validity lookup, claim documentation, OEM-specific submission flows |
| 281 | NHTSA recall processing | 🔲 | VIN-based recall lookup, recall completion tracking, OEM reimbursement |
| 282 | Vendor: Parts Unlimited integration | 🔲 | API integration, parts availability, wholesale pricing, dropship |
| 283 | Vendor: NAPA integration | 🔲 | NAPA TRACS integration, parts catalog, local store inventory |
| 284 | Vendor: Drag Specialties integration | 🔲 | Drag Specialties wholesale, Harley/V-twin parts focus |
| 285 | Vendor: Dennis Kirk integration | 🔲 | Dennis Kirk wholesale, Japanese parts, off-road |
| 286 | Vendor: tire distributor integrations | 🔲 | Dunlop, Michelin, Metzeler, Bridgestone — wholesale tire ordering |
| 287 | VIN decoder service | 🔲 | NHTSA VPIC integration, make-specific VIN structure decoding, model-year lookup |
| 288 | Tax rate lookup by shop location | 🔲 | State/county/city sales tax, automated tax calculation on invoices |
| 289 | Multi-currency support | 🔲 | USD/CAD/EUR/GBP exchange rates, multi-currency invoicing, currency conversion |
| 290 | Financial reporting | 🔲 | P&L per mechanic, per bay, per customer, monthly/quarterly/annual |
| 291 | Estimate vs actual variance tracking | 🔲 | Quote accuracy, labor time variance, parts cost variance |
| 292 | Gate 15 — Business infrastructure integration test | 🔲 | Customer books → intake → warranty check → repair → invoice → payment → accounting export |

## Track P — Reference Data Library (Phases 293–302)

Deep reference database: service manual citations, exploded parts diagrams, visual failure library, video tutorials, per-model specs.

| Phase | Title | Status | Notes |
|-------|-------|--------|-------|
| 293 | Factory service manual references | 🔲 | Clymer/Haynes/OEM page citation database, searchable by make/model/year/topic |
| 294 | Exploded parts diagram integration | 🔲 | Partzilla/BikeBandit part number → diagram lookup, visual parts browser |
| 295 | Visual failure library | 🔲 | Photo database of common failures, user-contributed + curated, failure signatures |
| 296 | Curated video tutorial index | 🔲 | YouTube embeds by symptom/repair, verified mechanic channels, offline viewing |
| 297 | Per-model torque spec database | 🔲 | Expand Phase 93 generic specs → complete per-model torque database |
| 298 | Per-model fluid capacity database | 🔲 | Oil/coolant/brake fluid/fork oil capacities by exact model/year |
| 299 | Electrical schematic references | 🔲 | Wire color codes per model/year, connector pinouts, module locations |
| 300 | Special tool database | 🔲 | Tools required per repair, OEM vs aftermarket, cost, rental availability |
| 301 | Service interval tables | 🔲 | OEM service intervals per model, normal vs severe service, expand Phase 93 |
| 302 | Gate 16 — Reference data library integration test | 🔲 | Query any bike/repair → manual page + diagram + torque + tool + video |

## Track Q — Extended UX Affordances (Phases 303–317)

Multi-user auth, voice-first mode, printing, barcode scanning, photo annotation, i18n, AR overlay, accessibility, customization.

| Phase | Title | Status | Notes |
|-------|-------|--------|-------|
| 303 | Multi-user auth with roles | 🔲 | Owner/tech/service writer/apprentice, permission gating, session management |
| 304 | Voice-first mode (expand Phase 183) | 🔲 | Hands-free wrenching, voice commands, continuous listening mode |
| 305 | Print + label support | 🔲 | Service tags, work order printouts, parts labels, Brother/Dymo printer integration |
| 306 | Barcode / QR scanning | 🔲 | Parts inventory scanning, bike check-in via VIN barcode, mobile camera or USB scanner |
| 307 | Photo annotation | 🔲 | Draw circles on leaks, arrows to cracks, text labels, annotation persistence |
| 308 | Spanish localization | 🔲 | Priority language — large US mechanic demographic, full UI + knowledge base translation |
| 309 | French localization | 🔲 | Quebec, Europe markets, UI + knowledge base |
| 310 | German localization | 🔲 | European market, aftermarket catalogs, UI + knowledge base |
| 311 | AR overlay (research/placeholder) | 🔲 | ARKit/ARCore integration for camera-based diagnostic overlay, scope-deferred — research phase only |
| 312 | Accessibility (screen reader + high contrast) | 🔲 | WCAG 2.1 AA compliance, VoiceOver/TalkBack, keyboard navigation |
| 313 | Dark mode (desktop) | 🔲 | High contrast dark theme, complement Phase 203 mobile, user preference |
| 314 | Keyboard shortcuts + power user features | 🔲 | Desktop CLI hotkeys, vim-style navigation, command palette, custom aliases |
| 315 | Customizable dashboards | 🔲 | Drag-and-drop widgets, per-user layouts, saved views |
| 316 | Workflow recording (train-by-example) | 🔲 | Record my process → replay for training, generate workflow templates from recordings |
| 317 | Gate 17 — Extended UX integration test | 🔲 | Multi-user auth → voice input → photo annotation → Spanish UI → print work order |

## Track R — Advanced AI Capabilities (Phases 318–327)

Beyond the base AI engine: human-in-the-loop learning, tuning recommendations, expanded predictive maintenance, cross-fleet anomaly detection, knowledge graph.

| Phase | Title | Status | Notes |
|-------|-------|--------|-------|
| 318 | Human-in-the-loop learning | 🔲 | Mechanic overrides train the system, feedback loop closes on diagnostic accuracy, retraining pipeline |
| 319 | Tuning recommendations | 🔲 | Jetting calculations (altitude/mods), Power Commander/FTECU/Dynojet map suggestions |
| 320 | Predictive maintenance expansion | 🔲 | Beyond Phase 148 — per-customer, per-fleet, per-usage-pattern failure prediction |
| 321 | Fleet anomaly detection | 🔲 | Cross-bike pattern recognition, identify "same model same issue" at scale |
| 322 | AI-assisted customer communication | 🔲 | Draft status updates, explain repairs in plain English, estimate customer questions |
| 323 | Image similarity search | 🔲 | "Show me bikes with this symptom" — visual failure similarity via embedding |
| 324 | Repair success prediction | 🔲 | "Will this fix work for this bike?" — historical outcome prediction |
| 325 | Knowledge graph construction | 🔲 | Symptom ↔ cause ↔ fix relationships, graph queries for complex diagnostics |
| 326 | Continuous learning pipeline | 🔲 | Automated model fine-tuning from accumulated diagnostic feedback |
| 327 | Gate 18 — Advanced AI integration test | 🔲 | Feedback → learning → prediction → anomaly detection → customer draft end-to-end |

## Track S — Launch + Business Layer (Phases 328–342)

Commercial launch infrastructure: billing, onboarding, data migration from competitors, legal, training/certification, community.

| Phase | Title | Status | Notes |
|-------|-------|--------|-------|
| 328 | Subscription billing foundation | 🔲 | Stripe integration from Track O wired to subscription tiers, tier enforcement flips to hard mode here |
| 329 | Self-service signup flow (web) | 🔲 | Trial signup, credit card capture, email verification, onboarding trigger |
| 330 | Onboarding wizard for new shops | 🔲 | Bike inventory import, staff setup, initial data entry, first diagnostic walkthrough |
| 331 | Data migration: Mitchell 1 → MotoDiag | 🔲 | Import existing shop data from Mitchell 1 (auto/moto), vehicle history, work orders |
| 332 | Data migration: ShopKey → MotoDiag | 🔲 | Import from Snap-on ShopKey, SMS Pro |
| 333 | Data migration: ALLDATA → MotoDiag | 🔲 | Import from AutoZone ALLDATA Shop Management |
| 334 | Terms of Service + liability framework | 🔲 | Legal ToS, liability disclaimers on repair recommendations, mechanic indemnification |
| 335 | MotoDiag Certified training track | 🔲 | Online courses, video tutorials, structured learning paths for new mechanics |
| 336 | Certification exam system | 🔲 | Proctored exam, certificate generation, renewal requirements, certification tiers |
| 337 | In-app mechanic community | 🔲 | Q&A forum, moderated discussion, expert verification, reputation system |
| 338 | Customer referral program | 🔲 | Referral codes, tracking, credits/discounts, viral acquisition |
| 339 | Promotional codes + discounts | 🔲 | Coupon system, time-limited promotions, tier upgrade incentives |
| 340 | Enterprise sales portal | 🔲 | B2B lead management, custom quotes, multi-year contracts, SLA negotiation |
| 341 | SLA + uptime dashboard | 🔲 | Public status page, uptime metrics, incident communication, enterprise SLAs |
| 342 | Gate 19 — Launch readiness check | 🔲 | Billing → signup → onboarding → data migration → first diagnostic under paid plan |

## Track T — Operational Infrastructure (Phases 343–352)

Running MotoDiag as a production service: observability, support, backup, feature flags, admin tools.

| Phase | Title | Status | Notes |
|-------|-------|--------|-------|
| 343 | Telemetry + crash reporting (Sentry) | 🔲 | Sentry integration, crash reports, performance monitoring, user session replay |
| 344 | In-app support channel | 🔲 | Chat widget or ticketing, support team routing, knowledge base integration |
| 345 | Cloud backup + sync | 🔲 | S3 encrypted backups, automatic sync, point-in-time restore |
| 346 | Multi-location / franchise support | 🔲 | Shared customers across locations, inter-location parts transfer, centralized reporting |
| 347 | Real-time sync between devices | 🔲 | Desktop ↔ mobile ↔ web real-time data sync, conflict resolution |
| 348 | Audit log (who did what, when) | 🔲 | Immutable event log, security audit trail, compliance readiness |
| 349 | Feature flags / gradual rollout | 🔲 | LaunchDarkly-style feature flags, percentage rollouts, kill switches |
| 350 | A/B testing framework | 🔲 | Experiment tracking, conversion metrics, feature comparison |
| 351 | Admin panel for support staff | 🔲 | Customer lookup, account management, subscription changes, impersonation for debugging |
| 352 | Gate 20 — Operational readiness | 🔲 | Telemetry → support → backup → multi-location → audit log → admin panel end-to-end |

---

## Architecture Overview

```
moto-diag/
├── pyproject.toml
├── src/
│   └── motodiag/
│       ├── __init__.py
│       ├── core/           ← config, database, base models (Track A)
│       ├── vehicles/       ← vehicle registry, specs (Track A/B, expanded Retrofit 110)
│       ├── knowledge/      ← DTC codes, symptoms, known issues (Track B, expanded Retrofit 111)
│       ├── engine/         ← AI diagnostic engine (Track C)
│       ├── media/          ← video/audio diagnostic analysis (Track C2, annotations Retrofit 119)
│       ├── cli/            ← terminal interface (Track D)
│       ├── auth/           ← users, roles, permissions (Retrofit 112)
│       ├── crm/            ← customers, customer-bikes join (Retrofit 113)
│       ├── hardware/       ← OBD adapter interface (Track E)
│       ├── advanced/       ← fleet, maintenance, prediction (Track F)
│       ├── shop/           ← shop management, work orders, triage, scheduling (Track G)
│       ├── api/            ← REST API + web layer (Track H)
│       ├── billing/        ← Stripe integration, subscriptions, payments (Retrofit 118, Track O/S)
│       ├── accounting/     ← QuickBooks/Xero export, financial reports (Retrofit 118, Track O)
│       ├── inventory/      ← parts inventory, reorder points, vendor integration (Retrofit 118, Track O)
│       ├── scheduling/     ← appointments, calendar sync (Retrofit 118, Track O)
│       ├── workflows/      ← PPI, tire service, winterization templates (Retrofit 114, Track N)
│       ├── i18n/           ← translations, locale handling (Retrofit 115, Track Q)
│       ├── reference/      ← manual refs, parts diagrams, video tutorials (Retrofit 117, Track P)
│       ├── feedback/       ← diagnostic feedback, override tracking (Retrofit 116, Track R)
│       ├── ai_advanced/    ← human-in-loop learning, tuning, knowledge graph (Track R)
│       ├── launch/         ← signup, onboarding, migration, community (Track S)
│       └── ops/            ← telemetry, support, backups, feature flags, admin (Track T)
├── data/
│   ├── dtc_codes/          ← fault code databases
│   ├── vehicles/           ← make/model specs
│   └── knowledge/          ← known issues, repair procedures
├── tests/
├── output/
├── main.py
└── docs/
    └── phases/             ← per-phase implementation + log docs
```

## Design Principles

1. **Core depends on nothing** — no framework imports in business logic
2. **Hardware is optional** — full diagnostic value without plugging anything in
3. **Mechanic-first UX** — terse, useful output; no fluff
4. **Every diagnosis is traceable** — session → symptoms → reasoning → conclusion
5. **Knowledge compounds** — each diagnostic session can improve future diagnoses
6. **Cost-aware AI** — track tokens, use cheapest model that works, cache aggressively
