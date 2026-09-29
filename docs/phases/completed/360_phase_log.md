# Phase 360 — F174 powertrain default, and the edit guard — phase log

**Status:** ✅ Complete (2026-09-29)
**Branch:** `phase-360` (Opus session, main checkout, the only writer)

---

### 2026-09-28 — Opened

The prompt is `docs/prompts/360_powertrain_and_edit_guard.txt` (merged in
`145d0b6`). The operator's decisions of 2026-09-28, verbatim:

> 1, 2, 3, 5 as recommended.

> add to the F174 phase: enforce the edit rule. 356 and 357 both edited source without the Edit tool — a written rule broken twice. PreToolUse hook on Bash that blocks sed -i, heredoc/redirect writes into src/ and tests/, same fail-closed pattern as the push guard, with a planted positive control per blocked form.

Recommendation 5 was a small phase for F174 before Track O batch 1.

Read first: the 357 handoff (`docs/handoffs/2026-09-28_357_closed.md`),
F174 and 357's amendment, the Track O triage with the decisions at its top,
the deploy skill, and `pre_push_guard.sh` / `_pre_push_guard.py`.

- 360 is the next free number: the highest row was 359, and no phase
  document or handoff names 360.
- Row 360 🚧: `dfb0a9a`, pushed. `roadmap_check.py` green; the row is 61
  words. `wholetree.sh` before the commit: 1480 passed.

### 2026-09-28 — The session's machine slept mid-Step 0

After `dfb0a9a`, the machine slept before any Step 0 document was
written. The operator measured, and this session re-measured:
- only `dfb0a9a` had landed, and it was pushed;
- the tree was clean and `in_progress/` was empty;
- live was untouched: the database file's mtime was still 14:49, and it
  held 10 bikes, all `ice`, at schema 73.

The census and the 17 tables referencing `vehicles` were read again, with
the same result. The per-option test counts had been grep counts of call
sites, not a measurement, so they were measured again by running each
option in a worktree (S0-6).

### 2026-09-28 — Step 0

`360_step0.md`. In short:
- **Six paths store `ice` nobody stated**: the four named, plus the photo
  path when the vision reply omits the key, and the column default, which
  live rows 6–9 very likely came through.
- **Storing NULL changes no reader's output today except `garage list`**,
  which prints NULL as `ice`.
- **The live census is `ice` 10**, every one a petrol-only model. Whether
  anyone stated them cannot be told. No option changes a live row.
- **The fork**: (a) require or ask everywhere; (b) store unknown; (c) the
  CLI asks and the API stores unknown. Recommended: (c), with
  `workflow start` storing the stated value on a bike held as unknown.
  Migration 074's rebuild (the default removed) is common to all three.
- **The guard's design**, with its blocked forms, fail-closed cases,
  allowed forms and known limits. `perl -i` is proposed beyond the
  operator's list.

Decisions made here, not stops:
- **The per-option counts come from a worktree of `dfb0a9a`**, run with
  `PYTHONPATH` set to the worktree's `src`, never from a checkout of this
  tree. Its own 16 baseline failures are subtracted as IDs. They come
  from the worktree's location: the packaging tests' fresh venv, and gate
  11's read of the sibling mobile repo. That ceiling is written in S0-6.
  Measured counts beyond that baseline: (a) 85, (b) 6, (c) 61; every one
  is a test that pins the old default or adds a bike without a
  powertrain.
- `engine_type`'s identical default is out of scope. It is filed as F177
  with this Step 0, because the first `wholetree.sh` run failed B2 on the
  citation before the entry existed.
- The app's `ice` preselection is the mobile repo's finding, for a session
  rooted there.

**Stopped for the operator's pick on part 1** (rule 1: a real fork).
Committed `3dc7022`, pushed.

### 2026-09-28 — The operator's picks, verbatim

> 1: (c). 2: (ii). 3: keep perl -i, and also block cp, mv and patch into src/ and tests/ (git mv stays allowed), each with its own planted positive control.

So:
- **Part 1 is option (c).** `garage add` and `add-from-photo` ask for the
  powertrain when none is given. The API stores NULL when the field is
  absent.
- **`workflow start` is (ii).** On a bike stored as unknown, it stores the
  stated value on the bike and says so.
- **`perl -i` stays blocked.** `cp`, `mv` and `patch` into `src/` or
  `tests/` are blocked too, each with its own planted positive control.
  `git mv` stays allowed. The known limits lose those three.

