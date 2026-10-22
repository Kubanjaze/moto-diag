# Phase 387 — The XO and the Yeoman — phase log

**Status:** ✅ Complete (2026-10-22)
**Branch:** `phase-387-xo-yeoman` (Opus session on the Mac, the only writer)

---

### 2026-10-22 — Opened, and Step 0

The prompt is `docs/prompts/387_xo_and_yeoman.txt`, saved verbatim. 385
has a committed prompt and no row, and 386 is closed, so the next free
number is 387.

- `ce59e68`: row 387 as 🚧 (60 words by `roadmap_words.py`;
  `roadmap_check.py` ok) and the prompt.
- `wholetree.sh` before it, run on its own: exit 0, 1794 passed.

Read first: `docs/handoffs/2026-10-22_386_closed.md` (the newest, by
`git log -1 --name-only --format= -- docs/handoffs/`); rows 382–386;
`ROADMAP_AUTHORITY.md`; the fleet proposal; `386_implementation.md`,
`386_step0.md`; `docs/decisions.md`. Open findings that touch this phase:
F213 (B2 reads only phase documents; the proposal applies B2's habit to
K-ids, which `decide` does for its own line) and F214 (the fleet's own
GitHub identity and the ruleset, later; this phase uses the operator's
login as the prompt says).

**A guard blocked a command.** A shell loop probing six model ids wrote
each answer with `> $m.json`; the edit guard refused it: "the edit guard
cannot tell where the redirect `>` `$m.json` writes (a variable,
substitution, glob or unknown directory), and blocks what it cannot
resolve. Use a literal path." The probes moved into a scratchpad script,
`probe_models.py`, that writes its own files; the guard is unchanged.

Step 0 is `387_step0.md`. In short: Fable is reachable (`claude-fable-5-1`
served), so the XO runs on Fable. The XO's flags leave the session with
only Glob, Grep and Read, and a planted Bash call made nothing; the
control with Bash allowed made the file. `gh` is the operator's admin
login and none of the eleven labels exists. One XO call on 386's v1.0
read about 148K tokens and wrote 7,347, $1.22 at list price, and returned
its verdict through `--json-schema`. The checklist as written fails both
plans the prompt names as known-good: a real fork, put to the operator.

### 2026-10-22 — The operator's answer, and v1.0

The fork in `387_step0.md` was put to the operator in plain words: the
checker asks three things 384 and 386 never did (a classification line;
the three newest change-log entries and their checks; the stops it
expects), so how should it treat those two plans? The options were "Pin
them (Recommended)" and "No pin, they fail". The operator's answer,
verbatim: **"Pin them (Recommended)"**.

So `plan_check.py` carries a pinned list of the two plans written before
it, with the items each predates (384: classification, change log, stops;
386: change log, stops), held to equality by a test. Every plan from 387
on faces every item.

Decided without asking, each in v1.0 with its reason:
- `decide` uses no model: the words are the operator's, verbatim.
- `digest` reads this repository's `FOLLOWUPS.md` only (mobile's headings
  do not mark closure; S0-7).
- A failed checklist is a back-to-captain round, with no model call.
- The XO's rounds are counted from its own comments on the mission issue,
  so the state lives on GitHub, where the label is.

`ea6fed8`: v1.0, pushed before any code. **A guard blocked a command:** the
first try put `git commit` and `git push` in one command; the push guard
refused it ("it would push a commit it never saw"), and neither ran. They
were run separately. The same block happened once more, at the mutation
commit, the same way. Both are my error; the guard is unchanged.

### 2026-10-22 — The build

| item | commit |
|---|---|
| `plan_check.py`, the good tree and 21 known-bad cases, the contract test (50 tests then) | `8c9f5fd` |
| `rank_call.py` and `xo.py`, 18 tests | `dc7290f` |
| `yeoman.py`, `labels.py`, their tests; the eleven labels made | `acdd1bd` |
| K40 and K41 in `docs/decisions.md`, by `yeoman.py decide` | `9726ac7` |
| `SKILL.md`, `CHANGELOG.md`, `fence_probe.py` | `0e1f302` |
| the mutation run | `c9620ca` |
| bug fix #1, F215 | `187da51` |
| bug fix #2, the day's digest | `6e42473` |
| `COLLECTED_TEST_FLOOR` 11001 → 11093 | `ec8b669` |

