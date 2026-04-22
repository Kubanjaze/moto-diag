# MotoDiag Phase 176 — Auth + API Keys + Stripe + Hard Paywall

**Version:** 1.0 | **Tier:** Large | **Date:** 2026-04-22

## Goal

**The monetization gate.** Phase 175 opened the HTTP API; Phase 176
locks it behind authentication + subscription. Every `/v1/*` route
now requires a valid API key AND an active subscription matching the
route's tier requirement. Anonymous requests get rate-limited to a
discovery tier (30/min, 100/day) for demo/trial use; authenticated
requests scale up per tier (individual / shop / company).

Core capabilities:
1. **API key auth** — Stripe-style `mdk_live_...` keys hashed with
   SHA-256 before storage; only prefix (first 12 chars) visible in
   UIs. Keys never round-trip the database in plaintext.
2. **Rate limiting** — in-memory token-bucket per key/anonymous-IP.
   Per-tier quotas (60/300/1000 rpm by tier; 30 rpm anonymous).
3. **Subscription tracking** — `subscriptions` table mirrors the
   Stripe subscription lifecycle (active / past_due / canceled /
   trialing / incomplete).
4. **Stripe integration via provider ABC** — `BillingProvider`
   interface with `FakeBillingProvider` (tests + dev) +
   `StripeBillingProvider` (prod). Settings toggles via
   `MOTODIAG_BILLING_PROVIDER=stripe|fake`.
5. **Webhook endpoint** — `POST /v1/billing/webhooks/stripe` with
   HMAC signature verification + idempotency (events dispatched once,
   replay returns 200 but skips the handler).
6. **Hard paywall dependencies** — `require_api_key`,
   `require_active_subscription(tier="shop")` as FastAPI
   `Depends(...)`. Routes that need `shop` tier get a 402 Payment
   Required if the caller has only `individual`.
7. **CLI** — `motodiag apikey {create, list, revoke, show}` +
   `motodiag subscription {show, checkout-url, portal-url, cancel}`
   — all tied to the Phase 112 user model.

**Design rule:** zero AI. Stripe lib is an optional dependency —
tests use `FakeBillingProvider` exclusively so `pip install
'motodiag[api]'` doesn't require a Stripe account.

CLI — **2 new subgroups, 9 subcommands** (`apikey` + `subscription`).

Outputs (~1650 LoC + ~50 tests):
- Migration 037 (~100 LoC): `api_keys` + `subscriptions` +
  `stripe_webhook_events` tables + 5 indexes.
- `src/motodiag/auth/` package (~550 LoC, 4 files):
  - `api_key_repo.py` — CRUD, hashing, verification, last-used
    tracking
  - `rate_limiter.py` — token-bucket keyed by api_key_id or client IP
  - `deps.py` — FastAPI deps (`get_api_key`, `get_current_user`,
    `require_active_subscription`, `require_tier`)
  - `models.py` — Pydantic (`ApiKey`, `AuthedUser`, `RateLimitState`)
- `src/motodiag/billing/` package (~500 LoC, 4 files):
  - `models.py` — Pydantic + `SubscriptionStatus`, `SubscriptionTier`
  - `subscription_repo.py` — CRUD + state transitions
  - `providers.py` — `BillingProvider` ABC + `FakeBillingProvider` +
    `StripeBillingProvider`
  - `webhook_handlers.py` — Stripe event dispatch + idempotency
- `src/motodiag/api/routes/billing.py` (~150 LoC) — checkout URL,
  portal URL, webhook endpoint
- `src/motodiag/api/middleware.py` — extend with
  `RateLimitMiddleware`
- `src/motodiag/api/app.py` — wire `RateLimitMiddleware` after
  `RequestIdMiddleware`
- `src/motodiag/cli/apikey.py` (~180 LoC) — 4 subcommands
- `src/motodiag/cli/subscription.py` (~160 LoC) — 5 subcommands
- `src/motodiag/cli/main.py` — register both subgroups
- `src/motodiag/core/config.py` — add billing + auth fields
- `src/motodiag/core/database.py` SCHEMA_VERSION **36 → 37**.
- `tests/test_phase176_auth_billing.py` (~50 tests, 7 classes).

