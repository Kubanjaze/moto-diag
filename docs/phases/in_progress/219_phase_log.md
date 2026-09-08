# Phase 219 — Ducati desmodromic valve service — Phase Log

**Status:** ✅ Complete
**Started:** 2026-09-07 | **Completed:** 2026-09-07
**Repos:** `Kubanjaze/moto-diag`, branch `phase-219-ducati-desmo`

---

### 2026-09-07 — Step 0, hand-drafted content, close

- **The roadmap named a mechanism the engine does not have.** Row 219
  said "shim-over-bucket opener/closer". Verified by search: desmo uses
  **two rocker arms and two shims per valve** — a small opening shim on
  the stem, a large closing shim retaining the collets — and **no
  buckets**. "Shim-over-bucket" is a spring-valve design. Fourth row
  correction in the Ducati block; corrected at close-out.
- **The genericness test runs backwards here.** The corpus holds 22
  valve-clearance entries across four Japanese makes, all spring-valve
  and several explicitly "shim-under-bucket". Desmo is a different
  mechanism, so the risk is writing a generic clearance entry with a
  Ducati badge — the test requires every entry to **name desmodromic
  hardware** rather than forbidding a shared topic.
- **Six entries**, procedure-shaped rather than failure-shaped: what
  the mechanism is and why spring-valve assumptions fail; both
  clearances and the closing one that has no analogue; collet and
  half-ring seating (rated **critical** — a released collet drops a
  valve); shim availability rather than price being what strands a bike
  mid-service; intervals varying by generation so a remembered figure
  produces a wrong quote; and 2V versus 4V being different jobs.
- **My validator was wrong for the fourth consecutive phase**, in two
  new ways: it flagged "shim-under-bucket" (a *proper name* for the
  other design) and "the Granturismo **is not** desmodromic", where the
  negation follows the term rather than preceding it. Negation is now
  checked in both directions and named-system compounds are exempt.
- **Intervals deferred by test**: a regex assertion fails any entry
  stating a mileage figure as fact, because a wrong interval becomes a
  wrong quote.
- 734 → 740; 22 phase tests; regression **5145 / 0**; F9 clean.
- **Key finding: a validator over prose must distinguish assertion from
  reference, and negation can arrive from either side.** Four phases of
  false positives were one mistake in four costumes.
