# Phase 201 — Parts Ordering from Mobile — Phase Log

**Status:** 📋 Planned
**Started:** 2026-09-03 | **Completed:** —
**Repos:** `Kubanjaze/moto-diag` + `Kubanjaze/moto-diag-mobile`, both on
branch `phase-201-parts-ordering`

---

### 2026-09-03 23:49 — Plan written (Step 0 audit + v1.0)

- **Step 0 audit (delegated, both repos) reshaped the phase.** "Browse ·
  cart · order" read as greenfield; it is the reverse. Track G shipped
  the complete parts domain (`shop/parts_needs.py`, 18 functions, the
  `open→ordered→received→installed` line lifecycle as a CHECK
  constraint, requisition snapshots, catalog search in
  `advanced/parts_repo.py`) and Phase 180 deferred its HTTP exposure to
  "Phase 181+", which never happened. **Zero parts routes exist.** The
  backend half is a composing router with no migration expected; the
  error mapping is already in `api/errors.py`.
- **No supplier exists behind "order", by design** — Track O Phase 279
  reserves PO generation, and `vendors`/`inventory_items` are
  disconnected from `parts`. `parts_arrived` has sat in the 170 enum
  with no producer; 199's ledger pointed here.
- **Mobile is greenfield**: no `Parts*` types, hooks, or section
  variant. A client-side cart would trip ADR-003's 3-screen trigger.
- **User decisions:** order = the internal line lifecycle · **the WO's
  open lines ARE the cart** (server-backed; no client store; ADR-003
  untripped) · AI sourcing stays CLI-side.
- **Next milestone:** plan commit + push → backend router + tests →
  mobile types/hooks/section/screen → device smoke incl. the
  `parts_arrived` push.
