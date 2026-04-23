# Track H — API + Web Layer — Closure Summary

**Status:** ✅ **Track H closed** at Phase 184 / Gate 9 on 2026-04-23.
**Phases:** 175 → 184 (10 phases, including Gate 9).
**Endpoints:** 57 HTTP + 1 WebSocket across 10 sub-surfaces.
**Test count at closure:** 311 phase-specific tests + Gate 9.
**Schema version at closure:** 38 (Track H added 2 migrations: 037
+ 038; Phases 179-184 all shipped migration-free).
**Project version at closure:** 0.12.7+ (Gate 9 bumps to 0.13.0
on Track H closure).

MotoDiag opened Track H as a local-CLI-only tool with 174 phases
of substrate behind it (Tracks A–G). Track H grafted a real HTTP
API on top of that substrate without rewriting any of it: every
route is a thin (~5 line) translation from a domain repo call to
a JSON response, every domain exception auto-maps to an RFC 7807
ProblemDetail body, every endpoint is paywall-gated by a single
dependency declaration. When Track I (mobile app) opens, it has
57 endpoints + a fully-documented OpenAPI spec to consume.

---

## Phase inventory

| Phase | Title | Endpoints added | Migrations |
|------:|-------|----------------:|------------|
| 175 | FastAPI scaffold + /healthz + /v1/version + smoke shop route | 4 | — |
| 176 | Auth + API keys + Stripe + hard paywall | +4 (billing) | 037 |
| 177 | Vehicle endpoints — first full-CRUD domain router | +6 | 038 |
| 178 | Diagnostic session endpoints + monthly quota | +9 | — |
| 179 | KB endpoints — DTC / symptoms / known-issues / unified search | +7 | — |
| 180 | Shop management endpoints — Track G's CLI mapped onto HTTP | +24 | — |
| 181 | WebSocket live data endpoint — first non-CRUD surface | +1 WS | — |
| 182 | PDF report generation endpoints | +6 | — |
| 183 | OpenAPI enrichment + spec polish | 0 (spec-only) | — |
| 184 | **Gate 9 — intake-to-invoice integration test through HTTP** | 0 (test-only) | — |

**Sub-surface breakdown at closure:**
- `meta` — `/healthz`, `/v1/version`
- `auth` — API keys + subscription management (CLI + future HTTP)
- `shops` — global shop registry read
- `billing` — Stripe checkout + portal + webhooks
- `vehicles` — caller's garage (6 CRUD)
- `sessions` — diagnostic session lifecycle (9)
- `knowledge-base` — DTC / symptom / issue lookups (7)
- `shop-management` — full operator console (24)
- `reports` — JSON + PDF reports (6)
- `live` — WebSocket OBD stream (1)

---

## 8 design pillars

These patterns crystallized across Phases 175-184 and should
shape Track I + future API work.

### 1. Auto-mapped domain exceptions
Route handlers raise the *domain* exception (e.g.
`SessionOwnershipError`, `WorkOrderNotFoundError`,
`PermissionDenied`) and a global registered handler in
`api/errors.py` maps it to the right HTTP status with an RFC 7807
`ProblemDetail` body. Routes contain zero `try/except` /
`HTTPException` boilerplate. Adding a new domain exception is a
one-line addition to `_exc_class_chain()` in `api/errors.py`.

### 2. Compose-don't-duplicate routers
Phase 180 ships 24 endpoints in 838 LoC by dispatching to existing
Track G repos rather than re-implementing logic. Phase 182's
report builders compose Phase 178 / 169 / 160 reads. Phase 184's
gate test composes Phases 175-183 endpoints. A new domain endpoint
should be ~20-50 LoC of route + Pydantic schemas; if it grows past
that, the missing piece is a repo helper, not a fatter route.

### 3. Scope-as-code
Owner scoping (`*_for_owner` repo helpers + `get_session_for_owner`,
`get_vehicle_for_owner`) is enforced at the repo layer, not the
route. Routes can't accidentally bypass the scope; cross-user
access uniformly returns 404 to prevent enumeration. Shop scoping
lives in `require_shop_access(shop_id, user, db_path,
permission=...)` — bare = any active member, `permission=` = a
specific Phase 112 permission. Cross-shop = 403.

### 4. Renderer ABC for document endpoints
Phase 182's `ReportRenderer` ABC + `ReportDocument` dict shape lets
three distinct artifacts (session / WO / invoice) share one PDF
pipeline + one router shape. Future report kinds (intake summary,
labor estimate, diagnostic certificate) cost ~100 LoC of builder
+ 2 endpoints + 5 tests.

### 5. Spec-as-single-source-of-truth (Phase 183)
The OpenAPI override centralizes spec polish. Adding a new route
automatically inherits the right security + error-response refs
based on tags / path params / request bodies. The walker is
path/tag-driven, not hand-mapped — no per-route OpenAPI
boilerplate.

### 6. Factory pattern for transport-layer providers
Phase 181's `LiveReadingProvider` ABC + `FakeLiveProvider` +
env-dispatched `get_live_provider()` factory + module-level
monkey-patch test seam keeps the route trivial while leaving real
hardware wiring (Phase 140 OBD adapter) for when it's needed. The
plain dict `ReportDocument` follows the same "ABC + dict + factory"
shape.

