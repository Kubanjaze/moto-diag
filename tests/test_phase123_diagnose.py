"""Phase 123 — Interactive diagnostic session CLI tests.

Covers:
- _resolve_model tier gating (hard + soft modes)
- _load_vehicle / _load_known_issues / _parse_symptoms helpers
- _run_quick creates session, calls diagnose, persists, closes
- _run_interactive: early exit on high confidence, multi-round, hard cap,
  empty input termination
- _persist_response writes diagnosis + token accumulation
- _render_response prints all fields
- CLI: diagnose quick / start / list / show — happy paths and error paths
- Tier enforcement in CLI (individual + --model sonnet)
- Zero live API tokens burned.
"""

from __future__ import annotations

from unittest.mock import patch

import click
import pytest
from click.testing import CliRunner

from motodiag.core.database import init_db, get_connection
from motodiag.core.models import VehicleBase, ProtocolType
from motodiag.core.session_repo import get_session, list_sessions
from motodiag.engine.models import DiagnosticResponse, TokenUsage
from motodiag.vehicles.registry import add_vehicle

from motodiag.cli.diagnose import (
    CONFIDENCE_ACCEPT_THRESHOLD,
    MAX_CLARIFYING_ROUNDS,
    _load_known_issues,
    _load_vehicle,
    _parse_symptoms,
    _persist_response,
    _render_response,
    _resolve_model,
    _run_interactive,
    _run_quick,
    _FakeUsage,
)


# --- Shared test helpers ---


class _DiagItem:
    """Minimal diagnosis-item shim matching engine.models.DiagnosisItem shape."""
    def __init__(self, diagnosis, confidence, severity="medium",
                 rationale="test rationale", recommended_actions=None):
        self.diagnosis = diagnosis
        self.confidence = confidence
        self.severity = severity
        self.rationale = rationale
        self.recommended_actions = recommended_actions or []


def make_response(confidence=0.9, extra_tests=None, diagnoses=None, notes=None):
    """Build a DiagnosticResponse-like shim with controllable confidence."""
    from types import SimpleNamespace
    return SimpleNamespace(
        vehicle_summary="Test Vehicle 2020",
        symptoms_acknowledged=["won't start"],
        diagnoses=(diagnoses if diagnoses is not None else [
            _DiagItem("Stator failure", confidence, "high",
                      "Common on 2000s Harleys", ["Check stator AC output", "Replace if low"]),
        ]),
        additional_tests=(extra_tests if extra_tests is not None else []),
        notes=notes,
    )


def make_usage(input_tokens=500, output_tokens=150, model="haiku"):
    return TokenUsage(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        model=model,
        cost_estimate=0.001,
        latency_ms=1200,
    )


def make_diagnose_fn(responses, usages=None):
    """Factory: returns a diagnose_fn mock that yields responses in order."""
    if not isinstance(responses, list):
        responses = [responses]
    if usages is None:
        usages = [make_usage() for _ in responses]
    state = {"i": 0}

    def _call(**kwargs):
        idx = min(state["i"], len(responses) - 1)
        state["i"] += 1
        return responses[idx], usages[idx]
    _call.state = state
    return _call


@pytest.fixture
def db(tmp_path):
    path = str(tmp_path / "diagnose.db")
    init_db(path)
    return path


@pytest.fixture
def seeded_vehicle(db):
    vid = add_vehicle(VehicleBase(
        make="Harley-Davidson", model="Sportster 1200", year=2001,
        engine_cc=1200, protocol=ProtocolType.J1850,
    ), db_path=db)
    # Fetch back as dict
    with get_connection(db) as conn:
        cursor = conn.execute("SELECT * FROM vehicles WHERE id = ?", (vid,))
        row = dict(cursor.fetchone())
    return row


@pytest.fixture
def cli_db(db, monkeypatch):
    """CLI fixture — same pattern as Phase 122: reset cached Settings after env patch."""
    from motodiag.core.config import reset_settings
    monkeypatch.setenv("MOTODIAG_DB_PATH", db)
    reset_settings()
    yield db
    reset_settings()


# --- _resolve_model ---


