"""Phase 167 — AI labor time estimation tests.

Five test classes across ~30 tests:

- :class:`TestMigration031` (4) — schema bump, labor_estimates table, CHECK, rollback.
- :class:`TestEstimateLabor` (11) — happy path + validation + math guard + write-back audit.
- :class:`TestReconcile` (5) — pure-arithmetic comparison happy + edge cases.
- :class:`TestBulkEstimate` (4) — iterates open WOs + skip-unless-force + bulk budget.
- :class:`TestLaborCLI` (6) — estimate/bulk/show/history/reconcile/budget CLI round-trips.
- :class:`TestAntiRegression` (2) — no direct anthropic import; no raw UPDATE work_orders.
"""

from __future__ import annotations

import json as _json
import pathlib
import re
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
from motodiag.crm import customer_repo
from motodiag.crm.models import Customer
from motodiag.shop import (
    AIResponse, LaborEstimate, LaborEstimateMathError, LaborEstimatorError,
    ReconcileMissingDataError, TokenUsage,
    bulk_estimate_open_wos, complete_work_order, create_shop,
    create_work_order, estimate_labor, get_work_order, labor_budget,
    list_labor_estimates, open_work_order, reconcile_with_actual,
    start_work, update_work_order,
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


def _add_customer(db_path, name="Jane"):
    return customer_repo.create_customer(
        Customer(name=name, phone="555-0100", email="jane@example.com"),
        db_path=db_path,
    )


@pytest.fixture
def db(tmp_path):
    path = str(tmp_path / "phase167.db")
    init_db(path)
    return path


@pytest.fixture
def cli_db(tmp_path, monkeypatch):
    from motodiag.core.config import reset_settings
    path = str(tmp_path / "phase167_cli.db")
    init_db(path)
    monkeypatch.setenv("MOTODIAG_DB_PATH", path)
    monkeypatch.setenv("COLUMNS", "240")
    reset_settings()
    yield path
    reset_settings()


def _seed_open_wo(db_path, title="oil change"):
    shop_id = create_shop("s", db_path=db_path)
    c = _add_customer(db_path)
    v = _add_vehicle(db_path)
    wo_id = create_work_order(shop_id, v, c, title, db_path=db_path)
    open_work_order(wo_id, db_path=db_path)
    return wo_id, shop_id


def make_fake_scorer(
    base=0.5, skill=0.0, mileage=0.0, confidence=0.9,
    rationale="oil change is a standard half-hour bench job",
    skill_tier="journeyman", cost_cents=2,
    tokens_in=150, tokens_out=80, model="claude-haiku-4-5-20251001",
    prompt_cache_hit=False,
    breakdown=None, alternatives=None, environment_notes=None,
):
    """_default_scorer_fn drop-in returning (payload_dict, AIResponse).

    The closure captures `model` by name into the inner var so the
    call-site's ``model=`` kwarg override doesn't shadow it.
    """
    adjusted = round(base * (1 + skill) * (1 + mileage), 2)
    _closure_model = model
    _closure_skill_tier = skill_tier

    def _fake(wo, issues, **_call_kwargs):
        # Ignore call-site model/skill_tier overrides; closure wins.
        payload = {
            "wo_id": wo["id"],
            "base_hours": base,
            "adjusted_hours": adjusted,
            "skill_adjustment": skill,
            "mileage_adjustment": mileage,
            "confidence": confidence,
            "rationale": rationale,
            "skill_tier": _closure_skill_tier,
            "breakdown": breakdown or [],
            "alternative_estimates": alternatives or [],
            "environment_notes": environment_notes,
        }
        ai_resp = AIResponse(
            text="fake",
            model=_closure_model,
            usage=TokenUsage(input_tokens=tokens_in, output_tokens=tokens_out),
            cost_cents=cost_cents,
            cache_hit=prompt_cache_hit,
        )
        return (payload, ai_resp)
    return _fake


# ===========================================================================
# 1. Migration 031
# ===========================================================================


class TestMigration031:
    def test_schema_version_bumped_to_at_least_31(self, db):
        assert SCHEMA_VERSION >= 31
        assert get_schema_version(db) >= 31

    def test_labor_estimates_table_present(self, db):
        assert table_exists("labor_estimates", db)

    def test_indexes_present(self, db):
        expected = {
            "idx_labor_est_wo",
            "idx_labor_est_generated",
            "idx_labor_est_model",
        }
        with get_connection(db) as conn:
            actual = {r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='index'"
            ).fetchall()}
        assert expected.issubset(actual)

    def test_rollback_to_30_drops_table(self, tmp_path):
        path = str(tmp_path / "rollback.db")
        init_db(path)
        assert table_exists("labor_estimates", path)
        rollback_to_version(30, path)
        assert not table_exists("labor_estimates", path)
        # Phase 166 substrate preserved
        assert table_exists("sourcing_recommendations", path)


