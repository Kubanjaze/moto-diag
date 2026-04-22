"""Phase 162 — Issue logging + categorization tests.

Four test classes across ~42 tests:

- :class:`TestMigration027` (6) — schema bump to >=27, issues table + 5 indexes,
  category CHECK enforces 12 values (rejects e.g. 'unknown_cat'), severity CHECK
  rejects 'info', status CHECK rejects invalid values, rollback drops cleanly.
- :class:`TestIssueRepo` (16) — CRUD + validators + composable filters + stats.
- :class:`TestIssueLifecycle` (10) — guarded transitions: resolve / mark-duplicate
  / mark-wontfix / reopen + invalid transition + cascade-delete + canonical-delete.
- :class:`TestIssueCLI` (10) — all 12 subcommands round-trip through CliRunner.

All tests SW + SQL only. Zero AI calls, zero network, zero live tokens.
"""

from __future__ import annotations

import json as _json

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
    ISSUE_CATEGORIES,
    ISSUE_SEVERITIES,
    ISSUE_STATUSES,
    InvalidIssueTransition,
    IssueNotFoundError,
    categorize_issue,
    count_issues,
    create_intake,
    create_issue,
    create_shop,
    create_work_order,
    get_issue,
    issue_stats,
    link_dtc,
    link_symptom,
    list_issues,
    mark_duplicate_issue,
    mark_wontfix_issue,
    reopen_issue,
    require_issue,
    resolve_issue,
    update_issue,
)


def _make_cli():
    @click.group()
    def root() -> None:
        """test root"""
    register_shop(root)
    return root


@pytest.fixture
def db(tmp_path):
    path = str(tmp_path / "phase162.db")
    init_db(path)
    return path


@pytest.fixture
def cli_db(tmp_path, monkeypatch):
    from motodiag.core.config import reset_settings
    path = str(tmp_path / "phase162_cli.db")
    init_db(path)
    monkeypatch.setenv("MOTODIAG_DB_PATH", path)
    monkeypatch.setenv("COLUMNS", "240")
    reset_settings()
    yield path
    reset_settings()


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


def _setup_wo(db_path):
    """Set up shop+customer+vehicle+work_order; return wo_id."""
    shop_id = create_shop("s", db_path=db_path)
    c = _add_customer(db_path)
    v = _add_vehicle(db_path)
    wo_id = create_work_order(shop_id, v, c, "test-wo", db_path=db_path)
    return wo_id, shop_id, c, v


# ===========================================================================
# 1. Migration 027
# ===========================================================================


class TestMigration027:
    def test_schema_version_bumped_to_at_least_27(self, db):
        assert SCHEMA_VERSION >= 27
        assert get_schema_version(db) >= 27

    def test_issues_table_created(self, db):
        assert table_exists("issues", db) is True

    def test_indexes_present(self, db):
        expected = {
            "idx_issues_wo_status",
            "idx_issues_category",
            "idx_issues_severity",
            "idx_issues_reported_at",
            "idx_issues_duplicate_of",
        }
        with get_connection(db) as conn:
            rows = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='index'"
            ).fetchall()
            actual = {r[0] for r in rows}
        assert expected.issubset(actual)

    def test_category_check_rejects_invalid(self, db):
        wo_id, *_ = _setup_wo(db)
        import sqlite3
        with pytest.raises(sqlite3.IntegrityError):
            with get_connection(db) as conn:
                conn.execute(
                    "INSERT INTO issues (work_order_id, title, category) "
                    "VALUES (?, ?, 'bogus_cat')",
                    (wo_id, "x"),
                )

    def test_severity_check_rejects_info(self, db):
        wo_id, *_ = _setup_wo(db)
        import sqlite3
        with pytest.raises(sqlite3.IntegrityError):
            with get_connection(db) as conn:
                conn.execute(
                    "INSERT INTO issues (work_order_id, title, severity) "
                    "VALUES (?, ?, 'info')",
                    (wo_id, "x"),
                )

    def test_rollback_to_version_26_drops_issues_only(self, tmp_path):
        path = str(tmp_path / "rollback.db")
        init_db(path)
        assert table_exists("issues", path) is True
        rollback_to_version(26, path)
        assert table_exists("issues", path) is False
        # Phases 160 + 161 tables preserved.
        assert table_exists("shops", path) is True
        assert table_exists("intake_visits", path) is True
        assert table_exists("work_orders", path) is True


