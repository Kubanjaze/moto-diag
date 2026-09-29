"""Phase 360 — F174: a bike's powertrain is never assumed.

Four paths stored `ice` when nobody stated it, and Step 0 found two more
(`360_step0.md`, S0-3). The operator's pick (2026-09-28): "1: (c). 2: (ii)."
- `garage add` and `garage add-from-photo` ask when no powertrain is given,
  and save nothing without an answer;
- the API stores NULL when the field is absent;
- migration 074 removes the column's `DEFAULT 'ice'`;
- `workflow start` on a bike stored as unknown stores the stated value.

Every reader is tested on a bike stored as NULL. Where unknown and `ice`
behave alike by design (retrieval only acts on `electric`), a spy shows the
reader passes `None` on, so a planted `or "ice"` fails. Every database is a
fresh one under `tmp_path`, never `data/motodiag.db`; what was stored is
read with plain SQL.
"""

from __future__ import annotations

import io
import json
import sqlite3
from types import SimpleNamespace

import pytest
from click.testing import CliRunner
from rich.console import Console

from motodiag.cli.main import cli as main_cli
from motodiag.cli.theme import reset_console
from motodiag.core.config import reset_settings
from motodiag.core.database import SCHEMA_VERSION, get_connection, init_db
from motodiag.core.migrations import MIGRATIONS, apply_pending_migrations, rollback_to_version
from motodiag.core.models import VehicleBase
from motodiag.vehicles.registry import add_vehicle, get_vehicle

MIGRATION = 74
WIDE = 10000

#: The index SQL before migration 074, byte for byte, as a fresh database
#: and the live one both held it on 2026-09-28 (`360_step0.md`).
INDEX_SQL = {
    "idx_vehicles_make_model": "CREATE INDEX idx_vehicles_make_model ON vehicles(make, model)",
    "idx_vehicles_owner": "CREATE INDEX idx_vehicles_owner\n                ON vehicles(owner_user_id)",
    "idx_vehicles_year": "CREATE INDEX idx_vehicles_year ON vehicles(year)",
}


@pytest.fixture
def db(tmp_path):
    path = str(tmp_path / "phase360.db")
    init_db(path)
    return path


def _cli(db_path, *args, answers=()):
    text = "".join(f"{a}\n" for a in answers)
    try:
        with pytest.MonkeyPatch.context() as mp:
            mp.setenv("MOTODIAG_DB_PATH", db_path)
            mp.setenv("COLUMNS", str(WIDE))
            reset_settings()
            reset_console()
            return CliRunner().invoke(main_cli, list(args), input=text)
    finally:
        reset_settings()
        reset_console()


def _sql(db_path, sql, params=()):
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute(sql, params).fetchall()
        conn.commit()
        return rows
    finally:
        conn.close()


def _unknown_bike(db_path, make="Zero", model="SR/S", year=2024) -> int:
    """A bike stored with no powertrain, through the registry itself."""
    return add_vehicle(VehicleBase(make=make, model=model, year=year), db_path=db_path)


def _powertrains(db_path):
    return _sql(db_path, "SELECT make, model, powertrain FROM vehicles ORDER BY id")


# --------------------------------------------------------------- checks
def assert_stored(db_path, want: list[tuple]):
    got = _powertrains(db_path)
    assert got == want, f"stored {got}, want {want}"


class TestTheHelpersFailOnPlantedInput:
    def test_assert_stored_fails_on_an_assumed_ice(self, db):
        _sql(db, "INSERT INTO vehicles (make, model, year, powertrain) "
                 "VALUES ('Zero', 'SR/S', 2024, 'ice')")
        with pytest.raises(AssertionError):
            assert_stored(db, [("Zero", "SR/S", None)])


# --------------------------------------------------------------- migration 074
def _schema_default(db_path) -> object:
    rows = _sql(db_path, "PRAGMA table_info(vehicles)")
    return next(r[4] for r in rows if r[1] == "powertrain")


def _all_rows(db_path):
    return _sql(db_path, "SELECT * FROM vehicles ORDER BY id")


def _seq(db_path):
    return _sql(db_path, "SELECT seq FROM sqlite_sequence WHERE name = 'vehicles'")


def _index_sql(db_path):
    return dict(_sql(db_path, "SELECT name, sql FROM sqlite_master "
                              "WHERE type = 'index' AND tbl_name = 'vehicles'"))


