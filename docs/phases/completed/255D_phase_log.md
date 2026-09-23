# Phase 255D — Procedures as folders — phase log

**Status:** ✅ Complete
**Opened:** 2026-09-22

---

### 2026-09-22 19:00 — D1: the mechanism proof. One half passes, one half fails, and a third thing is broken

v1.0's D1 said: run the mechanism before writing anything that matters, and
**if either half fails, stop and re-plan.** One half failed. This is the
stop.

## Result 1 — the skill is NOT discoverable. **FAIL.**

`.claude/skills/ping/SKILL.md` was created, containing a single sentinel
`PING-255D-SENTINEL-8f3a2c`. Invoking it returned:

```
Unknown skill: ping
```

**Two locations were tried, because the first failure had an obvious
alternative explanation.** The session's transcript directory is
`~/.claude/projects/-Users-lilquant-Projects/`, which encodes the session
root as `/Users/lilquant/Projects` — the **parent** of the repository, not
`moto-diag`. So the skill was placed a second time at
`/Users/lilquant/Projects/.claude/skills/ping/SKILL.md`. **Same result.**

**Conclusion:** skills are enumerated when the session starts. A skill
created during a session is not invocable in that session. This is not a
path error — it reproduces at both candidate roots.

**Not yet distinguished, and the operator can settle it in one step:**
whether a restart makes `ping` invocable. The file is committed and left in
place for exactly that test.

**Second finding, independent of the reload question, and it matters more
for the plan.** If the project root for `.claude/` discovery is the
directory a session is *started in*, then a skill committed to
`moto-diag/.claude/skills/` is invisible to any session started at
`/Users/lilquant/Projects` — which is how this session was started, and
therefore plausibly the normal case. **That would make "versioned folders in
the repo" unreachable by the mechanism that is supposed to read them.** v1.0
assumed the repository was the root. It did not verify it, and Step 0 did
not either.

## Result 2 — the PreToolUse hook DOES block. **PASS.**

`.claude/settings.json` was given a `PreToolUse` hook on `Bash` running a
script that writes to stderr and exits 2. It fired, and the block came back
as the tool error:

```
PreToolUse:Bash hook error: [.../pre_push_guard_test.sh]:
BLOCKED-255D-HOOK-4d1e9b: closeout has not been verified for this phase.
```

So the enforcement half of D2.6 is real: **exit 2 blocks, and stderr reaches
the model.** That is the mechanism the push guard depends on, and it works.

**Two qualifications, both learned the hard way.**

*Config is picked up with roughly a one-turn delay.* The first `git push`
after writing `settings.json` was **not** blocked; the hook fired on the
following turn. A guard written and immediately tested in the same turn will
look like it does not work.

*A blocking hook on `Bash` locks out `Bash`, including the command that
would remove it.* That is how the block was discovered: it fired on a `cat`,
not a push. Recovery was via the `Write` tool, which does not pass through a
`Bash` matcher. **Worth knowing before a guard is installed for real.**

## Result 3 — `if` is honoured on PostToolUse and IGNORED on PreToolUse. **BROKEN as v1.0 specified.**

This is why the blocking hook fired on a `cat`. Isolated with non-blocking
marker hooks so nothing could lock out again:

| hook | `if` | non-push command | result |
|---|---|---|---|
| `PostToolUse` on `Bash` | `Bash(git push *)` | ran | marker **absent** — filtered correctly |
| `PreToolUse` on `Bash` | `Bash(git push *)` | ran twice | marker grew **1 → 2** — fired both times |

**`PreToolUse` ignores `if` in this build.** v1.0's D2.6 specifies exactly
that combination, so **the push guard as planned would block every Bash
command in the session.** It did, to me, for one turn.

**The fix, for the re-plan:** the guard must filter itself. The hook receives
the tool call as JSON on stdin, so `pre_push_guard.sh` reads
`tool_input.command`, exits 0 immediately unless it is a `git push`, and only
then runs the closeout test. That is correct whether or not `if` is honoured,
and it does not depend on a field whose behaviour differs by event.

## What this changes