class TestResolveModel:
    def test_individual_default_haiku(self):
        assert _resolve_model("individual", None) == "haiku"

    def test_shop_default_haiku(self):
        assert _resolve_model("shop", None) == "haiku"

    def test_shop_can_pick_sonnet(self):
        assert _resolve_model("shop", "sonnet") == "sonnet"

    def test_company_can_pick_sonnet(self):
        assert _resolve_model("company", "sonnet") == "sonnet"

    def test_case_insensitive(self):
        assert _resolve_model("Individual", "HAIKU") == "haiku"

    def test_unknown_model_raises(self):
        with pytest.raises(click.ClickException):
            _resolve_model("shop", "opus")

    def test_individual_sonnet_hard_mode_raises(self, monkeypatch):
        monkeypatch.setenv("MOTODIAG_PAYWALL_MODE", "hard")
        with pytest.raises(click.ClickException, match="Shop tier"):
            _resolve_model("individual", "sonnet")

    def test_individual_sonnet_soft_mode_falls_back(self, monkeypatch):
        monkeypatch.setenv("MOTODIAG_PAYWALL_MODE", "soft")
        result = _resolve_model("individual", "sonnet")
        assert result == "haiku"


# --- Helpers ---


class TestHelpers:
    def test_load_vehicle_found(self, db, seeded_vehicle):
        row = _load_vehicle(seeded_vehicle["id"], db_path=db)
        assert row is not None
        assert row["make"] == "Harley-Davidson"

    def test_load_vehicle_missing(self, db):
        assert _load_vehicle(99999, db_path=db) is None

    def test_load_known_issues_returns_list(self, db, seeded_vehicle):
        result = _load_known_issues("Harley-Davidson", "Sportster 1200", 2001, db_path=db)
        assert isinstance(result, list)

    def test_parse_symptoms_simple(self):
        assert _parse_symptoms("won't start, rough idle") == ["won't start", "rough idle"]

    def test_parse_symptoms_mixed_separators(self):
        assert _parse_symptoms("stalls;dies at idle\nvibration") == \
               ["stalls", "dies at idle", "vibration"]

    def test_parse_symptoms_empty(self):
        assert _parse_symptoms("") == []
        assert _parse_symptoms("   ") == []

    def test_parse_symptoms_strips_whitespace(self):
        assert _parse_symptoms("  stalls  ,  rough idle  ") == ["stalls", "rough idle"]


# --- _run_quick ---


class TestRunQuick:
    def test_creates_and_closes_session(self, db, seeded_vehicle):
        fn = make_diagnose_fn(make_response(confidence=0.9))
        session_id, response = _run_quick(
            vehicle=seeded_vehicle,
            symptoms=["won't start"],
            description=None,
            ai_model="haiku",
            db_path=db,
            diagnose_fn=fn,
        )
        assert session_id > 0
        s = get_session(session_id, db)
        assert s["status"] == "closed"
        assert s["diagnosis"] is not None
        assert "Stator failure" in s["diagnosis"]
        assert s["confidence"] == pytest.approx(0.9)

    def test_diagnose_fn_called_with_context(self, db, seeded_vehicle):
        called = {}

        def _spy(**kwargs):
            called.update(kwargs)
            return make_response(), make_usage()

        _run_quick(
            vehicle=seeded_vehicle,
            symptoms=["won't start", "rough idle"],
            description="Acts up when cold",
            ai_model="haiku",
            db_path=db,
            diagnose_fn=_spy,
        )
        assert called["make"] == "Harley-Davidson"
        assert called["year"] == 2001
        assert called["symptoms"] == ["won't start", "rough idle"]
        assert called["description"] == "Acts up when cold"
        assert called["ai_model"] == "haiku"


# --- _run_interactive ---