## Logic

### Migration 037

```sql
CREATE TABLE IF NOT EXISTS api_keys (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    key_prefix TEXT NOT NULL,        -- first 12 chars (mdk_live_abc…)
    key_hash TEXT NOT NULL UNIQUE,   -- sha256 hex of full key
    name TEXT,                       -- human label ("laptop", "ci bot")
    last_used_at TIMESTAMP,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    revoked_at TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
CREATE INDEX idx_api_keys_user ON api_keys(user_id, is_active);
CREATE INDEX idx_api_keys_prefix ON api_keys(key_prefix);

CREATE TABLE IF NOT EXISTS subscriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    tier TEXT NOT NULL CHECK(tier IN (
        'individual', 'shop', 'company'
    )),
    status TEXT NOT NULL CHECK(status IN (
        'active', 'trialing', 'past_due',
        'canceled', 'incomplete', 'incomplete_expired'
    )),
    stripe_customer_id TEXT,
    stripe_subscription_id TEXT UNIQUE,
    stripe_price_id TEXT,
    current_period_start TIMESTAMP,
    current_period_end TIMESTAMP,
    cancel_at_period_end INTEGER NOT NULL DEFAULT 0,
    canceled_at TIMESTAMP,
    trial_end TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
CREATE INDEX idx_subs_user_status ON subscriptions(user_id, status);
CREATE INDEX idx_subs_stripe_cust ON subscriptions(stripe_customer_id);

CREATE TABLE IF NOT EXISTS stripe_webhook_events (
    event_id TEXT PRIMARY KEY,       -- Stripe's evt_XXXX (idempotency)
    type TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP,
    error TEXT
);
CREATE INDEX idx_webhook_events_type ON stripe_webhook_events(type);
```

Rollback drops all 3 tables + indexes.

### API key format + hashing

```
mdk_live_<32-char-url-safe-base64>    (live/prod)
mdk_test_<32-char-url-safe-base64>    (test-env keys)
```

- Generator: `secrets.token_urlsafe(24)` → 32 chars.
- Prefix (`key_prefix`): the full prefix up to and including 4 chars
  of the secret — e.g. `mdk_live_AbCd` (12 chars). Safe to log, safe
  to show in UI, insufficient to auth.
- Hash: `hashlib.sha256(full_key.encode()).hexdigest()`. No salt —
  the key itself has 144 bits of entropy, so rainbow-table risk is
  effectively zero, and a deterministic hash lets us look up by
  `WHERE key_hash = ?` at auth time without loading every row.

### `auth/api_key_repo.py`

```python
def generate_api_key(env: str = "live") -> str: ...
def hash_api_key(key: str) -> str: ...
def key_prefix(key: str) -> str: ...  # first 12 chars

def create_api_key(
    user_id: int, name: Optional[str] = None,
    env: str = "live", db_path: Optional[str] = None,
) -> tuple[ApiKey, str]:
    """Create + persist a new key. Returns (ApiKey record,
    plaintext_key). **The plaintext key is only ever returned here
    — caller must show it once and store it securely.**"""

def verify_api_key(
    plaintext: str, db_path: Optional[str] = None,
) -> Optional[ApiKey]:
    """Look up by hash; return ApiKey if active, else None.
    Updates last_used_at (best-effort, non-blocking on failure)."""

def list_api_keys(
    user_id: int, include_revoked: bool = False,
    db_path: Optional[str] = None,
) -> list[ApiKey]: ...

def revoke_api_key(
    key_id: int, db_path: Optional[str] = None,
) -> bool: ...

def get_api_key_by_prefix(
    prefix: str, db_path: Optional[str] = None,
) -> Optional[ApiKey]: ...  # for CLI "show" by prefix
```

### `auth/rate_limiter.py`

In-memory token bucket per (key_id, bucket_window). Windows: 1-minute
+ 1-day. Rate table:

| Tier        | Authenticated/min | Authenticated/day |
|-------------|------------------:|------------------:|
| anonymous   |                30 |               100 |
| individual  |                60 |              1000 |
| shop        |               300 |            10_000 |
| company     |              1000 |            50_000 |

