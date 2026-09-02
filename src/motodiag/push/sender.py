"""Phase 199 — PushSender seam + APNs implementation.

Seam discipline (196 transport-seam precedent): everything above this
module depends on :class:`PushSender` only. ``ApnsSender`` is the iOS
transport; an FCM sender slots in when Android ships.

``ApnsSender`` imports its heavy deps (httpx/h2, PyJWT, cryptography)
LAZILY — tests and dry-run mode never touch them. Live use requires
``pip install -e ".[push]"`` (extras added this phase).

Config (env, MOTODIAG_ prefix):
    APNS_KEY_PATH  — path to the .p8 auth key
    APNS_KEY_ID    — 10-char key id (e.g. 5F2J49F8UT)
    APNS_TEAM_ID   — developer team id (e.g. B6QK49DPRZ)
    APNS_TOPIC     — bundle id (com.bandithero.motodiag)
    APNS_SANDBOX   — "1" (default) = sandbox gateway (Debug builds)
    APNS_DRY_RUN   — "1" = log instead of sending (default in dev)
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass
from typing import Optional, Protocol

logger = logging.getLogger(__name__)

APNS_HOST_SANDBOX = "https://api.sandbox.push.apple.com"
APNS_HOST_PROD = "https://api.push.apple.com"

#: JWT reuse window — Apple rejects tokens older than 1h; refresh at 45m.
_JWT_REFRESH_SECONDS = 45 * 60


@dataclass
class PushResult:
    ok: bool
    #: True when the token is dead (APNs 410/Unregistered) and should
    #: be pruned from the registry.
    unregistered: bool = False
    detail: str = ""


class PushSender(Protocol):
    """The seam: send one alert to one device token."""

    def send(self, token: str, title: str, body: str,
             thread_id: Optional[str] = None) -> PushResult: ...


class DryRunSender:
    """Logs sends instead of performing them. Default outside prod."""

    def __init__(self) -> None:
        self.sent: list[dict] = []  # test-inspectable

    def send(self, token: str, title: str, body: str,
             thread_id: Optional[str] = None) -> PushResult:
        record = {
            "token": token, "title": title, "body": body,
            "thread_id": thread_id,
        }
        self.sent.append(record)
        logger.info("[push dry-run] %s", record)
        return PushResult(ok=True)


class ApnsSender:
    """Direct APNs over HTTP/2 with .p8 ES256 provider-token auth."""

    def __init__(
        self,
        key_path: str,
        key_id: str,
        team_id: str,
        topic: str,
        sandbox: bool = True,
    ) -> None:
        self.key_path = key_path
        self.key_id = key_id
        self.team_id = team_id
        self.topic = topic
        self.host = APNS_HOST_SANDBOX if sandbox else APNS_HOST_PROD
        self._jwt: Optional[str] = None
        self._jwt_issued_at: float = 0.0
        self._client = None  # lazy httpx.Client(http2=True)

    # -- lazy dependency surface ------------------------------------
    def _get_client(self):
        if self._client is None:
            import httpx  # lazy: [push] extra
            self._client = httpx.Client(http2=True, timeout=10.0)
        return self._client

    def _get_jwt(self) -> str:
        now = time.time()
        if self._jwt and now - self._jwt_issued_at < _JWT_REFRESH_SECONDS:
            return self._jwt
        import jwt  # PyJWT, lazy: [push] extra
        with open(self.key_path, "r", encoding="utf-8") as fh:
            key = fh.read()
        self._jwt = jwt.encode(
            {"iss": self.team_id, "iat": int(now)},
            key,
            algorithm="ES256",
            headers={"kid": self.key_id},
        )
        self._jwt_issued_at = now
        return self._jwt

    # -- seam -------------------------------------------------------
    def send(self, token: str, title: str, body: str,
             thread_id: Optional[str] = None) -> PushResult:
        payload: dict = {
            "aps": {
                "alert": {"title": title, "body": body},
                "sound": "default",
            },
        }
        if thread_id:
            payload["aps"]["thread-id"] = thread_id
        try:
            response = self._get_client().post(
                f"{self.host}/3/device/{token}",
                json=payload,
                headers={
                    "authorization": f"bearer {self._get_jwt()}",
                    "apns-topic": self.topic,
                    "apns-push-type": "alert",
                    "apns-priority": "10",
                },
            )
        except Exception as thrown:  # transport-level: log-and-continue
            logger.warning("APNs send failed (transport): %s", thrown)
            return PushResult(ok=False, detail=str(thrown))

        if response.status_code == 200:
            return PushResult(ok=True)
        unregistered = response.status_code == 410
        detail = f"HTTP {response.status_code}: {response.text[:200]}"
        logger.warning("APNs send failed: %s", detail)
        return PushResult(ok=False, unregistered=unregistered, detail=detail)


_sender: Optional[PushSender] = None


def get_sender() -> PushSender:
    """Resolve the configured sender (module singleton).

    Dry-run unless APNS_DRY_RUN=0 AND the key config is complete —
    misconfiguration degrades to logging, never to crashes
    (notifications are best-effort by design; plan Risks).
    """
    global _sender
    if _sender is not None:
        return _sender

    dry_run = os.environ.get("MOTODIAG_APNS_DRY_RUN", "1") != "0"
    key_path = os.environ.get("MOTODIAG_APNS_KEY_PATH", "")
    key_id = os.environ.get("MOTODIAG_APNS_KEY_ID", "")
    team_id = os.environ.get("MOTODIAG_APNS_TEAM_ID", "")
    topic = os.environ.get("MOTODIAG_APNS_TOPIC", "")

    if dry_run or not (key_path and key_id and team_id and topic):
        if not dry_run:
            logger.warning(
                "APNs config incomplete — falling back to dry-run sender",
            )
        _sender = DryRunSender()
    else:
        _sender = ApnsSender(
            key_path=key_path,
            key_id=key_id,
            team_id=team_id,
            topic=topic,
            sandbox=os.environ.get("MOTODIAG_APNS_SANDBOX", "1") != "0",
        )
    return _sender


def reset_sender_for_tests() -> None:
    global _sender
    _sender = None