class TestRunInteractive:
    def test_high_confidence_stops_after_one_round(self, db, seeded_vehicle):
        fn = make_diagnose_fn(make_response(confidence=0.9))
        answers = iter(["won't start, rough idle"])  # Only initial prompt should fire

        def ask(_q):
            return next(answers)

        sid, resp = _run_interactive(
            vehicle=seeded_vehicle, ai_model="haiku",
            db_path=db, diagnose_fn=fn, prompt_fn=ask,
        )
        assert fn.state["i"] == 1  # one diagnose call
        s = get_session(sid, db)
        assert s["status"] == "closed"

    def test_continues_when_confidence_low_and_additional_tests(self, db, seeded_vehicle):
        # Round 1: low confidence + additional_tests
        # Round 2: high confidence → stop
        fn = make_diagnose_fn([
            make_response(confidence=0.4, extra_tests=["Check battery voltage"]),
            make_response(confidence=0.85),
        ])
        answers = iter(["won't start", "battery reads 12.1V cold"])

        def ask(_q):
            return next(answers)

        sid, resp = _run_interactive(
            vehicle=seeded_vehicle, ai_model="haiku",
            db_path=db, diagnose_fn=fn, prompt_fn=ask,
        )
        assert fn.state["i"] == 2

    def test_hard_cap_at_max_rounds(self, db, seeded_vehicle):
        # Every round is low confidence with a follow-up test.
        # Must cap at MAX_CLARIFYING_ROUNDS (3).
        fn = make_diagnose_fn([
            make_response(confidence=0.3, extra_tests=["t1"]),
            make_response(confidence=0.3, extra_tests=["t2"]),
            make_response(confidence=0.3, extra_tests=["t3"]),
        ])
        answers = iter(["won't start", "ans1", "ans2", "ans3"])

        def ask(_q):
            return next(answers, "")

        _run_interactive(
            vehicle=seeded_vehicle, ai_model="haiku",
            db_path=db, diagnose_fn=fn, prompt_fn=ask,
        )
        assert fn.state["i"] == MAX_CLARIFYING_ROUNDS

    def test_empty_answer_terminates_loop(self, db, seeded_vehicle):
        # Round 1: low confidence + test. Mechanic answers empty → stop.
        fn = make_diagnose_fn([
            make_response(confidence=0.4, extra_tests=["Check fuel pressure"]),
            # Second call would happen if loop continued — should NOT be called.
            make_response(confidence=0.9),
        ])
        answers = iter(["won't start", ""])

        def ask(_q):
            return next(answers, "")

        _run_interactive(
            vehicle=seeded_vehicle, ai_model="haiku",
            db_path=db, diagnose_fn=fn, prompt_fn=ask,
        )
        assert fn.state["i"] == 1

    def test_skip_terminates_loop(self, db, seeded_vehicle):
        fn = make_diagnose_fn([
            make_response(confidence=0.4, extra_tests=["t"]),
            make_response(confidence=0.9),
        ])
        answers = iter(["won't start", "skip"])

        def ask(_q):
            return next(answers, "")

        _run_interactive(
            vehicle=seeded_vehicle, ai_model="haiku",
            db_path=db, diagnose_fn=fn, prompt_fn=ask,
        )
        assert fn.state["i"] == 1

    def test_no_additional_tests_stops_even_at_low_confidence(self, db, seeded_vehicle):
        fn = make_diagnose_fn([make_response(confidence=0.4, extra_tests=[])])
        answers = iter(["won't start"])

        def ask(_q):
            return next(answers)

        _run_interactive(
            vehicle=seeded_vehicle, ai_model="haiku",
            db_path=db, diagnose_fn=fn, prompt_fn=ask,
        )
        assert fn.state["i"] == 1

    def test_tokens_accumulate_across_rounds(self, db, seeded_vehicle):
        fn = make_diagnose_fn([
            make_response(confidence=0.3, extra_tests=["t1"]),
            make_response(confidence=0.9),
        ], usages=[make_usage(input_tokens=500, output_tokens=150),
                   make_usage(input_tokens=600, output_tokens=200)])
        answers = iter(["won't start", "ans1"])

        def ask(_q):
            return next(answers)

        sid, _ = _run_interactive(
            vehicle=seeded_vehicle, ai_model="haiku",
            db_path=db, diagnose_fn=fn, prompt_fn=ask,
        )
        s = get_session(sid, db)
        # 500+150 + 600+200 = 1450 total tokens
        assert s["tokens_used"] == 1450
        assert s["ai_model_used"] == "haiku"


