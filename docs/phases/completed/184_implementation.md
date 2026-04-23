# MotoDiag Phase 184 — Gate 9: Intake-to-Invoice Integration Test Through HTTP

**Version:** 1.1 | **Tier:** Gate | **Date:** 2026-04-23

## Goal

**Close Track H.** End-to-end integration test that walks a full
mechanic workflow from customer intake to paid invoice —
**entirely through HTTP**, using only the endpoints Phases
175-183 shipped. Gate 8 (Phase 174) proved the same workflow
works through CLI; Gate 9 proves it works through the API
surface that Track I mobile + external consumers will use.

Gate 9 green → Track H closed → Track I opens.

CLI — none. Gate 9 is pure API exercise.

Outputs (832 LoC total: 618 test + 214 closure doc; no production
code):
- `tests/test_phase184_gate9.py` (618 LoC, 10 tests across 5
  classes):
  - `TestGate9HappyPath` ×1 — one `TestClient` walk from shop
    signup to paid invoice, 27 HTTP calls hitting every Track H
    sub-surface.
  - `TestGate9CrossUserIsolation` ×1 — User B cannot see User A's
    vehicles (404) or session reports (404).
  - `TestGate9CrossShopIsolation` ×1 — Shop B cannot access Shop
    A's WO / invoice reports (403), cannot list Shop A's WOs (403),
    cannot create WOs in Shop A (403).
  - `TestGate9OpenAPIContract` ×4 — Phase 183 enrichment still
    intact: 10 tags, 7 error responses, 2 security schemes,
    apiKey attached to authed endpoints.
  - `TestGate9AntiRegression` ×3 — SCHEMA_VERSION == 38,
    `TRACK_H_SUMMARY.md` exists in `completed/`, Phase 184
    implementation doc exists.
