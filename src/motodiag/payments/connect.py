"""A shop's Stripe connected account (Phase 273, the operator's 1A).

Each shop is a v2 Account with the ``merchant`` configuration: the full
Stripe Dashboard, Stripe collects its fees from the shop and carries
negative balances, and payments are direct charges on the shop's account.
Onboarding is Stripe-hosted.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from motodiag.accounting import tax as tax_mod
from motodiag.core.config import Settings, get_settings
from motodiag.core.database import get_connection
from motodiag.core.timestamps import utc_now as _now
from motodiag.payments import stripe_api
from motodiag.shop.shop_repo import get_shop

# The operator's 1A (2026-10-06). `defaults.responsibilities` cannot be
# changed after the merchant configuration is added (Stripe, C2).
DASHBOARD = "full"
FEES_COLLECTOR = "stripe"
LOSSES_COLLECTOR = "stripe"


class ConnectError(ValueError):
    """A shop cannot be connected or paid as asked; the message says why."""


@dataclass(frozen=True)
class ShopAccount:
    shop_id: int
    stripe_account_id: str
    country: str
    currency: str
    card_payments_status: Optional[str]
    requirements_due: Optional[int]
    status_checked_at: Optional[str]
    livemode: bool

    @property
    def can_take_payments(self) -> bool:
        return self.card_payments_status == "active"


def get_shop_account(shop_id: int, db_path: Optional[str] = None) -> Optional[ShopAccount]:
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM shop_payment_accounts WHERE shop_id = ?", (shop_id,)
        ).fetchone()
    if row is None:
        return None
    return ShopAccount(
        shop_id=row["shop_id"],
        stripe_account_id=row["stripe_account_id"],
        country=row["country"],
        currency=row["currency"],
        card_payments_status=row["card_payments_status"],
        requirements_due=row["requirements_due"],
        status_checked_at=row["status_checked_at"],
        livemode=bool(row["livemode"]),
    )


def require_payable_account(shop_id: int, db_path: Optional[str] = None) -> ShopAccount:
    """The shop's account, if Stripe has made ``card_payments`` active."""
    acct = get_shop_account(shop_id, db_path=db_path)
    if acct is None:
        raise ConnectError(
            f"shop {shop_id} has no Stripe account; connect it with "
            f"`motodiag shop payments connect --shop {shop_id}`"
        )
    if not acct.can_take_payments:
        seen = acct.card_payments_status or "not yet read"
        raise ConnectError(
            f"shop {shop_id}'s Stripe account cannot take card payments yet "
            f"(card_payments: {seen}). Finish onboarding, then run "
            f"`motodiag shop payments status --shop {shop_id}`."
        )
    return acct


def _country_and_currency(shop_id: int, country: Optional[str],
                          currency: Optional[str],
                          db_path: Optional[str]) -> tuple[str, str]:
    jur = tax_mod.shop_jurisdiction(shop_id, db_path=db_path)
    if country is None and jur is not None:
        country = jur["code"].split("-")[0]
    if currency is None and jur is not None:
        currency = jur["currency"]
    if not country or not currency:
        raise ConnectError(
            f"shop {shop_id} has no tax jurisdiction to take its country and "
            "currency from; pass --country and --currency, or set it with "
            f"`motodiag shop tax jurisdiction set --shop {shop_id} --code CODE`"
        )
    if len(country) != 2 or len(currency) != 3:
        raise ConnectError("country is two letters and currency three (ISO)")
    return country.lower(), currency.lower()


