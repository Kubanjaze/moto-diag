# Phase 407 — A decision for the operator is asked first, with its label (F285)

**Version 1.1, 2026-11-20.** Built by the advisor session on the Mac (K96),
on `phase-407-the-operators-decision-asked-first` from master `3908d99`.
Classification: **extension** (`407_step0.md`). v1.0 was committed and
pushed before any code (`68b91aa`); the build is `6eaf13c`, the review's
fixes `df7d11a`.

## Goal

When the fleet's first step calls a phase a reshape, the operator's call
(`plan_check` P4), the dispatcher asks the operator at once and labels the
issue `needs-admiral`. No plan-writer call is spent on a plan the checklist
is bound to refuse, and nothing waits on the operator without the label.
The operator's release (the decision recorded, the report relabelled, the
label taken off) starts the plan writer as today. This closes F285, once
merged and the fleet's code copy has moved.

## The plan of record

407 runs beside the 'Next, in order' list (K96; the plan of record's entry
"2026-11-20, later"). The fleet does not wait for it, and it does not wait
for the fleet. It arrives as a pull request the operator merges after the
advisor's review (K93's way). It takes effect when the fleet's code copy is
moved after the merge (`remote.py fleet-move`), which 405's merge needs
anyway.

## Logic

### 1. One helper, `Fleet.ask_reshape`, and the reason it quotes

`ask_reshape(issue, rank, phase, step0_text) -> bool`: when
`plan_check.classification(step0_text)` is `reshape`, it escalates
`needs-admiral` for `rank` through the existing `escalate` and returns
True; otherwise it returns False and does nothing. The question, in plain
English:

> Phase N's first step calls it a reshape, which is your call: REASON.
> Answer in your own words: (A) the fleet builds it, and the report's line
> becomes `Classification: extension`, that word first and your words after
> it, as you decided for phases 404 and 405; or (B) a builder session builds
> it. Once the report says extension, take `needs-admiral` off and the plan
> writer starts.

REASON is `reshape_reason(step0_text)`, a module function: the text after
`reshape` on the Classification line, read on that line only, cut at the
first full stop followed by a capital (so "e.g. the" stays whole), at most
300 characters, with no `*` or backtick (it sits inside `escalate`'s bold)
and an @name put in a code span, so GitHub notifies no one. `escalate` adds
"The fleet leaves this issue alone until the operator takes `needs-admiral`
off." The helper keeps both stages' complexity where it is.

### 2. The scout stage

`stage_scout`, after the `fleet-scout: step0` marker, labels `step0:done`
and then calls `ask_reshape(issue, "scout", ...)` on the report it wrote.
The label comes first, so a question GitHub refuses leaves the plan writer
due, and its guard (3) asks again with no model call. Taking `needs-admiral`
off makes the plan writer due as the label put back does today: no
plan-writer marker is newer than `step0:done`. On a reshape the marker's
note says "Next: the operator's call, asked below." instead of "Next: the
Captain writes v1.0."

### 3. The plan writer's stage

`stage_captain`, after it has read the report from its stage clone and
before `captain.write_plan`, calls `ask_reshape(issue, "captain", ...)`.
On True it returns "reshape: the operator is asked" and calls no model.
This covers a report written before 407 or edited by hand. Its marker,
`needs-admiral rank=captain`, is not one of the plan writer's due markers,
so the release works the same way.

### 4. The sweep on a held issue

`sweep`, on an issue that carries `needs-admiral` or `needs-hands`, sweeps
only the hold: no rank moves a label under it, so naming the rank whose
label it is (the Captain, for `step0:done`) pointed the operator the wrong
way.

### 5. The record

- The dispatcher's docstring: the reshape case beside "A stage that needs
  the operator adds `needs-admiral`", and the sweep on a held issue.
- `.claude/skills/fleet/SKILL.md`: a section after the stages, the question
  and the release; the test list.
- `.claude/skills/fleet/CHANGELOG.md`: the dated entry, with two known
  limits.
- F285 closed by this phase, at the close-out.

## Rule-1 stops anticipated

None. K96 is the operator's word for exactly this. A change to a label's
meaning, to `plan_check`, to any rank's brief, or to another stop is outside
it, and would be a stop. None was met.

## Tests

`tests/test_phase407_reshape_asks_first.py`, on the `world` stand-ins of
`tests/test_phase389_dispatcher.py` (GitHub and the models stood in, no
network), and for one test the kill harness of
`tests/test_phase390_resume.py`:

1. A reshape report: after the scout's cycle the issue has `mission`,
   `needs-admiral` and `step0:done`, one comment carrying
   `needs-admiral rank=scout` and the question with the report's reason, and
   the scout's note naming the operator's call. The next cycle starts no
   stage: no model call, no comment, no ask from the plan writer.
2. An extension report, the control: `mission` and `step0:done` only, the
   note naming the plan writer, and the plan writer runs on the next cycle.
3. A reshape report reaching the plan writer's stage (no label, as for a
   report written before 407): `needs-admiral rank=captain` and the label,
   and no model call.
