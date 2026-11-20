# Phase 405 — phase log

**Status:** In progress

## 2026-11-20 — Step 0, re-measured by the Engineer

On this branch at `8ba8c66` (v1.0, the Executive Officer's round 3, K97).

- **Line numbers in `.claude/skills/deploy/deploy.py`,** all as the plan
  reads them: `SERVER_WRITES` 184, `server_masked` 189, `schema` 229,
  `exact` 260, `_leaves` 282, `exact_gaps` 291, `check_scope` 358 (schema
  names at 362), `preflight` 567 (drift read 593, refusal 598, fresh copy
  migrated 609), `apply_live` 626, `shape_gaps` 748 (union walk at 754),
  `verify_live` 762 (its one `shape_gaps` call at 804).
- **The callers:** `through_fleet.py` calls `D.apply_live` at 450 and
  `D.verify_live` at 340 and 473; `dispatcher.py`'s `verify_live_here` is
  at 701, and `stage_deployed` at **2087** (the plan says 2109: the file
  moved; what it does, stop on any exit but 0, is as the plan reads);
  `quartermaster.py`'s `database_step` at 153 reads the two header lines
  `**Scope problems:** \`none\`` and `**Equals the approved exact diff:**
  \`yes\`` (167 to 168) and the exit code; `verify_phase.sh` check 8 at 69,
  `remote.py live-check` at 83, the dry-run-diff test at 90; `remote.py`
  `AT_COMMIT` 44, `pushed_head` 78, used at 189; the desktop's
  `live_check` at 247, `at` at 209, "no dry-run diff: no deploy to verify"
  at 260. So `remote.py` sends the Mac's pushed HEAD for `live-check`, and
  the desktop checks that commit out and runs its `deploy.py`.
- **`git grep -n -F 'equals the backup' -- .claude/skills/deploy`,** before
  the work: two lines, `SKILL.md:129` and `deploy.py:26`.
- **Views:** `create view v as select a from t` reads back from
  `sqlite_master` as `('view', 'v', 'v')`; an index and a trigger on `t`
  read `tbl_name` `t`. No migration creates a view (`git grep -n -i -E
  'create +(temp(orary)? +)?view' -- src/motodiag/core/migrations.py`: 0
  lines). `git grep -n -E "approved \[|live \[" -- tests`: 0 lines.
- **The census,** `405_entries_census.py`, last line: "24 files, 21 with an
  exact diff; 20 list a table, 20 of them with an empty dict; <clock>
  inside a changed pair: 0". As the plan reads.
- **`SERVER_WRITES` under the new rule:** it still decides a verdict in one
  place, a listed column the server writes in a touched table between the
  dry run and the apply. See the build entry for the case that shows it.
- **The scope gate and an object the migration never creates:** shown by
  `test_a_scope_naming_an_index_the_migration_never_creates_is_refused_first`
  (the build entry): the fresh dry run's scope check refuses, and the split
  is never reached.

## 2026-11-20 — the build

- **`deploy.py`:** `touched` beside `server_masked`; `tbl_names` beside
  `schema`; `entries` beside `_leaves`; `listed_differences` and
  `approved_holds` beside `shape_gaps`; `drift_gate` and `_counts` beside
  `preflight`. `preflight` reads the approved diff, refuses one with no
  exact diff, runs the fresh dry run's two gates (unchanged), reads
  `names` from the backup and then the migrated copy before `_drop`, and
  only then calls `drift_gate`. `shape_gaps` walks `sorted(a)`: its
  signature and messages are unchanged. `apply_live` no longer reads the
  scope or runs `check_scope` after the migration; its live diff gains
  `Other differences, listed`. `verify_live` prints `other differences,
  listed:` and its items before `equals the approved exact diff`. The
  module docstring's `apply-live` and `verify-live` lines, `verify_live`'s
  docstring and the `SERVER_WRITES` comment block's two "so either one is
  drift" sentences say what holds after 405.
- **`SERVER_WRITES` still decides a verdict, in one place:**
  `TestTheTouchedSet::test_a_listed_server_write_in_a_touched_table_is_still_set_aside`.
  The plan names 383's `TestAMigrationThatWritesTheColumn` scope as the
  case; under that scope the approved diff names `api_keys` row 2
  `last_used_at`, so a request on that row is never set aside (the rule
  "a field the approved diff names never is"). The case used instead is a
  scope that names `api_keys` with nothing expected of it: a request then
  writes `last_used_at` in a touched table, it is set aside, and the apply
  returns 0.
- **The controls K91 moves,** each with the sentence of K91 that moves it
  ("before the apply it refuses only a change since the dry run in a table
  the change touches" for the before-the-apply cases, A; "after the apply,
  and in every later check, the approved changes must hold, and other
  differences are listed, not failed" for the after-the-apply cases, B):
  - `test_phase358_deploy_contract.py::TestTheApplyRefuses::test_when_live_changed_since_the_backup`:
    a `known_issues` row, untouched, now applies and is listed (A); the
    new sibling `test_when_a_touched_table_changed_since_the_backup`
    (a `checklist_items` row) keeps the refusal.
  - `test_phase378_verify_live.py::TestReadingItBack::test_a_row_outside_the_approved_diff_is_reported`:
    exit 0, `rows: known_issues +0 ~1 -0` still printed, the row in the
    listed lines (B). `test_a_masked_clock_matches_any_timestamp_and_nothing_else`
    is unchanged and green.
  - `test_phase379_verify_live_fails.py::test_an_approved_diff_missing_a_live_row_fails`:
    now the approved row deleted from live, exit 3; its old shape is
    `test_a_live_row_the_approved_diff_lacks_is_listed`, exit 0 (B).
    `test_a_later_migration_is_named_as_the_cause_and_still_fails`: the
    later migration alters an approved row, exit 3 with the F197 line; its
    old shape is `test_a_later_migration_that_only_adds_is_listed` (B).
  - `test_phase383_server_writes.py`: `TestTheControlsStillFail`'s three
    before-the-apply cases run under a scope naming their table
    (`api_keys`, `api_keys`, `devices`), still refusing; their
    fixture-scope forms are in `TestListedOutsideTheTouchedTables`, applied
    and listed (A). `test_another_column_after_the_apply` and
    `test_another_table_after_the_apply` moved into that class, exit 0 with
    the change listed (B). `TestAWholeTableKeepsItsControls::test_a_changed_row_before_the_apply`
    runs under a scope naming `audit_events`, still refusing; its
    fixture-scope form, `test_a_removed_row_after_the_apply` and
    `test_another_table_s_added_row_after_the_apply` are in
    `TestAWholeTableListedOutsideTheTouchedTables` (A, B).
    `TestAMigrationThatWritesTheColumn` gains
    `test_the_approved_row_removed_after_the_apply` (version 71 deleted,
    exit 3). `test_the_list_is_exactly_this` is unchanged.
  - `test_phase385_server_writes.py::TestTheControlsStillFail`:
    `test_before_the_apply` runs under a scope naming `device_tokens`:
    `rebind` and `added_row` refuse, beside and alone, and `other_table`
    (`phones`) is listed (A); `test_before_the_apply_under_the_fixture_scope`
    lists all three (A); `test_after_the_apply` lists all six, exit 0 (B).
    `TestAMigrationThatWritesTheColumn` gains
    `test_the_approved_row_removed_after_the_apply`, exit 3.
  - Not in the plan's list: `test_phase395_through_fleet.py::test_a_live_that_moved_since_the_dry_run_is_refused_by_apply_live`
    went red on the new rule: it wrote to `api_keys`, which its scope does
    not touch, so the change is listed and applied (A). Its write now goes
    to `schema_version`, which its scope names; its assertions are
    unchanged and it refuses again. A deviation, in v1.1.
  - Unchanged: `test_phase348_server_writes.py`, `test_phase357_deploy_exact.py`,
    `test_phase406_through_fleet_split.py` (K95's condition: the dry run's
    list before the question), `test_phase395_q1.py`, and 379's check 8
    tests.
- **Each class docstring** says which shape it holds.
- **Old code:** the new file run against `8ba8c66`'s `deploy.py` (a
  worktree under `/fleet/run`): 23 failed, 17 passed (the 17 are the
  controls: the refusals, the failing cases, the other gates and check 8).
- **Mutations:** `405_mutate.py`, `405_mutate.out`: 14/14 red, and the
  control (378's clock test under the union walk, G2's note) green.
- **`COLLECTED_TEST_FLOOR`:** 12960 to 13015, by a diff of collected ids
  against `8ba8c66`: +59 -4 (the four are 383's after-the-apply cases,
  moved into the listed classes).
- **`git grep -n -F 'equals the backup' -- .claude/skills/deploy`,** after
  the work: no line (two before, at Step 0).
- **The deploy skill:** `SKILL.md` step 4's bullet, step 4's closing
  paragraph, step 5, "From the Mac"'s line on the payments feed, the exit
  codes and "What it holds, and what it cannot"; `CHANGELOG.md`'s entry.

## 2026-11-20 — the first regression run, and bug fix #1

`wholetree.sh --full` at `e46955b`: 5341 passed, 36 skipped (1042.6 s
wall), record written. `regression.sh` at `e46955b`: "Regression run
FAILED (not of record): 12909 passed, 1 failed, 105 skipped, 0 errors at
`e46955b` (36 min 11 s wall, ...)". The one failure is below; no
`deploy.py` test failed.

### Bug fix #1 — 2026-11-20 — 406's stand-in test asked dash for several names in one `command -v`

- **Issue:** `tests/test_phase406_install.py::test_the_stand_ins_are_the_ones_the_scripts_shell_finds`
  failed in the regression inside the fence: `sh -c "command -v id install
  visudo sha256sum sudo systemctl"` printed one path, where the test
  expects six. It fails alone, on master's code as on this branch's.
- **Root cause:** the fence's `/bin/sh` is dash. POSIX defines `command -v`
  for one name, and dash prints only the first of several; the Mac's sh,
  where 406 was built and its regression ran, prints all. 334's regression
  inside the fence (12745 tests) predates 406's tests reaching its branch,
  so this run is the first inside the fence to include them. The desktop's
  scripts use `command -v` with one name only (`ops/desktop/*.sh`), so only
  the test was wrong.
- **Fix:** one `command -v` per name, joined with `;`. What the test holds
  is unchanged: the six stand-ins are found first on the PATH.
- **Files:** `tests/test_phase406_install.py`.
- **Verified:** the file, 11 passed; the same loop with the system
  directories ahead of the stand-ins on the PATH prints `/usr/bin/id` and
  the other system paths, which the assertion refuses.
- **Commit:** `ad60d5e`.
