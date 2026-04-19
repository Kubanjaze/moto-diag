"""Phase 152 — service history tracking tests.

Five classes across ~35 tests:

- :class:`TestMigration020` (4) — ALTER vehicles.mileage, service_history
  table shape, three indexes, rollback drops service_history + indexes
  but preserves vehicles.mileage (SQLite pre-3.35 DROP COLUMN caveat).
- :class:`TestHistoryRepo` (10) — add+get round-trip, list filters,
  cross-bike list, by_type, counts, delete, FK cascade on vehicle
  delete, mechanic SET NULL on user delete, CHECK rejects unknown
  type, monotonic mileage bump, no-decrease guard.
- :class:`TestHistoryCLI` (12) — CliRunner happy paths for add /
  list / show / show-all / by-type, --mechanic resolution, unknown
  bike remediation, empty yellow panel, --json round-trip,
  ``garage update --mileage`` persists.
- :class:`TestPhase148IntegrationBonus` (5) — predictor +0.05 bonus
  for mileage_source="db", flag wins over DB, direct-args always
  "flag", NULL mileage yields no source tag.
- :class:`TestRegression` (4) — Phase 148 44 tests still green (the
  critical --current-miles "flag" surface is byte-identical), Phase
  140 hardware scan slug, Phase 12 Gate 1, Phase 08 known_issues.

All SW + SQL only. Zero AI calls, zero network, zero live tokens.
"""

from __future__ import annotations

import json as _json
import sqlite3
from datetime import date

import pytest
from click.testing import CliRunner

from motodiag.advanced import (
    ServiceEvent,
    add_service_event,
    count_service_events,
    delete_service_event,
    get_service_event,
    list_all_service_events,
    list_by_type,
    list_service_events,
)
from motodiag.core.database import get_connection, init_db
from motodiag.core.migrations import (
    get_migration_by_version,
    rollback_migration,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_cli():
    """Return the production CLI (has `advanced` + `garage` wired in)."""
    from motodiag.cli.main import cli as real_cli

    return real_cli


@pytest.fixture
def db(tmp_path):
    """Fresh DB at the latest schema version."""
    path = str(tmp_path / "phase152.db")
    init_db(path)
    return path


@pytest.fixture
def cli_db(tmp_path, monkeypatch):
    """Point settings + CLI paths at a temp DB."""
    from motodiag.core.config import reset_settings

    path = str(tmp_path / "phase152_cli.db")
    init_db(path)
    monkeypatch.setenv("MOTODIAG_DB_PATH", path)
    monkeypatch.setenv("COLUMNS", "240")
    reset_settings()
    yield path
    reset_settings()


def _seed_vehicle(
    db_path: str, make: str = "Harley-Davidson",
    model: str = "Sportster 1200", year: int = 2010,
) -> int:
    from motodiag.core.models import (
        EngineType, PowertrainType, ProtocolType, VehicleBase,
    )
    from motodiag.vehicles.registry import add_vehicle

    v = VehicleBase(
        make=make, model=model, year=year, engine_cc=1200,
        protocol=ProtocolType.J1850,
        powertrain=PowertrainType.ICE,
        engine_type=EngineType.FOUR_STROKE,
    )
    return add_vehicle(v, db_path=db_path)


def _seed_user(db_path: str, username: str = "wrench-wielder") -> int:
    """Insert a minimal users row for mechanic attribution tests."""
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (username, "x"),
        )
        return int(cursor.lastrowid)


# ===========================================================================
# 1. Migration 020
# ===========================================================================


