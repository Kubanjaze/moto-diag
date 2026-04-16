"""Tests for Phase 87 — Safety Warnings + Critical Alerts.

25+ tests covering AlertLevel enum, SafetyAlert model, SafetyChecker methods
(check_diagnosis, check_symptoms, check_repair_procedure), format_alerts,
and SAFETY_RULES coverage. All pure logic — no API calls.
"""

import pytest

from motodiag.engine.safety import (
    AlertLevel,
    SafetyAlert,
    SafetyChecker,
    SAFETY_RULES,
    REPAIR_SAFETY_KEYWORDS,
    format_alerts,
)


# ---------------------------------------------------------------------------
# AlertLevel enum tests
# ---------------------------------------------------------------------------

class TestAlertLevel:
    """Tests for the AlertLevel enum."""

    def test_critical_value(self):
        assert AlertLevel.CRITICAL == "critical"

    def test_warning_value(self):
        assert AlertLevel.WARNING == "warning"

    def test_caution_value(self):
        assert AlertLevel.CAUTION == "caution"

    def test_info_value(self):
        assert AlertLevel.INFO == "info"

    def test_all_levels_present(self):
        levels = {e.value for e in AlertLevel}
        assert levels == {"critical", "warning", "caution", "info"}


# ---------------------------------------------------------------------------
# SafetyAlert model tests
# ---------------------------------------------------------------------------

class TestSafetyAlert:
    """Tests for SafetyAlert Pydantic model."""

    def test_create_full_alert(self):
        alert = SafetyAlert(
            level=AlertLevel.CRITICAL,
            title="Test alert",
            message="This is a test",
            affected_system="brakes",
            immediate_action="Stop now",
            do_not="Do NOT ride",
        )
        assert alert.level == AlertLevel.CRITICAL
        assert alert.title == "Test alert"
        assert alert.message == "This is a test"
        assert alert.affected_system == "brakes"
        assert alert.immediate_action == "Stop now"
        assert alert.do_not == "Do NOT ride"

    def test_create_alert_without_do_not(self):
        alert = SafetyAlert(
            level=AlertLevel.INFO,
            title="Info alert",
            message="Minor note",
            affected_system="engine",
            immediate_action="Schedule service",
        )
        assert alert.do_not is None

    def test_alert_level_is_enum(self):
        alert = SafetyAlert(
            level=AlertLevel.WARNING,
            title="Warning",
            message="Be careful",
            affected_system="electrical",
            immediate_action="Check wiring",
        )
        assert isinstance(alert.level, AlertLevel)


# ---------------------------------------------------------------------------
# SafetyChecker — check_diagnosis() tests
# ---------------------------------------------------------------------------

class TestCheckDiagnosis:
    """Tests for SafetyChecker.check_diagnosis()."""

    @pytest.fixture
    def checker(self):
        return SafetyChecker()

    def test_brake_failure_is_critical(self, checker):
        alerts = checker.check_diagnosis("The front brake has complete loss of pressure")
        assert len(alerts) >= 1
        critical = [a for a in alerts if a.level == AlertLevel.CRITICAL]
        assert len(critical) >= 1
        assert any("brake" in a.title.lower() for a in critical)

    def test_brake_leak_is_critical(self, checker):
        alerts = checker.check_diagnosis("Rear brake fluid leak from caliper seal")
        critical = [a for a in alerts if a.level == AlertLevel.CRITICAL]
        assert len(critical) >= 1

    def test_fuel_leak_is_critical(self, checker):
        alerts = checker.check_diagnosis("Fuel leak at the petcock fitting, dripping onto engine")
        critical = [a for a in alerts if a.level == AlertLevel.CRITICAL]
        assert len(critical) >= 1
        assert any("fuel" in a.title.lower() for a in critical)

    def test_stator_connector_melting_is_critical(self, checker):
        alerts = checker.check_diagnosis("Stator connector melting — wires charred at the plug")
        critical = [a for a in alerts if a.level == AlertLevel.CRITICAL]
        assert len(critical) >= 1
        assert any("stator" in a.title.lower() for a in critical)

    def test_head_gasket_is_warning(self, checker):
        alerts = checker.check_diagnosis("Head gasket blown, coolant mixing with oil")
        warnings = [a for a in alerts if a.level == AlertLevel.WARNING]
        assert len(warnings) >= 1

    def test_overheating_steam_is_warning(self, checker):
        alerts = checker.check_diagnosis("Engine overheating with steam coming from radiator overflow")
        warnings = [a for a in alerts if a.level == AlertLevel.WARNING]
        assert len(warnings) >= 1

    def test_electrical_short_is_warning(self, checker):
        alerts = checker.check_diagnosis("Electrical short in the wiring harness causing smoke")
        warnings = [a for a in alerts if a.level == AlertLevel.WARNING]
        assert len(warnings) >= 1

    def test_chain_worn_is_caution(self, checker):
        alerts = checker.check_diagnosis("Drive chain is worn and stretched beyond adjustment limit")
        cautions = [a for a in alerts if a.level == AlertLevel.CAUTION]
        assert len(cautions) >= 1

    def test_tire_worn_is_caution(self, checker):
        alerts = checker.check_diagnosis("Rear tire is bald — no tread remaining")
        cautions = [a for a in alerts if a.level == AlertLevel.CAUTION]
        assert len(cautions) >= 1

    def test_oil_leak_is_caution(self, checker):
        alerts = checker.check_diagnosis("Oil leak from the primary cover gasket")
        cautions = [a for a in alerts if a.level == AlertLevel.CAUTION]
        assert len(cautions) >= 1

    def test_valve_clearance_is_info(self, checker):
        alerts = checker.check_diagnosis("Valve clearance is tight on the exhaust side")
        infos = [a for a in alerts if a.level == AlertLevel.INFO]
        assert len(infos) >= 1

    def test_unrelated_diagnosis_no_alert(self, checker):
        alerts = checker.check_diagnosis("Paint is faded on the tank")
        assert len(alerts) == 0

    def test_case_insensitive(self, checker):
        alerts = checker.check_diagnosis("BRAKE FAILURE detected")
        assert len(alerts) >= 1

    def test_no_duplicate_alerts(self, checker):
        alerts = checker.check_diagnosis("Brake failure and brake leak and brake loss")
        titles = [a.title for a in alerts]
        assert len(titles) == len(set(titles)), "Should not produce duplicate alerts"


