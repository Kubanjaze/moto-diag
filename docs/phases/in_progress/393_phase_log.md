# Phase 393 — phase log: the code itself gets checked

**Status:** In progress

**Started 2026-10-29** on the home desktop (WSL2), the only writer, on
`phase-393-the-code-itself-gets-checked` from `master` at `159c430` (303
merged). The prompt is `docs/prompts/393_the_code_itself_gets_checked.txt`
(the operator's words, verbatim).

## 2026-10-29 — start

- **The row first.** Row 393 to 🚧, committed at `a38a36b` and pushed.
  `roadmap_check.py`: ok. `wholetree.sh` before it: exit 0, 2354 passed,
  10 skipped, 76.5 s wall, 74 files.
- **The fleet only read.** `dispatcher.log`'s last line: "next: phase 393 is
  a builder's (the plan's #4); the fleet waits for it". No model-free run in
  progress, so no wait was needed before any run (F220).
- **A guard block.** `git commit … && git push` in one command was refused
  by the push guard ("it would push a commit it never saw"). Committed, then
  pushed, as two commands. The guard is unchanged.

## 2026-10-29 — Step 0

`393_step0.md`. The tools pinned (ruff 0.16.9, mypy 2.3.1, coverage 7.14.1,
pytest-cov 7.1.0, in this venv and the fleet's); the counts measured twice;
the safe fixes tried in a scratch worktree (imports and f-strings only);
the two bugs measured.

- **A second guard block.** A shell heredoc writing the code-check fixtures
  into the scratchpad was refused by the edit guard ("a Python script body
  writes to a path the edit guard cannot resolve, and the body names src/ or
  tests/"): the fixture trees hold `src/motodiag/`. The fixture files were
  written with the Write tool. The guard is unchanged.
- **A first run with coverage, outside the fence** (not of record, for the
  stop's first reading): `python -m pytest -n auto --dist load --cov=motodiag`
  on `a38a36b`, 9 min 48 s wall, "4 failed, 11853 passed, 33 skipped". The
  four are the desktop's four (F216: no ffmpeg, no Subconscious profile,
  `osacompile` twice), not coverage's. Total line coverage 87.56%
  (31749 of 36258 statements, 296 files).
- **The fenced run with coverage** (the stop's reading of record):
  `393_fenced_measure.py ~/motodiag/p393/state a38a36b cov covA`, 35 min
  33 s, "11785 passed, 105 skipped", exit 0, 87.60%. Under 45 minutes; no
  stop. Details in S0-8.
- **The stop conditions:** none holds (S0-4, S0-8). The phase goes on.

## 2026-10-29 — v1.0

`plan_check 393`: PASS (a first run failed P3: `ruff check` is not in its
query vocabulary; the commands were re-run as `python -m ruff` and
`python -m mypy` and cited that way, and the checker is unchanged).
F234 and F235 filed before v1.0 cites them; `finding_check.py`: exit 0.
