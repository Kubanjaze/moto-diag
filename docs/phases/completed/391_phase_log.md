# Phase 391 — phase log: the Quartermaster, in shadow

**Status:** Complete
**Branch:** `phase-391-quartermaster`
**Prompt:** `docs/prompts/391_quartermaster.txt`

## 2026-10-26 — start, and the operator's two items first

- Read the plan: rows 389A to 390A, `ROADMAP_AUTHORITY.md` (391 is backend,
  205+), the newest handoff (`2026-10-26_390_closed.md`), `FOLLOWUPS.md`
  to F221, the fleet proposal's step 8 and its decisions table, the
  `fleet` skill and `dispatcher.py`, `captain.py`, `red_team.py`,
  `rank_call.py`, `journal.py`, `yeoman.py`, `verify_phase.sh`,
  `closeout_check.py`, `roadmap_check.py`, the push guard.
- 13:05:48: #14's model-free run on `e15b462` was running (`dispatcher.log`,
  two `bwrap` processes). Nothing of #14, PR #15 or their labels was
  touched; no test run of mine until it ended.
- **Item 1, row 390A** (the operator: "Close the row honestly per the
  ledger rule (what it proved, that it did not ship), with its handoff").
  Row 390A ✅, "Did not ship", and `docs/handoffs/2026-10-26_390A_closed.md`.
  Found while writing it: the branch `phase-390A-quartermaster-row` is no
  longer on GitHub (`git ls-remote origin 'refs/heads/phase-39*'` lists only
  `phase-390-resume`); `refs/pull/20/head` is `f987bf3`. The handoff and
  the row say so. The row is 91 words (`roadmap_words.py 390A --check`).
- **Item 2, F222** (the operator: "Make that a check (a close-out or
  fixture rule over handoffs' paste blocks), fix 390's handoff block in
  place, and file it as a finding"). Where it lives: `roadmap_check.py`,
  as R8, because R1–R7 already read the handoffs and run with every suite
  and on every push; a closeout A-rule would see only the phase being
  closed. Census first (a
  scratch script over every fenced block printing ALL GOOD): 45 handoffs,
  one block calling `gh` (390's); `docs/phases/`, one more (389's operator
  steps, whose `gh api` paths name the repository). R8 fired on 390's block
  and on nothing else; the good fixture first gave two false hits (an
  inline `GH_REPO=` and `cd … && gh` on one line), fixed by reading the
  text up to the `gh` word. `tests/test_roadmap_continuity.py`: 35 passed.
- **Guard blocks, two, both kept as they are:**
  - the edit guard refused `sed -i '1s/R1-R6/R1-R8/' tests/test_roadmap_continuity.py`
    ("`sed -i` edits a file in place, and is blocked wherever it points");
    done with the Edit tool;
  - the edit guard refused a mutation loop that copied the original back
    with `cp $D/orig.py` ("cannot tell where `cp` `$D/orig.py` writes");
    R8's mutations moved into this phase's `391_mutate.py`.
- **13:58:11, #14 failed its model-free run again** (`dispatcher.log`:
  "needs-admiral (engineer) … Regression run FAILED"): 11294 passed,
  3 failed, 105 skipped at `e15b462`, all three nested gates
  (`test_phase205_gate11`, `test_phase240_gate12` re-running gate 6;
  `test_phase258_gate14` re-running gate 13). The output
  (`runs/20261026_130548_check/run/check.txt`) prints no traceback. The
  gates' time limits on `e15b462` equal master's (900 s and 1800 s), so it
  is not 390's bug fix #3 missing. Read only; #14 is the operator's.
- `wholetree.sh` exit 0 (2210 passed, 10 skipped, 61 s), then two commits
  on `master`: `d3c0cc1` (R8, F222), `133dc26` (row 390A, row 391 🚧, the
  prompt), pushed `edd286c..133dc26`. Branch `phase-391-quartermaster`
  from `133dc26`.

## 2026-10-26 — Step 0

`391_step0.md`. The dry run's driver is kept as `391_dry_run.py` (it ran
from the session's scratch folder; its paths are that folder's).
- `verify_phase.sh 390A 44f846d f987bf3` in the fence, no model, no token:
  first with no virtualenv bound, when check 10 printed "No module named
  pytest" (a trap the reading of V10 must catch), then with the fleet's
  venv, 36 s, exit 1 from check 8.
- One Quartermaster call on PR #20: 61,300 tokens read, 1,093 written,
  3 turns, 11 s, $0.28 at list price. Verdict refuse, as the operator
  ruled; but it named checks of its own, so the brief lists the ids and
  the script refuses an unknown one.
