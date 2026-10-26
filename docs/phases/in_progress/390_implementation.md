# Phase 390 — The fleet resumes where it left off

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-10-25 (v1.0 `ea1f057`)

v1.1 updates every section to what shipped (each change marked "As
built"), ticks the planned items, and adds Deviations and Results. Two
pieces of scope were added by the operator during the build: the held run
and its recheck (section 10), and free space phase to phase, which closes
F221 (section 11).

---

## Goal

Close F219: a stage killed by a restart, a power cut or a crash is lost
today, and its issue stalls with nothing said (Step 0, S0-2: every rank has
such a kill point). After this phase:

1. **Every stage keeps a journal** in its run directory, written before
   the stage does anything and after each step it finishes.
2. **On every start, before its first cycle, the dispatcher searches** the
   run directories for unfinished journals and the open issues for a
   rank's `started` marker with no end after it, and **resumes** each
   unfinished stage from its run directory: a model call with `--resume`
   and the session id from its transcript, a model-free run started again
   on the same commit, then the push, the pull request, the comments and
   the label it was waiting on, each checked against GitHub first so
   nothing is written twice. **One log line per resumed stage.**
3. **A stage that cannot be resumed** gets a stop comment on its issue, and
   its label is left as it was. The fleet never goes quiet.
4. **Every rank is covered**: the Science Officer, the Captain (v1.0,
   revision, recommendation), the Executive Officer, the Chief Engineer
   (its session, its model-free run, its push and its pull request), the
   Red Team, and the digest.
5. **`prune_runs` never deletes an unfinished run.**

As built, two more, both the operator's:

6. **An Engineer stop whose only failure is the model-free run is held**,
   and taking `needs-admiral` off runs that run again on the same commit
   (section 10; the operator after F220).
7. **Free space is part of the method**: a reclaim on a timer, at each
   merge and at each close-out, and a floor below which no new stage
   starts (section 11; F221, closed).

The prompt is `docs/prompts/390_resume.txt`. Step 0 is `390_step0.md`
(classification: extension). The Quartermaster moves to the next phase.

## Logic

### 1. The journal (`journal.py`, new)

`runs/<run>/stage.json`, beside `clone/` and `run/`, **outside** the
fence's `/fleet/run`, so no model can write it. Written atomically
(write to a temporary file, then rename), as `state.json` is.

- `record`: what `Fleet.resume` needs to call the stage again: `stage`,
  `issue`, `phase`, `run`, and the stage's own arguments (`title`, `body`,
  `branch`, `items`, `rnd`, `findings`, `day`). The pause record's shape
  (`dispatcher.py` l. 705–971), so a pause and a kill resume through the
  same door.
- `pid`, `boot` (`/proc/sys/kernel/random/boot_id`), `started`.
- `calls`: one entry per model call, in order: a hash of its command (the
  `--resume` flag left out), the transcripts that existed before it, its
  session id once known, and, when it finished, its exit code and output.
- `checks`: each finished model-free run, keyed by commit and kind, with
  its verdict and regression line.
- `steps`: each GitHub write and commit this stage has made, by name.
- `ended` and `outcome`, set when the stage is over (done, stopped,
  escalated). A paused stage is not ended.

Written before the first thing a stage does: `new_run` takes the record
and writes the journal before it returns, before the clone.

### 2. Replay: what a resumed stage does not do twice

A resumed stage calls its rank's function again from the top (`scout`,
`captain.write_plan`, `xo.review`, `red_team.review`, `captain.recommend`,
`yeoman.digest`). The runner it is handed replays the journal:

- **A model call that finished** returns its saved output and makes no
  call. Its output carries `"fleet_replayed": true`, and `rank_call.call`
  does not write a replayed call to the cost ledger a second time.
- **The call that was cut** is made again with `--resume <id>`, the id
  being the transcript that appeared after the call began (S0-5 measured
  that `--resume` keeps the id and its file). With no transcript, the call
  is made fresh in the same run directory.
- **A call whose command differs from the saved one** (a prompt that
  changed between the two runs) ends the replay: that call and every later
  one run fresh, and the log line says so.
  *As built:* the key (`journal.call_key`) is the command without its
  prompt and without `--resume`. The scout's second prompt holds a census
  that changes once its own Step 0 is committed, so a prompt-keyed replay
  would never match. A changed command (another model, schema or tool
  list) still ends the replay. A resumed call sends its original prompt
  again into the resumed session.
