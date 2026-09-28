# Phase 357 — Saved workflow runs — phase log

**Status:** 🚧 In progress
**Branch:** `phase-357` (Opus session, main checkout, the only writer)

---

### 2026-09-28 — Opened

The prompt is `docs/prompts/357_saved_workflow_runs.txt` (committed in
`215a030`, merged `b0ff03a`). The operator's order, verbatim
(2026-09-27): "content phase (F159/F163/F166 templates + F158's 27 rows)
→ 356 → 357 → Track O." 356 closed on 2026-09-28.

Read first: the 356 handoff (`docs/handoffs/2026-09-28_356_closed.md`),
F165, F172 and F174, 356's documents, and the deploy skill.

- Row 357 🚧: `5076216`. `roadmap_check.py` green.

### 2026-09-28 — F172 closed, before Step 0 (the prompt's first commit)

The prompt: "Make `deploy.py apply-live` refuse unless its fresh dry run's
diff equals the committed diff field for field, with timestamps masked.
Known-bad fixture: a fresh dry run that differs in one field is refused.
The good case applies."

Decisions, each made here and not a stop:
- **What is compared is a new JSON block, not the markdown report.** The
  report prints three fields of an added row (`x['b'][k][1:4]`), so two
  runs could differ in a fourth field with equal reports. The dry-run file
  now ends with every field, after a second marker; the file is still
  committed and hash-checked by git as before.
- **The mask is by value and by the run's clock, not by column name.** A
  timestamp-shaped value within one day of the run's UTC clock reads
  `<clock>`. That covers 359's five (`applied_at`, `updated_at`), and
  SQLite's `CURRENT_TIMESTAMP` (UTC) against any local offset. A column
  name rule (`*_at`) would also mask a fixed date a migration writes into
  such a column; this rule compares it. Its ceiling is in the skill.
- **Schema objects are diffed and scoped.** 357's migration adds tables.
  A rows-only diff of it shows one `schema_version` row, so the diff the
  operator approves would not show the tables. The scope names each
  object under `"schema"`. No earlier scope is affected: 262's and 359's
  migrations changed no schema object, and their phases are closed.

Tests, `tests/test_phase357_deploy_exact.py`, 8, with 358's and 359's
deploy tests: 30 passed. `357_mutate.py F172`: 6/6 red (the refusal, no
mask, a mask with no date window, an old file accepted, schema left out
of the exact diff, an unnamed schema change let through). F172 closed in
`docs/FOLLOWUPS.md`.
