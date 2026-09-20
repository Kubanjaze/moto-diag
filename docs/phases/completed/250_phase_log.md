# Phase 250 — Gate 13: the electric track through the real front doors — phase log

**Status:** ✅ Complete
**Opened:** 2026-09-19

---

## 2026-09-19 — Plan v1.0

Track L's closing gate. Step 0 walked the path the roadmap row names —
"query electric bike → BMS/motor/regen/thermal analysis end-to-end" — and
found it does not carry the track's own content: retrieval is by vehicle
and symptom-blind, 241's ten critical HV-safety rows fill the twelve-row
prompt cap, and for an Energica Ego or a Harley-Davidson LiveWire none of
the four generic layers reaches the model at all. The corpus is right and
the path to it is not.

The operator's decision is that the gate reports and 250B repairs, the
pattern 240B and 240C set after Gate 12. So this phase measures: seven
classes over the real CLI, the real API and the real prompt, with the
honest-gaps class pinning what Track L knowingly lacks — no DTC file for
any electric make, five fault-code categories that exist with no codes in
them, no adapter row for any electric bike, Damon present as a make and
absent as content, and F93's 24 stale Energica anchors.

## 2026-09-19 — Built

`tests/test_phase250_gate13.py`, 106 tests in seven classes, no production
code. Every Step 0 measurement reproduced on a freshly seeded database,
which loads to exactly 996 rows — the count the live database carries, so
the shipped seed and the corpus agree.

The diagnostic class walks the real `diagnose quick` with the AI call
replaced and pins what reaches the model: the twelve-row cap filled every
time, the controller layer only on a Zero SR/F and a LiveWire ONE, nothing
at all on an Energica Ego or a Harley-Davidson LiveWire, and the same
twelve rows whether the rider reports a hot pack or a dead regen brake
light. Each of those tests is written to fail when row 250B lands.

Two things the gate found that Step 0 had not. Every electric bike in the
garage renders its motor power as **"NonekW"** — `motor_kw` is a real
column, `garage add` cannot set it, and the renderer's `.get(key,
default)` never fires for a key that exists holding None (F95). And the
corpus carries two forum conventions: the generic layer dates its pages,
the per-make rows name their evidence class instead, so the gate asserts
the newer rule only where it applies rather than reporting a history as a
defect.

## 2026-09-19 — Complete

Regression **7,301 passed, 0 failed, 28:17**. No schema change, no production code, no corpus change. Row 250B opens with the measurement, and this gate's own diagnostic tests are its acceptance criteria.
