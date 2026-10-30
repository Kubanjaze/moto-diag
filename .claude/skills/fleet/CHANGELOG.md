# fleet — changelog

## 2026-10-29 — the database step through the fleet (Phase 395, K58, F232)

The operator, 2026-10-29: "add it altogether to throw at it", then "yes go
ahead" to the advisor's reading (K58): the fleet stops at the right point
and hands the operator one paste block for the desktop; that block tries
the change on a copy, shows what changes, applies it and checks it; when
the operator says it is done, the fleet carries on. The prompt is
`docs/prompts/395_the_database_step.txt`; Step 0 is `395_step0.md`.

- **The Engineer's `deploy` outcome** (`engineer.py`): the brief's database
  step, `read_result`, `verify_deploy`, `CLOSEOUT`, `verify_after_apply`,
  `migration_changes`, the fix round's line on an applied migration.
- **The dispatcher** (`engineer_deploy`, `deploy_block`, `fetch_applied`,
  `stage_deployed`, `verify_live_here`; the `deploy` hold in `held_for`;
  `resume`; `STAGE_RANK["deployed"]` and its kill point).
- **Q1** (`quartermaster.database_step`, `live_check`); `NOT_READ["V8"]`.
- **The planners** (`captain.BRIEF`, `xo.BRIEF`): `## The database step`.
- **Fixtures:** `fixtures/deploy/` (the five known-bad cases, the trial's
  output); `fixtures/resume/kill_points.json` gains `deployed`.
- F232 closed. 35/35 mutations red (`395_mutate.out`).

## 2026-10-29 — the code itself gets checked (Phase 393)

The operator, 2026-10-27: "how do i make sure and maintain the quality of
code thats been written leading up to this point ?" (K54, with the
numbers: 85% changed-line coverage, McCabe 20, 100 KB per file, the
ratchet). The prompt is `docs/prompts/393_the_code_itself_gets_checked.txt`;
Step 0 is `393_step0.md`.

- **The Quartermaster's Q10–Q12** (`quartermaster.code_command`,
  `code_result`, `code_checks`; `Fleet.code_findings`): lint and types per
  touched file, changed-line coverage, complexity and size; model-free in
  the fence, with the base's script and rules. `Check.coverage` carries the
  full run's coverage JSON.
- **The Red Team's five questions** (`red_team.QUESTIONS`, `code_scan`,
  `checklist_nos`): `code_checklist` is required; a "no" is a back.
- **The weekly page** (`quality_report.py`, `Fleet.stage_quality`): Monday
  08:00, one pinned issue in the fleet's name, `quality.jsonl`, a digest line
  (`yeoman.facts(quality=…)`).
