"""Phase 208 — the CLI must write rows the API can read.

Found by documenting the shop workflow rather than describing it.
Writing `docs/guide/shop-workflow.md` meant running the workflow, and
running it surfaced this: Phase 207 gave `customers` a `shop_id` and
taught the API to scope on it, but `motodiag shop customer add` kept
inserting NULL. The API serves a NULL-`shop_id` row to no shop, so
every customer added from the CLI was invisible to the mobile app and
to the API — silently, with both halves passing their own tests.

Phase 207's tests covered the API path only. That is the integration
gap in its usual shape: each side is correct in isolation and the seam
between them is where the product breaks.

These tests hold the seam. They assert the CLI and the API agree about
what a customer belongs to, which no single-sided test can.
"""

from __future__ import annotations

import pytest
from click.testing import CliRunner
from fastapi.testclient import TestClient

from motodiag.api.app import create_app
from motodiag.auth.api_key_repo import create_api_key
from motodiag.cli.main import cli
from motodiag.core.database import get_connection, init_db


@pytest.fixture
def shop_env(tmp_path, monkeypatch):
    """One registered shop, one shop-tier member, one API key."""
    from motodiag.core.config import reset_settings

    path = str(tmp_path / "parity.db")
    init_db(path)
    monkeypatch.setenv("MOTODIAG_DB_PATH", path)
    for tier in ("anonymous", "individual", "shop", "company"):
        monkeypatch.setenv(
            f"MOTODIAG_RATE_LIMIT_{tier.upper()}_PER_MINUTE", "9999",
        )
    reset_settings()

    with get_connection(path) as conn:
        uid = conn.execute(
            "INSERT INTO users (username, email, tier, is_active) "
            "VALUES ('owner', 'owner@ex.com', 'shop', 1)",
        ).lastrowid
        conn.execute(
            "INSERT INTO subscriptions (user_id, tier, status, "
            " current_period_end) VALUES (?, 'shop', 'active', "
            " datetime('now', '+30 days'))", (uid,),
        )
        shop_id = conn.execute(
            "INSERT INTO shops (name, owner_user_id) VALUES ('Solo', ?)",
            (uid,),
        ).lastrowid
        conn.execute(
            "INSERT INTO shop_members (user_id, shop_id, role, is_active) "
            "VALUES (?, ?, 'owner', 1)", (uid, shop_id),
        )
    _, key = create_api_key(uid, db_path=path)
    client = TestClient(
        create_app(db_path_override=path), raise_server_exceptions=False,
    )
    yield client, key, shop_id, path
    reset_settings()


def _api_customer_names(client, key, shop_id) -> set[str]:
    r = client.get(
        f"/v1/shop/{shop_id}/customers", headers={"X-API-Key": key},
    )
    assert r.status_code == 200, r.text
    return {row["name"] for row in r.json()["items"]}


class TestCliCreatedCustomersAreVisibleToTheApi:
    def test_a_cli_customer_appears_in_the_api_list(self, shop_env):
        client, key, shop_id, _ = shop_env
        result = CliRunner().invoke(
            cli, ["shop", "customer", "add", "--name", "Marcus Webb"],
        )
        assert result.exit_code == 0, result.output
        assert "Marcus Webb" in _api_customer_names(client, key, shop_id), (
            "the CLI wrote a customer the API cannot see"
        )

    def test_the_row_carries_the_shop_not_null(self, shop_env):
        _client, _key, shop_id, path = shop_env
        result = CliRunner().invoke(
            cli, ["shop", "customer", "add", "--name", "Dana Reyes"],
        )
        assert result.exit_code == 0, result.output
        with get_connection(path) as conn:
            row = conn.execute(
                "SELECT shop_id FROM customers WHERE name = 'Dana Reyes'",
            ).fetchone()
        assert row["shop_id"] == shop_id

    def test_an_explicit_shop_id_is_honoured(self, shop_env):
        _client, _key, shop_id, path = shop_env
        result = CliRunner().invoke(cli, [
            "shop", "customer", "add", "--name", "Explicit",
            "--shop-id", str(shop_id),
        ])
        assert result.exit_code == 0, result.output
        with get_connection(path) as conn:
            assert conn.execute(
                "SELECT shop_id FROM customers WHERE name = 'Explicit'",
            ).fetchone()["shop_id"] == shop_id


class TestAmbiguousShopIsRefusedRatherThanGuessed:
    """Filing a customer under the wrong business is worse than a
    command that stops and asks."""

    def test_two_shops_means_shop_id_is_required(self, shop_env):
        _client, _key, _shop_id, path = shop_env
        with get_connection(path) as conn:
            conn.execute(
                "INSERT INTO shops (name, owner_user_id) VALUES ('Second', 1)",
            )
        result = CliRunner().invoke(
            cli, ["shop", "customer", "add", "--name", "Ambiguous"],
        )
        assert result.exit_code != 0
        assert "--shop-id" in result.output
        with get_connection(path) as conn:
            assert conn.execute(
                "SELECT COUNT(*) c FROM customers WHERE name = 'Ambiguous'",
            ).fetchone()["c"] == 0, "a customer was filed despite the refusal"

    def test_two_shops_still_works_when_told_which(self, shop_env):
        _client, _key, shop_id, path = shop_env
        with get_connection(path) as conn:
            conn.execute(
                "INSERT INTO shops (name, owner_user_id) VALUES ('Second', 1)",
            )
        result = CliRunner().invoke(cli, [
            "shop", "customer", "add", "--name", "Told",
            "--shop-id", str(shop_id),
        ])
        assert result.exit_code == 0, result.output

    def test_no_shop_at_all_says_what_to_do(self, tmp_path, monkeypatch):
        from motodiag.core.config import reset_settings

        path = str(tmp_path / "empty.db")
        init_db(path)
        monkeypatch.setenv("MOTODIAG_DB_PATH", path)
        reset_settings()
        result = CliRunner().invoke(
            cli, ["shop", "customer", "add", "--name", "Nobody"],
        )
        assert result.exit_code != 0
        assert "shop profile init" in result.output
        reset_settings()


class TestCliListCanScopeTheSameWayTheApiDoes:
    def test_scoped_list_excludes_another_shops_customer(self, shop_env):
        _client, _key, shop_id, path = shop_env
        with get_connection(path) as conn:
            other = conn.execute(
                "INSERT INTO shops (name, owner_user_id) VALUES ('Other', 1)",
            ).lastrowid
            conn.execute(
                "INSERT INTO customers (name, shop_id) VALUES ('Theirs', ?)",
                (other,),
            )
            conn.execute(
                "INSERT INTO customers (name, shop_id) VALUES ('Ours', ?)",
                (shop_id,),
            )
        result = CliRunner().invoke(
            cli, ["shop", "customer", "list", "--shop-id", str(shop_id),
                  "--json"],
        )
        assert result.exit_code == 0, result.output
        assert "Ours" in result.output
        assert "Theirs" not in result.output
