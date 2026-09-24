"""Phase 257B — the per-vehicle transmission field.

`vehicles.transmission` has existed since migration 063 (Phase 255) and the
resolver has always answered `explicit` first. Nothing a rider could reach
wrote the column, and the API's one retrieval door (video `/ask`) read it
with getattr on a context that had no such field — so every vehicle was
resolved from the lookup alone, and the 528 the lookup does not name failed
closed with no way out.

The machine used throughout is a Honda PCX150: the lookup says `cvt`
(model-sourced), so an explicit `manual` is visibly different from it and a
clear is visibly a return to it.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from motodiag.api import create_app
from motodiag.auth.api_key_repo import create_api_key
from motodiag.core.database import get_connection, init_db
from motodiag.core.session_repo import create_session_for_owner
from motodiag.knowledge import retrieval
from motodiag.knowledge.issues_repo import add_known_issue
from motodiag.knowledge.transmission import resolve_transmission
from motodiag.media.vision_types import (
    Grounding, GuidanceCandidate, GuidanceResponse,
)

SIX = ["manual", "cvt", "dct", "semi_auto_centrifugal",
       "semi_auto_actuated", "direct_drive"]
CVT_ROW = "Variator rollers flat-spotted"
MANUAL_ROW = "Clutch cable frayed"


@pytest.fixture
def api_db(tmp_path, monkeypatch):
    from motodiag.core.config import reset_settings

    db_path = str(tmp_path / "phase257B.db")
    init_db(db_path)
    monkeypatch.setenv("MOTODIAG_DB_PATH", db_path)
    monkeypatch.setenv("MOTODIAG_DATA_DIR", str(tmp_path))
    for tier in ("anonymous", "individual", "shop", "company"):
        monkeypatch.setenv(f"MOTODIAG_RATE_LIMIT_{tier.upper()}_PER_MINUTE", "9999")
    reset_settings()
    yield db_path
    reset_settings()


def _user(db_path, username="rider", tier="shop"):
    with get_connection(db_path) as conn:
        uid = int(conn.execute(
            "INSERT INTO users (username, email, tier, is_active) VALUES (?, ?, 'individual', 1)",
            (username, f"{username}@example.com")).lastrowid)
        conn.execute(
            "INSERT INTO subscriptions (user_id, tier, status, current_period_end) "
            "VALUES (?, ?, 'active', datetime('now', '+30 days'))", (uid, tier))
    _, key = create_api_key(uid, db_path=db_path)
    return uid, key


def _client(db_path):
    return TestClient(create_app(db_path_override=db_path))


def _pcx(c, key, **extra):
    body = {"make": "Honda", "model": "PCX150", "year": 2019, **extra}
    r = c.post("/v1/vehicles", json=body, headers={"X-API-Key": key})
    assert r.status_code == 201, r.text
    return r.json()


def _stored(db_path, vid):
    with get_connection(db_path) as conn:
        return conn.execute(
            "SELECT transmission FROM vehicles WHERE id = ?", (vid,),
        ).fetchone()[0]


# ---------------------------------------------------------------------------
# Finish line 1: stored, returned, set and cleared through the vehicle API
# ---------------------------------------------------------------------------


class TestTheApiStoresIt:
    def test_a_vehicle_created_without_it_is_unset(self, api_db):
        _, key = _user(api_db)
        v = _pcx(_client(api_db), key)
        assert v["transmission"] is None
        assert _stored(api_db, v["id"]) is None

    def test_a_vehicle_created_with_it_keeps_it(self, api_db):
        _, key = _user(api_db)
        c = _client(api_db)
        v = _pcx(c, key, transmission="cvt")
        assert v["transmission"] == "cvt"
        assert _stored(api_db, v["id"]) == "cvt"
        got = c.get(f"/v1/vehicles/{v['id']}", headers={"X-API-Key": key})
        assert got.json()["transmission"] == "cvt"

    @pytest.mark.parametrize("value", SIX)
    def test_every_value_round_trips(self, api_db, value):
        _, key = _user(api_db)
        c = _client(api_db)
        v = _pcx(c, key)
        r = c.patch(f"/v1/vehicles/{v['id']}", json={"transmission": value},
                    headers={"X-API-Key": key})
        assert r.status_code == 200, r.text
        assert r.json()["transmission"] == value
        assert _stored(api_db, v["id"]) == value

    def test_set_change_clear(self, api_db):
        _, key = _user(api_db)
        c = _client(api_db)
        vid = _pcx(c, key)["id"]
        h = {"X-API-Key": key}
        assert c.patch(f"/v1/vehicles/{vid}", json={"transmission": "manual"},
                       headers=h).json()["transmission"] == "manual"
        assert c.patch(f"/v1/vehicles/{vid}", json={"transmission": "dct"},
                       headers=h).json()["transmission"] == "dct"
        cleared = c.patch(f"/v1/vehicles/{vid}", json={"transmission": None},
                          headers=h)
        assert cleared.status_code == 200, cleared.text
        assert cleared.json()["transmission"] is None
        assert _stored(api_db, vid) is None

    def test_omitting_the_key_leaves_it_alone(self, api_db):
        """The clear is an explicit null, not an absent key."""
        _, key = _user(api_db)
        c = _client(api_db)
        vid = _pcx(c, key, transmission="manual")["id"]
        r = c.patch(f"/v1/vehicles/{vid}", json={"mileage": 1200},
                    headers={"X-API-Key": key})
        assert r.json()["mileage"] == 1200
        assert r.json()["transmission"] == "manual"

    def test_a_null_on_another_field_still_means_not_sent(self, api_db):
        """D3: only transmission honours null; notes keeps its old meaning."""
        _, key = _user(api_db)
        c = _client(api_db)
        vid = _pcx(c, key, notes="keep me")["id"]
        r = c.patch(f"/v1/vehicles/{vid}", json={"notes": None},
                    headers={"X-API-Key": key})
        assert r.json()["notes"] == "keep me"

    @pytest.mark.parametrize("bad", ["automatic", "semi_auto", "CVT ", ""])
    def test_an_off_enum_value_is_refused(self, api_db, bad):
        _, key = _user(api_db)
        c = _client(api_db)
        vid = _pcx(c, key)["id"]
        r = c.patch(f"/v1/vehicles/{vid}", json={"transmission": bad},
                    headers={"X-API-Key": key})
        assert r.status_code == 422
        r = c.post("/v1/vehicles", json={"make": "Honda", "model": "PCX150",
                                         "year": 2019, "transmission": bad},
                   headers={"X-API-Key": key})
        assert r.status_code == 422
        assert _stored(api_db, vid) is None

    def test_the_database_check_still_holds(self, api_db):
        with pytest.raises(sqlite3.IntegrityError):
            with get_connection(api_db) as conn:
                conn.execute(
                    "INSERT INTO vehicles (make, model, year, transmission) "
                    "VALUES ('Honda', 'PCX150', 2019, 'automatic')")

    def test_another_owner_cannot_set_it(self, api_db):
        _, key_a = _user(api_db, "a")
        _, key_b = _user(api_db, "b")
        c = _client(api_db)
        vid = _pcx(c, key_a)["id"]
        r = c.patch(f"/v1/vehicles/{vid}", json={"transmission": "manual"},
                    headers={"X-API-Key": key_b})
        assert r.status_code == 404
        assert _stored(api_db, vid) is None

    def test_existing_vehicles_are_untouched(self, api_db):
        """A row written the pre-257B way reads back unset, and setting a
        neighbour's value does not move a byte of it."""
        uid, key = _user(api_db)
        with get_connection(api_db) as conn:
            old = int(conn.execute(
                "INSERT INTO vehicles (make, model, year, owner_user_id, mileage) "
                "VALUES ('Yamaha', 'MT07', 2018, ?, 9000)", (uid,)).lastrowid)
            before = tuple(conn.execute(
                "SELECT * FROM vehicles WHERE id = ?", (old,)).fetchone())
        c = _client(api_db)
        got = c.get(f"/v1/vehicles/{old}", headers={"X-API-Key": key}).json()
        assert got["transmission"] is None
        vid = _pcx(c, key)["id"]
        c.patch(f"/v1/vehicles/{vid}", json={"transmission": "cvt"},
                headers={"X-API-Key": key})
        with get_connection(api_db) as conn:
            after = tuple(conn.execute(
                "SELECT * FROM vehicles WHERE id = ?", (old,)).fetchone())
        assert after == before

    def test_openapi_carries_the_six_values(self, api_db):
        """The app's types are generated from this; a bare string would
        type the field as `string` and lose the list."""
        spec = _client(api_db).get("/openapi.json").json()
        for name in ("VehicleCreateRequest", "VehicleUpdateRequest",
                     "VehicleResponse"):
            prop = spec["components"]["schemas"][name]["properties"]["transmission"]
            enums = [a.get("enum") for a in prop["anyOf"] if "enum" in a]
            assert enums == [SIX], (name, prop)