- A resumed stage is not new: the 70% gates do not apply to it (389's
  `gate_model` rule, unchanged).
- **The Engineer's session** is one call: a finished session is not
  resumed; a cut one is resumed with 389's continuation prompt, reworded
  to cover a restart as well as a usage limit.
- **A model-free run that finished** returns its saved verdict; one that
  did not is started again on the same commit (the run is a function of
  the commit alone: no model, no token, `--net none`).

### 3. Steps: what a resumed stage checks on GitHub before writing

A kill can fall between a write to GitHub and the journal's record of it.
So when a stage is resumed, each step not in `steps` first asks GitHub
whether it is already done, and does only what is missing:

| step | already done when |
|---|---|
| a commit | the clone's `HEAD` is past the base the journal saved, with this subject |
| a push | the mirror, updated, has the branch at this commit |
| a rank's marker comment | a comment on the issue begins with this marker, which now ends ` run=<run>` |
| a pull-request comment | a comment on the PR carries this marker, with ` run=<run>` |
| a pull request | `pr_for(branch)` finds it |
| a label | the issue carries it; for the Captain's revision, `plan:needs-review` applied after this run's marker |
| an escalation | the operator's label is on the issue (its comment alone: the label only) |
| the XO's verdict | `xo.review` is not called again when a verdict comment newer than the journal's start exists; the label it names is set |

Every marker a stage writes gains ` run=<run name>` before ` -->`. The
due rules and the regular expressions that read markers read prefixes, so
nothing that parses them changes (checked in the tests).

### 4. The `started` marker, for every rank

The Engineer's `started round=N` marker gains ` run=<run>`. Every other
rank posts `<!-- fleet-dispatcher: started rank=<rank> run=<run> -->`
with one plain sentence ("Science Officer, phase N: started"), as the
journal's first GitHub step. The digest has no issue and posts none.

*As built:* the marker is `<!-- fleet-started: rank=<rank> run=<run> -->`,
with its own prefix (`STARTED_M`). With the dispatcher's prefix, the XO's
due rule read it as a rank's comment, and six 389 tests failed. No due
rule reads the new prefix, so a stage's start never makes its own label
look handled.

### 5. The search on start (`Fleet.recover`)

Called by `run` and `once` after the lock and before the first cycle,
after the mirror is updated.

1. **Run directories:** every `stage.json` with no `ended`, oldest first,
   except the run named by `state.json`'s `paused` (it waits for its
   reset). We hold the lock, so no other dispatcher can own one; the
   journal's `pid` and `boot` are logged.
   - Its issue closed, carrying `needs-admiral` or `needs-hands`, or its
     phase's row on `master` no longer 🚧: not resumed. The journal is
     ended `abandoned`; a comment on an open issue says why, label
     unchanged; a log line either way.
   - Another rank's marker on the issue after the journal's start
     (another stage has run since, by hand or by older code): the same.
   - Otherwise it is resumed through `Fleet.resume`: one log line, "resume:
     <stage> on issue N from <run>, at <step>, session <id or fresh>",
     and one more for its outcome.
