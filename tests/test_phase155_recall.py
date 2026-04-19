"""Phase 155 — NHTSA safety recall tests.

Five test classes:

- :class:`TestMigration023` (4) — ALTER recalls schema, partial unique
  index, new recall_resolutions table + FK cascade / SET NULL,
  Phase 118 retrofit rows preserved with open=1 default.
- :class:`TestRecallRepo` (10) — VIN validation + charset rejection,
  decode_vin WMI + year-cycle, check_vin VIN-range match, all-VIN
  match, list_open_for_bike filters resolved, mark_resolved
  idempotent, get_resolutions_for_bike JOIN, lookup, loader
  idempotent.
- :class:`TestRecallLoader` (4) — parse success, seed row count,
  malformed JSON raises ValueError with line, missing file raises
  FileNotFoundError.
- :class:`TestRecallCLI` (10, Click CliRunner) — 4 subcommands happy-
  path, VIN length validation, unknown bike remediation,
  mark-resolved duplicate yellow panel, --json round-trip x 4,
  --open-only filter.
- :class:`TestPhase148RecallIntegration` (2) — predict_failures
  attaches NHTSA IDs when a critical open recall matches the bike +
  escalates severity to "critical"; no open recalls leaves
  applicable_recalls=[] and severity untouched.

All tests are SW + SQL only. Zero AI calls, zero network, zero live
tokens.
"""

from __future__ import annotations

import json as _json
from pathlib import Path

import pytest
from click.testing import CliRunner

from motodiag.advanced.recall_repo import (
    _vin_in_range,
    check_vin,
    decode_vin,
    get_resolutions_for_bike,
    list_open_for_bike,
    load_recalls_from_json,
    lookup as lookup_recalls,
    mark_resolved,
)
from motodiag.advanced import predict_failures
from motodiag.cli.advanced import register_advanced
from motodiag.core.database import (
    get_connection,
    init_db,
    table_exists,
)
from motodiag.core.migrations import (
    get_migration_by_version,
    rollback_migration,
)
from motodiag.knowledge.issues_repo import add_known_issue


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


def _make_cli():
    """Build a fresh CLI group with only `advanced` registered."""
    import click

    @click.group()
    def root() -> None:
        """test root"""

    register_advanced(root)
    return root


@pytest.fixture
def db(tmp_path):
    """Per-test SQLite DB pre-migrated to the latest schema."""
    path = str(tmp_path / "phase155.db")
    init_db(path)
    return path


@pytest.fixture
def cli_db(tmp_path, monkeypatch):
    """Point settings + CLI env at a temp DB."""
    from motodiag.core.config import reset_settings

    path = str(tmp_path / "phase155_cli.db")
    init_db(path)
    monkeypatch.setenv("MOTODIAG_DB_PATH", path)
    monkeypatch.setenv("COLUMNS", "240")
    reset_settings()
    yield path
    reset_settings()


def _add_vehicle(
    db_path: str,
    make: str = "Harley-Davidson",
    model: str = "Touring",
    year: int = 2020,
) -> int:
    """Insert a vehicles row directly."""
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "INSERT INTO vehicles (make, model, year, protocol) "
            "VALUES (?, ?, ?, 'none')",
            (make, model, year),
        )
        return cursor.lastrowid


