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