v1.0's enforcement design survives: **a test plus a PreToolUse guard that
exits 2** is buildable and was demonstrated. What does not survive is
(a) the assumption that a skill can be added and used without a restart,
and, more seriously, (b) the assumption that `moto-diag/.claude/skills/` is
the directory the mechanism reads.

**Halted for re-planning rather than continuing, per v1.0 D1 and the
operator's instruction.** Building `closeout` now would mean writing a skill
that cannot be invoked into a directory that may not be read, and enforcing
it with a hook configured in a way that blocks every command.

**Nothing was left behind.** The test hook, its guard script and the
session-root copy of the skill were removed;
`moto-diag/.claude/skills/ping/SKILL.md` is committed and kept, because it
is the fixture for the restart test.

### 2026-09-22 20:10 — Bug fix #1: the closeout check's own A4 matched across a line boundary

**Issue.** Run against Phase 255C, `closeout_check.py` reported the bug-fix
register as `[1, 2, 3, 4, 5, 5, 6, 7]` — a duplicate `#5` — against a log
whose headings are a clean `#1`–`#7`.

**Root cause.** A single `re.findall` with `re.S`, so the non-greedy `.*?`
before `Bug fix #` ran **across a newline** and matched a later heading's
number from an earlier heading's line. **The check was wrong, not the log.**
Same DOTALL-across-a-line-boundary defect that deleted a guard in 255B.

**Fix.** Heading detection is line-anchored: collect heading line indices
first, then take each entry's body between consecutive headings.

**Files.** `.claude/skills/closeout/closeout_check.py`.

**Verified.** 255C's register reads `#1`–`#7`, contiguous, every entry
carrying its commit. The known-bad fixture still reports `[1, 3]`.

**Commit.** `1b82ace`.

### 2026-09-22 20:10 — Bug fix #2: finding's B2 read one of the two F-number files

**Issue.** 98 dangling F-number citations on the first run against the real
repository.

**Root cause.** F-numbers are **one global sequence across both
repositories**, and the check resolved citations against moto-diag's
`FOLLOWUPS.md` alone, so every mobile finding read as missing.

**Fix.** Citations resolve against the union of both files.

**Files.** `.claude/skills/finding/finding_check.py`.

**Verified.** 98 → 9. The denominator was wrong, not the repository, which
is why the first move was to check the denominator rather than weaken the
assertion.

**Commit.** `1bb3c3e`.

### 2026-09-22 20:10 — Bug fix #3: the exclusion rule removed the one case it exists to catch

**Issue.** Four of the nine remaining citations were not findings at all —
`F650`, `F700`, `F750` are **BMW motorcycles**, `F401` is a **flake8 code**
in a `# noqa:` comment, and `F48` is a **phase** whose documents cite their
own name. A bare `F` plus digits is a model designation in this corpus at
least as often as a finding.

**Root cause of the FIX, which is the actual bug.** The first exclusion rule
was a **ceiling**: ignore any citation above the highest assigned number. It
removed all four false positives — and also skipped a citation of `F139` in
a file that stops at `F138`, which is **exactly the failure the check exists
to catch**. F135's shape is a phase citing a number that was never created,
and that number is almost always one past the end.

**Fix.** Named exclusions with a reason each (`NOT_FINDINGS`), plus a pinned
`KNOWN_DANGLING` set for four historical citations. A named list cannot hide
a citation one past the end.

**Files.** `.claude/skills/finding/finding_check.py`;
`fixtures/bad` cites `F139` deliberately.

**Verified.** Real repository clean; the fixture's `F139` is caught; a test
pins that the motorcycles are excluded **by name** and not by a ceiling.

**Commit.** `1bb3c3e`.

### 2026-09-22 20:10 — Bug fix #4: a push of three files the repo silently did not take

**Issue.** The workspace `CLAUDE.md` was pushed pointing at `claude/cos.md`,
`claude/drug-discovery.md` and `claude/coding-standards-jvm-and-node.md` —
**none of which were in the repository.**

**Root cause.** `workspace-docs/.gitignore` is an **allowlist** beginning
with `/*`. `git add -A` added nothing and reported nothing; the commit
succeeded and the push succeeded.

