# MotoDiag Phase 121 — Gate R: Retrofit Integration Test

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-04-17

## Goal
Gate R is the retrofit integration checkpoint. Prove that all 11 retrofit-era additions (phases 110-120 — migrations 003-012, 12 new packages, 23 new tables, ~280 new tests) work together in an end-to-end scenario AND that fresh DB init + full migration replay produce identical state. No new features, no new packages. Only: **one big integration test file** that wires every retrofit package into a realistic shop workflow, plus migration replay verification. This is the pass/fail checkpoint before Track D resumes from Phase 122.

CLI: `python -m pytest tests/test_phase121_gate_r.py -v`

Outputs: `tests/test_phase121_gate_r.py` (~20 integration tests), no production code changes

## Logic

### Part A — End-to-end shop workflow integration

Build a single cohesive scenario that exercises every retrofit package in one DB:

1. **Setup user & customer (Phases 112, 113)**:
   - Create owner user + tech user via `auth.users_repo`
   - Grant roles + verify permissions
   - Create customer via `crm.customer_repo`

2. **Add a European electric bike (Phase 110)**:
   - Register a LiveWire One (make="Harley-Davidson", model="LiveWire One", year=2024, powertrain=ELECTRIC, protocol=J1939) via `vehicles.registry`
   - Assign customer → vehicle via `crm.customer_bikes_repo`

3. **DTC from expanded taxonomy (Phase 111)**:
   - Add an HV_BATTERY category DTC specific to the electric bike
   - Query via the category meta table to verify the taxonomy works

4. **Diagnostic session with feedback (Phases 07, 116)**:
   - Open diagnostic session, attach DTCs
   - Close session with a mock diagnosis
   - Submit `DiagnosticFeedback` (outcome=PARTIALLY_CORRECT)
   - Record a `SessionOverride` on the diagnosis field
   - Verify `FeedbackReader.get_accuracy_metrics()` reflects the outcome

5. **Workflow template execution (Phase 114)**:
   - Load the seeded `generic_ppi_v1` template
   - Verify its 5 seed checklist items are present

6. **i18n lookups (Phase 115)**:
   - Pull `t("welcome", namespace="cli")` → "Welcome to MotoDiag"
   - Pull `t("severity_critical", namespace="diagnostics")` → "Critical"
   - Verify fallback chain: nonexistent key → `[ns.key]`

7. **Reference data wiring (Phase 117)**:
   - Add a manual_reference for the LiveWire
   - Add a parts_diagram citing that manual
   - Add a failure_photo (submitted by tech user)
   - Verify year-range filter works with `list_manuals(target_year=2024)`

8. **Photo annotation on the failure photo (Phase 119)**:
   - Add 3 photo annotations (circle + arrow + text) to the failure_photo
   - Verify `list_annotations_for_failure_photo` returns all 3
   - Delete the failure_photo → verify annotations CASCADE

9. **Ops substrate (Phase 118)**:
   - Create subscription (tier=SHOP, status=ACTIVE) for the owner user
   - Record a successful $99 payment
   - Create an invoice for the customer, add line items (labor + parts)
   - `recalculate_invoice_totals(tax_rate=0.0875)` → verify subtotal/tax/total
   - Schedule an appointment (type=DIAGNOSTIC) assigned to the tech user
   - Add inventory item + vendor + recall record for the LiveWire
   - Register warranty on the vehicle

10. **Sound signature lookup (Phase 120)**:
    - Look up `SIGNATURES[EngineType.ELECTRIC_MOTOR]` for the LiveWire
    - Verify cylinders=0, idle_rpm_range=(0,0), whine frequency fields populated

11. **Final integrity check**:
    - Count rows across all retrofit tables — should all be non-zero for the ones touched
    - Query `get_schema_version(db) >= 12`
    - Query `get_applied_migrations(db)` returns [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12] (baseline + 10 retrofit)

### Part B — Migration replay verification

Two tests prove migrations produce consistent state:

1. **`test_fresh_db_ends_at_schema_version_12`**: `init_db(new_path)` on blank DB → verify all 12 schema versions recorded, all 23 retrofit tables present.

2. **`test_rollback_and_replay_identical_tables`**:
   - Init fresh DB (applies all 10 retrofit migrations)
   - Collect table set A
   - `rollback_to_version(2, db)` → back to baseline
   - `apply_pending_migrations(db)` → reapply all 10
   - Collect table set B
   - Assert A == B (migration replay is deterministic)

### Part C — CLI smoke test

One quick test: `python -m motodiag --help` returns successfully (no import errors from any retrofit package). Run via subprocess.

## Key Concepts
- **Gate R is a checkpoint, not a feature**: no new production code, no new packages. Success criterion is the whole system behaves coherently when pushed through a realistic workflow.
- **One cohesive scenario**: rather than 11 disconnected tests (one per retrofit phase), Gate R uses a single shared database fixture that every step builds on. This catches cross-package bugs that siloed tests miss (e.g., FK integrity between auth.users and billing.subscriptions, workflow references to the workflow_templates table after i18n migration).
- **Migration replay test**: the rollback-and-replay pattern guarantees migrations 003-012 are idempotent and order-stable. If any future phase adds a migration that depends on implicit state, this test catches it.
- **No new production code**: if Gate R reveals a bug, the fix goes in a follow-up phase (or an immediate hotfix commit with a CHANGELOG entry), not inside Phase 121 itself. Gate R is purely observation.
- **CLI smoke test covers import graph**: `motodiag --help` exercises the entire import chain — if any retrofit package has a circular import or a module-level side effect, `--help` will fail. Cheap insurance.

## Verification Checklist
- [ ] End-to-end scenario creates user → customer → vehicle → session → feedback → override → workflow → i18n → reference → annotation → ops → sound sig → verifies row counts
- [ ] All 10 retrofit migrations applied in order on a fresh DB
- [ ] Schema version ends at >= 12
- [ ] Fresh DB and replayed DB have identical table sets
- [ ] CLI smoke test: `python -m motodiag --help` exits 0
- [ ] FK CASCADE tested in the main scenario (photo delete → annotations gone)
- [ ] Invoice recalculation produces expected totals with tax
- [ ] FeedbackReader.get_accuracy_metrics returns non-zero after feedback submission
- [ ] i18n fallback chain works in integration (not just unit tests)
- [ ] Electric bike powertrain field flows from vehicle registry to sound signature lookup
- [ ] All 1992 existing tests still pass (zero regressions)

## Risks
- **Gate R failure = retrofit is not done**: if this phase finds a cross-package bug, the retrofit can't close. The bug gets fixed (as a follow-up) before Phase 122 starts. Accepted — this is the entire point of the gate.
- **Test file size**: one big scenario test could be 200+ lines. Acceptable — integration tests are naturally longer than unit tests, and splitting them defeats the purpose (each step depends on the previous step's state).
- **Subprocess CLI test flakiness**: running `python -m motodiag` via subprocess is platform-sensitive. Mitigated by using `sys.executable` (the same interpreter running pytest) and checking only exit code + basic stdout content.
- **Test runtime**: adds ~1-2 seconds to the regression suite. Acceptable given the confidence it provides.
