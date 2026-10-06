"""Phase 273 — the one gateway to Stripe.

The pinned SDK and API version; a live key refused outside prod (with a
planted live key and a test-key control); no key or secret in any output;
the SDK's errors named; the call log; no test reaching Stripe.
"""

from __future__ import annotations

import json
import tomllib
from pathlib import Path

import pytest
import stripe

from motodiag.billing.providers import BillingProviderError, StripeBillingProvider
from motodiag.core.config import Environment
from motodiag.payments import stripe_api
from support.phase273 import STRIPE_ENV, answer, cli, new_db, seed_account, seed_invoice
from support.stripe_fixtures import (
    LIVE_KEY_PLANTED, SHOP_ACCOUNT, TEST_KEY, TEST_SECRET, stripe_settings,
)

ROOT = Path(__file__).resolve().parent.parent


class TestThePin:
    def test_the_api_version_sent_is_the_sdks_own(self):
        from stripe._api_version import _ApiVersion
        assert stripe_api.API_VERSION == _ApiVersion.CURRENT == "2026-09-30.endive"

    def test_pyproject_pins_the_sdk_exactly_and_the_server_installs_it(self):
        extras = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"][
            "optional-dependencies"]
        assert extras["payments"] == ["stripe==16.0.0"]
        assert stripe.VERSION == "16.0.0"
        assert "payments" in extras["server"][0]

    def test_without_the_sdk_it_says_what_to_install(self, monkeypatch):
        """The import is inside the call (209's no-extras install imports
        the package); with the SDK absent, the call names the extra."""
        import sys
        monkeypatch.setitem(sys.modules, "stripe", None)
        with pytest.raises(stripe_api.StripeLibraryMissing, match="motodiag\\[payments\\]"):
            stripe_api.client(stripe_settings())


class TestALiveKeyIsRefused:
    @pytest.mark.parametrize("key", [LIVE_KEY_PLANTED, "rk_live_" + "planted0restricted"])
    def test_outside_prod_before_any_request(self, monkeypatch, key):
        http = answer(monkeypatch, [])
        with pytest.raises(stripe_api.LiveKeyRefused):
            stripe_api.client(stripe_settings(stripe_api_key=key))
        assert http.requests == []

    def test_in_prod_it_is_allowed(self):
        stripe_api.client(stripe_settings(stripe_api_key=LIVE_KEY_PLANTED,
                                          env=Environment.PROD))

    def test_the_control_a_test_key_in_dev_is_allowed(self):
        stripe_api.client(stripe_settings())

    def test_176s_provider_refuses_it_too(self):
        with pytest.raises(BillingProviderError, match="live Stripe key"):
            StripeBillingProvider(LIVE_KEY_PLANTED, TEST_SECRET,
                                  settings=stripe_settings(stripe_api_key=LIVE_KEY_PLANTED))

    def test_a_command_refuses_it_and_does_not_print_it(self, tmp_path, monkeypatch):
        db = new_db(tmp_path)
        ids = seed_invoice(db)
        seed_account(db, ids["shop_id"])
        http = answer(monkeypatch, [])
        env = {**STRIPE_ENV, "MOTODIAG_STRIPE_API_KEY": LIVE_KEY_PLANTED}
        out = cli(db, "shop", "invoice", "pay-link", ids["invoice_id"], env=env)
        assert out.exit_code == 1
        assert "live Stripe key" in out.output
        assert "planted0control" not in out.output
        assert http.requests == []

    def test_the_command_control_a_test_key_reaches_stripe(self, tmp_path, monkeypatch):
        db = new_db(tmp_path)
        ids = seed_invoice(db)
        seed_account(db, ids["shop_id"])
        http = answer(monkeypatch, [("POST", r"/v1/checkout/sessions",
                                     "checkout_session_invoice")])
        out = cli(db, "shop", "invoice", "pay-link", ids["invoice_id"])
        assert out.exit_code == 0, out.output
        assert len(http.requests) == 1


