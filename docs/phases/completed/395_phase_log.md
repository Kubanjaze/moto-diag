# Phase 395 — phase log: the fleet hands the operator the database step

**Status:** Complete

**Started 2026-10-29** on the home desktop (WSL2), the only writer, on
`phase-395-the-database-step` from `master` at `f6b6034`. The prompt is
`docs/prompts/395_the_database_step.txt` (the operator's words, verbatim),
with two additions the operator gave with it (K58):
1. the after-the-merge block in the handoff also brings the live server's
   checkout (`~/motodiag/server`) to master, restarts
   `motodiag-api.service` and checks `/healthz`, each part explained in
   plain words: the server is still on 303's merge `159c430`, so 393's
   `src/` changes are not live;
2. that block takes `needs-admiral` off issue #36 so the fleet resumes
   348. #36, its branch and its labels are not touched before then.

## 2026-10-29 — start

- **The numbers, before any is taken.** `git fetch --all` in both
  repositories, then every branch's `docs/FOLLOWUPS.md` and
  `docs/decisions.md` read: the highest F-number is F236 (master; the
  mobile repository's highest is F181), the highest K-id K58. Nothing
  taken yet.
- **The fleet is idle.** `pgrep -x bwrap`: exit 1. `dispatcher.log`'s last
  line (20:43): "next: phase 395 is a builder's (the plan's #5); the fleet
  waits for it". #36 carries `needs-admiral`.
- **The row first.** Row 395 🔲 → 🚧, `59f7378`. `wholetree.sh` before it:
  exit 0, 2442 passed.

## 2026-10-29 — Step 0

`395_step0.md`. Every fact in the prompt re-read and holding (S0-1). The
deploy tools take a stand-in for live with no new knob (S0-2). One hole
found and closed by the design: a rank may change `.claude/skills/deploy/`
on its branch, so the block runs master's deploy tools and refuses a
branch that changes them (S0-3). Decisions in S0-4; none is a rule-1
stop. **The dry run runs in the block**, not in the dispatcher: the dry
run's backup and retain-5 change the backup folder, which only the
operator's paste should do, and a backup taken seconds before the apply is
the one apply-live's "live still equals the backup" can hold.

## 2026-10-29 — the build

- **Guard blocks, each recorded, no guard changed.**
  1. `git commit … && git push` in one command: the push guard refused
     ("it would push a commit it never saw"). Run as two commands.
  2. A Python script editing `engineer.py`: the edit guard refused ("a
     Python script body writes to a path the edit guard cannot resolve,
     and the body names src/ or tests/"); the body held the string
     `src/motodiag/core/migrations.py`. The same edits made with the Edit
     tool.
  3. `sed -i` on `dispatcher.py`: the edit guard refused. Made with Edit.
- **`through_fleet.py`** and its 14 tests, on a real git mirror and tmp
  databases.
- **The Engineer** (`deploy` outcome, `verify_deploy`, `CLOSEOUT`,
  `verify_after_apply`, `migration_changes`), **the dispatcher**
  (`engineer_deploy`, `deploy_block`, `fetch_applied`, `stage_deployed`,
  the `deploy` hold in `held_for`, `resume`, `STAGE_RANK`), **Q1**
  (`database_step`, `live_check`), **the Captain's and the XO's briefs**.
- **A contract asked for the new stage's kill point**
  (`tests/test_phase390_resume_contract.py`: every stage in `STAGE_RANK`
  has one). `deployed` has one, `test_deployed_cut_in_its_close_out_session`,
  and the contract's module list names 395's file, as 391–393 did.
- **A contract kept Q1 read-only** (`tests/test_phase391_contract.py`: the
  module runs only read-only git verbs). Q1's "committed" check uses
  `cat-file -e HEAD:<path>`, already allowed, not `ls-files`.

### Bug fix #1 — 2026-10-29 — the block's question could not be asked on a real terminal

- **Issue.** The trial's first full run (21:22) reached the question and
  stopped: `io.UnsupportedOperation: File or stream is not seekable`, a
  Python traceback, and the block ended with no SOMETHING IS OFF line.
  Nothing was applied: the stand-in stayed at schema 87, real live and the
  real backups were unchanged.
- **Root cause.** `ask_tty` opened `/dev/tty` once, `"r+"`, in text mode;
  Python's text layer refuses a read-write open of a terminal. The tests
  stood the question in (`ask=`), so no test opened a terminal; only the
  trial, in the real place, did. And `main` caught only `Off` and
  `LiveElsewhere`, so any other error ended without the verdict.
- **Fix.** Two opens, one to write the question and one to read the
  answer; `main` turns any other error into `SOMETHING IS OFF` with the
  traceback above it.
- **Files.** `.claude/skills/deploy/through_fleet.py`,
  `tests/test_phase395_through_fleet.py`.
- **Verified.** A new test asks through a pty, in a child whose standard
  input is not the terminal (as the paste block's is not), and a second
  plants an unexpected error: both red on the old code (2 failed), green
  on the fix (16 passed).
**Commit.** `6d425b8`

A first trial run before that one stopped at the push gate ("G3 nothing to
push"): the trial had pushed the planted Engineer's commits to its stand-in
GitHub itself. In the fleet those commits exist only in the stage's clone,
so the trial's planted session now makes them there. Not a defect of the
code under trial.

## 2026-10-29 — the trial, the mutations, the documents

- **The trial**, once, on the home desktop (`395_trial.py`), 21:25: a
  planted phase 990 whose migration 088 adds one empty table, through the
  real `stage_engineer` → `engineer_deploy` (the push gate, pushing to a
  local bare repository standing in for GitHub), the comment's own paste
  block run by bash in a terminal (a pty) and answered "yes", the real
  `through_fleet.py` against a backup-API copy of live (`HOME` and
  `live.json` the trial's own), `needs-hands` off, `stage_deployed` (the
  fetch, the real `verify-live`, the close-out round, `engineer_finish`),
  Q1 outside and inside the fence, and the block pasted again. TRIAL
  PASSED. Real live's schema (head 87) and row counts, and the real backup
  folder's listing, were the same before and after; the API was left
  running (it serves real live, not the stand-in). Its output is
  `.claude/skills/fleet/fixtures/deploy/trial/trial_output.txt`. The first
  full run found bug fix #1.
- **The mutations:** 35/35 red (`395_mutate.out`), each on the phase's own
  tests: 10 on the block's script, 9 on the Engineer, 10 on the
  dispatcher, 4 on Q1, 2 on the planners.
- **The known-bad fixtures** (`.claude/skills/fleet/fixtures/deploy/known_bad/`),
  each refused by its test, the good tree beside it passing: a deploy with
  a dirty clone, a deploy with no scope file, a resume with live not equal
  to the approved diff, a code change after the apply, Q1 with a migration
  and no live diff. Each test is also red under its mutation (E1, E2, D4,
  E4/D6, Q1).
- **Documents:** "Through the fleet" in both skills' `SKILL.md`, each
  `CHANGELOG.md`; F232 closed in `docs/FOLLOWUPS.md`.
- **`COLLECTED_TEST_FLOOR`** 11987 → 12049, by a diff of collected ids
  against master at `f6b6034`: +62 −0.

## 2026-10-29 — the regression of record

- **`wholetree.sh --full`** at `8f20b84` (21:32–21:40): exit 0, 4994
  passed. `pgrep -x bwrap` before it: exit 1, and `dispatcher.log`'s last
  line was still 20:43's "the fleet waits for it".
- **`regression.sh` in this checkout** (21:40–21:52): Regression run
  FAILED (not of record): 12012 passed, 4 failed, 33 skipped, at `8f20b84`.
  The four: `test_phase204_gate10.py::TestFfmpegArgsSurviveModernFfmpeg::
  test_installed_ffmpeg_accepts_the_flag_we_pass` and three in
  `test_phase257_orchestrator_guards.py` (`test_the_script_compiles` ×2,
  `test_the_real_subc_profile_points_at_subconscious`). **The same four
  fail on master** (`origin/master` at `f6b6034`, a worktree, this venv: 4
  failed, 30 passed): they read this machine's own tools and profile, not
  the code. Not a phase defect; not the run of record.
- **The run of record**, as 393's and 394's were: this branch's
  `Fleet.check_run` on `8f20b84` in a fresh clone in the fleet's fence, no
  model and no token, the fleet's venv, with the mobile repository a clean
  clone at its published `main` (`2dc9b20`), by `395_regression.py`
  (21:53–22:15; `wholetree.sh --full` inside it: 4973 passed, 36 skipped).
  Its lines, as printed:

Regression of record: 11944 passed, 0 failed, 105 skipped, 0 errors at `8f20b84` (13 min 5 s wall, `python -m pytest -n auto --dist load --cov=motodiag`, exit 0) (run inside the fleet's fence)
Skipped in the regression of record: [1] tests/test_phase204_gate10.py:47: inside the fleet's fence: no ffmpeg on the home desktop
Skipped in the regression of record: [1] tests/test_phase191b_ffmpeg.py:249: real ffmpeg binary or fixture mp4 not available
Skipped in the regression of record: [1] tests/test_phase191b_ffmpeg.py:264: real ffmpeg binary or fixture mp4 not available
Skipped in the regression of record: [1] tests/test_phase191b_ffmpeg.py:269: real ffmpeg binary or fixture mp4 not available
Skipped in the regression of record: [1] tests/test_phase191b_ffmpeg.py:277: real ffmpeg binary or fixture mp4 not available
Skipped in the regression of record: [1] tests/test_phase191b_ffmpeg.py:283: real ffmpeg binary or fixture mp4 not available
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
Skipped in the regression of record: [1] tests/test_phase257_sandbox_boundary.py:119: sandbox-exec is macOS-only; the orchestrator runs only there
Skipped in the regression of record: [1] tests/test_phase257_sandbox_boundary.py:125: sandbox-exec is macOS-only; the orchestrator runs only there
Skipped in the regression of record: [1] tests/test_phase257_sandbox_boundary.py:131: sandbox-exec is macOS-only; the orchestrator runs only there
Skipped in the regression of record: [1] tests/test_phase257_manual_route_excerpts.py:147: needs the on-disk library
Skipped in the regression of record: [1] tests/test_phase257_source_checks.py:527: the KTM manual is not in this machine's library
Skipped in the regression of record: [1] tests/test_phase257_manual_route_excerpts.py:352: needs the on-disk library
Skipped in the regression of record: [1] tests/test_phase257_manual_route_excerpts.py:358: needs the on-disk library
Skipped in the regression of record: [1] tests/test_phase257_manual_route_excerpts.py:364: needs the on-disk library
Skipped in the regression of record: [1] tests/test_phase257_manual_route_excerpts.py:367: needs the on-disk library
Skipped in the regression of record: [1] tests/test_phase257_source_checks.py:476: acquired/Yamaha/library_om_contents_pdf_10_5YR-F8199-15_02.pdf is not in this machine's library
Skipped in the regression of record: [7] tests/test_phase257_source_checks.py:211: needs the on-disk library
Skipped in the regression of record: [1] tests/test_phase257_source_checks.py:476: acquired/KTM/24_3214961_en_OM.pdf is not in this machine's library
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
Skipped in the regression of record: [1] tests/test_phase257_orchestrator_guards.py:85: inside the fleet's fence: no Subconscious login there (K42)
Skipped in the regression of record: [2] tests/test_phase257_orchestrator_guards.py:149: inside the fleet's fence: osacompile is macOS-only
Skipped in the regression of record: [4] tests/test_phase257_sandbox_boundary.py:72: sandbox-exec is macOS-only; the orchestrator runs only there
Skipped in the regression of record: [1] tests/test_phase257_sandbox_boundary.py:80: sandbox-exec is macOS-only; the orchestrator runs only there
Skipped in the regression of record: [1] tests/test_phase257_sandbox_boundary.py:87: sandbox-exec is macOS-only; the orchestrator runs only there
Skipped in the regression of record: [1] tests/test_phase257_sandbox_boundary.py:93: sandbox-exec is macOS-only; the orchestrator runs only there
Skipped in the regression of record: [1] tests/test_phase257_sandbox_boundary.py:106: sandbox-exec is macOS-only; the orchestrator runs only there
Skipped in the regression of record: [1] tests/test_phase257_sandbox_boundary.py:112: sandbox-exec is macOS-only; the orchestrator runs only there
Line coverage of record: 87.62% at `8f20b84` (the pin is 87.50%)

- **Free space**, the close-out's reclaim
  (`python3 .claude/skills/fleet/dispatcher.py reclaim`): C: 282.1 -> 282.1
  GB free (nothing came back to Windows: the disk image is not sparse, so
  the trim freed space inside Ubuntu only); Ubuntu 1007.1 -> 1007.1 GB free;
  fstrim: /: 1.8 GiB (1954820096 bytes) trimmed.

## 2026-10-29 — close-out

- **Live:** none. Nothing here changes live; the trial used a copy.
- **Guard blocks:** the push guard refused `git commit … && git push` a
  second time (21:30, my repeat of the first); the two were run apart.
- **#36, its branch and its labels** were read only (Step 0), never
  written; the handoff's block releases #36 after the merge.
- No refute pass ran.
