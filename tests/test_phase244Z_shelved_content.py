"""Phase 244Z — what the shelved modules would say if anyone wired them.

Six engine modules stayed on the shelf after 244Y. The 2026-09-17 audit named
four things in them that would put a wrong number or a wrong diagnosis in
front of a technician the day any one is wired; every one is content, not
wiring, and every one is pinned here so it cannot come back with a refactor.

None of this reaches a user today — all six are on MODULE_ISLANDS — and this
file asserts that too. Fix-before-wiring, said plainly.
"""

from __future__ import annotations

import importlib
import re
from pathlib import Path

import pytest
from support.integration_gaps_allowlist import MODULE_ISLANDS
from support.source_guards import code_of

SRC = Path(__file__).resolve().parent.parent / "src" / "motodiag" / "engine"
SHELVED = ["repair", "parts", "workflows", "intermittent", "correlation", "confidence"]


# ---------------------------------------------------------------------------
# 1. repair.py — no invented torque figures
# ---------------------------------------------------------------------------


class TestTheRepairPromptDoesNotInventTorque:
    def test_no_numeric_torque_example(self):
        """The audit's single highest risk: `"Torque drain plug to 14-16 ft-lbs"`
        as an exemplar, in a module with no provenance anywhere. A per-call
        hallucinated torque leaves no literal to grep and no fixture to fix."""
        from motodiag.engine.repair import REPAIR_PROMPT

        assert not re.search(r"\d+\s*-\s*\d+\s*ft-?lbs?", REPAIR_PROMPT)
        assert not re.search(r"\d+(\.\d+)?\s*Nm", REPAIR_PROMPT)

    def test_it_refers_to_the_manual(self):
        from motodiag.engine.repair import REPAIR_PROMPT

        assert "service manual" in REPAIR_PROMPT
        assert "Never estimate a torque" in REPAIR_PROMPT

    def test_it_says_why(self):
        """The same sentence `ref torque` leads with, because the failure is
        symmetric and both directions are expensive."""
        from motodiag.engine.repair import REPAIR_PROMPT

        assert "brake failure" in REPAIR_PROMPT
        assert "aluminium case" in REPAIR_PROMPT


# ---------------------------------------------------------------------------
# 2. correlation.py — no coolant jacket on an air-cooled twin
# ---------------------------------------------------------------------------

_LIQUID = ("coolant", "radiator", "thermostat", "water pump", "cooling fan")
_AIR = (
    "twin cam", "evolution", "sportster", "shovelhead", "panhead", "air-cooled",
    "dr-z", "klr", "sr400",
)


def _liquid_on_air(rule) -> bool:
    text = " ".join([*sorted(rule.symptom_set), rule.explanation, rule.root_cause]).lower()
    liquid = any(w in text for w in _LIQUID)
    air = (any(a in v.lower() for v in rule.common_vehicles for a in _AIR)
           or "air-cooled" in rule.explanation.lower())
    return liquid and air


class TestNoRuleDiagnosesCoolantOnAnAirCooledEngine:
    def test_corr_001_is_gone(self):
        """It said "compression leak into coolant jacket" and "Common on
        air-cooled twins" in the same sentence, at severity critical. Deleted
        rather than rewritten: making it true would mean authoring Harley
        head-gasket symptoms, which is content this project does not invent."""
        from motodiag.engine.correlation import CORRELATION_RULES

        assert "CORR-001" not in {r.rule_id for r in CORRELATION_RULES}

    def test_every_rule_passes_the_scan(self):
        """The mechanical check from Step 0, kept as a test so the next
        authored rule that puts coolant on an air-cooled twin fails here."""
        from motodiag.engine.correlation import CORRELATION_RULES

        bad = [r.rule_id for r in CORRELATION_RULES if _liquid_on_air(r)]
        assert bad == [], bad

    def test_the_scan_would_have_caught_the_original(self):
        """A guard that cannot fail is a comment. Reconstructed CORR-001."""
        from motodiag.engine.correlation import CorrelationRule

        original = CorrelationRule(
            rule_id="CORR-001", symptom_set={"overheating", "loss of power", "coolant smell"},
            root_cause="Head gasket failure", confidence=0.85,
            explanation="compression leak into coolant jacket. Common on air-cooled twins.",
            system_category="cooling", severity="critical",
            common_vehicles=["Harley-Davidson Twin Cam"],
        )
        assert _liquid_on_air(original)

    def test_the_docstring_example_names_a_rule_that_exists(self):
        from motodiag.engine import correlation
        from motodiag.engine.correlation import CORRELATION_RULES

        ids = {r.rule_id for r in CORRELATION_RULES}
        for m in re.findall(r"CORR-\d{3}", correlation.__doc__ or ""):
            assert m in ids, m


