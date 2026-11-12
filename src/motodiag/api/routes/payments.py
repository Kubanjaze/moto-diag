"""A shop's card payments over HTTP (Phase 372).

Five routes in front of Phase 273's functions, called as they are:

- ``GET  /v1/shop/{shop_id}/payments/account``: the shop's Stripe account,
  as stored, or Stripe's reading of the moment with ``?refresh=true``
  (any active member);
- ``POST /v1/shop/{shop_id}/payments/connect``: create the account if the
  shop has none, and a one-time onboarding link (``manage_billing``);
- ``POST /v1/shop/{shop_id}/invoices/{invoice_id}/payments/checkout`` and
  ``.../payments/terminal``: start a payment of the invoice, online or at
  the shop's reader (``manage_shop``);
- ``GET  /v1/shop/{shop_id}/invoices/{invoice_id}/payments``: the
  invoice's payments, which is how the app learns the outcome
  (``manage_shop``).

Starting a payment never pays the invoice: only Stripe's verified news
does (the webhook or the payments feed). The refusals are mapped in
``motodiag.api.errors``; nothing here catches an exception.
"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel

from motodiag.api.deps import get_db_path
from motodiag.api.routes.shop_mgmt import require_shop_access
from motodiag.auth.deps import AuthedUser, require_tier
from motodiag.cli.payments import PAID_BY_EVENT
from motodiag.core.database import get_connection
from motodiag.payments.connect import (
    ShopAccount,
    connect_shop,
    get_shop_account,
    onboarding_link,
    refresh_status,
)
from motodiag.payments.invoice_payments import (
    StartedPayment,
    payments_for_invoice,
    start_checkout,
    start_terminal,
)
from motodiag.shop.invoicing import InvoiceNotFoundError

router = APIRouter(prefix="/shop", tags=["payments"])

_PROBLEM = {"application/json": {"schema": {"$ref": "#/components/schemas/ProblemDetail"}}}

ERRORS: dict[int | str, dict[str, Any]] = {
    403: {"$ref": "#/components/responses/Forbidden"},
    409: {
        "description": (
            "Stripe cannot be asked for this yet: the shop has no account or "
            "it cannot take card payments, the invoice is not sent or "
            "overdue, the shop has no reader, or a contact email is missing. "
            "The detail says which, and what to do."
        ),
        "content": _PROBLEM,
    },
    503: {
        "description": (
            "Payments are not configured on this server, or Stripe could not "
            "be reached or refused the request. The detail names the setting "
            "or the Stripe call, never a key."
        ),
        "content": _PROBLEM,
    },
}


class PaymentAccount(BaseModel):
    stripe_account_id: str
    card_payments_status: Optional[str]
    requirements_due: Optional[int]
    status_checked_at: Optional[str]
    livemode: bool
    can_take_payments: bool


class ConnectRequest(BaseModel):
    contact_email: Optional[str] = None
    country: Optional[str] = None
    currency: Optional[str] = None


class ConnectAnswer(BaseModel):
    stripe_account_id: str
    created: bool
    onboarding_url: str
    expires_at: Optional[str]
    card_payments_status: Optional[str]


class CheckoutStarted(BaseModel):
    payment_id: int
    invoice_number: str
    amount_cents: int
    currency: str
    channel: str
    checkout_url: str
    paid_when: str


class TerminalStarted(BaseModel):
    payment_id: int
    invoice_number: str
    amount_cents: int
    currency: str
    channel: str
    payment_intent_id: str
    reader_action_status: Optional[str]
    paid_when: str


class InvoicePayment(BaseModel):
    id: int
    channel: str
    amount_cents: int
    currency: str
    status: str
    outcome: Optional[str]
    outcome_reason: Optional[str]
    failure_message: Optional[str]
    refunded_cents: int
    started_at: str
    settled_at: Optional[str]
    started_by_user_id: Optional[int]


class InvoicePayments(BaseModel):
    items: list[InvoicePayment]
    total: int


def _account(acct: ShopAccount) -> PaymentAccount:
    return PaymentAccount(
        stripe_account_id=acct.stripe_account_id,
        card_payments_status=acct.card_payments_status,
        requirements_due=acct.requirements_due,
        status_checked_at=acct.status_checked_at,
        livemode=acct.livemode,
        can_take_payments=acct.can_take_payments,
    )


def _invoice_shop_id(invoice_id: int, db_path: str) -> Optional[int]:
    """The shop of the invoice's work order; ``None`` when either is missing."""
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT w.shop_id FROM invoices i "
            "JOIN work_orders w ON w.id = i.work_order_id WHERE i.id = ?",
            (invoice_id,),
        ).fetchone()
    return None if row is None else row["shop_id"]


def _require_invoice_at_shop(invoice_id: int, shop_id: int, db_path: str) -> None:
    """An invoice at another shop looks like no invoice."""
    if _invoice_shop_id(invoice_id, db_path) != shop_id:
        raise InvoiceNotFoundError(
            f"invoice id={invoice_id} not found at shop id={shop_id}"
        )