`wholetree.sh` was run on its own before every commit and its exit code
read: 0 each time (1794, then 1844 to 1846 passed in fast mode, as the new
contract test joined it by the suite's own rule).

**The count rule, tightened and measured** (v1.0's promise). Over the 34
step-0 reports in `completed/`, the prototype flagged 32, 198 blocks; the
shipped rule flags 32, 197 blocks
(`python3 -c '…plan_check.unshown_counts(…)'` over
`docs/phases/completed/*step0*.md`). Two tightenings came from this
phase's own report: a preposition, article or verb between a number and
its noun ("384 on three items" names a phase), and a table's lead may be
the bullet before it (the good fixture caught that). Most remaining hits
are real (a live count with its source named and no query); the rule is
strict on purpose, and a hit costs a round, never a wrong approval.

**The labels.** `labels.py --check` first: 9 labels, all 11 missing. Then
`labels.py`: 11 made, 20 labels after. Run again: all 11 "reused", none
made, nothing forced: pre-approval (b)'s path, proven.

**The mutation run** (`387_mutate.py`, output `387_mutate.out`): 52/52 red
at the end (50 at first; X14 and Y11 came with the bug fixes, and X7's
text moved with bug fix #1). One test case was added before the first run,
so the rule that a number naming a phase is not a count had a test of its
own.

### 2026-10-22 — The proofs

**1. `plan_check` on 384's and 386's v1.0, at their commits** (the operator's
pick, K41):
- `plan_check.py 384 --rev b6ffcb6` → PASS; P4, P7 and P8 skipped as
  "written before plan_check (pinned)", each naming what it would have
  failed: no classification line; the change-log entries 2026-10-19 and
  2026-10-07 not cited and 2026-10-20 cited without its check; no stop
  section.
- `plan_check.py 386 --rev 5d0a687` → PASS; P7 and P8 skipped the same way.
- `--no-pin`: 384 FAIL (P4, P7, P8), 386 FAIL (P7, P8): exactly the pin.
- `plan_check.py 387` (v1.0, `ea6fed8`) → PASS with nothing skipped and
  nothing pinned: the positive control for P4, P7 and P8 on a real plan.

**2. The known-bad cases:** `plan_check.py --self-test` → the good tree
passes; each of the 21 cases fails on its own item and no other: P1 ×2,
P2, P3 ×2, P4 ×2, P5 ×5, P6 ×3, P7 ×3, P8 ×3. Every item fails by name.

**3. A planted Bash call refused** (`fence_probe.py`, Haiku, the ranks' own
`FENCE`). First run, before bug fix #1: fenced, offered `Glob`, `Grep`,
`Read`; the model tried `Bash` and no file was made; the control (Bash
allowed) made its file. After bug fix #1: the same, and the read case: a
canary under `~/.config` denied to Read, Grep and Glob, never reaching
the session; a repository file read. Exit 0 both times: "fence holds".

**4. One real `xo.py` run on this plan.** The mission issue is
[#9](https://github.com/Kubanjaze/moto-diag/issues/9), opened with
`mission` and `plan:needs-review`. The plan and step-0 report unchanged
since `ea6fed8` (`git diff --quiet ea6fed8 -- …`). `xo.py review 387
--issue 9` → exit 0, verdict **approve**, label **`plan:approved`** set and
`plan:needs-review` removed; the issue's labels after: `mission`,
`plan:approved`. The call: `claude-fable-5-1`, session
`87db23c8-0661-4c48-b4a2-a93e397ce84b`, input 162, cache write 38,802,
cache read 203,234, output 7,699, 20 turns, 99 s, $1.21 at list price.
Its reason ends with an observation it called non-blocking: "the XO and
the Haiku digest have Read on the whole filesystem, and their text lands
in a public repository (issue comments, docs/fleet/digests/); the fence
proves no writes, not read scope". Measured and taken as bug fix #1.

**5. One `yeoman.py digest`**, `docs/fleet/digests/2026-10-22.md`. The first
run's summary said "Phase 386 closed on 2022-10-22": bug fix #2. The
second run under the fix set its summary aside for "23" (the day of
2026-10-23, written as "October 23"), a false hit fixed the same commit.
The third, committed: summary kept, 131 words (over the 120 asked; the
page says so), session `e2da5fa0-29ee-46a2-b3e1-8125f184a6a3`, 2 turns,
9 s. One limit the token check cannot see: the summary says "41 broken
pointers" where the facts say 41 pointers, which were missing. Wording is
the model's, under its own heading, above the script's facts.

### Bug fix #1 — 2026-10-22 — the read-only ranks could read the login token

- **Issue:** the XO's first real verdict observed that the fence proves no
  writes, not read scope. A rank's text lands in a public issue comment or
  digest, and the operator's login token is in
  `~/.config/motodiag/anthropic.env`.
- **Root cause:** Read, Grep and Glob need no permission, so `dontAsk` never
  sees them; `--allowedTools` and `--tools` decide whether they exist, not
  where they reach. Measured with a canary outside the repository: read
  and quoted under the shipped flags, and with the allow rule dropped.
- **Fix:** `rank_call.SECRET_HOMES` (`~/.config`, `~/.ssh`, `~/.claude`,
  `~/.claude.json`, `~/.subconscious`, `~/.aws`, `~/.gnupg`, `~/.docker`,
  `~/.netrc`, `~/.npmrc`, `~/.pypirc`, `~/Library`, the shell histories)
  denied to Read, Grep and Glob in `--disallowedTools`. A denylist: F215
  carries the confinement to the fence phase.
- **Files:** `.claude/skills/fleet/rank_call.py`, `fence_probe.py`,
  `tests/test_phase387_xo.py`, `387_mutate.py` (X7 moved, X14),
  `docs/FOLLOWUPS.md` (F215).
- **Verified:** `fence_probe.py`'s read case: the canary under `~/.config`
  denied to all three tools and absent from the session, a repository file
  read; the fence test asserts each tool and home is denied; X14 red.

**Commit.** `187da51`

### Bug fix #2 — 2026-10-22 — the digest published a date the model invented

- **Issue:** the first real digest's summary said "Phase 386 closed on
  2022-10-22"; the facts below it said 2026-10-22. The script wrote it
  unchecked.
- **Root cause:** `digest` checked the call (model, usage, an answer) but
  not the answer against the facts it was given.
- **Fix:** `yeoman.unsupported`: every date, F- or K-id and number of two
  digits or more in the summary must be in the facts (a bare number may be
  any digit run there); otherwise the summary is set aside on the page,
  naming what it invented, and the facts still go out.
- **Files:** `.claude/skills/fleet/yeoman.py`, `tests/test_phase387_yeoman.py`,
  `387_mutate.py` (Y11), `docs/fleet/digests/2026-10-22.md`.
- **Verified:** a summary with 2022-10-22 and K9 is set aside naming both;
  one restating the facts is kept; Y11 red; the real digest rerun.

**Commit.** `6e42473`

Two bug fixes, both one shape: a model's output trusted further than it
was checked (what it may read, what it may say). A third would have
stopped the build for a shared cause.

No refute pass ran.

### 2026-10-22 — The regression of record, and close-out

`wholetree.sh --full` on `c64e055`: exit 0, 4318 passed, 104 files.

Regression of record: 11092 passed, 0 failed, 1 skipped, 0 errors at `c64e055` (20 min 44 s wall, `python -m pytest -n auto --dist load`, exit 0)
Skipped in the regression of record: [1] tests/test_phase244H_test_db_isolation.py:79: no production database on this machine

The collected count, 11093, equals the floor. Everything after `c64e055`
is documents: v1.1, the handoff, row 387, `implementation.md`'s history
row, and the root `phase_log.md`'s pointers for 386 (which its own
close-out did not add) and 387.

**A guard blocked a command.** Filling the regression line into the two
drafts with a short Python script was refused by the edit guard: "a Python
script body writes to a path the edit guard cannot resolve, and the body
names src/ or tests/". The line names a test file. The drafts were edited
with the Edit tool; the guard is unchanged.

K11: the operator has not confirmed the Subconscious lapse to this phase,
so it is not logged as done; carried in the handoff.

No migration: nothing goes live.
