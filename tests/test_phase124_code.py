"""Phase 124 — Fault code lookup CLI tests.

Covers:
- `_lookup_local` fallback chain (make-specific → generic → None).
- `_classify_fallback` for OBD-II generic / chassis / unknown formats.
- `_render_local` smoke check + yellow fallback banner behavior.
- `_render_explain` prints all sections (causes, tests, repair, hours/cost,
  safety-critical banner).
- `_render_category_list` empty + populated paths.
- CLI `code` command: happy-path lookup, unknown-code fallback, make filter,
  category list, --explain happy path, --explain error paths, tier gating.
- Command is registered alongside existing CLI commands.
- Zero live API tokens burned (all interpret calls mocked via `patch`).
"""

from __future__ import annotations

import io
from types import SimpleNamespace
from unittest.mock import patch

import click
import pytest
from click.testing import CliRunner
from rich.console import Console

from motodiag.core.database import init_db
from motodiag.core.models import (
    DTCCategory,
    DTCCode,
    ProtocolType,
    Severity,
    SymptomCategory,
    VehicleBase,
)
from motodiag.engine.models import TokenUsage
from motodiag.knowledge.dtc_repo import add_dtc
from motodiag.vehicles.registry import add_vehicle

from motodiag.cli.code import (
    _classify_fallback,
    _lookup_local,
    _render_category_list,
    _render_explain,
    _render_local,
    _run_explain,
)


# --- Shared test fixtures and helpers ---


@pytest.fixture
def db(tmp_path):
    path = str(tmp_path / "code.db")
    init_db(path)
    return path


@pytest.fixture
def seeded_dtcs(db):
    """Seed a handful of DTCs across make + category combos."""
    add_dtc(DTCCode(
        code="P0115",
        description="Engine Coolant Temperature Sensor Circuit",
        category=SymptomCategory.ENGINE,
        dtc_category=DTCCategory.ENGINE,
        severity=Severity.MEDIUM,
        make=None,
        common_causes=[
            "ECT sensor open or shorted",
            "ECT sensor wiring fault",
            "Corroded ECT connector",
        ],
        fix_summary="Ohm-check sensor (warm ~200Ω, cold ~2kΩ); repair wiring or replace sensor.",
    ), db_path=db)

    add_dtc(DTCCode(
        code="P0115",
        description="Honda ECT circuit — known harness chafe near #3 header",
        category=SymptomCategory.ENGINE,
        dtc_category=DTCCategory.ENGINE,
        severity=Severity.MEDIUM,
        make="Honda",
        common_causes=[
            "Harness chafe against #3 header (common on VFR800)",
            "ECT connector water ingress",
        ],
        fix_summary="Inspect harness near #3 header; add split loom; replace connector if green.",
    ), db_path=db)

    add_dtc(DTCCode(
        code="P0A80",
        description="HV Battery Pack Deterioration",
        category=SymptomCategory.ELECTRICAL,
        dtc_category=DTCCategory.HV_BATTERY,
        severity=Severity.HIGH,
        make=None,
        common_causes=[
            "Cell imbalance exceeds BMS threshold",
            "One or more cells below minimum voltage",
        ],
        fix_summary="Read cell voltages via BMS; rebalance or replace affected modules.",
    ), db_path=db)

    add_dtc(DTCCode(
        code="HV_B001",
        description="High-voltage interlock loop open",
        category=SymptomCategory.ELECTRICAL,
        dtc_category=DTCCategory.HV_BATTERY,
        severity=Severity.CRITICAL,
        make="Zero",
        common_causes=[
            "HV service disconnect not seated",
            "Interlock pigtail pinched",
        ],
        fix_summary="Do NOT ride. Inspect interlock circuit; re-seat service disconnect.",
    ), db_path=db)

    return db


@pytest.fixture
def cli_db(db, monkeypatch):
    """CLI fixture — reset cached Settings after env var patch."""
    from motodiag.core.config import reset_settings
    monkeypatch.setenv("MOTODIAG_DB_PATH", db)
    reset_settings()
    yield db
    reset_settings()