Returns `RateLimitState(allowed, retry_after_s, tier, minute_used,
day_used)`. Middleware sets `X-RateLimit-*` response headers (limit,
remaining, reset).

In-memory only for Phase 176; a Redis/shared-state backend can be
swapped in for multi-worker deployments in Track J. Documented.

### `auth/deps.py`

```python
API_KEY_HEADER = "X-API-Key"

async def get_api_key(
    api_key_header: Optional[str] = Header(None, alias="X-API-Key"),
    authorization: Optional[str] = Header(None),
    db_path: str = Depends(get_db_path),
) -> Optional[ApiKey]:
    """Resolve the caller's API key from X-API-Key header OR
    `Authorization: Bearer mdk_...`. Returns None when anonymous
    (so routes can decide whether to allow)."""

async def require_api_key(
    api_key: Optional[ApiKey] = Depends(get_api_key),
) -> ApiKey:
    """401 if no key or key is revoked."""

async def get_current_user(
    api_key: ApiKey = Depends(require_api_key),
    db_path: str = Depends(get_db_path),
) -> AuthedUser:
    """Resolve api_key.user_id → users row → AuthedUser."""

def require_tier(required_tier: SubscriptionTier):
    """Dependency factory: returns a dep that 402s if the user's
    active subscription doesn't meet `required_tier`.

    Tier ordering: individual < shop < company (company covers all).

    Usage:
        @router.get("/v1/shops/{id}",
                    dependencies=[Depends(require_tier("shop"))])
    """
    async def _check(
        user: AuthedUser = Depends(get_current_user),
        db_path: str = Depends(get_db_path),
    ) -> AuthedUser:
        sub = get_active_subscription(user.id, db_path=db_path)
        if sub is None:
            raise SubscriptionRequiredError(required_tier)
        if not _tier_meets(sub.tier, required_tier):
            raise SubscriptionTierInsufficientError(
                current=sub.tier, required=required_tier,
            )
        return user
    return _check
```

Exception classes: `InvalidApiKeyError` (401), `SubscriptionRequiredError`
(402), `SubscriptionTierInsufficientError` (402), `RateLimitExceededError`
(429). All mapped in Phase 175's `errors.py`.

### `billing/providers.py`

