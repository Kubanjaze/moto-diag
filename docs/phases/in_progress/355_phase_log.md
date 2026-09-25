# Phase 355 — Parallel test suite (pytest-xdist) — phase log

**Status:** 🚧 In progress
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
- **Commit:** `8b298c1`
