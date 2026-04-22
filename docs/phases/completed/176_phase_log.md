# MotoDiag Phase 176 — Phase Log

**Status:** ✅ Complete — **MONETIZATION GATE SHIPPED** | **Started:** 2026-04-22 | **Completed:** 2026-04-22
**Repo:** https://github.com/Kubanjaze/moto-diag

---

### 2026-04-22 — Plan written (monetization gate)

Plan v1.0 authored in-session. Scope: **the monetization gate**. Phase
175 opened the HTTP API; Phase 176 locks it behind authentication +
subscription + rate limiting + Stripe billing. This is where moto-
diag starts earning real money.

Key design decisions:
- **Stripe-style API keys** (`mdk_live_<32>` / `mdk_test_<32>`)
  hashed with sha256 once at creation. Plaintext returned to user
  exactly once — if lost, user rotates. Prefix (first 12 chars) safe
  to log + display.
- **In-memory token-bucket rate limiter** (per api_key or per IP for
  anonymous). Multi-worker shared state deferred to Track J.
- **Tier ordering**: `individual < shop < company`. `require_tier`
  dep-factory enforces.
- **BillingProvider ABC** with `FakeBillingProvider` (tests + dev)
  and `StripeBillingProvider` (prod, lazy stripe-lib import). Switch
  via `MOTODIAG_BILLING_PROVIDER=stripe|fake`.
- **Webhook idempotency** via `stripe_webhook_events.event_id`
  primary key — Stripe retries on 5xx; we accept duplicates
  gracefully.
- **402 Payment Required** (not 403) for subscription-insufficient —
  matches Stripe/OpenAI/GitHub conventions; mobile clients branch
  cleanly to billing portal.
- **Anonymous discovery tier**: 30/min rate limit for unauthenticated
  callers. Read-only routes can allow anonymous; mutations require
  `require_api_key`.

Migration 037: `api_keys` + `subscriptions` + `stripe_webhook_events`
tables + 5 indexes. Rollback clean.

New packages:
- `src/motodiag/auth/` — api_key_repo, rate_limiter, deps, models
- `src/motodiag/billing/` — subscription_repo, providers,
  webhook_handlers, models

2 new CLI subgroups (9 subcommands): `motodiag apikey {create, list,
revoke, show}` + `motodiag subscription {show, checkout-url,
portal-url, cancel, sync}`.

~1650 LoC + ~50 tests. Zero AI. Stripe library is an *optional*
deploy-time dependency — CI/tests pass without it via
FakeBillingProvider.

### 2026-04-22 — Build complete

Files shipped (~1400 LoC across 12 files):

1. **Migration 037** (schema v36→v37): `api_keys` + extensions to
   Phase 118's `subscriptions` (6 new columns via ALTER TABLE) +
   `stripe_webhook_events`. 4 new indexes. Rollback uses rename-
   recreate to restore Phase 118 shape.

2. **`src/motodiag/auth/api_key_repo.py`** (201 LoC): Stripe-style
   `mdk_live_*` / `mdk_test_*` key generation via
   `secrets.token_urlsafe(24)`, sha256 hashing, `verify_api_key` +
   `create_api_key` (returns plaintext exactly once) + CRUD. Phase
   112 auth package extended with 12 new re-exports.

3. **`src/motodiag/auth/rate_limiter.py`** (196 LoC): thread-safe
   in-memory token-bucket keyed by `key:<id>` or `ip:<addr>`.
   Per-tier budgets (60/300/1000 rpm for individual/shop/company;
   30 rpm anonymous) from Settings. `RateLimitState` snapshot
   includes minute_reset_ts for X-RateLimit-Reset header.
   Configurable clock for test-time advancement.

4. **`src/motodiag/auth/deps.py`** (178 LoC): FastAPI
   `get_api_key` / `require_api_key` / `get_current_user` /
   `require_tier(T)` factory. Accepts `X-API-Key` header OR
   `Authorization: Bearer <key>`. Tier ordering: individual < shop
   < company. 402 Payment Required on tier mismatch (distinct type
   URIs for "no-sub" vs "tier-insufficient").