# ---------------------------------------------------------------------------
# 3. intermittent.py — one charging reference, not two
# ---------------------------------------------------------------------------


class TestIntermittentDefersToTheShippedChargingReference:
    def test_the_two_stale_floors_are_gone(self):
        """The thresholds lived in code strings, not prose, so blanked code
        is where their absence is checked."""
        code = code_of(SRC / "intermittent.py")
        assert "should be >13V" not in code
        assert "13.5-14.5V at 3000RPM" not in code

    def test_no_charging_voltage_literal_disagrees_with_wiring(self):
        """Computed from both modules, not hardcoded: every voltage literal on
        a line of intermittent.py that talks about charging must appear in the
        charging circuit reference that `ref circuit charging` prints."""
        from motodiag.engine.wiring import get_circuit_reference

        charging = get_circuit_reference("charging")
        assert charging is not None
        shipped = " ".join([
            charging.description, *charging.test_points, *charging.common_failures,
            *charging.diagnostic_tips, *[w.expected_voltage or "" for w in charging.wires],
        ])
        src = (SRC / "intermittent.py").read_text(encoding="utf-8")
        offenders = []
        for i, line in enumerate(src.splitlines(), 1):
            if "charg" not in line.lower():
                continue
            for lit in re.findall(r"\d+(?:\.\d+)?V\b", line):
                if lit not in shipped:
                    offenders.append(f"{i}: {lit}")
        assert offenders == [], offenders

    def test_it_points_at_the_command(self):
        src = (SRC / "intermittent.py").read_text(encoding="utf-8")
        assert src.count("motodiag ref circuit charging") >= 2


# ---------------------------------------------------------------------------
# 4. parts.py — no equivalence claims
# ---------------------------------------------------------------------------


class TestPartsDoesNotSolicitEquivalences:
    def test_the_word_is_gone_from_the_module(self):
        """An invented part number fails safe — the counter says no such
        number. An invented equivalence fails unsafe — both resolve, the
        wrong part ships, and it installs."""
        src = (SRC / "parts.py").read_text(encoding="utf-8")
        assert not re.search(r"equivalen", src, re.I)

    def test_the_field_says_verify(self):
        from motodiag.engine.parts import PartRecommendation

        desc = PartRecommendation.model_fields["cross_references"].description
        assert "verify" in desc and "never presented as interchangeable" in desc


# ---------------------------------------------------------------------------
# 5. Still shelved, still importable
# ---------------------------------------------------------------------------


class TestStillShelved:
    @pytest.mark.parametrize("name", SHELVED)
    def test_the_module_imports(self, name):
        importlib.import_module(f"motodiag.engine.{name}")

    @pytest.mark.parametrize("name", SHELVED)
    def test_the_module_is_still_on_the_islands_table(self, name):
        """Nothing here made anything reachable. The wire-or-delete decision
        is the operator's, and it is cleaner now."""
        assert f"motodiag.engine.{name}" in MODULE_ISLANDS

    def test_the_table_did_not_move(self):
        assert len(MODULE_ISLANDS) == 14  # f9-noqa: ssot-pin fixture-data: unchanged by Phase 244Z, on purpose — content fixed, reachability untouched.
