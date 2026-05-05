"""Phase 192 Commit 1 — route integration tests for the videos
extension.

Light integration coverage of the existing ``GET
/v1/reports/session/{id}`` route (shipped by Phase 182 + extended by
this commit). Confirms:

1. Route returns the new ``Videos`` section when the session has at
   least one video row.
2. Route omits the ``Videos`` section when zero videos (empty-state
   policy per shape doc Variant 5; matches symptoms / fault_codes
   pattern).
3. Cross-owner read returns 404 even when the session has videos —
   verifies F29 ADR (auth-policy.md) owner-only-with-404 posture
   still holds end-to-end after the videos extension.
4. Free-tier user can read their own session's report containing
   videos → 200 OK. Verifies "read access doesn't gate on tier" per
   F29 (the ADR's smoke-gate template, plan v1.0.1 Section G step 7).

These exist as the F29 smoke gate boundary check; Phase 182's
existing tests already exercise the route shape, so this file does
the minimum to confirm the videos extension hasn't broken the auth
posture.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from motodiag.api import create_app
from motodiag.auth.api_key_repo import create_api_key
from motodiag.core.database import get_connection, init_db
from motodiag.core.session_repo import create_session_for_owner
from motodiag.core.video_repo import create_video


@pytest.fixture
def api_db(tmp_path, monkeypatch):
    """Mirrors ``tests/test_phase182_reports.py::api_db`` so the route
    layer behaves identically (rate limit headroom, settings reset)."""
    from motodiag.core.config import reset_settings
    path = str(tmp_path / "phase192_route.db")
    init_db(path)
    monkeypatch.setenv("MOTODIAG_DB_PATH", path)
    for tier in ("anonymous", "individual", "shop", "company"):
        monkeypatch.setenv(
            f"MOTODIAG_RATE_LIMIT_{tier.upper()}_PER_MINUTE", "9999",
        )
    reset_settings()
    yield path
    reset_settings()


def _make_user(db_path, username="bob", tier="individual"):
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "INSERT INTO users (username, email, tier, is_active) "
            "VALUES (?, ?, ?, 1)",
            (username, f"{username}@ex.com", tier),
        )
        return cursor.lastrowid


def _seed_video(db_path, session_id, file_path="/tmp/v.mp4"):
    return create_video(
        session_id=session_id,
        file_path=file_path,
        sha256="0" * 64,
        started_at="2026-05-05T14:32:18+00:00",
        duration_ms=5200,
        width=1280, height=720,
        file_size_bytes=1572864,
        db_path=db_path,
    )


# ===========================================================================
# Route — videos extension boundary tests
# ===========================================================================


class TestRouteVideosExtension:

    def test_route_returns_videos_section_for_session_with_videos(
        self, api_db,
    ):
        user_id = _make_user(api_db)
        _, plaintext = create_api_key(user_id, db_path=api_db)
        sid = create_session_for_owner(
            user_id, "Honda", "CBR600", 2005, db_path=api_db,
        )
        _seed_video(api_db, sid)

        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)
        r = client.get(
            f"/v1/reports/session/{sid}",
            headers={"X-API-Key": plaintext},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        # Videos section present when at least one video row exists.
        videos_secs = [
            s for s in body.get("sections", []) if "videos" in s
        ]
        assert len(videos_secs) == 1
        assert videos_secs[0]["heading"] == "Videos"
        assert len(videos_secs[0]["videos"]) == 1
        # Required metadata field surfaces in the JSON payload.
        card = videos_secs[0]["videos"][0]
        assert "video_id" in card
        assert "analysis_state" in card

    def test_route_omits_videos_section_for_session_with_zero_videos(
        self, api_db,
    ):
        user_id = _make_user(api_db)
        _, plaintext = create_api_key(user_id, db_path=api_db)
        sid = create_session_for_owner(
            user_id, "Honda", "CBR600", 2005, db_path=api_db,
        )
        # Note: deliberately NO video seeded.

        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)
        r = client.get(
            f"/v1/reports/session/{sid}",
            headers={"X-API-Key": plaintext},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        videos_secs = [
            s for s in body.get("sections", []) if "videos" in s
        ]
        assert videos_secs == []  # omit-when-empty per shape doc.

    def test_route_404_cross_owner_with_videos_present(self, api_db):
        """F29 ADR boundary: cross-owner returns 404 (not 403) even
        when the underlying session has videos. Verifies the videos
        extension hasn't accidentally weakened the existence-disclosure
        posture (e.g., by short-circuiting on a video lookup before the
        ownership check fires)."""
        me = _make_user(api_db, "me")
        other = _make_user(api_db, "other")
        _, plaintext_me = create_api_key(me, db_path=api_db)
        sid = create_session_for_owner(
            other, "Honda", "CBR600", 2005, db_path=api_db,
        )
        _seed_video(api_db, sid)

        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)
        r = client.get(
            f"/v1/reports/session/{sid}",
            headers={"X-API-Key": plaintext_me},
        )
        assert r.status_code == 404, r.text

    def test_route_free_tier_user_can_read_own_session_with_videos(
        self, api_db,
    ):
        """F29 ADR boundary: read access doesn't gate on tier. A
        base-tier (individual) user fetching their own session's report
        — even one with videos — receives 200, NOT 402 / 403. Plan
        v1.0.1 Section G step 7 smoke gate."""
        user_id = _make_user(api_db, "freetier", tier="individual")
        _, plaintext = create_api_key(user_id, db_path=api_db)
        sid = create_session_for_owner(
            user_id, "Honda", "CBR600", 2005, db_path=api_db,
        )
        _seed_video(api_db, sid)

        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)
        r = client.get(
            f"/v1/reports/session/{sid}",
            headers={"X-API-Key": plaintext},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        # Sanity: the videos section landed in the JSON for the
        # base-tier user (no tier-gating on the videos surface).
        videos_secs = [
            s for s in body.get("sections", []) if "videos" in s
        ]
        assert len(videos_secs) == 1