def connect_shop(shop_id: int, contact_email: str, *,
                 country: Optional[str] = None, currency: Optional[str] = None,
                 user_id: Optional[int] = None,
                 settings: Optional[Settings] = None,
                 db_path: Optional[str] = None) -> tuple[ShopAccount, bool]:
    """Create the shop's v2 Account if it has none.

    Returns the account and whether it was created now.
    """
    shop = get_shop(shop_id, db_path=db_path)
    if shop is None:
        raise ConnectError(f"shop not found: id={shop_id}")
    existing = get_shop_account(shop_id, db_path=db_path)
    if existing is not None:
        return existing, False
    if not contact_email or "@" not in contact_email:
        raise ConnectError("a contact email for the shop's owner is required (--email)")
    country, currency = _country_and_currency(shop_id, country, currency, db_path)
    sc = stripe_api.client(settings)
    account = stripe_api.call("create the shop's account", lambda: sc.v2.core.accounts.create({
        "display_name": shop["name"],
        "contact_email": contact_email,
        "dashboard": DASHBOARD,
        "identity": {"country": country},
        "configuration": {
            "merchant": {"capabilities": {"card_payments": {"requested": True}}},
        },
        "defaults": {
            "currency": currency,
            "responsibilities": {
                "fees_collector": FEES_COLLECTOR,
                "losses_collector": LOSSES_COLLECTOR,
            },
        },
        "include": ["configuration.merchant", "requirements"],
    }))
    data = stripe_api.as_dict(account)
    card_status, due = _read_status(data)
    with get_connection(db_path) as conn:
        conn.execute(
            """INSERT INTO shop_payment_accounts
               (shop_id, stripe_account_id, dashboard, fees_collector,
                losses_collector, country, currency, card_payments_status,
                requirements_due, status_checked_at, livemode, created_by_user_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (shop_id, data["id"], DASHBOARD, FEES_COLLECTOR, LOSSES_COLLECTOR,
             country, currency, card_status, due, _now(),
             1 if data.get("livemode") else 0, user_id),
        )
    return get_shop_account(shop_id, db_path=db_path), True


def onboarding_link(shop_id: int, *, settings: Optional[Settings] = None,
                    db_path: Optional[str] = None) -> tuple[str, Optional[str]]:
    """A one-time Stripe-hosted onboarding URL and when it expires."""
    s = settings or get_settings()
    acct = get_shop_account(shop_id, db_path=db_path)
    if acct is None:
        raise ConnectError(f"shop {shop_id} has no Stripe account yet")
    sc = stripe_api.client(s)
    link = stripe_api.call("create an onboarding link", lambda: sc.v2.core.account_links.create({
        "account": acct.stripe_account_id,
        "use_case": {
            "type": "account_onboarding",
            "account_onboarding": {
                "refresh_url": s.connect_refresh_url,
                "return_url": s.connect_return_url,
            },
        },
    }))
    data = stripe_api.as_dict(link)
    return data["url"], data.get("expires_at")


def refresh_status(shop_id: int, *, settings: Optional[Settings] = None,
                   db_path: Optional[str] = None) -> ShopAccount:
    """Read the account from Stripe and store what it says."""
    acct = get_shop_account(shop_id, db_path=db_path)
    if acct is None:
        raise ConnectError(
            f"shop {shop_id} has no Stripe account; connect it with "
            f"`motodiag shop payments connect --shop {shop_id}`"
        )
    sc = stripe_api.client(settings)
    account = stripe_api.call("read the shop's account", lambda: sc.v2.core.accounts.retrieve(
        acct.stripe_account_id,
        {"include": ["configuration.merchant", "requirements"]},
    ))
    card_status, due = _read_status(stripe_api.as_dict(account))
    with get_connection(db_path) as conn:
        conn.execute(
            "UPDATE shop_payment_accounts SET card_payments_status = ?, "
            "requirements_due = ?, status_checked_at = ? WHERE shop_id = ?",
            (card_status, due, _now(), shop_id),
        )
    return get_shop_account(shop_id, db_path=db_path)


def _read_status(data: dict) -> tuple[Optional[str], Optional[int]]:
    """``card_payments``' status, and how many requirements are due now.

    ``None`` where Stripe's answer does not include them: never assumed.
    """
    merchant = ((data.get("configuration") or {}).get("merchant") or {})
    card = ((merchant.get("capabilities") or {}).get("card_payments") or {})
    status = card.get("status")
    reqs = data.get("requirements")
    due = None
    if isinstance(reqs, dict) and reqs.get("entries") is not None:
        due = sum(
            1 for e in reqs["entries"]
            if ((e.get("minimum_deadline") or {}).get("status")
                in ("currently_due", "past_due"))
        )
    return status, due
