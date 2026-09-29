# Phase 361 — F178 hybrid values, and F177 engine type — phase log

**Status:** 🚧 In progress
**Branch:** `phase-361` (Opus session, main checkout, the only writer)

---

### 2026-09-29 — Opened

The prompt is `docs/prompts/361_hybrid_values_and_engine_type.txt` (merged
in `af0d392`). The operator's decision (2026-09-29), verbatim:

> 361 with F177, write the prompts

It answered the recommendation of a small phase before Track O batch 1, run
the two-session way 360 was: the safety checker first, then the API's
powertrain values, then a mobile session for the snapshot.

Read first: the 360 handoff (`docs/handoffs/2026-09-29_360_closed.md`),
F177 and F178, the mobile repo's F179, 360's documents in `completed/`
(the migration 074 rebuild and the gate 11 stop), and the deploy skill.

- 361 is the next free number: the highest row was 360, and no phase
  document, handoff or ROADMAP line names 361.
- Row 361 🚧: `5fb84a8`, pushed. `roadmap_check.py` green; the row is 71
  words. `wholetree.sh` before the commit: 1480 passed.

### 2026-09-29 — Step 0

`361_step0.md`. What it found beyond the prompt:
- **The safety hole is wider than F178 says.** Any string outside
  `("ice", "hybrid")` other than `None` hides the seven rules: an empty
  string and `ICE` in capitals do too, not only the two hybrid variants.
- **The engine type has F178's shape exactly.** The API's literal holds
  `rotary`, `diesel`, `none`; the enum holds `electric_motor`, `hybrid`,
  `desmodromic`. Create refuses the first three with 400, an update stores
  them, and the API cannot record an electric motor. Nothing reads the
  engine type to hide anything.
