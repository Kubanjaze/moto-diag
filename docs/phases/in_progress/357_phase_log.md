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

### 2026-09-28 — F175 filed and fixed, before Step 0 (the prompt's second commit)

The prompt: "File F175 with the finding skill ... Fix the rule so the class
of test 244Z belongs to joins by rule, not by name. Control: a planted
failure in 244Z turns `wholetree.sh --full` red. If the fix changes fast
mode's members or moves its time toward the guard's 285 s limit, stop and
ask."

- **What 244Z's class is, measured:** of the tests that import a
  `tests/support` module and are not members, 244Y and 244Z import the gap
  tables (`integration_gaps_allowlist`, `integration_gaps_counts`). Those
  modules hold only data, and 209B keeps them equal to the tree.
  `source_guards` is imported by 13 non-members too, but it is shared
  code, not the tree's state; the rule leaves it out, and a fixture holds
  that exclusion.
- **The rule, full mode only:** a test importing a data-only support
  module that a code-class member imports. Full 80 → 82 with the rule;
  fast unchanged.
- **Fast mode, and why this is not the stop:** the rule adds nothing to
  fast. This phase's new test imports `wholetree`, as 358's contract test
  does, so 358's own rule makes it the 32nd fast file (about a second).
  Timed back to back: 105.0 s without the change, 77.6 s with it. The
  spread is the machine. Reported to the operator at Step 0.
- **The control, the run of record:** a failure planted in 244Z, then
  `wholetree.sh --full`, 12:51–12:57: 83 files, `1 failed, 3945 passed`,
  exit 1. The plant was removed and 244Z's diff is clean.
  - An earlier run at 10:38 gave the same result. The machine then slept
    before anything was committed, and the operator, verbatim: "The F175
    entry already says the planted control turned --full red, but that
    run hadn't happened when the machine slept: run it now (plant in
    244Z, --full red, remove, diff clean), then commit F175 and Step 0,
    and stop for my powertrain pick." Made again as asked; the documents
    cite the second run.
- `357_mutate.py F175`: 4/4 red.
- Also filed: F176 (`garage remove` on a bike a work order names ends in
  a traceback), and an amendment to F174 (a fourth `ice` default in the
  API; the CLI cannot correct a stored powertrain). Both measured at
  Step 0.

### 2026-09-28 — Step 0, stopped for the operator's pick

`357_step0.md`. K8: five verbs, five commands. What is reused from 356
and what changes. The schema: `workflow_runs`, `workflow_run_items`,
three indexes; the migration only adds. The powertrain is a fork:
A, A+ (recommended), B, C.

### 2026-09-28 — The operator's pick, verbatim

> A+.

Option A+ of `357_step0.md` S0-4: the powertrain from `--powertrain` or
the prompt; a bike whose stored value disagrees is refused; `garage
update` gains `--powertrain`. F174 stays open.

### 2026-09-28 — v1.0

`357_implementation.md` v1.0, committed and pushed before code.
