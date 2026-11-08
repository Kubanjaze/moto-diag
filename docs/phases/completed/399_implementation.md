# Phase 399 — The fleet's cost ledger, made true (F254, F255)

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-11-08 (v1.0 `6818f99`)

---

## Goal

Fleet-only by K69's exception to K43, so it unblocks no shop phase: built
by a builder session while 371 runs, and the fleet does not wait for it.
The operator: "the cost ledger and Bosun’s watch-only phase may go ahead as
fleet-only phases, one at a time while a shop phase runs; anything after
comes back to me".

After this phase:
1. (a) **F254.** No test writes the fleet's real cost ledger
   (`~/.local/state/motodiag/fleet/calls.jsonl`). One autouse fixture gives
   every test a ledger file of its own, and a run of the suite that changes
   the real ledger fails. The rows already there stay as they are; readers
   skip the stand-in's rows (`sess-1`) by a named rule.
2. (b) **F255.** Each Chief Engineer session goes into the ledger once when
   it ends (usage, wall time, cost), and a resumed one is not counted
   twice. Every ledger line, for every rank, names its phase, issue and
   run. Kept run folders holding an Engineer `session.json` are read in
   once; a second pass adds nothing.
3. Nothing changes what a stage runs, and no existing ledger row is
   rewritten or deleted (the prompt's stops).

## The plan of record

Not in "Next, in order" (K69; the dated entry of 2026-11-07 in
`docs/reports/2026-10-12_plan_of_record.md`). The list does not change.

## Logic

Causes and measurements: `399_step0.md`, S0-1 to S0-4.

1. **(a), the fixture.** `tests/support/ledger_guard.py`, loaded by
   `tests/conftest.py`'s `pytest_plugins`: `_never_the_real_cost_ledger`,
   autouse, sets `FLEET_LEDGER` to `calls_<n>.jsonl` in one session-scoped
   temporary folder. A test that sets `FLEET_LEDGER` itself still wins; a
   subprocess inherits it.
2. **(a), the check.** In the same module, on the controller only (not an
   xdist worker): `pytest_sessionstart` reads the ledger the suite started
   with (`$FLEET_LEDGER`, else the default); `pytest_sessionfinish` fails
   the run (`session.exitstatus = TESTS_FAILED`) and names the rows when
   the bytes that were there changed, or a row was appended that the fleet
   did not write. The fleet runs beside the suite on the desktop and
   appends real calls meanwhile: a row is the fleet's when its session id
   is named in one of the fleet's run folders (a journal's `calls`, or an
   Engineer's `session.json`). No test can make such a row.
3. **(a), the readers.** `rank_call.STAND_IN_SESSION = "sess-1"`,
   `is_stand_in`, `rows(stand_ins=False)` and `summary()` (and
   `rank_call.py ledger`, which prints it). There was no reader before;
   this is the one way to read the ledger, for 400's Bosun too.
4. **(b), every line names its stage.** `Call` gains `phase`, `issue`,
   `run`, `source` ("call", "session", "read-in") and `key` (None for a
   rank's call). `rank_call.call` takes them from `run.ledger_context()`
   when the runner has one; `FencedRunner.ledger_context` gives the
   journal's phase and issue and the run folder's name. A call made by hand
   carries None.
5. **(b), the Engineer's session.** `FencedRunner.ledger_session`, called
   in `session` when the process has ended (by itself, by a watcher's
   reason, or at a usage limit, before `RateLimited` is raised) and when a
   resumed stage reads a finished session back. `rank_call.session_call`
   makes the row from `session.json`'s last line (a session that printed
   nothing is a row with no usage); `record_once` writes it unless a row
   with its key is there. The key is the run folder and the sha256 of the
   bytes the session printed: read back, it is the same; a part run again
   with `--resume` prints anew and is its own row. It never raises: a
   ledger that cannot be written logs a line and the stage goes on.
6. **(b), the read-in.** `Fleet.ledger_read_in`, first in `recover` (the
   search on start): every run folder whose `run/session.json` has ended
   (`session_ended`) becomes a `read-in` row with the journal's phase and
   issue, under the same key, unless it is there. One log line:
   `the ledger read-in: N Engineer session(s) added, M already there`. A
   dry run (`recover --dry-run`) says what it would add.
7. **Finish line:** the census before and after; the regression of record
   leaves the real ledger unchanged; the guard and each fix seen red.

## Rule-1 stops anticipated

None. The prompt's stops: no existing ledger row is rewritten or deleted
(the fixture and the check only read the real ledger; the read-in only
appends); no stage's command changes (the ledger write happens after the
session's process has ended, outside the fence).

## Tests

- `tests/test_phase399_cost_ledger.py`, new:
  - (a) each test's own ledger file; the check's rule on planted run
    folders (the fleet's rows taken, any other refused, existing bytes
    changed refused); nested pytest runs under a throwaway HOME: with the
    guard, a test that writes the ledger fails the run and the row lands
    only under that HOME; the control without the guard passes (F254 as it
    was); a row whose session a planted run folder names passes; readers
    skip `sess-1` and keep `sess-10` (the planted control).
  - (b) a real `claude -p --output-format json` result becomes an Engineer
    row; through 389's test world the Engineer's session lands once with
    phase 902, issue 31 and its run, and every rank's line names its
    stage; resumed, it adds nothing; cut between the end and the write, the
    resume writes it once; a cut session resumed with `--resume` is one
    row; a usage limit's part is one row however often it is read back; the
    read-in adds one, then nothing, and a dry run writes nothing; a session
    recorded live is not read in again; the search on start runs it.
- Old code: the new tests against master's `rank_call.py`, `dispatcher.py`
  and `conftest.py`, red.
- Mutations, `399_mutate.py`, each under a throwaway HOME: the fixture off;
  the check never fails; the check takes every appended row as the
  fleet's; readers keep `sess-1`; no `ledger_context`; the session not
  recorded; recorded with no key check (counted twice); the read-in
  skipped at start; the read-in not keyed.
- `COLLECTED_TEST_FLOOR` raised by a diff of collected ids.

## Non-goals

Which model or effort a rank uses (400); the fence and the providers;
F256 (filed here, left); every other finding.

## Planned items

- [x] (a) the fixture, the check, the readers
- [x] (b) phase, issue and run on every line; the Engineer's session once
- [x] (b) the read-in of kept folders
- [x] the census after; the tests red on the old code; the mutations
- [x] the regression of record, the close-out, the handoff

## Deviations

1. **The census ran in 12 chunks, each started only while no fleet sandbox
   ran** (F220), not as one run: the fleet was planning 371 throughout,
   with stages minutes apart. A sandbox still started beside 5 of the
   before-census's chunks and 1 of the after's (each run says which). Both
   ran in worktrees (master `1222862`; the fix `fdafadc`), so this checkout
   could be built meanwhile.
2. **The replay fixture is not an Engineer's session.json**: none survived
   anywhere on the machine (Step 0, S0-4), so the tests replay a real
   result of the same command (371's Science Officer). 371's own Chief
   Engineer session appeared later, in
   `runs/20261108_095532_engineer_371`, and was replayed read-only too
   (Results).
3. **Bug fix #1** (`2bb35de`): the fixture asked for `monkeypatch`, which
   broke the database tripwire's teardown order; the first regression, at
   `fdafadc`, had 819 setup errors and is not of record. The fixture sets
   and restores the variable itself. One test and one mutation (M12) more
   than v1.0 listed.
4. **One test beyond v1.0's list** besides bug fix #1's: a usage limit's
   part is one row however often it is read back. Writing it found F256.
5. **No push guard ran on this branch's pushes**: the builder session ran
   outside the repository root, so the repo's hook was not loaded.
   `wholetree.sh` fast was run by hand, alone, before each commit.

## Results

- **(a) Cause, re-measured:** nothing kept a test off the default ledger;
  5,616 of the desktop's 5,726 rows were `sess-1`. **The census before**
  (`1222862`): 6 files, 57 rows a run, all `sess-1`
  (`test_phase393_code_checks.py` 21, `test_phase392_answers.py` 16,
  `test_phase392_red_team_c7.py` 7, `test_phase396_slips.py` 7,
  `test_phase392_check_limit.py` 4, `test_phase392_next_mission.py` 2);
  F254 had measured four. **The census after** (`fdafadc`): 0 files, 0
  rows. The guard broken on purpose goes red (M1–M4, M12), each under a
  throwaway HOME.
- **(b) Cause, re-measured:** `Runner.session` wrote only the run folder.
  Now: the Engineer's session lands once with its phase, issue and run; a
  resumed stage reading it back adds nothing; a stage cut between the end
  and the write writes it once on resume; the read-in adds one, then
  nothing. **371's real session, replayed read-only** (copied to a
  throwaway state folder): one `read-in` row, Opus, input 234, cache write
  207,619, cache read 17,685,247, output 79,410, $6.79 at list price, 135
  turns, 7,013 s, phase 371, issue 54, run `20261108_095532_engineer_371`;
  the second pass added nothing; the run folder's files hashed the same
  before and after.
- `tests/test_phase399_cost_ledger.py`: 18 passed. On master's code: 12 of
  the first 17 failed; the 5 that passed test the guard module, which is
  new either way.
- `399_mutate.py`: **12/12 mutations red**, every one under a throwaway
  HOME, the real ledger unchanged by them.
- `COLLECTED_TEST_FLOOR` 12416 to 12434 (+18 −0 against `1222862`).
- F256 filed (a usage limit read back re-pauses a resumed Engineer), left.
- **Regression of record:** 12329 passed, 0 failed, 105 skipped, 0 errors at `2bb35de`, coverage 88.04%, inside the fence (wholetree --full first: 5093 passed, 36 skipped); the real ledger across it: 5,521,653 bytes and 5,731 rows before and after, sha256 9ed1861d… both times, 0 rows appended.
- `dispatcher.py` and `rank_call.py` changed: the fleet's copy moves to
  master and `motodiag-fleet.service` restarts after the merge (the
  handoff's block), and the search on start then reads 371's kept session
  in.

## Version history

| version | date | what |
|---|---|---|
| 1.0 | 2026-11-08 | the plan (`6818f99`) |
| 1.1 | 2026-11-08 | built (`fdafadc`, bug fix #1 `2bb35de`); Deviations and Results |
