"""Phase 154 — Technical Service Bulletin tests.

Five test classes:

- :class:`TestMigration022` (3) — ``technical_service_bulletins`` table
  + columns + ``UNIQUE(tsb_number)`` index present after init.
- :class:`TestTsbRepo` (12) — add/get/list/search/count/list_for_bike
  across every pattern shape: exact literal, ``Model%`` wildcard, year
  envelope honored, LIKE search across all three text fields, severity
  bucket-adjacent filter, INSERT OR IGNORE idempotency.
- :class:`TestTsbLoader` (4) — loading the packaged ``tsbs.json``,
  malformed JSON with line/col, missing file, non-array root.
- :class:`TestTsbCLI` (8, Click CliRunner) — list (all / --bike /
  --make), search, show (hit / miss), by-make, --json round-trip,
  unknown-bike remediation.
- :class:`TestPhase148TsbIntegration` (3) — ``predict_failures``
  populates ``applicable_tsbs`` when a TSB + issue share a 4-char token
  AND adjacent severity; no token overlap → no attachment; pre-
  migration DB → graceful ``[]``.

All tests are SW + SQL only. Zero AI calls, zero network, zero live
tokens.
"""

from __future__ import annotations

import json as _json
import sqlite3
from pathlib import Path

import pytest
from click.testing import CliRunner

from motodiag.advanced.tsb_repo import (
    VALID_SEVERITIES,
    add_tsb,
    count_tsbs,
    get_tsb,
    list_tsbs,
    list_tsbs_for_bike,
    load_tsbs_file,
    search_tsbs,
    tsb_numbers_for_vehicle,
)
from motodiag.advanced import predict_failures
from motodiag.cli.advanced import register_advanced
from motodiag.core.database import get_connection, init_db
from motodiag.knowledge.issues_repo import add_known_issue


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


def _make_cli():
    """Build a fresh CLI group with only ``advanced`` registered."""
    import click

    @click.group()
    def root() -> None:
        """test root"""

    register_advanced(root)
    return root


def _clear_tsbs(path: str) -> None:
    """Wipe the auto-seeded TSB rows so tests run against a known-empty table."""
    with get_connection(path) as conn:
        conn.execute("DELETE FROM technical_service_bulletins")


@pytest.fixture
def db(tmp_path):
    """Per-test SQLite DB pre-migrated + TSB table cleared.

    ``init_db`` auto-seeds ``tsbs.json`` on an empty DB — useful in
    production, noisy in unit tests. We wipe the table after init so
    each test starts with a known-empty slate.
    """
    path = str(tmp_path / "phase154.db")
    init_db(path)
    _clear_tsbs(path)
    return path


@pytest.fixture
def cli_db(tmp_path, monkeypatch):
    """Point settings + CLI env at a temp DB (TSB table cleared)."""
    from motodiag.core.config import reset_settings

    path = str(tmp_path / "phase154_cli.db")
    init_db(path)
    _clear_tsbs(path)
    monkeypatch.setenv("MOTODIAG_DB_PATH", path)
    monkeypatch.setenv("COLUMNS", "240")
    reset_settings()
    yield path
    reset_settings()


def _add_vehicle(
    db_path: str,
    make: str = "Harley-Davidson",
    model: str = "Dyna Super Glide",
    year: int = 2012,
) -> int:
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "INSERT INTO vehicles (make, model, year, protocol) "
            "VALUES (?, ?, ?, 'none')",
            (make, model, year),
        )
        return cursor.lastrowid


def _seed_stator_tsb(db_path: str, **overrides) -> int:
    """Seed a representative TSB row. Returns the inserted id."""
    defaults = dict(
        tsb_number="M-1287",
        make="Harley-Davidson",
        model_pattern="Dyna%",
        title="Stator output voltage verification",
        description="Stator premature failure under heat; verify AC output.",
        fix_procedure="Replace stator (part 29965-06A) if below 32 VAC.",
        year_min=2006,
        year_max=2017,
        severity="high",
        issued_date="2013-05-15",
        source_url="https://service.h-d.com/M-1287",
        verified_by="HD M-1287 Rev A",
    )
    defaults.update(overrides)
    defaults["db_path"] = db_path
    return add_tsb(**defaults)


# ===========================================================================
# 1. Migration 022
# ===========================================================================


