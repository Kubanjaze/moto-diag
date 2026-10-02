# Phase 369 — F183: the test worker lost with no traceback — phase log

**Status:** ✅ Complete (2026-10-01)
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

### 2026-10-01 — The build: the fix, the check, the plugin and their tests

- **Row, v1.0 and the cause:** `17d632d`, pushed. `wholetree.sh` before
  it: 1517 passed. The code was held out of the tree for that commit and
  restored after.
- **The fix.** Both guards' `main()` cancel the alarm in a `finally`
  (`_pre_push_guard.py`, `_edit_guard.py`). Each still fails closed on its
  own clock. Recorded in `.claude/skills/closeout/CHANGELOG.md`.
- **The check**, `tests/support/alarm_left_armed.py`. **The plugin**,
  `tests/support/worker_loss.py`. Both are loaded by `tests/conftest.py`'s
  `pytest_plugins`.
- **The tests**, `tests/test_phase369_worker_loss.py`, 8 tests:
  - both guards leave no alarm armed;
  - the check fails a planted alarm, and the next test survives;
  - the plugin names a planted `os._exit(2)`, SIGKILL and SIGTERM, with
    each one's last test and PID;
  - the wiring.
- **Mutation:** `369_mutate.py`, 9/9 red (`369_mutate.out`). It covers
  both guards reverted to their pre-369 code, the check disabled or run
  before the real teardown, the report, the exit status, the signal
  registration and the last-test record each removed, and the conftest
  wiring removed.
- **R2, R0's command on the fixed guard:** 2 passed in 400.89 s, with no
  lost worker and no teardown failure (`369_repro_R2_fixed.log`).
- **244G's scanner** over `tests/`: 0 hits. The integration-gaps and
  ledger gates (10 files): 478 passed. No allowlist entry or size pin
  changed.

**Decided on the way, with the reason:**
- **The plugin's controller test.** It first asked whether xdist's
  `dsession` plugin was registered. Under `-p` that runs before xdist's
  own configure, so a nested run made no records; inside the suite the
  order happened to work, as R1 showed. It now reads xdist's `dist`
  option, which is set before any configure hook.
- **Dump lines are prefixed** `worker-loss:`, so one grep of a log keeps
  a lost worker's whole report.
- **No fatal signal is planted in the suite.** A planted SIGBUS wrote two
  macOS crash reports
  (`~/Library/Logs/DiagnosticReports/Python-2026-10-01-145527.ips` and
  `-145534.ips`; they are this phase's, not a regression's). A test doing
  that on every run would fill the folder F183 was diagnosed from. The
  fatal-dump path was proven once by hand instead
  (`369_fatal_dump_once.log`: "killed by signal SIGBUS (10)", then
  "Fatal Python error: Bus error" and the stack). That run left no
  further report.
- **Phase 355's gate caught a spawned pytest** whose `-n` came through
  `*args`. `wholetree.sh` failed, 1 failed and 1524 passed. `_nested` now
  states `-n` in the literal list. That was this phase's own new code,
  before any commit, so it is not entered as a bug fix.

**The edit guard blocked two commands, both rightly, and was not
loosened:**
- `sed -i` on a docs file;
- `mv` back into `tests/support/`.

They were redone with the Edit and Write tools and with `git stash pop`.

**Full run #1** (before the fix, with both plugins) is running in a
scratchpad worktree at `17d632d`.

### 2026-10-01 — Full run #1: the unfixed guards, at full scale (14:52–15:12 EDT)

A scratchpad worktree at `17d632d` (the guards unfixed), with both plugins
written in. The canonical command, with the worktree's `src` first on
`PYTHONPATH`. Summary in `369_full1_summary.txt`. It ran alongside this
session's mutation runs and R2.

27 failed, 10145 passed, 7 skipped, 3 errors in 19 min 24 s.
- **The one this run was for:**
  `test_an_error_in_the_whole_tree_gate_blocks` ERRORs in teardown, "left
  SIGALRM armed (345 s to go)". It is the only test in the suite that
  leaves the alarm armed, and no worker was lost (`node down` 0 times,
  `worker-loss:` 0 lines).