v1.0: `3f5d0df`, pushed before any code.

### 2026-09-28 — The edit guard

Built first, so the rest of the build runs under it:
- `.claude/skills/closeout/edit_guard.sh`, a wrapper that turns any exit
  status other than 0 into 2;
- `_edit_guard.py`, with a small shell lexer (quotes, `$…`, `$(…)`,
  backticks, heredocs, `((…))`, comments), then a per-command check;
- the second `Bash` `PreToolUse` entry in `.claude/settings.json`, with a
  30 s timeout; the guard's own clock is `LIMIT_S = 5`.

**Tests:** `tests/test_phase360_edit_guard.py`, 139, through the wrapper
with the hook payload on stdin:
- positive controls: `sed -i` 14 spellings; `perl -i` 4; redirects 18,
  357's `cat >> src/… <<'EOF'` among them; `tee` 3; `cp` 5; `mv` 4;
  `patch` 5; script bodies 18, 356's exact-match replace script among
  them; plus an unresolvable body naming `tests/` and a symlink into
  `src/`;
- fail-closed: 9 unreadable or unresolvable lines; a payload that is not
  JSON; an injected exception; a planted slow check past the clock; the
  wrapper converting exit 1;
- negative controls, 42: the commit-message heredoc with `sed -i`,
  `> src/x`, `;` and apostrophes in its body; `git mv`, `checkout`,
  `apply`, `stash pop`; read-only scripts; redirects into the scratchpad
  and `docs/`; `sed -n`; `grep '->'`; `awk '$1 > 5'`; `(( ))` and `[[ ]]`.
  A mobile-repo script naming its own `src/` is allowed, and the same body
  run here is blocked;
- each assertion helper shown red on the other's output first;
- the settings entry and its timeout.

**The replay (`360_replay_guard.py`, committed with the census).** Before
the hook went on, every Bash command in the eight newest session
transcripts was run through the guard. The first pass blocked 665 of
5,675, and reading samples of each class found three guard defects,
fixed before the hook went on:
- **The mention fallback ignored the working directory.** A `node` script
  run in `moto-diag-mobile` was blocked for naming that repo's `src/`. A
  mention now counts only when it resolves into this checkout's
  `src/` or `tests/`.
- **`$'` inside double quotes was read as an ANSI-C string.** That broke a
  `python -c "…'^\]\s*$'…"`.
- **An unquoted heredoc's body was parsed raw.** `$n != 2` is not
  Python. The body is now expanded as the shell would expand it, and so
  is a `-c` word.

Also from the replay, and decided here, not stops:
- **The resolver follows every assignment of a name**, and uses the fixed
  directory of an f-string, a `/` join or a shell word. Under `src/` or
  `tests/` the write is blocked outright; under a directory that cannot
  hold them it is allowed; only a path under the checkout root stays
  unknown.
- **An unterminated heredoc is read as bash reads it**, to the end of
  input, and judged, rather than refused as unparseable.

The final census (5,698 commands, 2026-09-09 to 2026-09-29 UTC):
- 552 real edits blocked, 459 of them Python heredoc bodies;
- 68 blocked by failing closed (1.2%);
- 5 malformed commands blocked;
- the slowest check took 6.3 ms.

**The rule was broken hundreds of times across those sessions, not twice.**

**The hook went live mid-session.** Just after the settings entry was
added, `echo planted >> tests/_planted_live_probe.py` was refused by
`edit_guard.sh` and the file was absent after. The fresh-session proof
follows.

**The fresh-session proof.** A scratch worktree at `499b7a8` (the guard
commit), and a headless `claude -p --model haiku --allowedTools Bash`
started in it, loading the new settings at startup:
- asked to run `echo planted >> tests/_fresh_probe.py`, it replied "The
  command was blocked by the edit guard hook: 'edit guard: blocked — the
  redirect `>>` writes into tests/_fresh_probe.py…'", and the file was
  absent;
- control, the same session shape: `echo planted >> docs/_fresh_probe.md`
  succeeded, and the file held `planted`. So the guard does not simply
  block all of Bash.

The worktree was removed after.

**Known limits:** in the closeout CHANGELOG's 2026-09-28 entry, and here:
- a script file run by name is not opened (the mutation scripts);
- `install`, `rsync`, `dd`, `truncate`, `ln`, `rm` and `git apply` are not
  blocked;
