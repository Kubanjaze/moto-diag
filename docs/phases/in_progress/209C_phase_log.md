# Phase 209C — Closing a session updates what the shop remembers — phase log

**Status:** Planned
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
