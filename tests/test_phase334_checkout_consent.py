"""Phase 334 — the second switch: Checkout asks for the terms (Logic item 7).

The Checkout params are built by `checkout_session_params`, which needs no
Stripe client. `StripeBillingProvider` is driven with a stand-in client that
records the params it is handed, never the network. The route answers the
same URL from the fake provider either way.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from motodiag.billing.providers import StripeBillingProvider, checkout_session_params
from motodiag.core.config import Settings, reset_settings

from support.phase303 import client, make_key, make_user, new_db

KEYS = {"mode", "line_items", "client_reference_id", "success_url",
        "cancel_url", "metadata", "subscription_data", "customer_email"}


def _params(consent: bool) -> dict:
    return checkout_session_params(
        user_id=7, email="o@ex.com", tier="shop", price="p_shop",
        success_url="https://s/", cancel_url="https://c/", terms_consent=consent)


def test_off_no_consent_collection_and_every_existing_key():
    p = _params(False)
    assert "consent_collection" not in p
    assert set(p) == KEYS
    assert p["subscription_data"] == {"metadata": {"user_id": "7", "tier": "shop"}}
    assert p["metadata"] == {"user_id": "7", "tier": "shop"}
    assert p["line_items"] == [{"price": "p_shop", "quantity": 1}]
    assert (p["mode"], p["client_reference_id"]) == ("subscription", "7")


def test_on_consent_is_required_and_the_same_keys():
    p = _params(True)
    assert p["consent_collection"] == {"terms_of_service": "required"}
    assert set(p) == KEYS | {"consent_collection"}
    assert {k: v for k, v in p.items() if k != "consent_collection"} == _params(False)


class _Sessions:
    def __init__(self):
        self.seen: list[dict] = []

    def create(self, params):
        self.seen.append(params)
        return {"url": "https://checkout.example/x", "id": "cs_x", "customer": None}


@pytest.mark.parametrize("on", [False, True])
def test_the_stripe_provider_reads_the_switch(monkeypatch, on):
    settings = Settings(_env_file=None, stripe_price_shop="p_shop",
                        checkout_terms_consent=on)
    provider = StripeBillingProvider("sk_test_x", "", settings=settings)
    sessions = _Sessions()
    fake = SimpleNamespace(v1=SimpleNamespace(checkout=SimpleNamespace(sessions=sessions)))
    monkeypatch.setattr(provider, "_stripe", lambda: fake)
    monkeypatch.setattr(provider, "_call", lambda what, fn: fn())
    provider.create_checkout_session(7, "o@ex.com", "shop", "https://s/", "https://c/")
    (seen,) = sessions.seen
    assert ("consent_collection" in seen) is on
    assert seen == _params(on)


@pytest.mark.parametrize("on", ["false", "true"])
def test_the_route_answers_the_same_url_from_the_fake_provider(tmp_path, monkeypatch, on):
    db = new_db(tmp_path, monkeypatch)
    monkeypatch.setenv("MOTODIAG_CHECKOUT_TERMS_CONSENT", on)
    reset_settings()
    try:
        key = make_key(db, make_user(db, "olga"))
        r = client(db).post("/v1/billing/checkout-session",
                            headers={"X-API-Key": key}, json={"tier": "shop"})
        assert r.status_code == 200, r.text
        assert "fake-billing.local" in r.json()["checkout_url"]
    finally:
        reset_settings()
