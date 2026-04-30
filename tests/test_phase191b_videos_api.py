"""Phase 191B — Video upload + analysis HTTP endpoints tests.

Six classes, ~30 tests. No live AI calls — the BackgroundTask that
fires :func:`run_analysis_pipeline` is monkeypatched to a no-op in
every test that exercises the upload route.

Mirrors :mod:`tests.test_phase178_session_api` shape (same ``api_db``
fixture pattern, same ``_make_user`` / ``_make_sub`` helpers extended
for tier + sessions).
"""

from __future__ import annotations

import json as _json
import os
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

import pytest
from fastapi.testclient import TestClient

from motodiag.api import create_app
from motodiag.auth.api_key_repo import create_api_key
from motodiag.core.database import get_connection, init_db
from motodiag.core.session_repo import create_session_for_owner
from motodiag.core.video_repo import (
    create_video,
    get_video,
    list_session_videos,
    soft_delete_video,
)


# ---------------------------------------------------------------------------
# Fixtures + helpers
# ---------------------------------------------------------------------------


@pytest.fixture
def api_db(tmp_path, monkeypatch):
    """Create a fresh DB + override env so create_app picks it up.

    Also overrides ``MOTODIAG_DATA_DIR`` to a tmp path so the upload
    route writes files inside the test sandbox, never the real
    ``data/`` directory.
    """
    from motodiag.core.config import reset_settings

    db_path = str(tmp_path / "phase191b_api.db")
    init_db(db_path)
    monkeypatch.setenv("MOTODIAG_DB_PATH", db_path)
    monkeypatch.setenv("MOTODIAG_DATA_DIR", str(tmp_path))
    for tier in ("anonymous", "individual", "shop", "company"):
        monkeypatch.setenv(
            f"MOTODIAG_RATE_LIMIT_{tier.upper()}_PER_MINUTE", "9999",
        )
    reset_settings()
    yield db_path
    reset_settings()


@pytest.fixture
def patch_worker(monkeypatch):
    """Replace the analysis worker with a no-op so tests don't hit ffmpeg."""
    import motodiag.media.analysis_worker as worker_mod

    def _noop(video_id, db_path=None):
        return None

    monkeypatch.setattr(worker_mod, "run_analysis_pipeline", _noop)
    yield


def _make_user(db_path: str, username: str = "bob", tier: str = "individual") -> int:
    """Create a user row + return id. Tier here is the *legacy* user.tier
    column; the *subscription* tier is set separately via _make_sub."""
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "INSERT INTO users (username, email, tier, is_active) "
            "VALUES (?, ?, ?, 1)",
            (username, f"{username}@example.com", tier),
        )
        return int(cursor.lastrowid)


def _make_sub(db_path: str, user_id: int, tier: str = "shop") -> None:
    """Stamp an active subscription on a user."""
    with get_connection(db_path) as conn:
        conn.execute(
            """INSERT INTO subscriptions
               (user_id, tier, status, current_period_end)
               VALUES (?, ?, 'active', datetime('now', '+30 days'))""",
            (user_id, tier),
        )


def _make_session(db_path: str, user_id: int, year: int = 2005) -> int:
    return create_session_for_owner(
        owner_user_id=user_id,
        vehicle_make="Honda",
        vehicle_model="CBR600",
        vehicle_year=year,
        db_path=db_path,
    )


def _create_api_key(db_path: str, user_id: int) -> str:
    """Create a key + return the plaintext (X-API-Key header value)."""
    _, plaintext = create_api_key(user_id, db_path=db_path)
    return plaintext


def _shop_user_with_session(db_path: str, username: str = "shopper"):
    """Convenience: shop-tier user with one open session.

    Returns ``(user_id, plaintext_key, session_id)``.
    """
    uid = _make_user(db_path, username=username)
    _make_sub(db_path, uid, tier="shop")
    key = _create_api_key(db_path, uid)
    sid = _make_session(db_path, uid)
    return uid, key, sid


