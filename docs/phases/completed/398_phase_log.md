# Phase 398 — phase log: the two stalls at the Red Team's clear (F251, F252)

**Status:** Complete

**Started 2026-11-08** (UTC; 2026-11-07 evening EST) on the home desktop
(WSL2), the only writer, on `phase-398-the-two-stalls`. The prompt is
`docs/prompts/398_the_two_stalls.txt` (the operator's words, verbatim);
the operator's word is K67.

## 2026-11-08 01:14 UTC — start

- Master fetched at 01:14 at `f6aead1` (the prompt, row 398 🔲, K67 and
  row 12 of "Next, in order" already on it). `pgrep -x bwrap` empty: no
  fleet stage running.
- Read before planning: `CLAUDE.md`, `docs/decisions.md` (K65–K67),
  F251 and F252 in `docs/FOLLOWUPS.md`, the plan of record's "Changes to
  the order", and the code each finding names.
- F253 was the next free number (`next_f_number.sh`; no `### F25[3-9]`
  or `### F26` on any local or remote branch).
- Issue #54 and its hold untouched.
- Row 398 🚧 on the branch before Step 0.

## 2026-11-08 01:20 UTC — Step 0

`398_step0.md`. (a) A5 fails both refused logs and passes both hand
fixes; reading only lines that begin with the prefix reads the real
record in both refused logs (12186 at `c2b0767`; 12292 at `ca580f6`) and
changes what A5 reads in no closed log (the three bullets that do not
begin their line, 258–260, are on `A5_COMMAND_EXEMPT`). No reason not to
build F251's first fix. (b) The stop path, the due rule and the round
count are as F252 says; the real stop comments on #45 and #50 and the
label events (2 h 8 min, 9 h 13 min) re-measured. Auditing the other
readers of the prefix found Q4's counts read the old way: filed as
**F253**, left.

**Decision (recorded, not a stop):** the hold catches any `Stop` from the
record push, not only the gate's G6, since a failed push or a fast run
held for space leaves the same nothing-due state; the operator's step is
the same (fix, then take `needs-hands` off).

- `f8c7e62`: Step 0, v1.0, row 398 🚧, F253. wholetree fast passed first
  (2588 passed, 10 skipped, exit 0). Pushed on its own.

## 2026-11-08 01:25 UTC — the build

- **(a)** `closeout_check.regression_record`: `ln.startswith(PREFIX)`, the
  docstring saying why (F251).
- **(b)** `dispatcher.py`: in `stage_red_team`'s clear path, a `Stop` from
  `push_once` holds the run (`journal.hold`, `why: record`, the table, the
  round, the branch, the wording finding's number and rows) and
  `hold_record` escalates with `needs-hands` (the comment names the gate's
  reasons and what to do); `review:open` stays. A clear that pushes
  releases older record holds. `held_record` and `stage_red_record` as
  v1.0 says; when the kept table is already on the branch (the operator
  pushed it, as on #45 and #50), nothing is committed and `review:clear`
  is set. `held_for` skips record holds. `STAGE_RANK`, `resume`, and the
  kill point in `fixtures/resume/kill_points.json` (390's contract test
  gained 398's module).
- **Design choices (recorded):** the hold is said through `escalate`, so a
  stage cut off between the comment and the label is resumed like the
  Engineer's escalation (`not_resumable` reads the `escalate` step), and a
  resumed `stage_red_team` or `stage_red_record` whose label step is done
  returns at once. Its due rule reads list order, not times, because the
  verdict marker and the hold can share a second.
- **Fixtures:** `.claude/skills/closeout/fixtures/f251/`, the two refused
  logs byte for byte (sha256 `87d97cb5…` for 345's at `9555925`,
  `997b7233…` for 343's at `41370d2`), and `a5_bad_table_row_only.md`;
  `.claude/skills/fleet/fixtures/f252/stops.json`, the stop comments on #45
  and #50 as `gh issue view` returned them.
- `tests/test_phase398_two_stalls.py`: 17 passed (7.8 s).
- **Red on the old code** (master's `closeout_check.py` and `dispatcher.py`
  copied in, then restored): 14 failed, 3 passed. The 3 that pass are the
  known-bad controls, which must fail A5 under either rule (a refused log
  with its record lines removed, twice, and the exemption pins). The 4
  fixture replays of (a) and the 10 of (b) are red.
- `398_mutate.py`, 01:32–01:33: **8/8 mutations red**; output kept as
  `398_mutate.out`.
- `COLLECTED_TEST_FLOOR` 12397 to 12416, by a diff of collected ids against
  master at `f6aead1` (12398): +18 −0.
- wholetree fast at 01:36 (89 files): 2606 passed, 10 skipped, exit 0.
  `pgrep -x bwrap` empty before it.

## 2026-11-08 01:39 UTC — the regression of record

- `e816e02` pushed at 01:38. The time: no regression near 00:00 UTC
  (F246); this one ran 01:39–02:34 UTC.
- **The run of record**, as 393's to 397's were: `Fleet.check_run` on
  `e816e02` in a fresh clone in the fleet's fence, no model and no token,
  the fleet's venv, the mobile repository a clean clone at its published
  `main` (`04be61c`), by `398_regression.py` (397's driver, renamed), its
  state folder under `~/.cache/motodiag/398_regression/`.
  `wholetree.sh --full` inside it: 5075 passed, 36 skipped, exit 0.
  **What else ran:** no fleet stage (`dispatcher.log` wrote no line
  between 20:39 and 21:34 local, and the fleet's newest run stayed the
  morning's digest); the always-on `motodiag-api.service` and the idle
  dispatcher. `pgrep -x bwrap` empty before it. Its lines, as printed:

Regression of record: 12311 passed, 0 failed, 105 skipped, 0 errors at `e816e02` (37 min 18 s wall, `python -m pytest -n auto --dist load --cov=motodiag`, exit 0) (run inside the fleet's fence)
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
Skipped in the regression of record: [1] tests/test_phase257_source_checks.py:476: acquired/Yamaha/library_om_contents_pdf_10_5YR-F8199-15_02.pdf is not in this machine's library
Skipped in the regression of record: [1] tests/test_phase257_source_checks.py:476: acquired/KTM/24_3214961_en_OM.pdf is not in this machine's library
Skipped in the regression of record: [1] tests/test_phase257_source_checks.py:527: the KTM manual is not in this machine's library
Skipped in the regression of record: [7] tests/test_phase257_source_checks.py:211: needs the on-disk library
Skipped in the regression of record: [1] tests/test_phase257_manual_route_excerpts.py:147: needs the on-disk library
Skipped in the regression of record: [1] tests/test_phase257_manual_route_excerpts.py:352: needs the on-disk library
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

Line coverage of record: 88.04% at `e816e02` (the pin is 87.50%): 0.54 points above it; raise COVERAGE_PERCENT to lock it in

## 2026-11-08 02:40 UTC — close-out

- v1.1 (Deviations and Results), this log, row 398 ✅, the root
  `implementation.md` and `phase_log.md`, F251 and F252 closed in
  `docs/FOLLOWUPS.md`, the handoff `docs/handoffs/2026-11-08_398_closed.md`.
- No bug fixes in this phase.
- No refute pass ran: the phase changes fleet and close-out code and
  tests, takes no claim from a source, and is held by its tests and
  mutations.