# ---------------------------------------------------------------------------
# Finish line 2: the vehicle's own value first; unset is today's behaviour
# ---------------------------------------------------------------------------


class TestTheResolverOrder:
    def test_explicit_beats_the_lookup(self):
        r = resolve_transmission("Honda", "PCX150", explicit="manual")
        assert (r.provenance, r.candidates) == ("explicit", frozenset({"manual"}))

    def test_unset_is_exactly_the_lookup(self):
        assert resolve_transmission("Honda", "PCX150", explicit=None) == \
            resolve_transmission("Honda", "PCX150")
        assert resolve_transmission("Honda", "PCX150").provenance == "model-sourced"

    def test_explicit_rescues_a_machine_the_lookup_does_not_name(self):
        assert resolve_transmission("Honda", "cbrf4i").provenance == "unknown"
        r = resolve_transmission("Honda", "cbrf4i", explicit="manual")
        assert r.provenance == "explicit"


# ---------------------------------------------------------------------------
# Wiring: the CLI diagnose door reads the stored value
# ---------------------------------------------------------------------------


class _Stop(Exception):
    pass


def _seed_rows(db_path):
    add_known_issue(title=CVT_ROW, description="d", make="Honda",
                    model="PCX150", db_path=db_path,
                    applicability={"transmission": ["cvt"]})
    add_known_issue(title=MANUAL_ROW, description="d", make="Honda",
                    model="PCX150", db_path=db_path,
                    applicability={"transmission": ["manual"]})


