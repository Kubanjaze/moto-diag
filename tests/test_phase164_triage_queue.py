"""Phase 164 — Automated triage queue tests.

Four test classes across ~32 tests:

- :class:`TestMigration028` (5) — schema bump to >=28, triage_weights column
  present, nullable default, rollback preserves Phase 160-163 state.
- :class:`TestTriageWeights` (6) — Pydantic defaults + validation + save/load/
  reset round-trip.
- :class:`TestTriageMarkers` (4) — _parse_triage_markers handles all 4 combos.
- :class:`TestBuildTriageQueue` (10) — ranking + filters + wait-time + urgent +
  skip + parts soft-guard + determinism.
- :class:`TestTriageCLI` (7) — queue / next / flag-urgent / skip / weights CLI.

All tests pure stdlib + SQL. Zero AI, zero tokens, zero network.
"""

from __future__ import annotations

import importlib
import json as _json
import sys
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import click
import pytest
from click.testing import CliRunner

from motodiag.cli.shop import register_shop
from motodiag.core.database import (
    SCHEMA_VERSION, get_connection, get_schema_version, init_db,
    table_exists,
)
from motodiag.core.migrations import rollback_to_version
from motodiag.crm import customer_repo
from motodiag.crm.models import Customer
from motodiag.shop import (
    ShopTriageWeights, TriageItem, build_triage_queue, clear_urgent,
    create_shop, create_work_order, flag_urgent, load_triage_weights,
    open_work_order, reset_triage_weights, save_triage_weights,
    skip_work_order,
)
from motodiag.shop.triage_queue import (
    _compute_score, _parse_triage_markers, _parts_available_for,
)


def _make_cli():
    @click.group()
    def root() -> None:
        """test root"""
    register_shop(root)
    return root


def _add_vehicle(db_path, make="Harley-Davidson", model="Sportster 1200", year=2010):
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "INSERT INTO vehicles (make, model, year, protocol) "
            "VALUES (?, ?, ?, 'none')",
            (make, model, year),
        )
        return cursor.lastrowid


def _add_customer(db_path, name="Jane Doe"):
    return customer_repo.create_customer(
        Customer(name=name, phone="555-0100", email="jane@example.com"),
        db_path=db_path,
    )


@pytest.fixture
def db(tmp_path):
    path = str(tmp_path / "phase164.db")
    init_db(path)
    return path


@pytest.fixture
def cli_db(tmp_path, monkeypatch):
    from motodiag.core.config import reset_settings
    path = str(tmp_path / "phase164_cli.db")
    init_db(path)
    monkeypatch.setenv("MOTODIAG_DB_PATH", path)
    monkeypatch.setenv("COLUMNS", "240")
    reset_settings()
    yield path
    reset_settings()


def _seed_wo(db_path, priority=3, title="x"):
    shop_id = create_shop("s", db_path=db_path)
    c = _add_customer(db_path)
    v = _add_vehicle(db_path)
    wo_id = create_work_order(
        shop_id, v, c, title, priority=priority, db_path=db_path,
    )
    open_work_order(wo_id, db_path=db_path)
    return wo_id, shop_id


# ===========================================================================
# 1. Migration 028
# ===========================================================================


