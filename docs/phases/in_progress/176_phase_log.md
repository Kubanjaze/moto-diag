# MotoDiag Phase 176 — Phase Log

**Status:** 🟡 In Progress | **Started:** 2026-04-22
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
