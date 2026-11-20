# Phase 407 — phase log

**Status:** In progress

## 2026-11-20 — Step 0 and v1.0

The operator, 2026-11-20 (K96): "do that and let me know where issues
stand", answering the advisor's proposal for F285.

Master `3908d99` holds K96, row 407 (🚧), the prompt
(`docs/prompts/407_the_operators_decision_asked_first.txt`) and the plan of
record's entry. This branch is `phase-407-the-operators-decision-asked-first`,
from `3908d99`.

Step 0 (`407_step0.md`): the scout stage labels `step0:done` whatever the
report says, the plan writer runs on that label, and P4 refuses a reshape
only after two calls; `escalate` already carries `needs-admiral` for ten
other stops. Classification: extension.

v1.0 (`407_implementation.md`): one helper, `Fleet.ask_reshape`, called by
the scout stage after its report and by the plan writer's stage before any
model call; five tests; six mutations. Committed and pushed as `68b91aa`
before any code.

**A guard block, recorded as rule 6 asks.** The first try at that push held
`git commit` and `git push` in one command. The push guard refused it before
anything ran: "This command runs `git commit` before `git push`, and the
guard judges the push before any of it runs, so it would push a commit it
never saw. Run `git commit` and `git push` as separate commands." The
commit, a whole-tree run on it, and the push were then three commands. The
guard is unchanged.

## 2026-11-20 — the build

- **`Fleet.ask_reshape`** (`.claude/skills/fleet/dispatcher.py`) reads the
  report's word with `plan_check.classification`. On reshape it calls
  `escalate(issue, rank, "needs-admiral", question)`. The question carries
  the reason's first sentence, at most 300 characters, and the two answers
  K90 and K95 gave.
- **`stage_scout`** calls it on the report it wrote, before `step0:done`.
  **`stage_captain`** calls it before `captain.write_plan`, and on a
  reshape returns "reshape: the operator is asked" with no model called.
- **The record:** the dispatcher's docstring, and the fleet skill's
  `SKILL.md` (a section, and the list of tests) and `CHANGELOG.md`.
- **Tests:** `tests/test_phase407_reshape_asks_first.py`, 8 passed. With
  389's dispatcher tests, 390's resume tests and 392's next-mission tests,
  74 passed.
- **Lint:** no new finding in `dispatcher.py` (9 before, 9 after). The test
  file carries only the redefined-name warning that every user of 389's
  `world` fixture carries. The code counts read `src/`, which 407 does not
  touch.
- **A first whole-tree run failed, before any commit:** the line above named
  that warning by its lint code, and `finding_check` B2 read the code as a
  finding number with no entry. The standalone `finding_check.py .` had
  passed, because it reads only `completed/`, while the whole-tree run reads
  `in_progress/` too. The line now names the warning in words.
- **Mutations:** `407_mutate.py`, 7/7 red (`407_mutate.out`).
- **The floor:** 12968, by a diff of collected ids against master at
  `3908d99` (12960): +8 −0, all in the new file.
