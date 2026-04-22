# MotoDiag — Project Phase Log

**Project:** moto-diag
**Repo:** https://github.com/Kubanjaze/moto-diag

This is the **project-level** change log. Records updates to the project's architecture, package structure, dependencies, and completion gate status. Per-phase logs live in `docs/phases/{NN}_phase_log.md`.

---

### 2026-04-15 16:00 — Project created
- Created 100-phase roadmap (8 tracks: A–H)
- Initialized monorepo at `C:\Users\Kerwyn\PycharmProjects\moto-diag\`
- GitHub repo: `Kubanjaze/moto-diag`

### 2026-04-15 16:30 — Phase 01 complete
- 8 subpackages created: core, vehicles, knowledge, engine, cli, hardware, advanced, api
- Base models: VehicleBase, DiagnosticSessionBase, DTCCode, 5 enums (ProtocolType, Severity, etc.)
- Config system: pydantic-settings with MOTODIAG_ env prefix
- CLI: Click group with 5 subcommands (diagnose, code, garage, history, info)
- 24 tests passing

### 2026-04-15 17:00 — Documentation restructured
- Created project-level `implementation.md` (project overview doc)
- Created project-level `phase_log.md` (this file)
- Moved Phase 01 docs to `docs/phases/01_implementation.md` and `01_phase_log.md`
- Two-tier doc structure: project-level (root) + per-phase (docs/phases/)

### 2026-04-15 17:30 — Target fleet expanded, roadmap extended to 150 phases
- Expanded target fleet from narrow sport bike focus to full coverage:
  - Honda: added CBR600RR, CBR1000RR, Shadow/VTX/Rebel cruisers, CB standards, VFR V4, Africa Twin, vintage air-cooled
  - Yamaha: added FZ/MT naked, V-Star/Bolt cruisers, VMAX, Ténéré, vintage XS/RD/SR
  - Kawasaki: added Ninja 250/300/400, ZX-12R/14R, H2, Z naked line, Vulcan cruisers, KLR650, vintage KZ/GPz
  - Suzuki: added SV650/1000, V-Strom, Bandit, GSX-S, Boulevard cruisers, DR-Z400/DR650, vintage GS
- Track B expanded from 16 phases (13–28) to 66 phases (13–78) — every bike family gets its own phase
- Roadmap extended from 100 to 150 phases total
- All downstream tracks renumbered: C (79–95), D (96–108), E (109–122), F (123–134), G (135–144), H (145–150)
- Completion gates updated to match new phase numbers, added Gate 7 for API

### 2026-04-15 18:00 — Phase 02 complete
- Config system: Environment enum (dev/test/prod), 7 new fields, 3 field validators
- Added ensure_directories(), lru_cache singleton, reset_settings()
- CLI: `motodiag config show/paths/init` subcommand group
- core package status: Scaffold → Active

### 2026-04-15 18:20 — Phase 03 complete
- Database: 6 tables (vehicles, dtc_codes, symptoms, known_issues, diagnostic_sessions, schema_version)
- Connection manager: WAL mode, foreign keys, auto-rollback, Row factory
- Schema versioning (v1) for future migrations
- 5 indexes for query performance

### 2026-04-15 18:30 — Phase 04 complete
- Vehicle registry: full CRUD (add, get, list, update, delete, count)
- Filtered listing by make/model/year with LIKE queries
- vehicles package status: Scaffold → Active

### 2026-04-15 18:35 — Documentation remediation
- Phases 02 and 03 had incomplete implementation.md (v1.0 never updated to v1.1) and stub phase_log.md files
- Corrected: all completed phase docs now have full v1.1 with Results, Verification Checklist [x], and timestamped log entries
- Updated project implementation.md with Phase History rows, DB table inventory, CLI commands, package statuses
- Rule reinforced: no phase is complete until docs are fully fleshed out and pushed

### 2026-04-15 19:30 — Phase 05 complete
- DTC repository: CRUD + search with make-specific fallback chain
- JSON loader: file and directory import for bulk DTC loading
- Sample data: 20 generic OBD-II P-codes + 20 Harley-Davidson specific codes
- CLI: `motodiag code <DTC>` now functional with Rich Panel output
- knowledge package status: Scaffold → Active

### 2026-04-15 20:00 — Phase 06 complete
- Symptom repository: CRUD + search with category and keyword filtering
- Starter taxonomy: 40 symptoms across starting, idle, engine, cooling, exhaust, electrical, fuel, brakes, drivetrain, vibration, suspension, noise categories
- Extended loader.py with load_symptom_file()
- Each symptom links to related_systems for cross-system diagnostics

### 2026-04-15 20:30 — Phase 07 complete
- Diagnostic session lifecycle: 9 functions covering full OPEN → CLOSED workflow
- Symptom/fault code accumulation with duplicate prevention
- Diagnosis with confidence scoring, severity, repair steps
- Cost tracking fields (ai_model_used, tokens_used) ready for Track C

### 2026-04-15 21:30 — Phase 08 complete
- Known issues repository: 6 functions (add, get, search, find_by_symptom, find_by_dtc, count)
- 10 Harley-Davidson starter issues with forum-level fixes and part numbers
- Year range queries for spanning model generations
- Extended loader.py with load_known_issues_file()
- knowledge package now has 3 repos: dtc_repo, symptom_repo, issues_repo

### 2026-04-15 22:00 — Phase 09 complete
- Unified search engine: search_all() queries vehicles, DTCs, symptoms, known issues, sessions
- CLI: `motodiag search <query>` with --make filter, Rich grouped output
- 5 stores searched from one entry point

### 2026-04-16 00:00 — Phase 10 complete
- Structured logging: setup_logging(), get_logger(), reset_logging()
- Session lifecycle events logged (create, diagnose, close)
- Console + optional file handler, configurable log level

### 2026-04-16 00:15 — Phase 11 complete
- Enhanced conftest.py: 7 shared fixtures (fresh_db, populated_db, sample vehicles)
- Full regression suite: 136/136 tests passed in 4.92s
- Zero regressions across all 10 phase test files

### 2026-04-16 00:30 — Phase 12 complete — GATE 1 PASSED
- End-to-end integration test: 10-step mechanic diagnostic workflow verified
- Cross-store linkage: symptom → known issue → DTC connections confirmed
- `motodiag db init` CLI: initializes DB + loads all starter data
- Full regression: 140/140 tests passed
- **Track A (Core Infrastructure) COMPLETE — all 12 phases done**
- Gate 1 status: PASSED — ready for Track B (Vehicle Knowledge Base)

### 2026-04-16 22:30 — Phases 54-66 complete — Kawasaki + Suzuki finished
- Kawasaki completed (phases 54-56): dual-sport KLR650/KLX/Versys, vintage KZ/GPz, electrical + FI dealer mode
- Suzuki completed (phases 57-66): GSX-R600/750/1000/1100, SV650/1000, V-Strom, Bandit, GSX-S/Katana, cruisers, dual-sport
- 130 new issues added (30 Kawasaki + 100 Suzuki), 78 new tests
- **Track B status: 54 of 66 phases complete (phases 13-66)**
- Total knowledge base: 550 issues across 5 manufacturers
- Remaining: phases 67-78 (Suzuki vintage + cross-platform systems)

### 2026-04-17 01:40 — Phases 67-78 complete — GATE 2 PASSED
- Suzuki completed (phases 67-69): vintage GS/Katana, electrical + C-mode, cross-model patterns
- Cross-platform systems (phases 70-77): carbs, FI, charging, starting, ignition, cooling, brakes, drivetrain
- Phase 78: Gate 2 integration test — 21 tests, 650+ issues, all 5 makes, cross-platform verified
- 120 new issues (30 Suzuki + 80 cross-platform + 10 extra from agent overlap), 69 new tests
- **Track B (Vehicle Knowledge Base) COMPLETE — all 66 phases done (13-78)**
- **Gate 2 PASSED** — query any target bike → get DTCs, symptoms, known issues, fixes
- Ready for Track C (AI Diagnostic Engine)

### 2026-04-16 05:35 — Phase 86 complete — Cost estimation
- New module: `src/motodiag/engine/cost.py` — pure-calculation cost estimator
- 4 Pydantic models (ShopType, CostLineItem, CostEstimate, PartCost), 1 class (CostEstimator), 1 standalone function (format_estimate)
- CostEstimator.estimate(), estimate_from_diagnosis(), compare_shop_types() — bridges DiagnosisItem to customer-facing cost estimates
- 25 tests in `tests/test_phase86_cost.py`
- Engine `__init__.py` updated with cost module exports
- implementation.md bumped to v0.3.9

### 2026-04-16 05:40 — Phase 87 complete — Safety warnings + critical alerts
- New module: `src/motodiag/engine/safety.py` — rule-based safety hazard detection
- AlertLevel enum (4 levels), SafetyAlert Pydantic model, SafetyChecker class
- 18 SAFETY_RULES (regex-based): brakes, fuel, stator fire, stuck throttle, head gasket, overheating, electrical short, steering, wheel bearings, chain, tires, oil, coolant, exhaust, valves, air filter, spark plugs, brake fluid
- 12 REPAIR_SAFETY_KEYWORDS: fuel handling, lifting, brake work, battery, coolant, exhaust, chain, springs, wiring
- check_diagnosis(), check_symptoms(), check_repair_procedure() + format_alerts()
- 37 tests in `tests/test_phase87_safety.py`
- Engine `__init__.py` updated with safety module exports
- implementation.md bumped to v0.4.0

### 2026-04-17 08:00 — Phases 79-95 complete — GATE 3 PASSED
- Track C (AI Diagnostic Engine) COMPLETE — all 17 phases done
- 16 engine modules: client, symptoms, fault_codes, workflows, confidence, repair, parts, cost, safety, history, retrieval, correlation, intermittent, wiring, service_data, evaluation
- Phase 95 Gate 3 integration test: 39 tests verifying full symptom-to-repair pipeline
- Full regression: 1163/1163 tests passing in 4m 26s
- Engine package: 16 modules, 580+ engine-specific tests, zero live API calls (all mocked or pure logic)
- **Track C COMPLETE — Gate 3 PASSED** — full diagnostic pipeline functional
- Ready for Track C2 (Media Diagnostic Intelligence) or Track D (CLI + User Experience)

### 2026-04-17 10:00 — Phases 96-108 complete — GATE 4 PASSED
- Track C2 (Media Diagnostic Intelligence) COMPLETE — all 13 phases done
- 12 media modules: audio_capture, spectrogram, sound_signatures, anomaly_detection, video_frames, vision_analysis, fusion, comparative, realtime, annotation, reports, coaching
- Audio pipeline: capture → preprocess → spectrogram → signatures → anomaly detection → comparative
- Video pipeline: frame extraction → Claude Vision analysis → annotation → reports
- Multimodal fusion: weighted combination of audio + video + text + DTC evidence
- Phase 108 Gate 4 integration test: 24 tests verifying full media pipeline
- Full regression: 1575/1575 tests passing in 5m 10s
- **Track C2 COMPLETE — Gate 4 PASSED** — full media diagnostic pipeline functional
- 3-tier subscription model noted as architecture requirement (individual, shop, company)
- Ready for Track D (CLI + User Experience)

### 2026-04-17 11:00 — Phase 109 complete — CLI foundation + 3-tier subscription
- Created `cli/subscription.py`: SubscriptionTier enum, TierFeatures, TIER_LIMITS for 3 tiers ($19/$99/$299/mo)
- Created `cli/registry.py`: CommandRegistry singleton for modular command registration
- Dual enforcement modes: SOFT (dev default) vs HARD (Track H+ activates via MOTODIAG_PAYWALL_MODE)
- New CLI: `motodiag tier` (show current tier) + `motodiag tier --compare` (3-tier ASCII table)
- 41 tests, 1616/1616 total regression passing
- Subscription architecture now foundational — all downstream Tracks D-T use it

### 2026-04-17 12:00 — ROADMAP EXPANSION — 198 phases → 352 phases, 11 tracks → 21 tracks
- User committed to full expansion scope: brand coverage, electric, scooters, specialized workflows, business infrastructure, reference data, UX, AI, launch, operational
- **Inserted 12-phase Retrofit Track (110-121)** between Track C2 and Track D remainder, to refactor codebase for expansion before new tracks build
  - Retrofit adds: vehicle/protocol taxonomy, DTC schema expansion, auth layer, CRM foundation, workflow substrate, i18n substrate, feedback hooks, reference tables, billing/accounting/inventory/scheduling substrate, media annotations, sound signature expansion, Gate R
- **Renumbered Tracks D-J** (shifted by +12 from phase 122 onward):
  - Track D (remainder): 110-121 → 122-133 (Gate 5)
  - Track E: 122-135 → 134-147 (Gate 6)
  - Track F: 136-147 → 148-159 (Gate 7)
  - Track G: 148-162 → 160-174 (Gate 8)
  - Track H: 163-172 → 175-184 (Gate 9) — hard paywall activates
  - Track I: 173-192 → 185-204 (Gate 10)
  - Track J: 193-198 → 205-210
- **Appended 10 new expansion tracks (K-T, phases 211-352):**
  - Track K — European Brand Coverage (211-240, 30 phases): BMW, Ducati, KTM, Triumph, Aprilia, MV Agusta
  - Track L — Electric Motorcycles (241-250, 10 phases): HV safety, Zero, LiveWire, Energica, Damon, BMS, inverter, regen, thermal
  - Track M — Scooters & Small Displacement (251-258, 8 phases): Vespa, Grom/Ruckus, Kymco/SYM, CVT, small electrical
  - Track N — Specialized Workflows (259-272, 14 phases): PPI, tire service, crash/insurance, track prep, winterization, break-in, emissions, valve/brake/suspension/chain service
  - Track O — Business Infrastructure (273-292, 20 phases): Stripe, CRM, booking, accounting, inventory, warranty/recall, 5 vendor integrations, VIN decoder, multi-currency, financial reporting
  - Track P — Reference Data Library (293-302, 10 phases): Clymer/Haynes citations, exploded diagrams, failure library, video index, per-model torque/fluid/schematic/tool/service data
  - Track Q — Extended UX Affordances (303-317, 15 phases): multi-user auth, voice-first, print/labels, barcode scan, photo annotation, Spanish/French/German, AR placeholder, accessibility, dark mode, shortcuts, dashboards, workflow recording
  - Track R — Advanced AI Capabilities (318-327, 10 phases): human-in-loop learning, tuning recs, predictive maintenance expansion, fleet anomaly, customer draft, image similarity, repair success prediction, knowledge graph, continuous learning
  - Track S — Launch + Business Layer (328-342, 15 phases): billing, signup, onboarding, Mitchell 1/ShopKey/ALLDATA migration, ToS/liability, certification, community, referrals, promo codes, enterprise sales, SLA dashboard
  - Track T — Operational Infrastructure (343-352, 10 phases): Sentry, support, cloud backup, multi-location, real-time sync, audit log, feature flags, A/B testing, admin panel
- 18 new packages planned: auth, crm, billing, accounting, inventory, scheduling, workflows, i18n, reference, feedback, ai_advanced, launch, ops
- Gates: Gate R (retrofit), Gates 5-20 (tracks D-T)
- Next: execute Part 2 — auto-iterate through 12 retrofit phases (110-121) before any new tracks begin

### 2026-04-17 17:20 — Retrofit Phase 115 complete — i18n substrate
- Migration 008: `translations` table with composite PK `(locale, namespace, key)` + 2 indexes, 45 English strings seeded (11 cli + 12 ui + 11 diagnostics + 11 workflow). Rollback drops the table cleanly.
- New package `src/motodiag/i18n/`: `Locale` enum (7 ISO 639-1 codes — en/es/fr/de/ja/it/pt), `Translation` model, `t()` translator with fallback chain locale → en → `[namespace.key]` + `{placeholder}` string interpolation, env-var-driven `current_locale/set_locale`, 8 repo functions (get/set/delete/list/import/list_locales/count/locale_completeness).
- Substrate only — English-only content. Track Q phases 308-310 populate Spanish/French/German via `import_translations()` from JSON files.
- Schema v7 → v8. 40 new tests. Full regression: 1841/1841 passing (7:21 runtime). Zero regressions. Forward-compat pattern maintained (all schema version assertions use `>= 8`).
- Implementation.md → v0.5.1 (Phase 115 row added to Phase History, `translations` row added to Database Tables, `i18n` package status Planned → Complete).

### 2026-04-17 17:55 — Retrofit Phase 116 complete — feedback/learning hooks substrate
- Migration 009: `diagnostic_feedback` (12 cols) + `session_overrides` (8 cols) tables. FK CASCADE on session, SET DEFAULT on user (preserves training signal if user deleted). 4 indexes. Rollback drops both.
- New package `src/motodiag/feedback/`: `FeedbackOutcome` enum (correct/partially_correct/incorrect/inconclusive), `OverrideField` enum (6 fields), `DiagnosticFeedback` + `SessionOverride` Pydantic models, 8 repo functions (submit/get/list/count × feedback; record/get/count × overrides), `FeedbackReader` read-only hook class with `iter_feedback` generator, `get_accuracy_metrics`, `get_common_overrides`.
- Feedback records are immutable once submitted — no update/delete API (preserves training signal integrity). Writes go through feedback_repo only; FeedbackReader is read-only by design.
- Substrate only — Track R phases 318-327 build the actual learning loop on top. `get_accuracy_metrics()` already produces the primary accuracy signal Track R phase 327 (continuous learning) needs.
- Schema v8 → v9. 26 new tests. Full regression: 1867/1867 passing (8:58 runtime). Zero regressions.
- Implementation.md → v0.5.2 (Phase 116 row, 2 new table rows, `feedback` package status Planned → Complete).

### 2026-04-17 18:25 — Retrofit Phase 117 complete — reference data tables
- Migration 010: 4 new tables (`manual_references`, `parts_diagrams`, `failure_photos`, `video_tutorials`) with 8 indexes. `parts_diagrams.source_manual_id` ON DELETE SET NULL. `failure_photos.submitted_by_user_id` ON DELETE SET DEFAULT (system user id=1). Rollback drops all 4 in FK-safe order.
- New package `src/motodiag/reference/`: 4 enums (ManualSource 5, DiagramType 4, FailureCategory 7, SkillLevel 4), 4 Pydantic models, 4 repo modules (manual/diagram/photo/video) × 5 CRUD functions each = 20 total.
- Year-range filter pattern (`year_start <= target AND year_end >= target`, NULL = universal) reused from `known_issues` — now the de-facto knowledge-layer query convention used by 5 tables.
- Tables empty by design — Phase 117 is substrate only. Track P phases 293-302 populate Clymer/Haynes citations, per-model torque data, failure photo library, video tutorial index.
- Schema v9 → v10. 28 new tests. Full regression: 1895/1895 passing (8:26 runtime). Zero regressions.
- Implementation.md → v0.5.3 (Phase 117 row, 4 new table rows, `reference` package status Planned → Complete).

### 2026-04-17 19:30 — Retrofit Phase 118 complete — ops substrate (billing/accounting/inventory/scheduling)
- Largest single retrofit phase. Migration 011: 9 new tables (subscriptions, payments, invoices, invoice_line_items, vendors, inventory_items, recalls, warranties, appointments) + 14 indexes. FK strategy: CASCADE on user/customer/vehicle/invoice parents; SET NULL on vendor/repair_plan/mechanic references.
- 4 new packages (~1700 LoC, 16 files):
  - `src/motodiag/billing/`: SubscriptionTier/SubscriptionStatus/PaymentStatus enums, Subscription + Payment models, 11 repo functions with Stripe column pre-wiring
  - `src/motodiag/accounting/`: InvoiceStatus/InvoiceLineItemType enums, Invoice + InvoiceLineItem models, 11 repo functions including `recalculate_invoice_totals(tax_rate)`
  - `src/motodiag/inventory/`: CoverageType enum, 4 models (InventoryItem/Vendor/Recall/Warranty), 4 repo modules with 25+ functions including `adjust_quantity(delta)`, `items_below_reorder()`, `list_recalls_for_vehicle(make, year)`, `increment_claim_count()`
  - `src/motodiag/scheduling/`: AppointmentType/AppointmentStatus enums, Appointment model, 9 repo functions including `cancel_appointment(reason)`, `complete_appointment(actual_end)`, `list_upcoming(from_iso)`, `list_for_user(mechanic_id)`
- Stripe column names (`stripe_customer_id`, `stripe_subscription_id`, `stripe_payment_intent_id`) match Stripe's own naming — Track O 273 Stripe integration becomes pure plug-in with zero schema changes.
- Subscriptions.tier column mirrors Phase 109 MOTODIAG_SUBSCRIPTION_TIER env var — Track H 178 switches enforcement to DB-backed.
- Schema v10 → v11. 37 new tests. Full regression: 1932/1932 passing (10:08 runtime). Zero regressions.
- Implementation.md → v0.5.4 (Phase 118 row, 9 new table rows, 4 package statuses Planned → Complete).

### 2026-04-17 20:05 — Retrofit Phase 119 complete — photo annotation layer
- Migration 012: `photo_annotations` table with 3 indexes (image_ref, failure_photo_id, created_by_user_id). FK CASCADE on failure_photos, SET DEFAULT on users. Rollback drops table.
- New module `src/motodiag/media/photo_annotation.py`: AnnotationShape enum (circle/rectangle/arrow/text), PhotoAnnotation Pydantic model with 3 validators: coord bounds [0.0, 1.0], `#RRGGBB` hex regex with auto-uppercase, size bounds [-1.0, 1.0] (supports negative arrow deltas).
- New module `src/motodiag/media/photo_annotation_repo.py`: 8 functions (add/get/list_for_image/list_for_failure_photo/count/update/delete/bulk_import). `update_annotation` uses SQL `CURRENT_TIMESTAMP` literal for `updated_at`.
- Dual-mode annotation: FK-linked annotations CASCADE on failure_photo delete; orphan annotations (image_ref only, no FK) survive — supports both formal failure-photo library workflow AND ad-hoc mechanic notes on phone photos.
- Coordinate normalization (0.0–1.0 floats) survives image resize/crop/pixel-density differences. Track Q phase 307 builds the canvas overlay renderer.
- Schema v11 → v12. 22 new tests. Full regression: 1954/1954 passing (9:44 runtime). Zero regressions.
- Implementation.md → v0.5.5 (Phase 119 row + `photo_annotations` table row).

