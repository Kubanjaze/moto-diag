"""Phase 383, F205 — a media row written under one data folder reads back
under another.

The upload routes stored the receiving machine's absolute path, so moving
live from the Mac to the desktop (Phase 382) stranded every media row until
its paths were rewritten by hand (V-A). Now a row holds the path relative to
`settings.data_dir` and every reader resolves it on the machine that reads.
Migration 087 rewrites the rows already stored.

Each round trip: upload under folder A, move A's files to folder B, read
under B. With the old writer the row names A, which no longer exists.
"""

from __future__ import annotations

import shutil
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import test_phase191b_videos_api as V
import test_phase194_commit0_photo_upload as P
import test_phase195_commit0_voice_transcripts as T
import test_phase244J_guidance_surface as J
from motodiag.api import create_app
from motodiag.auth.api_key_repo import create_api_key
from motodiag.core.config import reset_settings
from motodiag.core.database import init_db
from motodiag.core.migrations import apply_migration, get_migration_by_version
from motodiag.media.analysis_worker import run_analysis_pipeline as RUN_ANALYSIS
from motodiag.media.paths import resolve_media_path, stored_media_path


def _use(monkeypatch, db: str, data_dir: Path) -> TestClient:
    """Point the settings at ``data_dir`` and return a fresh client."""
    monkeypatch.setenv("MOTODIAG_DB_PATH", db)
    monkeypatch.setenv("MOTODIAG_DATA_DIR", str(data_dir))
    for tier in ("anonymous", "individual", "shop", "company"):
        monkeypatch.setenv(f"MOTODIAG_RATE_LIMIT_{tier.upper()}_PER_MINUTE", "9999")
    reset_settings()
    return TestClient(create_app(db_path_override=db), raise_server_exceptions=False)


#: The arguments each transcript upload queued its extraction with.
QUEUED: list[tuple] = []


@pytest.fixture
def folders(tmp_path, monkeypatch):
    db = str(tmp_path / "phase383.db")
    init_db(db)
    import motodiag.media.analysis_worker as worker_mod
    monkeypatch.setattr(worker_mod, "run_analysis_pipeline",
                        lambda video_id, db_path=None, data_dir=None: None)
    import motodiag.api.routes.transcripts as transcripts_mod
    QUEUED.clear()
    monkeypatch.setattr(transcripts_mod, "run_extraction_pipeline",
                        lambda *a, **k: QUEUED.append(a))
    yield db, tmp_path / "a", tmp_path / "b"
    reset_settings()


def _move(a: Path, b: Path) -> None:
    shutil.move(str(a), str(b))


def _cell(db: str, sql: str, *params):
    c = sqlite3.connect(db)
    try:
        return c.execute(sql, params).fetchone()[0]
    finally:
        c.close()


def _shop(db: str) -> tuple[str, int, int]:
    uid = P._make_user(db, "owner")
    _, key = create_api_key(uid, db_path=db)
    shop_id, wo_id = P._seed_shop_and_wo(db, uid)
    return key, shop_id, wo_id


class TestTheTwoFunctions:
    def test_a_path_under_the_data_folder_is_stored_relative(self, tmp_path):
        assert stored_media_path(tmp_path / "videos" / "shop_1" / "1.mp4", tmp_path) == \
            "videos/shop_1/1.mp4"

    def test_a_path_outside_it_is_kept_whole(self, tmp_path):
        outside = tmp_path / "elsewhere" / "1.mp4"
        assert stored_media_path(outside, tmp_path / "data") == str(outside)

    def test_a_relative_value_resolves_under_the_reader_s_folder(self, tmp_path):
        assert resolve_media_path("videos/shop_1/1.mp4", tmp_path) == \
            tmp_path / "videos" / "shop_1" / "1.mp4"

    def test_an_absolute_value_resolves_to_itself(self, tmp_path):
        assert resolve_media_path("/srv/x/1.mp4", tmp_path) == Path("/srv/x/1.mp4")