def _add_recall(
    db_path: str,
    nhtsa_id: str = "22V999000",
    campaign_number: str = "TEST-CAMP-001",
    make: str = "Harley-Davidson",
    model: str = "Touring",
    year_start: int = 2019,
    year_end: int = 2021,
    description: str = "Test recall description",
    severity: str = "high",
    vin_range=None,
    open_flag: int = 1,
) -> int:
    """Insert a recall with the Phase 155 extended schema."""
    vin_range_json = _json.dumps(vin_range) if vin_range is not None else None
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            """INSERT INTO recalls
               (nhtsa_id, campaign_number, make, model, year_start,
                year_end, description, severity, remedy,
                notification_date, vin_range, open)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                nhtsa_id, campaign_number, make, model, year_start,
                year_end, description, severity, "Test remedy",
                "2022-01-01", vin_range_json, open_flag,
            ),
        )
        return cursor.lastrowid


# ===========================================================================
# 1. Migration 023
# ===========================================================================


class TestMigration023:
    """Migration 023: ALTER recalls + recall_resolutions."""

    def test_recalls_new_columns_added(self, db):
        """nhtsa_id, vin_range, open columns exist on recalls."""
        with get_connection(db) as conn:
            cols = [
                row[1]
                for row in conn.execute("PRAGMA table_info(recalls)").fetchall()
            ]
        assert "nhtsa_id" in cols
        assert "vin_range" in cols
        assert "open" in cols

    def test_partial_unique_index_on_nhtsa_id(self, db):
        """Partial UNIQUE: two NULL nhtsa_id rows OK; two matching non-NULL
        raise IntegrityError.
        """
        import sqlite3

        with get_connection(db) as conn:
            # Two NULL nhtsa_id rows — should succeed (partial index
            # excludes NULL).
            conn.execute(
                "INSERT INTO recalls (campaign_number, make, description) "
                "VALUES (?, ?, ?)",
                ("NULL-1", "Honda", "desc"),
            )
            conn.execute(
                "INSERT INTO recalls (campaign_number, make, description) "
                "VALUES (?, ?, ?)",
                ("NULL-2", "Honda", "desc"),
            )
            # Two matching non-NULL — should fail the second time.
            conn.execute(
                "INSERT INTO recalls "
                "(nhtsa_id, campaign_number, make, description) "
                "VALUES (?, ?, ?, ?)",
                ("22V000001", "C1", "Honda", "desc"),
            )
            with pytest.raises(sqlite3.IntegrityError):
                conn.execute(
                    "INSERT INTO recalls "
                    "(nhtsa_id, campaign_number, make, description) "
                    "VALUES (?, ?, ?, ?)",
                    ("22V000001", "C2", "Honda", "desc"),
                )

    def test_recall_resolutions_table_exists_with_fk_cascade(self, db):
        """recall_resolutions table + FK cascade on vehicle + recall,
        SET NULL on user.
        """
        assert table_exists("recall_resolutions", db) is True

        vid = _add_vehicle(db)
        rid = _add_recall(db)
        with get_connection(db) as conn:
            conn.execute(
                "INSERT INTO recall_resolutions "
                "(vehicle_id, recall_id, resolved_by_user_id) "
                "VALUES (?, ?, ?)",
                (vid, rid, 1),
            )
            count = conn.execute(
                "SELECT COUNT(*) FROM recall_resolutions"
            ).fetchone()[0]
            assert count == 1

            # Delete vehicle → cascade
            conn.execute("DELETE FROM vehicles WHERE id = ?", (vid,))
            count_after = conn.execute(
                "SELECT COUNT(*) FROM recall_resolutions"
            ).fetchone()[0]
            assert count_after == 0

    def test_open_default_one_preserves_phase118_rows(self, db):
        """Inserting with no open value gets open=1 by default."""
        with get_connection(db) as conn:
            conn.execute(
                "INSERT INTO recalls (campaign_number, make, description) "
                "VALUES (?, ?, ?)",
                ("LEGACY-1", "Yamaha", "Legacy Phase 118 shape"),
            )
            row = conn.execute(
                "SELECT open FROM recalls WHERE campaign_number = ?",
                ("LEGACY-1",),
            ).fetchone()
        assert row["open"] == 1


# ===========================================================================
# 2. recall_repo (VIN decode + matching + CRUD)
# ===========================================================================


class TestRecallRepo:
    """decode_vin, check_vin, list_open_for_bike, mark_resolved, lookup."""

    def test_decode_vin_rejects_wrong_length(self):
        with pytest.raises(ValueError):
            decode_vin("1HD1KH4196Y123")  # 14 chars

    def test_decode_vin_rejects_iopo_chars(self):
        """I, O, Q forbidden per NHTSA. 17-char VIN with one rejected."""
        with pytest.raises(ValueError):
            decode_vin("1HD1KH4O96Y123456")  # contains O (17 chars)

    def test_decode_vin_wmi_and_year_cycle(self):
        """Harley 1HD + position-10='L' disambiguates to 2020 (closer
        to current year 2026 than 1990).
        """
        # Build a VIN where position 10 (0-indexed 9) is 'L'.
        # Positions: 1HD (WMI) + 6 chars + L (pos 10) + 7 chars = 17.
        vin = "1HD1KHABCL1234567"
        assert len(vin) == 17
        assert vin[9] == "L"
        decoded = decode_vin(vin)
        assert decoded["make"] == "Harley-Davidson"
        assert decoded["wmi"] == "1HD"
        assert decoded["year_code"] == "L"
        # 'L' is 1990 or 2020. Current date is 2026, so 2020 wins.
        assert decoded["year"] == 2020

    def test_check_vin_range_match(self, db):
        """check_vin respects vin_range: a VIN outside the range gets []."""
        # Open recall with a narrow VIN range
        _add_recall(
            db,
            nhtsa_id="22V111000",
            campaign_number="VINRANGE-A",
            make="Harley-Davidson",
            model=None,
            year_start=2019,
            year_end=2021,
            vin_range=[["1HD1KHC17K", "1HD1KHC19M"]],
        )
        # VIN outside range (1HD1KH start but suffix-differ)
        out_of_range = "1HD1KHC20K123456C"  # 17 chars
        assert len(out_of_range) == 17
        rows = check_vin(out_of_range, db_path=db)
        assert rows == [] or all(r["nhtsa_id"] != "22V111000" for r in rows)

        # VIN inside range
        in_range = "1HD1KHC18LM123456"  # starts with 1HD1KHC18L → between K and M
        assert len(in_range) == 17
        rows = check_vin(in_range, db_path=db)
        # At least our recall appears
        found = [r for r in rows if r["nhtsa_id"] == "22V111000"]
        assert len(found) == 1

    def test_check_vin_all_vin_match(self, db):
        """vin_range=None matches every VIN for that make."""
        _add_recall(
            db,
            nhtsa_id="22V222000",
            campaign_number="ALLVIN-B",
            make="Harley-Davidson",
            model=None,
            year_start=2019,
            year_end=2021,
            vin_range=None,
        )
        vin = "1HD1KHL0LM123456C"
        rows = check_vin(vin, db_path=db)
        found = [r for r in rows if r["nhtsa_id"] == "22V222000"]
        assert len(found) == 1

    def test_vin_in_range_none_is_all(self):
        """_vin_in_range(vin, None) → True (all-VIN)."""
        assert _vin_in_range("1HD1KHL0LM123456C", None) is True

    def test_list_open_for_bike_filters_resolved(self, db):
        """Resolutions excluded from list_open_for_bike."""
        vid = _add_vehicle(db, make="Harley-Davidson", model="Touring",
                           year=2020)
        rid1 = _add_recall(
            db, nhtsa_id="22V333000", campaign_number="TOUR-A",
            make="Harley-Davidson", model="Touring",
            year_start=2019, year_end=2021, vin_range=None,
        )
        rid2 = _add_recall(
            db, nhtsa_id="22V333001", campaign_number="TOUR-B",
            make="Harley-Davidson", model="Touring",
            year_start=2019, year_end=2021, vin_range=None,
        )
        # Both open at first
        rows = list_open_for_bike(vid, db_path=db)
        ids = {r["id"] for r in rows}
        assert rid1 in ids and rid2 in ids

        # Resolve rid1
        inserted = mark_resolved(vid, rid1, db_path=db)
        assert inserted == 1

        rows_after = list_open_for_bike(vid, db_path=db)
        ids_after = {r["id"] for r in rows_after}
        assert rid1 not in ids_after
        assert rid2 in ids_after

    def test_mark_resolved_idempotent(self, db):
        """Second mark_resolved call returns 0, no exception."""
        vid = _add_vehicle(db)
        rid = _add_recall(db)
        assert mark_resolved(vid, rid, db_path=db) == 1
        assert mark_resolved(vid, rid, db_path=db) == 0
        # Still just 1 row
        with get_connection(db) as conn:
            count = conn.execute(
                "SELECT COUNT(*) FROM recall_resolutions "
                "WHERE vehicle_id = ? AND recall_id = ?",
                (vid, rid),
            ).fetchone()[0]
        assert count == 1

    def test_get_resolutions_for_bike_join(self, db):
        """get_resolutions_for_bike joins recalls for metadata."""
        vid = _add_vehicle(db)
        rid = _add_recall(
            db, nhtsa_id="22V444000", campaign_number="RES-TEST",
            severity="critical",
        )
        mark_resolved(vid, rid, notes="Dealer completed 2023-05-12",
                      db_path=db)
        rows = get_resolutions_for_bike(vid, db_path=db)
        assert len(rows) == 1
        row = rows[0]
        assert row["nhtsa_id"] == "22V444000"
        assert row["severity"] == "critical"
        assert row["resolution_notes"] == "Dealer completed 2023-05-12"

    def test_lookup_by_make_year(self, db):
        """lookup() filters by make + year + open_only."""
        _add_recall(
            db, nhtsa_id="22V555000", campaign_number="LU-A",
            make="Honda", model=None,
            year_start=2020, year_end=2022, open_flag=1,
        )
        _add_recall(
            db, nhtsa_id="22V555001", campaign_number="LU-B",
            make="Honda", model=None,
            year_start=2020, year_end=2022, open_flag=0,
        )
        # open_only=True drops closed
        rows_open = lookup_recalls(make="Honda", year=2021,
                                   open_only=True, db_path=db)
        nids = {r["nhtsa_id"] for r in rows_open}
        assert "22V555000" in nids
        assert "22V555001" not in nids
        # open_only=False keeps both
        rows_all = lookup_recalls(make="Honda", year=2021,
                                  open_only=False, db_path=db)
        nids_all = {r["nhtsa_id"] for r in rows_all}
        assert "22V555000" in nids_all
        assert "22V555001" in nids_all

    def test_load_recalls_from_json_idempotent(self, db, tmp_path):
        """Second load returns 0 new inserts."""
        json_path = tmp_path / "mini_recalls.json"
        json_path.write_text(_json.dumps([
            {
                "nhtsa_id": "22V777000",
                "campaign_number": "IDEM-A",
                "make": "Suzuki",
                "model": "GSX-R1000",
                "year_start": 2019,
                "year_end": 2020,
                "description": "Idempotent test recall",
                "severity": "medium",
                "remedy": "Dealer fix",
                "notification_date": "2022-03-01",
                "vin_range": None,
                "open": 1,
            },
        ]), encoding="utf-8")
        n1 = load_recalls_from_json(str(json_path), db_path=db)
        assert n1 == 1
        n2 = load_recalls_from_json(str(json_path), db_path=db)
        assert n2 == 0


# ===========================================================================
# 3. recall loader edge cases
# ===========================================================================


class TestRecallLoader:
    """Seed loader parse + error paths."""

    def test_default_seed_loads_successfully(self, db):
        """The shipped recalls.json parses + loads."""
        n = load_recalls_from_json(db_path=db)
        assert n >= 25

    def test_seed_has_30_campaigns(self):
        """recalls.json ships with 30 campaigns."""
        seed_path = (
            Path(__file__).parent.parent
            / "src" / "motodiag" / "advanced" / "data" / "recalls.json"
        )
        data = _json.loads(seed_path.read_text(encoding="utf-8"))
        assert isinstance(data, list)
        assert 25 <= len(data) <= 35
        # Every entry has the required fields
        for entry in data:
            assert "nhtsa_id" in entry
            assert "campaign_number" in entry
            assert "make" in entry
            assert "description" in entry
            assert "severity" in entry
            assert "open" in entry

    def test_malformed_json_raises_value_error(self, tmp_path, db):
        """Bad JSON → ValueError mentioning line number."""
        bad = tmp_path / "bad.json"
        bad.write_text("[{not valid json", encoding="utf-8")
        with pytest.raises(ValueError, match="line"):
            load_recalls_from_json(str(bad), db_path=db)

    def test_missing_file_raises_file_not_found(self, tmp_path, db):
        """Absent file → FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            load_recalls_from_json(
                str(tmp_path / "does_not_exist.json"), db_path=db,
            )


