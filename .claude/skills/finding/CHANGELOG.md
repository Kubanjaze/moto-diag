# finding — changelog

## 2026-09-22 — created (Phase 255D)

Second procedure folder. The F-number discipline was **not written down
anywhere** before this — not in CLAUDE.md, not in a phase doc. It lived only
in practice, which is the strongest case for a folder and is why `finding`
was sequenced second.

**Two measurement errors while building it, both caught by running the check
against the real repository rather than trusting it.**

*98 dangling citations, on the first run.* The check read only moto-diag's
`FOLLOWUPS.md`, and **F-numbers are one global sequence across both
repositories**, so every mobile finding read as missing. 98 → 9 once the
sibling file was included. The denominator was wrong, not the repository —
the same under-scoped-denominator error this project has made repeatedly,
and the reason the first move was to check the denominator rather than
weaken the assertion.

*Then 9 → 0, and four of the nine were not findings at all.* `F650`, `F700`
and `F750` are **BMW motorcycles**; `F401` is a **flake8 code**; `F48` is a
**phase**, whose own documents cite their own name. A bare `F` plus digits
is a model designation in this corpus at least as often as a finding.

**And the fix for that was itself wrong, which the fixture caught.** The
first version excluded them by a ceiling — ignore anything above the highest
assigned. The known-bad fixture cites `F139` when the file stops at `F138`,
which is exactly the real failure shape, and the ceiling skipped it silently.
**The rule that removed the false positives removed the true positive too.**
Replaced with named exclusions carrying a reason each.

That is three wrong rules in one afternoon, each caught by a control rather
than by review, which is the argument for the control.
