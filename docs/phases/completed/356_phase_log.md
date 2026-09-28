# Phase 356 — In-memory workflow runner — phase log

**Status:** ✅ Complete (2026-09-28)
**Branch:** `phase-356` (Opus session, main checkout, the only writer)

---

### 2026-09-27 — Opened

The prompt is `docs/prompts/356_workflow_runner.txt` (committed in
`12aeec9`, merged `a2eafef`). The operator's order, verbatim
(2026-09-27): "content phase (F159/F163/F166 templates + F158's 27 rows)
→ 356 → 357 → Track O." 359 closed the content phase.

- Row 356 🚧, and F172 and F173 filed with the finding skill, as the
  first commit: `e86be59`.
  - F172: `apply-live` does not compare its fresh dry run with the
    committed diff; a gap to close before 357's live apply.
  - F173: `test_cross_platform_brakes` failed once in parallel in 359's
    first `--full`.

### 2026-09-27 — Step 0, stopped for the operator's pick

`356_step0.md`, committed `7cab578`. Phase 82's engine stops at the first
fail (measured on `brake_service_v1` and `valve_adjustment_v1`), so one
engine change is needed, `stop_on_fail`. Refusals match `show`. Gate 15
is unaffected. The powertrain is a fork: A (ask or flag), B (a garage
bike), C (both). Recommended A.

### 2026-09-28 — The operator's pick, verbatim

> A. Also file a finding for garage add's --powertrain default of "ice"
> (cli/main.py): an electric bike added without the flag is stored as
> ice, and diagnose, the predictor and the safety scoping read that
> value; 357's bike link would inherit it. File it, don't fix it in 356.

- **F174 filed.** Before citing them, each reader was read: diagnose
  (`cli/diagnose.py:466`, `:542`, `:721`), the predictor
  (`advanced/predictor.py:243`) and the priority scorer
  (`shop/priority_scorer.py:321`). One finding changes the premise's
  shape for the safety scoping: `ice` hides no rule from an electric
  bike, because no rule is scoped to electric alone; the seven
  `("ice", "hybrid")` rules are shown to it in addition. The entry says
  so.

### 2026-09-28 — v1.0, then the build

v1.0 and this log committed and pushed before code: `23ea56a`.

- **`engine/workflows.py`:** `stop_on_fail: bool = True`; `is_complete()`'s
  fail clause applies only when it is true.
- **`workflows/runner.py`:** `checklist_workflow(template, items)`, one
  step per item, `max_steps` the item count, `stop_on_fail=False`. An
  item's `expected_pass` and `expected_fail` may be `None`
  (`ChecklistItem` allows it) and the step's are `str`, so each is
  given as `or ""`.
- **`cli/workflow.py`:** `workflow run <slug> [--powertrain]`. `show`'s
  item block became `_print_item` and its lookup `_template_or_refuse`,
  which both commands use, so `run` refuses exactly as `show` does.
- **A manual run** against the Step 0 database (brake_service_v1,
  electric): the items print as `show` prints them. A typed `s` on
  required item 5 printed `Error: 's' is not one of 'p', 'f'.` and asked
  again, so the answers that followed shifted by one and the input ran
  out at item 7 (`Aborted!`, exit 1). That is the refusal working, not a
  fault.
- **`tests/test_phase356_workflow_run.py`, 32 tests, green at the first
  run.** A first green is not evidence, so every helper has a planted
  input it must fail on (12 tests, beside one that the good output
  passes), and the source was mutated:
- **Mutations, `356_mutate.py` (committed with this build): 11/11 red.**
  M1 the engine default no longer stops on a fail; M2 the runner keeps the
  stop; M3 `max_steps` left at the default (the largest template has 8,
  under 10, so only the mapping test sees it); M4 no skip on an optional
  item; M5 no diagnosis on a fail; M6 a retired template not refused; M7
  an uncovered powertrain not refused; M8 a skip counted as a pass; M9 no
  powertrain prompt; M10 the powertrain asked before the template is
  checked; M11 the summary lists no failed item.
