"""Recording what a vision call cost — Phase 244L.

Two vision paths spend money on every call: the sweep
(``analyze_video_frames``) and guidance (``answer_question_about_frames``). The
sweep kept its usage and buried it in an ``analysis_findings`` JSON blob.
Guidance bound it to ``_usage`` — the convention for *deliberately unused* — and
threw it away, so Phase 244J shipped an endpoint that spends a vision call per
request and recorded nothing.

**One choke point on purpose.** Two call sites each remembering to record are two
chances to forget, and forgetting is exactly what happened. Both paths go through
:func:`record_vision_cost`.

**Recording is subordinate to answering.** The money is spent before the ledger
is touched, so a failed write must never cost a technician their answer. Every
failure here is caught and logged.
"""

from __future__ import annotations

import logging
import sqlite3
from decimal import ROUND_HALF_UP, Decimal
from typing import Optional

from motodiag.engine.models import TokenUsage
from motodiag.shop.cost_repo import CostEventKind, record_cost_event

_log = logging.getLogger(__name__)

#: The sweep: a fixed six-category pass over every frame.
KIND_SWEEP: CostEventKind = "vision_sweep"
#: Guidance: one technician question, answered from the frames.
KIND_GUIDANCE: CostEventKind = "vision_guidance"


def cost_usd_to_cents(usd: float) -> int:
    """USD to whole cents, rounded half-up.

    A vision call costs on the order of $0.14, so truncating would lose a
    seventh of it. The ledger stores integer cents because money in a report
    should not carry float error.

    Uses ``Decimal`` with ``ROUND_HALF_UP`` rather than ``round()``: Python's
    builtin is banker's rounding, so ``round(0.5)`` is 0 and a half-cent would
    fall toward even rather than up. Written with ``round()`` first, and the
    docstring said half-up while the code did something else — the kind of
    mismatch that turns into an unexplainable few cents in a monthly report.
    """
    if usd <= 0:
        return 0
    return int(
        Decimal(str(usd)).scaleb(2).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    )


def record_vision_cost(
    usage: Optional[TokenUsage],
    kind: CostEventKind,
    *,
    video_id: Optional[int] = None,
    shop_id: Optional[int] = None,
    db_path: Optional[str] = None,
) -> Optional[int]:
    """Write one ledger row for a vision call. Returns its id, or None.

    Returns None rather than raising when the write fails or there is nothing
    to record — the caller has already paid for the call and already has the
    answer, and losing that answer to a bookkeeping failure would be the worse
    outcome by far.
    """
    if usage is None:
        return None

    def _write(vid: Optional[int]) -> int:
        return record_cost_event(
            kind=kind,
            model=usage.model or "unknown",
            cost_usd_cents=cost_usd_to_cents(usage.cost_estimate),
            video_id=vid,
            shop_id=shop_id,
            # Matches the kind-polymorphic pair the ledger already uses:
            # ('duration_ms', N) for Whisper, ('tokens', N) for Claude.
            units_label="tokens",
            units_value=(usage.input_tokens or 0) + (usage.output_tokens or 0),
            db_path=db_path,
        )

    try:
        return _write(video_id)
    except sqlite3.IntegrityError:
        # The video_id FK failed — most plausibly the video was deleted between
        # the call being made and the cost being recorded. The money was still
        # spent, so record it unlinked rather than losing the row: a ledger that
        # drops charges because a link broke is worse than one with a null link.
        _log.warning(
            "vision cost: video_id=%s did not resolve; recording unlinked",
            video_id,
        )
        try:
            return _write(None)
        except Exception as exc:
            _log.warning("vision cost not recorded (kind=%s): %s", kind, exc)
            return None
    except Exception as exc:
        _log.warning(
            "vision cost not recorded (kind=%s, video_id=%s): %s",
            kind, video_id, exc,
        )
        return None