@pytest.fixture
def spy(monkeypatch):
    """Record every resolution the chokepoint makes, without changing it."""
    seen = []
    real = retrieval.rows_for_machine

    def _spy(rows, **kw):
        result = real(rows, **kw)
        seen.append(result.resolution)
        return result

    monkeypatch.setattr(retrieval, "rows_for_machine", _spy)
    return seen


class TestTheCliDoorReadsIt:
    def test_diagnose_uses_the_stored_value(self, tmp_path, monkeypatch):
        from motodiag.cli import diagnose
        from motodiag.core.models import VehicleBase, VehicleTransmission
        from motodiag.vehicles.registry import add_vehicle, get_vehicle

        db = str(tmp_path / "cli.db")
        init_db(db)
        _seed_rows(db)
        vid = add_vehicle(VehicleBase(
            make="Honda", model="PCX150", year=2019,
            transmission=VehicleTransmission.MANUAL), db_path=db)
        seen = {}

        def _diagnose_fn(**kw):
            seen["titles"] = sorted(r["title"] for r in kw["known_issues"])
            raise _Stop

        real = diagnose.rows_for_machine
        resolutions = []

        def _spy(rows, **kw):
            result = real(rows, **kw)
            resolutions.append(result.resolution)
            return result

        # diagnose.py imports the name at module top, so patch it there.
        monkeypatch.setattr(diagnose, "rows_for_machine", _spy)
        with pytest.raises(_Stop):
            diagnose._run_quick(vehicle=get_vehicle(vid, db), symptoms=["slips"],
                                description=None, ai_model="haiku",
                                db_path=db, diagnose_fn=_diagnose_fn)
        assert resolutions[-1].provenance == "explicit"
        assert MANUAL_ROW in seen["titles"] and CVT_ROW not in seen["titles"]


