# Phase 360 — F174 powertrain default, and the edit guard

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-09-29 (v1.0 2026-09-28)

**Outcome (v1.1).** Shipped as planned, with one stop in the middle:
- **The edit guard** is live (`499b7a8`). A fresh session was blocked on
  `tests/` and allowed on `docs/`.
- **F174 is closed.** Migration 074 is live at schema 74, and its live
  diff equals the approved exact diff; no existing row changed.
- **The stop:** gate 11 pins the mobile repo's API snapshot, whose
  `default: "ice"` the fix had to change. Step 0 missed it. The operator's
  side cleared it in moto-diag-mobile `57c9e45`.

One bug fix (the guard test that could not see G15). F177 and F178 filed.
Regression of record: 9950 passed, 0 failed at `8a460f2`. Deviations and
Results are at the end.

## Goal

Row 360: "The operator's decision 5 of 2026-09-28, before Track O batch 1.
F174: a bike's powertrain is never assumed; four paths store `ice` when
nobody said it. The edit guard: a second `PreToolUse` hook on Bash that
blocks `sed -i` and heredoc or redirect writes into `src/` and `tests/`,
failing closed, with a planted positive control for each blocked form."

Step 0 is `360_step0.md`. It found six paths that store `ice` nobody
stated, not four. **The operator's picks (2026-09-28), verbatim:** "1: (c).
2: (ii). 3: keep perl -i, and also block cp, mv and patch into src/ and
tests/ (git mv stays allowed), each with its own planted positive control."

F174 closes when no path stores `ice` that nobody stated, and every
reader's handling of an unknown powertrain is tested.

## Logic

### Part 1: F174, option (c)

**Migration 074 rebuilds `vehicles` without the powertrain default.**
- The new table is `powertrain TEXT` with no default. Every other column
  keeps its name, order, type, default and the `transmission` CHECK.
- The pattern is migration 064's: `PRAGMA foreign_keys=OFF`; create
  `vehicles_rebuild_074`; copy every column by name; carry the old
  `sqlite_sequence` value across; drop `vehicles`; rename; recreate
  `idx_vehicles_make_model`, `idx_vehicles_year` and `idx_vehicles_owner`
  with their SQL byte for byte, so they do not show as changed;
  `foreign_keys=ON`.
- It changes no row. The rollback rebuilds the same way with
  `DEFAULT 'ice'`, the pre-074 schema.
- `SCHEMA_VERSION` 73 → 74.

**The model and the registry.**
- `VehicleBase.powertrain` becomes `Optional[PowertrainType] = None`.
- Both registry inserts (`add_vehicle`, `add_vehicle_for_owner`) bind
  `None` as NULL.

**The entry points:**
- **`garage add`:** `--powertrain` has no default. When it is absent, the
  command asks: `Powertrain (ice, electric, hybrid)`. With no answer (end
  of input, or no terminal), it refuses: "No powertrain given: add
  --powertrain ice|electric|hybrid. Nothing was saved." It exits 1.
- **`garage add-from-photo`:**
  - gains `--powertrain`. A value a person gives wins over the vision
    guess.
  - `VehicleGuess.powertrain_guess` becomes `Optional[str] = None`. The
    parser reads a missing, blank or unrecognised value as `None`, not
    `ice`.
  - When neither gives a value, it asks, and refuses on no answer, as
    `garage add` does.
  - The guess panel prints `Powertrain: unknown` for `None`.
- **`POST /v1/vehicles`:** `powertrain: Optional[PowertrainLiteral] =
  None`. An absent field is stored as NULL.

**The readers:**
- **`garage list`** prints `unknown` for NULL.
- **`workflow start` is (ii).** On a bike stored as NULL, once the template
  covers the stated powertrain and the run is saved, the stated value is
  written to the bike: "Bike #N had no powertrain on record; stored as
  electric, as stated." A bike stored with another value is still refused,
  as in 357.
- Diagnose, the predictor, the priority scorer, the safety scoping and the
  API read are unchanged. Each gets a test on a bike stored as NULL: the
  behaviour `360_step0.md` S0-4 records, pinned.

### Part 2: the edit guard

**Files:**
- `.claude/skills/closeout/edit_guard.sh`, a thin wrapper like
  `pre_push_guard.sh`;
- `_edit_guard.py`, which holds all the logic.

**`.claude/settings.json`:** a second entry in the `Bash` matcher's
`hooks` list, `timeout: 30`.

