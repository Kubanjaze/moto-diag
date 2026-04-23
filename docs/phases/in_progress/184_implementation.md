# MotoDiag Phase 184 — Gate 9: Intake-to-Invoice Integration Test Through HTTP

**Version:** 1.0 | **Tier:** Gate | **Date:** 2026-04-23

## Goal

**Close Track H.** End-to-end integration test that walks a full
mechanic workflow from customer intake to paid invoice —
**entirely through HTTP**, using only the endpoints Phase 175-183
shipped. Gate 8 (Phase 174) proved the same workflow works through
CLI; Gate 9 proves it works through the API surface that Track I
mobile + external consumers will use.

When Gate 9 passes green, Track H is closed and Track I (mobile
app) opens with a known-good HTTP contract.

CLI — none. Gate 9 is pure API exercise.

Outputs (~550 LoC test + ~180 LoC closure doc):
- `tests/test_phase184_gate9.py` (~550 LoC, ~20 tests across 5
  classes):
  - `TestGate9HappyPath` — one big `TestClient` walk from signup
    to paid invoice, hitting every Track H sub-surface.
  - `TestGate9CrossUserIsolation` — two users' garages + sessions
    don't cross-pollinate.
  - `TestGate9CrossShopIsolation` — two shops' WOs + invoices stay
    separated; the 403 boundary holds.
  - `TestGate9OpenAPIContract` — the spec at `/openapi.json`
    still contains the 10-tag catalog + 2 security schemes + 7
    reusable error responses after all routers mount (no
    regression from Phase 183).
  - `TestGate9AntiRegression` — SCHEMA_VERSION == 38 (Gate 9 ships
    no migrations), closure doc exists, Track H summary doc
    exists.
- `docs/phases/completed/TRACK_H_SUMMARY.md` (~180 LoC) — Track H
  closure document. 9 phases, 57 HTTP + 1 WS endpoints, design
  pillars (auto-mapped domain exceptions, compose-over-duplicate
  routers, scope-as-code, renderer-ABC, spec-as-single-source-of-
  truth), known limitations → Track I seeds.

No migration, no schema change, no new production code. Gate 9 is
a test + documentation closure, identical in shape to Gate 8.

## Logic

### End-to-end HTTP walk (`TestGate9HappyPath`)

The test walks these steps using a single `TestClient(app)` and a
fresh tmp_path DB. All steps are HTTP; all auth is via API key.
Comments on the right indicate the Phase that shipped each step.

1. Create an anonymous user row + API key directly in the DB        (Phase 176 fixture)
2. Create an active subscription row (`shop` tier)                   (Phase 176 fixture)
3. `POST /v1/shop/profile` → create shop                             (Phase 180)
4. Seed first shop owner via `seed_first_owner` direct call          (Phase 172 fixture)
5. `POST /v1/shop/{id}/customers` → create customer                  (Phase 180)
6. `POST /v1/vehicles` → register a bike                             (Phase 177)
7. `POST /v1/sessions` → start a diagnostic session                  (Phase 178)
8. `POST /v1/sessions/{id}/symptoms` → add 2 symptoms                (Phase 178)
9. `POST /v1/sessions/{id}/fault-codes` → add 2 DTC codes            (Phase 178)
10. `PATCH /v1/sessions/{id}` → set diagnosis + confidence + severity (Phase 178)
11. `GET /v1/reports/session/{id}/pdf` → download session report     (Phase 182)
12. Assert PDF starts with `%PDF-`.
13. `GET /v1/kb/dtc/P0171` → look up a DTC                           (Phase 179)
14. `GET /v1/kb/search?q=idle` → unified search                      (Phase 179)
15. `POST /v1/sessions/{id}/close` → close the session               (Phase 178)
16. `POST /v1/shop/{id}/work-orders` → create WO                     (Phase 180)
17. `POST /v1/shop/{id}/work-orders/{wo_id}/transition` → open       (Phase 180)
18. `POST /v1/shop/{id}/work-orders/{wo_id}/transition` → start      (Phase 180)
19. `POST /v1/shop/{id}/issues` → add issue to WO                    (Phase 180)
20. `POST /v1/shop/{id}/work-orders/{wo_id}/transition` → complete   (Phase 180)
21. `POST /v1/shop/{id}/invoices/generate` → generate invoice        (Phase 180)
22. `GET /v1/reports/work-order/{wo_id}/pdf` → download WO receipt   (Phase 182)
23. `GET /v1/reports/invoice/{inv_id}/pdf` → download invoice PDF    (Phase 182)
24. `GET /v1/shop/{id}/analytics/snapshot` → shop dashboard          (Phase 180)
25. Assert the snapshot's throughput count includes the completed WO.
26. `GET /v1/version` → metadata (sanity)                            (Phase 175)
27. `GET /openapi.json` → spec (sanity)                              (Phase 183)

