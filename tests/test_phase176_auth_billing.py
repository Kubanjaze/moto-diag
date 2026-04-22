"""Phase 176 — Auth + API keys + Stripe + paywall tests.

Seven test classes across ~50 tests. Zero live AI, zero Stripe
network traffic — FakeBillingProvider exclusively.
"""

from __future__ import annotations

import hashlib
import json as _json
import time
from unittest.mock import patch

import click
import pytest
from click.testing import CliRunner
from fastapi import APIRouter, Depends
from fastapi.testclient import TestClient

from motodiag.api import create_app
from motodiag.auth import (
    ApiKey,
    AuthedUser,
    RateLimiter,
    SubscriptionRequiredError,
    SubscriptionTierInsufficientError,
    create_api_key,
    generate_api_key,
    get_current_user,
    hash_api_key,
    key_prefix,
    list_api_keys,
    require_api_key,
    require_tier,
    reset_rate_limiter,
    revoke_api_key,
    tier_meets,
    verify_api_key,
)
from motodiag.auth.api_key_repo import InvalidApiKeyError
from motodiag.auth.rate_limiter import RateLimitExceededError
from motodiag.billing import (
    ActiveSubscription,
    FakeBillingProvider,
    WebhookSignatureError,
    dispatch_event,
    get_active_subscription,
    upsert_from_stripe,
)
from motodiag.billing.providers import StripeLibraryMissingError
from motodiag.core.config import Settings, reset_settings
from motodiag.core.database import (
    SCHEMA_VERSION, get_connection, init_db, table_exists,
)
from motodiag.core.migrations import rollback_to_version


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def db(tmp_path):
    path = str(tmp_path / "phase176.db")
    init_db(path)
    return path


@pytest.fixture
def cli_db(tmp_path, monkeypatch):
    path = str(tmp_path / "phase176_cli.db")
    init_db(path)
    monkeypatch.setenv("MOTODIAG_DB_PATH", path)
    reset_settings()
    yield path
    reset_settings()


@pytest.fixture
def api_db(tmp_path, monkeypatch):
    path = str(tmp_path / "phase176_api.db")
    init_db(path)
    monkeypatch.setenv("MOTODIAG_DB_PATH", path)
    # Give the anonymous + individual tiers some headroom for tests
    monkeypatch.setenv("MOTODIAG_RATE_LIMIT_ANONYMOUS_PER_MINUTE", "9999")
    monkeypatch.setenv("MOTODIAG_RATE_LIMIT_INDIVIDUAL_PER_MINUTE", "9999")
    monkeypatch.setenv("MOTODIAG_RATE_LIMIT_SHOP_PER_MINUTE", "9999")
    monkeypatch.setenv("MOTODIAG_RATE_LIMIT_COMPANY_PER_MINUTE", "9999")
    reset_settings()
    yield path
    reset_settings()


def _make_user(db_path, username="bob", email="b@ex.com"):
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "INSERT INTO users (username, email, tier, is_active) "
            "VALUES (?, ?, 'individual', 1)",
            (username, email),
        )
        return cursor.lastrowid


def _make_sub(
    db_path, user_id, tier="individual", status="active",
    stripe_sub_id=None, stripe_customer=None,
):
    """Insert a subscription row directly (bypass Pydantic to set
    Phase 176 fields)."""
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            """INSERT INTO subscriptions
               (user_id, tier, status, stripe_customer_id,
                stripe_subscription_id, current_period_end)
               VALUES (?, ?, ?, ?, ?, datetime('now', '+30 days'))""",
            (
                user_id, tier, status, stripe_customer, stripe_sub_id,
            ),
        )
        return cursor.lastrowid


# ===========================================================================
# 1. Migration 037
# ===========================================================================


