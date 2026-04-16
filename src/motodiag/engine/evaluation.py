"""AI evaluation + accuracy tracking — score diagnostic quality, cost, and latency.

Phase 94: Tracks diagnostic accuracy against known outcomes, monitors API cost
per diagnosis, and produces quality scorecards using the ADR-005 evaluation
framework: Quality (40%) + Cost (40%) + Latency (20%).
"""

from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field


class DiagnosticOutcome(BaseModel):
    """Records the actual outcome of a diagnostic session for accuracy tracking."""
    session_id: str = Field(..., description="ID of the diagnostic session")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    predicted_diagnosis: str = Field(..., description="What the AI diagnosed")
    predicted_confidence: float = Field(..., ge=0.0, le=1.0, description="AI's confidence in the prediction")
    actual_diagnosis: str = Field(default="", description="What the actual problem turned out to be")
    was_correct: Optional[bool] = Field(None, description="Whether the AI prediction was correct")
    was_helpful: Optional[bool] = Field(None, description="Whether the AI output was useful to the mechanic")
    api_cost_usd: float = Field(default=0.0, description="Total API cost for this session")
    latency_ms: int = Field(default=0, description="Total latency for the session (all API calls)")
    tokens_used: int = Field(default=0, description="Total tokens consumed")
    model_used: str = Field(default="", description="Which AI model was used")
    notes: Optional[str] = Field(None, description="Mechanic feedback or resolution notes")


class QualityScorecard(BaseModel):
    """Evaluation scorecard following ADR-005: Quality (40%) + Cost (40%) + Latency (20%).

    Each component is scored 0.0-1.0, then weighted to produce a composite score.
    """
    # Quality component (40% weight)
    accuracy_rate: float = Field(default=0.0, ge=0.0, le=1.0, description="Correct diagnoses / total with known outcomes")
    helpfulness_rate: float = Field(default=0.0, ge=0.0, le=1.0, description="Helpful outputs / total with feedback")
    confidence_calibration: float = Field(default=0.0, ge=0.0, le=1.0, description="How well confidence predicts accuracy")
    quality_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Combined quality metric")

    # Cost component (40% weight)
    avg_cost_per_diagnosis: float = Field(default=0.0, description="Average USD per diagnostic session")
    cost_efficiency: float = Field(default=0.0, ge=0.0, le=1.0, description="1.0 = free, 0.0 = $1+ per diagnosis")
    cost_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Combined cost metric")

    # Latency component (20% weight)
    avg_latency_ms: float = Field(default=0.0, description="Average milliseconds per session")
    p95_latency_ms: float = Field(default=0.0, description="95th percentile latency")
    latency_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Combined latency metric")

    # Composite
    composite_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Weighted composite: Q*0.4 + C*0.4 + L*0.2")
    total_sessions: int = Field(default=0, description="Total diagnostic sessions evaluated")
    sessions_with_outcome: int = Field(default=0, description="Sessions where actual outcome is known")


