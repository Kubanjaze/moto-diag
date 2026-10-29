# Phase 394 — phase log: the fleet passes a rank's brief on standard input

**Started 2026-10-28** on the home desktop (WSL2), the only writer, on
`phase-394-brief-on-stdin` from `master` at `c608169`. The prompt is
`docs/prompts/394_the_brief_on_stdin.txt` (the operator's words, verbatim).

## 2026-10-28 — start

- **The row first.** Row 394 (🚧), K55 (recorded with `yeoman.py decide`),
  394 as row 3 of "Next, in order" right after 303 with its dated entry,
  and `tests/test_phase392_plan_order.py` moved to the new order, in one
  commit: `467a092`. `wholetree.sh` before it: exit 0, 2343 passed.
- **A guard block.** Moving the test with a Python script was refused by
  the edit guard ("a Python script body writes
  tests/test_phase392_plan_order.py"). The three edits were made with the
  Edit tool instead. The guard is unchanged.
- **`pgrep -x bwrap`** before the whole-tree command: exit 1, no fenced
  run. #31 carries `needs-admiral`, so the cycle runs no stage on it.
- **#31 and PR #34** are only read (the comment count in Step 0), never
  written.

## 2026-10-28 — Step 0

`394_step0.md`. The defect measured (69 launch failures, 69 "started"
comments); `claude -p` on this install (2.1.312) reads a 291094-byte brief
from stdin and follows it; five argv launches, two in scope. Decisions in
S0-5; none is a rule-1 stop.
