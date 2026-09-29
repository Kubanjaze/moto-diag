# closeout — changelog

## 2026-09-28 — the edit guard (Phase 360)

The operator: "enforce the edit rule. 356 and 357 both edited source
without the Edit tool — a written rule broken twice. PreToolUse hook on
Bash that blocks sed -i, heredoc/redirect writes into src/ and tests/,
same fail-closed pattern as the push guard, with a planted positive
control per blocked form." At Step 0 the operator added: "keep perl -i,
and also block cp, mv and patch into src/ and tests/ (git mv stays
allowed), each with its own planted positive control."

`edit_guard.sh`, a thin wrapper, runs `_edit_guard.py`. It is the second
`Bash` `PreToolUse` hook in `.claude/settings.json`, with a 30 s timeout.

**Blocked:**
- `sed -i` and `perl -i` in every spelling, whatever the path;
- a write redirect, `tee`, `cp` or `mv` into `src/` or `tests/`;
- `patch` onto a file there, or with no named file inside this checkout;
- a heredoc, here-string or `-c` script whose body writes there. Python
  bodies are parsed; shell bodies are judged again as a command line.

**Fails closed**, exit 2 with a reason, on:
- a command it cannot lex;
- a write target it cannot resolve;
- any exception, and any other exit status (the wrapper turns it into 2);
- its own 5 s clock. 358 measured that a hook killed by its timeout lets
  the command run.

`tests/test_phase360_edit_guard.py` holds a positive control for each
blocked form and a negative control for each form a session needs. The
negative controls include the commit-message heredoc and every other
`git` command.

**Measured by replay.** `docs/phases/…/360_replay_guard.py 8` ran the
5,698 Bash commands in this repo's eight newest session transcripts
(2026-09-09 to 2026-09-29 UTC, this session included) through the guard:
- **552 blocked as real edits:**
  - 459 Python heredoc bodies writing `src/` or `tests/`;
  - 48 redirects;
  - 30 `sed -i` or `perl -i`;
  - 15 `tee`, `cp`, `mv`, `patch` or other bodies.

  The rule was broken hundreds of times, not twice.
- **68 blocked by failing closed** on a target it could not resolve
  (`$(mktemp -d)` backups, bodies that glob over `src/` and write an
  unresolved path): 1.2% of the commands.
- **5 blocked as malformed.** Bash itself fails on these, or warns.
- The slowest check took 6.3 ms.

Three guard defects were found by the replay and fixed before the hook
went on, each with a control:
- a mobile-repo script naming its own `src/` was blocked;
- `$'` inside double quotes was read as an ANSI-C string;
- an unquoted heredoc's `$n` was parsed as Python.

**It switched on mid-session.** Hooks edited in `settings.json` took effect
in the running session: a planted `echo planted >> tests/…` was blocked at
once, and the file was absent after.

**Known limits:**
- **A script file run by name is not opened.** The phases' mutation
  scripts write into `src/` that way, by design.
- `install`, `rsync`, `dd`, `truncate`, `ln`, `rm` and `git apply` are not
  blocked. A redirect of `git` output into `src/` is blocked like any
  other redirect.
- `subprocess` calls, `eval`, `os.chdir` and values known only at run time
  are not followed.
- Only Python and shell bodies are parsed. A `node`, `ruby` or `perl -e`
  body is blocked when it names a path in this checkout's `src/` or
  `tests/` and a file write.
- Only this checkout is protected. A path inside another repository's
  `src/` is that repository's.
- A glob or a value substituted after the fixed leading directory is
  judged by that directory alone.

Recovery, if it ever blocks every Bash call: edit `.claude/settings.json`
with the Write tool, which does not pass through the `Bash` matcher.

## 2026-09-28 — wholetree.sh --full gains the ledger class (Phase 357, F175)

