# Phase 247 — Motor controller / inverter faults: the generic layer, anchored per make — phase log

**Status:** 🚧 In progress
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
