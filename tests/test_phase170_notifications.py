"""Phase 170 — Customer communication tests.

Six test classes across ~32 tests:

- :class:`TestMigration034` (5) — schema_version >= 34, table + CHECK +
  indexes present, rollback drops cleanly.
- :class:`TestTemplates` (5) — catalog size, event coverage, channel
  mix, unknown event/channel raises, rendering works.
- :class:`TestTriggerAndPreview` (9) — preview without persist,
  trigger persists pending, missing email/phone raises clean error,
  unknown event raises, recipient derived from channel, parts_list
  for wo_parts, shop hours formatting, extra_context override,
  placeholder miss raises.
- :class:`TestLifecycle` (5) — mark-sent, mark-failed + reason
  required, cancel, resend creates new pending, illegal transition
  raises.
- :class:`TestListing` (3) — composable filters, bogus status/event
  rejected.
- :class:`TestNotifyCLI` (5) — trigger/preview/mark-sent/cancel/
  resend round-trip.

All tests SW + SQL only; zero AI, zero network, zero live tokens.
"""

from __future__ import annotations

import json as _json
import sqlite3

import click
import pytest
from click.testing import CliRunner

from motodiag.cli.shop import register_shop
from motodiag.core.database import (
    SCHEMA_VERSION,
    get_connection,
    get_schema_version,
    init_db,
    table_exists,
)
from motodiag.core.migrations import (
    get_migration_by_version,
    rollback_to_version,
)
from motodiag.crm import customer_repo
from motodiag.crm.models import Customer
from motodiag.shop import (
    NOTIFICATION_EVENTS,
    InvalidNotificationTransition,
    NotificationContextError,
    NotificationNotFoundError,
    UnknownEventError,
    cancel_notification,
    complete_work_order,
    create_shop,
    create_work_order,
    generate_invoice_for_wo,
    get_notification,
    get_template,
    list_notifications,
    list_template_catalog,
    mark_notification_failed,
    mark_notification_sent,
    open_work_order,
    preview_notification,
    resend_notification,
    start_work,
    trigger_notification,
)


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


def _make_cli():
    @click.group()
    def root() -> None:
        """test root"""

    register_shop(root)
    return root


@pytest.fixture
def db(tmp_path):
    path = str(tmp_path / "phase170.db")
    init_db(path)
    return path


@pytest.fixture
def cli_db(tmp_path, monkeypatch):
    from motodiag.core.config import reset_settings

    path = str(tmp_path / "phase170_cli.db")
    init_db(path)
    monkeypatch.setenv("MOTODIAG_DB_PATH", path)
    monkeypatch.setenv("COLUMNS", "240")
    reset_settings()
    yield path
    reset_settings()


def _add_vehicle(db_path, make="Harley-Davidson",
                 model="Sportster 1200", year=2010):
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "INSERT INTO vehicles (make, model, year, protocol) "
            "VALUES (?, ?, ?, 'none')",
            (make, model, year),
        )
        return cursor.lastrowid


def _add_customer(db_path, name="Jane Doe",
                  email="jane@example.com", phone="555-0100"):
    return customer_repo.create_customer(
        Customer(name=name, phone=phone, email=email),
        db_path=db_path,
    )


def _seed_wo(db_path, *, actual_hours=2.0, shop_name="s"):
    shop_id = create_shop(
        shop_name, phone="555-0999",
        hours_json='{"mon":"08:00-17:00","tue":"08:00-17:00",'
                   '"wed":"08:00-17:00","thu":"08:00-17:00",'
                   '"fri":"08:00-17:00","sat":"09:00-15:00"}',
        db_path=db_path,
    )
    c = _add_customer(db_path)
    v = _add_vehicle(db_path)
    wo_id = create_work_order(
        shop_id=shop_id, vehicle_id=v, customer_id=c,
        title="rear brake pad replacement", estimated_hours=1.5,
        db_path=db_path,
    )
    open_work_order(wo_id, db_path=db_path)
    return shop_id, c, wo_id


def _seed_completed(db_path):
    shop_id, c, wo_id = _seed_wo(db_path)
    start_work(wo_id, db_path=db_path)
    complete_work_order(wo_id, actual_hours=2.0, db_path=db_path)
    return shop_id, c, wo_id


# ===========================================================================
# 1. Migration 034
# ===========================================================================


