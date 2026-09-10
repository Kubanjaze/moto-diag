# Phase 244G — Guard-shape sweep — phase log

**Status:** Planned
**Opened:** 2026-09-10

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
