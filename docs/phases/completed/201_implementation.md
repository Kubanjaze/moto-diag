# Phase 201 — Parts Ordering from Mobile

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-09-04 (v1.0 plan 2026-09-03)

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

- [x] Every parts route rejects: no key (401), individual tier (402),
      non-member (403), other shop's WO (404) — and a part LINE from a
      different WO is 404 too, so a line id cannot be edited across WOs
- [x] Cart round-trip: add → list → PATCH quantity → DELETE; adding the
      same part twice bumps quantity and returns 200 + `merged: true`
- [x] Transitions: `open→ordered→received→installed` each 200; skipping
      a step and going backwards each 409 through the existing
      ProblemDetail mapping; `cancel` from open/ordered 200
- [x] Bulk order marks only `open` lines and returns the count; the
      second press returns 0
- [x] `received` creates exactly one `parts_arrived` queue row and one
      push to the assignee; actor == assignee → no push; unassigned →
      no push; a customer with no email is NOT an error
- [x] Requisition create → list → show over HTTP; another shop's
      requisition is 404
- [x] OpenAPI: every parts path carries the `parts` tag and `apiKey`
      security; `/parts/requisitions` is not swallowed by
      `/parts/{part_id}`
- [x] Backend full regression green on the canonical interpreter
- [x] Mobile: hooks + builder + screen tests green; tsc clean; **eslint
      0 errors repo-wide** (which required fixing a pre-existing Phase
      187 error `eslint .` had been carrying — see Deviations)
- [x] No new client store — the cart is server state, ADR-003 untripped
- [~] Device smoke: **the parts_arrived push was verified landing on the
      real phone through live APNs.** The in-app browse → add → Order
      journey could NOT be exercised: the tailnet the app's baked
      `API_BASE_URL` points at stopped routing partway through the
      session (see Deviations). Everything behind that URL was verified
      over HTTP instead.

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

## Deviations from Plan

- **No migration, as predicted — but also no new domain logic at all.**
  The plan called this "composition"; it turned out to be stricter than
  that. Every branch calls a Track G function. The only new backend
  behaviour is the `parts_arrived` producer and two compositions the
  domain layer does not do: add-dedupe (bump an existing open line
  rather than grow a second) and delete-vs-cancel by status.
- **The plan's "AI sourcing out of MVP" held**, and `vendors` /
  `inventory_items` were not touched, keeping the Track O 279 boundary
  intact.
- **A latent bug in existing code was found and NOT fixed** (filed as
  F58): `list_parts_for_shop_open_wos` calls
  `get_xrefs(part_id)` where the function takes an *OEM part number*,
  then reads `role` / `part` keys it never returns — inside a bare
  `except: pass`. So `oem_cost_cents` / `aftermarket_cost_cents` on
  every `ConsolidatedPartNeed` have always been `None`. Out of this
  phase's scope, and changing those values could move things other
  tests pin.
- **F57, found by smoking this phase, was fixed in its own commit.**
  The serve log had no application log lines at all, ever:
  `uvicorn.run(log_level=...)` configures uvicorn's own loggers, and
  every `motodiag.*` logger inherits root (WARNING, no handler), so
  INFO was discarded while `logger.exception` still surfaced via the
  last-resort handler. That made **F52's "a successful push leaves a
  trace" false in production** while its test passed, because
  `caplog.at_level` forces the level the server never set.
- **An unrelated pre-existing lint error was fixed in its own commit.**
  `eslint .` had been red since Phase 187 (`Buffer` undefined in a Node
  build script linted with the RN config) while every commit passed,
  because `lint-staged` only lints STAGED files. Worth knowing: the
  repo's lint gate has never covered unstaged or untouched files.
- **Two first-run test failures were fixture bugs worth recording**, not
  route bugs: catalog `make` is stored lowercased by `add_part`, so
  seeding "Honda" makes fitment search silently return nothing; and
  `create_work_order` lands in `draft`, which the shop-wide
  consolidation excludes, so a draft WO contributes nothing to needs or
  requisitions.
- **Device smoke was split by an environment failure.** The push half
  was verified on the real phone (APNs does not use the tailnet). The
  in-app half could not run: the Mac's tailnet stopped routing mid-
  session — `tailscale status` reports Running and online, `tailscale
  serve` still shows the proxy config, the backend listens on `*:8000`
  and answers on loopback, but both the `ts.net` name and the raw
  tailnet IP time out. The documented remedy
  (`dev_loop_wireless_parked.md`) is a System Settings VPN toggle or a
  reboot, which is the user's call.

## Results

| Metric | Value |
|--------|-------|
| Backend new tests | 37 (`test_phase201_parts_api.py`) + 3 (F57) |
| Backend full regression | **4702 passed, 0 failed, 5 skipped** (8:36) |
| Mobile new tests | +20 → 73 suites / 896 green |
| Mobile static checks | tsc clean · eslint 0 errors repo-wide |
| New HTTP surface | 12 routes, 0 migrations |
| Domain functions newly reachable from the app | 18 (all of `parts_needs`) + 4 catalog readers |
| Smoke | browse-by-bike 5 parts · dedupe `merged: true` · cart $155.96 · Order 2 then 0 · illegal skip 409 · `parts_arrived` queued to the right recipient · **push landed on the phone via live APNs** |
| Follow-ups filed | F57 (residual), F58, F59 |

**Key finding:** the phase's own smoke is what caught the more serious
bug, and it was not in this phase's code. Chasing a missing
`parts_arrived` log line exposed that the server had never emitted a
single application log line — which meant a fix shipped two phases ago
(F52's "log successful pushes") had been inert in production while its
test passed. A test that forces the log level cannot see a server that
never sets one. That is the same verify-the-artifact-not-the-settings
lesson Phase 199 wrote down, arriving a third time, and it argues for
smoking the observability, not just the behaviour.
