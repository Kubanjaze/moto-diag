# Phase 371B — phase log: the payments alarm's check-in sends its key once (F273)

**Status:** Complete

**Started 2026-11-11** on the Mac, on mains power, by the advisor
session, the only writer on this checkout. The branch is
`phase-371B-the-alarm-sends-its-key-once`, from `master` at `17e4692`.
The prompt is `docs/prompts/371B_the_alarm_sends_its_key_once.txt`, the
operator's two messages word for word, with the Sentry address left out.

## 2026-11-11 — start

- Master fetched at `17e4692`, which holds F273 and F274. 371B was free.
  After this branch was made, `git branch -a --list '*371B*'` listed only
  it. `git grep -n '371B' origin/master -- docs src tests .claude` found
  0 lines.
- **`e6f15eb`: the start.** It holds row 371B as 🚧, the prompt, and K80,
  the operator's words "Go ahead and build 371B.", recorded by
  `yeoman.py decide`. The fast whole-tree run passed first (2643 passed,
  1 skipped; exit 0). It was merged to master as `1b7e40d` and pushed.
  The push printed GitHub's "Cannot update this protected ref" notice and
  went through (`17e4692..1b7e40d`). So the ledger on master shows 371B in
  progress from the start.
- **Step 0 and v1.0.** `plan_check.py 371B --no-pin` passes P1 to P10.
  The first run failed on three items, and the plan was changed to answer
  them:
  - P7: the three newest change-log entries were not cited;
  - P8: the stops were not listed by kind;
  - P9: no K-id put 371B in order, which K80 now does.
- **`8b2fc96`: Step 0, v1.0 and this log, pushed on the branch before
  any code.** The push guard refused twice. Both refusals are recorded
  here, and the guard is unchanged.
  - **First refusal:** the command ran `git commit` and `git push`
    together, which the guard refuses. That was the advisor's error. The
    two then ran as separate commands.
  - **Second refusal:** the guard's own fast run outran its 285 s limit,
    and the guard fails closed. The Mac was under load, with a load
    average of 28: the Claude app's window process at 178% CPU, and Photos'
    `mediaanalysisd` at 96%. `wholetree.sh` was then run by hand on the
    committed tree: 2643 passed, 1 skipped, 294.2 s, exit 0. Its record
    let the push through.

## 2026-11-11 — the build

- **The code.** `src/motodiag/telemetry/monitor.py`: `checkin` sends
  `Content-Type` alone, and the module docstring says why (F273).
- **The 371 test.** In `tests/test_phase371_monitor.py`,
  `test_the_post_carries_the_url_the_header_and_the_schedule` is now
  `test_the_post_carries_the_key_once_and_the_schedule`, asserting that
  the headers are exactly `{"Content-Type": "application/json"}`. The
  docstring follows.
- **The new test file**, `tests/test_phase371B_checkin_key_once.py`.
  Its stand-in Sentry server runs on loopback with Relay's order: header,
  `Authorization`, query, then path. It holds four tests:
  - the check-in, sent through the real transport, is accepted, and the
    key was read from the path only;
  - 371's request, with the key twice, gets 401 and "multiple
    authorization payloads detected";
  - a request with no key gets 401;
  - the error reports are accepted, with the header alone.
- **The related suites pass.** `pytest` on the new file,
  `test_phase371_monitor.py`, `test_phase343_sender.py` and
  `test_phase343_dsn.py`: 54 passed.
- **`371B_mutate.py`** (output in `371B_mutate.out`):
  - K1, the copy with no mutation, is green;
  - M1 to M4 are red, 4/4;
  - `--old` puts `monitor.py` back as it was at `1b7e40d`: the check-in
    test fails, which is the operator's 401 reproduced on the Mac, and
    the three controls pass.
  - The first run stopped at "not green before mutating": the copy lacked
    `tests/fixtures/`, which `support/stripe_fixtures.py` reads. The
    script now copies it. This was a fault in the new script, not in the
    phase's code, so it is not a bug fix.
- **`COLLECTED_TEST_FLOOR` 12572 to 12576**, by a diff of collected ids
  against master at `1b7e40d`, each side with its own `src/`: +5 -1. The
  five added are the four new tests and the renamed 371 test, which
  replaces the one removed.
