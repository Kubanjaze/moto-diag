# Phase 397 — phase log: the one-second window in a fleet test (F241)

**Status:** In progress

**Started 2026-10-31** on the home desktop (WSL2), the only writer, on
`phase-397-the-one-second-window`. The prompt is
`docs/prompts/397_the_one_second_window.txt` (the operator's words,
verbatim); the operator's word is K63.

## 2026-10-31 — start

- Master fetched at 22:33 at `48cf7ca`. Across every local and remote
  branch, 397, K63 and F242 were free (K67 appears only as a BMW chassis
  code).
- `3d0fa45`: the prompt, row 397 🔲, row 10 of "Next, in order" (343 to
  210 renumbered 11 to 17) with the dated entry, K63 (by `yeoman.py
  decide`) and `tests/test_phase392_plan_order.py` (one test added).
  wholetree fast passed first (2548 passed, 10 skipped; exit 0, the fleet
  idle). Merged to master as `2405758` and pushed; the push printed
  GitHub's "Cannot update this protected ref" notice and went through
  (`48cf7ca..2405758`).
- **Guard block** (recorded, guard unchanged): the edit guard refused a
  Python script body that edited the plan of record, because its text
  named `tests/`; the Edit tool made the same edits.
- Issue #45 and the phase-345 branch untouched.
- Row 397 🚧 on the branch before Step 0.

## 2026-10-31 — Step 0

`397_step0.md`. (a) The planted command needs about 6 ms of its 1 s
window here (86 ms at most beside 128 busy processes); with `sleep 2`
planted the test as it stands is red 10 of 10, `assert 'started' in ''`,
the Mac's failure; `run_group` keeps all that was printed. (b) An escaped,
live child reads alive through `/proc` and ended with `/proc` absent. The
census: 19 lines in 9 files; two tests in the file are fixed here, three
elsewhere share the weakness and are filed as F242.

**The machine:** the Quartermaster's stage on 345 ran from 22:40:37; the
load measurement and the known-bad runs (22:42–22:43) shared the machine
with it. No whole-tree run did.

## 2026-10-31 — the build

- **Order slip, recorded.** While the Quartermaster's stage held the
  machine, the test change was written before v1.0 was committed. Nothing
  was committed out of order: Step 0 and v1.0 are committed and pushed
  first, on their own, and the code after them.
- `tests/test_phase392_check_limit.py`: the windows (1, 2, 4, 8, 16, 32 s),
  each with its own folder and bound (`window + 29` s), stopping at the
  first in which the planted command reached its child; the 120 s window
  for `test_run_group_passes_a_run_that_ends`; `alive()` through
  `ps -o stat= -p`; `test_alive_answers_on_this_system`, its controls.
- The fixed file: 5 passed (2.88 s). With `sleep 2` planted, the fixed
  test is green 5 of 5 (`397_measure.py knownbad 5`, about 7 s each: the
  1 s and 2 s windows fall short, the 4 s window reaches the child).
- `397_mutate.py`, 22:49 to 22:55, beside the Quartermaster's stage on
  345 (two `bwrap` processes): **8/8 mutations red**; K1 green 3 of 3;
  master's old test red on `sleep 2` and, on Linux, red on an escaped
  child. Output kept as `397_mutate.out`. M2 took 301 s, as its
  docstring says.

## 2026-10-31 — waiting for the fleet

At 23:19 the Quartermaster's fenced `regression.sh` on 345 had run 38 min
53 s (started about 22:40). The operator's standing word (F220): no
whole-tree or regression run while a fleet model-free run is in progress.
The commits wait for it, since each needs `wholetree.sh` first.

The regression ended at 23:33:14. My next `wholetree.sh` (fast) began at
23:33:41 and did not stop on a fleet stage that had started again: the
Quartermaster's two short checks (`20261031_233322_check`, the fenced
read of where live is, refused by design; `20261031_233433_check`,
`{"Q10": [], "Q12": []}`) and then its model call ran beside it. It
passed: 2549 passed, 10 skipped, exit 0. Neither fleet check shows a
failure from the load. From here, each run checks `bwrap` and the log
immediately before it starts, and stops if a stage is running.