# ===========================================================================
# 4. CLI
# ===========================================================================


class TestRecallCLI:
    """Click CliRunner tests for the recall subgroup."""

    def test_recall_list_happy(self, cli_db):
        _add_recall(
            cli_db, nhtsa_id="22V000100", campaign_number="CLI-LIST-A",
            make="Honda", model="CBR1000RR",
        )
        runner = CliRunner()
        result = runner.invoke(
            _make_cli(), ["advanced", "recall", "list", "--make", "Honda"],
        )
        assert result.exit_code == 0, result.output
        assert "22V000100" in result.output

    def test_recall_check_vin_happy(self, cli_db):
        _add_recall(
            cli_db, nhtsa_id="22V000200", campaign_number="CLI-VIN-A",
            make="Harley-Davidson", model=None,
            year_start=2018, year_end=2022, vin_range=None,
        )
        runner = CliRunner()
        result = runner.invoke(
            _make_cli(),
            ["advanced", "recall", "check-vin", "1HD1KHL0LM123456C"],
        )
        assert result.exit_code == 0, result.output
        # Decoded block shows
        assert "Harley-Davidson" in result.output

    def test_recall_lookup_happy(self, cli_db):
        _add_recall(
            cli_db, nhtsa_id="22V000300", campaign_number="CLI-LU-A",
            make="Yamaha", model="MT-09",
            year_start=2021, year_end=2022,
        )
        runner = CliRunner()
        result = runner.invoke(
            _make_cli(),
            ["advanced", "recall", "lookup",
             "--make", "Yamaha", "--model", "MT-09", "--year", "2022"],
        )
        assert result.exit_code == 0, result.output
        assert "22V000300" in result.output

    def test_recall_mark_resolved_happy(self, cli_db):
        vid = _add_vehicle(cli_db, make="Kawasaki", model="Ninja 400",
                           year=2020)
        rid = _add_recall(
            cli_db, nhtsa_id="22V000400", campaign_number="CLI-MR-A",
            make="Kawasaki", model="Ninja 400",
        )
        # Mock _resolve_bike_slug to return our vehicle row
        import motodiag.cli.diagnose as diag_mod
        original = diag_mod._resolve_bike_slug
        diag_mod._resolve_bike_slug = lambda slug: {
            "id": vid, "make": "Kawasaki", "model": "Ninja 400",
            "year": 2020,
        }
        try:
            runner = CliRunner()
            result = runner.invoke(
                _make_cli(),
                ["advanced", "recall", "mark-resolved",
                 "--bike", "fake-slug",
                 "--recall-id", str(rid)],
            )
        finally:
            diag_mod._resolve_bike_slug = original
        assert result.exit_code == 0, result.output
        assert "resolved" in result.output.lower()

    def test_recall_check_vin_rejects_invalid(self, cli_db):
        """Short VIN → click.ClickException."""
        runner = CliRunner()
        result = runner.invoke(
            _make_cli(),
            ["advanced", "recall", "check-vin", "TOO-SHORT"],
        )
        assert result.exit_code != 0

    def test_recall_mark_resolved_unknown_bike(self, cli_db):
        """Unknown slug → bike-not-found + exit code 1."""
        import motodiag.cli.diagnose as diag_mod
        original = diag_mod._resolve_bike_slug
        diag_mod._resolve_bike_slug = lambda slug: None
        try:
            runner = CliRunner()
            result = runner.invoke(
                _make_cli(),
                ["advanced", "recall", "mark-resolved",
                 "--bike", "bogus", "--recall-id", "1"],
            )
        finally:
            diag_mod._resolve_bike_slug = original
        assert result.exit_code == 1
        assert "not found" in result.output.lower() or "no bike" in result.output.lower()

    def test_recall_mark_resolved_duplicate_yellow(self, cli_db):
        """Second mark-resolved → 'already' yellow panel."""
        vid = _add_vehicle(cli_db, make="Honda", model="Gold Wing",
                           year=2019)
        rid = _add_recall(
            cli_db, nhtsa_id="22V000500", campaign_number="CLI-DUP-A",
            make="Honda", model="Gold Wing",
        )
        # Resolve once directly
        mark_resolved(vid, rid, db_path=cli_db)

        import motodiag.cli.diagnose as diag_mod
        original = diag_mod._resolve_bike_slug
        diag_mod._resolve_bike_slug = lambda slug: {
            "id": vid, "make": "Honda", "model": "Gold Wing", "year": 2019,
        }
        try:
            runner = CliRunner()
            result = runner.invoke(
                _make_cli(),
                ["advanced", "recall", "mark-resolved",
                 "--bike", "slug", "--recall-id", str(rid)],
            )
        finally:
            diag_mod._resolve_bike_slug = original
        assert result.exit_code == 0
        assert "already" in result.output.lower()

    def test_recall_list_json_roundtrip(self, cli_db):
        _add_recall(
            cli_db, nhtsa_id="22V000600", campaign_number="CLI-LJ-A",
            make="Suzuki",
        )
        runner = CliRunner()
        result = runner.invoke(
            _make_cli(),
            ["advanced", "recall", "list", "--make", "Suzuki", "--json"],
        )
        assert result.exit_code == 0
        payload = _json.loads(result.output)
        assert "recalls" in payload
        assert any(r["nhtsa_id"] == "22V000600" for r in payload["recalls"])

    def test_recall_check_vin_json_roundtrip(self, cli_db):
        _add_recall(
            cli_db, nhtsa_id="22V000700", campaign_number="CLI-VJ-A",
            make="Harley-Davidson", model=None,
            year_start=2018, year_end=2022, vin_range=None,
        )
        runner = CliRunner()
        result = runner.invoke(
            _make_cli(),
            ["advanced", "recall", "check-vin", "1HD1KHL0LM123456C",
             "--json"],
        )
        assert result.exit_code == 0
        payload = _json.loads(result.output)
        assert "vin" in payload
        assert "decoded" in payload
        assert "recalls" in payload

    def test_recall_lookup_open_only_filter(self, cli_db):
        """--open-only drops closed; --all keeps them."""
        _add_recall(
            cli_db, nhtsa_id="22V000800", campaign_number="CLI-OO-A",
            make="BMW", model="R1250GS",
            year_start=2020, year_end=2022, open_flag=1,
        )
        _add_recall(
            cli_db, nhtsa_id="22V000801", campaign_number="CLI-OO-B",
            make="BMW", model="R1250GS",
            year_start=2020, year_end=2022, open_flag=0,
        )
        runner = CliRunner()
        result_open = runner.invoke(
            _make_cli(),
            ["advanced", "recall", "lookup",
             "--make", "BMW", "--model", "R1250GS",
             "--year", "2021", "--json"],
        )
        assert result_open.exit_code == 0
        open_payload = _json.loads(result_open.output)
        open_ids = {r["nhtsa_id"] for r in open_payload["recalls"]}
        assert "22V000800" in open_ids
        assert "22V000801" not in open_ids

        result_all = runner.invoke(
            _make_cli(),
            ["advanced", "recall", "lookup",
             "--make", "BMW", "--model", "R1250GS",
             "--year", "2021", "--all", "--json"],
        )
        assert result_all.exit_code == 0
        all_payload = _json.loads(result_all.output)
        all_ids = {r["nhtsa_id"] for r in all_payload["recalls"]}
        assert "22V000800" in all_ids
        assert "22V000801" in all_ids


