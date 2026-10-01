# Phase 369 — F183: the test worker lost with no traceback — phase log

**Status:** 🚧 In progress (2026-10-01)
**Branch:** `phase-369` (Opus session, main checkout, the only writer)

---

### 2026-10-01 — Opened

The prompt is `docs/prompts/369_f183_worker_loss.txt` (merged in
`c3dbb3d`). The operator's decision (2026-10-01), verbatim: "If a worker is
lost again, stop: F183 then gets its own phase before 281 closes." A fourth
worker was lost at `8ba118e`.

- 369 is the next free number: `master`'s highest row is 366, `phase-281`
  holds 367 and 368, and no branch, phase document or mobile ROADMAP line
  names 369.
- Read: F183 on `origin/phase-281`, 281's phase log there, the three crash
  logs, the 275 handoff.

### 2026-10-01 — Step 0: the cause found

The full record is in `369_implementation.md` ("Step 0"). In short:

- **The search that found it.** The "nothing kills processes" grep was
  widened from kill calls to `signal.signal`, `os._exit`, `setrlimit`,
  `fork` and fd calls, over `src/`, `tests/`, `scripts/` and `.claude/`.
  It returned nine hits; two were SIGALRM handlers that call `os._exit(2)`,
  in `_edit_guard.py` and `_pre_push_guard.py`.
- **The cause.** `_pre_push_guard.main()` arms a 345 s alarm and cancels
  it inside its `try`, so an exception from `wholetree_gate` skips the
  cancel.
  `test_phase358_wholetree_contract.py::TestTheWiring::test_an_error_in_the_whole_tree_gate_blocks`
  runs `main()` in the worker with the gate raising. 345 s later
  `os._exit(2)` ends whichever test that worker has reached, with no
  traceback.
- **The logs agree.** In each logged loss, the dead worker is the one that
  ran that test (gw2 at `3b7528f`, gw1 at `4faa46b`, gw6 at `8ba118e`).
  `369_f183_timing.py` (output in `369_f183_timing.out`) reads all 19
  parallel logs since Phase 358:
  - the three dead workers had 306.0, 311.8 and 327.6 s of completed test
    time after it, and died inside the next test;
  - the sixteen survivors ran out of tests at 63–343 s.

  281's 320 reproduction runs never ran the 358 test.

### 2026-10-01 — Reproduced, before any fix

Two runs, each with one worker (`-n 1 --dist load`): the real leaking
test, then `369_repro_sleeper.py` (sleeps 400 s). The plugin
(`tests/support/worker_loss.py`) and the teardown check
(`tests/support/alarm_left_armed.py`) were in the working tree, not yet
committed. The guard was unfixed.

| run | check | result |
|---|---|---|
| R1 | off (`-p no:support.alarm_left_armed`) | `[gw0] node down: Not properly terminated` during the sleeper; the plugin: `exited with status 2 (no signal)`, last test the sleeper, no catchable signal, empty faulthandler dump; 345.56 s (`369_repro_R1_unfixed_check_off.log`) |
| R0 | on | the leaking test ERRORs in teardown, "left SIGALRM armed (345 s to go)"; the sleeper passes after 400 s (`369_repro_R0_unfixed_check_on.log`) |

R1 is F183's signature exactly, and the plugin names the exit status, the
`os._exit(2)` of `_out_of_time`.

R0's first attempt failed differently: the check, as a plain
`pytest_runtest_teardown` hook, ran before pytest's own teardown, so the
next test's setup raised "previous item was not torn down properly". It was
made a `wrapper=True` hook that checks after the real teardown, then re-run.
That was a fault in this phase's own uncommitted code, found before any
commit, so it is not entered as a bug fix.

### 2026-10-01 — The operator, after the session's connection dropped (14:30)

> The cause you found holds up. … Fix the guard so the cancel is in a
> finally. _edit_guard.main() cancels after its try/except, so it's safe
> today, but give it the same finally. Record the guard change in the
> closeout skill's CHANGELOG.md. Then carry on: the teardown check, a test
> that fails on the planted cause, the regression, close-out.

v1.0 said the edit guard would be left as it is. The operator's answer
replaces that: it gets the same `finally`.