def _good_metadata(file_size_bytes: int = 100) -> str:
    return _json.dumps({
        "started_at": "2026-04-29T10:00:00Z",
        "duration_ms": 5000,
        "width": 1920,
        "height": 1080,
        "file_size_bytes": file_size_bytes,
        "format": "mp4",
        "codec": "h264",
        "interrupted": False,
    })


def _good_files(payload: bytes = b"\x00" * 100):
    return {"file": ("test.mp4", payload, "video/mp4")}


# ===========================================================================
# 1. Upload endpoint
# ===========================================================================


class TestUploadEndpoint:

    def test_upload_happy_path_returns_201_with_pending_analysis_state(
        self, api_db, patch_worker,
    ):
        _, key, sid = _shop_user_with_session(api_db)
        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)
        r = client.post(
            f"/v1/sessions/{sid}/videos",
            files=_good_files(),
            data={"metadata": _good_metadata()},
            headers={"X-API-Key": key},
        )
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["id"] > 0
        assert body["session_id"] == sid
        assert body["analysis_state"] == "pending"
        assert body["upload_state"] == "uploaded"
        # file_path / sha256 NOT exposed
        assert "file_path" not in body
        assert "sha256" not in body

    def test_upload_creates_db_row_with_sha256(
        self, api_db, patch_worker,
    ):
        _, key, sid = _shop_user_with_session(api_db)
        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)
        payload = b"hello-mp4-bytes"
        r = client.post(
            f"/v1/sessions/{sid}/videos",
            files={"file": ("test.mp4", payload, "video/mp4")},
            data={"metadata": _good_metadata(file_size_bytes=len(payload))},
            headers={"X-API-Key": key},
        )
        assert r.status_code == 201, r.text
        vid = r.json()["id"]
        # sha256 is on the row, not the response
        with get_connection(api_db) as conn:
            row = conn.execute(
                "SELECT sha256 FROM videos WHERE id = ?", (vid,),
            ).fetchone()
        import hashlib as _h
        assert row["sha256"] == _h.sha256(payload).hexdigest()

    def test_upload_writes_file_to_disk_at_canonical_path(
        self, api_db, patch_worker, tmp_path,
    ):
        uid, key, sid = _shop_user_with_session(api_db)
        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)
        payload = b"\x01\x02\x03" * 50
        r = client.post(
            f"/v1/sessions/{sid}/videos",
            files={"file": ("test.mp4", payload, "video/mp4")},
            data={"metadata": _good_metadata(file_size_bytes=len(payload))},
            headers={"X-API-Key": key},
        )
        assert r.status_code == 201, r.text
        vid = r.json()["id"]
        # Path layout: {data_dir}/videos/shop_{shop_id}/session_{sid}/{vid}.mp4
        # shop_id falls back to user id when no shop membership.
        expected = (
            Path(str(tmp_path))
            / "videos" / f"shop_{uid}" / f"session_{sid}" / f"{vid}.mp4"
        )
        assert expected.exists(), f"missing {expected}"
        assert expected.read_bytes() == payload

    def test_upload_queues_background_analysis_task(
        self, api_db, monkeypatch,
    ):
        """Verify add_task is invoked with the right args."""
        called: list[tuple] = []

        def fake_run(video_id, db_path=None):
            called.append((video_id, db_path))

        import motodiag.media.analysis_worker as worker_mod
        monkeypatch.setattr(worker_mod, "run_analysis_pipeline", fake_run)

        _, key, sid = _shop_user_with_session(api_db)
        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)
        r = client.post(
            f"/v1/sessions/{sid}/videos",
            files=_good_files(),
            data={"metadata": _good_metadata()},
            headers={"X-API-Key": key},
        )
        assert r.status_code == 201, r.text
        # TestClient runs BackgroundTasks synchronously after the response
        assert len(called) == 1
        assert called[0][0] == r.json()["id"]

    def test_upload_without_api_key_returns_401_with_problem_detail(
        self, api_db, patch_worker,
    ):
        _, _, sid = _shop_user_with_session(api_db)
        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)
        r = client.post(
            f"/v1/sessions/{sid}/videos",
            files=_good_files(),
            data={"metadata": _good_metadata()},
        )
        assert r.status_code == 401
        body = r.json()
        assert body["status"] == 401
        assert "type" in body
        assert "title" in body

    def test_upload_with_individual_tier_returns_402_with_problem_detail(
        self, api_db, patch_worker,
    ):
        # require_tier('shop') 402s individual subscriptions
        uid = _make_user(api_db)
        _make_sub(api_db, uid, tier="individual")
        key = _create_api_key(api_db, uid)
        sid = _make_session(api_db, uid)
        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)
        r = client.post(
            f"/v1/sessions/{sid}/videos",
            files=_good_files(),
            data={"metadata": _good_metadata()},
            headers={"X-API-Key": key},
        )
        assert r.status_code == 402, r.text
        body = r.json()
        assert body["status"] == 402
        assert (
            body["type"].endswith("subscription-tier-insufficient")
            or body["type"].endswith("subscription-required")
        )

    def test_upload_with_invalid_metadata_json_returns_422(
        self, api_db, patch_worker,
    ):
        _, key, sid = _shop_user_with_session(api_db)
        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)
        r = client.post(
            f"/v1/sessions/{sid}/videos",
            files=_good_files(),
            data={"metadata": "this is not json"},
            headers={"X-API-Key": key},
        )
        assert r.status_code == 422

    def test_upload_at_session_count_cap_returns_402_with_problem_detail(
        self, api_db, patch_worker,
    ):
        from motodiag.api.routes.videos import PER_SESSION_COUNT_CAP

        uid, key, sid = _shop_user_with_session(api_db)
        # Seed PER_SESSION_COUNT_CAP videos directly via repo
        for i in range(PER_SESSION_COUNT_CAP):
            create_video(
                session_id=sid,
                file_path=f"/tmp/seed_{i}.mp4",
                sha256=f"{i:064d}",
                started_at="2026-04-29T10:00:00Z",
                duration_ms=1000, width=640, height=480,
                file_size_bytes=1000, db_path=api_db,
            )
        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)
        r = client.post(
            f"/v1/sessions/{sid}/videos",
            files=_good_files(),
            data={"metadata": _good_metadata()},
            headers={"X-API-Key": key},
        )
        assert r.status_code == 402, r.text
        body = r.json()
        assert body["status"] == 402
        assert body["type"].endswith("video-quota-exceeded")

    def test_upload_exceeding_session_size_cap_returns_413_with_problem_detail(
        self, api_db, patch_worker,
    ):
        from motodiag.api.routes.videos import PER_SESSION_BYTES_CAP

        uid, key, sid = _shop_user_with_session(api_db)
        # Seed one big row that consumes (cap - 50) bytes
        create_video(
            session_id=sid,
            file_path="/tmp/seed_big.mp4",
            sha256="b" * 64,
            started_at="2026-04-29T10:00:00Z",
            duration_ms=10000, width=1920, height=1080,
            file_size_bytes=PER_SESSION_BYTES_CAP - 50,
            db_path=api_db,
        )
        # Try to upload 100 bytes — would exceed by 50
        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)
        r = client.post(
            f"/v1/sessions/{sid}/videos",
            files=_good_files(b"\x00" * 100),
            data={"metadata": _good_metadata(file_size_bytes=100)},
            headers={"X-API-Key": key},
        )
        assert r.status_code == 413, r.text
        body = r.json()
        assert body["status"] == 413
        assert body["type"].endswith("video-too-large")

    def test_upload_at_monthly_tier_quota_returns_402_with_problem_detail(
        self, api_db, patch_worker,
    ):
        from motodiag.api.routes.videos import TIER_MONTHLY_VIDEO_LIMITS

        cap = TIER_MONTHLY_VIDEO_LIMITS["shop"]
        uid, key, sid = _shop_user_with_session(api_db)
        # Seed `cap` videos this month across (cap // 9 + 1) sessions
        # so we don't hit the per-session count cap (10).
        sessions_needed = (cap // 9) + 1
        seeded_sessions = [sid]
        for _ in range(sessions_needed - 1):
            seeded_sessions.append(_make_session(api_db, uid))

        seeded = 0
        for s in seeded_sessions:
            for i in range(9):  # stay under PER_SESSION_COUNT_CAP=10
                if seeded >= cap:
                    break
                create_video(
                    session_id=s,
                    file_path=f"/tmp/seed_{s}_{i}.mp4",
                    sha256=f"{seeded:064d}",
                    started_at="2026-04-29T10:00:00Z",
                    duration_ms=1000, width=640, height=480,
                    file_size_bytes=1000, db_path=api_db,
                )
                seeded += 1
            if seeded >= cap:
                break

        # Use a fresh session (no seeded videos) so per-session count
        # doesn't get hit first
        fresh_sid = _make_session(api_db, uid)
        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)
        r = client.post(
            f"/v1/sessions/{fresh_sid}/videos",
            files=_good_files(),
            data={"metadata": _good_metadata()},
            headers={"X-API-Key": key},
        )
        assert r.status_code == 402, r.text
        body = r.json()
        assert body["type"].endswith("video-quota-exceeded")