- `fixtures/code_checks/` (Q10–Q12's known-bad and good trees);
  `fixtures/resume/kill_points.json` gains `quality`.

## 2026-10-28 — a rank's brief on standard input (Phase 394)

The operator, 2026-10-28: "New small phase, on my word: the fleet passes a
rank's brief on standard input." (K55). The prompt is
`docs/prompts/394_the_brief_on_stdin.txt`; Step 0 is `394_step0.md`. PR #34
made the Red Team's brief larger than Linux's 131072-byte limit on one
argument: 69 launch failures and 69 "Red Team started" comments on #31.

- **`rank_call.command`** has no prompt argument; `call` hands the brief to
  `claude -p` on stdin. `FencedRunner` passes it through the fence.
- **The Chief Engineer**: `engineer.session_argv()` and
  `engineer.session_brief()`; the brief is `<run>/session.brief`, opened as
  the session's stdin; resumed, `CONTINUE` is.
- **`rank_call.LaunchFailed(Stop)`**: an `OSError` from a launch stops the
  stage once, label unchanged, instead of failing the cycle every 5 minutes.
- **`started` once per stage run** (`Fleet.failed_start`).
- **`journal.call_key`** keys the old and the new command shapes alike, so a
  stage cut across the upgrade replays.
- Tests: `tests/test_phase394_brief_on_stdin.py` (18), with a stand-in
  `claude` on PATH and the kernel's real limit; 15/15 mutations red.

## 2026-10-27 — the fleet follows the plan of record (Phase 392)

The operator, 2026-10-26: "well the fleet should be reading the plan of
record, how tf is that missed!?" (K44). The prompt is
`docs/prompts/392_the_fleet_follows_the_plan.txt`; Step 0 is
`392_step0.md`; the operator's Step 0 answers are K48–K51, and K52
corrected the list before it merged.

- **`plan_order.py`** (new): the plan of record's "Next, in order" list at
  its top, read exactly (K48); its dated changes; `docs/decisions.md` with
  its new `Covers` column (K50); `bearing`, `brief_block`, `cite_line` for
  a phase; `answer` for a stop; `check` and `check_texts`.
- **Every rank that plans or judges reads the record** (the Science
  Officer, the Captain, the XO, the Red Team, the Quartermaster): its
  brief carries `brief_block`, and what it writes ends with the script's
  `cite_line`. The Science Officer's report has a scripted "The plan of
  record" section.
- **`plan_check` P9 and P10**: a v1.0 must name the entry or K-id that puts
  its phase in order, and a fleet-only phase the first-shop phase it
  unblocks (K43). `BEFORE_THE_RECORD` pins 384, 386 and 387 to what they
  fail. Four known-bad cases.
- **The next mission** (`stage_next`): the plan's next entry gets its
  issue in the fleet's name, the operator's question when the plan says it
  needs them, and a one-row pull request the operator merges by hand (K49:
  "the fleet never pushes to master"). The push gate's new rank `row` may
  change the phase's ROADMAP status and nothing else.
  `dispatcher.py next --dry-run` says what the next cycle would do.
- **Answered stops** (`answer_stop`): an Engineer stop of kind
  `third-bug-fix` or `guard-blocked-twice` that one K-id's `Covers` names
  for this phase is answered with that K-id's words, verbatim, once. A
  rule-1 stop never is.
- **F223**: a marker counts only from the fleet's account, or the
  operator's on a trial issue; an issue only from those two
  (`fleet_git.trusted_authors`, `from_trusted`, `opened_by_trusted`).
- **F226**: a finished stage's `run/tmp` is deleted (`clean_tmp`), the
  worker-loss folders kept; held, paused and unfinished runs keep theirs.
  The reclaim line says when nothing came back to Windows (K45).
- **F225**: `CHECK_TIMEOUT_S` 5400 (K51); a run past it has its process
  group killed and is a failed check, one stop (`run_group`).
- **F227**: the unit's `LimitNOFILE=1048576` (K51); the contract's `nofile`
  rule.
- **F228**: the Red Team's brief states C7; the dispatcher files the one
  finding open wording defects go to, and G3 lets `red-team-record` add to
  `docs/FOLLOWUPS.md` and nothing more. `fixtures/red_team/14_round3.json`
  is #14's round-3 output, the known-bad case.

## 2026-10-26 — the Quartermaster, in shadow (Phase 391)

Step 8 of `docs/reports/2026-10-22_fleet_proposal.md`. The prompt is
`docs/prompts/391_quartermaster.txt`; Step 0 is `391_step0.md`.

- **`quartermaster.py`**: Q1–Q9 and one fresh read-only Opus call. Scripts
  run the checks: `wholetree.sh --full`, `regression.sh` and
  `verify_phase.sh` in the fence with no model; the module reads
  `verify_phase.sh` section by section (V1–V14), never by its exit code,
  and adds what the fourteen miss for a fleet-built PR: the scope, the
  Captain's word and the Red Team's clear, the counts, the commit claims,
  the stub rule over v1.1, the handoff (and R1–R8 on the branch), and a
  clean merge onto master. The script composes the verdict: a scripted
  failure refuses whatever the model says, and a model refusal must name a
  listed check.
- **`stage_quartermaster`** in the dispatcher, on `merge:needs-review`,
  journaled and resumable, under the free-space floor. Its verdict goes on
  the PR, on the issue (`<!-- fleet-quartermaster: verdict=… -->`) and in
  `quartermaster.jsonl`. It merges nothing and moves no label.
- **`quartermaster_since`** in `state.json`: only a label applied after the
  Quartermaster first came up on the machine is judged.
- **The digest** gains "The Quartermaster (shadow)": each verdict beside
  what became of its PR.
- **`Check.out`**: a command run keeps its whole output, in the journal too.
- **Fixtures**: `fixtures/quartermaster/pr20/`, the Step 0 dry run on PR
  #20 (the fence's `verify_phase.sh` output, the context, the model's
  answer, the brief as drafted); `fixtures/resume/kill_points.json` gains
  the stage's four kill points.

