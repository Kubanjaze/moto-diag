# Phase 224 — KTM engine families (LC8 / LC8c / LC4) — Phase Log

**Status:** ✅ Complete
**Started:** 2026-09-07 | **Completed:** 2026-09-07
**Repos:** `Kubanjaze/moto-diag`, branch `phase-224-ktm-engines`

---

### 2026-09-07 — Step 0, scope decision, hand-drafted content, close

- **The row's entire stated content was already written.** Row 224
  reserved cam chain tensioner, electric start and valve clearance.
  Across 762 entries those topics appear in **37, 23 and 26** entries,
  with the procedures already in generic form — starter relay, motor and
  sprag clutch in `cross_platform_starting`; CCT and valve clearance in
  the Honda and Yamaha cross-model files with `model: "All"`. A KTM cam
  chain tensioner entry would have been the thirty-eighth. **None of the
  three is written here**, and a test asserts no KTM-specific failure
  claim about them exists.
- **But the row is structurally right.** The corpus's own precedent is a
  per-make cross-engine file. Row 224 is KTM's, and KTM has something
  Honda and Yamaha do not: three architectures under two prefixes.
- **The LC8c scope question from Phase 222 is decided: widened.** Row
  224 goes from "LC8 V-twin" to the KTM engine families. A V-twin-only
  phase had almost nothing left to write, the precedent is a per-make
  cross-engine file, and the block as numbered has no free row for an
  LC8c one. Recorded on the row so it is visible and reversible.
- **Not knowing is recorded as a result.** Honda's entry can call the
  inline-four tensioner a documented weakness because it is. I have no
  equivalent confident LC8 knowledge, and inventing it would be
  fabrication in the costume of specificity — the exact failure the
  `model-generated` provenance discipline exists to prevent. The absence
  is a test (`FAILURE_CLAIM`), not an intention.
- **Four entries**, each carrying what only a KTM cross-engine file can:
  the architecture map; **generation span within the LC8** — 950 through
  1290 across two decades, the error that survives getting the
  architecture right; cylinder identification on a 75-degree vee,
  **without asserting which cylinder is which** — the entry sends the
  reader to the manual and a test forbids "cylinder 1"; and routing for
  the three universal topics.
- **A factual claim about the corpus was wrong in the first draft.** The
  routing entry said all three procedures were cross-platform. Only the
  starter ones are; CCT and valve clearance live in make-scoped
  cross-*model* files. The plan's Step 0 had the same overstatement.
  Both corrected, and a test now requires the entry to draw the
  distinction. Caught by re-verifying against the corpus rather than by
  a test — an entry that describes the corpus has to be checked against
  it, not against memory of it.
- **Duplication checked by symptom overlap across all four KTM files** —
  the same mechanic query must not resolve to two files. Coexistence
  asserted as the invariant, not a constant (the 223 lesson, applied
  first time rather than after a regression failure).
- **No validator false positive this phase** — the first since 216. The
  claim checks here were narrower (a failure-claim regex, a numbering
  regex) rather than the general `_asserts` helper, so this is one data
  point about scope rather than evidence the helper is finished.
- 762 → 766; 21 KTM entries across four files; 25 phase tests;
  regression 5286/0; F9 clean.
- **Key finding: a row can be structurally right while its stated
  content is already written — and not knowing a make-specific failure
  pattern is a result to record, not a gap to fill.**