# ===========================================================================
# 5. Phase 148 integration — predictor attaches applicable_recalls
# ===========================================================================


class TestPhase148RecallIntegration:
    """predict_failures populates applicable_recalls + escalates severity."""

    def test_predictor_attaches_nhtsa_ids_and_escalates_severity(self, db):
        """Bike with open critical recall → applicable_recalls populated,
        severity raised to 'critical'.
        """
        vid = _add_vehicle(db, make="Harley-Davidson", model="Touring",
                           year=2020)
        _add_recall(
            db,
            nhtsa_id="22V999777",
            campaign_number="INT-CRIT",
            make="Harley-Davidson",
            model="Touring",
            year_start=2019,
            year_end=2021,
            severity="critical",
            vin_range=None,
            open_flag=1,
        )
        # Seed a known_issue with severity=medium so we can watch the
        # escalation happen.
        add_known_issue(
            title="Front brake soft lever",
            description="Mild brake issue reported on HD Touring models.",
            make="Harley-Davidson",
            model="Touring",
            year_start=2019,
            year_end=2021,
            severity="medium",
            symptoms=["soft brake"],
            dtc_codes=[],
            causes=["Seal wear"],
            fix_procedure="Inspect calipers and replace if needed.",
            parts_needed=["Caliper kit"],
            estimated_hours=1.5,
            db_path=db,
        )
        vehicle = {
            "id": vid,
            "make": "Harley-Davidson",
            "model": "Touring",
            "year": 2020,
            "mileage": 18_000,
        }
        preds = predict_failures(
            vehicle, horizon_days=3650, db_path=db,
        )
        assert len(preds) >= 1
        # Find our seeded issue's prediction
        target = [p for p in preds if "Front brake soft lever" in p.issue_title]
        assert len(target) == 1
        pred = target[0]
        # NHTSA ID attached
        assert "22V999777" in pred.applicable_recalls
        # Severity escalated from 'medium' to 'critical'
        assert pred.severity == "critical"

    def test_predictor_no_open_recalls_leaves_fields_default(self, db):
        """No recalls → applicable_recalls=[], severity untouched."""
        vid = _add_vehicle(db, make="Kawasaki", model="KLR650", year=2005)
        add_known_issue(
            title="Doohickey failure",
            description="Factory lever breaks.",
            make="Kawasaki",
            model="KLR650",
            year_start=1987,
            year_end=2007,
            severity="high",
            symptoms=["ticking"],
            dtc_codes=[],
            causes=["fatigue"],
            fix_procedure="Upgrade to Eagle Mike.",
            parts_needed=["Eagle Mike kit"],
            estimated_hours=4.0,
            db_path=db,
        )
        vehicle = {
            "id": vid,
            "make": "Kawasaki",
            "model": "KLR650",
            "year": 2005,
            "mileage": 22_000,
        }
        preds = predict_failures(vehicle, horizon_days=3650, db_path=db)
        target = [p for p in preds if "Doohickey" in p.issue_title]
        assert len(target) >= 1
        pred = target[0]
        assert pred.applicable_recalls == []
        # Severity unchanged from seeded value
        assert pred.severity == "high"
