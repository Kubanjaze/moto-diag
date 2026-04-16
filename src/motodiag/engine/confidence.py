"""Confidence scoring system — evidence-weighted probability estimation for diagnoses.

Produces calibrated confidence scores by weighting evidence from multiple sources:
symptom matches, DTC codes, knowledge base matches, test results, vehicle history,
and environmental factors. Scores are 0.0-1.0 with explicit uncertainty handling.
"""

from typing import Optional

from pydantic import BaseModel, Field


class EvidenceWeight:
    """Standard weights for different evidence types."""
    DTC_CODE_MATCH = 0.25       # A DTC code directly matches a known cause
    SYMPTOM_MATCH = 0.15        # A reported symptom matches a known issue pattern
    KB_ISSUE_MATCH = 0.20       # Knowledge base has a matching known issue for this vehicle
    TEST_RESULT_CONFIRM = 0.30  # A diagnostic test confirmed the suspected cause
    TEST_RESULT_DENY = -0.25    # A diagnostic test ruled out the suspected cause
    VEHICLE_HISTORY = 0.10      # Vehicle history suggests this is a repeat or known pattern
    ENVIRONMENTAL = 0.05        # Environmental factors (season, climate, altitude) support the diagnosis
    MULTIPLE_SYMPTOM = 0.10     # Multiple symptoms pointing to same root cause (correlation bonus)


class EvidenceItem(BaseModel):
    """A single piece of evidence supporting or opposing a diagnosis."""
    source: str = Field(..., description="Where this evidence comes from (symptom, dtc, kb, test, history, environmental)")
    description: str = Field(..., description="What the evidence is")
    weight: float = Field(..., description="How much this evidence contributes to confidence (-1.0 to 1.0)")
    supports_diagnosis: bool = Field(default=True, description="True = supports, False = contradicts")


class ConfidenceScore(BaseModel):
    """Structured confidence score for a single diagnosis."""
    diagnosis: str = Field(..., description="The diagnosis being scored")
    raw_score: float = Field(default=0.0, description="Raw accumulated evidence score before normalization")
    normalized_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Final confidence 0.0-1.0")
    evidence_items: list[EvidenceItem] = Field(default_factory=list, description="All evidence contributing to this score")
    evidence_count: int = Field(default=0, description="Total evidence items considered")
    supporting_count: int = Field(default=0, description="Evidence items that support this diagnosis")
    contradicting_count: int = Field(default=0, description="Evidence items that contradict this diagnosis")
    confidence_label: str = Field(default="unknown", description="Human-readable label: very_high, high, moderate, low, very_low")

    def add_evidence(self, item: EvidenceItem) -> None:
        """Add an evidence item and recalculate the score."""
        self.evidence_items.append(item)
        self.evidence_count += 1
        if item.supports_diagnosis:
            self.supporting_count += 1
            self.raw_score += item.weight
        else:
            self.contradicting_count += 1
            self.raw_score -= abs(item.weight)
        self._recalculate()

    def _recalculate(self) -> None:
        """Recalculate normalized score and label from raw score."""
        # Normalize: sigmoid-like mapping of raw score to 0.0-1.0
        # Raw score range is roughly -1.0 to +1.5 based on evidence weights
        if self.raw_score <= -0.5:
            self.normalized_score = 0.05  # Very unlikely but not impossible
        elif self.raw_score <= 0.0:
            self.normalized_score = 0.1 + (self.raw_score + 0.5) * 0.2  # 0.1-0.2
        elif self.raw_score <= 0.3:
            self.normalized_score = 0.2 + self.raw_score * 1.0  # 0.2-0.5
        elif self.raw_score <= 0.6:
            self.normalized_score = 0.5 + (self.raw_score - 0.3) * 1.0  # 0.5-0.8
        elif self.raw_score <= 1.0:
            self.normalized_score = 0.8 + (self.raw_score - 0.6) * 0.375  # 0.8-0.95
        else:
            self.normalized_score = min(0.95, 0.8 + self.raw_score * 0.1)

        # Ensure bounds
        self.normalized_score = max(0.0, min(1.0, round(self.normalized_score, 2)))

        # Assign label
        if self.normalized_score >= 0.85:
            self.confidence_label = "very_high"
        elif self.normalized_score >= 0.65:
            self.confidence_label = "high"
        elif self.normalized_score >= 0.40:
            self.confidence_label = "moderate"
        elif self.normalized_score >= 0.20:
            self.confidence_label = "low"
        else:
            self.confidence_label = "very_low"


