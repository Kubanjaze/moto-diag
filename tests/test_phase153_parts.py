"""Phase 153 — Parts cross-reference tests.

Four test classes across ~30 tests:

- :class:`TestMigration021` (4) — schema-version bump, 2 tables + 4
  indexes, child-first rollback, CHECK constraints enforced.
- :class:`TestPartsRepo` (10) — CRUD, INSERT OR IGNORE, fuzzy search,
  cascade delete, xref validation + ranking, lookup_typical_cost.
- :class:`TestPartsLoader` (6) — file loaders, seed_all idempotent,
  malformed JSON reporting, unknown xref slug, dependency order.
- :class:`TestPartsCLI` (10, CliRunner) — search, xref, show, seed
  commands plus Phase 148 predict regression when seeded.

All tests are SW + SQL only. Zero AI calls, zero network.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from motodiag.advanced import parts_loader as pl
from motodiag.advanced import parts_repo as pr
from motodiag.cli.advanced import register_advanced
from motodiag.core.database import (
    get_connection,
    get_schema_version,
    init_db,
    table_exists,
)
from motodiag.core.migrations import (
    get_migration_by_version,
    rollback_migration,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def db_path(tmp_path):
    """Per-test SQLite DB pre-migrated to the latest schema."""
    path = str(tmp_path / "phase153.db")
    init_db(path)
    return path


@pytest.fixture
def seeded_db(tmp_path):
    """Per-test DB preloaded with a small hand-rolled parts fixture set."""
    path = str(tmp_path / "phase153_seeded.db")
    init_db(path)
    # Three OEM parts + three aftermarket crossrefs.
    pr.add_part(
        slug="hd-tens-oem", oem_part_number="HD-26499-08",
        brand="Harley-Davidson",
        description="Twin Cam 88 hydraulic cam tensioner (OEM)",
        category="cam-tensioner",
        make="Harley-Davidson", model_pattern="%",
        year_min=1999, year_max=2017,
        typical_cost_cents=8999, db_path=path,
    )
    pr.add_part(
        slug="feuling-tens", oem_part_number="4124",
        brand="Feuling",
        description="HP+ cam tensioner upgrade",
        category="cam-tensioner",
        make="Harley-Davidson", model_pattern="%",
        year_min=1999, year_max=2017,
        typical_cost_cents=12995, db_path=path,
    )
    pr.add_part(
        slug="sands-tens", oem_part_number="33-4220",
        brand="S&S Cycle",
        description="S&S cam tensioner crossref for TC88/96/103",
        category="cam-tensioner",
        make="Harley-Davidson", model_pattern="%",
        year_min=1999, year_max=2017,
        typical_cost_cents=11495, db_path=path,
    )
    pr.add_part(
        slug="honda-filter-oem", oem_part_number="15410-MCJ-505",
        brand="Honda",
        description="Honda CBR oil filter (OEM)",
        category="oil-filter",
        make="Honda", model_pattern="%",
        year_min=2001, year_max=2024,
        typical_cost_cents=999, db_path=path,
    )
    pr.add_part(
        slug="kn-filter-honda", oem_part_number="KN-204",
        brand="K&N",
        description="K&N oil filter for Honda CBR (crossref 15410-MCJ-505)",
        category="oil-filter",
        make="Honda", model_pattern="%",
        year_min=2001, year_max=2024,
        typical_cost_cents=1149, db_path=path,
    )
    pr.add_xref(
        "hd-tens-oem", "feuling-tens",
        equivalence_rating=5,
        notes="Direct drop-in",
        source_url="https://example/feuling",
        db_path=path,
    )
    pr.add_xref(
        "hd-tens-oem", "sands-tens",
        equivalence_rating=4,
        notes="Drop-in, minor spring diff",
        source_url="https://example/sands",
        db_path=path,
    )
    pr.add_xref(
        "honda-filter-oem", "kn-filter-honda",
        equivalence_rating=5,
        notes="Identical fitment",
        source_url="https://example/kn",
        db_path=path,
    )
    return path


def _make_cli():
    """Build a fresh CLI group with only `advanced` registered."""
    import click

    @click.group()
    def root() -> None:
        """test root"""

    register_advanced(root)
    return root


@pytest.fixture
def cli_db(tmp_path, monkeypatch):
    """Point settings + CLI paths at a temp DB."""
    from motodiag.core.config import reset_settings

    path = str(tmp_path / "phase153_cli.db")
    init_db(path)
    monkeypatch.setenv("MOTODIAG_DB_PATH", path)
    monkeypatch.setenv("COLUMNS", "240")
    reset_settings()
    yield path
    reset_settings()


# ---------------------------------------------------------------------------
# TestMigration021
# ---------------------------------------------------------------------------


class TestMigration021:
    """Migration 021 applies cleanly, creates 2 tables + 4 indexes, rolls back."""

    def test_schema_version_at_least_21(self, db_path):
        # Phase 153 bumps to 21; later phases may bump higher — assert >=.
        assert get_schema_version(db_path) >= 21

    def test_two_tables_plus_four_indexes(self, db_path):
        assert table_exists("parts", db_path) is True
        assert table_exists("parts_xref", db_path) is True
        expected_indexes = {
            "idx_parts_oem",
            "idx_parts_make_cat",
            "idx_parts_slug",
            "idx_xref_oem",
        }
        with get_connection(db_path) as conn:
            cur = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='index'"
            )
            actual = {row[0] for row in cur.fetchall()}
        assert expected_indexes.issubset(actual), (
            f"missing indexes: {expected_indexes - actual}"
        )

    def test_rollback_drops_tables_child_first(self, tmp_path):
        """Rollback must drop parts_xref before parts to respect FK."""
        path = str(tmp_path / "rollback.db")
        init_db(path)
        assert table_exists("parts", path) is True
        migration = get_migration_by_version(21)
        assert migration is not None
        rollback_migration(migration, path)
        assert table_exists("parts_xref", path) is False
        assert table_exists("parts", path) is False

    def test_check_constraints_active(self, db_path):
        """Self-xref, negative price, and OOR rating rejected at the DB."""
        # Two parts so we can try to force a self-xref via direct SQL.
        pr.add_part(
            slug="a", oem_part_number="A", brand="B", description="D",
            category="c", make="X", model_pattern="%",
            typical_cost_cents=100, db_path=db_path,
        )
        pr.add_part(
            slug="b", oem_part_number="B", brand="B", description="D",
            category="c", make="X", model_pattern="%",
            typical_cost_cents=100, db_path=db_path,
        )
        with get_connection(db_path) as conn:
            row = conn.execute(
                "SELECT id FROM parts WHERE slug='a'",
            ).fetchone()
            a_id = int(row[0])
        # 1) Self-xref blocked by CHECK(oem != aftermarket)
        import sqlite3
        with pytest.raises(sqlite3.IntegrityError):
            with get_connection(db_path) as conn:
                conn.execute(
                    "INSERT INTO parts_xref "
                    "(oem_part_id, aftermarket_part_id, equivalence_rating) "
                    "VALUES (?, ?, 3)",
                    (a_id, a_id),
                )
        # 2) Negative typical_cost_cents rejected by the repo validator.
        with pytest.raises((TypeError, ValueError)):
            pr.add_part(
                slug="neg", oem_part_number="N", brand="B", description="D",
                category="c", make="X", model_pattern="%",
                typical_cost_cents=-5, db_path=db_path,
            )
        # 3) OOR equivalence_rating rejected by the repo validator.
        with pytest.raises(ValueError):
            pr.add_xref(
                "a", "b", equivalence_rating=6, db_path=db_path,
            )


# ---------------------------------------------------------------------------
# TestPartsRepo
# ---------------------------------------------------------------------------


class TestPartsRepo:
    """CRUD semantics, validation, search, xref, cascade, lookup_typical_cost."""

    def test_add_and_get_roundtrip(self, db_path):
        new_id = pr.add_part(
            slug="p1", oem_part_number="OEM-001", brand="Acme",
            description="Widget", category="widget",
            make="Harley-Davidson", model_pattern="%",
            typical_cost_cents=500, db_path=db_path,
        )
        assert new_id > 0
        row = pr.get_part("p1", db_path=db_path)
        assert row is not None
        assert row["brand"] == "Acme"
        # make is lowercased on insert
        assert row["make"] == "harley-davidson"

    def test_insert_or_ignore_returns_existing_id(self, db_path):
        id1 = pr.add_part(
            slug="dup", oem_part_number="X", brand="A", description="D",
            category="c", make="Honda", model_pattern="%",
            typical_cost_cents=100, db_path=db_path,
        )
        id2 = pr.add_part(
            slug="dup", oem_part_number="Y", brand="Z", description="D2",
            category="c", make="Honda", model_pattern="%",
            typical_cost_cents=999, db_path=db_path,
        )
        assert id1 == id2
        # Original row wins — second insert's data is NOT merged.
        row = pr.get_part("dup", db_path=db_path)
        assert row["brand"] == "A"
        assert row["typical_cost_cents"] == 100

    def test_search_parts_fuzzy_like(self, seeded_db):
        rows = pr.search_parts("tensioner", db_path=seeded_db)
        slugs = {r["slug"] for r in rows}
        # 3 tensioner rows in seeded fixture
        assert {"hd-tens-oem", "feuling-tens", "sands-tens"}.issubset(slugs)

    def test_search_parts_filter_make_category(self, seeded_db):
        # Filter to Honda only — should match only the 2 Honda rows
        rows = pr.search_parts(
            "", make="Honda", category="oil-filter", db_path=seeded_db,
        )
        assert len(rows) == 2
        assert all(r["make"] == "honda" for r in rows)

    def test_add_xref_dup_insert_or_ignore(self, seeded_db):
        # Adding the exact same xref twice returns the same id and does
        # not create a duplicate row.
        id1 = pr.add_xref(
            "hd-tens-oem", "feuling-tens",
            equivalence_rating=5, db_path=seeded_db,
        )
        id2 = pr.add_xref(
            "hd-tens-oem", "feuling-tens",
            equivalence_rating=3, db_path=seeded_db,
        )
        assert id1 == id2
        # Ensure only one row exists for this pair
        with get_connection(seeded_db) as conn:
            count = conn.execute(
                "SELECT COUNT(*) FROM parts_xref x "
                "JOIN parts oem ON oem.id = x.oem_part_id "
                "JOIN parts aft ON aft.id = x.aftermarket_part_id "
                "WHERE oem.slug='hd-tens-oem' AND aft.slug='feuling-tens'",
            ).fetchone()[0]
        assert count == 1

    def test_add_xref_rejects_self(self, db_path):
        pr.add_part(
            slug="s1", oem_part_number="S1", brand="B", description="D",
            category="c", make="X", model_pattern="%",
            typical_cost_cents=100, db_path=db_path,
        )
        with pytest.raises(ValueError, match="self-reference"):
            pr.add_xref("s1", "s1", db_path=db_path)

    def test_get_xrefs_sort_rating_then_cost(self, seeded_db):
        """get_xrefs sorts rating DESC then cost ASC then brand then id."""
        rows = pr.get_xrefs("HD-26499-08", db_path=seeded_db)
        assert len(rows) == 2
        # Rating 5 (Feuling, $129.95) comes before rating 4 (S&S, $114.95)
        assert rows[0]["aftermarket_slug"] == "feuling-tens"
        assert rows[0]["equivalence_rating"] == 5
        assert rows[1]["aftermarket_slug"] == "sands-tens"
        assert rows[1]["equivalence_rating"] == 4

    def test_cascade_delete_removes_xrefs(self, seeded_db):
        # Delete the Honda OEM part — its xref row should cascade.
        with get_connection(seeded_db) as conn:
            before = conn.execute(
                "SELECT COUNT(*) FROM parts_xref",
            ).fetchone()[0]
            assert before == 3
            conn.execute("DELETE FROM parts WHERE slug='honda-filter-oem'")
        with get_connection(seeded_db) as conn:
            after = conn.execute(
                "SELECT COUNT(*) FROM parts_xref",
            ).fetchone()[0]
        # One xref referenced honda-filter-oem → now 2 remain
        assert after == 2

    def test_lookup_typical_cost_hit_and_miss(self, seeded_db):
        # Tier 1: exact OEM match (alphanumeric normalised)
        assert (
            pr.lookup_typical_cost(
                "HD-26499-08", make="Harley-Davidson",
                db_path=seeded_db,
            )
            == 8999
        )
        # Also matches without separators
        assert (
            pr.lookup_typical_cost("HD2649908", db_path=seeded_db)
            == 8999
        )
        # Tier 2: description LIKE
        cost = pr.lookup_typical_cost(
            "cam tensioner", make="Harley-Davidson", db_path=seeded_db,
        )
        assert cost is not None and cost >= 8999
        # Tier 3: category keyword via make
        cost2 = pr.lookup_typical_cost(
            "oil filter", make="Honda", db_path=seeded_db,
        )
        assert cost2 == 999

    def test_lookup_typical_cost_none_on_empty_input(self, seeded_db):
        assert pr.lookup_typical_cost("", db_path=seeded_db) is None
        assert pr.lookup_typical_cost(None, db_path=seeded_db) is None
        # Unknown part — returns None
        assert (
            pr.lookup_typical_cost(
                "Unobtanium 9000", make="Harley-Davidson",
                db_path=seeded_db,
            )
            is None
        )

    def test_equivalence_rating_bounds_and_cost_type(self, db_path):
        pr.add_part(
            slug="a", oem_part_number="A", brand="B", description="D",
            category="c", make="X", model_pattern="%",
            typical_cost_cents=100, db_path=db_path,
        )
        pr.add_part(
            slug="b", oem_part_number="B", brand="B", description="D",
            category="c", make="X", model_pattern="%",
            typical_cost_cents=100, db_path=db_path,
        )
        # Rating below 1 rejected
        with pytest.raises(ValueError):
            pr.add_xref("a", "b", equivalence_rating=0, db_path=db_path)
        # Rating above 5 rejected
        with pytest.raises(ValueError):
            pr.add_xref("a", "b", equivalence_rating=7, db_path=db_path)
        # Float cost rejected via TypeError
        with pytest.raises(TypeError):
            pr.add_part(
                slug="f", oem_part_number="F", brand="B", description="D",
                category="c", make="X", model_pattern="%",
                typical_cost_cents=19.99, db_path=db_path,
            )


# ---------------------------------------------------------------------------
# TestPartsLoader
# ---------------------------------------------------------------------------


class TestPartsLoader:
    """JSON seeder idempotency + error reporting + dependency order."""

    def test_load_parts_file(self, db_path, tmp_path):
        p = tmp_path / "parts.json"
        p.write_text(
            json.dumps([
                {
                    "slug": "t",
                    "oem_part_number": "T-1",
                    "brand": "Acme",
                    "description": "Test widget",
                    "category": "widget",
                    "make": "X",
                    "model_pattern": "%",
                    "typical_cost_cents": 100,
                }
            ]),
            encoding="utf-8",
        )
        n = pl.load_parts_file(p, db_path=db_path)
        assert n == 1
        assert pr.get_part("t", db_path=db_path) is not None

    def test_load_parts_xref_file(self, db_path, tmp_path):
        # Seed the parts first
        pr.add_part(
            slug="a", oem_part_number="A", brand="B", description="D",
            category="c", make="X", model_pattern="%",
            typical_cost_cents=100, db_path=db_path,
        )
        pr.add_part(
            slug="b", oem_part_number="B", brand="B", description="D",
            category="c", make="X", model_pattern="%",
            typical_cost_cents=100, db_path=db_path,
        )
        p = tmp_path / "xref.json"
        p.write_text(
            json.dumps([
                {
                    "oem_slug": "a",
                    "aftermarket_slug": "b",
                    "equivalence_rating": 5,
                    "notes": "test",
                }
            ]),
            encoding="utf-8",
        )
        n = pl.load_parts_xref_file(p, db_path=db_path)
        assert n == 1

    def test_seed_all_idempotent(self, db_path, tmp_path):
        """seed_all is idempotent — 2nd run inserts zero new rows."""
        # Use the real bundled data (tests migration + real seed path).
        summary1 = pl.seed_all(db_path=db_path)
        assert summary1["parts"] > 0
        assert summary1["xref"] > 0
        # Capture exact row counts after first seed
        with get_connection(db_path) as conn:
            parts_count_1 = conn.execute(
                "SELECT COUNT(*) FROM parts"
            ).fetchone()[0]
            xref_count_1 = conn.execute(
                "SELECT COUNT(*) FROM parts_xref"
            ).fetchone()[0]
        summary2 = pl.seed_all(db_path=db_path)
        # Counts (input rows) match both runs
        assert summary2 == summary1
        # But no new rows were inserted
        with get_connection(db_path) as conn:
            parts_count_2 = conn.execute(
                "SELECT COUNT(*) FROM parts"
            ).fetchone()[0]
            xref_count_2 = conn.execute(
                "SELECT COUNT(*) FROM parts_xref"
            ).fetchone()[0]
        assert parts_count_1 == parts_count_2
        assert xref_count_1 == xref_count_2

    def test_malformed_json_raises_valueerror_with_line_col(
        self, db_path, tmp_path,
    ):
        p = tmp_path / "bad.json"
        p.write_text(
            "[\n  {\"slug\": \"x\",\n  broken\n]",
            encoding="utf-8",
        )
        with pytest.raises(ValueError) as excinfo:
            pl.load_parts_file(p, db_path=db_path)
        msg = str(excinfo.value)
        assert "bad.json" in msg
        assert "line" in msg
        assert "col" in msg

    def test_xref_unknown_slug_raises(self, db_path, tmp_path):
        p = tmp_path / "xref.json"
        p.write_text(
            json.dumps([
                {
                    "oem_slug": "missing-oem",
                    "aftermarket_slug": "missing-aft",
                    "equivalence_rating": 3,
                }
            ]),
            encoding="utf-8",
        )
        with pytest.raises(ValueError, match="unknown"):
            pl.load_parts_xref_file(p, db_path=db_path)

    def test_dependency_order_enforced(self, db_path, tmp_path):
        """xref file referencing a slug that isn't in parts.json raises."""
        parts_file = tmp_path / "parts.json"
        parts_file.write_text(
            json.dumps([
                {
                    "slug": "only-one",
                    "oem_part_number": "A",
                    "brand": "B",
                    "description": "D",
                    "category": "c",
                    "make": "X",
                    "model_pattern": "%",
                    "typical_cost_cents": 0,
                }
            ]),
            encoding="utf-8",
        )
        xref_file = tmp_path / "parts_xref.json"
        xref_file.write_text(
            json.dumps([
                {
                    "oem_slug": "only-one",
                    "aftermarket_slug": "not-yet-seeded",
                    "equivalence_rating": 3,
                }
            ]),
            encoding="utf-8",
        )
        # First the parts load succeeds ...
        pl.load_parts_file(parts_file, db_path=db_path)
        # ... but the xref load raises because 'not-yet-seeded' is missing.
        with pytest.raises(ValueError, match="unknown"):
            pl.load_parts_xref_file(xref_file, db_path=db_path)


