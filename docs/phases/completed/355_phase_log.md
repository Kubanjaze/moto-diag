# Phase 355 — Parallel test suite (pytest-xdist) — phase log

**Status:** ✅ Complete (2026-09-25)
**Branch:** `phase-355` (Opus session, the canonical checkout)

---

### 2026-09-25 — Opened from the operator's prompt

Operator request, 2026-09-25: make the suite run in parallel, run to
exact parity with serial, and make it the canonical regression. Read
before acting: this repo's CLAUDE.md and the working-rules index; the
ROADMAP (Track T ends at 354, so 355 is the next free number);
`ROADMAP_AUTHORITY.md` (205+ is backend); the newest handoff,
`2026-09-25_260_closed.md` (it names 261 as next; the operator's queue
puts 355 first); the closeout skill and `verify_phase.sh`.
`docs/phases/in_progress/` was empty.

Branch `phase-355` from `master` at `5b5fd47`. Row 355 🚧 committed
before Step 0: `c6d3f3a`, `roadmap_check.py` ok, row 70 words.

### 2026-09-25 — Step 0, measured

The full record is in `355_implementation.md` § Step 0. In short:

- **Serial baseline** at `c6d3f3a`, before xdist was installed:
  9,375 passed, 0 failed, 0 skipped, exit 0, in 30 min 33 s by pytest's
  clock and 49 min 40 s by the wall clock. The Mac idle-slept for 21
  minutes during the run (`pmset -g log`, 09:24:35 → 09:45:55). Every
  later timed run goes under `caffeinate -i`.
- `pytest-xdist` 3.8.0 installed in `.venv`; `pytest-xdist>=3.6` added
  to `pyproject.toml`'s `dev` extra. No test pins the `dev` list (grep:
  136, 132 and 209 read other extras).
- **Matrix:** `-n auto --dist load` 13:26, exact parity;
  `-n auto --dist loadfile` 18:16, 8 failed; `-n 6` 20:22 and `-n 4`
  31:14, both exact parity.
- **The machine:** Low Power Mode is on for AC power, and two background
  daemons hold about 75% CPU each. Per-test time inflates about 3× under
  every worker count. Recorded, not changed: they are the operator's
  settings.