class TestMigration037:

    def test_schema_version_bumped(self, db):
        assert SCHEMA_VERSION >= 37

    def test_api_keys_table_created(self, db):
        assert table_exists("api_keys", db)
        with get_connection(db) as c:
            cols = {
                r[1] for r in c.execute(
                    "PRAGMA table_info(api_keys)"
                ).fetchall()
            }
        for required in ("key_prefix", "key_hash", "is_active"):
            assert required in cols

    def test_subscriptions_extended_columns(self, db):
        """Phase 176 adds 6 columns to Phase 118's subscriptions."""
        with get_connection(db) as c:
            cols = {
                r[1] for r in c.execute(
                    "PRAGMA table_info(subscriptions)"
                ).fetchall()
            }
        for new_col in (
            "stripe_price_id", "current_period_start",
            "current_period_end", "cancel_at_period_end",
            "canceled_at", "trial_end",
        ):
            assert new_col in cols

    def test_webhook_events_table(self, db):
        assert table_exists("stripe_webhook_events", db)

    def test_rollback_drops_cleanly(self, tmp_path):
        path = str(tmp_path / "rollback.db")
        init_db(path)
        assert table_exists("api_keys", path)
        rollback_to_version(36, path)
        assert not table_exists("api_keys", path)
        assert not table_exists("stripe_webhook_events", path)
        # subscriptions returns to Phase 118 shape
        with get_connection(path) as c:
            cols = {
                r[1] for r in c.execute(
                    "PRAGMA table_info(subscriptions)"
                ).fetchall()
            }
        assert "stripe_price_id" not in cols


# ===========================================================================
# 2. API key generation + CRUD
# ===========================================================================


class TestApiKeys:

    def test_generate_live(self):
        k = generate_api_key("live")
        assert k.startswith("mdk_live_")
        assert len(k) > 30

    def test_generate_test_env(self):
        k = generate_api_key("test")
        assert k.startswith("mdk_test_")

    def test_generate_rejects_bogus_env(self):
        with pytest.raises(ValueError):
            generate_api_key("prod")

    def test_hash_deterministic(self):
        k = generate_api_key("live")
        assert hash_api_key(k) == hash_api_key(k)

    def test_hash_is_sha256_hex(self):
        k = "mdk_live_abcdefghijklmnopqrstuvwx"
        h = hash_api_key(k)
        assert len(h) == 64
        assert h == hashlib.sha256(k.encode()).hexdigest()

    def test_prefix_is_12_chars(self):
        k = generate_api_key("live")
        assert key_prefix(k) == k[:12]

    def test_create_persists_and_returns_plaintext(self, db):
        user_id = _make_user(db)
        record, plaintext = create_api_key(user_id, name="laptop", db_path=db)
        assert plaintext.startswith("mdk_live_")
        assert record.user_id == user_id
        assert record.name == "laptop"
        assert record.is_active
        # Plaintext not stored; only hash persists
        assert record.key_hash == hash_api_key(plaintext)

    def test_verify_accepts_valid_key(self, db):
        user_id = _make_user(db)
        _, plaintext = create_api_key(user_id, db_path=db)
        result = verify_api_key(plaintext, db_path=db)
        assert result is not None
        assert result.user_id == user_id

    def test_verify_rejects_revoked(self, db):
        user_id = _make_user(db)
        record, plaintext = create_api_key(user_id, db_path=db)
        revoke_api_key(record.id, db_path=db)
        result = verify_api_key(plaintext, db_path=db)
        assert result is None

    def test_verify_rejects_unknown_key(self, db):
        result = verify_api_key(
            "mdk_live_" + "x" * 32, db_path=db,
        )
        assert result is None

    def test_verify_rejects_malformed(self, db):
        assert verify_api_key("not_a_real_key", db_path=db) is None
        assert verify_api_key("", db_path=db) is None
        assert verify_api_key(None, db_path=db) is None

    def test_list_filters_revoked(self, db):
        user_id = _make_user(db)
        k1, _ = create_api_key(user_id, name="a", db_path=db)
        k2, _ = create_api_key(user_id, name="b", db_path=db)
        revoke_api_key(k1.id, db_path=db)
        active = list_api_keys(user_id, db_path=db)
        assert len(active) == 1
        assert active[0].id == k2.id
        all_keys = list_api_keys(
            user_id, include_revoked=True, db_path=db,
        )
        assert len(all_keys) == 2


