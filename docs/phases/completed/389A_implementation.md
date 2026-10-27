# Phase 389A — 385's ROADMAP row

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-10-25 (v1.0 `f13d170`)

v1.1, written by the Chief Engineer after the build: every section updated to
what shipped (each change marked "As built"), the planned items ticked, and
Deviations and Results added. The one change of substance: the regression run
in the stage clone **was of record** (389's "Sandbox counts", which closed
after this plan was written), so the close-out was done on the branch rather
than handed to the operator on the Mac. The Tests section foresaw this case.

Written by the Captain from `docs/phases/in_progress/389A_step0.md`
(classification: extension), the ROADMAP row 389A and the mission prompt
`docs/prompts/389A_385_s_roadmap_row.txt`. The Executive Officer checks this
document before any work; the Chief Engineer builds to it and writes v1.1.
This revision answers the Executive Officer's items on the first two drafts:
the review stage that does not exist in this trial (Logic, section 5), the
shape of the ROADMAP diff (section 1's finish line), the phase log's own
commit (section 3's finish line), the draft row's word count (section 1), and
the ref the diff is taken against. The first draft diffed against `master`,
which does not resolve in the stage clone: `dispatcher.py` makes
that clone with `git clone --branch <branch> <mirror>`, so the clone's only
local head is the phase branch and `master` exists there only as
`refs/remotes/origin/master` (at `6adffc5` in this fence's clone, the commit
that added row 389A). Every diff in this plan is now against
`origin/master`, and the phase log records the hash that ref resolved to when
the diff was taken, since the mirror is refreshed before each stage.

---

## Goal

Phase 385, "the push token's own write", has a committed prompt
(`docs/prompts/385_the_push_tokens_own_write.txt`), an operator decision
(K39 in `docs/decisions.md`, 2026-10-21) and the finding it will close (F212
in `docs/FOLLOWUPS.md`), but no row in `docs/ROADMAP.md`. The Step 0 census
searched the docs folder for `| 385 |` and found nothing, so the gap is real.

This phase adds that one row, after 384's, status 🔲, naming the prompt and
F212. It is docs only: nothing under `src/`, nothing under `tests/`, no
migration, nothing on live. It is also the fleet's first trial mission, run by
the dispatcher from Step 0 to the Captain's merge recommendation, under the
operator's login as Phase 389's pre-approval (b) allows. The operator merges
by hand.

The one deliverable is the row. Everything else in this document is the
record a phase leaves behind so the ledger, the checks and the next session
agree about what happened.

## Logic

### 1. `docs/ROADMAP.md`: row 385

One new table row, inserted directly after row 384 (today line 661) and
before row 386. The ROADMAP's rows from 353 on sit in numeric order in the
Track T table, and 385 belongs between 384 and 386.

The row's facts, which are the contract (the Engineer may tighten the
wording, never the facts):

- status 🔲, the status key's "not started", because Phase 385 has not begun;
- the title "The push token's own write";
- what 385 will do: `device_tokens.last_seen_at` joins `SERVER_WRITES`, the
  set-aside list Phase 383 built, with 383's three controls each seen failing
  (another column of that row, an added token row, the same column in another
  table), and the live check `verify_phase.sh 384` passes again from the Mac;
- the finding it closes, F212, under the operator's K39 of 2026-10-21, scoped
  to that one column; F210 keeps what the list still cannot cover;
- no migration and no change to live are expected of 385;
- its prompt, `docs/prompts/385_the_push_tokens_own_write.txt`;
- that this row was added by Phase 389A, and that 385's own session turns it
  🚧 at its Step 0.

A draft that carries all of them. Its body cell is 87 words by
`roadmap_words.count`, which splits the fourth cell on whitespace; the finish
line records the script's own printed count, and that count is the one that
stands:

```
| 385 | The push token's own write | 🔲 | `device_tokens.last_seen_at` joins `SERVER_WRITES`, 383's set-aside list, with 383's three controls each seen failing (another column of that row, an added token row, the same column in another table); the live check `verify_phase.sh 384` passes again from the Mac. Closes F212 (the operator's K39, 2026-10-21, scoped to that one column); F210 names what the list still cannot cover. No migration and no change to live expected. Prompt: `docs/prompts/385_the_push_tokens_own_write.txt`. Row added by Phase 389A, the fleet's first trial mission; 385's own session turns it 🚧 at its Step 0. |
```

In the same commit, row 389A's last sentence moves with the work, as the
ledger rule asks: "Step 0 next." becomes what is true at the commit (the plan
committed, row 385 added, awaiting the operator's merge). Nothing else in
row 389A changes, and no other row changes.

The diff is taken against `origin/master`, never `master`: the stage clone
has no local `master` (the revision in this document's opening paragraph).
Before taking it, the Engineer runs `git rev-parse origin/master` and records
the hash it prints in the phase log next to the diff, because the mirror is
refreshed before each stage and the ref can move between stages. The
expected shape below holds while that hash is `6adffc5` or a descendant that
carries row 389A unchanged; if the ref has moved past that, the Engineer
records the new hash and the shape it produces, and the recommendation names
the difference.

**Finish line:** `grep -c '^| 385 |' docs/ROADMAP.md` prints 1 (the Step 0
census printed 0); `python3 .claude/skills/closeout/roadmap_words.py 385
--check` exits 0 and its printed count is recorded in the phase log;
`python3 .claude/skills/closeout/roadmap_check.py` exits 0;
`git rev-parse origin/master` is recorded in the phase log;
`git diff --stat origin/master -- docs/ROADMAP.md` prints exactly
`1 file changed, 2 insertions(+), 1 deletion(-)`, because git shows the
change to row 389A as one line removed and one added; and the diff body,
`git diff origin/master -- docs/ROADMAP.md`, has exactly one `-` row line,
389A's old row, and exactly two `+` row lines, row 385 and 389A's new row,
not counting the `---`/`+++` header lines. The resolved hash, the stat line
and the three diff lines go in the phase log.

**As built** (`e69c6f6`): the draft row verbatim, inserted after 384's;
`roadmap_words.py 385 --check` printed 87, exit 0. Row 389A's "Step 0 next."
became "Plan committed; row 385 added; awaiting the operator's merge.", and
then, at the close-out, the row went ✅ with its CLOSED date and the
regression line (Deviations). `grep -c` printed 1; `roadmap_check.py` exit
0. `origin/master` resolved to `7ca42e0` (389's merge), a descendant of
`6adffc5` carrying row 389A unchanged, so the expected shape held: the
`--stat` line was `1 file changed, 2 insertions(+), 1 deletion(-)`, with one
`-` row line (389A old) and two `+` (385, 389A new), at the row commit. By
fix round 2, `origin/master` had moved to `6f32013` (row 390); that
measurement is in the phase log and under Deviations.

### 2. `docs/phases/in_progress/389A_implementation.md`: this plan, then v1.1

This document is v1.0. After the row is committed the Engineer writes v1.1:
every section updated to what shipped, the planned items ticked, and two new
sections, Deviations and Results. v1.1 carries no close date and no history
row: the close-out writes those (see section 4), and `roadmap_check.py` R6
reads a history row as a close.

**Finish line:** v1.1 committed on the branch; `python3
.claude/skills/fleet/plan_check.py 389A` still exits 0 against it.

**As built:** this v1.1 is in the close-out commit, together with the close
date and the history row, because the close-out happened on the branch
(section 4, as built). `plan_check.py 389A` against it: see Results.

### 3. `docs/phases/in_progress/389A_phase_log.md`: the dated record

A new file, in the shape of `docs/phases/completed/388_phase_log.md`. One
dated entry per event: the plan commit and its hash; the row commit and its
hash; the hash `origin/master` resolved to when the ROADMAP diff was taken,
with the stat line and the three diff lines; `wholetree.sh`'s exit code
before each commit, read on its own, never through a pipe; the regression
attempt and its printed line, marked of record or not; any guard that blocks
a command, recorded and never loosened; every label on issue #14 as it
actually moved, and which script moved it; the status note (section 5's
third point); and the line "No refute pass ran", since nothing here is a
content row.

**Finish line:** every commit on the branch after the plan commit, except the
last, has an entry naming its hash; every `wholetree.sh` run has its exit
code; the regression attempt has its line verbatim; the ROADMAP diff entry
names the `origin/master` hash it was taken against. The last commit on the
branch is the one that lands the log's final entry, so the log cannot name
its own hash. That hash is recorded in the Captain's merge recommendation on
the pull request (section 5), and the operator's merge-outcome line in the
handoff, added after the merge, names it again.

**As built:** `389A_phase_log.md`, moved to `completed/` at the close-out.
It names `93e1df0` (the merge of `master`) and `e69c6f6` (the row), the two
commits between the plan and the close-out, the
`origin/master` hash `7ca42e0`, every `wholetree.sh` exit code, and the
regression lines as printed. No label moved inside this session (it has no
network but the model's); the log says so and leaves the label record to the
dispatcher and the recommendation.

### 4. `docs/handoffs/YYYY-MM-DD_389A_closed.md`: the handoff, and the close-out it hands over

The Engineer writes the handoff on the branch, dated the day it is written:
what shipped (one row), what is open, what is next (Phase 385 itself, from
its prompt, flipping the row to 🚧 at its Step 0).

The close-out of 389A itself cannot finish on the fleet's host. F216 records
that the home desktop's regression run fails four tests for want of a Mac
tool and carries 33 unpinned skips, so `regression.sh` there is not a
regression of record, and F216 is open. So on this branch:

- row 389A stays 🚧 and its documents stay in `docs/phases/in_progress/`, so
  `roadmap_check.py` R3 holds at the merge;
- the handoff says "Regression of record: the operator's, on the Mac (F216)"
  and carries one paste block for the operator, in rule 6's form: the Mac, a
  Terminal window at the checkout, one block that runs `wholetree.sh --full`
  and then `regression.sh` on this branch and prints the regression line,
  ending ALL GOOD or SOMETHING IS OFF, with no internal labels in what the
  operator reads;
- the handoff names the close-out steps that follow the regression of record,
  in the closeout skill's order: row 389A to ✅ with its CLOSED date and the
  regression line, the three documents moved to `docs/phases/completed/`,
  this handoff dated to the close day (R6 refuses a handoff dated before the
  close), the merge, and the merge's outcome added after it.

**Finish line:** the handoff exists on the branch, its paste block is one
block ending ALL GOOD or SOMETHING IS OFF, and it says in plain words that
the regression of record and the close-out are the operator's on the Mac.

**As built:** not as planned. 389 closed, before this round, with the
operator's "Sandbox counts (Recommended)": a regression run inside the
fleet's fence is of record. The run in the stage clone was: "Regression of
record: 11297 passed, 0 failed, 105 skipped, 0 errors at `e69c6f6`", exit 0,
inside the fence. So the close-out ran on the branch, in the closeout
skill's order: row 389A ✅ with its CLOSED date and the regression line, the
three documents moved to `docs/phases/completed/`, `implementation.md`'s
history row and version, the root `phase_log.md`'s pointer, and the handoff
`docs/handoffs/2026-10-25_389A_closed.md`. The handoff has no paste block for
the Mac: nothing is left for the operator to run but the merge. Its "After
the merge" section is for whoever merges.

### 5. The Captain's merge recommendation

Not a file in the repository: three lines on the pull request. In this trial
it follows the pull request's opening directly, with no review stage between.
The reason is on this branch: `dispatcher.py`'s `NEXT_RANK` names the Red
Team as the mover of `review:open`, but when this plan was written the
dispatcher had only `stage_xo` and `stage_digest`; 388's non-goals list every seat that writes
code, including the Red Team, as a later rollout step; and row 389A says 389
builds the Captain and the Engineer only. No rank in this trial can move
`review:open` to `review:clear`, so the trial does not pass through those two
labels. The Engineer's stage opens the pull request; the Captain's stage,
389's, reads the pull request as opened and posts the recommendation. The
label it then sets is the one 389's script sets from its parsed result; the
phase log records that label by name. If 389's scripts set no label at the
pull request, the issue's label stays where the last script left it, and the
recommendation says so as the trial's first finding for 389, instead of
anyone moving it by hand.

The recommendation must carry:

- the diff's shape: one ROADMAP row added, 389A's row updated, the three
  phase documents and the handoff, nothing under `src/` or `tests/`; and the
  `origin/master` hash the shape was measured against;
- the hash of the branch's last commit (the one the phase log cannot name,
  section 3) and each check's exit code from the phase log;
- the status note for the operator: the mission says 🔲 and 385's prompt says
  "add it as 🚧 before Step 0". Both hold: the row is 🔲 until 385 starts,
  and 385's session turns it 🚧. The prompt's first line will read as if the
  row were missing; the prompt is a committed record and is not edited here;
- that no Red Team ran, and why (the paragraph above), so the operator reads
  the diff knowing it had the Executive Officer's check on the plan and no
  adversarial pass on the result;
- that the close-out is the operator's on the Mac (section 4), and why
  (F216);
- that issues #9 and #10 from Phase 388 are untouched and remain the
  operator's to close.

**Finish line:** the recommendation is posted on the pull request, and every
label on issue #14 was set by a rank's script from a parsed result, none by
hand; the phase log's label entries show it.

**As built:** outside this session. The Engineer's stage cannot open the
pull request, post on it or set a label from inside the fence; the
dispatcher pushes and opens the pull request after its own checks and
model-free run. Since this plan was written, 389 merged with `red_team.py`,
and the dispatcher on this branch has `stage_scout`, `stage_captain`,
`stage_engineer`, `stage_red_team` and `stage_recommend` besides
`stage_xo` and `stage_digest`, so the reason above no longer holds. A Red
Team did run on the pull request (#15) and sent it back; its round-2
findings and their fixes are in the phase log. Two of
the points above changed with the build: the close-out is no longer the
operator's on the Mac (section 4, as built), and the branch's last commit is
the close-out commit.

### What this phase does not change in the code

`src/motodiag/api/routes/push.py`, `motodiag/push/registry.py` and
`deploy.py`'s `SERVER_WRITES` are the code Phase 385 concerns. This phase
reads none of them and edits none of them. No test file is added or changed,
so `COLLECTED_TEST_FLOOR` does not move.

### The login's scope

Every write under the operator's login is one of: a push of this branch, a
comment on mission issue #14, the pull request the recommendation goes on,
and a label set by a rank's script from a parsed result. No merge, no issue
closed, no label by hand, no write to `master`.

## The change log's three newest entries

- **2026-10-22, `fleet` joins the procedure folders.** No check: the entry
  says the table row "is text only, and no check reads the table". This
  mission is the first run through that folder's dispatcher from Step 0 to a
  merge recommendation, which is why its records are kept to the letter.
- **2026-10-20, rule 6: plain English to the operator.** No check: the entry
  says "Text only; no check holds it." The one thing this phase hands the
  operator, the paste block in the handoff (Logic, section 4), is written to
  it: which computer, which window, one block, ending ALL GOOD or SOMETHING
  IS OFF, no internal labels. As built: the regression was of record in the
  fence, so the handoff hands the operator no paste block, only the merge.
- **2026-10-19, live is on the home desktop.** The check it became:
  `tests/test_phase382_live_location.py`. The fleet's host is the machine that
  holds live; this phase never reads live, names no live path and ships no
  migration, so the check has nothing to see here and nothing to refuse.

## Rule-1 stops anticipated

- **A test it cannot make green: anticipated, from F216.** The regression of
  record cannot be produced on the fleet's host: four tests fail there for
  want of a Mac tool and 33 skips are not pinned, so `regression.sh` there is
  not of record. The Engineer runs `wholetree.sh --full` and `regression.sh`
  once in the stage clone, records the printed line and exit code verbatim as
  not of record, and stops there. The guard is not loosened and no skip is
  pinned here (pinning is the operator's call under F206). Recommended: the
  operator runs the regression of record on the Mac and does the close-out
  there, as 388's "Mac runs it (Recommended)" did; the handoff carries the
  paste block. If `wholetree.sh` fast mode itself blocks a commit on the host
  for the same want, that is the same stop: record it, never loosen it.
  **As built: did not occur.** 389's "Sandbox counts" made a fenced run of
  record, and the run here was green with every skip pinned; fast mode
  never blocked.
- **A login or a credential: covered, not open.** The mission runs under the
  operator's login by Phase 389's pre-approval (b), "a planted trial mission
  may use my login until the identity exists", applied literally to the
  writes listed under Logic. Any other write under that login is a stop. The
  fleet's own identity (F214) is not made here.
- **A real fork: none expected.** The row's facts come from the mission, the
  385 prompt, K39 and F212; there is one way to write them and nothing else
  ships. Skipping the review labels (Logic, section 5) is not a fork: no
  second plan exists that could run a Red Team on this branch, and the
  recommendation tells the operator plainly that none ran.
- **A threshold or a rule's definition: none expected.** The 120-word cap and
  the status key are applied, not changed. `SERVER_WRITES` is a gate's
  definition and is not touched; the operator's K39 approval covers its change
  for Phase 385's own run, scoped to one column, and no part of it is spent
  here. The 🔲/🚧 wording is a note for the operator, not a change to either
  definition. The label table in the fleet proposal is not edited; the trial
  records which of its labels it passed through and which it could not.
- **A live-database change: none expected.** No migration, no live row, no
  read of live.

## Tests

No test file is added: a test that one ROADMAP row exists would be a test
that cannot fail once the row is in, and the ledger already has its checks.
The build runs the checks that exist and records each one's output and exit
code in the phase log:

- `python3 .claude/skills/closeout/roadmap_check.py`: exit 0 on the branch
  (R1 no duplicate number, R2 and R3 the row and documents agree, R4 385 is
  in this repository's range, R6 and R7 unaffected). Then
  `roadmap_check.py --self-test`, which plants each rule's bad case and
  watches it fire, so the check is seen red before it is trusted green. If R5
  cannot read the mobile repository's copy of the authority contract inside
  the fence, the log says so and the fast gate's verdict stands.
- `python3 -m pytest tests/test_roadmap_continuity.py`: passes, the same
  check as the suite runs it.
- `python3 .claude/skills/closeout/roadmap_words.py 385 --check`: exit 0,
  the count printed; the same for 389A after its row's last sentence
  changes. As the control, the module's `count()` on a 121-word cell returns
  121, run from the stage's run directory on a string, not on the repository.
- `grep -c '^| 385 |' docs/ROADMAP.md`: 0 before (the Step 0 census), 1
  after.
- `git rev-parse origin/master`: the hash recorded, then
  `git diff --stat origin/master -- docs/ROADMAP.md` prints
  `1 file changed, 2 insertions(+), 1 deletion(-)`, and
  `git diff origin/master -- docs/ROADMAP.md` has one `-` row line and two
  `+` row lines (header lines not counted), the three rows named in Logic,
  section 1. `master` is not used: the stage clone has no such local ref.
- `.claude/skills/closeout/wholetree.sh` (fast mode) before every commit, run
  on its own, its exit code read before the commit.
- `python3 .claude/skills/fleet/plan_check.py 389A`: exit 0 against v1.0
  (the Executive Officer's run) and against v1.1.
- `wholetree.sh --full` then `regression.sh`, once, in the stage clone: the
  line recorded verbatim with its exit code and marked not of record, F216's
  expected outcome. If it unexpectedly passes with every skip pinned, that is
  a regression of record and the merge recommendation says so as a change
  from this plan.

**As run**: `roadmap_check.py` exit 0, its
`--self-test` R1–R7 each fire and the good tree passes, exit 0 (R5 read the
mobile copy inside the fence); `tests/test_roadmap_continuity.py` 28 passed
under `.venv/bin/python` (the host's `python3` has no pytest);
`roadmap_words.py` 87 for 385 and 60 for 389A before the close-out, exit 0;
the control returned 121; `grep -c` 0 then 1; `origin/master` `7ca42e0`
and the expected `--stat` and three row lines; `wholetree.sh` fast exit 0
before each commit; `wholetree.sh --full` exit 0; `regression.sh` exit 0
and of record. `plan_check.py 389A` against v1.1: Results.

## Non-goals

- Phase 385's own work: the change to `SERVER_WRITES` in `deploy.py`, its
  three controls, the live check from the Mac, closing F212. 385 runs from
  its own prompt and turns the row 🚧 at its Step 0.
- Anything under `src/` or `tests/`, including the push routes and the
  registry; `COLLECTED_TEST_FLOOR` is unchanged.
- Any migration, any read or write of live, any path under `data/`, seed
  data, a split or an eval protocol.
- Editing `docs/prompts/385_the_push_tokens_own_write.txt`, whose first line
  says to add the row as 🚧: a committed prompt is a record. Editing
  `docs/decisions.md` K39, whose "not built" stays true.
- Pinning any skip or fixing any of F216's four failures; closing F216 or
  F217.
- The fleet's GitHub identity and the master ruleset (F214).
- A Red Team stage, a `review:open` or `review:clear` move, or any edit to
  `dispatcher.py`'s label table to match this trial: 389 and the later
  rollout steps own those. This trial only records which labels it passed
  through.
- Creating a local `master` branch in the stage clone, or changing how
  `dispatcher.py` clones, so that `master` would resolve: the diff is taken
  against `origin/master` instead.
- Merging, closing issues #9, #10 or #14, or moving any label by hand.
- Any new check that reads the `<!-- fleet-trial -->` marker, which the
  census finds nowhere.

## Planned items

- [x] the plan commit: this v1.0 on `phase-389A-385s-roadmap-row` (`f13d170`, the approved revision)
- [x] row 385 in `docs/ROADMAP.md`, after 384's, and 389A's row's last
      sentence updated; `wholetree.sh` exit 0 before the commit
- [x] the checks run and recorded: `roadmap_check.py` and its `--self-test`,
      `tests/test_roadmap_continuity.py`, `roadmap_words.py 385 --check` with
      its count and its 121-word control, the `grep -c` before and after, the
      `origin/master` hash from `git rev-parse`, the `--stat` line and the
      three diff lines against `origin/master`
- [x] `wholetree.sh --full` and `regression.sh` once in the stage clone, the
      line recorded verbatim and marked of record or not
- [x] `389A_phase_log.md` with every commit but the last, every exit code,
      every guard block, every label move and the `origin/master` hash the
      diff was taken against
- [x] `389A_implementation.md` v1.1 with Deviations and Results
- [x] the handoff on the branch; as built, with the close-out done on the
      branch and no paste block (Deviations)
- the pull request and the Captain's merge recommendation: the dispatcher's
      stages after this session, which cannot open or post on a pull request
      from inside the fence (Logic, section 5, as built)

## Deviations

- **The close-out ran on the branch, not on the Mac.** v1.0 (section 4 and
  its anticipated rule-1 stop) assumed F216 made a regression of record
  impossible on the fleet's host. 389 closed before this round with the
  operator's "Sandbox counts (Recommended)": a regression run inside the
  fence is of record, with the fence's skips pinned. The run here was green,
  of record, with every skip pinned, which is the case this plan's Tests
  section names ("that is a regression of record and the merge
  recommendation says so as a change from this plan"). So row 389A is ✅
  with its CLOSED date and the regression line, the three documents are in
  `completed/`, `implementation.md` has its history row and version, the
  root `phase_log.md` its pointer, and the handoff hands the operator only
  the merge, with no paste block. Not a fork: the plan named this outcome,
  and the mission prompt for this round asks for the close-out.
- **`origin/master` was `7ca42e0`, not `6adffc5`**: 389's merge, a
  descendant carrying row 389A unchanged, so the expected diff shape held.
  The stage clone now also has a local `master` (389's bug fix #3); the diff
  was still taken against `origin/master`, as the plan says.
- **The continuity test ran under `.venv/bin/python`**, not `python3`: the
  host interpreter has no pytest. Same test, the canonical interpreter.
- **Section 5 is outside this session.** The labels, the pull request and
  the recommendation are the dispatcher's and the Captain's. 389 has since
  merged a Red Team rank, and it ran on the pull request (#15).
- **`plan_check.py 389A` against v1.1 ran in a scratch worktree.** The
  checker reads only `docs/phases/in_progress/` and P1 wants the row 🚧, so
  on the closed tree it prints "CANNOT READ", exit 2. It ran on a worktree
  of `e69c6f6` (row 389A 🚧) with v1.1 copied into `in_progress/`; the
  phase log has the command and the file's hash.
- **The branch's diff also carries `docs/prompts/389A_385_s_roadmap_row.txt`**,
  the mission prompt, committed with Step 0 (`ffe1691`) before the plan;
  section 5's diff shape does not name it.
- **`origin/master` moved to `6f32013` by fix round 2** (389's handoff
  outcome, row 390). Against it, the two-dot `--stat` reads
  `2 insertions(+), 2 deletions(-)`, because this branch predates row 390;
  against the merge base, `7ca42e0`, the shape is still the planned one.
  The phase log has both.
- **The regression was run again on 2026-10-27, after the operator merged
  `master` into the branch** (`bc50c4b`). Issue #14's check had failed on
  `e15b462` for want of `master`'s gate-6 time limit; the record now names
  the merged tree. Nothing was built in that round.
- No bug fixes; no guard blocked a command.

## Results

Regression of record: 11500 passed, 0 failed, 105 skipped, 0 errors at `bc50c4b` (33 min 39 s wall, `python -m pytest -n auto --dist load`, exit 0) (run inside the fleet's fence)

Added 2026-10-27, on the merge of `master` into this branch (`bc50c4b`,
the operator's): `wholetree.sh --full` 4716 passed, 36 skipped, exit 0,
then the line above. 11500 + 105 = 11605, `COLLECTED_TEST_FLOOR` as
`master` has it. It supersedes the close-out's run, kept below.

The close-out's run, 2026-10-25: 11297 passed, 0 failed, 105 skipped, 0 errors at `e69c6f6` (30 min 18 s wall, `python -m pytest -n auto --dist load`, exit 0) (run inside the fleet's fence)

11297 + 105 = 11402, `COLLECTED_TEST_FLOOR`, unchanged. The skip lines
are in the phase log as printed.

- **Row 385**, 🔲, 87 words, after 384's (`e69c6f6`). `grep -c '^| 385 |'`
  printed 0 before and 1 after.
- **Row 389A**: "Step 0 next." moved with the work at `e69c6f6`, then ✅ at
  the close-out.
- **The diff against `origin/master` (`7ca42e0`)**: `docs/ROADMAP.md` only
  `1 file changed, 2 insertions(+), 1 deletion(-)`; nothing under `src/` or
  `tests/`; no migration, nothing on live.
- **Checks**: `roadmap_check.py` exit 0 and its self-test R1–R7 fire;
  `tests/test_roadmap_continuity.py` 28 passed; `wholetree.sh` fast exit 0
  before each commit; `wholetree.sh --full` 4530 passed, 36 skipped, exit 0.
- **`plan_check.py 389A` against v1.1**, in the scratch worktree
  (Deviations): P1–P8 pass, "plan_check 389A: PASS", exit 0.