### 2026-04-17 20:07 — Scope change: Phase 122 expanded for photo-based bike intake
- User requested mid-retrofit: photo → auto-populate make/model/year/engine_cc for friction-free onboarding.
- Placement: folded into existing Phase 122 (was "Vehicle garage management") rather than inserting a new phase — photo-based intake is the same endpoint (add a bike to garage), just an alternate UX path. Keeps numbering clean across 12+ downstream Track D phases.
- Phase 122 now scoped: Click CLI garage commands + `src/motodiag/intake/` package with `vehicle_identifier.py` reusing Phase 101 Claude Vision. Default Claude Haiku 4.5, escalate to Sonnet if confidence < 0.5. Image sha256 cache, 1024px max dim, VIN fallback. Per-tier caps: individual 20/mo, shop 200/mo, company unlimited. 80%-of-cap budget alert.
- ROADMAP.md updated; memory entry `project_motodiag_photo_bike_id.md` records scope + cost envelope decisions.

### 2026-04-17 20:45 — Retrofit Phase 120 complete — engine sound signature library expansion
- No migration (pure in-memory dict expansion). Extended `src/motodiag/media/sound_signatures.py`:
  - 4 new EngineType enum members (11 total): ELECTRIC_MOTOR, DUCATI_L_TWIN, KTM_LC8_V_TWIN, TRIUMPH_TRIPLE
  - 4 new SIGNATURES entries with physics-grounded frequencies, ≥4 characteristic_sounds each, diagnostic notes
  - New helper `motor_rpm_to_whine_frequency(motor_rpm, pole_pairs)` — Zero SR/F (4 pole pairs → 200 Hz @ 3000 RPM), LiveWire (8 pole pairs → 400 Hz @ 3000 RPM)
- Electric motor signature reinterprets firing_freq_* fields as motor whine fundamental (documented). Idle_rpm_range=(0,0), cylinders=0. Key diagnostic markers: inverter carrier tone, gear whine shift under load, contactor clicking patterns.
- Ducati L-twin signature explicitly documents dry clutch rattle as **NORMAL** — prevents mechanic misdiagnosis. Also covers desmo valve click, cam belt hum on pre-Panigale V2.
- 3 Phase 98 test fixes for forward-compat: `test_all_engine_types_defined` (== → issubset), `test_signature_fields_populated` and `test_estimate_rpm_roundtrip` (ELECTRIC_MOTOR exempted from combustion-specific assertions via `continue`). Original 7 signatures still under full strict assertions.
- 38 new tests. Full regression: 1992/1992 passing (11:00 runtime). Zero regressions after forward-compat fixes.
- Implementation.md → v0.5.6 (Phase 120 row added to Phase History).
- Key finding: existing SoundSignature model handles non-combustion powertrains without architectural change — validates Track L electric phase feasibility. Forward-compat pattern (previously only schema versions) now formally extends to enum membership.

### 2026-04-17 21:15 — 🎉 RETROFIT COMPLETE — GATE R PASSED
Phase 121 executed the Retrofit Integration Test. **All 10 Gate R tests pass, full regression 2002/2002 (10:43 runtime), zero regressions across the entire retrofit track.**

**Retrofit totals (phases 110-121):**
- 12 phases, 10 migrations (003-012), 23 new tables, 12 new packages (auth, crm, workflows, i18n, feedback, reference, billing, accounting, inventory, scheduling, + 2 media-package additions)
- **386 new tests** (1616 → 2002 passing end-to-end)
- Zero regressions sustained across all 12 phases
- Schema version 2 → 12