# ===========================================================================
# 3. Rate limiter
# ===========================================================================


class TestRateLimiter:

    def _make_settings(self, **overrides) -> Settings:
        defaults = dict(
            db_path="",
            rate_limit_anonymous_per_minute=5,
            rate_limit_anonymous_per_day=10,
            rate_limit_individual_per_minute=10,
            rate_limit_individual_per_day=20,
            rate_limit_shop_per_minute=50,
            rate_limit_shop_per_day=200,
            rate_limit_company_per_minute=100,
            rate_limit_company_per_day=1000,
        )
        defaults.update(overrides)
        return Settings(**defaults)

    def test_under_limit_allowed(self):
        clock = [1_700_000_000.0]
        rl = RateLimiter(
            settings=self._make_settings(),
            clock=lambda: clock[0],
        )
        for _ in range(5):
            state = rl.check_and_consume("key:1", "individual")
            assert state.allowed is True

    def test_over_minute_limit_blocks(self):
        clock = [1_700_000_000.0]
        rl = RateLimiter(
            settings=self._make_settings(),
            clock=lambda: clock[0],
        )
        for _ in range(10):
            s = rl.check_and_consume("key:1", "individual")
            assert s.allowed is True
        s = rl.check_and_consume("key:1", "individual")
        assert s.allowed is False
        assert s.retry_after_s > 0

    def test_minute_window_resets(self):
        clock = [1_700_000_000.0]
        rl = RateLimiter(
            settings=self._make_settings(),
            clock=lambda: clock[0],
        )
        for _ in range(10):
            rl.check_and_consume("key:1", "individual")
        # Advance 61 seconds — new minute bucket
        clock[0] += 61
        s = rl.check_and_consume("key:1", "individual")
        assert s.allowed is True

    def test_daily_limit_enforced(self):
        clock = [1_700_000_000.0]
        rl = RateLimiter(
            settings=self._make_settings(),
            clock=lambda: clock[0],
        )
        for i in range(20):
            # Advance 7 seconds per call so we don't hit /min limit
            clock[0] += 7
            s = rl.check_and_consume("key:1", "individual")
            assert s.allowed is True
        clock[0] += 7
        s = rl.check_and_consume("key:1", "individual")
        assert s.allowed is False  # daily exhausted

    def test_tiers_get_different_limits(self):
        rl = RateLimiter(settings=self._make_settings())
        s_anon = rl.check_and_consume("ip:1.2.3.4", "anonymous")
        assert s_anon.limit_per_minute == 5
        s_shop = rl.check_and_consume("key:2", "shop")
        assert s_shop.limit_per_minute == 50
        s_co = rl.check_and_consume("key:3", "company")
        assert s_co.limit_per_minute == 100

    def test_state_includes_minute_reset_ts(self):
        rl = RateLimiter(settings=self._make_settings())
        s = rl.check_and_consume("key:1", "individual")
        assert s.minute_reset_ts > 0


# ===========================================================================
# 4. Tier comparisons + FastAPI deps
# ===========================================================================


class TestTierAndDeps:

    def test_tier_meets(self):
        assert tier_meets("shop", "individual") is True
        assert tier_meets("company", "shop") is True
        assert tier_meets("individual", "shop") is False
        assert tier_meets(None, "individual") is False

    def test_require_tier_rejects_bogus(self):
        with pytest.raises(ValueError):
            require_tier("enterprise")  # not in enum


# ===========================================================================
# 5. API auth integration (real FastAPI TestClient)
# ===========================================================================


