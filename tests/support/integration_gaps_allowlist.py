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
    "advanced/fleet_repo.py::list_fleets_for_bike": ("public-api",
        "Reverse lookup kept as library surface. Its only mention outside its "
        "own file is prose in core/migrations.py:1221; Phase 244W stopped a "
        "name inside a string literal from counting as a use."),
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
    "hardware/compat_repo.py::update_adapter": ("unwired-feature",
        "Sibling of remove_adapter below and unreached the same way: the "
        "`hardware compat` CLI has no update command. Its only mentions are "
        "its own error message (compat_repo.py:276) and __all__; Phase 244W "
        "stopped a name inside a string literal from counting as a use."),
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

# Dotted module name -> (classification, reason). Phase 244W.
#
# A module every one of whose public names is referenced only by itself, by a
# package __init__ re-export, or by another module in this table. The import
# walk cannot see these (the __init__ import edge is real), the package-level
# island check cannot (the package is alive), and the orphan count cannot (a
# class that names itself, or a dead module naming another, counts as a use).
# Orphans inside a module listed here are implied by the module entry and are
# not listed a second time in ORPHANS — the same convention as
# UNREACHABLE_MODULES.
_SUBSTRATE_118 = "Phase 118 substrate (billing/accounting/inventory/scheduling)"
MODULE_ISLANDS: dict[str, tuple[str, str]] = {
    # -- superseded: a live implementation does the job elsewhere -----------
    "motodiag.engine.history": ("superseded",
        "Phase 88 in-memory session store (DiagnosticHistory/DiagnosticRecord). "
        "The live store is core/session_repo over diagnostic_sessions. Carries a "
        "3.0/1.0/0.5/2.0 scoring ladder (history.py:287-311) never measured. Its "
        "only referrer is engine/retrieval.py, also in this table."),
    "motodiag.hardware.protocols.models": ("superseded",
        "Phase 134 containers (PIDResponse, DTCReadResult, ProtocolConnection). "
        "The docstring says the adapters populate these; the adapters Phases "
        "135-139 built return plain list[str]/Optional[int] through "
        "ProtocolAdapter (base.py:101-143), and nothing in the tree constructs "
        "any of the three. An unfulfilled contract."),
    "motodiag.auth.roles_repo": ("superseded",
        "Phase 112 RBAC repo (create_role, assign_role, grant_permission...). "
        "The live permission check, shop/rbac.py:299-320, walks the same "
        "roles/role_permissions/permissions tables with its own SQL; the write "
        "path exists only as migration-005 seed data. Nothing calls these to "
        "change a role."),

    # -- substrate: built ahead for a named roadmap row ----------------------
    "motodiag.media.photo_annotation": ("substrate",
        "Phase 119 photo-annotation model (AnnotationShape, PhotoAnnotation), "
        "awaiting Phase 307 (photo annotation). Distinct from Phase 105's "
        "timestamp-based video annotation, which is live."),
    "motodiag.media.photo_annotation_repo": ("substrate",
        "Phase 119 CRUD over photo_annotations, awaiting Phase 307. The table "
        "has no live reader or writer."),
    "motodiag.inventory.item_repo": ("substrate",
        _SUBSTRATE_118 + ": inventory-item CRUD over inventory_items, awaiting "
        "Phase 279 (parts inventory with reorder points). The live parts path "
        "(shop/parts_needs, api/routes/parts) uses parts/parts_requisitions/"
        "work_order_parts, not this table."),
    "motodiag.inventory.vendor_repo": ("substrate",
        _SUBSTRATE_118 + ": vendor CRUD, awaiting Phases 282-286 (vendor "
        "integrations). vendors has no live reader or writer."),
    "motodiag.inventory.warranty_repo": ("substrate",
        _SUBSTRATE_118 + ": warranty CRUD, awaiting Phase 280 (OEM warranty "
        "claims) and Gate 16. warranties has no live reader or writer."),
    "motodiag.billing.payment_repo": ("substrate",
        _SUBSTRATE_118 + ": customer-payment CRUD over payments, awaiting Phase "
        "273 (Stripe Connect / card terminals). Distinct from the live Phase 176 "
        "subscription path (billing/subscription_repo, billing/providers), "
        "which is the platform charging the shop, not the shop charging a "
        "customer."),
    "motodiag.feedback.learning_hook": ("substrate",
        "Phase 116 read-only FeedbackReader over diagnostic_feedback and "
        "session_overrides, awaiting Track R Phases 318-327 (human-in-loop "
        "learning). Its only non-init mention is a string literal in "
        "core/migrations.py:545 — the case that made Phase 244W blank prose."),

    # -- unwired-feature: complete, tested, reachable by nothing -------------
    "motodiag.engine.retrieval": ("unwired-feature",
        "Phase 89 similar-case retrieval (CaseRetriever; symptom/vehicle/year "
        "weights 0.50/0.30/0.20 at retrieval.py:44-46, never measured). Reads "
        "only from engine/history.py, above, so it cannot run against real "
        "sessions without a rewrite."),
    "motodiag.engine.confidence": ("unwired-feature",
        "Phase 85 evidence-to-confidence scorer: 19 hardcoded numbers and a "
        "non-monotonic curve (audit 2026-09-17, consensus 2.3/10). Its two "
        "public functions were ORPHANS entries until this table absorbed them."),
    "motodiag.engine.correlation": ("unwired-feature",
        "Phase 90 symptom-cluster rules. Whole-string matching returns nothing "
        "on real input, and CORR-001 diagnoses a coolant-jacket leak on an "
        "air-cooled twin (correlation.py:71-82). Consensus 3.0/10."),
    "motodiag.engine.cost": ("unwired-feature",
        "Phase 86 repair-cost estimator: floats-as-dollars beside an "
        "integer-cents invoicing path (shop/invoicing.py), hardcoded labour "
        "rates that disagree with themselves (cost.py:28 vs :97). Third "
        "costing implementation; consensus 2.0/10, delete candidate."),
    "motodiag.engine.evaluation": ("unwired-feature",
        "Phase 91 quality scorecard. Its data source, diagnostic_feedback, has "
        "0 rows and no writer; absent data scores as perfect "
        "(evaluation.py:102-122). Consensus 2.0/10, delete candidate."),
    "motodiag.engine.intermittent": ("unwired-feature",
        "Phase 87: 12 authored intermittent-fault patterns. Unbounded substring "
        "keyword matching (intermittent.py:584) ranks false positives above "
        "true ones; its charging thresholds contradict what `ref circuit "
        "charging` prints. Consensus 4.0/10."),
    "motodiag.engine.parts": ("unwired-feature",
        "Phase 83 AI parts recommender. Every call spends money through ask() "
        "with no cost ledger row, no stop_reason check, and no labelling of "
        "model-invented part numbers and prices. Consensus 3.3/10."),
    "motodiag.engine.repair": ("unwired-feature",
        "Phase 84 AI repair-procedure generator. REPAIR_PROMPT:106 instructs "
        "the model to invent torque specs and nothing labels them on screen; "
        "the audit's single highest risk. Consensus 4.3/10."),
    "motodiag.engine.workflows": ("unwired-feature",
        "Phase 82 guided-troubleshooting scripts. is_complete() ends the "
        "charging workflow on its first FAIL, leaving 3 of 4 steps "
        "unreachable (workflows.py:120-123). Consensus 4.3/10."),
}