class EvaluationTracker:
    """Tracks diagnostic outcomes and produces quality scorecards.

    Collects outcomes over time and calculates accuracy, cost efficiency,
    and latency metrics using the ADR-005 framework.
    """

    def __init__(self):
        self.outcomes: list[DiagnosticOutcome] = []

    def record_outcome(self, outcome: DiagnosticOutcome) -> None:
        """Record a diagnostic outcome for tracking."""
        self.outcomes.append(outcome)

    def get_scorecard(self) -> QualityScorecard:
        """Calculate and return the current quality scorecard."""
        if not self.outcomes:
            return QualityScorecard()

        total = len(self.outcomes)
        with_outcome = [o for o in self.outcomes if o.was_correct is not None]
        with_feedback = [o for o in self.outcomes if o.was_helpful is not None]

        # Quality metrics
        accuracy_rate = 0.0
        if with_outcome:
            correct = sum(1 for o in with_outcome if o.was_correct)
            accuracy_rate = correct / len(with_outcome)

        helpfulness_rate = 0.0
        if with_feedback:
            helpful = sum(1 for o in with_feedback if o.was_helpful)
            helpfulness_rate = helpful / len(with_feedback)

        # Confidence calibration: how close is avg confidence to accuracy rate?
        # Perfect calibration means predicted confidence matches actual accuracy
        confidence_calibration = 0.0
        if with_outcome:
            avg_confidence = sum(o.predicted_confidence for o in with_outcome) / len(with_outcome)
            calibration_error = abs(avg_confidence - accuracy_rate)
            confidence_calibration = max(0.0, 1.0 - calibration_error * 2)  # 0.5 error = 0.0 score

        quality_score = (accuracy_rate * 0.5 + helpfulness_rate * 0.3 + confidence_calibration * 0.2)

        # Cost metrics
        costs = [o.api_cost_usd for o in self.outcomes if o.api_cost_usd > 0]
        avg_cost = sum(costs) / len(costs) if costs else 0.0
        # Cost efficiency: $0 = 1.0, $0.01 = 0.9, $0.05 = 0.5, $0.10 = 0.0
        cost_efficiency = max(0.0, min(1.0, 1.0 - avg_cost * 10))
        cost_score = cost_efficiency

        # Latency metrics
        latencies = [o.latency_ms for o in self.outcomes if o.latency_ms > 0]
        avg_latency = sum(latencies) / len(latencies) if latencies else 0.0
        sorted_latencies = sorted(latencies) if latencies else [0]
        p95_index = int(len(sorted_latencies) * 0.95)
        p95_latency = sorted_latencies[min(p95_index, len(sorted_latencies) - 1)]
        # Latency score: <1s = 1.0, 1-3s = 0.7, 3-5s = 0.4, >5s = 0.1
        if avg_latency <= 1000:
            latency_score = 1.0
        elif avg_latency <= 3000:
            latency_score = 0.7
        elif avg_latency <= 5000:
            latency_score = 0.4
        else:
            latency_score = 0.1

        # Composite: Quality (40%) + Cost (40%) + Latency (20%)
        composite = quality_score * 0.4 + cost_score * 0.4 + latency_score * 0.2

        return QualityScorecard(
            accuracy_rate=round(accuracy_rate, 3),
            helpfulness_rate=round(helpfulness_rate, 3),
            confidence_calibration=round(confidence_calibration, 3),
            quality_score=round(quality_score, 3),
            avg_cost_per_diagnosis=round(avg_cost, 4),
            cost_efficiency=round(cost_efficiency, 3),
            cost_score=round(cost_score, 3),
            avg_latency_ms=round(avg_latency, 1),
            p95_latency_ms=round(p95_latency, 1),
            latency_score=round(latency_score, 3),
            composite_score=round(composite, 3),
            total_sessions=total,
            sessions_with_outcome=len(with_outcome),
        )

    def get_accuracy_by_model(self) -> dict[str, float]:
        """Get accuracy rate broken down by AI model used."""
        model_outcomes: dict[str, list[bool]] = {}
        for o in self.outcomes:
            if o.was_correct is not None and o.model_used:
                model_outcomes.setdefault(o.model_used, []).append(o.was_correct)
        return {
            model: sum(results) / len(results)
            for model, results in model_outcomes.items()
        }

    def get_cost_by_model(self) -> dict[str, float]:
        """Get average cost per diagnosis broken down by AI model."""
        model_costs: dict[str, list[float]] = {}
        for o in self.outcomes:
            if o.api_cost_usd > 0 and o.model_used:
                model_costs.setdefault(o.model_used, []).append(o.api_cost_usd)
        return {
            model: sum(costs) / len(costs)
            for model, costs in model_costs.items()
        }

    def format_scorecard(self, scorecard: Optional[QualityScorecard] = None) -> str:
        """Format the scorecard as a human-readable report."""
        sc = scorecard or self.get_scorecard()
        lines = [
            "═══════════════════════════════════════",
            "  MotoDiag AI Diagnostic Quality Report",
            "═══════════════════════════════════════",
            "",
            f"  Sessions evaluated: {sc.total_sessions}",
            f"  Sessions with known outcome: {sc.sessions_with_outcome}",
            "",
            "  QUALITY (40% weight)",
            f"    Accuracy rate:    {sc.accuracy_rate:.1%}",
            f"    Helpfulness rate: {sc.helpfulness_rate:.1%}",
            f"    Calibration:      {sc.confidence_calibration:.1%}",
            f"    Quality score:    {sc.quality_score:.3f}",
            "",
            "  COST (40% weight)",
            f"    Avg cost/diagnosis: ${sc.avg_cost_per_diagnosis:.4f}",
            f"    Cost efficiency:    {sc.cost_efficiency:.1%}",
            f"    Cost score:         {sc.cost_score:.3f}",
            "",
            "  LATENCY (20% weight)",
            f"    Avg latency:  {sc.avg_latency_ms:.0f}ms",
            f"    P95 latency:  {sc.p95_latency_ms:.0f}ms",
            f"    Latency score: {sc.latency_score:.3f}",
            "",
            "  ─────────────────────────────────────",
            f"  COMPOSITE SCORE: {sc.composite_score:.3f}",
            "  ─────────────────────────────────────",
        ]
        return "\n".join(lines)