# ---------------------------------------------------------------------------
# SafetyChecker — check_symptoms() tests
# ---------------------------------------------------------------------------

class TestCheckSymptoms:
    """Tests for SafetyChecker.check_symptoms()."""

    @pytest.fixture
    def checker(self):
        return SafetyChecker()

    def test_overheating_steam_symptoms(self, checker):
        alerts = checker.check_symptoms(["engine overheating", "steam from radiator"])
        warnings = [a for a in alerts if a.level == AlertLevel.WARNING]
        assert len(warnings) >= 1

    def test_fuel_smell_symptom(self, checker):
        alerts = checker.check_symptoms(["strong fuel smell inside cockpit area"])
        critical = [a for a in alerts if a.level == AlertLevel.CRITICAL]
        assert len(critical) >= 1

    def test_normal_symptom_no_alert(self, checker):
        alerts = checker.check_symptoms(["rough idle at cold start", "slightly louder exhaust note"])
        # These shouldn't trigger critical/warning
        critical_or_warning = [a for a in alerts if a.level in (AlertLevel.CRITICAL, AlertLevel.WARNING)]
        assert len(critical_or_warning) == 0

    def test_empty_symptoms(self, checker):
        alerts = checker.check_symptoms([])
        assert len(alerts) == 0


# ---------------------------------------------------------------------------
# SafetyChecker — check_repair_procedure() tests
# ---------------------------------------------------------------------------

class TestCheckRepairProcedure:
    """Tests for SafetyChecker.check_repair_procedure()."""

    @pytest.fixture
    def checker(self):
        return SafetyChecker()

    def test_drain_fuel_fire_caution(self, checker):
        alerts = checker.check_repair_procedure(["Drain fuel from the tank into a container"])
        assert len(alerts) >= 1
        assert any("fire" in a.title.lower() or "fuel" in a.title.lower() for a in alerts)

    def test_brake_fluid_paint_caution(self, checker):
        alerts = checker.check_repair_procedure(["Remove brake fluid reservoir cap and top off"])
        assert len(alerts) >= 1
        assert any("brake" in a.title.lower() or "paint" in a.title.lower() for a in alerts)

    def test_jack_crush_hazard(self, checker):
        alerts = checker.check_repair_procedure(["Jack up the motorcycle and secure on paddock stand"])
        assert len(alerts) >= 1
        assert any("crush" in a.title.lower() or "jack" in a.title.lower() or "support" in a.title.lower()
                    for a in alerts)

    def test_lift_warning(self, checker):
        alerts = checker.check_repair_procedure(["Lift the motorcycle onto the work bench"])
        assert len(alerts) >= 1

    def test_normal_step_no_alert(self, checker):
        alerts = checker.check_repair_procedure(["Remove the seat", "Disconnect the air filter housing"])
        # "air filter" is not in REPAIR_SAFETY_KEYWORDS
        assert len(alerts) == 0

    def test_multiple_hazards_in_procedure(self, checker):
        steps = [
            "Drain fuel from the tank",
            "Remove fuel tank from frame",
            "Disconnect battery cables",
            "Replace brake caliper seals",
        ]
        alerts = checker.check_repair_procedure(steps)
        # Should get alerts for: drain fuel, remove fuel tank, battery, brake caliper
        assert len(alerts) >= 3


