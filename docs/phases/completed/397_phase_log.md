# Phase 397 — phase log: the one-second window in a fleet test (F241)

**Status:** Complete

**Started 2026-10-31** on the home desktop (WSL2), the only writer, on
`phase-397-the-one-second-window`. The prompt is
`docs/prompts/397_the_one_second_window.txt` (the operator's words,
verbatim); the operator's word is K63.

## 2026-10-31 — start

- Master fetched at 22:33 at `48cf7ca`. Across every local and remote
  branch, 397, K63 and F242 were free (K67 appears only as a BMW chassis
  code).
- `3d0fa45`: the prompt, row 397 🔲, row 10 of "Next, in order" (343 to
  210 renumbered 11 to 17) with the dated entry, K63 (by `yeoman.py
  decide`) and `tests/test_phase392_plan_order.py` (one test added).
  wholetree fast passed first (2548 passed, 10 skipped; exit 0, the fleet
  idle). Merged to master as `2405758` and pushed; the push printed
  GitHub's "Cannot update this protected ref" notice and went through
  (`48cf7ca..2405758`).
- **Guard block** (recorded, guard unchanged): the edit guard refused a
  Python script body that edited the plan of record, because its text
  named `tests/`; the Edit tool made the same edits.
- Issue #45 and the phase-345 branch untouched.
- Row 397 🚧 on the branch before Step 0.

## 2026-10-31 — Step 0

`397_step0.md`. (a) The planted command needs about 6 ms of its 1 s
window here (86 ms at most beside 128 busy processes); with `sleep 2`
planted the test as it stands is red 10 of 10, `assert 'started' in ''`,
the Mac's failure; `run_group` keeps all that was printed. (b) An escaped,
live child reads alive through `/proc` and ended with `/proc` absent. The
census: 19 lines in 9 files; two tests in the file are fixed here, three
elsewhere share the weakness and are filed as F242.

**The machine:** the Quartermaster's stage on 345 ran from 22:40:37; the
load measurement and the known-bad runs (22:42–22:43) shared the machine
with it. No whole-tree run did.

## 2026-10-31 — the build

- **Order slip, recorded.** While the Quartermaster's stage held the
  machine, the test change was written before v1.0 was committed. Nothing
  was committed out of order: Step 0 and v1.0 are committed and pushed
  first, on their own, and the code after them.
- `tests/test_phase392_check_limit.py`: the windows (1, 2, 4, 8, 16, 32 s),
  each with its own folder and bound (`window + 29` s), stopping at the
  first in which the planted command reached its child; the 120 s window
  for `test_run_group_passes_a_run_that_ends`; `alive()` through
  `ps -o stat= -p`; `test_alive_answers_on_this_system`, its controls.
- The fixed file: 5 passed (2.88 s). With `sleep 2` planted, the fixed
  test is green 5 of 5 (`397_measure.py knownbad 5`, about 7 s each: the
  1 s and 2 s windows fall short, the 4 s window reaches the child).
- `397_mutate.py`, 22:49 to 22:55, beside the Quartermaster's stage on
  345 (two `bwrap` processes): **8/8 mutations red**; K1 green 3 of 3;
  master's old test red on `sleep 2` and, on Linux, red on an escaped
  child. Output kept as `397_mutate.out`. M2 took 301 s, as its
  docstring says.

## 2026-10-31 — waiting for the fleet

At 23:19 the Quartermaster's fenced `regression.sh` on 345 had run 38 min
53 s (started about 22:40). The operator's standing word (F220): no
whole-tree or regression run while a fleet model-free run is in progress.
The commits wait for it, since each needs `wholetree.sh` first.

The regression ended at 23:33:14. My next `wholetree.sh` (fast) began at
23:33:41 and did not stop on a fleet stage that had started again: the
Quartermaster's two short checks (`20261031_233322_check`, the fenced
read of where live is, refused by design; `20261031_233433_check`,
`{"Q10": [], "Q12": []}`) and then its model call ran beside it. It
passed: 2549 passed, 10 skipped, exit 0. Neither fleet check shows a
failure from the load. From here, each run checks `bwrap` and the log
immediately before it starts, and stops if a stage is running.

## 2026-11-01 — the regression of record

- **The clock check.** `clock_check.sh` at 23:39:09 refused, exit 2:
  "faketime is not installed". Installing it here needs `sudo`'s
  password, a credential. Instead the regression began after midnight, so
  it ran on no month's last evening.
- **`wholetree.sh --full`** at `d8f419c` (23:39:25–23:46:40): exit 0,
  5039 passed, 15 skipped; record `b195ed3c…_full.json`. `pgrep -x bwrap`
  empty before it, and no fleet stage during it.
- **`regression.sh` in this checkout** (00:00:33–00:12:27, 32 workers,
  "created: 32/32 workers"): Regression run FAILED (not of record): 12149
  passed, 4 failed, 33 skipped, 0 errors at `d8f419c`. The four are the
  ones 396 recorded for this checkout: `test_phase204_gate10.py`'s
  installed-ffmpeg check and three of
  `test_phase257_orchestrator_guards.py` (`test_the_script_compiles` ×2,
  `test_the_real_subc_profile_points_at_subconscious`). They read this
  machine's own tools and profile, not the code. Not the run of record.
  **What else ran:** a fenced fleet stage from 00:04:37 to 00:05:06
  (two `bwrap` processes; a `python3 -c` inside the fence; `dispatcher.log`
  wrote no line for it).