**Early exit.** A command with none of `>`, `<<`, `tee`, `sed`, `perl`,
`cp`, `mv`, `patch` or `-c` leaves at once with exit 0, before parsing.

**Parsing:**
1. Heredoc bodies are cut out first, as the push guard does. Each is kept
   with the command that it feeds.
2. The rest is lexed with quotes, `$(…)`, backticks, `>(…)` and `((…))`
   understood.
3. The command is then split on `;`, `&&`, `||`, `|`, `&` and newlines.
4. A `$(…)` or `>(…)` body is judged again as a command line.

**Blocked**, each with its own planted positive control:

| form | the rule |
|---|---|
| `sed -i` | any spelling, anywhere: `-i`, `-i.bak`, `-i ''`, `--in-place[=…]`, a cluster holding `i` before `e`/`f`/`l`, `gsed`; also after `xargs`, `find -exec`, `env` |
| `perl -i` | `-i`, `-i.bak`, a cluster holding `i` (`-pi`, `-pie`) |
| redirect | `>`, `>>`, `>|`, `&>`, `&>>`, `N>` with a target in `src/` or `tests/`. This covers `cat`/`printf`/`echo` into a file and `cat > f <<'EOF'` |
| `tee` | a target there, with or without `-a` |
| `cp`, `mv` | a destination there: the last operand, or `-t DIR` / `--target-directory=DIR` |
| `patch` | an explicit file or `-d DIR` there; or no explicit file while the working directory is inside this checkout (the diff names the files, and it is not read) |
| heredoc or `-c` script | `python`/`python3` fed by `<<`, or given `-` or `-c`: the body writes there (see below). `bash`/`sh`/`zsh` the same: the body is judged as a command line |

**A Python body is blocked** when it has a write call whose target is
protected:
- the write calls: `open(…, mode)` with a mode holding `w`, `a`, `x` or
  `+`; `.write_text(`; `.write_bytes(`; `shutil.copy*`/`shutil.move`'s
  destination; `os.replace`/`os.rename`'s destination;
- a target counts as protected when it is a literal path there, or a name
  assigned such a literal (or a `Path(…)` of one) in the same body;
- when a write call's target cannot be resolved and the body names `src/`
  or `tests/` anywhere, the body is blocked too.

**Paths:**
- A target is resolved against the payload's `cwd`, through literal
  `cd DIR` segments earlier in the line.
- `~`, `$HOME`, `$CLAUDE_PROJECT_DIR`, `$TMPDIR` and literal `NAME=value`
  assignments made earlier in the line are expanded.
- A path is protected when it resolves, following symlinks, under
  `<repo>/src` or `<repo>/tests`.
- `/dev/*` is never protected.

**Fail closed.** Exit 2, with a reason on stderr, for:
- a line it cannot lex (an unbalanced quote, an unterminated `$(` or
  heredoc);
- a write target it cannot resolve (an unknown `$VAR`, a backtick, `$(…)`,
  a glob);
- any exception;
- the guard's own limit, `LIMIT_S = 5`, under `SIGALRM`, inside the 30 s
  hook timeout. 358 measured that a hook killed by its timeout lets the
  command run.

**Allowed**, each shown by a negative control:
- every `git` command, including `git mv`, `git checkout` and `git apply`.
  The commit-message heredoc is allowed even when the message holds
  `sed -i`, `> src/x`, `;` and apostrophes;
- read-only heredoc and `-c` scripts;
- `cat <<EOF` to stdout, and `sqlite3 <<EOF`;
- redirects, `tee`, `cp` and `mv` into the scratchpad or `docs/`;
- `cp src/x /scratch/`, whose source is protected but not its target;
- `2>&1`, `>/dev/null`, `&>/dev/null`;
- `sed -n`; `sed 's/a/b/' f` to stdout; `grep '->'`; `awk '$1 > 5'`;
  `(( a > b ))`;
- a command with none of the early-exit tokens.

**Known limits** (written into the closeout CHANGELOG and the phase log):
- **A script file run by name is not opened.** The phase mutation scripts
  write into `src/` by design, and run that way.
- `install`, `rsync`, `dd`, `truncate`, `ln`, `rm` and `git apply` are not
  blocked.
- `subprocess` calls inside a script body, `eval`, and values known only at
  run time are not followed.
- Only Python and shell bodies are parsed. A `node`, `ruby` or `perl -e`
  body is blocked only when it names a protected path and one of the write
  words `writeFile`, `open(` or `File.write`.
- Only this checkout is protected.
- Hooks are read when a session starts.

