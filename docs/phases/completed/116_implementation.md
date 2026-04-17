# MotoDiag Phase 116 — Feedback/Learning Hooks

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-17

## Goal
Create the feedback/learning substrate that Track R phases 318-327 (human-in-loop learning, continuous learning, repair success prediction) will consume. New `src/motodiag/feedback/` package plus `diagnostic_feedback` and `session_overrides` tables that capture what actually went wrong versus what the AI suggested, and which fields the mechanic overrode. Exposes a read-only `FeedbackReader` hook so future Track R phases can pull feedback history to retrain or fine-tune ranking. Substrate only — the learning loop itself is Track R's job.

CLI: `python -m pytest tests/test_phase116_feedback.py -v`

Outputs: `src/motodiag/feedback/` package (4 files), migration 009, 26 tests

## Logic
1. **Migration 009**:
   - `CREATE TABLE diagnostic_feedback` — session_id (FK `diagnostic_sessions` ON DELETE CASCADE), submitted_by_user_id (FK `users` ON DELETE SET DEFAULT 1), ai_suggested_diagnosis, ai_confidence, actual_diagnosis, actual_fix, outcome (CHECK via enum at app layer), mechanic_notes, parts_used (JSON, NOT NULL DEFAULT '[]'), actual_labor_hours, submitted_at
   - `CREATE TABLE session_overrides` — session_id (FK CASCADE), field_name, ai_value, override_value, overridden_by_user_id (FK), reason, overridden_at
   - 4 indexes: `idx_feedback_session`, `idx_feedback_outcome`, `idx_overrides_session`, `idx_overrides_field`
   - Rollback drops both tables

2. **`feedback/models.py`**:
   - `FeedbackOutcome` enum (4): CORRECT, PARTIALLY_CORRECT, INCORRECT, INCONCLUSIVE
   - `OverrideField` enum (6): DIAGNOSIS, SEVERITY, COST_ESTIMATE, CONFIDENCE, REPAIR_STEPS, PARTS
   - `DiagnosticFeedback` Pydantic model — 10 fields, `parts_used` as `list[str]`, `ai_confidence` bounded 0.0–1.0, defaults to system user (id=1)
   - `SessionOverride` Pydantic model — 8 fields, field_name typed as `OverrideField`

3. **`feedback/feedback_repo.py`** — 8 functions:
   - `submit_feedback` (INSERT, returns id), `get_feedback`, `get_feedback_for_session` (chronological), `list_feedback` (filters: outcome/user/limit, order DESC)
   - `count_feedback_by_outcome` — returns `{outcome_value: count}` for all 4 outcomes including zeros
   - `record_override`, `get_overrides_for_session`, `count_overrides_for_field`
   - No update/delete API on feedback — records are immutable once submitted (preserves training signal integrity)
   - `parts_used` serialized as JSON text column; deserialized on read via `_row_to_feedback`

4. **`feedback/learning_hook.py`** — `FeedbackReader` class:
   - `iter_feedback(since=None, outcome=None)` → generator yielding feedback rows in chronological order
   - `get_accuracy_metrics()` → dict with total, per-outcome counts, `correct_ratio`, `partial_plus_correct_ratio`
   - `get_common_overrides(top_n=5)` → top-N most-overridden fields sorted desc
   - Read-only by design — all writes go through `feedback_repo`. Track R extends this class (adding new read methods is fine; adding writes is a design violation)

5. **`database.py`**: `SCHEMA_VERSION` 8 → 9.

## Key Concepts
- Feedback is per-session, submitted after a diagnostic session closes
- `outcome` values let Track R compute AI accuracy over time without re-parsing free-text notes
- `session_overrides` captures every field the mechanic disagreed on — richer signal than just "was the overall diagnosis correct"
- FK CASCADE on `session_id`: deleting a session purges its feedback and overrides (intentional — orphaned feedback without session context is not useful)
- FK SET DEFAULT on user FKs: if a user is deleted, their feedback/overrides fall back to system user (preserves the training signal)
- `FeedbackReader` is intentionally read-only — Track R's learning loop never writes through this interface
- `iter_feedback` uses a generator to stream large histories without loading everything into memory
- Feedback records are immutable (no update API) — a typo fix requires delete + resubmit (not exposed in Phase 116)

## Verification Checklist
- [x] Migration 009 creates `diagnostic_feedback` and `session_overrides` tables with correct indexes
- [x] `FeedbackOutcome` enum has 4 members
- [x] `OverrideField` enum has 6 members
- [x] Submit feedback → read back with JSON parts_used deserialized correctly
- [x] FK CASCADE: deleting a diagnostic_session cascades feedback and overrides
- [x] System user (id=1) is default submitter for feedback with no explicit user
- [x] `FeedbackReader.iter_feedback` yields submitted feedback in chronological order
- [x] `FeedbackReader.iter_feedback` filter by outcome works
- [x] `FeedbackReader.get_accuracy_metrics` returns correct ratios (7/2/1 → 0.7 correct_ratio, 0.9 partial+correct)
- [x] `get_accuracy_metrics` handles empty history (total=0, ratios=0.0)
- [x] `get_common_overrides` returns top-N sorted desc with correct counts
- [x] `record_override` + `get_overrides_for_session` round trips
- [x] `count_feedback_by_outcome` includes all 4 outcomes with zero counts
- [x] `count_overrides_for_field` accepts both enum and string
- [x] Rollback drops both tables cleanly
- [x] Schema version assertions use `>= 9` (forward-compat)
- [x] All 1841 existing tests still pass (zero regressions) — full suite 1867/1867 in 8:58

## Risks
- **FK CASCADE on session delete**: deleting sessions nukes their feedback. Accepted — orphaned feedback without session context is not useful for learning. If soft-delete on sessions is added later, revisit this.
- **Override table growth**: one row per overridden field per session could balloon on power users. Acceptable at this scale (no production traffic); a retention policy can be added when Track O billing infrastructure lands.
- **Feedback immutability**: no update API means a typo in mechanic_notes can't be corrected. Trade-off accepted for training signal integrity. Fix path (delete + resubmit) not exposed in Phase 116.
- **Track R hook surface extension**: `FeedbackReader` API shape may need extension when Track R actually consumes it. Additive changes are safe; the underlying tables won't change.

## Deviations from Plan
- None. Built exactly to plan: migration 009, feedback/ package with 4 files, 8 repo functions + FeedbackReader with 3 read methods, 26 tests.

## Results
| Metric | Value |
|--------|-------|
| New files | 5 (feedback/__init__.py, models.py, feedback_repo.py, learning_hook.py, test_phase116_feedback.py) |
| New tests | 26 |
| Total tests | 1867 passing (was 1841) |
| New enums | 2 (FeedbackOutcome 4 members, OverrideField 6 members) |
| New models | 2 (DiagnosticFeedback, SessionOverride) |
| Repo functions | 8 + FeedbackReader class with 3 methods |
| Schema version | 8 → 9 |
| Regression status | Zero regressions — full suite 8:58 runtime |

Phase 116 gives Track R a clean, read-only substrate to build the learning loop on: feedback records capture outcome + free-text context + parts used, overrides capture field-level disagreement, and `FeedbackReader.get_accuracy_metrics()` already produces the AI accuracy signal Track R phase 327 (continuous learning) needs as its primary input metric.
