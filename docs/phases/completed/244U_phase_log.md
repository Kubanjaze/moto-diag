# Phase 244U — The gate can see what a re-export hides — phase log

**Status:** ✅ Complete
**Opened:** 2026-09-17

---

## 2026-09-17 — Plan v1.0 written

Last of the reachability phases. Opened because 244T had to wire
`SafetyChecker` by hand four phases after Phase 241 recorded it had no
caller — the gate never said a word, because `engine/__init__` re-exports it.
Every number in the plan was re-measured rather than carried over from the
sweep that raised the issue; its headline figure did not survive.

## 2026-09-17 — Built

`blank_exports` does both halves, and the measurement is the phase's whole
argument: alias lists alone reveal **nothing at all**, `__all__` alone reveals
3, together they reveal 20. Seventeen names appear only when both are applied,
because a re-export writes each name twice and blanking one leaves the other.
A test pins that, so nobody ships the obvious half, sees a green gate, and
concludes there was nothing here.

The sweep that raised this claimed 117 names across 42 modules. Measured
against the gate's own definition of a live orphan, it is 20. Repeating the
larger number would have been easier and wrong.

What the blind spot hid is coherent rather than scattered: torque specs, valve
clearances, wiring circuit references, cost estimation, parts recommendation,
repair-procedure generation — engine capability a technician would ask for by
name, reachable by nothing. Four readers classified the 20 and four
challengers checked them; 19 stood, one reason was corrected.

A wrong expectation of my own became a test: a re-exported module stays
reachable, because the import edge is real, while the name inside it is an
orphan. Importable is not reachable.

12 tests, 4/4 mutations.

## 2026-09-17 20:37 EDT — Complete

Regression **6,914 passed, 0 failed, 30:07**. No schema change.
