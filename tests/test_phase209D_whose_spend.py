"""Phase 209D — whose spend is it.

F78, as the operator revised it on 2026-09-17: build the instrument, leave
the number for later. Every ``cost_events`` row for vision and text carried
``shop_id = NULL``, because a session had no shop, so a cap read through
``shop_cost_this_month`` would have seen $0 for every shop and never fired.

Two halves, and the second is the one that is easy to get wrong:

1. work and its spend carry a shop;
2. **off means off.** A brake that defaults to off is indistinguishable from
   a brake that does not work unless both sides are tested, so the default
   is exercised past any plausible cap, and the configured cap is exercised
   at the point where money would be spent.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from unittest import mock

import pytest
from click.testing import CliRunner
from fastapi.testclient import TestClient

from motodiag.api import create_app
from motodiag.auth.api_key_repo import create_api_key
from motodiag.core.database import get_connection, init_db
from motodiag.core.migrations import get_migration_by_version, rollback_to_version
from motodiag.core.models import ProtocolType, VehicleBase
from motodiag.core.session_repo import create_session, get_session
from motodiag.shop.attribution import (
    only_shop,
    shop_for_session,
    shop_for_user,
    shop_for_video,
)
from motodiag.shop.cost_cap import CostCapExceeded, cap_cents, check_cost_cap
from motodiag.shop.cost_repo import record_cost_event, shop_cost_this_month
from motodiag.vehicles.registry import add_vehicle


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def db(tmp_path):
    path = str(tmp_path / "phase209D.db")
    init_db(path)
    return path


@pytest.fixture
def api_db(tmp_path, monkeypatch):
    from motodiag.core.config import reset_settings

    path = str(tmp_path / "phase209D_api.db")
    init_db(path)
    monkeypatch.setenv("MOTODIAG_DB_PATH", path)
    monkeypatch.setenv("MOTODIAG_DATA_DIR", str(tmp_path))
    for tier in ("anonymous", "individual", "shop", "company"):
        monkeypatch.setenv(
            f"MOTODIAG_RATE_LIMIT_{tier.upper()}_PER_MINUTE", "9999",
        )
    reset_settings()
    yield path
    reset_settings()


def _user(db_path, username="tech", tier="shop") -> int:
    """A technician with a shop-tier subscription — the ask route requires one."""
    with get_connection(db_path) as conn:
        uid = conn.execute(
            "INSERT INTO users (username, email, tier, is_active) "
            "VALUES (?, ?, ?, 1)",
            (username, f"{username}@ex.com", tier),
        ).lastrowid
        conn.execute(
            "INSERT INTO subscriptions (user_id, tier, status, current_period_end) "
            "VALUES (?, ?, 'active', datetime('now', '+30 days'))",
            (uid, tier),
        )
        return uid


def _shop(db_path, owner_user_id: int, name="Bandit Hero Moto") -> int:
    with get_connection(db_path) as conn:
        return conn.execute(
            "INSERT INTO shops (owner_user_id, name, is_active) VALUES (?, ?, 1)",
            (owner_user_id, name),
        ).lastrowid


def _member(db_path, user_id: int, shop_id: int, active: int = 1) -> None:
    with get_connection(db_path) as conn:
        conn.execute(
            "INSERT INTO shop_members (user_id, shop_id, role, is_active) "
            "VALUES (?, ?, 'tech', ?)",
            (user_id, shop_id, active),
        )


def _vehicle(db_path) -> int:
    return add_vehicle(
        VehicleBase(
            make="Honda", model="CBR600F4i", year=2001,
            engine_cc=599, protocol=ProtocolType.NONE,
        ),
        db_path=db_path,
    )


def _client(db_path):
    return TestClient(
        create_app(db_path_override=db_path), raise_server_exceptions=False,
    )


def _open_session(client, key, vehicle_id=None) -> int:
    body = {
        "vehicle_make": "Honda", "vehicle_model": "CBR600F4i",
        "vehicle_year": 2001, "symptoms": ["oil leak left side"],
    }
    if vehicle_id is not None:
        body["vehicle_id"] = vehicle_id
    r = client.post("/v1/sessions", json=body, headers={"X-API-Key": key})
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _cost_rows(db_path) -> list[tuple]:
    with get_connection(db_path) as conn:
        return [
            tuple(r) for r in conn.execute(
                "SELECT kind, shop_id, cost_usd_cents FROM cost_events ORDER BY id"
            )
        ]


# ---------------------------------------------------------------------------
# 1. The column
# ---------------------------------------------------------------------------


class TestMigration061:
    def _columns(self, db_path) -> set[str]:
        c = sqlite3.connect(db_path)
        try:
            return {r[1] for r in c.execute("PRAGMA table_info(diagnostic_sessions)")}
        finally:
            c.close()

    def test_a_fresh_database_has_the_column(self, db):
        assert "shop_id" in self._columns(db)

    def test_the_index_exists(self, db):
        c = sqlite3.connect(db)
        try:
            names = {r[0] for r in c.execute(
                "SELECT name FROM sqlite_master WHERE type='index'"
            )}
        finally:
            c.close()
        assert "idx_sessions_shop" in names

    def test_rollback_removes_both(self, db):
        rollback_to_version(60, db)
        assert "shop_id" not in self._columns(db)
        c = sqlite3.connect(db)
        try:
            names = {r[0] for r in c.execute(
                "SELECT name FROM sqlite_master WHERE type='index'"
            )}
        finally:
            c.close()
        assert "idx_sessions_shop" not in names

    def test_it_says_what_it_is_for(self):
        text = get_migration_by_version(61).description
        assert "shop_id = NULL" in text or "shop_id" in text
        assert "cap" in text.lower()


# ---------------------------------------------------------------------------
# 2. Work carries a shop
# ---------------------------------------------------------------------------


class TestSessionsCarryTheirShop:
    def test_the_api_stamps_the_callers_only_shop(self, api_db):
        uid = _user(api_db)
        shop = _shop(api_db, uid)
        _member(api_db, uid, shop)
        _, key = create_api_key(uid, db_path=api_db)
        sid = _open_session(_client(api_db), key)
        assert get_session(sid, db_path=api_db)["shop_id"] == shop

    def test_two_memberships_stay_unattributed(self, api_db):
        uid = _user(api_db)
        a, b = _shop(api_db, uid, "A"), _shop(api_db, uid, "B")
        _member(api_db, uid, a)
        _member(api_db, uid, b)
        _, key = create_api_key(uid, db_path=api_db)
        sid = _open_session(_client(api_db), key)
        assert get_session(sid, db_path=api_db)["shop_id"] is None, (
            "guessing would put one shop's AI spend on the other's ledger"
        )

    def test_an_inactive_membership_does_not_count(self, api_db):
        uid = _user(api_db)
        _member(api_db, uid, _shop(api_db, uid), active=0)
        _, key = create_api_key(uid, db_path=api_db)
        sid = _open_session(_client(api_db), key)
        assert get_session(sid, db_path=api_db)["shop_id"] is None

    def test_a_user_in_no_shop_still_gets_a_session(self, api_db):
        uid = _user(api_db)
        _, key = create_api_key(uid, db_path=api_db)
        sid = _open_session(_client(api_db), key)
        assert get_session(sid, db_path=api_db)["shop_id"] is None

    def test_the_cli_uses_the_shop_the_database_runs(self, db):
        shop = _shop(db, _user(db))
        sid = create_session("Honda", "CBR600F4i", 2001, db_path=db,
                             shop_id=only_shop(db))
        assert get_session(sid, db_path=db)["shop_id"] == shop

    def test_two_shops_in_the_database_get_no_guess(self, db):
        uid = _user(db)
        _shop(db, uid, "A")
        _shop(db, uid, "B")
        assert only_shop(db) is None


class TestTheLookups:
    def test_shop_for_user_needs_exactly_one_active_membership(self, db):
        uid = _user(db)
        assert shop_for_user(uid, db) is None
        shop = _shop(db, uid)
        _member(db, uid, shop)
        assert shop_for_user(uid, db) == shop
        _member(db, uid, _shop(db, uid, "B"))
        assert shop_for_user(uid, db) is None

    def test_shop_for_session_reads_the_stamp(self, db):
        shop = _shop(db, _user(db))
        sid = create_session("Honda", "CBR", 2001, db_path=db, shop_id=shop)
        assert shop_for_session(sid, db) == shop
        assert shop_for_session(999999, db) is None

    def test_shop_for_video_follows_the_session(self, db):
        shop = _shop(db, _user(db))
        sid = create_session("Honda", "CBR", 2001, db_path=db, shop_id=shop)
        with get_connection(db) as conn:
            vid = conn.execute(
                "INSERT INTO videos (session_id, file_path, sha256, started_at, "
                "duration_ms, width, height, file_size_bytes) "
                "VALUES (?, '/tmp/v.mp4', 'a', '2026-09-17T00:00:00Z', 1, 1, 1, 1)",
                (sid,),
            ).lastrowid
        assert shop_for_video(vid, db) == shop

    def test_a_lookup_never_raises(self, tmp_path):
        missing = str(tmp_path / "nope.db")
        assert shop_for_user(1, missing) is None
        assert only_shop(missing) is None
        assert shop_for_session(1, missing) is None
        assert shop_for_video(1, missing) is None


# ---------------------------------------------------------------------------
# 3. Spend carries the shop
# ---------------------------------------------------------------------------


def _guidance_answer():
    from motodiag.media.vision_types import GuidanceResponse

    return GuidanceResponse(
        question_understood_as="Where is the leak?",
        answers_the_question=True,
        candidates=[],
        what_would_narrow_it=["Degrease and re-run"],
        not_established="Frames cannot resolve the origin",
        observation_basis="1 frame",
    )


@pytest.fixture
def no_vision(monkeypatch, tmp_path):
    """Stub ffmpeg and the vision call; capture who the route says pays."""
    import motodiag.media.ffmpeg as ff
    from motodiag.media.vision_analysis_pipeline import VisionAnalyzer

    seen: dict = {}

    def _frames(video_path, output_dir, max_frames=60):
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        p = out / "frame_001.jpg"
        p.write_bytes(b"jpg")
        return [p]

    def _answer(self, frames, question, vehicle_context=None, known_issues=None,
                video_id=None, shop_id=None, db_path=None):
        seen["shop_id"] = shop_id
        return _guidance_answer()

    monkeypatch.setattr(ff, "extract_frames", _frames)
    monkeypatch.setattr(VisionAnalyzer, "answer_question_about_frames", _answer)
    return seen


def _video_for(db_path, session_id, tmp_path) -> int:
    f = Path(tmp_path) / "v.mp4"
    f.write_bytes(b"video")
    with get_connection(db_path) as conn:
        return conn.execute(
            "INSERT INTO videos (session_id, file_path, sha256, started_at, "
            "duration_ms, width, height, file_size_bytes) "
            "VALUES (?, ?, 'a', '2026-09-17T00:00:00Z', 1000, 640, 480, 5)",
            (session_id, str(f)),
        ).lastrowid


class TestSpendCarriesTheShop:
    def test_a_video_question_says_who_pays(self, api_db, tmp_path, no_vision):
        uid = _user(api_db)
        shop = _shop(api_db, uid)
        _member(api_db, uid, shop)
        _, key = create_api_key(uid, db_path=api_db)
        client = _client(api_db)
        sid = _open_session(client, key, _vehicle(api_db))
        vid = _video_for(api_db, sid, tmp_path)

        r = client.post(
            f"/v1/sessions/{sid}/videos/{vid}/ask",
            json={"question": "Where is the leak?"},
            headers={"X-API-Key": key},
        )
        assert r.status_code == 200, r.text
        assert no_vision["shop_id"] == shop

    def test_the_sweep_says_who_pays(self, db, tmp_path):
        from motodiag.media import analysis_worker as worker_mod
        from motodiag.media.vision_types import VisualAnalysisResult

        shop = _shop(db, _user(db))
        sid = create_session("Honda", "CBR600F4i", 2001, db_path=db,
                             vehicle_id=_vehicle(db), shop_id=shop)
        vid = _video_for(db, sid, tmp_path)
        seen: dict = {}

        def _analyze(frames, vehicle_context=None, video_id=None, shop_id=None,
                     db_path=None):
            seen["shop_id"] = shop_id
            return VisualAnalysisResult(
                overall_assessment="stub", frames_analyzed=len(frames),
                model_used="stub", cost_estimate_usd=0.0,
            )

        analyzer = mock.MagicMock()
        analyzer.analyze_video_frames.side_effect = _analyze
        with mock.patch.object(
            worker_mod.ffmpeg_module, "extract_frames", return_value=[object()],
        ), mock.patch.object(worker_mod, "VisionAnalyzer", return_value=analyzer):
            worker_mod.run_analysis_pipeline(vid, db_path=db)
        assert seen["shop_id"] == shop

    def test_a_cli_diagnosis_lands_on_the_shops_ledger(self, tmp_path, monkeypatch):
        """The whole path: the command, the real client, the ledger row."""
        from motodiag.core.config import reset_settings
        from motodiag.engine.client import DiagnosticClient
        from motodiag.cli.main import cli

        db_path = str(tmp_path / "cli.db")
        init_db(db_path)
        monkeypatch.setenv("MOTODIAG_DB_PATH", db_path)
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-not-real")
        reset_settings()
        shop = _shop(db_path, _user(db_path))
        vid = _vehicle(db_path)

        payload = {
            "vehicle_summary": "2001 Honda CBR600F4i",
            "symptoms_acknowledged": ["oil leak left side"],
            "diagnoses": [{
                "diagnosis": "Left crankcase cover gasket weeping",
                "confidence": 0.72, "severity": "medium",
                "evidence": ["Wet film below the cover"],
                "repair_steps": ["Replace cover gasket"],
            }],
            "additional_tests": [], "notes": "",
        }
        block = mock.Mock()
        block.type = "tool_use"
        block.input = payload
        response = mock.Mock()
        response.content = [block]
        response.stop_reason = "tool_use"
        # Big enough to cost more than a cent: `record_diagnosis_cost`
        # skips zero-cost rows by design (Phase 244Q).
        response.usage = mock.Mock(input_tokens=100_000, output_tokens=50_000)
        sdk = mock.Mock()
        sdk.messages.create.return_value = response

        with mock.patch.object(DiagnosticClient, "_get_client", lambda self: sdk):
            r = CliRunner().invoke(cli, [
                "diagnose", "quick", "--vehicle-id", str(vid),
                "--symptoms", "oil leak left side", "--shop", str(shop),
            ])
        assert r.exit_code == 0, r.output
        rows = _cost_rows(db_path)
        assert rows and rows[0][0] == "text_diagnosis"
        assert rows[0][1] == shop, f"text diagnosis unattributed: {rows}"
        assert shop_cost_this_month(shop, db_path=db_path) == rows[0][2]
        reset_settings()

    def test_voice_spend_still_carries_its_shop(self, db):
        """Whisper and extraction attributed before this phase; they still do."""
        record_cost_event(
            kind="whisper", model="whisper-1", cost_usd_cents=3,
            shop_id=7, units_label="duration_ms", units_value=1000, db_path=db,
        )
        record_cost_event(
            kind="claude_extraction", model="haiku", cost_usd_cents=1,
            shop_id=7, units_label="tokens", units_value=900, db_path=db,
        )
        assert [r[1] for r in _cost_rows(db)] == [7, 7]
        assert shop_cost_this_month(7, db_path=db) == 4


# ---------------------------------------------------------------------------
# 4. Off means off; on means before the money
# ---------------------------------------------------------------------------


class TestTheCapIsOffByDefault:
    def test_the_default_setting_is_no_cap(self, api_db):
        assert cap_cents() == 0

    def test_nothing_blocks_however_much_was_spent(self, db):
        record_cost_event(
            kind="vision_guidance", model="sonnet", cost_usd_cents=999_99,
            shop_id=1, db_path=db,
        )
        check_cost_cap(1, db_path=db)  # must not raise

    def test_a_video_question_is_not_refused_by_default(
        self, api_db, tmp_path, no_vision,
    ):
        uid = _user(api_db)
        shop = _shop(api_db, uid)
        _member(api_db, uid, shop)
        _, key = create_api_key(uid, db_path=api_db)
        client = _client(api_db)
        sid = _open_session(client, key, _vehicle(api_db))
        vid = _video_for(api_db, sid, tmp_path)
        record_cost_event(
            kind="vision_guidance", model="sonnet", cost_usd_cents=500_00,
            shop_id=shop, db_path=api_db,
        )
        r = client.post(
            f"/v1/sessions/{sid}/videos/{vid}/ask",
            json={"question": "Where is the leak?"},
            headers={"X-API-Key": key},
        )
        assert r.status_code == 200, r.text


@pytest.fixture
def capped(monkeypatch):
    """A $25 cap, set the way an operator would set one."""
    from motodiag.core.config import reset_settings

    monkeypatch.setenv("MOTODIAG_COST_CAP_MONTHLY_USD_CENTS", "2500")
    reset_settings()
    yield 2500
    reset_settings()


class TestWhenACapIsSet:
    def test_it_reads_the_setting(self, capped):
        assert cap_cents() == 2500

    def test_under_the_cap_nothing_happens(self, db, capped):
        record_cost_event(kind="vision_sweep", model="sonnet",
                          cost_usd_cents=2499, shop_id=1, db_path=db)
        check_cost_cap(1, db_path=db)

    def test_at_the_cap_it_refuses(self, db, capped):
        record_cost_event(kind="vision_sweep", model="sonnet",
                          cost_usd_cents=2500, shop_id=1, db_path=db)
        with pytest.raises(CostCapExceeded) as exc:
            check_cost_cap(1, db_path=db)
        assert "monthly AI limit" in str(exc.value)

    def test_unattributed_work_is_not_refused(self, db, capped):
        """A call with no shop cannot be measured against a per-shop ceiling."""
        record_cost_event(kind="vision_sweep", model="sonnet",
                          cost_usd_cents=9999, shop_id=1, db_path=db)
        check_cost_cap(None, db_path=db)

    def test_the_video_question_is_refused_before_it_pays(
        self, api_db, tmp_path, no_vision, capped,
    ):
        uid = _user(api_db)
        shop = _shop(api_db, uid)
        _member(api_db, uid, shop)
        _, key = create_api_key(uid, db_path=api_db)
        client = _client(api_db)
        sid = _open_session(client, key, _vehicle(api_db))
        vid = _video_for(api_db, sid, tmp_path)
        record_cost_event(kind="vision_guidance", model="sonnet",
                          cost_usd_cents=2500, shop_id=shop, db_path=api_db)

        r = client.post(
            f"/v1/sessions/{sid}/videos/{vid}/ask",
            json={"question": "Where is the leak?"},
            headers={"X-API-Key": key},
        )
        assert r.status_code == 402, r.text
        body = r.json()
        assert "Monthly AI limit" in (body.get("title") or "")
        assert "shop_id" not in no_vision, "the vision call was made anyway"

    def test_the_sweep_is_skipped_and_the_video_stays_pending(
        self, db, tmp_path, capped,
    ):
        from motodiag.core.models import VideoAnalysisState
        from motodiag.media import analysis_worker as worker_mod

        shop = _shop(db, _user(db))
        sid = create_session("Honda", "CBR600F4i", 2001, db_path=db,
                             vehicle_id=_vehicle(db), shop_id=shop)
        vid = _video_for(db, sid, tmp_path)
        record_cost_event(kind="vision_sweep", model="sonnet",
                          cost_usd_cents=2500, shop_id=shop, db_path=db)

        analyzer = mock.MagicMock()
        with mock.patch.object(
            worker_mod.ffmpeg_module, "extract_frames", return_value=[object()],
        ) as frames, mock.patch.object(
            worker_mod, "VisionAnalyzer", return_value=analyzer,
        ):
            worker_mod.run_analysis_pipeline(vid, db_path=db)

        analyzer.analyze_video_frames.assert_not_called()
        frames.assert_not_called()
        with get_connection(db) as conn:
            state = conn.execute(
                "SELECT analysis_state FROM videos WHERE id = ?", (vid,),
            ).fetchone()[0]
        assert state == VideoAnalysisState.PENDING.value, (
            "nothing failed and nothing was attempted; 'failed' would say otherwise"
        )

    def test_the_cli_refuses_before_it_pays(self, tmp_path, monkeypatch, capped):
        from motodiag.core.config import reset_settings
        from motodiag.engine.client import DiagnosticClient
        from motodiag.cli.main import cli

        db_path = str(tmp_path / "capped.db")
        init_db(db_path)
        monkeypatch.setenv("MOTODIAG_DB_PATH", db_path)
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-not-real")
        reset_settings()
        shop = _shop(db_path, _user(db_path))
        vid = _vehicle(db_path)
        record_cost_event(kind="text_diagnosis", model="haiku",
                          cost_usd_cents=2500, shop_id=shop, db_path=db_path)

        sdk = mock.Mock()
        with mock.patch.object(DiagnosticClient, "_get_client", lambda self: sdk):
            r = CliRunner().invoke(cli, [
                "diagnose", "quick", "--vehicle-id", str(vid),
                "--symptoms", "oil leak", "--shop", str(shop),
            ])
        assert r.exit_code == 1, r.output
        assert "monthly AI limit" in r.output
        sdk.messages.create.assert_not_called()
        assert len(_cost_rows(db_path)) == 1, "a refused call must not be billed"
        reset_settings()


# ---------------------------------------------------------------------------
# 5. The number is visible where the spend is
# ---------------------------------------------------------------------------


class TestTheReportShowsTheCap:
    def _report(self, *args):
        from motodiag.cli.main import cli

        r = CliRunner().invoke(cli, ["costs", "report", *args])
        assert r.exit_code == 0, r.output
        return r.output

    def test_it_says_when_no_cap_is_set(self, api_db):
        assert "cap: none set" in self._report()

    def test_it_shows_the_spend_against_the_cap(self, api_db, capped):
        record_cost_event(kind="vision_guidance", model="sonnet",
                          cost_usd_cents=312, shop_id=4, db_path=api_db)
        out = self._report("--shop", "4", "--this-month")
        assert "cap: $25.00 this month" in out
        assert "spent $3.12" in out
        assert "remaining $21.88" in out

    def test_without_a_shop_it_says_the_cap_is_per_shop(self, api_db, capped):
        assert "per shop per month" in self._report()
