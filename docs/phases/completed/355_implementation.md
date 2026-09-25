# Phase 355 — Parallel test suite (pytest-xdist)

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-09-25 (v1.1: close-out, with Deviations and Results)

**Branch:** `phase-355` (Opus session, the canonical checkout).

## Goal

The full suite (9,375 tests at `c6d3f3a`) runs serially in 30–55 minutes,
every phase needs at least one run, and a late failure costs a second one
(259 needed three runs, 131 minutes). Make the regression of record run in
parallel under pytest-xdist, with **exact parity** with the serial run: the
same collected count, the same passed set, 0 failed, 0 skipped. Keep the
serial run as a documented fallback.

Operator request, 2026-09-25. Every later phase is gated on it.

Outputs: `pytest-xdist>=3.6` in `pyproject.toml`'s `dev` extra; fixes to
parallel-unsafe tests (one bug fix each); the canonical command changed in
every place that states or runs it; the regression line records its command.

## Step 0 — measured (2026-09-25)

**Greenfield or extension:** extension of the test infrastructure. No
`src/` change is planned. `grep` over `tests/`, `.claude/` and `scripts/`
for spawned pytest found 10 test files and `verify_phase.sh`:

- 6 gate re-runs: 147 → 133 and 121; 159 → 147 and 133; 205, 240 and 250
  parametrised over earlier gates; 258 → 250;
- 1 collection count: 255B, the `COLLECTED_TEST_FLOOR` test;
- 3 `pytest.main` calls under `if __name__ == "__main__"` (191C, 191D,
  195C), which never run in a suite.

**Serial baseline.** Command
`PYTHONUTF8=1 .venv/bin/python -m pytest -rA --junitxml=…` at `c6d3f3a`,
without xdist installed. `c6d3f3a` is 260's `b22b715` plus docs only
(`code_after_regression.py` exit 0). Result: **9,375 passed, 0 failed,
0 skipped**, exit 0, in **30 min 33 s** by pytest's clock and 49 min 40 s
by the wall clock. The Mac idle-slept from 09:24:35 to 09:45:55
(`pmset -g log`), and pytest's clock does not advance during sleep. 260's
own record was 54 min 46 s. The live DB SHA-256 was `195bd383…` before
and after.

**Parallel matrix** (`caffeinate -i`, pytest-xdist 3.8.0, execnet 2.1.2,
each run compared to the serial junit by ID and outcome):

| command | wall | result | parity with serial |
|---|---|---|---|
| `-n auto --dist load` (10 workers) | **13 min 26 s** | 9,375 passed | exact |
| `-n auto --dist loadfile` | 18 min 16 s | **8 failed**, 9,367 passed | no |
| `-n 6 --dist load` | 20 min 22 s | 9,375 passed | exact |
| `-n 4 --dist load` | 31 min 14 s | 9,375 passed | exact |

**Failures the serial run does not have:** 8, all under `loadfile`:
`test_phase146_recovery.py::TestDiagnoseCommand` × 7 and
`test_phase143_dashboard.py::TestTextualMissing::test_other_hardware_subcommands_unaffected`,
each `OperationalError('no such table: dtc_codes')`. They reproduce
**serially, with xdist disabled**, when the two files run alone
(8 failed, 94 passed). This is an order dependence that parallel
scheduling exposes, not a race: bug fix #1.

**The machine.** 10 cores: 4 performance, 6 efficiency. Summed per-test
time inflates about 3× in every parallel run (1,823 s serially;
5,314 / 5,747 / 5,978 s at 10 / 6 / 4 workers), including tests that
take under 50 ms. `pmset -g custom` shows **Low Power Mode on for AC
power**, and `corespotlightd` and `mediaanalysisd` each hold about 75% CPU
at idle. These are the operator's machine settings, and this phase
changes neither. They set the ceiling on the speed-up; they do not
affect parity.

## Logic

1. **Find every parallel-unsafe test.** The matrix finds what one
   scheduling order exposes. A second sweep finds the whole class: **every
   test file run alone in its own process**, which removes every
   cross-file dependency whatever the scheduler's order. Every file that
   is not all-passed alone is diagnosed.
2. **Fix each one** as a numbered bug fix with its own commit. Skipping a
   test, or marking one serial-only, is a rule-1 stop.
3. **Choose the canonical command:**
   `python -m pytest -n auto --dist load`. It is the fastest in the
   matrix. `load` over `loadfile` because it spreads the long gate
   re-runs across workers. `auto` sizes itself to the machine.
4. **Keep `-n` out of `addopts`.** The ten spawned pytest runs would each
   inherit it and start their own worker pool inside a worker. The
   canonical command carries `-n` explicitly. Spawned runs pass
   `-p no:xdist`, so they run serially inside their worker and say so
   (decision D2).
