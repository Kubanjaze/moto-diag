"""Phase 372 — the payment routes are reached from their integration points.

`create_app` routes the five paths under the `payments` tag; the document
names the tag, gates it on the tier and declares each refusal; the error
map holds the four Phase 273 refusals; each route checks the shop and the
permission its verb needs. Source is read with `code_of`, comments and
docstrings blanked, as 244G's meta-guard requires.
"""

from __future__ import annotations

import pytest
from support.source_guards import code_of

from motodiag.api import create_app, openapi
from motodiag.api.errors import _exc_class_chain
from motodiag.api.routes import payments as routes
from motodiag.payments.connect import ConnectError
from motodiag.payments.stripe_api import (
    LiveKeyRefused,
    StripeNotConfigured,
    StripeUnavailable,
)

OPERATIONS = [
    ("get", "/v1/shop/{shop_id}/payments/account"),
    ("post", "/v1/shop/{shop_id}/payments/connect"),
    ("post", "/v1/shop/{shop_id}/invoices/{invoice_id}/payments/checkout"),
    ("post", "/v1/shop/{shop_id}/invoices/{invoice_id}/payments/terminal"),
    ("get", "/v1/shop/{shop_id}/invoices/{invoice_id}/payments"),
]


@pytest.fixture(scope="module")
def spec():
    return create_app().openapi()


def test_create_app_routes_the_five_paths_under_the_payments_tag(spec):
    for method, path in OPERATIONS:
        assert spec["paths"][path][method]["tags"] == ["payments"], path


def test_the_tag_is_in_the_catalog_and_tier_gated():
    assert "payments" in {t["name"] for t in openapi.TAG_CATALOG}
    assert "payments" in openapi._ALWAYS_TIER_GATED_TAGS


@pytest.mark.parametrize("method,path", OPERATIONS)
def test_every_operation_is_authenticated_and_declares_its_refusals(spec, method, path):
    op = spec["paths"][path][method]
    assert op.get("security"), path
    assert not any(path.startswith(p) for p in openapi.PUBLIC_PATH_PREFIXES)
    assert {"401", "402", "403", "404", "409", "503"} <= set(op["responses"]), path
    assert op["responses"]["403"]["$ref"] == "#/components/responses/Forbidden"


def test_the_error_map_holds_the_four_refusals():
    chain = {cls: (status, slug) for cls, status, slug, _ in _exc_class_chain()}
    assert chain[ConnectError] == (409, "payment-refused")
    assert chain[StripeNotConfigured] == (503, "payments-not-configured")
    assert chain[LiveKeyRefused] == (503, "payments-not-configured")
    assert chain[StripeUnavailable] == (503, "stripe-unavailable")


@pytest.mark.parametrize("fn,permission", [
    (routes.payments_account, None),
    (routes.payments_connect, '"manage_billing"'),
    (routes.payments_checkout, '"manage_shop"'),
    (routes.payments_terminal, '"manage_shop"'),
    (routes.invoice_payments, '"manage_shop"'),
])
def test_each_route_checks_the_shop_and_its_permission(fn, permission):
    code = code_of(fn)
    assert 'Depends(require_tier("shop"))' in code
    if permission is None:
        assert "require_shop_access(shop_id, user, db_path)" in code
    else:
        assert f"require_shop_access(shop_id, user, db_path, permission={permission})" in code


@pytest.mark.parametrize("fn", [routes.payments_checkout, routes.payments_terminal,
                                routes.invoice_payments])
def test_each_invoice_route_checks_the_invoices_shop(fn):
    assert "_require_invoice_at_shop(invoice_id, shop_id, db_path)" in code_of(fn)


def test_the_starts_pass_the_caller():
    assert "start_checkout(invoice_id, user_id=user.id" in code_of(routes.payments_checkout)
    assert "start_terminal(invoice_id, user_id=user.id" in code_of(routes.payments_terminal)
    assert "user_id=user.id" in code_of(routes.payments_connect)


def test_the_route_module_catches_nothing():
    assert "except" not in code_of(routes)