# ===========================================================================
# 2. List endpoint
# ===========================================================================


class TestListEndpoint:

    def test_list_returns_videos_newest_first(self, api_db):
        uid, key, sid = _shop_user_with_session(api_db)
        v1 = create_video(
            session_id=sid, file_path="/tmp/a.mp4", sha256="a" * 64,
            started_at="2026-04-29T10:00:00Z", duration_ms=1000,
            width=640, height=480, file_size_bytes=1000, db_path=api_db,
        )
        v2 = create_video(
            session_id=sid, file_path="/tmp/b.mp4", sha256="b" * 64,
            started_at="2026-04-29T10:01:00Z", duration_ms=1000,
            width=640, height=480, file_size_bytes=1000, db_path=api_db,
        )
        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)
        r = client.get(
            f"/v1/sessions/{sid}/videos",
            headers={"X-API-Key": key},
        )
        assert r.status_code == 200, r.text
        items = r.json()
        # newest first → v2 before v1
        assert [it["id"] for it in items] == [v2, v1]

    def test_list_excludes_soft_deleted(self, api_db):
        uid, key, sid = _shop_user_with_session(api_db)
        v1 = create_video(
            session_id=sid, file_path="/tmp/a.mp4", sha256="a" * 64,
            started_at="2026-04-29T10:00:00Z", duration_ms=1000,
            width=640, height=480, file_size_bytes=1000, db_path=api_db,
        )
        v2 = create_video(
            session_id=sid, file_path="/tmp/b.mp4", sha256="b" * 64,
            started_at="2026-04-29T10:01:00Z", duration_ms=1000,
            width=640, height=480, file_size_bytes=1000, db_path=api_db,
        )
        soft_delete_video(v1, db_path=api_db)
        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)
        r = client.get(
            f"/v1/sessions/{sid}/videos",
            headers={"X-API-Key": key},
        )
        assert r.status_code == 200
        items = r.json()
        assert [it["id"] for it in items] == [v2]

    def test_list_returns_404_for_cross_owner_session(self, api_db):
        # caller is `me`; session is owned by `other`
        me = _make_user(api_db, username="me")
        _make_sub(api_db, me, tier="shop")
        key_me = _create_api_key(api_db, me)
        other = _make_user(api_db, username="other")
        other_sid = _make_session(api_db, other)

        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)
        r = client.get(
            f"/v1/sessions/{other_sid}/videos",
            headers={"X-API-Key": key_me},
        )
        assert r.status_code == 404, r.text
        body = r.json()
        assert body["type"].endswith("video-not-found")

    def test_list_returns_empty_array_for_session_with_no_videos(
        self, api_db,
    ):
        uid, key, sid = _shop_user_with_session(api_db)
        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)
        r = client.get(
            f"/v1/sessions/{sid}/videos",
            headers={"X-API-Key": key},
        )
        assert r.status_code == 200
        assert r.json() == []

    def test_list_without_api_key_returns_401(self, api_db):
        uid, _, sid = _shop_user_with_session(api_db)
        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)
        r = client.get(f"/v1/sessions/{sid}/videos")
        assert r.status_code == 401


