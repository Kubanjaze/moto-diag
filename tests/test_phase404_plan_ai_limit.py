"""Phase 404, Logic item 2 (F271) — each plan's AI figure, kept by the server.

Fresh databases with a shop, an owner on each plan and planted
``cost_events`` rows. The figures are K84's: Individual $5, Shop $50,
Company $150, per shop per UTC calendar month. The shop's plan is the
highest active subscription among its active owner-role members in
``shop_members``, never ``shops.owner_user_id`` and never the caller's own.
The brake (``MOTODIAG_COST_CAP_MONTHLY_USD_CENTS``) stays 0 and refuses
nothing on its own. Every paid call site in the Step 0 census refuses
before its stand-in client is called. Never the live database.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

import pytest
from click.testing import CliRunner
from fastapi.testclient import TestClient

from motodiag.api import create_app
from motodiag.auth.api_key_repo import create_api_key
from motodiag.billing.subscription_repo import shop_plan
from motodiag.core.config import reset_settings
from motodiag.core.database import get_connection, init_db
from motodiag.core.session_repo import create_session
from motodiag.shop import create_shop, create_work_order, open_work_order
from motodiag.shop.cost_cap import (
    PLAN_AI_CENTS,
    CostCapExceeded,
    PlanAILimitReached,
    check_cost_cap,
    month_turns,
)
from motodiag.shop.cost_repo import record_cost_event
from motodiag.shop.rbac import seed_first_owner

# ---------------------------------------------------------------------------
# Fixtures and helpers
# ---------------------------------------------------------------------------


@pytest.fixture
def db(tmp_path, monkeypatch):
    path = str(tmp_path / "phase404_ai.db")
    init_db(path)
    monkeypatch.delenv("MOTODIAG_COST_CAP_MONTHLY_USD_CENTS", raising=False)
    reset_settings()
    yield path
    reset_settings()


@pytest.fixture
def cli_db(db, tmp_path, monkeypatch):
    monkeypatch.setenv("MOTODIAG_DB_PATH", db)
    monkeypatch.setenv("MOTODIAG_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-not-real")
    monkeypatch.setenv("COLUMNS", "240")
    reset_settings()
    yield db
    reset_settings()


@pytest.fixture
def api_db(cli_db, monkeypatch):
    for tier in ("anonymous", "individual", "shop", "company"):
        monkeypatch.setenv(f"MOTODIAG_RATE_LIMIT_{tier.upper()}_PER_MINUTE", "9999")
    reset_settings()
    yield cli_db
    reset_settings()


@pytest.fixture
def brake(monkeypatch):
    def _set(cents: int) -> None:
        monkeypatch.setenv("MOTODIAG_COST_CAP_MONTHLY_USD_CENTS", str(cents))
        reset_settings()
    return _set


def _user(db_path: str, name: str, tier: str | None = None) -> int:
    with get_connection(db_path) as conn:
        uid = conn.execute(
            "INSERT INTO users (username, email, tier, is_active) VALUES (?, ?, 'individual', 1)",
            (name, f"{name}@ex.com"),
        ).lastrowid
    if tier is not None:
        _subscribe(db_path, uid, tier)
    return uid


def _subscribe(db_path: str, uid: int, tier: str) -> None:
    with get_connection(db_path) as conn:
        conn.execute(
            "INSERT INTO subscriptions (user_id, tier, status, current_period_end) "
            "VALUES (?, ?, 'active', datetime('now', '+30 days'))",
            (uid, tier),
        )


def _shop_as_the_api_makes_it(db_path: str, owner: int, name: str = "Bandit Moto") -> int:
    """``create_shop_endpoint``'s two calls: no owner given to create_shop,
    so ``shops.owner_user_id`` keeps its default; the owner goes to
    ``shop_members``."""
    shop = create_shop(name, db_path=db_path)
    seed_first_owner(shop, owner, db_path=db_path)
    return shop


def _member(db_path: str, uid: int, shop: int, role: str = "tech", active: int = 1) -> None:
    with get_connection(db_path) as conn:
        conn.execute(
            "INSERT INTO shop_members (user_id, shop_id, role, is_active) VALUES (?, ?, ?, ?)",
            (uid, shop, role, active),
        )


def _spend(db_path: str, shop: int, cents: int) -> None:
    record_cost_event(kind="text_diagnosis", model="haiku",
                      cost_usd_cents=cents, shop_id=shop, db_path=db_path)


def _planned_shop(db_path: str, plan: str, spent: int) -> int:
    shop = _shop_as_the_api_makes_it(db_path, _user(db_path, f"owner_{plan}", plan))
    _spend(db_path, shop, spent)
    return shop


def _next_month() -> str:
    turns = month_turns(datetime.now(timezone.utc))
    return f"1 {turns:%B %Y}"


# ---------------------------------------------------------------------------
# 1. The figures and the check
# ---------------------------------------------------------------------------


class TestTheFigures:
    def test_k84s_figures_and_no_other(self):
        assert PLAN_AI_CENTS == {"individual": 500, "shop": 5000, "company": 15000}

    @pytest.mark.parametrize("plan", ["individual", "shop", "company"])
    def test_at_the_figure_refused(self, db, plan):
        shop = _planned_shop(db, plan, PLAN_AI_CENTS[plan])
        with pytest.raises(PlanAILimitReached):
            check_cost_cap(shop, db_path=db)

    @pytest.mark.parametrize("plan", ["individual", "shop", "company"])
    def test_one_cent_under_the_figure_served(self, db, plan):
        shop = _planned_shop(db, plan, PLAN_AI_CENTS[plan] - 1)
        check_cost_cap(shop, db_path=db)

    @pytest.mark.parametrize("plan,name,dollars", [
        ("individual", "Individual", "$5.00"),
        ("shop", "Shop", "$50.00"),
        ("company", "Company", "$150.00"),
    ])
    def test_the_message_names_the_plan_and_the_month_turning(self, db, plan, name, dollars):
        shop = _planned_shop(db, plan, PLAN_AI_CENTS[plan])
        with pytest.raises(PlanAILimitReached) as exc:
            check_cost_cap(shop, db_path=db)
        msg = str(exc.value)
        assert f"The {name} plan's {dollars} of AI" in msg
        assert f"It starts again on {_next_month()} (UTC)." in msg
        assert isinstance(exc.value, CostCapExceeded)

    def test_last_months_spend_does_not_count(self, db):
        shop = _planned_shop(db, "individual", 0)
        with get_connection(db) as conn:
            conn.execute(
                "INSERT INTO cost_events (kind, model, cost_usd_cents, shop_id, created_at) "
                "VALUES ('text_diagnosis', 'haiku', 99999, ?, '2000-01-15 00:00:00')",
                (shop,))
        check_cost_cap(shop, db_path=db)

    def test_the_month_turns_in_december(self):
        assert month_turns(datetime(2026, 12, 31, 23, 59, tzinfo=timezone.utc)) == \
            datetime(2027, 1, 1, tzinfo=timezone.utc)
        assert month_turns(datetime(2026, 11, 18, tzinfo=timezone.utc)) == \
            datetime(2026, 12, 1, tzinfo=timezone.utc)


class TestTheShopsPlan:
    @pytest.mark.parametrize("user1_plan", [None, "individual"])
    def test_the_owner_in_shop_members_not_owner_user_id(self, db, user1_plan):
        if user1_plan is not None:
            _subscribe(db, 1, user1_plan)
        shop = _shop_as_the_api_makes_it(db, _user(db, "real_owner", "company"))
        with get_connection(db) as conn:
            assert conn.execute("SELECT owner_user_id FROM shops WHERE id = ?",
                                (shop,)).fetchone()[0] == 1
        assert shop_plan(shop, db_path=db) == "company"
        _spend(db, shop, 600)  # past Individual's $5, inside Company's $150
        check_cost_cap(shop, db_path=db)
        _spend(db, shop, PLAN_AI_CENTS["company"] - 600)
        with pytest.raises(PlanAILimitReached) as exc:
            check_cost_cap(shop, db_path=db)
        assert "Company" in str(exc.value)

    def test_two_active_owners_the_higher_plan(self, db):
        shop = _shop_as_the_api_makes_it(db, _user(db, "a", "individual"))
        _member(db, _user(db, "b", "shop"), shop, role="owner")
        assert shop_plan(shop, db_path=db) == "shop"
        _spend(db, shop, 600)
        check_cost_cap(shop, db_path=db)
        _spend(db, shop, PLAN_AI_CENTS["shop"] - 600)
        with pytest.raises(PlanAILimitReached):
            check_cost_cap(shop, db_path=db)

    def test_an_inactive_owner_is_not_counted(self, db):
        shop = _shop_as_the_api_makes_it(db, _user(db, "a", "individual"))
        _member(db, _user(db, "gone", "company"), shop, role="owner", active=0)
        assert shop_plan(shop, db_path=db) == "individual"
        _spend(db, shop, 600)
        with pytest.raises(PlanAILimitReached):
            check_cost_cap(shop, db_path=db)

    def test_a_member_who_is_not_an_owner_is_not_counted(self, db):
        shop = _shop_as_the_api_makes_it(db, _user(db, "a", "individual"))
        _member(db, _user(db, "tech", "company"), shop, role="tech")
        assert shop_plan(shop, db_path=db) == "individual"

    def test_the_resolve_tier_rule_and_the_shops_plan_agree(self, db):
        from motodiag.auth.api_key_repo import ApiKey
        from motodiag.auth.deps import resolve_tier

        shop = _shop_as_the_api_makes_it(db, _user(db, "a", "individual"))
        _member(db, _user(db, "b", "company"), shop, role="owner")
        tech = _user(db, "tech")
        _member(db, tech, shop)
        cred = ApiKey(id=1, user_id=tech, key_prefix="mds_x", key_hash="x",
                      kind="session", created_at="2026-11-18", is_active=True)
        assert resolve_tier(cred, db_path=db) == shop_plan(shop, db_path=db) == "company"


class TestTheBrake:
    def test_the_brake_at_0_alone_refuses_nothing(self, db):
        shop = _shop_as_the_api_makes_it(db, _user(db, "noplan"))
        _spend(db, shop, 10_000_000)
        assert shop_plan(shop, db_path=db) is None
        check_cost_cap(shop, db_path=db)

    def test_a_shop_with_no_plan_is_held_only_by_the_brake(self, db, brake):
        shop = _shop_as_the_api_makes_it(db, _user(db, "noplan"))
        _spend(db, shop, 2500)
        brake(2500)
        with pytest.raises(CostCapExceeded) as exc:
            check_cost_cap(shop, db_path=db)
        assert not isinstance(exc.value, PlanAILimitReached)

    def test_a_shop_with_no_owner_is_held_only_by_the_brake(self, db, brake):
        shop = create_shop("no owner", db_path=db)
        _spend(db, shop, 10_000_000)
        check_cost_cap(shop, db_path=db)
        brake(2500)
        with pytest.raises(CostCapExceeded):
            check_cost_cap(shop, db_path=db)

    def test_the_lower_brake_refuses_first(self, db, brake):
        shop = _planned_shop(db, "shop", 2500)
        brake(2500)
        with pytest.raises(CostCapExceeded) as exc:
            check_cost_cap(shop, db_path=db)
        assert not isinstance(exc.value, PlanAILimitReached)

    def test_the_lower_plan_refuses_first(self, db, brake):
        shop = _planned_shop(db, "company", PLAN_AI_CENTS["company"])
        brake(20000)
        with pytest.raises(PlanAILimitReached):
            check_cost_cap(shop, db_path=db)

    def test_an_unattributed_call_is_not_held(self, db):
        _planned_shop(db, "individual", 99999)
        check_cost_cap(None, db_path=db)


# ---------------------------------------------------------------------------
# 2. The API's answer
# ---------------------------------------------------------------------------


def test_the_error_table_keeps_the_brakes_row_and_adds_the_plans():
    from motodiag.api.errors import _exc_class_chain

    rows = {cls: (status, slug, title) for cls, status, slug, title in _exc_class_chain()}
    assert rows[CostCapExceeded] == (402, "ai-spend-cap-reached",
                                     "Monthly AI limit reached for this shop")
    assert rows[PlanAILimitReached] == (402, "plan-ai-limit-reached",
                                        "Monthly AI allowance for this plan reached")


@pytest.fixture
def no_vision(monkeypatch):
    """Stub ffmpeg and the vision call; record whether either was reached."""
    import motodiag.media.ffmpeg as ff
    from motodiag.media.vision_analysis_pipeline import VisionAnalyzer

    calls: list[str] = []

    def _frames(video_path, output_dir, max_frames=60):
        calls.append("frames")
        return []

    def _answer(self, *args, **kwargs):
        calls.append("vision")
        raise AssertionError("the paid vision call was reached")

    monkeypatch.setattr(ff, "extract_frames", _frames)
    monkeypatch.setattr(VisionAnalyzer, "answer_question_about_frames", _answer)
    return calls


def _client(db_path: str) -> TestClient:
    return TestClient(create_app(db_path_override=db_path), raise_server_exceptions=False)


def _video(db_path: str, session_id: int, tmp_path) -> int:
    f = Path(tmp_path) / "v.mp4"
    f.write_bytes(b"video")
    with get_connection(db_path) as conn:
        return conn.execute(
            "INSERT INTO videos (session_id, file_path, sha256, started_at, "
            "duration_ms, width, height, file_size_bytes) "
            "VALUES (?, ?, 'a', '2026-11-18T00:00:00Z', 1000, 640, 480, 5)",
            (session_id, str(f)),
        ).lastrowid


def _bike(db_path: str) -> int:
    with get_connection(db_path) as conn:
        return conn.execute(
            "INSERT INTO vehicles (make, model, year, protocol) "
            "VALUES ('Honda', 'CBR600F4i', 2001, 'none')").lastrowid


def _ask(client, key, db_path, tmp_path):
    r = client.post("/v1/sessions", headers={"X-API-Key": key}, json={
        "vehicle_make": "Honda", "vehicle_model": "CBR600F4i", "vehicle_year": 2001,
        "symptoms": ["oil leak"], "vehicle_id": _bike(db_path)})
    assert r.status_code == 201, r.text
    sid = r.json()["id"]
    vid = _video(db_path, sid, tmp_path)
    return client.post(f"/v1/sessions/{sid}/videos/{vid}/ask",
                       json={"question": "Where is the leak?"},
                       headers={"X-API-Key": key})


class TestThroughTheAPI:
    def test_the_video_question_is_402_before_it_pays(self, api_db, tmp_path, no_vision):
        owner = _user(api_db, "owner", "shop")
        shop = _shop_as_the_api_makes_it(api_db, owner)
        _spend(api_db, shop, PLAN_AI_CENTS["shop"])
        r = _ask(_client(api_db), create_api_key(owner, db_path=api_db)[1], api_db, tmp_path)
        assert r.status_code == 402, r.text
        body = r.json()
        assert body["type"].endswith("plan-ai-limit-reached")
        assert body["title"] == "Monthly AI allowance for this plan reached"
        assert "The Shop plan's $50.00 of AI" in body["detail"]
        assert _next_month() in body["detail"]
        assert no_vision == []

    def test_control_under_the_figure_the_question_goes_through(
            self, api_db, tmp_path, no_vision):
        owner = _user(api_db, "owner", "shop")
        shop = _shop_as_the_api_makes_it(api_db, owner)
        _spend(api_db, shop, PLAN_AI_CENTS["shop"] - 1)
        _ask(_client(api_db), create_api_key(owner, db_path=api_db)[1], api_db, tmp_path)
        assert no_vision[:1] == ["frames"]

    def test_the_owners_plan_not_the_callers(self, api_db, tmp_path, no_vision):
        """A technician on Company in a shop whose owner is on Individual is
        held to Individual's $5: the shop's plan, not the caller's."""
        shop = _shop_as_the_api_makes_it(api_db, _user(api_db, "owner", "individual"))
        tech = _user(api_db, "tech", "company")
        _member(api_db, tech, shop)
        _spend(api_db, shop, 600)
        r = _ask(_client(api_db), create_api_key(tech, db_path=api_db)[1], api_db, tmp_path)
        assert r.status_code == 402, r.text
        assert "The Individual plan's $5.00" in r.json()["detail"]
        assert no_vision == []

    def test_the_transcript_upload_is_402_before_the_audio_is_stored(
            self, api_db, tmp_path, monkeypatch):
        import io
        import json
        import wave

        import motodiag.api.routes.transcripts as route

        queued: list = []
        monkeypatch.setattr(route, "run_extraction_pipeline",
                            lambda *a, **k: queued.append(a))
        owner = _user(api_db, "owner", "shop")
        shop = _shop_as_the_api_makes_it(api_db, owner)
        with get_connection(api_db) as conn:
            cust = conn.execute("INSERT INTO customers (name, phone, email) "
                                "VALUES ('Al', '555', 'a@ex.com')").lastrowid
        wo = create_work_order(shop_id=shop, vehicle_id=_bike(api_db), customer_id=cust,
                               title="brakes", priority=2, db_path=api_db)
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(16000)
            wf.writeframes(b"\x00\x00" * 16000)
        _spend(api_db, shop, PLAN_AI_CENTS["shop"])
        meta = {"captured_at": "2026-11-18T10:00:00Z", "duration_ms": 1000,
                "language": "en-US", "preview_text": "squeal", "preview_engine": "ios-speech"}
        r = _client(api_db).post(
            f"/v1/shop/{shop}/work-orders/{wo}/transcripts",
            files={"file": ("v.wav", buf.getvalue(), "audio/wav")},
            data={"metadata": json.dumps(meta)},
            headers={"X-API-Key": create_api_key(owner, db_path=api_db)[1]})
        assert r.status_code == 402, r.text
        assert r.json()["type"].endswith("plan-ai-limit-reached")
        assert queued == []
        with get_connection(api_db) as conn:
            assert conn.execute("SELECT count(*) FROM voice_transcripts").fetchone()[0] == 0
        assert not list((tmp_path / "data").rglob("*.wav"))