# ---------------------------------------------------------------------------
# format_alerts() tests
# ---------------------------------------------------------------------------

class TestFormatAlerts:
    """Tests for the format_alerts() standalone function."""

    def test_empty_list_returns_empty_string(self):
        result = format_alerts([])
        assert result == ""

    def test_critical_appears_first(self):
        alerts = [
            SafetyAlert(
                level=AlertLevel.INFO,
                title="Info alert",
                message="Minor",
                affected_system="engine",
                immediate_action="Schedule service",
            ),
            SafetyAlert(
                level=AlertLevel.CRITICAL,
                title="Critical alert",
                message="Dangerous",
                affected_system="brakes",
                immediate_action="Stop now",
                do_not="Do NOT ride",
            ),
        ]
        result = format_alerts(alerts)
        crit_pos = result.find("CRITICAL")
        info_pos = result.find("INFO")
        assert crit_pos < info_pos, "CRITICAL should appear before INFO"

    def test_correct_ordering_all_levels(self):
        alerts = [
            SafetyAlert(level=AlertLevel.INFO, title="Info", message="m",
                        affected_system="s", immediate_action="a"),
            SafetyAlert(level=AlertLevel.CAUTION, title="Caution", message="m",
                        affected_system="s", immediate_action="a"),
            SafetyAlert(level=AlertLevel.CRITICAL, title="Critical", message="m",
                        affected_system="s", immediate_action="a", do_not="dn"),
            SafetyAlert(level=AlertLevel.WARNING, title="Warning", message="m",
                        affected_system="s", immediate_action="a"),
        ]
        result = format_alerts(alerts)
        crit_pos = result.find("Critical")
        warn_pos = result.find("Warning")
        caut_pos = result.find("Caution")
        info_pos = result.find("Info")
        assert crit_pos < warn_pos < caut_pos < info_pos

    def test_do_not_field_included(self):
        alerts = [
            SafetyAlert(
                level=AlertLevel.CRITICAL,
                title="Test",
                message="msg",
                affected_system="sys",
                immediate_action="act",
                do_not="Do NOT do this",
            ),
        ]
        result = format_alerts(alerts)
        assert "DO NOT" in result
        assert "Do NOT do this" in result

    def test_header_present(self):
        alerts = [
            SafetyAlert(level=AlertLevel.INFO, title="T", message="m",
                        affected_system="s", immediate_action="a"),
        ]
        result = format_alerts(alerts)
        assert "SAFETY ALERTS" in result


# ---------------------------------------------------------------------------
# SAFETY_RULES coverage test
# ---------------------------------------------------------------------------

class TestRulesCoverage:
    """Tests for rule set completeness."""

    def test_at_least_10_safety_rules(self):
        assert len(SAFETY_RULES) >= 10, f"Expected >= 10 rules, got {len(SAFETY_RULES)}"

    def test_at_least_10_repair_keywords(self):
        assert len(REPAIR_SAFETY_KEYWORDS) >= 10, f"Expected >= 10 keywords, got {len(REPAIR_SAFETY_KEYWORDS)}"

    def test_all_levels_represented_in_rules(self):
        levels_in_rules = {rule["level"] for rule in SAFETY_RULES}
        assert AlertLevel.CRITICAL in levels_in_rules
        assert AlertLevel.WARNING in levels_in_rules
        assert AlertLevel.CAUTION in levels_in_rules
        assert AlertLevel.INFO in levels_in_rules

    def test_every_rule_has_required_fields(self):
        required = {"patterns", "level", "title", "message", "affected_system", "immediate_action"}
        for i, rule in enumerate(SAFETY_RULES):
            for field in required:
                assert field in rule, f"Rule {i} missing field '{field}'"

    def test_every_repair_keyword_has_required_fields(self):
        required = {"level", "title", "message", "affected_system", "immediate_action"}
        for keyword, rule in REPAIR_SAFETY_KEYWORDS.items():
            for field in required:
                assert field in rule, f"Repair keyword '{keyword}' missing field '{field}'"
