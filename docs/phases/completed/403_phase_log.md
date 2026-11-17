# Phase 403 — phase log: the fleet's stops (F231, F266, F275, F261, F264, F276, F277)

**Status:** Complete

**Started 2026-11-16** on the home desktop (WSL2), the only writer on this
checkout, on `phase-403-the-fleets-stops` from master `8e22b1f`. The prompt
is `docs/prompts/403_the_fleets_stops.txt`; the operator's words are K84
and K88. The fleet is idle while it waits for this phase; its service and
folders are left alone, except that four of 372's run folders were to be
copied for fixtures.

## 2026-11-16 17:02 EST — start

- Master fetched (`8e22b1f`). `~/Projects/moto-diag` was on a detached
  `f15ed2f`, clean; the branch was made from `origin/master`.
- Read before planning: `CLAUDE.md` and the working rules,
  `docs/decisions.md` (K84, K88), F231, F261, F264, F266, F275, F276, F277,
  `docs/ROADMAP.md` row 403, the plan of record, and the code each finding
  names.
- The fixtures first: two of the four run folders the prompt names
  (`20261112_152526_engineer_372`, `20261112_225609_engineer_372`) were
  already pruned when this phase began; the other two were copied to
  `~/403-fixture-staging/`. The pruned two are rebuilt from git and issue
  #59 (`403_step0.md`, S0-0).
- Row 403 🚧 on the branch before Step 0.

## 2026-11-16 — Step 0

`403_step0.md`. Every line number of the prompt holds at `8e22b1f`. The
generator reproduces `993fadc`, `d292eef` and `13b6e68` byte for byte.
(e) measured at about 90 lines of code over five files: a small addition,
built (K88); said to the operator in the thread before any code.

## 2026-11-16 — v1.0 committed (`7cb4914`), then the build

- v1.0 committed before any code. The push of it waits for the operator's
  typed approval in the thread (this builder may not push on its own); the
  code was written after the commit, against the plan as committed.
- No push guard ran on any commit: this builder session was started
  outside the repository root (F268), so the repository's hooks are not
  loaded. `wholetree.sh` was run by hand, on its own, before each commit.
- (d) the briefs; (a), (b), (c) and (e) in `dispatcher.py`, `engineer.py`,
  `fleet_git.py`, `red_team.py`, `plan_order.py`, the new `app_copy.py`,
  `refute_check.py` and `closeout_check.py`, as v1.0's Logic sets out.
- The fixtures, in `tests/fixtures/phase403/`: `stops_372.json` (the three
  stops: kind, the stop note's words, GitHub's branch then, the commits
  only the clone had, from git), `issue59_stops_and_answers.json` (the
  three stop notes and the operator's three answers, verbatim from GitHub),
  `red_team_372_round4.json` (run `20261115_125327_red_team_372`'s call 0,
  whole), `371_phase_log_before_260cf7f.md` (`git show f0b3512:…`).
- 61 new tests in five files, all green. Against master's code (a worktree
  of `8e22b1f` with only the new tests and fixtures copied in): 42 failed,
  the app-copy file failed to collect (no `app_copy` module: its 16 red),
  and 3 passed, the three controls that read only what this phase leaves
  alone: the edit guard's refusals, the refute checker's C5 on a `code`
  kind, and that the stop note of 2026-11-13 04:56 UTC is the guard's
  words.
- Measured on the way: 372's round-4 table has 16 lines marked round 4 and
  the checker reads 15. The 16th quotes a table line holding `\|`, which
  splits its cells, so no check sees it and its open wording defect was
  never filed. Filed as F279 and left (the prompt: file what you find).
  F277's "16 rows … all fail C5" counted lines, not rows.
- `COLLECTED_TEST_FLOOR` 12623 → 12685: master `8e22b1f` collects 12624,
  this tree 12685, +61 -0, all in the five new files.
- The wider fleet and close-out suites (`tests/test_phase35*`, `36*`,
  `38*`, `39*`, `255*`, `403_*`, `test_roadmap_continuity.py`): 2365
  passed.

## 2026-11-16 — the mutations

`403_mutate.py`, 31 mutations over (a) to (e), under a throwaway HOME. The
first run: 30/31 red. M14 (Gate 11 not run again against the refreshed
copy) survived: no test refreshed a copy that left Gate 11 red. Added
`test_gate11_still_red_against_the_new_copy_stops` (`COLLECTED_TEST_FLOOR`
12685 → 12686, +1 in `test_phase403_app_copy.py`); M14 then red. The run of
record: 31/31 red (`403_mutate.out`).