def test_the_video_sweep_leaves_the_video_pending(db, tmp_path):
    from motodiag.core.models import VideoAnalysisState
    from motodiag.media import analysis_worker as worker_mod

    shop = _planned_shop(db, "company", PLAN_AI_CENTS["company"])
    sid = create_session("Honda", "CBR600F4i", 2001, db_path=db,
                         vehicle_id=_bike(db), shop_id=shop)
    vid = _video(db, sid, tmp_path)
    analyzer = mock.MagicMock()
    with mock.patch.object(worker_mod.ffmpeg_module, "extract_frames",
                           return_value=[object()]) as frames, \
            mock.patch.object(worker_mod, "VisionAnalyzer", return_value=analyzer):
        worker_mod.run_analysis_pipeline(vid, db_path=db)
    analyzer.analyze_video_frames.assert_not_called()
    frames.assert_not_called()
    with get_connection(db) as conn:
        state = conn.execute("SELECT analysis_state FROM videos WHERE id = ?",
                             (vid,)).fetchone()[0]
    assert state == VideoAnalysisState.PENDING.value


# ---------------------------------------------------------------------------
# 3. Through the CLI: a red line, exit 1, and no call to the stand-in
# ---------------------------------------------------------------------------


def _cli(*args):
    from motodiag.cli.main import cli

    return CliRunner().invoke(cli, list(args))


