# closeout — changelog

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