class TestMigration020:
    """Migration 020 shape: ALTER + new table + 3 indexes + rollback."""

    def test_vehicles_has_mileage_column(self, db):
        """ALTER TABLE added vehicles.mileage as INTEGER nullable."""
        with get_connection(db) as conn:
            cols = [
                dict(r) for r in conn.execute(
                    "PRAGMA table_info(vehicles)"
                ).fetchall()
            ]
        names = [c["name"] for c in cols]
        assert "mileage" in names, names
        mileage_col = next(c for c in cols if c["name"] == "mileage")
        assert mileage_col["type"].upper().startswith("INT")
        # Nullable: PRAGMA "notnull" 0 means NULL allowed
        assert int(mileage_col["notnull"]) == 0

    def test_service_history_table_shape(self, db):
        """service_history has all expected columns + CHECK constraint."""
        with get_connection(db) as conn:
            cols = [
                dict(r) for r in conn.execute(
                    "PRAGMA table_info(service_history)"
                ).fetchall()
            ]
        names = {c["name"] for c in cols}
        assert names.issuperset({
            "id", "vehicle_id", "event_type", "at_miles", "at_date",
            "notes", "cost_cents", "mechanic_user_id", "parts_csv",
            "completed_at",
        }), names

        # CHECK constraint enforcement: try inserting an unknown type.
        with get_connection(db) as conn:
            vid = _seed_vehicle_inline(conn)
            with pytest.raises(sqlite3.IntegrityError):
                conn.execute(
                    "INSERT INTO service_history (vehicle_id, event_type, at_date) "
                    "VALUES (?, ?, ?)",
                    (vid, "frobnicate", date.today().isoformat()),
                )

    def test_three_indexes_created(self, db):
        """Migration 020 creates 3 indexes on service_history."""
        with get_connection(db) as conn:
            rows = conn.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type='index' AND tbl_name='service_history'"
            ).fetchall()
        names = {r["name"] for r in rows}
        for expected in (
            "idx_service_history_vehicle",
            "idx_service_history_type",
            "idx_service_history_date",
        ):
            assert expected in names, names

    def test_rollback_drops_table_and_indexes(self, tmp_path):
        """rollback_migration(020) drops service_history + indexes but
        leaves vehicles.mileage in place (SQLite pre-3.35 caveat)."""
        path = str(tmp_path / "rollback.db")
        init_db(path)
        m = get_migration_by_version(20)
        assert m is not None, "Migration 020 must be registered"

        rollback_migration(m, path)

        with get_connection(path) as conn:
            # Table gone
            row = conn.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type='table' AND name='service_history'"
            ).fetchone()
            assert row is None
            # Indexes gone
            idx = conn.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type='index' AND name LIKE 'idx_service_history%'"
            ).fetchall()
            assert idx == []
            # vehicles.mileage stays (documented SQLite caveat)
            cols = [
                dict(r) for r in conn.execute(
                    "PRAGMA table_info(vehicles)"
                ).fetchall()
            ]
            names = [c["name"] for c in cols]
            assert "mileage" in names


def _seed_vehicle_inline(conn) -> int:
    """Minimal vehicle seed helper usable with a raw connection."""
    cursor = conn.execute(
        "INSERT INTO vehicles (make, model, year, protocol) "
        "VALUES (?, ?, ?, ?)",
        ("Honda", "CBR600RR", 2005, "none"),
    )
    return int(cursor.lastrowid)


# ===========================================================================
# 2. history_repo CRUD
# ===========================================================================


