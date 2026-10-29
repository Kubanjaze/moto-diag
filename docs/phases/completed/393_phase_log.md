# Phase 393 — phase log: the code itself gets checked

**Status:** Complete

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
- **v1.0** committed at `a9f1212` and pushed, with F234 and F235.

## 2026-10-29 — the build

- **A second fenced coverage run** on `a38a36b` (`393_fenced_measure.py …
  cov covB`), run beside the build: "11785 passed, 105 skipped", 39 min
  13 s (under the build's load), 87.597%, the same as run A to the last
  digit. The count is stable; no stop.
- **The tools pinned** in the `dev` extra (`a0bcabc`), with `[tool.mypy]`
  (no site-packages), McCabe 20 and coverage's source. The fleet's venv got
  ruff 0.16.9 and mypy 2.3.1 at Step 0 (`uv pip install --python
  ~/.local/state/motodiag/fleet/venv/bin/python …`): a venv outside the
  repository, as 389 built it, not live.
- **The safe fixes** (`a0bcabc`): `ruff check src --fix` with the
  migrations excluded, 297 fixed in 182 files. Two tests moved:
  - `test_phase209B_integration_gaps.py::test_no_new_orphan` went red on
    nine shop functions whose only reference was an unused import in
    `cli/shop.py` (`cancel_slot`, `complete_slot`, `start_slot`,
    `current_assignment`, `list_shop_mechanics`, `mechanic_workload`,
    `ShopTriageError`, `clear_urgent`, `trigger_rules_for_event`). Listed in
    the allowlist as unwired-feature with the reason; ORPHAN_COUNT 115 →
    124, in its history, the K2 way.
  - `test_phase256_chokepoint.py` pins three source lines; each moved up one.
  The full suite outside the fence on that tree: "4 failed, 11862 passed,
  33 skipped", the four F216's.
- **Bug fix #1** (`b0327b2`) and **bug fix #2** (`f2149cb`), below. Their
  tests: 8 of 12 red with `renderers.py` and `erase.py` at `a0bcabc`
  (stashed), all 12 green after.
- **The rest** (`68aa0e2`): the pins, the ratchet, the coverage gate,
  Q10–Q12, the five questions, the weekly page, the workflow, the
  documents. 29 existing Red Team stand-in replies failed on the required
  checklist and were given it (Deviations 12). `393_mutate.py`: 31/31 red.
  `COLLECTED_TEST_FLOOR` 11890 → 11987 by a diff of collected ids (+115
  −18; the 18 renumbered gap-test ids).
- **Guard blocks**, each recorded and none loosened:
  - the edit guard refused `cp` of the drafted test files into `tests/`;
    they were written with the Write tool;
  - the edit guard refused a stray `sed -i` (aimed at `/dev/null`, a slip);
    the import was added with the Edit tool.
- **The coverage pin** (`251a94b`): 87.6 sat above the fenced 87.597% and
  would have refused the regression of record; set to 87.5 before it
  (Deviations 6).
- **The pull request**: #35. **The Actions workflow's first run**:
  https://github.com/Kubanjaze/moto-diag/actions/runs/40962596948,
  success. "25 passed in 18.57s" for the ratchet on GitHub's runner, the
  same counts as here; `roadmap_check`: ok, the mobile half not run
  there.

### Bug fix #1 — 2026-10-29 — the PDF renderer ran `html.escape`

- **Issue.** `PdfReportRenderer.render` escaped every string with
  `html.escape`, not the reportlab markup escape written for it.
- **Root cause.** `src/motodiag/reporting/renderers.py` defined `_escape`
  (line 471 on master) for reportlab's markup, and line 517,
  `from html import escape as _escape  # noqa: E402`, rebound the name for
  the HTML renderer. The PDF renderer looks the name up when it runs, so it
  got the second binding. reportlab renders `&quot;` and `&#x27;`, so no
  PDF read wrong (Step 0, S0-7).
- **Fix.** The markup escape is `_markup_escape`; the HTML renderer imports
  `from html import escape as _html_escape` at the top. One name, one
  function.
- **Files.** `src/motodiag/reporting/renderers.py`;
  `tests/test_phase393_bug_fixes.py` (`TestThePdfEscape`).
- **Verified.** pypdf reads `She said "hi" & it's <ok> > fine` back five
  times from a PDF's title, subtitle, heading, body and bullet, with no
  entity; the spy sees `_markup_escape` called with the title; three of
  the five tests fail on the old file (the spy, the escape's output, the
  name). mypy 204 → 202.

**Commit.** `b0327b2`.

### Bug fix #2 — 2026-10-29 — the customer-data erase swallowed every error

- **Issue.** An error at the guidance table during a customer's erase was
  swallowed: `erase_customer` returned the memory facts it deleted as
  success, and the customer's guidance questions stayed.
- **Root cause.** `src/motodiag/memory/erase.py` lines 84, 105 and 146 on
  master: `except Exception: pass`, written for "table absent at this
  install's schema version", catching every error, a locked table included.
- **Fix.** Each catches `sqlite3.OperationalError` and calls
  `_table_absent(e)`, which re-raises unless the message says "no such
  table". The error reaches `get_connection`, which rolls back.
- **Files.** `src/motodiag/memory/erase.py`;
  `tests/test_phase393_bug_fixes.py` (`TestTheEraseRefusesOnAnErrorItWasNotWrittenFor`,
  `TestTheControlTablesAbsentStillErase`).
- **Verified.** SQLite's "database table is locked" error planted at each
  of the three statements: the erase raises and the memory fact and the
  guidance question are both still there (3 tests), and the dry run raises
  too (2); all five red on the old file. The control, both tables dropped:
  the plan counts 1 and the erase deletes 1.

**Commit.** `f2149cb`.

## 2026-10-29 — the first regression run, refused by the whole tree

`393_regression.py ~/motodiag/p393/state 251a94b` (no fleet run in
progress: `pgrep -x bwrap` exit 1, `dispatcher.log` idle since 15:34):
`wholetree full: FAILED — 1 failed, 4910 passed, 36 skipped` (17 min 13 s),
so `regression.sh` did not start. The one failure is bug fix #3. Not of
record.

### Bug fix #3 — 2026-10-29 — the weekly page's digest test ran the real `gh`

Bug fixes #1 and #2 are the two product bugs the prompt named; this is the
build's first defect, in this phase's own new test, so the third-fix rule's
shared-cause stop does not apply.
- **Issue.** `tests/test_phase393_quality_report.py::TestTheStage::test_the_digest_gets_one_line`
  failed in the fence with `FileNotFoundError: [Errno 2] No such file or
  directory: 'gh'`. Outside the fence it passed, by calling GitHub.
- **Root cause.** The test handed `yeoman.facts` the real `subprocess.run`;
  `facts` lists the escalation issues with `gh issue list`. A test reached
  the network, and the fence, which has no `gh`, exposed it.
- **Fix.** The test hands `facts` a stand-in runner that answers `[]`.
- **Files.** `tests/test_phase393_quality_report.py`.
- **Verified.** With `gh` taken off PATH, the file's 14 tests pass; the
  failing run's log is
  `~/motodiag/p393/state/runs/20261029_180452_check/clone/.git/motodiag_wholetree/last_full.log`.

**Commit.** `0029289`.

## 2026-10-29 — the regression of record

`393_regression.py ~/motodiag/p393/state 0029289`: this branch's `Fleet.check_run`, a fresh clone of `0029289` in the fence, no model, no token (`~/motodiag/p393/state/runs/20261029_182440_check`), the mobile repository at its published `origin/main`. `pgrep -x bwrap` before it: exit 1; `dispatcher.log` idle since 15:34 (F220).

    wholetree full: PASSED — 4911 passed, 36 skipped, 32 warnings in 977.98s (0:16:17) (980.5 s wall)

Regression of record: 11882 passed, 0 failed, 105 skipped, 0 errors at `0029289` (34 min 26 s wall, `python -m pytest -n auto --dist load --cov=motodiag`, exit 0) (run inside the fleet's fence)
Skipped in the regression of record: [1] tests/test_phase191b_ffmpeg.py:249: real ffmpeg binary or fixture mp4 not available
Skipped in the regression of record: [1] tests/test_phase191b_ffmpeg.py:264: real ffmpeg binary or fixture mp4 not available
Skipped in the regression of record: [1] tests/test_phase191b_ffmpeg.py:269: real ffmpeg binary or fixture mp4 not available
Skipped in the regression of record: [1] tests/test_phase191b_ffmpeg.py:277: real ffmpeg binary or fixture mp4 not available
Skipped in the regression of record: [1] tests/test_phase191b_ffmpeg.py:283: real ffmpeg binary or fixture mp4 not available
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
Skipped in the regression of record: [1] tests/test_phase204_gate10.py:47: inside the fleet's fence: no ffmpeg on the home desktop
Skipped in the regression of record: [1] tests/test_phase244H_test_db_isolation.py:79: no production database on this machine
Skipped in the regression of record: [1] tests/test_phase257_manual_route_excerpts.py:147: needs the on-disk library
Skipped in the regression of record: [1] tests/test_phase257_manual_route_excerpts.py:352: needs the on-disk library
Skipped in the regression of record: [1] tests/test_phase257_manual_route_excerpts.py:358: needs the on-disk library
Skipped in the regression of record: [1] tests/test_phase257_manual_route_excerpts.py:364: needs the on-disk library
Skipped in the regression of record: [1] tests/test_phase257_manual_route_excerpts.py:367: needs the on-disk library
Skipped in the regression of record: [1] tests/test_phase257_orchestrator_guards.py:85: inside the fleet's fence: no Subconscious login there (K42)
Skipped in the regression of record: [2] tests/test_phase257_orchestrator_guards.py:149: inside the fleet's fence: osacompile is macOS-only
Skipped in the regression of record: [4] tests/test_phase257_sandbox_boundary.py:72: sandbox-exec is macOS-only; the orchestrator runs only there
Skipped in the regression of record: [1] tests/test_phase257_sandbox_boundary.py:80: sandbox-exec is macOS-only; the orchestrator runs only there
Skipped in the regression of record: [1] tests/test_phase257_sandbox_boundary.py:87: sandbox-exec is macOS-only; the orchestrator runs only there
Skipped in the regression of record: [1] tests/test_phase257_sandbox_boundary.py:93: sandbox-exec is macOS-only; the orchestrator runs only there
Skipped in the regression of record: [1] tests/test_phase257_sandbox_boundary.py:106: sandbox-exec is macOS-only; the orchestrator runs only there
Skipped in the regression of record: [1] tests/test_phase257_sandbox_boundary.py:112: sandbox-exec is macOS-only; the orchestrator runs only there
Skipped in the regression of record: [1] tests/test_phase257_sandbox_boundary.py:119: sandbox-exec is macOS-only; the orchestrator runs only there
Skipped in the regression of record: [1] tests/test_phase257_sandbox_boundary.py:125: sandbox-exec is macOS-only; the orchestrator runs only there
Skipped in the regression of record: [1] tests/test_phase257_sandbox_boundary.py:131: sandbox-exec is macOS-only; the orchestrator runs only there
Skipped in the regression of record: [7] tests/test_phase257_source_checks.py:211: needs the on-disk library
Skipped in the regression of record: [1] tests/test_phase257_source_checks.py:476: acquired/Yamaha/library_om_contents_pdf_10_5YR-F8199-15_02.pdf is not in this machine's library
Skipped in the regression of record: [1] tests/test_phase257_source_checks.py:476: acquired/KTM/24_3214961_en_OM.pdf is not in this machine's library
Skipped in the regression of record: [1] tests/test_phase257_source_checks.py:527: the KTM manual is not in this machine's library
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

Line coverage of record: 87.62% at `0029289` (the pin is 87.50%)

With coverage: 34 min 26 s for the suite. Coverage 87.62%, 0.12 points over the pin; the gate's reminder to raise it starts at 0.5.

## 2026-10-29 — close-out

- **The reclaim** (`dispatcher.py reclaim`): C: 282.4 -> 282.4 GB free
  (nothing came back to Windows: the disk image is not sparse, so the trim
  freed space inside Ubuntu only); Ubuntu 1007.7 -> 1007.7 GB free; fstrim:
  /: 43 GiB (46127366144 bytes) trimmed.
- **No live change**: no migration, nothing reads live.
- **Three bug fixes** (#1, #2 the prompt's; #3 the build's own test).

No refute pass ran.
- v1.1, the ROADMAP row (✅, 76 words by `roadmap_words.py`), the history
  row in `implementation.md`, the files moved to `completed/`, the handoff.