**Fix.** `!/claude/` added to the allowlist; the three files committed.

**Files.** `workspace-docs/.gitignore`.

**Verified.** All three are tracked and pushed.

**Note, because it is the point.** This is the **dangling-pointer failure
this phase built `finding` to catch** — committed by the phase that built
it, ten minutes later, in the other repository where the check does not run.
Caught by reading `git status` output rather than trusting that `add -A` had
done something.

**Commit.** `e536740` (workspace-docs).

### 2026-09-22 21:05 — Closing regression and final state

**Regression 8,130 passed / 0 failed / 0 skipped / 49:50 at `b0ae748`.**
`COLLECTED_TEST_FLOOR` 8,091 → 8,130 (+39: 23 closeout, 9 finding, 7
refute). Three procedure folders, each with a hand-written known-bad fixture
its assertion is required to fail on, a dated changelog in its own folder,
and a script for the parts that are "run this and check that".

No schema change, no migration, no database touched — this phase is process
files and tests only.

### 2026-09-22 21:40 — Bug fix #5: B2 could not tell describing a number from citing one

**Issue.** `verify_phase.sh` run against **255D itself** failed check 13:
three dangling F-numbers — F138, F139, F140 — cited by 255D's own
documents.

**Root cause.** Those documents *describe* the `finding` known-bad fixture,
and that fixture uses fabricated numbers. **Prose about an identifier is
indistinguishable from a citation of it** under a bare `\bF\d+\b` scan.

**Root cause of the first FIX, which is the interesting part.** The obvious
repair was to pin 138–140 in `KNOWN_DANGLING`. It made check 13 pass — and
**broke the control**, because F139 is the fixture's deliberate
one-past-the-end case. A global pin made the known-bad fixture pass and the
assertion meaningless. **That is the ceiling bug again, in the fix for a
different bug**, twice in one phase.

**Fix.** `DESCRIBED_NOT_CITED` holds `(number, document)` pairs, so the
exclusion is scoped to the documents that merely describe the numbers. The
fixture still catches F139 where it matters.

**Files.** `.claude/skills/finding/finding_check.py`.

**Verified.** Real repository clean; all 9 finding tests green, including
`test_b2_names_the_citation_one_past_the_end`, which is the one the global
pin had silently disabled.

**Commit.** `7b578af`.

**The lesson, since it is now three for three.** Every exclusion rule
written in this phase removed a true positive along with the false ones:
the ceiling, the global pin, and nearly the sub-brand narrowing in 255C.
**An exclusion is a claim that something cannot be the thing you are looking
for, and it needs a control like any other claim.**

### 2026-09-22 21:55 — Bug fix #6: A7 could only ever be satisfied by the newest phase

**Issue.** `verify_phase.sh`'s check 10 failed for 255D:
`test_a_closed_phase_passes` reported **255C** — a phase that was correct
and unchanged — failing A7.

**Root cause.** A7 required `implementation.md`'s version header to name the
phase. That header names the phase that closed **most recently**, so it can
only ever name one. A7 was therefore unpassable for every phase except the
newest, and **it broke the moment the next phase landed** — the test pinned
255C, 255D closed, and 255C began failing on a document nobody had touched.

**An assertion that only the newest artefact can satisfy is not a property
of a closed phase.** It is a property of being last.

**Fix.** A7 keeps the history-row requirement for every phase, and applies
the version-header requirement **only when the phase is the newest row** in
`implementation.md`.

**Files.** `.claude/skills/closeout/closeout_check.py`.

**Verified.** 255C and 255D both pass; the known-bad fixture still fires A7,
because its phase has no history row at all; 23 closeout tests green.

**Commit.** `fc1f8fc`.

**Why it was found at all.** Because the contract is run against a phase it
was **not written for**. A check exercised only on its own phase would have
passed for exactly one phase and then rotted silently.

### 2026-09-22 20:38 — Bug fix #7: A4 passed on a non-answer

**Issue.** Raised by the operator after `/closeout` was run on this phase:
fixes #5 and #6 above recorded their commit as `This one.`, and A4 passed
them. So did 255C's fix #7, whose line read *"See the close-out commit for
this fix."*

