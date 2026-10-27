# Phase 392 — phase log: the fleet follows the plan of record

**Status:** Complete
**Branch:** `phase-392-the-fleet-follows-the-plan`
**Prompt:** `docs/prompts/392_the_fleet_follows_the_plan.txt`

## 2026-10-27 — start

- Read the plan: rows 389A to 392, `ROADMAP_AUTHORITY.md` (392 is backend,
  205+), the newest handoff (`2026-10-26_391_closed.md`), `FOLLOWUPS.md`
  F223 to F228, the plan of record, `docs/decisions.md`, the `fleet`
  skill, `dispatcher.py`, `captain.py`, `red_team.py`, `xo.py`,
  `engineer.py`, `plan_check.py`, `fleet_git.py`, `refute_check.py`,
  `worker_loss.py`, `fence.sh`, the unit.
- `dispatcher.log`: no stage running (the last line, 10:09:32, #14's Red
  Team stopped on C7). #14 is parked; not touched.
- `wholetree.sh` exit 0 (2271 passed, 10 skipped, 72.7 s).
- **Guard block, kept as it is:** the push guard refused `git commit … &&
  git push` in one command ("it would push a commit it never saw"). Run
  as two commands.
- Row 392 🚧 on `master`, `f1763df`, pushed. GitHub printed "Cannot update
  this protected ref" and took the push all the same (the admin bypass):
  `git ls-remote origin refs/heads/master` is `f1763df`.

## 2026-10-27 — Step 0, and the operator's answers

`392_step0.md`. The operator answered the four Step 0 questions in one
message before they were put; recorded verbatim as K48–K51 with
`yeoman.py decide`. The reading of K50 (its head governs its parenthesis:
all five rule-1 kinds are never answered) and the decisions that are not
forks are in Step 0, S0-4 and S0-5.

F227's measurement started at Step 0 (`392_fd_probe.py`, a fenced full
run on `f1763df` with each process's open files sampled from outside), in
`~/motodiag/p392/fd_full`.
- **Guard block, the same as at the start, kept as it is:** the push guard
  refused the Step 0 commit and its push in one command, the same reason.
  My slip; run as two commands, and every commit since is pushed apart.

## 2026-10-27 — the record, read exactly (Logic 1, 2, 4)

- `plan_order.py`: the "Next, in order" list, the dated changes, the
  decisions with their Covers column, `bearing`, `brief_block`,
  `cite_line`, `answer`, `first_shop`, `check`.
- The plan of record gained the list at its top and the dated entry
  2026-10-27 (K48). The list transcribes the order already there: 392,
  303, 348, then Wave 1's own numbering; what each row needs is Wave 1's
  and "The operator's steps outside the code". Every `docs/decisions.md`
  row has `no stop`: no decision so far answers a stop the record may
  answer.
- `yeoman.py decide --covers`, refusing a rule-1 kind and a line that is
  not a lookup.
