# Phase 405 — phase log

**Status:** Complete

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

## 2026-11-20 — the first regression run, and its one failure

`wholetree.sh --full` at `e46955b`: 5341 passed, 36 skipped (1042.6 s
wall), record written. `regression.sh` at `e46955b`: "Regression run
FAILED (not of record): 12909 passed, 1 failed, 105 skipped, 0 errors at
`e46955b` (36 min 11 s wall, ...)". The one failure is below; no
`deploy.py` test failed.

### Bug fix #1 — 2026-11-20 — 406's stand-in test asked dash for several names in one `command -v`

**Issue.** `tests/test_phase406_install.py::test_the_stand_ins_are_the_ones_the_scripts_shell_finds`
failed in the regression inside the fence: `sh -c "command -v id install
visudo sha256sum sudo systemctl"` printed one path, where the test expects
six. It fails when run alone too, and nothing this phase changed is in its
path (it reads the desktop's install scripts and a stand-in PATH).

**Root cause.** The fence's `/bin/sh` is dash. POSIX defines `command -v`
for one name, and dash prints only the first of several; the Mac's sh,
where 406 was built and its regression ran, prints all. 334's regression
inside the fence (12745 tests) predates 406's tests reaching its branch, so
this run is the first inside the fence to include them. The desktop's
scripts use `command -v` with one name only (`ops/desktop/*.sh`), so only
the test was wrong.

**Fix.** One `command -v` per name, joined with `;`. What the test holds is
unchanged: the six stand-ins are found first on the PATH.

**Files.** `tests/test_phase406_install.py`.

**Verified.** The file, 11 passed; the same loop with the system
directories ahead of the stand-ins on the PATH prints `/usr/bin/id` and the
other system paths, which the assertion refuses; the regression of record
below.

**Commit.** `ad60d5e`.

## 2026-11-20 — the regression of record

After `wholetree.sh --full` at `c8f400b` (5341 passed, 36 skipped, 1037.5 s wall, record written), `regression.sh` printed:

Regression of record: 12910 passed, 0 failed, 105 skipped, 0 errors at `c8f400b` (36 min 13 s wall, `python -m pytest -n auto --dist load --cov=motodiag`, exit 0) (run inside the fleet's fence)
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:292: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:306: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:321: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:333: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:340: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:438: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:445: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:464: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase191b_ffmpeg.py:249: real ffmpeg binary or fixture mp4 not available
Skipped in the regression of record: [1] tests/test_phase191b_ffmpeg.py:264: real ffmpeg binary or fixture mp4 not available
Skipped in the regression of record: [1] tests/test_phase191b_ffmpeg.py:269: real ffmpeg binary or fixture mp4 not available
Skipped in the regression of record: [1] tests/test_phase191b_ffmpeg.py:277: real ffmpeg binary or fixture mp4 not available
Skipped in the regression of record: [1] tests/test_phase191b_ffmpeg.py:283: real ffmpeg binary or fixture mp4 not available
Skipped in the regression of record: [1] tests/test_phase204_gate10.py:47: inside the fleet's fence: no ffmpeg on the home desktop
Skipped in the regression of record: [1] tests/test_phase257_manual_route_excerpts.py:147: needs the on-disk library
Skipped in the regression of record: [1] tests/test_phase257_manual_route_excerpts.py:352: needs the on-disk library
Skipped in the regression of record: [1] tests/test_phase257_manual_route_excerpts.py:358: needs the on-disk library
Skipped in the regression of record: [1] tests/test_phase257_manual_route_excerpts.py:364: needs the on-disk library
Skipped in the regression of record: [1] tests/test_phase257_manual_route_excerpts.py:367: needs the on-disk library
Skipped in the regression of record: [1] tests/test_phase257_orchestrator_guards.py:85: inside the fleet's fence: no Subconscious login there (K42)
Skipped in the regression of record: [2] tests/test_phase257_orchestrator_guards.py:149: inside the fleet's fence: osacompile is macOS-only
Skipped in the regression of record: [4] tests/test_phase257_sandbox_boundary.py:72: sandbox-exec is macOS-only; the orchestrator runs only there
Skipped in the regression of record: [1] tests/test_phase257_sandbox_boundary.py:80: sandbox-exec is macOS-only; the orchestrator runs only there
Skipped in the regression of record: [1] tests/test_phase257_sandbox_boundary.py:87: sandbox-exec is macOS-only; the orchestrator runs only there
Skipped in the regression of record: [1] tests/test_phase257_sandbox_boundary.py:93: sandbox-exec is macOS-only; the orchestrator runs only there
Skipped in the regression of record: [1] tests/test_phase257_sandbox_boundary.py:106: sandbox-exec is macOS-only; the orchestrator runs only there
Skipped in the regression of record: [1] tests/test_phase257_sandbox_boundary.py:112: sandbox-exec is macOS-only; the orchestrator runs only there
Skipped in the regression of record: [1] tests/test_phase257_sandbox_boundary.py:119: sandbox-exec is macOS-only; the orchestrator runs only there
Skipped in the regression of record: [1] tests/test_phase257_sandbox_boundary.py:125: sandbox-exec is macOS-only; the orchestrator runs only there
Skipped in the regression of record: [1] tests/test_phase257_sandbox_boundary.py:131: sandbox-exec is macOS-only; the orchestrator runs only there
Skipped in the regression of record: [7] tests/test_phase257_source_checks.py:211: needs the on-disk library
Skipped in the regression of record: [1] tests/test_phase257_source_checks.py:476: acquired/Yamaha/library_om_contents_pdf_10_5YR-F8199-15_02.pdf is not in this machine's library
Skipped in the regression of record: [1] tests/test_phase257_source_checks.py:476: acquired/KTM/24_3214961_en_OM.pdf is not in this machine's library
Skipped in the regression of record: [1] tests/test_phase257_source_checks.py:527: the KTM manual is not in this machine's library
Skipped in the regression of record: [1] tests/test_phase244H_test_db_isolation.py:79: no production database on this machine
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:104: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:121: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:137: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:145: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:153: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:162: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:175: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:185: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:218: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:223: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:248: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:259: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:272: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:61: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [4] tests/test_phase388_fence_boundary.py:96: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [3] tests/test_phase388_fence_boundary.py:105: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:113: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:120: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:125: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:131: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:139: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:148: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:159: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:164: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:170: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:177: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:186: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:198: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [2] tests/test_phase388_fence_boundary.py:210: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:216: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [7] tests/test_phase388_fence_boundary.py:221: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:235: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:244: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [2] tests/test_phase388_fence_boundary.py:280: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:287: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:291: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:295: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:303: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [2] tests/test_phase388_fence_boundary.py:316: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:325: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:330: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:338: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:344: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:350: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:354: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:360: inside the fleet's fence: its boundary is proven from the host, not from inside
Line coverage of record: 88.35% at `c8f400b` (the pin is 87.50%): 0.85 points above it; raise COVERAGE_PERCENT to lock it in

## 2026-11-20 — the close-out

v1.1 of `405_implementation.md` (Deviations, Results, the history row);
F259 and F210 closed in `docs/FOLLOWUPS.md` "once merged and live"; the
phase's files moved to `docs/phases/completed/`; the ROADMAP row ✅; the
root `phase_log.md`'s pointer; the handoff,
`docs/handoffs/2026-11-20_405_closed.md`, with the live step as two paste
blocks for the Mac. No finding was filed: the build found no case the rule
does not cover.

## Refuter pass

| claim | verdict | quote | source | round · kind · outcome |
|---|---|---|---|---|
| The new test file has 40 collected ids | kept | "`tests/test_phase405_what_the_change_did.py` (40)" | tests/test_phase255B_collected_test_floor.py p. 588 | 1 · none · kept |
| COLLECTED_TEST_FLOOR goes from 12960 to 13015, +59 −4 | kept | "+59 -4. Added: test_phase405_what_the_change_did.py (40); the controls" | tests/test_phase255B_collected_test_floor.py p. 588 | 1 · none · kept |
| The floor equals the regression's passed plus skipped (12910 + 105) | kept | "COLLECTED_TEST_FLOOR = 13015" | tests/test_phase255B_collected_test_floor.py p. 594 | 1 · none · kept |
| The regression of record is 12910 passed, 0 failed, 105 skipped at c8f400b | kept | "Regression of record: 12910 passed, 0 failed, 105 skipped, 0 errors at `c8f400b` (36 min 13 s wall" | docs/phases/completed/405_phase_log.md p. 174 | 1 · none · kept |
| Line coverage is 88.35% against a pin of 87.50% | kept | "Line coverage of record: 88.35% at `c8f400b` (the pin is 87.50%)" | docs/phases/completed/405_phase_log.md p. 256 | 1 · none · kept |
| Mutations: 14/14 red, the one control green | kept | "14/14 red; 1/1 controls green" | docs/phases/completed/405_mutate.out p. 16 | 1 · none · kept |
| Deviation 6: the mutations are T1–T4, G1–G3, E1–E3, H1, plus T2b, G3b, E2b and the control C1 | kept | "C1 the union walk: 378's clock test stays green: green, as expected" | docs/phases/completed/405_mutate.out p. 15 | 1 · none · kept |
| Deviation 8: stage_deployed is at dispatcher.py line 2087 | kept | "    def stage_deployed(self, issue: int, phase: str, body: str, branch: str, held: pathlib.Path," | .claude/skills/fleet/dispatcher.py p. 2087 | 1 · none · kept |
| The Quartermaster reads the two header lines | kept | "    if live and (\"**Scope problems:** `none`\" not in live" | .claude/skills/fleet/quartermaster.py p. 167 | 1 · none · kept |
| remote.py sends the Mac's pushed HEAD for live-check | kept | "        words = argv + [pushed_head(repo)] if argv[0] in AT_COMMIT else argv" | .claude/skills/deploy/remote.py p. 189 | 1 · none · kept |
| The desktop prints "no dry-run diff: no deploy to verify" at line 260 | kept | "            say(f\"  {phase} has no dry-run diff: no deploy to verify\")" | ops/desktop/motodiag_remote.py p. 260 | 1 · none · kept |
| The drift split runs after the fresh dry run's two gates | kept | "    drift_gate(bk, db, approved, touched(scope, approved, names))" | .claude/skills/deploy/deploy.py p. 681 | 1 · none · kept |
| names is read from the backup, then the migrated copy, before _drop | kept | "        names = {**tbl_names(bk), **tbl_names(fresh)}" | .claude/skills/deploy/deploy.py p. 672 | 1 · none · kept |
| The refusal still contains "changed since the dry run" and ends "Stop and ask." | kept | "        raise Refused(f\"live changed since the dry run in a table this change touches: \"" | .claude/skills/deploy/deploy.py p. 705 | 1 · none · kept |
| shape_gaps walks the approved leaves only | kept | "    for p in sorted(a):" | .claude/skills/deploy/deploy.py p. 841 | 1 · none · kept |
| approved_holds skips a side with no entries | kept | "    gaps = shape_gaps(ea, eb) if ea else []" | .claude/skills/deploy/deploy.py p. 888 | 1 · none · kept |
| The live diff gains the line `Other differences, listed` | kept | "        f\"- **Other differences, listed:** `{len(listed)}` \"" | .claude/skills/deploy/deploy.py p. 735 | 1 · none · kept |
| A view is left out of tbl_names | kept | "        \"and type != 'view'\")}" | .claude/skills/deploy/deploy.py p. 273 | 1 · none · kept |
| The SERVER_WRITES block's two "so either one is drift" sentences say what holds after 405 | kept | "not listed (F210), so either one is drift. After Phase 405 (K91): before" | .claude/skills/deploy/deploy.py p. 191 | 1 · none · kept |
| SKILL.md says a database step no longer needs the feed stopped, "the feed's writes are in tables the change does not touch" | killed | "  feed stopped: the feed's writes are in tables the change does not touch," | .claude/skills/deploy/SKILL.md p. 244 | 1 · wording · open F286 |
| Deviation 1: 395's test now writes to schema_version, which its scope names | kept | "SCOPE = {\"tables\": {\"schema_version\": {\"added\": 1}}," | tests/test_phase395_through_fleet.py p. 32 | 1 · none · kept |
| Deviation 2 / bug fix #1: 406's test asks one name per command -v | kept | "    r = subprocess.run([\"sh\", \"-c\", \"; \".join(f\"command -v {n}\" for n in STAND_INS)]," | tests/test_phase406_install.py p. 139 | 1 · none · kept |
| Deviation 3: SERVER_WRITES is shown deciding under a scope naming api_keys with nothing expected | kept | "        _ready(env, scope={\"tables\": {**SCOPE[\"tables\"], \"api_keys\": {}}})" | tests/test_phase405_what_the_change_did.py p. 153 | 1 · none · kept |
| Deviation 7: the check 8 case reuses 379's harness and reads only the exit | kept | "        assert _check_8(tmp_path / \"gap\", 3)[0] == 1" | tests/test_phase405_what_the_change_did.py p. 405 | 1 · none · kept |
| 358's old control is now listed, and a new sibling keeps the refusal | kept | "    def test_when_a_touched_table_changed_since_the_backup(self, env, capsys):" | tests/test_phase358_deploy_contract.py p. 210 | 1 · none · kept |
| F259 is closed "once merged and live" by Phase 405 | kept | "Closed 2026-11-20 by Phase 405, once merged and live (K91, neither option" | docs/FOLLOWUPS.md p. 5517 | 1 · none · kept |
| F210 is closed "once merged and live" by Phase 405 | kept | "Closed 2026-11-20 by Phase 405, once merged and live (K91, 383's option" | docs/FOLLOWUPS.md p. 3664 | 1 · none · kept |
| The grep for "equals the backup" under the deploy folder finds no line after the work | kept | "  the work: no line (two before, at Step 0)." | docs/phases/completed/405_phase_log.md p. 129 | 1 · none · kept |
| The ROADMAP row is ✅ with its CLOSED date and regression line | kept | "**CLOSED 2026-11-20.** Built by the fleet (K91)." | docs/ROADMAP.md p. 687 | 1 · none · kept |
| The handoff's gh calls name the repository (R8) | kept | "MERGE=$(gh pr list -R \"$R\" --state merged --head \"$BRANCH\"" | docs/handoffs/2026-11-20_405_closed.md p. 158 | 1 · none · kept |
| The handoff's Mac block stops unless HEAD is the merge | kept | "[ \"$HEAD_NOW\" = \"$MERGE\" ] || bad" | docs/handoffs/2026-11-20_405_closed.md p. 165 | 1 · none · kept |
| The CHANGELOG entry is dated, cites K91, F210 and F259, and gives the mutation count | kept | "## 2026-11-20 — the check asks what the change did (Phase 405, K91, F210, F259)" | .claude/skills/deploy/CHANGELOG.md p. 3 | 1 · none · kept |