2. **Markers:** on each open issue the cycle would look at (`mission`, a
   🚧 row, no operator label), the newest `started` marker per rank
   (both forms, and the Engineer's older form without ` run=`). It is
   **open** when nothing ends it after it: that rank's end marker
   (`pr-ready`, a verdict, `step0`, a v1.0, a revision, a recommendation),
   a `stopped rank=`, a `needs-admiral`/`needs-hands rank=`, a
   `rate-limited stage=` comment, the XO's verdict or stop, **or a flow
   label applied after it** (the issue moved on: #14's 15:06 marker, the
   operator's 15:50 `review:open`). An open marker whose run has an
   unfinished journal is step 1's. Any other open marker gets the stop
   comment, `stopped rank=<rank> run=<run or none>`: "the stage started at
   T was cut off and left nothing to resume from; label unchanged; apply
   `<label>` again to run it fresh." That comment ends the marker, so it
   is said once.
   *As built:* an open marker with nothing to resume gets the stop comment
   only when the issue is **stalled**, meaning no stage is due on it
   (`Fleet.stalled`, `next_stage` is None). The flow-label rule above
   failed on #14's real history: at 15:50 the operator applied
   `review:open` again, a label the Engineer also sets, so the rule read
   it as the Engineer's own work. Under the stall rule, a label applied
   by hand makes a stage due, the cycle runs it, and nothing needs saying.
3. **A stage that cannot be resumed** (its resume raises `Stop`, or any
   other error) gets the same stop comment with the reason, its journal is
   ended `stopped`, and the label stays. An error with no issue (the
   digest) is logged.

`dispatcher.py recover --dry-run` prints what the search would do and
writes nothing: no lock, no comment, no label, no journal. It is run on
the live state before the code goes live (the fleet's rule since 389).

*As built:* every search ends with one summary line in dispatcher.log,
"the search on start: nothing to resume" or "the search on start: N
stage(s) acted on". Before that, a start with nothing to do logged
nothing, and could not be told apart from a start that never searched.

### 6. The pause, kept until its stage ends

`cycle` no longer removes `paused` before the resumed stage runs (l. 1116):
it is removed after the stage returns or stops. A stage that pauses again
writes a new `paused`. A kill during a resumed stage leaves `paused` past
its reset, and the next cycle resumes it again from its journal.

### 7. `prune_runs`

Never removes a run whose journal has no `ended`, nor the paused run.
`check` runs carry no journal and stay prunable: a finished one's verdict is
in its stage's journal, and an unfinished one is started again.

### 8. The service, and #14

The new code reaches the service as 389's did: the service's clone
(`~/motodiag/fleet/code`) switched to `phase-390-resume`, then a restart.

- **Not while any #14 stage runs** (the operator's rule). The deploy waits
  until #14 rests on a label the fleet does not move (`merge:needs-review`
  or `needs-admiral`), or, if the build is ready first, for a gap between
  #14's stages, read in `dispatcher.log`.
- Before it, `recover --dry-run` on the live state must show nothing to do
  for #14 (its old `started` markers end in later markers and labels).
- From then, #14's remaining stages, if any, run on the new code and post
  `started` markers. That is the fleet's own work, not a hand on #14.

**How the service is restarted.** `sudo -n -l` lists a password-free
`systemctl` only for `motodiag-api.service`. As in 389, the restart is a
SIGTERM to the unit's main process (`systemctl show -p MainPID`, the
operator's own user's process): `Restart=always` starts it again after 30
seconds, and `KillMode=control-group` kills the stage's processes, the
same end a `systemctl restart` makes. The phase log records each one.

### 9. The proofs: "restart each portion of the fleet"

Row **390A** 🚧 on `master` first (a follow-on, as 389A was): "the
restart proofs' planted mission", whose deliverable is row 391, the
Quartermaster, not started. Every planted issue is titled `Phase 390A: …`,
carries the trial marker (pre-approval (a): pushes under the operator's
login), names the one branch `phase-390A-quartermaster-row`, and is closed
by the planter once its rank's stage has reached its label, before the
next cycle picks it up. Labels on planted issues are applied by the
planter.

| rank | the planted issue starts at | restarted during | proof: with no hand on it |
|---|---|---|---|
| the Science Officer | `mission` | its model call | `step0:done`, one Step 0 commit |
| the Captain, v1.0 | `step0:done` | its Fable call | `plan:needs-review`, one v1.0 commit |
| the Executive Officer | `plan:needs-review` | its Fable call | its verdict's label, one verdict comment |
| the Chief Engineer | `plan:approved` (once the XO approves) | its session, and again its model-free run | `review:open`, one push, one PR |
| the Red Team | `review:open` (the PR above) | its Opus call | its verdict's label, one PR comment |
| the Captain's recommendation | `review:clear` | its Fable call | `merge:needs-review`, one PR comment |
| the digest | `last_digest` set back one day in `state.json` while the service is idle | its Haiku call | the digest written, `last_digest` saved |

Each: the restart time, the log's resume line, the session id resumed (the
same as the transcript's), the label reached, and a count of the issue's
comments showing nothing doubled. If the XO sends the plan back, the
Captain's revision and the next round run on the XO's issue until approve
or the XO's own limit; the Engineer's issue waits for an approved plan.

**The whole-Ubuntu restart is the operator's**: a paste block for the
administrator PowerShell (`wsl --shutdown`, then a check that prints the
resume line) ending ALL GOOD or SOMETHING IS OFF, given only when no #14
stage is running, timed for the middle of a planted stage (the Engineer's
model-free run is the longest).

### 10. A held run and its recheck (as built; the operator after F220)

The operator, 2026-10-25, after F220 (my test runs overlapping #14's
model-free run made it time out): "Make #14 the real-artefact proof: once
390 is merged and live, the operator taking needs-admiral off an Engineer
stop whose only failure was the model-free run should rerun that run on
the same commit, then push and go on to Red Team round 3."

- `engineer_finish` is the shared tail of a `pr-ready`: the model-free run
  on HEAD, the push, the PR, `review:open`.
- When the model-free run is the only failure (`engineer.verify` with the
  Engineer's own regression line passes), the run is held:
  `journal.hold` writes `held.json` (issue, phase, round, commit). The
  stop then says "take `needs-admiral` off to run it again on the same
  commit".
- `held_for` finds the held run once `needs-admiral` is off and that
  stop is still the issue's last rank comment. `stage_recheck` checks
  the held clone is at the held commit, then runs `engineer_finish` on
  it. `prune_runs` keeps held runs.
- #14's run (`runs/20261025_160200_engineer_389A`, commit `e15b462`) was
  given its `held.json` by hand, so that the operator's step after the
  merge is this path.

### 11. Free space, phase to phase (as built; the operator, F221)

The operator, 2026-10-25: "it's just something that needs to be done
frequently to free up the claimed space, now it just needs to be written
into the method itself. as a part of the overall process phase to phase".
Their numbers: "50 GB on each", "every 3 hours".

- **The one-time switch, the operator's** (`390_compact_vhdx.ps1`, run
  23:10): the disk image made sparse (`wsl --manage --set-sparse true`),
  and `ops/desktop/install_fstrim_sudoers.sh`, which allows lilcu
  `fstrim -v /` and nothing else, with no password. bubblewrap sets
  `no_new_privs`, so no model can use it.
- **`Fleet.reclaim`** runs fstrim through that line. It runs on the
  3-hour timer, at each merge (a row 🚧 on master at the last cycle and ✅
  now) and at each close-out (after the Engineer's model-free run passes,
  with its line in the PR). It logs `reclaim (<why>): C: a -> b GB free;
  Ubuntu c -> d GB free; fstrim: <its line>`. A failed trim is said, not
  raised.
- **The floor** (`SPACE_FLOOR_GB`, 50 GB on C: and in Ubuntu): no new
  model stage, and no model-free run, below it, or when a disk cannot be
  read. Below a floor it reclaims first. If it is still below, it holds
  the stage: the label stays, a `<!-- fleet-space:` comment says why, and
  `needs-hands` is added. No due rule reads that comment, so taking
  `needs-hands` off lets the held stage run. An Engineer held before its
  model-free run keeps its run (`why: space`), and that run goes again on
  the same commit, as section 10's does.
- **`dispatcher.py reclaim`** prints the line a hand close-out's handoff
  records (closeout skill, step 9). Only `main` gives a `Fleet` its disks
  and the trim, so no test reads a real disk or runs sudo.

## The change log's three newest entries

- **2026-10-22, `fleet` joins the procedure folders.** The check it named
  is the folder's own tests (`tests/test_phase387_fleet_contract.py`); the
  table row is text. This phase adds a module and a CLI verb to that
  folder; the row still describes it, and the CHANGELOG records the change.
- **2026-10-20, rule 6: plain English to the operator.** No check: the
  entry says "Text only; no check holds it." The stop comments a resume
  posts, and the whole-Ubuntu paste block, are written to it.
- **2026-10-19, live is on the home desktop.** The check it became:
  `tests/test_phase382_live_location.py`. No rank and no resume reads
  live; the journal lives in the fleet's state directory.

## Rule-1 stops anticipated

- **A login or a credential:** none needed. The restart is a SIGTERM to
  the operator's own process (section 8). If the operator wants the
  literal `systemctl restart`, a sudoers line for this one unit (as
  `motodiag-api.service` has) is theirs to add; the proofs do not wait.
- **A test that cannot be made green:** none expected; if a resume
  behaves differently live than on stand-ins, it is a bug fix here.
- **A live-database change:** none; no rank reads live.
- **A threshold or a rule's definition:** none; `KEEP_RUNS`, the 70%
  gates and the sweep stay as they are.
- **A fork:** none seen at Step 0.

*As built:* one stop, a threshold. The free-space floor and the reclaim
timer were the operator's numbers to set; asked and answered ("50 GB on
each", "every 3 hours"). Two pre-approvals were used, each as worded:
(b), the test floor for this phase's own tests, three times; and (c), a
service restart for a planted proof in a gap with no #14 stage running,
for every cut. Pre-approval (a) ("until the machine user exists") ended
at 22:25, when the operator created `kubanjazefleet`'s file. From then
the dispatcher pushes as that account.

## Tests

- `tests/test_phase390_journal.py`: the journal is written before the
  clone; each step and call recorded; atomic writes; `ended` only at the
  end and never on a pause; the replay (a finished call returns its output
  and is not recorded twice in the ledger; the cut call gets `--resume`
  with the transcript's id; no transcript runs fresh; a changed command
  ends the replay); checks cached by commit.
- `tests/test_phase390_resume.py`: for **every kill point in Step 0's
  tables**, a stage on 389's stand-ins (a real git mirror, `gh` and the
  fence stood in) is killed at that point (a `BaseException` the stages do
  not catch, raised by the stand-in), a new `Fleet` over the same state
  directory runs `recover()`, and the issue reaches the stage's next label
  with every GitHub write made exactly once.
