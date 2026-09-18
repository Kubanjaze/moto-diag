# Phase 248 — Regenerative braking diagnostics: the generic layer, anchored per make — phase log

**Status:** ✅ Complete
**Opened:** 2026-09-18

---

## 2026-09-18 — Plan v1.0

Straight after 247, in the same shape. Step 0 found the `regen` category
empty like its five siblings, no corpus row with a regen symptom, and
nothing generic about regen anywhere; the manuals 246 and 247 verified
were never read for their ride-mode sections. Regen is the one electric
subsystem the rider sets, so the row is written around what each maker
lets the rider set, what the machine does off throttle and at a stop,
whether the brake lamp answers regen, and whether anyone offers a one-pedal
stop — as published, or as an absence. The three make sweeps were launched
with the plan.

## 2026-09-18 — Built

Ninety claims, forty pages, twenty refuter groups that fetched every page
themselves, a critic. Seven rows: six service-manual concepts written as
what regen does and how Zero, Energica and LiveWire show it, and one dated
community row. No regulation row: no make has a regen campaign. The
refuters overturned four of the sweeps' absence claims by finding what the
sweeps had missed, and the critic held all of it back until someone quotes
it — no quote, no row — so it is filed as F92. Mutation 2 survived its
first run and exposed a bug older than this phase: the number rule could
never see a percentage. Fixed in all three content tests; nothing shipped
was mislabelled.

64 tests, 517 across the suites, 8/8 mutations. README count 985 → 992.

## 2026-09-18 — Complete

Regression **7,155 passed, 0 failed, 27:31**. No schema change.
