# Phase 395 — phase log: the fleet hands the operator the database step

**Status:** In progress

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
- **Commit.** `6d425b8`

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
