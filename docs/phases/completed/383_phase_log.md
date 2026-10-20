# Phase 383 — 382's follow-ups: the live gates, then media paths — phase log

**Status:** ✅ Complete (2026-10-19)
**Branch:** `phase-383` (Opus session on the Mac, the only writer; the deploy
runs on the desktop, from commands given here)

---

### 2026-10-19 — Opened, Step 0, and the stop

The prompt is `docs/prompts/383_follow_ups_from_382.txt` (merged
`e4a691f`). Row 383 went 🚧 before Step 0. Read first: F205, F206, F208 in
`docs/FOLLOWUPS.md`; 382's handoff and `382_*` in `completed/`; the deploy
skill, "Where live is (Phase 382)" first.

`383_step0.md` re-verifies every measured fact in the prompt (S0-1): all
hold. The prompt's figures were taken at `05f9e5c`; this branch starts at
`e4a691f`, which adds only the prompt.

Decided at Step 0, without a stop (reasons in `383_step0.md` S0-5): 087
rewrites by the routes' layout, not by a data folder; readers outside the
routes resolve with `get_settings().data_dir`; the route docstrings that
feed the OpenAPI descriptions are not edited, so the mobile snapshot stays
equal.

**A guard blocked a command:** a `sed -i` on `383_step0.md` (fixing the
prompt's file name) was refused by the edit guard. Made with the Edit tool
instead; the guard is unchanged.

The prompt asks for a stop at Step 0 with three questions: F206's rule,
F208's rule, F205's window. They are in `383_step0.md` S0-2 to S0-4, with
the options, what each ships, and the recommendation (1C, 2A with
apply-live following it and check 8 unchanged, 3A). Waiting for the
operator's picks.

### 2026-10-19 — The operator's picks, F210, v1.0

The operator, verbatim:

> 1C, 2A with apply-live following it, check 8 unchanged, 3A.
> - 1C: pin each expected skip by its test file and its reason, not the reason alone. EXPECTED_SKIPS is held by an equality test as A5_COMMAND_EXEMPT is, and adding to it is my call.
> - 2A: file a finding now that the column list cannot hold once a shop's traffic reaches live (a new work order between the dry run and the apply refuses the apply; any use after it fails check 8), to be settled before onboarding (330).

**F210 filed** (`docs/FOLLOWUPS.md`, through the finding skill:
`next_f_number.sh` gave F210; `finding_check.py` exit 0).

v1.0 written. Decided without a stop:
- The strict shape parses all 28 post-K6 closed logs (scratchpad
  `f206_strict.py`); it is the new `_REGRESSION`.
- pytest's `-rA` groups identical skips as `SKIPPED [N] file:line: reason`
  (measured on 244H's file under `-n 2`), so a skip line carries its count
  and A5 sums them.
- The line's writer moves into `closeout_check.py` beside its reader, so a
  test can feed one to the other; `regression.sh` calls it.

### 2026-10-19 — The build: F206, F208, F205

Committed in the prompt's order:
- **F206** `12008ba`: `regression_record` (A5 and K18), `format_regression`
  beside it, `regression.sh` printing through it, eight known-bad fixtures
  (382's failing desktop line verbatim among them) and one good.
  `test_phase358_closeout_k6_k7.py`'s exemption control now judges each
  log as its own phase (the skip exemption is per phase); without that,
  382 joined the command exemption's measured set.
- **F208** `d45f3e0`: `SERVER_WRITES`, `server_masked`, applied to the
  drift check, the after-apply comparison and verify-live, each printing
  what it set aside. Check 8 unchanged.
- **F205** `4fc1ca1`: `media/paths.py`; the three writers; the readers
  (the three file routes, the ask route, `analysis_worker`, `audio_sweep`,
  `transcript_pipeline`), the routes passing their `data_dir` to the
  background workers so a worker resolves under the folder the row was
  written under; migration 087; `SCHEMA_VERSION` 87.
  `wholetree.sh --full` before it: PASSED, 4207 passed (gate 11 among them:
  the OpenAPI snapshot is unchanged, as S0-1 required).

Decided without a stop:
- **The 191b worker fakes take the new argument.** `patch_worker`'s no-op
  had the old signature; the upload's background task then raised inside
  `TestClient(raise_server_exceptions=False)` and the tests passed while
  it threw. `test_upload_queues_background_analysis_task` now also checks
  that the worker receives the app's data folder. Not a bug fix: the
  signature change is this phase's own.
- **087's `WHERE` is not load-bearing.** With `instr` = 0 the `substr`
  returns the whole value, so dropping either condition rewrites nothing
  differently; it only limits which rows are written. No mutation targets
  it; M13–M15 break the rewrite itself.

**Mutations** (`383_mutate.py`, `383_mutate.out`): the first run left two
green, each a gap in the tests, not the code:
- R1 (the failures not read): every failing fixture also exited nonzero.
  Added `a5_bad_failed_exit_zero.md`.
- S7 (an added row dropped with the masked ones): the added-row control had
  no masked change in the same table, so it never reached that branch. It
  now carries a request beside the insert.
Also added before the run: the ask route's round trip (M5), the transcript
route's queued folder (M12), and `a5_bad_skip_other_file.md` (R5, the
operator's "by its test file and its reason"). Second run: **35/35 red**.

**The floor:** 10871 → 10923, by a diff of collected ids against master
`e4a691f` in a scratchpad worktree (10872 there): +51 −0, all in the three
new files.

### 2026-10-19 — 087's scope; the desktop's steps

**A guard blocked a command:** a `git commit … && git push` in one command
was refused by the push guard ("it would push a commit it never saw").
Run as two commands; the guard is unchanged.

`383_deploy_scope.json`: the six `videos` rows by id and their current
desktop path (382's after-values), `file_path` only, each with its `to`
value; `schema_version` +1. Photos and transcripts are not named: any row
there is a scope problem, and a stop.

Rehearsed with the script's own code (`deploy.dryrun`) on a synthetic
database at schema 86 holding those six paths, in a scratchpad repo:
`scope problems: none`, `Migrations applied on the copy: [87]`, 6 `videos`
rows, exit 0.

`383_desktop_steps.md` holds the commands for the desktop (D1 the dry run,
D2 the apply with the API stopped, D3 the server and verify_phase).

### 2026-10-19 — 087's dry run on the desktop; the regression of record; the approval

**The dry run** (D1, the operator on the desktop, at `5603ff3`), committed
there as `7f75896` and pulled here with `--ff-only`: live 5801 rows, 121
tables, integrity ok; backup
`/home/lilcu/backups/motodiag/motodiag_pre383_20261019_212534.db`, sha256
`a18a2f9378c934d8dd1ffc94fc7d9f1af3cb241720e9142eb77db487d3a8c577`;
scope sha256 `de7f0eb5…f5a5`, equal to the rehearsal's (the same scope
file); `[87]`; F158 census 41; scope problems none; exit 0. The diff:
`videos` 6 changed (`file_path` only, rows 1–6, each to its relative
path), `schema_version` +1 (version 87); no other table, no schema object.

**The regression of record**, on the Mac, after `wholetree.sh --full` at
`5603ff3` (PASSED, record written):

Regression of record: 10922 passed, 0 failed, 1 skipped, 0 errors at `5603ff3` (30 min 16 s wall, `python -m pytest -n auto --dist load`, exit 0)
Skipped in the regression of record: [1] tests/test_phase244H_test_db_isolation.py:79: no production database on this machine

10922 + 1 = 10923 collected, the floor. Log
`~/.cache/motodiag/regressions/5603ff3_parallel_20261019_210638.log`.

**The operator's approval**, verbatim:

> Approved: once the regression of record passes, apply 087 live with the API stopped from just before the apply until the merge and restart (3A), exactly as the committed dry-run diff (7f75896) shows: file_path on videos rows 1–6, each to its relative path, and 087's own schema_version row. If anything else differs, stop and show me.

### 2026-10-19 — 087 live (D2, the operator on the desktop)

At `2a98f5b`, with `motodiag-api.service` stopped just before the apply
(3A). The operator's report: `apply-live 383` exit 0, `verify-live 383`
exit 0, live at schema_version 87, 5802 rows, integrity ok; the
API left stopped until D3. The live diff, committed there as `8a85e8f` and
pulled here with `--ff-only`:
- scope problems `none`; **equals the approved exact diff: `yes`**;
- set aside, written by the running API: `0` (the API was stopped, so
  F208's list had nothing to set aside);
- F158 census on live 41, as in the dry run;
- `videos` 6 changed, `file_path` only, rows 1–6, each from
  `/home/lilcu/motodiag/live/videos/shop_1/session_N/I.mp4` to
  `videos/shop_1/session_N/I.mp4`; `schema_version` +1 (87); nothing else.

That is the approval's scope exactly; nothing else differs, so no stop.

### 2026-10-19 — Close-out

- **F206, F208, F205 closed** in `docs/FOLLOWUPS.md`, each naming its
  known-bad control. F210 stays open (before row 330).
- **No bug fixes** in this phase: nothing broke that the phase had built
  and committed; the two mutation survivors were test gaps, fixed before the
  run of record (above). No register, so A4 has nothing to read.
- No refute pass ran.
- `implementation.md` v1.1; the root `implementation.md` 0.13.110 →
  0.13.111 with 383's history row; row 383 ✅; the files to `completed/`;
  the handoff `docs/handoffs/2026-10-19_383_closed.md`.
- Still to come, from the desktop (D3): the server's pull and start after
  the merge, and `verify_phase.sh 383 5603ff3 <merge>`, which runs check 8
  where live is.
