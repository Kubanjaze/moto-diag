# Phase 369 — F183: the test worker lost with no traceback

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-10-01 (v1.0 2026-10-01)

**Outcome (v1.1).** Found, fixed and proven.
- **The cause:** the push guard's `main()` left a 345 s SIGALRM armed when
  the whole-tree gate raised. Its handler calls `os._exit(2)`. Phase 358's
  `test_an_error_in_the_whole_tree_gate_blocks` runs `main()` inside an
  xdist worker, so 345 s later that worker died, with no traceback, in
  whatever test it had reached.
- **The evidence:**
  - the dead worker in each logged loss is the one that ran that test;
  - R1 reproduced the loss on demand, and the plugin read its exit:
    "exited with status 2 (no signal)".
- **The fix:** both guards cancel in a `finally`.
- **What holds it:**
  - a teardown check that fails any test leaving SIGALRM armed;
  - eight tests, mutation 9/9 red.
- **What stays:** a plugin that makes the next lost worker explain itself.

**F183 is closed.** No bug fixes. Regression of record: see Results.

## Goal

Row 369, opened at the operator's decision of 2026-10-01: "If a worker is
lost again, stop: F183 then gets its own phase before 281 closes." A fourth
worker was lost, at `8ba118e`. Find why a pytest-xdist worker dies with no
traceback near the end of the full parallel regression, fix it with a test
that fails on the cause, and prove the fix, so that Phase 281 can close.

The canonical regression stays as it is (`regression.sh`,
`python -m pytest -n auto --dist load`); no rerun plugin; no `-n` in
`addopts`; nothing runs against `data/motodiag.db`; `phase-281` is not
touched.

## Step 0 — what was re-verified, and what was found

**Re-verified.**
- 369 is the next free number: `master` ends at 366, `phase-281` holds 367
  and 368, no branch and not the mobile ROADMAP has a 369. Only its prompt
  exists (`docs/prompts/369_f183_worker_loss.txt`).
