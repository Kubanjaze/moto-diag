# Phase 244Y — Dead code leaves with its evidence — phase log

**Status:** ✅ Complete
**Opened:** 2026-09-18

---

## 2026-09-18 — Plan v1.0

The instrument is finished; this is the first phase that acts on what it
reports. Step 0 was gathered read-only while 244X's regression ran: every
`superseded` entry across the three allowlist tables, plus the two engine
modules the audit named for deletion with no dissent. Seven modules and ten
defs, 1,846 source lines, each with a table entry naming its live
replacement and its line count printed in the plan before anything moves.

Two things Step 0 changed. The recall repo 244X had called a duplicate is
delegated to by the live one for a single function — the four orphaned
functions go, the file stays, and 244X's entries were corrected before they
were committed. And two one-line wrappers in `memory/compile.py` stay,
reclassified rather than deleted, because forty-five tests call one of them
and a one-line wrapper is not worth forty-five rewrites.

Three gate tests depend on candidates. Gate 3's definition was written when
the modules it imports were the track; the six tests that assert a dead
module is importable come out with a docstring saying so, and the plan says
so up front, because a gate test being edited is something to hear before
rather than after.

## 2026-09-18 — Built

The build was a script, dry-run twice on copies before it touched the
tree, and it still needed the operator for one thing: the auto-mode
classifier declined eleven `git rm`s as irreversible. Everything else is an
edit, so the edits ran first and the tree sat intentionally red — entries
gone, files present — while the gate reported exactly that.

Then the files went, and the gate earned its keep a second time. Three
names whose only callers had just left surfaced as new orphans: a prompt
builder only the deleted class called, an exception only the deleted
decorator raised, a data model only the deleted repo constructed. Two were
cascade-deleted; the model joined its four siblings on the list. A second
run reported nothing new.

Two of my own mistakes were caught by the build's own checks rather than
by luck. My list of deleted names had ten of `roles_repo`'s twelve; a diff
of each module's full AST surface against the list found the two. And a
mutation — a dead re-export left in an init — survived every gate suite,
because those suites are static and never import the package. The phase's
own test file now imports every pruned package. Recorded as 4/4 with the
caveat, not rounded.

50 tests, 4/4 mutations, 288 across the trimmed files and gates.

The first full regression then failed exactly one test, and it was the
right one: 244G's meta-guard, which exists because a guard that reads source
text will eventually read a comment, fired on three assertions in this
phase's own test file. One now reads blanked code; the two that check
docstrings on purpose say so on the line. Re-run in full.


## 2026-09-18 — Complete

Regression **6,947 passed, 0 failed, 25:45**. 248 tests removed with their code; no schema change.

Next: 244Z, the content hazards in the six engine modules that stay shelved.
