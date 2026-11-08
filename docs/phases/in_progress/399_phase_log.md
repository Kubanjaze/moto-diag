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

## 2026-11-08 05:01–06:19 UTC — the censuses and a first regression, not of record

- **The census before** (`1222862`, worktree of master, throwaway HOME, 12
  chunks between fleet stages; a fleet sandbox beside chunks 2, 4, 6, 7
  and 10): 12358 passed, 9 failed, 8 errors, 49 skipped; the failures and
  errors are tests that need the real HOME or this machine's tools (388's
  fence boundary, 257's orchestrator guards, 209's packaging, 204's
  ffmpeg). **6 files wrote to the default ledger, 57 rows a run, every one
  `sess-1`:** `test_phase393_code_checks.py` 21 (3 tests),
  `test_phase392_answers.py` 16 (4), `test_phase392_red_team_c7.py` 7 (1),
  `test_phase396_slips.py` 7 (1), `test_phase392_check_limit.py` 4 (1),
  `test_phase392_next_mission.py` 2 (1). F254 measured the four in the
  middle; the first and fifth are new. The real ledger grew by 4 rows
  meanwhile, all real (2 Captain, 2 XO, 371).
- **The census after** (`fdafadc`, worktree, the same way; a sandbox
  beside chunk 10): **0 files, 0 rows**; the real ledger byte for byte the
  same before and after (5,520,588 bytes, sha256 `41535625…`).
- **A regression at `fdafadc`, not of record**, inside the fence, 00:28 EST:
  wholetree --full 5092 passed, 36 skipped; then 11509 passed, 0 failed,
  105 skipped, **819 errors**, exit 1. The real ledger unchanged across it
  (0 rows appended). The fleet was quiet (371 on `needs-admiral` from
  23:51). Every error is the database tripwire, on one worker (gw14), from
  `test_phase244H_test_db_isolation.py::TestTheTripwireItself::test_the_tripwire_message_names_the_cause`
  on.

### Bug fix #1 — the fixture's `monkeypatch` moved a teardown

The autouse fixture asked for `monkeypatch`, so `monkeypatch` was set up
before conftest's tripwire (`_never_the_production_database`) and torn
down after it. 244H's `test_the_tripwire_fires_when_the_default_points_at_production`
sets `MOTODIAG_DB_PATH` to production through its own `monkeypatch`: its
undo now came after the tripwire's `reset_settings()`, so the next test on
the worker read the production path. Reproduced in one process with
`test_phase244H_test_db_isolation.py` then `test_phase24_honda_cbr600f.py`
(10 errors). The census after had more errors than the census before (57
against 8) for the same reason. **Fix:** the fixture sets and restores
`FLEET_LEDGER` itself and asks for no `monkeypatch`. The two files: 20
passed, 1 skipped. New test
`test_the_fixture_leaves_the_database_tripwire_as_it_was` runs them; new
mutation M12 (the fixture's first version) is red. `399_mutate.py`:
**12/12 red**, the real ledger's sha256 the same before and after.
`COLLECTED_TEST_FLOOR` 12434 (+18 −0 against `1222862`).
