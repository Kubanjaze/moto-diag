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

## Track D — CLI + User Experience (Phases 109, 122–133) ✅ COMPLETE

The mechanic's daily driver interface. Phase 109 delivered the foundation; remaining phases shifted to 122-133 after Retrofit track insertion.

| Phase | Title | Status | Notes |
|-------|-------|--------|-------|
| 109 | CLI foundation + command structure | ✅ | Click CLI, subcommands, 3-tier subscription system ($19/$99/$299), tier command, 41 tests |
| 122 | Vehicle garage management + photo intake | ✅ | Migration 013 + src/motodiag/intake/ package. VehicleIdentifier with Claude Haiku 4.5 vision, Sonnet escalation < 0.5 confidence, sha256 image cache, 1024px Pillow resize, tier caps 20/200/unlimited enforced from subscriptions.tier, 80% budget alert on crossing. CLI: garage add/list/remove, garage add-from-photo, intake photo, intake quota. 49 tests, all vision calls mocked (0 tokens burned), 2051 total, zero regressions. Schema v12→v13. |
| 123 | Interactive diagnostic session | ✅ | New cli/diagnose.py orchestration + 4 CLI subcommands (start/quick/list/show). Q&A loop caps at 3 rounds, stops on confidence ≥ 0.7. Tier-gated model access (individual=Haiku; shop/company=Sonnet). No migration — reuses Phase 03 substrate. 39 tests, all mocked (0 tokens), 2090 total, zero regressions. |
| 124 | Fault code lookup command | ✅ | New `cli/code.py` (392 LoC) replaces Phase 01's inline `code` command via `register_code(cli)` with legacy-eviction guard. Single command, three modes: default DB lookup with fallback chain (make-specific → generic → `classify_code()` heuristic + yellow banner), `--category <cat>` list mode (via Phase 111's `get_dtcs_by_category`), and `--explain --vehicle-id N` tier-gated AI interpretation (`FaultCodeInterpreter`). Reuses `_resolve_model/_load_vehicle/_load_known_issues/_parse_symptoms` from `cli.diagnose` — no copy-paste. Phase 05 `test_code_help` updated to use `--help`. 33 tests, all mocked (0 tokens), 2123 total, zero regressions. |
| 125 | Quick diagnosis mode | ✅ | Extended `cli/diagnose.py` (+180 LoC): `_parse_slug` + `_resolve_bike_slug` (4-tier match), `--bike SLUG` option on `diagnose quick`, new top-level `motodiag quick "<symptoms>"` via `register_quick` + Click `ctx.invoke()` delegation. Pure UX sugar — no substrate. First agent-delegated build (Builder-A). 34 tests, 2157 total, zero regressions, zero live tokens. |
| 126 | Diagnostic report output | ✅ | Extended `cli/diagnose.py` (+200 LoC): 3 pure formatters (txt/json/md) + `--format` and `--output` options on existing `diagnose show`. JSON has `format_version: "1"` for future schema evolution. Second agent-delegated phase. 22 tests, 2179 total, zero regressions, zero live tokens. |
| 127 | Session history browser | ✅ | Migration 014 adds nullable `notes` column (schema v13→v14). Extended `diagnose list` with 7 new filter options (vehicle-id/make/model/search/since/until/limit), new `diagnose reopen <id>` and `diagnose annotate <id> "note"` commands. Append-only notes with timestamp prefix. Third agent-delegated phase. 28 tests, 2207 total, zero regressions, zero live tokens. |
| 128 | Knowledge base browser | ✅ | New `cli/kb.py` (~320 LoC) + new `search_known_issues_text` repo function. 5 subcommands under `motodiag kb`: list (structured filters), show, search (free-text across title/description/symptoms), by-symptom, by-code (DTC upper-cased). Fourth agent-delegated phase. 26 tests, 2233 total, zero regressions, zero live tokens. |
| 129 | Rich terminal UI (tables, colors, progress) | ✅ | New `cli/theme.py` (~230 LoC) centralizes Console singleton + color maps (severity/status/tier) + icons + spinner context. Migrated 10+ inline `Console()` sites across 5 CLI modules. Progress spinners wrap AI calls (diagnose, code --explain, intake). Respects `NO_COLOR` + `COLUMNS`. Textual TUI explicitly deferred. 20 tests, 2253 total, zero regressions, zero live tokens. |
| 130 | Shell completions + shortcuts | ✅ | New `cli/completion.py` (~260 LoC) wraps Click's shell completion + adds 3 dynamic completers (bike slugs / DTC codes / session IDs), defensive on fresh DB. 4 hidden short aliases (d/k/g/q) via shallow-copy pattern. `shell_complete=` wired on 6 existing option sites. Sixth agent-delegated phase. 18 tests, 2271 total, zero regressions, zero live tokens. |
| 131 | Offline mode | ✅ | Migration 015 adds `ai_response_cache` (schema v14→v15). New `engine/cache.py` (SHA256 keys) + `cli/cache.py` (stats/purge/clear). `--offline` flag on `diagnose quick/start` + `code --explain`. Cache misses on `--offline` raise clear RuntimeError. Seventh agent-delegated phase. 30 tests, 2301 total, zero regressions, zero live tokens. |
| 132 | Export + sharing | ✅ | Extends Phase 126 `--format` with `html` and `pdf` on `diagnose show` + brings `kb show` to parity (md/html/pdf). New `cli/export.py` shared module (`format_as_html` via `markdown`, `format_as_pdf` via `xhtml2pdf`). `motodiag[export]` optional extras. Markdown is the pivot format. Eighth agent-delegated phase. 25 tests, 2326 total, zero regressions, zero live tokens. |
| 133 | Gate 5 — CLI integration test | ✅ | **GATE 5 PASSED.** Single new test file `test_phase133_gate_5.py` (~7 tests across 3 classes): one big end-to-end workflow test with 19 CLI invocations on shared DB + `CliRunner` + 3 AI mocks (`_default_diagnose_fn` / `_default_interpret_fn` / `_default_vision_call`), 4 CLI-surface breadth tests, 2 regression tests (Gate R still passes, schema ≥ v15, all `cli.*` submodules import). Consolidated 15-20 planned tests into 7 cohesive ones (same pattern as Gate R's 20→10). Ninth agent-delegated phase — Builder-A clean first pass, 7 tests passed in 6.04s on trust-but-verify. Zero new production code (pure observation), zero schema changes, zero live tokens. 2333 total. |

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
| 118 | Billing/invoicing/inventory/scheduling substrate | ✅ | Migration 011 + 4 new packages (billing/accounting/inventory/scheduling). 9 tables + 14 indexes. Stripe column pre-wiring, invoice recalc with tax, low-stock alerts, calendar-ready appointments. Schema v10→v11. 37 tests, 1932 total |
| 119 | Media annotation layer | ✅ | Migration 012 + media/photo_annotation module (AnnotationShape enum 4 members, PhotoAnnotation model with 3 validators, 8 repo functions). photo_annotations table with 3 indexes. Dual-mode: FK-linked CASCADE or orphan-safe by image_ref. Schema v11→v12. 22 tests, 1954 total |
| 120 | Engine sound signature library expansion | ✅ | 4 new EngineType enum + SIGNATURES entries (ELECTRIC_MOTOR, DUCATI_L_TWIN, KTM_LC8_V_TWIN, TRIUMPH_TRIPLE). motor_rpm_to_whine_frequency helper. Dry-clutch-as-normal documented. 3 Phase 98 forward-compat test fixes. 38 tests, 1992 total |
| 121 | Gate R — Retrofit integration test | ✅ | **GATE R PASSED.** 10 integration tests: end-to-end workflow through every retrofit package, migration determinism (two-fresh-DB identical), CLI smoke + in-process package imports. One known limitation documented (migration 005 ALTER rollback). 1616 → 2002 total tests, zero regressions across the entire retrofit |

## Track E — Hardware Interface (Phases 134–147) ✅ COMPLETE

OBD adapter integration, live sensor data, ECU communication. Shifted from 122-135 due to Retrofit track insertion.

| Phase | Title | Status | Notes |
|-------|-------|--------|-------|
| 134 | OBD protocol abstraction layer | ✅ | New `hardware/protocols/` package: `base.py` (`ProtocolAdapter` ABC — connect/disconnect/is_connected/read_dtcs/clear_dtcs/read_pid/read_vin/send_raw/get_protocol_name), `models.py` (`ProtocolConnection` frozen Pydantic model + `DTCReadResult` with `mode="before"` uppercase normalization + `PIDResponse` paired value/unit validator), `exceptions.py` (`ProtocolError` base + `ConnectionError` + `TimeoutError` + `UnsupportedCommandError(command)`). Wave 1 Builder (parallel dispatch) delivered clean first pass. No migration, no CLI. 49 tests, 2382 total. |
| 135 | ELM327 adapter communication | ✅ | New `hardware/protocols/elm327.py` (~584 LoC) — first concrete `ProtocolAdapter`. Wraps ELM327 OBD-II chip over pyserial (serial/USB/Bluetooth-SPP) with full AT-command handshake (`ATZ`/`ATE0`/`ATL0`/`ATSP0`), multi-frame response tolerance (scans for `43`/`41 XX` service echo rather than index 0), DTC parsing (mode 03 response → P/B/C/U codes), VIN assembly (mode 09 PID 02 multi-line). Unlocks ~80% of aftermarket OBD dongles (OBDLink, Vgate, generic clones). Wave 2 Builder. 52 tests. |
| 136 | CAN bus protocol implementation | ✅ | New `hardware/protocols/can.py` (~470 LoC). ISO 15765-4 over `python-can` (any backend — SocketCAN/PCAN/Vector/Kvaser/slcan/Peak). Hand-rolled ISO-TP (not `python-can-isotp` — fewer Windows-fragile deps). Services: mode 03 DTCs, mode 04 clear (`True` on positive, `False` on NRC 0x22, raises on others), mode 09 VIN, read_pid with big-endian byte combination. New `can = ["python-can>=4.0"]` optional extras. Target bikes: 2011+ Harley Touring, modern CAN-equipped Japanese/EU bikes. Wave 2 Builder. 38 tests. |
| 137 | K-line/KWP2000 protocol implementation | ✅ | New `hardware/protocols/kline.py` (~670 LoC) — ISO 14230-4 over pyserial for 90s/2000s Japanese sport-bikes (CBR/ZX/GSX-R/YZF-R1) and vintage Euro (Aprilia RSV, Ducati 996, KTM LC4). Module-level pure `_build_frame`/`_parse_frame` helpers for testability. Slow-baud wakeup, checksum validation, local-echo cancellation, strict timing windows. Services 0x10/0x11/0x14/0x18/0x1A/0x21. DTC decode (`(0x02, 0x01) → P0201`). Write services (0x27/0x2E/0x31) deliberately out of scope (tune-writing safety). Wave 2 Builder. 44 tests. |
| 138 | J1850 protocol implementation | ✅ | New `hardware/protocols/j1850.py` (~600 LoC) — J1850 VPW (10.4 kbps) for pre-2011 Harley. No direct bit-bang; talks through bridge devices (ScanGauge II, Daytona Twin Tec, Dynojet Power Commander, Digital Tech II clones). Multi-module DTC read merges ECM (P-codes) + BCM (B-codes) + ABS (C-codes) into single list, with supplementary `read_dtcs_by_module() -> dict`. Bridge variants: `daytona/scangauge/dynojet/generic`. `read_pid` raises `NotImplementedError` (Phase 141); `read_vin` raises `UnsupportedCommandError` (pre-2008 HDs lacked Mode 09). Wave 2 Builder. 27 tests. |
| 139 | ECU auto-detection + handshake | ✅ | New `hardware/ecu_detect.py` (~460 LoC). `AutoDetector` given a serial port + optional `make_hint` tries protocol adapters in priority order (Harley→J1850 first; Japanese→CAN/KWP2000; European→CAN/KWP2000; unknown→all four) until one negotiates. Per-protocol `_build_adapter` factory handles non-uniform adapter kwargs (each of CAN/K-line/J1850/ELM327 has different constructor signature). Lazy per-adapter imports so missing optional deps only surface when tried. `identify_ecu()` probes VIN + ECU part number + software version + supported OBD modes, each best-effort. `NoECUDetectedError` carries `port`, `make_hint`, and `errors: list[(name, exception)]` for introspection. No live hardware — all tests use `MagicMock` adapters. Wave 3 Builder. 31 tests. |
| 140 | Fault code read/clear operations | ✅ | First user-facing Track E phase. New `motodiag hardware` CLI group with `scan` (auto-detect + Mode 03 read + Rich table with 3-tier DTC enrichment), `clear` (Mode 04 with yellow safety warning + confirm/`--yes`), `info` (`identify_ecu()` → Rich Panel with VIN/ECU#/sw/modes). 5 new files: `hardware/mock.py` (249 LoC `MockAdapter` ABC-satisfying with configurable state), `hardware/connection.py` (255 LoC `HardwareSession` context manager — real/mock/override paths + disconnect-on-exception), `knowledge/dtc_lookup.py` (147 LoC `resolve_dtc_info` with `source=db_make/db_generic/classifier` discriminator), `cli/hardware.py` (556 LoC), `test_phase140_hardware_cli.py` (40 tests across 6 classes). `--mock` flag bypasses pyserial entirely for CI/offline dev. Tenth agent-delegated phase — Builder-A's cleanest pass (no sandbox block, 40 tests in 21.24s, zero iterative fixes). 2614 total. |
| 141 | Live sensor data streaming | ✅ | New `hardware/sensors.py` (SAE J1979 PID catalog + `SensorSpec`/`SensorReading`/`SensorStreamer` one-shot iterator) + `motodiag hardware stream --port --pids --hz --duration --output` subcommand with Rich `Live` panel + optional CSV append logging. `MockAdapter.pid_values` additive kwarg. 42 tests GREEN. Bug fix #1: hz-throttle test (generator post-yield sleep semantics). |
| 142 | Data logging + recording | ✅ | Migration 016 (schema v15→v16): `sensor_recordings` + `sensor_samples` + 4 indexes (FK CASCADE). New `hardware/recorder.py` (`RecordingManager` with SQLite/JSONL split at 1000 rows, transparent load merge, linear-interp `DiffReport` via stdlib `bisect`). `motodiag hardware log {start,stop,list,show,replay,diff,export,prune}` 8-subcommand subgroup. `parquet = [pyarrow]` optional extra. 52 tests GREEN. |
| 143 | Real-time terminal dashboard | ✅ | New `hardware/dashboard.py` (1282 LoC — `DashboardApp(textual.App)` with 3-column grid + ctrl+q/ctrl+r/d/1-6 keybindings, `GaugeWidget`/`PidChart`/`DTCPanel`/`StatusBar`, `LiveDashboardSource` wrapping SensorStreamer + `ReplayDashboardSource` walking recordings). `motodiag hardware dashboard` subcommand. `dashboard = [textual>=0.40,<1.0]` optional extra. Lazy Textual import with install-hint. 46 tests GREEN. Bug fix #1: `GaugeWidget` numeric display used unclamped value. |
| 144 | Hardware simulator | ✅ | New `hardware/simulator.py` (1212 LoC — `SimulationClock` manual-tick, 9 Pydantic discriminated-union event models, `Scenario` aggregate with cross-event validators, `ScenarioLoader` from_yaml/from_recording/list_builtins, `SimulatedAdapter(ProtocolAdapter)` sibling to MockAdapter). 10 built-in YAML scenarios under `scenarios/`. `motodiag hardware simulate {list,run,validate}` + `--simulator SCENARIO` opt-in on scan/clear/info. `pyyaml>=6` base dep + `package-data` for YAMLs. 81 tests GREEN. Bug fix #1: `_coerce_pid` bare-number → decimal (JSON round-trip identity). |
| 145 | Adapter compatibility database | ✅ | Migration 017 (schema v16→v17): `obd_adapters` + `adapter_compatibility` + `compat_notes` + 6 indexes. New `hardware/compat_repo.py` (870 LoC CRUD + ranking + `check_compatibility` specificity match + `protocols_to_skip_for_make` AutoDetector filter hook) + `compat_loader.py` (idempotent JSON seed). Seed data: 24 real adapters (OBDLink MX+/SX/LX, Dynojet PV3, Daytona TCFI, Vance & Hines FP4, Autel AP200BT, Foxwell NT301, Vgate iCar Pro, HD Digital Tech II, 24 total) + 110 compat matrix rows + 12 curated notes. `motodiag hardware compat {list,recommend,check,show,note,seed}`. AutoDetector gets `compat_repo=None` kwarg (Phase 139 backward-compat preserved). 57 tests GREEN. Bug fix #1: TestCompatCLI fixture three-layer db_path redirect. Bug fix #2: compat_notes.json `obdlink-cx` → `scantool-obdlink-cx` slug. |
| 146 | Connection troubleshooting + recovery | ✅ | `hardware/connection.py` +446 LoC: `RetryPolicy` Pydantic model (exponential-with-clamp backoff) + `ResilientAdapter` wrapper (retries transient wire ops, never retries `UnsupportedCommandError`/`NoECUDetectedError`/`clear_dtcs`) + `HardwareSession` `retry_policy`/`auto_reconnect` kwargs + `try_reconnect()` helper. AutoDetector `verbose` + `on_attempt` callback kwargs. `MockAdapter.flaky_rate` + `flaky_seed` for deterministic retry tests. `motodiag hardware diagnose` 5-step troubleshooter (port open / ATZ probe / AutoDetector negotiate / VIN read / DTC scan) with mechanic-readable Rich-panel remediation. `--retry`/`--no-retry` on scan/info (default on), clear (default off). 56 tests GREEN. Bug fix #1: `MockAdapter` lazy-import in diagnose `--mock` branch. Bug fix #2: `--retry`/`--simulator` mutex → silent retry=False. |
| 147 | Gate 6 — Hardware integration test | ✅ | **GATE 6 PASSED — Track E closed.** New `tests/test_phase147_gate_6.py` (875 LoC, 8 tests across 3 classes, zero production code). Class A: one big CliRunner workflow — `garage add` → `compat seed/recommend` → `hardware info/scan --simulator` → `hardware log start/list/show/replay/export` → `hardware stream` → `hardware diagnose --mock` → `hardware clear --simulator`. Shared DB fixture + 3 defensive AI mocks + `time.sleep` no-ops. Class B: 4 surface tests verify 9-subcommand registration + subgroup children + `--help` + submodule import graph. Class C: 3 regression tests — subprocess re-runs of Gate 5 + Gate R + tiered schema floor `>= 15/16/17`. 8 tests GREEN. Bug fix #1: `CliRunner(mix_stderr=False)` removed in Click 8.2+. Bug fix #2: `FROM recordings` → `FROM sensor_recordings`. |

## Track F — Advanced Diagnostics (Phases 148–159)

Power features for experienced mechanics. Shifted from 136-147 due to Retrofit track insertion.

| Phase | Title | Status | Notes |
|-------|-------|--------|-------|
| 148 | Predictive maintenance | ✅ | **First Track F phase.** Promotes `advanced` package Scaffold → Active. New `advanced/models.py` (frozen Pydantic v2 `FailurePrediction` + `PredictionConfidence` enum), `advanced/predictor.py` (395 LoC — `predict_failures(vehicle, horizon_days, min_severity, db_path)` with 4-pass candidate retrieval, match-tier scoring exact_model=1.0/family=0.75/make=0.5/generic=0.3, severity-keyed heuristic onset critical=15k/high=30k/medium=50k/low=80k mi, mileage + age scoring bonuses, Forum-tip-precedence `preventive_action` extraction, `verified_by` substring heuristic, horizon/severity filters, stable sort cap 50). `motodiag advanced predict --bike SLUG \| --make/--model/--year/--current-miles [--horizon-days] [--min-severity] [--json]`. Zero migration, zero AI, zero live tokens. 44 tests GREEN. |
| 149 | Wear pattern analysis | ✅ | File-seeded 30-pattern `advanced/wear.py` with overlap-ratio scoring. Mechanic symptom vocabulary ("tick of death" / "chain slap on decel" / "dim headlight"). Substring-either-direction matching. `motodiag advanced wear --bike SLUG --symptoms ...`. 33 tests GREEN. |
| 150 | Fleet management | ✅ | Migration 018: `fleets` + `fleet_bikes` tables. `advanced/fleet_repo.py` (12 CRUD) + `fleet_analytics.py` (Phase 148/149 rollups). `motodiag advanced fleet {create,list,show,add-bike,remove-bike,rename,delete,status}` (8 subcommands). 35 tests GREEN. |
| 151 | Maintenance scheduling | ✅ | Migration 019: `service_intervals` + `service_interval_templates` (44 seeded). `advanced/schedule_repo.py` + `scheduler.py` dual-axis (miles OR months) with month-end clamp. `motodiag advanced schedule {init,list,due,overdue,complete,history}`. 37 tests GREEN. |
| 152 | Service history + monotonic mileage | ✅ | Migration 020: `service_history` + `vehicles.mileage` column. `advanced/history_repo.py` with monotonic mileage bump. `predictor.py` +0.05 bonus when `mileage_source='db'`. `motodiag advanced history {add,list,show,show-all,by-type}`. 35 tests GREEN. |
| 153 | Parts cross-reference | ✅ | Migration 021: `parts` + `parts_xref` tables. `advanced/parts_repo.py` + `parts_loader.py` with OEM ↔ aftermarket catalog. `predictor.py` populates `parts_cost_cents` on FailurePrediction. `motodiag advanced parts {search,xref,show,seed}`. 31 tests GREEN. |
| 154 | OEM Technical Service Bulletins (TSBs) | ✅ | Migration 022: `technical_service_bulletins` with SQL LIKE `model_pattern` + partial unique index. `advanced/tsb_repo.py` (466 LoC) + 44 real HD/Honda/Yamaha entries seeded. Auto-seed on `init_db()`. `predictor.py` `applicable_tsbs` via 4-char token overlap + severity bucket-adjacency. `motodiag advanced tsb {list,search,show,by-make}`. 32 tests GREEN. |
| 155 | NHTSA safety recalls | ✅ | Migration 023: extends `recalls` with nhtsa_id/vin_range/open + new `recall_resolutions` junction. `advanced/recall_repo.py` (603 LoC) with VIN validation + range check + WMI decode + resolutions. `predictor.py` `applicable_recalls` + critical-severity escalation. `motodiag advanced recall {list,check-vin,lookup,mark-resolved}`. 31 tests GREEN. |
| 156 | Comparative diagnostics | ✅ | No migration. `advanced/comparative.py` (709 LoC) two-stage reduction — per-recording summary → percentile across recordings. `--peers-min 5` noisy-stats guard. 200-row cohort cap. `motodiag advanced compare {bike,recording,fleet}`. 34 tests GREEN. |
| 157 | Healthy baselines | ✅ | Migration 024: `baselines` table with per-(make, model, year, pid) percentile statistics aggregated from mechanic-flagged-healthy recordings. `motodiag advanced baseline {show,flag-healthy,rebuild,list}`. 31 tests GREEN. |
| 158 | Sensor drift tracking | ✅ | No migration. `advanced/drift.py` (597 LoC) stdlib mean-of-products linear regression. Flags drifting >5%/30d slow / ≥10%/30d fast. O2 aging / coolant silting / battery decay. Unicode sparkline + CSV export. `predictor.py` opt-in `_apply_drift_bonus` (capped +0.1). `motodiag advanced drift {bike,show,recording,plot}`. 39 tests GREEN. |
| 159 | Gate 7 — Advanced diagnostics integration test | ✅ | **GATE 7 PASSED — Track F closed.** `tests/test_phase159_gate_7.py` (8 tests): end-to-end workflow across all 10 advanced subgroups + surface breadth + Gate 5/6 subprocess re-runs. 3349/3351 full regression passing. Zero new production code. |

## Track G — Shop Management + Optimization (Phases 160–174)

Shop-level features: log bikes in your shop, track issues across the fleet, triage what to fix first, auto-generate parts lists, optimize workflow. Shifted from 148-162 due to Retrofit track insertion.

| Phase | Title | Status | Notes |
|-------|-------|--------|-------|
| 160 | Shop profile + multi-bike intake | ✅ | Migration 025: `shops` + `intake_visits` tables. `shop/shop_repo.py` (337 LoC, 11 fns + hours_json validator) + `shop/intake_repo.py` (481 LoC, guarded `open→closed\|cancelled→(reopen)→open` lifecycle). `cli/shop.py` (1003 LoC) new top-level `motodiag shop` group with 3 subgroups × 22 subcommands — `profile` (5), `customer` (9, first CLI for Phase 113 dormant `crm/`), `intake` (8). 44 tests GREEN. Zero AI. |
| 161 | Work order system | ✅ | Migration 026: `work_orders` table with denormalized shop_id/vehicle_id/customer_id + intake_visit_id FK SET NULL + 4 indexes. `shop/work_order_repo.py` (748 LoC, 14 fns + 7 dedicated lifecycle transitions + guarded `draft→open→in_progress→(on_hold\|completed\|cancelled)→(reopen)→open` + composable list filters). `cli/shop.py` +473 LoC = `motodiag shop work-order {create,list,show,update,start,pause,resume,complete,cancel,reopen,assign,unassign}` (12 subcommands). 47 tests GREEN. Forward-compat bug fix: Phase 160 + Phase 161 rollback tests migrated to `rollback_to_version` pattern after Phase 161 FK broke Phase 160's bare-drop test. |
| 162 | Issue logging + categorization | ✅ | Migration 027: `issues` table (work_order_id FK CASCADE + symptoms/sessions FK SET NULL + self-referencing duplicate_of FK) with **12-category CHECK** (engine/fuel/electrical/cooling/exhaust/transmission/brakes/suspension/drivetrain/tires_wheels/accessories/rider_complaint/other — Domain-Researcher override from default 7) + 4-tier severity + 4-state guarded lifecycle + 5 indexes. `shop/issue_repo.py` (720 LoC, 14 fns + crosswalk dict for Phase 163 AI categorization). `cli/shop.py` +656 LoC = `motodiag shop issue {add,list,show,update,resolve,reopen,mark-duplicate,mark-wontfix,categorize,link-dtc,link-symptom,stats}` (12 subcommands). 42 tests GREEN. mark-wontfix requires audit-trail notes; linked_dtc_code soft-validates to survive seed reloads; duplicate_of cycle prevention via one-hop canonical check. |
| 163 | Repair priority scoring | ✅ | First Track G AI phase. Composes against Phase 162.5 `shop/ai_client.py` (zero direct anthropic imports — anti-regression grep test enforced). New `shop/priority_scorer.py` (311 LoC) + `shop/priority_models.py` (82 LoC). 4-tier rubric (CRITICAL safety / HIGH ridability / MEDIUM service / LOW cosmetic) + wait-time aging + customer-history bonus baked into cached system prompt. Mechanic-intent preservation: AI overwrites work_orders.priority ONLY when confidence > 0.75; below threshold logs to ai_response_cache (kind='priority_score') without DB mutation. Safety override + `--force` escape hatch. Write-back via Phase 161 `update_work_order` whitelist (never raw SQL). Per-call cap 3¢ + session budget 50¢ default. CLI: `motodiag shop priority {score, rescore-all, show, budget}`. 26 tests GREEN; injection seam pattern (`_default_scorer_fn=None`) is canonical Track G AI test convention. Zero schema migration. |
| 164 | Automated triage queue | ✅ | Migration 028: `ALTER TABLE shops ADD COLUMN triage_weights TEXT` (nullable). Pure query-synthesis + deterministic scoring over Phase 161/162/163; soft-guards Phase 165 via `importlib.util.find_spec("motodiag.shop.parts_needs")`. New `shop/triage_queue.py` (365 LoC) — `build_triage_queue` + `ShopTriageWeights` + `TriageItem` + 5 mutators + `ShopTriageError`. Triage formula = priority + wait + parts + urgent_flag - skip_penalty (per-shop tunable). Markers ride on `work_orders.description` via `[TRIAGE_URGENT] ` / `[TRIAGE_SKIP: reason] ` prefix tokens (idempotent, parser-anchored). CLI: `motodiag shop triage {queue, next, flag-urgent, skip, weights}`. 32 tests GREEN. |
| 165 | Parts needed aggregation | ✅ | Migration 029: 3 new tables (work_order_parts + parts_requisitions + parts_requisition_items). Bridges Phase 153 parts catalog (`parts` + `parts_xref`) to Phase 161 work_orders via FK reuse — zero schema duplication. New `shop/parts_needs.py` (605 LoC, 18 fns including 5 CRUD + 3 lifecycle + critical `_recompute_wo_parts_cost` helper that writes back via Phase 161 `update_work_order` whitelist — NEVER raw SQL, verified by mock-patch audit test). **Phase 164 contract satisfied automatically:** `list_parts_for_wo(wo_id, db_path=None)` exported with the exact name 164's soft-guard imports. Immutable requisition snapshots (`build_requisition` freezes header + items at creation; validates wo_ids belong to shop_id). OEM/aftermarket cost columns via `parts_repo.get_xrefs`. CLI: `motodiag shop parts-needs {add, list, consolidate, mark-ordered, mark-received, requisition {create, list, show}}` (8 subcommands). 38 tests GREEN. |
| 166 | Parts sourcing + cost optimization | ✅ | Second Track G AI phase. Composes against Phase 162.5 ShopAIClient (zero direct anthropic imports, anti-regression grep test). Migration 030: single `sourcing_recommendations` audit table. New `shop/sourcing_models.py` (65 LoC) + `shop/parts_sourcing.py` (482 LoC, recommend_source + get_recommendation + sourcing_budget). System prompt baked from Domain-Researcher pricing brief — decision tree + 6-tier vendor taxonomy + counter-intuitive aftermarket wins (Ricks stators, EBC HH pads). Append-only audit log with cache_hit separate from cost_cents. CLI: `motodiag shop sourcing {recommend, show, budget}`. 27 tests GREEN. `optimize_requisition` + `compare` deferred to Phase 169. |
| 167 | Labor time estimation | ✅ | Third Track G AI phase. Composes against Phase 162.5 ShopAIClient (zero direct anthropic imports) + writes back via Phase 161 update_work_order whitelist (zero raw SQL) — both enforced by anti-regression grep tests. Migration 031: `labor_estimates` audit history table with full breakdown + alternatives + environment notes. Math-consistency guard rejects AI output where adjusted ≠ base*(1+skill)*(1+mileage); retry at temp 0.1 on first mismatch. System prompt baked from Domain-Researcher pricing brief (labor norms + per-platform adjustments + skill/mileage multipliers). Reconciliation is pure arithmetic at ±20% threshold. CLI: `motodiag shop labor {estimate, bulk, show, history, reconcile, budget}`. 33 tests GREEN (incl. 2 anti-regression grep tests). |
| 168 | Bay/lift scheduling | ✅ | Migration 032: `shop_bays` + `bay_schedule_slots` tables + 4 indexes. Stdlib-only deterministic scheduling engine in `shop/bay_scheduler.py` (702 LoC): greedy next-free-window auto-assign with level-loading tie-break + overrun detection at 25% buffer + sweep-line conflict detection (≥15min = error) + utilization tracking + `optimize_shop_day(random_seed)` deterministic for per-shop-per-day reproducibility. FK asymmetry: `work_order_id SET NULL` on slots preserves utilization history through WO deletion (load-bearing for Phase 171 analytics). CLI: `motodiag shop bay {add, list, show, deactivate, schedule, reschedule, conflicts, optimize, utilization, calendar}` (10 subcommands). 37 tests GREEN. **Closes Track G deterministic core (161/162/164/165/168) alongside AI phases (163/166/167) + 162.5.** |
| 169 | Revenue tracking + invoicing | ✅ | Micro-migration 033: single `invoices.work_order_id` column + index. **Zero new tables — reuses Phase 118 `invoices` + `invoice_line_items` + `accounting.invoice_repo`.** `shop/invoicing.py` (~496 LoC): `generate_invoice_for_wo` (labor from Phase 167 actual_hours fallback estimated; parts lines from Phase 165 installed+received; tax + shop-supplies pct/flat + optional diagnostic fee stacking), `mark_invoice_paid`, `void_invoice` (enables regen via `-Rn` invoice-number suffix), `get_invoice_with_items`, `list_invoices_for_shop`, `revenue_rollup` (shop-scoped or all-shops). CLI: `motodiag shop invoice {generate, list, show, mark-paid, void, revenue}` (6 subcommands). 32 tests GREEN. **Track G commercial core closes: intake→triage→WO→parts→labor→bay→completion→invoice→revenue all through `motodiag shop *`.** |
| 170 | Customer communication | ✅ | Migration 034: `customer_notifications` table with 4 FKs + 2 CHECK constraints + 3 indexes. `shop/notification_templates.py` (~265 LoC): 23 templates across 10 events × 2-3 channels (email/sms/in_app); content baked from motorcycle-mechanic feedback (first-name recipient, WO# + shop phone everywhere, plain language, prominent totals). `shop/notifications.py` (~510 LoC): 8 public APIs with guarded `pending → sent\|failed\|cancelled` lifecycle; `resend_notification` creates new pending row preserving failure audit. **Queue-only — actual email/SMS delivery deferred to Track J transport.** CLI: `motodiag shop notify {trigger, preview, list, mark-sent, mark-failed, cancel, resend, templates}` (8 subcommands). 32 tests GREEN single-pass. Total shop CLI: 13 subgroups, 96 subcommands. |
| 171 | Shop analytics dashboard | ✅ | Read-only deterministic rollups over Track G state. Zero migrations, zero AI. `shop/analytics.py` (~524 LoC): 10 rollup functions (throughput/turnaround/utilization/overrun/labor-accuracy/top-issues/top-parts/mechanic-perf/customer-repeat) + `dashboard_snapshot` composer that delegates to Phase 168 utilization + Phase 169 revenue without duplicating. Each rollup is a pure function returning a Pydantic summary — Phase 173 can use them as rule conditions. CLI: `motodiag shop analytics {snapshot, throughput, turnaround, utilization, overruns, labor-accuracy, top-issues, top-parts, mechanic, customer-repeat}` (10 subcommands). 31 tests GREEN. Total shop CLI: 14 subgroups, 106 subcommands. |
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