# ---------------------------------------------------------------------------
# Finish line 4: end to end through the real API
# ---------------------------------------------------------------------------


FAKE_ANSWER = GuidanceResponse(
    question_understood_as="Why does it slip under load?",
    answers_the_question=True,
    candidates=[GuidanceCandidate(
        candidate="Worn drive element",
        why_plausible="Slip under load is a drive-side symptom.",
        how_to_discriminate="Check engine speed against road speed.",
        grounding=Grounding.CROSS_PLATFORM,
        grounding_detail="drive slip",
    )],
    what_would_narrow_it=["Measure the slip."],
    not_established="Frames cannot measure slip.",
    observation_basis="1 frame.",
)


@pytest.fixture
def no_vision(monkeypatch):
    """Stub ffmpeg and the vision call; the signature follows the real one
    (244L), or the mock stops testing the call."""
    import motodiag.media.ffmpeg as ff
    from motodiag.media.vision_analysis_pipeline import VisionAnalyzer

    asked = []

    def _frames(video_path, output_dir, max_frames=60):
        f = Path(output_dir); f.mkdir(parents=True, exist_ok=True)
        p = f / "frame_001.jpg"; p.write_bytes(b"jpg")
        return [p]

    def _answer(self, frames, question, vehicle_context=None, known_issues=None,
                video_id=None, shop_id=None, db_path=None):
        asked.append(sorted(r["title"] for r in (known_issues or [])))
        return FAKE_ANSWER

    monkeypatch.setattr(ff, "extract_frames", _frames)
    monkeypatch.setattr(VisionAnalyzer, "answer_question_about_frames", _answer)
    return asked


class TestEndToEnd:
    def test_set_ask_clear_ask(self, api_db, tmp_path, no_vision, spy):
        """Set -> the diagnosis uses the rider's value -> clear -> back to
        the lookup. Every step through HTTP; only frames and the model call
        are stubbed."""
        uid, key = _user(api_db)
        h = {"X-API-Key": key}
        c = _client(api_db)
        _seed_rows(api_db)
        vid = _pcx(c, key)["id"]
        sid = create_session_for_owner(
            owner_user_id=uid, vehicle_make="Honda", vehicle_model="PCX150",
            vehicle_year=2019, vehicle_id=vid, db_path=api_db)
        mp4 = tmp_path / "v.mp4"
        mp4.write_bytes(b"not-a-real-mp4")
        with get_connection(api_db) as conn:
            video = int(conn.execute(
                """INSERT INTO videos (session_id, started_at, duration_ms, width,
                   height, file_size_bytes, file_path, sha256)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (sid, "2026-09-24T10:00:00Z", 5000, 1280, 720, 14, str(mp4),
                 "x" * 64)).lastrowid)

        def ask():
            r = c.post(f"/v1/sessions/{sid}/videos/{video}/ask",
                       json={"question": "Why does it slip under load?"},
                       headers=h)
            assert r.status_code == 200, r.text
            return spy[-1], no_vision[-1]

        res, titles = ask()
        assert res.provenance == "model-sourced"
        assert CVT_ROW in titles and MANUAL_ROW not in titles

        r = c.patch(f"/v1/vehicles/{vid}", json={"transmission": "manual"}, headers=h)
        assert r.json()["transmission"] == "manual"
        res, titles = ask()
        assert (res.provenance, res.candidates) == ("explicit", frozenset({"manual"}))
        assert MANUAL_ROW in titles and CVT_ROW not in titles

        r = c.patch(f"/v1/vehicles/{vid}", json={"transmission": None}, headers=h)
        assert r.json()["transmission"] is None
        res, titles = ask()
        assert res.provenance == "model-sourced"
        assert CVT_ROW in titles and MANUAL_ROW not in titles
