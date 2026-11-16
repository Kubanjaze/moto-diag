# Phase 403 — phase log: the fleet's stops (F231, F266, F275, F261, F264, F276, F277)

**Status:** In progress

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
