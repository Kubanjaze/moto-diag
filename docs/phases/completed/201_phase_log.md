# Phase 201 — Parts Ordering from Mobile — Phase Log

**Status:** ✅ Complete
**Started:** 2026-09-03 | **Completed:** 2026-09-04
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

---

### 2026-09-04 00:11 — Build complete (backend + mobile)

- **Backend (`f07f7f6`):** `api/routes/parts.py` — 12 routes, **zero
  migrations**, every branch calling an existing Track G function. New
  behaviour limited to the `parts_arrived` producer plus two
  compositions the domain layer does not do: add-dedupe (bump an open
  line rather than grow a second) and delete-while-open vs cancel-after.
  `notify_parts_arrived` added to the push events layer. **37 tests.**
- **Mobile (`987fe25`):** 8th `WorkOrderSection` variant,
  `useWorkOrderParts` (the cart — server state, no client store, so
  ADR-003 stays untripped), `usePartsSearch`, `PartsBrowseScreen`, and
  the Add parts / Order card on the WO detail. **+20 tests → 73 suites
  / 896 green**, tsc clean.
- **The exhaustive-switch guard did its job:** adding the variant broke
  `WorkOrderSectionCard`'s `never` assertion at compile time, exactly
  the property Phase 193's smoke gate Step 9 was built to give.
- **Two first-run failures were fixture bugs**, both worth writing down:
  catalog `make` is stored lowercased by `add_part`, and
  `create_work_order` lands in `draft` which the shop-wide consolidation
  excludes.

### 2026-09-04 00:11 — SMOKE + the bug the smoke actually found

- **HTTP flow verified end to end:** browse-by-bike returned 5 parts
  with no query typed; free-text narrowed to 2; add → dedupe returned
  `merged: true` with quantity 2; cart $155.96; **Order** moved 2 lines
  and a second press moved 0; an illegal skip returned 409; a
  requisition snapshot came back with the right totals.
- **`parts_arrived` verified on the real device.** A second shop member
  received a part on a work order assigned to the phone; the push
  reached it through **live APNs** (`push sent to user 1 (Parts arrived
  for work order #2)`).
- **Chasing that log line found F57.** Before the fix there was no push
  line — and no access line, and no Phase 200 "minted share" line
  either. The server had **never emitted a single application log**:
  `uvicorn.run(log_level=...)` configures uvicorn's own loggers, and
  `motodiag.*` inherits root (WARNING, no handler), so INFO was dropped
  while `logger.exception` still surfaced. **F52's "a successful push
  leaves a trace" had therefore been false in production since it
  shipped**, with a green test, because `caplog.at_level` forces the
  level the server never set. Fixed in `af18aca` with 3 regression
  tests.
- **Also split expected from unexpected** in the producer: a customer
  with no email (a walk-in, or the id-1 "Unassigned" sentinel) is
  routine and now logs one readable line instead of a traceback.
- **In-app UI half NOT verified.** The Mac's tailnet stopped routing
  mid-session — Tailscale reports Running and online and `tailscale
  serve` still shows the proxy, but both the `ts.net` name and the raw
  tailnet IP time out while loopback answers. The app's `API_BASE_URL`
  is baked to that name, so browse/add/Order on the phone could not be
  exercised. Remedy is the documented VPN toggle or reboot — the user's
  call, not something to do to their VPN unasked.

### 2026-09-04 00:11 — Documentation update + close

- `201_implementation.md` → v1.1 (honest `[~]` on the device row,
  deviations incl. F57/F58 and the pre-existing lint error, results,
  key finding). Docs → `completed/`.
- Mobile project docs updated; ROADMAP 201 ✅; **F57, F58, F59** filed.
- Branches fast-forwarded into `master` / `main`, pushed.