**Gate R findings:**
1. Migration 005's rollback SQL intentionally does not DROP the ALTER-added `user_id` column (pre-3.35 SQLite lacks DROP COLUMN, documented as harmless). Consequence: in-place rollback-and-replay is unsafe. Fresh init is fully deterministic — verified by `test_two_fresh_dbs_have_identical_table_sets`.
2. All 12 retrofit packages import cleanly both as subprocess (`python -m motodiag.cli.main --help`) and in-process.
3. End-to-end workflow exercises every package on a shared DB — catches cross-package FK integrity, CASCADE behavior, tier enforcement, i18n fallback, and invoice recalc-with-tax.

**Forward-compat patterns formalized during retrofit:**
- `>=` for schema version assertions (not `==`)
- `issubset` / `in` for enum membership tests (not `==`)
- `continue` / conditional branching for powertrain-specific skips (electric motor in combustion-only loops)

**Next**: Track D resumes at Phase 122 — vehicle garage management + photo-based bike intake with Claude Haiku 4.5 (scope locked: make/model/year/engine_cc, tiered caps individual 20/shop 200/company unlimited).

Implementation.md → v0.6.0 (major version bump — Gate R closes the retrofit track, marks architectural completion).

### 2026-04-17 22:10 — Phase 122 complete — Vehicle garage management + photo-based bike intake
First post-retrofit user-facing phase. **Retrofit pays off immediately**: `subscriptions.tier` from Phase 118 is load-bearing for photo-ID quota enforcement; `users` from Phase 112 is the FK target of `intake_usage_log`. Integrated cleanly in one phase with zero schema surprises — validates the substrate-first approach of phases 110-121.

- Migration 013: `intake_usage_log` table (user_id FK CASCADE, kind enum, model_used, confidence, image_hash, tokens + cost tracking, 3 indexes).
- New package `src/motodiag/intake/`: IdentifyKind enum, VehicleGuess + IntakeUsageEntry + IntakeQuota models, IntakeError + QuotaExceededError exceptions, VehicleIdentifier orchestrator class.
- Vision pipeline: quota check → preprocess (1024px resize via Pillow + JPEG q=85 + alpha-to-white flatten) → sha256 on preprocessed bytes → cache lookup → Haiku 4.5 call → parse JSON (markdown-fence tolerant, one retry on malformed) → Sonnet escalation if confidence < 0.5 → usage log → 80%-of-cap budget alert on threshold crossing (not continuous).
- Privacy: image bytes never persist, only sha256 hash.
- Cost controls: Haiku 4.5 by default (~$0.003-0.005/call), Sonnet escalation only when needed, cache returns zero-token cached guess on re-uploads.
- Tier caps: individual 20/mo, shop 200/mo, company unlimited. Enforced via QuotaExceededError raised pre-call.
- CLI: `garage` is now a `@click.group` with 4 subcommands (add/list/remove/add-from-photo) + new `intake` group with 2 subcommands (photo/quota). Pretty rich.Panel output for VehicleGuess preview.
- Pillow added as optional dep: `motodiag[vision] = ["pillow>=10.0"]`. Graceful RuntimeError with install hint if missing.
- Build-phase fix: `test_garage_remove` initially failed because `init_db()` reads `settings.db_path` from `@lru_cache`-cached Settings. Resolved by adding `cli_db` fixture that calls `reset_settings()` after monkeypatching `MOTODIAG_DB_PATH` env var.
- 49 new tests, all vision calls mocked via `make_vision_mock` factory → **zero live API tokens burned during build or regression**.
- Full regression: 2051/2051 passing (12:05 runtime). Zero regressions.
- Implementation.md → v0.6.1 (Phase 122 row added + `intake` package row + `intake_usage_log` table row).
- Next: Track D resumes at Phase 123 (interactive diagnostic session).

### 2026-04-17 22:45 — Phase 123 complete — Interactive diagnostic session (CLI)
Second post-retrofit user-facing phase. **No migration** — reuses Phase 03 `diagnostic_sessions` table. The substrate keeps paying off: every column Phase 123 needed (`diagnosis`, `confidence`, `severity`, `repair_steps`, `ai_model_used`, `tokens_used`) was already there. Phase 118's `subscriptions.tier` is now load-bearing a second time — Phase 122 used it for quota; Phase 123 uses it for model access.

- New `src/motodiag/cli/diagnose.py` (~450 LoC): `CONFIDENCE_ACCEPT_THRESHOLD`, `MAX_CLARIFYING_ROUNDS`, `_resolve_model` (tier gating), `_load_vehicle`, `_load_known_issues`, `_parse_symptoms`, `_default_diagnose_fn` (production wrapper), `_run_quick`, `_run_interactive` (Q&A loop), `_persist_response` (with `_FakeUsage` shim for accumulated rounds), `_render_response`, `register_diagnose(cli_group)`.
- 4 new CLI commands: `diagnose start` (interactive Q&A), `diagnose quick` (one-shot), `diagnose list` (rich table, status filter), `diagnose show <id>` (rendered panel).
- Q&A loop termination: confidence ≥ 0.7 OR no additional_tests OR MAX_CLARIFYING_ROUNDS (3) OR empty input OR "skip"/"stop"/"done".
- Tier gating: individual → Haiku only; shop/company → Sonnet available via `--model sonnet`. HARD paywall mode raises `ClickException` with upgrade hint; SOFT mode falls back to Haiku with yellow warning.
- One session row per user-visible interaction; interactive rounds accumulate `tokens_used`. Keeps `diagnostic_sessions` readable as workflow history rather than API audit log (`intake_usage_log` is the audit log).
- Build-phase fix: test helper `make_response` originally used a nested class; Python class bodies don't close over enclosing-function params. Switched to `types.SimpleNamespace`.
- `_default_diagnose_fn` injected via `patch()` in tests — zero live API tokens burned.
- 39 new tests. Full regression: 2090/2090 passing (11:43 runtime). Zero regressions.
- Implementation.md → v0.6.2.
- Next: Track D resumes at Phase 124 (Fault code lookup command).

### 2026-04-17 23:50 — Phase 124 complete — Fault code lookup CLI
Third post-retrofit user-facing phase. **No migration** — reuses Phase 03 `dtc_codes` + Phase 111 `dtc_category_meta` substrates. Replaces Phase 01's inline `code` command (a 50-line DB-only scaffold) with a full orchestration module and three explicit modes. Track D is now halfway through the CLI surface that paying users will actually touch.

- New `src/motodiag/cli/code.py` (392 LoC): `_lookup_local` (make-specific → generic fallback chain), `_classify_fallback` (classify_code heuristic → dtc_row-shaped dict), `_default_interpret_fn` (production wrapper around `FaultCodeInterpreter`), `_run_explain` (known-issues loader + injected interpret call), `_render_local` (DB row or fallback with yellow banner), `_render_explain` (7-section AI result renderer with safety-critical callout), `_render_category_list` (table), `register_code(cli_group)` (with legacy-command eviction guard).
- Modified `src/motodiag/cli/main.py`: deleted the Phase 01 inline `code` command, added `from motodiag.cli.code import register_code`, called `register_code(cli)` alongside `register_diagnose(cli)`.
- Three CLI modes in one command: (1) `motodiag code P0115` — default DB lookup, zero tokens; (2) `motodiag code --category hv_battery` — list DTCs in a category, zero tokens; (3) `motodiag code P0115 --explain --vehicle-id N` — AI root-cause analysis, tier-gated.
- Tier gating reused from Phase 123: individual → Haiku only; shop/company → Sonnet available via `--model sonnet`. HARD raises; SOFT falls back with warning. `_resolve_model`, `_load_vehicle`, `_load_known_issues`, `_parse_symptoms` all imported from `cli.diagnose` (no copy-paste).
- Fallback chain ensures the mechanic always gets something back: DB make-specific → DB generic → `classify_code()` heuristic. The heuristic output gets a yellow "No DB entry — heuristic classification only" banner and a hint to re-run with `--explain`.
- `_default_interpret_fn` injected via `patch("motodiag.cli.code._default_interpret_fn", fn)` in every AI-hitting test — zero live tokens burned across the full Phase 124 test suite.
- Phase 05 `test_code_help` regression: updated to invoke `motodiag code --help` instead of `motodiag code` with no args, since the new command correctly raises `ClickException` on missing args per Phase 124's spec. Documented under Deviations.
- 33 new tests across 8 classes. Full regression: 2123/2123 passing (~9:58 runtime). Zero regressions.
- Implementation.md → v0.6.3.
- Next: Track D continues — history browse, export, etc.

### 2026-04-17 23:58 — Phase 125 complete — Quick diagnosis mode (bike slug + shortcut)
First post-Phase-124 and first agent-delegated build. Pure UX sugar on Phase 123 `diagnose quick` — no new substrate, no migration. Also surfaced a limitation in the "persistent agent pool" pattern I'd just codified: the `SendMessage` tool referenced in Claude Code's Agent docs is not actually available in this runtime. Each `Agent()` call is a fresh spawn; pool-reuse via message-continuation doesn't work. Correction to CLAUDE.md follows.
- Extended `src/motodiag/cli/diagnose.py` (+180 LoC): `SLUG_YEAR_MIN`/`SLUG_YEAR_MAX` constants, `_parse_slug` (last-hyphen year split with bounds), `_resolve_bike_slug` (4-tier match: exact model → exact make → partial model LIKE → partial make LIKE, deterministic by `created_at, id`), `_list_garage_summary` (UX helper for unknown-slug error body).
- Added `--bike SLUG` option on `diagnose quick` alongside existing `--vehicle-id INT`. Both-given → ID wins with yellow warning. Neither-given → clear error. Unknown slug → error listing garage (or "Garage is empty" variant).
- New top-level `motodiag quick "<symptoms>" [--bike | --vehicle-id] ...` via `register_quick(cli_group)`. Pulls `diagnose quick` from the already-registered subgroup and delegates via Click `ctx.invoke()` — single source of truth.
- Wired `register_quick(cli)` into `cli/main.py` after `register_diagnose(cli)`.
- **Agent delegation process**: Builder-A produced clean code across `cli/diagnose.py`, `cli/main.py`, and a 34-test file. Sandboxed runtime blocked Python for the agent, so it shipped without self-testing. Architect ran Phase 125 tests as part of trust-but-verify: all 34 passed. Finalization (docs, regression, commit) done by Architect since no SendMessage to dispatch Finalizer-A.
- Deviations: 4-tier slug match (plan said 3-tier) — added partial-LIKE tiers so `cbr929` → CBR929RR works. Ambiguous-match warning skipped — deterministic `ORDER BY created_at, id` is sufficient. Test count 34 vs planned 15-20 due to thorough boundary coverage.
- Schema v13 unchanged. Full regression: 2157/2157 passing, zero regressions. Zero live tokens.
- Implementation.md → v0.6.4.
- Next: correct CLAUDE.md's agent-pool section re: SendMessage reality; then Phase 126.

### 2026-04-18 00:30 — Phase 126 complete — Diagnostic report output (export to file)
Second agent-delegated phase. No migration, no new package. Extended `cli/diagnose.py` (+200 LoC) with three pure formatters and three new options on the existing `diagnose show` command.
- New: `_format_session_text`, `_format_session_json`, `_format_session_md` (pure `dict → str`), 4 private utility helpers (`_short_ts`, `_fmt_list`, `_fmt_conf`, `_write_report_to_file`).
- Extended `diagnose show` with `--format [terminal|txt|json|md]` default `terminal`, `--output PATH` optional, `--yes` to skip overwrite confirmation.
- Behavior matrix: terminal+no-output = Phase 123 Rich Panel unchanged; terminal+PATH = warning printed, no file written; txt/json/md to stdout if no PATH, to file if PATH.
- JSON includes `"format_version": "1"` as first key via ordered dict construction — consumers can reject unknown versions when schema evolves.
- File writing: UTF-8 + `newline=""` for Windows CRLF safety, `os.makedirs(parent, exist_ok=True)`, `click.confirm` for overwrite unless `--yes`, PermissionError and IsADirectoryError surface as ClickException.
- Pure-formatter architecture sets up Phase 132 (export + sharing) to reuse `_format_session_md` as input to a markdown → PDF pipeline with zero refactoring.
- **Agent delegation**: Builder-A shipped clean code in one pass. Sandbox blocked Python for the agent; Architect ran 22 phase tests as trust-but-verify — all passed in 4.31s. Finalization done in-process since SendMessage unavailable. One design simplification from plan: `--format terminal --output PATH` prints warning instead of using Rich `console.record` — keeps Phase 123 terminal path byte-for-byte unchanged.
- Full regression (running when this entry was written): expected 2179/2179 passing, zero regressions.
- Implementation.md → v0.6.5.
- Next: Phase 127 (session history browser).

