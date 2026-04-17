# MotoDiag Phase 116 — Feedback/Learning Hooks

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-04-17

## Goal
Create the feedback/learning substrate that Track R phases 318-327 (human-in-loop learning, continuous learning, repair success prediction) will consume. New `src/motodiag/feedback/` package plus `diagnostic_feedback` table that records what actually went wrong versus what the AI suggested. Adds a read-only hook interface on the AI engine so future Track R phases can pull feedback history to retrain or fine-tune ranking. Does not build the learning loop itself — this is plumbing only.

CLI: `python -m pytest tests/test_phase116_feedback.py -v`

Outputs: `src/motodiag/feedback/` package (4 files), migration 009, ~35 tests

## Logic
1. **Migration 009**:
   - `CREATE TABLE diagnostic_feedback` — session_id (FK diagnostic_sessions ON DELETE CASCADE), submitted_by_user_id (FK users DEFAULT 1), ai_suggested_diagnosis, ai_confidence, actual_diagnosis, actual_fix, outcome (enum: correct/partially_correct/incorrect/inconclusive), mechanic_notes, parts_used (JSON), actual_labor_hours, submitted_at
   - `CREATE TABLE session_overrides` — session_id (FK diagnostic_sessions), field_name (e.g., 'diagnosis', 'severity', 'cost_estimate'), ai_value, override_value, overridden_by_user_id, overridden_at, reason
   - 3 indexes: session_id on both, outcome on diagnostic_feedback
   - Rollback drops both tables

2. **`feedback/models.py`**:
   - `FeedbackOutcome` enum: CORRECT, PARTIALLY_CORRECT, INCORRECT, INCONCLUSIVE
   - `OverrideField` enum: DIAGNOSIS, SEVERITY, COST_ESTIMATE, CONFIDENCE, REPAIR_STEPS, PARTS
   - `DiagnosticFeedback` Pydantic model — all columns typed, parts_used serialized as JSON
   - `SessionOverride` Pydantic model — field_name limited to OverrideField enum

3. **`feedback/feedback_repo.py`** — CRUD:
   - `submit_feedback(feedback)`, `get_feedback(feedback_id)`, `get_feedback_for_session(session_id)`
   - `list_feedback(outcome=None, user_id=None, limit=None)` with filters
   - `count_feedback_by_outcome()` — returns dict keyed by outcome enum
   - `record_override(override)`, `get_overrides_for_session(session_id)`, `count_overrides_for_field(field)`

4. **`feedback/learning_hook.py`** — read-only interface for future Track R:
   - `FeedbackReader` class with `iter_feedback(since=None, outcome=None)` generator, `get_accuracy_metrics()` → dict with correct/partial/incorrect/inconclusive ratios, `get_common_overrides()` → top-N fields that are overridden most often
   - No side effects — pure reads. Track R phases build the learning loop on top of this.

5. **`feedback/__init__.py`** — exports public API.

6. **`database.py`**: `SCHEMA_VERSION` 8 → 9.

## Key Concepts
- Feedback is per-session, submitted after a diagnostic session closes
- Outcome values let Track R compute AI accuracy over time without re-parsing free-text notes
- `session_overrides` captures every field where the mechanic disagreed with the AI — richer signal than just "was the overall diagnosis correct"
- `FeedbackReader` is intentionally read-only — keeps the feedback loop decoupled from the learning implementation (which lands in Track R)
- Feedback records are immutable once submitted (no update/delete in the repo) — preserves training signal integrity
- `parts_used` as JSON array — Track R can join to the parts catalog (Phase 118) when that lands

## Verification Checklist
- [ ] Migration 009 creates diagnostic_feedback and session_overrides tables
- [ ] FeedbackOutcome enum has 4 members
- [ ] OverrideField enum has 6 members
- [ ] Submit feedback, read back, confirm JSON parts_used deserializes
- [ ] FK CASCADE: deleting a diagnostic_session cascades feedback deletion
- [ ] System user (id=1) is the default submitter for feedback with no explicit user
- [ ] FeedbackReader.iter_feedback yields submitted feedback in chronological order
- [ ] FeedbackReader.get_accuracy_metrics returns correct ratios
- [ ] record_override + get_overrides_for_session round trips
- [ ] count_feedback_by_outcome returns zero counts for unseeded outcomes
- [ ] Rollback drops both tables cleanly
- [ ] All 1841 existing tests still pass (zero regressions)
- [ ] Schema version assertions use `>=` (forward-compat)

## Risks
- **FK CASCADE concern**: deleting sessions nukes their feedback. For now this is desired — orphaned feedback without session context is not useful for learning. If later phases need soft-delete on sessions, revisit then.
- **Override table growth**: one row per overridden field per session could balloon on power users. Mitigation: add a DELETE WHERE session older than N days policy in a future phase — not needed yet (no production traffic).
- **Feedback immutability**: no update API means a mechanic can't correct a typo in a feedback note. Trade-off accepted for training signal integrity. Fix path: delete + resubmit.
- **Track R hook surface**: if `FeedbackReader` API shape doesn't match what Track R actually needs, we can extend it then — the underlying tables won't change.