# --- _persist_response ---


class TestPersistResponse:
    def test_writes_diagnosis_and_tokens(self, db, seeded_vehicle):
        from motodiag.core.session_repo import create_session
        sid = create_session(
            "Harley-Davidson", "Sportster 1200", 2001,
            symptoms=["won't start"], db_path=db,
        )
        resp = make_response(confidence=0.88)
        usage = make_usage(input_tokens=1000, output_tokens=300)
        _persist_response(sid, resp, usage, "haiku", db)
        s = get_session(sid, db)
        assert "Stator failure" in s["diagnosis"]
        assert s["confidence"] == pytest.approx(0.88)
        assert s["tokens_used"] == 1300
        assert s["ai_model_used"] == "haiku"

    def test_empty_diagnoses_still_persists(self, db, seeded_vehicle):
        from motodiag.core.session_repo import create_session
        sid = create_session(
            "Harley-Davidson", "Sportster 1200", 2001, db_path=db,
        )
        resp = make_response(confidence=0, diagnoses=[], notes="Ambiguous — more info needed.")
        _persist_response(sid, resp, make_usage(), "haiku", db)
        s = get_session(sid, db)
        assert s["diagnosis"] is not None
        assert "Ambiguous" in s["diagnosis"]


# --- _render_response ---


class TestRenderResponse:
    def test_renders_all_fields(self):
        from rich.console import Console
        import io
        buf = io.StringIO()
        console = Console(file=buf, force_terminal=False, width=120)
        resp = make_response(confidence=0.87, extra_tests=["Check A", "Check B"],
                             notes="Watch for intermittent repeat.")
        _render_response(resp, console)
        out = buf.getvalue()
        assert "Stator failure" in out
        assert "0.87" in out
        assert "Check A" in out
        assert "Watch for intermittent" in out

    def test_empty_diagnoses_shows_note(self):
        from rich.console import Console
        import io
        buf = io.StringIO()
        console = Console(file=buf, force_terminal=False, width=120)
        resp = make_response(diagnoses=[])
        _render_response(resp, console)
        out = buf.getvalue()
        assert "No definitive diagnosis" in out


# --- CLI ---


