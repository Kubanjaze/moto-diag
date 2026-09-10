"""Phase 244J — the guidance surface had no caller.

Phase 244B built a contract that cannot express a diagnosis, grounding labels
that force the model to say what it is reasoning from, and thirty-five guards.
Nothing called it: the only way to ask the product a question was a Python
import.

The fourth integration gap this session found — after `SafetyChecker` (241), the
`HV_` DTC format (244) and `_build_vehicle_context` (244B) — and the only one it
created itself.
"""

from __future__ import annotations

from pathlib import Path
from unittest import mock

import pytest
from fastapi.testclient import TestClient

from support.source_guards import code_of
from motodiag.api import create_app
from motodiag.auth.api_key_repo import create_api_key
from motodiag.core.database import get_connection, init_db
from motodiag.core.session_repo import create_session_for_owner
from motodiag.media.vision_types import (
    Grounding, GuidanceCandidate, GuidanceResponse,
)


@pytest.fixture
def api_db(tmp_path, monkeypatch):
    from motodiag.core.config import reset_settings

    db_path = str(tmp_path / "phase244J.db")
    init_db(db_path)
    monkeypatch.setenv("MOTODIAG_DB_PATH", db_path)
    monkeypatch.setenv("MOTODIAG_DATA_DIR", str(tmp_path))
    for tier in ("anonymous", "individual", "shop", "company"):
        monkeypatch.setenv(f"MOTODIAG_RATE_LIMIT_{tier.upper()}_PER_MINUTE", "9999")
    reset_settings()
    yield db_path
    reset_settings()


def _user(db_path, username, tier="shop"):
    with get_connection(db_path) as conn:
        uid = int(conn.execute(
            "INSERT INTO users (username, email, tier, is_active) VALUES (?, ?, 'individual', 1)",
            (username, f"{username}@example.com")).lastrowid)
        conn.execute(
            "INSERT INTO subscriptions (user_id, tier, status, current_period_end) "
            "VALUES (?, ?, 'active', datetime('now', '+30 days'))", (uid, tier))
    _, key = create_api_key(uid, db_path=db_path)
    return uid, key


