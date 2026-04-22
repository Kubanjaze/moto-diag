"""Built-in customer-notification templates (Phase 170).

10 workflow events × 2-3 channels each. `string.Template` placeholders;
unresolved placeholders raise a clean error at render time rather than
leaking ``$customer_name`` to a live customer. Content baked from
motorcycle-mechanic feedback: first-name recipient, WO # + shop phone in
every message, plain language, prominent totals, shop-hours in pickup
messages.
"""

from __future__ import annotations

from string import Template
from typing import Literal, Optional


NotificationEvent = Literal[
    "wo_opened", "wo_in_progress", "wo_on_hold", "wo_completed",
    "wo_cancelled", "invoice_issued", "invoice_paid",
    "parts_arrived", "estimate_ready", "approval_requested",
]

NotificationChannel = Literal["email", "sms", "in_app"]


NOTIFICATION_EVENTS: tuple[str, ...] = (
    "wo_opened", "wo_in_progress", "wo_on_hold", "wo_completed",
    "wo_cancelled", "invoice_issued", "invoice_paid",
    "parts_arrived", "estimate_ready", "approval_requested",
)

NOTIFICATION_CHANNELS: tuple[str, ...] = ("email", "sms", "in_app")


class NotificationTemplate:
    """One template, one (event, channel) pair.

    Email templates have ``subject`` + ``body``; SMS/in_app are body-only
    and MAY set ``subject=None``.
    """

    __slots__ = ("event", "channel", "subject_tmpl", "body_tmpl")

    def __init__(
        self, event: str, channel: str,
        body: str, subject: Optional[str] = None,
    ) -> None:
        self.event = event
        self.channel = channel
        self.subject_tmpl = Template(subject) if subject else None
        self.body_tmpl = Template(body)

    def render(self, context: dict) -> tuple[Optional[str], str]:
        """Render (subject, body). Raises KeyError on unresolved placeholder."""
        subject: Optional[str] = None
        if self.subject_tmpl is not None:
            subject = self.subject_tmpl.substitute(context)
        body = self.body_tmpl.substitute(context)
        return subject, body


# ---------------------------------------------------------------------------
# Template catalog
# ---------------------------------------------------------------------------


_TEMPLATES: dict[tuple[str, str], NotificationTemplate] = {}


def _register(event: str, channel: str, body: str,
              subject: Optional[str] = None) -> None:
    _TEMPLATES[(event, channel)] = NotificationTemplate(
        event, channel, body=body, subject=subject,
    )


# --- wo_opened -------------------------------------------------------------

_register("wo_opened", "email",
    subject="Work order #$wo_id opened for your $bike_label",
    body=(
        "Hey $customer_first,\n\n"
        "We've opened work order #$wo_id for your $bike_label: "
        "$wo_title.\n"
        "We'll keep you posted as we dig in. Questions? $shop_phone.\n\n"
        "— $shop_name"
    ),
)
_register("wo_opened", "sms",
    body=(
        "$shop_name: WO #$wo_id opened for your $bike_label "
        "($wo_title). We'll keep you posted. $shop_phone"
    ),
)
_register("wo_opened", "in_app",
    body="WO #$wo_id opened — $wo_title ($customer_first, $bike_label)",
)

# --- wo_in_progress --------------------------------------------------------

_register("wo_in_progress", "email",
    subject="WO #$wo_id — work has started on your $bike_label",
    body=(
        "Hey $customer_first,\n\n"
        "Work has started on your $bike_label (WO #$wo_id: $wo_title).\n"
        "We'll reach out if anything unexpected comes up or if we need "
        "your approval on additional work.\n\n"
        "— $shop_name ($shop_phone)"
    ),
)
_register("wo_in_progress", "sms",
    body=(
        "$shop_name: started work on your $bike_label (WO #$wo_id). "
        "$shop_phone"
    ),
)

# --- wo_on_hold ------------------------------------------------------------

_register("wo_on_hold", "email",
    subject="WO #$wo_id — on hold for your $bike_label",
    body=(
        "Hey $customer_first,\n\n"
        "WO #$wo_id ($wo_title) is on hold. $hold_reason\n"
        "Call or text when you're ready to move forward.\n\n"
        "— $shop_name ($shop_phone)"
    ),
)
_register("wo_on_hold", "sms",
    body=(
        "$shop_name: WO #$wo_id on hold. $hold_reason "
        "Call $shop_phone when ready."
    ),
)

# --- wo_completed ----------------------------------------------------------

_register("wo_completed", "email",
    subject="Your $bike_label is ready — WO #$wo_id",
    body=(
        "Hey $customer_first,\n\n"
        "Good news — your $bike_label is done.\n"
        "WO #$wo_id: $wo_title\n"
        "Final total: $$$invoice_total\n"
        "$shop_hours_line\n"
        "Questions? Call $shop_phone.\n\n"
        "— $shop_name"
    ),
)
_register("wo_completed", "sms",
    body=(
        "$shop_name: your $bike_label is done (WO #$wo_id). "
        "Total $$$invoice_total. Pickup: $shop_hours_short. $shop_phone"
    ),
)
_register("wo_completed", "in_app",
    body="WO #$wo_id complete — $customer_first's $bike_label ($$$invoice_total)",
)