# ---------------------------------------------------------------------------
# TestPartsCLI
# ---------------------------------------------------------------------------


def _seed_cli_db(db_path):
    """Hand-roll a deterministic mini set identical to `seeded_db`."""
    pr.add_part(
        slug="hd-tens-oem", oem_part_number="HD-26499-08",
        brand="Harley-Davidson",
        description="Twin Cam 88 hydraulic cam tensioner (OEM)",
        category="cam-tensioner",
        make="Harley-Davidson", model_pattern="%",
        year_min=1999, year_max=2017,
        typical_cost_cents=8999,
        verified_by="service-manual", db_path=db_path,
    )
    pr.add_part(
        slug="feuling-tens", oem_part_number="4124",
        brand="Feuling",
        description="HP+ cam tensioner upgrade",
        category="cam-tensioner",
        make="Harley-Davidson", model_pattern="%",
        typical_cost_cents=12995,
        verified_by="forum", db_path=db_path,
    )
    pr.add_part(
        slug="sands-tens", oem_part_number="33-4220",
        brand="S&S Cycle",
        description="S&S cam tensioner crossref for TC88/96/103",
        category="cam-tensioner",
        make="Harley-Davidson", model_pattern="%",
        typical_cost_cents=11495,
        verified_by="forum", db_path=db_path,
    )
    pr.add_xref(
        "hd-tens-oem", "feuling-tens",
        equivalence_rating=5,
        notes="Direct drop-in",
        source_url="https://example/feuling",
        db_path=db_path,
    )
    pr.add_xref(
        "hd-tens-oem", "sands-tens",
        equivalence_rating=4,
        notes="Drop-in, minor spring diff",
        source_url="https://example/sands",
        db_path=db_path,
    )


