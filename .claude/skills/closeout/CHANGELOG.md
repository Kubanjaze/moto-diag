# closeout — changelog

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
