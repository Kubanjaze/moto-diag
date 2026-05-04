"""Phase 191B fix-cycle-3 — `motodiag subscription set` CLI regression guard.

Architect-gate halted at re-smoke step 5 with backend POST
/v1/sessions/1/videos returning 403 (require_tier('shop') gate firing
because user 1 was on individual tier). Existing tier-upgrade paths
were:

  (a) `motodiag subscription checkout-url` — Stripe checkout, requires
       real-payment-completion round-trips, overkill for smoke
  (b) Direct SQL into the `subscriptions` table — unsafe to copy-paste
       in a runbook without the table schema in front of you
  (c) Running `motodiag subscription sync` — only syncs an existing
       Stripe-side row; doesn't create one

This commit adds `motodiag subscription set --user N --tier T` as the
smoke-runbook-friendly path. Marked dev/test only in help text; the
production path remains the Stripe checkout flow.

Tests guard:
  - The command creates an active subscription with the right tier
  - It cancels any existing active subscription before creating the new one
  - --tier validation rejects unknown values
  - --user is required
  - --days defaults to 30 and is overrideable
  - The new row's stripe_subscription_id is NULL (no Stripe round-trip)
  - Period fields populate (current_period_start, current_period_end, ends_at)
  - Status is 'active' (not 'trialing')

Phase 178/191B integration test: after `subscription set --tier shop`,
`get_active_subscription(user_id).tier == 'shop'` so downstream
`require_tier('shop')` checks pass without going through Stripe.
"""

from __future__ import annotations

from datetime import datetime, timezone

import click
import pytest
from click.testing import CliRunner

from motodiag.billing.subscription_repo import get_active_subscription
from motodiag.core.database import get_connection, init_db


@pytest.fixture
def cli_with_subscription(tmp_path, monkeypatch):
    """Click CLI with the subscription group registered + DB pointed at tmp."""
    db_path = str(tmp_path / "phase191b_subset.db")
    monkeypatch.setenv("MOTODIAG_DB_PATH", db_path)
    from motodiag.core.config import reset_settings
    reset_settings()
    init_db(db_path)

    # Ensure user 1 exists (init_db may seed a default user 1; INSERT
    # OR IGNORE handles both fresh + already-seeded cases).
    with get_connection(db_path) as conn:
        conn.execute(
            "INSERT OR IGNORE INTO users "
            "(id, username, email, tier, is_active) "
            "VALUES (1, 'kerwyn', 'k@example.com', 'individual', 1)"
        )

    from motodiag.cli.billing import register_subscription

    @click.group()
    def root() -> None:
        pass

    register_subscription(root)
    yield root, db_path
    reset_settings()


# ---------------------------------------------------------------------
# 1. Happy-path subscription creation
# ---------------------------------------------------------------------


class TestSubscriptionSetHappyPath:

    def test_creates_active_subscription_with_specified_tier(
        self, cli_with_subscription,
    ):
        root, _ = cli_with_subscription
        runner = CliRunner()
        result = runner.invoke(
            root, ["subscription", "set", "--user", "1", "--tier", "shop"],
        )
        assert result.exit_code == 0, result.output
        sub = get_active_subscription(1)
        assert sub is not None
        assert sub.tier == "shop"
        assert sub.status == "active"

    def test_individual_tier(self, cli_with_subscription):
        root, _ = cli_with_subscription
        runner = CliRunner()
        result = runner.invoke(
            root,
            ["subscription", "set", "--user", "1", "--tier", "individual"],
        )
        assert result.exit_code == 0
        assert get_active_subscription(1).tier == "individual"

    def test_company_tier(self, cli_with_subscription):
        root, _ = cli_with_subscription
        runner = CliRunner()
        result = runner.invoke(
            root, ["subscription", "set", "--user", "1", "--tier", "company"],
        )
        assert result.exit_code == 0
        assert get_active_subscription(1).tier == "company"

    def test_period_end_default_30_days(self, cli_with_subscription):
        root, db_path = cli_with_subscription
        runner = CliRunner()
        before = datetime.now(timezone.utc)
        result = runner.invoke(
            root, ["subscription", "set", "--user", "1", "--tier", "shop"],
        )
        assert result.exit_code == 0
        with get_connection(db_path) as conn:
            row = conn.execute(
                "SELECT current_period_end, ends_at FROM subscriptions "
                "WHERE user_id = 1 AND status = 'active'"
            ).fetchone()
        period_end = datetime.fromisoformat(row["current_period_end"])
        delta = (period_end - before).days
        assert 29 <= delta <= 31  # tolerance for clock skew

    def test_days_override(self, cli_with_subscription):
        root, db_path = cli_with_subscription
        runner = CliRunner()
        before = datetime.now(timezone.utc)
        result = runner.invoke(
            root,
            ["subscription", "set", "--user", "1", "--tier", "shop",
             "--days", "7"],
        )
        assert result.exit_code == 0
        with get_connection(db_path) as conn:
            row = conn.execute(
                "SELECT current_period_end FROM subscriptions "
                "WHERE user_id = 1 AND status = 'active'"
            ).fetchone()
        period_end = datetime.fromisoformat(row["current_period_end"])
        delta = (period_end - before).days
        assert 6 <= delta <= 8  # tolerance for clock skew

    def test_no_stripe_subscription_id(self, cli_with_subscription):
        """The dev-only path bypasses Stripe; the row must have
        stripe_subscription_id NULL so future cancel/sync commands
        don't try a Stripe round-trip."""
        root, db_path = cli_with_subscription
        runner = CliRunner()
        runner.invoke(
            root, ["subscription", "set", "--user", "1", "--tier", "shop"],
        )
        with get_connection(db_path) as conn:
            row = conn.execute(
                "SELECT stripe_subscription_id FROM subscriptions "
                "WHERE user_id = 1 AND status = 'active'"
            ).fetchone()
        assert row["stripe_subscription_id"] is None


