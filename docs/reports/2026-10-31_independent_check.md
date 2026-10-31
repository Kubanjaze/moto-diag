# Independent check of master, on the Mac

**2026-10-31**, by the advisor session on the Mac. It ran from the
operator's prompt of 2026-10-31, which asked for "the full test run, then
the code-quality comparison" in one go. Behind that prompt are the
operator's words that morning: "I wanted to run like a rugression to make
sure nothing is broken and that the agents are actually developing in line
with the quality of work already done".

**Where it ran:** the Mac, on AC power, with 10 cores (4 performance, 6
efficiency). The repository was `~/Projects/moto-diag`, master at
`ce97159`, a clean tree. The tools were the checkout's `.venv`: Python
3.14.5, pytest 9.0.3, pytest-xdist 3.8.0, coverage 7.14.1, ruff 0.16.9 and
mypy 2.3.1. Nothing ran on the home desktop, where the fleet was building
345.

## The answer

**Nothing in the program is broken, and the fleet's work holds up against
the builder sessions' work.**
- One test failed out of the 12,135 that ran. Its one-second window is too
  short for a busy Mac (F241), and it passes when run alone.
- Line coverage is 87.75%, above the 87.50% pin.
- Each of the seven code counts on master equals its pin.

The comparison:
- **No phase has made any of the seven counts worse since the quality
  rules began** with Phase 393 (merged 2026-10-29), whether the fleet or a
  builder session built it. 348 is the only phase since then that changed
  the program code (11 files, +545 −19), and it kept every count where it
  was.
- **303, built by the fleet before the rules existed, added 4 lint
  findings and 1 type error.** 393's clean-up then brought both counts
  below where they stood before 303.
- **Every phase's tests caught every bug planted in it.** The fleet's
  scored 24/24, 12/12 and 5/5; the builders' scored 31/31, 15/15, 35/35 and
  18/18.
- **The fleet's phases face a reviewer the builders' phases do not: the
  Red Team.** On 303 and 348 it sent back wording problems in the documents
  only, never a fault in the code.
- **The fleet logged no bug fixes in its three builds.** The builder
  sessions logged 3 in 393 and 1 in 395.

What this check cannot see:
- **The seven counts read only the program code under `src/`.** 385, 394,
  395 and 396 changed only the fleet's and the deploy tools under
  `.claude/skills/`, which the counts do not read.
- **47 tests that check the fleet's sandbox from outside ran in neither
  full run.** The Mac skips them because its sandbox is a different kind,
  tested separately. The desktop's runs skip them because those runs happen
  inside that sandbox. The records read here do not say when they last ran
  on the desktop outside the sandbox.

## Part 1: the full test run

### The whole-tree command, full mode

`.claude/skills/closeout/wholetree.sh --full` ran from 18:54:19 to
19:01:50 and exited 0:

    wholetree full: 140 test files
    wholetree full: PASSED — 5052 passed, 1 skipped, 11 warnings in 449.90s (0:07:29) (450.4 s wall)
    wholetree: record 1f39c32ec9de71c1939abf90a72255e17aa0ecd4_full.json for commit ce97159d8fd2

### The regression

