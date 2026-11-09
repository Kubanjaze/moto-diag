# Phase 399 — phase log: the fleet's cost ledger, made true (F254, F255)

**Status:** Complete

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

### Bug fix #1 — 2026-11-08 — the fixture's `monkeypatch` moved a teardown

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

**Commit.** `2bb35de`

## 2026-11-08 19:01 UTC — the regression of record

- `2bb35de` pushed at 17:47 UTC. The time: not near 00:00 UTC (F246), and
  not in 18:20–19:00 EST.
- **The run of record**, as 398's: `Fleet.check_run` on `2bb35de` in a fresh
  clone in the fleet's fence, no model and no token, the fleet's venv, the
  mobile repository a clean clone at its published `main` (`0773f91`), by
  `399_regression.py` (398's driver, with the real ledger read before and
  after), its state folder under `~/.cache/motodiag/399_regression2/`.
  `wholetree.sh --full` inside it: 5093 passed, 36 skipped, exit 0.
  **What else ran:** no fleet stage (issue 54 held on `needs-admiral` from
  12:46 EST; `dispatcher.log`'s last line before it was the 12:51 reclaim);
  the always-on `motodiag-api.service` and the idle dispatcher. `pgrep -x
  bwrap` empty before it. **The real ledger:** 5,521,653 bytes and 5,731 rows before and after, sha256 9ed1861d… both times, 0 rows appended. Its lines, as
  printed:

Regression of record: 12329 passed, 0 failed, 105 skipped, 0 errors at `2bb35de` (37 min 54 s wall, `python -m pytest -n auto --dist load --cov=motodiag`, exit 0) (run inside the fleet's fence)
Skipped in the regression of record: [1] tests/test_phase191b_ffmpeg.py:249: real ffmpeg binary or fixture mp4 not available
Skipped in the regression of record: [1] tests/test_phase191b_ffmpeg.py:264: real ffmpeg binary or fixture mp4 not available
Skipped in the regression of record: [1] tests/test_phase191b_ffmpeg.py:269: real ffmpeg binary or fixture mp4 not available
Skipped in the regression of record: [1] tests/test_phase191b_ffmpeg.py:277: real ffmpeg binary or fixture mp4 not available
Skipped in the regression of record: [1] tests/test_phase191b_ffmpeg.py:283: real ffmpeg binary or fixture mp4 not available
Skipped in the regression of record: [1] tests/test_phase244H_test_db_isolation.py:79: no production database on this machine
Skipped in the regression of record: [1] tests/test_phase204_gate10.py:47: inside the fleet's fence: no ffmpeg on the home desktop
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:104: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:121: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:137: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:145: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:153: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:162: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:175: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:185: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:218: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:223: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:248: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:259: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:272: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:292: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:306: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:321: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:333: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:340: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:438: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:445: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:464: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase257_sandbox_boundary.py:106: sandbox-exec is macOS-only; the orchestrator runs only there
Skipped in the regression of record: [1] tests/test_phase257_sandbox_boundary.py:112: sandbox-exec is macOS-only; the orchestrator runs only there
Skipped in the regression of record: [1] tests/test_phase257_sandbox_boundary.py:119: sandbox-exec is macOS-only; the orchestrator runs only there
Skipped in the regression of record: [1] tests/test_phase257_sandbox_boundary.py:125: sandbox-exec is macOS-only; the orchestrator runs only there
Skipped in the regression of record: [1] tests/test_phase257_sandbox_boundary.py:131: sandbox-exec is macOS-only; the orchestrator runs only there
Skipped in the regression of record: [7] tests/test_phase257_source_checks.py:211: needs the on-disk library
Skipped in the regression of record: [1] tests/test_phase257_source_checks.py:476: acquired/Yamaha/library_om_contents_pdf_10_5YR-F8199-15_02.pdf is not in this machine's library
Skipped in the regression of record: [1] tests/test_phase257_source_checks.py:476: acquired/KTM/24_3214961_en_OM.pdf is not in this machine's library
Skipped in the regression of record: [1] tests/test_phase257_source_checks.py:527: the KTM manual is not in this machine's library
Skipped in the regression of record: [1] tests/test_phase257_manual_route_excerpts.py:367: needs the on-disk library
Skipped in the regression of record: [1] tests/test_phase257_orchestrator_guards.py:85: inside the fleet's fence: no Subconscious login there (K42)
Skipped in the regression of record: [2] tests/test_phase257_orchestrator_guards.py:149: inside the fleet's fence: osacompile is macOS-only
Skipped in the regression of record: [4] tests/test_phase257_sandbox_boundary.py:72: sandbox-exec is macOS-only; the orchestrator runs only there
Skipped in the regression of record: [1] tests/test_phase257_sandbox_boundary.py:80: sandbox-exec is macOS-only; the orchestrator runs only there
Skipped in the regression of record: [1] tests/test_phase257_sandbox_boundary.py:87: sandbox-exec is macOS-only; the orchestrator runs only there
Skipped in the regression of record: [1] tests/test_phase257_sandbox_boundary.py:93: sandbox-exec is macOS-only; the orchestrator runs only there
Skipped in the regression of record: [1] tests/test_phase257_manual_route_excerpts.py:147: needs the on-disk library
Skipped in the regression of record: [1] tests/test_phase257_manual_route_excerpts.py:352: needs the on-disk library
Skipped in the regression of record: [1] tests/test_phase257_manual_route_excerpts.py:358: needs the on-disk library
Skipped in the regression of record: [1] tests/test_phase257_manual_route_excerpts.py:364: needs the on-disk library
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:61: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [4] tests/test_phase388_fence_boundary.py:96: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [3] tests/test_phase388_fence_boundary.py:105: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:113: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:120: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:125: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:131: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:139: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:148: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:159: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:164: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:170: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:177: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:186: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:198: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [2] tests/test_phase388_fence_boundary.py:210: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:216: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [7] tests/test_phase388_fence_boundary.py:221: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:235: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:244: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [2] tests/test_phase388_fence_boundary.py:280: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:287: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:291: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:295: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:303: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [2] tests/test_phase388_fence_boundary.py:316: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:325: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:330: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:338: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:344: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:350: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:354: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:360: inside the fleet's fence: its boundary is proven from the host, not from inside

Line coverage of record: 88.04% at `2bb35de` (the pin is 87.50%): 0.54 points above it; raise COVERAGE_PERCENT to lock it in

## 2026-11-08 — the real Engineer session, replayed read-only

`runs/20261108_095532_engineer_371` (371's Chief Engineer, 09:55–11:52
EST): its `stage.json` and `run/session.json` (4,767 bytes) copied to a
throwaway state folder, `Fleet.ledger_read_in` run twice there with
`FLEET_LEDGER` a throwaway file. First pass 1 added, second 0 ("the ledger
read-in: 0 Engineer session(s) added, 1 already there"). The row: engineer,
`claude-opus-5-5` served, session `4179b86f-…`, input 234, cache write
207,619, cache read 17,685,247, output 79,410, $6.7871374, 135 turns,
7,013.4 s, phase 371, issue 54, source `read-in`. The fleet's two files
hashed the same before and after. Issue 54 and the run folder untouched.

## 2026-11-08 — close-out

- v1.1 (Deviations and Results), this log, row 399 ✅, the root
  `implementation.md` and `phase_log.md`, F254 and F255 closed in
  `docs/FOLLOWUPS.md`, the handoff `docs/handoffs/2026-11-08_399_closed.md`.
- No refute pass ran: the phase changes fleet code and tests, takes no
  claim from a source, and is held by its tests and mutations.
- `b3e57c9`, the close-out commit, after wholetree fast (2624 passed, 10
  skipped, exit 0); pushed, and PR #57 opened with the attribution block.
  `verify_phase.sh 399 2bb35de b3e57c9`: 13 of 14 pass; check 1 (the tip
  on master) waits for the merge.
