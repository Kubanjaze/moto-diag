"""Phase 361 — F178's contract, and F177: a bike's engine type is never assumed.

F178, part 1b: the API accepted `hybrid_parallel` and `hybrid_series`, which
`PowertrainType` does not hold; create refused them and PATCH stored them
(`361_step0.md`, S0-3). The API's values are now the enum's, and
`update_vehicle` holds every writer to the enums.

F177, the operator's pick (2026-09-29): "(c). Keep the API's engine types
aligned to the code's five, and file rotary and diesel as a finding for a
later phase (until then such a bike is stored as unknown)."
- migration 075 removes the column's `DEFAULT 'four_stroke'`;
- `garage add` and `add-from-photo` ask for an engine type that is not
  given, unless the powertrain is electric; `unknown` stores NULL;
- the API stores NULL when the field is absent;
- every reader is tested on a bike stored as NULL.

Every database is a fresh one under `tmp_path`, never `data/motodiag.db`;
what was stored is read with plain SQL.
"""

from __future__ import annotations

import hashlib
import sqlite3
from types import SimpleNamespace

import pytest
from click.testing import CliRunner

from motodiag.cli.main import cli as main_cli
from motodiag.cli.theme import reset_console
from motodiag.core.config import reset_settings
from motodiag.core.database import SCHEMA_VERSION, get_connection, init_db
from motodiag.core.migrations import MIGRATIONS, apply_pending_migrations, rollback_to_version
from motodiag.core.models import EngineType, PowertrainType, VehicleBase
from motodiag.vehicles.registry import add_vehicle, get_vehicle, update_vehicle

MIGRATION = 75
WIDE = 10000

#: Migration 074's SQL as `5fb84a8` produced it, before Phase 361 gave its
#: helper an engine-type argument. 074 is applied live; its text must not move.
SHA256_074 = {
    "upgrade_sql": "b59b8ea2e4f275cbcf977db66563b344f3d8301afa453afd5a7aadc8117db774",
    "rollback_sql": "4f78892c5a5667ca45feeae6e481fa61d4ce9cafb99670ae34d41180d5814408",
}

#: The index SQL, byte for byte, as 074 left it (360's INDEX_SQL).
INDEX_SQL = {
    "idx_vehicles_make_model": "CREATE INDEX idx_vehicles_make_model ON vehicles(make, model)",
    "idx_vehicles_owner": "CREATE INDEX idx_vehicles_owner\n                ON vehicles(owner_user_id)",
    "idx_vehicles_year": "CREATE INDEX idx_vehicles_year ON vehicles(year)",
}

ENGINE_TYPES = ["four_stroke", "two_stroke", "electric_motor", "hybrid", "desmodromic"]


@pytest.fixture
def db(tmp_path):
    path = str(tmp_path / "phase361.db")
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


def _stored(db_path):
    return _sql(db_path, "SELECT model, powertrain, engine_type FROM vehicles ORDER BY id")


def assert_stored(db_path, want: list[tuple]):
    got = _stored(db_path)
    assert got == want, f"stored {got}, want {want}"


def _unknown_bike(db_path) -> int:
    """A bike stored with no powertrain and no engine type, through the registry."""
    return add_vehicle(VehicleBase(make="Honda", model="CHF50", year=2005), db_path=db_path)


class TestTheHelpersFailOnPlantedInput:
    def test_assert_stored_fails_on_an_assumed_four_stroke(self, db):
        _sql(db, "INSERT INTO vehicles (make, model, year, powertrain, engine_type) "
                 "VALUES ('Honda', 'CHF50', 2005, 'ice', 'four_stroke')")
        with pytest.raises(AssertionError):
            assert_stored(db, [("CHF50", "ice", None)])