def score_diagnosis_from_evidence(
    diagnosis: str,
    symptom_matches: int = 0,
    dtc_match: bool = False,
    kb_match: bool = False,
    test_confirmed: bool = False,
    test_denied: bool = False,
    vehicle_history_match: bool = False,
    multiple_symptoms_correlated: bool = False,
    environmental_factor: bool = False,
) -> ConfidenceScore:
    """Score a diagnosis based on available evidence.

    This is the convenience function for building a confidence score from
    discrete evidence flags. For fine-grained control, use ConfidenceScore
    directly with add_evidence().

    Args:
        diagnosis: The diagnosis to score.
        symptom_matches: Number of symptoms matching this diagnosis.
        dtc_match: Whether a DTC code matches this diagnosis.
        kb_match: Whether the knowledge base has a matching known issue.
        test_confirmed: Whether a diagnostic test confirmed this diagnosis.
        test_denied: Whether a diagnostic test ruled this out.
        vehicle_history_match: Whether vehicle history supports this diagnosis.
        multiple_symptoms_correlated: Whether multiple symptoms point to same root cause.
        environmental_factor: Whether environmental conditions support the diagnosis.

    Returns:
        ConfidenceScore with all evidence and normalized score.
    """
    score = ConfidenceScore(diagnosis=diagnosis)

    # Add symptom evidence
    for i in range(min(symptom_matches, 5)):  # Cap at 5 to prevent over-weighting
        score.add_evidence(EvidenceItem(
            source="symptom",
            description=f"Symptom #{i+1} matches this diagnosis pattern",
            weight=EvidenceWeight.SYMPTOM_MATCH,
            supports_diagnosis=True,
        ))

    # Add DTC evidence
    if dtc_match:
        score.add_evidence(EvidenceItem(
            source="dtc",
            description="DTC code directly corresponds to this diagnosis",
            weight=EvidenceWeight.DTC_CODE_MATCH,
            supports_diagnosis=True,
        ))

    # Add KB evidence
    if kb_match:
        score.add_evidence(EvidenceItem(
            source="knowledge_base",
            description="Known issue in the MotoDiag knowledge base matches this vehicle and diagnosis",
            weight=EvidenceWeight.KB_ISSUE_MATCH,
            supports_diagnosis=True,
        ))

    # Add test evidence
    if test_confirmed:
        score.add_evidence(EvidenceItem(
            source="diagnostic_test",
            description="Diagnostic test confirmed the suspected root cause",
            weight=EvidenceWeight.TEST_RESULT_CONFIRM,
            supports_diagnosis=True,
        ))

    if test_denied:
        score.add_evidence(EvidenceItem(
            source="diagnostic_test",
            description="Diagnostic test ruled out this cause",
            weight=EvidenceWeight.TEST_RESULT_DENY,
            supports_diagnosis=False,
        ))

    # Add history evidence
    if vehicle_history_match:
        score.add_evidence(EvidenceItem(
            source="vehicle_history",
            description="Vehicle history indicates this is a recurring or known issue on this specific bike",
            weight=EvidenceWeight.VEHICLE_HISTORY,
            supports_diagnosis=True,
        ))

    # Add correlation bonus
    if multiple_symptoms_correlated:
        score.add_evidence(EvidenceItem(
            source="correlation",
            description="Multiple symptoms independently point to the same root cause",
            weight=EvidenceWeight.MULTIPLE_SYMPTOM,
            supports_diagnosis=True,
        ))

    # Add environmental factor
    if environmental_factor:
        score.add_evidence(EvidenceItem(
            source="environmental",
            description="Environmental conditions (season, climate, altitude) support this diagnosis",
            weight=EvidenceWeight.ENVIRONMENTAL,
            supports_diagnosis=True,
        ))

    return score


def rank_diagnoses(scores: list[ConfidenceScore]) -> list[ConfidenceScore]:
    """Rank diagnoses by confidence score, highest first."""
    return sorted(scores, key=lambda s: s.normalized_score, reverse=True)
