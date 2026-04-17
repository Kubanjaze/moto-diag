# MotoDiag Phase 114 — Workflow Template Substrate

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-04-17

## Goal
Create the persistent workflow template substrate that Track N phases (259-272) will consume for non-diagnostic workflows (PPI, tire service, winterization, break-in, emissions compliance, valve/brake/suspension service). Adds `workflow_templates` and `checklist_items` tables plus a new `src/motodiag/workflows/` package with repo functions. Extends Phase 82's `DiagnosticWorkflow` engine to load templates from the database (vs. hardcoded templates). Does not build the actual Track N workflows yet — just the substrate.

CLI: `python -m pytest tests/test_phase114_workflow_substrate.py -v`

Outputs: `src/motodiag/workflows/` package, migration 007, tests

## Logic
1. **Migration 007**:
   - `CREATE TABLE workflow_templates` — id, slug (unique), name, description, category (diagnostic/ppi/tire/winterization/break_in/emissions/valve_service/brake_service/etc.), applicable_powertrains (JSON), estimated_duration_minutes, required_tier, created_by_user_id, is_active, created_at, updated_at
   - `CREATE TABLE checklist_items` — id, template_id (FK), sequence_number, title, description, instruction_text, expected_pass, expected_fail, diagnosis_if_fail, required (bool), tools_needed (JSON), estimated_minutes
   - Seed 2 starter templates to validate the schema: generic PPI (10 checklist items) and generic winterization (8 items)

2. **`src/motodiag/workflows/models.py`**:
   - `WorkflowCategory` enum (13 categories matching Track N phases + diagnostic)
   - `WorkflowTemplate` model
   - `ChecklistItem` model

3. **`src/motodiag/workflows/template_repo.py`** — CRUD for templates + checklist items, query by category/powertrain, load_template_to_workflow helper

## Key Concepts
- Bridges Phase 82's in-memory `DiagnosticWorkflow` to persistent shop-definable templates
- `WorkflowCategory` enum enumerates all 13 Track N workflow types + diagnostic
- `required_tier` gates templates: shop+ can customize, individual tier uses built-ins
- Seed templates validate schema; Track N phases replace with full content
- `applicable_powertrains` lets a template be ICE-only, electric-only, or universal
- `created_by_user_id` enables shops to create custom templates (required_tier='shop')

## Verification Checklist
- [ ] Migration 007 creates workflow_templates + checklist_items tables
- [ ] 2 seed templates present (PPI + winterization)
- [ ] WorkflowCategory enum has all 13 categories
- [ ] Template CRUD works
- [ ] Checklist item CRUD works
- [ ] Query by category/powertrain works
- [ ] All 1769 existing tests still pass