# ---------------------------------------------------------------------
# 2. Replacing existing subscription
# ---------------------------------------------------------------------


class TestSubscriptionSetReplacesExisting:

    def test_cancels_existing_active_when_setting_new_tier(
        self, cli_with_subscription,
    ):
        root, db_path = cli_with_subscription
        runner = CliRunner()

        # First set: individual
        runner.invoke(
            root,
            ["subscription", "set", "--user", "1", "--tier", "individual"],
        )
        first = get_active_subscription(1)

        # Second set: shop
        runner.invoke(
            root,
            ["subscription", "set", "--user", "1", "--tier", "shop"],
        )
        second = get_active_subscription(1)

        # The second is active + shop
        assert second is not None
        assert second.tier == "shop"
        assert second.status == "active"
        # Different row id
        assert second.id != first.id

        # The first row is now canceled
        with get_connection(db_path) as conn:
            row = conn.execute(
                "SELECT status, canceled_at FROM subscriptions WHERE id = ?",
                (first.id,),
            ).fetchone()
        assert row["status"] == "canceled"
        assert row["canceled_at"] is not None

    def test_no_existing_doesnt_error(self, cli_with_subscription):
        """First-time use (no prior subscription) creates cleanly."""
        root, _ = cli_with_subscription
        runner = CliRunner()
        # Sanity: no subscription before
        assert get_active_subscription(1) is None
        result = runner.invoke(
            root, ["subscription", "set", "--user", "1", "--tier", "shop"],
        )
        assert result.exit_code == 0
        assert get_active_subscription(1).tier == "shop"


# ---------------------------------------------------------------------
# 3. Input validation
# ---------------------------------------------------------------------


class TestSubscriptionSetValidation:

    def test_invalid_tier_rejected(self, cli_with_subscription):
        root, _ = cli_with_subscription
        runner = CliRunner()
        result = runner.invoke(
            root,
            ["subscription", "set", "--user", "1", "--tier", "enterprise"],
        )
        assert result.exit_code != 0
        assert "Invalid value for '--tier'" in result.output

    def test_user_required(self, cli_with_subscription):
        root, _ = cli_with_subscription
        runner = CliRunner()
        result = runner.invoke(
            root, ["subscription", "set", "--tier", "shop"],
        )
        assert result.exit_code != 0
        assert "Missing option" in result.output


# ---------------------------------------------------------------------
# 4. Output / dev-only marker
# ---------------------------------------------------------------------


class TestSubscriptionSetOutput:

    def test_output_marks_dev_test_path(self, cli_with_subscription):
        root, _ = cli_with_subscription
        runner = CliRunner()
        result = runner.invoke(
            root, ["subscription", "set", "--user", "1", "--tier", "shop"],
        )
        assert result.exit_code == 0
        assert "DEV/TEST PATH" in result.output

    def test_output_includes_period_end(self, cli_with_subscription):
        root, _ = cli_with_subscription
        runner = CliRunner()
        result = runner.invoke(
            root, ["subscription", "set", "--user", "1", "--tier", "shop"],
        )
        assert result.exit_code == 0
        assert "period_end=" in result.output
        # Format YYYY-MM-DD; Phase 191B is in 2026.
        assert "2026-" in result.output