@router.get(
    "/{shop_id}/payments/account",
    response_model=PaymentAccount,
    summary="The shop's Stripe account",
    responses=ERRORS,
)
def payments_account(
    shop_id: int,
    refresh: bool = False,
    user: AuthedUser = Depends(require_tier("shop")),
    db_path: str = Depends(get_db_path),
) -> PaymentAccount:
    """As stored, or with ``refresh=true`` read from Stripe first and stored,
    as `motodiag shop payments status` does. Any active member may read it."""
    require_shop_access(shop_id, user, db_path)
    acct = get_shop_account(shop_id, db_path=db_path)
    if acct is None:
        raise HTTPException(404, "this shop has no Stripe account yet")
    if refresh:
        acct = refresh_status(shop_id, db_path=db_path)
    return _account(acct)


@router.post(
    "/{shop_id}/payments/connect",
    response_model=ConnectAnswer,
    summary="Connect the shop to Stripe and get its onboarding link",
    responses={
        **ERRORS,
        201: {"description": "The shop's Stripe account was created now.",
              "model": ConnectAnswer},
        200: {"description": (
            "The shop already had an account; only a fresh link was made. "
            "Stripe's warning: the link is used once, by the shop's owner, "
            "opened inside the app, and never sent by email or text."
        )},
    },
)
def payments_connect(
    shop_id: int,
    body: ConnectRequest,
    response: Response,
    user: AuthedUser = Depends(require_tier("shop")),
    db_path: str = Depends(get_db_path),
) -> ConnectAnswer:
    """``contact_email`` is required the first time. ``country`` (two
    letters) and ``currency`` (three) default to the shop's tax
    jurisdiction. Stripe's warning: the onboarding link is used once, by
    the shop's owner, opened inside the app."""
    require_shop_access(shop_id, user, db_path, permission="manage_billing")
    acct, created = connect_shop(
        shop_id, body.contact_email or "", country=body.country,
        currency=body.currency, user_id=user.id, db_path=db_path,
    )
    url, expires_at = onboarding_link(shop_id, db_path=db_path)
    response.status_code = 201 if created else 200
    return ConnectAnswer(
        stripe_account_id=acct.stripe_account_id,
        created=created,
        onboarding_url=url,
        expires_at=expires_at,
        card_payments_status=acct.card_payments_status,
    )


def _started_fields(p: StartedPayment) -> dict[str, Any]:
    return {
        "payment_id": p.payment_id,
        "invoice_number": p.invoice_number,
        "amount_cents": p.amount_cents,
        "currency": p.currency,
        "channel": p.channel,
        "paid_when": PAID_BY_EVENT,
    }


@router.post(
    "/{shop_id}/invoices/{invoice_id}/payments/checkout",
    response_model=CheckoutStarted,
    status_code=201,
    summary="Start an online payment of the invoice (a pay-link)",
    responses=ERRORS,
)
def payments_checkout(
    shop_id: int,
    invoice_id: int,
    user: AuthedUser = Depends(require_tier("shop")),
    db_path: str = Depends(get_db_path),
) -> CheckoutStarted:
    """A Stripe Checkout page on the shop's account for the invoice's total.
    The invoice is not paid by this: see ``paid_when``."""
    require_shop_access(shop_id, user, db_path, permission="manage_shop")
    _require_invoice_at_shop(invoice_id, shop_id, db_path)
    p = start_checkout(invoice_id, user_id=user.id, db_path=db_path)
    return CheckoutStarted(**_started_fields(p), checkout_url=p.checkout_url or "")


@router.post(
    "/{shop_id}/invoices/{invoice_id}/payments/terminal",
    response_model=TerminalStarted,
    status_code=201,
    summary="Send the invoice to the shop's card reader",
    responses=ERRORS,
)
def payments_terminal(
    shop_id: int,
    invoice_id: int,
    user: AuthedUser = Depends(require_tier("shop")),
    db_path: str = Depends(get_db_path),
) -> TerminalStarted:
    """A card-present payment sent to the shop's reader. The invoice is not
    paid by this: see ``paid_when``."""
    require_shop_access(shop_id, user, db_path, permission="manage_shop")
    _require_invoice_at_shop(invoice_id, shop_id, db_path)
    p = start_terminal(invoice_id, user_id=user.id, db_path=db_path)
    return TerminalStarted(
        **_started_fields(p),
        payment_intent_id=p.payment_intent_id or "",
        reader_action_status=p.reader_action_status,
    )


@router.get(
    "/{shop_id}/invoices/{invoice_id}/payments",
    response_model=InvoicePayments,
    summary="An invoice's Stripe payments and their outcomes",
    responses=ERRORS,
)
def invoice_payments(
    shop_id: int,
    invoice_id: int,
    user: AuthedUser = Depends(require_tier("shop")),
    db_path: str = Depends(get_db_path),
) -> InvoicePayments:
    """Oldest first, as `motodiag shop invoice payments` lists them."""
    require_shop_access(shop_id, user, db_path, permission="manage_shop")
    _require_invoice_at_shop(invoice_id, shop_id, db_path)
    rows = payments_for_invoice(invoice_id, db_path=db_path)
    items = [InvoicePayment(**{k: r[k] for k in InvoicePayment.model_fields})
             for r in rows]
    return InvoicePayments(items=items, total=len(items))
