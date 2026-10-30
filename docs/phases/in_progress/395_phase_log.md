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
