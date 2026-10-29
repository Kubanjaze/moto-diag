"""AI diagnostic engine — Claude API integration, prompt engineering, reasoning.

Phase 79-94: 16 modules covering the full diagnostic pipeline from symptom intake
through AI analysis, repair procedures, cost estimation, safety checks, evaluation,
and reference data.
"""

from motodiag.engine.client import DiagnosticClient
from motodiag.engine.confidence import (
    ConfidenceScore,
    rank_diagnoses,
    score_diagnosis_from_evidence,
)
from motodiag.engine.correlation import SymptomCorrelator
from motodiag.engine.fault_codes import FaultCodeInterpreter, FaultCodeResult
from motodiag.engine.intermittent import IntermittentAnalyzer
from motodiag.engine.models import (
    DiagnosisItem,
    DiagnosticResponse,
    DiagnosticSeverity,
    SessionMetrics,
    TokenUsage,
)
from motodiag.engine.parts import (
    PartRecommendation,
    PartSource,
    PartsRecommender,
    ToolRecommendation,
)
from motodiag.engine.prompts import (
    DIAGNOSTIC_SYSTEM_PROMPT,
    build_full_prompt,
    build_knowledge_context,
    build_symptom_context,
    build_vehicle_context,
)
from motodiag.engine.repair import RepairProcedure, RepairProcedureGenerator, RepairStep, SkillLevel
from motodiag.engine.safety import AlertLevel, SafetyAlert, SafetyChecker, format_alerts
from motodiag.engine.service_data import (
    build_service_data_context,
    get_service_interval,
    get_torque_spec,
    get_valve_clearance,
)
from motodiag.engine.wiring import (
    build_wiring_context,
    get_circuit_reference,
    get_circuits_by_system,
)
from motodiag.engine.workflows import DiagnosticWorkflow, StepResult, WorkflowStep

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