class TestApiAuthIntegration:

    def _app_with_gated_routes(self, api_db):
        """Build an app with test routes that require various tiers."""
        app = create_app(db_path_override=api_db)
        router = APIRouter(prefix="/v1/bench")

        @router.get("/anon")
        def anon_ok():
            return {"ok": True}

        @router.get("/authed")
        def authed_ok(api_key=Depends(require_api_key)):
            return {"user_id": api_key.user_id}

        @router.get(
            "/shop-only",
            dependencies=[Depends(require_tier("shop"))],
        )
        def shop_only():
            return {"ok": True}

        app.include_router(router)
        return app

    def test_anonymous_ok_on_public_route(self, api_db):
        app = self._app_with_gated_routes(api_db)
        client = TestClient(app, raise_server_exceptions=False)
        r = client.get("/v1/bench/anon")
        assert r.status_code == 200

    def test_authed_route_rejects_missing_key(self, api_db):
        app = self._app_with_gated_routes(api_db)
        client = TestClient(app, raise_server_exceptions=False)
        r = client.get("/v1/bench/authed")
        assert r.status_code == 401
        body = r.json()
        assert body["type"].endswith("invalid-api-key")

    def test_authed_route_accepts_x_api_key_header(self, api_db):
        user_id = _make_user(api_db)
        _, plaintext = create_api_key(user_id, db_path=api_db)
        app = self._app_with_gated_routes(api_db)
        client = TestClient(app, raise_server_exceptions=False)
        r = client.get(
            "/v1/bench/authed",
            headers={"X-API-Key": plaintext},
        )
        assert r.status_code == 200
        assert r.json()["user_id"] == user_id

    def test_authed_route_accepts_bearer_token(self, api_db):
        user_id = _make_user(api_db)
        _, plaintext = create_api_key(user_id, db_path=api_db)
        app = self._app_with_gated_routes(api_db)
        client = TestClient(app, raise_server_exceptions=False)
        r = client.get(
            "/v1/bench/authed",
            headers={"Authorization": f"Bearer {plaintext}"},
        )
        assert r.status_code == 200

    def test_tier_insufficient_returns_402(self, api_db):
        user_id = _make_user(api_db)
        _, plaintext = create_api_key(user_id, db_path=api_db)
        # user has only 'individual' subscription
        _make_sub(api_db, user_id, tier="individual")
        app = self._app_with_gated_routes(api_db)
        client = TestClient(app, raise_server_exceptions=False)
        r = client.get(
            "/v1/bench/shop-only",
            headers={"X-API-Key": plaintext},
        )
        assert r.status_code == 402
        body = r.json()
        assert body["type"].endswith(
            "subscription-tier-insufficient",
        )

    def test_no_subscription_returns_402(self, api_db):
        user_id = _make_user(api_db)
        _, plaintext = create_api_key(user_id, db_path=api_db)
        app = self._app_with_gated_routes(api_db)
        client = TestClient(app, raise_server_exceptions=False)
        r = client.get(
            "/v1/bench/shop-only",
            headers={"X-API-Key": plaintext},
        )
        assert r.status_code == 402
        body = r.json()
        assert body["type"].endswith("subscription-required")

    def test_shop_sub_satisfies_shop_requirement(self, api_db):
        user_id = _make_user(api_db)
        _, plaintext = create_api_key(user_id, db_path=api_db)
        _make_sub(api_db, user_id, tier="shop")
        app = self._app_with_gated_routes(api_db)
        client = TestClient(app, raise_server_exceptions=False)
        r = client.get(
            "/v1/bench/shop-only",
            headers={"X-API-Key": plaintext},
        )
        assert r.status_code == 200

    def test_company_sub_satisfies_shop_requirement(self, api_db):
        user_id = _make_user(api_db)
        _, plaintext = create_api_key(user_id, db_path=api_db)
        _make_sub(api_db, user_id, tier="company")
        app = self._app_with_gated_routes(api_db)
        client = TestClient(app, raise_server_exceptions=False)
        r = client.get(
            "/v1/bench/shop-only",
            headers={"X-API-Key": plaintext},
        )
        assert r.status_code == 200


# ===========================================================================
# 6. Billing endpoints
# ===========================================================================