Measured at Step 0: one call on PR #20 read 61,300 tokens and wrote 1,093,
in 3 turns and 11 s ($0.28 at list price). Its verdict was refuse, as the
operator ruled, but it named checks of its own; the brief now lists them.

## 2026-10-25 — a stage a restart cuts off is resumed (Phase 390)

Closes F219. The prompt is `docs/prompts/390_resume.txt`; Step 0 is
`390_step0.md`, every kill point and what it left.

- **`journal.py`** (new): `runs/<run>/stage.json`, outside the fence,
  written before the clone and after each step.
- **`dispatcher.py`**: every stage on steps that check GitHub before each
  write when resumed; the runner's replay (calls, the Engineer's session,
  model-free runs); `recover()` before the first cycle, and
  `recover --dry-run`; a `fleet-started` marker for every rank; ` run=` on
  every marker; `paused` kept until its stage ends; `prune_runs` keeps
  unfinished runs and unreadable journals. The runner's `resume=` argument
  is gone: the session comes from the journal.
- **A held run and the recheck** (the operator, 2026-10-25, after F220): an
  Engineer stop whose only failure is the model-free run holds its run
  (`journal.hold`, `held.json`); taking `needs-admiral` off runs it again on
  the same commit (`stage_recheck`) and goes on to the push and the Red
  Team. `prune_runs` keeps held runs.
- **`rank_call.py`**: a replayed call is not recorded in the ledger again.
- **`engineer.py`**: `CONTINUE`, the resumed session's prompt, for a
  restart as well as a usage limit.
- **Fixtures**: `fixtures/resume/kill_points.json` (hand-written, Step 0's
  kill points, each naming its test), `fixtures/resume/bad/` (a truncated
  journal), `fixtures/resume/issue14_*_1633` (#14's comments and label
  events, read from GitHub).
- **Decided**: the `started` marker has its own prefix (with the
  dispatcher's, the XO's due rule read it as the Captain's comment); a
  call's journal key leaves the prompt out (a prompt can read what its
  stage already wrote); a stop on an open marker only when no stage is due
  (#14's 15:50, where the operator's re-applied `review:open` made the Red
  Team due).