## Key Concepts

- **NULL means "nobody said".** Every reader already handles it. What the
  phase changes is who is allowed to write `ice`: only a person, or a
  vision guess the person saw.
- **The guard judges the command line before any of it runs**, like the
  push guard. It can be wrong in both directions. A false block costs a
  retry with the Edit tool. A false pass is what its known limits list.

## Decisions

- **D1. (c) and (ii)**, the operator's picks.
- **D2. The column default goes**, rather than becoming `NOT NULL`. A raw
  insert then stores unknown, which every reader handles, rather than
  failing.
- **D3. No live row changes.** The ten `ice` rows stay `ice`.
- **D4. An unrecognised vision guess is read as unknown.** Today it raises
  `ValueError` in `PowertrainType(...)`.
- **D5. The API cannot set a stored value back to unknown.** An explicit
  null stays ignored, as today. Not in scope.
- **D6. `patch` without an explicit target is blocked inside the
  checkout.** The guard does not read the diff; outside the checkout it is
  allowed.
- **D7. No refute pass.** The phase ships code and a schema, no content
  rows.

## Non-goals

- F177 (`engine_type`'s default). The app's `ice` preselection, which is
  the mobile repo's.
- Changing any existing live row.
- Blocking the forms in the known limits.

## Planned items

1. This v1.0, committed and pushed before code.
2. **The guard first**, so the rest of the build runs under it:
   - `edit_guard.sh`, `_edit_guard.py` and the settings entry;
   - `tests/test_phase360_edit_guard.py`, driving the wrapper with JSON on
     stdin, as `test_phase255D_closeout_contract.py` does: one positive
     control per blocked form (`sed -i` GNU and BSD spellings, `perl -i`,
     each redirect operator, `tee`, `cp`, `mv`, `patch`, a Python heredoc
     body, a Python `-c`, a shell heredoc body); every negative control;
     the fail-closed cases (unlexable, unresolvable target, an injected
     exception, a planted slow analysis past `LIMIT_S` in a subprocess,
     exit 2); and the settings entry present with its timeout;
   - its own time on this machine, measured;
   - the live proof: a headless `claude -p` in a scratch worktree carrying
     the new settings is asked to append to a `tests/` file and is
     refused, and the file is shown unchanged.
3. Migration 074 and `SCHEMA_VERSION`. Tests:
   - every column and value kept;
   - the default gone;
   - the indexes' SQL unchanged;
   - the sequence kept, after a deleted top row;
   - the rollback restores `DEFAULT 'ice'`;
   - a raw insert without the column stores NULL;
   - the head pinned only as `>= 74` and `== max(MIGRATIONS)`.
4. The model, the registry, `garage add`, `add-from-photo`, the API,
   `garage list` and `workflow start` (ii).
5. `tests/test_phase360_powertrain_unknown.py`, on a `tmp_path` database:
   - each entry point with no powertrain (asks; refuses on no answer;
     the API stores NULL; the photo path asks when the guess lacks one);
   - each reader on a bike stored as NULL: diagnose's retrieval and
     prompt ordering, the predictor, the priority scorer, the safety
     scoping, `workflow start` (ii), `garage list`, the API read.

   The existing tests that pin the old default or add a bike without a
   powertrain are updated. Step 0 measured 61 under (c).
6. F174 closed and F177 kept open in `docs/FOLLOWUPS.md`.
7. Mutations, `360_mutate.py`, one per rule, each seen red.
8. `wholetree.sh --full`, then the regression of record by
   `regression.sh`; `COLLECTED_TEST_FLOOR` raised.
9. The deploy:
   - `360_deploy_scope.json`: `schema_version` +1; `"schema":
     {"changed": ["table vehicles"]}`; nothing else;
   - `deploy.py dryrun 360`, the diff committed and shown;
   - if any existing row's values would change, stop (rule 1);
   - `deploy.py apply-live 360`;
   - `sqlite_sequence` for `vehicles` checked by hand before and after,
     because the diff cannot see it.
10. Close-out: v1.1, row 360 ✅, handoff, `verify_phase.sh`.

## Verification Checklist

- [x] v1.0 committed and pushed before code (`3f5d0df`)
- [x] A positive control for each blocked form, seen blocked
- [x] Every negative control seen allowed, the commit-message heredoc included
- [x] Fail-closed cases seen blocked, the time limit included
- [x] Live proof in a fresh headless session (and mid-session)
- [x] Migration 074 keeps every value; the dry run shows no existing row changed
- [x] No path stores `ice` that nobody stated
- [x] Each reader tested on a bike stored as unknown; each planted known-bad fails
- [x] Mutations all red (36/36)
- [x] 244G scanner over `tests/`
- [x] `wholetree.sh` before each commit; `--full` before the migration commit and the regression
- [x] Regression of record by `regression.sh`; floor raised (9772 → 9950)
- [x] Dry-run diff committed (`427b6b7`); apply-live passes F172's exact check
- [x] Known limits in the CHANGELOG and the phase log
- [x] Handoff written; `verify_phase.sh` run after the merge (its result is in the handoff)

## Deviations from Plan

- **A stop at gate 11, which Step 0 missed.** Gate 11 compares the mobile
  repo's committed OpenAPI snapshot with the live API. The snapshot
  described `VehicleCreateRequest.powertrain` with `"default": "ice"`,
  so any fix to the API's half of F174 had to change it. The operator's
  side refreshed the snapshot, regenerated the app's types and removed
  the app's `ice` preselect in moto-diag-mobile `57c9e45` (the mobile
  repo's F179). Step 0 listed the API as a reader, and did not look for a
  test pinning its contract against the other repository.
- **The guard grew beyond v1.0's design**, from the replay of 5,698 past
  commands:
  - a Python path's fixed directory decides, and every assignment of a
    name is followed;
  - a shell word's fixed leading directory decides too;
  - an unquoted heredoc is expanded before it is parsed;
  - an unterminated heredoc is read to the end of input, as bash reads
    it, rather than refused.

  Three guard defects the replay found were fixed before the hook went on.
- **The guard's `git` branch was removed** as dead code (S9). `git` is
  judged by nothing, so its commands pass without the branch.
- **`add-from-photo` also reads an unrecognised vision guess as unknown**
  (D4). It used to raise at save time.
- **Ten existing tests or fixtures changed** (in 5 files), against the 61
  failures Step 0 measured under (c). 52 of those were errors from one
  gate 14 fixture, and one edit to that fixture cleared them all.
- **Part 1 was saved as a patch while stopped** (`41d78a8`), and removed
  when part 1 was committed (`0254132`).
- **The regression ran twice in effect.** The first start was refused,
  because its `--full` record was for the staged tree, not HEAD. The
  floor was then raised before the run of record, so no code follows it.
- **The deploy ran before the merge**, on the phase branch, as 357's did.
  The migration applied live is the one in `8a460f2`, the commit the
  regression tested.
- **F178 found and filed, not fixed.** The API's hybrid values are not the
  enum's, and a PATCH can hide seven safety rules. Fixing it changes the
  API contract again.

## Results

| | |
|---|---|
| Edit guard | `edit_guard.sh` + `_edit_guard.py`, second Bash `PreToolUse` hook, 30 s timeout, own 5 s clock; live since `499b7a8` |
| Guard tests | `test_phase360_edit_guard.py` 139: the positive control for each blocked form, 42 negative controls, the fail-closed cases |
| Guard replay | 5,698 commands (2026-09-09 to 2026-09-29): 552 real edits blocked (459 Python heredoc bodies), 68 fail closed (1.2%), 5 malformed; slowest 6.3 ms (`360_replay_guard.py`) |
| Live proofs | mid-session: planted `tests/` append refused, file absent; fresh headless session: refused on `tests/`, allowed on `docs/` |
| Migration | 074: `vehicles` rebuilt, `powertrain TEXT` with no default; schema 73 → 74; no row changed; sequence 10 kept |
| F174 tests | `test_phase360_powertrain_unknown.py` 38: migration, every entry point, every reader on an unknown bike |
| Mutations | 36/36 red (`360_mutate.py`: guard 15, F174 21) |
| Whole tree | `--full` at `8a460f2`: 83 files, 3945 passed |
| Regression | 9950 passed, 0 failed, 0 skipped at `8a460f2` (20 min 3 s, `-n auto --dist load`) |
| Floor | `COLLECTED_TEST_FLOOR` 9772 → 9950 |
| Deploy | dry run committed `427b6b7`; apply-live `[74]`; live 5843 → 5844 rows, 90 tables, integrity ok; equals the approved exact diff; F158 census 36; sequence 10, all ten `ice`, no default (by hand) |
| Mobile | snapshot and types refreshed, `ice` preselect removed: moto-diag-mobile `57c9e45` (F179) |
| Findings | F174 closed; F177, F178 filed |
| Bug fixes | 1 (the guard test that could not see G15) |
