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

## 2026-10-25 — mutations, and the floor

- `390_mutate.py`, first run: 29/33 red. Four survived, and each was a
  gap in the tests: P3 and P4 (my prune tests set `KEEP_RUNS = 0`, and
  `runs[:-0]` is empty, so they removed nothing whatever the code did);
  P1 (no test of a resumed stage pausing again); H4 (no test of an old
  hold once the issue has moved on). Fixed: the prune tests use
  `KEEP_RUNS = 1` with a control run that must go; two new tests. Also
  J5's assertion added (the resumed Step 0 dated by its stage's start).
  Second run, recorded in `390_mutate.out`: **33/33 red**, the source
  restored (`git status` clean under `.claude/`).
- `COLLECTED_TEST_FLOOR` 11402 → 11499 (pre-approval (b)): `master` at
  `6f32013` collects 11402, the branch 11499; the four new files collect
  38 + 19 + 39 + 1 = 97; 388's dispatcher tests 52 functions before and
  after.
- Before each run above, `dispatcher.log`'s last line read: 16:29:02
  "issue 14: checks failed", no fleet run in progress (F220's rule).

## 2026-10-25 — row 390A; the service on 390's code

- **Row 390A, 🚧, on `master`** (`9f0bd7b`, 57 words, `roadmap_check`
  ok, `wholetree.sh` exit 0 before the commit), pushed; `master` merged
  into the branch (`67735e2`) and pushed. **A miss, recorded:** the merge
  commit was made before its own `wholetree.sh` run; run straight after,
  on `67735e2`: exit 0 (2182 passed). Its content was the branch plus the
  one row, each checked on its own side.
- `recover --dry-run` on the live state with the final code: "nothing to
  resume", exit 0.
- **The service on the phase branch, in a gap** (pre-approval (c)): the
  last stage line 16:29:02, the unit's cgroup holding only the dispatcher
  (PID 203, no child). Its clone `~/motodiag/fleet/code` switched to
  `phase-390-resume` at `67735e2`; SIGTERM to PID 203 at 17:22:01 (no
  sudo for this unit, as in 389); `Restart=always` brought it back at
  17:22:31 (`NRestarts=1`, PID 2463289). Its first cycle: issues 10 and 9
  skipped (closed phases), #14 left alone (`needs-admiral`).
- **Seen in that start:** a start with nothing to resume logged nothing,
  so the log could not show the search had run. Added: one summary line
  per start ("the search on start: nothing to resume", or "N stage(s)
  acted on"), and its test; `COLLECTED_TEST_FLOOR` 11499 → 11500.

## 2026-10-25 — proof 1: the Science Officer (#16)

`390_proof.py scout 16 --close`. Issue #16 opened 17:2x with `mission`
(planted, the trial marker, branch `phase-390A-quartermaster-row`). The
stage began 17:32:35 (`runs/20261025_173233_scout_390A`); the service was
restarted at 17:32:42 (SIGTERM to PID 2619082) and back at 17:33:14 (PID
2621609): "resume scout from 20261025_173233_scout_390A (issue 16), after
started, clone". #16 closed by the planter at 17:33:16, while the resumed
stage ran. The stage pushed Step 0 at 17:35:18 (`9ad3bc3`, the branch's
one commit past `master`), commented, and set `step0:done` at 17:35:22;
"the search on start: 1 stage(s) acted on". #16's comments: one
`fleet-started`, the planter's close, one `fleet-scout: step0` marker.
Journal ended `step 0 pushed on phase-390A-quartermaster-row`.

**What the cut was, read from the journal:** between the stage's two
model calls, not inside one. Call 0 (session `c0e71e03`) had ended and
been recorded (its transcript last written 17:32:41); call 1 had not
begun. Resumed, call 0 was replayed, not made again, and call 1 ran fresh
(`99b6d566`, its `known` holding only `c0e71e03`): two transcripts in
the run. The proof script's cut test ("a transcript exists") fired on the
finished call's transcript; it now waits for the journal's latest call
to be unfinished with its own transcript, and checks again just before
the restart.

## 2026-10-25 — proof 2: the Captain, v1.0 (#17)

`390_proof.py captain 17 --close`; #17 opened with `mission` and
`step0:done`. The stage began 17:40:34 (`runs/20261025_174033_captain_390A`);
cut **inside its Fable call** at 17:40:39 (the journal's call 0
unfinished, its transcript `b3b110b8` there), SIGTERM to PID 2621609; back
at 17:41:11 (PID 2637284): "resume captain from 20261025_174033_captain_390A
(issue 17), after started, clone, session
b3b110b8-9eea-421e-962c-38dccad6c7f6". #17 closed by the planter 17:41:13.
The resumed call went on in that session: the run holds one transcript,
`b3b110b8….jsonl`, and the journal one call, done, session `b3b110b8`.
v1.0 pushed at 17:47:13 (`4123dfa`), marker and `plan:needs-review` at
17:47:16. #17's comments: one `fleet-started`, the close, one
`fleet-captain: v1.0 round=0 commit=4123dfa0e53d`. Journal ended "Phase
390A v1.0: the plan", steps started, clone, commit, push, marker, label.

## 2026-10-25 — proof 3: the Executive Officer (#18)

`390_proof.py xo 18 --close`; #18 opened with `mission` and
`plan:needs-review`. The stage began 17:52:27
(`runs/20261025_175225_xo_390A`); cut **inside its Fable call** at
17:52:33 (SIGTERM to PID 2637284); back at 17:53:04 (PID 2650947):
"resume xo from 20261025_175225_xo_390A (issue 18), after started, clone,
session e7286c05-5ff0-461e-8118-6989dfa21f2e". #18 closed 17:53:07. The
resumed call went on in that session (one transcript, `e7286c05….jsonl`;
the journal's one call done in it); the verdict, `back-to-captain` round
1, commented once and applied at 17:57:26 (`plan:needs-review`, the
XO's own label for a back). #18's comments: one `fleet-started`, the
close, one `xo-verdict`. Journal ended "verdict applied".

The XO's two items were real (`verify_phase.sh`'s arguments and its
post-merge place; the root `implementation.md` row count). The Engineer's
proof needs an approved plan, so #18 was reopened at 17:57:58 for the
Captain's revision and the XO's next round, with no restart, and is
closed again by the planter when the XO approves.
- The revision round on #18, no restart: the Captain's revision 18:02:39
  to 18:05:48; the XO, round 2, 18:10:55 to 18:14:20: **approve**
  (`plan:approved`); #18 closed by the planter at 18:14:23, before the
  next cycle. The branch at `e274426`.

## 2026-10-25 — proof 4, cut 1: the Chief Engineer's session (#19)

`390_proof.py engineer 19`; #19 opened 18:1x with `mission` and
`plan:approved`. The stage began 18:19:29
(`runs/20261025_181926_engineer_390A`); cut **inside its session** at
18:19:33 (SIGTERM to PID 2650947); back at 18:20:04 (PID 2667175):
"resume engineer from 20261025_181926_engineer_390A (issue 19), after
started, clone, label-build, session 8fe99d8e-d20d-4ee7-a4fd-600a84f046f9".
The running session's command line (`/proc/<pid>/cmdline`) carries
`--resume 8fe99d8e-…` and `engineer.CONTINUE`; one transcript in the run.

**The whole-Ubuntu restart handed to the operator** (18:3x), safe while no
#14 stage runs (#14 on `needs-admiral`), timed for #19's Engineer: its
session, then its model-free run, are the longest stretch of a stage. The
check is `390_ubuntu_check.py`, run from this checkout (not committed yet:
the Engineer was running its own pytest inside its session, so no
`wholetree.sh` here, F220). Tried read-only first: it reads the boot time,
the service, and the log lines after the boot, exit 0.

## 2026-10-25 — C: full, Ubuntu read-only, and the whole-Ubuntu proof

The operator: "continue. While I was out, C: filled at 19:02; Ubuntu's
disk (131 GB vhdx) could not grow and went read-only until 19:55, the
dispatcher crash-looping (Errno 30). I freed 200 GB and your Ubuntu-restart
block ran at 19:55: ext4 recovered (85 orphan inodes deleted), the service
came back with 0 restarts and resumed #19's Engineer at 19:55:27 from its
18:20 session. Check your three uncommitted phase files and #19's run
folder for damage, record what your check script printed, and count this
as the whole-Ubuntu proof if it holds. File a finding: the fleet has no
disk-space guard, and its run folders grew the vhdx until the host ran
out; no new stage should start below a free-space floor on C: and in
Ubuntu. Then carry on with the proofs, keeping the rule: no test runs
while a fleet model-free run is going."

- **The three uncommitted files, no damage:** `390_phase_log.md` (301
  lines, every section through the hand-over), `390_proof.py` (150),
  `390_ubuntu_check.py` (74): no NUL byte (`tr -cd '\000' | wc -c`: 0),
  valid UTF-8 (`iconv`), both scripts compile, each ends where it was
  written; `git fsck` of this repository clean.
- **#19's run folder, no damage:** `stage.json` reads (unfinished: steps
  started, clone, label-build; one call, session `8fe99d8e`, not done);
  the clone's `git fsck` clean, its tree clean, the Engineer's two commits
  from before 19:02 there (`95a127b` row 391, `44f846d` the phase log);
  the transcript's 233 lines all JSON. #19 on GitHub: one comment (its
  `started` marker), `build:open`: nothing written twice by the crash
  loop, which could not write its journal past the first save.
- **The record of the outage:** `dispatcher.log` has no line from 18:20:04
  to 19:55:27, and the previous boot's system journal ends at 19:02:02, so
  the crash loop is on record only in the operator's words. That boot's
  six service restarts (counter to 6) are this session's: 17:22, 17:27,
  17:33, 17:41, 17:53, 18:20. This boot: "EXT4-fs (sdd): 85 orphan inodes
  deleted", "recovery complete", 19:55:25.
- **The whole-Ubuntu proof holds:** Ubuntu started 19:55:19
  (`uptime -s`); the service up by itself 19:55:25 (`NRestarts=0`); "resume
  engineer from 20261025_181926_engineer_390A (issue 19), after started,
  clone, label-build, session 8fe99d8e-d20d-4ee7-a4fd-600a84f046f9" at
  19:55:27; the running session's command line carries `--resume`. Not a
  clean shutdown: the disk had been read-only since 19:02. It completes
  when #19 reaches `review:open`.
- **What the check script printed in the operator's window is not known
  here, and my script was wrong.** As handed over, it waited for both the
  resume line and the search's summary line, and the summary is written
  only when the resumed stage ends, an hour or more for an Engineer. Run
  mid-build it could only wait five minutes and print "SOMETHING IS OFF:
  no stage was picked up after the restart", which would be false. Re-run
  here with a 90-second limit it timed out (exit 124, its output
  buffered). Fixed: the resume line alone is the proof, the summary shown
  if there; output flushed. Re-run at 20:0x:

      Ubuntu started at:           19:55:19
      the fleet's service:         running since Sun 2026-10-25 19:55:25 EDT
      what it picked up:           resume engineer from 20261025_181926_engineer_390A (issue 19), after started, clone, label-build, session 8fe99d8e-d20d-4ee7-a4fd-600a84f046f9
      its search on start:         still working on what it picked up
      ALL GOOD: the fleet came back by itself and picked up the stage it was in the middle of

- **Filed F221** (`next_f_number.sh`: F221): no disk-space guard. Measured:
  the fleet's state 31 GB, 29.0 GB of it pytest's temporary folders in 21
  run folders (`run/tmp`); 8.7 GB for one model-free full run, 11.6 GB in
  #19's running Engineer stage; code under 0.1 GB a run. The floors are
  the operator's (a threshold, rule 1); not built in 390.
  `finding_check.py` exit 0.
- C: 197 GB free, Ubuntu 912 GB free, at 20:0x.

### 2026-10-25 21:07 — proof 4's second cut: inside the Engineer's model-free run

- `390_proof.py engineer 19 --at check --close`: the cut point was reached in
  `20261025_181926_engineer_390A` at 21:07:35, with the session done and the
  model-free run started at 21:07:29 on `f987bf313087`. SIGTERM went to
  PID 203, and the service was back as PID 64882 at 21:08:07: "resume
  engineer from 20261025_181926_engineer_390A (issue 19), after started,
  clone, label-build", then "the model-free run on f987bf313087", the same
  commit. #19 was closed at 21:08:09. ALL GOOD. The push, the PR and
  `review:open` are still to be confirmed when the run ends.

### 2026-10-25 21:15 — F221 is bigger than the guard (the operator)

- The operator: Ubuntu uses 44 GB, but `ext4.vhdx` grew from 131 to 164 GB
  after 19:55 (C: 205 -> 175 GB free), about 25 GB an hour during
  regressions, because freed blocks are never returned. Added to F221 with
  what I measured at 21:20:
  - the image is 163.9 GB and not sparse;
  - root is mounted with `discard`;
  - WSL 3.0.3.0 offers `--manage --set-sparse` and calls it "currently
    experimental";
  - `Optimize-VHD` is installed.
  `finding_check.py .` exit 0.
- **The operator's decision, verbatim:** "it's just something that needs
  to be done frequently to free up the claimed space, now it just needs to
  be written into the method itself. as a part of the overall process
  phase to phase". So 390 closes F221 too, in the method. Scope added by
  the operator; it goes in v1.1's Deviations.
- **What I decided, and why:**
  - **The privilege** is one sudoers line for `fstrim -v /`
    (`ops/desktop/install_fstrim_sudoers.sh`, the shape of 382's
    `install_sudoers.sh`), not systemd's `fstrim.timer`. The dispatcher has
    to trim at its own boundaries, and starting a system unit as lilcu
    would need a polkit rule, which is wider. `fstrim.timer` is enabled
    here but never scheduled (`systemctl list-timers` shows it with no
    next run).
  - **A model cannot use the line:** `bwrap --dev-bind / / grep NoNewPrivs
    /proc/self/status` prints `NoNewPrivs: 1` (outside the fence, 0).
  - lilcu already has sudo with a password (`(ALL : ALL) ALL`), so
    `sudo -n -l <cmd>` passes before the rule exists. The paste block
    checks for the NOPASSWD line itself; checked negative now, before the
    rule.
  - **Only `main()` sets up the disks and the trim.** The test fakes pass
    unknown commands to the real `subprocess.run`, so a default would run
    sudo from the tests.
  - **A hold for space has its own marker**, `<!-- fleet-space:`, read by
    no due rule: taking `needs-hands` off makes the held stage due again.
    An Engineer held before its model-free run keeps its run
    (`why: space`), and that run goes again on the same commit. It is due
    only while the hold comment is newer than any rank comment but a
    `started` one, so a recheck that stops does not loop.
  - **The merge boundary** is a row that was 🚧 on master at the last cycle
    and is ✅ now. **The close-out boundary** is after the Engineer's
    model-free run passes, with the line in the PR.
- **The floors and the timer are thresholds** (rule 1). The code carries
  50 GB on each disk and 1 hour as placeholders, and the operator has been
  asked.
- `390_compact_vhdx.ps1` is the operator's one-time paste block. It
  installs the rule, copies the live database to C:, shuts Ubuntu down,
  runs `wsl --manage --set-sparse true` (never `--allow-unsafe`), and
  brings Ubuntu back with the boot task. It then trims and checks that
  both services run, and prints C:'s free space before and after. If WSL
  will not mark the image sparse, it compacts it once with `Optimize-VHD`
  instead and says SOMETHING IS OFF. Its syntax is parsed clean. Only its
  read-only parts were run: the busy check saw the fleet's run.
- No test was run during #19's model-free run.
- **The operator's answers** (21:5x): floor "50 GB on each"; timer "every 3
  hours". `SPACE_FLOOR_GB = {"C:": 50, "Ubuntu": 50}`, `RECLAIM_HOURS = 3.0`.

### 2026-10-25 21:56 — proof 4 done: the Engineer, cut in its model-free run, reached `review:open`

- dispatcher.log: "pushed phase-390A-quartermaster-row at f987bf313087 as
  operator (engineer)" at 21:56:28; "issue 19: PR 20 ready" at 21:56:35;
  "the search on start: 1 stage(s) acted on" at 21:56:36.
- GitHub:
  - #19: closed, labels `mission`, `review:open`; 3 comments, of which 1
    is `pr-ready` and 1 is a started marker;
  - PR #20: open, head `f987bf3130874e806153d0784ecce246b971cbcb`, the
    only PR for the branch;
  - the push line occurs once in dispatcher.log.
- The resumed stage reran only the model-free run, on the same commit, and
  made no second session. **This also completes the whole-Ubuntu proof**:
  the 19:55 restart's resumed Engineer has reached its next label with no
  hand on it.

### 2026-10-25 22:0x — free space built, tested, mutated

- With the fleet idle (no pytest or bwrap process; the last log line is the
  21:56 idle cycle):
  - `tests/test_phase390_space.py`: 20 tests. The first run had 2 red, both
    in the tests: the close-out's own reclaim counted in a trim count, and
    the timer moved to 3 hours. Fixed, then one test added: a recheck that
    falls below the floor again keeps its run held.
  - That file with the 390, 389 and 388 dispatcher files: 224 passed in
    36 s (before the added test).
  - `390_mutate.py F`: 16/16 red.
- `COLLECTED_TEST_FLOOR` 11500 → 11520 (pre-approval (b)): 11520 collected
  against 11500 at `ea1f8d1`, +20 -0, all in `test_phase390_space.py`.