# ===========================================================================
# 2. estimate_labor
# ===========================================================================


class TestEstimateLabor:
    def test_unknown_wo_raises(self, db):
        with pytest.raises(Exception):
            estimate_labor(999, db_path=db, _default_scorer_fn=make_fake_scorer())

    def test_invalid_skill_tier_raises(self, db):
        wo_id, _ = _seed_open_wo(db)
        with pytest.raises(LaborEstimatorError):
            estimate_labor(wo_id, skill_tier="bogus", db_path=db,
                           _default_scorer_fn=make_fake_scorer())

    def test_terminal_wo_raises(self, db):
        wo_id, _ = _seed_open_wo(db)
        start_work(wo_id, db_path=db)
        complete_work_order(wo_id, actual_hours=0.5, db_path=db)
        with pytest.raises(LaborEstimatorError, match="terminal"):
            estimate_labor(wo_id, db_path=db,
                           _default_scorer_fn=make_fake_scorer())

    def test_basic_estimate_with_write_back(self, db):
        wo_id, _ = _seed_open_wo(db)
        est = estimate_labor(
            wo_id, db_path=db,
            _default_scorer_fn=make_fake_scorer(
                base=0.5, skill=0.0, mileage=0.0,
            ),
        )
        assert isinstance(est, LaborEstimate)
        assert est.base_hours == 0.5
        assert est.adjusted_hours == 0.5
        # Write-back happened
        row = get_work_order(wo_id, db_path=db)
        assert abs(float(row["estimated_hours"]) - 0.5) < 0.001

    def test_skill_tier_apprentice_applies_multiplier(self, db):
        wo_id, _ = _seed_open_wo(db)
        est = estimate_labor(
            wo_id, skill_tier="apprentice", db_path=db,
            _default_scorer_fn=make_fake_scorer(
                base=2.0, skill=0.25, mileage=0.0, skill_tier="apprentice",
            ),
        )
        # 2.0 * 1.25 = 2.5
        assert est.adjusted_hours == 2.5

    def test_mileage_adjustment_applies(self, db):
        wo_id, _ = _seed_open_wo(db)
        est = estimate_labor(
            wo_id, db_path=db,
            _default_scorer_fn=make_fake_scorer(
                base=3.0, skill=0.0, mileage=0.10,
            ),
        )
        # 3.0 * 1.10 = 3.3
        assert abs(est.adjusted_hours - 3.3) < 0.001

    def test_no_write_back_preserves_estimated_hours(self, db):
        wo_id, _ = _seed_open_wo(db)
        # Pre-set a mechanic estimate
        update_work_order(wo_id, {"estimated_hours": 9.9}, db_path=db)
        estimate_labor(
            wo_id, db_path=db, write_back=False,
            _default_scorer_fn=make_fake_scorer(base=0.5),
        )
        row = get_work_order(wo_id, db_path=db)
        assert float(row["estimated_hours"]) == 9.9

    def test_write_back_routes_through_update_work_order(self, db):
        """Critical: write-back must call update_work_order, NOT raw SQL."""
        wo_id, _ = _seed_open_wo(db)
        with patch(
            "motodiag.shop.labor_estimator.update_work_order",
        ) as mock_upd:
            estimate_labor(
                wo_id, db_path=db,
                _default_scorer_fn=make_fake_scorer(base=2.5),
            )
        # Find the call that included estimated_hours (there may be only one)
        calls = mock_upd.call_args_list
        matched = False
        for call in calls:
            # args or kwargs may carry the updates dict
            updates = None
            if len(call.args) > 1:
                updates = call.args[1]
            elif "updates" in call.kwargs:
                updates = call.kwargs["updates"]
            if isinstance(updates, dict) and "estimated_hours" in updates:
                matched = True
                break
        assert matched, (
            "update_work_order must be called with estimated_hours in updates"
        )

    def test_math_inconsistency_without_retry_raises(self, db):
        """If the injected scorer returns math-inconsistent output, LaborEstimateMathError."""
        wo_id, _ = _seed_open_wo(db)

        def bad_scorer(wo, issues, skill_tier=None, model=None):
            payload = {
                "wo_id": wo["id"],
                "base_hours": 1.0,
                "adjusted_hours": 99.0,  # inconsistent
                "skill_adjustment": 0.0,
                "mileage_adjustment": 0.0,
                "confidence": 0.9,
                "rationale": "bad math",
                "skill_tier": "journeyman",
                "breakdown": [],
                "alternative_estimates": [],
                "environment_notes": None,
            }
            ai_resp = AIResponse(
                text="bad",
                model="claude-haiku-4-5-20251001",
                usage=TokenUsage(),
                cost_cents=0, cache_hit=False,
            )
            return (payload, ai_resp)

        with pytest.raises(LaborEstimateMathError):
            estimate_labor(
                wo_id, db_path=db, _default_scorer_fn=bad_scorer,
            )

    def test_persists_to_labor_estimates(self, db):
        wo_id, _ = _seed_open_wo(db)
        estimate_labor(
            wo_id, db_path=db,
            _default_scorer_fn=make_fake_scorer(base=1.5),
        )
        rows = list_labor_estimates(wo_id=wo_id, db_path=db)
        assert len(rows) == 1
        assert float(rows[0]["adjusted_hours"]) == 1.5

    def test_full_audit_fields_persisted(self, db):
        wo_id, _ = _seed_open_wo(db)
        estimate_labor(
            wo_id, db_path=db,
            _default_scorer_fn=make_fake_scorer(
                cost_cents=7, tokens_in=200, tokens_out=50,
                model="claude-sonnet-4-6",
            ),
        )
        rows = list_labor_estimates(wo_id=wo_id, db_path=db)
        r = rows[0]
        assert r["cost_cents"] == 7
        assert r["tokens_in"] == 200
        assert r["tokens_out"] == 50
        assert r["ai_model"] == "claude-sonnet-4-6"

    def test_prompt_cache_hit_flag(self, db):
        wo_id, _ = _seed_open_wo(db)
        estimate_labor(
            wo_id, db_path=db,
            _default_scorer_fn=make_fake_scorer(prompt_cache_hit=True),
        )
        rows = list_labor_estimates(wo_id=wo_id, db_path=db)
        assert rows[0]["prompt_cache_hit"] == 1


