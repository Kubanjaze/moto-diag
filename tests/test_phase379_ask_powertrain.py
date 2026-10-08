"""Phase 379, F144 — video `/ask` passes the vehicle's powertrain to retrieval.

`/ask` called `rows_for_machine(powertrain=getattr(context, "powertrain",
None))`, and `VehicleContext` had no `powertrain`, so it was None for every
vehicle. An electric machine the lookup does not name therefore resolved
`unknown` in `/ask` and `powertrain-default` in `motodiag diagnose`. Now the
context carries the vehicle row's powertrain, as 257B made it carry the
transmission.

`VehicleContext` is not in the mobile OpenAPI snapshot (379's Step 0), and
gate 11 holds the snapshot.
"""

from __future__ import annotations

from motodiag.core.database import get_connection
from motodiag.core.session_repo import create_session_for_owner
from test_phase257B_transmission_field import (  # noqa: F401  (fixtures)
    _client, _user, api_db, no_vision, spy,
)


def _ask(api_db, tmp_path, make, model, powertrain, spy):
    uid, key = _user(api_db)
    c = _client(api_db)
    r = c.post("/v1/vehicles", json={"make": make, "model": model, "year": 2020,
                                     "powertrain": powertrain},
               headers={"X-API-Key": key})
    assert r.status_code == 201, r.text
    vid = r.json()["id"]
    sid = create_session_for_owner(owner_user_id=uid, vehicle_make=make,
                                   vehicle_model=model, vehicle_year=2020,
                                   vehicle_id=vid, db_path=api_db)
    mp4 = tmp_path / "v.mp4"
    mp4.write_bytes(b"not-a-real-mp4")
    with get_connection(api_db) as conn:
        video = int(conn.execute(
            """INSERT INTO videos (session_id, started_at, duration_ms, width, height,
               file_size_bytes, file_path, sha256) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (sid, "2026-10-08T10:00:00Z", 5000, 1280, 720, 14, str(mp4),
             "x" * 64)).lastrowid)
    r = c.post(f"/v1/sessions/{sid}/videos/{video}/ask",
               json={"question": "Why does it surge?"}, headers={"X-API-Key": key})
    assert r.status_code == 200, r.text
    return spy[-1]


def test_an_electric_machine_the_lookup_does_not_name_reaches_its_default(
        api_db, tmp_path, no_vision, spy):
    resolution = _ask(api_db, tmp_path, "Energica", "Ego", "electric", spy)
    assert resolution.provenance == "powertrain-default"
    assert resolution.candidates == frozenset({"direct_drive"})


def test_an_ice_machine_resolves_as_before(api_db, tmp_path, no_vision, spy):
    resolution = _ask(api_db, tmp_path, "Energica", "Ego", "ice", spy)
    assert resolution.provenance == "unknown"


def test_the_context_carries_it():
    from motodiag.media.vision_types import VehicleContext

    assert "powertrain" in VehicleContext.model_fields
    assert VehicleContext().powertrain is None