def make_result(
    code="P0115",
    code_format="obd2_generic",
    possible_causes=None,
    tests_to_confirm=None,
    related_symptoms=None,
    repair_steps=None,
    estimated_hours=1.5,
    estimated_cost="$120-$250",
    safety_critical=False,
    notes=None,
    system="fuel_and_air_metering",
):
    """Minimal FaultCodeResult-like shim for rendering + CLI tests."""
    return SimpleNamespace(
        code=code,
        code_format=code_format,
        description=system,
        system=system,
        possible_causes=possible_causes if possible_causes is not None else [
            "ECT sensor open", "Harness chafe near #3 header",
        ],
        tests_to_confirm=tests_to_confirm if tests_to_confirm is not None else [
            "Ohm-check ECT sensor cold (~2kΩ) and warm (~200Ω)",
        ],
        related_symptoms=related_symptoms if related_symptoms is not None else [
            "Hard cold start", "Rich mixture until warm",
        ],
        repair_steps=repair_steps if repair_steps is not None else [
            "Confirm reading with OEM tool",
            "Replace ECT sensor",
            "Clear codes and verify",
        ],
        estimated_hours=estimated_hours,
        estimated_cost=estimated_cost,
        safety_critical=safety_critical,
        notes=notes,
    )


def make_usage(input_tokens=420, output_tokens=140, model="haiku"):
    return TokenUsage(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        model=model,
        cost_estimate=0.001,
        latency_ms=950,
    )


def make_interpret_fn(result=None, usage=None):
    """Build an interpret_fn mock compatible with _default_interpret_fn's signature."""
    if result is None:
        result = make_result()
    if usage is None:
        usage = make_usage()

    def _call(**kwargs):
        _call.last_kwargs = kwargs
        return result, usage
    _call.last_kwargs = {}
    return _call


def _buf_console() -> tuple[Console, io.StringIO]:
    buf = io.StringIO()
    return Console(file=buf, force_terminal=False, width=120), buf


# --- _lookup_local ---


class TestLookupLocal:
    def test_make_specific_hit(self, seeded_dtcs):
        row = _lookup_local("P0115", make="Honda", db_path=seeded_dtcs)
        assert row is not None
        # Honda-specific row has the #3 header note
        assert "header" in row["description"].lower()

    def test_generic_fallback_when_no_make_specific(self, seeded_dtcs):
        # Yamaha has no P0115 row; falls back to generic
        row = _lookup_local("P0115", make="Yamaha", db_path=seeded_dtcs)
        assert row is not None
        # Generic row description doesn't mention header
        assert "header" not in row["description"].lower()

    def test_generic_lookup_with_none_make(self, seeded_dtcs):
        row = _lookup_local("P0115", make=None, db_path=seeded_dtcs)
        assert row is not None
        assert row["code"] == "P0115"

    def test_total_miss_returns_none(self, seeded_dtcs):
        assert _lookup_local("P9999", make=None, db_path=seeded_dtcs) is None

    def test_miss_with_make_returns_none(self, seeded_dtcs):
        assert _lookup_local("P9999", make="Honda", db_path=seeded_dtcs) is None


# --- _classify_fallback ---


class TestClassifyFallback:
    def test_obd2_generic(self):
        row = _classify_fallback("P0115", make=None)
        assert row["code"] == "P0115"
        assert row["code_format"] == "obd2_generic"
        assert row["source"] == "classify_fallback"
        assert row["common_causes"] == []
        assert row["fix_summary"] is None

    def test_chassis_code(self):
        row = _classify_fallback("C1234", make=None)
        # C-codes classify as harley_dtc / chassis per classify_code
        assert row["code_format"] == "harley_dtc"
        assert "chassis" in row["description"].lower()

    def test_unknown_format_still_returns_dict(self):
        row = _classify_fallback("NOTACODE", make=None)
        assert row["source"] == "classify_fallback"
        # The classifier labels this "unknown"
        assert row["code_format"] == "unknown"
        assert row["code"] == "NOTACODE"

    def test_kawasaki_dealer_code(self):
        row = _classify_fallback("12", make="Kawasaki")
        assert row["code_format"] == "kawasaki_dealer"
        # Recognized ISC entry
        assert "ISC" in row["description"] or "Idle" in row["description"]