### 2026-04-18 01:00 — Phase 127 complete — Session history browser
Third agent-delegated phase. Migration 014 adds nullable `notes` column to `diagnostic_sessions` (schema v13 → v14); no new table. Extends Phase 123's `diagnose list` into a proper history browser with 7 new filter options, plus new `diagnose reopen` and `diagnose annotate` commands.
- `core/session_repo.py` (+60 LoC): `list_sessions` kwargs `vehicle_id/search/since/until/limit`; new `reopen_session`, `append_note`, `get_notes` functions. Search is case-insensitive via `LOWER(diagnosis) LIKE LOWER('%..%')`.
- `cli/diagnose.py` (+150 LoC): `diagnose list --vehicle-id/--make/--model/--search/--since/--until/--limit`; `diagnose reopen <id>` (CLI checks status first for warning — repo runs UPDATE unconditionally); `diagnose annotate <id> <text>` (append-only with `[YYYY-MM-DDTHH:MM]` prefix).
- Phase 126 formatters updated: terminal rendering gets new Notes panel; `_format_session_text` and `_format_session_md` gain `## Notes` section when notes present; `_format_session_json` picks up the new field automatically via `dict(row)`.
- Builder-A UX improvement: bare `--until YYYY-MM-DD` is expanded to `T23:59:59` in CLI layer so it means "through end of day".
- Softened one assertion in `tests/test_phase123_diagnose.py` (exact match → substring) for forward-compat with the new empty-filter wording.
- **Agent delegation**: Builder-A shipped clean code; sandbox blocked Python for the agent. Architect ran 28 phase tests as trust-but-verify and caught ONE FK constraint failure: the test helper `_seed_diagnosed_session` passed arbitrary vehicle_ids without seeding matching `vehicles` rows. Fixed with `INSERT OR IGNORE INTO vehicles` when explicit vehicle_id is given. All 28 tests passed on retry. Trust-but-verify rule earning its keep.
- 28 new tests. Full regression (running): expected 2207/2207 passing, zero regressions.
- Implementation.md → v0.6.6.
- Next: Phase 128 (Knowledge base browser).

