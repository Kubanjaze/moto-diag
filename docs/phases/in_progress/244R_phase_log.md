# Phase 244R — The DTC taxonomy can hold content — phase log

**Status:** Planned
**Opened:** 2026-09-17

---

## 2026-09-17 15:05 EDT — Plan v1.0 written

Opened from a roadmap-readiness audit. The operator asked where to go next;
the audit found that most of the next six rows cannot be built honestly —
245 Damon has no documentation to build from, and 246/248/249's measurement
halves need telemetry the product has never once recorded (zero sensor
samples, no Mode 22/UDS in any adapter). What it did find was three shipped
capabilities no user can reach. This phase is the first of them.

`motodiag code --category engine` says "No DTCs found" over 29 engine codes.
One missing keyword argument in the seed loader, 99 rows, and six thousand
tests that never crossed the seam between authored data and the filter.

Step 0 ran as eight agents — four designs, each adversarially checked. Three
of the four designs were broken by their checker, which is the point of
running them. This one survived with six corrections, and two of them
changed the plan:

- **`unknown` is itself a category**, so `--category unknown` returns all 99
  today and my "never returns a row" claim was wrong. More importantly a typo
  and an empty category print the same line, so the phase now has to make a
  wrong category say so.
- **The taxonomy contradicts itself.** `dtc_category_meta` files O2, catalyst
  and secondary air under `exhaust`; the enum's own comment files them under
  `emissions`. Authoring even one row requires declaring an authority first.
  The meta table wins — it is what the CLI joins, what the API serves and
  what a reader can inspect — and the enum comment gets corrected to match.

Both mechanical shortcuts were measured and rejected: copying the legacy
column classifies 76/99 and silently writes 23 values that exist in no
category; deriving from the code prefix puts zero rows in `engine`.
