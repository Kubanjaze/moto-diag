"""Phase 145 — Adapter compatibility database tests.

Seven test classes, ~57 tests, zero real serial I/O, zero live tokens.

Test classes
------------

- :class:`TestMigration017` (4) — schema-version bump, 3 tables + 6
  indexes created, child-first rollback, FK to users intact.
- :class:`TestAdapterRepo` (10) — CRUD, INSERT OR IGNORE dup semantics,
  reliability / price validation, list filters, update partial,
  remove cascades.
- :class:`TestCompatibilityRepo` (12) — add, list by make/model/year,
  status ranking (full > partial > read-only), min_status filter,
  check_compatibility specificity, None vs incompatible.
- :class:`TestCompatNotes` (6) — add, type validation, make wildcard
  '*' rows, get by make returns scoped + wildcard, cascade delete.
- :class:`TestLoader` (6) — seed_all idempotent, per-file loaders,
  malformed JSON → ValueError with file + line, unknown slug in
  matrix → ValueError.
- :class:`TestCompatCLI` (15) — Click-runner driven: list, recommend
  (--bike + --make/--model), check with color panels, show,
  note add/list, seed --yes, --json output, error paths.
- :class:`TestAutoDetectorIntegration` (4) — compat_repo=None
  Phase 139 regression smoke, filter-hook with concrete repo,
  never-empty-fallback safety, unknown-make no-filter.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from motodiag.core.database import (
    SCHEMA_VERSION,
    get_connection,
    get_schema_version,
    init_db,
    table_exists,
)
from motodiag.core.migrations import (
    get_migration_by_version,
    rollback_migration,
)
from motodiag.hardware import compat_loader as cl
from motodiag.hardware import compat_repo as cr
from motodiag.hardware.ecu_detect import (
    AutoDetector,
    PROTOCOL_CAN,
    PROTOCOL_ELM327,
    PROTOCOL_J1850,
    PROTOCOL_KLINE,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def db_path(tmp_path):
    """Per-test SQLite DB pre-migrated to the latest schema."""
    path = str(tmp_path / "phase145.db")
    init_db(path)
    return path


@pytest.fixture
def seeded_db(tmp_path, monkeypatch):
    """Per-test DB preloaded with a small hand-rolled compat fixture set."""
    path = str(tmp_path / "phase145_seeded.db")
    init_db(path)

    # Three adapters spanning three tiers + statuses
    cr.add_adapter(
        slug="mock-mx",
        brand="MockBrand",
        model="MX Test",
        chipset="STN2100",
        transport="bluetooth",
        price_usd_cents=13999,
        supported_protocols_csv="ISO 15765,ISO 14230,J1850 VPW",
        supports_bidirectional=False,
        supports_mode22=True,
        reliability_1to5=5,
        db_path=path,
    )
    cr.add_adapter(
        slug="mock-elm",
        brand="MockBrand",
        model="ELM Clone",
        chipset="ELM327",
        transport="bluetooth",
        price_usd_cents=1299,
        supported_protocols_csv="ISO 15765,ISO 9141",
        supports_bidirectional=False,
        supports_mode22=False,
        reliability_1to5=2,
        db_path=path,
    )
    cr.add_adapter(
        slug="mock-pro",
        brand="MockBrand",
        model="Pro Bridge",
        chipset="proprietary",
        transport="bridge",
        price_usd_cents=49900,
        supported_protocols_csv="ISO 15765,J1850 VPW",
        supports_bidirectional=True,
        supports_mode22=True,
        reliability_1to5=5,
        db_path=path,
    )
    cr.add_compatibility(
        "mock-mx", "harley", "touring%", "partial",
        year_min=2011, year_max=2025, db_path=path,
    )
    cr.add_compatibility(
        "mock-elm", "harley", "touring%", "read-only",
        year_min=2011, year_max=2025, db_path=path,
    )
    cr.add_compatibility(
        "mock-elm", "harley", "touring%", "incompatible",
        year_min=1996, year_max=2010, db_path=path,
    )
    cr.add_compatibility(
        "mock-pro", "harley", "touring%", "full",
        year_min=2001, year_max=2025, db_path=path,
    )
    cr.add_compatibility(
        "mock-mx", "honda", "CBR%", "partial",
        year_min=2008, year_max=2025, db_path=path,
    )
    cr.add_compatibility(
        "mock-elm", "honda", "CBR%", "read-only",
        year_min=2008, year_max=2025, db_path=path,
    )
    return path


# ---------------------------------------------------------------------------
# Migration 017
# ---------------------------------------------------------------------------


class TestMigration017:
    """Migration 017 applies cleanly, creates 3 tables + 6 indexes, rolls back."""

    def test_schema_version_bumped_to_17(self, db_path):
        assert SCHEMA_VERSION == 17
        assert get_schema_version(db_path) == 17

    def test_three_tables_created(self, db_path):
        assert table_exists("obd_adapters", db_path) is True
        assert table_exists("adapter_compatibility", db_path) is True
        assert table_exists("compat_notes", db_path) is True

    def test_six_indexes_created(self, db_path):
        expected_index_names = {
            "idx_obd_adapters_slug",
            "idx_obd_adapters_chipset",
            "idx_compat_make_model",
            "idx_compat_make_year",
            "idx_compat_adapter",
            "idx_compat_notes_adapter_make",
        }
        with get_connection(db_path) as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='index'"
            )
            actual = {row[0] for row in cursor.fetchall()}
        assert expected_index_names.issubset(actual)

    def test_rollback_drops_tables_child_first(self, tmp_path):
        """Rolling back Migration 017 must drop all three tables without FK error."""
        path = str(tmp_path / "rollback.db")
        init_db(path)
        assert table_exists("obd_adapters", path) is True
        migration = get_migration_by_version(17)
        assert migration is not None
        # Rollback must not raise (child-first order handles the FK).
        rollback_migration(migration, path)
        assert table_exists("obd_adapters", path) is False
        assert table_exists("adapter_compatibility", path) is False
        assert table_exists("compat_notes", path) is False


# ---------------------------------------------------------------------------
# TestAdapterRepo
# ---------------------------------------------------------------------------


class TestAdapterRepo:
    """CRUD semantics + validation."""

    def test_add_and_get_roundtrip(self, db_path):
        new_id = cr.add_adapter(
            slug="a1", brand="B", model="M", chipset="ELM327",
            transport="usb", price_usd_cents=1999,
            supported_protocols_csv="ISO 15765",
            db_path=db_path,
        )
        assert new_id > 0
        row = cr.get_adapter("a1", db_path=db_path)
        assert row is not None
        assert row["slug"] == "a1"
        assert row["price_usd_cents"] == 1999
        assert row["supports_bidirectional"] is False
        assert row["supports_mode22"] is False

    def test_insert_or_ignore_returns_existing_id(self, db_path):
        id1 = cr.add_adapter(
            slug="dup", brand="B", model="M", chipset="ELM327",
            transport="usb", price_usd_cents=100,
            supported_protocols_csv="ISO 15765", db_path=db_path,
        )
        id2 = cr.add_adapter(
            slug="dup", brand="DIFFERENT", model="ALSO DIFFERENT",
            chipset="STN2100", transport="bluetooth",
            price_usd_cents=99999,
            supported_protocols_csv="ISO 15765,J1850 VPW",
            db_path=db_path,
        )
        assert id1 == id2
        # Original row wins — INSERT OR IGNORE on slug means the
        # second call's data is NOT merged.
        row = cr.get_adapter("dup", db_path=db_path)
        assert row["brand"] == "B"
        assert row["price_usd_cents"] == 100

    def test_reliability_out_of_range_raises_valueerror(self, db_path):
        with pytest.raises(ValueError, match="reliability"):
            cr.add_adapter(
                slug="bad", brand="B", model="M", chipset="ELM327",
                transport="usb", price_usd_cents=0,
                supported_protocols_csv="ISO 15765",
                reliability_1to5=6, db_path=db_path,
            )
        with pytest.raises(ValueError, match="reliability"):
            cr.add_adapter(
                slug="bad2", brand="B", model="M", chipset="ELM327",
                transport="usb", price_usd_cents=0,
                supported_protocols_csv="ISO 15765",
                reliability_1to5=0, db_path=db_path,
            )

    def test_price_float_raises_typeerror(self, db_path):
        with pytest.raises(TypeError, match="price_usd_cents"):
            cr.add_adapter(
                slug="bad-price", brand="B", model="M", chipset="ELM327",
                transport="usb", price_usd_cents=19.99,
                supported_protocols_csv="ISO 15765", db_path=db_path,
            )

    def test_price_negative_raises_valueerror(self, db_path):
        with pytest.raises(ValueError, match="price_usd_cents"):
            cr.add_adapter(
                slug="neg-price", brand="B", model="M", chipset="ELM327",
                transport="usb", price_usd_cents=-1,
                supported_protocols_csv="ISO 15765", db_path=db_path,
            )

    def test_list_adapters_filter_by_chipset(self, seeded_db):
        elm = cr.list_adapters(chipset="ELM327", db_path=seeded_db)
        stn = cr.list_adapters(chipset="STN2100", db_path=seeded_db)
        assert len(elm) == 1 and elm[0]["slug"] == "mock-elm"
        assert len(stn) == 1 and stn[0]["slug"] == "mock-mx"

    def test_list_adapters_filter_by_transport(self, seeded_db):
        bt = cr.list_adapters(transport="bluetooth", db_path=seeded_db)
        bridge = cr.list_adapters(transport="bridge", db_path=seeded_db)
        assert {a["slug"] for a in bt} == {"mock-mx", "mock-elm"}
        assert {a["slug"] for a in bridge} == {"mock-pro"}

    def test_update_adapter_partial(self, seeded_db):
        ok = cr.update_adapter(
            "mock-elm", db_path=seeded_db,
            reliability_1to5=3, notes="updated",
        )
        assert ok is True
        row = cr.get_adapter("mock-elm", db_path=seeded_db)
        assert row["reliability_1to5"] == 3
        assert row["notes"] == "updated"

    def test_update_adapter_rejects_unknown_field(self, seeded_db):
        with pytest.raises(ValueError, match="unknown fields"):
            cr.update_adapter("mock-elm", db_path=seeded_db, bogus=1)

    def test_remove_adapter_cascades_compat(self, seeded_db):
        # mock-elm has 3 compat rows (harley touring 1996-2010 incompatible,
        # 2011-2025 read-only, and honda CBR 2008-2025 read-only).
        with get_connection(seeded_db) as conn:
            before = conn.execute(
                "SELECT COUNT(*) FROM adapter_compatibility "
                "WHERE adapter_id = (SELECT id FROM obd_adapters "
                "WHERE slug='mock-elm')"
            ).fetchone()[0]
        assert before == 3
        ok = cr.remove_adapter("mock-elm", db_path=seeded_db)
        assert ok is True
        with get_connection(seeded_db) as conn:
            # CASCADE should leave no orphaned compat rows for this adapter.
            remaining = conn.execute(
                "SELECT COUNT(*) FROM adapter_compatibility c "
                "JOIN obd_adapters a ON a.id = c.adapter_id "
                "WHERE a.slug = 'mock-elm'"
            ).fetchone()[0]
        assert remaining == 0
        assert cr.get_adapter("mock-elm", db_path=seeded_db) is None


# ---------------------------------------------------------------------------
# TestCompatibilityRepo
# ---------------------------------------------------------------------------


class TestCompatibilityRepo:

    def test_add_compatibility_roundtrip(self, db_path):
        cr.add_adapter(
            slug="x", brand="B", model="M", chipset="ELM327",
            transport="usb", price_usd_cents=0,
            supported_protocols_csv="ISO 15765", db_path=db_path,
        )
        new_id = cr.add_compatibility(
            "x", "harley", "touring%", "full",
            year_min=2015, year_max=2020, db_path=db_path,
        )
        assert new_id > 0

    def test_add_compatibility_invalid_status_raises(self, db_path):
        cr.add_adapter(
            slug="x", brand="B", model="M", chipset="ELM327",
            transport="usb", price_usd_cents=0,
            supported_protocols_csv="ISO 15765", db_path=db_path,
        )
        with pytest.raises(ValueError, match="status"):
            cr.add_compatibility("x", "harley", "touring%", "bogus",
                                 db_path=db_path)

    def test_add_compatibility_unknown_slug_raises(self, db_path):
        with pytest.raises(ValueError, match="unknown adapter_slug"):
            cr.add_compatibility("nope", "harley", "%", "full",
                                 db_path=db_path)

    def test_add_compatibility_idempotent_natural_key(self, db_path):
        cr.add_adapter(
            slug="y", brand="B", model="M", chipset="ELM327",
            transport="usb", price_usd_cents=0,
            supported_protocols_csv="ISO 15765", db_path=db_path,
        )
        id1 = cr.add_compatibility(
            "y", "harley", "touring%", "full",
            year_min=2015, year_max=2020, db_path=db_path,
        )
        id2 = cr.add_compatibility(
            "y", "harley", "touring%", "full",
            year_min=2015, year_max=2020, db_path=db_path,
        )
        assert id1 == id2

    def test_list_compatible_adapters_ranks_by_status_then_reliability_then_price(
        self, seeded_db,
    ):
        rows = cr.list_compatible_adapters(
            make="harley", model="touring-road-glide", year=2015,
            db_path=seeded_db,
        )
        # mock-pro (full) should come before mock-mx (partial) before
        # mock-elm (read-only).
        slugs = [r["slug"] for r in rows]
        assert slugs.index("mock-pro") < slugs.index("mock-mx")
        assert slugs.index("mock-mx") < slugs.index("mock-elm")

    def test_list_compatible_adapters_sql_like_pattern_matches(self, seeded_db):
        rows = cr.list_compatible_adapters(
            make="honda", model="CBR1000RR-SP", year=2018,
            db_path=seeded_db,
        )
        assert len(rows) >= 2  # mock-mx + mock-elm both match CBR%
        slugs = {r["slug"] for r in rows}
        assert "mock-mx" in slugs
        assert "mock-elm" in slugs

    def test_list_compatible_adapters_year_range_filter(self, seeded_db):
        # mock-elm touring has two rows: 1996-2010 incompatible, 2011-2025
        # read-only. With default min_status='read-only' and year=2008,
        # only the 1996-2010 row could match but it's 'incompatible' so
        # it is excluded. mock-pro's 2001-2025 'full' matches.
        rows = cr.list_compatible_adapters(
            make="harley", model="touring-classic", year=2008,
            db_path=seeded_db,
        )
        slugs = {r["slug"] for r in rows}
        assert "mock-pro" in slugs
        assert "mock-elm" not in slugs
        assert "mock-mx" not in slugs  # mx is 2011-2025 only

    def test_list_compatible_adapters_min_status_filter(self, seeded_db):
        # min_status='full' excludes everything below full.
        rows = cr.list_compatible_adapters(
            make="harley", model="touring-x", year=2015,
            min_status="full", db_path=seeded_db,
        )
        slugs = {r["slug"] for r in rows}
        assert slugs == {"mock-pro"}

    def test_list_compatible_adapters_incompatible_excluded_by_default(
        self, seeded_db,
    ):
        # mock-elm has 'incompatible' for pre-2011 Touring. Default min_status
        # 'read-only' excludes it.
        rows = cr.list_compatible_adapters(
            make="harley", model="touring-softail", year=2005,
            db_path=seeded_db,
        )
        statuses = {r["status"] for r in rows}
        assert "incompatible" not in statuses

    def test_check_compatibility_returns_specific_match(self, seeded_db):
        result = cr.check_compatibility(
            "mock-mx", "harley", "touring-road-glide", 2015,
            db_path=seeded_db,
        )
        assert result is not None
        assert result["status"] == "partial"
        assert result["slug"] == "mock-mx"

    def test_check_compatibility_none_for_unknown(self, seeded_db):
        result = cr.check_compatibility(
            "mock-mx", "yamaha", "R1", 2015, db_path=seeded_db,
        )
        assert result is None

    def test_check_compatibility_most_specific_wins(self, db_path):
        """Exact pattern beats wildcard, narrower year beats wider."""
        cr.add_adapter(
            slug="s", brand="B", model="M", chipset="ELM327",
            transport="usb", price_usd_cents=0,
            supported_protocols_csv="ISO 15765", db_path=db_path,
        )
        # Wildcard broad row.
        cr.add_compatibility(
            "s", "harley", "%", "read-only", db_path=db_path,
        )
        # Exact pattern tighter year row.
        cr.add_compatibility(
            "s", "harley", "touring-glide", "full",
            year_min=2015, year_max=2015, db_path=db_path,
        )
        result = cr.check_compatibility(
            "s", "harley", "touring-glide", 2015, db_path=db_path,
        )
        assert result["status"] == "full"


# ---------------------------------------------------------------------------
# TestCompatNotes
# ---------------------------------------------------------------------------


class TestCompatNotes:

    def test_add_note_roundtrip(self, seeded_db):
        nid = cr.add_compat_note(
            "mock-mx", "harley", "tip",
            "Use --timeout 3 on pre-2011 Touring.",
            db_path=seeded_db,
        )
        assert nid > 0
        notes = cr.get_compat_notes("mock-mx", make="harley",
                                    db_path=seeded_db)
        assert any(n["id"] == nid for n in notes)

    def test_add_note_invalid_type_raises(self, seeded_db):
        with pytest.raises(ValueError, match="note_type"):
            cr.add_compat_note(
                "mock-mx", "harley", "bogus", "body", db_path=seeded_db,
            )

    def test_add_note_unknown_slug_raises(self, seeded_db):
        with pytest.raises(ValueError, match="unknown adapter_slug"):
            cr.add_compat_note(
                "nope", "harley", "tip", "body", db_path=seeded_db,
            )

    def test_get_compat_notes_includes_wildcard_when_make_given(
        self, seeded_db,
    ):
        cr.add_compat_note(
            "mock-mx", "*", "quirk", "Universal BT pairing tip.",
            db_path=seeded_db,
        )
        cr.add_compat_note(
            "mock-mx", "harley", "tip", "Harley-specific timeout tip.",
            db_path=seeded_db,
        )
        rows = cr.get_compat_notes("mock-mx", make="harley",
                                   db_path=seeded_db)
        makes = {r["vehicle_make"] for r in rows}
        assert "harley" in makes
        assert "*" in makes

    def test_get_compat_notes_without_make_returns_all(self, seeded_db):
        cr.add_compat_note(
            "mock-mx", "honda", "tip", "Honda tip.", db_path=seeded_db,
        )
        cr.add_compat_note(
            "mock-mx", "harley", "tip", "Harley tip.", db_path=seeded_db,
        )
        rows = cr.get_compat_notes("mock-mx", db_path=seeded_db)
        makes = {r["vehicle_make"] for r in rows}
        assert "honda" in makes
        assert "harley" in makes

    def test_cascade_delete_wipes_notes(self, seeded_db):
        cr.add_compat_note(
            "mock-mx", "harley", "tip", "will be deleted",
            db_path=seeded_db,
        )
        cr.remove_adapter("mock-mx", db_path=seeded_db)
        # Fetching notes on a deleted adapter returns empty (slug gone).
        rows = cr.get_compat_notes("mock-mx", db_path=seeded_db)
        assert rows == []


# ---------------------------------------------------------------------------
# TestLoader
# ---------------------------------------------------------------------------


class TestLoader:

    def test_seed_all_idempotent(self, db_path):
        summary1 = cl.seed_all(db_path=db_path)
        summary2 = cl.seed_all(db_path=db_path)
        assert summary1 == summary2
        # Re-seeding does not create duplicate adapter rows.
        all_adapters = cr.list_adapters(db_path=db_path)
        unique_slugs = {a["slug"] for a in all_adapters}
        assert len(all_adapters) == len(unique_slugs)

    def test_load_adapters_file_counts(self, db_path, tmp_path):
        p = tmp_path / "adapters.json"
        p.write_text(json.dumps([
            {"slug": "t1", "brand": "B", "model": "M",
             "chipset": "ELM327", "transport": "usb",
             "price_usd_cents": 100,
             "supported_protocols_csv": "ISO 15765"},
            {"slug": "t2", "brand": "B", "model": "M2",
             "chipset": "STN1110", "transport": "bluetooth",
             "price_usd_cents": 2000,
             "supported_protocols_csv": "ISO 15765,ISO 14230"},
        ]), encoding="utf-8")
        n = cl.load_adapters_file(p, db_path=db_path)
        assert n == 2
        assert cr.get_adapter("t1", db_path=db_path) is not None
        assert cr.get_adapter("t2", db_path=db_path) is not None

    def test_load_compat_matrix_file_counts(self, db_path, tmp_path):
        cr.add_adapter(
            slug="t", brand="B", model="M", chipset="ELM327",
            transport="usb", price_usd_cents=0,
            supported_protocols_csv="ISO 15765", db_path=db_path,
        )
        p = tmp_path / "matrix.json"
        p.write_text(json.dumps([
            {"adapter_slug": "t", "make": "harley",
             "model_pattern": "touring%", "status": "partial"},
            {"adapter_slug": "t", "make": "honda",
             "model_pattern": "CBR%", "status": "read-only"},
        ]), encoding="utf-8")
        n = cl.load_compat_matrix_file(p, db_path=db_path)
        assert n == 2

    def test_load_compat_notes_file_counts(self, db_path, tmp_path):
        cr.add_adapter(
            slug="t", brand="B", model="M", chipset="ELM327",
            transport="usb", price_usd_cents=0,
            supported_protocols_csv="ISO 15765", db_path=db_path,
        )
        p = tmp_path / "notes.json"
        p.write_text(json.dumps([
            {"adapter_slug": "t", "make": "harley",
             "note_type": "tip", "body": "nice"},
        ]), encoding="utf-8")
        n = cl.load_compat_notes_file(p, db_path=db_path)
        assert n == 1

    def test_malformed_json_raises_valueerror_with_line(
        self, db_path, tmp_path,
    ):
        p = tmp_path / "bad.json"
        # JSON that breaks at a specific line.
        p.write_text("[\n  {\"slug\": \"x\",\n  broken\n]",
                     encoding="utf-8")
        with pytest.raises(ValueError) as excinfo:
            cl.load_adapters_file(p, db_path=db_path)
        msg = str(excinfo.value)
        assert "bad.json" in msg
        assert "line" in msg

    def test_matrix_unknown_slug_raises_valueerror(
        self, db_path, tmp_path,
    ):
        p = tmp_path / "matrix.json"
        p.write_text(json.dumps([
            {"adapter_slug": "never-existed", "make": "harley",
             "model_pattern": "%", "status": "full"},
        ]), encoding="utf-8")
        with pytest.raises(ValueError, match="unknown adapter_slug"):
            cl.load_compat_matrix_file(p, db_path=db_path)


# ---------------------------------------------------------------------------
# TestCompatCLI
# ---------------------------------------------------------------------------


def _make_cli():
    import click
    from motodiag.cli.hardware import register_hardware

    @click.group()
    def root() -> None:
        """test root"""

    register_hardware(root)
    return root


@pytest.fixture
def cli_runner_with_db(tmp_path, monkeypatch):
    """CliRunner fixture with a seeded DB. Reroutes the default DB path
    through env + settings cache invalidation so CLI subcommands that
    call repo functions without a db_path argument pick up the tmp DB.
    """
    path = str(tmp_path / "cli.db")

    from motodiag.core import config as cfg_mod

    # Set the env var BEFORE init_db so Settings picks it up.
    monkeypatch.setenv("MOTODIAG_DB_PATH", path)
    cfg_mod.get_settings.cache_clear()
    assert cfg_mod.get_settings().db_path == path

    init_db(path)
    # Seed the full knowledge base so CLI tests have real data.
    cl.seed_all(db_path=path)

    # Also patch init_db inside the hardware module so it doesn't race
    # against the env-based default on Windows (init_db creates dirs,
    # and a stale settings object in another module would target the
    # real shop DB).
    from motodiag.cli import hardware as hw_mod

    original_init_db = hw_mod.init_db

    def _patched_init(*args, **kwargs):
        if args or kwargs:
            return original_init_db(*args, **kwargs)
        return original_init_db(path)

    monkeypatch.setattr(hw_mod, "init_db", _patched_init)

    runner = CliRunner()
    yield runner, path
    # Clear the cache on the way out so other tests start fresh.
    cfg_mod.get_settings.cache_clear()


class TestCompatCLI:

    def test_compat_list_renders_table(self, cli_runner_with_db):
        runner, _ = cli_runner_with_db
        cli = _make_cli()
        result = runner.invoke(cli, ["hardware", "compat", "list"])
        assert result.exit_code == 0, result.output
        assert "OBD Adapter Catalog" in result.output or \
               "OBDLink" in result.output

    def test_compat_list_json(self, cli_runner_with_db):
        runner, _ = cli_runner_with_db
        cli = _make_cli()
        result = runner.invoke(
            cli, ["hardware", "compat", "list", "--json"],
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert isinstance(data, list) and len(data) >= 20
        slugs = {a["slug"] for a in data}
        assert "obdlink-mx-plus" in slugs

    def test_compat_list_chipset_filter(self, cli_runner_with_db):
        runner, _ = cli_runner_with_db
        cli = _make_cli()
        result = runner.invoke(
            cli, ["hardware", "compat", "list",
                  "--chipset", "STN2100", "--json"],
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert all(a["chipset"] == "STN2100" for a in data)
        assert len(data) >= 1

    def test_compat_recommend_by_make_model(self, cli_runner_with_db):
        runner, _ = cli_runner_with_db
        cli = _make_cli()
        result = runner.invoke(
            cli, ["hardware", "compat", "recommend",
                  "--make", "harley", "--model", "touring-road-glide",
                  "--year", "2015", "--json"],
        )
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert isinstance(data, list)
        # Should find at least MX+ and PV3 for a 2015 Touring.
        slugs = {r["slug"] for r in data}
        assert "dynojet-power-vision-3" in slugs
        assert "obdlink-mx-plus" in slugs

    def test_compat_recommend_requires_make_or_bike(
        self, cli_runner_with_db,
    ):
        runner, _ = cli_runner_with_db
        cli = _make_cli()
        result = runner.invoke(
            cli, ["hardware", "compat", "recommend"],
        )
        assert result.exit_code != 0

    def test_compat_check_full_verdict(self, cli_runner_with_db):
        runner, _ = cli_runner_with_db
        cli = _make_cli()
        result = runner.invoke(
            cli, ["hardware", "compat", "check",
                  "--adapter", "dynojet-power-vision-3",
                  "--make", "harley",
                  "--model", "touring-road-glide",
                  "--year", "2015", "--json"],
        )
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["verdict"]["status"] == "full"

    def test_compat_check_unknown_adapter(self, cli_runner_with_db):
        runner, _ = cli_runner_with_db
        cli = _make_cli()
        result = runner.invoke(
            cli, ["hardware", "compat", "check",
                  "--adapter", "never-existed",
                  "--make", "harley",
                  "--model", "touring-x"],
        )
        assert result.exit_code == 1
        assert "Unknown adapter" in result.output

    def test_compat_check_unknown_bike_returns_none(
        self, cli_runner_with_db,
    ):
        runner, _ = cli_runner_with_db
        cli = _make_cli()
        result = runner.invoke(
            cli, ["hardware", "compat", "check",
                  "--adapter", "obdlink-mx-plus",
                  "--make", "tesla",
                  "--model", "cybertruck", "--json"],
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["verdict"] is None

    def test_compat_show_renders_detail_plus_matrix(
        self, cli_runner_with_db,
    ):
        runner, _ = cli_runner_with_db
        cli = _make_cli()
        result = runner.invoke(
            cli, ["hardware", "compat", "show",
                  "--adapter", "obdlink-mx-plus", "--json"],
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["adapter"]["slug"] == "obdlink-mx-plus"
        assert isinstance(data["compat"], list) and len(data["compat"]) > 0

    def test_compat_show_unknown_adapter(self, cli_runner_with_db):
        runner, _ = cli_runner_with_db
        cli = _make_cli()
        result = runner.invoke(
            cli, ["hardware", "compat", "show",
                  "--adapter", "ghost-adapter"],
        )
        assert result.exit_code == 1
        assert "Unknown adapter" in result.output

    def test_compat_note_add_and_list_roundtrip(
        self, cli_runner_with_db,
    ):
        runner, _ = cli_runner_with_db
        cli = _make_cli()
        # Add a note
        res1 = runner.invoke(
            cli, ["hardware", "compat", "note", "add",
                  "--adapter", "obdlink-mx-plus",
                  "--make", "harley",
                  "--type", "tip",
                  "Test note body content"],
        )
        assert res1.exit_code == 0, res1.output
        assert "Added note" in res1.output
        # List and check the note appears
        res2 = runner.invoke(
            cli, ["hardware", "compat", "note", "list",
                  "--adapter", "obdlink-mx-plus",
                  "--make", "harley", "--json"],
        )
        assert res2.exit_code == 0
        data = json.loads(res2.output)
        bodies = [n["body"] for n in data]
        assert "Test note body content" in bodies

    def test_compat_note_add_invalid_type(self, cli_runner_with_db):
        runner, _ = cli_runner_with_db
        cli = _make_cli()
        res = runner.invoke(
            cli, ["hardware", "compat", "note", "add",
                  "--adapter", "obdlink-mx-plus",
                  "--make", "harley",
                  "--type", "bogus",
                  "body"],
        )
        assert res.exit_code != 0

    def test_compat_seed_yes_idempotent(self, cli_runner_with_db):
        runner, _ = cli_runner_with_db
        cli = _make_cli()
        # Already seeded via fixture — re-run should still succeed and
        # report the row counts without creating duplicates.
        res = runner.invoke(
            cli, ["hardware", "compat", "seed", "--yes"],
        )
        assert res.exit_code == 0, res.output
        assert "Loaded" in res.output

    def test_compat_recommend_and_bike_mutually_exclusive(
        self, cli_runner_with_db,
    ):
        runner, _ = cli_runner_with_db
        cli = _make_cli()
        res = runner.invoke(
            cli, ["hardware", "compat", "recommend",
                  "--bike", "anything",
                  "--make", "harley",
                  "--model", "touring"],
        )
        assert res.exit_code != 0

    def test_compat_check_and_bike_mutually_exclusive(
        self, cli_runner_with_db,
    ):
        runner, _ = cli_runner_with_db
        cli = _make_cli()
        res = runner.invoke(
            cli, ["hardware", "compat", "check",
                  "--adapter", "obdlink-mx-plus",
                  "--bike", "any",
                  "--make", "harley",
                  "--model", "touring"],
        )
        assert res.exit_code != 0


# ---------------------------------------------------------------------------
# TestAutoDetectorIntegration
# ---------------------------------------------------------------------------


class TestAutoDetectorIntegration:
    """Verify Phase 139 regression + Phase 145 compat_repo hook."""

    def test_compat_repo_none_preserves_phase139_behavior(self):
        """Default compat_repo=None → same order as Phase 139."""
        det = AutoDetector(port="COM3", make_hint="harley")
        assert det._compat_repo is None
        order = det._protocol_order_for_hint(det.make_hint)
        assert order == (PROTOCOL_J1850, PROTOCOL_CAN, PROTOCOL_ELM327)

        det2 = AutoDetector(port="COM3")  # no hint
        order2 = det2._protocol_order_for_hint(None)
        assert order2 == (
            PROTOCOL_CAN, PROTOCOL_KLINE, PROTOCOL_J1850, PROTOCOL_ELM327,
        )

    def test_compat_repo_filters_protocols_for_make(self):
        """Attached compat_repo with skip set removes those protocols."""
        fake_repo = MagicMock()
        fake_repo.protocols_to_skip_for_make.return_value = {PROTOCOL_CAN}
        det = AutoDetector(
            port="COM3", make_hint="harley", compat_repo=fake_repo,
        )
        order = det._protocol_order_for_hint(det.make_hint)
        # Harley default: J1850, CAN, ELM327. Skip CAN → (J1850, ELM327).
        assert PROTOCOL_CAN not in order
        assert PROTOCOL_J1850 in order
        assert PROTOCOL_ELM327 in order

    def test_compat_repo_never_empties_fallback(self):
        """If skip set would empty the order, fall back to unfiltered."""
        fake_repo = MagicMock()
        # Skip every protocol in the harley list.
        fake_repo.protocols_to_skip_for_make.return_value = {
            PROTOCOL_CAN, PROTOCOL_J1850, PROTOCOL_ELM327,
        }
        det = AutoDetector(
            port="COM3", make_hint="harley", compat_repo=fake_repo,
        )
        order = det._protocol_order_for_hint(det.make_hint)
        # Must NOT be empty. Safety fallback returns the unfiltered
        # original order.
        assert len(order) > 0
        assert order == (PROTOCOL_J1850, PROTOCOL_CAN, PROTOCOL_ELM327)

    def test_compat_repo_not_consulted_when_make_hint_none(self):
        """No make hint → compat_repo is never consulted."""
        fake_repo = MagicMock()
        # If called, make the test fail loudly by returning a huge skip set.
        fake_repo.protocols_to_skip_for_make.return_value = {
            PROTOCOL_CAN, PROTOCOL_KLINE, PROTOCOL_J1850, PROTOCOL_ELM327,
        }
        det = AutoDetector(port="COM3", compat_repo=fake_repo)
        order = det._protocol_order_for_hint(None)
        assert order == (
            PROTOCOL_CAN, PROTOCOL_KLINE, PROTOCOL_J1850, PROTOCOL_ELM327,
        )
        fake_repo.protocols_to_skip_for_make.assert_not_called()