# --------------------------------------------------------------- F178: the enums hold
class TestUpdateVehicleHoldsTheEnums:
    @pytest.mark.parametrize("field,value", [
        ("powertrain", "hybrid_parallel"), ("powertrain", "hybrid_series"),
        ("powertrain", ""), ("engine_type", "rotary"), ("engine_type", "diesel"),
        ("engine_type", "none"),
    ])
    def test_a_value_outside_the_enum_is_refused_and_nothing_changes(self, db, field, value):
        vid = add_vehicle(VehicleBase(make="Honda", model="CHF50", year=2005,
                                      powertrain=PowertrainType.ICE,
                                      engine_type=EngineType.FOUR_STROKE), db_path=db)
        with pytest.raises(ValueError):
            update_vehicle(vid, {field: value}, db_path=db)
        assert_stored(db, [("CHF50", "ice", "four_stroke")])

    @pytest.mark.parametrize("field,value", [
        ("powertrain", "hybrid"), ("powertrain", PowertrainType.ELECTRIC),
        ("engine_type", "two_stroke"), ("engine_type", EngineType.ELECTRIC_MOTOR),
    ])
    def test_the_enums_own_values_are_stored(self, db, field, value):
        vid = _unknown_bike(db)
        assert update_vehicle(vid, {field: value}, db_path=db)
        stored = _sql(db, f"SELECT {field} FROM vehicles WHERE id = ?", (vid,))[0][0]
        assert stored == getattr(value, "value", value)

    def test_none_clears_the_engine_type(self, db):
        vid = add_vehicle(VehicleBase(make="Honda", model="CHF50", year=2005,
                                      engine_type=EngineType.TWO_STROKE), db_path=db)
        assert update_vehicle(vid, {"engine_type": None}, db_path=db)
        assert _sql(db, "SELECT engine_type FROM vehicles") == [(None,)]


@pytest.fixture
def api_db(tmp_path, monkeypatch):
    path = str(tmp_path / "phase361_api.db")
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


BIKE = {"make": "Honda", "model": "CHF50", "year": 2005}


class TestTheApi:
    def test_a_hybrid_bike_can_be_created(self, api_db):
        client, headers = _api(api_db)
        r = client.post("/v1/vehicles", json={**BIKE, "powertrain": "hybrid"}, headers=headers)
        assert r.status_code == 201, r.text
        assert r.json()["powertrain"] == "hybrid"
        assert_stored(api_db, [("CHF50", "hybrid", None)])

    @pytest.mark.parametrize("field,value", [
        ("powertrain", "hybrid_parallel"), ("powertrain", "hybrid_series"),
        ("engine_type", "rotary"), ("engine_type", "diesel"), ("engine_type", "none"),
    ])
    def test_an_old_value_is_refused_on_create_and_update(self, api_db, field, value):
        client, headers = _api(api_db)
        r = client.post("/v1/vehicles", json={**BIKE, field: value}, headers=headers)
        assert r.status_code == 422, r.text
        vid = client.post("/v1/vehicles", json={**BIKE, "powertrain": "ice",
                                                "engine_type": "four_stroke"},
                          headers=headers).json()["id"]
        r = client.patch(f"/v1/vehicles/{vid}", json={field: value}, headers=headers)
        assert r.status_code == 422, r.text
        assert_stored(api_db, [("CHF50", "ice", "four_stroke")])

    @pytest.mark.parametrize("value", ENGINE_TYPES)
    def test_every_engine_type_in_the_enum_is_accepted(self, api_db, value):
        client, headers = _api(api_db)
        r = client.post("/v1/vehicles", json={**BIKE, "engine_type": value}, headers=headers)
        assert r.status_code == 201, r.text
        r = client.patch(f"/v1/vehicles/{r.json()['id']}", json={"engine_type": value},
                         headers=headers)
        assert r.status_code == 200, r.text
        assert _sql(api_db, "SELECT engine_type FROM vehicles") == [(value,)]

    def test_a_patch_to_hybrid_is_stored(self, api_db):
        client, headers = _api(api_db)
        vid = client.post("/v1/vehicles", json=BIKE, headers=headers).json()["id"]
        r = client.patch(f"/v1/vehicles/{vid}", json={"powertrain": "hybrid"}, headers=headers)
        assert r.status_code == 200, r.text
        assert_stored(api_db, [("CHF50", "hybrid", None)])

    def test_a_create_without_an_engine_type_stores_unknown(self, api_db):
        client, headers = _api(api_db)
        r = client.post("/v1/vehicles", json=BIKE, headers=headers)
        assert r.status_code == 201, r.text
        assert r.json()["engine_type"] is None
        assert_stored(api_db, [("CHF50", None, None)])

    def test_the_list_filter_takes_hybrid(self, api_db):
        client, headers = _api(api_db)
        client.post("/v1/vehicles", json={**BIKE, "powertrain": "hybrid"}, headers=headers)
        r = client.get("/v1/vehicles", params={"powertrain": "hybrid"}, headers=headers)
        assert r.status_code == 200, r.text
        assert [v["powertrain"] for v in r.json()["items"]] == ["hybrid"]
        r = client.get("/v1/vehicles", params={"powertrain": "hybrid_parallel"}, headers=headers)
        assert r.status_code == 422

    def test_the_schema_offers_the_enums_values(self):
        from motodiag.api import create_app

        schemas = create_app().openapi()["components"]["schemas"]

        def enum_of(schema, field):
            prop = schemas[schema]["properties"][field]
            options = prop.get("anyOf", [prop])
            return next(o["enum"] for o in options if "enum" in o)

        for schema in ("VehicleCreateRequest", "VehicleUpdateRequest"):
            assert enum_of(schema, "powertrain") == [p.value for p in PowertrainType]
            assert enum_of(schema, "engine_type") == [e.value for e in EngineType]
        assert "default" not in schemas["VehicleCreateRequest"]["properties"]["engine_type"]