- The three logged losses read as F183 says. `3b7528f` line 19921 (gw2,
  359's round trip), `4faa46b` line 20315 (gw1, the same test), `8ba118e`
  line 20507 (gw6, gate 2's `test_cross_platform_cam_chain`). Each says
  `node down: Not properly terminated` and nothing else. 281's trial run
  left no log in `~/.cache/motodiag/regressions/`.
- `regression.sh` sends stdout and stderr to the log, so a worker's
  faulthandler output would have reached it. None did.

**Found: the cause is a SIGALRM the push guard leaves armed.** The grep
for code that ends a process was widened from kill calls to
`signal.signal`, `os._exit` and `setrlimit`. It hit two handlers in
`.claude/skills/closeout/`:

- `_pre_push_guard.main()` arms `signal.alarm(wholetree.FAST_LIMIT_S + 60)`
  (285 + 60 = 345 s) with `_out_of_time` as the handler, and
  `_out_of_time` calls `os._exit(2)`. The cancel, `signal.alarm(0)`, comes
  after `wholetree_gate()` inside the `try`, so an exception from the gate
  skips it.
- `test_phase358_wholetree_contract.py::TestTheWiring::test_an_error_in_the_whole_tree_gate_blocks`
  calls `guard.main()` in the worker's own process with `wholetree_gate`
  patched to raise. It leaves the 345 s alarm armed.
- 345 s later the alarm fires in that worker, in whatever test it has
  reached. `os._exit(2)` leaves no traceback, faulthandler sees no fatal
  signal, and `_out_of_time`'s line goes to pytest's captured stderr,
  which dies with the process. xdist sees the channel close: "Not properly
  terminated".

**The logs agree.** In all three logged losses, the worker that died is
the worker that ran the leaking test (gw2, gw1, gw6, at 83–84% of the run).
`369_f183_timing.py` reads every parallel log since Phase 358 (19), and
sums the JUnit time of the leaking worker's own tests after it:

- the three that died had 306.0, 311.8 and 327.6 s of completed tests
  after it, and died inside the next one;
- the sixteen that survived ran out of tests first, at 63–343 s.

Test time is a lower bound on wall time, so this fits a 345 s fuse. It is
why the losses sit in the run's last ~2%, why they land in the long tests
(gate 2 builds a full knowledge base per test; 359's round trip rolls a
database back), and why the 320 runs of those two files never lost a
worker: they never ran the 358 test.

## Logic

1. **The observability plugin**, `tests/support/worker_loss.py`, loaded
   from `tests/conftest.py` and kept after the phase. In an xdist run:
   - each worker writes `<gw>.last` (its PID and the test it last
     started), a faulthandler fatal dump to `<gw>.faulthandler`, and a
     traceback to `<gw>.<SIGNAME>` for SIGTERM, SIGHUP, SIGPIPE, SIGXCPU,
     SIGXFSZ, SIGUSR1 and SIGUSR2 (`faulthandler.register`, `chain=True`,
     so each signal still does what it did);
   - the controller, at `pytest_testnodedown`, reads the worker's exit
     status from its process and writes a `worker-loss:` block into the
     run's output: PID, exit status or signal, last test, signals
     received, the dump.

   The files go in a temporary directory outside pytest's basetemp,
   which the suite's nested pytest runs prune.
2. **The check on the cause**, `tests/support/alarm_left_armed.py`, also
   loaded from conftest: every test fails in teardown if it leaves the
   real-time timer armed, and the timer is cancelled there. Any future
   leak fails at the test that made it, instead of ending a later test
   minutes afterwards.
3. **The fix**: `_pre_push_guard.main()` cancels the alarm in a `finally`.
   The edit guard's `main()` already cancels on every `Exception`, and its
   tests run it in a subprocess; at the operator's word it gets the same
   `finally`. Both are recorded in the closeout skill's `CHANGELOG.md`.
4. **Tests** (`tests/test_phase369_worker_loss.py`, 8):
   - the push guard, given a gate that raises, returns 2 and leaves no
     alarm armed; the edit guard, interrupted by a `KeyboardInterrupt`
     (the one kind its `except Exception` lets through), leaves none
     either (each fails on its pre-369 code);
   - the check fails a planted test that arms an alarm, and a later test
     in the same worker survives (fails without the check);
   - the plugin names a planted `os._exit(2)`, SIGKILL and SIGTERM, each
     with its last test and PID (fails without the report);
   - the wiring: the suite's conftest loads both plugins.

   The planted runs are nested `-n 1` / `-n 2` pytest processes in
   `tmp_path`, with their own ini file. A fatal signal is not planted in
   the suite: on macOS each one writes a crash report (Deviations).

## Proof, and the number of full runs

- **Direct reproduction, before the fix**, run in one worker (`-n 1`):
  the real leaking test, then a scratch test that sleeps 400 s.
  - R1, with the check switched off: the worker should be lost at about
    345 s, and the plugin should say "exited with status 2 (no signal)"
    during the sleeper.
  - R0, with the check on: the leaking test should fail in teardown, and
    the sleeper should pass.
- **The same command after the fix**: no loss, no teardown failure.
- **Two full canonical runs** (`python -m pytest -n auto --dist load`):
  1. on the unfixed guard, with both plugins, in a scratchpad worktree:
     expected exactly one failure, the leaking test, caught by the check,
     and no lost worker;
  2. the regression of record on the fixed commit, via `regression.sh`:
     expected no failure, no `worker-loss:` line and no "left SIGALRM
     armed".
- Mutation: each new test is seen to fail with its code reverted.

## Files

- `.claude/skills/closeout/_pre_push_guard.py`, `_edit_guard.py`: the `finally`.
- `.claude/skills/closeout/CHANGELOG.md`: a dated entry.
- `tests/support/worker_loss.py`, `tests/support/alarm_left_armed.py`, `tests/conftest.py`.
- `tests/test_phase369_worker_loss.py`.
- `docs/FOLLOWUPS.md`: F183 closed.
- The phase folder (`docs/phases/completed/`):
  - `369_f183_timing.py` and its output `369_f183_timing.out`;
  - `369_repro_sleeper.py`, and the three reproductions'
    logs (`369_repro_R1_unfixed_check_off.log`,
    `369_repro_R0_unfixed_check_on.log`, `369_repro_R2_fixed.log`);
  - `369_fatal_dump_once.log`, `369_full1_summary.txt`;
  - `369_mutate.py` and `369_mutate.out`.
- `implementation.md`: 0.13.96, with its history row.

## Overlap with Phase 281

- `phase-281`'s copy of `_pre_push_guard.py` and
  `test_phase358_wholetree_contract.py` is identical to `master`'s.
- It also edits `tests/conftest.py`, adding its network guard after
  `import pytest`. This phase adds `pytest_plugins` further down, so the
  two should merge without a conflict.
- It extends F183 in `docs/FOLLOWUPS.md`. This phase closes F183 on
  `master` starting from 281's text, so the merge conflicts there and is
  resolved by taking `master`'s entry.
- 281 merges `master` and re-runs its close-out regression before it
  merges.

## Deviations from Plan

- **The edit guard got the same `finally`.** v1.0 said it would be left
  alone; the operator's word after the connection dropped (14:30) changed
  that. It is in the phase log, verbatim.
- **The check is its own module** (`support/alarm_left_armed.py`), not part
  of `worker_loss.py`. That way a reproduction can switch it off with
  `-p no:support.alarm_left_armed`, which R1 needed to show the loss
  itself.
- **The check wraps the real teardown** (`wrapper=True`). The first
  version, a plain hook, ran before pytest's own teardown and broke the
  next test's setup. R0's first attempt showed it.
- **The plugin reads xdist's `dist` option** to know it is the
  controller. Asking whether `dsession` was registered failed under `-p`,
  because of the order of the configure hooks.
- **No fatal signal is planted in the suite.** A planted SIGBUS wrote macOS
  crash reports; the fatal-dump path was proven once by hand instead
  (`369_fatal_dump_once.log`).
- **Full run #1 had 27 failures and 3 errors, not the one expected:**
  - **1 was expected:** the leaking test, ERROR in teardown, "left
    SIGALRM armed (345 s to go)", with no worker lost.
  - **22 failures and 2 errors come from the worktree's location:** no sibling
    `moto-diag-mobile`, a `/tmp` path the deploy defaults refuse, and the
    sandbox and packaging tests' dependence on the checkout's path.
  - **5 are Phase 122's intake quota.** It fails on `master` whenever the
    UTC date is a month's 1st, and Phase 281 fixed it as its bug fix #2
    (`4faa46b`), on `phase-281` only.
- **The regression of record waited for 20:00 EDT**, when the UTC date
  was the 2nd. It had to be green, and taking 281's fix would have shipped
  a second fix under F183's row.
- **Then gate 11 stopped it.** The mobile snapshot follows 281's API, so
  `master`'s API fails gate 11 until 281 merges. The operator chose option
  1: 281 carries this phase's fix (`1753822`), closes and merges first,
  and 369 closes on `master` afterwards.