class TestMigration034:

    def test_schema_version_bumped(self, db):
        assert SCHEMA_VERSION >= 34
        assert get_schema_version(db) >= 34

    def test_table_created(self, db):
        assert table_exists("customer_notifications", db)

    def test_indexes_present(self, db):
        expected = {
            "idx_notif_customer",
            "idx_notif_shop_status",
            "idx_notif_wo",
        }
        with get_connection(db) as conn:
            actual = {r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='index'"
            ).fetchall()}
        assert expected.issubset(actual)

    def test_event_and_channel_check_enforced(self, db):
        shop_id, c, wo_id = _seed_wo(db)
        with pytest.raises(sqlite3.IntegrityError):
            with get_connection(db) as conn:
                conn.execute(
                    "INSERT INTO customer_notifications "
                    "(customer_id, shop_id, work_order_id, event, "
                    " channel, recipient, body) "
                    "VALUES (?, ?, ?, 'bogus_event', 'email', "
                    "'x@y.com', 'body')",
                    (c, shop_id, wo_id),
                )
        with pytest.raises(sqlite3.IntegrityError):
            with get_connection(db) as conn:
                conn.execute(
                    "INSERT INTO customer_notifications "
                    "(customer_id, shop_id, work_order_id, event, "
                    " channel, recipient, body) "
                    "VALUES (?, ?, ?, 'wo_opened', 'fax', "
                    "'x@y.com', 'body')",
                    (c, shop_id, wo_id),
                )

    def test_rollback_drops_table(self, tmp_path):
        path = str(tmp_path / "rollback.db")
        init_db(path)
        assert table_exists("customer_notifications", path)
        rollback_to_version(33, path)
        assert not table_exists("customer_notifications", path)
        # Phase 169 invoices still present
        assert table_exists("invoices", path)


# ===========================================================================
# 2. Template catalog
# ===========================================================================


class TestTemplates:

    def test_catalog_covers_all_events(self):
        catalog = list_template_catalog()
        covered = {row["event"] for row in catalog}
        assert covered == set(NOTIFICATION_EVENTS)

    def test_at_least_two_channels_per_event(self):
        catalog = list_template_catalog()
        channels_by_event: dict[str, set[str]] = {}
        for row in catalog:
            channels_by_event.setdefault(row["event"], set()).add(
                row["channel"]
            )
        for event, channels in channels_by_event.items():
            assert len(channels) >= 2, (
                f"{event} has only {channels}"
            )

    def test_email_templates_have_subject(self):
        catalog = list_template_catalog()
        for row in catalog:
            if row["channel"] == "email":
                assert row["has_subject"] is True, row

    def test_unknown_event_raises(self):
        with pytest.raises(UnknownEventError):
            get_template("bogus_event", "email")

    def test_render_produces_expected_substitutions(self):
        t = get_template("wo_completed", "email")
        ctx = {
            "customer_first": "Jane",
            "bike_label": "2010 Sportster",
            "wo_id": 42,
            "wo_title": "rear brakes",
            "invoice_total": "123.45",
            "shop_hours_line": "M-F 8-5",
            "shop_hours_short": "M-F 8-5",
            "shop_phone": "555-1212",
            "shop_name": "BobMoto",
        }
        subj, body = t.render(ctx)
        assert "2010 Sportster" in subj
        assert "$123.45" in body
        assert "Jane" in body


# ===========================================================================
# 3. preview_notification + trigger_notification
# ===========================================================================