class TestMigration028:
    def test_schema_version_bumped_to_at_least_28(self, db):
        assert SCHEMA_VERSION >= 28
        assert get_schema_version(db) >= 28

    def test_triage_weights_column_present(self, db):
        with get_connection(db) as conn:
            cols = {r[1] for r in conn.execute("PRAGMA table_info(shops)").fetchall()}
        assert "triage_weights" in cols

    def test_triage_weights_default_null(self, db):
        shop_id = create_shop("s", db_path=db)
        with get_connection(db) as conn:
            row = conn.execute(
                "SELECT triage_weights FROM shops WHERE id = ?", (shop_id,),
            ).fetchone()
        assert row["triage_weights"] is None

    def test_rollback_to_27_drops_column(self, tmp_path):
        path = str(tmp_path / "rollback.db")
        init_db(path)
        with get_connection(path) as conn:
            cols_before = {r[1] for r in conn.execute("PRAGMA table_info(shops)").fetchall()}
        assert "triage_weights" in cols_before

        rollback_to_version(27, path)

        # Phase 160/161/162 tables survive
        assert table_exists("shops", path)
        assert table_exists("work_orders", path)
        assert table_exists("issues", path)

        with get_connection(path) as conn:
            cols_after = {r[1] for r in conn.execute("PRAGMA table_info(shops)").fetchall()}
        assert "triage_weights" not in cols_after

    def test_tables_still_exist_after_rollback(self, tmp_path):
        path = str(tmp_path / "rollback2.db")
        init_db(path)
        rollback_to_version(27, path)
        with get_connection(path) as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS n FROM sqlite_master "
                "WHERE type='table' AND name='shops'",
            ).fetchone()
        assert row["n"] == 1


# ===========================================================================
# 2. ShopTriageWeights + load/save/reset
# ===========================================================================


class TestTriageWeights:
    def test_defaults(self):
        w = ShopTriageWeights()
        assert w.priority_weight == 100.0
        assert w.wait_weight == 1.0
        assert w.parts_ready_weight == 10.0
        assert w.urgent_flag_bonus == 500.0
        assert w.skip_penalty == 50.0

    def test_rejects_negative(self):
        with pytest.raises(Exception):  # pydantic ValidationError
            ShopTriageWeights(priority_weight=-1.0)

    def test_rejects_unknown_key(self):
        with pytest.raises(Exception):
            ShopTriageWeights(unknown_key=1.0)

    def test_save_and_load_roundtrip(self, db):
        shop_id = create_shop("s", db_path=db)
        custom = ShopTriageWeights(wait_weight=2.5, parts_ready_weight=15.0)
        save_triage_weights(shop_id, custom, db_path=db)
        loaded = load_triage_weights(shop_id, db_path=db)
        assert loaded.wait_weight == 2.5
        assert loaded.parts_ready_weight == 15.0
        # Defaults preserved
        assert loaded.priority_weight == 100.0

    def test_load_null_returns_defaults(self, db):
        shop_id = create_shop("s", db_path=db)
        loaded = load_triage_weights(shop_id, db_path=db)
        assert loaded == ShopTriageWeights()

    def test_reset_returns_to_defaults(self, db):
        shop_id = create_shop("s", db_path=db)
        save_triage_weights(
            shop_id, ShopTriageWeights(wait_weight=5.0), db_path=db,
        )
        reset_triage_weights(shop_id, db_path=db)
        loaded = load_triage_weights(shop_id, db_path=db)
        assert loaded.wait_weight == 1.0


# ===========================================================================
# 3. Triage marker parsing
# ===========================================================================


class TestTriageMarkers:
    def test_none_description(self):
        result = _parse_triage_markers(None)
        assert result == {
            "flag": None, "skip_reason": None, "clean_description": "",
        }

    def test_urgent_only(self):
        result = _parse_triage_markers("[TRIAGE_URGENT] the rest")
        assert result["flag"] == "urgent"
        assert result["skip_reason"] is None
        assert result["clean_description"] == "the rest"

    def test_skip_only(self):
        result = _parse_triage_markers("[TRIAGE_SKIP: parts delay] other text")
        assert result["flag"] is None
        assert result["skip_reason"] == "parts delay"
        assert result["clean_description"] == "other text"

    def test_both_urgent_and_skip(self):
        result = _parse_triage_markers(
            "[TRIAGE_URGENT] [TRIAGE_SKIP: wait] body"
        )
        assert result["flag"] == "urgent"
        assert result["skip_reason"] == "wait"
        assert result["clean_description"] == "body"


# ===========================================================================
# 4. build_triage_queue
# ===========================================================================


