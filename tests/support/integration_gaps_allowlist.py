"""Phase 209B — every known piece of code that nothing reaches, and why.

The gate in `tests/test_phase209B_integration_gaps.py` fails when:

- something becomes unreachable, or an orphan appears, and it is not listed
  here;
- something listed here is now reachable or referenced (a stale entry, which
  would let the list quietly turn into a list of excuses);
- an entry's classification is not one of `CLASSIFICATIONS`, or its reason is
  shorter than 20 characters (the same floor `f9-noqa` uses).

**This file records; it does not approve.** An entry here is a known gap that
someone decided to write down instead of acting on, and the classification
says which decision it is still waiting for.
"""

from __future__ import annotations

CLASSIFICATIONS = {
    # A complete, tested capability that no user can reach. Needs a
    # wire-or-retire decision. The roadmap may mark it done.
    "unwired-feature",
    # Schema and repo layer built ahead for a roadmap phase that hasn't
    # started. Unreached by design, but the reason must name that phase, so
    # the entry becomes stale -- and fails -- once the phase lands and wires
    # it up.
    "substrate",
    # Replaced by a live implementation elsewhere. A removal candidate.
    "superseded",
    # Exists so the test suite can do its job.
    "test-infra",
    # A small library helper kept deliberately, with no in-tree caller.
    "public-api",
}

_C2 = (
    "Track C2 Media Diagnostic Intelligence (Phases 96-107): engine-audio "
    "analysis, tested and marked done, but no CLI command or API route "
    "imports it. The live media path is vision, photos, ffmpeg and Whisper."
)
_PRICING = (
    "Non-AI labor-rate table and repair-plan builder. Distinct from the AI "
    "`shop/labor_estimator`. Nothing reaches it."
)

# Dotted module name -> (classification, reason)
UNREACHABLE_MODULES: dict[str, tuple[str, str]] = {
    "motodiag.cli.registry": ("superseded",
        "Phase 109 command registry, never adopted: cli/main.py registers "
        "every group with a direct register_*(cli) call instead."),
    "motodiag.core.logging": ("unwired-feature",
        "Phase 10 structured logging + audit trail. setup_logging has a test "
        "and no production caller, so the served app never configures its "
        "own logging. Launch-relevant."),

    "motodiag.i18n": ("substrate",
        "Phase 115 i18n substrate, awaiting Phases 308-310 (Spanish, French, "
        "German localization). The translations table holds 45 rows nothing "
        "can read."),
    "motodiag.i18n.models": ("substrate", "Part of the Phase 115 i18n substrate; see motodiag.i18n."),
    "motodiag.i18n.translation_repo": ("substrate", "Part of the Phase 115 i18n substrate; see motodiag.i18n."),
    "motodiag.i18n.translator": ("substrate", "Part of the Phase 115 i18n substrate; see motodiag.i18n."),

    "motodiag.knowledge.seed": ("superseded",
        "Python seed modules. Installs seed from the SEED_DATA_DIR JSON "
        "directories (cli/main.py), and nothing imports these."),
    "motodiag.knowledge.seed.dtc_codes": ("superseded", "Part of the superseded knowledge.seed package; see it."),
    "motodiag.knowledge.seed.knowledge": ("superseded", "Part of the superseded knowledge.seed package; see it."),

    "motodiag.media.annotation": ("unwired-feature", _C2),
    "motodiag.media.anomaly_detection": ("unwired-feature", _C2),
    "motodiag.media.audio_capture": ("unwired-feature", _C2),
    "motodiag.media.coaching": ("unwired-feature", _C2),
    "motodiag.media.comparative": ("unwired-feature", _C2),
    "motodiag.media.fusion": ("unwired-feature", _C2),
    "motodiag.media.realtime": ("unwired-feature", _C2),
    "motodiag.media.reports": ("unwired-feature", _C2),
    "motodiag.media.sound_signatures": ("unwired-feature", _C2),
    "motodiag.media.spectrogram": ("unwired-feature", _C2),

    "motodiag.media.sim": ("test-infra",
        "Self-declared SIMULATION / TEST-ONLY (F48), superseded by "
        "motodiag.media.ffmpeg for real frame extraction."),
    "motodiag.media.sim.video_frames": ("test-infra", "Part of the test-only media.sim package; see it."),
    "motodiag.media.sim.vision_analyzer_textsim": ("test-infra", "Part of the test-only media.sim package; see it."),

    "motodiag.pricing": ("unwired-feature", _PRICING),
    "motodiag.pricing.estimate": ("unwired-feature", _PRICING),
    "motodiag.pricing.labor_rates": ("unwired-feature", _PRICING),
    "motodiag.pricing.repair_plan": ("unwired-feature", _PRICING),

    "motodiag.reference": ("substrate",
        "Phase 117 reference-data substrate, awaiting Track P, the Reference "
        "Data Library (Phases 293-302, Gate 17)."),
    "motodiag.reference.diagram_repo": ("substrate", "Part of the Phase 117 reference substrate; see motodiag.reference."),
    "motodiag.reference.manual_repo": ("substrate", "Part of the Phase 117 reference substrate; see motodiag.reference."),
    "motodiag.reference.models": ("substrate", "Part of the Phase 117 reference substrate; see motodiag.reference."),
    "motodiag.reference.photo_repo": ("substrate", "Part of the Phase 117 reference substrate; see motodiag.reference."),
    "motodiag.reference.video_repo": ("substrate", "Part of the Phase 117 reference substrate; see motodiag.reference."),

    "motodiag.scheduling": ("substrate",
        "Phase 118 appointment substrate, awaiting Phase 275 (Appointment "
        "booking). Phases 151 and 168 built their scheduling elsewhere "
        "(advanced/scheduler.py, shop bay tables)."),
    "motodiag.scheduling.appointment_repo": ("substrate", "Part of the Phase 118 scheduling substrate; see motodiag.scheduling."),
    "motodiag.scheduling.models": ("substrate", "Part of the Phase 118 scheduling substrate; see motodiag.scheduling."),

    "motodiag.workflows": ("substrate",
        "Phase 114 workflow-template substrate, awaiting Phase 316 "
        "(Workflow recording, train-by-example)."),
    "motodiag.workflows.models": ("substrate", "Part of the Phase 114 workflows substrate; see motodiag.workflows."),
    "motodiag.workflows.template_repo": ("substrate", "Part of the Phase 114 workflows substrate; see motodiag.workflows."),
}

