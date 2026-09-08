# Phase 223 — KTM enduro (EXC / EXC-F / 690 Enduro R) — Phase Log

**Status:** ✅ Complete
**Started:** 2026-09-07 | **Completed:** 2026-09-07
**Repos:** `Kubanjaze/moto-diag`, branch `phase-223-ktm-enduro`

---

### 2026-09-07 — Step 0, hand-drafted content, close

- **First phase in the KTM block whose gaps were large rather than
  narrow.** 221 and 222 both fought duplication. Here the searches came
  back empty: across 756 entries, `TPI`, `transfer port`, `engine hour`,
  `hour meter`, `competition` and `piston replacement` each returned
  **zero**, and the only genuine two-stroke service content was three
  RD350/400 entries in `yamaha_vintage` — 1970s road bikes. Modern
  competition two-stroke content did not exist in this corpus.
- **The backwards genericness test still applied**, because the off-road
  *topic* is well covered: four dual-sport files hold **40 entries** —
  DR650, KLR, XR, WR. Those are trail machines meant to last; these are
  competition machines meant to be rebuilt. Every entry must name an
  enduro designation in **title and body**, and the counter-assertion
  runs over two entire dual-sport files rather than one hand-picked
  entry — all of them score zero.
- **The row named the four-strokes wrongly.** It read "450/500 EXC". KTM
  uses **EXC** for the two-strokes (250, 300) and **EXC-F** for the
  four-strokes (250, 350, 450, 500), so "450 EXC" names a machine that
  does not exist, and the shorthand collapses precisely the distinction
  the naming exists to draw. Third naming correction in this block after
  the Super Adventure GT and the LC8c.
- **The "adventure" half of the row had no content and no home.** The
  390, 790 and 890 Adventure appear in **no row**: 221 took the 1290
  Super Adventure, 222 the Duke nakeds, and 224/225 are engine and
  electrical rows. Putting a parallel-twin tourer in the same phase as
  competition two-strokes would be incoherent, so this phase did not
  take them — and the block as numbered has no free row, so the gap is
  flagged on the roadmap for a deliberate decision rather than absorbed
  or quietly dropped. A test asserts the gap was not taken.
- **Six entries, built on the competition distinction**: TPI two-strokes
  running an oil pump rather than premix — rated **critical**, because
  both directions of that error destroy engines and neither announces
  itself on the first ride; EXC versus EXC-F; service counted in
  **engine hours** rather than miles, so a low-mileage bike can be far
  past due; a top end being **maintenance rather than failure**, where
  the harm is in how it is described rather than in the work; the
  exhaust power valve as a service item that presents like a fuelling
  fault; and the 690 Enduro R sitting between competition and road
  schedules.
- **Interval figures deferred by test**, as in 219 and more sharply — a
  missed top end on a competition two-stroke is an engine, not a wrong
  quote. A second assertion requires any entry that mentions intervals
  to point at the manual, and **that one caught a real content gap**:
  the naming entry said the two engines want different intervals without
  saying where to get them. Content fixed rather than the test loosened.
- **Seventh consecutive phase where my own check, not the content, was
  at fault**, and a new family member: **quotation**. It flagged
  `a request for a top end on a "450 EXC"` as calling a four-stroke a
  plain EXC — a sentence whose whole job is naming the error, already
  marked as a citation with quote marks. Text inside paired quotes is
  now exempt, joining negation (216/219), reported speech (221) and
  comparison (222). Verified on six discrimination cases: quoted errors
  pass, bare claims like "The 450 EXC is a four-stroke enduro" and
  "A TPI model takes premix" are still caught.
- **The full regression caught a guard with the defect I had fixed
  earlier in this same phase.** Phase 222's `test_they_load_together`
  globs the KTM files but hardcoded their total at 11; adding a third
  file broke it. That is the same mistake as the Phase 221 guard 222
  repaired — a constant standing in for an invariant — reintroduced one
  phase later by me. Both KTM coexistence tests now assert the
  invariant: loading every KTM file yields the sum of their entries with
  none lost to a collision, plus each file's own count. Fixing an
  instance of a bug is not fixing the habit that produces it.
- 756 → 762; 17 KTM entries across three files; 32 phase tests;
  regression 5261/0; F9 clean.
- **Key finding: a validator over prose must exempt quotation.** Naming
  an error is not committing it — and after seven phases the pattern is
  that every exemption is a different way of *mentioning* rather than
  *using* a term.