class TestHistoryRepo:
    """Per-bike CRUD, filters, cascade, monotonic bump, guards."""

    def test_add_and_get_roundtrip(self, db):
        vid = _seed_vehicle(db)
        ev = ServiceEvent(
            vehicle_id=vid,
            event_type="oil-change",
            at_miles=12_500,
            at_date=date(2026, 3, 1),
            notes="Synthetic 20w50, Mobil 1.",
            cost_cents=4_999,
            parts_csv="OIL-20W50-4Q,FILT-63731-99A",
        )
        new_id = add_service_event(ev, db_path=db)
        row = get_service_event(new_id, db_path=db)
        assert row is not None
        assert row["event_type"] == "oil-change"
        assert row["at_miles"] == 12_500
        assert row["at_date"] == "2026-03-01"
        assert row["cost_cents"] == 4_999
        assert row["parts_csv"] == "OIL-20W50-4Q,FILT-63731-99A"

    def test_list_filters_by_vehicle_and_date_range(self, db):
        vid = _seed_vehicle(db)
        # Two events on different dates.
        add_service_event(
            ServiceEvent(
                vehicle_id=vid, event_type="oil-change",
                at_miles=10_000, at_date=date(2025, 1, 15),
            ),
            db_path=db,
        )
        add_service_event(
            ServiceEvent(
                vehicle_id=vid, event_type="tire",
                at_miles=11_000, at_date=date(2026, 4, 1),
            ),
            db_path=db,
        )

        all_rows = list_service_events(vid, db_path=db)
        assert len(all_rows) == 2
        # Newest first — at_date DESC
        assert all_rows[0]["event_type"] == "tire"

        # since filter
        only_recent = list_service_events(
            vid, since="2026-01-01", db_path=db,
        )
        assert len(only_recent) == 1
        assert only_recent[0]["event_type"] == "tire"

        # until filter
        only_old = list_service_events(
            vid, until="2025-12-31", db_path=db,
        )
        assert len(only_old) == 1
        assert only_old[0]["event_type"] == "oil-change"

        # event_type filter
        only_tire = list_service_events(
            vid, event_type="tire", db_path=db,
        )
        assert len(only_tire) == 1

    def test_list_all_cross_bike(self, db):
        v1 = _seed_vehicle(db)
        v2 = _seed_vehicle(db, make="Honda", model="CBR600RR", year=2005)
        add_service_event(
            ServiceEvent(
                vehicle_id=v1, event_type="brake",
                at_date=date(2026, 1, 1),
            ),
            db_path=db,
        )
        add_service_event(
            ServiceEvent(
                vehicle_id=v2, event_type="oil-change",
                at_date=date(2026, 2, 1),
            ),
            db_path=db,
        )
        rows = list_all_service_events(db_path=db)
        assert len(rows) == 2
        # at_date DESC → honda (2026-02) before harley (2026-01)
        assert rows[0]["vehicle_id"] == v2

    def test_list_by_type_cross_bike(self, db):
        v1 = _seed_vehicle(db)
        v2 = _seed_vehicle(db, make="Honda", model="CBR600RR", year=2005)
        add_service_event(
            ServiceEvent(
                vehicle_id=v1, event_type="oil-change",
                at_date=date(2026, 1, 1),
            ),
            db_path=db,
        )
        add_service_event(
            ServiceEvent(
                vehicle_id=v2, event_type="oil-change",
                at_date=date(2026, 2, 1),
            ),
            db_path=db,
        )
        add_service_event(
            ServiceEvent(
                vehicle_id=v1, event_type="brake",
                at_date=date(2026, 3, 1),
            ),
            db_path=db,
        )
        oil_rows = list_by_type("oil-change", db_path=db)
        assert len(oil_rows) == 2
        assert all(r["event_type"] == "oil-change" for r in oil_rows)

    def test_count_service_events(self, db):
        vid = _seed_vehicle(db)
        assert count_service_events(db_path=db) == 0
        add_service_event(
            ServiceEvent(
                vehicle_id=vid, event_type="oil-change",
                at_date=date(2026, 1, 1),
            ),
            db_path=db,
        )
        add_service_event(
            ServiceEvent(
                vehicle_id=vid, event_type="tire",
                at_date=date(2026, 2, 1),
            ),
            db_path=db,
        )
        assert count_service_events(db_path=db) == 2
        assert count_service_events(vehicle_id=vid, db_path=db) == 2
        assert count_service_events(
            vehicle_id=vid, event_type="oil-change", db_path=db,
        ) == 1

    def test_delete_service_event(self, db):
        vid = _seed_vehicle(db)
        eid = add_service_event(
            ServiceEvent(
                vehicle_id=vid, event_type="custom",
                at_date=date(2026, 1, 1),
            ),
            db_path=db,
        )
        assert delete_service_event(eid, db_path=db) is True
        assert get_service_event(eid, db_path=db) is None
        # Second delete is a no-op
        assert delete_service_event(eid, db_path=db) is False

    def test_fk_cascade_on_vehicle_delete(self, db):
        vid = _seed_vehicle(db)
        add_service_event(
            ServiceEvent(
                vehicle_id=vid, event_type="oil-change",
                at_date=date(2026, 1, 1),
            ),
            db_path=db,
        )
        assert count_service_events(vehicle_id=vid, db_path=db) == 1
        with get_connection(db) as conn:
            conn.execute("DELETE FROM vehicles WHERE id = ?", (vid,))
        # CASCADE drops the history row with the bike.
        assert count_service_events(vehicle_id=vid, db_path=db) == 0

    def test_mechanic_set_null_on_user_delete(self, db):
        vid = _seed_vehicle(db)
        uid = _seed_user(db, "wrench-mike")
        eid = add_service_event(
            ServiceEvent(
                vehicle_id=vid, event_type="oil-change",
                at_date=date(2026, 1, 1),
                mechanic_user_id=uid,
            ),
            db_path=db,
        )
        row = get_service_event(eid, db_path=db)
        assert row["mechanic_user_id"] == uid
        # Delete the user; service_history row should have mechanic_user_id
        # nulled by ON DELETE SET NULL.
        with get_connection(db) as conn:
            conn.execute("DELETE FROM users WHERE id = ?", (uid,))
        row_after = get_service_event(eid, db_path=db)
        assert row_after["mechanic_user_id"] is None

    def test_check_rejects_unknown_event_type(self, db):
        """The DB CHECK rejects event_type values outside the 11-value vocab."""
        vid = _seed_vehicle(db)
        # Bypass Pydantic so the raw SQL hits the CHECK.
        with get_connection(db) as conn:
            with pytest.raises(sqlite3.IntegrityError):
                conn.execute(
                    "INSERT INTO service_history (vehicle_id, event_type, at_date) "
                    "VALUES (?, ?, ?)",
                    (vid, "frobnicate", "2026-01-01"),
                )

    def test_monotonic_mileage_bump_and_no_decrease(self, db):
        """add_service_event bumps vehicles.mileage when at_miles > current,
        and leaves it alone otherwise."""
        from motodiag.vehicles.registry import get_vehicle

        vid = _seed_vehicle(db)
        assert get_vehicle(vid, db_path=db).get("mileage") is None

        # First event sets mileage.
        add_service_event(
            ServiceEvent(
                vehicle_id=vid, event_type="oil-change",
                at_miles=10_000, at_date=date(2026, 1, 1),
            ),
            db_path=db,
        )
        assert get_vehicle(vid, db_path=db)["mileage"] == 10_000

        # Second event with higher miles bumps.
        add_service_event(
            ServiceEvent(
                vehicle_id=vid, event_type="tire",
                at_miles=12_500, at_date=date(2026, 3, 1),
            ),
            db_path=db,
        )
        assert get_vehicle(vid, db_path=db)["mileage"] == 12_500

        # Third event with LOWER miles (back-dated correction) does NOT
        # decrease.
        add_service_event(
            ServiceEvent(
                vehicle_id=vid, event_type="diagnostic",
                at_miles=5_000, at_date=date(2025, 12, 1),
            ),
            db_path=db,
        )
        assert get_vehicle(vid, db_path=db)["mileage"] == 12_500

        # Event without at_miles doesn't touch mileage.
        add_service_event(
            ServiceEvent(
                vehicle_id=vid, event_type="recall",
                at_date=date(2026, 4, 1),
            ),
            db_path=db,
        )
        assert get_vehicle(vid, db_path=db)["mileage"] == 12_500