class TestARowReadsBackUnderAnotherFolder:
    def test_a_video(self, folders, monkeypatch):
        db, a, b = folders
        client = _use(monkeypatch, db, a)
        uid, key, sid = V._shop_user_with_session(db)
        payload = b"\x01\x02\x03" * 50
        r = client.post(f"/v1/sessions/{sid}/videos",
                        files={"file": ("t.mp4", payload, "video/mp4")},
                        data={"metadata": V._good_metadata(file_size_bytes=len(payload))},
                        headers={"X-API-Key": key})
        assert r.status_code == 201, r.text
        vid = r.json()["id"]
        stored = _cell(db, "select file_path from videos where id = ?", vid)
        assert stored == f"videos/shop_{uid}/session_{sid}/{vid}.mp4"
        _move(a, b)
        got = _use(monkeypatch, db, b).get(f"/v1/sessions/{sid}/videos/{vid}/file",
                                           headers={"X-API-Key": key})
        assert got.status_code == 200, got.text
        assert got.content == payload

    def test_a_photo(self, folders, monkeypatch):
        db, a, b = folders
        client = _use(monkeypatch, db, a)
        key, shop_id, wo_id = _shop(db)
        r = P._post_photo(client, key, shop_id, wo_id)
        assert r.status_code == 201, r.text
        pid = r.json()["id"]
        stored = _cell(db, "select file_path from work_order_photos where id = ?", pid)
        assert stored == f"photos/shop_{shop_id}/work_order_{wo_id}/{pid}.jpg"
        on_disk = (a / stored).read_bytes()
        _move(a, b)
        got = _use(monkeypatch, db, b).get(
            f"/v1/shop/{shop_id}/work-orders/{wo_id}/photos/{pid}/file",
            headers={"X-API-Key": key})
        assert got.status_code == 200, got.text
        assert got.content == on_disk

    def test_a_voice_transcript(self, folders, monkeypatch):
        db, a, b = folders
        client = _use(monkeypatch, db, a)
        key, shop_id, wo_id = _shop(db)
        raw = T._make_wav_bytes(duration_sec=2.0)
        r = T._post_transcript(client, key, shop_id, wo_id, raw=raw)
        assert r.status_code == 201, r.text
        tid = r.json()["id"]
        stored = _cell(db, "select audio_path from voice_transcripts where id = ?", tid)
        assert stored == f"audio/shop_{shop_id}/work_order_{wo_id}/{tid}.wav"
        _move(a, b)
        got = _use(monkeypatch, db, b).get(
            f"/v1/shop/{shop_id}/work-orders/{wo_id}/transcripts/{tid}/audio",
            headers={"X-API-Key": key})
        assert got.status_code == 200, got.text
        assert got.content == raw

    def test_the_transcript_route_queues_its_data_folder(self, folders, monkeypatch):
        db, a, _ = folders
        client = _use(monkeypatch, db, a)
        key, shop_id, wo_id = _shop(db)
        tid = T._post_transcript(client, key, shop_id, wo_id).json()["id"]
        assert QUEUED == [(tid, shop_id, db, str(a))]

    def test_the_ask_route_reads_the_video_under_b(self, folders, monkeypatch):
        db, a, b = folders
        client = _use(monkeypatch, db, a)
        _, key, sid = V._shop_user_with_session(db)
        vid = client.post(f"/v1/sessions/{sid}/videos",
                          files={"file": ("t.mp4", b"\x05" * 64, "video/mp4")},
                          data={"metadata": V._good_metadata(file_size_bytes=64)},
                          headers={"X-API-Key": key}).json()["id"]
        stored = _cell(db, "select file_path from videos where id = ?", vid)
        _move(a, b)
        import motodiag.media.ffmpeg as ff
        from motodiag.media.vision_analysis_pipeline import VisionAnalyzer
        seen = []

        def frames(video_path, output_dir, max_frames=60):
            seen.append(video_path)
            p = Path(output_dir) / "frame_001.jpg"
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(b"jpg")
            return [p]

        monkeypatch.setattr(ff, "extract_frames", frames)
        monkeypatch.setattr(VisionAnalyzer, "answer_question_about_frames",
                            lambda self, *a, **k: J.FAKE_ANSWER)
        r = _use(monkeypatch, db, b).post(f"/v1/sessions/{sid}/videos/{vid}/ask",
                                          json={"question": "Where is the leak coming from?"},
                                          headers={"X-API-Key": key})
        assert r.status_code == 200, r.text
        assert seen == [b / stored]

    def test_an_absolute_value_still_reads(self, folders, monkeypatch, tmp_path):
        """A row the old code wrote (or one written in 3A's window)."""
        db, a, b = folders
        client = _use(monkeypatch, db, a)
        uid, key, sid = V._shop_user_with_session(db)
        payload = b"\x09" * 64
        vid = client.post(f"/v1/sessions/{sid}/videos",
                          files={"file": ("t.mp4", payload, "video/mp4")},
                          data={"metadata": V._good_metadata(file_size_bytes=len(payload))},
                          headers={"X-API-Key": key}).json()["id"]
        absolute = a / _cell(db, "select file_path from videos where id = ?", vid)
        c = sqlite3.connect(db)
        c.execute("update videos set file_path = ? where id = ?", (str(absolute), vid))
        c.commit()
        c.close()
        got = _use(monkeypatch, db, tmp_path / "c").get(
            f"/v1/sessions/{sid}/videos/{vid}/file", headers={"X-API-Key": key})
        assert got.status_code == 200 and got.content == payload


