# Phase 356 — In-memory workflow runner: `motodiag workflow run <slug>`

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-09-28

## Goal

Row 356: "`motodiag workflow run <slug>` connects a template's checklist
to Phase 82's step engine: each item in order, pass or fail recorded as
the mechanic answers, the template's diagnosis printed on a fail, a
summary at the end. Nothing is saved and there is no schema change.
Decides how a run chooses its powertrain, since items carry none."

Proposed by Gate 15 (272), which found that no workflow can be run
(F165). Step 0 is `356_step0.md`. **The operator picked option A
(2026-09-28): the run asks for a powertrain, or takes `--powertrain`, and
refuses a template that does not cover it.**

## Logic

### The command

```
motodiag workflow run <slug> [--powertrain ice|electric|hybrid]
```

In this order, stopping at the first refusal (exit 1):
1. **Unknown slug:** `No workflow template with slug '<slug>'.` and the
   hint to run `workflow list`, as `show` prints.
2. **Retired template:** `<slug>: <description>`, as `show` prints.
3. **Powertrain:** `--powertrain`, or else a prompt,
   `Powertrain (ice, electric, hybrid):`. A template whose
   `applicable_powertrains` does not name it is refused:
   `<slug> covers ice, hybrid, not electric.`
4. **The header:** the name, then `<slug> · for <powertrain> · <n> items`.
5. **Each item, in `sequence_number` order:** its number, title and
   "(optional)" flag, then its description, instruction, Pass and Fail
   lines and tools, as `show` prints them. Then the prompt:
   - required: `Result (p/f)`;
   - optional: `Result (p/f/s)`.

   Any other answer is asked again (click's `Choice`). The answer goes to
   the engine's `report_result`. On a fail, the item's
   `diagnosis_if_fail` is printed at once as `Diagnosis: …`.
6. **The summary:** `<n> passed, <n> failed, <n> skipped of <n>`, then
   each failed item's number, title and diagnosis, then one line saying
   nothing was saved. Exit 0: a run that finds faults has still run.

### The engine

`DiagnosticWorkflow` gains `stop_on_fail: bool = True`. `is_complete()`
ends a run on a failed step with a working diagnosis only when it is
true. The default keeps Phase 82's behaviour; the runner sets it false.

### The mapping

`motodiag/workflows/runner.py`, one function,
`checklist_workflow(template, items) -> DiagnosticWorkflow`:
`step_number` ← `sequence_number`, `test_instruction` ←
`instruction_text`, `expected_pass`, `expected_fail`,
`diagnosis_if_fail` as they are; `workflow_id` is the slug,
`workflow_type` the category, `max_steps` the item count,
`stop_on_fail=False`. The command keeps the item list beside the steps,
by index, for what the engine has no field for (title, description,
required, tools).

## Key Concepts

- **A checklist is not a decision tree.** Phase 82's engine concludes at
  the first fail; a checklist records every item. The flag is the only
  engine change.
- **The powertrain gates the template, nothing else.** Items carry none,
  so none is filtered. Powertrain-specific steps in a template that
  covers both kinds are optional (272's S0-4), and the mechanic skips
  them.
- **Refusals come before the first question.** A retired or unknown slug,
  or an uncovered powertrain, never reaches item 1.

## Decisions

- **D1. Option A**, the operator's pick. The garage link waits for 357.
- **D2. Required items take pass or fail; optional items also take
  skip.** The row says "pass or fail". The engine's `unclear` is not
  offered.
- **D3. The runner module has one caller now; 357 is the planned
  second** (saved runs build the same workflow), so the mapping lives in
  `motodiag.workflows`, not in the CLI.
- **D4. No refute pass.** The phase ships code and no content rows: no
  claim rests on a document.
- **D5. F174 (garage `--powertrain` defaults to `ice`) is filed, not
  fixed**, at the operator's word.

## Non-goals

- Saving a run, resuming one, or any table: row 357.
- A bike or work-order link, or reading the garage: 357.
- An API route or a mobile screen.
- Fixing F172, F173 or F174.

## Planned items

1. Row 356 🚧; F172 and F173 (`e86be59`); Step 0 (`7cab578`).
2. F174 filed; this v1.0 and the phase log, committed and pushed before
   code.
3. `stop_on_fail` in `engine/workflows.py`, with its test.
4. `workflows/runner.py` and `workflow run` in `cli/workflow.py`.
5. `tests/test_phase356_workflow_run.py`, through `CliRunner` with
   input, on a fresh `tmp_path` database (never `data/motodiag.db`):
   - a full pass;
   - a fail showing its diagnosis, and the run going on to the end;
   - an optional item skipped, and a required item refusing a skip;
   - a retired slug, and an unknown slug;
   - the powertrain by flag and by prompt, each refusing an uncovered
     template;
   - every active template run with all passes for every powertrain it
     covers, and refused for every one it does not;
   - the database unchanged by a run.

   Each assertion helper gets a planted known-bad input it must fail on,
   as a permanent test.
6. Mutations of the source, each seen red, with the script committed.
7. `COLLECTED_TEST_FLOOR` raised at the regression.
8. Close-out: v1.1, row 356 ✅, history row, handoff.

## Verification Checklist

- [ ] F174 filed; `finding_check.py` green
- [ ] `stop_on_fail` default keeps Phase 82's and Gate 3's tests green
- [ ] Each of the five named cases driven through `CliRunner` with input
- [ ] Each assertion helper red on its planted input
- [ ] Gate 15 green
- [ ] Mutations all red
- [ ] 244G scanner over the new test file
- [ ] `wholetree.sh` before each commit; `--full` before the regression
- [ ] Regression of record by `regression.sh`
- [ ] `COLLECTED_TEST_FLOOR` raised, the reason in the commit
- [ ] F165's status stated
- [ ] Handoff written