- **22 failures and 2 errors come from the worktree's location**, not the
  code:
  - the scratchpad has no sibling `moto-diag-mobile` (gate 11, and gates
    12–14 re-running it; the finding contract; the ledger's mobile check);
  - the deploy defaults refuse a `/tmp` path;
  - the sandbox boundary tests and the packaging tests' clean venv depend
    on the checkout's path.

  Each passes in the main checkout, where the regression of record runs.
- **5 failures are `test_phase122_intake.py`, and they are real on
  `master` today.** `_count_this_month` compares UTC `created_at`
  (`2026-10-01 19:13:09`) with a local ISO month start
  (`2026-10-01T00:00:00`). As text, the space sorts before the `T`, so
  nothing written on a month's 1st (UTC date) counts. It fails the same
  in the main checkout (5 failed, 44 passed, 15:13 EDT).
  - Phase 281 found and fixed this as its bug fix #2 (`4faa46b`), on
    `phase-281` only; it reaches `master` with 281's merge.
  - It is not F183's, and it is not F10, the month-end window.
  - It passes once the UTC date is the 2nd: from 20:00 EDT today.

**Decided: the regression of record runs after 20:00 EDT today.** It must
be green, and taking 281's fix into this phase would ship a second fix
under F183's row. Waiting changes nothing that ships.

### 2026-10-01 — Stopped before the regression: gate 11 is red on `master`'s API (20:01–20:10 EDT)

At 20:01 EDT (00:01 UTC on the 2nd) the close-out drafts were stashed,
leaving a clean tree at `fbf73da`. `wholetree.sh --full` on it: **4
failed, 3986 passed** (5 min 57 s), so no `--full` record was written, and
`regression.sh` will not start without one. The four:
- gates 12 and 13 re-running gate 11 (`test_earlier_gate_still_passes`);
- gate 13 re-running gate 12;
- gate 14's `test_gate_13_still_passes`.

Gate 11 run alone: 1 failed, 20 passed. `test_shared_schemas_have_not_drifted`
reports "InvoiceGenerateRequest.tax_rate: in the API, absent from the
snapshot".
- moto-diag-mobile's snapshot was refreshed for Phase 281's API at
  `e536e60` (2026-10-01 00:16 EDT): "an invoice request no longer carries
  a tax rate …" (its finding number exists only on `phase-281`, so it is
  not cited here).
- `master`'s API still has `tax_rate`
  (`src/motodiag/api/routes/shop_mgmt.py:237`).
- So every tree based on `master` fails gate 11 until 281 merges. It is
  not this phase's code: `wholetree.sh` (fast) does not run gate 11, and
  passed on each commit.

**This is a stop under rule 1: a test this phase cannot make green.**
- Making it green from here means changing the mobile repo, which belongs
  to its own session and would undo 281's refresh, or taking 281's API
  change into this phase.
- Merging this branch into `phase-281` does not work either. The push
  guard's close-out check takes the one phase with documents in
  `in_progress/`, which would be 369, so 281's push to `master` would be
  refused.

The close-out drafts (v1.1, the `implementation.md` row) are held
uncommitted. Nothing was merged; nothing touched live or `phase-281`.

### 2026-10-01 — The operator's pick: 281 lands first, carrying the fix

> Option 1, and you do 281's finish yourself, in this session:
> 1. Commit and push 369's held drafts on phase-369 first, so the branch is clean.
> 2. Switch to phase-281. Bring in 1753822's code — the two guards, the closeout CHANGELOG entry, tests/conftest.py, tests/support/alarm_left_armed.py, tests/support/worker_loss.py and tests/test_phase369_worker_loss.py — as a diff, not by copying files: 281's conftest.py carries its network guard, which a file copy would drop. None of the 369_* files. Record in 281's log that it carries Phase 369's F183 fix (1753822) and why: the mobile snapshot follows 281's API, so master fails gate 11 until 281 merges.
> 3. On 281: --full on the committed HEAD, then the close-out regression. A lost worker is a stop. Then merge 281, run verify_phase.sh, and add the handoff's after-merge note. F103 waits for a mobile session.
> 4. Versions: 281 keeps its 0.13.96; renumber 369's draft to 0.13.97.
> 5. Back on phase-369: merge master, keeping 369's closed F183 entry; --full, the regression, close-out, merge, verify_phase.sh.