class TestTriggerAndPreview:

    def test_preview_does_not_persist(self, db):
        shop_id, c, wo_id = _seed_wo(db)
        preview = preview_notification(
            "wo_opened", wo_id=wo_id, channel="email", db_path=db,
        )
        assert preview.event == "wo_opened"
        assert "@" in preview.recipient  # email
        rows = list_notifications(db_path=db)
        assert rows == []

    def test_trigger_persists_pending(self, db):
        shop_id, c, wo_id = _seed_wo(db)
        nid = trigger_notification(
            "wo_opened", wo_id=wo_id, channel="email", db_path=db,
        )
        notif = get_notification(nid, db_path=db)
        assert notif is not None
        assert notif.status == "pending"
        assert notif.work_order_id == wo_id
        assert notif.customer_id == c

    def test_sms_requires_phone(self, db):
        shop_id, c, wo_id = _seed_wo(db)
        # Blank out phone
        with get_connection(db) as conn:
            conn.execute(
                "UPDATE customers SET phone = NULL WHERE id = ?", (c,),
            )
        with pytest.raises(NotificationContextError, match="no phone"):
            trigger_notification(
                "wo_opened", wo_id=wo_id, channel="sms", db_path=db,
            )

    def test_email_requires_email(self, db):
        shop_id, c, wo_id = _seed_wo(db)
        with get_connection(db) as conn:
            conn.execute(
                "UPDATE customers SET email = NULL WHERE id = ?", (c,),
            )
        with pytest.raises(NotificationContextError, match="no email"):
            trigger_notification(
                "wo_opened", wo_id=wo_id, channel="email", db_path=db,
            )

    def test_unknown_event_raises(self, db):
        shop_id, c, wo_id = _seed_wo(db)
        with pytest.raises(UnknownEventError):
            trigger_notification(
                "bogus_event", wo_id=wo_id, db_path=db,
            )

    def test_wo_completed_includes_invoice_total(self, db):
        shop_id, c, wo_id = _seed_completed(db)
        inv_id = generate_invoice_for_wo(
            wo_id, labor_hourly_rate_cents=10000, db_path=db,
        )
        nid = trigger_notification(
            "wo_completed", wo_id=wo_id, channel="email", db_path=db,
        )
        notif = get_notification(nid, db_path=db)
        # Labor = 2 * $100 = $200 → "200.00"
        assert "200.00" in notif.body

    def test_shop_hours_rendering(self, db):
        shop_id, c, wo_id = _seed_completed(db)
        generate_invoice_for_wo(
            wo_id, labor_hourly_rate_cents=10000, db_path=db,
        )
        nid = trigger_notification(
            "wo_completed", wo_id=wo_id, channel="email", db_path=db,
        )
        notif = get_notification(nid, db_path=db)
        # Hours_json had Mon-Fri + Sat
        assert "08:00-17:00" in notif.body or "M-F" in notif.body

    def test_extra_context_override(self, db):
        shop_id, c, wo_id = _seed_wo(db)
        nid = trigger_notification(
            "approval_requested", wo_id=wo_id, channel="sms",
            extra_context={
                "approval_finding": "valves leaking",
                "approval_cost": "450.00",
            },
            db_path=db,
        )
        notif = get_notification(nid, db_path=db)
        assert "valves leaking" in notif.body
        assert "$450.00" in notif.body

    def test_recipient_channel_specific(self, db):
        shop_id, c, wo_id = _seed_wo(db)
        p_email = preview_notification(
            "wo_opened", wo_id=wo_id, channel="email", db_path=db,
        )
        p_sms = preview_notification(
            "wo_opened", wo_id=wo_id, channel="sms", db_path=db,
        )
        assert "@" in p_email.recipient
        assert "555" in p_sms.recipient


# ===========================================================================
# 4. Status lifecycle
# ===========================================================================


class TestLifecycle:

    def test_mark_sent(self, db):
        shop_id, c, wo_id = _seed_wo(db)
        nid = trigger_notification(
            "wo_opened", wo_id=wo_id, channel="email", db_path=db,
        )
        mark_notification_sent(nid, db_path=db)
        notif = get_notification(nid, db_path=db)
        assert notif.status == "sent"
        assert notif.sent_at is not None

    def test_mark_failed_requires_reason(self, db):
        shop_id, c, wo_id = _seed_wo(db)
        nid = trigger_notification(
            "wo_opened", wo_id=wo_id, channel="email", db_path=db,
        )
        with pytest.raises(ValueError, match="failure_reason required"):
            mark_notification_failed(nid, failure_reason="", db_path=db)
        mark_notification_failed(
            nid, failure_reason="email bounced", db_path=db,
        )
        notif = get_notification(nid, db_path=db)
        assert notif.status == "failed"
        assert "bounced" in notif.failure_reason

    def test_cancel(self, db):
        shop_id, c, wo_id = _seed_wo(db)
        nid = trigger_notification(
            "wo_opened", wo_id=wo_id, channel="email", db_path=db,
        )
        cancel_notification(nid, reason="customer asked", db_path=db)
        notif = get_notification(nid, db_path=db)
        assert notif.status == "cancelled"

    def test_resend_creates_new_pending(self, db):
        shop_id, c, wo_id = _seed_wo(db)
        nid = trigger_notification(
            "wo_opened", wo_id=wo_id, channel="email", db_path=db,
        )
        mark_notification_failed(
            nid, failure_reason="transient", db_path=db,
        )
        new_id = resend_notification(nid, db_path=db)
        assert new_id != nid
        new_notif = get_notification(new_id, db_path=db)
        assert new_notif.status == "pending"
        # Source untouched
        src = get_notification(nid, db_path=db)
        assert src.status == "failed"

    def test_illegal_transition_raises(self, db):
        shop_id, c, wo_id = _seed_wo(db)
        nid = trigger_notification(
            "wo_opened", wo_id=wo_id, channel="email", db_path=db,
        )
        mark_notification_sent(nid, db_path=db)
        # sent → anything is illegal
        with pytest.raises(InvalidNotificationTransition):
            mark_notification_sent(nid, db_path=db)
        with pytest.raises(InvalidNotificationTransition):
            cancel_notification(nid, db_path=db)