- `tests/test_phase390_kill.py`: a real dispatcher process on stand-ins,
  SIGKILLed while its stand-in model call sleeps, then a second process
  started: the stage resumes and finishes (F219's "a test kills a stage
  half way and restarts the dispatcher").
- `tests/test_phase390_search.py`: the marker search: an open marker with
  a journal is resumed, one without gets one stop comment and only one;
  each end form closes a marker; a flow label after it closes it; #14's
  real comments and label events (captured read-only into
  `fixtures/resume/`) give nothing to do; the paused run is skipped;
  a closed, operator-held or no-longer-🚧 issue is abandoned with a log
  line; `--dry-run` writes nothing; the pause kept until its stage ends;
  `prune_runs` keeps an unfinished run and removes a finished one.
- 388's and 389's dispatcher tests updated where markers gained ` run=`
  and every rank its `started` marker (the phase log lists each).
- `390_mutate.py`: each mutation red.

*As built:* 118 tests in five files.
- **No `test_phase390_journal.py`.** The journal's tests sit in
  `test_phase390_resume_contract.py` (39): the known-bad journals in
  `fixtures/resume/bad/`, the kill-point list in
  `fixtures/resume/kill_points.json` (each point names its tests), and the
  journal outside the fence.
- `test_phase390_resume.py` (38): every kill point; the held run and the
  recheck; the pause; the prune with `KEEP_RUNS=1` and a control.
- `test_phase390_search.py` (20): #14's real history at 15:34, 15:50 and
  20:33, from `fixtures/resume/issue14_*_1633`; the held #14 recheck due;
  the dry run; the abandon cases; the start order; the ledger; markers
  named by run; the summary line.
- `test_phase390_kill.py` (1), with `tests/support/fleet_kill_driver.py`:
  a real SIGKILL, then a second process.
- `test_phase390_space.py` (20): section 11.
- 388's dispatcher tests: one built from a journal, and the fixture plants
  a missing fleet identity (bug fix #1).

## Non-goals

- The Quartermaster: the next phase (its row is the planted mission's
  deliverable, row 391).
- Resuming a stage on a different machine, or after its run directory was
  deleted by hand: the stop comment says so instead.
- F217 (a digest day skipped while the host was off) and the sweep.
- Changing the unit file, `KillMode`, the restart method, or sudoers.
  *As built:* sudoers gained one line, `fstrim -v /` (section 11). The
  operator installed it, as part of the free space they added.
- #14, PR #15, their labels and the 389A branch: not touched by hand.
- Any path under the data folder, seed content, splits, eval protocols;
  anything under `src/`; live.

## Planned items

- [x] `journal.py`, and `new_run` writing it before the clone
- [x] the replay in the runner: calls, the Engineer's session, checks;
      `rank_call` skips the ledger for a replayed call
- [x] the steps' GitHub checks; ` run=` on every marker; the `started`
      marker for every rank
- [x] `Fleet.recover` and `recover --dry-run`; `run` and `once` call it
      first
- [x] the pause kept until its stage ends; `prune_runs` keeps unfinished
      runs
- [x] tests, fixtures (#14's captured history), 388/389 tests updated;
      `COLLECTED_TEST_FLOOR` raised (pre-approval (b))
- [x] `SKILL.md`, `CHANGELOG.md`; F219 closed in `docs/FOLLOWUPS.md`
- [x] the mutation run
- [x] the dry run on the live state; the service on the new code
- [x] row 390A on `master`; the seven planted proofs; the operator's
      whole-Ubuntu restart
- [x] close-out: `wholetree.sh --full`, the regression of record, the
      handoff, row 390 to ✅
- [x] *added:* the held run and its recheck (section 10); #14's
      `held.json`
- [x] *added:* free space (section 11): the reclaim, the floor, the
      sudoers line, the operator's sparse block; F221 closed

## Deviations

- **Scope added by the operator, twice.**
  - The held run and its recheck (section 10), after F220.
  - Free space phase to phase (section 11), which closes F221; the
    operator: "now it just needs to be written into the method itself".
    The floor and the timer are their numbers.
- **The `started` marker has its own prefix** (section 4). With the
  dispatcher's prefix, the XO's due rule read it.
- **A call's journal key leaves the prompt out** (section 2). A prompt can
  read what its own stage already wrote.
- **A stop on an open marker only when no stage is due** (section 5).
  #14's 15:50 history broke the flow-label rule.
- **One summary line per search on start** (section 5).
- **The restart is a SIGTERM to the unit's main process**, as section 8
  planned, never a literal `systemctl restart`: lilcu has no password-free
  systemctl for this unit.
- **The whole-Ubuntu restart was not the planned paste block.** C: filled
  at 19:02, and Ubuntu's disk went read-only until 19:55. The operator
  freed 200 GB and ran the restart. The service came back by itself and
  resumed #19's Engineer from its session; that stage reached
  `review:open` at 21:56. The operator counted it as the proof. The check
  script's first version (`390_ubuntu_check.py`) waited for a line that
  comes only at the stage's end; it was fixed, and re-run with ALL GOOD.
- **The Red Team was cut twice, with a control.** #21's resumed refute
  stopped on the refute checklist (C7), and the label stayed. #22, with no
  restart, passed. #23, resumed, passed and reached `build:open`. #21's
  miss is taken as the model's own: the same path passed on #23.
- **Planted issues** are #16 to #19 and #21 to #24 (PR #20 is the
  Engineer's), not one issue per rank as written. #18 was reopened for
  the revision round, so that #19 had an approved plan. #22 is the
  control. Every one is closed.
- **The service clone was moved forward to the branch tip** with each
  pushed change that the proofs needed (`ea1f8d1`, `3ad9dc3`, `b62e447`,
  `f681617`). A move took effect only at the next proof's restart.
- **F220 filed** (my test runs overlapped #14's model-free run, and it
  timed out). From then on, no test ran while a fleet model-free run was
  going, per the operator's rule.
- **Two bug fixes:** 388's fixture read the real fleet identity, and the
  digest's resume line said "(issue None)".
- **Guard blocks, all recorded in the log:** two commit-and-push
  commands, two `sed -i` and one `>>` into tests, and the push guard's
  fast run catching bug fix #1's two tests. No guard was changed.
- **Two misses in my own steps, recorded:**
  - a merge commit (`67735e2`) was made before its whole-tree run (it
    passed right after);
  - a proof script was started by mistake for issue 0 and killed within
    seconds, before it could act.
- **The sparse block's last check was wrong.** It waited for the fleet's
  own timer reclaim, which is not due until about 01:46. The fleet's
  reclaim is proven by that timer line instead (Results).

## Results

None at v1.0; v1.1 records the regression line, the mutation count and
each proof.