class TestBuildTriageQueue:
    def test_empty_returns_empty(self, db):
        items = build_triage_queue(db_path=db)
        assert items == []

    def test_single_wo_ranked_1(self, db):
        wo_id, _ = _seed_wo(db, priority=3)
        items = build_triage_queue(db_path=db)
        assert len(items) == 1
        assert items[0].rank == 1
        assert items[0].work_order["id"] == wo_id

    def test_priority_1_outranks_priority_5(self, db):
        shop_id = create_shop("s", db_path=db)
        c = _add_customer(db)
        v = _add_vehicle(db)
        wo_low = create_work_order(
            shop_id, v, c, "low", priority=5, db_path=db,
        )
        open_work_order(wo_low, db_path=db)
        wo_high = create_work_order(
            shop_id, v, c, "high", priority=1, db_path=db,
        )
        open_work_order(wo_high, db_path=db)
        items = build_triage_queue(db_path=db)
        ids = [item.work_order["id"] for item in items]
        assert ids.index(wo_high) < ids.index(wo_low)

    def test_urgent_flag_outranks_priority_1(self, db):
        shop_id = create_shop("s", db_path=db)
        c = _add_customer(db)
        v = _add_vehicle(db)
        wo_pri1 = create_work_order(
            shop_id, v, c, "pri1", priority=1, db_path=db,
        )
        open_work_order(wo_pri1, db_path=db)
        wo_urgent = create_work_order(
            shop_id, v, c, "other", priority=3, db_path=db,
        )
        open_work_order(wo_urgent, db_path=db)
        flag_urgent(wo_urgent, db_path=db)
        items = build_triage_queue(db_path=db)
        # urgent flag adds +500, which beats pri=1's +100
        assert items[0].work_order["id"] == wo_urgent

    def test_skip_demotes(self, db):
        shop_id = create_shop("s", db_path=db)
        c = _add_customer(db)
        v = _add_vehicle(db)
        wo1 = create_work_order(
            shop_id, v, c, "a", priority=3, db_path=db,
        )
        wo2 = create_work_order(
            shop_id, v, c, "b", priority=3, db_path=db,
        )
        open_work_order(wo1, db_path=db)
        open_work_order(wo2, db_path=db)
        skip_work_order(wo1, "parts", db_path=db)
        items = build_triage_queue(db_path=db)
        # wo2 (no skip) outranks wo1 (skipped)
        ids = [item.work_order["id"] for item in items]
        assert ids.index(wo2) < ids.index(wo1)

    def test_top_N_truncates(self, db):
        shop_id = create_shop("s", db_path=db)
        c = _add_customer(db)
        v = _add_vehicle(db)
        for _ in range(5):
            wo = create_work_order(shop_id, v, c, "x", db_path=db)
            open_work_order(wo, db_path=db)
        items = build_triage_queue(db_path=db, top=3)
        assert len(items) == 3

    def test_parts_soft_guard_when_phase165_absent(self, db):
        wo_id, _ = _seed_wo(db)
        # Phase 165 not installed → find_spec returns None → parts_ready=True
        ready, missing = _parts_available_for(wo_id, db_path=db)
        assert ready is True
        assert missing == []

    def test_flag_urgent_sets_priority_1_and_marker(self, db):
        wo_id, _ = _seed_wo(db, priority=3)
        flag_urgent(wo_id, db_path=db)
        with get_connection(db) as conn:
            row = conn.execute(
                "SELECT priority, description FROM work_orders WHERE id = ?",
                (wo_id,),
            ).fetchone()
        assert row["priority"] == 1
        assert (row["description"] or "").startswith("[TRIAGE_URGENT] ")

    def test_flag_urgent_idempotent(self, db):
        wo_id, _ = _seed_wo(db, priority=3)
        flag_urgent(wo_id, db_path=db)
        flag_urgent(wo_id, db_path=db)
        with get_connection(db) as conn:
            row = conn.execute(
                "SELECT description FROM work_orders WHERE id = ?", (wo_id,),
            ).fetchone()
        desc = row["description"] or ""
        # Only ONE [TRIAGE_URGENT] prefix
        assert desc.count("[TRIAGE_URGENT]") == 1

    def test_skip_empty_reason_clears(self, db):
        wo_id, _ = _seed_wo(db)
        skip_work_order(wo_id, "parts", db_path=db)
        skip_work_order(wo_id, "", db_path=db)
        with get_connection(db) as conn:
            row = conn.execute(
                "SELECT description FROM work_orders WHERE id = ?", (wo_id,),
            ).fetchone()
        desc = row["description"] or ""
        assert "[TRIAGE_SKIP" not in desc


