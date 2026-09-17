"""Phase 209D — the brake, built and left off.

The operator's decision on 2026-09-17, after reading the ledger: build the
instrument, choose the number later. Total spend at that point was **32¢
across 4 calls**, and at measured prices $25/month is about 500 automatic
sweeps or 190 video questions. A limit set from four samples would be a
guess wearing the clothes of a safeguard.

So the mechanism lives here and does nothing until someone sets
``MOTODIAG_COST_CAP_MONTHLY_USD_CENTS``. The setting already defaulted to 0
(``core/config.py``), and 0 keeps its meaning: **no cap**.

What a cap is actually for, once a number exists, is a runaway -- a leaked
key, a retry loop, a sweep firing on every upload overnight -- not a shop's
ordinary month.

The check is deliberately BEFORE the paid call. Checking afterwards would
bill the call that crossed the line and report it as refused.
"""

from __future__ import annotations

import logging
from typing import Optional

from motodiag.core.config import get_settings
from motodiag.shop.cost_repo import shop_cost_this_month

log = logging.getLogger(__name__)


class CostCapExceeded(RuntimeError):
    """Raised before a paid call when the shop is at or over its cap.

    A RuntimeError on purpose: `motodiag diagnose` already turns one into a
    red line and exit 1 (the offline cache-miss surface), so refusing to
    spend arrives the same way as any other reason the command cannot
    produce a diagnosis.
    """

    def __init__(self, shop_id: int, spent_cents: int, cap_cents: int):
        self.shop_id = shop_id
        self.spent_cents = spent_cents
        self.cap_cents = cap_cents
        super().__init__(
            f"shop {shop_id} has spent ${spent_cents / 100:.2f} of its "
            f"${cap_cents / 100:.2f} monthly AI limit"
        )


def cap_cents() -> int:
    """The configured monthly ceiling in cents. 0 means no cap."""
    try:
        return int(getattr(get_settings(), "cost_cap_monthly_usd_cents", 0) or 0)
    except Exception:
        # An unreadable setting must not block work. A cap that fails open is
        # the right failure for a brake nobody has turned on yet.
        log.warning("cost cap setting unreadable; treating as no cap", exc_info=True)
        return 0


def check_cost_cap(
    shop_id: Optional[int], db_path: Optional[str] = None,
) -> None:
    """Raise :class:`CostCapExceeded` if this shop may not spend more.

    A no-op when no cap is set, and when the work has no shop to charge --
    an unattributed call cannot be measured against a per-shop ceiling, and
    refusing it on a number that doesn't describe it would be worse than
    letting it through. Attribution (`shop/attribution.py`) is what shrinks
    that gap.
    """
    cap = cap_cents()
    if cap <= 0 or shop_id is None:
        return
    spent = shop_cost_this_month(shop_id, db_path=db_path)
    if spent >= cap:
        raise CostCapExceeded(shop_id, spent, cap)
