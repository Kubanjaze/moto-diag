# deploy — changelog

## 2026-10-08 — the diff sees a column a migration adds (Phase 380, bug fix #1)

- **The defect.** `diff()` kept only the old table's columns. For a migration
  adding a column, a scope `to` on it crashed (085's dry run), the exact diff
  dropped its values, and a change in it was not a moved field.
- **The change.** Both sides are lined up on the union of the two column
  lists. `tests/test_phase380_deploy_new_column.py` gives 3 failed before
  the fix and 3 passed after.

## 2026-10-08 — seed parity for content migrations (Phase 380, the operator's 2A)

The operator: "With 2A, each content migration's dry run shows the changed
rows equal a fresh seed build, by key, so the seed and live can't drift."
- `seed_parity` builds the seed at HEAD on a scratch database (`init_db` and
  every known-issue seed file), then compares every `known_issues` row the
  migration adds or changes, by `row_key`, every column but the id and the
  clocks.
- A difference, or a key no seed entry holds, is a scope problem. The dry run
  records it, and `apply-live` refuses, both on the recorded problem and on
  its own fresh run.
- It runs only when the copy has `row_key` (migration 085 on).
- The build is injectable (`parity_build`), so
  `tests/test_phase380_seed_parity.py` never builds the real seed. It covers
  a clean case, a drifting migration, a seed edited after the approval, and
  a key no seed holds.
- Its first real run read the backup's columns, which have no `row_key`, and
  checked nothing in 0.0 s. It now reads the copy's columns.

## 2026-10-08 — verify-live fails on a mismatch (Phase 379, F197)

The operator: "379 = the nine small fixes."
- `verify-live` exits 3 when live does not equal the approved exact diff.
  Before, it printed "no" and exited 0, which is how the advisor found it
  on 376.
- It says whether live's schema version is above the phase's own (read
  from the dry run's "Migrations applied on the copy"), in which case a
  later migration explains the difference.
- `tests/test_phase379_verify_live_fails.py`: the known-bad case is an
  approved diff missing one live row.

## 2026-10-07 — apply-live after the regression of record; verify-live (Phase 378, K18, K25, K27)

The operator: "approved: 378 = K18–K25." "K27: (a) now, (b) once the
first shop's real data is in."

- **K18.** `apply-live` refuses unless:
  - the phase log in `in_progress/` carries a regression line A5 can read
    (`closeout_check.regression_line`);
  - no code path changed between its commit and HEAD
    (`code_after_regression.is_code`, verify_phase's check 2 scope);
  - no code path is uncommitted.

  376 applied 083 before its regression, and nothing stopped it. The
  known-bad logs are `fixtures/k18/`. 358's fixture repository now records
  a regression line, so the older apply tests pass for their own reason.
  `tests/test_phase378_deploy_order.py`.
- **K25.** `verify-live <phase>` is new, read-only. It copies live and the
  phase's backup, the backup opened `immutable=1`; the WAL control shows a
  plain read-only open leaves `-shm`. It prints:
  - the schema and row differences;
  - whether they equal the approved exact diff (`<clock>` matched by
    shape);
  - integrity and foreign keys.

  `tests/test_phase378_verify_live.py`.
- **K27.** The skill records the operator's call: 5 backups now, 5 plus the
  first of each week once the first shop's real data is in. `KEEP` is
  unchanged.

## 2026-09-28 — apply-live compares the fresh dry run with the approved diff (Phase 357, F172)

The operator: "Make `deploy.py apply-live` refuse unless its fresh dry
run's diff equals the committed diff field for field, with timestamps
masked." Phase 359 made this comparison by hand.
- **The dry-run file ends with the exact diff**, as JSON after a second
  marker: every field of every added and removed row, before and after of
  every changed field. The markdown report shows only three fields of an
  added row, so it could not be the thing compared.
- **Clock values are masked** as `<clock>`: a timestamp-shaped value
  within one day of the run's own UTC clock. That is what 359 masked by
  hand (the new `applied_at`, four `updated_at`). A fixed date is compared.
- **apply-live refuses** when a fresh run differs in any field, naming
  each by its path, and refuses a diff file written before this change.
  After the live apply, the live diff says whether live equals the
  approved exact diff; a difference there is a scope problem, exit 1.
- **Schema objects are diffed and scoped** too: tables, indexes, triggers
  and views added, removed or rewritten, with their SQL. Phase 357's
  migration adds tables and no rows but one `schema_version` row, so a
  rows-only diff would not have shown what the operator approves. A
  scope names them under `"schema"`.
- **Controls:** `tests/test_phase357_deploy_exact.py` — one field differs
  (refused; the same edit passes the scope check alone), only the clock
  differs (applies), a fixed date differs (refused), an old diff file
  (refused), an unnamed new table (scope problem), a named table whose
  SQL differs (refused). `357_mutate.py F172`: 6/6 red.

## 2026-09-27 — a scope entry's `to` (Phase 359)

The operator's condition on live row 4615: "the dry-run diff shows 4615
changing only to its seed text, field for field, and nothing else." A
scope entry's `fields` already hold "nothing else". A new optional `to`
(`{field: value}`) holds "only to": after the migration the field must
equal that value. Otherwise it is a scope problem, so the dry run records
it and apply-live refuses.
- **Checked** in the dry run, the pre-apply fresh run, and after the live
  apply (`expected()`, and `check_scope`'s new argument).
- **The problem message has no backticks:** the diff header's parser reads
  a value between them, and a backtick in the message broke it (found by
  the new test).
- `tests/test_phase359_deploy_to.py` holds the known-bad case: the allowed
  field changes, but to other text. Ignoring `to` turned it red (Phase 359
  mutation M4).
- First real use: Phase 359's scope gives every changed field its value:
  26 known-issue rows, 4 templates, 2 items.

## 2026-09-27 — created (Phase 358, K3)

The operator: "deploy script in the repo. it writes the approved dry-run
diff into the phase folder, and the live apply refuses to run without that
file. no more temp copies." And, accepted at v1.0: "live apply refuses
unless the diff file is committed and unchanged."

- **Where it came from:** Phase 262's `deploy262.py`, kept verbatim with
  its sha256 in `358_step0.md`. What changed from it:
  - the scope is JSON in the phase folder, no longer Python constants;
  - the diff goes to the phase folder, no longer the scratchpad;
  - copies go to the gitignored `data/deploy_scratch/` and are deleted;
  - the census is `scripts/f158_census.py`;
  - the paths are arguments;
  - the apply refuses without a committed, unchanged diff, and when the
    diff records a scope problem, the backup's hash moved, or the scope
    file changed.
- **Controls, in the contract test, on fixture databases:**
  - each refusal: no file, uncommitted, edited after commit, an
    out-of-scope dry run, live changed, a fresh dry run out of scope, the
    scope changed, the backup gone;
  - a clean apply;
  - retain-5;
  - an ambiguous scope entry refused.
- **Four mutations were each seen red and reverted:** the committed check,
  the unchanged check, live-equals-backup, and the fresh scope check.
  Under each, the fixture's "live" was migrated.
- **358 never ran it against live.** Its first real use is the content
  phase.