# --------------------------------------------------------------- migration 075
def _engine_default(db_path) -> object:
    rows = _sql(db_path, "PRAGMA table_info(vehicles)")
    return next(r[4] for r in rows if r[1] == "engine_type")


def _all_rows(db_path):
    return _sql(db_path, "SELECT * FROM vehicles ORDER BY id")


def _seq(db_path):
    return _sql(db_path, "SELECT seq FROM sqlite_sequence WHERE name = 'vehicles'")


def _index_sql(db_path):
    return dict(_sql(db_path, "SELECT name, sql FROM sqlite_master "
                              "WHERE type = 'index' AND tbl_name = 'vehicles'"))


class TestMigration075:
    def test_the_head_is_at_least_075_and_the_last_migration(self):
        assert SCHEMA_VERSION >= MIGRATION
        assert SCHEMA_VERSION == max(m.version for m in MIGRATIONS)

    def test_migration_074s_sql_is_unchanged(self):
        m074 = next(m for m in MIGRATIONS if m.version == 74)
        for field, want in SHA256_074.items():
            assert hashlib.sha256(getattr(m074, field).encode()).hexdigest() == want, field

    def test_a_fresh_database_has_no_engine_type_default(self, db):
        assert _engine_default(db) is None

    def test_a_raw_insert_without_the_column_stores_unknown(self, db):
        _sql(db, "INSERT INTO vehicles (make, model, year) VALUES ('Honda', 'CHF50', 2005)")
        assert_stored(db, [("CHF50", None, None)])

    def test_the_indexes_keep_their_sql(self, db):
        assert _index_sql(db) == INDEX_SQL

    def test_every_row_and_the_sequence_survive_the_rebuild(self, db):
        rollback_to_version(MIGRATION - 1, db)
        assert _engine_default(db) == "'four_stroke'"
        _sql(db, "INSERT INTO vehicles (make, model, year, powertrain, engine_type, vin, "
                 "motor_kw, bms_present, mileage, transmission, notes) VALUES "
                 "('Harley-Davidson', 'Road King', 2012, 'ice', 'four_stroke', 'V1', "
                 "NULL, 0, 41000, 'manual', 'a note'), "
                 "('Zero', 'SR/S', 2024, 'electric', 'electric_motor', NULL, "
                 "82.0, 1, 900, 'direct_drive', NULL), "
                 "('Honda', 'CHF50', 2005, NULL, NULL, NULL, NULL, 0, NULL, NULL, NULL), "
                 "('Top', 'Deleted', 2020, 'ice', 'two_stroke', NULL, NULL, 0, NULL, "
                 "NULL, NULL)")
        _sql(db, "DELETE FROM vehicles WHERE make = 'Top'")
        with get_connection(db) as conn:
            vid = conn.execute("SELECT id FROM vehicles WHERE make = 'Zero'").fetchone()[0]
            conn.execute("INSERT INTO service_intervals (vehicle_id, item_slug, description, "
                         "every_miles) VALUES (?, 'oil', 'oil', 3000)", (vid,))
        before, seq = _all_rows(db), _seq(db)
        assert seq[0][0] > max(r[0] for r in before)          # the plant took

        assert apply_pending_migrations(db) == [
            m.version for m in MIGRATIONS if m.version >= MIGRATION]
        assert _all_rows(db) == before
        assert _seq(db) == seq
        assert _engine_default(db) is None
        assert _index_sql(db) == INDEX_SQL
        assert _sql(db, "PRAGMA foreign_key_check") == []
        assert _sql(db, "SELECT vehicle_id FROM service_intervals") == [(vid,)]

        rollback_to_version(MIGRATION - 1, db)
        assert _all_rows(db) == before
        assert _seq(db) == seq
        assert _engine_default(db) == "'four_stroke'"
        assert _index_sql(db) == INDEX_SQL

    def test_the_powertrain_keeps_no_default_either_way(self, db):
        """075's rollback restores 074's schema, not 073's: no `ice` default."""
        rollback_to_version(MIGRATION - 1, db)
        cols = {r[1]: r[4] for r in _sql(db, "PRAGMA table_info(vehicles)")}
        assert cols["powertrain"] is None