# --- wo_cancelled ----------------------------------------------------------

_register("wo_cancelled", "email",
    subject="WO #$wo_id cancelled",
    body=(
        "Hey $customer_first,\n\n"
        "WO #$wo_id ($wo_title) has been cancelled. $cancellation_reason\n"
        "If this is a mistake, call $shop_phone and we'll reopen it.\n\n"
        "— $shop_name"
    ),
)
_register("wo_cancelled", "sms",
    body=(
        "$shop_name: WO #$wo_id cancelled. $cancellation_reason "
        "Questions? $shop_phone"
    ),
)

# --- invoice_issued --------------------------------------------------------

_register("invoice_issued", "email",
    subject="Invoice $invoice_number — $$$invoice_total",
    body=(
        "Hey $customer_first,\n\n"
        "Invoice $invoice_number for the work on your $bike_label: "
        "$$$invoice_total total.\n"
        "Pay when convenient — cash, card, or bank transfer all work.\n"
        "WO #$wo_id: $wo_title\n\n"
        "— $shop_name ($shop_phone)"
    ),
)
_register("invoice_issued", "sms",
    body=(
        "$shop_name: invoice $invoice_number issued for your "
        "$bike_label — $$$invoice_total. $shop_phone"
    ),
)

# --- invoice_paid ----------------------------------------------------------

_register("invoice_paid", "email",
    subject="Receipt — Invoice $invoice_number paid",
    body=(
        "Hey $customer_first,\n\n"
        "Thanks — we've received payment on invoice $invoice_number "
        "($$$invoice_total).\n"
        "Ride safe. Let us know if your $bike_label gives you any "
        "trouble and we'll sort it.\n\n"
        "— $shop_name"
    ),
)
_register("invoice_paid", "sms",
    body=(
        "$shop_name: payment received on invoice $invoice_number "
        "($$$invoice_total). Thanks!"
    ),
)

# --- parts_arrived ---------------------------------------------------------

_register("parts_arrived", "email",
    subject="Parts arrived for WO #$wo_id",
    body=(
        "Hey $customer_first,\n\n"
        "Your parts came in for WO #$wo_id ($wo_title):\n"
        "$parts_list\n"
        "Scheduling install now; we'll reach out when the $bike_label "
        "is ready.\n\n"
        "— $shop_name ($shop_phone)"
    ),
)
_register("parts_arrived", "sms",
    body=(
        "$shop_name: parts in for WO #$wo_id — $parts_list. "
        "Scheduling install."
    ),
)

# --- estimate_ready --------------------------------------------------------

_register("estimate_ready", "email",
    subject="Estimate for your $bike_label — WO #$wo_id",
    body=(
        "Hey $customer_first,\n\n"
        "Estimate for WO #$wo_id ($wo_title): $$$estimate_total.\n"
        "Labor $estimate_labor_hours hours; parts listed below.\n"
        "$parts_list\n"
        "Reply or call $shop_phone to approve and we'll get started.\n\n"
        "— $shop_name"
    ),
)
_register("estimate_ready", "sms",
    body=(
        "$shop_name: estimate for WO #$wo_id — $$$estimate_total. "
        "Call $shop_phone to approve."
    ),
)

# --- approval_requested ----------------------------------------------------

_register("approval_requested", "email",
    subject="Approval needed — WO #$wo_id",
    body=(
        "Hey $customer_first,\n\n"
        "While working on your $bike_label we found: $approval_finding\n"
        "Additional cost: $$$approval_cost\n"
        "Reply yes/no or call $shop_phone. No work happens until we "
        "hear from you.\n\n"
        "— $shop_name"
    ),
)
_register("approval_requested", "sms",
    body=(
        "$shop_name: WO #$wo_id — $approval_finding (+$$$approval_cost). "
        "OK? Reply y/n or call $shop_phone."
    ),
)
_register("approval_requested", "in_app",
    body="WO #$wo_id: $customer_first approval needed — $approval_finding (+$$$approval_cost)",
)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


class UnknownEventError(ValueError):
    """Raised when an event string is not in NOTIFICATION_EVENTS."""


class TemplateNotFoundError(KeyError):
    """Raised when no template exists for (event, channel)."""


def get_template(event: str, channel: str) -> NotificationTemplate:
    """Fetch the template for (event, channel). Raises on miss."""
    if event not in NOTIFICATION_EVENTS:
        raise UnknownEventError(
            f"event {event!r} not in {NOTIFICATION_EVENTS}"
        )
    if channel not in NOTIFICATION_CHANNELS:
        raise ValueError(
            f"channel {channel!r} not in {NOTIFICATION_CHANNELS}"
        )
    try:
        return _TEMPLATES[(event, channel)]
    except KeyError as e:
        raise TemplateNotFoundError(
            f"no template for ({event!r}, {channel!r}); try a "
            f"different channel"
        ) from e


def list_templates() -> list[dict]:
    """Enumerate all registered templates."""
    out = []
    for (event, channel), t in sorted(_TEMPLATES.items()):
        out.append({
            "event": event,
            "channel": channel,
            "has_subject": t.subject_tmpl is not None,
        })
    return out
