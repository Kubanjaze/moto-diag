# Phase 361 — F178 hybrid values, and F177 engine type

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-09-29

## Goal

Row 361: "The operator's decision of 2026-09-29, before Track O batch 1.
F178 first, a safety defect: the safety checker reads any powertrain
outside the enum as unknown, so every rule shows; then the API accepts only
`ice`, `electric` and `hybrid`, on create and update. F177: a bike's engine
type is never assumed `four_stroke`; migration 075 drops the column
default. The API change needs the mobile snapshot refreshed, a planned
stop."

Step 0 is `361_step0.md`. **The operator's pick (2026-09-29), verbatim:**
"(c). Keep the API's engine types aligned to the code's five, and file
rotary and diesel as a finding for a later phase (until then such a bike is
stored as unknown). List the engine-type value change in the phase log as
an API change, so the mobile session accepts it and updates the app's
engine-type options."

F178 closes when no stored powertrain value can hide a safety rule, and
the API accepts only the enum's values on create and update. F177 closes
when no path stores `four_stroke` that nobody stated, and every reader's
handling of an unknown engine type is tested.

## Logic

### Part 1: F178

**1a. The safety checker (committed first; no API change).**
- `engine/safety.py` builds `_KNOWN_POWERTRAINS` from `PowertrainType`.
- `_applies` shows every rule when `self.powertrain` is not one of them,
  where today it does so only for `None`. So `None`, `""`, `ICE`,
  `hybrid_parallel` and any other value outside the enum all read as
  unknown. The docstring's invariant then holds for every stored value.
- A stated `electric` still drops the seven combustion rules, and `ice` and
  `hybrid` still show them.

**1b. The contract.**
- `PowertrainLiteral` becomes `ice, electric, hybrid`. It types the
  create and update requests and the list filter.
