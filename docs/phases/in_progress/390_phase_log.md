# Phase 390 — phase log: the fleet resumes where it left off

**Status:** In progress
**Branch:** `phase-390-resume`
**Prompt:** `docs/prompts/390_resume.txt`

## 2026-10-25 — start

- Read the plan: row 389A and the rows around it, `ROADMAP_AUTHORITY.md`
  (390 is backend, 205+), the newest handoff
  (`2026-10-25_389_closed.md`), F219, the `fleet` skill and the whole of
  `dispatcher.py`.
- **Row 390, 🚧, committed on `master` and pushed** (`6f32013`), before
  Step 0, as 389A's row was: a planted mission is run only when its
  phase's row on `master` is 🚧 (`dispatcher.py` l. 1144). 103 words by
  `roadmap_words.py`; `roadmap_check.py` ok; `wholetree.sh` exit 0
  (2085 passed, 10 skipped) before the commit.
- Branch `phase-390-resume` from `6f32013`, pushed.
- The service was in #14's Red Team round 2 (`dispatcher.log` 15:54:46,
  no end line). Nothing on the service, #14, PR #15 or the 389A branch was
  touched; no restart.

## 2026-10-25 — Step 0

`390_step0.md`. Every kill point per rank, what each leaves behind, what
the next start does with it today, and which of 389's resume code is
reused. Reported to the operator before v1.0, as the prompt asks; not a
stop (rule 1 names none here).

