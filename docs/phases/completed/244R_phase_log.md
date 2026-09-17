# Phase 244R — The DTC taxonomy can hold content — phase log

**Status:** ✅ Complete
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

## 2026-09-17 — Built

The fix itself is one keyword argument. The phase is the other 98% of the
work: deciding what 99 codes are, and making the surfaces stop disagreeing.

**The authority contradicted itself.** Step 0 had already caught the enum
comment disagreeing with the category table; reading the shipped rows showed
the table disagreeing with itself — `emissions` and `exhaust` both claimed O2
and catalyst. Authoring even one row was impossible until that was settled, so
migration 062 rewrites both descriptions and the ruling went into the
authoring brief. It held: the only two rows that came back `exhaust` are an
exhaust-valve position sensor and its drive stage, which is exactly the
hardware-not-emission-control line the ruling drew.

**Eight agents authored and re-checked the 99.** Four assigned with a reason
per row; four more re-derived every assignment from the seed files without
seeing the reasoning as authority. They agreed with **all 99 categories** —
every one of their six findings was about the runner-up annotation rather
than the assignment, including a good one: the runner-up for `P0500` should
be `transmission`, not `abs`, because someone "fixing" it later will read
that field.

**Three things I got wrong and the work corrected.** The first pass
re-serialised two seed files that store one entry per line, turning a 99-line
change into 800 and burying the review — redone as a textual insert. My test
module read the new key at collection time, so an unclassified corpus broke
collection rather than failing the one guard that should fail. And my own
headline was wrong before Step 0's checker caught it: `--category unknown`
worked all along, because `unknown` is a category too.

7 of 7 mutations caught. On a copy of production the migration classifies all
99 rows with `dtc_codes.id` unchanged and no other table touched.

## 2026-09-17 17:45 EDT — Complete

Regression **6,824 passed, 0 failed, 26:33**. Schema 61 → 62.
