# Phase 396 — phase log: the fleet's four slips from 348 and 385

**Status:** In progress

**Started 2026-10-31** on the home desktop (WSL2), the only writer, on
`phase-396-the-fleets-four-slips`. The prompt is
`docs/prompts/396_the_fleets_four_slips.txt` (the operator's words,
verbatim); the operator's word is K61.

## 2026-10-31 — start

- Master fetched at `8e5f014`; nothing newer from the Mac, so K61 is the
  next K-id.
- `3dff6d0`: the prompt, row 396 🔲, row 8 of "Next, in order" with the
  dated entry, K61 (by `yeoman.py decide`) and
  `tests/test_phase392_plan_order.py` (one test added). Merged to master as
  `230a077` and pushed, as 395's prompt was, so the fleet reads 396 as
  next. At 13:26 the dispatcher logged "next: phase 396 is a builder's
  (the plan's #8); the fleet waits for it".
- **Guard blocks** (recorded, guards unchanged): the edit guard refused a
  Python script body writing `tests/test_phase392_plan_order.py`, and a
  `sed -i` on the ROADMAP; the Edit tool did both. The push guard refused
  `git checkout … && git push` in one command; they ran separately.
- Row 396 🚧 on the branch before Step 0.
- The fleet idle before each whole-tree run: `pgrep -x bwrap` empty, and
  no model-free run open in `dispatcher.log`.

## 2026-10-31 — Step 0

`396_step0.md`. Each slip's cause, measured on the real artefact:
(a) `check_run`'s `" ".join(command)` breaks the `sh -c` script, and the
reason given was a tail of the command; (b) A8 makes a fleet close-out
write "No refute pass ran" before the Red Team's table exists; (c) the
mirror is refreshed only at a cycle's start; (d) `plan_commit` is the
commit that first added the plan. F237 and F238 filed for the two
out-of-scope items.