- Decided, not stops (rule 1 does not reserve them):
  - **Q2, a Captain's hold refuses.** The proposal names "all 14 checks
    pass and the Red Team is clear"; the Captain's recommendation is the
    rank the operator reads first, and the one real refusal on record
    (PR #20) was on it. Stricter than the proposal, never looser.
  - **`quartermaster_since`.** The stage acts on an application of
    `merge:needs-review` made after it first ran on the machine. It keeps
    the new rank off #14 and PR #15, as the operator asked, and off older
    issues; applying the label again is the way in, as for every rank.
  - **An unchanged v1.0 section is not a stub** (S0-1's measurement).

## 2026-10-26 — v1.0, then the build

- **v1.0 committed** (`d2947f5`), after `plan_check.py 391` passed P1–P8
  (its first run failed P3 four times, counts in Step 0 with no command
  beside them, and P5 on the plan's own `data/` in Goal and Logic; both
  reworded). Pushed as a separate command: the push guard refused
  `git commit … && git push` in one ("This command runs `git commit` before
  `git push`"), as it should.
- **`quartermaster.py`, Q1–Q9 and the call**, tried on the real record
  before any test: 390 at its close-out (`48e7d2c`) passes Q1, Q6, Q7, Q9
  and **fails Q8 on R8**: its handoff's paste block, the one that failed
  for the operator today. So the Quartermaster would have refused 390's
  handoff as it shipped. PR #20's fence output fails V12 alone.
- **One shared reader**: `plan_check.classification`, P4's parse, now used
  by P4 and Q1.
- **The dispatcher**: `stage_quartermaster`, `quartermaster_due`,
  `quartermaster_since` (set by the first cycle), `Check.out`, the
  `resume()` branch, `STAGE_RANK`, `RANK_PREFIXES`, the sweep's text, the
  digest's verdicts. `yeoman.shadow` writes the digest's section.
- **389's and 390's tests carried on**: 389's walk-through now meets the
  Quartermaster after `merge:needs-review` (a refusal, no label moved);
  390's contract finds kill-point tests in 391's file too, and reads the
  CHANGELOG's 390 entry wherever it stands (it read only the newest).
- **A bug before any commit**: `_text` raised on a missing file (389's
  walk-through has no `implementation.md` at the root). Fixed in place;
  not a bug-fix entry, as no commit held it.
- **Guard blocks, three more, each kept as it is:**
  - the edit guard refused a Python script writing
    `tests/test_phase391_dispatcher.py` ("a Python script body writes
    tests/…"); done with Edit;
  - the edit guard refused a Python script writing `SKILL.md` because its
    text named `tests/`; done with Edit;
  - 244G's meta-guard (a test, in `wholetree.sh`) refused the contract
    test's raw-source asserts; they read `code_of` now.
- Tests: `test_phase391_quartermaster.py` 49, `test_phase391_dispatcher.py`
  15, `test_phase391_contract.py` 8; with 387–390's and the ledger's, 549
  passed. `wholetree.sh` exit 0 (2271 passed, 10 skipped).

## 2026-10-26 — mutations

`391_mutate.py`, 60 mutations at first, each one exact edit, the tests run
after clearing `__pycache__`. **55/60 red; five survived**, each a defect
in the tests or the code, not in the harness:
- **Q4b** (a failed run passes): the test's failed run had no line, so the
  counts check refused it anyway. Added a failed run whose counts match.
- **Q5-3, Q5-5** (in_progress not read; A4 not read): each red section
  also removed what the other half of the rule reads (no completed list;
  no Deviations line), so the check refused for the wrong reason. Each
  case now breaks one thing.
- **Q8b** (an early handoff passes): Q8's own date rule repeated R6, which
  Q8 runs on the branch. The duplicate is removed; the test now holds R6's
  message inside Q8. The mutation goes with it.
- **R8e** (a comment is a call): the skip was never reached, as no good
  case had a `gh` after a separator inside a comment. The good fixture
  gains one, so the skip is exercised.

Two tests were added before the run, for gaps seen while writing it: a
resumed stage reads `verify_phase.sh`'s output back from its journal
(`Check.out`), and the digest stage carries the day's verdicts.
`yeoman.shadow` now reads an unreadable `gh` answer as "unknown" (the
stand-in's `pr view` answers with a body, not a state).

Then **59/59 red** (`391_mutate.out`).

## 2026-10-26 — the regression of record

- The fleet idle (no `bwrap`; #14 held under `needs-admiral` since
  13:58:11), as in 390: `Fleet.check_run` on a fresh clone of `ac1dc6b`
  in `runs/20261026_144852_check`, `--net none`, no token, the fleet's
  venv: `wholetree.sh --full` first, then `regression.sh`.
- **`wholetree.sh --full` inside the fence:** "PASSED — 4716 passed, 36
  skipped, 32 warnings in 1040.64s (0:17:20) (1043.6 s wall)", 119 test
  files.
- 11500 passed and 105 skipped: 11605, the floor `ac1dc6b` set.
- Logged by the dispatcher meanwhile, 14:03:39: "reclaim (phase 390A
  merged)". Row 390A going ✅ on master read as a merge, as `reclaim_boundaries`
  is written (a 🚧 row now ✅); a reclaim, nothing else. Not a defect.

Regression of record: 11500 passed, 0 failed, 105 skipped, 0 errors at `ac1dc6b` (35 min 45 s wall, `python -m pytest -n auto --dist load`, exit 0) (run inside the fleet's fence)
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
Skipped in the regression of record: [1] tests/test_phase244H_test_db_isolation.py:79: no production database on this machine
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

## 2026-10-26 — the whole-tree run before each commit

Each `wholetree.sh` ran on its own, its exit read, before the commit it
names (the outputs were kept in the session's scratch folder; the record
names the HEAD the run was made on, the commit before):

| before | output | exit |
|---|---|---|
| `d3c0cc1`, `133dc26` (master) | "PASSED — 2210 passed, 10 skipped … (61.4 s wall)", and no record | 0 |
| `d2947f5` (v1.0) | "PASSED — 2210 passed, 10 skipped … (56.5 s wall)", and no record | 0 |
| `a45b5be` (the build) | first "FAILED — 1 failed, 2270 passed" (244G's meta-guard, above); then "PASSED — 2271 passed, 10 skipped … (68.0 s wall)", record `8bd8e4b1…` on `d2947f5`, and again after the log entry, record `74dba163…` | 1, then 0 |
| `944fd42` (the mutations) | "PASSED — 2271 passed, 10 skipped … (71.2 s wall)", record `a76159a0…` on `a45b5be` | 0 |
| `ac1dc6b` (the floor) | "PASSED — 2271 passed, 10 skipped … (73.7 s wall)", record `3a78d36e…` on `944fd42` | 0 |

The close-out commit's is below, after the refute.

## 2026-10-26 — the refute

A fresh agent (Opus, read-only, not the builder's session) refuted the
close-out's documents against the code, git, GitHub and the fleet's files.
- **Round 1**: 33 rows; 10 killed, 6 factual or citation: 390's block
  "added after its merge" (it is in 390's close-out, `48e7d2c`); F222's
  "first written at `edd286c`"; 390A's "one per rank, each cut by a
  restart" and "each reached its next label" (#22 was the uncut control,
  #21 stopped on C7); the four commits "each after `wholetree.sh` … in the
  phase log" (the log named two); Step 0's V10 row (a `passed` count, which
  the code does not need). Four wording: the reclaim time, two signatures,
  the issue marker. Each fixed, deleting where it could.
- **Round 2** (the diff and its sentences only, K9): every fix held. Two
  new wording defects in the new table, fixed: "(untracked files)" said
  more than the tool does, and the build row's exit column hid the first
  run's failure. One left open by choice: the closeout CHANGELOG and a test
  name say `edd286c` where the block was first written at `48e7d2c`; both
  are code for check 2, so changing them would void the regression of
  record. It is F224, the one finding for open wording.

## Refuter pass

| claim | verdict | quote | source | round · kind · outcome |
|---|---|---|---|---|
| 390's paste block was added after its merge | killed | "gh issue edit 14 --remove-label needs-admiral </dev/null >/dev/null" | docs/handoffs/2026-10-26_390_closed.md p. 177 | 2 · factual · fixed |
| F222's real block was first written at 48e7d2c and still there at edd286c | kept | "block as first written at `48e7d2c` and still there at `edd286c`, and 389's block as the control)." | docs/FOLLOWUPS.md p. 4137 | 2 · citation · fixed |
| The CHANGELOG and the test name say the block as first written is at edd286c | killed | "the first as first written (`edd286c`) and not on the second, its" | .claude/skills/closeout/CHANGELOG.md p. 21 | 2 · wording · open F224 |
| 390A's planted missions: issues #16 to #19 and #21 to #24, the Red Team three times, the Captain twice | kept | "planted trials, for every rank (the Red Team three times, the Captain" | docs/handoffs/2026-10-26_390A_closed.md p. 14 | 2 · factual · fixed |
| Row 390A: issues #16–#19, #21–#24, for every rank | kept | "resumed refute stopped on C7, the model's own miss; #22 was the uncut" | docs/handoffs/2026-10-26_390_closed.md p. 73 | 2 · factual · fixed |
| 390A proved 390's resume, rank by rank | kept | "Phase 390's resume, rank by rank. The list, mission by mission, is in" | docs/handoffs/2026-10-26_390A_closed.md p. 20 | 2 · factual · fixed |
| A whole-tree run, exit 0, before each commit, now in the phase log | kept | "Each `wholetree.sh` ran on its own, its exit read, before the commit it" | docs/phases/completed/391_phase_log.md p. 243 | 2 · factual · fixed |
| Before the master commits: 2210 passed, 61.4 s wall, no record | kept | "PASSED — 2210 passed, 10 skipped … (61.4 s wall)" | docs/phases/completed/391_phase_log.md p. 249 | 2 · none · kept |
| Before d2947f5: 2210 passed, 56.5 s wall, no record | kept | "PASSED — 2210 passed, 10 skipped … (56.5 s wall)" | docs/phases/completed/391_phase_log.md p. 250 | 2 · none · kept |
| No record was written, for one of the three causes the tool names | kept | "and no record" | docs/phases/completed/391_phase_log.md p. 249 | 2 · wording · fixed |
| Before a45b5be: the first run failed, 1 failed and 2270 passed | kept | "first \"FAILED — 1 failed, 2270 passed\" (244G's meta-guard, above)" | docs/phases/completed/391_phase_log.md p. 251 | 2 · none · kept |
| The a45b5be row's exit is 1, then 0 | kept | "1, then 0" | docs/phases/completed/391_phase_log.md p. 251 | 2 · wording · fixed |
| Before 944fd42: 71.2 s, record a76159a0 on a45b5be | kept | "PASSED — 2271 passed, 10 skipped … (71.2 s wall)\", record `a76159a0…` on `a45b5be`" | docs/phases/completed/391_phase_log.md p. 252 | 2 · none · kept |
| Before ac1dc6b: 73.7 s, record 3a78d36e on 944fd42 | kept | "PASSED — 2271 passed, 10 skipped … (73.7 s wall)\", record `3a78d36e…` on `944fd42`" | docs/phases/completed/391_phase_log.md p. 253 | 2 · none · kept |
| Step 0: V10 needs a pytest summary line | kept | "rule(n, bool(_SUMMARY.search(s)) and not _RED_COUNT.search(s)," | .claude/skills/fleet/quartermaster.py p. 232 | 2 · factual · fixed |
| The reclaim line was logged at 15:44:08 | kept | "The reclaim line for this close-out (`dispatcher.py reclaim`, logged 15:44:08):" | docs/handoffs/2026-10-26_391_closed.md p. 63 | 2 · wording · fixed |
| full_run and read_verify have the built signatures | kept | "def full_run(ok: bool, line: str or None, why: str, log_text: str) -> Finding:" | .claude/skills/fleet/quartermaster.py p. 182 | 2 · wording · fixed |
| The issue marker carries verdict and failed | kept | "self.say_once(issue, f\"{QM_M} verdict={verdict} failed={checks.replace(' ', ',')} -->\"," | .claude/skills/fleet/dispatcher.py p. 1474 | 2 · wording · fixed |
| Regression of record 11500 passed, 105 skipped at ac1dc6b, 35 min 45 s | kept | "11500 passed, 0 failed, 105 skipped, 0 errors at `ac1dc6b` (35 min 45 s wall" | docs/phases/completed/391_phase_log.md p. 158 | 1 · none · kept |
| wholetree.sh --full: 4716 passed, 36 skipped | kept | "- **`wholetree.sh --full` inside the fence:** \"PASSED — 4716 passed, 36" | docs/phases/completed/391_phase_log.md p. 150 | 1 · none · kept |
| Floor 11520 to 11605, +78 by the diff of collected ids | kept | "#: at 133dc26 (11527: R8's 7 in test_roadmap_continuity.py, F222, landed" | tests/test_phase255B_collected_test_floor.py p. 1 | 1 · none · kept |
| Mutations 59/59 red, exit 0 | kept | "59/59 red" | docs/phases/completed/391_mutate.out p. 60 | 1 · none · kept |
| Q8b's mutation went with the duplicate date rule | kept | "\"\"\"Held by R6, which Q8 runs on the branch (no second date rule).\"\"\"" | tests/test_phase391_quartermaster.py p. 260 | 1 · none · kept |
| 17 tests in the dispatcher file, four kill points named | kept | "\"after the issue marker, before the record\": \"test_quartermaster_cut_after_its_issue_marker\"" | .claude/skills/fleet/fixtures/resume/kill_points.json p. 56 | 1 · none · kept |
| PR #20's fence output fails V12 alone | kept | "no refuter block (the phase ran no pass, or did not record one)" | .claude/skills/fleet/fixtures/quartermaster/pr20/verify.txt p. 32 | 1 · none · kept |
| verify_phase.sh's exit is set by check 8 alone | kept | "FAILED=0" | .claude/skills/closeout/verify_phase.sh p. 37 | 1 · none · kept |
| PR #20 and #24's markers fail Q2 and Q3 | kept | "assert ids(found) == [\"Q2\", \"Q3\"]" | tests/test_phase391_quartermaster.py p. 150 | 1 · none · kept |
| The dry run's model named checks of its own | kept | "\"check\": \"Q3 the Captain's recommendation\"," | .claude/skills/fleet/fixtures/quartermaster/pr20/verdict.json p. 5 | 1 · none · kept |
| #14 failed at 13:58:11, 11294 passed and 3 failed at e15b462 | kept | "3 failed, 105 skipped at `e15b462`, all three nested gates" | docs/phases/completed/391_phase_log.md p. 46 | 1 · none · kept |
| 14:03:39 reclaim read row 390A as merged | kept | "- Logged by the dispatcher meanwhile, 14:03:39:" | docs/phases/completed/391_phase_log.md p. 154 | 1 · none · kept |
| The nested gates' limits on master are 900 s and 1800 s | kept | "cwd=REPO_ROOT, capture_output=True, text=True, timeout=1800," | tests/test_phase258_gate14.py p. 914 | 1 · none · kept |
| The 50 GB free-space floor | kept | "SPACE_FLOOR_GB = {\"C:\": 50, \"Ubuntu\": 50}" | .claude/skills/fleet/dispatcher.py p. 126 | 1 · none · kept |
| The digest's section and its agreement words | kept | "out = [\"## The Quartermaster (shadow)\", \"\", f\"Verdicts in the window: {len(verdicts)}.\"]" | .claude/skills/fleet/yeoman.py p. 175 | 1 · none · kept |
| Checks 1, 7, 8 and 9 are not read | kept | "\"V9\": \"as V8\"," | .claude/skills/fleet/quartermaster.py p. 78 | 1 · none · kept |
| F223: ranks read markers by first line alone, via _RED | kept | "_RED = re.compile(r\"^<!-- fleet-red-team: verdict=(\\w+) round=(\\d+)\", re.M)" | .claude/skills/fleet/dispatcher.py p. 177 | 1 · none · kept |
| F222's tests carry four planted cases | kept | "(\"R8 docs/phases/completed/259_phase_log.md: an operator paste block runs `gh label list\"," | tests/test_roadmap_continuity.py p. 66 | 1 · none · kept |
| PR #20 closed unmerged at 16:38 UTC with the quoted comment | kept | "PR #20, closed unmerged by the operator on 2026-10-26 at 16:38 UTC, with" | docs/handoffs/2026-10-26_390A_closed.md p. 27 | 1 · none · kept |
| The Captain's hold quote on PR #20 | kept | "no record of a Red Team clear on the issue, on the branch or in the phase" | docs/handoffs/2026-10-26_390A_closed.md p. 38 | 1 · none · kept |
| Row 390A is 91 words | kept | "The row is 91 words (`roadmap_words.py 390A --check`)." | docs/phases/completed/391_phase_log.md p. 24 | 1 · none · kept |
| Step 0 census: the quartermaster hits are two, in the skills | kept | "The two skill hits for `quartermaster` are `dispatcher.py`'s sweep text" | docs/phases/completed/391_step0.md p. 21 | 1 · none · kept |
| S0-3: 390 has 4 claims, 390A has 2, all in history | kept | "`48e7d2c` has 4 claims, all in its history; 390A at `f987bf3` has 2, both" | docs/phases/completed/391_step0.md p. 121 | 1 · none · kept |

Before the close-out commit: `wholetree.sh` "PASSED — 2271 passed, 10
skipped … (78.2 s wall)", exit 0, record `c9fde2a4…` on `ac1dc6b`; then once
more after this line was written, below in the commit's own message.
`closeout_check.py . 391`, `refute_check.py` and `roadmap_check.py`: all
exit 0. Q1, Q6, Q7 and Q8 run on this tree by hand: all pass.

## 2026-10-26 — the trials

- **A missing handoff cannot be pushed** from either path. On a branch at
  `79a06da` with `docs/handoffs/2026-10-26_391_closed.md` deleted, row 391 ✅
  fails R6; `tests/test_roadmap_continuity.py` is a fast whole-tree member
  (`wholetree.members("fast")` lists it); the push guard accepts a pushed
  commit only with a signed whole-tree record for its tree
  (`_pre_push_guard.wholetree_gate`), and the fleet's push gate runs
  `roadmap_check` (G5). So no such commit was made or pushed, and the
  guard was not tried. Asked the operator how to plant that trial; their
  answer: "Handoff with no content (Recommended)": the handoff keeps its
  name, so R6 passes, and holds only its title line.
- **A stub v1.1 passes every check before the Quartermaster.** The stub
  branch (`bd3e8ea`: v1.1's Results replaced by "To be written after the
  merge.") passed `wholetree.sh`, exit 0 (2271 passed, 61.2 s), record
  `c36b9f43…`, and was pushed through the guard.
- **The service on this phase's code**, for the trials (as 390's ran on
  its branch): `~/motodiag/fleet/code` at `79a06da`, then a SIGTERM to the
  unit's main process (pre-approval (c): no fence running, #14 held under
  `needs-admiral`). dispatcher.log: "16:03:38 the search on start: nothing
  to resume", then "16:03:43 the Quartermaster judges merge:needs-review
  applied after 2026-10-26T16:03:43-04:00".
- **The stub trial**: PR #25, issue #26, opened under the operator's login
  (pre-approval (a)) by `qm_trial.sh`, a scratch driver: the PR, the issue
  with the trial marker, a Red Team clear and a Captain's merge each
  planted as a comment that says it is planted, then `merge:needs-review`.
  "16:08:52 issue 26: the Quartermaster on phase 391, bd3e8ea4484b".
- **The emptied-handoff branch** (`0836ed4`), made from `79a06da`; local
  Q8: "2026-10-26_391_closed.md has no '## What is open'; … no '## What is
  next'". Its whole-tree run waits for the fleet's run to end (F220).
- **The restart, mid-stage** (pre-approval (c), #14 still held): at
  16:58:24 a SIGTERM to the unit's main process, while #26's full
  model-free run had been going 49 minutes; its journal held only
  `started` and `clone`, no check. dispatcher.log, on the new start:
  "16:58:57 resume quartermaster from 20261026_160850_quartermaster_391
  (issue 26), after started, clone", then "issue 26: the Quartermaster on
  phase 391, bd3e8ea4484b": the cut run made again on the same commit, in
  the same run directory.
- **The stub trial's verdict**, "17:52:40 issue 26: verdict: refuse (Q7
  Q7)": Q7 named by the script ("section 'Results' has a stub: 'To be
  written after the merge.'") and again by the model; no other check
  failed. The model read check 4's two hits as prose ("just sentences
  describing the stub rule"). Its call: 50,464 tokens read, 603 written,
  3 turns, 8 s, $0.22 at list price. The comment is the fleet's
  (`kubanjazefleet`); #26's label stayed `merge:needs-review`. The same
  search on start logged "1 stage(s) acted on" once the stage ended.
  Cosmetic: the log line repeats an id the script and the model both named.
- **The emptied-handoff trial**: `0836ed4` passed `wholetree.sh`, exit 0
  (2271 passed, 58.9 s), record `8196941b…`, pushed; PR #27, issue #28.
- **#28's first run did not finish.** "18:58:44 cycle failed:" with
  `subprocess.TimeoutExpired` from `check_run` (its fenced run past
  `CHECK_TIMEOUT_S`, 3600 s), then "19:03:55 issue 28: the Quartermaster on
  phase 391, 0836ed4ba381", a new stage from the start: F225.
- **At 19:40 Ubuntu's disk went read-only** (the operator's account: write
  I/O errors on the sparse `ext4.vhdx`, C: not full). The operator moved
  Ubuntu to a fresh non-sparse image (`C:\WSL\Ubuntu-26.04`) by export and
  import. Lost: every fleet run folder but #14's two; the mirror rebuilt.
  This checkout, its branch and this log's uncommitted lines survived. The
  import left `runs/` owned by root: every cycle from 21:40 fails with
  `PermissionError` making a run folder. Filed as F226, with the reclaim
  that no longer shrinks the image (21:45:28: "C: 499.2 -> 499.2 GB free
  … 991.7 GiB trimmed").
- **The operator's order after the move**, verbatim: "(1) File two
  findings: the uncaught check-run timeout that crashes a cycle and
  restarts the stage; and the sparse-vhdx disk failures of 2026-10-25 and
  10-26 (sparse is now off; F221's reclaim must work without it: fstrim
  still runs but no longer shrinks the file, so record what replaces it).
  (2) Re-run the emptied-handoff trial (#28) and the green trial, record
  both, close the planted PRs/issues. (3) Merge 391: phase-391-quartermaster
  into master --no-ff, with origin/master (cadaa37: the 392 prompt, a plan
  entry, K43/K44) merged in first, whole-tree first; verify_phase.sh 391;
  push. (4) A dated correction in 391's log: line 50's claim about #14 is
  wrong; the failing call is inside test_phase147_gate_6.py, timeout=60 at
  lines 835 and 854 on e15b462, master 300. (5) #14, as 389 did, under my
  login: push e15b462 (from runs/20261025_160200_engineer_389A/clone) to
  phase-389A-385s-roadmap-row, merge origin/master into it (whole-tree
  first), push, take needs-admiral off #14 (gh with -R), re-apply
  plan:approved for a fresh Engineer round. Run no tests of yours while its
  model-free run goes. Comment on #14 what you did. Report after (3) and
  after (5)."
- **What replaces the shrink is not decided here.** F226 lists what was
  measured (compacting with Ubuntu shut down; bounding what the fleet
  keeps); choosing is the operator's.
- **22:1x, the operator's one command** (`sudo chown` on `runs/`, "ALL
  GOOD"). "22:21:24 issue 28: the Quartermaster on phase 391,
  0836ed4ba381": a fresh stage, run folder `20261026_222123_quartermaster_391`.
- **The emptied-handoff trial's verdict**, "22:59:49 issue 28: verdict:
  refuse (Q4 Q8 Q4 Q8)", by `kubanjazefleet` on PR #27; $0.23. Q8 is the
  planted defect, named by the script and the model. Q4 is not: the full
  run (`runs/20261026_222124_check`) ended "1 failed, 10556 passed, 105
  skipped … exit 3". Worker gw9 failed
  `test_f194_an_evening_invoice_carries_the_shops_day`, then raised
  "OSError: [Errno 24] Too many open files" in `worker_loss.py` writing
  `gw9.last`; xdist stopped on "assert not crashitem". Read first, as
  rule 6 asks: the worker-loss files hold no signal and an empty
  faulthandler dump for any worker; there is no "node down" block. The
  service runs at a soft limit of 1024 open files (`/proc/<pid>/limits`),
  the unit sets none, and it is the same unit as before the move. gw9's
  328 tests, in its order, serially under `ulimit -Sn 1024` in this
  checkout: 328 passed. Filed as F227; the unit is not changed here (its
  limit is the operator's).
- **Decided:** the trial stands as a refusal that names the right check.
  Its extra Q4 is recorded as the machine's failure, not the branch's.
  The green trial goes ahead on the next documents-only head; if its full
  run fails the same way, that is a test the phase cannot make green, and
  it stops.
- **The green trial** (PR #29, issue #30, `phase-391-qmtrial-green` at
  `7b96129`, opened 23:0x by a rewritten scratch driver: the reboot had
  cleared `/tmp`). The real Captain: "23:11:00 issue 30: recommendation:
  merge"; the Quartermaster: "00:05:47 issue 30: verdict: merge (none)",
  $0.25. Its full run (`runs/20261026_231611_check`): `wholetree.sh --full`
  4716 passed; then 11500 passed, 0 failed, 105 skipped at `7b96129`,
  exit 0, 32 min 26 s. The operator's verdict is the merge ordered above:
  it agrees.
- **Closed unmerged**: PRs #25, #27, #29 and issues #26, #28, #30, under
  the operator's login (pre-approval (a)). The trial branches are kept.

## 2026-10-27 — correction to the 13:58:11 entry on #14 (the operator's)

The entry "13:58:11, #14 failed its model-free run again" (under "start,
and the operator's two items first") says: "The gates' time limits on
`e15b462` equal master's (900 s and 1800 s), so it is not 390's bug fix
#3 missing." **That is wrong.** The outer gates' limits do match, but the
call that fails is inside `tests/test_phase147_gate_6.py`, which the
nested gates run: on `e15b462`
(`runs/20261025_160200_engineer_389A/clone`) it has `timeout=60` at lines
835 and 854; on `master` the same two calls are `timeout=300` (lines 838
and 858 now). So #14's branch lacks that raise, and its failure is
consistent with it. The original entry is left as written; this one
supersedes it. Found by the operator.

## 2026-10-27 — the merge

- `master` fast-forwarded to `cadaa37` (the 392 prompt, a plan entry,
  K43/K44: documents only), then `phase-391-quartermaster` merged into it
  `--no-ff`: `861f8b8`. `wholetree.sh` exit 0 on the staged merge (2271
  passed, 66.6 s) and on the commit (record for `861f8b8`); pushed.
  GitHub's reply carried "Cannot update this protected ref" as a rule the
  operator's login bypasses; `git ls-remote` shows `master` at `861f8b8`.
- `verify_phase.sh 391 ac1dc6b 861f8b8`: check 1 clean after the push,
  check 2 "none (docs only)", check 10 74 passed, checks 11–14 pass.
- The service's clone back on `master` at `861f8b8`; SIGTERM to its main
  process with no fence running and #14 held; "00:13:57 the search on
  start: nothing to resume".

## 2026-10-27 — #14's maintenance (the operator's item 5), stopped before any push

- `e15b462` fetched from `runs/20261025_160200_engineer_389A/clone` into a
  worktree beside this checkout, `~/Projects/moto-diag-389A`, on branch
  `phase-389A-385s-roadmap-row` (GitHub has it at `bdecabd`, `e15b462`'s
  parent). A first worktree under the scratch folder failed four tests that
  need `../moto-diag-mobile` beside the repository; it was removed.
- **A guard block, mine**: the edit guard refused `echo "/.venv" >> $E`
  ("cannot tell where the redirect `>>` `$E` writes"); nothing ran; redone
  with the literal path `.git/info/exclude`. No guard changed.
- **`e15b462` cannot be pushed through the push guard.** `wholetree.sh` on
  it: "2 failed, 2083 passed": `test_phase388_dispatcher.py::TestOneCycle::test_once_per_application_of_the_label`
  ("IndexError: pop from empty list") and
  `TestTheRateLimitPauses::test_recorded_commented_paused_then_resumed`
  (no `fence.sh`). Both, serially, in 0.9 s. On that commit they assume "no
  fleet account" on the machine; `~/.config/motodiag/fleet-github.env` now
  exists. In the Engineer's fence the same tree passed (`wt_r2c.txt`, 2085
  passed). The guard needs a record for every commit a push sends
  (`_pre_push_guard.wholetree_gate`), so no push was tried. A test I cannot
  make green: a stop (rule 1).
- **The merge is made, not pushed**: `bc50c4b`, `origin/master`
  (`1867604`) into `e15b462`, three ledger conflicts resolved in phase order;
  `roadmap_check` and `closeout_check . 389A` pass; `wholetree.sh` exit 0
  (2271 passed), record for `bc50c4b`.
- **A second question for the operator, found reading the dispatcher**:
  with `build:open` still on #14 and the held run kept (`held.json`),
  taking `needs-admiral` off makes the cycle choose the recheck on
  `e15b462` (`next_stage`: `build:open` and `held_for` come before
  `plan:approved`), not a fresh Engineer round. No label was moved.
- **The operator's answers** (2026-10-27): to how #14's branch reaches
  GitHub, "You push it (Recommended)" (a paste block from their own login,
  outside this session's guard; `e15b462` and `bc50c4b` both kept); to the
  labels, "Clear the old round (Recommended)" (`build:open` off too, and
  the held run released, its `held.json` kept as `held.json.released`).
- **The operator pushed** (2026-10-27, "ALL GOOD, the push is done");
  `git ls-remote` reads `bc50c4b` on `phase-389A-385s-roadmap-row`.
- **#14 handed back** (07:44, no `bwrap`, dispatcher idle): the held run's
  `held.json` renamed `held.json.released`; `gh issue edit 14 -R
  Kubanjaze/moto-diag --remove-label build:open --remove-label
  needs-admiral --add-label plan:approved`; labels read `mission`,
  `plan:approved`; master's 389A row is 🚧. Comment:
  https://github.com/Kubanjaze/moto-diag/issues/14#issuecomment-6441060414
- **The fresh round**: 07:45:21 "the Chief Engineer on phase 389A, round
  0" (`20261027_074517_engineer_389A`); 08:40:26 "the model-free run on
  ffcb6871711a"; its regression: "11500 passed, 0 failed, 105 skipped, 0
  errors at `ffcb687` (32 min 58 s wall, `python -m pytest -n auto --dist
  load`, exit 0)"; 09:29:55 the close-out reclaim "C: 396.4 -> 396.4 GB
  free"; 09:29:58 pushed as `kubanjazefleet`; 09:30:04 "PR 15 ready",
  labels `mission`, `review:open`. No test of mine ran from 07:44 to the
  run's end. Merging PR 15 stays the operator's.
- **Earlier the same morning**, one cycle failed "Could not resolve host:
  github.com" while updating the mirror; later cycles ran. A transient
  network failure, not filed.
