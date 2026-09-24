# finding — changelog

## 2026-09-24 — the "this repo leads" pin replaced (Phase 257B bug fix #2)

`test_both_followups_files_are_read` also asserted `max(backend) >
max(mobile)`, saying the allocation's assumptions needed revisiting if it
flipped. Phase 257B filed F145–F147 in the mobile file (app code; the
contract puts a finding with its code) and it flipped. Revisited:
`next_f_number.sh` takes the max over both files and B1 compares the
header with that same global max, so nothing depends on which file leads.
The pin is replaced by `test_the_next_number_clears_both_files`: the
script's next number is `max(both) + 1`, whichever file leads. Seen red
with the script narrowed to one file.

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

## 2026-09-24 — Yamaha's publication numbers are not findings (Phase 257, bug fix #9)

`NOT_FINDINGS` names 8199: Yamaha owner's-manual numbers ("BRG-F8199-11")
that Phase 257's citations carry. Excluded by name, as the BMW models are,
with a control that a real dangling citation in the same document still
fails.
