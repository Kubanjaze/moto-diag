# Phase 390 — The fleet resumes where it left off

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-10-25

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
3. **A stage that cannot be resumed** (its resume raises `Stop`, or any
   other error) gets the same stop comment with the reason, its journal is
   ended `stopped`, and the label stays. An error with no issue (the
   digest) is logged.

`dispatcher.py recover --dry-run` prints what the search would do and
writes nothing: no lock, no comment, no label, no journal. It is run on
the live state before the code goes live (the fleet's rule since 389).

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

## Non-goals

- The Quartermaster: the next phase (its row is the planted mission's
  deliverable, row 391).
- Resuming a stage on a different machine, or after its run directory was
  deleted by hand: the stop comment says so instead.
- F217 (a digest day skipped while the host was off) and the sweep.
- Changing the unit file, `KillMode`, the restart method, or sudoers.
- #14, PR #15, their labels and the 389A branch: not touched by hand.
- Any path under the data folder, seed content, splits, eval protocols;
  anything under `src/`; live.

## Planned items

- [ ] `journal.py`, and `new_run` writing it before the clone
- [ ] the replay in the runner: calls, the Engineer's session, checks;
      `rank_call` skips the ledger for a replayed call
- [ ] the steps' GitHub checks; ` run=` on every marker; the `started`
      marker for every rank
- [ ] `Fleet.recover` and `recover --dry-run`; `run` and `once` call it
      first
- [ ] the pause kept until its stage ends; `prune_runs` keeps unfinished
      runs
- [ ] tests, fixtures (#14's captured history), 388/389 tests updated;
      `COLLECTED_TEST_FLOOR` raised (pre-approval (b))
- [ ] `SKILL.md`, `CHANGELOG.md`; F219 closed in `docs/FOLLOWUPS.md`
- [ ] the mutation run
- [ ] the dry run on the live state; the service on the new code
- [ ] row 390A on `master`; the seven planted proofs; the operator's
      whole-Ubuntu restart
- [ ] close-out: `wholetree.sh --full`, the regression of record, the
      handoff, row 390 to ✅

## Deviations

None at v1.0; v1.1 lists each.

## Results

None at v1.0; v1.1 records the regression line, the mutation count and
each proof.
