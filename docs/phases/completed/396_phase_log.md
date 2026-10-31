# Phase 396 — phase log: the fleet's four slips from 348 and 385

**Status:** Complete

**Started 2026-10-31** on the home desktop (WSL2), the only writer, on
`phase-396-the-fleets-four-slips`. The prompt is
`docs/prompts/396_the_fleets_four_slips.txt` (the operator's words,
verbatim); the operator's word is K61.

## 2026-10-31 — start

- Master fetched at `8e5f014`; nothing newer from the Mac, so K61 is the
  next K-id.
- `3dff6d0`: the prompt, row 396 🔲, row 8 of "Next, in order" with the
  dated entry, K61 (by `yeoman.py decide`) and
  `tests/test_phase392_plan_order.py` (one test added). Merged to master as
  `230a077` and pushed, as 395's prompt was, so the fleet reads 396 as
  next. At 13:26 the dispatcher logged "next: phase 396 is a builder's
  (the plan's #8); the fleet waits for it".
- **Guard blocks** (recorded, guards unchanged): the edit guard refused a
  Python script body writing `tests/test_phase392_plan_order.py`, and a
  `sed -i` on the ROADMAP; the Edit tool did both. The push guard refused
  `git checkout … && git push` in one command; they ran separately.
- Row 396 🚧 on the branch before Step 0.
- The fleet idle before each whole-tree run: `pgrep -x bwrap` empty, and
  no model-free run open in `dispatcher.log`.

## 2026-10-31 — Step 0

`396_step0.md`. Each slip's cause, measured on the real artefact:
(a) `check_run`'s `" ".join(command)` breaks the `sh -c` script, and the
reason given was a tail of the command; (b) A8 makes a fleet close-out
write "No refute pass ran" before the Red Team's table exists; (c) the
mirror is refreshed only at a cycle's start; (d) `plan_commit` is the
commit that first added the plan. F237 and F238 filed for the two
out-of-scope items.

`e06db8c`: Step 0 and v1.0, pushed before any code.

## 2026-10-31 — the build

Tests first: `tests/test_phase396_slips.py` written before any fix, and
seen red: 26 of 29 failed. The two that reproduce a slip's behaviour, not
a missing name, failed as the real phases did: the unstubbed `check_run`
printed bash's "syntax error near unexpected token `then'" (385's kept
output, byte for byte but the paths), and the cycle with a merge during a
stage opened a second issue for the merged phase (#44).

- **(a)** `dispatcher.check_run`: `shlex.join(command)`.
  `quartermaster.no_result_why`: how the run ended, a time limit first, then
  the first line naming an error, else the last line; `code_findings`
  passes it; `code_checks` never leaves the reason empty. A stage-level
  test feeds 385's real output through the Quartermaster's stage and reads
  the comment.
- **(b)** `engineer.BRIEF` rule 7: the phase goes to the Red Team after the
  close-out; no sentence about a refute pass, the word left out of the
  log. `closeout_check.refute_contradictions`, inside A8. 385's v1.1 lost
  its two fragments ("no refute pass unless one runs" in Logic 8, "no
  refute pass" in Deviations), deleted, not rewritten (K9); 385's own
  checklist row still quotes the line it judged, which the check does not
  read.
- **(c)** `cycle()`: `update_mirror()` and `master_rows()` before `next_due`.
- **(d)** `red_team.plan_commit(clone, phase, approved_at)` and
  `plan_label`; `Fleet.plan_approved_at`; both gathers pass it. My first
  test expected #36's first approval (02:30Z) to pick the XO's round-2
  revision; the plan at 22:30 EDT was in fact still the Captain's draft,
  so the test was wrong, not the code, and now asserts both times.

**Mutations** (`396_mutate.py`, `396_mutate.out`): first run 17/19. A4
(the time limit said first) survived: its test's partial output had no
error line, so the error search found "time limit" anyway; the test now
has an error line the limit must win over. C2 (the cycle's start-of-cycle
`rows` kept after the refresh) is an equivalent mutant: `next_due` reads
the plan and the ROADMAP from the mirror itself, and `rows` only gates a
case `stage_next` re-checks against the fresh mirror; it was dropped. Then
18/18 red.

**The real fence** (`396_real_fence.py`, 389's rule): this branch's
`check_run`, the real `fence.sh`, the fleet's venv, a clone of the fleet's
mirror, at the heads the Quartermaster judged against the masters it
judged them on (348: `dd5aed2` on `d76b865`; 385: `46db82e` on `ddcdfd6`),
26 s. Both printed a result:
- 348: `{"Q10": [], "Q12": [{"file": "src/motodiag/core/migrations.py", "bytes": 575007, "base_bytes": 572812, "limit": 100000}]}` (F238);
- 385: `{"Q10": [], "Q12": []}`.
The command runs `/fleet/run/code_quality.py`, which exists only inside the
fence (`ls /fleet` on the host: no such file). Kept as
`fixtures/slips396/a_real_fence_348.txt` and `a_real_fence_385.txt`.

**Floor**: 12152 → 12184, by a diff of collected ids against master at
`8e5f014`: +32 −0 (`test_phase396_slips.py` 31, `test_phase392_plan_order.py` 1).

`c8bd296`: the build.

## 2026-10-31 — the regression of record

- **`wholetree.sh --full`** at `c8bd296` (13:43–13:51): exit 0, 5038
  passed, 15 skipped. `pgrep -x bwrap` before it: empty, and
  `dispatcher.log`'s last line was 13:26's "the fleet waits for it".
- **`regression.sh` in this checkout** (13:51–14:02): Regression run
  FAILED (not of record): 12147 passed, 4 failed, 33 skipped, 0 errors at
  `c8bd296`. The four are 395's: `test_phase204_gate10.py`'s
  installed-ffmpeg check and three of `test_phase257_orchestrator_guards.py`
  (`test_the_script_compiles` ×2, `test_the_real_subc_profile_points_at_subconscious`).
  **The same four fail on master** here (a worktree at `8e5f014`, this
  venv: 4 failed, 31 passed): they read this machine's tools and profile,
  not the code. Not a phase defect; not the run of record.
- **The run of record**, as 393's, 394's and 395's were: this branch's
  `Fleet.check_run` on `c8bd296` in a fresh clone in the fleet's fence, no
  model and no token, the fleet's venv, with the mobile repository a clean
  clone at its published `main` (`0773f91`), by `396_regression.py`
  (14:03–14:25; `wholetree.sh --full` inside it: 5017 passed, 36 skipped).
  Its lines, as printed:

Regression of record: 12079 passed, 0 failed, 105 skipped, 0 errors at `c8bd296` (13 min 8 s wall, `python -m pytest -n auto --dist load --cov=motodiag`, exit 0) (run inside the fleet's fence)
Skipped in the regression of record: [1] tests/test_phase191b_ffmpeg.py:249: real ffmpeg binary or fixture mp4 not available
Skipped in the regression of record: [1] tests/test_phase191b_ffmpeg.py:264: real ffmpeg binary or fixture mp4 not available
Skipped in the regression of record: [1] tests/test_phase191b_ffmpeg.py:269: real ffmpeg binary or fixture mp4 not available
Skipped in the regression of record: [1] tests/test_phase191b_ffmpeg.py:277: real ffmpeg binary or fixture mp4 not available
Skipped in the regression of record: [1] tests/test_phase191b_ffmpeg.py:283: real ffmpeg binary or fixture mp4 not available
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:438: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:445: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:464: inside the fleet's fence: no network to build a wheel
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
Skipped in the regression of record: [1] tests/test_phase257_manual_route_excerpts.py:147: needs the on-disk library
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
Line coverage of record: 87.71% at `c8bd296` (the pin is 87.50%)

## 2026-10-31 — close-out

- v1.1; this log Complete; the phase's files moved to
  `docs/phases/completed/`; row 396 ✅; `implementation.md` 0.13.125 and
  its history row; the root `phase_log.md`'s pointer; the handoff
  `docs/handoffs/2026-10-31_396_closed.md`.
- No bug fixes: no defect was found in code this phase had committed.
- No refute pass ran: the phase changes fleet code and tests, takes no
  content rows, and is a builder's phase, which the fleet's Red Team does
  not review.
- No migration and no change to live.
- The reclaim line, from `dispatcher.py reclaim` on the desktop: C: 281.4 -> 281.4 GB free (nothing came back to Windows: the disk image is not sparse, so the trim freed space inside Ubuntu only); Ubuntu 1007.2 -> 1007.2 GB free; fstrim: /: 6.7 GiB (7168823296 bytes) trimmed

## 2026-10-31 — after the close-out

- **The close-out commit was amended once, before any push:** between
  `git add -A` and the commit the index lost the moves out of
  `in_progress/` and the ROADMAP and root edits (the whole-tree run in
  between reported "the working copy differs from the index"), so the first
  commit held only the new files. `git add -A` and `--amend` gave
  `5874027`; `closeout_check` and `code_after_regression` pass on it.
- **The push of K61's row to master (`230a077`)** printed "Cannot update
  this protected ref" and was accepted: it went through as the operator's
  account's bypass of master's ruleset. Recorded for the operator.
- **PR #46**: `ratchet` passed; the merge was refused by the ruleset
  ("the base branch policy prohibits the merge"). Not overridden with
  `--admin`: the merge is the operator's.
- `verify_phase.sh 396 c8bd296 5874027`: 13 of 14; check 1 waits on the merge.