class TestNoSecretInAnyOutput:
    def test_payments_check_prints_only_set_and_test_mode(self, tmp_path):
        out = cli(new_db(tmp_path), "payments", "check")
        assert out.exit_code == 0, out.output
        assert "API key:         set" in out.output
        assert "Test mode:       yes" in out.output
        assert "Webhook secret:  set" in out.output
        assert "test placeholders" in out.output
        for secret in (TEST_KEY, TEST_SECRET):
            for piece in (secret, secret[-6:], secret[8:16]):
                assert piece not in out.output

    def test_payments_check_with_a_live_key_says_not_test_mode(self, tmp_path):
        env = {**STRIPE_ENV, "MOTODIAG_STRIPE_API_KEY": LIVE_KEY_PLANTED}
        out = cli(new_db(tmp_path), "payments", "check", env=env)
        assert "Test mode:       no" in out.output
        assert "planted0control" not in out.output

    def test_stripes_invalid_key_error_is_scrubbed(self, monkeypatch):
        answer(monkeypatch, [("GET", r"/v1/balance", "error_invalid_key")])
        sc = stripe_api.client(stripe_settings())
        with pytest.raises(stripe_api.StripeUnavailable) as e:
            stripe_api.call("read the balance", lambda: sc.v1.balance.retrieve())
        assert e.value.kind == "refused"
        assert "sk_test" not in e.value.message and "3abc" not in e.value.message
        assert "[redacted]" in e.value.message

    def test_a_bad_signature_error_does_not_echo_the_secret(self):
        provider = StripeBillingProvider(TEST_KEY, TEST_SECRET, settings=stripe_settings())
        from motodiag.billing.providers import WebhookSignatureError
        with pytest.raises(WebhookSignatureError) as e:
            provider.verify_webhook_signature(b"{}", "t=1,v1=bad")
        assert TEST_SECRET not in str(e.value)

    def test_no_webhook_secret_refuses_every_event(self):
        from motodiag.billing.providers import WebhookSignatureError
        provider = StripeBillingProvider(TEST_KEY, "", settings=stripe_settings())
        with pytest.raises(WebhookSignatureError, match="no webhook secret"):
            provider.verify_webhook_signature(b"{}", "t=1,v1=x")


class TestErrorsNameStripe:
    @pytest.mark.parametrize("status,payload,kind", [
        (400, {"error": {"type": "invalid_request_error", "message": "bad"}}, "rejected"),
        (429, {"error": {"type": "invalid_request_error", "message": "slow"}}, "busy"),
        (500, {"error": {"type": "api_error", "message": "down"}}, "error"),
    ])
    def test_status_maps_to_kind(self, monkeypatch, status, payload, kind):
        answer(monkeypatch, [("GET", r"/v1/balance", (status, payload))])
        sc = stripe_api.client(stripe_settings())
        with pytest.raises(stripe_api.StripeUnavailable) as e:
            stripe_api.call("read the balance", lambda: sc.v1.balance.retrieve())
        assert e.value.kind == kind
        assert e.value.message.startswith("Stripe")

    def test_unreachable(self, monkeypatch):
        class Down(stripe.HTTPClient):
            name = "down"

            def request(self, *a, **k):
                raise stripe.APIConnectionError("could not connect")

        monkeypatch.setattr(stripe_api, "_test_http_client", Down())
        sc = stripe_api.client(stripe_settings())
        with pytest.raises(stripe_api.StripeUnavailable) as e:
            stripe_api.call("read the balance", lambda: sc.v1.balance.retrieve())
        assert e.value.kind == "unreachable"
        assert "Stripe could not be reached" in e.value.message

    def test_the_network_guard_holds_for_the_sdk(self):
        """No fixture client: the SDK's own HTTP client meets 281's guard."""
        sc = stripe_api.client(stripe_settings())
        with pytest.raises(stripe_api.StripeUnavailable) as e:
            stripe_api.call("read the balance", lambda: sc.v1.balance.retrieve())
        assert "NetworkBlockedInTests" in e.value.detail


class TestTheCallLog:
    def test_one_line_per_request_and_no_secret(self, tmp_path, monkeypatch):
        log = tmp_path / "calls.jsonl"
        answer(monkeypatch, [("POST", r"/v1/checkout/sessions", "checkout_session_invoice")])
        sc = stripe_api.client(stripe_settings(stripe_call_log=str(log)))
        stripe_api.call("x", lambda: sc.v1.checkout.sessions.create(
            {"mode": "payment"}, {"stripe_account": SHOP_ACCOUNT}))
        text = log.read_text()
        line = json.loads(text)
        assert line["method"] == "POST" and line["path"] == "/v1/checkout/sessions"
        assert line["status"] == 200 and line["request_id"] == "req_fixture"
        assert line["stripe_version"] == "2026-09-30.endive"
        assert line["connected_account"] is True
        assert TEST_KEY not in text and "Bearer" not in text and SHOP_ACCOUNT not in text


class TestKeyStatus:
    def test_counts_and_flags_only(self):
        st = stripe_api.key_status(stripe_settings())
        assert (st.api_key_set, st.test_mode, st.webhook_secret_set, st.prices_set) == (
            True, True, True, 3)
        assert TEST_KEY not in repr(st)
