# Phase 244G — Guard-shape sweep — phase log

**Status:** ✅ Complete
**Opened:** 2026-09-10 | **Closed:** 2026-09-10
**Repo:** https://github.com/Kubanjaze/moto-diag

---

## 2026-09-10 — Plan v1.0 written

Opened because the same failure happened four times in one session: a guard
matching an identifier as text fired on the prose explaining it. Phase 241's
SafetyChecker tripwire fired on a docstring citing it as a cross-reference.
Phase 244's attribution filter flagged the correction for quoting the claim it
refuted. Phase 244D's guard against `INSERT OR IGNORE` fired on the comment
saying why it is not used. Phase 244F's derivation guard pinned a module the
code had left.

Two were repaired ad hoc with `ast`. Four instances is not bad luck — it is the
shape of how guards are written here, and the repairs were local to whichever
guard happened to break.

**The worse case has not been hit yet, which is why it is worth a phase.** A
guard asserting `"get_session" in src` passes if the identifier survives only in
a comment, so deleting the code it protects leaves the guard green. A false
failure is loud and gets fixed within minutes. A false pass is a guard quietly
protecting nothing.

**Step 0 found fourteen assertions over Python source** — two negative, twelve
positive. The wider `.read_text()` population is 60 files, but almost all read
report output or JSON corpus content, where literal matching is exactly right;
the concern is specific to source.

**The real damage is the incentive.** A guard that punishes explaining a defect
teaches the next author to delete the explanation rather than look at the code.
Phase 241's tripwire fired on the sentence written to make its own gap findable,
and the cheapest way to make it green was to remove that sentence.

So the deliverable is not the fourteen conversions. It is `code_of()` plus a
meta-guard that fails when a new assertion reads raw source instead — the
conversions fix today, the meta-guard fixes tomorrow.


---

## 2026-09-10 — Built

`tests/support/source_guards.py` provides `code_of()`: source with comments and
docstrings blanked and everything else **byte-for-byte** intact — same length,
same line numbers, same columns. That fidelity is not incidental. Guards here
pin multi-line SQL literals and a `tool_choice` dict, so a normalising rewriter
like `ast.unparse` would break the very guards this exists to keep working.
Ordinary string literals survive for the same reason: a guard pinning an
`ORDER BY` clause is reading code that happens to be a string.

**The meta-guard caught itself.** Its first version scanned with a regex and
flagged its own file, because the sample offender code it builds to test itself
sits inside string literals and a regex cannot tell a string containing code
from code. The tool built to stop that mistake made it. Rewritten to parse the
AST — assignments from `getsource`/`read_text`, then `Assert` nodes comparing a
string constant against those names.

**Parsing then found four offenders the manual audit had missed**, two written
the same hour in Phase 244F. The audit found 14; the parser found 18. Grep-based
auditing misses what grep-based guards miss.

**Both directions are now demonstrated rather than described.** A negative guard
no longer fires on a comment explaining why something is avoided. A positive
guard now fails when the identifier survives only in a comment — the case nobody
had hit, and the worse of the two: a false failure is loud and fixed in minutes,
a false pass is a guard quietly protecting nothing.

Phases 241 and 244D keep their own `ast`-based repairs, which are stronger than
`code_of` for what they check; this phase only guards that they have not
regressed to text matching.

19 guards, 5/5 mutations caught, F9 lint clean. Regression **6231 passed / 0 failed** (baseline 6212; +19 guards).