# ===========================================================================
# 3. Get-single endpoint
# ===========================================================================


class TestGetSingleEndpoint:

    def test_get_single_returns_video_with_analysis_state(self, api_db):
        uid, key, sid = _shop_user_with_session(api_db)
        vid = create_video(
            session_id=sid, file_path="/tmp/a.mp4", sha256="a" * 64,
            started_at="2026-04-29T10:00:00Z", duration_ms=1000,
            width=640, height=480, file_size_bytes=1000, db_path=api_db,
        )
        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)
        r = client.get(
            f"/v1/sessions/{sid}/videos/{vid}",
            headers={"X-API-Key": key},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["id"] == vid
        assert body["analysis_state"] == "pending"

    def test_get_single_returns_404_for_nonexistent_video(self, api_db):
        uid, key, sid = _shop_user_with_session(api_db)
        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)
        r = client.get(
            f"/v1/sessions/{sid}/videos/99999",
            headers={"X-API-Key": key},
        )
        assert r.status_code == 404
        assert r.json()["type"].endswith("video-not-found")

    def test_get_single_returns_404_for_video_in_different_session(
        self, api_db,
    ):
        uid, key, sid_a = _shop_user_with_session(api_db)
        sid_b = _make_session(api_db, uid)
        vid = create_video(
            session_id=sid_a, file_path="/tmp/a.mp4", sha256="a" * 64,
            started_at="2026-04-29T10:00:00Z", duration_ms=1000,
            width=640, height=480, file_size_bytes=1000, db_path=api_db,
        )
        # Look up vid via the WRONG session id → 404
        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)
        r = client.get(
            f"/v1/sessions/{sid_b}/videos/{vid}",
            headers={"X-API-Key": key},
        )
        assert r.status_code == 404

    def test_get_single_returns_404_for_cross_owner_video(self, api_db):
        me = _make_user(api_db, username="me")
        _make_sub(api_db, me, tier="shop")
        key_me = _create_api_key(api_db, me)
        other = _make_user(api_db, username="other")
        other_sid = _make_session(api_db, other)
        other_vid = create_video(
            session_id=other_sid, file_path="/tmp/x.mp4", sha256="x" * 64,
            started_at="2026-04-29T10:00:00Z", duration_ms=1000,
            width=640, height=480, file_size_bytes=1000, db_path=api_db,
        )
        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)
        r = client.get(
            f"/v1/sessions/{other_sid}/videos/{other_vid}",
            headers={"X-API-Key": key_me},
        )
        assert r.status_code == 404

    def test_get_single_returns_404_for_soft_deleted_video(self, api_db):
        uid, key, sid = _shop_user_with_session(api_db)
        vid = create_video(
            session_id=sid, file_path="/tmp/a.mp4", sha256="a" * 64,
            started_at="2026-04-29T10:00:00Z", duration_ms=1000,
            width=640, height=480, file_size_bytes=1000, db_path=api_db,
        )
        soft_delete_video(vid, db_path=api_db)
        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)
        r = client.get(
            f"/v1/sessions/{sid}/videos/{vid}",
            headers={"X-API-Key": key},
        )
        assert r.status_code == 404


