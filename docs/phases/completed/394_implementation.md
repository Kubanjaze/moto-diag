# Phase 394 — The fleet passes a rank's brief on standard input

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-10-29 (v1.0 `544012b`)

---

## Goal

Unblocks 303. PR #34, 303's build (+3579 lines), makes the Red Team's
brief larger than Linux's 128 KiB limit on one command-line argument
(`MAX_ARG_STRLEN`). `rank_call.command` puts the brief in argv as
`claude -p <brief>`, so starting the call raises `OSError: [Errno 7]
Argument list too long`, the cycle fails every 5 minutes, and each retry
says "Red Team started" again on #31: 69 times by 02:34 UTC on 2026-10-29
(`394_step0.md`, S0-1).

After this phase:
1. every rank's brief reaches `claude` on standard input, fenced and not,
   whatever its size;
2. a stage whose model call cannot start stops once, with a comment on its
   issue, label unchanged; the cycle does not fail and does not retry;
3. the "started" comment is said once per stage run, not once per retry.

## The plan of record

Row 3 of "Next, in order" in `docs/reports/2026-10-12_plan_of_record.md`,
right after 303, built by a builder, needing nothing from the operator:
the dated entry "2026-10-28: 394 goes right after 303 (K55)", on the
operator's word recorded as K55 in `docs/decisions.md`. A fleet-only phase:
it unblocks 303, a Wave 1 phase whose row is 🚧.

## Logic

1. **`rank_call.py`.** `command(model, schema=None, tools=FENCE)` returns
   `["claude", "-p", "--model", model, *tools, "--output-format", "json"]`,
   plus `--json-schema` when a schema is asked for: no brief in argv.
   `call()` passes the brief as
   `run(…, input=prompt)`. Measured at Step 0 (S0-2): `claude -p` with no
   prompt argument reads stdin, a 291094-byte brief included.
2. **A launch failure.** `rank_call.LaunchFailed(Stop)`: "the model call
   could not start: <the OSError>". `call()` raises it for an `OSError`
   from `run`, so every rank's existing stop applies: `run_stage` says it
   once on the issue (`stopped rank=<rank>`), the label is unchanged, and
   `due_for` reads that marker so the stage is not due again until the
   label is applied again. `xo.review` and `yeoman.digest` catch `Stop`
   already.
3. **The fence.** `FencedRunner.__call__` hands `input` to `fenced()`,
   which passes it to the fence in place of `token_pipe`'s
   `stdin=DEVNULL`. `fence.sh` and `fence_net.py inside` inherit fd 0
   (S0-2), so nothing in the fence changes.
4. **The Chief Engineer.** `engineer.session_argv()` returns the command
   without the brief; `engineer.session_brief()` returns the brief.
   `FencedRunner.session(cmd, brief, …)` writes the brief to
   `<run>/session.brief` and opens it as the session's stdin; a resumed
   session's brief is `engineer.CONTINUE`. An `OSError` from `Popen` is
   `LaunchFailed`.
5. **The journal's key.** `journal.call_key` drops `-p` and, only when it
   is not a flag, the argument after it. A command written before this
   phase and one written after key the same, so a stage cut across the
   upgrade resumes its calls.
6. **"started" once per stage run.** `Fleet.started()`: when the issue's
   last rank comment is this rank's `started` marker, and that marker's run
   ended `failed: …` in its journal, the stage is a retry of the same run.
   It says nothing new; the journal's `started` step records whose marker
   stands, and the log says so. Any comment in between (a stop, a verdict,
   another rank) makes it a new stage run, which says "started".

## The change log's three newest entries

- **2026-10-26, R8: an operator paste block's `gh` names its repository.**
  The check it became: `tests/test_roadmap_continuity.py`
  (`.claude/skills/closeout/roadmap_check.py` R8). This phase's handoff
  block carries `-R Kubanjaze/moto-diag`.
- **2026-10-22, `fleet` joins the procedure folders.** Held by the folder's
  own tests (`tests/test_phase387_fleet_contract.py`); the row is text.
  This phase extends the folder.
- **2026-10-20, rule 6: plain English to the operator.** No check: "Text
  only; no check holds it." The handoff's block is written to it.

## Rule-1 stops anticipated

