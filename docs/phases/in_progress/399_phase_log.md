# Phase 399 — phase log: the fleet's cost ledger, made true (F254, F255)

**Status:** In progress

**Started 2026-11-08** (UTC; 2026-11-07 evening EST) on the home desktop
(WSL2), the only writer on this checkout, on `phase-399-the-cost-ledger`.
The prompt is `docs/prompts/399_the_cost_ledger.txt` (the operator's
words, verbatim); the operator's word is K69. The fleet works 371 beside
it from its own copy; its issues, labels and pull requests are left alone,
and its service is not restarted.

## 2026-11-08 04:02 UTC — start

- Master fetched at 04:02 at `1222862` (the prompt, rows 399 and 400 🔲,
  K68, K69, F254, F255 already on it). `pgrep -x bwrap` empty.
- Read before planning: `CLAUDE.md`, `docs/decisions.md` (K68, K69), F254
  and F255, the 398 handoff and its phase documents, and the code each
  finding names.
- F256 was the next free number (`next_f_number.sh`).
- Row 399 🚧 on the branch before Step 0.
- The fetch first moved the local `phase-398-the-two-stalls` branch (it was
  checked out); it was set back to `54e8b4a`, as it was, and master
  checked out.

## 2026-11-08 04:05 UTC — Step 0

`399_step0.md`. S0-1: 5,726 rows, 5,616 `sess-1`. S0-2: nothing in
`conftest.py` keeps a test off the default ledger. S0-3: the census runs
in chunks between fleet stages (F220), on a worktree of master; 1 of 12
chunks done when the plan was committed. S0-4: no real Engineer
`session.json` survives anywhere on the machine; the replay fixture is a
real result of the same command, from 371's Science Officer. S0-5: F256
filed, left.

**Decisions (recorded, not stops):**
- the census runs in paused chunks, not one run (F220; the fleet is
  mid-371), as the coordinator asked;
- the guard's check takes an appended row for the fleet's when one of the
  fleet's run folders names its session (Step 0's decision);
- the code was drafted while the census waited; the plan is committed
  before any code is.

## 2026-11-08 04:13–04:31 UTC — the build

- **(a)** `tests/support/ledger_guard.py`, loaded by `conftest.py`'s
  `pytest_plugins`: the autouse fixture (a ledger file per test) and the
  check (controller only; existing bytes unchanged, every appended row's
  session named in a fleet run folder). `rank_call.STAND_IN_SESSION`,
  `is_stand_in`, `rows`, `summary`, `rank_call.py ledger`.
- **(b)** `rank_call.Call` gains `phase`, `issue`, `run`, `source`, `key`;
  `context(run)`; `session_call`, `session_key`, `record_once`.
  `dispatcher.py`: `FencedRunner.ledger_context`, `ledger_session` (after
  the process ends, before a usage limit is raised, and on a read-back);
  `Fleet.ledger_read_in`, first in `recover`, with its log line.
- `tests/test_phase399_cost_ledger.py`: 17 passed, under a throwaway HOME.
- **Red on the old code** (master's `rank_call.py`, `dispatcher.py` and
  `conftest.py` copied in, then restored), under a throwaway HOME: 12
  failed, 5 passed. The 5 are the guard module's own tests (the module is
  new, so it is there either way); the guard broken on purpose is
  mutations M1–M4. On the old code this file alone wrote 16 rows into that
  HOME's default ledger: F254, reproduced.
- `399_mutate.py`, 04:30: **11/11 mutations red**, every run under a
  throwaway HOME; the real ledger's sha256 the same before and after
  (`6275db3a…`). Output kept as `399_mutate.out`.
- The fleet's 973 tests (`test_phase38[7-9]*`, `test_phase39*`) under a
  throwaway HOME: 969 passed, 4 failed, all four in
  `test_phase388_fence_boundary.py`, which reads the real HOME's
  `~/.config`; that file with the real HOME: 47 passed, the real ledger
  unchanged.
- **Design choice (recorded):** the Engineer row's key is the run folder
  and the sha256 of `session.json`, not the session id: `--resume` keeps
  the id, and each printed part is its own spend.
- `COLLECTED_TEST_FLOOR` 12416 to 12433, by a diff of collected ids against
  master at `1222862` (12416): +17 −0.
- wholetree fast at 04:31 (90 files): 2623 passed, 10 skipped, exit 0.
  `pgrep -x bwrap` empty before it. No push guard ran on the plan's push:
  this builder session runs outside the repository root, so the repo's
  hook is not loaded; wholetree fast was run by hand before each commit
  and push instead.