- **Related suites** (Phases 82, 95, 114, 259–264, 272, 356): 322 passed.
  Gate 15 is green. The 244G scanner over `tests/`: 0.
- **`wholetree.sh` before the build commit: 2 failed, then 3.** Both
  gates that track unreached code saw `engine.workflows` become reached:
  - 244W: `motodiag.engine.workflows` was in `MODULE_ISLANDS` and is now
    used, a stale entry. Removed. Its pins followed:
    `MODULE_ISLAND_COUNT` 14 → 13, and 244W's engine-entry literal 6 → 5.
  - 209B: with the module reached, its four other public functions
    (`create_no_start_workflow`, `create_charging_workflow`,
    `create_overheating_workflow`, `generate_next_step`) became live
    orphans. Listed in `ORPHANS` as unwired-feature, the charging entry
    keeping the audit's 4.3/10; `ORPHAN_COUNT` 102 → 106.

  Not a bug-fix entry: none of this code had been committed (272's
  precedent). The two edits to `integration_gaps_counts.py` were made
  with an exact-string replace in a short script that asserted one
  occurrence each, not the Edit tool; the diff was read after, and it
  changes only the two counts and their history lines.
  Then `wholetree.sh`: 1475 passed.

### 2026-09-28 — The floor, `--full`, and the first regression

- `COLLECTED_TEST_FLOOR` 9639 → 9711, measured (`3e9b93d`).
- `wholetree.sh --full` at `3e9b93d`: 3866 passed, 80 files, 536.8 s
  wall.
- `regression.sh` at `3e9b93d`: 9710 passed, 1 failed, 20 min 51 s
  wall, `python -m pytest -n auto --dist load`. The failure is below.
  `test_cross_platform_brakes` (F173) passed.

### 2026-09-28 — Bug fix #1: 244Z still pinned engine.workflows as an island

- **Issue:** the regression at `3e9b93d` failed
  `test_phase244Z_shelved_content.py::TestStillShelved::test_the_module_is_still_on_the_islands_table[workflows]`:
  `motodiag.engine.workflows` is no longer in `MODULE_ISLANDS`.
- **Root cause:** a third pin on the module's shelved state, beside the
  two (244W, 209B) the fast whole-tree run caught before the build
  commit. 244Z is in neither `wholetree` mode's member set, so only the
  full suite reaches it. The build removed the island entry and did not
  search `tests/` for every other assertion naming the module.
- **Fix:** 244Z keeps its import test for all six shelved modules and
  asserts the island entry for five (`STILL_ISLANDS`). Its docstring
  says the wire-or-delete decision is the operator's. Row 356, as the
  operator scoped it on 2026-09-26, is that decision for
  `DiagnosticWorkflow`, and none of 244Z's four content pins (repair,
  correlation, intermittent, parts) is about `workflows.py`. The
  predefined scripts stay unreached, listed in ORPHANS.
  `COLLECTED_TEST_FLOOR` 9711 → 9710, deliberately: the removed
  parametrized case.
- **Files:** `tests/test_phase244Z_shelved_content.py`,
  `tests/test_phase255B_collected_test_floor.py`.
- **Verified:** the 244Z file is 24 passed with the fix; with the fix
  stashed it is 1 failed, 24 passed. A search of `tests/` for
  `motodiag.engine.workflows` or `"workflows"` finds 244Z, 356, 82 and
  95; none of the others asserts the island. Collected: 9,710.

**Commit.** `0130f1a`.

### 2026-09-28 — The regression of record

- `wholetree.sh --full` at `0130f1a`: 3866 passed, 80 files, 600.6 s
  wall.
- `test_cross_platform_brakes` (F173) passed in both regressions.

Regression of record: 9710 passed, 0 failed, 0 skipped, 0 errors at `0130f1a` (23 min 33 s wall, `python -m pytest -n auto --dist load`, exit 0)

### 2026-09-28 — Close-out decisions

- No refute pass ran: the phase ships code and no content row, and no
  claim rests on a document (v1.0, D4).
- **F165 stays open.** 356 makes a workflow runnable; nothing records a
  run or an item's result, which is row 357. The entry says so.
- No migration, no live change, no deploy.