- `subprocess`, `eval`, `os.chdir` and run-time values are not followed;
- only Python and shell bodies are parsed;
- only this checkout is protected;
- a glob or a substitution after a fixed directory is judged by that
  directory.

Committed `499b7a8`, pushed.

### 2026-09-28 — Part 1 built: F174, option (c) with (ii)

- **Migration 074** (`_vehicles_rebuild_074`): `vehicles` is rebuilt with
  `powertrain TEXT`, no default:
  - every column is copied by name, in the live order;
  - the AUTOINCREMENT sequence is carried across, because the deploy diff
    cannot see `sqlite_sequence`;
  - the three indexes are recreated byte for byte;
  - `foreign_keys` is off during the rebuild (17 child tables).

  The rollback rebuilds with `DEFAULT 'ice'`. `SCHEMA_VERSION` 73 → 74.
  Before writing it: a fresh database's `vehicles` SQL and the live one's
  are byte-identical (read only).
- **`VehicleBase.powertrain`** is `Optional[...] = None`; both registry
  inserts bind NULL.
- **`garage add`** asks when no powertrain is given (`_ask_powertrain`).
  With no answer it prints "No powertrain given: add --powertrain
  ice|electric|hybrid. Nothing was saved." and exits 1.
- **`garage add-from-photo`**:
  - gains `--powertrain`, which wins over the guess;
  - when neither gives one, it asks;
  - the panel prints `Powertrain: unknown`;
  - `_powertrain_guess` reads a missing, blank or unrecognised reply as
    `None`. An unrecognised one used to raise at save time.
- **The API** stores NULL when the field is absent.
- **`garage list`** prints `unknown`.
- **`workflow start` (ii):** on a bike stored as unknown, once the run is
  saved, the stated value is stored and printed: "Bike #N had no powertrain
  on record; stored as electric, as stated."
- **Re-verified:** the Step 0 search for an unstated `ice` now finds only
  history: migration 003's column (superseded by 074), 177's rollback, and
  074's own rollback.

**Tests:** `tests/test_phase360_powertrain_unknown.py`, 38, on `tmp_path`
databases:
- the migration: every row, the sequence after a deleted top row, a child
  row, the indexes, `foreign_key_check`, the rollback, a raw insert, and
  no reuse of a deleted id;
- `garage add`: asks; refuses on no answer; a given value is not asked for;
- the photo path, four cases;
- the vision reply, seven cases;
- the API: create without the field, create with it, read;
- every reader on a bike stored as NULL:
  - diagnose passes `None` on, and so does its retrieval, both shown by
    spies;
  - unknown is not resolved as electric;
  - the predictor and the priority scorer pass `None` on (spies; the
    scorer reads it from the table);
  - safety shows every rule, with the electric control showing the check
    can tell the difference;
  - `garage list`;
  - `workflow start` (ii): the stated value and the prompted value are
    stored; a stored value is not rewritten; a disagreeing bike is still
    refused; a template that does not cover the value changes nothing.

Each planted known-bad fails its assertion (`360_mutate.py`, below).

Existing tests that pinned the old default or added a bike without a
powertrain were updated: 10 tests or fixtures in 5 files, 13 diff hunks
(the count "12" first written here was corrected at close-out):
- `test_phase110`, 4: the two default tests assert unknown, and the
  filter tests state `ice`;
- `test_phase122`, 2;
- 357's F174 test, which planted the default on purpose, is now a mistake
  stated by the mechanic, with the same remedy;
- gate 11's two `garage add` calls and gate 14's fixture gain
  `--powertrain ice`. They are petrol bikes: a Road King, a CB500, and 50 cc
  scooters.

**Mutations, `360_mutate.py`: 36/36 red** (G1–G15 for the guard, P1–P21
for F174). The first run found two defects in the phase's own work:
- G15 stayed green. When the fixed-directory resolution was disabled,
  the mention fallback still blocked, so the test could not tell the two
  apart. `test_the_fixed_directory_of_a_python_path_is_enough_to_block`
  now asserts the definite reason.
- P9's text occurred twice, in the create and the update requests.

Also removed: the guard's `elif name == "git": return`. It was dead code
(S9): `git` is neither an interpreter nor a writer the guard judges, so no
mutation could make it red.

**F178 filed**, found while building. The API's powertrain literal
(`hybrid_parallel`, `hybrid_series`) is not the enum's (`hybrid`):
- no API request can create a hybrid bike: 422 for `hybrid`, 400 for
  the variants;