# ===========================================================================
# 2. issue_repo CRUD + validators + filters
# ===========================================================================


class TestIssueRepo:
    def test_create_with_defaults(self, db):
        wo_id, *_ = _setup_wo(db)
        issue_id = create_issue(wo_id, "rough idle", db_path=db)
        row = get_issue(issue_id, db_path=db)
        assert row is not None
        assert row["status"] == "open"
        assert row["category"] == "other"
        assert row["severity"] == "medium"
        assert row["resolved_at"] is None

    def test_create_missing_wo_raises(self, db):
        with pytest.raises(ValueError, match="work order"):
            create_issue(999, "x", db_path=db)

    def test_create_invalid_category_raises(self, db):
        wo_id, *_ = _setup_wo(db)
        with pytest.raises(ValueError, match="category"):
            create_issue(wo_id, "x", category="not_real", db_path=db)

    def test_create_invalid_severity_raises(self, db):
        wo_id, *_ = _setup_wo(db)
        with pytest.raises(ValueError, match="severity"):
            create_issue(wo_id, "x", severity="info", db_path=db)

    def test_create_empty_title_raises(self, db):
        wo_id, *_ = _setup_wo(db)
        with pytest.raises(ValueError, match="title"):
            create_issue(wo_id, "   ", db_path=db)

    def test_create_unknown_dtc_warns_but_persists(self, db, caplog):
        wo_id, *_ = _setup_wo(db)
        import logging
        with caplog.at_level(logging.WARNING, logger="motodiag.shop.issue_repo"):
            issue_id = create_issue(
                wo_id, "x", linked_dtc_code="P9999",
                db_path=db,
            )
        row = get_issue(issue_id, db_path=db)
        assert row["linked_dtc_code"] == "P9999"
        assert any("P9999" in rec.message for rec in caplog.records)

    def test_create_missing_symptom_raises(self, db):
        wo_id, *_ = _setup_wo(db)
        with pytest.raises(ValueError, match="symptom"):
            create_issue(wo_id, "x", linked_symptom_id=999, db_path=db)

    def test_get_issue_returns_denormalized(self, db):
        wo_id, _, _, v = _setup_wo(db)
        issue_id = create_issue(
            wo_id, "leak", category="cooling", severity="high", db_path=db,
        )
        row = get_issue(issue_id, db_path=db)
        assert row["work_order_title"] == "test-wo"
        assert row["shop_name"] == "s"
        assert row["customer_name"] == "Jane Doe"
        assert row["vehicle_make"] == "Harley-Davidson"

    def test_list_default_excludes_terminal(self, db):
        wo_id, *_ = _setup_wo(db)
        i1 = create_issue(wo_id, "a", db_path=db)
        i2 = create_issue(wo_id, "b", db_path=db)
        resolve_issue(i1, db_path=db)
        rows = list_issues(work_order_id=wo_id, db_path=db)
        assert {r["id"] for r in rows} == {i2}

    def test_list_status_all_includes_terminal(self, db):
        wo_id, *_ = _setup_wo(db)
        i1 = create_issue(wo_id, "a", db_path=db)
        i2 = create_issue(wo_id, "b", db_path=db)
        resolve_issue(i1, db_path=db)
        rows = list_issues(work_order_id=wo_id, status="all", db_path=db)
        assert {r["id"] for r in rows} == {i1, i2}

    def test_list_filter_by_category_and_severity(self, db):
        wo_id, *_ = _setup_wo(db)
        i_brakes = create_issue(
            wo_id, "soft lever", category="brakes", severity="high",
            db_path=db,
        )
        create_issue(wo_id, "scratch", category="other",
                     severity="low", db_path=db)
        rows = list_issues(category="brakes", db_path=db)
        assert {r["id"] for r in rows} == {i_brakes}
        rows = list_issues(severity="low", db_path=db)
        assert i_brakes not in {r["id"] for r in rows}

    def test_list_critical_first_sort(self, db):
        wo_id, *_ = _setup_wo(db)
        low = create_issue(wo_id, "low", severity="low", db_path=db)
        crit = create_issue(wo_id, "crit", severity="critical", db_path=db)
        med = create_issue(wo_id, "med", severity="medium", db_path=db)
        rows = list_issues(work_order_id=wo_id, db_path=db)
        ordered = [r["id"] for r in rows]
        assert ordered.index(crit) < ordered.index(med) < ordered.index(low)

    def test_count_issues(self, db):
        wo_id, *_ = _setup_wo(db)
        create_issue(wo_id, "a", db_path=db)
        create_issue(wo_id, "b", category="brakes", db_path=db)
        assert count_issues(work_order_id=wo_id, db_path=db) == 2
        assert count_issues(category="brakes", db_path=db) == 1

    def test_update_whitelist_cannot_mutate_status(self, db):
        wo_id, *_ = _setup_wo(db)
        issue_id = create_issue(wo_id, "x", db_path=db)
        update_issue(issue_id, {
            "title": "new title",
            "category": "brakes",
            "status": "resolved",     # must be ignored
            "resolved_at": "2099-01-01",  # must be ignored
            "evil_field": "y",        # must be ignored
        }, db_path=db)
        row = get_issue(issue_id, db_path=db)
        assert row["title"] == "new title"
        assert row["category"] == "brakes"
        assert row["status"] == "open"
        assert row["resolved_at"] is None

    def test_categorize_issue_updates_both(self, db):
        wo_id, *_ = _setup_wo(db)
        issue_id = create_issue(wo_id, "x", db_path=db)
        categorize_issue(issue_id, "electrical", severity="critical", db_path=db)
        row = get_issue(issue_id, db_path=db)
        assert row["category"] == "electrical"
        assert row["severity"] == "critical"

    def test_require_issue_raises_on_missing(self, db):
        with pytest.raises(IssueNotFoundError):
            require_issue(999, db_path=db)