class TestCliDiagnose:
    def _seed_vehicle(self, db_path):
        return add_vehicle(VehicleBase(
            make="Honda", model="CBR929RR", year=2001,
            engine_cc=929, protocol=ProtocolType.K_LINE,
        ), db_path=db_path)

    def test_quick_happy_path(self, cli_db):
        vid = self._seed_vehicle(cli_db)
        from motodiag.cli.main import cli

        fn = make_diagnose_fn(make_response(confidence=0.88))
        with patch("motodiag.cli.diagnose._default_diagnose_fn", fn):
            runner = CliRunner()
            r = runner.invoke(cli, [
                "diagnose", "quick",
                "--vehicle-id", str(vid),
                "--symptoms", "won't start, battery weak",
            ])
        assert r.exit_code == 0, r.output
        assert "Session #" in r.output
        assert "Stator failure" in r.output

    def test_quick_missing_vehicle(self, cli_db):
        from motodiag.cli.main import cli
        runner = CliRunner()
        r = runner.invoke(cli, [
            "diagnose", "quick",
            "--vehicle-id", "99999",
            "--symptoms", "x",
        ])
        assert r.exit_code != 0
        assert "not found" in r.output.lower()

    def test_quick_sonnet_on_individual_hard_mode(self, cli_db, monkeypatch):
        monkeypatch.setenv("MOTODIAG_PAYWALL_MODE", "hard")
        monkeypatch.setenv("MOTODIAG_SUBSCRIPTION_TIER", "individual")
        vid = self._seed_vehicle(cli_db)
        from motodiag.cli.main import cli
        runner = CliRunner()
        r = runner.invoke(cli, [
            "diagnose", "quick",
            "--vehicle-id", str(vid),
            "--symptoms", "x",
            "--model", "sonnet",
        ])
        assert r.exit_code != 0
        assert "shop tier" in r.output.lower() or "individual" in r.output.lower()

    def test_quick_sonnet_on_shop_succeeds(self, cli_db, monkeypatch):
        monkeypatch.setenv("MOTODIAG_PAYWALL_MODE", "hard")
        monkeypatch.setenv("MOTODIAG_SUBSCRIPTION_TIER", "shop")
        vid = self._seed_vehicle(cli_db)
        from motodiag.cli.main import cli
        fn = make_diagnose_fn(make_response(confidence=0.9))
        with patch("motodiag.cli.diagnose._default_diagnose_fn", fn):
            runner = CliRunner()
            r = runner.invoke(cli, [
                "diagnose", "quick",
                "--vehicle-id", str(vid),
                "--symptoms", "x",
                "--model", "sonnet",
            ])
        assert r.exit_code == 0, r.output

    def test_list_empty(self, cli_db):
        from motodiag.cli.main import cli
        runner = CliRunner()
        r = runner.invoke(cli, ["diagnose", "list"])
        assert r.exit_code == 0
        assert "No sessions yet" in r.output

    def test_list_after_quick(self, cli_db):
        vid = self._seed_vehicle(cli_db)
        from motodiag.cli.main import cli
        fn = make_diagnose_fn(make_response(confidence=0.88))
        with patch("motodiag.cli.diagnose._default_diagnose_fn", fn):
            runner = CliRunner()
            runner.invoke(cli, [
                "diagnose", "quick",
                "--vehicle-id", str(vid),
                "--symptoms", "starts then dies",
            ])
            r = runner.invoke(cli, ["diagnose", "list"])
        assert r.exit_code == 0
        assert "CBR929RR" in r.output

    def test_list_filter_by_status(self, cli_db):
        vid = self._seed_vehicle(cli_db)
        from motodiag.cli.main import cli
        fn = make_diagnose_fn(make_response(confidence=0.9))
        with patch("motodiag.cli.diagnose._default_diagnose_fn", fn):
            runner = CliRunner()
            runner.invoke(cli, [
                "diagnose", "quick",
                "--vehicle-id", str(vid),
                "--symptoms", "starts then dies",
            ])
            r = runner.invoke(cli, ["diagnose", "list", "--status", "closed"])
        assert r.exit_code == 0
        assert "CBR929RR" in r.output
        # Open-filter should show nothing now
        r2 = runner.invoke(cli, ["diagnose", "list", "--status", "open"])
        assert r2.exit_code == 0
        assert "No sessions yet" in r2.output

    def test_show_happy_path(self, cli_db):
        vid = self._seed_vehicle(cli_db)
        from motodiag.cli.main import cli
        fn = make_diagnose_fn(make_response(confidence=0.91))
        with patch("motodiag.cli.diagnose._default_diagnose_fn", fn):
            runner = CliRunner()
            r = runner.invoke(cli, [
                "diagnose", "quick",
                "--vehicle-id", str(vid),
                "--symptoms", "stalls",
            ])
        # Find the session ID
        sessions = list_sessions(db_path=cli_db)
        sid = sessions[0]["id"]

        r = runner.invoke(cli, ["diagnose", "show", str(sid)])
        assert r.exit_code == 0
        assert "Stator failure" in r.output
        assert f"#{sid}" in r.output

    def test_show_missing(self, cli_db):
        from motodiag.cli.main import cli
        runner = CliRunner()
        r = runner.invoke(cli, ["diagnose", "show", "99999"])
        assert r.exit_code != 0
        assert "not found" in r.output.lower()


# --- Regression safety ---


class TestRegressionSafety:
    def test_diagnose_group_registered(self):
        from motodiag.cli.main import cli
        assert "diagnose" in cli.commands
        group = cli.commands["diagnose"]
        subs = set(group.commands.keys())
        assert {"start", "quick", "list", "show"}.issubset(subs)

    def test_all_existing_cli_groups_still_present(self):
        from motodiag.cli.main import cli
        for expected in ("info", "tier", "garage", "intake", "diagnose"):
            assert expected in cli.commands