**Root cause.** A4 checked that the words `**Commit.**` were present, not
that they named anything. **A check that passes on a non-answer is the
defect this folder exists to stop shipping**, and it was in the check that
enforces the register.

**Fix.** A4 takes the backticked hash on each Commit line and requires
`git cat-file -e <hash>^{commit}` to succeed. `hash` (name) resolves in the
sibling checkout `name` — #4's `e536740` (workspace-docs) is real and lives
there — and an absent sibling is reported, not skipped. The known-bad
fixture plants a `This one.` line and an unresolvable `aaaaaaa`; the good
fixture now cites real commits. 255C #7 resolved to `f279533`.

**Files.** `.claude/skills/closeout/closeout_check.py`, both fixtures,
`tests/test_phase255D_closeout_contract.py`, `docs/phases/completed/255C_phase_log.md`.

**Verified.** 28 closeout tests green. Break-it: with resolution neutered,
three tests fail. The only phase newly failing A4 was 255D, for exactly the
two lines corrected above; fifteen older phases (141–255) already failed A4
on having no Commit line at all, and still do.

**Commit.** `1cce592`.

### 2026-09-22 20:39 — Bug fix #8: check 2 could not see `.claude/` (F137)

**Issue.** `verify_phase.sh` check 2 — no code after the regression hash —
reported only a floor-test bump for `b0ae748..3dfc78a`, although fixes #5
and #6 changed two skill scripts in that range.

**Root cause.** The check was `git diff -- src/ tests/`. Everything outside
two directories was treated as documentation, and `.claude/` holds this
phase's code. An exclusion that was never written down as one.

**Fix.** `code_after_regression.py`, one implementation for script and
test. A path is code unless positively documentation. Filed as **F137** and
closed by this fix.

**Files.** `.claude/skills/closeout/code_after_regression.py`,
`verify_phase.sh`, `fixtures/check2/`, the contract test, `docs/FOLLOWUPS.md`.

**Verified.** 32 closeout tests green. The real `b0ae748..3dfc78a` range now
reports both skill scripts. Break-it: old scope restored, three tests fail.

**Commit.** `b934926`.

### 2026-09-22 21:17 — Regression of record

**Regression 8,139 passed / 0 failed / 0 skipped / 36:37 at `2b24d39`.**
This supersedes the `b0ae748` run above as the phase's regression of record:
that run predated fixes #5–#8, all of which changed code under `.claude/`,
and check 2 could not see it until fix #8.

`COLLECTED_TEST_FLOOR` 8,130 → 8,139 (+9: five A4 tests from fix #7, four
check-2 tests from fix #8), raised in `2b24d39` **before** this run, so the
green run covers the floor file. The previous raise (`a00ec41`) landed after
its regression, and the new check 2 reports exactly that.

Everything after `2b24d39` is documentation: this log, `docs/FOLLOWUPS.md`.

**No database was touched by Phase 255D** — no schema change, no migration,
no write to `data/motodiag.db`. That is why `~/backups/motodiag/` holds no
`pre255D` backup: none was needed, and `verify_phase.sh` check 9 listing none
is expected, not a skipped step.

### 2026-09-22 21:17 — D1 open item closed: a repo-rooted session resolves project skills

D1 left one question for the operator: whether a **restart** makes `ping`
invocable, and — the part that mattered more — whether
`moto-diag/.claude/skills/` is read at all when a session is started in the
repository rather than its parent.

**Settled.** In a session started at `/Users/lilquant/Projects/moto-diag`,
`/ping` emitted `PING-255D-SENTINEL-8f3a2c` and `/closeout` loaded the
closeout skill's full text. Both resolved from `.claude/skills/` in the
repository, with no copy at the parent and no symlink. This is the behaviour
`moto-diag/CLAUDE.md`'s "Start sessions at this repository root" rule
depends on.

**What it proves and what it does not.** It proves discovery and loading at
a repo-rooted session start. It does not re-test the parent-rooted case,
which D1 measured as failing and which the rule exists to avoid; and, as the
`ping` skill itself says, loading a skill is not the same as following it.
The enforcement stays in the tests.