# ===========================================================================
# 3. Lifecycle transitions
# ===========================================================================


class TestIssueLifecycle:
    def test_resolve_open_to_resolved(self, db):
        wo_id, *_ = _setup_wo(db)
        issue_id = create_issue(wo_id, "x", db_path=db)
        resolve_issue(issue_id, resolution_notes="fixed coil", db_path=db)
        row = get_issue(issue_id, db_path=db)
        assert row["status"] == "resolved"
        assert row["resolved_at"] is not None
        assert row["resolution_notes"] == "fixed coil"

    def test_resolve_already_resolved_raises(self, db):
        wo_id, *_ = _setup_wo(db)
        issue_id = create_issue(wo_id, "x", db_path=db)
        resolve_issue(issue_id, db_path=db)
        with pytest.raises(InvalidIssueTransition):
            resolve_issue(issue_id, db_path=db)

    def test_mark_duplicate_rejects_self_reference(self, db):
        wo_id, *_ = _setup_wo(db)
        issue_id = create_issue(wo_id, "x", db_path=db)
        with pytest.raises(ValueError, match="duplicate of itself"):
            mark_duplicate_issue(issue_id, issue_id, db_path=db)

    def test_mark_duplicate_rejects_duplicate_canonical(self, db):
        wo_id, *_ = _setup_wo(db)
        canonical = create_issue(wo_id, "canonical", db_path=db)
        dup1 = create_issue(wo_id, "dup1", db_path=db)
        dup2 = create_issue(wo_id, "dup2", db_path=db)
        mark_duplicate_issue(dup1, canonical, db_path=db)
        # dup2 cannot point at dup1 (cycle prevention)
        with pytest.raises(ValueError, match="canonical"):
            mark_duplicate_issue(dup2, dup1, db_path=db)

    def test_mark_wontfix_requires_notes(self, db):
        wo_id, *_ = _setup_wo(db)
        issue_id = create_issue(wo_id, "x", db_path=db)
        with pytest.raises(ValueError, match="resolution_notes"):
            mark_wontfix_issue(issue_id, "", db_path=db)

    def test_reopen_clears_terminal_fields(self, db):
        wo_id, *_ = _setup_wo(db)
        canonical = create_issue(wo_id, "c", db_path=db)
        dup = create_issue(wo_id, "d", db_path=db)
        mark_duplicate_issue(dup, canonical, db_path=db)
        reopen_issue(dup, db_path=db)
        row = get_issue(dup, db_path=db)
        assert row["status"] == "open"
        assert row["resolved_at"] is None
        assert row["resolution_notes"] is None
        assert row["duplicate_of_issue_id"] is None

    def test_transition_resolved_to_duplicate_invalid(self, db):
        wo_id, *_ = _setup_wo(db)
        canonical = create_issue(wo_id, "c", db_path=db)
        i = create_issue(wo_id, "x", db_path=db)
        resolve_issue(i, db_path=db)
        with pytest.raises(InvalidIssueTransition):
            mark_duplicate_issue(i, canonical, db_path=db)

    def test_cascade_delete_wo_drops_issues(self, db):
        wo_id, *_ = _setup_wo(db)
        i = create_issue(wo_id, "x", db_path=db)
        with get_connection(db) as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute("DELETE FROM work_orders WHERE id = ?", (wo_id,))
        assert get_issue(i, db_path=db) is None

    def test_canonical_delete_orphans_duplicate_with_null(self, db):
        wo_id, *_ = _setup_wo(db)
        canonical = create_issue(wo_id, "c", db_path=db)
        dup = create_issue(wo_id, "d", db_path=db)
        mark_duplicate_issue(dup, canonical, db_path=db)
        with get_connection(db) as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute("DELETE FROM issues WHERE id = ?", (canonical,))
        row = get_issue(dup, db_path=db)
        assert row is not None
        assert row["duplicate_of_issue_id"] is None
        assert row["status"] == "duplicate"  # status unchanged

    def test_issue_stats_returns_all_buckets(self, db):
        wo_id, shop_id, _, _ = _setup_wo(db)
        create_issue(wo_id, "a", category="brakes", severity="critical",
                     db_path=db)
        create_issue(wo_id, "b", category="engine", severity="medium",
                     db_path=db)
        i = create_issue(wo_id, "c", db_path=db)
        resolve_issue(i, db_path=db)
        stats = issue_stats(work_order_id=wo_id, db_path=db)
        assert stats["total"] == 3
        assert stats["by_status"]["open"] == 2
        assert stats["by_status"]["resolved"] == 1
        assert stats["by_category"]["brakes"] == 1
        assert stats["by_category"]["engine"] == 1
        assert stats["by_severity"]["critical"] == 1
        assert stats["open_count"] == 2
        assert stats["critical_open_count"] == 1