class TestMigration074:
    def test_the_head_is_at_least_074_and_the_last_migration(self):
        assert SCHEMA_VERSION >= MIGRATION
        assert SCHEMA_VERSION == max(m.version for m in MIGRATIONS)

    def test_a_fresh_database_has_no_powertrain_default(self, db):
        assert _schema_default(db) is None

    def test_a_raw_insert_without_the_column_stores_unknown(self, db):
        _sql(db, "INSERT INTO vehicles (make, model, year) VALUES ('Honda', 'CB500', 2020)")
        assert_stored(db, [("Honda", "CB500", None)])

    def test_the_indexes_keep_their_sql(self, db):
        assert _index_sql(db) == INDEX_SQL

    def test_every_row_and_the_sequence_survive_the_rebuild(self, db):
        rollback_to_version(MIGRATION - 1, db)
        assert _schema_default(db) == "'ice'"
        _sql(db, "INSERT INTO vehicles (make, model, year, powertrain, engine_type, vin, "
                 "motor_kw, bms_present, mileage, transmission, notes) VALUES "
                 "('Harley-Davidson', 'Road King', 2012, 'ice', 'four_stroke', 'V1', "
                 "NULL, 0, 41000, 'manual', 'a note'), "
                 "('Zero', 'SR/S', 2024, 'electric', 'electric_motor', NULL, "
                 "82.0, 1, 900, 'direct_drive', NULL), "
                 "('Honda', 'CB500', 2020, NULL, 'four_stroke', NULL, NULL, 0, NULL, "
                 "NULL, NULL), "
                 "('Top', 'Deleted', 2020, 'ice', 'four_stroke', NULL, NULL, 0, NULL, "
                 "NULL, NULL)")
        _sql(db, "DELETE FROM vehicles WHERE make = 'Top'")
        # A child row, so the rebuild runs with a table pointing at vehicles.
        with get_connection(db) as conn:
            vid = conn.execute("SELECT id FROM vehicles WHERE make = 'Zero'").fetchone()[0]
            conn.execute("INSERT INTO service_intervals (vehicle_id, item_slug, description, "
                         "every_miles) VALUES (?, 'oil', 'oil', 3000)", (vid,))
        before, seq = _all_rows(db), _seq(db)
        assert seq[0][0] > max(r[0] for r in before)          # the plant took

        assert apply_pending_migrations(db) == [MIGRATION]
        assert _all_rows(db) == before
        assert _seq(db) == seq
        assert _schema_default(db) is None
        assert _index_sql(db) == INDEX_SQL
        assert _sql(db, "PRAGMA foreign_key_check") == []
        assert _sql(db, "SELECT vehicle_id FROM service_intervals") == [(vid,)]

        rollback_to_version(MIGRATION - 1, db)
        assert _all_rows(db) == before
        assert _seq(db) == seq
        assert _schema_default(db) == "'ice'"
        assert _index_sql(db) == INDEX_SQL

    def test_a_new_bike_after_the_rebuild_does_not_reuse_a_deleted_id(self, db):
        rollback_to_version(MIGRATION - 1, db)
        _sql(db, "INSERT INTO vehicles (make, model, year) VALUES ('A', 'A', 2020), "
                 "('B', 'B', 2020)")
        _sql(db, "DELETE FROM vehicles WHERE make = 'B'")
        apply_pending_migrations(db)
        new = _unknown_bike(db)
        assert new == 3


# --------------------------------------------------------------- entry points
class TestGarageAdd:
    def test_no_powertrain_asks_and_stores_the_answer(self, db):
        r = _cli(db, "garage", "add", "--make", "Zero", "--model", "SR/S", "--year", "2024",
                 answers=["electric"])
        assert r.exit_code == 0, r.output
        assert "Powertrain" in r.output
        assert_stored(db, [("Zero", "SR/S", "electric")])
        assert _sql(db, "SELECT engine_type FROM vehicles") == [("electric_motor",)]

    def test_no_answer_saves_nothing(self, db):
        r = _cli(db, "garage", "add", "--make", "Zero", "--model", "SR/S", "--year", "2024")
        assert r.exit_code == 1
        assert "No powertrain given: add --powertrain" in r.output
        assert "Nothing was saved" in r.output
        assert_stored(db, [])

    def test_a_given_powertrain_is_not_asked_for(self, db):
        r = _cli(db, "garage", "add", "--make", "Honda", "--model", "CB500", "--year", "2020",
                 "--powertrain", "ice")
        assert r.exit_code == 0, r.output
        assert "Powertrain:" not in r.output
        assert_stored(db, [("Honda", "CB500", "ice")])


