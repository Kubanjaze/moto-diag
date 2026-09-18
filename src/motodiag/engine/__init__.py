"""AI diagnostic engine — Claude API integration, prompt engineering, reasoning.

Phase 79-94: 16 modules covering the full diagnostic pipeline from symptom intake
through AI analysis, repair procedures, cost estimation, safety checks, evaluation,
and reference data.
"""

from motodiag.engine.client import DiagnosticClient
from motodiag.engine.models import (
    DiagnosticResponse, DiagnosisItem, DiagnosticSeverity, TokenUsage, SessionMetrics,
)
from motodiag.engine.prompts import (
    DIAGNOSTIC_SYSTEM_PROMPT, build_vehicle_context, build_symptom_context,
    build_knowledge_context, build_full_prompt,
)
from motodiag.engine.fault_codes import FaultCodeInterpreter, FaultCodeResult
from motodiag.engine.workflows import DiagnosticWorkflow, WorkflowStep, StepResult
from motodiag.engine.confidence import ConfidenceScore, score_diagnosis_from_evidence, rank_diagnoses
from motodiag.engine.repair import RepairProcedureGenerator, RepairProcedure, RepairStep, SkillLevel
from motodiag.engine.parts import PartsRecommender, PartRecommendation, ToolRecommendation, PartSource
from motodiag.engine.safety import SafetyChecker, SafetyAlert, AlertLevel, format_alerts
from motodiag.engine.correlation import SymptomCorrelator
from motodiag.engine.intermittent import IntermittentAnalyzer
from motodiag.engine.wiring import get_circuit_reference, get_circuits_by_system, build_wiring_context
from motodiag.engine.service_data import get_torque_spec, get_service_interval, get_valve_clearance, build_service_data_context

__all__ = [
    # Phase 79 — Client + models + prompts
    "DiagnosticClient", "DiagnosticResponse", "DiagnosisItem", "DiagnosticSeverity",
    "TokenUsage", "SessionMetrics", "DIAGNOSTIC_SYSTEM_PROMPT",
    "build_vehicle_context", "build_symptom_context", "build_knowledge_context", "build_full_prompt",
    # Phase 80 — Symptoms
    # Phase 81 — Fault codes
    "FaultCodeInterpreter", "FaultCodeResult",
    # Phase 82 — Workflows
    "DiagnosticWorkflow", "WorkflowStep", "StepResult",
    # Phase 83 — Confidence
    "ConfidenceScore", "score_diagnosis_from_evidence", "rank_diagnoses",
    # Phase 84 — Repair
    "RepairProcedureGenerator", "RepairProcedure", "RepairStep", "SkillLevel",
    # Phase 85 — Parts
    "PartsRecommender", "PartRecommendation", "ToolRecommendation", "PartSource",
    # Phase 86 — Cost
    # Phase 87 — Safety
    "SafetyChecker", "SafetyAlert", "AlertLevel", "format_alerts",
    # Phase 88 — History
    # Phase 89 — Retrieval
    # Phase 90 — Correlation
    "SymptomCorrelator",
    # Phase 91 — Intermittent
    "IntermittentAnalyzer",
    # Phase 92 — Wiring
    "get_circuit_reference", "get_circuits_by_system", "build_wiring_context",
    # Phase 93 — Service data
    "get_torque_spec", "get_service_interval", "get_valve_clearance", "build_service_data_context",
    # Phase 94 — Evaluation
    ]