Each step asserts the response status code (201 for POSTs, 200
for GETs, 422 never hit), payload keys (id > 0, status correct),
and a couple of structural invariants (WO status after each
transition, invoice `subtotal_cents` = 2h × $100/h = $200).

### Cross-user isolation (`TestGate9CrossUserIsolation`)

Two separate users, each with their own API key:
1. User A creates a vehicle + session.
2. User B tries `GET /v1/vehicles/{A's-vehicle-id}` → 404.
3. User B tries `GET /v1/reports/session/{A's-session-id}` → 404.

Exercises the owner-scoping + 404-for-enumeration policy across
two independent Track H routes (Phase 177 vehicles + Phase 182
reports using Phase 178 sessions).

### Cross-shop isolation (`TestGate9CrossShopIsolation`)

Two shops, two owners, no cross-membership:
1. Shop A creates WO → generates invoice.
2. Shop B's owner tries `GET /v1/reports/work-order/{A's-wo-id}/pdf` → 403.
3. Shop B's owner tries `GET /v1/reports/invoice/{A's-inv-id}/pdf` → 403.
4. Shop B's owner tries `POST /v1/shop/{A-shop-id}/work-orders` → 403.

Exercises the `require_tier` + shop-membership layer across
Phase 180 + Phase 182.

### OpenAPI contract regression (`TestGate9OpenAPIContract`)

- All 10 tags from `TAG_CATALOG` still appear in the emitted spec.
- All 7 error responses still in `components.responses`.
- apiKey + bearerAuth security schemes still in place.
- Every `/v1/*` path still has security attached (except `/v1/version`).

### Anti-regression (`TestGate9AntiRegression`)

- `SCHEMA_VERSION == 38` — Gate 9 ships no migrations.
- `docs/phases/completed/TRACK_H_SUMMARY.md` exists and contains
  the phrase "Track H closed".
- `docs/phases/completed/184_implementation.md` exists (so the
  closure gate's own docs are committed).

## Key Concepts

- **FastAPI `TestClient(app)`** — synchronous HTTP client that
  threads through the full middleware stack. Same semantics as
  `requests.Session` against a live uvicorn instance, but in-
  process so no socket or subprocess is involved.
- **Settings `db_path_override` seam** — `create_app(db_path_override=...)`
  gives the test a temp DB per test; FastAPI rebuilds the
  dependency graph with the override so every route uses the test
  DB.
- **In-test DB seeding for fixture scope** — some setup (users,
  API keys, shop memberships) is more honest via direct repo
  calls than constructing the full HTTP auth flow. Rationale:
  those API surfaces are owned by Track I (not yet built).
- **Zero-migration gate** — a closure gate proves integration
  *of existing code*. It must not require schema changes; if the
  gate test exposes a gap that needs new code, the gap becomes
  its own phase, not part of Gate 9.
- **Response-status invariants** — Gate 9 treats any non-2xx
  status mid-walk as a hard failure with a detailed message. No
  "soft" assertions; a successful Gate 9 run means Track H is
  genuinely shippable.

## Verification Checklist

- [ ] `TestGate9HappyPath.test_full_lifecycle` walks 27 HTTP calls
      and produces a paid invoice.
- [ ] Session report PDF downloads and starts with `%PDF-`.
- [ ] Work-order report PDF downloads and starts with `%PDF-`.
- [ ] Invoice report PDF downloads and starts with `%PDF-`.
- [ ] Analytics snapshot reflects the completed WO.
- [ ] Cross-user vehicle access → 404.
- [ ] Cross-user session report → 404.
- [ ] Cross-shop WO report → 403.
- [ ] Cross-shop invoice report → 403.
- [ ] Cross-shop WO creation → 403.
- [ ] OpenAPI spec still has all 10 tags + 7 error responses + 2
      security schemes.
- [ ] SCHEMA_VERSION == 38.
- [ ] `TRACK_H_SUMMARY.md` exists.
- [ ] Phase 175-183 still GREEN.
- [ ] Full Track H regression after Gate 9 merge is 291 + Gate 9
      tests all green.
- [ ] Zero AI calls.

## Risks

- **Fragile fixture chains** — seeding an owner + customer +
  vehicle + session + WO + invoice across ~10 direct repo calls
  risks breaking when any of those repos' signatures shift. Fix
  on shift is to update the fixture; tests don't assert on
  fixture internals.
- **Phase 180's issues endpoint path** — the exact POST path for
  adding an issue to a WO was confirmed during build (might be
  `/v1/shop/{id}/issues` or `/v1/shop/{id}/work-orders/{wo_id}/issues`
  depending on how Phase 180 shaped the router; test asserts the
  actual path).
- **PDF content assertions** — Gate 9 only asserts PDF magic
  bytes + length > 500. Deeper content checks live in the
  per-phase test suite.
- **Rate limiter in tests** — the 9999/min ceiling for test
  tiers (set in `api_db` fixtures) is already proven from prior
  phases; Gate 9 reuses that pattern.
