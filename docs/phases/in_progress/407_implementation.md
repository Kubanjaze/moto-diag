# Phase 407 — A decision for the operator is asked first, with its label (F285)

**Version 1.0, 2026-11-20.** Built by the advisor session on the Mac (K96),
on `phase-407-the-operators-decision-asked-first` from master `3908d99`.
Classification: **extension** (`407_step0.md`). This plan is committed and
pushed before any code.

## Goal

When the fleet's first step calls a phase a reshape, the operator's call
(`plan_check` P4), the dispatcher asks the operator at once and labels the
issue `needs-admiral`. No plan-writer call is spent on a plan the checklist
is bound to refuse, and nothing waits on the operator without the label.
The operator's release (the decision recorded, the report relabelled, the
label taken off) starts the plan writer as today. This closes F285.

## The plan of record

407 runs beside the 'Next, in order' list (K96; the plan of record's entry
"2026-11-20, later"). The fleet does not wait for it, and it does not wait
for the fleet. It arrives as a pull request the operator merges after the
advisor's review (K93's way). It takes effect when the fleet's code copy is
moved after the merge (`remote.py fleet-move`), which 405's merge needs
anyway.

## Logic

### 1. One helper, `Fleet.ask_reshape`

`ask_reshape(issue, rank, phase, step0_text) -> bool`: when
`plan_check.classification(step0_text)` is `reshape`, it escalates
`needs-admiral` for `rank` through the existing `escalate` and returns
True; otherwise it returns False and does nothing. The question, in plain
English:

> Phase N's first step calls it a reshape, which is your call: REASON.
> Answer in your own words: (A) the fleet builds it, the report's
> classification becomes extension with your words beside it, as K90 and
> K95 did; or (B) a builder session builds it. Once the report says
> extension, take `needs-admiral` off and the plan writer starts.

REASON is the report's own sentence after `**reshape.**` on its
Classification line, up to its first full stop, at most 300 characters.
`escalate` adds "The fleet leaves this issue alone until the operator takes
`needs-admiral` off." The helper keeps both stages' complexity where it is.

### 2. The scout stage

`stage_scout`, after the `fleet-scout: step0` marker and before
`label_once(issue, "step0:done")`, calls `ask_reshape(issue, "scout", ...)`
on the report it wrote. It still labels `step0:done` either way, so taking
`needs-admiral` off makes the plan writer due as the label put back does
today: no plan-writer marker is newer than `step0:done`.

### 3. The plan writer's stage

`stage_captain`, after it has read the report from its stage clone and
before `captain.write_plan`, calls `ask_reshape(issue, "captain", ...)`.
On True it returns "reshape: the operator asked" and calls no model. This
covers a report written before 407 or edited by hand. Its marker,
`needs-admiral rank=captain`, is not one of the plan writer's due markers,
so the release works the same way.

### 4. The record

- The dispatcher's docstring: the reshape case beside "A stage that needs
  the operator adds `needs-admiral`".
- `.claude/skills/fleet/SKILL.md`: a paragraph under the stages, the
  question and the release.
- `.claude/skills/fleet/CHANGELOG.md`: the dated entry.
- F285 closed by this phase, at the close-out.

## Rule-1 stops anticipated

None. K96 is the operator's word for exactly this. A change to a label's
meaning, to `plan_check`, to any rank's brief, or to another stop is outside
it, and would be a stop.

## Tests

`tests/test_phase407_reshape_asks_first.py`, on the `world` stand-ins of
`tests/test_phase389_dispatcher.py` (GitHub and the models stood in, no
network):

1. A reshape report: after the scout's cycle the issue has `mission`,
   `needs-admiral` and `step0:done`, and one comment carrying
   `needs-admiral rank=scout` and the question with the report's reason. The
   next cycle starts no stage: no model call.
2. An extension report, the control: `mission` and `step0:done` only, and
   the plan writer runs on the next cycle.
3. A reshape report reaching the plan writer's stage (no label, as for a
   report written before 407): `needs-admiral rank=captain` and the label,
   and no model call.
4. The release: the report relabelled extension on the branch and the label
   taken off; the next cycle runs the plan writer, which writes v1.0.
5. `ask_reshape` alone: greenfield, extension and a missing Classification
   line ask nothing; reshape asks once, and a second call on the same issue
   posts no second comment (the step asks GitHub first).

Mutations (`407_mutate.py`, N/N red): the scout's call removed; the
captain's call removed; the helper asking on every word; the helper asking
on none; `step0:done` not applied after a reshape; the guard's early return
removed (the model still called).

`COLLECTED_TEST_FLOOR` rises by the new tests' ids, by a diff of collected
ids, with the reason in the commit message.

## Non-goals

- Any other stop: a plan writer's or the Executive Officer's stop for a
  fleet failure keeps its note and its labels.
- `plan_check`, `scout.py`, `captain.py`, any rank's brief or any label's
  meaning.
- The release itself: relabelling stays the advisor's, on the operator's
  word, as for 404 and 405.
- The live database, the desktop's units, the way in.

## Deviations

To be written at v1.1.

## Results

To be written at v1.1.

## Planned items

- [ ] `Fleet.ask_reshape`, and its calls in `stage_scout` and `stage_captain`
- [ ] The five tests, each seen red; `407_mutate.py` N/N
- [ ] The docstring, the fleet skill's `SKILL.md` and `CHANGELOG.md`
- [ ] The regression of record, the close-out and the handoff
- [ ] The branch ready for a pull request the operator merges after review

## Version history

| version | date | change |
|---|---|---|
| 1.0 | 2026-11-20 | The plan, from Step 0 (K96). |