class TestBillingRoutes:

    def test_checkout_session_returns_fake_url(self, api_db):
        user_id = _make_user(api_db)
        _, plaintext = create_api_key(user_id, db_path=api_db)
        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)
        r = client.post(
            "/v1/billing/checkout-session",
            headers={"X-API-Key": plaintext},
            json={"tier": "shop"},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert "fake-billing.local" in body["checkout_url"]
        assert body["session_id"].startswith("cs_fake_")

    def test_checkout_session_rejects_bad_tier(self, api_db):
        user_id = _make_user(api_db)
        _, plaintext = create_api_key(user_id, db_path=api_db)
        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)
        r = client.post(
            "/v1/billing/checkout-session",
            headers={"X-API-Key": plaintext},
            json={"tier": "enterprise"},
        )
        assert r.status_code == 401
        # InvalidApiKeyError maps 401 — it's the fallback raise

    def test_subscription_endpoint_empty(self, api_db):
        user_id = _make_user(api_db)
        _, plaintext = create_api_key(user_id, db_path=api_db)
        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)
        r = client.get(
            "/v1/billing/subscription",
            headers={"X-API-Key": plaintext},
        )
        assert r.status_code == 200
        body = r.json()
        assert body.get("tier") is None

    def test_subscription_endpoint_returns_active(self, api_db):
        user_id = _make_user(api_db)
        _, plaintext = create_api_key(user_id, db_path=api_db)
        _make_sub(
            api_db, user_id, tier="shop",
            stripe_customer="cus_test_123",
            stripe_sub_id="sub_test_abc",
        )
        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)
        r = client.get(
            "/v1/billing/subscription",
            headers={"X-API-Key": plaintext},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["tier"] == "shop"
        assert body["stripe_subscription_id"] == "sub_test_abc"

    def test_portal_url_requires_stripe_customer(self, api_db):
        user_id = _make_user(api_db)
        _, plaintext = create_api_key(user_id, db_path=api_db)
        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)
        r = client.post(
            "/v1/billing/portal-session",
            headers={"X-API-Key": plaintext},
        )
        assert r.status_code == 402

    def test_portal_url_happy(self, api_db):
        user_id = _make_user(api_db)
        _, plaintext = create_api_key(user_id, db_path=api_db)
        _make_sub(
            api_db, user_id, tier="shop",
            stripe_customer="cus_abc_123",
            stripe_sub_id="sub_abc_123",
        )
        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)
        r = client.post(
            "/v1/billing/portal-session",
            headers={"X-API-Key": plaintext},
        )
        assert r.status_code == 200
        assert "fake-billing.local/portal" in r.json()["portal_url"]


# ===========================================================================
# 7. Webhook dispatch
# ===========================================================================