`.claude/skills/closeout/regression.sh` ran from 19:02:03 to 19:27:56 and
exited 1. pytest started 10 workers for 12,184 items (the log's header).
Its lines, as printed:

    Regression run FAILED (not of record): 12134 passed, 1 failed, 49 skipped, 0 errors at `ce97159` (25 min 53 s wall, `python -m pytest -n auto --dist load --cov=motodiag`, exit 1)
    Line coverage of record: 87.75% at `ce97159` (the pin is 87.50%)

The log is `~/.cache/motodiag/regressions/ce97159_parallel_20261031_190203.log`,
on the Mac only. The coverage JSON beside it counts 32,032 of 36,505 lines
covered (87.747%).

### The failure (F241)

The failing test is
`tests/test_phase392_check_limit.py::test_run_group_kills_the_whole_group_and_says_what_it_printed`.
It failed at line 60, `assert "started" in e.value.stdout`, with stdout
empty. The test gives a planted script one second to print "started"
before the dispatcher's `run_group` kills it. Under the full run's load,
the script had printed nothing by then.

Afterwards, on the same Mac:
- the test alone, ten times: 10 passed;
- the test alone, ten times, with 20 busy `yes` processes running: 10
  passed.

The 20 processes ran from about 19:29:30 to 19:34:57. That was longer than
intended, because the script's own clean-up missed them. Nothing else was
running then, and part 2 began at 19:36:02.

So the test fails only under the full parallel run's load. That is a bug
in the test, filed as F241. F241 also records a second weakness in the
same test: macOS has no `/proc`, so its check that the child process was
killed cannot fail on the Mac.

### Against the desktop's numbers

| | the Mac, `ce97159` | desktop, 396 at `c8bd296` | desktop, 385 at `4753b2d` |
|---|---|---|---|
| collected | 12,184 | 12,184 | 12,152 |
| passed | 12,134 | 12,079 | 12,047 |
| failed | 1 | 0 | 0 |
| skipped | 49 | 105 | 105 |
| line coverage | 87.75% | 87.71% | 87.71% |
| wall | 25 min 53 s | 13 min 8 s | 34 min 21 s |

The desktop's figures are the regression lines in its handoffs
(`docs/handoffs/2026-10-31_396_closed.md`,
`docs/handoffs/2026-10-31_385_closed.md`). Both runs were inside the
fleet's fence. Each difference, with its cause:

- **Collected: the same 12,184 as 396.** No file under `src/` or `tests/`
  changed between `c8bd296` and `ce97159`
  (`git diff --name-only c8bd296 ce97159 -- src tests` lists none). 385
  collected 32 fewer, because 396 added 32 (its commit `c8bd296`:
  "+32 -0").
- **Skipped: 49 against 105.** The table below lists the skips by file,
  from 396's skip lines (`docs/phases/completed/396_phase_log.md`) and
  this run's:

  | test file | desktop | Mac | the reason given |
  |---|---|---|---|
  | `test_phase388_fence_boundary.py` | 47 | 47 | desktop: inside the fence, its boundary is proven from the host; Mac: its fence is sandbox-exec, proven by `test_phase257_sandbox_boundary.py` |
  | `test_phase209_packaging.py` | 21 | 0 | inside the fence: no network to build a wheel |
  | `test_phase257_sandbox_boundary.py` | 12 | 0 | sandbox-exec is macOS-only |
  | `test_phase257_source_checks.py` | 10 | 0 | the on-disk library, or a manual not in it |
  | `test_phase191b_ffmpeg.py` | 5 | 0 | no real ffmpeg binary or fixture mp4 |
  | `test_phase257_manual_route_excerpts.py` | 5 | 0 | needs the on-disk library |
  | `test_phase257_orchestrator_guards.py` | 3 | 0 | inside the fence: osacompile is macOS-only (2), no Subconscious login (1) |
  | `test_phase204_gate10.py` | 1 | 0 | inside the fence: no ffmpeg on the home desktop |
  | `test_phase244H_test_db_isolation.py` | 1 | 1 | no production database on this machine (both) |
  | `test_phase390_space.py` | 0 | 1 | Mac: bubblewrap is the desktop's |

  So the Mac ran 57 tests that the desktop's run skips, and skipped 1 that
  it runs.
- **Passed: 12,134 against 12,079.** 12,079 + 57 − 1 − 1 (the failure) =
  12,134.
- **Coverage: 87.75% against 87.71%,** on the same program code. Suppose
  both runs counted the same 36,505 lines. Then the desktop's 87.71% is
  about 32,019 lines covered, so the Mac covered about 13 more lines, and
  it ran 57 more tests. Which lines those are was not measured: the
  desktop's coverage file is not on this Mac.
- **Wall time:** 25 min 53 s on the Mac, which is a different machine. The
  desktop's own swing between 13 and 35 minutes is F240.

## Part 2: the quality comparison

### How it was measured

Each phase was measured twice with master's
`scripts/code_quality.py counts --root <tree>`: on the phase's merge, and
on that merge's first parent (master just before it). Each tree was a
`git worktree add --detach` in the advisor session's scratchpad, never a
checkout here, and was removed afterwards. `git worktree list` then showed
the checkout alone.

**The same ruler for every tree.** The script reads each tree's own
`pyproject.toml`. The trees before 393 carry an older one, without
`[tool.mypy]`: `git show <commit>:pyproject.toml | shasum` gives
`9c30ea96…` at `c608169`, `f856439` and `159c430`, and `47686380…` from
`dcf5e16` on. So before measuring each tree, master's `pyproject.toml`
(`47686380…`) was written over the tree's own, and its checksum was
checked. Every tree was measured with the same script, the same settings
and the same tools. Master itself was measured in place, with `--coverage`
set to part 1's coverage JSON. Each tree took 2 to 3 seconds.

### The seven counts, before and after each phase

A single number means the count did not change. "Program code" is
`git diff --shortstat <first parent> <merge> -- src`.

| phase | built by | merge ← first parent | program code | ruff | mypy | complex | big | helpers | swallowed |
|---|---|---|---|---|---|---|---|---|---|
| 303 | the fleet | `159c430` ← `f856439` | 16 files, +1029 −41 | 1405 → 1409 (+4) | 203 → 204 (+1) | 25 | 5 | 19 | 25 |
| 348 | the fleet | `19e6e45` ← `005ed5b` | 11 files, +545 −19 | 1108 | 202 | 25 | 5 | 19 | 22 |
| 385 | the fleet | `8e5f014` ← `ddcdfd6` | none | 1108 | 202 | 25 | 5 | 19 | 22 |
| 393 | a builder | `dcf5e16` ← `159c430` | 183 files, +1166 −930 | 1409 → 1108 (−301) | 204 → 202 (−2) | 25 | 5 | 19 | 25 → 22 (−3) |
| 394 | a builder | `f856439` ← `c608169` | none | 1405 | 203 | 25 | 5 | 19 | 25 |
| 395 | a builder | `fae8378` ← `f6b6034` | none | 1108 | 202 | 25 | 5 | 19 | 22 |
| 396 | a builder | `f6f4cae` ← `230a077` | none | 1108 | 202 | 25 | 5 | 19 | 22 |

**Master now** (`ce97159`): ruff 1108, mypy 202, complex 25, big 5,
helpers 19, swallowed 22, coverage 87.75. These match every pin in
`tests/support/quality_counts.py` (1108, 202, 25, 5, 19, 22 and 87.5).

### From each phase's own documents

| phase | built by | tests added (a diff of collected ids) | planted bugs caught | Red Team | bug fixes logged | line coverage of record |
|---|---|---|---|---|---|---|
| 303 | the fleet | +141 −7 (`c079c24`) | 24/24 (`303_mutate.out`) | three rounds: six document corrections, then two; the third did not clear, and the operator moved it on (K57) | 0 | none (before the rule) |
| 348 | the fleet | +77 −0 (`fed9e47`) | 12/12 (`348_mutate.out`) | three rounds: rounds 1 and 2 documents only, cleared on round 3 (`dd5aed2`) | 0 | 87.70% |
| 385 | the fleet | +19 −0 (`f1e14b3`) | 5/5 (`385_mutate.out`) | cleared on round 1 (`46db82e`) | 0 | 87.71% |
| 393 | a builder | +115 −18 (`68aa0e2`) | 31/31 (`393_phase_log.md`) | none ("No refute pass ran") | 3 | 87.62% |
| 394 | a builder | +19 −1 (`ff3ce4a`) | 15/15 (`394_mutate.out`) | none ("No refute pass ran") | 0 | none (before the rule) |
| 395 | a builder | +62 −0 (`8f20b84`) | 35/35 (`395_mutate.out`) | none ("No refute pass ran") | 1 | 87.62% |
| 396 | a builder | +32 −0 (`c8bd296`) | 18/18 (`396_mutate.out`) | none ("No refute pass ran") | 0 | 87.71% |

Where each column comes from:
- **Tests added:** the commit named, the one that raised
  `COLLECTED_TEST_FLOOR` in that phase, by its diff of collected ids.
- **Planted bugs caught:** the last line of each
  `docs/phases/completed/<N>_mutate.out`. 393 has no `.out` file; its
  phase log says "31/31 red".
- **Red Team:** each phase log's round headings and its `## Refuter pass`
  section, and the commits named.
- **Bug fixes:** the headings naming a bug fix in each phase log.
- **Coverage:** each handoff's "Line coverage of record". 303's and 394's
  regression lines have no `--cov`: both were run before 393 added it.

### What the comparison can and cannot say

- **After 393, the counts cannot tell the fleet from a builder.**
  `tests/test_phase393_quality_ratchet.py` fails any count above its pin
  on every push. What the counts do show is that 348 added 545 lines of
  program code inside those limits.
- **385, 394, 395 and 396 changed no program code under `src/`.** Their
  work is in `.claude/skills/`, which the seven counts do not read
  (`git diff --shortstat <first parent> <merge> -- .claude/skills`: 385, 3
  files; 394, 6; 395, 19; 396, 16).