class _FakeIdentifier:
    guess = None

    def __init__(self, *a, **k):
        pass

    def identify(self, *a, **k):
        return _FakeIdentifier.guess


def _photo(db, tmp_path, monkeypatch, guess_powertrain, *args, answers=()):
    from motodiag import intake
    from motodiag.intake.models import VehicleGuess

    _FakeIdentifier.guess = VehicleGuess(
        make="Zero", model="SR/S", year_range=(2023, 2025), engine_cc_range=None,
        powertrain_guess=guess_powertrain, confidence=0.9, reasoning="planted")
    monkeypatch.setattr(intake, "VehicleIdentifier", _FakeIdentifier)
    image = tmp_path / "bike.jpg"
    image.write_bytes(b"not really a jpeg")
    return _cli(db, "garage", "add-from-photo", str(image), "--yes", *args, answers=answers)


class TestAddFromPhoto:
    def test_a_guess_without_a_powertrain_asks(self, db, tmp_path, monkeypatch):
        r = _photo(db, tmp_path, monkeypatch, None, answers=["electric"])
        assert r.exit_code == 0, r.output
        assert "Powertrain: unknown" in r.output
        assert_stored(db, [("Zero", "SR/S", "electric")])

    def test_no_answer_saves_nothing(self, db, tmp_path, monkeypatch):
        r = _photo(db, tmp_path, monkeypatch, None)
        assert r.exit_code == 1
        assert "No powertrain given" in r.output
        assert_stored(db, [])

    def test_a_person_wins_over_the_guess(self, db, tmp_path, monkeypatch):
        r = _photo(db, tmp_path, monkeypatch, "ice", "--powertrain", "electric")
        assert r.exit_code == 0, r.output
        assert_stored(db, [("Zero", "SR/S", "electric")])

    def test_a_guess_with_a_powertrain_is_stored_without_asking(self, db, tmp_path, monkeypatch):
        r = _photo(db, tmp_path, monkeypatch, "electric")
        assert r.exit_code == 0, r.output
        assert_stored(db, [("Zero", "SR/S", "electric")])


class TestTheVisionReply:
    @pytest.mark.parametrize("value,want", [
        (None, None), ("", None), ("gas", None), ("ice", "ice"),
        ("Electric ", "electric"), ("HYBRID", "hybrid"),
    ])
    def test_a_missing_or_unrecognised_guess_is_unknown(self, value, want):
        from motodiag.intake.vehicle_identifier import _powertrain_guess
        assert _powertrain_guess(value) == want

    def test_a_reply_without_the_key_is_unknown_not_ice(self):
        from motodiag.intake.vehicle_identifier import _parse_guess_json
        raw = json.dumps({"make": "Zero", "model": "SR/S", "year_low": 2023,
                          "year_high": 2025, "confidence": 0.8})
        assert _parse_guess_json(raw, "haiku", "h").powertrain_guess is None


@pytest.fixture
def api_db(tmp_path, monkeypatch):
    path = str(tmp_path / "phase360_api.db")
    init_db(path)
    monkeypatch.setenv("MOTODIAG_DB_PATH", path)
    monkeypatch.setenv("MOTODIAG_DATA_DIR", str(tmp_path))
    for tier in ("anonymous", "individual", "shop", "company"):
        monkeypatch.setenv(f"MOTODIAG_RATE_LIMIT_{tier.upper()}_PER_MINUTE", "9999")
    reset_settings()
    yield path
    reset_settings()


def _api(db_path):
    from fastapi.testclient import TestClient

    from motodiag.api import create_app
    from motodiag.auth.api_key_repo import create_api_key

    with get_connection(db_path) as conn:
        uid = int(conn.execute(
            "INSERT INTO users (username, email, tier, is_active) "
            "VALUES ('rider', 'rider@example.com', 'individual', 1)").lastrowid)
        conn.execute("INSERT INTO subscriptions (user_id, tier, status, current_period_end) "
                     "VALUES (?, 'shop', 'active', datetime('now', '+30 days'))", (uid,))
    _, key = create_api_key(uid, db_path=db_path)
    return TestClient(create_app(db_path_override=db_path)), {"X-API-Key": key}