# --------------------------------------------------------------- the CLI
class TestGarageAdd:
    ADD = ("garage", "add", "--make", "Honda", "--model", "CHF50", "--year", "2005")

    def test_no_engine_type_asks_and_stores_the_answer(self, db):
        r = _cli(db, *self.ADD, "--powertrain", "ice", answers=["two_stroke"])
        assert r.exit_code == 0, r.output
        assert "Engine type" in r.output
        assert_stored(db, [("CHF50", "ice", "two_stroke")])

    def test_no_answer_saves_nothing(self, db):
        r = _cli(db, *self.ADD, "--powertrain", "ice")
        assert r.exit_code == 1
        assert "No engine type given: add --engine-type" in r.output
        assert "Nothing was saved" in r.output
        assert_stored(db, [])

    def test_unknown_stores_null(self, db):
        r = _cli(db, *self.ADD, "--powertrain", "ice", answers=["unknown"])
        assert r.exit_code == 0, r.output
        assert_stored(db, [("CHF50", "ice", None)])

    def test_a_given_engine_type_is_not_asked_for(self, db):
        r = _cli(db, *self.ADD, "--powertrain", "ice", "--engine-type", "four_stroke")
        assert r.exit_code == 0, r.output
        assert "Engine type" not in r.output
        assert_stored(db, [("CHF50", "ice", "four_stroke")])

    def test_electric_gives_an_electric_motor_without_asking(self, db):
        r = _cli(db, *self.ADD, "--powertrain", "electric")
        assert r.exit_code == 0, r.output
        assert "Engine type" not in r.output
        assert_stored(db, [("CHF50", "electric", "electric_motor")])

    def test_a_hybrid_is_asked_not_stored_four_stroke(self, db):
        r = _cli(db, *self.ADD, "--powertrain", "hybrid")
        assert r.exit_code == 1
        assert_stored(db, [])


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
        make="Honda", model="CHF50", year_range=(2004, 2006), engine_cc_range=None,
        powertrain_guess=guess_powertrain, confidence=0.9, reasoning="planted")
    monkeypatch.setattr(intake, "VehicleIdentifier", _FakeIdentifier)
    image = tmp_path / "bike.jpg"
    image.write_bytes(b"not really a jpeg")
    return _cli(db, "garage", "add-from-photo", str(image), "--yes", *args, answers=answers)