_TEST_RESET = "Resets module-level state between tests; production has no reason to call it."
_REPO_HELPER = "Small repository query kept as library surface; low risk, no in-tree caller."
_PRICING_MODEL = "Pydantic/enum model used only by the unreachable motodiag.pricing package."

# `relative/path.py::name` inside REACHABLE modules -> (classification, reason).
# Orphans inside unreachable modules are implied by the module entry and are
# not listed a second time.
ORPHANS: dict[str, tuple[str, str]] = {
    # --- the ones that matter ---
    "media/ffmpeg.py::validate_video": ("unwired-feature",
        "Has a test and no caller. Uploads get size, quota and metadata-"
        "schema checks, but the file is never probed: width, height, "
        "duration and codec are taken from the client's own metadata."),
    "engine/workflows.py::create_no_start_workflow": ("unwired-feature",
        "Guided no-start diagnostic workflow; no CLI command or route runs it."),
    "engine/workflows.py::create_charging_workflow": ("unwired-feature",
        "Guided charging-system workflow; no CLI command or route runs it."),
    "engine/workflows.py::create_overheating_workflow": ("unwired-feature",
        "Guided overheating workflow; no CLI command or route runs it."),
    "engine/workflows.py::generate_next_step": ("unwired-feature",
        "Step engine for the guided workflows above; unreachable with them."),
    "media/photo_pipeline.py::heif_available": ("unwired-feature",
        "Capability probe for pillow-heif (HEIC decoding) that nothing "
        "consults."),
    "media/whisper_client.py::whisper_available": ("unwired-feature",
        "Capability probe nothing consults before a transcription attempt."),
    "media/ffmpeg.py::extract_audio": ("unwired-feature",
        "Audio extraction for the Track C2 audio layer, which is itself "
        "unreachable."),
    "shop/intake_repo.py::require_intake": ("public-api",
        "Raising variant of get_intake (IntakeNotFoundError on a miss); no "
        "caller uses this form."),
    "shop/extracted_symptom_repo.py::create_extracted_symptom": ("superseded",
        "Wired in by Phase 195 Commit 0 (api/routes/transcripts.py), removed "
        "by Phase 195B Commit 1 when extraction moved to the async Claude "
        "pipeline, which writes rows through the repo's other INSERT. "
        "Reclassified from unwired-feature on 2026-09-17: it was reachable "
        "once and was replaced, which makes it superseded, not unreachable."),
    "shop/extracted_symptom_repo.py::soft_delete_extracted_symptom": ("unwired-feature",
        "Soft delete with no route or command that calls it."),
    "shop/shop_repo.py::reactivate_shop": ("unwired-feature",
        "deactivate_shop exists; nothing calls the reverse."),
    "shop/wo_photo_repo.py::list_issue_photos": ("unwired-feature",
        "Photos can be attached per issue but never listed that way."),
    "advanced/fleet_repo.py::set_bike_role": ("unwired-feature",
        "A role is set when a bike joins a fleet, but no user path can "
        "change it afterwards."),
    "advanced/fleet_repo.py::update_fleet_description": ("unwired-feature",
        "No user path edits a fleet's description."),

    # --- superseded ---
    "cli/subscription.py::requires_tier": ("superseded",
        "CLI tier decorator never applied. The CLI enforces tier inline "
        "(soft enforcement in diagnose/code) and the API through "
        "auth.deps.require_tier. Not a gap in enforcement."),
    "cli/subscription.py::has_feature": ("superseded",
        "Feature check belonging to the unused requires_tier decorator."),

    # --- test infrastructure ---
    "core/config.py::reset_settings": ("test-infra", _TEST_RESET),
    "cli/theme.py::reset_console": ("test-infra", _TEST_RESET),
    "push/sender.py::reset_sender_for_tests": ("test-infra", _TEST_RESET),
    "core/migrations.py::rollback_to_version": ("test-infra",
        "Migration rollback, exercised by the migration test suites; no CLI "
        "exposes it."),
    "core/migrations.py::get_migration_by_version": ("test-infra",
        "Migration lookup used by the schema-contract tests."),
    "core/database.py::table_exists": ("test-infra",
        "Schema probe used by tests; the one production table check queries "
        "sqlite_master inline."),

    # --- library surface ---
    "core/session_repo.py::count_sessions": ("public-api", _REPO_HELPER),
    "vehicles/registry.py::count_vehicles": ("public-api", _REPO_HELPER),
    "knowledge/dtc_repo.py::count_dtcs": ("public-api", _REPO_HELPER),
    "knowledge/dtc_repo.py::list_dtcs_by_make": ("public-api", _REPO_HELPER),
    "knowledge/dtc_repo.py::get_category_meta": ("public-api", _REPO_HELPER),
    "knowledge/symptom_repo.py::count_symptoms": ("public-api", _REPO_HELPER),
    "knowledge/symptom_repo.py::get_symptom": ("public-api", _REPO_HELPER),
    "knowledge/symptom_repo.py::list_symptoms_by_category": ("public-api", _REPO_HELPER),
    "advanced/fleet_repo.py::get_fleet_by_name": ("public-api", _REPO_HELPER),
    "engine/service_data.py::FluidCapacity": ("public-api",
        "Data model for service data; exported, not constructed in-tree."),
    "hardware/protocols/j1850.py::J1850ParseError": ("public-api",
        "Exception type in the J1850 protocol's public surface, never raised in-tree."),
    "api/deps.py::get_request_id": ("public-api",
        "Accessor for request.state.request_id; the middleware sets the "
        "attribute directly and nothing reads it through this."),
    "api/routes/live.py::get_connection_manager": ("public-api",
        "Accessor for the WebSocket connection manager; the route uses the "
        "module-level instance directly."),
    "cli/theme.py::format_status": ("public-api",
        "Phase 129 Rich theme formatter with no in-tree caller."),
    "cli/theme.py::format_tier": ("public-api",
        "Phase 129 Rich theme formatter with no in-tree caller."),
    "core/models.py::DiagnosticSessionBase": ("public-api",
        "Base model kept for the public model surface; subclasses are used directly."),
    "core/models.py::VideoCreate": ("public-api",
        "Create model for videos; video_repo.create_video takes explicit "
        "arguments instead."),

    # --- belongs to the unreachable pricing package ---
    "core/models.py::LaborRateType": ("unwired-feature", _PRICING_MODEL),
    "core/models.py::PlanItemType": ("unwired-feature", _PRICING_MODEL),
    "core/models.py::RepairPlanStatus": ("unwired-feature", _PRICING_MODEL),

    # ---------------------------------------------------------------
    # Phase 244U — newly visible once a re-export stopped counting as a
    # use. These 20 were always orphans; the scanner could not see them
    # because a package __init__ writes each name twice (the import
    # alias and __all__). Classified by four readers and challenged by
    # four more; 19 stood, one reason was corrected.
    # ---------------------------------------------------------------
    "engine/confidence.py::rank_diagnoses": ("unwired-feature",
        "Ranking step of the Phase 83 evidence-weighted confidence "
        "feature. It sorts ConfidenceScore objects, and the only code "
        "that builds a ConfidenceScore is "
        "score_diagnosis_from_evidence in the same module, which is "
        "itself unreachable — so this is unreachable with it. "),
    "engine/confidence.py::score_diagnosis_from_evidence": ("unwired-feature",
        "The whole Phase 83 evidence-weighted confidence capability: "
        "it turns discrete evidence flags (symptom matches, DTC "
        "match, KB match, test confirmed/denied, vehicle history, "
        "environmental) into a 0.0-1.0 score with an itemised "
        "evidence list and a label. Complete and tested, and no CLI "
        "command or API route builds one. "),
    "engine/correlation.py::SymptomCorrelator": ("unwired-feature",
        "Phase 90 multi-symptom correlation: 15+ hand-written rules "
        "that map a set of symptoms to one root cause (overheating + "
        "power loss + coolant smell -> head gasket), with "
        "full/partial match scoring. "),
    "engine/cost.py::CostEstimator": ("unwired-feature",
        "Phase 86's pure-math repair-cost estimator: labor hours plus "
        "a parts list become low/high totals at dealer, independent "
        "or DIY rates, with a DIY-savings comparison, and "
        "estimate_from_diagnosis() takes a DiagnosisItem directly. "
        "Nothing constructs it. "),
    "engine/cost.py::format_estimate": ("unwired-feature",
        "The display half of the same Phase 86 cost feature: it "
        "renders a CostEstimate as a plain-text quote with line "
        "items, subtotals, total and DIY savings. "),
    "engine/evaluation.py::EvaluationTracker": ("unwired-feature",
        "Phase 94's ADR-005 quality scorecard: record per-session "
        "outcomes (predicted vs actual, helpfulness, cost, latency, "
        "model) and get back accuracy, confidence calibration, cost "
        "efficiency, latency percentiles, a weighted composite and a "
        "formatted report, plus per-model accuracy and cost "
        "breakdowns. "),
    "engine/intermittent.py::IntermittentAnalyzer": ("unwired-feature",
        "Phase 91 intermittent-fault analysis: pulls environmental "
        "conditions out of freeform customer text with pre-compiled "
        "regexes (cold start, heat soak, rain, load, RPM, time-of- "
        "day) and ranks them against 10+ predefined intermittent "
        "patterns, locally and with no API call. "),
    "engine/parts.py::PartsRecommender": ("unwired-feature",
        "Phase 85 AI second pass that turns a diagnosis plus vehicle "
        "into concrete parts — part numbers, brand, price range, "
        "OEM/aftermarket/used source, cross-references — and the "
        "tools needed for the job. "),
    "engine/repair.py::RepairProcedureGenerator": ("unwired-feature",
        "Phase 84 AI second pass that expands a diagnosis into a full "
        "RepairProcedure: numbered steps each with an optional pro "
        "tip and safety warning, tools, parts, estimated labour "
        "hours, an assessed skill level, and top-level safety "
        "warnings, with a graceful fallback that preserves raw text "
        "when the model's JSON will not parse. "),
    "engine/service_data.py::build_service_data_context": ("unwired-feature",
        "Formats torque specs, service intervals and valve clearances "
        "into prompt text so a diagnosis can quote real numbers. The "
        "consumer it was written for was never built: the diagnostic "
        "prompt is assembled from vehicle + symptom + knowledge "
        "context only, and there is no parameter for service data "
        "anywhere in that path. "),
    "engine/symptoms.py::SymptomAnalyzer": ("superseded",
        "Phase 80's two-pass symptom entry point. The same job — "
        "symptoms plus knowledge-base matches in, DiagnosticResponse "
        "plus TokenUsage out — is done live by "
        "DiagnosticClient.diagnose(), which the CLI calls through "
        "cli/diagnose.py:341 after its own KB pass, and which has "
        "since moved ahead: Phase 244Q switched the live path to "
        "ask_st… "),
    "engine/wiring.py::build_wiring_context": ("unwired-feature",
        "Renders a circuit reference — wire colours, expected "
        "readings, test points, common failures, diagnostic tips — as "
        "prompt text for AI injection. Same unbuilt seam as the "
        "service-data formatter: the diagnostic prompt has no slot "
        "for circuit context, so the function has never had a "
        "production caller. "),
    "hardware/compat_repo.py::remove_adapter": ("unwired-feature",
        "The only code path that can delete an adapter from the "
        "compatibility knowledge base. The `hardware compat` CLI "
        "group ships seven read-and-seed commands and no remove, no "
        "API route touches compat_repo, and `compat seed` is INSERT "
        "OR IGNORE — so from every user-reachable path the adapter "
        "table is append-only. "),
    "hardware/scenarios/__init__.py::builtin_path": ("test-infra",
        "Returns a filesystem Path to one of the ten packaged built- "
        "in simulator YAMLs. Its only two callers are parametrized "
        "test suites that need a real path — one to feed the loader, "
        "one to hand to `simulate validate` as a CLI argument. "),
    "hardware/sensors.py::decode_pid": ("public-api",
        "Thin __all__-exported wrapper over SENSOR_CATALOG "
        "(sensors.py:234) that decodes a raw value and raises "
        "ValueError for a PID the catalog does not cover; its own "
        "docstring says it exists so callers need not reach into the "
        "catalog dict. "),
}
