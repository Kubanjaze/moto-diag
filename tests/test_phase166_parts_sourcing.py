"""Phase 166 — AI parts sourcing tests.

Five test classes across ~28 tests:

- :class:`TestMigration030` (4) — schema bump, sourcing_recommendations table,
  CHECK constraints, rollback drops cleanly.
- :class:`TestRecommendSource` (10) — happy path with _default_scorer_fn injection,
  validation errors, cache-hit + persistence.
- :class:`TestPersistence` (5) — every recommendation persists; cache hits get cache_hit=1.
- :class:`TestSourcingCLI` (8) — recommend / show / budget round-trips with mocks.
- :class:`TestAntiRegression` (1) — parts_sourcing.py never imports anthropic directly.

All tests inject _default_scorer_fn — zero live tokens.
"""

from __future__ import annotations

import json as _json
import pathlib
from datetime import datetime, timezone
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
from motodiag.shop import (
    AIResponse, InvalidTierPreferenceError, MODEL_ALIASES, PartNotFoundError,
    SourcingRecommendation, TokenUsage, VendorSuggestion,
    get_recommendation, recommend_source, sourcing_budget,
)


def _make_cli():
    @click.group()
    def root() -> None:
        """test root"""
    register_shop(root)
    return root


def _add_part(db_path, slug="brake-pad-x", oem="HD-1234", typical_cents=1500):
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            """INSERT INTO parts (slug, oem_part_number, brand, description,
               category, make, model_pattern, typical_cost_cents, verified_by)
               VALUES (?, ?, 'EBC', 'sintered pad', 'brakes',
                       'harley-davidson', 'Sportster%', ?, 'test')""",
            (slug, oem, typical_cents),
        )
        return cursor.lastrowid


def _add_xref(db_path, oem_part_id, aftermarket_part_id, rating=5):
    with get_connection(db_path) as conn:
        conn.execute(
            """INSERT INTO parts_xref
               (oem_part_id, aftermarket_part_id, equivalence_rating)
               VALUES (?, ?, ?)""",
            (oem_part_id, aftermarket_part_id, rating),
        )


@pytest.fixture
def db(tmp_path):
    path = str(tmp_path / "phase166.db")
    init_db(path)
    return path


@pytest.fixture
def cli_db(tmp_path, monkeypatch):
    from motodiag.core.config import reset_settings
    path = str(tmp_path / "phase166_cli.db")
    init_db(path)
    monkeypatch.setenv("MOTODIAG_DB_PATH", path)
    monkeypatch.setenv("COLUMNS", "240")
    reset_settings()
    yield path
    reset_settings()


def make_fake_scorer(
    source_tier="aftermarket", confidence=0.9, cost_cents=2,
    rationale="standard mechanic recommendation",
    estimated_cost_cents=599,
    tokens_in=200, tokens_out=80, model=MODEL_ALIASES["haiku"],
    cache_hit=False,
):
    """_default_scorer_fn drop-in returning (payload_dict, AIResponse)."""
    def _fake(part, vehicle, xrefs, quantity, tier_preference, model=model):
        payload = {
            "part_id": part["id"],
            "quantity": quantity,
            "source_tier": source_tier,
            "confidence": confidence,
            "rationale": rationale,
            "estimated_cost_cents": estimated_cost_cents,
            "risk_notes": None,
            "alternative_parts": [xr["aftermarket_part_id"] for xr in xrefs],
            "vendor_suggestions": [
                {"name": "RevZilla", "url": None,
                 "rough_price_cents": estimated_cost_cents,
                 "availability": "in_stock", "notes": None},
            ],
        }
        ai_resp = AIResponse(
            text="fake",
            model=model,
            usage=TokenUsage(input_tokens=tokens_in, output_tokens=tokens_out),
            cost_cents=cost_cents,
            cache_hit=cache_hit,
        )
        return (payload, ai_resp)
    return _fake


# ===========================================================================
# 1. Migration 030
# ===========================================================================


class TestMigration030:
    def test_schema_version_bumped_to_at_least_30(self, db):
        assert SCHEMA_VERSION >= 30
        assert get_schema_version(db) >= 30

    def test_sourcing_recommendations_table_present(self, db):
        assert table_exists("sourcing_recommendations", db)

    def test_indexes_present(self, db):
        expected = {"idx_sr_part", "idx_sr_requisition"}
        with get_connection(db) as conn:
            actual = {r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='index'"
            ).fetchall()}
        assert expected.issubset(actual)

    def test_rollback_to_29_drops_table(self, tmp_path):
        path = str(tmp_path / "rollback.db")
        init_db(path)
        assert table_exists("sourcing_recommendations", path)
        rollback_to_version(29, path)
        assert not table_exists("sourcing_recommendations", path)
        # Phase 165 substrate preserved
        assert table_exists("work_order_parts", path)


# ===========================================================================
# 2. recommend_source
# ===========================================================================


