# Phase 244S — The retrieval fixes reach the commands people use — phase log

**Status:** Planned
**Opened:** 2026-09-17

---

## 2026-09-17 — Plan v1.0 written

Second of the three reachability phases the Track L audit found. Step 0 ran
inside 244R's sweep as a design plus an adversarial check, and **the checker
broke the design**: the two retrieval paths return different row shapes, so
swapping one for the other would have handed callers JSON strings where they
expect lists. Its corrections are the plan.

The measured harm is worse than "specific entries rank badly". A bike entered
as "Homda" returns 0 rows through the LIKE path, `build_knowledge_context([])`
returns "", and the model diagnoses with no corpus while nothing says so —
the exact failure 244C exists to end, still shipping on the primary command.
The resolver returns 143 for the same input.