- **Migration 074's own rebuild** carries `engine_type TEXT DEFAULT
  'four_stroke'`, so that is the live column's default.
- **Parts sourcing prints `engine_type: None`** for a NULL, 250B's trap.
- **No CLI command can correct an engine type.**
- Live: 10 bikes, all `ice` and `four_stroke`, schema 74. No value
  outside either enum, so part 2 changes no live row.

The per-option test counts were measured in four scratch worktrees, with
the mobile repo linked beside each so gate 11 ran against the real
snapshot. F178 alone breaks only gate 11's snapshot test and its three
reruns: the planned stop. F177: (a) 120, (b) 3, (c) 93.

**Stopped for the operator's pick (rule 1: a real fork).**

### 2026-09-29 — The operator's pick

The operator (2026-09-29), verbatim:

> (c). Keep the API's engine types aligned to the code's five, and file rotary and diesel as a finding for a later phase (until then such a bike is stored as unknown). List the engine-type value change in the phase log as an API change, so the mobile session accepts it and updates the app's engine-type options.

So:
- **F177 is (c):** `garage add` and `add-from-photo` ask for the engine
  type when it is not given and the powertrain is not `electric`, and save
  nothing without an answer; the API stores NULL when the field is absent.
- **The API's engine types are the enum's five.** Rotary and diesel go to
  a finding for a later phase; until then such a bike is stored as unknown.

## The API changes this phase makes (for the mobile session)

The mobile session (`moto-diag-mobile/docs/prompts/2026-09-29_api_snapshot_for_backend_361.txt`)
accepts a snapshot diff only when it changes these, and nothing else:

| schema | field | before | after |
|---|---|---|---|
| `VehicleCreateRequest` | `powertrain` | enum `ice, electric, hybrid_parallel, hybrid_series`, or null; no default | enum `ice, electric, hybrid`, or null; no default |
| `VehicleUpdateRequest` | `powertrain` | enum `ice, electric, hybrid_parallel, hybrid_series`, or null | enum `ice, electric, hybrid`, or null |
| `VehicleCreateRequest` | `engine_type` | enum `four_stroke, two_stroke, rotary, diesel, none`; default `four_stroke` | enum `four_stroke, two_stroke, electric_motor, hybrid, desmodromic`, or null; **no default** |
| `VehicleUpdateRequest` | `engine_type` | enum `four_stroke, two_stroke, rotary, diesel, none`, or null | enum `four_stroke, two_stroke, electric_motor, hybrid, desmodromic`, or null |
| path `GET /v1/vehicles` | query `powertrain` | the old four values | `ice, electric, hybrid` |

**What the app does with them:**
- **Powertrain options:** `ice`, `electric`, `hybrid`.
- **Engine-type options:** the five above, with labels. `rotary`, `diesel`
  and `none` go.
  - A bike that is rotary or diesel is left unknown (no engine type sent)
    until the later phase's finding adds them.
  - An electric bike's engine type is `electric_motor`, which replaces the
    app's "N/A" (`none`).
- **The add-bike form** asks for the engine type (the operator's (c),
  mirrored): no `four_stroke` preselect; the picker starts unchosen. Unlike
  F179's powertrain picker, it cannot simply be required, because a rotary
  or diesel bike has no value to pick until the finding is closed. So the
  form needs an answer that sends no engine type ("Not listed" or "Not
  sure"), which the API stores as unknown. How the form words that is the
  mobile session's call.
- **The edit screen** sends a powertrain or engine type only when the user
  chose one, with no `'ice'` or `'four_stroke'` fallback.

`VehicleResponse` does not change: `powertrain` and `engine_type` stay
`Optional[str]`. A bike already stored with an old value (none live) is
read back as it is.

### 2026-09-29 — v1.0, F180, and a commit made past a failed check

- **v1.0** is `da5dc0f`, the phase log's API change list with it.
- **The slip.** The command ran `wholetree.sh 2>&1 | tail -1 && git commit`.
  The pipe's exit was `tail`'s, so the commit ran although `wholetree.sh`
  printed FAILED: `finding_check` B2, because v1.0 cited F180 before the
  entry existed. It was caught before any push. F180 was filed with the
  `finding` skill (`be00cb6`), `wholetree.sh` then passed (1480), and both
  commits were pushed together. From here, `wholetree.sh` runs alone, its
  exit code is read, and only then is the commit made.
- **F180:** no engine-type value for a rotary or a diesel engine; such a
  bike is stored as unknown until a later phase adds them.

### 2026-09-29 — Part 1a: the safety checker (F178)

`engine/safety.py`: `_applies` shows every rule for any value outside
`PowertrainType`, not only for `None`.

- `tests/test_phase361_safety_unknown_powertrain.py`, 16 passed:
  - eight values outside the enum;
  - the controls (`electric` hides the fuel leak, `ice` and `hybrid` show
    it);
  - diagnose's safety panel on a bike stored as `hybrid_parallel`, `""`
    or `hybrid_series` by a raw insert.
- With the old checker restored, **10 fail**.
- The 12 test files that use the checker: 425 passed.
- 244G's scanner over `tests/`: clean.
- `wholetree.sh`: 1480 passed.

Committed `663accc`, pushed. **The fuel-leak hole is closed** before any
API change.

### 2026-09-29 — Part 1b and part 2 built

**Part 1b, the contract (F178):**
- `PowertrainLiteral` is `ice, electric, hybrid`;
- `update_vehicle` converts `powertrain` and `engine_type` through their
  enums, so every writer is refused a value outside them (`None` still
  clears).

**Part 2, F177 (c):**
- **Migration 075 and the model:**
  - `_vehicles_rebuild_074` is renamed `_vehicles_rebuild` and gains
    `engine_type_def`. 074's upgrade and rollback SQL hash as they did at
    `5fb84a8` (`b59b8ea2…`, `4f78892c…`), and a test holds both.
  - Migration 075 is in, and `SCHEMA_VERSION` is 75.
  - `VehicleBase.engine_type` defaults to None; both inserts bind NULL.
- **The API:** the engine-type literal is the enum's five, and create
  stores NULL when the field is absent.
- **The CLI:**
  - `garage add` and `add-from-photo` gain `--engine-type`; not given,
    electric derives `electric_motor`, and anything else asks;
  - no answer saves nothing; `unknown` stores NULL (D2);
  - `garage update --engine-type` sets the value, or clears it with
    `unknown`.
- **Parts sourcing** prints `unknown`.

**Tests:**
- `tests/test_phase361_contract_and_engine_type.py`: 51.
- The existing tests Step 0 predicted for (c) were updated, in 10 files:
  - `--engine-type four_stroke` in the gate 5, 6, 7, 11 and 14 flows and
    fixtures, 250B's fixture and 122's `garage add`: the value the old
    default stored;
  - `unknown` in 357's wrongly stated Energica, where the engine type is
    beside the point;
  - Phase 110's two default pins now pin None;
  - 360's rebuild test expects every migration from 074 on, not a head
    pin (F124).
- **Measured:** the 114 vehicle files plus both 361 files gave 3710
  passed and 4 failed. Before the updates they gave 97, exactly Step 0's
  93 for (c) plus F178's 4.
- **Mutations: 19/19 red** (`361_mutate.py`: safety 2, contract 3,
  F177 14).
- 244G's scanner over `tests/`: clean.

### 2026-09-29 — The planned stop: gate 11's contract snapshot

`wholetree.sh --full`: 3941 passed, **4 failed**, all gate 11:
- gate 12's and gate 13's reruns of gate 11;
- gate 13's rerun of gate 12;
- gate 14's rerun of gate 13.

Gate 11 itself reports exactly the four fields the API change list above
names, and nothing else:
`VehicleCreateRequest.engine_type`, `VehicleCreateRequest.powertrain`,
`VehicleUpdateRequest.engine_type`, `VehicleUpdateRequest.powertrain`:
changed.

- **Not committed:** part 1b and part 2 in `src/` and `tests/` (18
  files). The push guard needs a `--full` record for a commit to
  `migrations.py`, and `--full` is red until the snapshot is refreshed.
- **Backup:** `361_wip.patch` in this folder; `git apply --check` passes
  against `663accc`.
- **Committed:** this log, `361_mutate.py` and the patch.

The mobile session's prompt is
`moto-diag-mobile/docs/prompts/2026-09-29_api_snapshot_for_backend_361.txt`.
It serves this working tree from a scratch copy with `--skip-migrations`.
Until it pushes, this checkout does not switch branches or commit.

### 2026-09-29 — Pushing the stop's documents past a dirty tree

The push of `af9bb15` was refused. The push guard needs a whole-tree
record for the pushed commit's tree, and `wholetree.sh` writes one only
for a clean tree, which this one was not while `src/` and `tests/` held
the uncommitted work.
- **A clean worktree of `af9bb15` would not do.**
  `test_phase358_deploy_contract.py::test_the_defaults_name_the_repo_and_the_backup_folder`
  fails from a scratch location, so fast mode gave 1 failed, 1479 passed.
- **So the work was stashed in place** (`git stash push -u -- src tests`).
  - Before stashing: `git diff HEAD -- src tests` hashed `60f1d758…`, and
    the new test file `f6e0d36f…`.
  - On the clean tree, fast mode passed (1480) and wrote the record for
    `af9bb15`.
  - The stash was popped, and both hashes matched.
- The push then went through. The guard was not loosened.

### 2026-09-29 — Resumed: the mobile snapshot refreshed in moto-diag-mobile cd359e0

The operator (2026-09-29): "The mobile push has landed: moto-diag-mobile
cd359e0 on origin/main (its prompt is 1d5ee0a). … The snapshot diff is
exactly the five changes in your log's API table and nothing else;
src/api-types.ts matches. … Gate 11 from this checkout: 21 passed. Mobile:
jest 1194 passed in 99 suites, tsc exits 0. … The mobile session filed and
closed F181 (the edit screen's 'ice' and 'four_stroke' fallbacks) and
closed F177's app side."

Checked here:
- `cd359e0` is on `moto-diag-mobile` `origin/main`, and local `main` is
  level with it;
- this checkout was as it was left: HEAD `af9bb15`, 19 changed paths;
- **gate 11: 21 passed.**

- **FOLLOWUPS' numbering note** now reads "the highest assigned is
  **F181**, in the mobile file; this file's highest is **F180**", as
  `next_f_number.sh` reports. F181 is in the mobile file, so
  `finding_check` B1 failed on the old wording. (A first draft of this
  entry named the next free number; B2 counts any cited F-number without
  an entry, and failed on it in the first `--full` run, 3945 passed.)
- **The held work is committed from the working tree.** `361_wip.patch`,
  the backup, is removed in the same commit, since the commit now holds
  what it held.

### 2026-09-29 — The floor, and the regression of record

- **`COLLECTED_TEST_FLOOR` 9950 → 10018** (`83d0278`). Measured by
  diffing the collected test IDs against a `master` worktree: +68, none
  removed.
  - `test_phase361_safety_unknown_powertrain.py`, 16;
  - `test_phase361_contract_and_engine_type.py`, 51;
  - gate 15's `test_rolling_back_peels_every_successor[74]`, since 075
    now succeeds 74.
- `wholetree.sh --full` on the clean tree at `83d0278`: 3945 passed. That
  was the third `--full` since the resume. The first was red on B2 alone
  (the log named an F-number with no entry); the second was at `a8f84ad`.

Regression of record: 10018 passed, 0 failed, 0 skipped, 0 errors at `83d0278` (29 min 36 s wall, `python -m pytest -n auto --dist load`, exit 0)

### 2026-09-29 — The deploy: the dry run

- **Before, live, read only:** schema 74; 10 bikes, all `ice` and
  `four_stroke`; `sqlite_sequence` for `vehicles` 10.
- **Scope** (`361_deploy_scope.json`): `schema_version` +1;
  `"schema": {"changed": ["table vehicles"]}`; nothing else.
- **`deploy.py dryrun 361`:**
  - live 5844 rows, 90 tables, integrity ok;
  - backup `~/backups/motodiag/motodiag_pre361_20260929_174533.db`
    (retain-5 removed `motodiag_pre264_20260926_131946.db`);
  - applied `[75]` on the copy;
  - scope problems: none. F158 census: 36.
- **The diff (`361_dryrun_diff.md`):**
  - one `schema_version` row added (75);
  - `table vehicles` changed: its SQL is 074's with `engine_type TEXT`
    in place of `engine_type TEXT DEFAULT 'four_stroke'`;
  - **no existing row changed or removed** in any table;
  - the indexes do not show, so they are unchanged.
- **Not a rule-1 stop.** No existing row changes, the condition the
  operator set ("A dry run that changes any existing row is still a
  stop"). The diff is committed before apply-live.
