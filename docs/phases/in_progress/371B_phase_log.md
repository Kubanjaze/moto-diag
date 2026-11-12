# Phase 371B — phase log: the payments alarm's check-in sends its key once (F273)

**Status:** In progress

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
