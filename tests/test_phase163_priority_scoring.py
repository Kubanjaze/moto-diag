"""Phase 163 — AI-ranked repair priority scoring tests.

Four test classes across ~30 tests:

- :class:`TestPureHelpers` (~6) — wait-time penalty, rubric floor, customer
  prior tickets, _should_apply mechanic-intent preservation.
- :class:`TestScoreSingle` (~10) — score_work_order with mock _default_scorer_fn.
- :class:`TestRescoreAll` (~6) — budget enforcement + dry-run + filter passthrough.
- :class:`TestPriorityCLI` (~8) — Click CliRunner round-trips for 4 subcommands.

All tests inject _default_scorer_fn — zero Anthropic SDK calls. Grep-test
verifies priority_scorer.py never imports anthropic directly.
"""

from __future__ import annotations

import json
import pathlib
from datetime import datetime, timezone
from unittest.mock import patch

import click
import pytest
from click.testing import CliRunner

from motodiag.cli.shop import register_shop
from motodiag.core.database import get_connection, init_db
from motodiag.crm import customer_repo
from motodiag.crm.models import Customer
from motodiag.shop import (
    AIResponse, PriorityBudgetExhausted, PriorityScore,
    PriorityScoreResponse, PriorityScorerError, TokenUsage,
    create_intake, create_shop, create_work_order, get_work_order,
    open_work_order, complete_work_order, start_work,
    rescore_all_open, score_work_order,
)
from motodiag.shop.priority_scorer import (
    _priority_from_rubric, _should_apply, _wait_time_penalty,
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
    path = str(tmp_path / "phase163.db")
    init_db(path)
    return path


@pytest.fixture
def cli_db(tmp_path, monkeypatch):
    from motodiag.core.config import reset_settings
    path = str(tmp_path / "phase163_cli.db")
    init_db(path)
    monkeypatch.setenv("MOTODIAG_DB_PATH", path)
    monkeypatch.setenv("COLUMNS", "240")
    reset_settings()
    yield path
    reset_settings()


def _seed_open_wo(db_path, priority=3):
    """Seed shop+customer+vehicle+intake+open WO; return wo_id."""
    shop_id = create_shop("s", db_path=db_path)
    c = _add_customer(db_path)
    v = _add_vehicle(db_path)
    intake = create_intake(shop_id, c, v, db_path=db_path)
    wo_id = create_work_order(
        shop_id, v, c, "test wo", priority=priority,
        intake_visit_id=intake, db_path=db_path,
    )
    open_work_order(wo_id, db_path=db_path)
    return wo_id


def make_fake_scorer(
    priority=2, confidence=0.9, safety=False,
    ridability="high", cost_cents=2, model="claude-haiku-4-5-20251001",
    tokens_in=120, tokens_out=40,
):
    """Drop-in for the _default_scorer_fn seam."""
    def _fake(inp, model=None, db_path=None):
        resp = PriorityScoreResponse(
            priority=priority,
            rationale="fake scorer deterministic output",
            confidence=confidence,
            safety_risk=safety,
            ridability_impact=ridability,
        )
        ai_resp = AIResponse(
            text="fake",
            model=model or "claude-haiku-4-5-20251001",
            usage=TokenUsage(input_tokens=tokens_in, output_tokens=tokens_out),
            cost_cents=cost_cents,
            cache_hit=False,
        )
        return (resp, ai_resp)
    return _fake


# ===========================================================================
# 1. Pure helpers
# ===========================================================================


class TestPureHelpers:
    def test_wait_time_penalty_zero_under_24h(self):
        assert _wait_time_penalty(0.0) == 0
        assert _wait_time_penalty(23.9) == 0

    def test_wait_time_penalty_one_24_to_72h(self):
        assert _wait_time_penalty(24.0) == 1
        assert _wait_time_penalty(71.9) == 1

    def test_wait_time_penalty_two_over_72h(self):
        assert _wait_time_penalty(72.0) == 2
        assert _wait_time_penalty(500.0) == 2

    def test_priority_from_rubric_clamps_to_5(self):
        assert _priority_from_rubric(severity_tier=4, wait_hours=72.0) == 5
        assert _priority_from_rubric(severity_tier=5, wait_hours=200.0) == 5

    def test_priority_from_rubric_clamps_to_1(self):
        # severity_tier 1 + 0 wait → 1; can't go below 1
        assert _priority_from_rubric(severity_tier=1, wait_hours=0) == 1

    def test_should_apply_safety_overrides_low_confidence(self):
        resp = PriorityScoreResponse(
            priority=1, rationale="brake out",
            confidence=0.3, safety_risk=True,
            ridability_impact="high",
        )
        assert _should_apply(resp, current=4, force=False) is True

    def test_should_apply_low_confidence_no_apply(self):
        resp = PriorityScoreResponse(
            priority=2, rationale="ambiguous evidence",
            confidence=0.5, safety_risk=False,
            ridability_impact="med",
        )
        assert _should_apply(resp, current=3, force=False) is False

    def test_should_apply_force_overrides(self):
        resp = PriorityScoreResponse(
            priority=2, rationale="ambiguous evidence",
            confidence=0.5, safety_risk=False,
            ridability_impact="med",
        )
        assert _should_apply(resp, current=3, force=True) is True

    def test_should_apply_no_change_skips_apply(self):
        resp = PriorityScoreResponse(
            priority=3, rationale="no change needed",
            confidence=0.95, safety_risk=False,
            ridability_impact="med",
        )
        assert _should_apply(resp, current=3, force=False) is False


# ===========================================================================
# 2. score_work_order with injection seam
# ===========================================================================


class TestScoreSingle:
    def test_high_confidence_change_applies(self, db):
        wo_id = _seed_open_wo(db, priority=4)
        score = score_work_order(
            wo_id, db_path=db,
            _default_scorer_fn=make_fake_scorer(
                priority=1, confidence=0.95, safety=True,
            ),
        )
        assert score.applied is True
        assert score.priority_after == 1
        assert score.safety_risk is True
        # Verify DB write-back
        row = get_work_order(wo_id, db_path=db)
        assert row["priority"] == 1

    def test_low_confidence_logs_only(self, db):
        wo_id = _seed_open_wo(db, priority=3)
        score = score_work_order(
            wo_id, db_path=db,
            _default_scorer_fn=make_fake_scorer(
                priority=1, confidence=0.5, safety=False,
            ),
        )
        assert score.applied is False
        assert score.priority_after == 1
        # Mechanic priority preserved
        row = get_work_order(wo_id, db_path=db)
        assert row["priority"] == 3

    def test_safety_overrides_low_confidence(self, db):
        wo_id = _seed_open_wo(db, priority=3)
        score = score_work_order(
            wo_id, db_path=db,
            _default_scorer_fn=make_fake_scorer(
                priority=1, confidence=0.40, safety=True,
            ),
        )
        assert score.applied is True
        row = get_work_order(wo_id, db_path=db)
        assert row["priority"] == 1

    def test_no_change_skips_apply(self, db):
        wo_id = _seed_open_wo(db, priority=3)
        score = score_work_order(
            wo_id, db_path=db,
            _default_scorer_fn=make_fake_scorer(
                priority=3, confidence=0.95,
            ),
        )
        assert score.applied is False
        row = get_work_order(wo_id, db_path=db)
        assert row["priority"] == 3

    def test_force_overrides_threshold(self, db):
        wo_id = _seed_open_wo(db, priority=3)
        score = score_work_order(
            wo_id, db_path=db, force=True,
            _default_scorer_fn=make_fake_scorer(
                priority=1, confidence=0.30,
            ),
        )
        assert score.applied is True
        row = get_work_order(wo_id, db_path=db)
        assert row["priority"] == 1

    def test_terminal_wo_raises(self, db):
        wo_id = _seed_open_wo(db, priority=3)
        start_work(wo_id, db_path=db)
        complete_work_order(wo_id, db_path=db)
        with pytest.raises(PriorityScorerError, match="terminal"):
            score_work_order(
                wo_id, db_path=db,
                _default_scorer_fn=make_fake_scorer(),
            )

    def test_returns_priority_score_with_metadata(self, db):
        wo_id = _seed_open_wo(db, priority=3)
        score = score_work_order(
            wo_id, db_path=db,
            _default_scorer_fn=make_fake_scorer(
                priority=2, confidence=0.85, cost_cents=1,
                tokens_in=100, tokens_out=30,
            ),
        )
        assert isinstance(score, PriorityScore)
        assert score.wo_id == wo_id
        assert score.priority_before == 3
        assert score.priority_after == 2
        assert score.cost_cents == 1
        assert score.tokens_in == 100
        assert score.tokens_out == 30


# ===========================================================================
# 3. rescore_all_open
# ===========================================================================


class TestRescoreAll:
    def test_iterates_open_wos(self, db):
        shop_id = create_shop("s", db_path=db)
        c = _add_customer(db)
        v = _add_vehicle(db)
        wo1 = create_work_order(shop_id, v, c, "a", db_path=db)
        wo2 = create_work_order(shop_id, v, c, "b", db_path=db)
        open_work_order(wo1, db_path=db)
        open_work_order(wo2, db_path=db)
        results = rescore_all_open(
            shop_id=shop_id, db_path=db,
            _default_scorer_fn=make_fake_scorer(cost_cents=1),
        )
        assert len(results) == 2

    def test_budget_exhausted_raises_with_partial(self, db):
        shop_id = create_shop("s", db_path=db)
        c = _add_customer(db)
        v = _add_vehicle(db)
        for _ in range(5):
            wo = create_work_order(shop_id, v, c, "x", db_path=db)
            open_work_order(wo, db_path=db)
        # budget=3, each call costs 2 → 1st OK (0→2), 2nd OK (2→4 exceeds at start of 3rd)
        with pytest.raises(PriorityBudgetExhausted) as exc_info:
            rescore_all_open(
                shop_id=shop_id, db_path=db, budget_cents=3,
                _default_scorer_fn=make_fake_scorer(cost_cents=2),
            )
        # Some scored; not all 5
        assert 0 < len(exc_info.value.scored_so_far) < 5

    def test_dry_run_does_not_write(self, db):
        wo_id = _seed_open_wo(db, priority=3)
        results = rescore_all_open(
            db_path=db, dry_run=True,
            _default_scorer_fn=make_fake_scorer(
                priority=1, confidence=0.95,
            ),
        )
        # Score recorded, but priority NOT mutated on disk
        row = get_work_order(wo_id, db_path=db)
        assert row["priority"] == 3
        # Returned score reflects dry-run rollback
        assert results[0].applied is False

    def test_limit_caps_candidates(self, db):
        shop_id = create_shop("s", db_path=db)
        c = _add_customer(db)
        v = _add_vehicle(db)
        for _ in range(5):
            wo = create_work_order(shop_id, v, c, "x", db_path=db)
            open_work_order(wo, db_path=db)
        results = rescore_all_open(
            shop_id=shop_id, db_path=db, limit=2,
            _default_scorer_fn=make_fake_scorer(cost_cents=1),
        )
        assert len(results) == 2

    def test_no_open_wos_returns_empty(self, db):
        results = rescore_all_open(
            db_path=db,
            _default_scorer_fn=make_fake_scorer(),
        )
        assert results == []


# ===========================================================================
# 4. CLI subcommands
# ===========================================================================


class TestPriorityCLI:
    def test_help_lists_4_subcommands(self, cli_db):
        runner = CliRunner()
        root = _make_cli()
        result = runner.invoke(root, ["shop", "priority", "--help"])
        assert result.exit_code == 0
        for sub in ("score", "rescore-all", "show", "budget"):
            assert sub in result.output

    def test_score_cli_with_mock(self, cli_db):
        wo_id = _seed_open_wo(cli_db, priority=3)
        runner = CliRunner()
        root = _make_cli()
        # Patch score_work_order at the import site used by cli/shop.py
        with patch(
            "motodiag.cli.shop.score_work_order",
            return_value=PriorityScore(
                wo_id=wo_id, priority_before=3, priority_after=1,
                rationale="mock", confidence=0.95, safety_risk=True,
                ridability_impact="high",
                ai_model="claude-haiku-4-5-20251001",
                cost_cents=2, tokens_in=100, tokens_out=30,
                cache_hit=False,
                generated_at=datetime.now(timezone.utc),
                applied=True,
            ),
        ):
            result = runner.invoke(root, [
                "shop", "priority", "score", str(wo_id), "--json",
            ])
        assert result.exit_code == 0, result.output
        parsed = json.loads(result.output)
        assert parsed["wo_id"] == wo_id
        assert parsed["priority_after"] == 1
        assert parsed["applied"] is True

    def test_rescore_all_cli_with_mock(self, cli_db):
        wo_id = _seed_open_wo(cli_db, priority=3)
        runner = CliRunner()
        root = _make_cli()
        sample = PriorityScore(
            wo_id=wo_id, priority_before=3, priority_after=2,
            rationale="mock", confidence=0.85, safety_risk=False,
            ridability_impact="med",
            ai_model="claude-haiku-4-5-20251001",
            cost_cents=1, tokens_in=80, tokens_out=20,
            cache_hit=False,
            generated_at=datetime.now(timezone.utc),
            applied=True,
        )
        with patch(
            "motodiag.cli.shop.rescore_all_open",
            return_value=[sample],
        ):
            result = runner.invoke(root, [
                "shop", "priority", "rescore-all", "--json",
            ])
        assert result.exit_code == 0, result.output
        parsed = json.loads(result.output)
        assert len(parsed) == 1
        assert parsed[0]["wo_id"] == wo_id

    def test_budget_cli_empty(self, cli_db):
        runner = CliRunner()
        root = _make_cli()
        result = runner.invoke(root, [
            "shop", "priority", "budget", "--json",
        ])
        assert result.exit_code == 0, result.output
        parsed = json.loads(result.output)
        assert parsed["calls"] == 0
        assert parsed["cost_cents"] == 0


# ===========================================================================
# 5. Anti-regression: priority_scorer must not import anthropic directly
# ===========================================================================


def test_priority_scorer_does_not_import_anthropic_directly():
    """Phase 162.5 contract: AI phases compose against shop.ai_client only."""
    src = pathlib.Path(
        "src/motodiag/shop/priority_scorer.py"
    ).read_text(encoding="utf-8")
    # Allow comments + module docstring mention, but no imports.
    for line in src.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        if stripped.startswith("import anthropic") or stripped.startswith(
            "from anthropic"
        ):
            pytest.fail(
                f"priority_scorer.py imports anthropic directly: {line!r}\n"
                "Phase 162.5 contract violated — must use shop.ai_client."
            )
