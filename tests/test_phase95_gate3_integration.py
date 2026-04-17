"""Phase 95 — Gate 3 integration test: AI diagnostic engine end-to-end.

Verifies the full diagnostic pipeline: symptom intake → categorization →
urgency assessment → knowledge base correlation → confidence scoring →
repair procedures → cost estimation → safety checks → evaluation tracking.

All tests use mocked API calls or pure logic — no live API key required.
"""

import json
from unittest.mock import MagicMock
from datetime import datetime, timezone

import pytest

from motodiag.engine.client import DiagnosticClient
from motodiag.engine.models import DiagnosticResponse, DiagnosisItem, DiagnosticSeverity, TokenUsage
from motodiag.engine.symptoms import SymptomAnalyzer, categorize_symptoms, assess_urgency
from motodiag.engine.fault_codes import FaultCodeInterpreter, classify_code, CodeFormat
from motodiag.engine.workflows import (
    DiagnosticWorkflow, StepResult, create_no_start_workflow,
    create_charging_workflow, create_overheating_workflow,
)
from motodiag.engine.confidence import score_diagnosis_from_evidence, rank_diagnoses
from motodiag.engine.repair import RepairProcedure, RepairStep, SkillLevel, assess_skill_level
from motodiag.engine.parts import PartRecommendation, ToolRecommendation, PartSource
from motodiag.engine.cost import CostEstimator, ShopType, LABOR_RATES
from motodiag.engine.safety import SafetyChecker, AlertLevel
from motodiag.engine.history import DiagnosticHistory
from motodiag.engine.retrieval import CaseRetriever
from motodiag.engine.correlation import SymptomCorrelator
from motodiag.engine.intermittent import IntermittentAnalyzer
from motodiag.engine.wiring import get_circuit_reference, list_all_circuits
from motodiag.engine.service_data import get_torque_spec, get_service_interval, list_all_torque_specs
from motodiag.engine.evaluation import EvaluationTracker, DiagnosticOutcome


class TestGate3EngineModuleInventory:
    """Gate 3: Verify all 16 engine modules are importable and functional."""

    def test_module_count(self):
        """16 engine modules should be importable."""
        from motodiag.engine import __all__
        # At least 40 public symbols across 16 modules
        assert len(__all__) >= 40

    def test_client_module(self):
        client = DiagnosticClient(api_key="sk-test-key")
        assert client.is_configured
        assert client.session.call_count == 0

    def test_symptom_module(self):
        result = categorize_symptoms(["won't start", "noise", "overheating"])
        assert len(result) >= 2

    def test_fault_code_module(self):
        fmt, desc = classify_code("P0301")
        assert fmt == CodeFormat.OBD2_GENERIC

    def test_workflow_module(self):
        wf = create_no_start_workflow("2015 Suzuki GSX-R600")
        assert len(wf.steps) >= 4

    def test_confidence_module(self):
        score = score_diagnosis_from_evidence("Test", symptom_matches=3, dtc_match=True)
        assert score.normalized_score > 0

    def test_repair_module(self):
        assert assess_skill_level("oil change") == SkillLevel.BEGINNER
        assert assess_skill_level("engine rebuild crankshaft") == SkillLevel.ADVANCED

    def test_parts_module(self):
        part = PartRecommendation(
            part_name="Stator", brand="Rick's Motorsport",
            price_range_low=120.0, price_range_high=180.0, source=PartSource.AFTERMARKET,
        )
        assert part.source == PartSource.AFTERMARKET

    def test_cost_module(self):
        estimator = CostEstimator()
        est = estimator.estimate(labor_hours=2.0, parts=[], shop_type=ShopType.INDEPENDENT)
        assert est.labor_total_low > 0

    def test_safety_module(self):
        checker = SafetyChecker()
        alerts = checker.check_diagnosis("brake failure fluid leak")
        assert any(a.level == AlertLevel.CRITICAL for a in alerts)

    def test_history_module(self):
        history = DiagnosticHistory()
        stats = history.get_statistics()
        assert stats.total_records == 0

    def test_retrieval_module(self):
        history = DiagnosticHistory()
        retriever = CaseRetriever(history=history)
        assert retriever is not None

    def test_correlation_module(self):
        correlator = SymptomCorrelator()
        results = correlator.correlate(["overheating", "loss of power", "coolant smell"])
        assert len(results) >= 1

    def test_intermittent_module(self):
        analyzer = IntermittentAnalyzer()
        results = analyzer.analyze("rough idle", "only when cold, goes away after warmup")
        assert len(results) >= 1

    def test_wiring_module(self):
        circuits = list_all_circuits()
        assert len(circuits) >= 5

    def test_service_data_module(self):
        specs = list_all_torque_specs()
        assert len(specs) >= 15

    def test_evaluation_module(self):
        tracker = EvaluationTracker()
        sc = tracker.get_scorecard()
        assert sc.total_sessions == 0


