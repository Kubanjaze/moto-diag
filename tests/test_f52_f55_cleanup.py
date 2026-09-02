"""F52 + F55 pre-Gate-10 cleanup.

F55 — sessions can name their customer: migration 046 adds
``diagnostic_sessions.customer_id``, backfilled from the vehicle while
skipping the Phase 006 "Unassigned" sentinel, and the session report
document carries a ``prepared_for`` line that the customer-facing share
page renders.

F52 (backend half) — a successful push now logs. Phase 199's smoke had
to prove delivery by the ABSENCE of warnings, which is not evidence.
"""

from __future__ import annotations

import logging

import pytest
from fastapi.testclient import TestClient

from motodiag.api.app import create_app
from motodiag.auth.api_key_repo import create_api_key
from motodiag.core.database import SCHEMA_VERSION, get_connection, init_db
from motodiag.core.migrations import rollback_to_version
from motodiag.reporting.builders import (
    build_session_report_doc,
    resolve_session_customer_name,
)


@pytest.fixture
def db(tmp_path, monkeypatch):
    from motodiag.core.config import reset_settings
    path = str(tmp_path / "cleanup.db")
    init_db(path)
    monkeypatch.setenv("MOTODIAG_DB_PATH", path)
    for tier in ("anonymous", "individual", "shop", "company"):
        monkeypatch.setenv(
            f"MOTODIAG_RATE_LIMIT_{tier.upper()}_PER_MINUTE", "9999",
        )
    reset_settings()
    yield path
    reset_settings()


def _user(db_path, username="cleanup_user"):
    with get_connection(db_path) as conn:
        return conn.execute(
            "INSERT INTO users (username, email, tier, is_active) "
            "VALUES (?, ?, 'individual', 1)",
            (username, f"{username}@ex.com"),
        ).lastrowid


def _customer(db_path, name):
    with get_connection(db_path) as conn:
        return conn.execute(
            "INSERT INTO customers (name, is_active) VALUES (?, 1)",
            (name,),
        ).lastrowid


def _vehicle(db_path, customer_id=None):
    with get_connection(db_path) as conn:
        return conn.execute(
            "INSERT INTO vehicles (make, model, year, protocol, customer_id) "
            "VALUES ('Honda', 'CB500', 2020, 'none', ?)",
            (customer_id,),
        ).lastrowid


def _session(db_path, user_id, vehicle_id=None, customer_id=None):
    with get_connection(db_path) as conn:
        return conn.execute(
            "INSERT INTO diagnostic_sessions "
            "(vehicle_make, vehicle_model, vehicle_year, status, user_id, "
            " vehicle_id, customer_id) "
            "VALUES ('Honda', 'CB500', 2020, 'open', ?, ?, ?)",
            (user_id, vehicle_id, customer_id),
        ).lastrowid


class TestMigration046:
    def test_schema_version_and_column(self, db):
        assert SCHEMA_VERSION >= 46
        with get_connection(db) as conn:
            cols = {r[1] for r in conn.execute(
                "PRAGMA table_info(diagnostic_sessions)",
            )}
        assert "customer_id" in cols

    def test_backfill_takes_the_vehicle_customer_but_skips_the_sentinel(
        self, db,
    ):
        uid = _user(db)
        real = _customer(db, "Dana Reyes")
        with_real = _vehicle(db, customer_id=real)
        with_sentinel = _vehicle(db, customer_id=1)
        without = _vehicle(db, customer_id=None)
        s_real = _session(db, uid, vehicle_id=with_real)
        s_sentinel = _session(db, uid, vehicle_id=with_sentinel)
        s_none = _session(db, uid, vehicle_id=without)

        # Re-run migration 046 over rows that already exist, which is
        # exactly what it did to production history.
        with get_connection(db) as conn:
            conn.execute("UPDATE diagnostic_sessions SET customer_id = NULL")
        rollback_to_version(45, db)
        init_db(db)

        with get_connection(db) as conn:
            got = dict(conn.execute(
                "SELECT id, customer_id FROM diagnostic_sessions",
            ).fetchall())
        assert got[s_real] == real
        # The id-1 "Unassigned" placeholder must NOT be claimed as a
        # real customer — that is the whole point of the skip.
        assert got[s_sentinel] is None
        assert got[s_none] is None