- **A guard block, recorded (rule 6):** `git commit … && git push` in one
  command was refused by `pre_push_guard.sh` ("Run `git commit` and `git
  push` as separate commands"). Run separately: Step 0 committed as
  `9197117` and pushed. The guard was not touched.

## 2026-10-25 — the operator on Step 0

"Step 0 checked against dispatcher.log and git ls-remote: it holds. Carry
on: v1.0, plan commit pushed, then build. The rule stands: no service or
Ubuntu restart while any #14 stage is running (the Engineer's fix round 2
started 16:02, then its regression and Red Team round 3). Run your one
small --resume measurement whenever suits, and write the whole-Ubuntu
restart as my paste block only when there is a gap."

## 2026-10-25 — S0-5 measured: `--resume` after a kill, in the fence

The probe (the session's scratchpad, `resume_probe.py`): a Haiku call
through `fence.sh` with the token on fd 3, the Read tool, six files to open
one at a time, in its own process group; the group SIGKILLed (what the
unit's control-group kill does); the session id read from the transcript's
file name; a second fenced call with `--resume <id>` and a `--json-schema`.

| killed | killed call's stdout | transcript | resumed call |
|---|---|---|---|
| at 3.5 s, after 2 assistant lines | empty | `155dc771-….jsonl` | exit 0, the **same** session id, the same one file, `structured_output` `{'opened': ['README.md']}`, 2 turns, $0.0038 |
| at 1.5 s, no assistant line yet | empty | `87152a3c-….jsonl` (the prompt only) | exit 0, the same id, `{'opened': []}`, 2 turns, $0.0028 |

So: a killed call's id is always on disk once its transcript exists, and
`--resume` keeps that id (no new file), so the newest transcript that was
not there before a call is that call's session. A schema call resumes with
its schema. A first probe without tools finished in 13.5 s before the kill:
a one-turn answer is written to the transcript only when complete. Total
model cost of the measurement under one cent.

The service was not touched: the probe used its own run directory in the
scratchpad and a clone of the mirror (read).

## 2026-10-25 — v1.0 committed and pushed

`ea1f057`. `plan_check.py 390`: P1–P8 pass, after Step 0's two counts
were given their source (`KEEP_RUNS = 20`; `grep -n 'self.pause('`).

## 2026-10-25 — the build

- `journal.py` (new); `dispatcher.py`: `new_run` writes the journal before
  the clone; `begin`/`finish`/`step`; the replay in `FencedRunner` (calls,
  the Engineer's session) and `checked` (model-free runs); every stage on
  steps with GitHub checks; ` run=` on every marker; a `started` marker for
  every rank; `run_stage`; `recover` and `recover --dry-run`; the pause kept
  until its stage ends; `prune_runs` keeps unfinished runs.
  `rank_call.call` skips the ledger for a replayed call;
  `engineer.CONTINUE`.
- **Decision: the `started` marker has its own prefix**,
  `<!-- fleet-started:`, not the dispatcher's. With the dispatcher's
  prefix, six of 389's tests went red: the XO's due rule counts every
  dispatcher comment as a rank comment, so the Captain's `started` marker
  made the XO not due whenever `plan:needs-review` was applied in the same
  second. No due rule reads the new prefix.
- **Decision: a call's journal key leaves the prompt out** (model, tools,
  schema only). The replay of a cut Science Officer stage ran its finished
  second call fresh: its prompt carries a census of the clone, and the
  stage's own committed Step 0 had changed that census. A finished call's
  answer is still the right one. Deviation from v1.0 section 2.
- **Decision: the marker search says a stop only when no stage is due**
  (F219's stall), in place of v1.0's "a flow label applied after it". #14's
  real history, read into `fixtures/resume/` at 16:33, showed why: at 15:50
  the operator re-applied `review:open`, a label the Engineer also sets, so
  the label rule read the operator's hand as the Engineer's own work and
  would have commented on #14. The due rule sees the Red Team due and says
  nothing. Deviation from v1.0 section 5.
- 388's `test_a_resumed_opus_stage_is_not_new` now builds its resumed
  session from a journal (the runner's `resume=` argument is gone); the
  assertion is unchanged.
- **#14 reached `needs-admiral` at 16:29** (the Engineer's fix round 2:
  "the work says it is ready, and the checks say it is not"). No #14 stage
  runs since; it is the operator's.
- **The dry run on the live state** (16:3x, `dispatcher.py recover
  --dry-run` from this checkout): "nothing to resume", exit 0;
  `state.json` and `dispatcher.log` modification times unchanged before
  and after. No journal exists yet on the live host, and #14 is held.
- **A guard block, recorded (rule 6):** a `sed -i` of mine on
  `tests/test_phase390_search.py` was refused by `edit_guard.sh`. Made with
  the Edit tool instead; the guard untouched.
- Tests: `test_phase390_resume.py` (29: every kill point in Step 0's
  tables, and the pause), `test_phase390_search.py` (18, #14 at 15:34,
  15:50 and 16:33), `test_phase390_kill.py` (1: a real process SIGKILLed
  with its group, a second process resumes). 128 passed with 388's and
  389's dispatcher tests.

## 2026-10-25 — the operator, from the fleet watch (16:4x)

"Two things from the fleet watch. (1) Your whole-tree run at 16:16 and the
pytest runs at 16:27 overlapped #14's model-free run (16:11 to 16:29), and
it failed on one load timeout: test_phase240_gate12 -> test_phase159_gate_7
-> test_phase147_gate_6's 60-second subprocess limit on test_phase121_gate_r
(log in runs/20261025_161137_check/clone/.git/motodiag_wholetree/last_full.log).
File it as a finding. From now on, before any whole-tree or regression run,
check dispatcher.log for a fleet model-free run in progress and wait for it
to end. (2) #14 is on needs-admiral because of that, not because of the
work. Its round-2 fix is e15b462 in runs/20261025_160200_engineer_389A/clone.
Keep that folder from being pruned by your proofs. Make #14 the
real-artefact proof: once 390 is merged and live, the operator taking
needs-admiral off an Engineer stop whose only failure was the model-free run
should rerun that run on the same commit, then push and go on to Red Team
round 3. Write that as my paste block when it is time. Don't touch #14 or
its labels yourself."

- **Checked, and it holds.** The model-free run: 16:11:37 to 16:29:02
  (`dispatcher.log`). Its log, l. 95: "timed out after 60 seconds"; l. 117:
  "1 failed, 4529 passed, 36 skipped … in 1039.46s". My `wholetree.sh` for
  the v1.0 commit ended 16:17:49 at 88.5 s wall (55–57 s before and after).
  My mistake: I did not look for a fleet run before mine.
- **Filed F220** (`next_f_number.sh`: F219 here, F181 in mobile; next F220).
  `finding_check.py` exit 0.
- **The rule, kept from now on:** before each `wholetree.sh`, regression or
  large pytest run, the last line of `dispatcher.log` is read for a
  model-free run in progress. Every run since has been preceded by that
  read (the last line each time: 16:29:02 "issue 14: checks failed").
- **Read-only, #14's run:** `runs/20261025_160200_engineer_389A/clone` at
  `e15b462`, clean; `engineer.json` `pr-ready`; its stop comment's two
  items are both the model-free run's; `engineer.verify` with the
  Engineer's own regression line: `[]` (nothing else fails), the clone
  unchanged after (0 changed paths before and after). GitHub's branch is
  at `bdecabd`: `e15b462` was never pushed.
- **Built, at the operator's word** (an addition to v1.0; Deviations):
  `engineer_finish` (the Engineer's tail, shared); when only the model-free
  run fails (the Engineer's own line passes every other check), the run is
  **held** (`journal.hold`, `held.json` in the run folder) and the stop
  says "take `needs-admiral` off to run it again on the same commit";
  `prune_runs` keeps a held run; `held_for` and `stage_recheck`: with
  `build:open`, a held run for the issue, and the Engineer's stop still the
  last rank comment (the operator has taken the label off), the model-free
  run again on the held commit, then the push, the PR comment, `pr-ready`,
  `review:open`, and the hold released; failing again, held again.
- **#14's run held by hand** (17:0x): `held.json` written into
  `runs/20261025_160200_engineer_389A` with `journal.hold`: issue 14, phase
  389A, round 2, commit `e15b46278cc0fe64fb3269909f38a1b1a1642693`. The
  running service (old code) does not read it; nothing on #14, its labels,
  PR #15 or the 389A branch was touched. It keeps the folder from 390's
  prune and is what the recheck finds once 390 is live.
- **Two more guard blocks, recorded (rule 6):** a `sed -i` and a `>>`
  redirect of mine into `tests/` were refused by `edit_guard.sh`. Both
  redone with the Edit tool; the guard untouched.
- Tests added: the held stop, the recheck on the same commit and on to the
  Red Team, a failure beyond the model-free run not held, the recheck
  failing again, the recheck cut half way, the prune keeping a held run,
  and #14's real comments with `needs-admiral` off and its run held (the
  recheck due; without the hold, nothing). 95 passed across the four 390
  files.
