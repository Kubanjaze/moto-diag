# Phase 398 — The two stalls at the Red Team's clear (F251, F252)

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-11-08 (v1.0 `f8c7e62`)

---

## Goal

Unblocks 371 (K43 rule 4, K67), which would meet both stalls at its Red
Team stage. The operator: "yes, fix the two stalls now as phase 398".

After this phase:
1. (a) **F251.** The close-out check's A5 reads the regression of record
   only from a line that begins with "Regression of record:", as
   `regression.sh` prints it. A Red Team table that quotes the record (a
   row begins with `|`) no longer takes its place.
2. (b) **F252.** When the push gate refuses the Red Team's record commit,
   the stage adds `needs-hands`, keeps the cleared table and says what to
   do. Taking `needs-hands` off pushes the kept table through the gate on
   the branch as it then stands and sets `review:clear`, with no new
   round. A second refusal holds again.
3. Nothing loosens A5, C3, K9's three rounds or the push gate.

## The plan of record

Row 12 of "Next, in order" in `docs/reports/2026-10-12_plan_of_record.md`,
after 343 and before 371, built by a builder: the dated entry of
2026-11-05, on the operator's word recorded as K67 in `docs/decisions.md`.
The list does not change here.

## Logic

Causes and the measurements behind them: `398_step0.md`, S0-1 to S0-3.

1. **(a)** In `regression_record`, line 417 becomes
   `at = [i for i, ln in enumerate(lines) if ln.startswith(PREFIX)]`, and
   the docstring says why (F251). Nothing else in A5 changes: the shape,
   the outcome, the skip lines and both pins.
2. **(b), the hold.** In `stage_red_team`'s clear path, a `Stop` from
   the record push (the gate's refusal, a failed push, or a fast run held
   for space) no longer ends the stage as a stop. Instead:
   - `journal.hold(run, {...})` with `why: "record"`, the issue, phase,
     round, branch, the cleared table, and the wording finding's number
     and rows when there are any;
   - one comment with its own marker, `RECORD_M = "<!-- fleet-red-team-record:"`
     (read by no other due rule): the round cleared, the gate's reasons,
     the table is kept, and what to do: fix the branch so the gate
     passes, then take `needs-hands` off, and the fleet pushes the same
     table on the branch as it then stands, with no new round;
   - `needs-hands` added; `review:open` left as it is. The stage returns
     `held: …` and its journal ends; `held.json` keeps the run from
     `prune_runs` and its files from `clean_tmp`.
3. **(b), the release.** `next_stage` checks, before the Red Team's due
   rule: `review:open` on the issue and a held record run for it whose
   `RECORD_M` comment is newer than the issue's newest Red Team verdict
   marker and Red Team stop. Then `stage_red_record` runs:
   - a fresh stage clone of the branch as it now stands;
   - `record_in_log` with the kept table (and the kept finding, when
     there is one), committed with the round's subject; when that changes
     nothing (the table is already there), no commit and no push;
   - the push through the gate with a fresh fast run (`self.fast`);
   - `review:clear`, then `journal.release` on the held run.
   No model is called and no verdict marker is said, so `red_rounds` does
   not grow (K9).
   A `Stop` anywhere in it holds again: a new `RECORD_M` comment and
   `needs-hands`, the same held run kept. A cut-off `stage_red_record`
   resumes from its journal like every stage (`resume`, `STAGE_RANK`).
4. **Engineer holds stay apart.** `held_for` (the Engineer's) skips held
   runs whose `why` is `record`.
5. **Finish line:** both stalls replayed from their real artefacts; each
   new test red on the old code and green on the new; the mutations red.

## Rule-1 stops anticipated

None. The prompt's own stops (anything that loosens A5, C3, K9's three
rounds or the push gate) do not arise: A5 reads fewer lines and keeps
every test of the line it reads; C3 and the gate are unchanged; the
re-push makes no Red Team call.

## Tests

