# Phase 238 — Phase Log

**European valve service intervals, compared across makes**
Branch: `phase-238-european-valve-intervals` | Date: 2026-09-08

## Step 0
- Per-make files already print some intervals; this phase owns the
  comparison and two deferrals (234's shim diameter and F3 figure; 225B's
  sibling question). 225B's shipped sibling claim was found false here.

## Research
Paired 6-agent run with 239 (verdicts landed second, so the order swapped).
Both refuters refuted narrowly. Source lens MD5-matched ten PDFs and re-read
every table visually — all intervals survived. Contradiction lens found six
MV maintenance manuals on disk, unopened, containing the one documented
same-engine differing pair.

## Failures caught
- 225B's entry corrected; my first correction printed the figures into it
  and 225B's own boundary test caught that.
- My figure-carries-document test used a ±400-char window and failed an
  entry whose document sat 410 chars earlier — made per-entry.
- MV coupon ladder and Ducati oil-service column misreads, from refutation.
- A SIXTH designation-bar guard fired (Phase 226). Three earlier sweeps
  matched on the test's name; this copy is named differently. Re-swept by
  shape — every test globbing the knowledge dir and skipping by filename —
  which returns exactly six and clears 221's title test as correctly scoped.

## Close-out
- 904 → 917. Regression 5898 passed / 0 failed. F9 clean.
- Cleared for roadmap ✅, implementation.md 0.13.50 → 0.13.51, merge.