# ===========================================================================
# 3. reconcile_with_actual
# ===========================================================================


class TestReconcile:
    def test_non_completed_raises(self, db):
        wo_id, _ = _seed_open_wo(db)
        estimate_labor(wo_id, db_path=db,
                       _default_scorer_fn=make_fake_scorer())
        with pytest.raises(ReconcileMissingDataError):
            reconcile_with_actual(wo_id, db_path=db)

    def test_missing_actual_hours_raises(self, db):
        wo_id, _ = _seed_open_wo(db)
        estimate_labor(wo_id, db_path=db,
                       _default_scorer_fn=make_fake_scorer())
        start_work(wo_id, db_path=db)
        # Complete WITHOUT actual_hours
        complete_work_order(wo_id, db_path=db)
        with pytest.raises(ReconcileMissingDataError):
            reconcile_with_actual(wo_id, db_path=db)

    def test_no_estimate_raises(self, db):
        wo_id, _ = _seed_open_wo(db)
        start_work(wo_id, db_path=db)
        complete_work_order(wo_id, actual_hours=0.5, db_path=db)
        with pytest.raises(ReconcileMissingDataError):
            reconcile_with_actual(wo_id, db_path=db)

    def test_within_bucket_20_pct(self, db):
        wo_id, _ = _seed_open_wo(db)
        estimate_labor(
            wo_id, db_path=db,
            _default_scorer_fn=make_fake_scorer(base=2.0),
        )
        start_work(wo_id, db_path=db)
        complete_work_order(wo_id, actual_hours=2.3, db_path=db)  # +15%
        report = reconcile_with_actual(wo_id, db_path=db)
        assert report.bucket == "within"

    def test_under_bucket_when_actual_much_higher(self, db):
        wo_id, _ = _seed_open_wo(db)
        estimate_labor(
            wo_id, db_path=db,
            _default_scorer_fn=make_fake_scorer(base=1.0),
        )
        start_work(wo_id, db_path=db)
        complete_work_order(wo_id, actual_hours=2.0, db_path=db)  # +100%
        report = reconcile_with_actual(wo_id, db_path=db)
        assert report.bucket == "under"
        assert report.delta_pct is not None
        assert report.delta_pct > 20


