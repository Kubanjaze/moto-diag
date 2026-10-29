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

## 2026-10-28 — v1.0, and a second guard block

- **v1.0** committed at `544012b` and pushed. `plan_check 394`: PASS (a first
  run failed P3, a limit stated without its query, and P6, an ellipsis in
  Logic; both fixed before the commit).
- **The push guard refused** `git commit … && git push` in one command
  ("it would push a commit it never saw"). Committed, then pushed, as two
  commands. The guard is unchanged.
- **A third block:** `sed -i` on `dispatcher.py`'s import line was refused
  by the edit guard; the import was changed with the Edit tool.

## 2026-10-28 — the build (Logic 1–6)

- **`rank_call.py`:** `command(model, schema, tools)` has no brief; `call`
  passes `input=prompt`; `LaunchFailed(Stop)` for an `OSError` from `run`.
- **`dispatcher.py`:** `FencedRunner.fenced(…, input=)` replaces
  `token_pipe`'s `stdin=DEVNULL` with the brief; `__call__` hands it on.
  `session(cmd, brief, …)` writes `<run>/session.brief` and opens it as
  stdin; resumed, the brief is `engineer.CONTINUE`; a `Popen` `OSError` is
  `LaunchFailed`. `started()` asks `failed_start()` first.
- **`engineer.py`:** `session_argv(model)` and `session_brief(…)`.
- **`journal.py`:** `call_key` drops `-p` alone when a flag follows it.
- **Existing tests moved to stdin** (the brief was read at `cmd[2]` or
  after `-p`): 20 failed on the first run, all of that kind; the stubs in
  `test_phase389_captain.py`, `_scout.py`, `_red_team.py`, `_engineer.py`,
  `test_phase392_ranks_cite.py`, `_answers.py`, `test_phase390_resume.py`,
  `test_phase391_dispatcher.py` and 388's `Host` (`model_briefs()`) now
  read stdin. Then 729 passed.
- **`tests/test_phase394_brief_on_stdin.py` (18).** A stand-in `claude` on
  PATH, a real process, records its argv and its stdin; a stand-in fence
  execs what follows `--`. The control: the old shape with the 300 KiB
  brief raises errno 7 on this kernel. Each rank (Red Team, Quartermaster,
  the Captain's recommendation and plan, the Science Officer's two calls,
  the XO, the Yeoman) and, through the fence, a rank call fresh and resumed
  and the Chief Engineer's session: the whole brief on stdin, no argument
  at or over 131072 bytes. A launch `OSError` on the 389 walk-through's
  stand-in issue 31 (not the real #31, which nothing here touches): one
  `started`, one stop naming errno 7, label `review:open` unchanged, three
  more cycles with no model call and no comment, no "cycle failed". The
  Engineer's launch the same. `started` once over a failed run and two
  retries (the log says twice that the comment stands), then the stage
  runs to `review:clear` with still one; again after a stop and the label
  re-applied, two. `failed_start` only for a failed run, only for its rank.
- **Mutations:** `394_mutate.py`, 15/15 red (`394_mutate.out`). While
  writing them, S2 (any run's `started` stands) was judged, not run, to
  survive the first draft of the tests: in every walk-through the last rank
  comment after a stop is the stop. So
  `test_only_a_failed_runs_started_stands_for_a_retry` was written first,
  and the mutation run came after it.
- **The floor:** a diff of collected ids against a master worktree at
  `c608169`: 11738 → 11756, +19 −1 (18 new; 392's order test renamed).
- **The skill and its CHANGELOG** say it.