class TestWebhookDispatch:

    def _subscription_event(
        self, *, user_id, sub_id="sub_test_1", event_id="evt_1",
        tier="shop",
    ):
        return {
            "id": event_id,
            "type": "customer.subscription.created",
            "data": {
                "object": {
                    "id": sub_id,
                    "customer": f"cus_{user_id}",
                    "status": "active",
                    "metadata": {
                        "user_id": str(user_id), "tier": tier,
                    },
                }
            },
        }

    def test_subscription_created_upserts_row(self, db):
        user_id = _make_user(db)
        event = self._subscription_event(user_id=user_id)
        result = dispatch_event(event, db_path=db)
        assert result.processed is True
        assert result.error is None
        sub = get_active_subscription(user_id, db_path=db)
        assert sub is not None
        assert sub.tier == "shop"
        assert sub.stripe_subscription_id == "sub_test_1"

    def test_replay_skips_handler(self, db):
        user_id = _make_user(db)
        event = self._subscription_event(user_id=user_id)
        first = dispatch_event(event, db_path=db)
        second = dispatch_event(event, db_path=db)
        assert first.processed is True
        assert second.processed is False  # replay skip
        # Still only one sub row
        with get_connection(db) as c:
            count = c.execute(
                "SELECT COUNT(*) AS n FROM subscriptions",
            ).fetchone()["n"]
        assert count == 1

    def test_subscription_updated_upserts_in_place(self, db):
        user_id = _make_user(db)
        event = self._subscription_event(user_id=user_id)
        dispatch_event(event, db_path=db)
        update_event = {
            "id": "evt_2",
            "type": "customer.subscription.updated",
            "data": {
                "object": {
                    "id": "sub_test_1",
                    "customer": f"cus_{user_id}",
                    "status": "past_due",
                    "metadata": {
                        "user_id": str(user_id), "tier": "shop",
                    },
                }
            },
        }
        dispatch_event(update_event, db_path=db)
        sub = get_active_subscription(user_id, db_path=db)
        # past_due isn't in active states → should return None
        assert sub is None

    def test_subscription_deleted_marks_canceled(self, db):
        user_id = _make_user(db)
        dispatch_event(
            self._subscription_event(user_id=user_id), db_path=db,
        )
        delete_event = {
            "id": "evt_3",
            "type": "customer.subscription.deleted",
            "data": {
                "object": {
                    "id": "sub_test_1",
                    "customer": f"cus_{user_id}",
                }
            },
        }
        dispatch_event(delete_event, db_path=db)
        sub = get_active_subscription(user_id, db_path=db)
        assert sub is None

    def test_unhandled_event_type_still_marked_processed(self, db):
        event = {
            "id": "evt_unknown_1",
            "type": "some.random.event",
            "data": {"object": {}},
        }
        result = dispatch_event(event, db_path=db)
        assert result.processed is True

    def test_provider_verifies_fake_signature(self):
        p = FakeBillingProvider()
        payload = _json.dumps({
            "id": "evt_1", "type": "test.event",
            "data": {"object": {}},
        }).encode()
        event = p.verify_webhook_signature(
            payload, FakeBillingProvider.FAKE_SIGNATURE,
        )
        assert event["id"] == "evt_1"

    def test_provider_rejects_bad_signature(self):
        p = FakeBillingProvider()
        with pytest.raises(WebhookSignatureError):
            p.verify_webhook_signature(b"{}", "bogus")

    def test_webhook_endpoint_happy_path(self, api_db):
        user_id = _make_user(api_db)
        event = {
            "id": "evt_wh_1",
            "type": "customer.subscription.created",
            "data": {
                "object": {
                    "id": "sub_wh_1",
                    "customer": f"cus_{user_id}",
                    "status": "active",
                    "metadata": {
                        "user_id": str(user_id), "tier": "shop",
                    },
                }
            },
        }
        payload = _json.dumps(event).encode()
        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)
        r = client.post(
            "/v1/billing/webhooks/stripe",
            content=payload,
            headers={
                "Stripe-Signature": FakeBillingProvider.FAKE_SIGNATURE,
                "Content-Type": "application/json",
            },
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["received"] is True
        assert body["processed"] is True

    def test_webhook_endpoint_rejects_bad_signature(self, api_db):
        event = {"id": "evt_1", "type": "test", "data": {"object": {}}}
        payload = _json.dumps(event).encode()
        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)
        r = client.post(
            "/v1/billing/webhooks/stripe",
            content=payload,
            headers={
                "Stripe-Signature": "bogus",
                "Content-Type": "application/json",
            },
        )
        assert r.status_code == 400


# ===========================================================================
# 8. Rate-limit middleware in the real app
# ===========================================================================


class TestRateLimitMiddleware:

    def test_exempt_paths_bypass_rate_limit(self, api_db, monkeypatch):
        # Crank anonymous limit way down, confirm /healthz still works.
        monkeypatch.setenv(
            "MOTODIAG_RATE_LIMIT_ANONYMOUS_PER_MINUTE", "0",
        )
        reset_settings()
        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)
        # /healthz is in the exempt list
        for _ in range(5):
            r = client.get("/healthz")
            assert r.status_code == 200

    def test_anon_over_limit_returns_429(self, api_db, monkeypatch):
        monkeypatch.setenv(
            "MOTODIAG_RATE_LIMIT_ANONYMOUS_PER_MINUTE", "2",
        )
        reset_settings()
        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)
        # Hit a non-exempt route
        for _ in range(2):
            r = client.get("/v1/shops/999")
            # 404 because shop doesn't exist — but request counted
            assert r.status_code == 404
        r = client.get("/v1/shops/999")
        assert r.status_code == 429
        body = r.json()
        assert body["type"].endswith("rate-limit-exceeded")
        assert "Retry-After" in r.headers

    def test_ratelimit_headers_on_success(self, api_db):
        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)
        r = client.get("/v1/shops/999")
        # Response is 404 but rate-limit headers should still be set
        assert "X-RateLimit-Limit" in r.headers
        assert "X-RateLimit-Remaining" in r.headers
        assert "X-RateLimit-Tier" in r.headers