The operator: "Fix the rule so the class of test 244Z belongs to joins by
rule, not by name." 244Z pins MODULE_ISLANDS and enumerates nothing, so it
was in neither mode (fast 31, full 80), and only the full regression
reached it (356 bug fix #1).
- **The rule:** a `ledger` test imports a `tests/support` module whose
  body is only a docstring, imports and assignments, where a code-class
  member imports that module too. Full mode only.
- **Members now:** 244Y and 244Z; full 82 with the rule alone. Fast mode's
  members do not change. Phase 357's own ledger test imports `wholetree`,
  so 358's rule puts it in fast mode (fast 32, full 83).
- **Controls:** `tests/test_phase357_wholetree_ledger.py`, with a fixture
  tree for the rule and both exclusions. A planted failure in 244Z turned
  `--full` red. `357_mutate.py F175`: 4/4 red.

## 2026-09-27 — A5 judges the last regression line (Phase 359, bug fix #1)

358's A5 took the first line that parsed. After a re-run, that is the
superseded run: 358 recorded 9636 at `8a205ee`, then 9639 at `d93d8de`
after its bug fix #2 (`docs/handoffs/2026-09-27_358_closed.md`, "What is
open"). `regression_line` now reads the last line carrying "Regression of
record:" and parses that one. The rule is unchanged.
- Fixtures: `k6_k7/a5_bad_last_line_superseded.md` (the first line parses,
  the last does not: must fail) and `k6_k7/a5_good_last_line.md` (the last
  parses: passes with the last run's count and hash).
- `tests/test_phase359_a5_last_line.py`: 3 of its 4 tests went red on the
  old A5, including the `check()` wiring test.
- 358's two exemption controls still recompute to 10 and 40.

## 2026-09-27 — A5 parses the regression line, and A8 asks for the refute checklist (Phase 358, K6 and K7)

The operator: "K6 and K7 are closeout checks, not prose. K6: the regression
line must parse to command + hash + count. K7: a log mentioning refute
without a refute checklist fails. each has a known-bad fixture."

- **A5** now needs the line as `regression.sh` prints it: "Regression of
  record: N passed … at \`HASH\` (…, \`… pytest …\`, …)". Ten closes passed
  the old A5 with no command (255B, 255C, 255D, 257B, 257, 258, 259, 260,
  353, 354). They are `A5_COMMAND_EXEMPT` and keep the old rule.
- **A8** is new. A log that mentions refute must carry the `## Refuter
  pass` checklist, which must pass `refute_check`, or one line opening
  "No refute pass ran". The forty closed logs that fail it are
  `A8_REFUTE_EXEMPT`. They include the three known prose refutes: 255B,
  258, and 259, whose refute ran under a heading and left no checklist.
- **Both exemptions are pinned lists** (the operator: "not a cutoff").
  `tests/test_phase358_closeout_k6_k7.py` recomputes each set from the 312
  closed logs and requires equality.
- **Mutations.** Dropping the command from A5 inside `check()` first
  **survived**, because no test ran `check()` on a log with a hash and a
  count but no command. That test was added, and the mutation went red.
  Accepting any "no refute" sentence went red on four tests.
- **Fixture changes.** The good ZZZ log and both A7 fixtures now print the
  `regression.sh` line. The bad ZZZ log gained a prose refute for A8.
- verify_phase checks 12 and 14 still print what they did. A5 and A8 now
  enforce what they only showed.

## 2026-09-27 — R7: a folded row must fold into a closed phase (Phase 358, K5)

Track N closed eleven rows through three batch phases. The eight rows that
did not carry a batch read "✅ | Folded into NNN", with no date and no
documents, and nothing checked them. A fold into a number with no row, or
into a phase that never closed, passed. R7 fails those.

- **Only notes that open with "Folded into NNN" count as a fold.** The good
  tree holds a ✅ row whose prose says "folded into 258" (an open phase),
  and R7 must pass it.
- **Two mutations were each seen red:** ignoring the CLOSED date, and
  reading "folded into" anywhere in the notes. The second survived at
  first, because the prose row pointed at a closed phase; the control was
  strengthened.
- **The real ledger's eight folds pass.** With 261 set back to 🚧, R7 names
  exactly 269, 270 and 271.

## 2026-09-27 — one whole-tree command, and a push guard that fails closed (Phase 358, K1)

Rule 3 listed four checks by hand, the GLM prompt thirteen, and five red
regressions in 257–260 came from checks neither list ran. `wholetree.sh`
finds its members by rule on every run (a test that enumerates a repo
directory, or loads a helper that does) and runs them in two modes: fast
(the code-and-ledger class minus gates and the wheel build, plus
finding_check over both folders; 27 files, about 30 s) and `--full`
(every member; 74 files, about 6.5 min).

- The push guard runs fast mode on every push unless a record shows it
  passed on exactly the commit, tree and script being pushed. Records are
  signed with a key only the command creates. With no record, the guard
  runs fast mode itself on the checked-out clean commit, under its own
  limit (`FAST_LIMIT_S`: first 96 s from a battery run, then 285 s,
  3× the AC time of 94.9 s), and blocks on a failure or a timeout.
- The hook timeout went from 120 s to 600 s. A `PreToolUse` hook that
  outruns its timeout is killed and the command proceeds (measured, and
  documented by Claude Code), so the guard keeps its own clock far inside.
- A commit that changes seed data or `migrations.py` needs a `--full`
  record for the tree it commits. `regression.sh` needs one for HEAD.
- `git -C path push` was invisible to the guard; it is now seen.
- Controls, each in 358's phase log: the four 257–260 plants red in fast
  mode; a plant in an excluded file passes fast and fails `--full`; an
  amended commit, a hand-written record and a check sleeping past the
  limit are each refused at the push.

## 2026-09-25 — the regression of record runs in parallel (Phase 355)

Step 1 ran the full suite serially: 30 to 55 minutes on this Mac, at least
once per phase. It now runs `regression.sh`: `python -m pytest -n auto
--dist load` on a clean tree, under `caffeinate` because pytest's clock
stops while the Mac sleeps. The script prints the line the phase log
records, with the counts, the hash, the wall time and the command.
`regression.sh --serial` (`-p no:xdist`) is the documented fallback.

- `verify_phase.sh` check 10 runs its targeted tests with the same flags.
  The new check 14 shows whether the phase log's regression line names
  its command. It prints and enforces nothing. A5 is unchanged, because
  requiring the command there would change an artefact's definition.
- Every test that spawns pytest passes `-p no:xdist`, and
  `test_phase355_parallel_suite.py` fails when one does not. It also fails
  when `addopts` gains a worker count: each spawned gate run would inherit
  it and start a worker pool inside a worker.

Proven: the parallel run's passed IDs equal the serial run's (junit diff),
a planted failing test is reported by a two-worker run, and the `addopts`
guard went red on a planted `-n auto`. The phase log has the rest.

## 2026-09-24 — R6: every close-out leaves its handoff; the handoff is a step

Closing a phase never required a handoff. 353 and 354 each wrote one, and
257 and 257B wrote none, so the next session's "newest handoff" depended on
the builder remembering to write it. R6 in `roadmap_check.py` requires
`docs/handoffs/YYYY-MM-DD_<phase>_closed.md`, dated no earlier than the
close, for every phase closed since 2026-09-24. 257 and 257B are exempt by
name, because they closed that day before the rule existed.

**Per phase, because the date rule was measured first.** The rule as
proposed compared only the newest handoff's date with the newest close. The
real ledger has four closes and two handoffs on one date, so that rule passes
it with 353's handoff deleted. R6 also reads `implementation.md`'s history
row, which A7 requires, so a ✅ row written without its CLOSED date is still
a close.

**The sequence changed with it.** The guard runs R6 on every push, so the
handoff is step 7, written before the merge (353 and 354 wrote theirs after
the deploy). Step 8 now warns that `git merge -F -` does nothing: it exits
129 ("could not read file '-'", checked on git 2.54), and it happened twice
on 2026-09-24.

Proven:
- R6 fires on exactly the five planted cases in `fixtures/roadmap_bad`: no
  handoff, only a mid-phase handoff, a handoff dated before the close, a
  second close on the same day, and a close seen only through the history
  row. It does not fire on the same day's close that has its handoff.
- `fixtures/roadmap_good` holds 257 as the exemption's control.
- Five deliberate breaks each turned `tests/test_roadmap_continuity.py` red
  (22 tests), and all five were reverted.

## 2026-09-24 — A7: the newest phase is the row with the latest Date (F148)

A7 took the first bold row of `implementation.md`'s history table as the
newest phase. The table is not in date order: its first row is 244M
(2026-09-10), and 257B (2026-09-24) sits near the bottom. So the
version-header half of A7 ran only for 244M. A close-out that forgot the
version bump passed it, and 244M itself carried a false A7 failure, because
the header correctly names 257B.

**Measured first:** all 112 bold history rows carry one bold ISO date in
their third cell, so the Date is a total key except for same-day closes.
257 and 257B both closed on 2026-09-24. Their rows were first committed in
`b8382b5` (00:07) and `f3ef2fb` (13:17), so a tie goes to the row committed
later (`git log -S` on its `| **phase** |` prefix, the way A4's
`recorded_at` dates a heading), then to table position. A row not yet
committed counts as later than any committed row.

Proven: `fixtures/a7_newest_bad` puts 244M first and a ZZZ row, dated later,
under a stale header. Master's A7 returned `[]` on it. The fix returns
exactly the A7 header failure, and `fixtures/a7_newest_good` (header bumped)
passes. Of the five new tests, four failed on master's check. Changing the
tie-break to table order turned the reversed-order tie test red, and it was
reverted. On the real repo the newest phase is now 257B, and 244M no longer
fails A7. Its A5 and A6 failures come from older phases and are unchanged.
Commit `bac634d`. Close-out tooling; not a phase.

## 2026-09-24 — roadmap_check.py: the ROADMAP ledger holds, on every suite and every push

The phase after 257 was about to start with no ROADMAP row, and looking for
its place found a reused number (two rows read 256) and a row (353) outside
every range of the authority contract. The close-out checked a phase's row
only at the end, and only that it existed. Nothing checked the ledger while
work ran, or checked it against `docs/phases/` at all.

**Measured before it was written:** the rules were run over the real ledger
first. 371 rows, 370 numbers: the duplicate was 256. Of 298 phases with
documents, 27 had no backend row, and all 27 were Track I, whose rows the
contract puts in the mobile ROADMAP (all 27 are there), so R2 looks them up
there instead of exempting them. One phase has documents in `completed/`
and a ⏸️ row: 245, Damon, whose record was archived when it paused. So R3
accepts ⏸️ as well as ✅, and the good fixture carries a paused phase as that
exclusion's control.

**The guard now covers every push, not just `master`.** The narrowing below
(2026-09-22) was right for close-out, which cannot be complete mid-phase.
Continuity can always be true mid-phase, because a phase's row exists before
its Step 0. So a work-in-progress push is refused only when the ledger lies,
and the fix is one edit to the row.

Proven: on `master`'s ROADMAP before this change, the check reports exactly
R1 (256) and R4 (353). Each rule fires on `fixtures/roadmap_bad`, and
`fixtures/roadmap_good` passes. Breaking R1 (`c > 1` → `c > 9`), or the guard's
refusal (`return 2` → `return 0`), turned `tests/test_roadmap_continuity.py`
red, and both were reverted.

## 2026-09-22 — A4: a heading may not be dated after it was recorded (Phase 255D fix #9)

The operator asked for A4 to compare each bug-fix heading's time with its
fix commit. **Measured first: that rule fails 11 of 13 honest entries** in
255C and 255D, because a heading records when the *entry* was written —
often in a close-out batch an hour after the fix. It would have rewritten
the meaning of every heading to make the check pass.

What no honest entry does is carry a time **later than the commit that wrote
it**. That is the rule: the heading's time must not exceed the author time
of the first commit containing that heading line, plus five minutes; an
uncommitted heading is judged against now. It fires on exactly 255C #7
(18:05, written 16:25), 255D #5/#6 as first written (21:40/21:55, written
20:17/20:18), and the invented 22:40/22:55 of #7/#8 (written 20:39) — and on
nothing else. The historical headings are the positive control; git history
cannot drift.

## 2026-09-22 — check 2 sees `.claude/` (Phase 255D fix #8, F137)

`verify_phase.sh` check 2 was `git diff -- src/ tests/`. Fixes #5 and #6
changed two skill scripts after the closing regression and check 2 said
"docs only". The scope now lives in `code_after_regression.py` — one
implementation, called by the script and the test — and is inverted: a path
is code unless it is positively documentation. The positive control is the
real `b0ae748..3dfc78a` range, which cannot drift.

## 2026-09-22 — A4 resolves the commit, not the word (Phase 255D fix #7)

**A4 passed on a non-answer.** It looked only for the words `**Commit.**`,
so `This one.` (255D fixes #5 and #6) and `See the close-out commit for this
fix.` (255C fix #7) both satisfied it. The operator's `/closeout` read caught
it; the check did not.

A4 now takes the backticked hash on the Commit line and requires
`git cat-file -e <hash>^{commit}` to succeed. A line with no hash fails as a
non-answer; a well-formed hash that is not a commit fails as unresolved. A
trailing `(name)` resolves in the sibling checkout `name` —
`e536740` (workspace-docs) is real and lives there — and a sibling that is
not checked out is **reported, not skipped**.

The known-bad fixture plants both new defects (#1 `This one.`, #4
`aaaaaaa`); the known-good fixture now cites two real 255C commits, because a
fabricated hash can no longer pass. Break-it: with resolution neutered, three
tests fail.

**Scope, stated so it is not mistaken for a regression:** fifteen phases
from 141 to 255 already failed A4 on *no Commit line at all* — they predate
the register format. That is unchanged. The only phase this change newly
fails is 255D, for the two lines it was written to catch.

## 2026-09-22 — created (Phase 255D)

First procedure folder. Replaces close-out instructions that were spread
across four CLAUDE.md sections — `Phase build workflow`, `Phase completion
gate`, `implementation.md versioning rules` and `Deploy backups` — plus a
counting rule that had three different implementations at once.

**Built in this order, deliberately:** the check, then a real phase run
through it, then the fixtures, then the test, then the hook. Running the
check against **255C** — a phase closed the same day — found **two genuine
gaps** (no Deviations section, no regression line carrying both a hash and a
count) and **one bug in the check itself**. That is the order that finds
things; writing the fixtures first would have tested the fixtures.

**The check's own first bug, recorded because it is the point.** A4 used one
`re.findall` with `re.S`, so a non-greedy `.*?` ran across a newline and
matched a later heading's number from an earlier heading's line. It reported
`#5` twice against a log whose headings were a clean `#1..#7`. **The check
was wrong, not the log** — the same DOTALL-across-a-line-boundary defect
that ate a guard in Phase 255B. Heading detection is line-anchored now.

**The guard is narrower than "any push", on purpose.** It engages only on a
push that puts commits on `master`. A phase branch is pushed many times
while the phase is open; that is normal, not a skipped close-out. A guard
that blocked every push would block every work-in-progress push for the
whole phase, and the only way to work would be to turn it off — worse than
having no guard.

**Two operational facts learned the hard way in D1**, repeated here because
this is where the next person changing the hook will be reading:

* **Config loads with roughly one turn of delay.** A guard verified in the
  turn that installed it will look like it does not work, and the natural
  next move — assume the config is wrong and change it — makes things worse.
* **`PreToolUse` ignores the hook's `if` field in this build**, while
  `PostToolUse` honours it. Measured with non-blocking marker hooks: same
  field, same value, same matcher, opposite behaviour. **Do not add `if` back
  to this hook.** The guard filters itself from `tool_input.command`, which
  is correct either way.
