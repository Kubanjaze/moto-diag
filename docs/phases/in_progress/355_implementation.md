# Phase 355 — Parallel test suite (pytest-xdist)

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-09-25

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

- [ ] Every file passes when run alone (the per-file sweep)
- [ ] The parallel run has exact parity with serial: collected count,
      passed set, 0 failed, 0 skipped (junit diff)
- [ ] Two consecutive parallel runs, both at parity
- [ ] A planted failing test is reported by the parallel run, then removed
- [ ] SKILL.md step 1, `verify_phase.sh`, CLAUDE.md and the spawning tests
      state or run the new command
- [ ] The regression of record runs in parallel and records its command
- [ ] Before-and-after wall times, measured under the same conditions

## Deviations from Plan

## Results

## Risks

- The speed-up depends on the machine's state (Low Power Mode, background
  indexing). The parity proof does not.
- An order dependence that no measured order exposes can remain. The
  per-file sweep closes it between files. Within a file, `load` can split
  a file's tests across workers, so a test that relies on an earlier test
  in its own file can pass or fail by schedule. The two consecutive
  parallel runs are the check on that. They do not prove its absence.
