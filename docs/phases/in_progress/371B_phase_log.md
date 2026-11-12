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