class TestTheApi:
    def test_a_create_without_a_powertrain_stores_unknown(self, api_db):
        client, headers = _api(api_db)
        r = client.post("/v1/vehicles", json={"make": "Zero", "model": "SR/S", "year": 2024},
                        headers=headers)
        assert r.status_code == 201, r.text
        assert r.json()["powertrain"] is None
        assert_stored(api_db, [("Zero", "SR/S", None)])

    def test_a_given_powertrain_is_stored(self, api_db):
        client, headers = _api(api_db)
        r = client.post("/v1/vehicles", json={"make": "Zero", "model": "SR/S", "year": 2024,
                                              "powertrain": "electric"}, headers=headers)
        assert r.status_code == 201, r.text
        assert_stored(api_db, [("Zero", "SR/S", "electric")])

    def test_the_read_returns_unknown_as_null(self, api_db):
        client, headers = _api(api_db)
        vid = client.post("/v1/vehicles", json={"make": "Zero", "model": "SR/S",
                                                "year": 2024}, headers=headers).json()["id"]
        r = client.get(f"/v1/vehicles/{vid}", headers=headers)
        assert r.status_code == 200
        assert r.json()["powertrain"] is None


# --------------------------------------------------------------- the readers
class _Stop(Exception):
    pass


def _spy(captured: dict):
    def spy(*args, **kwargs):
        captured.update(kwargs)
        raise _Stop()
    return spy


class TestReadersOnAnUnknownBike:
    def test_garage_list_prints_unknown(self, db):
        _unknown_bike(db)
        r = _cli(db, "garage", "list")
        assert r.exit_code == 0, r.output
        line = next(ln for ln in r.output.splitlines() if "SR/S" in ln)
        assert "unknown" in line and "ice" not in line

    def test_diagnose_passes_unknown_on(self, db, monkeypatch):
        from motodiag.cli import diagnose

        vehicle = get_vehicle(_unknown_bike(db), db_path=db)
        seen: dict = {}
        monkeypatch.setattr(diagnose, "_load_known_issues", _spy(seen))
        with pytest.raises(_Stop):
            diagnose._run_quick(vehicle, ["no start"], None, "haiku", db_path=db,
                                diagnose_fn=lambda **k: None)
        assert "powertrain" in seen and seen["powertrain"] is None

    def test_diagnose_retrieval_gives_the_chokepoint_unknown(self, db, monkeypatch):
        from motodiag.cli import diagnose

        seen: dict = {}
        monkeypatch.setattr(diagnose, "known_issues_for_vehicle",
                            lambda *a, **k: (None, [{"id": 1, "year_start": None,
                                                     "year_end": None}]))
        monkeypatch.setattr(diagnose, "rows_for_machine", _spy(seen))
        with pytest.raises(_Stop):
            diagnose._load_known_issues("Zero", "SR/S", 2024, db, powertrain=None)
        assert "powertrain" in seen and seen["powertrain"] is None

    def test_unknown_is_not_resolved_as_electric(self):
        from motodiag.knowledge.transmission import resolve_transmission
        unknown = resolve_transmission("Zero", "SR/S", powertrain=None)
        electric = resolve_transmission("Zero", "SR/S", powertrain="electric")
        assert unknown.provenance != "powertrain-default"
        assert electric.provenance in ("powertrain-default", "model-sourced", "explicit")

    def test_the_predictor_passes_unknown_on(self, db, monkeypatch):
        from motodiag.advanced import predictor
        from motodiag.knowledge import retrieval
        from motodiag.knowledge.issues_repo import add_known_issue

        add_known_issue(title="Planted row", description="d", make="Zero", model="SR/S",
                        severity="medium", db_path=db)
        vehicle = get_vehicle(_unknown_bike(db), db_path=db)
        seen: dict = {}
        monkeypatch.setattr(retrieval, "rows_for_machine", _spy(seen))
        with pytest.raises(_Stop):
            predictor.predict_failures(vehicle, horizon_days=None, db_path=db)
        assert "powertrain" in seen and seen["powertrain"] is None

    def test_the_priority_scorer_reads_unknown_from_the_table(self, db, monkeypatch):
        from motodiag.knowledge import retrieval
        from motodiag.shop import priority_scorer

        vid = _unknown_bike(db)
        seen: dict = {}
        monkeypatch.setattr(retrieval, "rows_for_machine", _spy(seen))
        with pytest.raises(_Stop):
            priority_scorer._kb_candidates_for_vehicle(vid, db_path=db)
        assert "powertrain" in seen and seen["powertrain"] is None

    def _alerts(self, vehicle) -> str:
        from motodiag.cli import diagnose

        out = io.StringIO()
        response = SimpleNamespace(notes="fuel leak pooling under the carburettor",
                                   diagnoses=[])
        diagnose._render_safety(Console(file=out, width=200), response, vehicle=vehicle,
                                symptoms=[])
        return out.getvalue()

    def test_safety_shows_every_rule_for_an_unknown_bike(self, db):
        vehicle = get_vehicle(_unknown_bike(db), db_path=db)
        assert vehicle["powertrain"] is None
        assert "Fuel leak detected" in self._alerts(vehicle)

    def test_the_safety_check_can_tell_the_difference(self, db):
        """Control: the same text on a bike stated as electric does not show
        the combustion rule, so the test above is not passing by default."""
        vehicle = dict(get_vehicle(_unknown_bike(db), db_path=db), powertrain="electric")
        assert "Fuel leak detected" not in self._alerts(vehicle)

    def test_a_checker_for_unknown_compiles_every_rule(self):
        from motodiag.engine.safety import SAFETY_RULES, SafetyChecker
        assert len(SafetyChecker(powertrain=None)._compiled_rules) == len(SAFETY_RULES)


