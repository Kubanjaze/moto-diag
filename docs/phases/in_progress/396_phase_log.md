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

`e06db8c`: Step 0 and v1.0, pushed before any code.

## 2026-10-31 — the build

Tests first: `tests/test_phase396_slips.py` written before any fix, and
seen red: 26 of 29 failed. The two that reproduce a slip's behaviour, not
a missing name, failed as the real phases did: the unstubbed `check_run`
printed bash's "syntax error near unexpected token `then'" (385's kept
output, byte for byte but the paths), and the cycle with a merge during a
stage opened a second issue for the merged phase (#44).

- **(a)** `dispatcher.check_run`: `shlex.join(command)`.
  `quartermaster.no_result_why`: how the run ended, a time limit first, then
  the first line naming an error, else the last line; `code_findings`
  passes it; `code_checks` never leaves the reason empty. A stage-level
  test feeds 385's real output through the Quartermaster's stage and reads
  the comment.
- **(b)** `engineer.BRIEF` rule 7: the phase goes to the Red Team after the
  close-out; no sentence about a refute pass, the word left out of the
  log. `closeout_check.refute_contradictions`, inside A8. 385's v1.1 lost
  its two fragments ("no refute pass unless one runs" in Logic 8, "no
  refute pass" in Deviations), deleted, not rewritten (K9); 385's own
  checklist row still quotes the line it judged, which the check does not
  read.
- **(c)** `cycle()`: `update_mirror()` and `master_rows()` before `next_due`.
- **(d)** `red_team.plan_commit(clone, phase, approved_at)` and
  `plan_label`; `Fleet.plan_approved_at`; both gathers pass it. My first
  test expected #36's first approval (02:30Z) to pick the XO's round-2
  revision; the plan at 22:30 EDT was in fact still the Captain's draft,
  so the test was wrong, not the code, and now asserts both times.

**Mutations** (`396_mutate.py`, `396_mutate.out`): first run 17/19. A4
(the time limit said first) survived: its test's partial output had no
error line, so the error search found "time limit" anyway; the test now
has an error line the limit must win over. C2 (the cycle's start-of-cycle
`rows` kept after the refresh) is an equivalent mutant: `next_due` reads
the plan and the ROADMAP from the mirror itself, and `rows` only gates a
case `stage_next` re-checks against the fresh mirror; it was dropped. Then
18/18 red.

**The real fence** (`396_real_fence.py`, 389's rule): this branch's
`check_run`, the real `fence.sh`, the fleet's venv, a clone of the fleet's
mirror, at the heads the Quartermaster judged against the masters it
judged them on (348: `dd5aed2` on `d76b865`; 385: `46db82e` on `ddcdfd6`),
26 s. Both printed a result:
- 348: `{"Q10": [], "Q12": [{"file": "src/motodiag/core/migrations.py", "bytes": 575007, "base_bytes": 572812, "limit": 100000}]}` (F238);
- 385: `{"Q10": [], "Q12": []}`.
The command runs `/fleet/run/code_quality.py`, which exists only inside the
fence (`ls /fleet` on the host: no such file). Kept as
`fixtures/slips396/a_real_fence_348.txt` and `a_real_fence_385.txt`.

**Floor**: 12152 → 12184, by a diff of collected ids against master at
`8e5f014`: +32 −0 (`test_phase396_slips.py` 31, `test_phase392_plan_order.py` 1).