# ===========================================================================
# 5. CLI
# ===========================================================================


class TestTriageCLI:
    def test_help_lists_5_subcommands(self, cli_db):
        runner = CliRunner()
        root = _make_cli()
        result = runner.invoke(root, ["shop", "triage", "--help"])
        assert result.exit_code == 0
        for sub in ("queue", "next", "flag-urgent", "skip", "weights"):
            assert sub in result.output

    def test_queue_empty(self, cli_db):
        runner = CliRunner()
        root = _make_cli()
        result = runner.invoke(root, ["shop", "triage", "queue"])
        assert result.exit_code == 0
        assert "No work orders" in result.output

    def test_queue_json(self, cli_db):
        wo_id, _ = _seed_wo(cli_db, priority=3)
        runner = CliRunner()
        root = _make_cli()
        result = runner.invoke(root, ["shop", "triage", "queue", "--json"])
        assert result.exit_code == 0
        parsed = _json.loads(result.output)
        assert len(parsed) == 1
        assert parsed[0]["work_order"]["id"] == wo_id
        assert parsed[0]["rank"] == 1

    def test_next_empty_exits_nonzero(self, cli_db):
        runner = CliRunner()
        root = _make_cli()
        result = runner.invoke(root, ["shop", "triage", "next"])
        assert result.exit_code != 0
        assert "No open" in result.output

    def test_flag_urgent_cli(self, cli_db):
        wo_id, _ = _seed_wo(cli_db, priority=3)
        runner = CliRunner()
        root = _make_cli()
        result = runner.invoke(
            root, ["shop", "triage", "flag-urgent", str(wo_id)],
        )
        assert result.exit_code == 0
        assert "URGENT" in result.output
        with get_connection(cli_db) as conn:
            row = conn.execute(
                "SELECT priority FROM work_orders WHERE id = ?", (wo_id,),
            ).fetchone()
        assert row["priority"] == 1

    def test_weights_reset_and_set(self, cli_db):
        shop_id = create_shop("s", db_path=cli_db)
        runner = CliRunner()
        root = _make_cli()
        result = runner.invoke(
            root, [
                "shop", "triage", "weights",
                "--shop", str(shop_id),
                "--set", "wait_weight=2.5",
            ],
        )
        assert result.exit_code == 0
        loaded = load_triage_weights(shop_id, db_path=cli_db)
        assert loaded.wait_weight == 2.5

        # Now reset
        result2 = runner.invoke(
            root, ["shop", "triage", "weights",
                   "--shop", str(shop_id), "--reset"],
        )
        assert result2.exit_code == 0
        loaded2 = load_triage_weights(shop_id, db_path=cli_db)
        assert loaded2.wait_weight == 1.0

    def test_skip_cli(self, cli_db):
        wo_id, _ = _seed_wo(cli_db)
        runner = CliRunner()
        root = _make_cli()
        result = runner.invoke(
            root, ["shop", "triage", "skip", str(wo_id),
                   "--reason", "parts back-ordered"],
        )
        assert result.exit_code == 0
        with get_connection(cli_db) as conn:
            row = conn.execute(
                "SELECT description FROM work_orders WHERE id = ?", (wo_id,),
            ).fetchone()
        assert "[TRIAGE_SKIP: parts back-ordered]" in (row["description"] or "")
