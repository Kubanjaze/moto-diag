# Phase 357 — Saved workflow runs: start, record, finish, resume, read back

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-09-28

## Goal

Row 357: "After 356. A migration adds tables for a workflow run and its
per-item results, tied to a bike or a work order, with the commands to
start, record and finish a run; a run can be resumed and read back.
Proposed by Gate 15 (272) with 356 (F165)."

F165 closes when a run and its per-item results are saved and read back.
Step 0 is `357_step0.md`. **The operator picked option A+ (2026-09-28):
the run's powertrain comes from `--powertrain` or the prompt, as in 356;
a bike whose stored value disagrees is refused; and `garage update` gains
`--powertrain`, so the refusal names its remedy.**

Done before this v1.0, as the prompt's first commits: F172 closed
(`67be350`), F175 filed and fixed and F176 filed (`5a4e821`).

## Logic

### Migration 073: two tables, three indexes, nothing else

As `357_step0.md` S0-3 gives it: `workflow_runs` (template, vehicle
`NOT NULL`, work order nullable, powertrain, status `in_progress` or
`complete`, `started_at`, `finished_at`) and `workflow_run_items` (run,
checklist item nullable, `sequence_number`, `title`, `required`, `result`
null or `pass`/`fail`/`skipped`, `diagnosis`, `notes`, `answered_at`,
unique on run and number). The CHECKs hold: a finished run has a finish
time, an answer has a time, a skip only on an optional item, a diagnosis
only on a fail. Rollback drops the indexes and both tables.
`SCHEMA_VERSION` 72 → 73.

### The repository, `motodiag/workflows/run_repo.py`

- `start_run(template, items, vehicle_id, work_order_id, powertrain)`:
  the run row and one item row per checklist item, in one transaction.
- `get_run(run_id)`, `get_run_items(run_id)`, `list_runs(vehicle_id=,
  work_order_id=)`, newest first.
- `record_result(run_id, sequence_number, result, notes, diagnosis)`:
  refuses a finished run, an unknown item number and a skip on a required
  item.
- `finish_run(run_id)`: refuses while any item is unanswered.

### The commands, in `cli/workflow.py`

```
motodiag workflow start <slug> (--bike SLUG | --vehicle-id N | --work-order N) [--powertrain P]
motodiag workflow record <run> <item#> pass|fail|skip [--notes TEXT]
motodiag workflow resume <run>
motodiag workflow finish <run>
motodiag workflow runs [--bike SLUG | --vehicle-id N | --work-order N]
motodiag workflow report <run>
```

`start`, in this order, stopping at the first refusal (exit 1, nothing
saved):
1. an unknown or retired slug, as `show` refuses it;
2. the bike: neither flag given → refused, pointing at `workflow run`;
   an unknown bike, an unknown work order, or a `completed` or
   `cancelled` work order → refused; a work order and a bike naming
   different vehicles → refused;
3. the powertrain: `--powertrain`, or else the prompt; a template that
   does not cover it → refused as in 356; **a bike stored with another
   powertrain → refused**, naming the stored value and the command
   `motodiag garage update --bike <slug> --powertrain <given>`;
4. the run is saved and its number printed; then the walk.

**The walk** (shared with `run`): each unanswered item as 356 prints it;
each answer is saved before the next item; a fail prints and saves the
diagnosis. After the last item, the summary, then "Finish this run now?"
(default yes), which calls `finish`. End of input or Ctrl-C leaves the
run unfinished with its answers saved, and prints how to resume.

`resume` walks the unanswered items of an unfinished run; a finished or
unknown run is refused. `record` sets one item (a fail stores the item's
current diagnosis). `finish` refuses while items are unanswered, naming
them. `report` prints the run's template, bike, work order, powertrain,
status and times, each item's number, title, result, notes and
diagnosis, and the counts.

### `garage update --powertrain`

The same three choices; one column, through `update_vehicle`. "Nothing to
update" still refuses when no field is given.

## Key Concepts

- **The database is the record; the engine is the walker.** Each walk
  builds `checklist_workflow` over the items it will ask. Counts come from
  the saved rows.
- **A run keeps the items it started with.** Title, number, required flag
  and the diagnosis shown at a fail are copied into its rows.
- **The powertrain is what the mechanic states, checked against the
  garage.** A disagreement is caught at the first run on that bike, and
  can be fixed in one command.

## Decisions

- **D1. A+**, the operator's pick. F174 stays open (the default remains).
- **D2. `workflow run` is unchanged** and still saves nothing; its 32
  tests are not edited.
- **D3. The vehicle foreign key is `ON DELETE RESTRICT`**, as
  `work_orders` has; F176 records the traceback that shares this shape.
- **D4. A closed work order (`completed`, `cancelled`) is refused.**
- **D5. Correcting an answer:** `record` may overwrite an item's answer
  until the run is finished; after that the run is read-only.
- **D6. No refute pass.** The phase ships code and a schema, no content
  rows; no claim rests on a document.

## Non-goals

- An API route or a mobile screen for runs.
- Fixing F174's defaults or F176.
- Deleting or reopening a run.

## Planned items

1. This v1.0 and the phase log, committed and pushed before code.
2. Migration 073 and `SCHEMA_VERSION`; its tests: tables and indexes
   present, the CHECKs refuse bad rows, rollback peels exactly 073, the
   head pinned only as `>= 73` and `== max(MIGRATIONS)`.
3. `run_repo.py`, the commands, `garage update --powertrain`.
4. `tests/test_phase357_saved_runs.py` through `CliRunner` on a
   `tmp_path` database (never `data/motodiag.db`): start by bike, by
   vehicle id, by work order; each refusal; record, resume, finish,
   runs, report; a retired template and an unknown slug refused; the
   powertrain disagreement and its remedy. Each assertion helper gets a
   planted known-bad output it must fail on. **F165's proof:**
   `test_a_run_and_its_results_are_saved_and_read_back`.
5. Gate 15 (`test_phase272_gate15.py`) green; the gap gates updated if the
   new module or its functions need it.
6. Mutations, `357_mutate.py RUN`, each seen red.
7. `wholetree.sh --full`, then the regression of record by
   `regression.sh`; `COLLECTED_TEST_FLOOR` raised.
8. The deploy: `357_deploy_scope.json` (the two tables and three indexes
   under `schema`, `schema_version` +1, nothing else), `deploy.py dryrun
   357`, the diff committed, then `deploy.py apply-live 357`. If any
   existing row would change, stop and ask.
9. Close-out: v1.1, row 357 ✅, handoff, `verify_phase.sh`.

## Verification Checklist

- [ ] v1.0 committed and pushed before code
- [ ] Migration 073 adds only; rollback peels it; no literal head pin
- [ ] Each of the five verbs driven by a CliRunner test
- [ ] Retired and unknown slugs refused by `start`
- [ ] Powertrain disagreement refused; `garage update --powertrain` fixes it
- [ ] Each assertion helper red on its planted output
- [ ] F165's proof test named and green
- [ ] Gate 15 green
- [ ] Mutations all red
- [ ] 244G scanner over `tests/`
- [ ] `wholetree.sh` before each commit; `--full` before the regression and the migration commit
- [ ] Regression of record by `regression.sh`; floor raised
- [ ] Dry-run diff committed; apply-live passes F172's exact check
- [ ] Handoff written; `verify_phase.sh` green
