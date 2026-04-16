"""AI diagnostic engine — Claude API integration, prompt engineering, reasoning.

Phase 79+: Wraps the Anthropic SDK with motorcycle-specific configuration.
"""

from motodiag.engine.client import DiagnosticClient
from motodiag.engine.models import (
    DiagnosticResponse,
    DiagnosisItem,
    DiagnosticSeverity,
    TokenUsage,
    SessionMetrics,
)
from motodiag.engine.prompts import (
    DIAGNOSTIC_SYSTEM_PROMPT,
    build_vehicle_context,
    build_symptom_context,
    build_knowledge_context,
    build_full_prompt,
)

__all__ = [
    "DiagnosticClient",
    "DiagnosticResponse",
    "DiagnosisItem",
    "DiagnosticSeverity",
    "TokenUsage",
    "SessionMetrics",
    "DIAGNOSTIC_SYSTEM_PROMPT",
    "build_vehicle_context",
    "build_symptom_context",
    "build_knowledge_context",
    "build_full_prompt",
]