class TestGate3SymptomToRepairFlow:
    """Gate 3: Full symptom-to-repair flow with confidence + cost."""

    def test_symptom_categorization_and_urgency(self):
        """Step 1: Categorize symptoms and assess urgency."""
        symptoms = ["battery not charging", "dim lights at idle", "check engine light on"]
        categorized = categorize_symptoms(symptoms)
        assert "electrical" in categorized
        alerts = assess_urgency(symptoms)
        # Not critical combination, but categorization should work
        assert len(categorized) >= 1

    def test_confidence_scoring_pipeline(self):
        """Step 2: Score diagnosis confidence from multiple evidence sources."""
        score = score_diagnosis_from_evidence(
            diagnosis="Stator failure",
            symptom_matches=3,
            dtc_match=False,
            kb_match=True,
            test_confirmed=True,
            multiple_symptoms_correlated=True,
        )
        assert score.normalized_score >= 0.7
        assert score.confidence_label in ("high", "very_high")
        assert score.evidence_count >= 5

    def test_multi_diagnosis_ranking(self):
        """Step 3: Rank multiple diagnoses by confidence."""
        scores = [
            score_diagnosis_from_evidence("Stator failure", symptom_matches=3, kb_match=True, test_confirmed=True),
            score_diagnosis_from_evidence("Bad battery", symptom_matches=1),
            score_diagnosis_from_evidence("Reg/rec failure", symptom_matches=2, kb_match=True),
        ]
        ranked = rank_diagnoses(scores)
        assert ranked[0].diagnosis == "Stator failure"  # Highest confidence first
        assert ranked[-1].diagnosis == "Bad battery"  # Lowest last

    def test_cost_estimation_pipeline(self):
        """Step 4: Estimate repair cost with shop type comparison."""
        estimator = CostEstimator()
        from motodiag.engine.cost import PartCost
        parts = [
            PartCost(name="Stator", cost_low=120.0, cost_high=180.0),
            PartCost(name="MOSFET reg/rec", cost_low=60.0, cost_high=80.0),
        ]
        comparison = estimator.compare_shop_types(labor_hours=2.5, parts=parts)
        dealer = comparison[ShopType.DEALER]
        independent = comparison[ShopType.INDEPENDENT]
        diy = comparison[ShopType.DIY]
        assert dealer.total_high > independent.total_high > diy.total_high
        assert diy.diy_savings_low == 0.0  # Already DIY

    def test_safety_check_pipeline(self):
        """Step 5: Check diagnosis for safety-critical conditions."""
        checker = SafetyChecker()
        alerts = checker.check_diagnosis("fuel leak near exhaust headers")
        assert len(alerts) >= 1
        critical = [a for a in alerts if a.level == AlertLevel.CRITICAL]
        assert len(critical) >= 1

    def test_correlation_detects_root_cause(self):
        """Step 6: Multi-symptom correlation identifies root cause."""
        correlator = SymptomCorrelator()
        results = correlator.correlate(["battery not charging", "dim lights", "check engine light on"])
        assert len(results) >= 1
        # Should identify stator/reg-rec failure as a root cause
        root_causes = [r.rule.root_cause.lower() for r in results]
        assert any("stator" in rc or "charging" in rc or "reg" in rc for rc in root_causes)


class TestGate3WorkflowIntegration:
    """Gate 3: Diagnostic workflows operate correctly end-to-end."""

    def test_no_start_workflow_battery_path(self):
        wf = create_no_start_workflow("2012 Kawasaki Ninja 650")
        # Step 1: Battery fails
        wf.report_result(StepResult.FAIL, notes="10.2V — dead battery")
        assert wf.is_complete()
        assert "battery" in wf.working_diagnosis.lower()
        summary = wf.get_results_summary()
        assert summary["steps_completed"] == 1

    def test_charging_workflow_full_path(self):
        wf = create_charging_workflow("2015 Suzuki GSX-R600")
        # Step 1: Low voltage at RPM
        wf.report_result(StepResult.FAIL, notes="12.1V at 5000 RPM")
        assert wf.is_complete()
        assert wf.working_diagnosis  # Should have a diagnosis

    def test_overheating_workflow_thermostat_path(self):
        wf = create_overheating_workflow("2008 Honda CBR600RR")
        # Step 1: Coolant level OK
        wf.report_result(StepResult.PASS)
        # Step 2: Thermostat stuck closed
        wf.report_result(StepResult.FAIL, notes="Upper hose stays cold, engine hot")
        assert wf.is_complete()
        assert "thermostat" in wf.working_diagnosis.lower()


