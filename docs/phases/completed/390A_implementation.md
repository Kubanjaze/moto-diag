# Phase 390A — The Quartermaster's ROADMAP row

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-10-25 (v1.0 `4123dfa`, revised `e274426`)

v1.1 updates every section to what shipped (each change marked "As
built"), ticks the planned items, and adds Deviations and Results.

Written by the Captain from `390A_step0.md` (classification: greenfield),
ROADMAP row 390A and the mission prompt
`docs/prompts/390A_the_quartermaster_s_roadmap_row_the.txt` (issue #16).
Branch: `phase-390A-quartermaster-row`, from `master` at `9f0bd7b`.
Revised once before the push on the Executive Officer's two items: the
before-the-PR check is `closeout_check.py` and the push gate, with
`verify_phase.sh` as the operator's after-the-merge check; and the root
`implementation.md`'s Roadmap count line is re-measured at close-out.

---

## Goal

One ledger row, docs only. Phase 390A is Phase 390's planted mission for
the restart proofs, a follow-on of 390 as 389A was of 389. Its one
deliverable is row 391 in `docs/ROADMAP.md`, after row 390A, status 🔲:
"The Quartermaster", step 8 of `docs/reports/2026-10-22_fleet_proposal.md`,
the Quartermaster in shadow. Nothing under `src/`, no migration, nothing on
live.

The mission issue proves one rank, the Science Officer: the planter
restarts the fleet's service while its stage runs and closes the issue once
the resumed stage has started. This plan is still the full contract for the
phase, so that whoever builds it (the Engineer on this branch, or the
operator by hand) ships the same thing: the row, and the phase's own
close-out records.

What the Step 0 report left to check is settled here. The one `391` hit
under `src/` is a KTM owner's manual filename quoted in a source citation in
`src/motodiag/knowledge/transmission.py`, not a phase number; nothing under
`src/` changes. The Quartermaster appears in code only as the dispatcher's
routing note in `.claude/skills/fleet/dispatcher.py` ("not built yet") and a
label description in `.claude/skills/fleet/labels.py`; both stay as they
are until Phase 391 builds the rank.

**As built:** row 391 and the close-out records shipped, docs only, and
F220 was filed; nothing under `src/`, `tests/` or `.claude/` changed. The
Engineer built it on this branch.

## Logic

### 1. `docs/ROADMAP.md`: row 391

One table row inserted directly after row 390A, in the same table. Its
first three cells are `391`, `The Quartermaster`, `🔲`. Its body cell says,
in the proposal's own terms:

- step 8 of `docs/reports/2026-10-22_fleet_proposal.md`, the Quartermaster
  in shadow;
- what it does on `merge:needs-review`: runs `verify_phase.sh`, checks the
  commits exist and nothing is a stub, and writes its merge verdict to the
  digest while the operator still merges and closes the mission issue;
- the promotion rule: only after it has refused at least one planted bad PR
  and named the right check, recorded in both repositories' CLAUDE.md with
  the date; after promotion it merges and closes the issue through the same
  `/closeout` tail;
- its scope from the 2026-10-22 decisions: extension or greenfield, no
  migration, nothing on live;
- "Not started."

The wording to use, or a tightening of it that keeps every item above:

```
| 391 | The Quartermaster | 🔲 | Step 8 of `docs/reports/2026-10-22_fleet_proposal.md`: the Quartermaster in shadow. On `merge:needs-review` it runs `verify_phase.sh`, checks that the commits exist and nothing is a stub, and writes its merge verdict to the digest while the operator still merges and closes the mission issue. Promoted only after it has refused at least one planted bad PR and named the right check, recorded in both repositories' CLAUDE.md with the date; then it merges and closes the issue through the same `/closeout` tail. Extension or greenfield: no migration, nothing on live (the 2026-10-22 decisions). Not started. |
```

Finish line: `python3 .claude/skills/closeout/roadmap_words.py 391 --check`
exits 0 (the draft above is under the cap by the script's own method);
`python3 .claude/skills/closeout/roadmap_check.py` passes on the tree with
the row in it (391 is the next free number, R1; it has no documents under
`docs/phases/`, so R2 and R3 have nothing to disagree with; it sits in the
open-ended backend range of `ROADMAP_AUTHORITY.md`, R4). No other row is
changed by this step. The row is a ledger entry: the only way a reader
reaches it is by reading the ROADMAP, and the reach for each verb in it
belongs to Phase 391.

**As built:** the wording above, unchanged, inserted after row 390A in
`95a127b`. `roadmap_words.py 391 --check` printed 91, exit 0;
`roadmap_check.py` passed.

### 2. `docs/ROADMAP.md`: row 390A at close-out

Row 390A goes from 🚧 to ✅ in the close-out commit, with
`**CLOSED YYYY-MM-DD.**`, one sentence on what shipped (row 391, docs
only), and the regression line as `regression.sh` printed it. Finish line:
the body cell within the cap by `roadmap_words.py 390A --check`, and
`roadmap_check.py` passing with the phase's documents in `completed/`.

**As built:** row 390A ✅ in the close-out commit, with the sentence and the
regression line; one more clause names F220, the finding the regression
turned up (Deviations).

### 3. `docs/phases/in_progress/390A_phase_log.md`, new

The phase's dated log: Step 0 received, v1.0 committed, the row written and
checked, each whole-tree run's exit code, the regression of record's line,
any guard block (recorded, never loosened). It carries the line
"No refute pass ran" unless a refute pass runs, in which case it carries the
`## Refuter pass` checklist (A8). A bug-fix register appears only if a bug
fix happens; a docs row is expected to need none. Its status line reads
Complete at close-out (A2). Finish line: `closeout_check.py . 390A` reports
nothing.

**As built:** as planned, with no bug fix. It also records the two
regression runs that did not count (one cut off when the session stopped,
one red on F220), the decision to run the same tree again (Deviations), and
one edit-guard block.

### 4. `docs/phases/in_progress/390A_implementation.md`, this document

v1.1 at close-out: every section updated to what shipped, the planned items
ticked, Deviations and Results added (A3). Finish line: the plan as built
differs from v1.0 only where Deviations says so.

**As built:** this version.

### 5. The close-out records

- `docs/handoffs/YYYY-MM-DD_390A_closed.md`: what shipped, what is open,
  what is next, written before the merge (rule 4, R6). It ends with an
  `## After the merge` section, in the form of Phase 389's handoff, that
  the operator fills in after the merge with the merge's outcome and the
  verify script's result (below).
- The root `phase_log.md`: a `## Phase 390A` section pointing at the two
  phase documents, in the form of Phase 389's.
- The root `implementation.md`: the version header naming Phase 390A and a
  history row (A7), and its Roadmap count line re-measured with row 391 in
  the ledger. The line today reads `407 rows, 368 numbered phases and 39
  letter follow-ons, on 2026-10-25`; `master` already carries 409 rows
  (369 numbered and 40 letter), and with row 391 the ledger holds 410 rows,
  370 numbered phases and 40 letter follow-ons. The Engineer counts the
  `| N |` and `| NX |` rows on the close-out tree (the same rows
  `roadmap_check.py` reads), writes the three counts it gets and the
  close-out date, and records the count's command in the phase log. The
  figures above are what the count is expected to give, not what is
  written: what is written is what the count returns on that tree. Phases
  386 and 389 re-measured this line at their close-outs; a phase whose one
  deliverable is a ROADMAP row cannot leave it stale.
- The three 390A documents (`390A_step0.md`, `390A_implementation.md`,
  `390A_phase_log.md`) moved to `docs/phases/completed/`, none left in
  `in_progress/` (A1).

Finish line, in two parts, as Phase 389 ran it:

- **Before the PR**, on the branch: `python3
  .claude/skills/closeout/closeout_check.py . 390A` reports nothing (A1 to
  A8), and the push gate in `.claude/skills/fleet/fleet_git.py` passes the
  close-out commit. `verify_phase.sh` is not run before the PR: its usage is
  `verify_phase.sh PHASE REG_HASH TIP` and it exits on a missing third
  argument; its check 1 greps `origin/master` for the tip, which reads
  MISSING until the merge; and its check 8 reads live or the way in to it,
  which a stage clone inside the fence cannot reach.
- **After the merge**, the operator's check: `verify_phase.sh 390A
  <regression hash> <merge commit>`, as 389's was
  (`verify_phase.sh 389 2754a01 7ca42e0`). Its result goes in the handoff's
  `## After the merge` section, with the merge's outcome.

**As built:** the count on the close-out tree gave 410 rows, 370 numbered
phases and 40 letter follow-ons, the figures expected; the command is in
the phase log. The handoff, the root `phase_log.md` section and the history
row are written; the three documents are in `completed/`.

### 6. The order of work

Each commit on its own, with `.claude/skills/closeout/wholetree.sh` run on
its own first and its exit code read: the row (step 1), then the phase log
as it grows, then `wholetree.sh --full`, `regression.sh`, then the close-out
commit (steps 2, 4, 5). The push gate in `.claude/skills/fleet/fleet_git.py`
lets the Engineer add a ROADMAP row and change its own phase's row, and
refuses a change to any other phase's row; nothing in this plan touches
another phase's row.

**As built:** in that order, four commits: the row (`95a127b`), the phase
log (`44f846d`), the regression of record with F220 (`ab40626`), and the
close-out commit. F220 had to be filed before any document cited it (rule
6), so it went in with the regression's log entry.

## The change log's three newest entries

- **2026-10-22, `fleet` joins the procedure folders.** No check: the entry
  says the row "is text only, and no check reads the table". The folder's
  own tests, `tests/test_phase387_fleet_contract.py`, hold the folder, not
  the table. This phase adds nothing to the folder; the dispatcher's note
  that the Quartermaster is not built yet stays true until Phase 391.
- **2026-10-20, rule 6: plain English to the operator.** No check: the
  entry says "Text only; no check holds it." What this phase hands the
  operator is the after-the-merge check in Logic 5 and, if one arises, a
  stop from the Engineer; each is written as plain English with one paste
  block and no internal labels.
- **2026-10-19, live is on the home desktop.** The check it became:
  `tests/test_phase382_live_location.py`. This phase reads nothing from
  live and writes nothing to it; a stage clone inside the fence is a machine
  that does not hold live, which is why the verify script, whose check 8
  reads live, is the operator's to run after the merge.

## Rule-1 stops anticipated

- **A login or a credential:** none new. The branch pushes under the
  operator's login because the issue carries the trial marker, inside
  Phase 390's pre-approval (a), "planted missions push under my login until
  the machine user exists", applied literally to this issue. No other
  account or token is asked for.
- **A live-database change that alters or deletes rows:** none. Docs only:
  no migration, nothing on live, nothing under `src/`.
- **A real fork:** none expected. The mission fixes the row's number,
  place, status and source; the body cell's wording is routine judgement
  inside those, and the log records it.
- **A threshold or a rule's definition:** none expected. The row cap stays
  at its value, the ledger check is not edited, and the dispatcher's
  routing stays as it is.
- **A test it cannot make green:** none expected from the row; a red
  ledger check or cap check is a defect in the row, fixed before the commit.
  If the regression of record inside the fence goes red on something the
  row cannot have caused, that is this stop, put to the operator in plain
  English with the failing test's output, as 389A's was.

**As built:** no stop. One regression run went red on a test the row
cannot have caused, and the cause made it green on a run inside one UTC
day without a change, so it was run again rather than stopped (Deviations
1).

## Tests

No new test file. A 🔲 row is a ledger entry, not a capability with an
entry point; the ROADMAP already carries not-started rows that the ledger
check accepts, which is the control. The checks that hold this phase's work
already exist and are run on it:

- `tests/test_roadmap_continuity.py` runs `roadmap_check.py` R1–R7 over the
  ledger with row 391 in it, with every suite run and on every push.
- `roadmap_words.py 391 --check` and `roadmap_words.py 390A --check`, run
  by hand before each commit that touches the row; the verify script runs
  the cap check again after the merge, in the operator's hands.
- `roadmap_check.py --self-test` run once on this branch and its output
  kept in the phase log: its known-bad fixtures go red (a reused number, a
  row with no documents' agreement, a number outside every range), so the
  check that holds the row has been seen to fail.
- `wholetree.sh` before each commit; `wholetree.sh --full` then
  `regression.sh` for the regression of record (parallel; `--serial` only
  as the fallback the rule names), its line recorded in the phase log,
  v1.1's Results and row 390A.
- `plan_check.py 390A` on this plan (P1–P8) before it is pushed;
  `closeout_check.py . 390A` and the push gate before the PR;
  `verify_phase.sh 390A <regression hash> <merge commit>` by the operator
  after the merge, its result in the handoff.
- The root `implementation.md`'s Roadmap count line: the row count on the
  close-out tree matches the three figures written, and the date is the
  close-out's; the command and its output are in the phase log.
- `COLLECTED_TEST_FLOOR` does not move: no test is added or removed, and
  the floor test is expected to pass unchanged.

**As built:** all run as listed, with their outputs in the phase log; the
floor did not move, and the regression of record passed 11297, as at Phase
389's. `verify_phase.sh` stays the operator's, after the merge.

## Non-goals

- Building the Quartermaster: `verify_phase.sh` run by a rank, a merge
  verdict in the digest, the planted bad PR, promotion. All of it is Phase
  391's, and this phase only gives it a row.
- Anything under `src/`, `tests/` or `.claude/skills/fleet/`, including the
  dispatcher's "not built yet" note and the `merge:needs-review` label text.
- Changing `verify_phase.sh` so that it can run inside the fence before the
  merge: the script's checks 1 and 8 are right to read `origin/master` and
  live, and the split between the Engineer's before-the-PR checks and the
  operator's after-the-merge check is 389's practice, kept.
- Any migration, anything on live, any path under the data folder, seed
  content, splits, eval protocols.
- Row 385 (389A's deliverable) and its branch; the machine user and the
  master ruleset (F214's other half): the operator's and 389A's.
- Correcting the ROADMAP header's phase total, which already predates rows
  386 to 390A; a nit for a records phase. The root `implementation.md`'s
  count line is a different line and is re-measured here (Logic 5).
- Closing issue #16: the planter's, once the resumed stage has started.
- Phase 390's own proofs and F219: 390's branch.

## Planned items

- [x] 1. Row 391 in `docs/ROADMAP.md` after row 390A, 🔲, the wording in
      Logic 1; `roadmap_words.py 391 --check` exit 0; `roadmap_check.py`
      passing; one commit after `wholetree.sh` (`95a127b`)
- [x] 2. `roadmap_check.py --self-test` run once, its known-bad cases red,
      the output in the phase log
- [x] 3. `390A_phase_log.md`: dated entries from Step 0 on, the "No refute
      pass ran" line, the regression line
- [x] 4. `wholetree.sh --full`, then `regression.sh`; the line recorded
- [x] 5. v1.1 of this plan: every section as built, Deviations, Results
- [x] 6. Row 390A to ✅ with the CLOSED date and the regression line; the
      handoff `docs/handoffs/YYYY-MM-DD_390A_closed.md` with its
      `## After the merge` section left for the operator; the root
      `phase_log.md` section; `implementation.md`'s header, history row and
      Roadmap count line re-measured with row 391 in the ledger (expected
      410 rows, 370 numbered and 40 letter follow-ons, written as counted,
      with the close-out date); the three documents to `completed/`
- [x] 7. Before the PR: `closeout_check.py . 390A` reporting nothing and
      the push gate passing; the PR naming issue #16, the regression line
      and the model-free run. After the merge, the operator runs
      `verify_phase.sh 390A <regression hash> <merge commit>` and its
      result goes in the handoff's `## After the merge` section. As built:
      `closeout_check.py . 390A` prints nothing; the push gate, the
      model-free run and the PR are the dispatcher's, after this session,
      and the after-the-merge check is left in the handoff for the operator

## Deviations

1. **A red regression did not stop the phase.** "Rule-1 stops anticipated"
   says a red regression inside the fence on something the row cannot have
   caused is a stop for the operator. The second `regression.sh` run at
   `44f846d` failed one test,
   `test_phase274_quotes_variance.py::TestTheQuoteRecord::test_queuing_an_estimate_records_the_quote`
   (`'2026-10-26' == '2026-10-25'`). The cause was on the failure's face:
   the test reads its day at import (line 23); the run was collected at
   23:55 UTC and reached the test after midnight UTC. Rule 1 stops for a
   test that cannot be made green, and this one is green on any run inside
   one UTC day, with no change. So the same tree was run again unchanged at
   00:28 UTC and passed, 11297 to 0. The decision and the reason are in the
   phase log.
2. **F220 filed, and not fixed.** The test's defect is recorded in
   `docs/FOLLOWUPS.md` as F220, with what would close it, and the header's
   highest number moved to F220. Fixing it is a change under `tests/`,
   which this plan's Non-goals exclude. Row 390A names it in one clause.
3. **One regression run lost.** The first `regression.sh` run was cut off
   when the session stopped, before it printed anything; it counts for
   nothing, and the log says so.

Nothing else differs from v1.0: row 391's wording is v1.0's, no file under
`src/`, `tests/` or `.claude/` changed, and `COLLECTED_TEST_FLOOR` did not
move.

## Results

- Row 391, "The Quartermaster", 🔲, after row 390A: 91 words by
  `roadmap_words.py`; `roadmap_check.py` passes, and its `--self-test`
  goes red on every rule's known-bad tree (R1–R7) and passes the good one.
- The ledger with row 391: 410 rows, 370 numbered phases and 40 letter
  follow-ons, on 2026-10-25.
- `wholetree.sh --full` at `44f846d`: exit 0, 4530 passed, 36 skipped.
- The regression of record, as `regression.sh` printed it (its 105 skips,
  by file and reason, are below the same line in the phase log):

Regression of record: 11297 passed, 0 failed, 105 skipped, 0 errors at `44f846d` (31 min 33 s wall, `python -m pytest -n auto --dist load`, exit 0) (run inside the fleet's fence)

- F220 filed. No bug fix, no migration, nothing on live, no refute pass.