- **`scripts/code_quality.py counts`:** ruff 1108, mypy 202, 25 functions
  over McCabe 20, 5 files over 100 KB, 19 helpers, 22 swallowed, each at
  its pin. `code_quality.py pr --base 1b7e40d`: Q10 and Q12 empty.
- **`2080643`: the build.** The fast whole-tree run passed first (2643
  passed, 1 skipped, 172.7 s; exit 0).
- **`wholetree.sh --full` on `2080643`:** 5138 passed, 1 skipped,
  809.8 s, exit 0. Its record is `79bc051d…_full.json`. By then the Mac's
  load average had fallen to 5.

## 2026-11-11 — the desktop block, tested on the Mac

The handoff's step 1 is one block for the desktop. It updates the
server's copy of the code, sends one check-in with the new code, restarts
the payments feed, and reads the restarted feed's log for failed
check-ins. It names `2080643`, the commit that changes the code, so the
close-out's document commits after it do not change what it checks.

**The bench** stays in the session's scratch folder, as the earlier
go-live blocks' benches did. It is not committed, because it holds a copy
of the repository and the live settings file's shape. It has:
- a real clone at `43ccd1b`, the desktop's code tonight;
- a stand-in GitHub whose master holds the branch merged as GitHub's
  button would;
- the real code under the Mac's venv, and a real database;
- a stand-in Sentry with Relay's rule;
- stand-ins for `systemctl`, `sudo` and `journalctl`. A restarted "feed"
  really checks in with the code on disk, so the old code is refused and
  the new accepted.

**The results:** 23 cases pass, and 18 planted faults are each caught.
Three faults in the bench itself were found and fixed before its results
were counted, and none was in the block:
- its setup deleted the clone's tracked `data/` folder;
- a restarted stand-in Sentry was given the previous one's port;
- a branch left from an earlier run.

The alarm test (the handoff's step 3) is the block given to the operator
on 2026-11-11, unchanged. On its bench, 25 cases pass and 24 planted
faults are each caught.

No refute pass ran. The phase rests on one claim about Sentry: it refuses
the key sent twice and accepts it sent once. Sentry itself answered that
on 2026-11-11, from the desktop with the live key: 401 "multiple
authorization payloads detected" against 202. The phase writes no content
rows.

## 2026-11-12 — the regression of record

`regression.sh` on the Mac, on mains power, on a clean tree at `2080643`, after the
`--full` record above. It began at 23:39 on 2026-11-11, with the load average at 5, and
ran 33 min. Nothing else of the session's ran beside it: the desktop block's bench and its
planted faults had finished before it began.

Regression of record: 12527 passed, 0 failed, 49 skipped, 0 errors at `2080643` (33 min 10 s wall, `python -m pytest -n auto --dist load --cov=motodiag`, exit 0)
Skipped in the regression of record: [1] tests/test_phase244H_test_db_isolation.py:79: no production database on this machine
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:61: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [4] tests/test_phase388_fence_boundary.py:96: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [3] tests/test_phase388_fence_boundary.py:105: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:113: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:120: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:125: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:131: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:139: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:148: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:159: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:164: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:170: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:177: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:186: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:198: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [2] tests/test_phase388_fence_boundary.py:210: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:216: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [7] tests/test_phase388_fence_boundary.py:221: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:235: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:244: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [2] tests/test_phase388_fence_boundary.py:280: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:287: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:291: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:295: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:303: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [2] tests/test_phase388_fence_boundary.py:316: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:325: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:330: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:338: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:344: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:350: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:354: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:360: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase390_space.py:327: bubblewrap is the desktop's

Line coverage of record: 88.20% at `2080643` (the pin is 87.50%): 0.70 points above it; raise COVERAGE_PERCENT to lock it in

The 49 skips: 47 are the fence's Linux-only tests (`test_phase388_fence_boundary.py`),
one needs the live database (`test_phase244H_test_db_isolation.py`) and one needs
bubblewrap (`test_phase390_space.py`), as on the Mac's run of 402's merge. 12527 passed
and 49 skipped make the 12576 collected.