**Decision (logged, not asked):** the canonical command is
`-n auto --dist load`, the fastest configuration measured. `loadfile`'s
failures are fixed (bug fix #1), not avoided.

**Decision (logged, not asked):** a second sweep runs every test file
alone in its own process. The matrix shows only what one schedule
happens to expose. The sweep finds every cross-file dependency.

**Deviation:** bug fix #1 (`8b298c1`) was committed before v1.0. Step
0's measurement found it, and the fix is self-contained.

v1.0 committed and pushed: `680367f`.

### 2026-09-25 — The per-file sweep: every file alone in a fresh process

Every `tests/test_*.py` ran alone with `-p no:xdist`, which removes every
cross-file dependency. The first attempt printed "command line cannot be
assembled, too long" and ran nothing: BSD `xargs -I` caps the replacement
at 255 bytes. The rewrite used a helper script. It ran 80 files at six
processes, then stopped because it was too slow on this machine. The
remaining 245 ran at ten. Six files killed mid-run were re-queued rather
than counted.

**Result:** 325 files. Every file passed alone except
`test_phase355_parallel_suite.py`, whose spawn scan was red by design
until the spawn edits. The per-file logs sum to 9,386 passed and 2
failed: 9,388 tests, so the sweep covered every collected test. **No
cross-file dependency beyond bug fix #1.**

### 2026-09-25 — The canonical command (`5c2c4b3`)

`regression.sh`, the edits to SKILL.md step 1, `verify_phase.sh`,
CLAUDE.md and CHANGELOG, `-p no:xdist` on all nine spawned pytest lists,
`test_phase355_parallel_suite.py` (13 tests) and the floor raised 9375 →
9388. The implementation doc's Logic 4–5 and Results give the detail.

- The spawn scan was red (2 failed) before the spawn edits and green
  after.
- The `addopts` guard was **seen red** on a planted `-n auto` and
  reverted. With `-p no:xdist` pytest refuses the unknown `-n` before the
  test runs, so the check had to run with the plugin loaded.
- **Decision (logged, not asked):** A5 in `closeout_check.py` is **not**
  extended to require the command. That would change an artefact's
  definition, which is a rule-1 stop. The new check 14 in
  `verify_phase.sh` only prints. `regression.sh` writes the command
  into the line it prints, so every recorded line carries it. Enforcing
  it is proposed in the handoff.

### 2026-09-25 — The proof, trimmed by the operator

The proof script ran P1, then P2, on `5c2c4b3`. It was then to run a
full parallel run with a planted failure, and the serial fallback. **The
operator trimmed it:** "when P2's result lands, stop the proof script
before PLANT and SERIAL. Show the planted failure with a small -n auto
run … prove parity by diffing P1/P2's junit test IDs against this
morning's serial junit, plus one serial run of the 8 files you fixed. If
no code changed after P2, P2 is the regression of record; otherwise run
one more parallel regression on the final tree." `proof.sh` was
stopped while P2 ran. P2 finished, and nothing after it started.

- **P1** `5c2c4b3`: 9,388 passed, 0 failed, 0 skipped, 24 min 37 s.
- **P2** `5c2c4b3`: 9,388 passed, 0 failed, 0 skipped, 26 min 50 s.
  The small runs below overlapped part of it.
- **Planted failure**, as a small `-n auto --dist load` run over an
  untracked `test_zz_planted_355.py` plus three real files (10 workers):
  `FAILED tests/test_zz_planted_355.py::test_planted_failure_355`,
  exit 1. The file was removed and the tree is clean. **The same run
  found bug fix #2.**
- **Parity by junit diff:** all 9,375 IDs that passed serially at
  `c6d3f3a` passed in P1 and in P2. The only IDs the parallel runs add
  are the 13 in `test_phase355_parallel_suite.py`. P1 and P2 are
  identical: the same 9,388 IDs, all passed.
- **Serial run of the changed files.** "The 8 files you fixed" matches
  no file set exactly, so all 12 files this phase changed ran with
  `-p no:xdist` at `003058c`: the 4 bug-fix files, the 7 spawn-edited
  files and the new file. 516 passed, 0 failed, 6 min 11 s.
- Code changed after P2 (bug fix #2), so P2 is not the record, and one
  more parallel regression ran on the final tree.

### Regression of record

Regression of record: 9388 passed, 0 failed, 0 skipped, 0 errors at `003058c` (13 min 28 s wall, `python -m pytest -n auto --dist load`, exit 0)

That line is as `regression.sh` printed it, under `caffeinate`. Log and junit:
`~/.cache/motodiag/regressions/003058c_parallel_20260925_124145.*`. The
passed set is identical to P2's by junit diff. The live DB SHA-256 was
`195bd383…` before and after.

### Bug fixes

### Bug fix #1 — 2026-09-25

- **Issue:** 8 tests failed under `-n auto --dist loadfile` with
  `OperationalError('no such table: dtc_codes')`:
  `test_phase146_recovery.py::TestDiagnoseCommand` × 7 and
  `test_phase143_dashboard.py::TestTextualMissing::test_other_hardware_subcommands_unaffected`.
- **Root cause:** each file's autouse fixture redirected
  `hardware.init_db` to a per-test tmp DB. The DTC lookup in
  `hardware diagnose` (step 5) and in `hardware scan` goes through
  `get_connection()` with no path, i.e. the process's default DB. The
  tests passed only when an earlier test in the same process had
  initialised that default. Reproduced **serially with xdist disabled**
  by running the two files alone: 8 failed, 94 passed.
- **Fix:** the fixture also sets `MOTODIAG_DB_PATH` to its tmp DB and
  resets the cached settings. On teardown it calls `monkeypatch.undo()`
  before `reset_settings()`, so the cache is not rebuilt from the tmp
  path.
- **Files:** `tests/test_phase146_recovery.py`,
  `tests/test_phase143_dashboard.py`
- **Verified:** the same isolated command: 102 passed. Rule-3 checks: 58
  passed, `finding_check` exit 0.

**Commit.** `8b298c1`

### Bug fix #2 — 2026-09-25

- **Issue:** the small parallel run that showed the planted failure also
  failed two tests in `test_f124_schema_pin_discipline.py` with
  `FileNotFoundError: tests/test_zz_f124_planted_probe_constant.py`.
- **Root cause:** F124's controls wrote probe files into the real
  `tests/`, and 256's controls wrote modules into the real
  `src/motodiag/`, then scanned the whole directory. In parallel, one
  worker's probe can vanish between another worker's `glob` and its
  `read_text`, and any other test walking `tests/` or `src/` can see the
  probe. The full parallel runs passed only because `load` happened to
  send those tests to one worker. An AST search over `tests/` for writes
  to repo-rooted paths found F124 (its positive control) and 256, and
  nothing else.
- **Fix:** `_head_equality_pins(directory=TESTS)` and
  `_sql_offenders(src_root=ROOT/"src"/"motodiag")` take the directory to
  scan. The controls plant into `tmp_path` and scan it with the same
  function. The real-tree tests still scan the real tree.
- **Files:** `tests/test_f124_schema_pin_discipline.py`,
  `tests/test_phase256_chokepoint.py`
- **Verified:** the scanners were mutated to ignore the parameter (`-B`,
  pycache cleared), and all 5 detection controls went red; reverted. A
  first revert matched two identical lines, and the Edit tool refused it.
  The 3× run started against the mutated file was stopped before it
  reported, and the revert was redone with unique context. The formerly
  failing parallel set then passed 129 × 3. Rule-3 checks green,
  `finding_check` exit 0.

**Commit.** `003058c`