- `docs/phases/completed/TRACK_H_SUMMARY.md` (214 LoC) — Track H
  closure document: 9-phase inventory table + sub-surface
  breakdown, 8 design pillars (auto-mapped domain exceptions,
  compose-don't-duplicate routers, scope-as-code, renderer ABC,
  spec-as-SSOT, factory-pattern transports, hard-paywall-soft-
  discovery, RFC 7807 + correlation IDs), mechanic-facing
  workflow map (18 HTTP steps matching Gate 8's CLI walk), known
  limitations organized by which future track resolves them
  (Track I signup/files/photo-ID, Track J multi-worker state +
  transport worker + IP rate limiting, post-Gate-9 OBD hardware
  + OpenAPI docs site + PDF branding).

No migration, no production code — Gate 9 proves integration of
existing Phase 175-183 code. Schema stays at 38.

## Logic

### End-to-end happy-path HTTP walk (27 steps)

Single `TestClient(app)` + fresh tmp_path DB. All auth via API
key header. Bootstrap (user row, API key, subscription, shop
membership) seeds via direct repo calls — those surfaces are
owned by Track I.

1. `GET /v1/version` — public sanity + schema version (meta).
2. `POST /v1/shop/profile` — create shop → `{"id": N}`.
3. Seed owner membership via direct `seed_first_owner` call
   (Track I owns `POST /v1/auth/signup` wiring).
4. `POST /v1/shop/{id}/customers` — create customer "Alice Rider".
5. `POST /v1/vehicles` — register Honda CBR600 (2005) in garage.
6. `POST /v1/sessions` — start diagnostic session for the CBR
   with one seed symptom + one seed DTC.
7. `POST /v1/sessions/{id}/symptoms` — append second symptom.
8. `POST /v1/sessions/{id}/fault-codes` — append second DTC.
9. `PATCH /v1/sessions/{id}` — set diagnosis + confidence 0.85 +
   severity medium + cost estimate $180.
10. `GET /v1/reports/session/{id}/pdf` — download DIY session
    report PDF (owner-scope, no tier required).
11. `GET /v1/kb/dtc/P0171` — DTC lookup.
12. `GET /v1/kb/search?q=idle` — unified KB search.
13. `POST /v1/sessions/{id}/close` — archive session.
14. `POST /v1/shop/{id}/work-orders` — schedule repair (2.0h
    estimate, priority 3).
15. `POST /v1/shop/{id}/work-orders/{wo}/transition {action: "open"}`.
16. `POST /v1/shop/{id}/work-orders/{wo}/transition {action: "start"}`.
17. `POST /v1/shop/{id}/issues` — log "Fuel filter heavily clogged"
    issue against the WO (category `fuel_system`, severity medium).
18. `POST /v1/shop/{id}/work-orders/{wo}/transition
    {action: "complete", actual_hours: 2.0}`.
19. `POST /v1/shop/{id}/invoices/generate` — bill at $100/hr
    labor + 8.25% tax. Asserts `subtotal_cents == 20000`.
20. `GET /v1/reports/work-order/{wo}/pdf` — receipt PDF.
21. `GET /v1/reports/invoice/{inv}/pdf` — invoice PDF.
22. `GET /v1/reports/invoice/{inv}` — JSON preview sanity
    (Totals section present).
23. `GET /v1/shop/{id}/analytics/snapshot` — dashboard rolls up
    the completed WO.
24. `GET /v1/sessions` — list surfaces the closed one + shop-tier
    quota metadata (limit == 500).
25. `GET /v1/vehicles` — listing surfaces the CBR.
26. `GET /v1/shop/{id}/invoices` — list has the generated invoice.
27. `GET /openapi.json` — spec sanity (Phase 183 enrichment
    intact: servers array, `info.license.name == "MIT"`).

Each step asserts HTTP status + 1-2 structural invariants on the
response body. A non-2xx mid-walk fails the gate.

### Cross-user isolation (`TestGate9CrossUserIsolation`)

Two users, two API keys, no shared state:
- User B gets 404 on User A's `/v1/vehicles/{id}` and
  `/v1/reports/session/{id}` and `/v1/reports/session/{id}/pdf`.
- User B's `/v1/vehicles` + `/v1/sessions` listings return
  empty item arrays (owner-scoped queries).

Exercises Phase 177 (vehicles) + Phase 178 (sessions) +
Phase 182 (reports owner-scoped). 404-not-403 policy prevents
enumeration attacks.

### Cross-shop isolation (`TestGate9CrossShopIsolation`)

Two shops, two shop-tier owners with no cross-membership:
- Shop B's owner gets 403 on Shop A's
  `/v1/reports/work-order/{wo}` (both preview + PDF).
- Shop B's owner gets 403 on Shop A's
  `/v1/reports/invoice/{inv}/pdf`.
- Shop B's owner gets 403 on `/v1/shop/{A-shop-id}/work-orders`
  (list) and `POST /v1/shop/{A-shop-id}/work-orders` (create).

Exercises Phase 172 RBAC + Phase 180's `require_shop_access` +
Phase 182's `_require_member` gate.

### OpenAPI contract regression (`TestGate9OpenAPIContract`)

All four assertions walk the /openapi.json response:
- 10 tags from `TAG_CATALOG` all present.
- 7 error responses from `ERROR_RESPONSES` all in
  `components.responses`.
- 2 security schemes from `SECURITY_SCHEMES`.
- `/v1/vehicles` GET has `apiKey` in its `security` array.

Catches any drift in Phase 183's enrichment when new routes mount.

### Anti-regression (`TestGate9AntiRegression`)

- `SCHEMA_VERSION == 38` — Gate 9 ships no migrations.
- `TRACK_H_SUMMARY.md` exists in `completed/` and contains the
  phrase "Track H closed".
- `184_implementation.md` exists in either `completed/` or
  `in_progress/` (tolerates pre-finalization state during build).

## Key Concepts

- **FastAPI `TestClient(app)`** — synchronous HTTP client
  threading through the full middleware stack. Same semantics as
  `requests.Session` against uvicorn, but in-process.
- **Settings `db_path_override` seam** —
  `create_app(db_path_override=...)` gives the test a temp DB per
  test; FastAPI rebuilds the dependency graph with the override.
- **In-test DB seeding for bootstrap flows** — user rows + API
  keys + subscriptions + shop memberships seed via direct repo
  calls because those API surfaces are Track I's scope. Gate 9
  asserts what exists today.
- **Zero-migration gate** — closure gates prove integration *of
  existing code*. If the gate test exposes a gap that needs new
  code, the gap becomes its own phase, not part of Gate 9.
- **Response-status invariants** — any non-2xx mid-walk fails
  the gate. No "soft" assertions; green means Track H is
  genuinely shippable.

## Verification Checklist

- [x] `TestGate9HappyPath.test_full_lifecycle` walks 27 HTTP
      calls and produces a paid invoice with correct totals.
- [x] Session report PDF downloads, starts with `%PDF-`,
      has `session-{id}` in Content-Disposition.
- [x] Work-order report PDF downloads, starts with `%PDF-`,
      has `work-order-{id}` in Content-Disposition.
- [x] Invoice report PDF downloads and starts with `%PDF-`.
- [x] Analytics snapshot reflects the completed WO.
- [x] Cross-user vehicle access → 404.
- [x] Cross-user session report (preview + PDF) → 404.
- [x] Cross-user vehicle / session listings are empty for User B.
- [x] Cross-shop WO report (preview + PDF) → 403.
- [x] Cross-shop invoice PDF → 403.
- [x] Cross-shop `/v1/shop/{A}/work-orders` (list) → 403.
- [x] Cross-shop `POST /v1/shop/{A}/work-orders` → 403.
- [x] OpenAPI spec has all 10 tags + 7 error responses + 2
      security schemes.
- [x] SCHEMA_VERSION == 38.
- [x] `TRACK_H_SUMMARY.md` exists with "Track H closed" phrase.
- [x] Phase 175-183 still GREEN — full Track H regression
      (175-184): 301/301 in 6m 02s (362.14s).
- [x] Zero AI calls.

## Risks

- **Fragile fixture chains** — bootstrapping via ~8 direct repo
  calls risks breaking when those repos' signatures shift. Fix
  on shift is update the fixture; tests don't assert on fixture
  internals.
- **Phase 180's issue endpoint path** — confirmed during build:
  `POST /v1/shop/{shop_id}/issues` (shop-scoped, not
  WO-nested). Gate 9 uses that path.
- **PDF content assertions** — Gate 9 only asserts PDF magic
  bytes + length > 500. Deeper content checks live in Phase 182
  tests.
- **Rate limiter in tests** — the 9999/min ceiling for test
  tiers (set via MOTODIAG_RATE_LIMIT_*_PER_MINUTE env vars in
  the `api_db` fixture) is already proven from prior phases.

## Deviations from Plan

1. **10 tests vs ~20 planned.** The plan imagined one test per
   step; in practice each test class's single test walks many
   endpoints, which matches the Gate 8 pattern and is the right
   shape for an integration gate. Class counts: HappyPath×1 +
   CrossUserIsolation×1 + CrossShopIsolation×1 +
   OpenAPIContract×4 + AntiRegression×3 = 10.

2. **`/v1/version` response shape correction.** Plan assumed the
   response had a `version` key; actual shape is
   `{"api_version", "package", "schema_version"}`. One-line fix
   in the first assertion of the happy-path walk; documented
   here because future phases touching `/v1/version` should
   match this shape.

3. **Bootstrap via direct repo calls is explicit in the plan.**
   Not a deviation per se, but worth flagging: the gate test
   composes `_make_user`, `_make_sub`, `_seed_membership` as
   direct-call helpers since Track I owns signup/checkout/
   membership flows. Gate 9 proves Phases 175-183 work end-to-
   end; Track I's gate (future) will prove signup → checkout →
   membership assignment.

4. **Closure doc deviation.** Track H SUMMARY doc ships at 214
   LoC vs ~180 planned because the 8-design-pillar section +
   the known-limitations-by-future-track breakdown deserved
   more detail than the plan anticipated. The doc is the
   handoff to Track I — shortcuts here cost future time.

## Results

| Metric                              | Value                       |
|-------------------------------------|-----------------------------|
| Test LoC                            | 618                         |
| Summary doc LoC                     | 214                         |
| Grand total                         | 832                         |
| Production LoC                      | 0                           |
| Tests                               | 10 GREEN                    |
| Phase 184 test runtime              | 18.22s                      |
| Track H full regression (175-184)   | 301/301 GREEN (6m 02s)      |
| Schema version                      | 38 (unchanged)              |
| Migration                           | None                        |
| AI calls                            | 0                           |
| Network calls                       | 0                           |
| Track H phase count                 | 10 (175-184 inclusive)      |
| Track H HTTP endpoints              | 57                          |
| Track H WebSocket endpoints         | 1                           |
| Track H sub-surfaces                | 10                          |
| Project version                     | 0.12.7 → 0.13.0 (Track H closed) |

**Full Track H regression (phases 175-184): 301 / 301 GREEN in
6m 02s (362.14s). Zero regressions. Track H closes green.**

**Key finding:** Track H closes the "API surface" story for
MotoDiag. The 57 HTTP endpoints + 1 WebSocket + fully-documented
OpenAPI 3.1 spec is a contract Track I can consume without
needing to revisit Track H code. The 8 design pillars captured
in `TRACK_H_SUMMARY.md` are the load-bearing patterns —
auto-mapped exceptions, compose-don't-duplicate routers,
scope-as-code, renderer ABC, spec-as-SSOT — that make future
endpoint work small. Gate 9's 10 tests took 832 LoC total
(618 test + 214 doc) with zero production code changes. When
Track I mobile starts, the engineer can open `TRACK_H_SUMMARY.md`
+ `/openapi.json` and build confidently.
