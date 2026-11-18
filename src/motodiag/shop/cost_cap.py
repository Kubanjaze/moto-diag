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

Phase 404 (F271, the operator's K84) adds each plan's AI figure beside the
brake: $5, $50 and $150 a shop a calendar month, kept by the server. The
brake stays off.

The check is deliberately BEFORE the paid call. Checking afterwards would
bill the call that crossed the line and report it as refused.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from motodiag.billing.subscription_repo import shop_plan
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


#: Phase 404 (F271, the operator's K84): each plan's AI figure, a limit the
#: server keeps per shop per UTC calendar month, in cents. These numbers and
#: no other. ``cli.subscription.TIER_LIMITS`` shows the same figures, held
#: equal by ``tests/test_phase404_plan_names.py``.
PLAN_AI_CENTS: dict[str, int] = {
    "individual": 500,
    "shop": 5000,
    "company": 15000,
}

#: The plan as the refusal names it.
PLAN_NAMES: dict[str, str] = {
    "individual": "Individual",
    "shop": "Shop",
    "company": "Company",
}


def month_turns(now: datetime) -> datetime:
    """The first instant of the UTC calendar month after ``now``'s."""
    now = now.astimezone(timezone.utc)
    if now.month == 12:
        return datetime(now.year + 1, 1, 1, tzinfo=timezone.utc)
    return datetime(now.year, now.month + 1, 1, tzinfo=timezone.utc)


class PlanAILimitReached(CostCapExceeded):
    """Raised before a paid call when the shop has used its plan's AI figure
    for this UTC calendar month (Phase 404).

    A :class:`CostCapExceeded`, so every handler of the brake catches it:
    ``motodiag diagnose`` prints it red and exits 1, the video sweep leaves
    the video pending. The API answers it 402 ``plan-ai-limit-reached``.
    """

    def __init__(self, shop_id: int, spent_cents: int, cap_cents: int,
                 plan: str, now: Optional[datetime] = None):
        when = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
        turns = month_turns(when)
        self.shop_id = shop_id
        self.spent_cents = spent_cents
        self.cap_cents = cap_cents
        self.plan = plan
        self.resets_on = turns.date()
        RuntimeError.__init__(
            self,
            f"The {PLAN_NAMES.get(plan, plan)} plan's ${cap_cents / 100:.2f} "
            f"of AI for {when:%B} is used up. It starts again on "
            f"{turns.day} {turns:%B %Y} (UTC).",
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

    Phase 404 (F271): beside the brake, the shop's plan figure
    (:data:`PLAN_AI_CENTS`), read through the shop's active owners
    (:func:`motodiag.billing.subscription_repo.shop_plan`). The lower of
    the two refuses first. A shop with no plan is held by the brake alone.
    """
    if shop_id is None:
        return
    cap = cap_cents()
    plan = shop_plan(shop_id, db_path=db_path)
    figure = PLAN_AI_CENTS.get(plan) if plan is not None else None
    limits = [c for c in (cap if cap > 0 else None, figure) if c is not None]
    if not limits:
        return
    spent = shop_cost_this_month(shop_id, db_path=db_path)
    if spent < min(limits):
        return
    # The lower of the two refuses; on a tie the plan's, whose message
    # names the plan and the day the month turns.
    if plan is not None and figure is not None and (cap <= 0 or figure <= cap):
        raise PlanAILimitReached(shop_id, spent, figure, plan)
    raise CostCapExceeded(shop_id, spent, cap)