# --- Rendering ---


class TestRenderLocal:
    def test_renders_db_row(self, seeded_dtcs):
        from motodiag.knowledge.dtc_repo import get_dtc
        row = get_dtc("P0115", make=None, db_path=seeded_dtcs)
        console, buf = _buf_console()
        _render_local(row, console)
        out = buf.getvalue()
        assert "P0115" in out
        assert "Common causes" in out
        assert "ECT" in out or "Coolant" in out
        # Not a fallback → no yellow banner
        assert "No DB entry" not in out

    def test_renders_fallback_with_banner(self):
        row = _classify_fallback("P9999", make=None)
        console, buf = _buf_console()
        _render_local(row, console)
        out = buf.getvalue()
        assert "P9999" in out
        assert "No DB entry" in out
        # Suggests --explain
        assert "--explain" in out

    def test_renders_without_causes(self):
        row = {
            "code": "P0115",
            "description": "ECT",
            "category": "engine",
            "severity": "medium",
            "make": None,
            "common_causes": [],
            "fix_summary": None,
        }
        console, buf = _buf_console()
        _render_local(row, console)
        out = buf.getvalue()
        # Still renders the panel even with no causes
        assert "P0115" in out


class TestRenderExplain:
    def test_prints_all_sections(self):
        result = make_result()
        console, buf = _buf_console()
        _render_explain(result, console)
        out = buf.getvalue()
        assert "P0115" in out
        assert "Possible Causes" in out
        assert "ECT sensor" in out or "Harness chafe" in out
        assert "Tests to confirm" in out
        assert "Related symptoms" in out
        assert "Repair steps" in out
        assert "1.5" in out  # labor hours
        assert "$120" in out  # cost

    def test_safety_critical_banner(self):
        result = make_result(safety_critical=True)
        console, buf = _buf_console()
        _render_explain(result, console)
        out = buf.getvalue()
        assert "SAFETY-CRITICAL" in out

    def test_notes_section_renders(self):
        result = make_result(notes="Watch for intermittent repeat post-repair.")
        console, buf = _buf_console()
        _render_explain(result, console)
        out = buf.getvalue()
        assert "intermittent" in out


class TestRenderCategoryList:
    def test_empty(self):
        console, buf = _buf_console()
        _render_category_list([], console, "hv_battery")
        assert "No DTCs found" in buf.getvalue()

    def test_populated(self, seeded_dtcs):
        from motodiag.knowledge.dtc_repo import get_dtcs_by_category
        rows = get_dtcs_by_category(DTCCategory.HV_BATTERY, db_path=seeded_dtcs)
        console, buf = _buf_console()
        _render_category_list(rows, console, "hv_battery")
        out = buf.getvalue()
        assert "hv_battery" in out
        assert "P0A80" in out or "HV_B001" in out


# --- _run_explain ---


class TestRunExplain:
    def test_injects_interpret_fn(self, db):
        vid = add_vehicle(VehicleBase(
            make="Honda", model="VFR800", year=2002,
            engine_cc=782, protocol=ProtocolType.K_LINE,
        ), db_path=db)
        from motodiag.vehicles.registry import get_vehicle
        vehicle = get_vehicle(vid, db_path=db)

        fn = make_interpret_fn()
        result, usage = _run_explain(
            vehicle=vehicle,
            code="P0115",
            symptoms=["hard cold start"],
            ai_model="haiku",
            db_path=db,
            interpret_fn=fn,
        )
        assert result.code == "P0115"
        assert fn.last_kwargs["code"] == "P0115"
        assert fn.last_kwargs["ai_model"] == "haiku"
        assert fn.last_kwargs["symptoms"] == ["hard cold start"]
        # Known issues are loaded and passed (may be empty list)
        assert "known_issues" in fn.last_kwargs