class TestCustomerResolver:
    def test_prefers_the_sessions_own_customer(self, db):
        uid = _user(db)
        direct = _customer(db, "Direct Owner")
        other = _customer(db, "Vehicle Owner")
        vid = _vehicle(db, customer_id=other)
        sid = _session(db, uid, vehicle_id=vid, customer_id=direct)
        with get_connection(db) as conn:
            row = dict(conn.execute(
                "SELECT * FROM diagnostic_sessions WHERE id = ?", (sid,),
            ).fetchone())
        assert resolve_session_customer_name(row, db_path=db) == "Direct Owner"

    def test_falls_back_to_the_vehicle_owner(self, db):
        uid = _user(db)
        owner = _customer(db, "Vehicle Owner")
        vid = _vehicle(db, customer_id=owner)
        sid = _session(db, uid, vehicle_id=vid)
        with get_connection(db) as conn:
            row = dict(conn.execute(
                "SELECT * FROM diagnostic_sessions WHERE id = ?", (sid,),
            ).fetchone())
        assert resolve_session_customer_name(row, db_path=db) == "Vehicle Owner"

    @pytest.mark.parametrize("customer_id", [1, None])
    def test_sentinel_and_missing_both_resolve_to_none(self, db, customer_id):
        uid = _user(db)
        vid = _vehicle(db, customer_id=customer_id)
        sid = _session(db, uid, vehicle_id=vid)
        with get_connection(db) as conn:
            row = dict(conn.execute(
                "SELECT * FROM diagnostic_sessions WHERE id = ?", (sid,),
            ).fetchone())
        assert resolve_session_customer_name(row, db_path=db) is None

    def test_session_with_no_vehicle_resolves_to_none(self, db):
        uid = _user(db)
        sid = _session(db, uid)
        with get_connection(db) as conn:
            row = dict(conn.execute(
                "SELECT * FROM diagnostic_sessions WHERE id = ?", (sid,),
            ).fetchone())
        assert resolve_session_customer_name(row, db_path=db) is None


class TestPreparedForReachesTheCustomerPage:
    def test_document_carries_prepared_for(self, db):
        uid = _user(db)
        cust = _customer(db, "Dana Reyes")
        vid = _vehicle(db, customer_id=cust)
        sid = _session(db, uid, vehicle_id=vid)
        doc = build_session_report_doc(sid, uid, db_path=db)
        assert doc["prepared_for"] == "Dana Reyes"

    def test_key_is_present_as_none_when_unknown(self, db):
        uid = _user(db)
        sid = _session(db, uid)
        doc = build_session_report_doc(sid, uid, db_path=db)
        # Explicit None, not omitted — the `subtitle` convention.
        assert "prepared_for" in doc and doc["prepared_for"] is None

    def test_share_page_names_the_customer(self, db):
        uid = _user(db)
        _, key = create_api_key(uid, db_path=db)
        cust = _customer(db, "Dana Reyes")
        vid = _vehicle(db, customer_id=cust)
        sid = _session(db, uid, vehicle_id=vid)
        client = TestClient(
            create_app(db_path_override=db), raise_server_exceptions=False,
        )
        minted = client.post(
            f"/v1/reports/session/{sid}/share", json={},
            headers={"X-API-Key": key},
        )
        assert minted.status_code == 201, minted.text
        page = client.get(f"/v1/share/{minted.json()['token']}").text
        assert "Prepared for Dana Reyes" in page

    def test_customer_name_is_escaped_in_the_page(self, db):
        uid = _user(db)
        _, key = create_api_key(uid, db_path=db)
        cust = _customer(db, "<script>alert(1)</script>")
        vid = _vehicle(db, customer_id=cust)
        sid = _session(db, uid, vehicle_id=vid)
        client = TestClient(
            create_app(db_path_override=db), raise_server_exceptions=False,
        )
        token = client.post(
            f"/v1/reports/session/{sid}/share", json={},
            headers={"X-API-Key": key},
        ).json()["token"]
        page = client.get(f"/v1/share/{token}").text
        assert "<script>alert(1)</script>" not in page
        assert "&lt;script&gt;" in page


class TestPushSuccessIsLogged:
    def test_successful_send_logs_at_info(self, db, caplog):
        from motodiag.push import events as push_events
        from motodiag.push.registry import register_token
        from motodiag.push.sender import DryRunSender

        uid = _user(db)
        register_token(uid, "t" * 64, db_path=db)
        sender = DryRunSender()
        with caplog.at_level(logging.INFO, logger="motodiag.push.events"):
            push_events._send_to_user(
                uid, "Work order #1 was opened", "body", db_path=db,
            )
        assert any(
            "push sent to user" in record.message for record in caplog.records
        ), "a successful push must leave a trace, not just failures"
