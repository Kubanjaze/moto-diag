# Phase 247 — Motor controller / inverter faults: the generic layer, anchored per make — phase log

**Status:** ✅ Complete
**Opened:** 2026-09-18

---

## 2026-09-18 — Plan v1.0

Straight after 246 closed, in 246's shape. Step 0 found the `inverter` and
`motor` categories already in the meta table and empty, sixty rows that
mention a controller and none that explain one, and four refuter-verified
246 survivors waiting on this ground — Zero's thermal-strategy indicator and
motor gauge, Energica's VCU-run LIMP, LiveWire's Temp widget. The row's
bullets are generic engineering; the plan writes what each maker publishes
and says where they publish nothing. One decision: Energica's inverter
codes are not seeded into `dtc_codes` (the manual gives no causes or fixes;
F90 stays open) — they ride on the rows' `dtc_codes` lists instead. The
research runs as 246's fetch-and-verify pass through the Agent tool; the
three make sweeps were launched with the plan.

## 2026-09-18 — Built

Eighty-eight claims, forty-seven pages, twenty-one refuters that fetched
every page themselves, a critic that cut seven more. Eight rows: five
service-manual concepts written as what the controller does and how Zero,
Energica and LiveWire show it, two regulation rows for the controller
recalls on their own label, one dated community row. The row's bullets are
recorded as absences with the manuals read in full to say so. The sweep
reached Zero's own archived service manuals, which name the Sevcon
controllers and the dealer tool's controller interface, and two 2025 Zero
recall filings that name a Dana TM4 controller — more than Step 0 expected.
On the way, the Energica code-table refuter counted 129 rows where Phase
244's row said 110; that row is corrected, and the live copy is updated by
its old title at close-out, copy first. Two mutations survived first runs
(a code range instead of a list; pack units instead of controller units)
and both rules were tightened.

63 tests, 453 across the suites, 8/8 mutations. README count 977 → 985.

## 2026-09-18 — Complete

Regression **7,091 passed, 0 failed, 27:53**. No schema change.