class _RecordingShopAIClient:
    """A stand-in ShopAIClient that records a paid call and fails the test."""

    calls: list = []

    def __init__(self, *args, **kwargs):
        self.model = kwargs.get("model", "haiku")

    def ask(self, *args, **kwargs):
        type(self).calls.append(kwargs)
        raise AssertionError("the paid call was reached")


@pytest.fixture
def shop_ai(monkeypatch):
    import motodiag.shop.labor_estimator as labor
    import motodiag.shop.parts_sourcing as sourcing
    import motodiag.shop.priority_scorer as priority

    _RecordingShopAIClient.calls = []
    for mod in (labor, sourcing, priority):
        monkeypatch.setattr(mod, "ShopAIClient", _RecordingShopAIClient)
    return _RecordingShopAIClient.calls


def _open_wo(db_path: str, shop: int) -> int:
    with get_connection(db_path) as conn:
        cust = conn.execute("INSERT INTO customers (name, phone, email) "
                            "VALUES ('Jane', '555', 'j@ex.com')").lastrowid
    wo = create_work_order(shop, _bike(db_path), cust, "oil change", db_path=db_path)
    open_work_order(wo, db_path=db_path)
    return wo


def _part(db_path: str) -> int:
    with get_connection(db_path) as conn:
        return conn.execute(
            "INSERT INTO parts (slug, oem_part_number, brand, description, category, "
            "make, model_pattern, typical_cost_cents, verified_by) VALUES "
            "('pad-404', 'HD-404', 'EBC', 'pad', 'brakes', 'honda', 'CBR%', 1500, 'test')"
        ).lastrowid


