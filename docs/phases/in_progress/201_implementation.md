# Phase 201 — Parts Ordering from Mobile

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-09-03

## Existing-code audit (Step 0 — run 2026-09-03, before this plan)

Delegated read-only sweep across both repos. This audit reshaped the
phase more than any since 192: the roadmap wording ("browse · cart ·
order") reads as greenfield, and it is nearly the opposite.

- **Parts domain layer — EXTENSION, and complete.** Track G shipped the
  whole thing and Phase 180 then deferred exposing it to "Phase 181+",
  which never came. `shop/parts_needs.py` has 18 public functions:
  `add_part_to_work_order`, `list_parts_for_wo`, `update_part_quantity`,
  `update_part_cost_override`, `remove_part_from_work_order`,
  `cancel_part_need`, `mark_part_ordered/received/installed`,
  `list_parts_for_shop_open_wos`, `build_requisition`,
  `get_requisition`, `list_requisitions`, and friends. Catalog browse
  lives in `advanced/parts_repo.py` (`search_parts`,
  `list_parts_for_bike`, `get_part`, `get_xrefs`). The per-line lifecycle
  is already a CHECK constraint on `work_order_parts.status`:
  `open → ordered → received → installed`, plus `cancelled`.
- **HTTP surface — GREENFIELD. This is the core finding.** `shop_mgmt.py`
  exposes 25 shop routes and **not one** touches parts, requisitions or
  sourcing. Every domain function above is CLI-only
  (`motodiag shop parts-needs …`, `shop requisition …`). Error mapping
  is already wired: `api/errors.py` maps `WorkOrderPartNotFoundError`
  and `InvalidPartNeedTransition` to ProblemDetail. So the backend half
  of this phase is a router that composes existing functions — no
  migration expected.
- **"Order" has no supplier behind it — by design.** No supplier API,
  affiliate link or external catalog exists anywhere; `parts.purchase_url`
  is curated seed text and `VendorSuggestion.url` is LLM-authored.
  Track O Phase 279 explicitly reserves stock levels and automatic
  purchase-order generation as "distinct from per-job sourcing". An
  "order" in this phase is therefore the existing line lifecycle, not a
  PO. The `vendors` / `inventory_items` tables from Phase 118 exist but
  are **disconnected from `parts`** (no FK, no code path) — out of scope.
- **`parts_arrived` has been waiting for this phase.** The Phase 170
  notification enum carries `parts_arrived` with no producer; Phase 199's
  ledger names "Phase 201+" as where it lands. The `received` transition
  is the natural producer.
- **Mobile — GREENFIELD.** No `Parts*` type in `api-types.ts`, no parts
  hook among the 31, no parts variant among the 7 `WorkOrderSection`
  kinds, and the on-hold placeholder copy is the only mention of parts
  in `WorkOrderDetailScreen`.
- **ADR-003 sighting.** A client-side cart spanning Browse → Cart → WO
  detail would hit the ≥3-screen state-store trigger exactly. The
  server-backed cart decision below is what keeps the ADR untripped.

**User decisions (2026-09-03):** "order" = the internal line lifecycle
(no supplier PO) · **the work order's open lines ARE the cart** — no
client store · AI sourcing stays CLI-side, out of the mobile MVP.

## Goal

A mechanic on a work order searches the catalog for the bike in front of
them, adds the parts it needs, and taps Order. The work order's parts
section is the cart: it survives an app kill, every shop member sees it,
and each line walks the existing lifecycle. When a part is marked
received, the assigned mechanic gets a push and the customer's
notification queue gets its first `parts_arrived` event.

CLI: none new. (`mark_part_installed` has no CLI despite the function
existing — noted for a follow-up, not this phase's problem.)

Run:
- Backend: `pytest tests/test_phase201_parts_api.py`
- Device smoke: search → add two lines → Order → mark one received via
  a second shop member → push lands on the phone.

Outputs:
- **Backend (branch `phase-201-parts-ordering`):**
  - `api/routes/parts.py`, all routes `require_tier("shop")` + membership
    via the `shop_mgmt` idiom:
    - `GET  /v1/shop/{shop_id}/parts/search` — `q`, `make`, `model`,
      `year`, `category`, `limit`; composes `search_parts` /
      `list_parts_for_bike`
    - `GET  /v1/shop/{shop_id}/parts/{part_id}` — `get_part` + `get_xrefs`
    - `GET  /v1/shop/{shop_id}/work-orders/{wo_id}/parts` —
      `list_parts_for_wo` (the cart)
    - `POST /v1/shop/{shop_id}/work-orders/{wo_id}/parts` —
      `add_part_to_work_order` (201)
    - `PATCH …/parts/{wop_id}` — quantity / unit-cost override
    - `DELETE …/parts/{wop_id}` — remove while `open`; `cancel` otherwise
    - `POST …/parts/{wop_id}/transition` — body `{action: Literal[
      "ordered","received","installed","cancel"]}`; **`received` fires
      `parts_arrived`** (170 queue for the customer + a new 199 push
      `notify_parts_arrived` to the assigned mechanic, self-suppressed)
    - `POST …/work-orders/{wo_id}/parts/order` — the Order button: every
      `open` line → `ordered`; returns the count
    - `GET  /v1/shop/{shop_id}/parts/needs` — `list_parts_for_shop_open_wos`
    - `POST /v1/shop/{shop_id}/parts/requisitions` · `GET …/requisitions`
      · `GET …/requisitions/{id}`
  - `openapi.py`: `parts` TAG_CATALOG entry
  - `push/events.py`: `notify_parts_arrived(wo, part_line, acting_user_id)`
  - tests: membership + tier gating on every route, cart round-trip,
    each lifecycle transition incl. the two illegal ones
    (`InvalidPartNeedTransition` → 409), bulk order counts only `open`
    lines, `received` produces exactly one queue row and one push,
    self-suppression, requisition round-trip, OpenAPI tag guard
- **Mobile (branch `phase-201-parts-ordering`):**
  - `api-schema` + `api-types` refresh (first `Parts*` types)
  - hooks: `useWorkOrderParts(shopId, woId)` (list · add · update ·
    remove · transition · orderAll, typed-error union in the
    `ShopAccessError` family), `usePartsSearch(shopId, vehicle)`
  - `buildWorkOrderSections`: **8th variant `parts`** (lines with status
    chips, quantities, cost; empty state "No parts yet")
  - `WorkOrderSectionCard`: renders the variant; per-line transition
    actions gated by status; **Order** action when any line is `open`
  - `PartsBrowseScreen` in `ShopStack`, entered from the WO detail
    section; search pre-filtered to the WO's bike; "Add to work order"
  - tests: both hooks vs fake api (incl. 409 → typed error), the section
    builder's parts variant + empty state, screen smoke, ADR-003 guard
    (no new store introduced — asserted by the absence of a
    `src/store` import, cheap and honest)

## Logic

- **Browse:** `search_parts` with the WO's `vehicle_make/model/year` as
  defaults so the first screen is already the right bike; free-text `q`
  narrows.
- **Cart:** `list_parts_for_wo` is the cart read; `add_part_to_work_order`
  is add-to-cart (a duplicate part on the same WO bumps quantity rather
  than adding a second line — surfaced in the response so the UI can say
  so); remove-while-open is a true delete, anything later is `cancel`.
- **Order:** bulk `mark_part_ordered` over the WO's `open` lines. Not a
  requisition: a requisition is the shop-wide consolidated snapshot and
  stays its own action.
- **Receive → notify:** `mark_part_received` succeeds → `trigger_notification(
  event="parts_arrived")` on the 170 queue (customer channel, still
  transport-less by design) + `notify_parts_arrived` push to
  `assigned_mechanic_user_id` unless they are the actor.
- **Authorization:** every route resolves shop membership exactly like
  `shop_mgmt.py` does today; the WO must belong to the shop
  (cross-shop → 404 per the existing enumeration posture).

## Key Concepts

- **Composition over construction.** The router adds no business rules;
  every branch calls a Track G function that already has its own tests.
  New behaviour is confined to two things: HTTP shape and the
  `parts_arrived` producer.
- **The cart is a view, not a thing.** `work_order_parts.status = 'open'`
  is the cart membership predicate. That is why no client store is
  needed and why ADR-003 stays untripped — record this in the ADR's
  running notes so the next "we need a store" conversation starts from
  the right precedent.
- **Literal discipline on the wire (F37).** `status` and `action` cross
  the contract boundary as `Literal[...]` unions mirroring the CHECK
  constraints, never `str`.
- **Producer, not transport.** Firing `parts_arrived` into the 170 queue
  does not send anything; nothing drains that queue yet (Track J). The
  mechanic push is the only thing a human sees today. Say so in the
  ledger to avoid a false "customers get notified" claim.

## Verification Checklist

- [ ] Every parts route rejects: no key (401), individual tier (402),
      non-member (403), other shop's WO (404)
- [ ] Cart round-trip: add → list shows line `open` → PATCH quantity →
      DELETE removes; add same part twice bumps quantity
- [ ] Transitions: `open→ordered→received→installed` each 200;
      `open→received` and `installed→ordered` → 409 with the mapped
      ProblemDetail; `cancel` from `open`/`ordered` → 200
- [ ] Bulk order marks only `open` lines and returns the count; a second
      call returns 0
- [ ] `received` creates exactly one `customer_notifications` row with
      `event='parts_arrived'` and one push to the assignee; actor ==
      assignee → no push; unassigned → no push
- [ ] Requisition create → list → show round-trip over HTTP
- [ ] OpenAPI: all parts paths carry the `parts` tag and `apiKey` security
- [ ] Backend full regression green on the canonical interpreter
- [ ] Mobile: hooks + builder + screen tests green; tsc clean; eslint 0
- [ ] No new client store (`src/store*` absent) — the ADR-003 guard
- [ ] Device smoke: browse → add → Order → second member marks received →
      push on the phone → WO section shows `received`

## Risks

- **Membership resolution is the whole security story** and it is copied
  from `shop_mgmt.py` twelve times. Factor one dependency
  (`require_shop_member(shop_id)`) rather than pasting; a single
  forgotten check is a cross-shop parts leak.
- **`add_part_to_work_order` defaults `created_by_user_id=1`.** The route
  must pass the real caller or every line looks minted by the seed user.
- **Cost columns are cents integers** and `unit_cost_cents_override` is
  nullable. The UI must format, never compute, and must not send `0`
  when it means "no override".
- **The 170 queue still has no transport.** Producing `parts_arrived` is
  correct and expected, but the ledger must not imply a customer was
  told anything.
- **Catalog coverage is thin for many bikes**, so the browse screen's
  empty state matters more than usual: it needs "no catalog match" copy
  and still let the mechanic add by searching more loosely — not a dead
  end.
- **Track O 279 overlap.** Stock, reorder points and PO generation are
  reserved there. This phase touches none of `vendors` /
  `inventory_items`, and the ledger should say so to keep the boundary
  visible.