- **Free space, phase to phase** (F221; scope added by the operator,
  2026-10-25): `Fleet.reclaim` (fstrim through
  `ops/desktop/install_fstrim_sudoers.sh`'s one line) on a timer, at each
  merge and at each close-out, logged with the free space on C: and in
  Ubuntu; `SPACE_FLOOR_GB`, below which no new model stage or model-free run
  starts (reclaim first, then hold: label unchanged, a `fleet-space`
  comment, `needs-hands`); an Engineer held before its model-free run keeps
  its run for the same commit; `dispatcher.py reclaim`. Tests:
  `tests/test_phase390_space.py`.

## 2026-10-25 — the ranks that write: Science Officer, Captain, Engineer, Red Team (Phase 389)

Steps 6 and 7 of `docs/reports/2026-10-22_fleet_proposal.md`. The prompt is
`docs/prompts/389_captain_engineer.txt`; Step 0 is `389_step0.md`.

- **`scout.py`** (Haiku, K42), **`captain.py`** (Fable), **`engineer.py`**
  (Opus), **`red_team.py`** (Opus, fresh): each a script around fenced
  calls; every label moved by the dispatcher from a checked result.
- **`fleet_git.py`**: the push gate G1–G6, run outside any session because
  the push guard is a hook; the push identity (the fleet's machine user, or
  the operator's login for a planted trial only).
- **`fence.sh`**: the token on a pipe (`--token-fd`), never the environment
  (measured: in the environment a Bash tool could read it from three
  processes' `/proc/<pid>/environ`); `--venv` and `--mobile`.
- **`dispatcher.py`**: the four stages and their resumes, the model-free
  check run, the Fable gate, closed phases and operator-held issues left
  alone, the Engineer's watched session.
- **`rank_call.py`**: `tools=`, and `NO_TOOLS` for one-turn calls.
- **Fixtures**: `fixtures/push_gate/cases.json` (hand-written known-bad
  pushes, one G-id each), `fixtures/scout/` (hand-written replies, the
  known-bad ones named in its README), `fixtures/dispatcher/usage_fable_at_ceiling.txt`.
- **Decided**: for a repository file, a refute table's page is the line
  number (C4 asks for a page; a text file has none).

Not done here, and why: the master ruleset (F214's other half) changes who
may push to `master`, the operator's call; the push gate refuses `master`
meanwhile.

## 2026-10-22 — the fence on Linux and the dispatcher (Phase 388)

Steps 4 and 5 of `docs/reports/2026-10-22_fleet_proposal.md`, built on the
home desktop, the fleet's host from now on. The prompt is
`docs/prompts/388_fleet_host.txt`; Step 0 is `388_step0.md`.

- **`fence.sh`** and **`fence_net.py`**: one stage under bubblewrap, the
  clone and run directory writable, no `/home`, the rest read-only, the
  environment from nothing, the network the model API only. The
  `workspace-docs` import resolves inside: bound at the clone's sibling
  path, and the approval seeded for the fence's clone path (measured: a
  fresh clone at a new path runs with no workspace rules even with the
  sibling present). Closes F215's read confinement on this machine.
- **`dispatcher.py`**: the Executive Officer on `plan:needs-review`, the
  daily digest, the 24-hour sweep, the rate-limit pause and `--resume`, the
  70% Opus ceiling, one process by `flock`. 387's scripts are called as they
  are, with a `run=` that sends `claude` through the fence.
- **Fixtures**: `fixtures/dispatcher/` (the measured `/usage` text and
  hand-written known-bad ones; `README.md` says which is which);
  `fixtures/service/cases.json` (ten known-bad units, one rule each).
- **The service**: `ops/desktop/motodiag-fleet.service`,
  `install_fleet_unit.sh`, `motodiag-fleet-boot.xml`, installed by the
  operator.

Measured at Step 0: `claude -p "/usage"` prints the 5-hour and weekly
figures in print mode at no cost, so no ceiling file is needed.

## 2026-10-22 — created (Phase 387)

Steps 2 and 3 of `docs/reports/2026-10-22_fleet_proposal.md`: the
Executive Officer and the Yeoman, both read-only. The prompt is
`docs/prompts/387_xo_and_yeoman.txt`.

- **`plan_check.py`**: the checklist, P1–P8, no model. Reuses
  `roadmap_check.rows`/`ACTIVE` and `wholetree.CONTENT_PATHS`. `--rev`
  reads a plan as its commit held it. A good tree and 21 hand-written
  known-bad cases (`fixtures/bad/cases.json`), one edit each, each failing
  on its own item and no other.
- **The pin** (K41, the operator: "Pin them (Recommended)"): 384 and 386's
  v1.0 are not held to P4, P7 and P8, which they predate. Without it each
  fails on exactly its pinned items; the test holds that equality.
- **`xo.py`**: the checklist, then one read-only Fable call with a fixed
  verdict schema; the label set by the script; two back-to-captain rounds;
  a stop leaves the label.
- **`yeoman.py`**: `decide` (K40 and K41 were its first rows) and
  `digest`.
- **`rank_call.py`**: the fence and the stops, shared by the two ranks.
- **`fence_probe.py`**: the planted Bash call and its control.
- **`labels.py`**: the eleven labels, made 2026-10-22 under the operator's
  login (K40).

Measured at Step 0 (`387_step0.md`): `claude -p` serves
`claude-fable-5-1`, `claude-opus-5-5` and `claude-haiku-5-5` on this
login; one XO call on 386's v1.0 read 148,263 tokens (input, cache write
and cache read) and wrote 7,347, in 11 turns and 100 s.