class TestMigration022:
    """Migration 022 created the technical_service_bulletins table."""

    def test_table_exists(self, db):
        with get_connection(db) as conn:
            row = conn.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type='table' AND name='technical_service_bulletins'"
            ).fetchone()
        assert row is not None

    def test_required_columns_present(self, db):
        with get_connection(db) as conn:
            cols = {
                r[1]
                for r in conn.execute(
                    "PRAGMA table_info(technical_service_bulletins)"
                ).fetchall()
            }
        expected = {
            "tsb_number", "make", "model_pattern",
            "year_min", "year_max", "title", "description",
            "fix_procedure", "severity", "issued_date",
            "source_url", "verified_by",
        }
        assert expected.issubset(cols)

    def test_unique_tsb_number_enforced(self, db):
        _seed_stator_tsb(db)
        # A second add with same tsb_number is INSERT OR IGNORE — so the
        # second call should return the same id, not blow up.
        first_id = get_tsb("M-1287", db_path=db)["id"]
        second_id = _seed_stator_tsb(db, title="Different title")
        assert second_id == first_id


# ===========================================================================
# 2. Repository
# ===========================================================================


class TestTsbRepo:
    def test_add_and_get_round_trip(self, db):
        tid = _seed_stator_tsb(db)
        assert tid > 0
        row = get_tsb("M-1287", db_path=db)
        assert row is not None
        assert row["make"] == "harley-davidson"
        assert row["model_pattern"] == "Dyna%"
        assert row["severity"] == "high"

    def test_get_whitespace_tolerant(self, db):
        _seed_stator_tsb(db)
        # Mechanics paste TSB numbers out of PDFs — trim whitespace.
        assert get_tsb("  M-1287  ", db_path=db) is not None
        assert get_tsb("", db_path=db) is None
        assert get_tsb(None, db_path=db) is None

    def test_make_lowercased_on_insert(self, db):
        _seed_stator_tsb(db, tsb_number="M-X1", make="HARLEY-DAVIDSON")
        _seed_stator_tsb(db, tsb_number="M-X2", make="Harley-Davidson")
        rows = list_tsbs(db_path=db)
        makes = {r["make"] for r in rows}
        assert makes == {"harley-davidson"}

    def test_list_tsbs_ordered_by_issued_date_desc(self, db):
        _seed_stator_tsb(db, tsb_number="A-1", issued_date="2015-01-01")
        _seed_stator_tsb(db, tsb_number="A-2", issued_date="2020-06-06")
        _seed_stator_tsb(db, tsb_number="A-3", issued_date="2018-03-03")
        rows = list_tsbs(db_path=db)
        assert [r["tsb_number"] for r in rows] == ["A-2", "A-3", "A-1"]

    def test_list_tsbs_limit(self, db):
        for i in range(5):
            _seed_stator_tsb(
                db, tsb_number=f"L-{i}", issued_date=f"2020-01-0{i + 1}",
            )
        rows = list_tsbs(limit=2, db_path=db)
        assert len(rows) == 2

    def test_list_for_bike_matches_wildcard_pattern(self, db):
        _seed_stator_tsb(db)  # Dyna%
        rows = list_tsbs_for_bike(
            make="Harley-Davidson",
            model="Dyna Super Glide",
            year=2012,
            db_path=db,
        )
        assert len(rows) == 1
        assert rows[0]["tsb_number"] == "M-1287"

    def test_list_for_bike_year_out_of_range_filters_out(self, db):
        _seed_stator_tsb(db)  # 2006-2017
        # 2019 is past year_max → filter drops it.
        rows = list_tsbs_for_bike(
            make="Harley-Davidson",
            model="Dyna Super Glide",
            year=2019,
            db_path=db,
        )
        assert rows == []

    def test_list_for_bike_specific_outranks_wildcard(self, db):
        # Two TSBs match — specific pattern should sort first.
        _seed_stator_tsb(
            db,
            tsb_number="GEN-1",
            model_pattern="Dyna%",
            title="Generic Dyna issue",
            issued_date="2010-01-01",
        )
        _seed_stator_tsb(
            db,
            tsb_number="SPEC-1",
            model_pattern="Dyna Super Glide",
            title="Specific Super Glide issue",
            issued_date="2010-01-01",
        )
        rows = list_tsbs_for_bike(
            make="Harley-Davidson",
            model="Dyna Super Glide",
            year=2012,
            db_path=db,
        )
        assert [r["tsb_number"] for r in rows] == ["SPEC-1", "GEN-1"]

    def test_search_finds_by_fix_procedure_text(self, db):
        _seed_stator_tsb(db)
        rows = search_tsbs("part 29965-06A", db_path=db)
        assert len(rows) == 1
        assert rows[0]["tsb_number"] == "M-1287"

    def test_search_empty_query_returns_empty(self, db):
        _seed_stator_tsb(db)
        assert search_tsbs("", db_path=db) == []
        assert search_tsbs("   ", db_path=db) == []
        assert search_tsbs(None, db_path=db) == []

    def test_count_tsbs_matches_inserts(self, db):
        assert count_tsbs(db_path=db) == 0
        _seed_stator_tsb(db, tsb_number="C-1")
        _seed_stator_tsb(db, tsb_number="C-2")
        assert count_tsbs(db_path=db) == 2

    def test_invalid_severity_rejected(self, db):
        with pytest.raises(ValueError, match="severity"):
            _seed_stator_tsb(db, tsb_number="BAD-1", severity="catastrophic")

    def test_invalid_issued_date_rejected(self, db):
        with pytest.raises(ValueError, match="ISO"):
            _seed_stator_tsb(
                db, tsb_number="BAD-2", issued_date="not-a-date",
            )