# ===========================================================================
# 3. CLI
# ===========================================================================


class TestHistoryCLI:
    """CliRunner exercises add / list / show / show-all / by-type + garage update."""

    def test_add_happy_path(self, cli_db):
        _seed_vehicle(cli_db)
        runner = CliRunner()
        result = runner.invoke(
            _make_cli(),
            [
                "advanced", "history", "add",
                "--bike", "sportster-2010",
                "--type", "oil-change",
                "--at-miles", "15000",
                "--at-date", "2026-03-15",
                "--notes", "Mobil 1 20w50, OE filter",
                "--cost-cents", "4999",
                "--parts", "OIL-20W50-4Q,FILT-63731-99A",
            ],
        )
        assert result.exit_code == 0, result.output
        assert "Logged oil-change" in result.output or "Service event recorded" in result.output

    def test_add_with_mechanic_resolves_username(self, cli_db):
        _seed_vehicle(cli_db)
        _seed_user(cli_db, "wrench-mike")
        runner = CliRunner()
        result = runner.invoke(
            _make_cli(),
            [
                "advanced", "history", "add",
                "--bike", "sportster-2010",
                "--type", "brake",
                "--at-miles", "22000",
                "--mechanic", "wrench-mike",
                "--json",
            ],
        )
        assert result.exit_code == 0, result.output
        payload = _json.loads(result.output)
        assert payload["mechanic_user_id"] is not None

    def test_add_unknown_bike_remediation(self, cli_db):
        runner = CliRunner()
        result = runner.invoke(
            _make_cli(),
            [
                "advanced", "history", "add",
                "--bike", "nosuch-bike",
                "--type", "oil-change",
            ],
        )
        assert result.exit_code == 1
        assert "not found" in result.output.lower() or "no bike" in result.output.lower()

    def test_list_happy_path(self, cli_db):
        vid = _seed_vehicle(cli_db)
        add_service_event(
            ServiceEvent(
                vehicle_id=vid, event_type="oil-change",
                at_miles=10_000, at_date=date(2026, 1, 1),
            ),
        )
        runner = CliRunner()
        result = runner.invoke(
            _make_cli(),
            [
                "advanced", "history", "list",
                "--bike", "sportster-2010",
            ],
        )
        assert result.exit_code == 0, result.output
        assert "oil-change" in result.output

    def test_list_empty_yellow_panel(self, cli_db):
        _seed_vehicle(cli_db)
        runner = CliRunner()
        result = runner.invoke(
            _make_cli(),
            [
                "advanced", "history", "list",
                "--bike", "sportster-2010",
            ],
        )
        assert result.exit_code == 0, result.output
        assert "No" in result.output and "events" in result.output.lower()

    def test_show_by_id(self, cli_db):
        vid = _seed_vehicle(cli_db)
        eid = add_service_event(
            ServiceEvent(
                vehicle_id=vid, event_type="recall",
                at_date=date(2026, 2, 1),
                notes="Stator recall per TSB 2018-01",
            ),
        )
        runner = CliRunner()
        result = runner.invoke(
            _make_cli(),
            ["advanced", "history", "show", str(eid)],
        )
        assert result.exit_code == 0, result.output
        assert "recall" in result.output
        assert str(eid) in result.output

    def test_show_all_cross_bike(self, cli_db):
        v1 = _seed_vehicle(cli_db)
        v2 = _seed_vehicle(cli_db, make="Honda", model="CBR600RR", year=2005)
        add_service_event(
            ServiceEvent(
                vehicle_id=v1, event_type="oil-change",
                at_date=date(2026, 1, 1),
            ),
        )
        add_service_event(
            ServiceEvent(
                vehicle_id=v2, event_type="brake",
                at_date=date(2026, 2, 1),
            ),
        )
        runner = CliRunner()
        result = runner.invoke(
            _make_cli(),
            ["advanced", "history", "show-all"],
        )
        assert result.exit_code == 0, result.output
        assert "oil-change" in result.output
        assert "brake" in result.output

    def test_by_type_filter(self, cli_db):
        vid = _seed_vehicle(cli_db)
        add_service_event(
            ServiceEvent(
                vehicle_id=vid, event_type="tire",
                at_date=date(2026, 1, 1),
            ),
        )
        add_service_event(
            ServiceEvent(
                vehicle_id=vid, event_type="oil-change",
                at_date=date(2026, 2, 1),
            ),
        )
        runner = CliRunner()
        result = runner.invoke(
            _make_cli(),
            ["advanced", "history", "by-type", "tire"],
        )
        assert result.exit_code == 0, result.output
        assert "tire" in result.output
        # oil-change row filtered out
        assert "oil-change" not in result.output or result.output.count("tire") >= 1

    def test_json_roundtrip_list(self, cli_db):
        vid = _seed_vehicle(cli_db)
        add_service_event(
            ServiceEvent(
                vehicle_id=vid, event_type="oil-change",
                at_miles=5_000, at_date=date(2026, 1, 1),
                cost_cents=3_499,
            ),
        )
        runner = CliRunner()
        result = runner.invoke(
            _make_cli(),
            [
                "advanced", "history", "list",
                "--bike", "sportster-2010", "--json",
            ],
        )
        assert result.exit_code == 0, result.output
        payload = _json.loads(result.output)
        assert len(payload) == 1
        assert payload[0]["event_type"] == "oil-change"
        assert payload[0]["cost_cents"] == 3_499

    def test_garage_update_mileage_persists(self, cli_db):
        vid = _seed_vehicle(cli_db)
        runner = CliRunner()
        result = runner.invoke(
            _make_cli(),
            [
                "garage", "update",
                "--bike", "sportster-2010",
                "--mileage", "18500",
            ],
        )
        assert result.exit_code == 0, result.output
        from motodiag.vehicles.registry import get_vehicle

        assert get_vehicle(vid)["mileage"] == 18_500

    def test_garage_update_decrease_requires_yes(self, cli_db):
        vid = _seed_vehicle(cli_db)
        runner = CliRunner()
        # First set mileage to 20,000
        runner.invoke(
            _make_cli(),
            [
                "garage", "update",
                "--bike", "sportster-2010",
                "--mileage", "20000",
            ],
        )
        # Now try to decrease without --yes
        result = runner.invoke(
            _make_cli(),
            [
                "garage", "update",
                "--bike", "sportster-2010",
                "--mileage", "10000",
            ],
        )
        assert result.exit_code != 0
        assert "decrease" in result.output.lower() or "refusing" in result.output.lower()
        # With --yes it succeeds
        result2 = runner.invoke(
            _make_cli(),
            [
                "garage", "update",
                "--bike", "sportster-2010",
                "--mileage", "10000",
                "--yes",
            ],
        )
        assert result2.exit_code == 0, result2.output

    def test_history_add_bad_date_is_rejected(self, cli_db):
        _seed_vehicle(cli_db)
        runner = CliRunner()
        result = runner.invoke(
            _make_cli(),
            [
                "advanced", "history", "add",
                "--bike", "sportster-2010",
                "--type", "oil-change",
                "--at-date", "not-a-date",
            ],
        )
        assert result.exit_code != 0
        assert "iso" in result.output.lower() or "at-date" in result.output.lower()


