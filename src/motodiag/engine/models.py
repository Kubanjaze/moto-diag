"""Diagnostic engine response models — structured outputs from AI reasoning."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class DiagnosticSeverity(str, Enum):
    """Severity level of a diagnosis."""
    CRITICAL = "critical"  # Safety issue — stop riding immediately
    HIGH = "high"          # Major failure — repair before riding
    MEDIUM = "medium"      # Reduced performance — schedule repair
    LOW = "low"            # Minor issue — monitor and address at convenience


class DiagnosisItem(BaseModel):
    """A single diagnostic finding with confidence and evidence."""
    diagnosis: str = Field(..., description="What is wrong — specific root cause")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence 0.0-1.0")
    severity: DiagnosticSeverity = Field(..., description="How urgent is this")
    evidence: list[str] = Field(default_factory=list, description="What supports this diagnosis")
    repair_steps: list[str] = Field(default_factory=list, description="How to fix it")
    estimated_hours: Optional[float] = Field(None, description="Estimated labor hours")
    estimated_cost: Optional[str] = Field(None, description="Estimated parts + labor cost range")
    parts_needed: list[str] = Field(default_factory=list, description="Parts required for repair")
    safety_warning: Optional[str] = Field(None, description="Safety concern if applicable")


class DiagnosticResponse(BaseModel):
    """Full diagnostic response from the AI engine."""
    vehicle_summary: str = Field(..., description="Brief vehicle identification")
    symptoms_acknowledged: list[str] = Field(default_factory=list, description="Symptoms the AI understood")
    diagnoses: list[DiagnosisItem] = Field(default_factory=list, description="Ranked diagnoses")
    additional_tests: list[str] = Field(default_factory=list, description="Tests to narrow diagnosis")
    notes: Optional[str] = Field(None, description="General observations or caveats")


class TokenUsage(BaseModel):
    """Token usage for a single API call."""
    input_tokens: int = 0
    output_tokens: int = 0
    model: str = ""
    cost_estimate: float = 0.0  # USD
    latency_ms: Optional[int] = None


class SessionMetrics(BaseModel):
    """Cumulative metrics for a diagnostic session."""
    session_id: str = ""
    started_at: Optional[datetime] = None
    call_count: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cost: float = 0.0
    models_used: list[str] = Field(default_factory=list)
    avg_latency_ms: Optional[float] = None

    def add_usage(self, usage: TokenUsage) -> None:
        """Accumulate a single call's usage into session totals."""
        self.call_count += 1
        self.total_input_tokens += usage.input_tokens
        self.total_output_tokens += usage.output_tokens
        self.total_cost += usage.cost_estimate
        if usage.model and usage.model not in self.models_used:
            self.models_used.append(usage.model)
        if usage.latency_ms is not None:
            if self.avg_latency_ms is None:
                self.avg_latency_ms = float(usage.latency_ms)
            else:
                # Running average
                self.avg_latency_ms = (
                    (self.avg_latency_ms * (self.call_count - 1) + usage.latency_ms)
                    / self.call_count
                )

    @property
    def total_tokens(self) -> int:
        return self.total_input_tokens + self.total_output_tokens