# ===========================================================================
# 4. bulk_estimate_open_wos
# ===========================================================================


class TestBulkEstimate:
    def test_iterates_open_wos(self, db):
        shop_id = create_shop("s", db_path=db)
        c = _add_customer(db)
        v = _add_vehicle(db)
        wo1 = create_work_order(shop_id, v, c, "a", db_path=db)
        wo2 = create_work_order(shop_id, v, c, "b", db_path=db)
        open_work_order(wo1, db_path=db)
        open_work_order(wo2, db_path=db)
        results = bulk_estimate_open_wos(
            shop_id, db_path=db,
            _default_scorer_fn=make_fake_scorer(),
        )
        assert len(results) == 2

    def test_skips_wos_with_estimated_hours(self, db):
        shop_id = create_shop("s", db_path=db)
        c = _add_customer(db)
        v = _add_vehicle(db)
        wo = create_work_order(shop_id, v, c, "x", db_path=db)
        open_work_order(wo, db_path=db)
        update_work_order(wo, {"estimated_hours": 5.0}, db_path=db)
        results = bulk_estimate_open_wos(
            shop_id, db_path=db,
            _default_scorer_fn=make_fake_scorer(),
        )
        assert len(results) == 0

    def test_force_re_estimates(self, db):
        shop_id = create_shop("s", db_path=db)
        c = _add_customer(db)
        v = _add_vehicle(db)
        wo = create_work_order(shop_id, v, c, "x", db_path=db)
        open_work_order(wo, db_path=db)
        update_work_order(wo, {"estimated_hours": 5.0}, db_path=db)
        results = bulk_estimate_open_wos(
            shop_id, db_path=db, force=True,
            _default_scorer_fn=make_fake_scorer(base=1.0),
        )
        assert len(results) == 1

    def test_labor_budget_aggregates(self, db):
        wo_id, shop_id = _seed_open_wo(db)
        estimate_labor(wo_id, db_path=db,
                       _default_scorer_fn=make_fake_scorer(cost_cents=3))
        rollup = labor_budget(db_path=db)
        assert rollup["calls"] == 1
        assert rollup["cost_cents"] == 3


# ===========================================================================
# 5. CLI
# ===========================================================================