- **The run of record**, as 393's to 396's were: `Fleet.check_run` on
  `d8f419c` in a fresh clone in the fleet's fence, no model and no token,
  the fleet's venv, the mobile repository a clean clone at its published
  `main` (`0773f91`), by `397_regression.py` (396's driver, renamed).
- **First attempt lost** (00:13:08–00:22): I gave `397_regression.py` a
  state folder under `/tmp`, which here is a 16 GB RAM disk. The fenced
  run's clone and temporary files, with the 12 GB that the unfenced
  `regression.sh` had left in `/tmp/pytest-of-lilcu/pytest-2592` (its 32
  worker folders), filled it; the run's `check.txt` was written empty. No
  fleet stage ran in that window. I deleted only my own leftovers (that
  pytest folder, the run's clone and temporary files, the scratch mobile
  clone): `/tmp` back to 15 GB free. The main disk had 938 GB free
  throughout.
- **Second attempt**: the state folder and the mobile clone (`0773f91`)
  under `~/.cache/motodiag/397_regression/`, on the main disk.
  (00:24:18–01:16:06; `wholetree.sh --full` inside it: 5018 passed, 36
  skipped; `regression.sh` from 00:41:05, **32 test workers**, "created:
  32/32 workers" in its log). **What else ran on the machine:** no fleet
  stage (`dispatcher.log`'s last line stayed 23:40:27's reclaim, and the
  fleet's newest run stayed 23:34:33's check), the always-on
  `motodiag-api.service` and the idle dispatcher. Its lines, as printed:

Regression of record: 12081 passed, 0 failed, 105 skipped, 0 errors at `d8f419c` (34 min 44 s wall, `python -m pytest -n auto --dist load --cov=motodiag`, exit 0) (run inside the fleet's fence)
Skipped in the regression of record: [1] tests/test_phase191b_ffmpeg.py:249: real ffmpeg binary or fixture mp4 not available
Skipped in the regression of record: [1] tests/test_phase191b_ffmpeg.py:264: real ffmpeg binary or fixture mp4 not available
Skipped in the regression of record: [1] tests/test_phase191b_ffmpeg.py:269: real ffmpeg binary or fixture mp4 not available
Skipped in the regression of record: [1] tests/test_phase191b_ffmpeg.py:277: real ffmpeg binary or fixture mp4 not available
Skipped in the regression of record: [1] tests/test_phase191b_ffmpeg.py:283: real ffmpeg binary or fixture mp4 not available
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
Skipped in the regression of record: [1] tests/test_phase204_gate10.py:47: inside the fleet's fence: no ffmpeg on the home desktop
Skipped in the regression of record: [1] tests/test_phase244H_test_db_isolation.py:79: no production database on this machine
Skipped in the regression of record: [7] tests/test_phase257_source_checks.py:211: needs the on-disk library
Skipped in the regression of record: [1] tests/test_phase257_source_checks.py:476: acquired/Yamaha/library_om_contents_pdf_10_5YR-F8199-15_02.pdf is not in this machine's library
Skipped in the regression of record: [1] tests/test_phase257_source_checks.py:476: acquired/KTM/24_3214961_en_OM.pdf is not in this machine's library
Skipped in the regression of record: [1] tests/test_phase257_source_checks.py:527: the KTM manual is not in this machine's library
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
Skipped in the regression of record: [1] tests/test_phase257_manual_route_excerpts.py:147: needs the on-disk library
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
Line coverage of record: 87.71% at `d8f419c` (the pin is 87.50%)

## 2026-11-01 — close-out

- v1.1; this log Complete; the phase's files moved to
  `docs/phases/completed/`; row 397 ✅ with its CLOSED date and the
  regression line; the handoff
  `docs/handoffs/2026-11-01_397_closed.md`.
- No bug fixes: no register. The phase changes one test file and ships
  no content row.

No refute pass ran.

- **Guard blocks** (recorded, guards unchanged): the edit guard refused a
  command holding `sed -i` on this log's status line; the Edit tool made
  the change. The session's permission check refused
  `dispatcher.py reclaim` (it trims the disk), so the reclaim line in the
  handoff is the fleet timer's of 23:40:27.
- Nothing under `.claude/skills/fleet/` changed, so nothing moves on the
  desktop after the merge. F241 stays open until the advisor's full run on
  the Mac passes.

## 2026-11-01 — after the close-out

- PR #49 opened; its `ratchet` check passed (42 s).
  `verify_phase.sh 397 d8f419c f80557c`: 13 of 14 pass; check 1 (the tip
  on master) passes once #49 is merged.
- **Guard block** (recorded, guard unchanged): the push guard refused
  `git commit … && git push` in one command; they ran separately.