- a PATCH stores `hybrid_parallel` as it is, and `SafetyChecker` then
  shows no fuel-leak alert.

No live row is affected (all ten are `ice`). It is not fixed here: it
changes the API contract and the app's types.

### 2026-09-28 — Stopped: gate 11's contract snapshot (rule 1: a test it cannot make green)

Running every test that mentions vehicles after the build left one
failure, re-run up a chain of gates:
- `test_phase205_gate11.py::TestContractSnapshot::test_shared_schemas_have_not_drifted`
  fails with "The mobile snapshot describes schemas differently from the
  live API … `VehicleCreateRequest.powertrain: changed`";
- gate 12's, 13's and 14's regression tests re-run gate 11 and fail with
  it.

**The cause is the contract itself.** The mobile repo's committed
snapshot (`moto-diag-mobile/api-schema/openapi.json`) describes the field
as `{"type": "string", "enum": [...], "default": "ice"}`. The API now
describes it as nullable, with no default. Any fix to the API's half of
F174, under any of the three options, changes that description, so the
snapshot must be refreshed and the app's types regenerated in the mobile
repo (`npm run refresh-api-schema`, `npm run generate-api-types`).

**Step 0 missed this.** It listed the API as a reader, and did not look
for a test that pins the API's contract against the other repository.

This session does not write to the mobile repo: another repository gets
its own session. `wholetree.sh --full` holds gates 12–14, and the push
guard needs a `--full` record for a commit to `migrations.py`, so part 1
cannot be committed until the snapshot matches. That is the guard doing its
job.

**Saved, not committed:** part 1's diff is `360_part1_wip.patch` in this
folder, and it stays in the working tree. Everything else is committed:
the guard's test fix, the dead-branch removal, the mutation script and
F178.

Committed `41d78a8`, then `9d4db1e`, both pushed. Row 360 stays 🚧,
because `roadmap_check.py` R3 refuses ⏸️ while the documents are in
`in_progress/`; the pause is written in its note.

### 2026-09-29 — Resumed: the mobile snapshot refreshed in moto-diag-mobile 57c9e45

The operator (2026-09-29): "The mobile side is done and checked:
moto-diag-mobile 57c9e45 (pushed) refreshed api-schema/openapi.json (only
VehicleCreateRequest.powertrain changed: the enum or null, no default),
regenerated src/api-types.ts, and removed the app's ice preselect (F179,
closed in the mobile FOLLOWUPS). Gate 11 passes against your working tree:
21 passed."

Checked here:
- `57c9e45` is on `moto-diag-mobile` `main`, which is level with
  `origin/main`;
