# Phase 209C — Closing a session updates what the shop remembers — phase log

**Status:** ✅ Complete
**Opened:** 2026-09-17

---

## 2026-09-17 13:50 EDT — Plan v1.0 written

Picked up at the operator's direction ("F79 memory on close"). In the same
exchange the operator settled F78's two open questions: block new AI calls
at the cap, and the session carries its shop. Those are recorded in mobile
FOLLOWUPS (`cee05c7`) and wait for the next phase.

The ticket is one call. Step 0 is why the plan is larger than that:

- **Nothing supersedes a memory fact.** A fact's identity includes its
  text, so an edited diagnosis compiles as a new fact beside the old one.
  `facts.py` documents `superseded_at` as the fix, and `list_facts` already
  hides superseded rows, but no code ever sets it. Compiling on every
  close would make this happen routinely: reopen, edit, close is exactly
  what the operator did on 2026-09-17.
- **PATCH can close a session without `close_session()`.** It skips
  `closed_at` and would skip any hook put there.

Measured on a copy of production: a compile takes 4–6 ms per vehicle,
inserts 0 facts, and would supersede 0 of the 37. The reconciliation is
invisible in today's data.

## 2026-09-17 — Built

`memory/refresh.py` is new, `close_session` calls it, and `update_session`
now routes `status` through the lifecycle functions. `reconcile_facts` is
the first code that ever sets `memory_facts.superseded_at`.
`compile_vehicle` still returns rows inserted, so no caller changed;
`compile_vehicle_detailed` carries the supersede and revive counts, and the
CLI prints them when there are any.

The 31 tests passed on their first run, which is a reason to distrust them
rather than a result. The mutation run is what makes them evidence, and it
found one real hole. The route test for a failing compile asserted only
*"the close stands"*, and **both** guard layers log that phrase. Removing
the refresh's own `try` would have left the test green: the outer guard
caught the exception instead. The test now asserts the refresh's own line,
and three tests pin the function directly. After that, **15 of 15
mutations were caught.**

A second catch came from my own first draft of the PATCH routing: a PATCH
repeating `status: "closed"` would have returned 404. It's pinned now.

On a copy of production, the full compile changed nothing: 0 inserted,
0 superseded, 0 revived across 10 machines. `data/motodiag.db` itself was
not touched.

## 2026-09-17 14:15 EDT — Complete

Regression **6,657 passed, 0 failed, 25:32**. Schema unchanged (v60).
