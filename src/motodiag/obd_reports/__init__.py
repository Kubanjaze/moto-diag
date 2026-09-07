"""Field telemetry for OBD adapter connection failures.

Exists so the first real-world failure of the UNVERIFIED BLE transport
reaches the maintainer (F56), instead of a mechanic silently concluding
the app does not work with their dongle.
"""

from motodiag.obd_reports.repo import (
    ALERT_SUPPRESSION_MINUTES,
    list_failures,
    mark_notified,
    record_failure,
    should_alert,
)

__all__ = [
    "ALERT_SUPPRESSION_MINUTES",
    "list_failures",
    "mark_notified",
    "record_failure",
    "should_alert",
]