class TestThroughTheCLI:
    def test_diagnose(self, cli_db):
        from motodiag.engine.client import DiagnosticClient

        shop = _planned_shop(cli_db, "company", PLAN_AI_CENTS["company"])
        sdk = mock.Mock()
        with mock.patch.object(DiagnosticClient, "_get_client", lambda self: sdk):
            r = _cli("diagnose", "quick", "--vehicle-id", str(_bike(cli_db)),
                     "--symptoms", "oil leak", "--shop", str(shop))
        assert r.exit_code == 1, r.output
        assert "The Company plan's $150.00 of AI" in r.output
        sdk.messages.create.assert_not_called()

    def test_code_explain(self, cli_db):
        from motodiag.engine.client import DiagnosticClient

        _planned_shop(cli_db, "individual", PLAN_AI_CENTS["individual"])
        sdk = mock.Mock()
        with mock.patch.object(DiagnosticClient, "_get_client", lambda self: sdk):
            r = _cli("code", "P0171", "--explain", "--vehicle-id", str(_bike(cli_db)))
        assert r.exit_code == 1, r.output
        assert "The Individual plan's $5.00 of AI" in r.output
        sdk.messages.create.assert_not_called()

    def test_control_code_explain_under_the_figure_reaches_the_client(self, cli_db):
        from motodiag.engine.client import DiagnosticClient

        _planned_shop(cli_db, "individual", PLAN_AI_CENTS["individual"] - 1)
        sdk = mock.Mock()
        with mock.patch.object(DiagnosticClient, "_get_client", lambda self: sdk):
            _cli("code", "P0171", "--explain", "--vehicle-id", str(_bike(cli_db)))
        assert sdk.messages.create.called

    @pytest.mark.parametrize("command", [["intake", "photo"], ["garage", "add-from-photo"]])
    def test_photo_identification(self, cli_db, tmp_path, monkeypatch, command):
        from PIL import Image

        import motodiag.intake.vehicle_identifier as vi

        seen: list = []
        monkeypatch.setattr(vi, "_default_vision_call",
                            lambda *a: seen.append(a) or ("{}", 0, 0))
        img = tmp_path / "bike.jpg"
        Image.new("RGB", (32, 32), "red").save(img)
        _planned_shop(cli_db, "shop", PLAN_AI_CENTS["shop"])
        r = _cli(*command, str(img))
        assert r.exit_code != 0, r.output
        assert "The Shop plan's $50.00 of AI" in r.output
        assert seen == []

    def test_the_labor_estimate(self, cli_db, shop_ai):
        from motodiag.shop.labor_estimator import estimate_labor

        shop = _planned_shop(cli_db, "shop", PLAN_AI_CENTS["shop"])
        wo = _open_wo(cli_db, shop)
        with pytest.raises(PlanAILimitReached):
            estimate_labor(wo, db_path=cli_db)
        with pytest.raises(PlanAILimitReached):
            estimate_labor(wo, db_path=cli_db, client=_RecordingShopAIClient())
        r = _cli("shop", "labor", "estimate", str(wo))
        assert r.exit_code == 1, r.output
        assert "The Shop plan's $50.00 of AI" in r.output
        r = _cli("shop", "labor", "bulk", "--shop", str(shop))
        assert r.exit_code == 1, r.output
        assert "The Shop plan's $50.00 of AI" in r.output
        assert shop_ai == []

    def test_control_the_labor_estimate_under_the_figure_reaches_the_client(
            self, cli_db, shop_ai):
        from motodiag.shop.labor_estimator import estimate_labor

        shop = _planned_shop(cli_db, "shop", PLAN_AI_CENTS["shop"] - 1)
        with pytest.raises(AssertionError, match="paid call was reached"):
            estimate_labor(_open_wo(cli_db, shop), db_path=cli_db)
        assert len(shop_ai) == 1

    def test_the_priority_score(self, cli_db, shop_ai):
        from motodiag.shop.priority_scorer import score_work_order

        shop = _planned_shop(cli_db, "company", PLAN_AI_CENTS["company"])
        wo = _open_wo(cli_db, shop)
        with pytest.raises(PlanAILimitReached):
            score_work_order(wo, db_path=cli_db)
        r = _cli("shop", "priority", "score", str(wo))
        assert r.exit_code == 1, r.output
        assert "The Company plan's $150.00" in r.output
        r = _cli("shop", "priority", "rescore-all", "--shop", str(shop))
        assert r.exit_code == 1, r.output
        assert shop_ai == []

    def test_the_parts_sourcing(self, cli_db, shop_ai):
        from motodiag.shop.parts_sourcing import recommend_source

        _planned_shop(cli_db, "individual", PLAN_AI_CENTS["individual"])
        part = _part(cli_db)
        with pytest.raises(PlanAILimitReached):
            recommend_source(part, db_path=cli_db)
        r = _cli("shop", "sourcing", "recommend", "--part-id", str(part))
        assert r.exit_code == 1, r.output
        assert "The Individual plan's $5.00" in r.output
        assert shop_ai == []

    def test_two_shops_in_the_database_stay_unattributed(self, cli_db, shop_ai):
        from motodiag.shop.parts_sourcing import recommend_source

        _planned_shop(cli_db, "individual", PLAN_AI_CENTS["individual"])
        _shop_as_the_api_makes_it(cli_db, _user(cli_db, "other", "shop"), name="Other")
        with pytest.raises(AssertionError, match="paid call was reached"):
            recommend_source(_part(cli_db), db_path=cli_db)
