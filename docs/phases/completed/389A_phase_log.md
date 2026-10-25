# Phase 389A — 385's ROADMAP row — phase log

**Status:** ✅ Complete (2026-10-25)
**Branch:** `phase-389A-385s-roadmap-row` (the Chief Engineer, Opus, in the fleet's fence: a fresh clone, no push)

---

### 2026-10-25 — Before the build: what was on the branch

The plan, `389A_implementation.md` v1.0, was committed before this session
by the Captain: `4eee8ab` (the plan), `a28256b` (round 1 revision),
`f13d170` (round 2 revision), approved by the Executive Officer on issue #14.
Step 0 is `ffe1691`. `93e1df0` merged `master` into the branch (389's fence
pins and guard fix), so this round starts from 389's close.

Read first: `docs/handoffs/2026-10-25_389_closed.md` (the newest, by
`git log -1 --name-only --format= -- docs/handoffs/`); rows 384–389A;
`ROADMAP_AUTHORITY.md` (385 and 389A are this repository's); F212, F216;
the 385 prompt.

What changed since the plan was written: 389 closed with the operator's
"Sandbox counts (Recommended)": a regression run inside the fleet's fence is
of record. The plan's section 4 and its anticipated stop assumed F216 made
that impossible here. The plan's own Tests section covers the case ("If it
unexpectedly passes with every skip pinned, that is a regression of record
and the merge recommendation says so as a change from this plan"), so if
the run here is of record, the close-out is done on the branch and the
change is a Deviation, not a fork.

The stage clone now has a local `master` (389's bug fix #3). The diff is
still taken against `origin/master`, as the plan says.

### 2026-10-25 — Row 385 added; row 389A's last sentence moved

- `grep -c '^| 385 |' docs/ROADMAP.md`: 0 before, 1 after.
- `roadmap_words.py 385 --check`: prints `87`, exit 0.
- `roadmap_words.py 389A --check`: prints `60`, exit 0.
- The 121-word control, run from `/fleet/run` on a string of 121 words, not
  on the repository: `roadmap_words.count(...)` returned `121`.
- `roadmap_check.py`: "ok: the ROADMAP, docs/phases/ and
  ROADMAP_AUTHORITY.md agree, and every close has its handoff", exit 0.
  R5 read the mobile copy inside the fence (no complaint).
- `roadmap_check.py --self-test`: R1–R7 each fire on the known-bad tree,
  the good tree passes; exit 0.
- `.venv/bin/python -m pytest tests/test_roadmap_continuity.py`: 28 passed,
  exit 0. (`python3 -m pytest` has no pytest on the host interpreter; the
  clone's `.venv` is the canonical one.)
- `git rev-parse origin/master`: `7ca42e0e515b7ac30e2c862e3db589b3fd6417f1`,
  389's merge. It descends from `6adffc5` (`git merge-base --is-ancestor`)
  and carries row 389A unchanged (the only ROADMAP change between them is
  row 389's close), so the expected shape holds.
- `git diff --stat origin/master -- docs/ROADMAP.md`:
  `1 file changed, 2 insertions(+), 1 deletion(-)`.
- The three row lines of `git diff origin/master -- docs/ROADMAP.md`,
  cut to 80 characters:
  ```
  +| 385 | The push token's own write | 🔲 | `device_tokens.last_seen_at` joins 
  -| 389A | 385's ROADMAP row | 🚧 | The fleet's first trial mission, a follow-o
  +| 389A | 385's ROADMAP row | 🚧 | The fleet's first trial mission, a follow-o
  ```
  Row 389A's "Step 0 next." became "Plan committed; row 385 added;
  awaiting the operator's merge."
- `wholetree.sh` (fast) before the row commit, run on its own: exit 0,
  "2085 passed, 10 skipped" (115.1 s wall).

### 2026-10-25 — The regression of record, inside the fence

`git rev-parse HEAD` before it: `e69c6f6` (the row commit); the tree clean.

- `wholetree.sh --full`, run on its own: exit 0. "wholetree full: PASSED —
  4530 passed, 36 skipped, 32 warnings in 863.47s (0:14:23) (864.9 s
  wall)"; record `045d84a7ecf0ad7fddc57dc46c23e2c193f096cd_full.json` for
  commit `e69c6f656a3b`.
- `regression.sh`, run on its own: exit 0. **Of record**, under the
  operator's "Sandbox counts (Recommended)" (389): the line carries the
  fence's mark and its skips are those `EXPECTED_SKIPS` and
  `FENCE_EXPECTED_SKIPS` pin. The plan expected a run that was not of
  record (F216); its Tests section names this case as a change from the
  plan, recorded under Deviations. The lines as printed:

Regression of record: 11297 passed, 0 failed, 105 skipped, 0 errors at `e69c6f6` (30 min 18 s wall, `python -m pytest -n auto --dist load`, exit 0) (run inside the fleet's fence)
Skipped in the regression of record: [1] tests/test_phase191b_ffmpeg.py:249: real ffmpeg binary or fixture mp4 not available
Skipped in the regression of record: [1] tests/test_phase191b_ffmpeg.py:264: real ffmpeg binary or fixture mp4 not available
Skipped in the regression of record: [1] tests/test_phase191b_ffmpeg.py:269: real ffmpeg binary or fixture mp4 not available
Skipped in the regression of record: [1] tests/test_phase191b_ffmpeg.py:277: real ffmpeg binary or fixture mp4 not available
Skipped in the regression of record: [1] tests/test_phase191b_ffmpeg.py:283: real ffmpeg binary or fixture mp4 not available
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
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:164: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:170: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:177: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:186: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:198: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [2] tests/test_phase388_fence_boundary.py:210: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:216: inside the fleet's fence: its boundary is proven from the host, not from inside

11297 + 105 = 11402, `COLLECTED_TEST_FLOOR`, unchanged: no test was added.

### 2026-10-25 — Labels on issue #14

This session moved no label and has no network but the model's. Every label
on issue #14 is set by the dispatcher's scripts from a parsed result, outside
this session: before this round, 389's handoff records `needs-admiral` taken
off and `plan:approved` re-applied by the planter's maintenance after 389's
merge. The labels this round's result moves are the dispatcher's, recorded on
the issue and in the Captain's recommendation, not here: this log is written
inside the stage and cannot see them.

### 2026-10-25 — The status note, and the review that did not run

The mission says row 385 is 🔲; 385's prompt says "add it ... as 🚧 before
Step 0". Both hold: the row is 🔲 until 385 starts, and 385's own session
turns it 🚧. The prompt is a committed record and was not edited.

No refute pass ran: nothing here is a content row, and no Red Team stage is
part of this trial's plan (the plan's Logic, section 5).

### 2026-10-25 — Close-out

No bug fixes, no guard blocked a command, no migration, nothing on live.
The close-out commit carries v1.1, row 389A ✅, this log's Complete status,
the three documents moved to `completed/` with `git mv`,
`implementation.md`'s history row and version, the root `phase_log.md`'s
pointer, and the handoff `docs/handoffs/2026-10-25_389A_closed.md`. It is
the branch's last commit, so this log cannot name its hash (the plan's
section 3); the pull request and the handoff's merge outcome name it.

`wholetree.sh` (fast) before the close-out commit, run on its own, with the
close-out staged: exit 0, "2085 passed, 10 skipped" (92.9 s wall).
`closeout_check.py . 389A` printed nothing; `roadmap_check.py` exit 0;
`roadmap_words.py 389A --check` printed 79, exit 0.
