# MotoDiag Phase 180 — Shop Management Endpoints

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-04-22

## Goal

Expose the Track G shop-management console (16 subgroups, 123
subcommands) over HTTP. Scope is **pragmatic mapping** — the core
CRUD + lifecycle surface a web or mobile client actually needs, not
a 1:1 for every CLI subcommand. Phase 181+ can layer the long tail
if product demand emerges.

All endpoints require **`require_tier("shop")`** — shop management
is a paid-tier feature. `company` tier satisfies via the Phase 176
tier ordering (`individual < shop < company`). `individual` tier
gets 402.

**No migration.** Phase 160-173 already shipped every table + repo.
Phase 180 is pure routing — composes existing `motodiag.shop.*`
functions into HTTP endpoints. Cross-shop 404 via Phase 172's RBAC
(`require_shop_membership` or direct `has_shop_permission` check).

Outputs (~640 LoC + ~40 tests):
- `src/motodiag/api/routes/shop_mgmt.py` (~640 LoC) — 24 endpoints.
- `src/motodiag/api/app.py` — mount the router.
- `src/motodiag/api/routes/shops.py` — Phase 175's smoke route
  replaced by the fuller router; keep `GET /v1/shops/{id}` semantics.
- No migration. SCHEMA_VERSION stays at 38.
- `tests/test_phase180_shop_api.py` (~40 tests).

## Endpoint Map

**Profile (3):**
- `GET    /v1/shop/profile/list`
- `POST   /v1/shop/profile`
- `GET    /v1/shop/profile/{shop_id}`
- `PATCH  /v1/shop/profile/{shop_id}`

**Members (3):** (Phase 172 RBAC — shop owners manage)
- `GET    /v1/shop/{shop_id}/members`
- `POST   /v1/shop/{shop_id}/members`
- `DELETE /v1/shop/{shop_id}/members/{user_id}`

**Customers (3):**
- `GET    /v1/shop/{shop_id}/customers`
- `POST   /v1/shop/{shop_id}/customers`
- `GET    /v1/shop/{shop_id}/customers/{id}`

**Intake (2):**
- `GET    /v1/shop/{shop_id}/intakes`
- `POST   /v1/shop/{shop_id}/intakes`

**Work orders (4):**
- `GET    /v1/shop/{shop_id}/work-orders`
- `POST   /v1/shop/{shop_id}/work-orders`
- `GET    /v1/shop/{shop_id}/work-orders/{id}`
- `POST   /v1/shop/{shop_id}/work-orders/{id}/transition` (body:
  `{action: "open"|"start"|"pause"|"resume"|"complete"|"cancel"|"reopen"}`)

**Issues (2):**
- `GET    /v1/shop/{shop_id}/issues`
- `POST   /v1/shop/{shop_id}/issues`

**Invoices (2):**
- `GET    /v1/shop/{shop_id}/invoices`
- `POST   /v1/shop/{shop_id}/invoices/generate` (body:
  `{work_order_id}` → calls Phase 169 `generate_invoice_for_wo`)

**Notifications (2):**
- `GET    /v1/shop/{shop_id}/notifications`
- `POST   /v1/shop/{shop_id}/notifications/trigger`

**Analytics (3):**
- `GET    /v1/shop/{shop_id}/analytics/snapshot?since=30d`
- `GET    /v1/shop/{shop_id}/analytics/revenue?since=30d`
- `GET    /v1/shop/{shop_id}/analytics/top-issues?since=30d`

Total: **24 endpoints across 9 sub-surfaces.**

## Shop-scope authorization

Every `{shop_id}`-scoped route goes through
`require_shop_access(shop_id)` — a helper that checks:
1. `get_current_user()` resolves the caller (401 if not).
2. `require_tier("shop")` passes (402 if below).
3. `has_shop_permission(shop_id, user.id, "read_shop" or
   "manage_shop")` — the Phase 172 RBAC check (403 if not a member
   of this shop).

Cross-shop attempts → 403 (distinct from 404 for nonexistent shop)
because Phase 172's RBAC API is explicit: `PermissionDenied` exists
and maps naturally to 403.

## Pragmatic omissions (Phase 181+ scope)

- **Parts / sourcing / labor estimator / bay scheduler / triage /
  priority / rules** — all Track G's AI-driven or complex-workflow
  subgroups. Deferred to Phase 181+ when the mobile app actually
  needs them. Phase 174's Gate 8 CLI integration test already
  proves they work end-to-end; Phase 184's Gate 9 API test will
  exercise the HTTP surface.
- **Work order CRUD `DELETE`** — Track G doesn't expose delete
  (WOs use cancel lifecycle). Matches here.
- **Notification mark-sent** — Phase 170 queue management. Defer.

## Verification Checklist

- [ ] Unauthenticated → 401 across every endpoint.
- [ ] Individual-tier caller → 402 (no shop access).
- [ ] Shop-tier caller who isn't a member of `shop_id` → 403.
- [ ] Owner of `shop_id` → 200 on reads + writes.
- [ ] POST `/v1/shop/profile` creates shop + stamps caller as owner
      via `seed_first_owner` (Phase 172).
- [ ] Work-order `transition` endpoint dispatches to the 7 Phase
      161 lifecycle functions correctly.
- [ ] Invoice generation composes Phase 169 end-to-end.
- [ ] Analytics snapshot composes Phase 171 rollups.
- [ ] Phase 175-179 still GREEN.
- [ ] Zero AI calls.

## Risks

- **Cross-shop 404 vs 403 tension.** Vehicles + sessions use 404 for
  both nonexistent and cross-user (enumeration prevention). Shops
  are global-registry entities (owner creates them under a public
  name), so 403 for "you're not a member" is the honest response.
  Document this in the endpoint map so it doesn't surprise callers.
- **Transition-action endpoint union.** One POST body accepts 7
  action strings. Alternative: 7 POST endpoints. The union keeps
  the route surface cleaner; Pydantic `Literal` validates at
  boundary. Tests cover invalid action strings (422).
- **Profile/create races.** If two callers POST the same shop name,
  Phase 160 `create_shop` raises `ShopNameExistsError` (409 in
  Phase 175 error map). Tests verify.