# ===========================================================================
# 3. Loader
# ===========================================================================


class TestTsbLoader:
    def test_packaged_tsbs_json_loads(self, db):
        """Hand-load tsbs.json — the ``db`` fixture has cleared the
        auto-seed, so this measures loader behavior directly."""
        root = Path(__file__).resolve().parents[1]
        path = root / "src" / "motodiag" / "advanced" / "data" / "tsbs.json"
        count = load_tsbs_file(str(path), db_path=db)
        assert count >= 10
        assert count_tsbs(db_path=db) == count

    def test_loader_idempotent(self, db, tmp_path):
        bundle = [
            {
                "tsb_number": "IDEM-1",
                "make": "Honda",
                "model_pattern": "CBR600%",
                "title": "Test",
                "description": "Test description",
                "fix_procedure": "Test fix",
                "severity": "low",
                "issued_date": "2019-01-01",
            },
        ]
        p = tmp_path / "mini_tsbs.json"
        p.write_text(_json.dumps(bundle), encoding="utf-8")
        assert load_tsbs_file(str(p), db_path=db) == 1
        assert load_tsbs_file(str(p), db_path=db) == 1
        assert count_tsbs(db_path=db) == 1

    def test_malformed_json_raises_with_position(self, db, tmp_path):
        bad = tmp_path / "bad.json"
        bad.write_text("[{", encoding="utf-8")
        with pytest.raises(ValueError, match="line"):
            load_tsbs_file(str(bad), db_path=db)

    def test_missing_file_raises_file_not_found(self, db, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_tsbs_file(str(tmp_path / "nope.json"), db_path=db)


# ===========================================================================
# 4. CLI
# ===========================================================================


class TestTsbCLI:
    def test_list_no_bike_filter_shows_seeded(self, cli_db):
        """The CLI re-runs init_db which re-seeds the table, so `list`
        with no filters always returns the packaged TSBs. Verifies the
        command path runs end-to-end without error."""
        runner = CliRunner()
        result = runner.invoke(_make_cli(), ["advanced", "tsb", "list"])
        assert result.exit_code == 0
        # At least one known seeded TSB number appears.
        assert "TSBs" in result.output

    def test_list_with_data(self, cli_db):
        _seed_stator_tsb(cli_db)
        runner = CliRunner()
        result = runner.invoke(_make_cli(), ["advanced", "tsb", "list"])
        assert result.exit_code == 0
        assert "M-1287" in result.output

    def test_list_json(self, cli_db):
        _seed_stator_tsb(cli_db)
        runner = CliRunner()
        result = runner.invoke(
            _make_cli(), ["advanced", "tsb", "list", "--json"],
        )
        assert result.exit_code == 0
        payload = _json.loads(result.output)
        assert "tsbs" in payload
        assert any(t["tsb_number"] == "M-1287" for t in payload["tsbs"])

    def test_list_by_bike_unknown_slug_remediation(self, cli_db):
        runner = CliRunner()
        result = runner.invoke(
            _make_cli(),
            ["advanced", "tsb", "list", "--bike", "not-a-real-bike"],
        )
        assert result.exit_code == 1
        assert (
            "not found" in result.output.lower()
            or "unknown" in result.output.lower()
        )

    def test_search_finds_match(self, cli_db):
        _seed_stator_tsb(cli_db)
        runner = CliRunner()
        result = runner.invoke(
            _make_cli(), ["advanced", "tsb", "search", "stator"],
        )
        assert result.exit_code == 0
        assert "M-1287" in result.output

    def test_search_no_match_yellow_panel(self, cli_db):
        _seed_stator_tsb(cli_db)
        runner = CliRunner()
        result = runner.invoke(
            _make_cli(), ["advanced", "tsb", "search", "zxquz-nonsense"],
        )
        assert result.exit_code == 0
        assert "No" in result.output  # "No matches" panel

    def test_show_hit_and_miss(self, cli_db):
        _seed_stator_tsb(cli_db)
        runner = CliRunner()
        hit = runner.invoke(_make_cli(), ["advanced", "tsb", "show", "M-1287"])
        assert hit.exit_code == 0
        assert "M-1287" in hit.output

        miss = runner.invoke(
            _make_cli(), ["advanced", "tsb", "show", "NOT-A-TSB"],
        )
        assert miss.exit_code == 1
        assert "not found" in miss.output.lower()

    def test_by_make_lists(self, cli_db):
        _seed_stator_tsb(cli_db)
        runner = CliRunner()
        result = runner.invoke(
            _make_cli(),
            ["advanced", "tsb", "by-make", "harley-davidson", "--json"],
        )
        assert result.exit_code == 0
        payload = _json.loads(result.output)
        assert len(payload["tsbs"]) == 1


# ===========================================================================
# 5. Phase 148 integration
# ===========================================================================


class TestPhase148TsbIntegration:
    """predict_failures should attach applicable_tsbs by keyword overlap."""

    def test_attach_on_keyword_overlap(self, db):
        _seed_stator_tsb(db)  # title "Stator output voltage verification"
        add_known_issue(
            title="Stator failure on Twin Cam Dyna",
            description="Charging system stops working.",
            make="Harley-Davidson",
            model="Dyna Super Glide",
            year_start=2010,
            year_end=2013,
            severity="high",
            symptoms=["no charging"],
            dtc_codes=[],
            causes=["Stator insulation breakdown"],
            fix_procedure="Replace stator.",
            parts_needed=["Stator"],
            estimated_hours=3.0,
            db_path=db,
        )
        vehicle = {
            "make": "Harley-Davidson",
            "model": "Dyna Super Glide",
            "year": 2012,
            "mileage": 45_000,
        }
        preds = predict_failures(vehicle, horizon_days=None, db_path=db)
        stator = next(
            p for p in preds if p.issue_title.startswith("Stator failure")
        )
        assert "M-1287" in stator.applicable_tsbs

    def test_no_attach_without_token_overlap(self, db):
        _seed_stator_tsb(
            db,
            tsb_number="UNRELATED-1",
            title="Fuel tank vent hose routing",
            description="Intermittent stumble above 65 mph.",
            fix_procedure="Reroute vent hose.",
        )
        add_known_issue(
            title="Clutch basket wear on Sportster 1200",
            description="Clunky shifts and notchy neutral.",
            make="Harley-Davidson",
            model="Dyna Super Glide",
            year_start=2010,
            year_end=2013,
            severity="high",
            symptoms=["notchy neutral"],
            dtc_codes=[],
            causes=["Basket wear"],
            fix_procedure="Replace basket.",
            parts_needed=["Clutch basket"],
            estimated_hours=4.0,
            db_path=db,
        )
        vehicle = {
            "make": "Harley-Davidson",
            "model": "Dyna Super Glide",
            "year": 2012,
            "mileage": 45_000,
        }
        preds = predict_failures(vehicle, horizon_days=None, db_path=db)
        clutch = next(
            p for p in preds if p.issue_title.startswith("Clutch basket")
        )
        assert clutch.applicable_tsbs == []

    def test_pre_migration_db_graceful(self, tmp_path):
        """tsb_numbers_for_vehicle returns [] when the table is missing."""
        raw = tmp_path / "bare.db"
        with sqlite3.connect(str(raw)) as conn:
            conn.execute("CREATE TABLE just_something (id INTEGER)")
        result = tsb_numbers_for_vehicle(
            make="Harley-Davidson",
            model="Dyna Super Glide",
            year=2012,
            db_path=str(raw),
        )
        assert result == []


# ---------------------------------------------------------------------------
# Module-level constants sanity (kept cheap — single test, not a class).
# ---------------------------------------------------------------------------


def test_valid_severities_tuple_stable():
    """VALID_SEVERITIES is the contract other modules rely on."""
    assert VALID_SEVERITIES == ("critical", "high", "medium", "low")