class TestTheWorkersResolveUnderTheirFolder:
    def test_the_audio_sweep_prunes_the_file_under_b(self, folders, monkeypatch):
        db, a, b = folders
        client = _use(monkeypatch, db, a)
        key, shop_id, wo_id = _shop(db)
        tid = T._post_transcript(client, key, shop_id, wo_id).json()["id"]
        stored = _cell(db, "select audio_path from voice_transcripts where id = ?", tid)
        c = sqlite3.connect(db)
        c.execute("update voice_transcripts set created_at = '2020-01-01 00:00:00' where id = ?",
                  (tid,))
        c.commit()
        c.close()
        _move(a, b)
        from motodiag.media.audio_sweep import prune_old_audio
        res = prune_old_audio(datetime.now(timezone.utc), db_path=db, data_dir=str(b))
        assert res.pruned_count == 1 and not res.errors
        assert not (b / stored).exists()

    def test_the_transcript_pipeline_reads_the_file_under_b(self, folders, monkeypatch):
        db, a, b = folders
        client = _use(monkeypatch, db, a)
        key, shop_id, wo_id = _shop(db)
        tid = T._post_transcript(client, key, shop_id, wo_id).json()["id"]
        stored = _cell(db, "select audio_path from voice_transcripts where id = ?", tid)
        _move(a, b)
        import motodiag.media.transcript_pipeline as tp
        seen = []

        def fake_transcribe(path, **kw):
            seen.append(path)
            raise tp.WhisperUnavailableError("no key in the test")

        monkeypatch.setattr(tp, "transcribe", fake_transcribe)
        tp.run_extraction_pipeline(tid, shop_id, db, data_dir=str(b))
        assert seen == [str(b / stored)] and Path(seen[0]).is_file()

    def test_the_analysis_worker_reads_the_file_under_b(self, folders, monkeypatch):
        db, a, b = folders
        client = _use(monkeypatch, db, a)
        _, key, sid = V._shop_user_with_session(db)
        payload = b"\x07" * 64
        vid = client.post(f"/v1/sessions/{sid}/videos",
                          files={"file": ("t.mp4", payload, "video/mp4")},
                          data={"metadata": V._good_metadata(file_size_bytes=len(payload))},
                          headers={"X-API-Key": key}).json()["id"]
        stored = _cell(db, "select file_path from videos where id = ?", vid)
        _move(a, b)
        import motodiag.media.ffmpeg as ffmpeg_module
        import motodiag.shop.cost_cap as cost_cap
        seen = []

        def fake_extract(video_path, output_dir, **kw):
            seen.append(video_path)
            raise ffmpeg_module.FFmpegMissing("not in the test")

        monkeypatch.setattr(ffmpeg_module, "extract_frames", fake_extract)
        monkeypatch.setattr(cost_cap, "check_cost_cap", lambda *a, **k: None)
        RUN_ANALYSIS(vid, db, data_dir=str(b))
        assert seen == [b / stored] and seen[0].is_file()


