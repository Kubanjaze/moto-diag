# Phase 390A — The Quartermaster's ROADMAP row

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-10-25

Written by the Captain from `390A_step0.md` (classification: greenfield),
ROADMAP row 390A and the mission prompt
`docs/prompts/390A_the_quartermaster_s_roadmap_row_the.txt` (issue #16).
Branch: `phase-390A-quartermaster-row`, from `master` at `9f0bd7b`.

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

### 2. `docs/ROADMAP.md`: row 390A at close-out

Row 390A goes from 🚧 to ✅ in the close-out commit, with
`**CLOSED YYYY-MM-DD.**`, one sentence on what shipped (row 391, docs
only), and the regression line as `regression.sh` printed it. Finish line:
the body cell within the cap by `roadmap_words.py 390A --check`, and
`roadmap_check.py` passing with the phase's documents in `completed/`.

### 3. `docs/phases/in_progress/390A_phase_log.md`, new

The phase's dated log: Step 0 received, v1.0 committed, the row written and
checked, each whole-tree run's exit code, the regression of record's line,
any guard block (recorded, never loosened). It carries the line
"No refute pass ran" unless a refute pass runs, in which case it carries the
`## Refuter pass` checklist (A8). A bug-fix register appears only if a bug
fix happens; a docs row is expected to need none. Its status line reads
Complete at close-out (A2). Finish line: `closeout_check.py 390A` reports
nothing.

### 4. `docs/phases/in_progress/390A_implementation.md`, this document

v1.1 at close-out: every section updated to what shipped, the planned items
ticked, Deviations and Results added (A3). Finish line: the plan as built
differs from v1.0 only where Deviations says so.

### 5. The close-out records

- `docs/handoffs/YYYY-MM-DD_390A_closed.md`: what shipped, what is open,
  what is next, written before the merge (rule 4, R6); the merge's outcome
  added after it.
- The root `phase_log.md`: a `## Phase 390A` section pointing at the two
  phase documents, in the form of Phase 389's.
- The root `implementation.md`: the version header naming Phase 390A and a
  history row (A7).
- The three 390A documents (`390A_step0.md`, `390A_implementation.md`,
  `390A_phase_log.md`) moved to `docs/phases/completed/`, none left in
  `in_progress/` (A1).

Finish line: `.claude/skills/closeout/verify_phase.sh 390A <hash>` reads
every check green.

### 6. The order of work

Each commit on its own, with `.claude/skills/closeout/wholetree.sh` run on
its own first and its exit code read: the row (step 1), then the phase log
as it grows, then `wholetree.sh --full`, `regression.sh`, then the close-out
commit (steps 2, 4, 5). The push gate in `.claude/skills/fleet/fleet_git.py`
lets the Engineer add a ROADMAP row and change its own phase's row, and
refuses a change to any other phase's row; nothing in this plan touches
another phase's row.

## The change log's three newest entries

- **2026-10-22, `fleet` joins the procedure folders.** No check: the entry
  says the row "is text only, and no check reads the table". The folder's
  own tests, `tests/test_phase387_fleet_contract.py`, hold the folder, not
  the table. This phase adds nothing to the folder; the dispatcher's note
  that the Quartermaster is not built yet stays true until Phase 391.
- **2026-10-20, rule 6: plain English to the operator.** No check: the
  entry says "Text only; no check holds it." The one thing this phase may
  hand the operator is a stop from the Engineer, written as a plain-English
  question with no internal labels.
- **2026-10-19, live is on the home desktop.** The check it became:
  `tests/test_phase382_live_location.py`. This phase reads nothing from
  live and writes nothing to it; a stage clone inside the fence is a machine
  that does not hold live.

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

## Tests

No new test file. A 🔲 row is a ledger entry, not a capability with an
entry point; the ROADMAP already carries not-started rows that the ledger
check accepts, which is the control. The checks that hold this phase's work
already exist and are run on it:

- `tests/test_roadmap_continuity.py` runs `roadmap_check.py` R1–R7 over the
  ledger with row 391 in it, with every suite run and on every push.
- `roadmap_words.py 391 --check` and `roadmap_words.py 390A --check`, run
  by hand before the commit and again by `verify_phase.sh` (check 6).
- `roadmap_check.py --self-test` run once on this branch and its output
  kept in the phase log: its known-bad fixtures go red (a reused number, a
  row with no documents' agreement, a number outside every range), so the
  check that holds the row has been seen to fail.
- `wholetree.sh` before each commit; `wholetree.sh --full` then
  `regression.sh` for the regression of record (parallel; `--serial` only
  as the fallback the rule names), its line recorded in the phase log,
  v1.1's Results and row 390A.
- `plan_check.py 390A` on this plan (P1–P8) before it is pushed;
  `closeout_check.py 390A` and `verify_phase.sh 390A` at close.
- `COLLECTED_TEST_FLOOR` does not move: no test is added or removed, and
  the floor test is expected to pass unchanged.

## Non-goals

- Building the Quartermaster: `verify_phase.sh` run by a rank, a merge
  verdict in the digest, the planted bad PR, promotion. All of it is Phase
  391's, and this phase only gives it a row.
- Anything under `src/`, `tests/` or `.claude/skills/fleet/`, including the
  dispatcher's "not built yet" note and the `merge:needs-review` label text.
- Any migration, anything on live, any path under the data folder, seed
  content, splits, eval protocols.
- Row 385 (389A's deliverable) and its branch; the machine user and the
  master ruleset (F214's other half): the operator's and 389A's.
- Correcting the ROADMAP header's phase total, which already predates rows
  386 to 390A; a nit for a records phase.
- Closing issue #16: the planter's, once the resumed stage has started.
- Phase 390's own proofs and F219: 390's branch.

## Planned items

- [ ] 1. Row 391 in `docs/ROADMAP.md` after row 390A, 🔲, the wording in
      Logic 1; `roadmap_words.py 391 --check` exit 0; `roadmap_check.py`
      passing; one commit after `wholetree.sh`
- [ ] 2. `roadmap_check.py --self-test` run once, its known-bad cases red,
      the output in the phase log
- [ ] 3. `390A_phase_log.md`: dated entries from Step 0 on, the "No refute
      pass ran" line, the regression line
- [ ] 4. `wholetree.sh --full`, then `regression.sh`; the line recorded
- [ ] 5. v1.1 of this plan: every section as built, Deviations, Results
- [ ] 6. Row 390A to ✅ with the CLOSED date and the regression line; the
      handoff `docs/handoffs/YYYY-MM-DD_390A_closed.md`; the root
      `phase_log.md` section; `implementation.md`'s header and history row;
      the three documents to `completed/`
- [ ] 7. `closeout_check.py 390A` reporting nothing; `verify_phase.sh 390A`
      green; the PR naming issue #16, the regression line and the model-free
      run