class TestWorkflowStartOnAnUnknownBike:
    SLUG = "brake_service_v1"

    def test_the_stated_value_is_stored_on_the_bike(self, db):
        vid = _unknown_bike(db)
        r = _cli(db, "workflow", "start", self.SLUG, "--vehicle-id", str(vid),
                 "--powertrain", "electric")
        assert f"Bike #{vid} had no powertrain on record; stored as electric, as stated." \
            in r.output
        assert_stored(db, [("Zero", "SR/S", "electric")])
        assert _sql(db, "SELECT vehicle_id, powertrain FROM workflow_runs") == [(vid, "electric")]

    def test_the_prompted_value_is_stored_too(self, db):
        vid = _unknown_bike(db)
        r = _cli(db, "workflow", "start", self.SLUG, "--vehicle-id", str(vid),
                 answers=["electric"])
        assert "stored as electric, as stated" in r.output
        assert_stored(db, [("Zero", "SR/S", "electric")])

    def test_a_bike_with_a_stored_value_is_not_rewritten(self, db):
        _sql(db, "INSERT INTO vehicles (make, model, year, powertrain) "
                 "VALUES ('Zero', 'SR/S', 2024, 'electric')")
        r = _cli(db, "workflow", "start", self.SLUG, "--vehicle-id", "1",
                 "--powertrain", "electric")
        assert "had no powertrain on record" not in r.output
        assert_stored(db, [("Zero", "SR/S", "electric")])

    def test_a_disagreeing_bike_is_still_refused(self, db):
        _sql(db, "INSERT INTO vehicles (make, model, year, powertrain) "
                 "VALUES ('Zero', 'SR/S', 2024, 'ice')")
        r = _cli(db, "workflow", "start", self.SLUG, "--vehicle-id", "1",
                 "--powertrain", "electric")
        assert r.exit_code == 1
        assert "is stored as ice, not electric. Nothing was saved." in r.output
        assert_stored(db, [("Zero", "SR/S", "ice")])
        assert _sql(db, "SELECT COUNT(*) FROM workflow_runs") == [(0,)]

    def test_a_template_that_does_not_cover_it_changes_nothing(self, db):
        """The coverage refusal comes first: nothing is stored on the bike."""
        from motodiag.workflows import get_template_by_slug
        slug = "valve_adjustment_v1"
        assert "electric" not in get_template_by_slug(slug, db)["applicable_powertrains"]
        vid = _unknown_bike(db)
        r = _cli(db, "workflow", "start", slug, "--vehicle-id", str(vid),
                 "--powertrain", "electric")
        assert r.exit_code == 1
        assert "covers ice, hybrid, not electric" in r.output
        assert_stored(db, [("Zero", "SR/S", None)])