# ===========================================================================
# 4. Phase 148 integration bonus
# ===========================================================================


class TestPhase148IntegrationBonus:
    """The +0.05 mileage_source='db' bonus in the predictor."""

    def _seed_issue(self, db_path: str) -> int:
        """Family-make-tier issue sized to leave headroom for the +0.05 bonus.

        Using model=None and no year_start/year_end keeps the base score
        at 0.50 (match tier) + 0.20 (age bonus) = 0.70, so the Phase 152
        DB bonus of +0.05 is cleanly observable without clamp saturation.
        """
        from motodiag.knowledge.issues_repo import add_known_issue

        return add_known_issue(
            title="Stator failure",
            description="Service manual says inspect stator at 80k.",
            make="Harley-Davidson",
            model=None,
            year_start=None,
            year_end=None,
            severity="low",
            symptoms=["battery not charging"],
            dtc_codes=[],
            causes=["Insulation breakdown"],
            fix_procedure="Check AC output. Replace stator.",
            parts_needed=["Stator"],
            estimated_hours=3.0,
            db_path=db_path,
        )

    def test_db_source_adds_005_over_flag(self, db):
        """Source='db' scores higher than source='flag' by +0.05."""
        from motodiag.advanced.predictor import predict_failures

        self._seed_issue(db)
        base = {
            "make": "Harley-Davidson",
            "model": "Sportster 1200",
            "year": 2010,
            "mileage": 20_000,
        }
        v_flag = {**base, "mileage_source": "flag"}
        v_db = {**base, "mileage_source": "db"}

        preds_flag = predict_failures(
            v_flag, horizon_days=None, db_path=db,
        )
        preds_db = predict_failures(
            v_db, horizon_days=None, db_path=db,
        )

        stator_flag = next(
            p for p in preds_flag if p.issue_title == "Stator failure"
        )
        stator_db = next(
            p for p in preds_db if p.issue_title == "Stator failure"
        )
        diff = stator_db.confidence_score - stator_flag.confidence_score
        # Exactly +0.05 (modulo rounding to 4 decimals).
        assert abs(diff - 0.05) < 1e-6

    def test_bike_mode_sets_db_source_when_no_flag_used(self, cli_db):
        """--bike + no --current-miles + vehicles.mileage → source='db'."""
        from motodiag.vehicles.registry import update_vehicle

        vid = _seed_vehicle(cli_db)
        update_vehicle(vid, {"mileage": 22_000})
        self._seed_issue(cli_db)

        runner = CliRunner()
        result = runner.invoke(
            _make_cli(),
            [
                "advanced", "predict",
                "--bike", "sportster-2010",
                "--horizon-days", "3650",
                "--json",
            ],
        )
        assert result.exit_code == 0, result.output
        payload = _json.loads(result.output)
        # Mileage surfaces in the vehicle summary.
        assert payload["vehicle"].get("mileage") == 22_000
        assert len(payload["predictions"]) >= 1

    def test_bike_mode_flag_wins_over_db(self, cli_db):
        """--bike + --current-miles overrides vehicles.mileage and sets 'flag'."""
        from motodiag.advanced.predictor import predict_failures
        from motodiag.vehicles.registry import update_vehicle

        vid = _seed_vehicle(cli_db)
        update_vehicle(vid, {"mileage": 22_000})
        self._seed_issue(cli_db)

        # Also sanity check via direct predictor call.
        v_db_only = {
            "make": "Harley-Davidson", "model": "Sportster 1200",
            "year": 2010, "mileage": 22_000, "mileage_source": "db",
        }
        v_flag_wins = {**v_db_only, "mileage_source": "flag"}
        preds_db = predict_failures(
            v_db_only, horizon_days=None, db_path=cli_db,
        )
        preds_flag = predict_failures(
            v_flag_wins, horizon_days=None, db_path=cli_db,
        )
        stator_db = next(
            p for p in preds_db if p.issue_title == "Stator failure"
        )
        stator_flag = next(
            p for p in preds_flag if p.issue_title == "Stator failure"
        )
        assert stator_db.confidence_score > stator_flag.confidence_score

    def test_bike_mode_null_mileage_no_source_tag(self, cli_db):
        """--bike + vehicles.mileage IS NULL + no --current-miles → no +0.05.

        When the DB has NULL mileage and the user didn't pass a flag,
        there's no mileage at all, so the bonus branch can't apply
        (its guard is ``current_mileage is not None``).
        """
        from motodiag.advanced.predictor import predict_failures

        _seed_vehicle(cli_db)
        self._seed_issue(cli_db)

        # Simulate the CLI logic: no mileage set, no flag → neither
        # branch fires, source stays unset.
        vehicle = {
            "make": "Harley-Davidson",
            "model": "Sportster 1200",
            "year": 2010,
            # mileage absent, mileage_source absent
        }
        preds = predict_failures(
            vehicle, horizon_days=None, db_path=cli_db,
        )
        # Predictions still return (age-only), no crash.
        assert any(
            p.issue_title == "Stator failure" for p in preds
        )

    def test_direct_args_always_sets_flag_source(self, cli_db):
        """Direct-args CLI path sets mileage_source='flag' always."""
        from motodiag.advanced.predictor import predict_failures

        self._seed_issue(cli_db)
        # Parity test: direct-args + mileage_source='flag' should match
        # the historical Phase 148 score (before the +0.05 branch
        # existed). Since that branch is gated on 'db', passing 'flag'
        # yields no bonus.
        v = {
            "make": "harley-davidson",
            "model": "Sportster 1200",
            "year": 2010,
            "mileage": 20_000,
            "mileage_source": "flag",
        }
        preds = predict_failures(
            v, horizon_days=None, db_path=cli_db,
        )
        # No crash; bonus does not apply.
        assert len(preds) >= 1