### 7. Hard-paywall-soft-discovery
Phase 176 enforces the paywall at the dep boundary
(`require_tier("shop")`) but anonymous + individual-tier callers
get a discovery rate-limit budget so they can browse `/v1/version`,
`/healthz`, and read-only KB endpoints. The mobile app can show
useful screens before signup.

### 8. RFC 7807 + correlation IDs
Every error response carries `type`, `title`, `status`, `detail`,
`instance`, and `request_id` (matching the `X-Request-ID`
response header). Mobile clients can surface a single
`request_id` in a "report a bug" flow that maps directly to
server logs.

---

## Mechanic-facing workflow (HTTP version of Gate 8's CLI walk)

```
1. POST /v1/billing/checkout-session    → Stripe URL
   (operator clicks, completes Stripe checkout, webhook fires)
2. POST /v1/shop/profile                → create shop
3. POST /v1/shop/{id}/customers         → add customer
4. POST /v1/vehicles                    → register bike
5. POST /v1/sessions                    → start diagnosis
6. POST /v1/sessions/{id}/symptoms      → log observations
7. POST /v1/sessions/{id}/fault-codes   → record DTCs
8. PATCH /v1/sessions/{id}              → save AI diagnosis
9. GET  /v1/reports/session/{id}/pdf    → keep DIY-rider's record
10. POST /v1/sessions/{id}/close        → archive session
11. POST /v1/shop/{id}/work-orders      → schedule the repair
12. POST /v1/shop/{id}/work-orders/{wo}/transition  → open / start
13. POST /v1/shop/{id}/issues           → log issues found
14. POST /v1/shop/{id}/work-orders/{wo}/transition  → complete
15. POST /v1/shop/{id}/invoices/generate → bill the customer
16. GET  /v1/reports/work-order/{wo}/pdf → receipt
17. GET  /v1/reports/invoice/{inv}/pdf  → invoice for customer
18. GET  /v1/shop/{id}/analytics/snapshot → daily dashboard
```

Track I (mobile app) wraps this same sequence in screens.
Gate 9's `TestGate9HappyPath` walks all 18 steps + 9 sanity
checks (27 HTTP calls total) and asserts a paid invoice falls
out with correct totals.

---

## Known limitations → Track I + Track J seeds

These are deliberately deferred — none block Track H closure but
each is a known gap a future track must address.

### → Track I (mobile app, Phases 185-204)
- **No HTTP signup flow yet.** Bootstrapping a new user (creating
  the `users` row + first API key) currently requires direct DB
  insert or CLI; Track I needs `POST /v1/auth/signup` +
  `POST /v1/auth/login` to make the mobile flow shippable.
- **No password / OAuth login.** Phase 176 only supports API key
  auth. Track I will need session cookies or JWTs for the mobile
  app's "sign in with email" flow.
- **No file uploads.** Track I's photo-upload feature (vehicle
  photos, issue photos) needs `POST /v1/uploads` + S3 (or local
  disk) storage. Deferred to Track I.
- **No photo→make/model auto-ID feature.** See
  `project_motodiag_photo_bike_id.md` memory — slated for Phase
  ~205 post-Gate R as a friction-reduction onboarding feature.

### → Track J (ship + scale, Phases 193-198)
- **Single-process state for live WS connection manager.** Phase
  181's `ConnectionManager` is per-process. Multi-worker uvicorn
  splits state across workers. Track J adds Redis-backed state.
- **No HTTP signup-flow rate limiting.** Phase 176's rate limiter
  works per-API-key once a key exists; pre-key (signup,
  password-reset) flows need IP-based throttling. Track J adds it.
- **No background worker for notification queue.** Phase 170's
  `customer_notifications` table is queue-only; Track J wires the
  email/SMS transport (SendGrid / Twilio).
- **No production WSGI / uvicorn workers config.** `motodiag serve`
  is single-process for dev; Track J adds gunicorn + uvicorn
  worker config + process manager.

### → Future phases (post-Gate 9)
- **OBD hardware live provider (Phase 140 wiring).** `=obd` in
  Phase 181's `MOTODIAG_LIVE_PROVIDER` raises
  `ProviderUnavailableError`; the hook is in place but the
  adapter swap isn't wired. Lands when there's a real hardware
  scenario that needs it.
- **OpenAPI external docs site.** Phase 183's `TAG_CATALOG` has
  the structure for `externalDocs` per tag but no docs site
  exists yet. Lands with mobile launch (Phase 193+).
- **PDF brand customization.** Phase 182's PDF output is
  unbranded. A shop's logo + color scheme uploaded via
  `POST /v1/shop/{id}/profile` could feed `PdfReportRenderer`
  for white-labeled customer-facing PDFs. Lands when a
  multi-shop deployment requests it.

---

## Track H opens for Track I

The 57-endpoint surface + WebSocket + fully-documented OpenAPI 3.1
spec is a contract Track I can build against without further API
churn. Adding new endpoints during Track I should be the exception
— the goal of Tracks H and I together is one stable API surface
shared by web + iOS + Android, not three separate API
implementations.

**Next:** Track I (Phases 185-204) — React Native mobile app
consuming this exact API surface. iOS App Store + Google Play
Store launch by Track J close.