class TestRecommendSource:
    def test_unknown_part_raises(self, db):
        with pytest.raises(PartNotFoundError):
            recommend_source(999, db_path=db,
                             _default_scorer_fn=make_fake_scorer())

    def test_invalid_tier_raises(self, db):
        part_id = _add_part(db)
        with pytest.raises(InvalidTierPreferenceError):
            recommend_source(part_id, tier_preference="bogus",
                             db_path=db,
                             _default_scorer_fn=make_fake_scorer())

    def test_zero_qty_raises(self, db):
        part_id = _add_part(db)
        with pytest.raises(ValueError):
            recommend_source(part_id, quantity=0, db_path=db,
                             _default_scorer_fn=make_fake_scorer())

    def test_returns_full_recommendation(self, db):
        part_id = _add_part(db)
        rec = recommend_source(
            part_id, db_path=db,
            _default_scorer_fn=make_fake_scorer(
                source_tier="aftermarket", confidence=0.9,
            ),
        )
        assert isinstance(rec, SourcingRecommendation)
        assert rec.part_id == part_id
        assert rec.source_tier == "aftermarket"
        assert rec.confidence == 0.9

    def test_xrefs_loaded_for_alternatives(self, db):
        oem_part_id = _add_part(db, slug="oem-pad", oem="HD-X")
        aftermarket_id = _add_part(
            db, slug="ebc-pad", oem="EBC-FA416HH", typical_cents=599,
        )
        _add_xref(db, oem_part_id, aftermarket_id, rating=5)
        rec = recommend_source(
            oem_part_id, db_path=db,
            _default_scorer_fn=make_fake_scorer(),
        )
        assert aftermarket_id in rec.alternative_parts

    def test_quantity_passes_through(self, db):
        part_id = _add_part(db)
        rec = recommend_source(
            part_id, quantity=5, db_path=db,
            _default_scorer_fn=make_fake_scorer(),
        )
        assert rec.quantity == 5

    def test_vehicle_id_passes_through_to_persistence(self, db):
        part_id = _add_part(db)
        # Add a vehicle
        with get_connection(db) as conn:
            cursor = conn.execute(
                "INSERT INTO vehicles (make, model, year, protocol) "
                "VALUES ('Harley-Davidson', 'Sportster', 2010, 'none')",
            )
            v = cursor.lastrowid
        recommend_source(
            part_id, vehicle_id=v, db_path=db,
            _default_scorer_fn=make_fake_scorer(),
        )
        with get_connection(db) as conn:
            row = conn.execute(
                "SELECT vehicle_id FROM sourcing_recommendations "
                "ORDER BY id DESC LIMIT 1",
            ).fetchone()
        assert row["vehicle_id"] == v

    def test_cost_cents_propagated(self, db):
        part_id = _add_part(db)
        rec = recommend_source(
            part_id, db_path=db,
            _default_scorer_fn=make_fake_scorer(cost_cents=5),
        )
        assert rec.cost_cents == 5

    def test_estimated_cost_cents_in_recommendation(self, db):
        part_id = _add_part(db)
        rec = recommend_source(
            part_id, db_path=db,
            _default_scorer_fn=make_fake_scorer(estimated_cost_cents=1995),
        )
        assert rec.estimated_cost_cents == 1995

    def test_source_tier_check_constraint(self, db):
        """Migration 030 CHECK rejects invalid source_tier via direct INSERT."""
        part_id = _add_part(db)
        import sqlite3
        with pytest.raises(sqlite3.IntegrityError):
            with get_connection(db) as conn:
                conn.execute(
                    "INSERT INTO sourcing_recommendations "
                    "(part_id, source_tier, confidence, recommendation_json, ai_model) "
                    "VALUES (?, 'bogus', 0.5, '{}', 'haiku')",
                    (part_id,),
                )


# ===========================================================================
# 3. Persistence
# ===========================================================================


class TestPersistence:
    def test_recommendation_persists(self, db):
        part_id = _add_part(db)
        rec = recommend_source(
            part_id, db_path=db,
            _default_scorer_fn=make_fake_scorer(),
        )
        with get_connection(db) as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS n FROM sourcing_recommendations",
            ).fetchone()
        assert row["n"] == 1

    def test_cache_hit_persists_with_flag(self, db):
        part_id = _add_part(db)
        recommend_source(
            part_id, db_path=db,
            _default_scorer_fn=make_fake_scorer(cache_hit=True, cost_cents=0),
        )
        with get_connection(db) as conn:
            row = conn.execute(
                "SELECT cache_hit, cost_cents FROM sourcing_recommendations "
                "ORDER BY id DESC LIMIT 1",
            ).fetchone()
        assert row["cache_hit"] == 1
        assert row["cost_cents"] == 0

    def test_get_recommendation_round_trip(self, db):
        part_id = _add_part(db)
        recommend_source(
            part_id, db_path=db,
            _default_scorer_fn=make_fake_scorer(source_tier="oem"),
        )
        with get_connection(db) as conn:
            rec_id = conn.execute(
                "SELECT id FROM sourcing_recommendations LIMIT 1",
            ).fetchone()["id"]
        loaded = get_recommendation(rec_id, db_path=db)
        assert loaded is not None
        assert loaded["part_id"] == part_id
        assert loaded["source_tier"] == "oem"
        assert "rationale" in loaded["recommendation"]

    def test_get_recommendation_unknown_returns_none(self, db):
        assert get_recommendation(9999, db_path=db) is None

    def test_sourcing_budget_aggregates(self, db):
        part_id = _add_part(db)
        # 2 cache misses + 1 cache hit
        recommend_source(part_id, db_path=db,
                         _default_scorer_fn=make_fake_scorer(cost_cents=2))
        recommend_source(part_id, db_path=db, use_cache=False,
                         _default_scorer_fn=make_fake_scorer(cost_cents=3))
        recommend_source(part_id, quantity=2, db_path=db,
                         _default_scorer_fn=make_fake_scorer(cache_hit=True, cost_cents=0))
        rollup = sourcing_budget(db_path=db)
        assert rollup["calls"] == 3
        assert rollup["cost_cents"] == 5
        assert rollup["cache_hit_count"] == 1
        assert "aftermarket" in rollup["tier_distribution"]