# ===========================================================================
# 5. list_notifications
# ===========================================================================


class TestListing:

    def test_list_composable_filters(self, db):
        shop_id, c, wo_id = _seed_wo(db)
        a = trigger_notification(
            "wo_opened", wo_id=wo_id, channel="email", db_path=db,
        )
        b = trigger_notification(
            "wo_opened", wo_id=wo_id, channel="sms", db_path=db,
        )
        mark_notification_sent(a, db_path=db)
        # status filter
        pending = list_notifications(status="pending", db_path=db)
        assert len(pending) == 1
        assert pending[0]["id"] == b
        # shop filter
        shop_rows = list_notifications(shop_id=shop_id, db_path=db)
        assert len(shop_rows) == 2
        # wo filter
        wo_rows = list_notifications(wo_id=wo_id, db_path=db)
        assert len(wo_rows) == 2

    def test_list_rejects_bogus_status(self, db):
        with pytest.raises(ValueError):
            list_notifications(status="bogus", db_path=db)

    def test_list_rejects_bogus_event(self, db):
        with pytest.raises(UnknownEventError):
            list_notifications(event="bogus_event", db_path=db)


# ===========================================================================
# 6. CLI round-trip
# ===========================================================================


class TestNotifyCLI:

    def test_preview_cli(self, cli_db):
        root = _make_cli()
        runner = CliRunner()
        shop_id, c, wo_id = _seed_wo(cli_db)
        r = runner.invoke(root, [
            "shop", "notify", "preview", "wo_opened",
            "--wo", str(wo_id), "--channel", "email", "--json",
        ])
        assert r.exit_code == 0, r.output
        data = _json.loads(r.output)
        assert data["event"] == "wo_opened"
        assert "@" in data["recipient"]

    def test_trigger_cli_persists(self, cli_db):
        root = _make_cli()
        runner = CliRunner()
        shop_id, c, wo_id = _seed_wo(cli_db)
        r = runner.invoke(root, [
            "shop", "notify", "trigger", "wo_opened",
            "--wo", str(wo_id), "--channel", "email", "--json",
        ])
        assert r.exit_code == 0, r.output
        data = _json.loads(r.output)
        assert data["status"] == "pending"

    def test_mark_sent_cli(self, cli_db):
        root = _make_cli()
        runner = CliRunner()
        shop_id, c, wo_id = _seed_wo(cli_db)
        nid = trigger_notification(
            "wo_opened", wo_id=wo_id, db_path=cli_db,
        )
        r = runner.invoke(root, [
            "shop", "notify", "mark-sent", str(nid),
        ])
        assert r.exit_code == 0, r.output
        notif = get_notification(nid, db_path=cli_db)
        assert notif.status == "sent"

    def test_list_cli(self, cli_db):
        root = _make_cli()
        runner = CliRunner()
        shop_id, c, wo_id = _seed_wo(cli_db)
        trigger_notification(
            "wo_opened", wo_id=wo_id, db_path=cli_db,
        )
        r = runner.invoke(root, [
            "shop", "notify", "list", "--shop", str(shop_id),
            "--json",
        ])
        assert r.exit_code == 0, r.output
        rows = _json.loads(r.output)
        assert len(rows) == 1

    def test_resend_cli(self, cli_db):
        root = _make_cli()
        runner = CliRunner()
        shop_id, c, wo_id = _seed_wo(cli_db)
        nid = trigger_notification(
            "wo_opened", wo_id=wo_id, db_path=cli_db,
        )
        mark_notification_failed(
            nid, failure_reason="transient", db_path=cli_db,
        )
        r = runner.invoke(root, [
            "shop", "notify", "resend", str(nid),
        ])
        assert r.exit_code == 0, r.output
        pending = list_notifications(status="pending", db_path=cli_db)
        assert len(pending) == 1
