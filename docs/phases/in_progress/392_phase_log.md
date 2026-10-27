# Phase 392 — phase log: the fleet follows the plan of record

**Status:** In progress
**Branch:** `phase-392-the-fleet-follows-the-plan`
**Prompt:** `docs/prompts/392_the_fleet_follows_the_plan.txt`

## 2026-10-27 — start

- Read the plan: rows 389A to 392, `ROADMAP_AUTHORITY.md` (392 is backend,
  205+), the newest handoff (`2026-10-26_391_closed.md`), `FOLLOWUPS.md`
  F223 to F228, the plan of record, `docs/decisions.md`, the `fleet`
  skill, `dispatcher.py`, `captain.py`, `red_team.py`, `xo.py`,
  `engineer.py`, `plan_check.py`, `fleet_git.py`, `refute_check.py`,
  `worker_loss.py`, `fence.sh`, the unit.
- `dispatcher.log`: no stage running (the last line, 10:09:32, #14's Red
  Team stopped on C7). #14 is parked; not touched.
- `wholetree.sh` exit 0 (2271 passed, 10 skipped, 72.7 s).
- **Guard block, kept as it is:** the push guard refused `git commit … &&
  git push` in one command ("it would push a commit it never saw"). Run
  as two commands.
- Row 392 🚧 on `master`, `f1763df`, pushed. GitHub printed "Cannot update
  this protected ref" and took the push all the same (the admin bypass):
  `git ls-remote origin refs/heads/master` is `f1763df`.

## 2026-10-27 — Step 0, and the operator's answers

`392_step0.md`. The operator answered the four Step 0 questions in one
message before they were put; recorded verbatim as K48–K51 with
`yeoman.py decide`. The reading of K50 (its head governs its parenthesis:
all five rule-1 kinds are never answered) and the decisions that are not
forks are in Step 0, S0-4 and S0-5.

F227's measurement started at Step 0 (`392_fd_probe.py`, a fenced full
run on `f1763df` with each process's open files sampled from outside), in
`~/motodiag/p392/fd_full`.
- **Guard block, the same as at the start, kept as it is:** the push guard
  refused the Step 0 commit and its push in one command, the same reason.
  My slip; run as two commands, and every commit since is pushed apart.

## 2026-10-27 — the record, read exactly (Logic 1, 2, 4)

- `plan_order.py`: the "Next, in order" list, the dated changes, the
  decisions with their Covers column, `bearing`, `brief_block`,
  `cite_line`, `answer`, `first_shop`, `check`.
- The plan of record gained the list at its top and the dated entry
  2026-10-27 (K48). The list transcribes the order already there: 392,
  303, 348, then Wave 1's own numbering; what each row needs is Wave 1's
  and "The operator's steps outside the code". Every `docs/decisions.md`
  row has `no stop`: no decision so far answers a stop the record may
  answer.
- `yeoman.py decide --covers`, refusing a rule-1 kind and a line that is
  not a lookup.
- `plan_check.py` P9 and P10. The pin measured, not guessed: without it
  384 and 386 at their v1.0 fail P9 only (P10 passes them: neither names
  the fleet's folder), 387 fails both. `BEFORE_THE_RECORD` holds exactly
  that, equality-tested. Four known-bad cases; the first draft of
  `P9_kid_names_another_phase` failed nothing (the list's own route, K90,
  still put 900 in order) and was replaced by a plan citing a K-id about
  something else, which fails P9 alone. The dispatcher tests' stand-in
  plan for their trial phase 902 now cites K92, a row of the good tree's
  `docs/decisions.md` naming 902: the first whole-tree run failed 46
  tests in 389's and 390's walk-throughs, every one the Captain's plan
  failing P9.
- **Guard blocks, three, all kept as they are:**
  - the edit guard refused a Python script writing
    `tests/test_phase387_yeoman.py` ("a Python script body writes
    tests/…"); done with the Edit tool;
  - the edit guard refused a Python script editing `plan_check.py` whose
    text names `src/` ("writes to a path the edit guard cannot resolve,
    and the body names src/ or tests/"); done with the Edit tool;
  - the edit guard refused a command with a stray `sed -i` I had left at
    its end; the two fixture files were written with the Write tool.