Step 1: this commit holds the v1.1 draft of `369_implementation.md`. The
draft `implementation.md` history row is not committed. Committed, it
would read to `roadmap_check.py` R6 as a close with no handoff, and the
push would be refused. It is kept in the session scratchpad, and comes
back at close-out as 0.13.97.

### 2026-10-01 — Phase 281 finished first, carrying the fix

The operator's steps 2–4, as given:
- **281 carries the fix.** It took `1753822`'s seven code paths as a diff
  (`git apply --3way --index`), with its network guard kept in
  `tests/conftest.py` and none of the `369_*` files: `63fa5a8`.
- **281's regression of record:** 10279 passed, 0 failed at `63fa5a8`,
  with no worker lost.
- **281 merged** as `2806017`. `verify_phase.sh 281 63fa5a8 2806017` read
  all fourteen checks, and the after-merge note is `04b2df4`.
- **281 keeps 0.13.96**, so 369 takes 0.13.97.
- F103 waits for a mobile session.

281's log and handoff record each step.

### 2026-10-01 — `master` merged into this branch; the regression of record

- **The merge, `88dbbd1`.** Two conflicts, both resolved by keeping both
  sides:
  - `docs/FOLLOWUPS.md`: this phase's closed F183, then 281's F184 and
    F185;
  - `docs/ROADMAP.md`: Total Phases 369, then rows 367, 368, 369.

  The F183 code came in identical from both sides. Afterwards the
  branch's `src/`, `tests/` and `.claude/` equal `master`'s.
- **The push guard refused the first merge commit, rightly.** The merge
  brings 281's `migrations.py`, and the commit had no `--full` record for
  its tree. `wholetree.sh --full` on the staged merge passed 3988, then
  the commit went through.
- **`wholetree.sh --full` on the committed HEAD `88dbbd1`:** 3988 passed
  (10 min 4 s).

Regression of record: 10279 passed, 0 failed, 0 skipped, 0 errors at `88dbbd1` (22 min 44 s wall, `python -m pytest -n auto --dist load`, exit 0)

- **No worker was lost.** In
  `~/.cache/motodiag/regressions/88dbbd1_parallel_20261001_230743.log`,
  `node down`, `crashed`, `worker-loss:` and "left SIGALRM armed" each
  appear 0 times. 23:07–23:30 EDT on the 1st: neither the month-end window
  nor a UTC 1st.
- **What this run shows.** `369_f183_timing.py` on this log: gw6 ran the
  formerly leaking test, then had 287.5 s of its own tests left. That is
  under the 345 s fuse, so this run alone does not prove the fix. The
  proof stays R1, R2 and the teardown check: no test anywhere in the
  suite left the alarm armed.

### 2026-10-01 — Close-out

- No refute pass ran: the phase ships tooling and tests, and no content
  rows. No claim rests on a document.
- No bug fixes. Three faults in this phase's own uncommitted code were
  fixed before any commit, and are recorded above:
  - the check's hook order;
  - the plugin's controller test;
  - the `-n` in `*args`.
- F183 closed in `docs/FOLLOWUPS.md`; no finding filed.
- Row 369 ✅; `implementation.md` 0.13.97 with its history row; v1.1;
  handoff `docs/handoffs/2026-10-01_369_closed.md`.
- The documents move to `completed/`: this log, v1.1, and the timing
  script and its output, the reproductions' logs and sleeper, the fatal
  dump, run #1's summary, and the mutation script and its output.