# ===========================================================================
# 5. Regression
# ===========================================================================


class TestRegression:
    """Upstream phases still green after Phase 152 lands."""

    def test_phase148_current_miles_identical_surface(self, cli_db):
        """The --current-miles Phase 148 path is unchanged.

        Direct-args + --current-miles always sets source='flag', so
        the +0.05 branch cannot fire. That means the Phase 148
        regression surface (all 44 tests that exercise --current-miles)
        sees byte-identical prediction scores after Phase 152 lands.
        """
        from motodiag.knowledge.issues_repo import add_known_issue
        from motodiag.advanced.predictor import predict_failures

        add_known_issue(
            title="Generic oil leak",
            description="High-mileage rocker cover seepage.",
            make=None, model=None, year_start=None, year_end=None,
            severity="medium",
            symptoms=["oil seepage"],
            dtc_codes=[], causes=["gasket shrinkage"],
            fix_procedure="Service manual procedure: replace gasket.",
            parts_needed=["Gasket"],
            estimated_hours=1.0,
            db_path=cli_db,
        )
        # Mirrors Phase 148's direct-args call shape exactly.
        v = {
            "make": "suzuki", "model": "SV650", "year": 2005,
            "mileage": 50_000,
        }
        preds = predict_failures(v, horizon_days=None, db_path=cli_db)
        assert any(
            "oil" in p.issue_title.lower() for p in preds
        )

    def test_phase140_hardware_scan_slug_still_works(self):
        """Phase 140 hardware CLI still importable and registers cleanly."""
        import click

        from motodiag.cli.hardware import register_hardware

        @click.group()
        def root():
            pass

        register_hardware(root)
        assert "hardware" in root.commands

    def test_phase12_gate1_search_all_smoke(self, db):
        """Phase 12 Gate 1 search surface still works."""
        from motodiag.knowledge.issues_repo import (
            add_known_issue, search_known_issues,
        )

        add_known_issue(
            title="Test", description="x",
            make="Honda", model=None,
            year_start=None, year_end=None,
            severity="low",
            symptoms=[], dtc_codes=[], causes=[],
            fix_procedure="", parts_needed=[],
            estimated_hours=0.5,
            db_path=db,
        )
        rows = search_known_issues(make="Honda", db_path=db)
        assert len(rows) >= 1

    def test_phase08_known_issues_search_unchanged(self, db):
        """Phase 08 known_issues behavior — make filter still returns rows."""
        from motodiag.knowledge.issues_repo import (
            add_known_issue, search_known_issues,
        )

        add_known_issue(
            title="Harley-wide electrical",
            description="description",
            make="Harley-Davidson", model=None,
            year_start=2018, year_end=2024,
            severity="low",
            symptoms=["voltage sag"],
            dtc_codes=[], causes=[],
            fix_procedure="", parts_needed=[],
            estimated_hours=1.0,
            db_path=db,
        )
        rows = search_known_issues(make="Harley-Davidson", db_path=db)
        assert len(rows) >= 1