### 2026-04-18 01:35 — Phase 128 complete — Knowledge base browser (CLI)
Fourth agent-delegated phase. No migration, no new package. Adds a `motodiag kb` command group with 5 subcommands covering the knowledge-base browse use cases: list (structured filters), show (full detail), search (free-text), by-symptom, by-code.
- `knowledge/issues_repo.py` (+20 LoC): new `search_known_issues_text(query, limit, db_path)` with case-insensitive LIKE across `title`, `description`, and `symptoms` JSON column. Empty-query short-circuits to `[]` (doesn't return everything).
- New `src/motodiag/cli/kb.py` (~320 LoC): `register_kb(cli_group)` attaches `@cli_group.group("kb")` with 5 subcommands. Rendering helpers: `_year_range_str`, `_truncate`, `_render_issue_table`, `_render_bullet_list`, `_render_issue_detail`.
- `cli/main.py`: one-line wire-up (`register_kb(cli)` between `register_quick` and `register_code`).
- Design choices: `--symptom` on `kb list` is a Python post-filter (existing `search_known_issues` signature stays clean); `kb by-code <dtc>` force-uppercases DTC input; `kb search ""` rejected with ClickException to prevent "return everything" surprises.
- **Agent delegation**: Builder-A shipped clean code with zero iterative fixes. Sandbox blocked Python for the agent. Architect ran 26 phase tests as trust-but-verify and caught ONE word-wrap issue in a Rich Table assertion (`"Stator failure"` was split across lines in narrow terminal). Fixed by adding `monkeypatch.setenv("COLUMNS", "200")` to the `cli_db` fixture. All 26 passed on retry.
- 26 new tests across 7 classes. Zero AI calls. Zero live tokens.
- Full regression (running): expected 2233/2233 passing, zero regressions.
- Implementation.md → v0.6.7.
- Next: Phase 129 (Rich terminal UI / progress / colors enhancements).

### 2026-04-18 02:10 — Phase 129 complete — Rich terminal UI polish (theme + progress)
Fifth agent-delegated phase. No migration, no new commands. New `cli/theme.py` centralizes what was previously scattered: Console construction, severity/status/tier color coding, icon constants, spinner context for AI calls.
- New `src/motodiag/cli/theme.py` (~230 LoC): `get_console()` singleton + `reset_console()`, `SEVERITY_COLORS` / `STATUS_COLORS` / `TIER_COLORS` maps, style + markup helpers, 5 icon constants, `status(msg)` spinner context manager. Respects `NO_COLOR` and `COLUMNS` env vars.
- Migrated 10+ inline `Console()` sites across `cli/main.py`, `cli/subscription.py`, `cli/diagnose.py`, `cli/code.py`, `cli/kb.py`. Zero remaining inline Console construction in the cli package after this phase.
- Wired progress spinners around long-running AI operations: `diagnose quick` and `diagnose start` (around `_run_quick`/`_run_interactive`), `code --explain` (around `_run_explain`), `garage add-from-photo` and `intake photo` (around `VehicleIdentifier.identify`).
- Canonicalized severity coloring: dropped `code.py`'s local `_SEVERITY_COLORS` map (was `"critical": "red bold"`; now canonical `"red"` from theme.SEVERITY_COLORS). `kb.py`'s issue-detail header severity gained colorization (implicit consistency improvement).
- Added autouse fixture `_reset_console_around_every_test` alongside `cli_db`'s reset for defense-in-depth across all test classes.
- **Agent delegation**: Builder-A's cleanest pass so far — 20 tests passed first run in 1.29s, zero iterative fixes, zero assertion softening, zero fixture tweaks. Sandbox blocked Python (6th time), Architect ran trust-but-verify locally.
- 20 new tests. Zero AI calls. Zero live tokens.
- Full regression (running): expected 2253/2253, zero regressions.
- `Textual` full TUI explicitly deferred — out of scope for this polish phase; can be a future dedicated phase if demand materializes.
- Implementation.md → v0.6.8.
- Next: Phase 130 (Shell completions + shortcuts).

### 2026-04-18 02:40 — Phase 130 complete — Shell completions + shortcuts
Sixth agent-delegated phase. No migration, no new package. Adds `motodiag completion [bash|zsh|fish]` for tab-completion setup, three dynamic DB-backed completers for runtime data, and four short command aliases.
- New `src/motodiag/cli/completion.py` (~260 LoC): `register_completion(cli)` + three completer callbacks (`complete_bike_slug`, `complete_dtc_code`, `complete_session_id`) + install-hint wrapping around Click's built-in `get_completion_class(shell).source()`.
- Defensive completers: all three return `[]` on any DB-access failure (fresh install, missing tables, flaky network mount). Tab-completion never crashes a mechanic's shell.
- Dynamic completers wired into 6 existing option/argument sites: `--bike` on `diagnose quick` + top-level `quick`, `session_id` on `diagnose show`/`reopen`/`annotate`, and the positional `code` argument on `motodiag code`.
- Short aliases in `cli/main.py`: `d`→diagnose, `k`→kb, `g`→garage, `q`→quick. Uses `copy.copy(cmd)` to clone the canonical command, then sets `hidden=True` on the CLONE. Builder-A refinement over the plan — setting `hidden=True` on the canonical itself would have hidden it from `--help` everywhere.
- **Agent delegation**: Builder-A shipped clean code. Sandbox blocked Python (7th time); Architect's trust-but-verify caught ONE failure — `click.shell_completion.CompletionItem` isn't accessible via attribute access (must be imported from submodule). Fixed with `from click.shell_completion import CompletionItem` at top of `completion.py` and `sed`-replacement of all references. All 18 phase tests passed on retry.
- 18 new tests across 4 classes. Zero AI calls. Zero live tokens.
- Full regression (running): expected 2271/2271, zero regressions.
- Implementation.md → v0.6.9.
- Next: Phase 131 (Offline mode / AI response caching).

### 2026-04-18 03:20 — Phase 131 complete — Offline mode + AI response caching
Seventh agent-delegated phase. Largest post-retrofit phase so far — migration + 2 new modules + 2 engine integration points + 3 CLI integration points + 30 tests.
- Migration 015 adds `ai_response_cache` (schema v14 → v15): SHA256-keyed cache_key UNIQUE, kind ('diagnose'/'interpret'), model_used, response_json, tokens in/out, cost_cents, timestamps, hit_count. 2 indexes.
- New `src/motodiag/engine/cache.py` (~200 LoC): `_make_cache_key` SHA256 of canonical-JSON with kind prefix (prevents cross-path collisions); `get_cached_response` (pre-bump read + post-bump hit_count write); `set_cached_response` INSERT OR REPLACE; `purge_cache(older_than_days=None)` for stats-purge-clear; `get_cache_stats()`; `cost_dollars_to_cents` helper for float→int conversion.
- New `src/motodiag/cli/cache.py` (~130 LoC): `register_cache(cli)` + 3 subcommands. `cache stats` shows rich Panel with rows/hits/dollars saved. `cache purge --older-than 30` with confirm prompt (skipped with `--yes`). `cache clear` nukes all (prompts).
- Integrated into `DiagnosticClient.diagnose()` and `FaultCodeInterpreter.interpret()`: `use_cache: bool = True` + `offline: bool = False` kwargs. Cache hit reconstructs response + zero-token TokenUsage. Offline + miss raises `RuntimeError("Offline mode: no cached response...")`. Cache failures logged but never raised.
- `--offline` CLI flag wired on `diagnose quick`, `diagnose start`, `code --explain`. RuntimeError caught, red message, exit 1.
- **Agent delegation**: Builder-A shipped clean code, 30 phase tests passed first run in 5.37s — zero fixes. Sandbox blocked Python (8th phase in a row), Architect ran trust-but-verify. Builder's unprompted refinements (all good improvements): `mode="json"` on `model_dump()` for enum round-trip correctness; `TypeError` backward-compat fallback in `_run_*` keeps Phase 123/124 test doubles working; corrupted-JSON rows treated as cache miss (caller refreshes).
- 30 new tests across 8 classes. Zero AI calls. Zero live tokens.
- Full regression (running): expected 2301/2301, zero regressions.
- Implementation.md → v0.7.0 (minor version bump — cache substrate is a significant capability addition, and this closes out the bulk of Track D's user-facing features).
- Next: Phase 132 (Export + sharing — PDF/HTML diagnostic reports).

### 2026-04-18 04:05 — Phase 132 complete — Export + sharing (HTML + PDF)
Eighth agent-delegated phase. No migration, no new commands. Extends Phase 126's `--format` mechanism with `html` and `pdf` output on `diagnose show`, and brings `kb show` to parity with `diagnose show` (now also supports md/html/pdf output).
- New shared `src/motodiag/cli/export.py` (~260 LoC): `format_as_html` via `markdown` package, `format_as_pdf` via `xhtml2pdf.pisa`, `write_binary` for PDF file writes. Inline-CSS HTML wrapper with `@page` for print, serif font, table borders. Lazy-imports + install-hint ClickException on missing optional deps.
- Extended `cli/diagnose.py`: `--format` Choice now includes `html`/`pdf`; PDF requires `--output` (binary-to-stdout useless).
- Extended `cli/kb.py`: new `_format_issue_md`/`_format_issue_text` helpers (sparse-field tolerant — skip empty sections); new `--format [terminal|txt|md|html|pdf]`/`--output`/`--yes` options. Terminal default preserves Phase 128 behavior.
- New `motodiag[export]` optional extras in `pyproject.toml` (markdown + xhtml2pdf).
- Markdown is the pivot format: `_format_session_md` (Phase 126) and `_format_issue_md` (Phase 132) are the single source of truth; HTML is markdown + CSS; PDF is HTML + page layout. Any future format (DOCX, EPUB) plugs in at the same pivot.
- **Agent delegation**: Builder-A shipped 25 tests all passing first run in 11.94s — zero iterative fixes, zero Architect corrections. Builder's unprompted refinements: HTML-entity escape on title; `_format_issue_text` aliases `_format_issue_md` per plan permission; `_write_report_to_file` re-imported to avoid duplication.
- Pre-dispatch prep: Architect pip-installed `markdown` + `xhtml2pdf` before sending to Builder so full regression passes `TestExtrasAvailable` checks.
- 25 new tests across 6 classes. Zero AI calls. Zero live tokens.
- Full regression (running): expected 2326/2326, zero regressions.
- Implementation.md → v0.7.1.
- Next: Phase 133 — **Gate 5 integration test** (full mechanic workflow through CLI). Closes out Track D.

### 2026-04-18 05:00 — Phase 133 complete — Gate 5 PASSED, Track D closed
Ninth agent-delegated phase. **GATE 5 PASSED** — the mechanic CLI track (phases 109 + 122-132) is fully integrated. Pure observation test file, zero new production code.
- New `tests/test_phase133_gate_5.py` with 7 tests across 3 classes.
  - `TestMechanicEndToEnd` (1 big test): `CliRunner`-driven 19-command workflow on a shared DB fixture — `garage add`/`list` → `motodiag quick "won't start"` → `diagnose list`/`show [--format md/html/pdf --output]` → `diagnose annotate`/`reopen` → `code P0115 [--explain]` → `kb list`/`search "stator"`/`show --format md` → `cache stats` → `intake quota` → `tier --compare` → `completion bash`. State flows through the whole workflow (session created → annotated → reopened → exported) — any cross-step regression gets caught. 3 AI mocks (`_default_diagnose_fn`/`_default_interpret_fn`/`_default_vision_call`) patched at import time.
  - `TestCliSurface` (4 tests): all 14 canonical top-level commands registered, 4 hidden aliases (`d`/`k`/`g`/`q`) present but omitted from `--help`, expected subcommands per subgroup, subprocess `--help` exits 0.
  - `TestRegression` (2 tests): Phase 121's Gate R workflow still passes + schema >= v15 + all `motodiag.cli.*` submodules import cleanly.
- Consolidated 15-20 planned tests into 7 cohesive ones (same pattern as Gate R's 20 to 10). CliRunner over subprocess for workflow tests (10-100x faster, cleaner exception surface); subprocess reserved for the `--help` smoke test only.
- Seeded DTC P0115 + one known-issue entry in the shared fixture to keep `code P0115` and `kb search "stator"` hermetic.
- Builder-A clean first pass, no iterative fixes. Sandbox blocked Python (expected), Architect ran trust-but-verify: 7 tests passed in 6.04s.
- Zero new production code (pure observation over the Phase 109-132 CLI surface), zero schema changes, zero live tokens burned.
- Full regression: 2333/2333, zero regressions.
- Implementation.md to v0.7.2.
- **Track D closed.** Track E (hardware) is next.

### 2026-04-18 06:00 — Phase 134 complete — Track E opens: OBD protocol abstraction layer
First Track E phase. New `hardware/protocols/` package — library-only scaffolding that subsequent Track E phases (135-139) build against.
- New package `src/motodiag/hardware/protocols/` with 4 new modules + `__init__.py` exporting 8 public names.
  - `base.py` — `ProtocolAdapter` ABC with 8 abstract methods: `connect(port, baud)`, `disconnect`, `is_connected` (concrete property with `getattr(self, "_is_connected", False)` fallback so subclasses only flip the backing attribute), `read_dtcs`, `clear_dtcs -> bool`, `read_pid(pid) -> Optional[int]`, `read_vin`, `send_raw(service, data)`, `get_protocol_name`.
  - `models.py` — `ProtocolConnection` frozen + `extra="forbid"` Pydantic model (port/baud/protocol_name/connected_at); `DTCReadResult` with `mode="before"` validator that uppercases DTC codes before type validation; `PIDResponse` with paired value+unit presence validator.
  - `exceptions.py` — `ProtocolError` base + `ConnectionError` + `TimeoutError` (both intentionally shadow built-ins with clear docstring callouts) + `UnsupportedCommandError` with custom `__init__(command: str)` carrying `.command` attribute (the only custom init — `ConnectionError`/`TimeoutError` stay plain).
- Wave 1 of the parallel-pipeline dispatch pattern: Planner then Builder then Architect phase-test-verify then Finalizer, with many agents in flight simultaneously across phases that do not share files. Builder-A delivered clean first pass, 49 tests passed locally in 0.35s.
- **Package inventory update**: `hardware` moves from Scaffold to Active. No migration, no CLI, no AI.

### 2026-04-18 06:30 — Phases 135-138 complete — Wave 2: four concrete protocol adapters
Parallel-pipeline Wave 2 shipped four concrete `ProtocolAdapter` implementations — one per bike ecosystem era — in parallel, all building against Phase 134's abstraction. Each adapter is a standalone module with its own test file; no shared state between them (which is what enables the parallel dispatch).
- **Phase 135 — ELM327** (`hardware/protocols/elm327.py` ~584 LoC, 52 tests). Wraps ELM327 chip via pyserial. Full AT-command handshake (`ATZ`/`ATE0`/`ATL0`/`ATSP0`), multi-frame response tolerance scanning for `43`/`41 XX` service echo, mode 03 DTC parsing, mode 09 VIN assembly. Unlocks ~80% of aftermarket OBD dongles.
- **Phase 136 — CAN/ISO 15765** (`hardware/protocols/can.py` ~470 LoC, 38 tests). ISO 15765-4 over `python-can` (any backend). Hand-rolled ISO-TP (not `python-can-isotp`). Modes 03 DTCs / 04 clear / 09 VIN / read_pid. Added `can = ["python-can>=4.0"]` optional extras. Target: 2011+ Harley Touring, modern CAN bikes.
- **Phase 137 — K-line/KWP2000** (`hardware/protocols/kline.py` ~670 LoC, 44 tests). ISO 14230-4 over pyserial. Target: 90s/2000s Japanese sport-bikes + vintage Euro. Slow-baud wakeup, checksum, local-echo cancellation, strict timing. Services 0x10/0x11/0x14/0x18/0x1A/0x21. Write services deliberately out of scope for tune-writing safety.
- **Phase 138 — J1850 VPW** (`hardware/protocols/j1850.py` ~600 LoC, 27 tests). Pre-2011 Harley via bridge devices (Scan Gauge II / Daytona Twin Tec / Dynojet Power Commander / Digital Tech II clones). Multi-ECM DTC read merges ECM (P-codes) + BCM (B-codes) + ABS (C-codes). `read_pid` raises `NotImplementedError` (Phase 141); `read_vin` raises `UnsupportedCommandError` (pre-2008 HDs lacked Mode 09).
- All four adapters reconciled their concrete signatures to match Phase 134's ABC contract (same `connect(port, baud)` shape, `read_pid -> Optional[int]`, `clear_dtcs -> bool`). Consistent deviation pattern across the wave — documented once, applied everywhere.
- All Wave 2 builds were clean first passes. 161 tests across the wave, all passed locally.
- Dependencies: `pyproject.toml` adds `can = ["python-can>=4.0"]` optional extras (CAN backend).

### 2026-04-18 07:00 — Phase 139 complete — ECU auto-detection + handshake (Wave 3)
Wave 3 of Track E: glue layer over all four Phase 134-138 protocol adapters. New `src/motodiag/hardware/ecu_detect.py` (~460 LoC).
- `AutoDetector(port, make_hint=None, timeout_s=2.0, baud=None)` tries protocol adapters in priority order keyed by bike make hint until one negotiates a live session:
  - Harley -> J1850 first (covers pre-2011 FLH/FXR/Sportster) then CAN (covers 2011+ Touring)
  - Japanese (honda/yamaha/kawasaki/suzuki) -> CAN then KWP2000 then ELM327
  - European (ducati/bmw/ktm/triumph) -> CAN then KWP2000
  - No hint -> try all four in default order (CAN, KWP2000, J1850, ELM327)
- Per-protocol `_build_adapter` factory handles non-uniform adapter kwargs — each of the four adapters has a different constructor signature (CAN uses `channel/bitrate/request_timeout+multiframe_timeout`, K-line uses `port/baud/read_timeout`, J1850 uses `port/baudrate/timeout_s`, ELM327 uses `port/baud/timeout`). Plan flagged this as a Risk; confirmed and solved.
- Lazy per-adapter imports so missing optional deps (`python-can`, `pyserial`) only surface when that protocol is actually attempted. Means the detector does not require all four optional extras installed.
- `identify_ecu()` best-effort probes VIN (mode 09 PID 02) + ECU part number (mode 09 PID 04) + software version (mode 09 PID 06) + supported OBD modes (mode 01 PID 00). Each probe is independent — VIN failure does not prevent ECU ID lookup.
- `_decode_vin` handles both the `49 02 01` echo-prefixed form and the stripped response form; ASCII decode strips padding bytes; returns `None` if the decoded string is not exactly 17 chars (prevents bogus truncation).
- `NoECUDetectedError(port, make_hint, errors=[(name, exception), ...])` subclass of `ProtocolError` carries programmatic error list for introspection — callers can log which adapters failed with what.
- Zero live hardware — all 31 tests use `MagicMock` adapters. Passed locally in 0.25s.
- Phase 140 (hardware CLI `motodiag connect/scan`) picks up `AutoDetector` for user-facing flows.

### 2026-04-18 07:30 — Track E substrate closed (phases 134-139) + Gate 5 consolidated
Summary of the 7-phase Track D to E transition:
- **Gate 5 PASSED** at Phase 133. Track D closed.
- **Track E substrate shipped** at Phases 134-139: protocol ABC + 4 concrete adapters (ELM327/CAN/K-line/J1850) + ECU auto-detector. `hardware` package Active.
- **Test count**: 2326 -> 2574 (+248 tests across 7 phases).
- **New dependency**: `python-can>=4.0` (optional, behind `motodiag[can]`).
- **Schema version**: unchanged at v15 — Track E is library-only until Phase 140 lands the CLI surface.
- **Next up**: Phase 140 (fault code read/clear + hardware CLI `motodiag connect/scan`) wires the Phase 139 detector into user-facing flows.
- Implementation.md to v0.7.2.

### 2026-04-18 08:30 — Phase 140 complete — Hardware CLI scan/clear/info (first user-facing Track E phase)
Tenth agent-delegated phase. **Builder-A's cleanest pass yet** — no sandbox block, Builder ran the tests before reporting: 40 passed locally in 21.24s, zero iterative fixes. Architect's trust-but-verify reproduced 40/40 in 24.52s.

**The phase that turns hardware from library code into a shippable feature** — a mechanic can now plug an OBD dongle into a serial port and pull DTCs from a bike via `motodiag hardware scan --port COM3 --bike harley-glide-2015`. Or test the full flow without hardware via `--mock`.

- **CLI surface**: 3 new subcommands under `motodiag hardware`:
  - `hardware scan --port COM3 [--bike SLUG | --make harley] [--baud] [--timeout] [--mock]` — auto-detect + Mode 03 DTC read + Rich table with Code/Description/Category/Severity/Source columns (3-tier enrichment: db_make → db_generic → classifier heuristic).
  - `hardware clear --port COM3 [--bike|--make] [--yes] [--mock]` — yellow safety warning panel ("do NOT clear before diagnosis is complete") + confirm prompt + Mode 04 clear + green/red outcome panels.
  - `hardware info --port COM3 [--bike|--make] [--mock]` — `identify_ecu()` → Rich Panel with Protocol / VIN / ECU Part # / SW Version / Supported OBD Modes.
- **5 new files** (2012 LoC total):
  - `hardware/mock.py` (249 LoC) — `MockAdapter(ProtocolAdapter)` concrete class with configurable state (dtcs/vin/ecu_part/sw_version/supported_modes/clear_returns/protocol_name/fail_on_connect/vin_unsupported kwargs). All 8 ABC methods satisfied plus additive `identify_info()` helper. Docstring explicitly marks it "not for production — substrate for `--mock` flag and Phase 144 simulator."
  - `hardware/connection.py` (255 LoC) — `HardwareSession` context manager with three construction paths: real (`AutoDetector.detect()`), mock (`MockAdapter` with defaults), `adapter_override` (test injection with pre-configured adapter). `__exit__` swallows disconnect failures per Phase 134 ABC contract — never masks propagating exception.
  - `knowledge/dtc_lookup.py` (147 LoC) — `resolve_dtc_info(code, make_hint) -> DTCInfo` with 3-tier fallback. `source` discriminator checks returned row's `.make` field to accurately distinguish make-specific hits from `get_dtc()`'s internal cascade downgrades (so `db_make` means "actually matched the make column," not "we passed make to the query").
  - `cli/hardware.py` (556 LoC) — `register_hardware(cli)` + the 3 subcommands. Reuses `_resolve_bike_slug` from `cli.diagnose`, `get_console()` / `format_severity` / `ICON_*` from `cli.theme`. `[MOCK]` yellow badge when `--mock`. `NoECUDetectedError` handler unpacks `errors=[(name, exception), ...]` into a per-adapter breakdown with actionable "hint: use --mock to test without hardware" footer — not a raw traceback.
  - `tests/test_phase140_hardware_cli.py` (805 LoC, 40 tests) — 6 classes: MockAdapterContract×5 (ABC + state round-trip), HardwareSession×6 (mock/override/disconnect-on-exception/error propagation), ScanCommand×10 (happy path + enrichment variants + error paths), ClearCommand×8 (safety + prompt flow + outcomes), InfoCommand×6 (all-fields/VIN-None/empty-modes), DTCLookup×5 (source discriminator semantics).
- **File modified**: `cli/main.py` — added `register_hardware(cli)` call alongside the existing `register_*` registrations.
- **Deviations (all documented in 140_implementation.md v1.1):**
  1. DTC lookup extraction deferred: `cli/code.py`'s `_lookup_local` + `_classify_fallback` are entangled with `_render_local`'s populated fields (`common_causes`/`fix_summary`/`code_format`) beyond `DTCInfo`'s schema. Clean extraction would require renderer changes too. `cli/hardware.py` uses the new helper; `cli/code.py` unchanged; TODO noted for Phase 145 cleanup.
  2. `MockAdapter.identify_info()` is additive beyond the ABC — not a contract change. Session method delegates to this on mock path, `AutoDetector.identify_ecu()` on the real path.
  3. `_resolve_bike_slug` imported as underscore-private from `motodiag.cli.diagnose` — matches existing cross-module reuse patterns.
  4. `source` discriminator checks row's `.make` post-query (nuance: the repo's own fallback meant `db_make` → `db_generic` downgrade had to live in `resolve_dtc_info`).
  5. `classify_code` returns `(code_format, system_description)` — Builder put `system_description` (not `code_format`) into `DTCInfo.category` for meaningful UI text.
- **No migration, no new DB tables, no AI.** Schema stays at v15. Zero live tokens.
- Full regression (running): expected 2614/2614, zero regressions.
- Implementation.md to v0.7.3.
- **Next**: Phase 141 (live sensor data streaming — RPM / TPS / coolant / battery V / O2 via `motodiag hardware stream`).

### 2026-04-18 18:15 — Phases 141-148 complete — Track E CLOSED via Gate 6 + Track F OPENED

**Sixteen consecutive phases shipped in one session (133-148).** Full regression `pytest tests/ -q` → **3003 passed in 647.23s (0:10:47)**. Implementation.md bumped 0.7.3 → 0.8.0.

**Phase 141 — Live sensor data streaming (Wave 1):** new `hardware/sensors.py` (SAE J1979 Mode 01 PID catalog with 23 entries + `SensorSpec` dataclass + `SensorReading` Pydantic v2 model + `SensorStreamer` one-shot iterator + `parse_pid_list`). `cli/hardware.py` +400 LoC: `stream` subcommand with Rich `Live(auto_refresh=False)` loop + `_StreamCsvWriter` wide-format CSV append. `mock.py` +34 LoC: `pid_values` additive kwarg (None preserves Phase 140 byte-identity). Error taxonomy: `TimeoutError` per-PID → `status=timeout` cell + retry next tick; `ConnectionError`/other `ProtocolError` → re-raise → red panel + exit 1. 42 tests GREEN. Bug fix #1: hz-throttle test expectation (generator post-yield sleep semantics).

**Phase 142 — Data logging + recording (Wave 2):** migration 016 (v15→v16). `sensor_recordings` + `sensor_samples` + 4 indexes. `hardware/recorder.py` (864 LoC — `RecordingManager` with SQLite/JSONL split at 1000 rows, transparent merge via (captured_at, pid_hex, raw) signature dedup, linear-interp `DiffReport` via stdlib `bisect`). `cli/hardware.py` +1300 LoC: `log {start,stop,list,show,replay,diff,export,prune}` 8-subcommand subgroup. Export: CSV wide / JSON / Parquet (lazy pyarrow). `parquet = [pyarrow>=15.0]` optional extra. 52 tests GREEN on first trust-but-verify — no bug fixes needed.

**Phase 143 — Textual TUI dashboard (Wave 3):** new `hardware/dashboard.py` (1282 LoC — lazy Textual import with stubs for missing-dep. `DashboardApp(App)` with 3-column CSS grid + BINDINGS ctrl+q/ctrl+r/d/1-6. `GaugeWidget`/`PidChart`/`DTCPanel`/`StatusBar`. `LiveDashboardSource` wraps Phase 141 SensorStreamer iterator; `ReplayDashboardSource` walks Phase 142 RecordingManager). `hardware dashboard` subcommand. `dashboard = [textual>=0.40,<1.0]` optional extra. 46 tests GREEN. Bug fix #1: `GaugeWidget.render()` used `numeric` (unclamped) in display; fixed to `clamped`.

**Phase 144 — Hardware simulator (Wave 1):** new `hardware/simulator.py` (1212 LoC — SimulationClock + 9 Pydantic event models discriminated-union on `action` + Scenario aggregate with cross-event validators + ScenarioLoader from_yaml/from_recording/list_builtins + `SimulatedAdapter(ProtocolAdapter)` sibling to MockAdapter). 10 built-in YAML scenarios. `hardware simulate {list,run,validate}` subgroup + `--simulator SCENARIO` opt-in on scan/clear/info. `pyyaml>=6` base dep + `package-data` YAML assets. 81 tests GREEN. Bug fix #1: `_coerce_pid` bare-number → decimal (JSON round-trip identity).

**Phase 145 — Adapter compatibility database (Wave 2):** migration 017 (v16→v17). 3 tables (`obd_adapters` + `adapter_compatibility` + `compat_notes`) + 6 indexes. `hardware/compat_repo.py` (814 LoC CRUD + ranking + filter hook). `compat_loader.py` (206 LoC idempotent). Seed data: 24 real adapters across 5 price tiers + 110 compat matrix rows + 12 curated notes. `hardware compat {list,recommend,check,show,note add,note list,seed}` 7-subcommand subgroup. AutoDetector `compat_repo=None` kwarg (Phase 139 backward-compat). 57 tests GREEN after 2 bug fixes. Bug fix #1 (Builder-145-Fix): fixture three-layer db_path redirect. Bug fix #2 (Architect): `obdlink-cx` → `scantool-obdlink-cx` slug drift between adapters.json and compat_notes.json.

**Phase 146 — Retry/recover + diagnose troubleshooter (Wave 3):** `connection.py` +446 LoC (RetryPolicy + ResilientAdapter + retry_policy/auto_reconnect kwargs + try_reconnect). `ecu_detect.py` +62 LoC (`verbose`/`on_attempt` kwargs after compat_repo). `mock.py` +91 LoC (`flaky_rate`/`flaky_seed` with _roll_flaky; flaky_rate=0.0 preserves Phase 140 byte-identity). `cli/hardware.py` +1089 LoC: `--retry`/`--no-retry` on scan/info (on) and clear (off) + `hardware diagnose` 5-step troubleshooter. 56 tests GREEN after 2 bug fixes. Bug fix #1: MockAdapter missing import in diagnose `--mock` branch. Bug fix #2: `--retry`/`--simulator` mutex too strict → silent `retry=False`.

**Phase 147 — Gate 6 (Track E CLOSED):** single new `tests/test_phase147_gate_6.py` (875 LoC, 8 tests across 3 classes, zero production code). Class A `test_full_hardware_flow`: one big CliRunner workflow (garage add → compat seed/recommend → hardware info/scan --simulator → log start/list/show/replay/export → stream → diagnose --mock → clear --simulator) on shared DB + 3 defensive AI mocks + time.sleep no-op patches. Class B: 4 surface tests (9-subcommand registration, subgroup children, --help, submodule imports). Class C: 3 regression (subprocess Gate 5 + Gate R + tiered schema floor). 8 tests GREEN after 2 bug fixes. Bug fix #1: `CliRunner(mix_stderr=False)` removed in Click 8.2+. Bug fix #2: `FROM recordings` wrong — Phase 142 table is `sensor_recordings`.

**Phase 148 — Track F kickoff (predictive maintenance):** promotes `advanced` package Scaffold → Active. `advanced/models.py` (frozen Pydantic v2 FailurePrediction + PredictionConfidence). `advanced/predictor.py` (395 LoC — predict_failures with 4-pass retrieval, match-tier scoring exact_model=1.0/family=0.75/make=0.5/generic=0.3, severity-keyed heuristic onset critical=15k/high=30k/medium=50k/low=80k mi, mileage + age scoring bonuses, Forum-tip-precedence preventive_action extraction, verified_by substring heuristic, horizon/severity filters). `cli/advanced.py` (281 LoC — `predict --bike SLUG | --make/--model/--year/--current-miles`). 44 tests GREEN on first trust-but-verify. Zero migration, zero AI, zero live tokens.

**Updates to this implementation.md + ROADMAP.md:**
- Implementation version 0.7.3 → 0.8.0.
- Package Inventory: `hardware` → Complete (Track E closed); `advanced` → Active (Phase 148); `auth`/`crm` stale "Planned" → Complete (Audit-Agent-3 finding).
- Database Tables: added sensor_recordings, sensor_samples, obd_adapters, adapter_compatibility, compat_notes. Schema version noted as v17.
- CLI Commands: full rewrite by track with 20+ previously-missing commands documented. Hidden aliases d/k/g/q noted.
- Dependencies: added pyyaml base, python-can optional, pyarrow optional, textual optional.
- Phase History rows for 141-148.
- Completion Gates: Gate 6 ✅ (Track E closed).
- ROADMAP: Phases 141-148 flipped 🔲 → ✅ with rich completion summaries. Track E header annotated "✅ COMPLETE".

**Bug-fix discipline honored per CLAUDE.md peak-efficiency mode:** 9 total bug fixes across phases, each documented with Issue/Root cause/Fix/Files/Verified in the respective phase's phase_log.md + committed separately where practical.

**Next session:** Track F continues (phases 149-159: wear pattern analysis / fleet management / maintenance scheduling / service history / cross-referencing / TSB+recall integration / comparison / baseline / drift detection / Gate 7).

### 2026-04-19 12:15 — Track F closed, Gate 7 passed (v0.9.0)

**Summary:** Wave 1a (Phases 149, 150, 156, 158) shipped earlier today. Wave 1b (Phases 151, 152, 153, 154, 155, 157) + Gate 7 (Phase 159) shipped this cycle.

**Track F (Phases 148-159) complete.** `advanced` package promoted from Active → **Complete**. 11 subgroups under `motodiag advanced`: `predict, wear, fleet, schedule, history, parts, tsb, recall, compare, baseline, drift`.

**New DB tables (migrations 018-024):** `fleets`, `fleet_bikes`, `service_intervals`, `service_interval_templates`, `service_history`, `parts`, `parts_xref`, `technical_service_bulletins`, `recall_resolutions`, `baselines`. Plus `vehicles.mileage` column (Phase 152) + extension of existing `recalls` table with nhtsa_id/vin_range/open (Phase 155). Schema bumped from v17 → **v24**.

**Predictor cross-wiring:** Phase 148's `predict_failures()` now emits enriched `FailurePrediction` objects with `applicable_tsbs` (Phase 154), `applicable_recalls` (Phase 155), and `parts_cost_cents` (Phase 153) populated opportunistically from whatever migrations have landed. Drift bonus (Phase 158) and DB-sourced mileage bonus (Phase 152) layer cleanly into the confidence score.

**Gate 7 passed:** `tests/test_phase159_gate_7.py` (8 tests, 92s runtime): end-to-end workflow exercising all 10 advanced subgroups on a shared DB + surface breadth + subprocess Gate 5/Gate 6 re-runs. 3349/3351 full regression passing.

**Bug fixes landed this cycle (each logged in its phase's phase_log.md):**
- Phase 152 #1: Test fixture saturation — stator exact-model issue saturated score clamp, rewrote to family-make tier for observable +0.05 DB bonus delta.
- Phase 154 #1: Builder-154 rate-limited before test file created; Architect wrote 528-LoC test suite directly.
- Phase 154 #2: Missing `_render_tsb_table` + `_render_tsb_panel` renderer helpers in `cli/advanced.py`; Architect added definitions modeled after Phase 155's `_render_recall_table`.
- Phase 158 #1: `_normalize_pid_hex` missed zero-pad causing `"0x5"` vs canonical `"0x05"` mismatch; one-line `.zfill(2)` fix.

**Peak-Efficiency mode deployed:** Per user request, the agent pool ran 8+ concurrent agents across Planner / Builder / Architect / Validator / Finalizer roles with file-overlap-analyzed parallel dispatch. The pattern has been formalized as a dedicated section in `C:\Users\Kerwyn\PycharmProjects\CLAUDE.md` ("Peak-Efficiency Agent Pool Mode"). Several Builders (153, 154, 155, 157) hit Anthropic rate limits mid-build; Architect recovered by writing remaining test files + bug-fix patches directly.

**Forward-compat cleanup:** Two pre-existing brittle `SCHEMA_VERSION == N` asserts in `tests/test_phase145_compat.py` and `tests/test_phase150_fleet.py` loosened to `>=` so future migration bumps don't retroactively break earlier-phase tests.

**Project version:** 0.8.0 → **0.9.0**.

**Completion gates status:**
- Gates 1-6: ✅ (as before)
- Gate 7 (Phase 159): ✅ — Track F closed
- Gates 8-20: 🔲 (future tracks)

Track G (phases 160-174) opens next — shop management + work orders + triage + parts auto-pick + repair scheduling.

### 2026-04-21 15:55 — Phase 160 complete (Track G opens)

**First Track G phase shipped.** Architect-direct auto-iterate build. Migration 025 adds `shops` + `intake_visits` tables + 4 indexes, bumping `SCHEMA_VERSION` 24→25. New `shop/` package shipped with `shop_repo.py` (337 LoC, 11 fns incl. `reactivate_shop` + hours_json JSON-object validator) and `intake_repo.py` (481 LoC, 12 fns with guarded `open→closed|cancelled→(reopen)→open` status lifecycle — generic `update_intake` cannot mutate `status`, only dedicated transition helpers can). New top-level `motodiag shop` CLI group surfaces 3 subgroups × 22 subcommands: `profile` (5), `customer` (9), `intake` (8). `cli/shop.py` landed at 1003 LoC including Rich Panel/Table rendering helpers + Phase 125-style remediation errors. 44 tests GREEN across 5 classes; full regression 3395 passed, 0 failed (up from 3349 at Phase 159 close — +44 phase 160 + 2 formerly-skipped conditional tests that now run with shops in schema).

**Load-bearing architectural reuse:** Phase 160 is the first CLI surface for Phase 113's dormant `crm/` substrate. `customers` + `customer_bikes` tables and repos have been in the codebase since Phase 113 (March) but never wired to Click. Phase 160's `shop customer` subgroup (9 subcommands) delegates to `crm/customer_repo.py` + `crm/customer_bikes_repo.py` without modifying them — "build substrate first, surface later" rhythm validated across 47 phases of shelf time. This unlocks the intake pipeline without requiring a parallel schema.

**FK delete asymmetry as a deliberate contract:** `intake_visits.shop_id` cascades on shop delete (explicit, confirmed, rare — retaining orphan intakes pointing at a dead shop_id produces more confusion than value); `customer_id` and `vehicle_id` use `ON DELETE RESTRICT` (prevents accidental history erasure via unrelated deletes — mechanics deactivate customers via Phase 113's `deactivate_customer`, they don't delete). Tests cover both paths including the "delete customer with 0 intakes succeeds / delete customer with 1 intake raises" boundary.

**New package:** `shop` joins the active-package roster alongside `hardware` and `advanced`. Phase 161 (work orders) will extend under the same top-level `motodiag shop` group; file-overlap planning applies — 161's migration 026 needs to land serially on top of 025, same for any `cli/main.py` edits.

**Deviations from plan (all strict expansions):** `profile list`/`profile delete` added (plan had 3 profile subcommands, shipped 5). `intake cancel` added distinct from `close` so Phase 171 analytics can filter completed-from-withdrawn at SQL (plan had 7 intake subcommands, shipped 8). `reactivate_shop` symmetric counterpart added to shop_repo during test-writing (plan omitted). 22 subcommands shipped vs 19 planned; 44 tests vs 40 planned; zero planned surface contracted.

**Project version:** 0.9.0 → **0.9.1**.

**Completion gates status:**
- Gates 1-7: ✅ (as before)
- Gate 8 (Phase 174): 🔲 — shop management intake-to-invoice integration test, pending Phases 161-173.

Phases 161-174 queued. Track G compounding begins: work orders (161) attach to `intake_visits.id`, issues (162) link to work orders, invoicing (169) closes the loop back on the intake row created this phase.

### 2026-04-21 22:35 — Phase 161 complete + 10-agent peak-efficiency pool dispatched

**Phase 161 closed.** Architect-direct auto-iterate build. Migration 026 adds `work_orders` table + 4 indexes, bumping `SCHEMA_VERSION` 25→26. New `shop/work_order_repo.py` (748 LoC, 14 functions + 7 dedicated lifecycle transition helpers, guarded `draft→open→in_progress→(on_hold|completed|cancelled)→(reopen)→open` lifecycle — generic `update_work_order` cannot mutate status, only the 7 transition functions can). FK delete asymmetry mirrors Phase 160: shop_id CASCADE, intake_visit_id SET NULL (work history survives intake delete), vehicle_id + customer_id RESTRICT. New top-level CLI `motodiag shop work-order` group with 12 subcommands appended additively to Phase 160's `register_shop` (no main.py edit). 47 tests GREEN across 4 classes; full regression 3441 passed / 1 failed.

**Bug fix #1 — forward-compat rollback test pattern.** Full regression flagged `test_phase160_shop.py::TestMigration025::test_rollback_drops_child_first` failing with `sqlite3.OperationalError: no such table: main.intake_visits`. Root cause: Phase 161's `work_orders.intake_visit_id` FK references `intake_visits`; Phase 160's rollback test ran `rollback_migration(25)` directly, which attempted bare `DROP TABLE intake_visits` while work_orders still referenced it. Solution: migrated both Phase 160 + Phase 161 rollback tests to `rollback_to_version(target_version, path)` — peels all migrations beyond `target_version` in correct reverse-version order. Phase 160 uses `rollback_to_version(24, path)`; Phase 161 preemptively uses `rollback_to_version(25, path)` for when Phase 162 lands. Forward-compat protection now standard for all future phases. Re-verified 91/91 Phase 160 + Phase 161 tests GREEN in 56.98s post-fix. Pattern matches the Phase 145/150 SCHEMA_VERSION `>= N` loosening from Track F closure — codified as canonical MotoDiag rollback-test pattern going forward.

**10-agent peak-efficiency pool dispatched in same session.** Per user request ("auto iterate with 10 agents", "operate all agents under CLAUDE.md"), dispatched a Stage A planning wave: 7 Planner agents (Phases 162-168) + 2 Domain-Researcher agents (mechanic workflow + parts/labor pricing) + 1 Architect-Auditor (project-level docs drift audit). All 10 returned. Outcomes:

- **Plans 162-168 + new micro-phase 162.5 persisted to `docs/phases/in_progress/`** (8 implementation.md files committed across 2 batches: `06c36f5` + `22d65d5`).
- **Three independent AI-phase planners (163, 166, 167) converged on a duplication risk** — each proposed re-implementing Anthropic client setup + cost math + prompt caching + JSON extraction. Inserted **micro-phase 162.5 (NEW, not in original ROADMAP)** to extract `src/motodiag/shop/ai_client.py` BEFORE Phase 163 ships; subsequent AI phases compose on it.
- **Domain-Researcher-Workflow brief overrode Phase 162's category taxonomy** — Planner reused the existing 7 `SymptomCategory` values; Researcher found that misfiles ~40-50% of real shop tickets to "other." **Phase 162 now ships with 12 categories** (existing 7 + brakes/suspension/drivetrain/tires_wheels/accessories/rider_complaint).
- **Domain-Researcher-Workflow priority formula converged independently with Planner-163's** (base tier 1000/500/200/50 + per-tier daily aging 100/50/20/10 + customer-history bonus 0/25/75/150). High confidence in Phase 163's scoring approach.
- **Domain-Researcher-Pricing brief seeds Phase 166 sourcing prompt** with concrete OEM-vs-aftermarket rubric (Ricks Motorsports stators > OEM on 80s-00s Japanese; EBC HH > OEM on most sport bikes; etc.) + 6-tier vendor taxonomy (T1 OEM dealer → T6 AliExpress-avoid). Same brief seeds Phase 167 labor estimator with per-platform baseline labor table + skill/mileage adjustments.
- **Architect-Auditor flagged 5 finalization fixes for this commit:** SCHEMA_VERSION footnote (25→26), Database Tables row for work_orders, Phase History row for 161, Shop CLI subcommand count bump (22→34), and pyproject/doc version split documentation. All 5 applied.
- **Migration numbering locked across Track G:** 027 (Phase 162 issues), no migration (Phase 163 AI), 028 (Phase 164 triage_weights column), 029 (Phase 165 parts_needs three tables), 030 (Phase 166 sourcing_recommendations), 031 (Phase 167 labor_estimates), 032 (Phase 168 bay_scheduler two tables).
- **Build order locked: serial per-phase end-to-end** per user direction ("complete each in entirety before moving on") — no parallel Builders across phases since cli/shop.py + migrations.py + SCHEMA_VERSION are inherently serializing.

**Project version:** 0.9.1 → **0.9.2**.

**Completion gates status:**
- Gates 1-7: ✅ (as before)
- Gate 8 (Phase 174): 🔲 — shop management intake-to-invoice integration test, pending Phases 162-173.

Track G work-order pillar landed. Next: Phase 162 (issues, 12-category shop taxonomy) → Phase 162.5 (shop/ai_client.py extraction) → Phase 163 (AI priority scoring). Each fully complete before next begins.

### 2026-04-21 23:05 — Phase 162 complete

**Track G issues pillar landed.** Migration 027 adds `issues` table with FK CASCADE to work_orders + 5 indexes, bumping `SCHEMA_VERSION` 26→27. **12-category taxonomy shipped on day one** (override from Planner-162's original 7-value reuse — Domain-Researcher-Workflow brief found existing `SymptomCategory` misfiles ~40-50% of real shop tickets to "other"; brakes/suspension/drivetrain/tires_wheels/accessories/rider_complaint added as first-class buckets). 4-tier severity + 4-state guarded lifecycle (open → resolved | duplicate | wont_fix → reopen → open). New `shop/issue_repo.py` (720 LoC, 14 functions + 4 dedicated transition helpers + `SYMPTOM_CATEGORY_TO_ISSUE_CATEGORY` 18-entry crosswalk dict — the canonical bridge between diagnostic symptom-class vocabulary and shop repair-class vocabulary that Phase 163 AI categorization will route through). New `motodiag shop issue` subgroup with 12 subcommands appended additively to Phase 160's `register_shop`.

**Tests:** 42 GREEN across 4 classes (TestMigration027×6 + TestIssueRepo×16 + TestIssueLifecycle×10 + TestIssueCLI×10) in 27.74s. Track G regression sample (160+161+162): 133 GREEN in 84.40s. Full regression in flight at finalize-doc-write time.

**Architectural decisions baked in:**
- `mark_wontfix_issue` REQUIRES non-empty `resolution_notes` — deliberate audit-trail asymmetry vs `resolve_issue` (which has WO actual_hours + parts for context). "Customer declined $800 rebuild on $400 bike" needs the audit justification.
- `linked_dtc_code` stored as TEXT not FK — survives `dtc_codes` seed reloads via soft-validation (logging.warning on miss; persist anyway). Keeps issue log populated on fresh shop installs before the DTC library is imported.
- `linked_symptom_id` is hard FK with SET NULL — symptoms table is shop-lifetime stable; SET NULL covers rare hard-deletes.
- Self-referencing `duplicate_of_issue_id` FK with one-hop cycle prevention (canonical issue cannot itself be a duplicate).
- Forward-compat rollback test (`test_rollback_to_version_26_drops_issues_only`) inherits the Phase 161-codified `rollback_to_version(target_version)` pattern automatically.

**Architect-direct serial build per user direction** "complete each in entirety before moving on" — no parallel Builders across phases (cli/shop.py + migrations.py + SCHEMA_VERSION serialize naturally).

**Project version:** 0.9.2 → **0.9.3**.

**Completion gates status:**
- Gates 1-7: ✅
- Gate 8 (Phase 174): 🔲 — pending Phases 162.5, 163-173.

Next: Phase 162.5 (shop/ai_client.py extraction — micro-phase from convergent 163/166/167 planner findings) → Phase 163 (AI priority scoring uses shop.ai_client) → Phase 164 (triage queue) → ...

### 2026-04-21 23:40 — Phase 162.5 complete (NEW micro-phase shipped)

**Track G shared AI client helper landed.** Inserted between Phase 162 and Phase 163 per `_research/consolidation_notes.md`. Three independent Track G AI planners (163, 166, 167) flagged the same duplication risk; rule-of-three extract executed BEFORE Phase 163 ships. Single new module `src/motodiag/shop/ai_client.py` (273 LoC) provides:

- `MODEL_ALIASES` dict (haiku/sonnet/opus → full ids)
- `MODEL_PRICING` table (cache_read 10%, cache_creation 125%)
- `TokenUsage` + `AIResponse` frozen dataclasses
- Pure helpers: `resolve_model`, `calculate_cost`, `extract_json_block`
- Lazy singleton `get_anthropic_client` via `@lru_cache(maxsize=1)`
- `ShopAIClient` high-level wrapper with always-on ephemeral prompt caching + Phase 131 `ai_response_cache` integration (cache hit returns zero cost; cache miss persists; cache write errors silently swallowed)
- `ShopAIClientError` for SDK + setup failures

20 tests GREEN in 2.08s across 2 classes (TestHelpers×12 + TestShopAIClient×8). All Anthropic SDK calls mocked — zero live tokens. Targeted regression sample (Phase 131 ai_response_cache direct dependency + Phase 160/161/162 Track G + Phase 162.5): 183 GREEN in 99.43s.

Zero migrations, zero CLI surface, zero schema changes. Pure helper-module micro-phase. Total cost: ~30 minutes wall-clock + 0 AI tokens. Estimated savings: ~250 LoC of duplication across Phases 163/166/167 + ~3 hours of consolidation refactor work that won't be needed.

**Project version:** 0.9.3 → **0.9.4**.

Next: Phase 163 (AI priority scoring) composes against `ShopAIClient.ask(...)` in 3 lines instead of ~80 LoC of duplicated SDK + cost + cache integration.

### 2026-04-22 00:00 — Phase 163 complete (Track G first AI phase)

**First Track G phase to spend AI tokens.** Composes against the Phase 162.5 `shop/ai_client.py` substrate — zero direct `anthropic` imports anywhere (enforced by `test_priority_scorer_does_not_import_anthropic_directly` anti-regression grep test). Two new modules:

- `shop/priority_models.py` (82 LoC) — `PriorityScorerInput` + `PriorityScoreResponse` + `PriorityScore` Pydantic models. Separated from priority_scorer so tests import schemas without pulling SDK seam.
- `shop/priority_scorer.py` (311 LoC) — `score_work_order` + `rescore_all_open` + `priority_budget` + `get_latest_priority_score` + 6 helper functions (`_wait_time_penalty`, `_priority_from_rubric`, `_should_apply`, `_load_issues_safe`, `_find_kb_matches_safe`, `_customer_prior_ticket_count`) + 3 exceptions (`PriorityScorerError`, `PriorityCostCapExceeded`, `PriorityBudgetExhausted`). Constants: CONFIDENCE_APPLY_THRESHOLD=0.75, PER_CALL_COST_CAP_CENTS=3, DEFAULT_SESSION_BUDGET_CENTS=50, DEFAULT_RESCORE_LIMIT=10.

System prompt baked from Domain-Researcher 4-tier rubric (CRITICAL safety / HIGH ridability / MEDIUM service-interval / LOW cosmetic) + wait-time aging (24h/72h penalties) + customer-history bonus (0/+25/+75/+150). Sent with `cache_control={"type":"ephemeral"}` automatically via `ShopAIClient` — every `score` call after the first within 5 minutes hits the prompt cache.

**Mechanic-intent preservation:** AI-proposed priority overwrites `work_orders.priority` ONLY when `confidence > 0.75`. Below threshold, score is logged to Phase 131 `ai_response_cache` (kind='priority_score') but DB priority untouched. Safety override (`safety_risk=true AND priority=1`) bypasses threshold. `--force` CLI flag is the explicit human override.

**Write-back routing:** `update_work_order(wo_id, {"priority": int})` from Phase 161 — never raw SQL. Inherits `_validate_priority` (1-5 CHECK) for free.

CLI: new `motodiag shop priority {score, rescore-all, show, budget}` (4 subcommands, +188 LoC in cli/shop.py). All AI calls in tests injected via `_default_scorer_fn=None` seam — zero live tokens.

**Tests:** 26 GREEN across 5 classes (TestPureHelpers×9 + TestScoreSingle×7 + TestRescoreAll×5 + TestPriorityCLI×4 + TestAntiRegression×1) in 10.74s. Targeted regression sample: 209 GREEN in 111.76s covering Phase 131 (ai_response_cache direct dependency) + Track G phases 160-163 + Phase 162.5.

**Phase 162.5 extraction paid off as predicted:** scorer module composes against `ShopAIClient.ask()` in 5 lines instead of the ~80 LoC of duplicated SDK + cost + cache integration that 162.5's plan estimated. Injection seam pattern (`_default_scorer_fn`) is the load-bearing test convention every Track G AI phase will use (166, 167). Anti-regression grep test enforces no direct anthropic imports going forward — if a future Phase 175 author tries to bypass `shop/ai_client`, the test fails loudly.

**Project version:** 0.9.4 → **0.9.5**.

**Track G AI substrate (162.5) + first AI phase (163) = canonical pattern:**
1. Pydantic models in their own file (testable without SDK).
2. Scorer/orchestrator module composes against `ShopAIClient.ask()`.
3. `_default_scorer_fn=None` injection seam for tests.
4. Write-back via existing whitelist (never raw SQL).
5. Anti-regression grep test enforces shop.ai_client composition.
6. Phase 131 `ai_response_cache` partition via unique `kind=` value.
7. Per-call cost cap (diagnostic) + session budget cap (hard stop with PriorityBudgetExhausted carrying partial results).

Phases 166 (AI parts sourcing) and 167 (AI labor estimation) follow this exact shape. Pattern is now the Track G AI canonical.

Next: Phase 164 (deterministic triage queue, no AI).

### 2026-04-22 00:30 — Phase 164 complete

**Track G triage queue pillar landed.** Migration 028 adds nullable `shops.triage_weights TEXT` column (NULL = ShopTriageWeights pydantic defaults), bumping SCHEMA_VERSION 27 → 28. Pure query-synthesis layer over Phase 161 work_orders + Phase 162 issues + Phase 163 AI priority (consumed via work_orders.priority) + Phase 165 parts (soft-guarded since 165 hasn't shipped).

New `shop/triage_queue.py` (365 LoC):
- `build_triage_queue()` — pure read; returns ranked `list[TriageItem]`.
- `ShopTriageWeights` — Pydantic with 5 tunable scalars + `extra="forbid"`.
- `TriageItem` — Pydantic carrying work_order + issues + parts_ready + missing_skus + wait_hours + flag + skip_reason + score + rank.
- 6 helpers: `_parse_triage_markers`, `_build_marked_description`, `_parts_available_for` (Phase 165 soft-guard via `importlib.util.find_spec`), `_compute_wait_hours`, `_compute_score`, `_load_issues_safe`.
- 5 mutators: `load/save/reset_triage_weights`, `flag_urgent`/`clear_urgent` (writes priority=1 + `[TRIAGE_URGENT] ` prefix; idempotent), `skip_work_order(reason)` (writes `[TRIAGE_SKIP: reason] ` prefix; empty reason clears).
- `ShopTriageError` exception.

**Triage score formula:** `priority_weight*(1/priority) + wait_weight*(wait_hours/24) + parts_ready_weight*ready + urgent_flag_bonus*urgent - skip_penalty*skipped`. Defaults: priority_weight=100, wait_weight=1.0, parts_ready_weight=10, urgent_flag_bonus=500, skip_penalty=50 — per-shop tunable via `shop triage weights --set key=value`.

**Markers ride on work_orders.description** via prefix tokens — no new triage-state column. `[TRIAGE_URGENT] ` and `[TRIAGE_SKIP: reason] ` parsed on read. Idempotent (calling `flag_urgent` twice doesn't double-prefix). `clear_urgent` removes prefix but does NOT auto-restore prior priority — explicit mechanic action via `work-order update --set priority=N`.

**Phase 165 soft-guard pattern:** `_parts_available_for` returns `(True, [])` when Phase 165 module absent; when 165 ships and exports `list_parts_for_wo(wo_id, db_path=None)`, the guard automatically picks up real parts data with no Phase 164 code change.

CLI: new `motodiag shop triage {queue, next, flag-urgent, skip, weights}` (5 subcommands, +250 LoC in cli/shop.py).

**Tests:** 32 GREEN across 5 classes (TestMigration028×5 + TestTriageWeights×6 + TestTriageMarkers×4 + TestBuildTriageQueue×10 + TestTriageCLI×7) in 21.15s. Targeted regression sample (Phase 131 + 160-164 + 162.5): 241 GREEN in 165.54s.

**Project version:** 0.9.5 → **0.9.6**.

Next: Phase 165 (parts needs aggregation — bridges Phase 153 catalog to Phase 161 work_orders; transactional cost recompute through Phase 161 update_work_order whitelist).

### 2026-04-22 01:00 — Phase 165 complete

**Track G parts pillar landed.** Migration 029 (schema v28→v29) creates 3 new tables bridging Phase 153 parts catalog (`parts` + `parts_xref`) to Phase 161 work_orders via FK reuse — zero schema duplication.

New `shop/parts_needs.py` (605 LoC) — 18 functions:
- 5 CRUD (`add_part_to_work_order` / `remove_part_from_work_order` / `update_part_quantity` / `update_part_cost_override` / `cancel_part_need`)
- 3 lifecycle transitions (`mark_part_ordered` / `mark_part_received` / `mark_part_installed`)
- 1 critical helper `_recompute_wo_parts_cost` — writes back via Phase 161 `update_work_order(wo_id, {"estimated_parts_cost_cents": ...})` — NEVER raw SQL
- 2 read APIs (`list_parts_for_wo` for Phase 164 contract + `list_parts_for_shop_open_wos` for cross-WO consolidation with OEM/aftermarket cost surfacing via `parts_repo.get_xrefs`)
- 3 requisition APIs (`build_requisition` / `get_requisition` / `list_requisitions`) — immutable snapshots
- 3 Pydantic models (`WorkOrderPartLine` / `ConsolidatedPartNeed` / `Requisition`)
- 3 exceptions (`WorkOrderPartNotFoundError` / `InvalidPartNeedTransition` / `PartNotInCatalogError`)

**Critical audit guarantee:** `test_recompute_routes_through_update_work_order` patches `motodiag.shop.parts_needs.update_work_order` and asserts it's called with `{"estimated_parts_cost_cents": new_total}` in the updates dict. Proves the cost recompute routes through the Phase 161 whitelist — if a future author tries to bypass with raw `UPDATE work_orders SET ...`, the test fails loudly.

**Phase 164 contract satisfied automatically:** `list_parts_for_wo(wo_id, db_path=None)` exported with the exact name Phase 164's `_parts_available_for` soft-guard imports. The `test_phase164_soft_guard_contract` test in this phase's suite verifies the contract end-to-end: when no parts exist on a WO, soft-guard returns `(True, [])`; when an open part exists, soft-guard returns `(False, [missing_skus])`. Phase 164's triage queue automatically picks up real parts-availability data with no Phase 164 code change.

**Immutable requisition snapshots:** `build_requisition(shop_id, wo_ids=None|list)` validates wo_ids belong to shop_id (raises ValueError on mismatch), then freezes header + items at creation. Subsequent edits to `work_order_parts` do NOT mutate the snapshot — gives the shop an auditable "as-of" record. Empty requisition still creates a header row with zero counts (intentional — explicit "we checked, found nothing" record).

**FK asymmetry mirrors Phases 160/161:** structural ownership (WO→lines, requisition→items) cascades; curated reference data (`parts`) is RESTRICT-protected so removing a part referenced anywhere is blocked at the FK layer (preserves cost audit history).

CLI: new `motodiag shop parts-needs {add, list, consolidate, mark-ordered, mark-received, requisition {create, list, show}}` (5 top-level + 3 nested = 8 subcommands; +320 LoC in cli/shop.py).

**Tests:** 38 GREEN across 5 classes (TestMigration029×5 + TestPartsNeedsCRUD×12 + TestPartsLifecycle×5 + TestRequisitions×8 + TestPartsNeedsCLI×8) in 32.96s. Targeted regression sample (Phase 131 + 153 + 160-165 + 162.5): 310 GREEN in 229.41s. Phase 153 parts catalog tests pass unchanged.

**Project version:** 0.9.6 → **0.9.7**.

Next: Phase 166 (AI parts sourcing — composes against Phase 162.5 ShopAIClient + reads Phase 165 ConsolidatedPartNeed for OEM-vs-aftermarket recommendations seeded from research-brief vendor taxonomy).

### 2026-04-22 01:35 — Phase 166 complete (Track G second AI phase)

**Second Track G AI phase.** Composes against Phase 162.5 `shop/ai_client.py` substrate — zero direct `anthropic` imports anywhere (enforced by `test_parts_sourcing_does_not_import_anthropic_directly` anti-regression grep test).

Migration 030 (schema v29→v30) creates single audit table `sourcing_recommendations` with full AI response log (recommendation_json TEXT + ai_model + tokens + cache_hit + cost_cents + batch_id reserved). 2 indexes: `(part_id, generated_at DESC)` + `(requisition_id, requisition_line_id)` reserved.

Two new modules:
- `shop/sourcing_models.py` (65 LoC) — `SourcingRecommendation` + `VendorSuggestion` Pydantic models + `SourceTier`/`TierPreference`/`Availability` Literal types. Separated so tests + Phase 169 can import without SDK seam.
- `shop/parts_sourcing.py` (482 LoC) — `recommend_source` + `get_recommendation` + `sourcing_budget` + 3 exceptions (`PartNotFoundError`, `InvalidTierPreferenceError`, `SourcingParseError`) + `BatchTimeoutError` reserved + 4 helpers + `_default_scorer_fn=None` injection seam.

**System prompt baked from Domain-Researcher pricing brief** (`_research/track_g_pricing_brief.md`):
- Decision tree (safety-critical path-of-force → OEM only; consumables → aftermarket first)
- 6-tier vendor taxonomy (T1 OEM dealer → T6 AliExpress-avoid)
- Counter-intuitive aftermarket wins (Ricks Motorsports stators on 80s-00s Japanese; EBC HH brake pads on most sport bikes)
- Discontinued-OEM cascade (used → aftermarket reproduction → China-direct)

**Canonical Track G AI pattern (inherited from Phase 163):**
```python
def recommend_source(part_id, ..., _default_scorer_fn=None):
    part = _require_part(part_id)              # Phase 153 reuse
    xrefs = _load_xrefs(part_id)               # Phase 153 reuse
    if _default_scorer_fn is not None:
        payload, ai_resp = _default_scorer_fn(...)  # test injection
    else:
        client = ShopAIClient(...)             # Phase 162.5 composition
        ai_resp = client.ask(...)              # cached prompt automatic
        payload = _parse_recommendation(ai_resp.text)
    rec = SourcingRecommendation(**payload)
    _persist_recommendation(rec, ...)          # audit log
    return rec
```

5-line integration vs ~80 LoC duplication without Phase 162.5. Pattern is now proven across 2 AI phases (163 priority, 166 sourcing) — Phase 167 will follow identically.

New CLI `motodiag shop sourcing {recommend, show, budget}` (3 subcommands, +175 LoC in cli/shop.py).

**Tests:** 27 GREEN across 5 classes (TestMigration030×4 + TestRecommendSource×10 + TestPersistence×5 + TestSourcingCLI×7 + TestAntiRegression×1) in 35.86s.

**Targeted regression: 337 GREEN in 484s (8m 4s)** covering Phase 131 (ai_response_cache) + Phase 153 (parts catalog) + Track G phases 160-166 + Phase 162.5. Zero regressions across all dependencies.

Build deviations:
- `optimize_requisition` Batches API path deferred to Phase 169 (when invoicing needs bulk-source for finalized WOs).
- CLI `compare` subcommand reserved for Phase 169 (Rich Columns side-by-side rendering).
- 27 tests vs ~30 planned (deferred coverage matches deferred subcommands).

**Project version:** 0.9.7 → **0.9.8**.

Next: Phase 167 (AI labor time estimation) — composes against Phase 162.5 `ShopAIClient` + reads work_orders + issues; writes back `work_orders.estimated_hours` via Phase 161 `update_work_order` whitelist (never raw SQL, verified by grep test like Phase 165's cost-recompute audit).
