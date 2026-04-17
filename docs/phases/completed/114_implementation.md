# MotoDiag Phase 114 — Workflow Template Substrate

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-17

## Goal
Create the persistent workflow template substrate that Track N phases 259-272 (PPI, tire service, winterization, break-in, emissions, valve/brake/suspension/drivetrain service) will consume. Adds `workflow_templates` and `checklist_items` tables plus a new `src/motodiag/workflows/` package with template/checklist CRUD. Seeds 2 built-in templates (generic PPI + generic winterization) with 9 starter checklist items to validate the schema. Does not build actual Track N workflow content — that's Track N's job.

CLI: `python -m pytest tests/test_phase114_workflow_substrate.py -v`

Outputs: `src/motodiag/workflows/` package, migration 007, 32 tests

## Logic
1. **Migration 007**:
   - `CREATE TABLE workflow_templates` — slug (unique), name, description, category, applicable_powertrains (JSON), estimated_duration_minutes, required_tier, created_by_user_id (FK users), is_active, timestamps
   - `CREATE TABLE checklist_items` — template_id (FK, ON DELETE CASCADE), sequence_number, title, description, instruction_text, expected_pass/fail, diagnosis_if_fail, required, tools_needed (JSON), estimated_minutes
   - 2 indexes: category, slug on templates; template_id on checklist_items
   - Seeds 2 built-in templates: `generic_ppi_v1` (5 items) + `generic_winterization_v1` (4 items)
   - Rollback drops both tables

2. **`workflows/models.py`**:
   - `WorkflowCategory` enum: 13 members covering all Track N workflow types + diagnostic (DIAGNOSTIC, PPI, TIRE_SERVICE, CRASH_SUPPORT, TRACK_PREP, WINTERIZATION, DE_WINTERIZATION, BREAK_IN, EMISSIONS, VALVE_SERVICE, BRAKE_SERVICE, SUSPENSION_SERVICE, DRIVETRAIN_SERVICE)
   - `WorkflowTemplate`: 10 fields, defaults to 3-powertrain support and individual tier
   - `ChecklistItem`: 11 fields including required/tools_needed/estimated_minutes

3. **`workflows/template_repo.py`** — 10 functions:
   - Template CRUD: create, get, get_by_slug, list (filters: category/powertrain/is_active), update, deactivate, count
   - Checklist CRUD: add_checklist_item, get_checklist_items (ordered by sequence), update, delete
   - JSON field handling: applicable_powertrains and tools_needed serialized as JSON, deserialized on read

## Key Concepts
- Bridges Phase 82's in-memory DiagnosticWorkflow engine to persistent, shop-definable templates — Track N and Track Q phases can now create custom workflows
- Composite constraint on templates: slug (unique) + category allows "two different shops can both have templates with different slugs but same category"
- `required_tier` gates access: shop+ can create custom templates, individual uses built-ins only (enforced at use-time by CLI/API, not migration)
- `applicable_powertrains` JSON array allows ICE-only, electric-only, or universal templates — winterization is ICE/hybrid only because electric bikes don't need fuel stabilizer
- ON DELETE CASCADE on checklist_items ensures deleting a template cleanly removes its items — no orphans
- FK on created_by_user_id → users with ON DELETE SET DEFAULT 1 means if a shop owner account is deleted, their custom templates revert to system-owned (not lost)
- PPI and winterization seed templates are MINIMAL content — they exist to validate the schema and provide a baseline. Track N phase 259 expands PPI to engine+chassis with 20+ items; phase 264 expands winterization with make-specific variants
- `list_templates(powertrain="electric")` uses substring match on JSON — sufficient for simple slug values, Track O may upgrade to proper JSON query if this becomes a hotspot

## Verification Checklist
- [x] Migration 007 creates workflow_templates + checklist_items tables (2 tests)
- [x] 2 built-in templates seeded (PPI + winterization) with correct metadata (3 tests)
- [x] PPI has 5 starter checklist items in correct sequence (2 tests)
- [x] Winterization has 4 starter checklist items (1 test)
- [x] tools_needed parsed as list on read (1 test)
- [x] Schema version bumped to 7 (1 test)
- [x] Rollback drops workflow tables cleanly (1 test)
- [x] WorkflowCategory enum has all 13 members (3 tests)
- [x] Template model defaults + full field population (2 tests)
- [x] ChecklistItem model minimal + full (2 tests)
- [x] Template CRUD: create, get, by_slug, list, filters, update, deactivate, count (10 tests)
- [x] Checklist item CRUD: add, ordered retrieval, update, delete, cascade on template delete (5 tests)
- [x] All 1769 pre-phase-114 tests still pass (full regression)
- [x] All 32 new Phase 114 tests pass (3.02s)

## Risks
- JSON field queries limited. **Accepted:** substring match on JSON applicable_powertrains is sufficient for simple cases; proper JSON queries can be added later if needed.
- Forgot forward-compat test pattern again. **Discovered + fixed:** test_schema_version_at_7 used `== 7` hardcode. Switched to `>= 7`, and pre-emptively fixed Phase 113's `== 6` test (which had just started failing due to Phase 114 bumping version to 7). Pattern now applied: all schema version tests use `>=`.

## Deviations from Plan
- Seeded 2 starter templates with 9 checklist items total (plan said "seed schema validation" without specifying count).
- Pre-emptively fixed Phase 113's test_schema_version_at_6 to use >= — same forward-compat pattern.
- Added ON DELETE CASCADE on checklist_items FK and ON DELETE SET DEFAULT 1 on created_by_user_id FK — both good practices not explicitly in plan.

## Results
| Metric | Value |
|--------|-------|
| Files created | 3 (workflows/__init__.py, workflows/models.py, workflows/template_repo.py) |
| Files modified | 3 (migrations.py, database.py, tests/test_phase113_crm_foundation.py) |
| New Pydantic models | 2 (WorkflowTemplate, ChecklistItem) |
| New enums | 1 (WorkflowCategory with 13 members) |
| New DB tables | 2 (workflow_templates, checklist_items) |
| New indexes | 3 (category, slug, template_id) |
| New repo functions | 10 (7 template + 4 checklist) |
| Seeded data | 2 templates, 9 checklist items |
| Tests added | 32/32 passing in 3.02s |
| Tests fixed | 1 (Phase 113 schema version hardcode) |
| Full regression | 1801/1801 passing in 3m 35s (zero regressions) |
| Schema version | 6 → 7 |

Key finding: The workflow template substrate unlocks Track N (13 non-diagnostic workflow types) AND provides a persistence layer for Phase 82's in-memory workflows — a dual benefit not fully planned. Track N phases can build on this by calling `create_template + add_checklist_item` in bulk. The WorkflowCategory enum's 13 members map 1:1 to Track N phases 259-272 (except for de_winterization which pairs with winterization phase 265). All cross-phase migration version test hardcodes now proactively use `>=` pattern — no more phase-N+1 breaking phase-N's tests.