- `tests/test_phase398_two_stalls.py`, new:
  - (a) the refused logs at `9555925` (345) and `41370d2` (343), kept as
    fixtures under `.claude/skills/closeout/fixtures/f251/`: A5 passes
    each and reads the real record (12186 at `c2b0767`; 12292 at
    `ca580f6`); known-bad: each with its real record lines removed, and a
    log whose only prefixed line is a table row, still fail A5; the
    pinned exemptions still hold by equality (the existing tests, run).
  - (b) through the dispatcher's test world (389's): the real stop text
    of #45 and #50 planted as a G6 refusal on the record push leaves
    `needs-hands`, `review:open` and the `RECORD_M` comment, and keeps
    the table in `held.json`; taking `needs-hands` off after a fix pushes
    the same table and sets `review:clear`, with no model call and no new
    verdict marker; a second refusal holds again; the held run outlives a
    new `Fleet` (a restart) and `prune_runs` past `KEEP_RUNS`; an Engineer
    hold is not taken for a record hold.
- Old code: the new tests run against master's two files, red.
- Mutations, `398_mutate.py` (each red): M1 A5 back to `PREFIX in ln`;
  M2 the hold adds no `needs-hands`; M3 the table not kept; M4 the release
  runs a Red Team round; M5 the release sets `review:clear` without
  pushing; M6 a second refusal does not hold again; M7 `prune_runs`
  deletes a record hold; M8 `held_for` takes a record hold for the
  Engineer's.
- `COLLECTED_TEST_FLOOR` raised by a diff of collected ids.

## Non-goals

F253 (Q4's reading, filed at Step 0); any change to the Red Team's brief
or to C3; anything else about the fleet; issue #54 and its hold.

## Planned items

- [x] (a) A5 reads only a line that begins with the prefix
- [x] (b) the hold on a refused record push
- [x] (b) the release when `needs-hands` comes off
- [x] the tests, red on the old code; the mutations
- [x] the regression of record, the close-out, the handoff

## Deviations

1. **Three tests beyond v1.0's list**, each guarding a case the build met:
   the kept table already on the branch (as the operator pushed it by hand
   on #45 and #50) commits nothing and sets `review:clear`; a later Red
   Team verdict or stop ends the hold's due; a later clear releases an
   older kept table.
2. **The hold is said through `escalate`**, not a marker of its own
   (`RECORD_M` in v1.0): `not_resumable` already treats a stage cut off
   inside an escalation as resumable, and the hold's due rule reads the
   escalation's marker (`needs-hands rank=red-team`). The resumed stage
   returns at once when its label step is done.
3. **The hold's due rule reads comment order, not times**: the verdict
   marker and the hold can be posted in the same second.
4. **No `wholetree.sh --full` in this checkout.** The fenced run of record
   runs it first, in its own clone of `e816e02` (5075 passed, 36 skipped,
   exit 0), as `Fleet.check_run` always does.

## Results

- (a) Cause, re-measured: A5 took the Red Team table's quote on both
  refused logs and failed them; it now reads 12186 at `c2b0767` (345) and
  12292 at `ca580f6` (343). Known-bad: the logs without their record lines,
  and a log whose only prefixed line is a table row (which the old A5
  passed), fail. Both pins hold by equality; the line A5 reads changes in
  no closed log.
- (b) Cause, re-measured: the stop added no label and nothing was due.
  With #45's and #50's real refusal planted as G6 on the record push: the
  issue gets `needs-hands` and the comment, `review:open` stays, the table
  is in `held.json`; `needs-hands` off after a fix pushes the same table
  on the fixed branch and sets `review:clear`, with no model call and no
  new verdict; a second refusal holds again; the hold outlives a restart
  and `prune_runs`; a cut after the re-push's push resumes.
- `tests/test_phase398_two_stalls.py`: 17 passed. On master's code: 14
  failed, the 3 known-bad controls passing (they must fail A5 under
  either rule).
- `398_mutate.py`: 8/8 mutations red.
- `COLLECTED_TEST_FLOOR` 12397 to 12416 (+18 −0 against `f6aead1`).
- F253 filed (Q4 reads the prefix the old way; harmless on both logs).
- Regression of record: 12311 passed, 0 failed, 105 skipped, 0 errors at
  `e816e02`, coverage 88.04%, inside the fence, no fleet stage beside it.
- `dispatcher.py` changed: the fleet's copy moves to master and
  `motodiag-fleet.service` restarts after the merge (the handoff's block).

## Version history

| version | date | what |
|---|---|---|
| 1.0 | 2026-11-08 | the plan (`f8c7e62`) |
| 1.1 | 2026-11-08 | built (`e816e02`); Deviations and Results |