class TestLaborCLI:
    def test_help_lists_6_subcommands(self, cli_db):
        runner = CliRunner()
        root = _make_cli()
        result = runner.invoke(root, ["shop", "labor", "--help"])
        assert result.exit_code == 0
        for sub in ("estimate", "bulk", "show", "history",
                    "reconcile", "budget"):
            assert sub in result.output

    def test_estimate_cli_with_mock(self, cli_db):
        wo_id, _ = _seed_open_wo(cli_db)
        runner = CliRunner()
        root = _make_cli()
        sample = LaborEstimate(
            wo_id=wo_id, base_hours=0.5, adjusted_hours=0.5,
            skill_adjustment=0.0, mileage_adjustment=0.0,
            confidence=0.9, rationale="quick job",
            ai_model="claude-haiku-4-5-20251001",
            tokens_in=100, tokens_out=30, cost_cents=2,
            prompt_cache_hit=False,
            generated_at=datetime.now(timezone.utc),
        )
        with patch(
            "motodiag.cli.shop.estimate_labor", return_value=sample,
        ):
            result = runner.invoke(root, [
                "shop", "labor", "estimate", str(wo_id), "--json",
            ])
        assert result.exit_code == 0, result.output
        parsed = _json.loads(result.output)
        assert parsed["wo_id"] == wo_id

    def test_budget_cli_empty(self, cli_db):
        runner = CliRunner()
        root = _make_cli()
        result = runner.invoke(root, ["shop", "labor", "budget", "--json"])
        assert result.exit_code == 0
        parsed = _json.loads(result.output)
        assert parsed["calls"] == 0

    def test_history_cli_empty(self, cli_db):
        wo_id, _ = _seed_open_wo(cli_db)
        runner = CliRunner()
        root = _make_cli()
        result = runner.invoke(root, [
            "shop", "labor", "history", str(wo_id),
        ])
        assert result.exit_code == 0
        assert "No labor estimates" in result.output

    def test_history_cli_with_data(self, cli_db):
        wo_id, _ = _seed_open_wo(cli_db)
        estimate_labor(
            wo_id, db_path=cli_db,
            _default_scorer_fn=make_fake_scorer(base=1.5),
        )
        runner = CliRunner()
        root = _make_cli()
        result = runner.invoke(root, [
            "shop", "labor", "history", str(wo_id), "--json",
        ])
        assert result.exit_code == 0
        parsed = _json.loads(result.output)
        assert parsed["wo_id"] == wo_id
        assert len(parsed["estimates"]) == 1

    def test_reconcile_cli_non_completed(self, cli_db):
        wo_id, _ = _seed_open_wo(cli_db)
        runner = CliRunner()
        root = _make_cli()
        result = runner.invoke(root, [
            "shop", "labor", "reconcile", str(wo_id),
        ])
        assert result.exit_code != 0


# ===========================================================================
# 6. Anti-regression
# ===========================================================================


def test_labor_estimator_does_not_import_anthropic_directly():
    """Phase 162.5 contract: AI phases compose against shop.ai_client only."""
    src = pathlib.Path(
        "src/motodiag/shop/labor_estimator.py"
    ).read_text(encoding="utf-8")
    for line in src.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        if (stripped.startswith("import anthropic")
                or stripped.startswith("from anthropic")):
            pytest.fail(
                f"labor_estimator.py imports anthropic directly: {line!r}"
            )


def test_labor_estimator_does_not_write_raw_sql_to_work_orders():
    """Phase 161 whitelist discipline: never write raw SQL to work_orders.

    Any UPDATE/INSERT/DELETE on work_orders must route through
    update_work_order. Check the source for forbidden SQL strings.
    """
    src = pathlib.Path(
        "src/motodiag/shop/labor_estimator.py"
    ).read_text(encoding="utf-8")
    forbidden = [
        r"UPDATE\s+work_orders",
        r"INSERT\s+INTO\s+work_orders",
        r"DELETE\s+FROM\s+work_orders",
    ]
    for pattern in forbidden:
        if re.search(pattern, src, re.IGNORECASE):
            pytest.fail(
                f"labor_estimator.py contains forbidden SQL pattern "
                f"{pattern!r} against work_orders — must route through "
                "Phase 161 update_work_order whitelist."
            )