5. **Update every place that states or runs the regression:** the closeout
   SKILL.md step 1; `verify_phase.sh` check 10; the CLAUDE.md regression
   text (this repo's rule 3 paragraph); the spawning tests. The floor test
   keeps its serial `--collect-only`: collection is the same count either
   way, and the parity proof checks that.
6. **Prove parity:** junit diffs of passed IDs against serial, two
   consecutive parallel runs, a planted failing test reported and then
   removed, and a serial re-run under the same machine conditions for the
   before-and-after times.

## Decisions

- **D1 `--dist load`, not `loadfile`.** Measured: `load` was faster
  (13:26 against 18:16) and had parity. `loadfile` exposed bug fix #1,
  which is fixed rather than avoided.
- **D2 spawned pytest runs pass `-p no:xdist`.** A nested run inside a
  worker must not start a pool of its own. The flag says so in the
  command, not by inheritance.
- **D3 the serial fallback is the same command without `-n`**, for a
  machine without xdist or for bisecting an order-dependent failure.

## Non-goals

Test speed-ups inside individual tests (the gate chain's re-runs, the
corpus loads); Low Power Mode and Spotlight settings; CI.

## Verification Checklist

- [x] Every file passes when run alone (the per-file sweep): 325 files,
      9,386 + 2 = 9,388 tests, the 2 the known red before the spawn edits
- [x] The parallel run has exact parity with serial: every serial pass
      passes in parallel, and the only extra IDs are this phase's 13
      (junit diff)
- [x] Two consecutive parallel runs, both at parity: P1 and P2 identical;
      the regression of record identical to P2
- [x] A planted failing test is reported by the parallel run, then
      removed (a small `-n auto` run, per the operator's trim)
- [x] SKILL.md step 1, `verify_phase.sh`, CLAUDE.md and the spawning tests
      state or run the new command, held by `test_phase355_parallel_suite.py`
- [x] The regression of record runs in parallel and records its command
- [x] Before-and-after wall times, measured under the same conditions:
      back to back this morning; see Results for the afternoon spread

## Deviations from Plan

- **Bug fix #1 was committed before v1.0.** Step 0's measurement found
  it, and the fix is self-contained.
- **The proof was trimmed by the operator.** The plan ran a full
  parallel run with a planted failure and a second serial run. The
  operator replaced both: a small `-n auto` run over the plant plus three
  real files; parity diffed against this morning's serial junit; one
  serial run of the changed files. Their wording is in the phase log.
- **The small planted run found bug fix #2**, a race that three full
  parallel runs had not shown. Bug fix #2 is code after P2, so the
  regression of record is a third parallel run on the final tree, per
  the operator's rule.
- **The before-and-after time is not one number.** The serial "before" is
  this morning's 30:33 by pytest's clock. The Mac slept 21 minutes of a
  49:40 wall, and pytest's clock does not count sleep. The parallel
  "after" ranged from 13:26 to 26:50 on one tree as the machine's state
  changed. Both are reported, with the conditions.
- **`regression.sh` is a new file** the plan did not name. It is the one
  implementation of the canonical command, and it puts the command into
  the line it prints. Without it, "the regression line records its
  command" would depend on each session remembering to add it.
- **A5 is unchanged.** Making the command part of A5 is a rule-1 stop
  (an artefact's definition). The handoff proposes it.
- **The serial file set is 12 files, not 8.** "The 8 files you fixed"
  matched no file set exactly, so every file the phase changed ran.

## Results

**Canonical command:** `.claude/skills/closeout/regression.sh`, which runs
`python -m pytest -n auto --dist load` on a clean tree under `caffeinate`.
Fallback: `regression.sh --serial` (`-p no:xdist`).

**Regression of record: 9388 passed, 0 failed, 0 skipped at `003058c`**
(13 min 28 s wall, `python -m pytest -n auto --dist load`, exit 0).

| run | tree | wall | result |
|---|---|---|---|
| serial baseline, before xdist | `c6d3f3a` | **30:33** by pytest's clock (49:40 wall, 21 min asleep) | 9,375 / 0 / 0 |
| 260's regression of record, serial | `b22b715` | 54:46 | 9,375 / 0 / 0 |
| parallel, Step 0 (back to back with the serial run) | `c6d3f3a`, xdist installed | **13:26** | 9,375 / 0 / 0 |
| P1 | `5c2c4b3` | 24:37 | 9,388 / 0 / 0 |
| P2 | `5c2c4b3` | 26:50 | 9,388 / 0 / 0 |
| regression of record | `003058c` | **13:28** | 9,388 / 0 / 0 |

**Speed-up:** 30:33 → 13:26–13:28, **2.3×** in comparable conditions,
and 2–4× against 260's 54:46. On the throttled afternoon machine (P1/P2)
it fell to 1.1–1.2×. During P1 `kernel_task` held 63% CPU and each worker
25–35%: the workers wait, they do not compute. Low Power Mode is on for
AC power, and `corespotlightd`/`mediaanalysisd` hold CPU at idle. Those
settings are the operator's; this phase changed neither.

**Parity:** every serial pass passes in parallel, and the only extra IDs
are this phase's 13 tests. P1, P2 and the regression of record have the
same 9,388 passed IDs. A planted failure is reported by a 10-worker run.
All 325 files pass alone.

**Fixed:** bug fix #1: 8 tests in 146/143 read an uninitialised default
DB (order dependence). Bug fix #2: the F124 and 256 controls planted
files into the real `tests/` and `src/` (a race). No test was skipped or
marked serial-only.

Floor 9375 → 9388. 13 new tests. No `src/` change, no migration, nothing
to deploy.

## Risks

- The speed-up depends on the machine's state (Low Power Mode, background
  indexing). The parity proof does not.
- An order dependence that no measured order exposes can remain. The
  per-file sweep closes it between files. Within a file, `load` can split
  a file's tests across workers, so a test that relies on an earlier test
  in its own file can pass or fail by schedule. The two consecutive
  parallel runs are the check on that. They do not prove its absence.