# ===========================================================================
# 4. Delete endpoint
# ===========================================================================


class TestDeleteEndpoint:

    def test_delete_returns_204_and_soft_deletes(self, api_db):
        uid, key, sid = _shop_user_with_session(api_db)
        vid = create_video(
            session_id=sid, file_path="/tmp/a.mp4", sha256="a" * 64,
            started_at="2026-04-29T10:00:00Z", duration_ms=1000,
            width=640, height=480, file_size_bytes=1000, db_path=api_db,
        )
        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)
        r = client.delete(
            f"/v1/sessions/{sid}/videos/{vid}",
            headers={"X-API-Key": key},
        )
        assert r.status_code == 204
        # Soft-deleted: get_video returns None
        assert get_video(vid, db_path=api_db) is None

    def test_delete_idempotent_second_call_also_204(self, api_db):
        uid, key, sid = _shop_user_with_session(api_db)
        vid = create_video(
            session_id=sid, file_path="/tmp/a.mp4", sha256="a" * 64,
            started_at="2026-04-29T10:00:00Z", duration_ms=1000,
            width=640, height=480, file_size_bytes=1000, db_path=api_db,
        )
        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)
        r1 = client.delete(
            f"/v1/sessions/{sid}/videos/{vid}",
            headers={"X-API-Key": key},
        )
        r2 = client.delete(
            f"/v1/sessions/{sid}/videos/{vid}",
            headers={"X-API-Key": key},
        )
        assert r1.status_code == 204
        assert r2.status_code == 204

    def test_delete_for_cross_owner_returns_204_no_existence_leak(
        self, api_db,
    ):
        """Cross-owner soft-delete → 204 (silent no-op) per repo's
        silent-False semantics. Information-leak guard."""
        me = _make_user(api_db, username="me")
        _make_sub(api_db, me, tier="shop")
        key_me = _create_api_key(api_db, me)
        other = _make_user(api_db, username="other")
        other_sid = _make_session(api_db, other)
        other_vid = create_video(
            session_id=other_sid, file_path="/tmp/x.mp4", sha256="x" * 64,
            started_at="2026-04-29T10:00:00Z", duration_ms=1000,
            width=640, height=480, file_size_bytes=1000, db_path=api_db,
        )
        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)
        r = client.delete(
            f"/v1/sessions/{other_sid}/videos/{other_vid}",
            headers={"X-API-Key": key_me},
        )
        assert r.status_code == 204
        # And the row is NOT actually deleted (cross-owner no-op)
        row = get_video(other_vid, db_path=api_db)
        assert row is not None

    def test_delete_without_api_key_returns_401(self, api_db):
        uid, _, sid = _shop_user_with_session(api_db)
        vid = create_video(
            session_id=sid, file_path="/tmp/a.mp4", sha256="a" * 64,
            started_at="2026-04-29T10:00:00Z", duration_ms=1000,
            width=640, height=480, file_size_bytes=1000, db_path=api_db,
        )
        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)
        r = client.delete(f"/v1/sessions/{sid}/videos/{vid}")
        assert r.status_code == 401