class TestMigration087:
    """On a database at 86, with each form a row can hold."""

    ROWS = [  # (stored before, expected after)
        ("/Users/lilquant/Projects/moto-diag/data/videos/shop_1/session_1/1.mp4",
         "videos/shop_1/session_1/1.mp4"),
        ("/home/lilcu/motodiag/live/videos/shop_1/session_4/2.mp4",
         "videos/shop_1/session_4/2.mp4"),
        ("/tmp/elsewhere/3.mp4", "/tmp/elsewhere/3.mp4"),
        ("videos/shop_1/session_6/4.mp4", "videos/shop_1/session_6/4.mp4"),
        ("", ""),
    ]

    def _db_with_videos(self, folders, monkeypatch) -> tuple[str, list[int]]:
        db, a, _ = folders
        client = _use(monkeypatch, db, a)
        _, key, sid = V._shop_user_with_session(db)
        ids = []
        for i, (before, _) in enumerate(self.ROWS):
            payload = bytes([i + 1]) * 32
            vid = client.post(f"/v1/sessions/{sid}/videos",
                              files={"file": ("t.mp4", payload, "video/mp4")},
                              data={"metadata": V._good_metadata(file_size_bytes=32)},
                              headers={"X-API-Key": key}).json()["id"]
            ids.append(vid)
        c = sqlite3.connect(db)
        for vid, (before, _) in zip(ids, self.ROWS):
            c.execute("update videos set file_path = ? where id = ?", (before, vid))
        c.execute("delete from schema_version where version = 87")
        c.commit()
        c.close()
        return db, ids

    def _rows(self, db: str, table: str) -> dict:
        c = sqlite3.connect(db)
        c.row_factory = sqlite3.Row
        out = {r["id"]: dict(r) for r in c.execute(f"select * from {table}")}
        c.close()
        return out

    def test_it_rewrites_only_the_layout_shaped_absolute_paths(self, folders, monkeypatch):
        db, ids = self._db_with_videos(folders, monkeypatch)
        before = self._rows(db, "videos")
        apply_migration(get_migration_by_version(87), db)
        after = self._rows(db, "videos")
        for vid, (_, expected) in zip(ids, self.ROWS):
            assert after[vid]["file_path"] == expected
            assert {k: v for k, v in after[vid].items() if k != "file_path"} == \
                {k: v for k, v in before[vid].items() if k != "file_path"}
        assert _cell(db, "select max(version) from schema_version") == 87

    def test_photos_and_transcripts(self, folders, monkeypatch):
        db, a, _ = folders
        client = _use(monkeypatch, db, a)
        key, shop_id, wo_id = _shop(db)
        pid = P._post_photo(client, key, shop_id, wo_id).json()["id"]
        tid = T._post_transcript(client, key, shop_id, wo_id).json()["id"]
        photo = f"/Users/x/data/photos/shop_{shop_id}/work_order_{wo_id}/{pid}.jpg"
        audio = f"/home/y/live/audio/shop_{shop_id}/work_order_{wo_id}/{tid}.wav"
        c = sqlite3.connect(db)
        c.execute("update work_order_photos set file_path = ? where id = ?", (photo, pid))
        c.execute("update voice_transcripts set audio_path = ? where id = ?", (audio, tid))
        c.execute("delete from schema_version where version = 87")
        c.commit()
        c.close()
        before_p = self._rows(db, "work_order_photos")[pid]
        before_t = self._rows(db, "voice_transcripts")[tid]
        apply_migration(get_migration_by_version(87), db)
        after_p = self._rows(db, "work_order_photos")[pid]
        after_t = self._rows(db, "voice_transcripts")[tid]
        assert after_p["file_path"] == photo.split("/data/", 1)[1]
        assert after_t["audio_path"] == audio.split("/live/", 1)[1]
        assert {**after_p, "file_path": None} == {**before_p, "file_path": None}
        assert {**after_t, "audio_path": None} == {**before_t, "audio_path": None}

    def test_a_fresh_database_is_at_87(self, tmp_path):
        db = str(tmp_path / "fresh.db")
        init_db(db)
        assert _cell(db, "select max(version) from schema_version") == 87