- the snapshot's `VehicleCreateRequest.powertrain` reads `anyOf [the
  enum, null]`, with no default;
- the 15 changes in this tree were as they were left.

So the snapshot refresh is **moto-diag-mobile `57c9e45`**, made in a
session rooted in that repo, as the stop proposed (option A).

- **FOLLOWUPS' numbering note** now reads "the highest assigned is
  **F179**, in the mobile file; this file's highest is **F178**", as
  `next_f_number.sh` reports. A first wording named F178 as the highest
  assigned. `finding_check` B1 reads both files, so it failed that wording
  in the `--full` run.
- **F177 gains its app side:** the add-bike form still preselects
  `engine_type` `'four_stroke'` (`NewVehicleScreen.tsx:85`). The mobile
  repo's F179 records this and leaves it under F177.
- **The vehicle tests re-run:** the 100 files that mention `garage`,
  `VehicleBase`, `/v1/vehicles`, `add_vehicle`, `powertrain` or `vehicles`
  gave 3173 passed, 0 failed, gate 11 among them. 244G's scanner over
  `tests/` is clean.
- **Part 1 is committed from the working tree.** `360_part1_wip.patch`,
  the backup, is removed in the same commit, since the commit now holds
  what it held.

`wholetree.sh --full` on the staged tree gave 3945 passed. Part 1 is
`0254132`, pushed.

### 2026-09-29 — The floor, and the regression of record

- **`COLLECTED_TEST_FLOOR` 9772 → 9950** (`8a460f2`). The count was
  measured by diffing the collected test IDs against a `master` worktree.
  +178:
  - the edit guard's 139 tests;
  - F174's 38;
  - gate 15's `test_rolling_back_peels_every_successor[73]`, since 074
    now succeeds 73.

  Three tests were renamed, net 0.
- **An order slip, caught before it cost anything.** `regression.sh` was
  started first, and refused: its `--full` record was for the staged tree
  before the commit, not for HEAD. Before re-running it I saw the floor
  still had to rise, and a test edit after the regression would be code
  after the regression hash. So the run was stopped, the floor raised and
  committed, and then `--full` and the regression ran on `8a460f2`.
- `wholetree.sh --full` at `8a460f2`: 3945 passed, 83 files, 631.7 s wall.

Regression of record: 9950 passed, 0 failed, 0 skipped, 0 errors at `8a460f2` (20 min 3 s wall, `python -m pytest -n auto --dist load`, exit 0)

### 2026-09-29 — The deploy of 074: the dry run

The prompt's condition: "The dry run's diff must show no existing row's
values changed. If any would change, that is a rule-1 stop." The
operator, 2026-09-29: "the deploy of 074 (its diff must show no existing
value changed)".

- `360_deploy_scope.json`: `schema_version` +1; `"schema": {"changed":
  ["table vehicles"]}`; nothing else.
- `deploy.py dryrun 360` (`360_dryrun_diff.md`):
  - live before, read only: 5843 rows, 90 tables, integrity ok;
  - backup `~/backups/motodiag/motodiag_pre360_20260929_111643.db`
    (sha256 `887c2aff…`); retain-5 removed `motodiag_pre261_20260926_120114.db`;
  - the diff: **one `schema_version` row added (74); one schema object
    changed, `table vehicles`, whose powertrain column reads `powertrain
    TEXT` with no default; no existing row changed or removed in any
    table**. The three indexes are not in the diff, so their SQL is
    unchanged;
  - scope problems: none; F158 census 36.
- **By hand, because the diff skips `sqlite_%`:** live
  `sqlite_sequence` for `vehicles` is 10, with max(id) 10 and 10 rows,
  all `ice`, at schema 73. This is checked again after the apply.

No existing value changes, so the condition is met, and the apply follows
once the diff is committed.

Committed `427b6b7`, pushed. A first attempt ran `git commit … && git
push` in one line, and the push guard refused the whole line, as it
should; nothing ran. They were then run as two commands.

### 2026-09-29 — The deploy of 074: the live apply

`deploy.py apply-live 360`:
- the preflight passed, including F172's check that a fresh dry run
  equals the committed exact diff;
- applied `[74]`;
- live after: 5844 rows, 90 tables, integrity ok;
- scope problems: none; **equals the approved exact diff: yes**; F158
  census on live: 36 (`360_live_diff.md`).

By hand, read only, after:
- `sqlite_sequence` for `vehicles` is **10**, as before;
- max(id) 10 and 10 rows, **all still `ice`**;
- schema 74;
- `foreign_key_check` empty; `integrity_check` ok;
- `pragma_table_info` shows no default on `powertrain`.

### 2026-09-28 — Bug fix #1: a guard test could not tell a definite block from the fallback

- **Issue:** `360_mutate.py` G15 stayed green. With the fixed-directory
  resolution of a Python path disabled, the guard tests still passed.
- **Root cause:** the two cases for it
  (`open(f'tests/test_phase{stem}.py', 'w')` and `(K / name).write_text`
  with `K = Path('src/…/seed')`) sat in `SCRIPT`, whose test asserts a
  block with no reason. Disabled, the resolution returns unknown, and the
  mention fallback blocks the same command with another reason, so the
  assertion held either way.
- **Fix:** the two cases moved to `FIXED_DIRECTORY`, and
  `test_the_fixed_directory_of_a_python_path_is_enough_to_block` asserts
  the definite reason (`writes tests/…`, `writes src/motodiag/knowledge/seed/…`).
- **Files:** `tests/test_phase360_edit_guard.py`, `360_mutate.py` (P9's
  text made unique in the same pass).
- **Verified:** 139 passed; `360_mutate.py` 36/36 red, G15 red.

**Commit.** `41d78a8`.

### 2026-09-29 — Close-out

- No refute pass ran: the phase ships code, a migration and tooling, and
  no content rows. No claim rests on a document.
- F174 closed in `docs/FOLLOWUPS.md`; F177 and F178 stay open.
- Row 360 ✅; `implementation.md` 0.13.92 with its history row; v1.1;
  handoff `docs/handoffs/2026-09-29_360_closed.md`.
- The documents move to `completed/`: this log, v1.1, the Step 0, the
  mutation and replay scripts, the scope, and both diffs.
