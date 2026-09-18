"""Phase 244T — a hazard is told to the person holding the wrench.

`engine/safety.py` has had 19 rules and no caller since Phase 241, which
recorded that as its own open finding. `media/analysis_worker.py:223` names
`SafetyChecker` as this codebase's canonical example of built-and-never-wired,
and the 209B reachability gate could not see it because `engine/__init__`
re-exports the name — the blind spot 244U exists to close.

Two decisions are pinned here because both could be quietly reversed:

* **the threshold.** Measured across 970 corpus entries, 30% fire some alert
  and 9.9% fire a critical one. The operator chose CRITICAL + WARNING on
  2026-09-17; rendering caution too would put a notice on a third of jobs.
* **where "electric" comes from.** The garage record, never the make. Step 0's
  first design inferred it, and failed in both directions on one manufacturer:
  the corpus route calls Harley-Davidson electric, a hardcoded list misses
  LiveWire.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from motodiag.core.database import init_db
from motodiag.core.models import ProtocolType, VehicleBase
from motodiag.engine.safety import SAFETY_RULES, SafetyChecker
from motodiag.vehicles.registry import add_vehicle


def _response(text: str, *, summary: str = "2001 Honda CBR600F4i"):
    """A DiagnosticResponse-shaped stand-in, as the other CLI suites build."""
    return SimpleNamespace(
        vehicle_summary=summary,
        symptoms_acknowledged=[],
        diagnoses=[SimpleNamespace(
            diagnosis=text, confidence=0.8, severity="high",
            evidence=["seen on inspection"], rationale=text,
            repair_steps=["inspect"],
        )],
        additional_tests=[],
        notes="",
    )


def _diagnose_fn(text: str):
    def _call(**kwargs):
        return _response(text), SimpleNamespace(
            input_tokens=10, output_tokens=10, model="haiku", cost_estimate=0.0,
        )
    return _call


@pytest.fixture
def garage(tmp_path, monkeypatch):
    from motodiag.core.config import reset_settings

    db = str(tmp_path / "phase244T.db")
    init_db(db)
    monkeypatch.setenv("MOTODIAG_DB_PATH", db)
    reset_settings()
    yield db
    reset_settings()


def _bike(db, *, powertrain="ice", make="Honda", model="CBR600F4i") -> int:
    kwargs = dict(make=make, model=model, year=2001, engine_cc=599,
                  protocol=ProtocolType.NONE)
    if powertrain is not None:
        kwargs["powertrain"] = powertrain
    return add_vehicle(VehicleBase(**kwargs), db_path=db)


def _run_diagnosis(vehicle_id: int, diagnosis_text: str, symptoms: str = "runs badly"):
    from motodiag.cli.main import cli

    with patch("motodiag.cli.diagnose._default_diagnose_fn", _diagnose_fn(diagnosis_text)):
        return CliRunner().invoke(cli, [
            "diagnose", "quick", "--vehicle-id", str(vehicle_id),
            "--symptoms", symptoms,
        ])


# ---------------------------------------------------------------------------
# 1. The wiring itself
# ---------------------------------------------------------------------------


class TestTheHazardReachesTheTechnician:
    def test_a_critical_diagnosis_shows_its_alert(self, garage):
        result = _run_diagnosis(
            _bike(garage), "Brake failure — no lever pressure at the front master cylinder",
        )
        assert result.exit_code == 0, result.output
        assert "Brake system failure" in result.output
        assert "SAFETY" in result.output.upper()

    def test_a_warning_diagnosis_shows_its_alert(self, garage):
        """Asserted on the rule's own ACTION text, not its title: the title
        also appears in the ranked-diagnoses table, so asserting on it passed
        even with warnings suppressed — the mutation run caught that."""
        result = _run_diagnosis(
            _bike(garage), "Head gasket failure, coolant in the oil",
        )
        assert "SAFETY" in result.output.upper()
        assert "Risk of engine seizure" in result.output

    def test_the_symptoms_the_technician_typed_are_checked_too(self, garage):
        """A leak described at intake and not repeated by the model is still
        a leak."""
        result = _run_diagnosis(
            _bike(garage),
            "Charging system output is low at idle",
            symptoms="fuel odor is strong inside the fairing",
        )
        assert "fuel" in result.output.lower()

    def test_the_diagnosis_still_renders(self, garage):
        result = _run_diagnosis(_bike(garage), "Brake failure — no lever pressure")
        assert "Ranked Diagnoses" in result.output


class TestTheThreshold:
    def test_a_caution_grade_finding_stays_quiet(self, garage):
        """'Oil leak' is caution. It fires on 185 corpus entries; showing it
        is how the panel stops being read."""
        result = _run_diagnosis(garage_bike := _bike(garage), "Oil leak at the stator cover gasket")
        assert garage_bike
        assert "SAFETY" not in result.output.upper()

    def test_an_info_grade_finding_stays_quiet(self, garage):
        result = _run_diagnosis(_bike(garage), "Spark plug service needed at this mileage")
        assert "SAFETY" not in result.output.upper()

    def test_a_clean_diagnosis_shows_no_panel(self, garage):
        result = _run_diagnosis(_bike(garage), "Loose side stand switch connector")
        assert "SAFETY" not in result.output.upper()


# ---------------------------------------------------------------------------
# 2. Which bike it is
# ---------------------------------------------------------------------------


class TestPowertrainScoping:
    def test_an_engine_rule_does_not_fire_on_an_electric_bike(self, garage):
        vid = _bike(garage, powertrain="electric", make="Zero", model="SR/F")
        result = _run_diagnosis(vid, "Strong fuel odor around the tank")
        assert "SAFETY" not in result.output.upper(), (
            "an electric motorcycle has no fuel tank"
        )

    def test_a_universal_rule_still_fires_on_an_electric_bike(self, garage):
        vid = _bike(garage, powertrain="electric", make="Zero", model="SR/F")
        result = _run_diagnosis(vid, "Brake failure — no lever pressure")
        assert "Brake system failure" in result.output

    def test_an_unknown_powertrain_shows_everything(self):
        """Failing toward showing. The field can hold a photo model's guess,
        so a blank or wrong value must not hide a fuel-leak warning."""
        unknown = SafetyChecker(powertrain=None)
        assert len(unknown._compiled_rules) == len(SAFETY_RULES)
        assert unknown.check_diagnosis("fuel leak at the petcock")

    def test_the_checker_cannot_be_told_a_make_at_all(self):
        """Step 0's rejected design, pinned by signature rather than by
        grepping the source — my first version of this guard tripped on the
        docstring that explains why the make is not used, which is the
        mention-vs-use trap this repo keeps naming."""
        import inspect

        params = set(inspect.signature(SafetyChecker.__init__).parameters)
        assert params == {"self", "powertrain"}, (
            f"the checker must take only a powertrain, got {sorted(params)}"
        )

    def test_a_harley_keeps_its_fuel_rules(self):
        """The inference that Step 0 rejected would have called this make
        electric and suppressed exactly this alert."""
        assert SafetyChecker(powertrain="ice").check_diagnosis(
            "fuel leaking at the petcock"
        )


class TestTheFalsePositivesWiringFound:
    """Four phases with no caller meant nothing ever pressed these patterns
    against real diagnosis text. Two substring matches printed a CRITICAL
    "do not start the engine" on ordinary findings."""

    @pytest.mark.parametrize("text", [
        "Valve cover gasket weeping; no other leak found",
        "Head gasket replaced; no leak now",
        "Oil leak traced to the clutch cover gasket",
    ])
    def test_a_gasket_is_not_a_fuel_leak(self, text):
        """`gas(oline)?` matched the "gas" inside "gasket"."""
        titles = [a.title for a in SafetyChecker().check_diagnosis(text)]
        assert "Fuel leak detected" not in titles

    def test_a_coil_is_not_an_oil_leak(self):
        """`oil` matched the "oil" inside "coil"."""
        titles = [
            a.title for a in SafetyChecker().check_diagnosis(
                "Ignition coil is leaking at the plug tube"
            )
        ]
        assert "Oil leak detected" not in titles

    @pytest.mark.parametrize("text,expected", [
        ("Fuel leaking from the petcock onto the header", "Fuel leak detected"),
        ("Oil leak at the stator cover", "Oil leak detected"),
        ("fuel odor is strong inside the cockpit", "Strong fuel odor — leak likely"),
        ("front tire is flat", "Tire condition — replacement needed"),
        ("air filter is clogged and restricting flow", "Air filter maintenance needed"),
    ])
    def test_the_real_thing_still_fires(self, text, expected):
        """The word boundaries must not silence the rule they guard — the
        first attempt did exactly that, because `"\\b"` in a plain Python
        string is a backspace, not a word boundary."""
        titles = [a.title for a in SafetyChecker().check_diagnosis(text)]
        assert expected in titles

    def test_a_critical_false_alarm_would_reach_the_technician(self, garage):
        """Why this mattered enough to fix inside the wiring phase: the
        threshold shows CRITICAL, so a gasket weep would have printed
        "do not start the engine"."""
        result = _run_diagnosis(
            _bike(garage), "Valve cover gasket weeping; no other leak found",
        )
        assert "FUEL LEAK" not in result.output.upper()


# ---------------------------------------------------------------------------
# 3. It cannot break the diagnosis
# ---------------------------------------------------------------------------


class TestSafetyNeverBreaksTheDiagnosis:
    def test_a_failing_checker_leaves_the_diagnosis_intact(self, garage):
        with patch(
            "motodiag.engine.safety.SafetyChecker",
            side_effect=RuntimeError("regex engine exploded"),
        ):
            result = _run_diagnosis(_bike(garage), "Brake failure — no lever pressure")
        assert result.exit_code == 0, result.output
        assert "Ranked Diagnoses" in result.output

    def test_an_empty_response_is_not_an_error(self, garage):
        result = _run_diagnosis(_bike(garage), "")
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# 4. What this phase does not claim
# ---------------------------------------------------------------------------


class TestWhatIsStillUnwired:
    def test_there_are_no_high_voltage_rules_yet(self):
        """Scoping can only suppress here. An electric bike gets FEWER alerts,
        not the ones it needs — recorded rather than invented, and filed."""
        text = " ".join(str(r).lower() for r in SAFETY_RULES)
        assert "high-voltage" not in text and "hv " not in text

    def test_check_repair_procedure_is_still_unwired(self):
        """Named so the next phase finds it, rather than rediscovering it."""
        from pathlib import Path

        src = Path("src/motodiag")
        callers = [
            f"{p}:{i}"
            for p in src.rglob("*.py")
            for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1)
            if "check_repair_procedure(" in line and "def " not in line
        ]
        assert callers == [], f"now wired — update this test and the docs: {callers}"
