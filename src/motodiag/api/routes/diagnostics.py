"""Field telemetry from the mobile app.

`POST /v1/diagnostics/obd-failure` — a mechanic could not connect an OBD
adapter. Recorded, and the maintainer is alerted.

Why this route exists: the BLE transport ships UNVERIFIED against real
hardware (F56). Buying an adapter to exercise a path no user can
currently reach was judged the wrong trade, so the alternative is to
make the first real failure LOUD. Without it the failure mode is a
mechanic quietly concluding the app does not work with their dongle,
and nobody ever hearing about it.

Authed, because an unauthenticated telemetry sink is an invitation to
fill someone's database.
"""

from __future__ import annotations

import logging
from typing import Literal, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field

from motodiag.api.deps import get_db_path
from motodiag.auth.deps import AuthedUser, get_current_user
from motodiag.obd_reports import record_failure
from motodiag.push.events import notify_obd_failure

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/diagnostics", tags=["diagnostics"])

#: Mirrors the mobile `ObdConnectionError` union (src/obd/obdErrors.ts).
#: Literal rather than str per the F37 enum-contract-drift lesson: a
#: client typo should be a 422 here, not a silent row nobody can query.
ObdErrorKind = Literal[
    "ble_powered_off",
    "ble_unauthorized",
    "ble_unsupported",
    "device_not_found",
    "connect_failed",
    "handshake_failed",
    "disconnected_unexpectedly",
]


class ObdFailureRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    error_kind: ObdErrorKind
    # Values mirror the mobile `ObdTransport` union
    # (src/obd/ObdConnection.ts:47) EXACTLY. This first shipped as
    # "classic" against the app's "classic-bt" — the same F37
    # enum-contract drift the comment above warns about, caught only
    # because the mobile typecheck rejected the mismatch.
    transport: Optional[Literal["ble", "classic-bt", "wifi"]] = None
    device_id: Optional[str] = Field(None, max_length=200)
    message: Optional[str] = Field(None, max_length=2000)
    app_version: Optional[str] = Field(None, max_length=50)
    platform: Optional[str] = Field(None, max_length=50)
    os_version: Optional[str] = Field(None, max_length=50)


class ObdFailureResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    recorded: bool
    #: Whether the maintainer was alerted. False is normal and expected —
    #: alerts are disabled by default, and repeat failures are
    #: deliberately suppressed.
    alerted: bool


@router.post(
    "/obd-failure",
    response_model=ObdFailureResponse,
    status_code=201,
    summary="Report an OBD adapter connection failure from the field",
)
def report_obd_failure(
    req: ObdFailureRequest,
    user: AuthedUser = Depends(get_current_user),
    db_path: str = Depends(get_db_path),
) -> ObdFailureResponse:
    report_id = record_failure(
        user_id=user.id,
        error_kind=req.error_kind,
        transport=req.transport,
        device_id=req.device_id,
        message=req.message,
        app_version=req.app_version,
        platform=req.platform,
        os_version=req.os_version,
        db_path=db_path,
    )
    # WARNING, not INFO: this is a user who could not do the thing they
    # opened the app to do. It should be visible without turning up the
    # log level (the F52/F57 lesson about logs nobody sees).
    logger.warning(
        "OBD failure reported: kind=%s transport=%s device=%s user=%s "
        "app=%s %s/%s — %s",
        req.error_kind, req.transport, req.device_id, user.id,
        req.app_version, req.platform, req.os_version,
        (req.message or "")[:200],
    )
    alerted = notify_obd_failure(
        report_id=report_id,
        error_kind=req.error_kind,
        transport=req.transport,
        device_id=req.device_id,
        message=req.message,
        db_path=db_path,
    )
    return ObdFailureResponse(recorded=True, alerted=alerted)
