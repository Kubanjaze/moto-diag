# Phase 394 — phase log: the fleet passes a rank's brief on standard input

**Status:** Complete

**Started 2026-10-28** on the home desktop (WSL2), the only writer, on
`phase-394-brief-on-stdin` from `master` at `c608169`. The prompt is
`docs/prompts/394_the_brief_on_stdin.txt` (the operator's words, verbatim).

## 2026-10-28 — start

- **The row first.** Row 394 (🚧), K55 (recorded with `yeoman.py decide`),
  394 as row 3 of "Next, in order" right after 303 with its dated entry,
  and `tests/test_phase392_plan_order.py` moved to the new order, in one
  commit: `467a092`. `wholetree.sh` before it: exit 0, 2343 passed.
- **A guard block.** Moving the test with a Python script was refused by
  the edit guard ("a Python script body writes
  tests/test_phase392_plan_order.py"). The three edits were made with the
  Edit tool instead. The guard is unchanged.
- **`pgrep -x bwrap`** before the whole-tree command: exit 1, no fenced
  run. #31 carries `needs-admiral`, so the cycle runs no stage on it.
- **#31 and PR #34** are only read (the comment count in Step 0), never
  written.

## 2026-10-28 — Step 0

`394_step0.md`. The defect measured (69 launch failures, 69 "started"
comments); `claude -p` on this install (2.1.312) reads a 291094-byte brief
from stdin and follows it; five argv launches, two in scope. Decisions in
S0-5; none is a rule-1 stop.

## 2026-10-28 — v1.0, and a second guard block

- **v1.0** committed at `544012b` and pushed. `plan_check 394`: PASS (a first
  run failed P3, a limit stated without its query, and P6, an ellipsis in
  Logic; both fixed before the commit).
- **The push guard refused** `git commit … && git push` in one command
  ("it would push a commit it never saw"). Committed, then pushed, as two
  commands. The guard is unchanged.
- **A third block:** `sed -i` on `dispatcher.py`'s import line was refused
  by the edit guard; the import was changed with the Edit tool.

## 2026-10-28 — the build (Logic 1–6)

- **`rank_call.py`:** `command(model, schema, tools)` has no brief; `call`
  passes `input=prompt`; `LaunchFailed(Stop)` for an `OSError` from `run`.
- **`dispatcher.py`:** `FencedRunner.fenced(…, input=)` replaces
  `token_pipe`'s `stdin=DEVNULL` with the brief; `__call__` hands it on.
  `session(cmd, brief, …)` writes `<run>/session.brief` and opens it as
  stdin; resumed, the brief is `engineer.CONTINUE`; a `Popen` `OSError` is
  `LaunchFailed`. `started()` asks `failed_start()` first.
- **`engineer.py`:** `session_argv(model)` and `session_brief(…)`.
- **`journal.py`:** `call_key` drops `-p` alone when a flag follows it.
- **Existing tests moved to stdin** (the brief was read at `cmd[2]` or
  after `-p`): 20 failed on the first run, all of that kind; the stubs in
  `test_phase389_captain.py`, `_scout.py`, `_red_team.py`, `_engineer.py`,
  `test_phase392_ranks_cite.py`, `_answers.py`, `test_phase390_resume.py`,
  `test_phase391_dispatcher.py` and 388's `Host` (`model_briefs()`) now
  read stdin. Then 729 passed.
- **`tests/test_phase394_brief_on_stdin.py` (18).** A stand-in `claude` on
  PATH, a real process, records its argv and its stdin; a stand-in fence
  execs what follows `--`. The control: the old shape with the 300 KiB
  brief raises errno 7 on this kernel. Each rank (Red Team, Quartermaster,
  the Captain's recommendation and plan, the Science Officer's two calls,
  the XO, the Yeoman) and, through the fence, a rank call fresh and resumed
  and the Chief Engineer's session: the whole brief on stdin, no argument
  at or over 131072 bytes. A launch `OSError` on the 389 walk-through's
  stand-in issue 31 (not the real #31, which nothing here touches): one
  `started`, one stop naming errno 7, label `review:open` unchanged, three
  more cycles with no model call and no comment, no "cycle failed". The
  Engineer's launch the same. `started` once over a failed run and two
  retries (the log says twice that the comment stands), then the stage
  runs to `review:clear` with still one; again after a stop and the label
  re-applied, two. `failed_start` only for a failed run, only for its rank.
- **Mutations:** `394_mutate.py`, 15/15 red (`394_mutate.out`). While
  writing them, S2 (any run's `started` stands) was judged, not run, to
  survive the first draft of the tests: in every walk-through the last rank
  comment after a stop is the stop. So
  `test_only_a_failed_runs_started_stands_for_a_retry` was written first,
  and the mutation run came after it.
- **The floor:** a diff of collected ids against a master worktree at
  `c608169`: 11738 → 11756, +19 −1 (18 new; 392's order test renamed).
- **The skill and its CHANGELOG** say it.

## 2026-10-28 — the build commit; gate 11 and the run of record

- **The build** committed at `ff3ce4a` after `wholetree.sh` (exit 0, 2361
  passed). `pgrep -x bwrap` before each whole-tree run: exit 1.
- **`wholetree.sh --full` on `ff3ce4a`, in this checkout:** exit 1, 4 failed,
  4823 passed, 15 skipped (437 s). All four are gate 11
  (`tests/test_phase205_gate11.py`) run by gates 12, 13 and 14: the mobile
  snapshot "describes schemas the API no longer returns: ['LoginRequest',
  'PasswordChangeRequest', 'PasswordResetRequest']" and promises `/v1/auth/*`
  routes.
- **The cause is not this phase.** Gate 11 reads
  `../moto-diag-mobile/api-schema/openapi.json`. On this machine that
  repository's `main` is one commit ahead of `origin/main`: `7489fd5`
  (2026-10-28 14:26, "API schema: refresh for backend Phase 303 (staff
  logins); regenerate types and push after 303 merges"), unpushed by
  design. Control: `git switch master`, then
  `pytest tests/test_phase205_gate11.py`: 2 failed, 19 passed, the same two
  tests. (A first control from a worktree in the scratchpad was void: it
  has no `moto-diag-mobile` beside it, and failed 6 for that reason.)
- **Decision (not a rule-1 stop: the test is green against the published
  mobile repository, and nothing is loosened):** the regression of record
  runs as the fleet's model-free run does, a fresh clone of `ff3ce4a` in the
  fence with the fleet's virtualenv (`394_regression.py`), with `--mobile`
  a clean clone of the mobile repository at its published `origin/main`
  (`0074eb9`). The mobile commit `7489fd5` is not touched.
- **Open, for the handoff:** until 303 merges and `7489fd5` is pushed,
  gate 11 fails every backend without 303 on this machine, in this
  checkout and in the fleet's own model-free runs, which mount
  `~/Projects/moto-diag-mobile` (`fleet_git.MOBILE`). 303's own branch
  carries the routes, so its checks are not affected.

## 2026-10-28 — the regression of record

`394_regression.py ~/motodiag/p394/state ff3ce4a <scratch>/mobile394`: this
branch's `Fleet.check_run`, a fresh clone of `ff3ce4a` in the fence, no
model, no token (`~/motodiag/p394/state/runs/20261028_231357_check`), with
the mobile repository at its published `origin/main` (`0074eb9`).
`pgrep -x bwrap` before it: exit 1; `dispatcher.log`'s last line was the
22:39 reclaim, no stage running (F220).

    wholetree full: PASSED — 4806 passed, 36 skipped, 32 warnings in 1003.75s (0:16:43) (1006.6 s wall)

Regression of record: 11651 passed, 0 failed, 105 skipped, 0 errors at `ff3ce4a` (34 min 35 s wall, `python -m pytest -n auto --dist load`, exit 0) (run inside the fleet's fence)
Skipped in the regression of record: [1] tests/test_phase191b_ffmpeg.py:249: real ffmpeg binary or fixture mp4 not available
Skipped in the regression of record: [1] tests/test_phase191b_ffmpeg.py:264: real ffmpeg binary or fixture mp4 not available
Skipped in the regression of record: [1] tests/test_phase191b_ffmpeg.py:269: real ffmpeg binary or fixture mp4 not available
Skipped in the regression of record: [1] tests/test_phase191b_ffmpeg.py:277: real ffmpeg binary or fixture mp4 not available
Skipped in the regression of record: [1] tests/test_phase191b_ffmpeg.py:283: real ffmpeg binary or fixture mp4 not available
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
Skipped in the regression of record: [1] tests/test_phase204_gate10.py:47: inside the fleet's fence: no ffmpeg on the home desktop
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
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:292: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:306: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:321: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:333: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:340: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:438: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:445: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:464: inside the fleet's fence: no network to build a wheel
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

## 2026-10-29 — close-out

- **A fourth guard block:** writing v1.1 with a Python script was refused
  by the edit guard ("the body names src/ or tests/"); v1.1, the history
  row and the header were written with the Edit tool.
- **The reclaim** (`dispatcher.py reclaim`): C: 282.7 -> 282.7 GB free
  (nothing came back to Windows: the disk image is not sparse, so the trim
  freed space inside Ubuntu only); Ubuntu 1008.8 -> 1008.8 GB free; fstrim:
  /: 38.4 GiB (41271394304 bytes) trimmed.
- **No bug fixes,** and no live change.

No refute pass ran.
- v1.1, the ROADMAP row (✅, 79 words by `roadmap_words.py`), the history
  row in `implementation.md`, the files moved to `completed/`, the handoff
  `docs/handoffs/2026-10-29_394_closed.md`. The merge is the operator's.
