# MotoDiag — Full Roadmap

**Project:** moto-diag — AI-Powered Motorcycle Diagnostic Tool (Hybrid: Software + Hardware)
**Repo:** `Kubanjaze/moto-diag`
**Local:** `C:\Users\Kerwyn\PycharmProjects\moto-diag\`
**Started:** 2026-04-15
**Target Fleet:** Harley-Davidson (all years), Honda, Yamaha, Kawasaki, Suzuki (all classes — sport, standard, cruiser, dual-sport, vintage)
**Target Users:** Motorcycle mechanics
**Total Phases:** 198

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

## Track D — CLI + User Experience (Phases 109–121)

The mechanic's daily driver interface.

| Phase | Title | Status | Notes |
|-------|-------|--------|-------|
| 109 | CLI foundation + command structure | 🔲 | Click/Typer CLI, subcommands, help system |
| 110 | Vehicle garage management | 🔲 | Add/edit/list/remove vehicles from personal garage |
| 111 | Interactive diagnostic session | 🔲 | Start session → describe problem → guided Q&A → diagnosis |
| 112 | Fault code lookup command | 🔲 | `motodiag code P0115` → plain-English explanation + fix |
| 113 | Quick diagnosis mode | 🔲 | One-shot: `motodiag diagnose "won't start when cold" --bike sportster-2001` |
| 114 | Diagnostic report output | 🔲 | Formatted terminal report + save to file (txt/json) |
| 115 | Session history browser | 🔲 | Browse past diagnostic sessions, re-open, annotate |
| 116 | Knowledge base browser | 🔲 | Browse known issues by make/model, search, filter |
| 117 | Rich terminal UI (tables, colors, progress) | 🔲 | Pretty output with rich/textual |
| 118 | Shell completions + shortcuts | 🔲 | Tab completion, aliases, power-user features |
| 119 | Offline mode | 🔲 | Cache AI responses, work without internet for code lookups |
| 120 | Export + sharing | 🔲 | Export diagnosis to PDF/HTML, share with customer |
| 121 | Gate 5 — CLI integration test | 🔲 | Full mechanic workflow through CLI |

## Track E — Hardware Interface (Phases 122–135)

OBD adapter integration, live sensor data, ECU communication.

| Phase | Title | Status | Notes |
|-------|-------|--------|-------|
| 122 | OBD protocol abstraction layer | 🔲 | Interface definition for all protocol adapters |
| 123 | ELM327 adapter communication | 🔲 | Serial/Bluetooth ELM327 command protocol |
| 124 | CAN bus protocol implementation | 🔲 | ISO 15765 — for 2011+ Harleys, modern bikes |
| 125 | K-line/KWP2000 protocol implementation | 🔲 | ISO 14230 — for 90s/2000s Japanese bikes |
| 126 | J1850 protocol implementation | 🔲 | For older Harleys (pre-2011) |
| 127 | ECU auto-detection + handshake | 🔲 | Detect protocol, establish session, identify ECU |
| 128 | Fault code read/clear operations | 🔲 | Read DTCs from ECU, clear after repair |
| 129 | Live sensor data streaming | 🔲 | RPM, TPS, coolant temp, battery V, O2 sensor |
| 130 | Data logging + recording | 🔲 | Record sensor sessions, replay, analyze |
| 131 | Real-time terminal dashboard | 🔲 | Live gauges/graphs in terminal (textual) |
| 132 | Hardware simulator | 🔲 | Mock adapter for testing without physical hardware |
| 133 | Adapter compatibility database | 🔲 | Which adapters work with which bikes |
| 134 | Connection troubleshooting + recovery | 🔲 | Handle disconnects, timeouts, protocol errors |
| 135 | Gate 6 — Hardware integration test | 🔲 | Simulated ECU → adapter → read codes → AI diagnosis |

## Track F — Advanced Diagnostics (Phases 136–147)

Power features for experienced mechanics.

| Phase | Title | Status | Notes |
|-------|-------|--------|-------|
| 136 | Predictive maintenance | 🔲 | Mileage/age-based failure prediction per model |
| 137 | Wear pattern analysis | 🔲 | Correlate symptoms with known wear patterns |
| 138 | Fleet management | 🔲 | Manage multiple bikes, shop inventory |
| 139 | Maintenance scheduling | 🔲 | Service intervals, upcoming maintenance alerts |
| 140 | Service history tracking | 🔲 | Full repair history per vehicle |
| 141 | Parts cross-reference | 🔲 | OEM ↔ aftermarket part number lookup |
| 142 | Technical service bulletin (TSB) database | 🔲 | Known manufacturer issues + fixes |
| 143 | Recall information | 🔲 | NHTSA recall lookup by VIN/model |
| 144 | Comparative diagnostics | 🔲 | Same model, different bikes — spot anomalies |
| 145 | Performance baselining | 🔲 | Establish "healthy" sensor baselines per model |
| 146 | Degradation tracking | 🔲 | Track sensor drift over time |
| 147 | Gate 7 — Advanced diagnostics integration test | 🔲 | Fleet + history + prediction end-to-end |

## Track G — Shop Management + Optimization (Phases 148–162)

Shop-level features: log bikes in your shop, track issues across the fleet, triage what to fix first, auto-generate parts lists, optimize workflow.

| Phase | Title | Status | Notes |
|-------|-------|--------|-------|
| 148 | Shop profile + multi-bike intake | 🔲 | Register shop, log incoming bikes with customer info |
| 149 | Work order system | 🔲 | Create/assign/track work orders per bike |
| 150 | Issue logging + categorization | 🔲 | Log reported issues per bike, categorize by system/severity |
| 151 | Repair priority scoring | 🔲 | AI-ranked priority: safety > ridability > cosmetic, weighted by wait time |
| 152 | Automated triage queue | 🔲 | "What to fix first" — sorted by priority, parts availability, bay time |
| 153 | Parts needed aggregation | 🔲 | Cross all active work orders → consolidated parts list |
| 154 | Parts sourcing + cost optimization | 🔲 | OEM vs aftermarket vs used, vendor price comparison |
| 155 | Labor time estimation | 🔲 | AI-estimated wrench time per job, based on model + issue |
| 156 | Bay/lift scheduling | 🔲 | Schedule repairs across available bays/lifts, minimize idle time |
| 157 | Revenue tracking + invoicing | 🔲 | Parts cost + labor = invoice, track revenue per bike/job |
| 158 | Customer communication | 🔲 | Status updates, approval requests, completion notifications |
| 159 | Shop analytics dashboard | 🔲 | Revenue, throughput, avg repair time, common issues |
| 160 | Multi-mechanic assignment | 🔲 | Assign jobs to mechanics, track who worked on what |
| 161 | Workflow automation rules | 🔲 | "If safety issue → priority 1", "if parts > $500 → customer approval" |
| 162 | Gate 8 — Shop management integration test | 🔲 | Intake → triage → parts → schedule → repair → invoice flow |

## Track H — API + Web Layer (Phases 163–172)

REST API for future mobile app / web dashboard.

| Phase | Title | Status | Notes |
|-------|-------|--------|-------|
| 163 | FastAPI foundation + project structure | 🔲 | API scaffold, CORS, error handling |
| 164 | Auth + API keys | 🔲 | API key management, rate limiting |
| 165 | Vehicle endpoints | 🔲 | CRUD for garage vehicles |
| 166 | Diagnostic session endpoints | 🔲 | Start/update/complete diagnostic sessions |
| 167 | Knowledge base endpoints | 🔲 | Search DTCs, symptoms, known issues |
| 168 | Shop management endpoints | 🔲 | Work orders, triage, parts, scheduling |
| 169 | WebSocket live data | 🔲 | Stream sensor data to web clients |
| 170 | Report generation endpoints | 🔲 | Generate PDF/HTML diagnostic reports + invoices |
| 171 | API documentation + OpenAPI spec | 🔲 | Auto-generated docs, example requests |
| 172 | Gate 9 — API integration test | 🔲 | Full API workflow: auth → vehicle → diagnose → shop → report |

## Track I — Mobile App (iOS + Android) (Phases 173–192)

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
| 173 | Mobile architecture decision (React Native vs Flutter) | 🔲 | Evaluate framework, decide on shared codebase approach |
| 174 | Mobile project scaffold + CI/CD | 🔲 | iOS + Android build pipeline, TestFlight / Play Store beta |
| 175 | Auth + API client library | 🔲 | Secure token storage, API wrapper, offline token refresh |
| 176 | Vehicle garage screen | 🔲 | Add/edit/view bikes, VIN scanner (camera), big touch targets |
| 177 | DTC code lookup screen | 🔲 | Search by code or text, voice input, offline DTC database |
| 178 | Interactive diagnostic session (mobile) | 🔲 | Guided Q&A with large buttons, voice input for symptoms |
| 179 | Video diagnostic capture (mobile) | 🔲 | Film bike running, auto-extract audio + key frames → AI analysis |
| 180 | Diagnostic report viewer | 🔲 | View/share diagnosis, PDF export, AirDrop/Share Sheet |
| 181 | Shop dashboard (mobile) | 🔲 | Work order list, triage queue, tap to assign/update |
| 182 | Camera + photo integration | 🔲 | Photograph issues, attach to work orders, before/after |
| 183 | Voice input for symptom description | 🔲 | Speech-to-text, structured symptom extraction from voice |
| 184 | Bluetooth OBD adapter connection | 🔲 | Scan for adapters, pair, connect, protocol handshake |
| 185 | Live sensor data dashboard (mobile) | 🔲 | Real-time gauges, swipe between sensors, landscape mode |
| 186 | Offline mode + local database | 🔲 | SQLite on device, full DTC database cached, queue API calls |
| 187 | Push notifications | 🔲 | Work order updates, diagnostic results, parts arrival alerts |
| 188 | Customer-facing share view | 🔲 | Simplified report for bike owners, text/email share |
| 189 | Parts ordering from mobile | 🔲 | Browse needed parts, add to cart, order from phone |
| 190 | Mechanic time tracking | 🔲 | Clock in/out per job, timer for labor billing |
| 191 | Dark mode + shop-friendly UI | 🔲 | High contrast, readable in sunlight and under shop lights |
| 192 | Gate 10 — Mobile integration test | 🔲 | Full flow: film bike → diagnose → share report |

## Track J — Ship + Scale (Phases 193–198)

Polish, package, launch.

| Phase | Title | Status | Notes |
|-------|-------|--------|-------|
| 193 | End-to-end integration testing | 🔲 | All tracks working together (desktop + mobile) |
| 194 | Performance optimization | 🔲 | Query speed, API response time, memory usage |
| 195 | Security audit | 🔲 | API keys, input validation, SQL injection prevention |
| 196 | Documentation + user guide | 🔲 | README, usage guide, mechanic quickstart, app store listing |
| 197 | Packaging + distribution | 🔲 | pip install, standalone binary, Docker, App Store, Play Store |
| 198 | Launch readiness + full integration | 🔲 | Everything together — the complete MotoDiag platform |

---

## Architecture Overview

```
moto-diag/
├── pyproject.toml
├── src/
│   └── motodiag/
│       ├── __init__.py
│       ├── core/           ← config, database, base models (Track A)
│       ├── vehicles/       ← vehicle registry, specs (Track A/B)
│       ├── knowledge/      ← DTC codes, symptoms, known issues (Track B)
│       ├── engine/         ← AI diagnostic engine (Track C)
│       ├── media/          ← video/audio diagnostic analysis (Track C2)
│       ├── cli/            ← terminal interface (Track D)
│       ├── hardware/       ← OBD adapter interface (Track E)
│       ├── advanced/       ← fleet, maintenance, prediction (Track F)
│       ├── shop/           ← shop management, work orders, triage, scheduling (Track G)
│       └── api/            ← REST API (Track H)
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