# --- CLI ---


class TestCliCode:
    def _seed_vehicle(self, db_path):
        return add_vehicle(VehicleBase(
            make="Honda", model="VFR800", year=2002,
            engine_cc=782, protocol=ProtocolType.K_LINE,
        ), db_path=db_path)

    def _seed_generic_p0115(self, db_path):
        add_dtc(DTCCode(
            code="P0115",
            description="Engine Coolant Temperature Sensor Circuit",
            category=SymptomCategory.ENGINE,
            dtc_category=DTCCategory.ENGINE,
            severity=Severity.MEDIUM,
            make=None,
            common_causes=["ECT sensor open", "Harness fault"],
            fix_summary="Ohm-check sensor; replace if out of spec.",
        ), db_path=db_path)

    def _seed_honda_p0115(self, db_path):
        add_dtc(DTCCode(
            code="P0115",
            description="Honda ECT — #3 header harness chafe",
            category=SymptomCategory.ENGINE,
            dtc_category=DTCCategory.ENGINE,
            severity=Severity.MEDIUM,
            make="Honda",
            common_causes=["Harness chafe near #3 header"],
            fix_summary="Inspect harness; add split loom.",
        ), db_path=db_path)

    def _seed_hv_battery(self, db_path):
        add_dtc(DTCCode(
            code="P0A80",
            description="HV Battery Pack Deterioration",
            category=SymptomCategory.ELECTRICAL,
            dtc_category=DTCCategory.HV_BATTERY,
            severity=Severity.HIGH,
            make=None,
            common_causes=["Cell imbalance"],
            fix_summary="Rebalance or replace modules.",
        ), db_path=db_path)

    def test_happy_path_local_lookup(self, cli_db):
        self._seed_generic_p0115(cli_db)
        from motodiag.cli.main import cli
        runner = CliRunner()
        r = runner.invoke(cli, ["code", "P0115"])
        assert r.exit_code == 0, r.output
        assert "P0115" in r.output
        assert "ECT" in r.output or "Coolant" in r.output
        # No fallback banner when DB row exists
        assert "No DB entry" not in r.output

    def test_unknown_code_falls_back_to_classify(self, cli_db):
        from motodiag.cli.main import cli
        runner = CliRunner()
        r = runner.invoke(cli, ["code", "P9999"])
        assert r.exit_code == 0, r.output
        assert "P9999" in r.output
        assert "No DB entry" in r.output

    def test_make_filter_narrows_to_specific(self, cli_db):
        self._seed_generic_p0115(cli_db)
        self._seed_honda_p0115(cli_db)
        from motodiag.cli.main import cli
        runner = CliRunner()
        r = runner.invoke(cli, ["code", "P0115", "--make", "Honda"])
        assert r.exit_code == 0, r.output
        assert "#3 header" in r.output or "harness chafe" in r.output.lower()

    def test_make_filter_falls_back_to_generic(self, cli_db):
        self._seed_generic_p0115(cli_db)
        from motodiag.cli.main import cli
        runner = CliRunner()
        r = runner.invoke(cli, ["code", "P0115", "--make", "Yamaha"])
        assert r.exit_code == 0, r.output
        assert "P0115" in r.output
        # Generic row, not make-specific
        assert "#3 header" not in r.output

    def test_category_list_mode(self, cli_db):
        self._seed_hv_battery(cli_db)
        from motodiag.cli.main import cli
        runner = CliRunner()
        r = runner.invoke(cli, ["code", "--category", "hv_battery"])
        assert r.exit_code == 0, r.output
        assert "hv_battery" in r.output
        assert "P0A80" in r.output

    def test_category_list_empty(self, cli_db):
        from motodiag.cli.main import cli
        runner = CliRunner()
        r = runner.invoke(cli, ["code", "--category", "hv_battery"])
        assert r.exit_code == 0, r.output
        assert "No DTCs found" in r.output

    def test_explain_happy_path(self, cli_db):
        vid = self._seed_vehicle(cli_db)
        from motodiag.cli.main import cli

        fn = make_interpret_fn()
        with patch("motodiag.cli.code._default_interpret_fn", fn):
            runner = CliRunner()
            r = runner.invoke(cli, [
                "code", "P0115", "--explain",
                "--vehicle-id", str(vid),
                "--symptoms", "hard cold start, runs rich",
            ])
        assert r.exit_code == 0, r.output
        assert "P0115" in r.output
        assert "Possible Causes" in r.output
        assert "Repair steps" in r.output

    def test_explain_missing_vehicle_id(self, cli_db):
        from motodiag.cli.main import cli
        runner = CliRunner()
        r = runner.invoke(cli, ["code", "P0115", "--explain"])
        assert r.exit_code != 0
        assert "--vehicle-id" in r.output

    def test_explain_missing_code_argument(self, cli_db):
        vid = self._seed_vehicle(cli_db)
        from motodiag.cli.main import cli
        runner = CliRunner()
        r = runner.invoke(cli, [
            "code", "--explain", "--vehicle-id", str(vid),
        ])
        assert r.exit_code != 0
        assert "dtc code argument is required" in r.output.lower() \
            or "required" in r.output.lower()

    def test_explain_missing_vehicle_record(self, cli_db):
        from motodiag.cli.main import cli
        runner = CliRunner()
        r = runner.invoke(cli, [
            "code", "P0115", "--explain", "--vehicle-id", "99999",
        ])
        assert r.exit_code != 0
        assert "not found" in r.output.lower()

    def test_explain_sonnet_on_individual_hard_mode_errors(
        self, cli_db, monkeypatch,
    ):
        monkeypatch.setenv("MOTODIAG_PAYWALL_MODE", "hard")
        monkeypatch.setenv("MOTODIAG_SUBSCRIPTION_TIER", "individual")
        vid = self._seed_vehicle(cli_db)
        from motodiag.cli.main import cli
        runner = CliRunner()
        r = runner.invoke(cli, [
            "code", "P0115", "--explain",
            "--vehicle-id", str(vid),
            "--model", "sonnet",
        ])
        assert r.exit_code != 0
        assert "shop tier" in r.output.lower() or "individual" in r.output.lower()

    def test_explain_sonnet_on_shop_succeeds(self, cli_db, monkeypatch):
        monkeypatch.setenv("MOTODIAG_PAYWALL_MODE", "hard")
        monkeypatch.setenv("MOTODIAG_SUBSCRIPTION_TIER", "shop")
        vid = self._seed_vehicle(cli_db)
        from motodiag.cli.main import cli
        fn = make_interpret_fn(result=make_result(), usage=make_usage(model="sonnet"))
        with patch("motodiag.cli.code._default_interpret_fn", fn):
            runner = CliRunner()
            r = runner.invoke(cli, [
                "code", "P0115", "--explain",
                "--vehicle-id", str(vid),
                "--model", "sonnet",
            ])
        assert r.exit_code == 0, r.output
        assert fn.last_kwargs["ai_model"] == "sonnet"

    def test_default_no_code_no_category_errors(self, cli_db):
        from motodiag.cli.main import cli
        runner = CliRunner()
        r = runner.invoke(cli, ["code"])
        assert r.exit_code != 0


# --- Registration ---


class TestRegistration:
    def test_code_command_registered(self):
        from motodiag.cli.main import cli
        assert "code" in cli.commands
        # Should not be a group — should be a plain command
        assert not isinstance(cli.commands["code"], click.Group)

    def test_existing_cli_commands_still_present(self):
        from motodiag.cli.main import cli
        expected = ("info", "tier", "garage", "intake", "diagnose", "code", "search")
        for name in expected:
            assert name in cli.commands, f"Missing command: {name}"