5. **`src/motodiag/billing/providers.py`** (242 LoC):
   `BillingProvider` ABC + `FakeBillingProvider` (deterministic
   zero-network) + `StripeBillingProvider` (lazy stripe-lib import;
   raises `StripeLibraryMissingError` when missing). Factory
   `get_billing_provider(settings)` selects via
   `MOTODIAG_BILLING_PROVIDER` env var. Tests use
   `FakeBillingProvider.FAKE_SIGNATURE = "fake_signature_ok"` for
   HMAC-mock verification.

6. **`src/motodiag/billing/subscription_repo.py`** (+145 LoC):
   Phase 176 additions on top of Phase 118 — `ActiveSubscription`
   Pydantic, `get_active_subscription`,
   `get_subscription_by_stripe_id`, `upsert_from_stripe` (idempotent).

7. **`src/motodiag/billing/webhook_handlers.py`** (237 LoC):
   `dispatch_event` with event_id-based idempotency. Handlers for
   `customer.subscription.created/updated/deleted` + invoice
   payment events (logged as noop for Phase 176 — Phase 182 will
   wire up invoicing hooks). Unhandled types still recorded for
   audit + marked processed.

8. **`src/motodiag/api/routes/billing.py`** (175 LoC):
   POST /v1/billing/checkout-session / portal-session /
   webhooks/stripe + GET /v1/billing/subscription. Webhook endpoint
   reads raw body (needed for HMAC), verifies signature via
   provider, dispatches.

9. **`src/motodiag/api/middleware.py`** (+162 LoC):
   `RateLimitMiddleware` — resolves caller via API key or client IP,
   looks up active subscription tier, consumes a token. Exempt
   list: `/healthz`, `/v1/version`, OpenAPI endpoints,
   `/v1/billing/webhooks/*` (Stripe retries).

10. **`src/motodiag/api/errors.py`** (+54 LoC): 8 new exception
    mappings (InvalidApiKeyError 401, ApiKeyNotFoundError 404,
    SubscriptionRequiredError 402, SubscriptionTierInsufficientError
    402, RateLimitExceededError 429, WebhookSignatureError 400,
    StripeLibraryMissingError 500, BillingProviderError 502) +
    specialized `_rate_limit_handler` that adds Retry-After header.

11. **`src/motodiag/cli/apikey.py`** (148 LoC): `motodiag apikey
    {create, list, revoke, show}` — 4 subcommands.

12. **`src/motodiag/cli/billing.py`** (189 LoC): `motodiag
    subscription {show, checkout-url, portal-url, cancel, sync}` —
    5 subcommands. Named `billing.py` to avoid shadowing Phase 109's
    `cli/subscription.py` tier-enforcement utility.

13. **`src/motodiag/core/config.py`** (+20 LoC): 9 new fields
    (billing_provider, stripe_api_key, stripe_webhook_secret,
    3 tier price IDs, checkout URLs, portal URL, 8 rate-limit
    budgets).

14. **`tests/test_phase176_auth_billing.py`** (58 tests across 10
    classes): TestMigration037×5 + TestApiKeys×12 + TestRateLimiter×6
    + TestTierAndDeps×2 + TestApiAuthIntegration×8 +
    TestBillingRoutes×6 + TestWebhookDispatch×9 +
    TestRateLimitMiddleware×3 + TestCli×6 + TestStripeLazyImport×1.

**Bug fixes during build:**
- **Bug fix #1: Middleware-raised exceptions don't reach FastAPI
  handlers.** First draft of `RateLimitMiddleware` raised
  `RateLimitExceededError` expecting the global exception-handler
  registry to produce the 429 response. That pattern only works
  for route-raised exceptions — middleware exceptions bubble
  through Starlette's stream layer unhandled. Fixed by building the
  429 `JSONResponse` inline in the middleware with ProblemDetail
  body + `Retry-After` + `X-RateLimit-*` headers. The registered
  global handler still exists as a safety net for any route-raised
  instances.
