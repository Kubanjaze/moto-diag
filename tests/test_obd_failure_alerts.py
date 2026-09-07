"""Field telemetry for OBD connection failures.

Built instead of buying a BLE adapter (F56 re-scope): the BLE transport
ships unverified against real hardware, and rather than exercise a path
no user can currently reach, the first real failure is made to reach the
maintainer with enough context to reproduce it.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from motodiag.api.app import create_app
from motodiag.auth.api_key_repo import create_api_key
from motodiag.core.database import get_connection, init_db
from motodiag.obd_reports import (
    ALERT_SUPPRESSION_MINUTES,
    list_failures,
    mark_notified,
    record_failure,
    should_alert,
)


@pytest.fixture
def db(tmp_path, monkeypatch):
    from motodiag.core.config import reset_settings
    path = str(tmp_path / "obd.db")
    init_db(path)
    monkeypatch.setenv("MOTODIAG_DB_PATH", path)
    for tier in ("anonymous", "individual", "shop", "company"):
        monkeypatch.setenv(
            f"MOTODIAG_RATE_LIMIT_{tier.upper()}_PER_MINUTE", "9999",
        )
    reset_settings()
    yield path
    reset_settings()


def _user(db_path, name="mechanic"):
    with get_connection(db_path) as conn:
        return conn.execute(
            "INSERT INTO users (username, email, tier, is_active) "
            "VALUES (?, ?, 'individual', 1)",
            (name, f"{name}@ex.com"),
        ).lastrowid


class TestReporting:
    def test_requires_auth(self, db):
        client = TestClient(
            create_app(db_path_override=db), raise_server_exceptions=False,
        )
        r = client.post(
            "/v1/diagnostics/obd-failure",
            json={"error_kind": "connect_failed"},
        )
        assert r.status_code == 401

    def test_records_a_failure_with_its_context(self, db):
        uid = _user(db)
        _, key = create_api_key(uid, db_path=db)
        client = TestClient(
            create_app(db_path_override=db), raise_server_exceptions=False,
        )
        r = client.post(
            "/v1/diagnostics/obd-failure",
            headers={"X-API-Key": key},
            json={
                "error_kind": "handshake_failed",
                "transport": "ble",
                "device_id": "AA:BB:CC",
                "message": "no response to ATZ",
                "app_version": "0.5.0",
                "platform": "ios",
                "os_version": "26.4",
            },
        )
        assert r.status_code == 201, r.text
        assert r.json()["recorded"] is True

        rows = list_failures(db_path=db)
        assert len(rows) == 1
        row = rows[0]
        # The whole point is reproducing it later, so the context must
        # survive: which transport, which dongle, which build.
        assert row["error_kind"] == "handshake_failed"
        assert row["transport"] == "ble"
        assert row["device_id"] == "AA:BB:CC"
        assert row["app_version"] == "0.5.0"

    def test_rejects_an_unknown_error_kind(self, db):
        """Literal, not str — the F37 enum-drift lesson. A client typo
        must be a 422, not a silent row nobody can query."""
        uid = _user(db)
        _, key = create_api_key(uid, db_path=db)
        client = TestClient(
            create_app(db_path_override=db), raise_server_exceptions=False,
        )
        r = client.post(
            "/v1/diagnostics/obd-failure",
            headers={"X-API-Key": key},
            json={"error_kind": "totally_made_up"},
        )
        assert r.status_code == 422

    @pytest.mark.parametrize("kind", [
        "ble_powered_off", "ble_unauthorized", "ble_unsupported",
        "device_not_found", "connect_failed", "handshake_failed",
        "disconnected_unexpectedly",
    ])
    def test_accepts_every_kind_the_mobile_union_defines(self, db, kind):
        """Pins the contract against src/obd/obdErrors.ts. A kind the
        app can produce but the backend rejects would drop exactly the
        report we built this for."""
        uid = _user(db)
        _, key = create_api_key(uid, db_path=db)
        client = TestClient(
            create_app(db_path_override=db), raise_server_exceptions=False,
        )
        r = client.post(
            "/v1/diagnostics/obd-failure",
            headers={"X-API-Key": key},
            json={"error_kind": kind, "transport": "ble"},
        )
        assert r.status_code == 201, f"{kind} rejected: {r.text}"


class TestAlertSuppression:
    """A dongle that will not connect gets retried, not tried once.
    Twelve identical pushes would get the alerts muted, which would hide
    the next real signal — so suppression is the feature, not a nicety."""

    def test_first_failure_alerts(self, db):
        uid = _user(db)
        record_failure(uid, "connect_failed", "ble", db_path=db)
        assert should_alert("connect_failed", "ble", db_path=db) is True

    def test_repeat_within_the_window_is_suppressed(self, db):
        uid = _user(db)
        rid = record_failure(uid, "connect_failed", "ble", db_path=db)
        mark_notified(rid, db_path=db)
        assert should_alert("connect_failed", "ble", db_path=db) is False

    def test_a_different_kind_still_alerts(self, db):
        uid = _user(db)
        rid = record_failure(uid, "connect_failed", "ble", db_path=db)
        mark_notified(rid, db_path=db)
        # A NEW failure mode is a new story, even on the same transport.
        assert should_alert("handshake_failed", "ble", db_path=db) is True

    def test_the_window_expires(self, db):
        uid = _user(db)
        rid = record_failure(uid, "connect_failed", "ble", db_path=db)
        past = datetime.now(timezone.utc) - timedelta(
            minutes=ALERT_SUPPRESSION_MINUTES + 5,
        )
        mark_notified(rid, now=past, db_path=db)
        assert should_alert("connect_failed", "ble", db_path=db) is True


class TestAlertDelivery:
    def test_disabled_by_default(self, db, monkeypatch):
        """admin_user_id defaults to 0. Anyone running their own
        instance should not silently push to user 0."""
        from motodiag.push.events import notify_obd_failure
        uid = _user(db)
        rid = record_failure(uid, "connect_failed", "ble", db_path=db)
        assert notify_obd_failure(
            rid, "connect_failed", "ble", None, None, db_path=db,
        ) is False

    def test_alerts_the_configured_maintainer(self, db, monkeypatch):
        from motodiag.core.config import reset_settings
        from motodiag.push import events as push_events
        from motodiag.push.registry import register_token

        admin = _user(db, "maintainer")
        register_token(admin, "t" * 64, db_path=db)
        monkeypatch.setenv("MOTODIAG_ADMIN_USER_ID", str(admin))
        reset_settings()

        sent = []
        monkeypatch.setattr(
            push_events, "_send_to_user",
            lambda uid, title, body, thread_id=None, db_path=None: (
                sent.append((uid, title, body)) or 1
            ),
        )
        rid = record_failure(
            _user(db, "mech2"), "handshake_failed", "ble",
            device_id="AA:BB", db_path=db,
        )
        assert push_events.notify_obd_failure(
            rid, "handshake_failed", "ble", "AA:BB", "no ATZ reply",
            db_path=db,
        ) is True
        assert sent and sent[0][0] == admin
        assert "ble" in sent[0][1]
        assert "handshake_failed" in sent[0][2]

    def test_telemetry_failure_never_breaks_the_caller(self, db, monkeypatch):
        """Best-effort, like every other push path: an alert problem must
        not propagate into the endpoint that recorded the failure."""
        from motodiag.core.config import reset_settings
        from motodiag.push import events as push_events

        admin = _user(db, "maintainer2")
        monkeypatch.setenv("MOTODIAG_ADMIN_USER_ID", str(admin))
        reset_settings()

        def boom(*a, **k):
            raise RuntimeError("APNs exploded")

        monkeypatch.setattr(push_events, "_send_to_user", boom)
        rid = record_failure(_user(db, "mech3"), "connect_failed", "ble", db_path=db)
        assert push_events.notify_obd_failure(
            rid, "connect_failed", "ble", None, None, db_path=db,
        ) is False


class TestTransportEnumMatchesTheApp:
    """The transport values must mirror the mobile `ObdTransport` union
    exactly (src/obd/ObdConnection.ts). This shipped briefly as
    "classic" against the app's "classic-bt" — F37 enum-contract drift,
    caught only by the mobile typecheck. A mismatch here silently drops
    every report from that transport."""

    @pytest.mark.parametrize("transport", ["ble", "classic-bt", "wifi"])
    def test_accepts_every_transport_the_app_can_send(self, db, transport):
        uid = _user(db, f"mech_{transport.replace('-', '_')}")
        _, key = create_api_key(uid, db_path=db)
        client = TestClient(
            create_app(db_path_override=db), raise_server_exceptions=False,
        )
        r = client.post(
            "/v1/diagnostics/obd-failure",
            headers={"X-API-Key": key},
            json={"error_kind": "connect_failed", "transport": transport},
        )
        assert r.status_code == 201, f"{transport} rejected: {r.text}"
