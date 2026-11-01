# Phase 397 — The one-second window in a fleet test (F241)

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-10-31

---

## Goal

Unblocks a clean full run on the Mac (K43 rule 4, K63): the independent
check that follows 345, and every first-shop phase after it. The operator:
"give me the prompt for the builder chat to fix that test".

After this phase:
1. (a) `test_run_group_kills_the_whole_group_and_says_what_it_printed`
   does not fail because a busy machine was slow to start its planted
   command; every test in `tests/test_phase392_check_limit.py` that gives a
   real process a short window to finish or print gets a window load
   cannot close;
2. (b) the check that the planted command's child was killed can fail on
   macOS as well as on Linux;
3. the three proofs stand as strongly as before: the whole group is
   killed; what was printed is kept; the run ends inside its bound.

## The plan of record

Row 10 of "Next, in order" in `docs/reports/2026-10-12_plan_of_record.md`,
after 345 and before 343, built by a builder: the dated entry of
2026-10-31, later, on the operator's word recorded as K63 in
`docs/decisions.md`.

## Logic

Causes and the measurements behind them: `397_step0.md`, S0-1 to S0-4.

1. **(a)** `WINDOWS = (1, 2, 4, 8, 16, 32)`. The test runs `planted()` in
   each window in turn, each in its own folder, and stops at the first in
   which the pid file holds a whole line (written after `echo started`).
   Every window asserts `elapsed < window + 29`. On the window that
   counts: "started" in what `run_group` kept, then the child not alive.
   No window reaching the child fails the test, saying so.
   `test_run_group_passes_a_run_that_ends` gets `timeout=120`.
   `test_the_engineers_over_limit_run_stops_once_and_is_not_started_again`
   is unchanged (S0-3: nothing must happen inside its window).
2. **(b)** `alive(pid)` asks `ps -o stat= -p <pid>`: alive when a state
   other than `Z` is printed; ended when nothing is printed and `ps` exits
   1; any other answer fails. A new test,
   `test_alive_answers_on_this_system`: this process alive, an unreaped
   exited child (a zombie) not, a reaped child not.
3. **Finish line:** with `sleep 2` planted before `echo started`, the old
   test red 10 of 10 (Step 0) and the new one green; the mutations below
   red; `397_mutate.py` runs on Linux and macOS.
4. **The record:** F242 for the three tests elsewhere (filed at Step 0);
   this document at v1.1, the phase log, the floor raised by a diff of
   collected ids, the handoff. Nothing under `.claude/skills/fleet/`
   changes, so nothing moves on the desktop after the merge; the advisor
   runs the full suite on the Mac, and F241 closes when it passes.

## Rule-1 stops anticipated

None. The prompt's own stop, a change that drops or weakens one of the
three proofs, does not arise: each is asserted on the window that counts
with the old strength, and the bound keeps its 29 s of slack (S0-4).

## Tests

- `tests/test_phase392_check_limit.py`: the two tests changed, `alive()`
  rewritten, one test added.
- Mutations, `397_mutate.py` (red): M1 what was printed is lost; M2 only
  the direct child is killed; M3 the run outlives its bound; M4 a child
  escapes the group (b's known-bad); M5 `alive()` answers "ended" without
  asking; M6 a zombie counts as alive; M7 the windows do not widen, and
  M8 a window counts before its child is reached, each with `sleep 2`
  planted. Must stay green: K1, `sleep 2` planted. Master's old file, for
  the record: red on `sleep 2`; on an escaped child, red on Linux and
  green on macOS.

## Non-goals

F240's cause; the 47 fence-boundary tests that ran in neither full run;
the three tests of F242; any change to `run_group`.

## Planned items

- [ ] (a) the widening windows; the 120 s window
- [ ] (b) `alive()` through `ps`; its own test
- [ ] the mutations, red, and the known-bad green
- [ ] the regression of record, the close-out, the handoff

## Version history

| version | date | what |
|---|---|---|
| 1.0 | 2026-10-31 | the plan |