def _session_with_video(db_path, uid, tmp_path, name="v"):
    sid = create_session_for_owner(
        owner_user_id=uid, vehicle_make="Honda", vehicle_model="CBR600F4i",
        vehicle_year=2001, db_path=db_path)
    mp4 = tmp_path / f"{name}.mp4"
    mp4.write_bytes(b"not-a-real-mp4")
    with get_connection(db_path) as conn:
        vid = int(conn.execute(
            """INSERT INTO videos (session_id, started_at, duration_ms, width, height,
               file_size_bytes, file_path, sha256) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (sid, "2026-09-10T10:00:00Z", 5000, 1280, 720, 14, str(mp4), "x" * 64)).lastrowid)
    return sid, vid, mp4


FAKE_ANSWER = GuidanceResponse(
    question_understood_as="Where is the oil leak coming from?",
    answers_the_question=True,
    candidates=[GuidanceCandidate(
        candidate="Stator cover gasket",
        why_plausible="Left-side sealing surface on this engine family.",
        how_to_discriminate="Degrease and look for the highest wet point.",
        grounding=Grounding.CROSS_PLATFORM,
        grounding_detail="Cam chain tensioner — Honda inline-4 weakness",
    )],
    what_would_narrow_it=["Clean the case and run to temperature."],
    not_established="Frames cannot resolve the exact origin.",
    observation_basis="22 frames of the left side.",
)


@pytest.fixture
def no_vision(monkeypatch, tmp_path):
    """Stub ffmpeg and the vision call — this phase is wiring, not inference."""
    import motodiag.media.ffmpeg as ff
    from motodiag.media.vision_analysis_pipeline import VisionAnalyzer

    calls = {"frames": 0, "asked": []}

    def _frames(video_path, output_dir, max_frames=60):
        calls["frames"] += 1
        f = Path(output_dir); f.mkdir(parents=True, exist_ok=True)
        p = f / "frame_001.jpg"; p.write_bytes(b"jpg")
        return [p]

    def _answer(self, frames, question, vehicle_context=None, known_issues=None,
                video_id=None, shop_id=None, db_path=None):
        # Phase 244L widened the real signature with ledger context; a mock
        # that does not follow is a mock that stops testing the real call.
        calls["asked"].append({"question": question, "context": vehicle_context,
                               "issues": known_issues or []})
        return FAKE_ANSWER

    monkeypatch.setattr(ff, "extract_frames", _frames)
    monkeypatch.setattr(VisionAnalyzer, "answer_question_about_frames", _answer)
    return calls


class TestTheEndpointExists:
    def test_the_route_is_registered(self, api_db):
        app = create_app(db_path_override=api_db)
        paths = {(tuple(sorted(r.methods)), r.path) for r in app.routes if hasattr(r, "methods")}
        assert (("POST",), "/v1/sessions/{session_id}/videos/{video_id}/ask") in paths

    def test_asking_a_question_returns_guidance(self, api_db, tmp_path, no_vision):
        uid, key = _user(api_db, "shopper")
        sid, vid, _ = _session_with_video(api_db, uid, tmp_path)
        c = TestClient(create_app(db_path_override=api_db))
        r = c.post(f"/v1/sessions/{sid}/videos/{vid}/ask",
                   json={"question": "Where is the leak coming from?"},
                   headers={"X-API-Key": key})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["answers_the_question"] is True
        assert body["candidates"][0]["grounding"] == "cross_platform"

    def test_the_question_reaches_the_model(self, api_db, tmp_path, no_vision):
        uid, key = _user(api_db, "shopper")
        sid, vid, _ = _session_with_video(api_db, uid, tmp_path)
        c = TestClient(create_app(db_path_override=api_db))
        c.post(f"/v1/sessions/{sid}/videos/{vid}/ask",
               json={"question": "Why does it smoke on startup?"},
               headers={"X-API-Key": key})
        assert no_vision["asked"][0]["question"] == "Why does it smoke on startup?"

    def test_the_response_cannot_carry_a_diagnosis(self, api_db, tmp_path, no_vision):
        """Phase 244B's contract, asserted at the surface a client actually sees."""
        uid, key = _user(api_db, "shopper")
        sid, vid, _ = _session_with_video(api_db, uid, tmp_path)
        c = TestClient(create_app(db_path_override=api_db))
        body = c.post(f"/v1/sessions/{sid}/videos/{vid}/ask",
                      json={"question": "Where is the leak?"},
                      headers={"X-API-Key": key}).json()
        for forbidden in ("diagnosis", "repair_steps", "parts_needed", "estimated_cost"):
            assert forbidden not in body


class TestOwnershipIsCheckedBeforeAnythingExpensive:
    def test_another_users_video_is_refused(self, api_db, tmp_path, no_vision):
        owner, _ = _user(api_db, "owner")
        _, other_key = _user(api_db, "intruder")
        sid, vid, _ = _session_with_video(api_db, owner, tmp_path)
        c = TestClient(create_app(db_path_override=api_db))
        r = c.post(f"/v1/sessions/{sid}/videos/{vid}/ask",
                   json={"question": "Where is the leak?"},
                   headers={"X-API-Key": other_key})
        assert r.status_code == 404

    def test_no_frames_are_extracted_for_a_refused_request(self, api_db, tmp_path, no_vision):
        """Authorisation ordering is a cost property here, not only a security
        one: frame extraction and a paid vision call must not happen first."""
        owner, _ = _user(api_db, "owner")
        _, other_key = _user(api_db, "intruder")
        sid, vid, _ = _session_with_video(api_db, owner, tmp_path)
        c = TestClient(create_app(db_path_override=api_db))
        c.post(f"/v1/sessions/{sid}/videos/{vid}/ask",
               json={"question": "Where is the leak?"}, headers={"X-API-Key": other_key})
        assert no_vision["frames"] == 0
        assert no_vision["asked"] == []

    def test_a_video_from_another_session_of_the_same_user_is_refused(
        self, api_db, tmp_path, no_vision,
    ):
        """Owning the video is not enough — it must belong to THIS session."""
        uid, key = _user(api_db, "shopper")
        sid_a, vid_a, _ = _session_with_video(api_db, uid, tmp_path, name="a")
        sid_b, _vid_b, _ = _session_with_video(api_db, uid, tmp_path, name="b")
        c = TestClient(create_app(db_path_override=api_db))
        r = c.post(f"/v1/sessions/{sid_b}/videos/{vid_a}/ask",
                   json={"question": "Where is the leak?"}, headers={"X-API-Key": key})
        assert r.status_code == 404
        assert no_vision["frames"] == 0

    def test_a_missing_file_on_disk_is_refused(self, api_db, tmp_path, no_vision):
        uid, key = _user(api_db, "shopper")
        sid, vid, mp4 = _session_with_video(api_db, uid, tmp_path)
        mp4.unlink()
        c = TestClient(create_app(db_path_override=api_db))
        r = c.post(f"/v1/sessions/{sid}/videos/{vid}/ask",
                   json={"question": "Where is the leak?"}, headers={"X-API-Key": key})
        assert r.status_code == 404
        assert no_vision["frames"] == 0


class TestTheGates:
    def test_individual_tier_is_refused(self, api_db, tmp_path, no_vision):
        uid, key = _user(api_db, "hobbyist", tier="individual")
        sid, vid, _ = _session_with_video(api_db, uid, tmp_path)
        c = TestClient(create_app(db_path_override=api_db))
        r = c.post(f"/v1/sessions/{sid}/videos/{vid}/ask",
                   json={"question": "Where is the leak?"}, headers={"X-API-Key": key})
        assert r.status_code == 402

    def test_no_api_key_is_refused(self, api_db, tmp_path, no_vision):
        uid, _ = _user(api_db, "shopper")
        sid, vid, _ = _session_with_video(api_db, uid, tmp_path)
        c = TestClient(create_app(db_path_override=api_db))
        assert c.post(f"/v1/sessions/{sid}/videos/{vid}/ask",
                      json={"question": "Where is the leak?"}).status_code == 401

    @pytest.mark.parametrize("bad", ["", "  ", "ab"])
    def test_an_empty_or_trivial_question_is_rejected(self, api_db, tmp_path, no_vision, bad):
        uid, key = _user(api_db, "shopper")
        sid, vid, _ = _session_with_video(api_db, uid, tmp_path)
        c = TestClient(create_app(db_path_override=api_db))
        r = c.post(f"/v1/sessions/{sid}/videos/{vid}/ask",
                   json={"question": bad}, headers={"X-API-Key": key})
        assert r.status_code == 422


class TestTheCorpusArrivesThroughTheResolver:
    def test_known_issues_are_supplied_and_tiered(self, api_db, tmp_path, no_vision):
        """So the endpoint inherits Phases 244C-244I rather than re-querying."""
        from motodiag.knowledge.issues_repo import add_known_issue
        from motodiag.knowledge.marques import rebuild_make_index_at
        from motodiag.knowledge.models import rebuild_model_index_at

        add_known_issue(title="CCT wear", description="d", make="Honda",
                        model="CBR600F4i", db_path=api_db)
        rebuild_make_index_at(api_db)
        rebuild_model_index_at(api_db)

        uid, key = _user(api_db, "shopper")
        sid, vid, _ = _session_with_video(api_db, uid, tmp_path)
        c = TestClient(create_app(db_path_override=api_db))
        c.post(f"/v1/sessions/{sid}/videos/{vid}/ask",
               json={"question": "Where is the leak?"}, headers={"X-API-Key": key})
        issues = no_vision["asked"][0]["issues"]
        assert issues, "no corpus rows reached the guidance call"
        assert all("match_tier" in row for row in issues), "rows arrived untiered"

    def test_the_session_vehicle_reaches_the_model(self, api_db, tmp_path, no_vision):
        uid, key = _user(api_db, "shopper")
        sid, vid, _ = _session_with_video(api_db, uid, tmp_path)
        c = TestClient(create_app(db_path_override=api_db))
        c.post(f"/v1/sessions/{sid}/videos/{vid}/ask",
               json={"question": "Where is the leak?"}, headers={"X-API-Key": key})
        ctx = no_vision["asked"][0]["context"]
        assert ctx is not None and ctx.make == "Honda"
        assert "2001 Honda" in ctx.to_context_string()


class TestTheIntegrationGapCannotSilentlyReopen:
    """The inverse of Phase 241's SafetyChecker tripwire.

    That guard asserts `SafetyChecker` has NO production caller, recording a
    known gap. This one asserts `answer_question_about_frames` DOES have one.
    Same idea pointed in opposite directions; both fail loudly when reality
    moves away from what the docs claim."""

    @staticmethod
    def _production_callers() -> list[str]:
        import ast

        src_root = Path(__file__).parent.parent / "src" / "motodiag"
        hits = []
        for py in src_root.rglob("*.py"):
            if py.name == "vision_analysis_pipeline.py":
                continue
            try:
                tree = ast.parse(py.read_text(encoding="utf-8"))
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.Attribute) and node.attr == "answer_question_about_frames":
                    hits.append(str(py.relative_to(src_root)))
        return hits

    def test_the_guidance_method_has_a_production_caller(self):
        callers = self._production_callers()
        assert callers, (
            "answer_question_about_frames has no production caller. Phase 244B "
            "built the guidance path and shipped it unreachable — a technician "
            "could only get to it through a Python import. If the route was "
            "removed deliberately, delete this tripwire and say why."
        )

    def test_the_caller_is_the_api_route(self):
        assert any("routes/videos.py" in c for c in self._production_callers())

    def test_it_detects_use_not_mention(self):
        """Reads the AST, so a docstring naming the method does not satisfy it —
        the mention-versus-use lesson from Phase 244G."""
        src = code_of(Path(__file__))
        assert "ast.walk" in src


class TestTheSweepPathIsUntouched:
    def test_analyze_video_frames_still_forces_its_own_tool(self):
        import motodiag.media.vision_analysis_pipeline as vap

        src = code_of(vap.VisionAnalyzer.analyze_video_frames)
        assert 'tool_choice = {"type": "tool", "name": "report_video_findings"}' in src

    def test_the_upload_route_still_queues_the_worker(self):
        from motodiag.api.routes import videos as videos_mod

        src = code_of(videos_mod)
        assert "run_analysis_pipeline" in src
        assert "background_tasks.add_task" in src