# ===========================================================================
# 5. File-stream endpoint
# ===========================================================================


class TestFileStreamEndpoint:

    def test_file_stream_returns_video_mp4_with_correct_headers(
        self, api_db, tmp_path,
    ):
        uid, key, sid = _shop_user_with_session(api_db)
        # Create a real file on disk so FileResponse can serve it
        on_disk = tmp_path / "real_video.mp4"
        payload = b"fake-mp4-bytes-for-test"
        on_disk.write_bytes(payload)
        vid = create_video(
            session_id=sid, file_path=str(on_disk), sha256="c" * 64,
            started_at="2026-04-29T10:00:00Z", duration_ms=1000,
            width=640, height=480, file_size_bytes=len(payload),
            db_path=api_db,
        )
        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)
        r = client.get(
            f"/v1/sessions/{sid}/videos/{vid}/file",
            headers={"X-API-Key": key},
        )
        assert r.status_code == 200, r.text
        assert r.headers.get("content-type", "").startswith("video/mp4")
        assert r.content == payload

    def test_file_stream_returns_404_for_nonexistent_video(self, api_db):
        uid, key, sid = _shop_user_with_session(api_db)
        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)
        r = client.get(
            f"/v1/sessions/{sid}/videos/99999/file",
            headers={"X-API-Key": key},
        )
        assert r.status_code == 404

    def test_file_stream_returns_404_when_file_missing_on_disk(
        self, api_db,
    ):
        uid, key, sid = _shop_user_with_session(api_db)
        vid = create_video(
            session_id=sid,
            file_path="/tmp/this/does/not/exist_video_xyz.mp4",
            sha256="c" * 64,
            started_at="2026-04-29T10:00:00Z", duration_ms=1000,
            width=640, height=480, file_size_bytes=100, db_path=api_db,
        )
        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)
        r = client.get(
            f"/v1/sessions/{sid}/videos/{vid}/file",
            headers={"X-API-Key": key},
        )
        assert r.status_code == 404
        assert r.json()["type"].endswith("video-not-found")