- `plan_check.py` P9 and P10. The pin measured, not guessed: without it
  384 and 386 at their v1.0 fail P9 only (P10 passes them: neither names
  the fleet's folder), 387 fails both. `BEFORE_THE_RECORD` holds exactly
  that, equality-tested. Four known-bad cases; the first draft of
  `P9_kid_names_another_phase` failed nothing (the list's own route, K90,
  still put 900 in order) and was replaced by a plan citing a K-id about
  something else, which fails P9 alone. The dispatcher tests' stand-in
  plan for their trial phase 902 now cites K92, a row of the good tree's
  `docs/decisions.md` naming 902: the first whole-tree run failed 46
  tests in 389's and 390's walk-throughs, every one the Captain's plan
  failing P9.
- **Guard blocks, three, all kept as they are:**
  - the edit guard refused a Python script writing
    `tests/test_phase387_yeoman.py` ("a Python script body writes
    tests/…"); done with the Edit tool;
  - the edit guard refused a Python script editing `plan_check.py` whose
    text names `src/` ("writes to a path the edit guard cannot resolve,
    and the body names src/ or tests/"); done with the Edit tool;
  - the edit guard refused a command with a stray `sed -i` I had left at
    its end; the two fixture files were written with the Write tool.

## 2026-10-27 — the ranks read and cite (Logic 3)

- The Science Officer's `assess` reads `plan_order.brief_block`; its
  report's "## The plan of record" is the script's (`scout.record_section`:
  the cite line beside the command that makes it, the record's words in a
  fenced block, so P3 reads none of its dates as counts).
- The Captain's v1.0 brief asks for "The plan of record" and, for a
  fleet-only phase, an "Unblocks:" line; P9 and P10 hold it through the
  existing one-more-call rule. Its recommendation reads the record.
- The XO's, the Red Team's and the Quartermaster's briefs carry the
  record; each brief says what in it is a finding (the Quartermaster's
  under Q1). Every comment those ranks and the Captain's recommendation
  post ends with `plan_order.cite_line`, written by script.
- `tests/test_phase392_ranks_cite.py`: each brief, each comment, and on
  389's walk-through the XO's, the Red Team's and the Captain's comments.

## 2026-10-27 — F223 (Logic 7)

- `fleet_git.trusted_authors`, `from_trusted`, `opened_by_trusted`;
  `Fleet.comments` (every due rule, round count, marker search and brief
  reads through it), `Fleet.issues_open` (the cycle and the search on
  start), `pr_has_comment`, `xo.prior_rounds` (and `xo.review` now takes
  the identity file, so no test reads `~/.config`).
- Measured before relying on it: #14 was opened by `Kubanjaze` and its
  body carries `<!-- fleet-trial -->`; its comments are 22 by `Kubanjaze`
  and 9 by `kubanjazefleet` (`gh issue view 14 --json comments`). So #14's
  history still counts after the merge.
- The stand-ins learned authors: `gh issue comment` posts as
  `Host.commenter` (the operator unless a test says), a planted comment
  with none is the operator's, as #14's fixture history was. Tests whose
  issues modelled the fleet working under the operator's login gained the
  trial marker, as #14 has; one that modelled a non-trial issue with no
  fleet account now says what F223 makes of it: the fleet's own verdict,
  in the operator's name, is not a marker, so nothing follows it.
- Known-bad, `tests/test_phase392_authors.py`: a third login's Red Team
  clear, back, Captain merge (Q2 and Q3 both fail, and the model's texts
  are "(none)"), XO verdict and XO rounds; its mission issue; and with the
  fleet's account, the operator's marker on a non-trial issue.

## 2026-10-27 — K52: two corrections to the list, before it merged

The operator, relaying the advisor (verbatim in `docs/decisions.md`, K52):
row 6 (371) needs Stripe's live account as well as the webhook fork; row 8
(330) needs F210's general rule first, which changes the set-aside list's
definition, the operator's call. Applied as the list's rule asks: a
sub-bullet under the 2026-10-27 dated entry, the "As of" line moved to
K52, the two rows' needs rewritten with the record's own words quoted.
A need for a rule's definition had no kind in the list, so `NEEDS` gained
"a rule change", asked with `needs-admiral` (rule 1's threshold-or-rule).
One row may carry one kind, so 371's is "a fork" with the account named in
the same cell; both are asked in one plain-English comment.

## 2026-10-27 — F225, F226 (Logic 8, 9)

- **F225.** `CHECK_TIMEOUT_S = 5400` (K51). `check_run` runs the fence
  through `run_group`: its own session, and past the limit the whole
  process group is killed (`subprocess.run` killed only the direct child)
  and a failed `Check` names the limit. Known-bad: a planted fence that
  outlives a 1 s limit and leaves a grandchild; through the Engineer's
  stage it stops once, said on the issue, its run held, not started again
  next cycle, no "cycle failed" (`tests/test_phase392_check_limit.py`).
- **F226.** `clean_tmp(run)` removes `run/tmp` but its
  `motodiag_worker_loss_*` folders: when a stage's journal ends (not a
  pause, not a held run), when a check run has written its result (or hit
  its limit), when a held run is released; `prune_runs` cleans every kept,
  ended, unheld run, and a check run with a `check.txt`. `KEEP_RUNS`
  unchanged. The reclaim line says "(nothing came back to Windows: the
  disk image is not sparse, so the trim freed space inside Ubuntu only)"
  when C: moved by less than 0.1 GB beside a trim that ran; two of 390's
  space tests pinned the old line and now pin the new one. Known-bad, each
  kept: a held run (and through prune), a paused one, an unfinished one, a
  run prune is told to keep, a check run a restart cut off; the
  worker-loss files survive every deletion (`tests/test_phase392_tmp.py`).

## 2026-10-27 — F227 (Logic 10)

- **The probe** (`392_fd_probe.py`), a fenced full run on `f1763df`, each
  process's `/proc/<pid>/fd` counted once a second from outside: 2102 s,
  449 processes. **Peak: 793 open files in one xdist worker** (gw15, in
  `tests/test_pricing.py::TestRepairPlanCRUD::test_get_plan`, 1491 s in),
  774 and 768 in two others within 20 s, 698 and 682 next. Against the
  service's soft limit of 1024. Its 14 failures were the probe's own
  set-up (the mobile repository not bound: gate 11's snapshot, the finding
  contract), not a lost worker; no "Too many open files". The probe now
  binds it, as the dispatcher does.
- **The leak, looked for.** A per-test trace (a plugin counting this
  process's open files after each test), the full suite with `-n auto` in
  this checkout, 9 min: no worker ends with more than 56 open, and no test
  file leaves more than 55 behind (`test_phase274_quotes_variance.py`,
  `test_phase373_warranty_invoice.py`). Sampled every 2 ms inside the three
  files the fence's peaks were in, run alone: at most 72. So outside the
  fence there is no build-up between tests. A second fenced run with both
  plugins inside is under way (`~/motodiag/p392/fd_fence2`).
- **The unit:** `LimitNOFILE=1048576` (K51), with the reason beside it;
  the service contract's new rule `nofile`, two known-bad cases (no limit,
  1024). Known-bad run: a planted two-worker run holding 300 files each
  under a soft limit of 256 runs out ("Too many open files"); the same
  under 1048576 passes (`tests/test_phase392_open_files.py`). Not a fence
  test: those skip on the Mac and inside the fence, and a new skip must be
  pinned; the limit reaching the fence is read live after the install,
  from the service's own `/proc/<pid>/limits`.

## 2026-10-27 — F228 (Logic 11)

- The brief states C7 in its own words: an open wording defect is written
  "open" with no F-number; the rank never files one or writes a number of
  its own; a script files the one finding and writes its number into each
  row.
- `red_team.check_table`: C7 set aside on a back before round 3, as C6 is;
  on a clear or a back in round 3, the table is checked as it will be
  written (`with_finding` with a stand-in number) and `wording_open` lists
  the rows. The dispatcher picks the number once (journaled), over the
  branch's, master's and the mobile repository's `FOLLOWUPS.md`, writes
  the entry (`red_team.wording_entry`) and the header's highest number,
  and commits it with the table (a clear) or alone (round 3's back) as
  `red-team-record`. G3 lets that rank add to `docs/FOLLOWUPS.md` and
  refuses any removed line but the header's count.
- Known-bad: #14's round-3 output, kept from its run's `stage.json` as
  `fixtures/red_team/14_round3.json`. As it came it fails C7 on its wording
  row, and with 392's change set aside the round stops as it did at 10:09;
  now it finishes with the one row to file; on the walk-through its round
  3 files the stand-in's next free number, writes it into the table on
  the PR and goes to the operator (`tests/test_phase392_red_team_c7.py`). Measured on the way:
  one of its four factual rows quotes `\|` and is not a row
  `refute_check` reads, so C6 counts three.

## 2026-10-27 — the next mission, and answered stops (Logic 5, 6)

- **The next mission** (`stage_next`, journaled, a kill point in
  `fixtures/resume/kill_points.json`): each cycle reads master's record
  from the mirror (`plan_order.check_texts`; a list that does not read
  exactly starts nothing, logged once). The first entry not ✅: a
  builder's is waited for (logged once); else its issue, opened in the
  fleet's name with `mission` and the work branch named; if the plan says
  it needs the operator, one plain-English question quoting the entry and
  `needs-hands` or `needs-admiral`, then nothing until the label is off;
  then branch `phase-<N>-row` from master, the row's status alone set to
  🚧 (`mark_row_active`), pushed through the gate as the new rank `row`
  (G3: the ROADMAP only, one line, its status only), and the pull request
  whose body tells the operator, plainly, that merging starts the phase,
  with a one-line paste block (`-R Kubanjaze/moto-diag`, ALL GOOD or
  SOMETHING IS OFF). Without the fleet's account it opens nothing. G1 is
  unchanged: it never pushes `master`.
- **Caught by its own test before any commit:** on the cycle after the
  operator took the label off, the stage opened a second issue (`step`
  asks GitHub first only when resuming). The issue is now found before it
  is opened. Not a bug fix in the register: the code had never been
  committed.
- **Answered stops** (`answer_stop`): an Engineer stop of kind
  `third-bug-fix` or `guard-blocked-twice` asks `plan_order.answer`; one
  covering K-id is said on the issue with the operator's words verbatim
  (`<!-- fleet-answered: kid=… stop=… -->`), and the Engineer runs again
  with them in its brief (`engineer.ANSWERED`: applied literally). The
  same K-id and stop a second time goes to the operator; so does a rule-1
  kind, which `answer` never matches. The due rule reads the answer when
  at least as new as the Engineer's last word (the stand-in clock does not
  move inside a cycle; on GitHub they are seconds apart).
- In the good fixture tree, 900 is now a builder's row in the list, so no
  walk-through starts a next mission it did not ask for.

## 2026-10-27 — the skill, the dry run, the mutations, the floor

- `dispatcher.py next --dry-run`: what the next cycle would do, read-only
  (no lock, no mirror update, printed, not logged). On today's master it
  prints that the list cannot be read exactly there (it is not merged
  yet). On a scratch mirror whose master is this branch with row 392 ✅
  (`~/motodiag/p392/next_dry`, GitHub read live): "next: would open the
  mission issue for phase 303 (the plan's #2), then open the row's pull
  request (`phase-303-row`)".
- SKILL.md: P9, P10 and their pin; `decide --covers`; "The plan of record
  — `plan_order.py`"; whose words count (F223); the check's limit and the
  open-file limit; the open wording defect; what replaced the shrink in
  "Free space"; the tests. CHANGELOG's entry. 391's contract test pinned
  its CHANGELOG entry as the newest; it now asks that the entry is there,
  as 391 did to 390's.
- FOLLOWUPS: F223, F225, F226, F228 closed with what closed them; F221's
  method says what replaced the shrink. F227 waits for the leak.
- `392_mutate.py`: 53 mutations. The first pass, 52/53: C4 (the Science
  Officer's section left out of the rendered report) survived, as the test
  read the section builder, not the report; a test on `scout.render` was
  added. The pass of record, `392_mutate.out`: 53/53 red.
- `COLLECTED_TEST_FLOOR` 11605 → 11737, by a diff of collected ids against
  master at `f1763df`: +132 −0, each file named in the floor's comment.

### Bug fix #1 — 2026-10-27 — `init_db` never closed its connection (F227's leak)

- **Issue.** The second fenced probe (`~/motodiag/p392/fd_fence2`, `f1763df`,
  a per-test trace and a 2 ms peak sampler inside each worker, the mobile
  repository bound): one xdist worker (gw16) **ended** the suite holding
  919 open files, 922 at its peak; another 802. Almost all SQLite handles:
  `.db` 3308, `.db-wal` 1844, `.db-shm` 376 over the workers' last
  readings. They built up in `test_phase373_warranty_invoice.py` (+872
  across workers), `test_phase376_settlement_export.py` (+855) and
  `test_phase375_deductibles.py` (+783), about 37 a test. Outside the
  fence the same tests left them too (`test_phase376_settlement_export.py`
  alone: 37 to 41 a test), and the garbage collector freed them later, so
  the first trace's workers ended at 56 or fewer.
- **Root cause.** `src/motodiag/core/database.py` line 202, `init_db`:
  `with sqlite3.connect(path) as conn:`. sqlite3's own `with` commits or
  rolls back and never closes. Every CLI command runs `init_db`, so every
  call left one connection, open until a garbage collection. A recorder of
  where each unclosed connection was made (`sqlite3.connect` wrapped, every
  connection still open at each test's end named by the frame that made
  it) named this line for every one, over the three files and the two the
  fence's first peaks were in: 260 and 16 (the settlement export file
  alone), then 605, 84, 24 and 6. `git grep -n 'with sqlite3.connect' --
  src`: this one line.
- **Fix.** `with closing(sqlite3.connect(path)) as conn, conn:` (commit or
  roll back, then close). A change under `src/`, which v1.0 did not plan:
  in Deviations.
- **Files.** `src/motodiag/core/database.py`;
  `tests/test_phase392_init_db_closes.py` (new: every connection `init_db`
  makes is closed when it returns, the garbage collector held off);
  `tests/test_phase255B_collected_test_floor.py` (+1, 11738).
- **Verified.** The test failed first on the unfixed code ("1 of 132
  connections left open"), then passed. The recorder over the three
  leaking files after the fix: no connection left open, 123 passed.

**Commit.** `98083c3`.

- **Guard block, kept as it is:** the edit guard refused `cp` of the
  test back from the scratch folder into `tests/` (it had been set aside
  so the previous commit carried no part of this fix); written with the
  Write tool.

## 2026-10-27 — the regression of record, and the disk (stage 1)

`392_disk_proof.py ~/motodiag/p392/state 98083c3 --full`: this branch's
`Fleet.check_run`, a fresh clone in the fence, no model, no token
(`~/motodiag/p392/state/runs/20261027_134217_check`). The first try exited
at once: the driver fetched a short commit id, which `git fetch` refuses,
and the check's own clone would not have carried the commit; it now
fetches the branches and pins the commit to a local branch.
`dispatcher.log` showed no fleet stage running (F220).

    wholetree full: PASSED — 4788 passed, 36 skipped, 32 warnings in 992.56s (0:16:32) (995.5 s wall)

Regression of record: 11633 passed, 0 failed, 105 skipped, 0 errors at `98083c3` (35 min 12 s wall, `python -m pytest -n auto --dist load`, exit 0) (run inside the fleet's fence)
Skipped in the regression of record: [1] tests/test_phase191b_ffmpeg.py:249: real ffmpeg binary or fixture mp4 not available
Skipped in the regression of record: [1] tests/test_phase191b_ffmpeg.py:264: real ffmpeg binary or fixture mp4 not available
Skipped in the regression of record: [1] tests/test_phase191b_ffmpeg.py:269: real ffmpeg binary or fixture mp4 not available
Skipped in the regression of record: [1] tests/test_phase191b_ffmpeg.py:277: real ffmpeg binary or fixture mp4 not available
Skipped in the regression of record: [1] tests/test_phase191b_ffmpeg.py:283: real ffmpeg binary or fixture mp4 not available
Skipped in the regression of record: [1] tests/test_phase244H_test_db_isolation.py:79: no production database on this machine
Skipped in the regression of record: [1] tests/test_phase257_orchestrator_guards.py:85: inside the fleet's fence: no Subconscious login there (K42)
Skipped in the regression of record: [2] tests/test_phase257_orchestrator_guards.py:149: inside the fleet's fence: osacompile is macOS-only
Skipped in the regression of record: [4] tests/test_phase257_sandbox_boundary.py:72: sandbox-exec is macOS-only; the orchestrator runs only there
Skipped in the regression of record: [7] tests/test_phase257_source_checks.py:211: needs the on-disk library
Skipped in the regression of record: [1] tests/test_phase257_source_checks.py:476: acquired/Yamaha/library_om_contents_pdf_10_5YR-F8199-15_02.pdf is not in this machine's library
Skipped in the regression of record: [1] tests/test_phase257_source_checks.py:476: acquired/KTM/24_3214961_en_OM.pdf is not in this machine's library
Skipped in the regression of record: [1] tests/test_phase257_source_checks.py:527: the KTM manual is not in this machine's library
Skipped in the regression of record: [1] tests/test_phase257_sandbox_boundary.py:80: sandbox-exec is macOS-only; the orchestrator runs only there
Skipped in the regression of record: [1] tests/test_phase257_sandbox_boundary.py:87: sandbox-exec is macOS-only; the orchestrator runs only there
Skipped in the regression of record: [1] tests/test_phase257_sandbox_boundary.py:93: sandbox-exec is macOS-only; the orchestrator runs only there
Skipped in the regression of record: [1] tests/test_phase257_sandbox_boundary.py:106: sandbox-exec is macOS-only; the orchestrator runs only there
Skipped in the regression of record: [1] tests/test_phase257_sandbox_boundary.py:112: sandbox-exec is macOS-only; the orchestrator runs only there
Skipped in the regression of record: [1] tests/test_phase257_sandbox_boundary.py:119: sandbox-exec is macOS-only; the orchestrator runs only there
Skipped in the regression of record: [1] tests/test_phase257_sandbox_boundary.py:125: sandbox-exec is macOS-only; the orchestrator runs only there
Skipped in the regression of record: [1] tests/test_phase257_sandbox_boundary.py:131: sandbox-exec is macOS-only; the orchestrator runs only there
Skipped in the regression of record: [1] tests/test_phase204_gate10.py:47: inside the fleet's fence: no ffmpeg on the home desktop
Skipped in the regression of record: [1] tests/test_phase257_manual_route_excerpts.py:147: needs the on-disk library
Skipped in the regression of record: [1] tests/test_phase257_manual_route_excerpts.py:352: needs the on-disk library
Skipped in the regression of record: [1] tests/test_phase257_manual_route_excerpts.py:358: needs the on-disk library
Skipped in the regression of record: [1] tests/test_phase257_manual_route_excerpts.py:364: needs the on-disk library
Skipped in the regression of record: [1] tests/test_phase257_manual_route_excerpts.py:367: needs the on-disk library
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

11633 + 105 = 11738, the floor. The 105 skips are those pinned since 389
("Sandbox counts").

**The disk, stage 1** (`/mnt/c` free, `C:\WSL\Ubuntu-26.04\ext4.vhdx`'s
size, `/` free):

| | at | C: free | image | Ubuntu free |
|---|---|---|---|---|
| Step 0 | 2026-10-27 ~11:00 | 396.35 GB | 119.00 GB | — |
| before | 13:42:17 | 331.11 GB | 184.09 GB | 955.99 GB |
| after | 14:34:25 | 295.60 GB | 219.26 GB | 955.88 GB |

After the stage its `run/tmp` held only the eight
`motodiag_worker_loss_*` folders. Inside Ubuntu the stage cost 0.11 GB;
the image grew 35.17 GB and C: lost 35.51 GB. Between Step 0 and stage 1
the image grew 65 GB: this phase's own probes and test runs, whose
folders `clean_tmp` does not touch (they are not the fleet's stages).
So deleting a stage's files frees space inside Ubuntu, and Ubuntu then
writes the next stage to blocks the image has never held, growing it,
rather than to the ones it freed. Stage 2 decides it, by the operator's
rule: if the image still grows with each stage once the files are
deleted, that is a stop for the operator, with the numbers.

## 2026-10-27 — the disk, stage 2

Before it, this phase's own probe folders' temporary files were deleted
(`fd_full/run/tmp` and `fd_fence2/run/tmp`, 9.5 GB each by `du -sh`),
the deletion the fleet now makes for its own stages. The same command
again (`runs/20261027_143513_check`):

Regression run (a second, not of record): 11633 passed, 0 failed, 105 skipped, 0 errors at `98083c3`, 34 min 39 s.

| | at | C: free | image | Ubuntu free |
|---|---|---|---|---|
| before | 14:35:13 | 295.59 GB | 219.26 GB | 976.16 GB |
| after | 15:27:04 | 295.61 GB | 219.26 GB | 976.05 GB |

`ls -l` of the image afterwards: 219257241600 bytes, unchanged. The run's
`run/tmp` held only its eight worker-loss folders.

**Read together:** stage 1 grew the image 35.17 GB, when the space Ubuntu
had freed was not yet where it wrote; stage 2, after stage 1's files and
the probes' were deleted, wrote into freed space and the image did not
grow. So the image grows to the fleet's peak and stays there; it does not
grow with each stage once the files are deleted. The operator's stop ("if
the image still grows with each stage once the files are deleted") is not
met. Nothing comes back to Windows either: the 35 GB stage 1 took stays
the image's until a compaction, which K45 chose against.

## 2026-10-27 — close-out

No refute pass ran.

This phase builds the fleet's code, and no rank may push to
`.claude/skills/fleet/` (G3), so no Red Team round ran on it; its claims
are held by its tests, the 53 mutations, and the two full fenced runs.
v1.1, the row ✅ (89 words by `roadmap_words.py 392 --check`),
`implementation.md` 0.13.119 and its history row, the root `phase_log.md`
pointer, the files moved to `completed/`, and the handoff
`docs/handoffs/2026-10-27_392_closed.md`.