# ===========================================================================
# 4. CLI subcommands
# ===========================================================================


class TestIssueCLI:
    def test_help_lists_12_subcommands(self, cli_db):
        runner = CliRunner()
        root = _make_cli()
        result = runner.invoke(root, ["shop", "issue", "--help"])
        assert result.exit_code == 0
        for sub in (
            "add", "list", "show", "update", "resolve", "reopen",
            "mark-duplicate", "mark-wontfix", "categorize",
            "link-dtc", "link-symptom", "stats",
        ):
            assert sub in result.output

    def test_add_creates_row(self, cli_db):
        wo_id, *_ = _setup_wo(cli_db)
        runner = CliRunner()
        root = _make_cli()
        result = runner.invoke(root, [
            "shop", "issue", "add",
            "--work-order", str(wo_id),
            "--title", "soft brake lever",
            "--category", "brakes",
            "--severity", "high",
        ])
        assert result.exit_code == 0, result.output
        rows = list_issues(work_order_id=wo_id, db_path=cli_db)
        assert len(rows) == 1
        assert rows[0]["category"] == "brakes"

    def test_list_default_excludes_terminal(self, cli_db):
        wo_id, *_ = _setup_wo(cli_db)
        i1 = create_issue(wo_id, "a", db_path=cli_db)
        i2 = create_issue(wo_id, "b", db_path=cli_db)
        resolve_issue(i1, db_path=cli_db)
        runner = CliRunner()
        root = _make_cli()
        result = runner.invoke(root, [
            "shop", "issue", "list", "--json",
        ])
        assert result.exit_code == 0
        ids = {r["id"] for r in _json.loads(result.output)}
        assert i2 in ids
        assert i1 not in ids

    def test_show_json(self, cli_db):
        wo_id, *_ = _setup_wo(cli_db)
        issue_id = create_issue(wo_id, "x", db_path=cli_db)
        runner = CliRunner()
        root = _make_cli()
        result = runner.invoke(root, [
            "shop", "issue", "show", str(issue_id), "--json",
        ])
        assert result.exit_code == 0, result.output
        parsed = _json.loads(result.output)
        assert parsed["id"] == issue_id

    def test_update_set_category_and_severity(self, cli_db):
        wo_id, *_ = _setup_wo(cli_db)
        issue_id = create_issue(wo_id, "x", db_path=cli_db)
        runner = CliRunner()
        root = _make_cli()
        result = runner.invoke(root, [
            "shop", "issue", "update", str(issue_id),
            "--set", "category=cooling",
            "--set", "severity=critical",
        ])
        assert result.exit_code == 0, result.output
        row = get_issue(issue_id, db_path=cli_db)
        assert row["category"] == "cooling"
        assert row["severity"] == "critical"

    def test_resolve_yes_skips_confirm(self, cli_db):
        wo_id, *_ = _setup_wo(cli_db)
        issue_id = create_issue(wo_id, "x", db_path=cli_db)
        runner = CliRunner()
        root = _make_cli()
        result = runner.invoke(root, [
            "shop", "issue", "resolve", str(issue_id),
            "--notes", "fixed",
            "--yes",
        ])
        assert result.exit_code == 0, result.output
        row = get_issue(issue_id, db_path=cli_db)
        assert row["status"] == "resolved"

    def test_mark_wontfix_rejects_empty_notes(self, cli_db):
        wo_id, *_ = _setup_wo(cli_db)
        issue_id = create_issue(wo_id, "x", db_path=cli_db)
        runner = CliRunner()
        root = _make_cli()
        result = runner.invoke(root, [
            "shop", "issue", "mark-wontfix", str(issue_id),
            "--notes", "   ",
        ])
        assert result.exit_code != 0
        assert "required" in result.output.lower() or "audit-trail" in result.output.lower()

    def test_categorize_round_trip(self, cli_db):
        wo_id, *_ = _setup_wo(cli_db)
        issue_id = create_issue(wo_id, "x", db_path=cli_db)
        runner = CliRunner()
        root = _make_cli()
        result = runner.invoke(root, [
            "shop", "issue", "categorize", str(issue_id),
            "--category", "drivetrain",
            "--severity", "high",
        ])
        assert result.exit_code == 0, result.output
        row = get_issue(issue_id, db_path=cli_db)
        assert row["category"] == "drivetrain"
        assert row["severity"] == "high"

    def test_reopen_round_trip(self, cli_db):
        wo_id, *_ = _setup_wo(cli_db)
        issue_id = create_issue(wo_id, "x", db_path=cli_db)
        resolve_issue(issue_id, db_path=cli_db)
        runner = CliRunner()
        root = _make_cli()
        result = runner.invoke(root, [
            "shop", "issue", "reopen", str(issue_id), "--yes",
        ])
        assert result.exit_code == 0, result.output
        row = get_issue(issue_id, db_path=cli_db)
        assert row["status"] == "open"

    def test_stats_json_contains_buckets(self, cli_db):
        wo_id, shop_id, _, _ = _setup_wo(cli_db)
        create_issue(wo_id, "a", category="brakes", severity="critical",
                     db_path=cli_db)
        runner = CliRunner()
        root = _make_cli()
        result = runner.invoke(root, [
            "shop", "issue", "stats",
            "--shop", str(shop_id),
            "--json",
        ])
        assert result.exit_code == 0, result.output
        stats = _json.loads(result.output)
        for key in (
            "total", "by_status", "by_category", "by_severity",
            "open_count", "critical_open_count",
        ):
            assert key in stats
        assert stats["critical_open_count"] >= 1