# ===========================================================================
# 6. ProblemDetail envelope
# ===========================================================================


class TestProblemDetailEnvelope:

    def test_404_response_body_matches_problem_detail_shape(self, api_db):
        uid, key, sid = _shop_user_with_session(api_db)
        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)
        r = client.get(
            f"/v1/sessions/{sid}/videos/77777",
            headers={"X-API-Key": key},
        )
        assert r.status_code == 404
        body = r.json()
        assert "type" in body
        assert "title" in body
        assert "status" in body
        assert isinstance(body["status"], int)
        assert body["status"] == 404

    def test_402_quota_response_body_matches_problem_detail_shape(
        self, api_db, patch_worker,
    ):
        from motodiag.api.routes.videos import PER_SESSION_COUNT_CAP

        uid, key, sid = _shop_user_with_session(api_db)
        for i in range(PER_SESSION_COUNT_CAP):
            create_video(
                session_id=sid,
                file_path=f"/tmp/seed_{i}.mp4",
                sha256=f"{i:064d}",
                started_at="2026-04-29T10:00:00Z",
                duration_ms=1000, width=640, height=480,
                file_size_bytes=1000, db_path=api_db,
            )
        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)
        r = client.post(
            f"/v1/sessions/{sid}/videos",
            files=_good_files(),
            data={"metadata": _good_metadata()},
            headers={"X-API-Key": key},
        )
        assert r.status_code == 402
        body = r.json()
        assert "type" in body and "title" in body and "status" in body
        assert body["status"] == 402
        assert isinstance(body["status"], int)

    def test_413_too_large_response_body_matches_problem_detail_shape(
        self, api_db, patch_worker,
    ):
        from motodiag.api.routes.videos import PER_SESSION_BYTES_CAP

        uid, key, sid = _shop_user_with_session(api_db)
        create_video(
            session_id=sid, file_path="/tmp/seed_big.mp4",
            sha256="b" * 64,
            started_at="2026-04-29T10:00:00Z", duration_ms=10000,
            width=1920, height=1080,
            file_size_bytes=PER_SESSION_BYTES_CAP - 50,
            db_path=api_db,
        )
        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)
        r = client.post(
            f"/v1/sessions/{sid}/videos",
            files=_good_files(b"\x00" * 100),
            data={"metadata": _good_metadata(file_size_bytes=100)},
            headers={"X-API-Key": key},
        )
        assert r.status_code == 413
        body = r.json()
        assert "type" in body and "title" in body and "status" in body
        assert body["status"] == 413
        assert isinstance(body["status"], int)