# ===========================================================================
# 4. CLI
# ===========================================================================


class TestSourcingCLI:
    def test_help_lists_3_subcommands(self, cli_db):
        runner = CliRunner()
        root = _make_cli()
        result = runner.invoke(root, ["shop", "sourcing", "--help"])
        assert result.exit_code == 0
        for sub in ("recommend", "show", "budget"):
            assert sub in result.output

    def test_recommend_cli_with_mock(self, cli_db):
        part_id = _add_part(cli_db)
        runner = CliRunner()
        root = _make_cli()
        sample = SourcingRecommendation(
            part_id=part_id, quantity=1,
            source_tier="aftermarket", confidence=0.9,
            rationale="test recommendation",
            estimated_cost_cents=599,
            ai_model=MODEL_ALIASES["haiku"],
            tokens_in=200, tokens_out=50, cost_cents=2,
            cache_hit=False,
            generated_at=datetime.now(timezone.utc),
        )
        with patch(
            "motodiag.cli.shop.recommend_source",
            return_value=sample,
        ):
            result = runner.invoke(root, [
                "shop", "sourcing", "recommend",
                "--part-id", str(part_id), "--json",
            ])
        assert result.exit_code == 0, result.output
        parsed = _json.loads(result.output)
        assert parsed["part_id"] == part_id
        assert parsed["source_tier"] == "aftermarket"

    def test_recommend_cli_invalid_tier(self, cli_db):
        runner = CliRunner()
        root = _make_cli()
        result = runner.invoke(root, [
            "shop", "sourcing", "recommend",
            "--part-id", "1", "--tier", "bogus",
        ])
        # Click's Choice validator catches this
        assert result.exit_code != 0

    def test_show_unknown_returns_error(self, cli_db):
        runner = CliRunner()
        root = _make_cli()
        result = runner.invoke(root, ["shop", "sourcing", "show", "9999"])
        assert result.exit_code != 0
        assert "not found" in result.output

    def test_show_after_recommend(self, cli_db):
        part_id = _add_part(cli_db)
        recommend_source(
            part_id, db_path=cli_db,
            _default_scorer_fn=make_fake_scorer(),
        )
        with get_connection(cli_db) as conn:
            rec_id = conn.execute(
                "SELECT id FROM sourcing_recommendations LIMIT 1",
            ).fetchone()["id"]
        runner = CliRunner()
        root = _make_cli()
        result = runner.invoke(root, [
            "shop", "sourcing", "show", str(rec_id), "--json",
        ])
        assert result.exit_code == 0
        parsed = _json.loads(result.output)
        assert parsed["id"] == rec_id

    def test_budget_empty_zero(self, cli_db):
        runner = CliRunner()
        root = _make_cli()
        result = runner.invoke(root, [
            "shop", "sourcing", "budget", "--json",
        ])
        assert result.exit_code == 0
        parsed = _json.loads(result.output)
        assert parsed["calls"] == 0
        assert parsed["cost_cents"] == 0

    def test_budget_after_calls(self, cli_db):
        part_id = _add_part(cli_db)
        recommend_source(
            part_id, db_path=cli_db,
            _default_scorer_fn=make_fake_scorer(cost_cents=2),
        )
        runner = CliRunner()
        root = _make_cli()
        result = runner.invoke(root, [
            "shop", "sourcing", "budget", "--json",
        ])
        assert result.exit_code == 0
        parsed = _json.loads(result.output)
        assert parsed["calls"] == 1
        assert parsed["cost_cents"] == 2


# ===========================================================================
# 5. Anti-regression: never import anthropic directly
# ===========================================================================


def test_parts_sourcing_does_not_import_anthropic_directly():
    """Phase 162.5 contract: AI phases compose against shop.ai_client only."""
    src = pathlib.Path(
        "src/motodiag/shop/parts_sourcing.py"
    ).read_text(encoding="utf-8")
    for line in src.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        if (stripped.startswith("import anthropic")
                or stripped.startswith("from anthropic")):
            pytest.fail(
                f"parts_sourcing.py imports anthropic directly: {line!r}\n"
                "Phase 162.5 contract violated — must use shop.ai_client."
            )
