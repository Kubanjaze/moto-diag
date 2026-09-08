# Phase 218 — Ducati Multistrada — Phase Log

**Status:** ✅ Complete
**Started:** 2026-09-07 | **Completed:** 2026-09-07
**Repos:** `Kubanjaze/moto-diag`, branch `phase-218-ducati-multistrada`

---

### 2026-09-07 — Step 0, hand-drafted content, a gate correction, close

- **Two Step 0 findings, both inversions of the two phases before it.**
  (1) The **Multistrada V4 has no desmodromic valves** — the Granturismo
  uses conventional spring return with a ~60,000 km interval against
  roughly 15,000 miles for the desmo V4. Verified by search. That means
  **Phase 219 ("Ducati desmodromic valve service") does not apply to
  this bike**, and row 219 is annotated. (2) **The cam drive splits
  inside one model name**: 1200/1260/V2 are belt driven, V4 is chain
  driven — so neither 216's rule nor 217's holds across the Multistrada.
  The tests resolve belt-versus-chain **per entry** from its own model
  string; the first conditional guardrail in the project.
- **Semi-active suspension was already saturated** — five entries (BMW
  ESA, ESA II, DDC, Öhlins Smart EC, ZX-10R KECS), all some version of
  "the unit failed". Skyhook only earned a place by covering what none
  of them can: the **load selection** on an electronically preloaded
  adventure bike, and the test asserts that framing.
- **A latent gate tripped and the obvious fix would have been
  dishonest.** Gate 2 requires ≥90% of issues to carry a "Forum tip";
  the count hit 660/734 = 89.9%. Adding "Forum tip" to my entries would
  have **fabricated provenance** — the exact thing `source` exists to
  prevent. Measured instead: forum-sourced entries are at **100%
  (660/660)**, model-generated at **0/74**. The gate's intent was never
  violated; its denominator changed when Phase 211 added a second
  provenance class. Scoped it to that population and added the inverse
  assertion — model-generated entries must NOT claim forum tips — which
  makes it a two-sided guarantee rather than a weakened one. It has been
  drifting since 211 and caught 218 by arithmetic, not by fault.
- **Eight entries**: the Granturismo spring-valve exception, the split
  cam drive, DVT variable timing on the 2015–17 1200, V4 radar sensors
  read as a cruise fault, Skyhook load selection, V4 rear-bank
  deactivation at a standstill, 1200-vs-1260 parts and procedure, and
  loaded-touring inspection on the Rally.
- 726 → 734; 22 phase tests; regression **5123 / 0**; F9 clean.
- **Key finding: guardrails can be conditional, and gates can decay by
  addition rather than by fault.**