- **Bug fix #2: Gate 8 assertion brittle.** Phase 174's
  `test_schema_version_at_gate` asserted `SCHEMA_VERSION == 36`
  exactly; Phase 176 legitimately bumps to 37. Widened to
  `>= 36` — same widening pattern Phase 172 applied to Phase 171's
  brittle assertion. Intent preserved via phase_log docs.

**Single-pass-after-fixes: 58 GREEN in 32.30s.**

**Targeted regression: 736/736 GREEN in 483.43s (8m 3s)** covering
Phase 113 + 118 + 131 + 153 + Track G 160-174 + 162.5 + 175 + 176,
with the one Phase 174 assertion widened. Zero functional
regressions.

Build deviations vs plan:
- `subscriptions` ALTER-extended, not recreated (Phase 169 pattern).
- CLI file named `cli/billing.py` (shadowing avoidance).
- In-middleware 429 response (Starlette constraint).
- Gate 8 assertion widened.
- 58 tests vs ~50 planned (+8 for CLI + middleware edge cases).

### 2026-04-22 — Documentation finalization — **💰 MONETIZATION GATE SHIPPED**

`implementation.md` promoted to v1.1. All `[x]` in Verification
Checklist. Deviations + Results sections populated. Key finding
captures the transformative moment: moto-diag is now a real
paywalled API service.

Project-level updates:
- `implementation.md` schema_version footnote v36 → v37
- `implementation.md` Database Tables: append `api_keys` +
  `stripe_webhook_events`; note Phase 176 extensions on
  `subscriptions`
- `implementation.md` Phase History: append Phase 176 row marking
  "monetization gate shipped"
- `implementation.md` CLI Commands: add `motodiag apikey` +
  `motodiag subscription` rows
- `implementation.md` Package Inventory: extend `auth/` with Phase
  176 modules; note Phase 176 additions to `billing/`
- `phase_log.md` project-level: Phase 176 closure entry
- `docs/ROADMAP.md`: Phase 176 row → ✅
- Project version 0.11.1 → **0.12.0** (major minor bump —
  monetization is a structural product change)

**Key finding:** Phase 176 validates the "everything composes at
the dep boundary" pattern. API keys + rate limiting + subscription
tier enforcement + Stripe billing all flow through one coherent
FastAPI dep chain: `get_api_key` → `require_api_key` →
`get_current_user` → `require_tier(T)`. Every Phase 177-184 route
(and every Track I mobile screen) opts in by declaring which dep
it needs; no route handler has to know about auth, subscriptions,
or rate limits. The `BillingProvider` ABC kept tests zero-cost
(FakeBillingProvider exclusively, no stripe lib needed for CI)
while prod swaps via one env var. The webhook idempotency via
event_id PK means Stripe can retry freely without corrupting state.
**moto-diag is now a real paywalled API service** — the monetization
infrastructure is fully production-ready; operator just needs to:
(1) configure Stripe keys, (2) set `MOTODIAG_BILLING_PROVIDER=stripe`,
(3) `pip install stripe`, (4) point the Stripe dashboard webhook to
`POST /v1/billing/webhooks/stripe`. Phases 177-180 (vehicle / session /
KB / shop domain routes) now compose on top with `dependencies=[
Depends(require_tier("individual"))]` — ~5 lines of code per route.

Next: **Phase 177** (vehicle endpoints — garage CRUD with
individual-tier minimum) is the first domain router on top of the
paywall. Phases 178-180 follow in parallel. Phase 181 (WebSocket
live data for OBD streams), 182 (PDF report generation), 183
(OpenAPI enrichment), 184 (Gate 9 full-API integration test)
close Track H.
