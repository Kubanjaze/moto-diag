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

## 2026-11-20 — the review, and its fixes

A fresh agent read the build's diff (`68b91aa..6eaf13c`), given the code and
the plan, not this log. It found seven points. Each was checked against the
code before anything changed:

1. **The question came before `step0:done`.** A question GitHub refused
   stopped the scout with only `mission` on the issue: after a release
   nothing was due, and nothing said so. The scout now labels `step0:done`
   first and asks after. A refused question leaves the plan writer due, and
   its guard asks again with no model call. Test:
   `test_a_question_github_refuses_is_asked_again_with_no_model_call`.
2. **Test 1's hold check could not fail.** With the cycle's skip for a held
   issue removed, the plan writer's guard asked again and the labels stayed
   as they were, so the test stayed green. It now counts the issue's comments
   and the plan writer's asks across the held cycle.
3. **Two claims had no test.**
   - The plan's test 5 says "a second call on the same issue posts no second
     comment (the step asks GitHub first)". That holds inside a stage's
     journal, on a resumed stage; outside one, `step()` runs every write. It
     is tested where it holds:
     `test_a_scout_cut_between_its_question_and_its_label_asks_once`, on
     390's kill harness. v1.1's Deviations says so.
   - A release after the plan writer's own ask:
     `test_the_release_after_the_plan_writers_ask_starts_the_plan_writer`.
4. **The reason.** "e.g." cut it short; an empty reason took the next
   heading; `**` inside it broke the bold; an @name would notify a GitHub
   user, which the report file never did. `reshape_reason` reads the
   Classification line only, cuts at a full stop before a capital, drops `*`
   and backticks, and puts an @name in a code span. Four cases.
5. **Another refusal still costs two plan-writer calls.** A Classification
   line that does not start with its word (a hand relabel such as
   "Classification (by the operator): extension") reads as that first word,
   and P4 refuses it after two calls with no label: F285's pattern, on the
   release path. Not changed in code: the scout writes the word first, and
   the question now says the line becomes `Classification: extension`, that
   word first. Recorded as a known limit in the fleet's `CHANGELOG.md`.
6. **Words that pointed the wrong way.**
   - The scout's note said "Next: the Captain writes v1.0." above the
     question. On a reshape it now says "Next: the operator's call, asked
     below."
   - After 24 hours the sweep named the Captain for a held issue's
     `step0:done`. On a held issue it now sweeps only the hold. That changes
     the sweep for every held issue, which the plan did not name; v1.1's
     Deviations says so. Test: `test_a_held_issue_is_swept_for_its_hold_alone`.
   - The question cited two K-ids, internal labels rule 6 keeps out of what
     the operator is asked. It now says "as you decided for phases 404 and
     405".
7. **A resumed plan writer reads its old clone.** Cut between its question
   and the label, with the report relabelled while the dispatcher was down,
   the resumed stage puts `needs-admiral` back on a report that already says
   extension; taking it off again starts the plan writer. Not changed:
   recorded as a known limit in the fleet's `CHANGELOG.md`.

- **Found sound by the same review:** the release, the hold, the revision
  rounds after a release, a cut inside `escalate`, and the parsing (P4's own
  function; on the real 404 and 405 reports it reads the right reasons).
- **Tests:** 16 passed; with 388's, 389's, 390's and 392's suites, 146
  passed.
- **Lint:** `dispatcher.py` 9 findings before, 9 after; the test file only
  the redefined-fixture warnings (`world`, and 390's `w`).
- **Mutations:** `407_mutate.py` 16/16 red (`407_mutate.out`). Z1, Z5 and
  Z7 moved to the rewritten lines; Z8 to Z16 are new, one for each fix and
  one for the resumed question.
- **The floor:** 12976, by a diff of the file's collected ids against
  `6eaf13c` (8): +8 −0; no other test file changed.
- **A guard blocked a command,** at 13:43 EST, during the advisor's work on
  405's hand-back block (K97), on a stand-in in the scratchpad: "edit guard:
  blocked — `sed -i` edits a file in place, and is blocked wherever it
  points." Nothing ran; the edit was made with the Edit tool. The guard is
  unchanged.