class TestPartsCLI:
    """CliRunner coverage of the four subcommands + predict integration."""

    def test_search_rich_table_and_json(self, cli_db):
        _seed_cli_db(cli_db)
        runner = CliRunner()
        # Rich table
        result = runner.invoke(
            _make_cli(),
            ["advanced", "parts", "search", "tensioner"],
        )
        assert result.exit_code == 0, result.output
        assert "Feuling" in result.output

        # JSON round-trip
        result2 = runner.invoke(
            _make_cli(),
            ["advanced", "parts", "search", "tensioner", "--json"],
        )
        assert result2.exit_code == 0, result2.output
        payload = json.loads(result2.output)
        assert "parts" in payload
        assert len(payload["parts"]) >= 3

    def test_xref_ranks_results(self, cli_db):
        _seed_cli_db(cli_db)
        runner = CliRunner()
        result = runner.invoke(
            _make_cli(),
            ["advanced", "parts", "xref", "HD-26499-08", "--json"],
        )
        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        xrefs = payload["xrefs"]
        assert len(xrefs) == 2
        # Highest rating first
        assert xrefs[0]["equivalence_rating"] == 5
        assert xrefs[1]["equivalence_rating"] == 4

    def test_xref_min_rating_filter(self, cli_db):
        _seed_cli_db(cli_db)
        runner = CliRunner()
        result = runner.invoke(
            _make_cli(),
            [
                "advanced", "parts", "xref", "HD-26499-08",
                "--min-rating", "5", "--json",
            ],
        )
        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        assert len(payload["xrefs"]) == 1
        assert payload["xrefs"][0]["equivalence_rating"] == 5

    def test_show_panel_and_nested_xref(self, cli_db):
        _seed_cli_db(cli_db)
        runner = CliRunner()
        result = runner.invoke(
            _make_cli(),
            ["advanced", "parts", "show", "hd-tens-oem"],
        )
        assert result.exit_code == 0, result.output
        # Panel title shows slug
        assert "hd-tens-oem" in result.output
        # Nested xref table shows both alternatives
        assert "Feuling" in result.output
        assert "S&S" in result.output

    def test_show_unknown_slug_red(self, cli_db):
        runner = CliRunner()
        result = runner.invoke(
            _make_cli(),
            ["advanced", "parts", "show", "no-such-slug"],
        )
        assert result.exit_code == 1
        assert "no part with slug" in result.output.lower()

    def test_search_empty_yellow_panel(self, cli_db):
        runner = CliRunner()
        result = runner.invoke(
            _make_cli(),
            ["advanced", "parts", "search", "unobtanium"],
        )
        assert result.exit_code == 0, result.output
        assert "No parts" in result.output or "no parts" in result.output.lower()

    def test_seed_requires_yes(self, cli_db):
        """`seed` without --yes prints a confirmation, does not seed."""
        runner = CliRunner()
        result = runner.invoke(
            _make_cli(),
            ["advanced", "parts", "seed"],
        )
        assert result.exit_code == 0
        assert "--yes" in result.output
        # No rows landed
        with get_connection(cli_db) as conn:
            count = conn.execute(
                "SELECT COUNT(*) FROM parts"
            ).fetchone()[0]
        assert count == 0

    def test_seed_with_yes_summary(self, cli_db):
        runner = CliRunner()
        result = runner.invoke(
            _make_cli(),
            ["advanced", "parts", "seed", "--yes", "--json"],
        )
        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        assert payload["summary"]["parts"] > 0
        assert payload["summary"]["xref"] > 0

    def test_xref_invalid_rating_rejected_by_click(self, cli_db):
        runner = CliRunner()
        result = runner.invoke(
            _make_cli(),
            [
                "advanced", "parts", "xref", "HD-26499-08",
                "--min-rating", "9",
            ],
        )
        assert result.exit_code != 0
        # Click's IntRange rejects OOR before the command runs
        assert "9" in result.output or "range" in result.output.lower()

    def test_predict_populates_parts_cost_when_seeded(self, cli_db):
        """Phase 148 integration: predict shows cents when parts seeded."""
        # Seed the parts table via CLI-equivalent repo calls
        _seed_cli_db(cli_db)
        # Also seed a known_issue whose parts_needed[0] resolves via tier 1
        from motodiag.knowledge.issues_repo import add_known_issue
        add_known_issue(
            title="Cam chain tensioner failure",
            description="Gen 1 TC88 hydraulic CCT weeps pressure at 40-60k mi.",
            make="Harley-Davidson", model="Sportster 1200",
            year_start=1999, year_end=2017,
            severity="high",
            symptoms=["cam chain rattle"],
            dtc_codes=[],
            causes=["Worn hydraulic plunger"],
            fix_procedure="Forum tip: upgrade to Feuling HP+ tensioner.",
            parts_needed=["HD-26499-08"],
            estimated_hours=3.0,
            db_path=cli_db,
        )
        from motodiag.advanced.predictor import predict_failures
        preds = predict_failures(
            {
                "make": "Harley-Davidson", "model": "Sportster 1200",
                "year": 2010, "mileage": 45_000,
            },
            horizon_days=3650,
            db_path=cli_db,
        )
        assert len(preds) > 0
        cct_pred = next(
            (p for p in preds if "Cam chain" in p.issue_title), None,
        )
        assert cct_pred is not None
        # Seeded cost for HD-26499-08 is 8999
        assert cct_pred.parts_cost_cents == 8999