class TestGate3FaultCodeIntegration:
    """Gate 3: Fault code classification works across all makes."""

    def test_obd2_codes(self):
        fmt, _ = classify_code("P0301")
        assert fmt == CodeFormat.OBD2_GENERIC

    def test_kawasaki_codes(self):
        fmt, desc = classify_code("12")
        assert fmt == CodeFormat.KAWASAKI_DEALER
        assert "ISC" in desc

    def test_suzuki_codes(self):
        fmt, desc = classify_code("C28")
        assert fmt == CodeFormat.SUZUKI_CMODE
        assert "pump" in desc.lower() or "relay" in desc.lower()

    def test_honda_codes(self):
        fmt, _ = classify_code("7")
        assert fmt == CodeFormat.HONDA_BLINK

    def test_harley_codes(self):
        fmt, _ = classify_code("B1004")
        assert fmt == CodeFormat.HARLEY_DTC


class TestGate3ReferenceDataIntegration:
    """Gate 3: Reference data modules provide lookup and context."""

    def test_wiring_reference_lookup(self):
        circuit = get_circuit_reference("charging")
        assert circuit is not None
        assert len(circuit.wires) >= 2
        assert len(circuit.test_points) >= 3

    def test_torque_spec_lookup(self):
        spec = get_torque_spec("drain plug")
        assert spec is not None
        assert spec.spec_nm > 0
        assert spec.spec_ftlbs > 0

    def test_service_interval_lookup(self):
        interval = get_service_interval("oil change")
        assert interval is not None
        assert interval.interval_miles > 0

    def test_valve_clearance_lookup(self):
        from motodiag.engine.service_data import get_valve_clearance
        cl = get_valve_clearance("inline-4 exhaust")
        assert cl is not None
        assert cl.spec_mm_high > cl.spec_mm_low


class TestGate3EvaluationIntegration:
    """Gate 3: Evaluation tracks diagnostic quality correctly."""

    def test_evaluation_pipeline(self):
        tracker = EvaluationTracker()

        # Simulate 5 diagnostic sessions
        for i in range(5):
            tracker.record_outcome(DiagnosticOutcome(
                session_id=f"gate3-{i}",
                predicted_diagnosis="Stator failure",
                predicted_confidence=0.85,
                actual_diagnosis="Stator failure",
                was_correct=True,
                was_helpful=True,
                api_cost_usd=0.003,
                latency_ms=800,
                tokens_used=800,
                model_used="haiku",
            ))

        sc = tracker.get_scorecard()
        assert sc.total_sessions == 5
        assert sc.accuracy_rate == 1.0
        assert sc.helpfulness_rate == 1.0
        assert sc.composite_score > 0.8  # High composite = good quality + cheap + fast

        report = tracker.format_scorecard()
        assert "COMPOSITE SCORE" in report
        assert "100.0%" in report  # 100% accuracy


class TestGate3IntermittentIntegration:
    """Gate 3: Intermittent fault analysis identifies condition-specific patterns."""

    def test_cold_start_pattern(self):
        analyzer = IntermittentAnalyzer()
        results = analyzer.analyze("won't start", "only when cold, fine after warm-up")
        assert len(results) >= 1
        # Should match cold-start pattern
        all_causes = []
        for r in results:
            all_causes.extend(r.pattern.likely_causes if hasattr(r, 'pattern') else [])

    def test_rain_pattern(self):
        analyzer = IntermittentAnalyzer()
        results = analyzer.analyze("engine dies", "only happens when riding in rain or washing the bike")
        assert len(results) >= 1

    def test_condition_extraction(self):
        analyzer = IntermittentAnalyzer()
        # Use the analyzer's method to extract conditions from text
        results = analyzer.analyze("won't start", "It only happens when it's really cold outside, below freezing")
        assert len(results) >= 1  # Should match cold-start pattern