class TestAddFromPhoto:
    def test_no_engine_type_asks(self, db, tmp_path, monkeypatch):
        r = _photo(db, tmp_path, monkeypatch, "ice", answers=["four_stroke"])
        assert r.exit_code == 0, r.output
        assert "Engine type" in r.output
        assert_stored(db, [("CHF50", "ice", "four_stroke")])

    def test_no_answer_saves_nothing(self, db, tmp_path, monkeypatch):
        r = _photo(db, tmp_path, monkeypatch, "ice")
        assert r.exit_code == 1
        assert "No engine type given" in r.output
        assert_stored(db, [])

    def test_a_given_engine_type_is_stored(self, db, tmp_path, monkeypatch):
        r = _photo(db, tmp_path, monkeypatch, "ice", "--engine-type", "unknown")
        assert r.exit_code == 0, r.output
        assert_stored(db, [("CHF50", "ice", None)])

    def test_an_electric_guess_gives_an_electric_motor(self, db, tmp_path, monkeypatch):
        r = _photo(db, tmp_path, monkeypatch, "electric")
        assert r.exit_code == 0, r.output
        assert_stored(db, [("CHF50", "electric", "electric_motor")])


class TestGarageUpdate:
    def test_sets_and_clears_the_engine_type(self, db):
        _unknown_bike(db)
        r = _cli(db, "garage", "update", "--bike", "chf50-2005", "--engine-type", "two_stroke")
        assert r.exit_code == 0, r.output
        assert_stored(db, [("CHF50", None, "two_stroke")])
        r = _cli(db, "garage", "update", "--bike", "chf50-2005", "--engine-type", "unknown")
        assert r.exit_code == 0, r.output
        assert_stored(db, [("CHF50", None, None)])

    def test_an_old_value_is_not_a_choice(self, db):
        _unknown_bike(db)
        r = _cli(db, "garage", "update", "--bike", "chf50-2005", "--engine-type", "rotary")
        assert r.exit_code == 2
        assert_stored(db, [("CHF50", None, None)])


# --------------------------------------------------------------- the readers
class _Stop(Exception):
    pass


class TestReadersOnAnUnknownEngineType:
    def test_diagnose_passes_unknown_on(self, db, monkeypatch):
        from motodiag.cli import diagnose

        vehicle = get_vehicle(_unknown_bike(db), db_path=db)
        assert vehicle["engine_type"] is None
        seen: dict = {}

        def spy(**kwargs):
            seen.update(kwargs)
            raise _Stop()

        monkeypatch.setattr(diagnose, "_load_known_issues", lambda *a, **k: (None, []))
        with pytest.raises(_Stop):
            diagnose._run_quick(vehicle, ["no start"], None, "haiku", db_path=db,
                                diagnose_fn=spy)
        assert "engine_type" in seen and seen["engine_type"] is None

    def test_the_diagnose_prompt_leaves_the_engine_line_out(self, monkeypatch):
        from motodiag.engine import client as engine_client

        prompts: list[str] = []

        def ask(self, prompt, **k):
            prompts.append(prompt)
            raise _Stop()

        monkeypatch.setattr(engine_client.DiagnosticClient, "ask_structured", ask)
        client = engine_client.DiagnosticClient(api_key="sk-test-not-used")
        for engine_type in (None, "two_stroke"):
            with pytest.raises(_Stop):
                client.diagnose(make="Honda", model_name="CHF50", year=2005,
                                symptoms=["no start"], engine_type=engine_type,
                                use_cache=False)
        unknown, stated = prompts
        assert "Engine:" not in unknown
        assert "four_stroke" not in unknown
        assert "Engine: two_stroke" in stated              # control

    def test_the_cache_key_tells_unknown_from_four_stroke(self):
        from motodiag.engine.cache import _make_cache_key

        keys = {_make_cache_key("diagnose", {"engine_type": v}) for v in (None, "four_stroke")}
        assert len(keys) == 2

    def test_parts_sourcing_prints_unknown(self, db):
        from motodiag.shop import parts_sourcing

        vehicle = parts_sourcing._load_vehicle(_unknown_bike(db), db_path=db)
        prompt = parts_sourcing._build_user_prompt({"id": 1}, 1, vehicle, [], "balanced")
        line = next(ln for ln in prompt.splitlines() if "engine_type:" in ln)
        assert line.strip() == "engine_type: unknown"

    def test_the_api_read_returns_null(self, api_db):
        client, headers = _api(api_db)
        vid = client.post("/v1/vehicles", json=BIKE, headers=headers).json()["id"]
        r = client.get(f"/v1/vehicles/{vid}", headers=headers)
        assert r.status_code == 200
        assert r.json()["engine_type"] is None