## 2026-11-16 17:59–18:22 EST — the regression of record

`403_regression.py` (399's driver, renamed) on `e5040ba`: this branch's
`Fleet.check_run` in a fresh clone in the fence, no model, no token, the
fleet's virtualenv, a state folder of its own (`/tmp/403-regstate`), and a
clean clone of moto-diag-mobile's `main` (`9045c32`, which holds
`13b6e68`) as `../moto-diag-mobile`. `pgrep -x bwrap` was empty at the
start; the fleet was idle. First `wholetree.sh --full` in the same run:
150 test files, 5165 passed, 36 skipped. The real cost ledger before and
after: 5,796,986 bytes, 5,780 rows, sha256 8a55eb86… both times, 0 rows
appended. The record, as `regression.sh` printed it:

Regression of record: 12581 passed, 0 failed, 105 skipped, 0 errors at `e5040ba` (13 min 47 s wall, `python -m pytest -n auto --dist load --cov=motodiag`, exit 0) (run inside the fleet's fence)
Skipped in the regression of record: [1] tests/test_phase191b_ffmpeg.py:249: real ffmpeg binary or fixture mp4 not available
Skipped in the regression of record: [1] tests/test_phase191b_ffmpeg.py:264: real ffmpeg binary or fixture mp4 not available
Skipped in the regression of record: [1] tests/test_phase191b_ffmpeg.py:269: real ffmpeg binary or fixture mp4 not available
Skipped in the regression of record: [1] tests/test_phase191b_ffmpeg.py:277: real ffmpeg binary or fixture mp4 not available
Skipped in the regression of record: [1] tests/test_phase191b_ffmpeg.py:283: real ffmpeg binary or fixture mp4 not available
Skipped in the regression of record: [1] tests/test_phase204_gate10.py:47: inside the fleet's fence: no ffmpeg on the home desktop
Skipped in the regression of record: [7] tests/test_phase257_source_checks.py:211: needs the on-disk library
Skipped in the regression of record: [1] tests/test_phase257_source_checks.py:476: acquired/Yamaha/library_om_contents_pdf_10_5YR-F8199-15_02.pdf is not in this machine's library
Skipped in the regression of record: [1] tests/test_phase257_source_checks.py:476: acquired/KTM/24_3214961_en_OM.pdf is not in this machine's library
Skipped in the regression of record: [1] tests/test_phase257_source_checks.py:527: the KTM manual is not in this machine's library
Skipped in the regression of record: [1] tests/test_phase257_manual_route_excerpts.py:147: needs the on-disk library
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
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:292: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:306: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:321: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:333: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:340: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:438: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:445: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:464: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase257_manual_route_excerpts.py:352: needs the on-disk library
Skipped in the regression of record: [1] tests/test_phase257_manual_route_excerpts.py:358: needs the on-disk library
Skipped in the regression of record: [1] tests/test_phase257_manual_route_excerpts.py:364: needs the on-disk library
Skipped in the regression of record: [1] tests/test_phase257_manual_route_excerpts.py:367: needs the on-disk library
Skipped in the regression of record: [1] tests/test_phase244H_test_db_isolation.py:79: no production database on this machine
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
Line coverage of record: 88.17% at `e5040ba` (the pin is 87.50%): 0.67 points above it; raise COVERAGE_PERCENT to lock it in
Coverage data: /fleet/run/home/.cache/motodiag/regressions/e5040ba_parallel_20261116_180821.coverage.json

## 2026-11-16 — close-out

- v1.1 (Deviations and Results), this log, row 403 ✅ (110 words), the
  root `implementation.md` (0.13.135) and `phase_log.md`, the handoff
  `docs/handoffs/2026-11-16_403_closed.md` with the operator's three steps
  after the merge and the trial's block.
- No refute pass ran: this phase was built by a builder session, not by the
  fleet, so no Red Team round reviewed it; it is held by its tests and
  mutations, and by the coordinator's review of its pull request.
- The phase log's status line was set with `sed -i`, a slip: the edit
  guard is not loaded in this session (F268), and rule 3 of the
  Engineer's brief, rewritten in this phase, says such an edit is refused.
  The line changed is the one intended; nothing else did.