# ===========================================================================
# 9. CLI
# ===========================================================================


class TestCli:

    def test_apikey_create_cli(self, cli_db):
        from motodiag.cli.main import cli
        user_id = _make_user(cli_db)
        runner = CliRunner()
        r = runner.invoke(
            cli, ["apikey", "create", "--user", str(user_id),
                  "--name", "laptop", "--json"],
        )
        assert r.exit_code == 0, r.output
        payload = _json.loads(r.output)
        assert "plaintext" in payload
        assert payload["plaintext"].startswith("mdk_live_")
        assert payload["name"] == "laptop"

    def test_apikey_list_cli(self, cli_db):
        from motodiag.cli.main import cli
        user_id = _make_user(cli_db)
        create_api_key(user_id, name="a", db_path=cli_db)
        create_api_key(user_id, name="b", db_path=cli_db)
        runner = CliRunner()
        r = runner.invoke(
            cli, ["apikey", "list", "--user", str(user_id), "--json"],
        )
        assert r.exit_code == 0
        rows = _json.loads(r.output)
        assert len(rows) == 2

    def test_apikey_revoke_cli(self, cli_db):
        from motodiag.cli.main import cli
        user_id = _make_user(cli_db)
        k, _ = create_api_key(user_id, db_path=cli_db)
        runner = CliRunner()
        r = runner.invoke(cli, ["apikey", "revoke", str(k.id)])
        assert r.exit_code == 0
        keys = list_api_keys(user_id, db_path=cli_db)
        assert len(keys) == 0  # active only

    def test_apikey_show_by_prefix(self, cli_db):
        from motodiag.cli.main import cli
        user_id = _make_user(cli_db)
        k, _ = create_api_key(user_id, name="laptop", db_path=cli_db)
        runner = CliRunner()
        r = runner.invoke(
            cli, ["apikey", "show", k.key_prefix, "--json"],
        )
        assert r.exit_code == 0
        payload = _json.loads(r.output)
        assert payload["id"] == k.id

    def test_subscription_show_cli_empty(self, cli_db):
        from motodiag.cli.main import cli
        user_id = _make_user(cli_db)
        runner = CliRunner()
        r = runner.invoke(
            cli,
            ["subscription", "show", "--user", str(user_id), "--json"],
        )
        assert r.exit_code == 0
        assert _json.loads(r.output)["active"] is False

    def test_subscription_checkout_url_cli(self, cli_db):
        from motodiag.cli.main import cli
        user_id = _make_user(cli_db)
        runner = CliRunner()
        r = runner.invoke(
            cli,
            ["subscription", "checkout-url",
             "--user", str(user_id), "--tier", "shop"],
        )
        assert r.exit_code == 0, r.output
        assert "fake-billing.local/checkout" in r.output


# ===========================================================================
# 10. Stripe lib lazy import safeguard
# ===========================================================================


class TestStripeLazyImport:

    def test_stripe_provider_raises_when_lib_missing(self):
        from motodiag.billing.providers import StripeBillingProvider
        provider = StripeBillingProvider(
            api_key="sk_test_dummy", webhook_secret="whsec_dummy",
        )
        # Simulate stripe lib absent
        with patch.dict("sys.modules", {"stripe": None}):
            with pytest.raises(StripeLibraryMissingError):
                provider._stripe()
