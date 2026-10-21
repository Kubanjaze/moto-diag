"""Phase 384 — `media_check.py`: every video fetched through the API's file route.

The proof on live fetches the six videos nobody had fetched since 383 stored
their paths relative to the data folder. Here, on videos uploaded through the
real route: equal bodies pass; a missing file, a changed file, an empty
table and a soft-deleted video that still serves each fail.
"""

from __future__ import annotations

import importlib.util
import pathlib
import sqlite3
import sys

import pytest
from fastapi.testclient import TestClient

import test_phase191b_videos_api as V
from motodiag.api import create_app
from motodiag.core.config import reset_settings
from motodiag.core.database import init_db

ROOT = pathlib.Path(__file__).resolve().parents[1]
DEPLOY = ROOT / ".claude" / "skills" / "deploy"
sys.path.insert(0, str(DEPLOY))
spec = importlib.util.spec_from_file_location("media_check384", DEPLOY / "media_check.py")
M = importlib.util.module_from_spec(spec)
spec.loader.exec_module(M)


@pytest.fixture
def uploaded(tmp_path, monkeypatch):
    """Two videos uploaded through the route into `data`; returns (db, data, ids)."""
    db, data = str(tmp_path / "live.db"), tmp_path / "data"
    init_db(db)
    import motodiag.media.analysis_worker as worker_mod
    monkeypatch.setattr(worker_mod, "run_analysis_pipeline",
                        lambda video_id, db_path=None, data_dir=None: None)
    monkeypatch.setenv("MOTODIAG_DB_PATH", db)
    monkeypatch.setenv("MOTODIAG_DATA_DIR", str(data))
    for tier in ("anonymous", "individual", "shop", "company"):
        monkeypatch.setenv(f"MOTODIAG_RATE_LIMIT_{tier.upper()}_PER_MINUTE", "9999")
    reset_settings()
    client = TestClient(create_app(db_path_override=db), raise_server_exceptions=False)
    _, key, sid = V._shop_user_with_session(db)
    ids = []
    for n in (1, 2):
        payload = bytes([n]) * 120
        r = client.post(f"/v1/sessions/{sid}/videos",
                        files={"file": ("t.mp4", payload, "video/mp4")},
                        data={"metadata": V._good_metadata(file_size_bytes=len(payload))},
                        headers={"X-API-Key": key})
        assert r.status_code == 201, r.text
        ids.append(r.json()["id"])
    yield pathlib.Path(db), data, ids
    reset_settings()


def _stored(db, vid) -> str:
    with sqlite3.connect(db) as c:
        return c.execute("select file_path from videos where id = ?", (vid,)).fetchone()[0]


def test_every_video_served_equal_passes(uploaded, capsys):
    db, data, ids = uploaded
    assert M.check(db, data) == 0
    out = capsys.readouterr().out
    assert "media-check: 2 video(s)" in out and out.count(" equals the upload's") == 2
    assert "PASSED" in out


def test_a_missing_file_fails(uploaded, capsys):
    db, data, ids = uploaded
    (data / _stored(db, ids[0])).unlink()
    assert M.check(db, data) == 1
    assert "<- FAILS" in capsys.readouterr().out


def test_a_changed_file_fails(uploaded, capsys):
    db, data, ids = uploaded
    (data / _stored(db, ids[1])).write_bytes(b"not the upload")
    assert M.check(db, data) == 1
    assert "DIFFERS FROM the upload's" in capsys.readouterr().out


def test_the_wrong_data_folder_fails(uploaded, tmp_path):
    db, _, _ = uploaded
    assert M.check(db, tmp_path / "elsewhere") == 1


def test_a_soft_deleted_video_passes_only_when_refused(uploaded, capsys):
    db, data, ids = uploaded
    with sqlite3.connect(db) as c:
        c.execute("update videos set deleted_at = '2026-10-20T00:00:00' where id = ?", (ids[0],))
    assert M.check(db, data) == 0
    assert "(soft-deleted): 404" in capsys.readouterr().out


def test_a_soft_deleted_video_that_still_serves_fails(uploaded, monkeypatch, capsys):
    db, data, _ = uploaded
    monkeypatch.setattr(M, "serve_all", lambda db, data_dir: [
        (1, True, 200, "120 bytes, sha256 0, equals the upload's (videos/x.mp4)")])
    assert M.check(db, data) == 1
    assert "<- FAILS" in capsys.readouterr().out


def test_no_videos_fails(tmp_path):
    db = tmp_path / "empty.db"
    init_db(str(db))
    assert M.check(db, tmp_path) == 1


def test_live_is_only_copied(uploaded):
    db, data, _ = uploaded
    before = db.stat().st_mtime_ns, db.read_bytes()
    M.check(db, data)
    assert (db.stat().st_mtime_ns, db.read_bytes()) == before


def test_on_a_machine_without_live_it_refuses(tmp_path, monkeypatch):
    monkeypatch.setenv("MOTODIAG_LIVE_CONFIG", str(tmp_path / "absent.json"))
    assert M.main([]) == 4