```python
class BillingProvider(ABC):
    @abstractmethod
    def create_checkout_session(
        user_id: int, email: str, tier: SubscriptionTier,
    ) -> CheckoutSessionResult: ...

    @abstractmethod
    def create_portal_session(
        stripe_customer_id: str, return_url: str,
    ) -> str: ...  # portal URL

    @abstractmethod
    def verify_webhook_signature(
        payload: bytes, signature_header: str,
    ) -> dict: ...  # returns parsed Stripe event

    @abstractmethod
    def retrieve_subscription(stripe_sub_id: str) -> dict: ...

    @abstractmethod
    def cancel_subscription(stripe_sub_id: str) -> dict: ...


class FakeBillingProvider(BillingProvider):
    """Deterministic no-network impl for tests + dev.

    - Checkout URL: `https://fake-billing.local/checkout/{user_id}/{tier}`
    - Customer IDs: `cus_fake_{user_id}`
    - Subscription IDs: `sub_fake_{user_id}_{counter}`
    - Signature verification: accepts "fake_signature" literal;
      otherwise raises
    """


class StripeBillingProvider(BillingProvider):
    """Real Stripe API integration. Lazy-imports `stripe`; raises
    a clear error if the library is not installed."""

    def __init__(self, api_key: str, webhook_secret: str): ...
```

### `billing/subscription_repo.py`

```python
def create_subscription(...) -> int
def get_active_subscription(user_id: int, ...) -> Optional[Subscription]
def update_subscription(sub_id: int, **fields) -> bool
def list_subscriptions_for_user(user_id, ...) -> list[Subscription]
def cancel_subscription_record(sub_id, ...) -> bool
```

### `billing/webhook_handlers.py`

Event dispatch table:

```python
HANDLERS = {
    "customer.subscription.created": _handle_subscription_created,
    "customer.subscription.updated": _handle_subscription_updated,
    "customer.subscription.deleted": _handle_subscription_deleted,
    "invoice.payment_succeeded": _handle_payment_succeeded,
    "invoice.payment_failed": _handle_payment_failed,
}

def dispatch_event(event: dict, db_path: str) -> None:
    """Idempotent: checks stripe_webhook_events for event.id; skips
    if already processed."""
```

### `api/routes/billing.py`

```
POST /v1/billing/checkout-session      (require_api_key; returns {url})
POST /v1/billing/portal-session        (require_api_key + active sub)
POST /v1/billing/webhooks/stripe       (no auth; HMAC verified)
GET  /v1/billing/subscription          (require_api_key; current sub)
```

Webhook endpoint:
- Reads `Stripe-Signature` header.
- Body is raw bytes (need `Request` object, not parsed JSON — Stripe's
  signature is over the raw body).
- Calls provider's `verify_webhook_signature` → event dict.
- Calls `dispatch_event(event, db_path)`.
- Returns 200 OK with `{"received": true, "event_id": ...}`.
- On signature failure: 400.

### `RateLimitMiddleware`

```python
class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        # Skip rate-limit for /healthz, /v1/version, /docs, /openapi.json
        if self._is_exempt(request.url.path):
            return await call_next(request)

        # Identify caller: api key > anonymous (by IP)
        api_key = await self._try_get_api_key(request)
        tier = api_key.tier if api_key else "anonymous"
        bucket_key = (
            f"key:{api_key.id}" if api_key else f"ip:{request.client.host}"
        )

        allowed, state = rate_limiter.check_and_consume(
            bucket_key, tier,
        )
        response = await call_next(request)
        # Set X-RateLimit-* response headers
        response.headers["X-RateLimit-Limit"] = str(state.limit_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(state.remaining_minute)
        response.headers["X-RateLimit-Reset"] = str(state.minute_reset_ts)
        if not allowed:
            return _rate_limit_response(state)
        return response
```

Exemption list: `/healthz`, `/v1/version`, `/openapi.json`, `/docs`,
`/redoc`, `/v1/billing/webhooks/*` (Stripe retries would be blocked
otherwise).

### Config additions

```python
# core/config.py
billing_provider: str = "fake"       # "fake" | "stripe"
stripe_api_key: str = ""
stripe_webhook_secret: str = ""
stripe_price_individual: str = ""    # price_XXX from Stripe dashboard
stripe_price_shop: str = ""
stripe_price_company: str = ""
checkout_success_url: str = (
    "http://localhost:3000/billing/success"
)
checkout_cancel_url: str = (
    "http://localhost:3000/billing/cancel"
)
billing_portal_return_url: str = "http://localhost:3000/billing"
```

### CLI: `motodiag apikey`

```
apikey create --user USER_ID [--name LABEL] [--env live|test]
apikey list --user USER_ID [--include-revoked] [--json]
apikey revoke KEY_ID
apikey show PREFIX   # identify-by-prefix; never prints full secret
```

### CLI: `motodiag subscription`

```
subscription show --user USER_ID [--json]
subscription checkout-url --user USER_ID --tier (individual|shop|company)
subscription portal-url --user USER_ID
subscription cancel --user USER_ID [--immediate]
subscription sync --user USER_ID    # pull from Stripe, reconcile
```

## Key Concepts

- **API keys hashed once with sha256; never stored plaintext.** The
  generator returns the plaintext exactly once at creation time —
  caller must show it to the user immediately. Lost keys are
  unrecoverable (user creates a new one; revokes old).
- **Prefix is safe to log.** 12 chars isn't enough to auth (remaining
  20+ chars are the secret). UIs can show `mdk_live_AbCd…` safely.
- **Provider ABC is the Stripe seam.** Tests wire
  `FakeBillingProvider`; prod wires `StripeBillingProvider`. No
  stripe lib import at module level — only inside Stripe provider
  methods. `MOTODIAG_BILLING_PROVIDER=fake` keeps CI + dev zero-
  dollar.
- **Webhook idempotency via `event_id` PK.** Stripe retries on 5xx;
  we accept duplicates gracefully. Every event is logged in
  `stripe_webhook_events` with `processed_at`; re-delivery returns
  200 but skips the handler.
- **Rate limiter is in-memory for Phase 176.** Single-worker
  deployments (the typical `motodiag serve` setup) work fine.
  Multi-worker shared state is Track J scope. Documented.
- **Tier ordering**: `individual < shop < company`. `require_tier`
  passes when the user's active subscription tier meets OR EXCEEDS
  the required tier. Company owners can access shop routes; shop
  owners can access individual routes.
- **402 Payment Required is the monetization signal.** Distinct from
  401 (no auth) and 403 (wrong user). Mobile clients branch on 402
  to redirect to the Stripe portal.
- **Anonymous discovery tier.** Read-only routes with no tier
  requirement can be called without a key — rate-limited hard (30/min)
  so casual visitors can try the API without paying. Routes that
  mutate state require `require_api_key` at minimum.

## Verification Checklist

- [ ] Migration 037 creates 3 tables + 5 indexes + CHECK constraints.
- [ ] SCHEMA_VERSION 36 → 37.
- [ ] Rollback to 36 drops cleanly.
- [ ] `generate_api_key("live")` returns `mdk_live_<32>`; `("test")`
      returns `mdk_test_<32>`.
- [ ] `hash_api_key` is deterministic; two different keys never
      collide.
- [ ] `create_api_key` persists hash + prefix; returns plaintext
      exactly once.
- [ ] `verify_api_key` accepts active; rejects revoked; bumps
      `last_used_at`.
- [ ] Rate limiter: within limit → allowed; over limit → blocked
      with retry_after.
- [ ] Per-tier limits honored.
- [ ] `X-RateLimit-*` headers set.
- [ ] `/healthz` + `/v1/version` exempt from rate limit.
- [ ] `require_api_key` 401s on missing / invalid header.
- [ ] `require_tier("shop")` passes for shop+company users; 402s
      for individual.
- [ ] `FakeBillingProvider.create_checkout_session` returns
      deterministic URL.
- [ ] Stripe webhook with valid signature → dispatches handler; same
      event replayed → 200 but handler not re-called.
- [ ] Stripe webhook with bad signature → 400.
- [ ] Subscription CRUD + status transitions work.
- [ ] `customer.subscription.created` webhook creates a subscription
      row with correct tier.
- [ ] CLI `apikey {create, list, revoke, show}` round-trip.
- [ ] CLI `subscription {show, checkout-url, portal-url, cancel}`
      round-trip.
- [ ] Phase 113/118/131/153/160-175 tests still GREEN.
- [ ] Zero AI calls.

## Risks

- **In-memory rate limiter resets on restart.** Intentional for
  Phase 176 (single-worker default); a restart loop could let an
  abuser bypass daily limits. Mitigation: daily bucket uses wall-
  clock date so restart-then-spam gets capped at `today's remaining`
  not `full daily quota`.
- **No stripe library installed.** Tests use `FakeBillingProvider`
  exclusively; `StripeBillingProvider` lazy-imports and raises a
  clear `ClickException`/`HTTPException` if `stripe` absent.
  Deploy-time: operator runs `pip install stripe` before setting
  `MOTODIAG_BILLING_PROVIDER=stripe`.
- **Webhook endpoint bypasses rate limiter.** Correct (Stripe retries
  would be throttled away); but also an attack surface for abuse.
  Mitigation: HMAC signature verification rejects anything not from
  Stripe; no DB writes happen before signature passes.
- **`get_current_user` opens a DB connection per request.** At
  smoke-level traffic this is fine; Phase 180+ may add a request-
  scoped connection cache if profiling shows a bottleneck.
- **Subscription state drift from Stripe.** Webhooks can be missed
  (Stripe outage, our downtime, etc). `subscription sync` CLI
  command pulls from Stripe as the source of truth and reconciles.
  Operators should run weekly.
- **No refund/dispute flow in this phase.** Phase 176 ships
  checkout + portal + webhook + cancel. Refund/dispute UX is Track
  J/future scope — Stripe portal handles refunds today.
- **Rate-limit test flakiness if wall-clock used naively.** Tests
  use a monkey-patched clock to advance buckets deterministically.
- **402 status code**: RFC 7231 reserves it for future use; modern
  browsers + libraries handle it cleanly, and Stripe/OpenAI/
  GitHub all use it for paywall. Safer than inventing a custom
  403-with-special-header.