- `update_vehicle` (`vehicles/registry.py`) converts `powertrain` and
  `engine_type` through their enums before writing, so any writer (the
  API's PATCH, the CLI, a script) is refused a value outside them with
  `ValueError`. `None` is left alone: it is how `transmission` clears, and
  the other fields' callers drop it before the call.
- `POST /v1/vehicles` with `hybrid` → 201, stored `hybrid`. The variants
  → 422, from the literal.

### Part 2: F177, option (c)

**Migration 075 rebuilds `vehicles` without the engine-type default.**
- `_vehicles_rebuild_074` is renamed `_vehicles_rebuild` and gains an
  `engine_type_def` argument whose default is today's text. 074's upgrade
  and rollback SQL stay byte for byte what they were; a test compares them
  with the text `5fb84a8` produced.
- 075's upgrade is `powertrain TEXT`, `engine_type TEXT`; its rollback is
  `powertrain TEXT`, `engine_type TEXT DEFAULT 'four_stroke'`, the
  pre-075 schema. 074's pattern otherwise: foreign keys off, every column
  copied by name, the sequence carried, the three indexes recreated
  unchanged. No row changes. `SCHEMA_VERSION` 74 → 75.

**The model and the registry.** `VehicleBase.engine_type` becomes
`Optional[EngineType] = None`. Both registry inserts bind `None` as NULL.

**The API.**
- `EngineTypeLiteral` becomes the enum's five: `four_stroke`,
  `two_stroke`, `electric_motor`, `hybrid`, `desmodromic`.
- `VehicleCreateRequest.engine_type: Optional[EngineTypeLiteral] = None`;
  absent is stored as NULL. Create converts through the enum; update is
  checked in the registry (1b).

**The CLI.**
- `garage add` and `garage add-from-photo` gain `--engine-type`, choices
  the enum's five plus `unknown`.
- When it is not given:
  - a stated `electric` powertrain gives `electric_motor`, since that
    follows from what was stated;
  - otherwise the command asks: `Engine type (four_stroke, two_stroke,
    electric_motor, hybrid, desmodromic, unknown)`;
  - with no answer (end of input, no terminal) it refuses: "No engine type
    given: add --engine-type …. Nothing was saved." Exit 1, as 360's
    powertrain question does.
- **`unknown` stores NULL.** It is how a mechanic records a rotary or
  diesel bike until the finding adds those values (the operator's "until
  then such a bike is stored as unknown"), and a bike whose engine they do
  not know. A stated unknown is not an assumed value.
- `add-from-photo` asks after the powertrain is settled. The vision guess
  has no engine type.
- `garage update` gains `--engine-type`, the same six choices; `unknown`
  sets it back to NULL. There is no CLI way to correct it today (S0-2).

**The readers:**
- Parts sourcing prints `engine_type: unknown` for NULL, not `None`.
- Diagnose (the prompt leaves the line out; the cache key carries `None`)
  and the API read (`null`) are unchanged, and each gets a test on a bike
  stored as NULL.

### Part 3: the mobile stop

Part 1a is committed first. When the rest is built and the only red is
gate 11's snapshot test and the gates that re-run it, the build stops.
What the push guard will not accept stays in the working tree, with
`361_wip.patch` in this folder as a backup. The mobile session serves this
working tree from a scratch copy with `--skip-migrations`; no branch switch
and no commit while it runs. After its push: gate 11 re-run, commit, and
the rest of the phase. The API changes it must accept are listed in the
phase log.

## Key Concepts

- **Unknown shows everything.** The safety checker's only safe reading of
  a value it does not recognise is the one it already gives `None`.
- **NULL means "nobody said", or "said unknown".** Both are honest; a
  default of `four_stroke` was neither.
- **A contract is two repositories.** Any change to an API model moves
  gate 11 until the mobile snapshot follows (360's lesson).

## Decisions

- **D1. (c)**, the operator's pick, and the enum's five engine types.
- **D2. `unknown` is a CLI choice for the engine type**, storing NULL. The
  operator's words say a rotary or diesel bike is stored as unknown; with
  only the five choices, the question could not be answered for one.
- **D3. The enum check is in `update_vehicle`**, not only in the route, so
  every writer is held to it.
- **D4. The safety checker does not normalise case.** `ICE` reads as
  unknown and shows every rule; that is the safe direction, and nothing
  writes a capitalised value once 1b is in.
- **D5. No live row changes.** Ten bikes, all `ice` and `four_stroke`,
  none outside either enum (S0-4, S0-7).
- **D6. No refute pass.** The phase ships code and a schema, no content
  rows.
- **D7. `garage list` is unchanged.** It does not show the engine type;
  the operator can add it later.

## Non-goals

- Adding `rotary` or `diesel` to the enum: a finding, for a later phase.
- The app's changes, which are the mobile session's.
- Changing any existing live row.
- Letting the API clear a powertrain or engine type back to unknown (360's
  D5).

## Planned items

1. This v1.0, committed and pushed before code.
2. **Part 1a**, `tests/test_phase361_safety_unknown_powertrain.py`:
   - every value outside the enum (`None`, `""`, `ICE`, `Hybrid`,
     `hybrid_parallel`, `hybrid_series`, `petrol`) compiles all 19 rules and
     shows the fuel-leak alert;
   - controls: `electric` hides it, `ice` and `hybrid` show it;
   - through diagnose's `_render_safety`, on a bike row stored as
     `hybrid_parallel` by a raw insert;
   - a planted return to `is None` fails it (the mutation script).

   `wholetree.sh`, commit, push.
3. The finding for rotary and diesel (the `finding` skill; F180 is next).
4. **Part 1b and part 2**, with
   `tests/test_phase361_contract_and_engine_type.py`:
   - the API: `hybrid` created; the variants and old engine types 422 on
     create and update; an update with a value outside the enum through
     `update_vehicle` raises; `engine_type` absent stored as NULL;
   - migration 075: every row and value kept, the default gone, the
     indexes' SQL unchanged, the sequence kept after a deleted top row, the
     rollback restoring `DEFAULT 'four_stroke'`, 074's SQL unchanged, a raw
     insert storing NULL; the head pinned only as `>= 75` and
     `== max(MIGRATIONS)`;
   - the CLI: each entry point with no engine type asks, refuses on no
     answer, derives `electric_motor` for electric, stores NULL for
     `unknown`; `garage update --engine-type` sets and clears;
   - each reader on a bike stored as NULL: the diagnose prompt, the cache
     key, parts sourcing, the API read.

   The 93 existing tests Step 0 measured under (c) are updated:
   fixtures gain `--engine-type four_stroke`; the default pins become
   pins of the new rule.
5. Mutations, `361_mutate.py`, one per rule, each seen red.
6. `wholetree.sh --full`. **The planned stop**: gate 11 and its reruns
   only. The patch saved; the operator told.
7. After the mobile push: gate 11 re-run, the rest committed.
8. `--full` again, the regression of record by `regression.sh`,
   `COLLECTED_TEST_FLOOR` raised.
9. The deploy: `361_deploy_scope.json` (`schema_version` +1; `"schema":
   {"changed": ["table vehicles"]}`), `deploy.py dryrun 361`, the diff
   committed and shown; stop if any existing row would change;
   `deploy.py apply-live 361`; the sequence, the defaults and
   `foreign_key_check` read by hand after.
10. Close-out: F177 and F178 closed, v1.1, row 361 ✅, handoff,
    `verify_phase.sh`.

## Verification Checklist

- [ ] v1.0 committed and pushed before code
- [ ] No stored powertrain value hides a safety rule; the planted `is None` fails the test
- [ ] The API accepts only the enum's values, on create and update, and `update_vehicle` refuses others
- [ ] Migration 075 keeps every value; 074's SQL unchanged; the dry run shows no existing row changed
- [ ] No path stores `four_stroke` that nobody stated
- [ ] Each reader tested on a bike with an unknown engine type
- [ ] Mutations all red
- [ ] 244G scanner over the new tests
- [ ] `wholetree.sh` before each commit; `--full` before the migration commit and the regression
- [ ] The mobile snapshot refreshed; gate 11 green
- [ ] Regression of record by `regression.sh`; floor raised
- [ ] Dry-run diff committed; apply-live passes F172's exact check
- [ ] The rotary and diesel finding filed; F177, F178 closed
- [ ] Handoff written; `verify_phase.sh` run after the merge
