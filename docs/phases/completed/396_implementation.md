# Phase 396 — The fleet's four slips from 348 and 385

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-10-31 (v1.0 `e06db8c`)

---

## Goal

Unblocks 345 and every first-shop phase after it (K43 rule 4, K61), whose
Quartermaster verdicts are not trustworthy until the code check runs in
the fence. The operator: "fix the four things the fleet got wrong on 348
and 385 before the next phase."

After this phase:
1. (a) the Quartermaster's Q10 and Q12 run in the fence and give a
   result; a check that cannot run says why;
2. (b) a fleet close-out writes nothing about a refute pass, and a phase
   whose log has the Red Team's checklist cannot also say no refute pass
   ran;
3. (c) the next mission is read from master as it is after the cycle's
   stages, not as it was at the cycle's start;
4. (d) the Red Team and the Quartermaster read the plan as it stood when
   `plan:approved` was last applied.

## The plan of record

Row 8 of "Next, in order" in `docs/reports/2026-10-12_plan_of_record.md`,
after 385 and before 345, built by a builder: the dated entry of
2026-10-31, on the operator's word recorded as K61 in `docs/decisions.md`.

## Logic

Causes and the measurements behind them: `396_step0.md`, S0-1 to S0-4.

1. **(a)** `dispatcher.check_run` builds a command's script with
   `shlex.join(command)`. `quartermaster.no_result_why(check)` gives the
   reason for no result: the exit, and the output's first line naming an
   error, else its last line, else "it printed nothing"; `code_findings`
   passes it to `code_checks`, whose "no result" finding always carries a
   reason. Finish line: `check_run`, unstubbed, runs `code_command` to a
   parsed result in a test; the real fence on 348's and 385's merged
   heads prints a `{"Q10": …, "Q12": …}` line.
2. **(b)** `engineer.BRIEF` rule 7: the phase goes to the Red Team after
   the close-out; write no sentence that a refute pass did or did not
   run, and leave refute out of the phase log; the dispatcher commits the
   Red Team's `## Refuter pass` table (A8). `closeout_check`: A8 also
   refuses a phase whose log carries the checklist while its v1.1, its
   log outside the table, or its handoff says "no refute pass" (file and
   line named). 385's two lines are deleted. Finish line: the real lines
   of 303, 348 and 385 are each refused; master's closed phases pass.
3. **(c)** `cycle()` calls `update_mirror()` and `master_rows()` again
   just before `next_due`. Finish line: a merge and an issue close during
   a stage open no issue in the same cycle.
4. **(d)** `red_team.plan_commit(clone, phase, approved_at=None)`: with a
   time, the newest commit changing the plan at or before it; without,
   the first commit, and the gathers' headers say which. The dispatcher's
   Red Team and Quartermaster stages pass `last_applied(label_events,
   "plan:approved")`. Finish line: 348's history picks `85b2db5`'s place,
   not `f1a4146`'s.
5. **The record**: this document at v1.1, the phase log, the fleet
   skill's `SKILL.md` and `CHANGELOG.md` (and the closeout skill's for A8),
   the floor raised by a diff of collected ids, the handoff with the
   after-the-merge block for the desktop.

## Rule-1 stops anticipated

None. The prompt's own stop, a change that loosens a Quartermaster check,
the push gate or a deploy refusal, does not arise (Step 0, S0-5).

## Tests

- `tests/test_phase396_slips.py`: for each slip, its real fixture refused
  or reproduced before the fix and passing after; the unstubbed
  `check_run` on `code_command`; the A8 contradiction on each real line
  and its control (a log with the checklist and no such line; a log with
  "No refute pass ran" and no checklist still passes A8); the cycle with
  a merge during a stage; `plan_commit` on 348's history, and its
  fallback said.
- `.claude/skills/fleet/fixtures/slips396/`: the real artefacts, and the
  real-fence output.
- Mutations: `396_mutate.py`, each fix reverted on its own, red.

## Non-goals

Q3's override (F237); Q12 and `migrations.py` (F238); any change to what
a check accepts; the Red Team's own judgement of a false line (385's
round 1 kept it); the duplicated Q10/Q12 lines in a verdict.

## Planned items

- [x] (a) `shlex.join`, `no_result_why`, tests
- [x] (b) the brief, A8's contradiction, 385's two lines, tests
- [x] (c) the cycle's refresh, test
- [x] (d) `plan_commit` and its callers, tests
- [x] the real fence on 348's and 385's heads, kept
- [x] the mutations, red
- [x] skills' SKILL.md and CHANGELOG.md
- [x] the regression of record, the close-out, the handoff

## Deviations

- **(b)'s trigger is wider than the checklist.** v1.0's Logic 2 named a
  log carrying the `## Refuter pass` checklist. 303's log, when the
  Quartermaster read it, had no checklist yet, only dated entries for the
  Red Team's rounds; so a dated "Red Team's round N" heading counts too,
  or 303's real line would have passed.
- **One test added beyond v1.0's list:** a stage-level test that feeds
  385's real output through the Quartermaster's stage and reads the
  comment, so `code_findings` itself is held (mutation A2).
- **One mutation dropped as equivalent** (C2, the cycle's start-of-cycle
  rows after the refresh); the phase log says why.
- **The regression of record ran in the fence**, as 393's to 395's did:
  this checkout's `regression.sh` failed the four tests that fail on
  master here too (the phase log). Its driver is `396_regression.py`;
  the real-fence proof's is `396_real_fence.py`.
- **No bug fixes.**

## Results

- **Tests:** `tests/test_phase396_slips.py` (31) and one in
  `tests/test_phase392_plan_order.py`. Collected floor 12152 → 12184, by
  a diff of collected ids against master at `8e5f014` (+32 −0).
- **Each slip's real artefact, refused or reproduced before the fix and
  passing after** (`.claude/skills/fleet/fixtures/slips396/`): 385's
  fenced code-check output and 348's verdict lines (a); the five false
  lines of 303, 348 and 385 (b); the 2026-10-31 log (c); 348's plan
  history and `plan:approved` events (d).
- **The real fence** (a), on the heads the Quartermaster judged: 348
  `{"Q10": [], "Q12": [migrations.py, 575,007 bytes]}` (F238), 385
  `{"Q10": [], "Q12": []}` (`a_real_fence_348.txt`, `a_real_fence_385.txt`).
- **Mutations:** 18/18 red (`396_mutate.out`).
- **Regression of record** (inside the fence, after `wholetree.sh --full`
  5017 passed): Regression of record: 12079 passed, 0 failed, 105 skipped, 0 errors at `c8bd296` (13 min 8 s wall, `python -m pytest -n auto --dist load --cov=motodiag`, exit 0) (run inside the fleet's fence)
- **Line coverage of record:** 87.71% at `c8bd296` (the pin is 87.50%).
- **Live:** none; this phase changes nothing on live.
- **F237, F238** filed, for the operator's decision.

## Version history

| version | date | what |
|---|---|---|
| 1.0 | 2026-10-31 | the plan (`e06db8c`) |
| 1.1 | 2026-10-31 | built; Deviations and Results |