- **A real fork:** none; the prompt fixes all three behaviours.
- **A threshold or a rule's definition:** none changes.
- **A test that cannot be made green:** none expected.
- **A login or a credential:** none; the fleet's restart after the merge
  is the operator's own block.
- **A live-database change:** none; nothing here reads live.

## Tests

- `tests/test_phase394_brief_on_stdin.py`:
  - a 300 KiB brief reaches the model call (a stub runner) on stdin, with
    no argument over 128 KiB, for each rank: XO, Yeoman, Science Officer
    (both calls), Captain (plan and recommendation), Red Team,
    Quartermaster, Chief Engineer;
  - the same through `FencedRunner` (the fence argv and stdin), fresh and
    resumed;
  - a launch `OSError` stops the stage once: one stop comment, label
    unchanged, the cycle does not raise, the next cycle runs nothing;
  - "started" said once over a failed run and its retry; said again after
    a stop;
  - `call_key` equal for the old and the new command shapes.
- The existing tests that read the brief at `cmd[2]` read it from stdin.
- `docs/phases/in_progress/394_mutate.py`: every mutation red.
- `wholetree.sh` before each commit; `wholetree.sh --full`, then
  `regression.sh`, for the regression of record.

## Non-goals

- Touching #31 or PR #34: #31 stays held with `needs-admiral` until the
  operator's block after the merge.
- `fence_probe.py` and `claude -p /usage`: short fixed arguments, not
  briefs.
- Shrinking any rank's brief.
- Any migration, anything under `data/`, seed data, a split or an eval
  protocol, or live.

## Planned items

- [x] `rank_call.py`: stdin, `LaunchFailed`
- [x] `dispatcher.py`: `FencedRunner` stdin, the Engineer's session, `started()` once per run
- [x] `engineer.py`: `session_argv`, `session_brief`
- [x] `journal.py`: `call_key`
- [x] tests; existing tests moved to stdin; collected floor
- [x] skill and CHANGELOG
- [x] mutations; regression of record; close-out; handoff with the operator's block

## Deviations

- **The regression of record ran in the fence, not in this checkout.**
  `wholetree.sh --full` here failed gate 11 (4 failures, all
  `tests/test_phase205_gate11.py` run by later gates). Gate 11 reads
  `../moto-diag-mobile`, whose local `main` carries the unpushed commit
  `7489fd5`, 303's API snapshot ("push after 303 merges"). Master fails it
  the same way (2 failed, 19 passed). The run of record is the fleet's
  model-free run of `ff3ce4a` (`394_regression.py`) with the mobile
  repository at its published `origin/main`, `0074eb9`. Nothing in either
  repository was changed for it. Open in the handoff.
- **`failed_start`** is a method of its own (the plan put the check inside
  `started()`), so it could be tested directly: in every walk-through a
  stop, not a `started`, is the last rank comment.
- **A test the plan did not list:**
  `test_only_a_failed_runs_started_stands_for_a_retry`, for mutation S2.
- **The existing tests moved to stdin** were ten files the plan did not
  name: the stubs of 388 (`Host.model_briefs`), 389 (Captain, Science
  Officer, Red Team, Engineer, dispatcher), 390 (resume), 391 (dispatcher)
  and 392 (answers, ranks cite).
- No bug fixes: the register is empty.

## Results

- **Step 0:** 69 launch failures in `dispatcher.log`, 69 "Red Team
  started" comments on #31; `claude -p` 2.1.312 reads a 291094-byte brief
  from stdin; this kernel refuses a 131073-byte argument and takes a
  131072-byte one.
- **Tests:** `tests/test_phase394_brief_on_stdin.py`, 18, against a
  stand-in `claude` on PATH under the kernel's real limit. Collected floor
  11738 → 11756 by a diff of collected ids against master at `c608169`
  (+19 −1).
- **Mutations:** 15/15 red (`394_mutate.out`).
- **Regression of record** (inside the fence, after `wholetree.sh --full`
  4806 passed): Regression of record: 11651 passed, 0 failed, 105 skipped, 0 errors at `ff3ce4a` (34 min 35 s wall, `python -m pytest -n auto --dist load`, exit 0) (run inside the fleet's fence)
- **Live:** none; nothing here reads live.
- **#31 and PR #34** were read, never written.