4. The release: the report relabelled extension on the branch and the label
   taken off; the next cycle runs the plan writer, which writes v1.0. Also
   after the plan writer's own ask.
5. `ask_reshape` alone: greenfield, extension and a missing Classification
   line ask nothing; reshape asks once. A second question on the same issue
   is not posted by a resumed stage cut between its question and its label
   (390's kill harness): the step asks GitHub first.
6. A question GitHub refuses: the scout stops with `step0:done` on, and the
   plan writer's guard asks on the next cycle with no model call.
7. `reshape_reason` on four lines: an empty reason does not take the next
   heading; "e.g." does not cut it; `**` and an @name are made safe; an
   address's @ is left alone.
8. A held issue's sweep names the hold, not the Captain.

Mutations (`407_mutate.py`, 16/16 red): the scout's call removed; the
plan writer's call removed; the helper asking on every word; the helper
asking on none; `step0:done` not applied after a reshape; the guard's early
return removed (the model still called); the reason not cut; the scout
asking before it labels; a held issue worked; the reason running onto the
next line; the reason cut at "e.g."; an @name left bare; the reason keeping
its asterisks; the sweep naming every label on a held issue; the scout's
note always naming the plan writer; a resumed question not asking GitHub
first.

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

1. **The order in the scout stage.** v1.0 asked before `step0:done`. An
   independent review of the build (`407_phase_log.md`, "the review, and
   its fixes", 1) showed that a question GitHub refused then left only
   `mission` on the issue, with nothing due after a release. The label now
   comes first.
2. **Test 5's second claim** ("a second call on the same issue posts no
   second comment") holds only inside a stage's journal, on a resumed
   stage; outside one, `step()` runs every write. It is tested where it
   holds, on 390's kill harness, and the two direct calls of v1.0's
   wording are not made.
3. **Beyond v1.0, from the same review:** the reason made safe for a comment
   (`reshape_reason`); the question names no K-id and says the
   Classification line's word comes first; the scout's note on a reshape;
   and the sweep on a held issue, which changes the sweep for every held
   issue, not only a reshape. Each is in Logic above, with its test and
   mutation.
4. **No bug-fix register.** The review's points were found and fixed before
   the regression of record, in the phase's own new code and in the sweep
   next to it; the log lists each with its fix and test, as 406's did.
5. **Two known limits, not changed** (the fleet's `CHANGELOG.md`): a
   Classification line that does not start with its word still costs two
   plan-writer calls with no label, as before 407; a plan writer cut between
   its question and the label, with the report relabelled while the
   dispatcher was down, puts `needs-admiral` back on resume.

## Results

- `Fleet.ask_reshape`, `reshape_reason`, the scout stage's order and note,
  the plan writer's guard, and the sweep on a held issue, in
  `.claude/skills/fleet/dispatcher.py` (lint findings 9 before, 9 after).
- 16 tests in `tests/test_phase407_reshape_asks_first.py`; with 388's,
  389's, 390's and 392's suites, 146 passed. `407_mutate.py` 16/16 red.
- `COLLECTED_TEST_FLOOR` 12960 → 12968 (the build) → 12976 (the review's
  fixes), each by a diff of collected ids: +16 −0 in all, all in the new
  file.
- Regression of record: 12927 passed, 0 failed, 49 skipped, 0 errors at
  `df7d11a` (52 min 56 s wall, on the Mac, on battery), after
  `wholetree.sh --full` on the same commit (5349 passed, 1 skipped). The 49
  skips are the Mac's pinned ones (the phase log lists them). Line coverage
  of record 88.36% (the pin is 87.50%).
- No migration, no change to live. F285 closed, once merged and the
  fleet's code copy has moved.

## Planned items

- [x] `Fleet.ask_reshape`, and its calls in `stage_scout` and `stage_captain`
- [x] The tests, each seen red; `407_mutate.py` 16/16
- [x] The docstring, the fleet skill's `SKILL.md` and `CHANGELOG.md`
- [x] The regression of record, the close-out and the handoff
- [x] The branch ready for a pull request the operator merges after review

## Version history

| version | date | change |
|---|---|---|
| 1.0 | 2026-11-20 | The plan, from Step 0 (K96). |
| 1.1 | 2026-11-20 | Every section brought to what was built; the review's fixes (the label before the question, the reason, the sweep on a held issue); Deviations and Results. |
