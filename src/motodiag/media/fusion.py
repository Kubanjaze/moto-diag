"""Multimodal fusion for combining diagnostic evidence across modalities.

Phase 102: Combines evidence from audio analysis, video/image analysis,
text symptom descriptions, DTC codes, and test results into a unified
diagnostic assessment. Weights modalities by reliability, detects conflicts
between modalities, and formats the combined evidence for AI prompt injection.

Designed to feed the AI Diagnostic Engine (Track C) with richer context
than any single modality alone.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ModalityType(str, Enum):
    """Types of diagnostic input modalities."""
    AUDIO = "audio"
    VIDEO = "video"
    TEXT = "text"
    DTC = "dtc"
    TEST_RESULT = "test_result"


# --- Modality Weights ---
# Weights reflect the diagnostic reliability of each modality.
# DTC codes are the most objective, followed by measured test results,
# then audio spectrogram analysis, then video/visual, then text descriptions.
# Weights sum to 1.0.

MODALITY_WEIGHTS: dict[str, float] = {
    ModalityType.DTC: 0.30,
    ModalityType.TEST_RESULT: 0.25,
    ModalityType.AUDIO: 0.20,
    ModalityType.VIDEO: 0.15,
    ModalityType.TEXT: 0.10,
}


class ModalityInput(BaseModel):
    """Input from a single diagnostic modality."""
    modality_type: ModalityType = Field(..., description="Type of modality")
    data_summary: str = Field(
        ...,
        description="Brief summary of what this modality captured",
    )
    findings: list[str] = Field(
        default_factory=list,
        description="Specific findings from this modality",
    )
    confidence: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Confidence in this modality's findings (0.0-1.0)",
    )
    raw_data: Optional[dict] = Field(
        default=None,
        description="Optional raw data payload for downstream processing",
    )

    @property
    def weight(self) -> float:
        """Look up the standard weight for this modality type."""
        return MODALITY_WEIGHTS.get(self.modality_type, 0.10)

    @property
    def weighted_confidence(self) -> float:
        """Confidence multiplied by modality weight."""
        return self.confidence * self.weight


class ConflictRecord(BaseModel):
    """Records a conflict between two or more modalities."""
    description: str = Field(
        ..., description="Description of the conflicting evidence"
    )
    modalities_involved: list[str] = Field(
        default_factory=list,
        description="Which modalities disagree",
    )
    resolution_hint: str = Field(
        default="",
        description="Suggested approach to resolve the conflict",
    )
    severity: str = Field(
        default="medium",
        description="Impact of this conflict: low, medium, high",
    )


class FusionResult(BaseModel):
    """Result of combining evidence across all modalities."""
    combined_diagnosis: str = Field(
        default="",
        description="Synthesized diagnosis from all modalities",
    )
    evidence_by_modality: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Findings grouped by modality type",
    )
    overall_confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Weighted confidence across all modalities",
    )
    conflicts: list[str] = Field(
        default_factory=list,
        description="Conflicts detected between modalities",
    )
    conflict_details: list[ConflictRecord] = Field(
        default_factory=list,
        description="Detailed conflict records",
    )
    modality_count: int = Field(
        default=0,
        description="Number of modalities that contributed evidence",
    )
    modality_weights_used: dict[str, float] = Field(
        default_factory=dict,
        description="Weights applied to each modality",
    )

    @property
    def has_conflicts(self) -> bool:
        """Whether any conflicts were detected."""
        return len(self.conflicts) > 0

    @property
    def high_confidence(self) -> bool:
        """Whether overall confidence exceeds 0.7."""
        return self.overall_confidence > 0.7


# --- Conflict Detection Patterns ---
# Pairs of findings that indicate a conflict when they appear in different modalities.
# Format: (pattern_A, pattern_B, description, resolution_hint)

_CONFLICT_PATTERNS: list[tuple[str, str, str, str]] = [
    (
        "no smoke",
        "oil burn",
        "Video shows no smoke but audio/text indicates oil burning",
        "Re-examine under load — smoke may only appear under acceleration",
    ),
    (
        "no leak",
        "coolant loss",
        "Visual inspection shows no leak but coolant level is dropping",
        "Check for internal leak (head gasket) — perform coolant pressure test",
    ),
    (
        "normal idle",
        "misfire",
        "Audio sounds normal at idle but DTC/text reports misfire",
        "Misfire may be intermittent — check under load or at specific RPM range",
    ),
    (
        "running smooth",
        "rough idle",
        "One modality says smooth, another says rough",
        "Verify RPM stability with tachometer — subjective assessment may vary",
    ),
    (
        "no codes",
        "check engine",
        "No DTCs stored but check engine light is on",
        "Scan for pending codes — light may be from a cleared but recurring fault",
    ),
    (
        "cold start normal",
        "cold start rough",
        "Conflicting reports on cold start behavior",
        "Record audio on next cold start for objective analysis",
    ),
    (
        "chain tight",
        "chain loose",
        "Conflicting chain tension assessment",
        "Measure chain slack with ruler at tightest point of rotation",
    ),
]


class MultimodalFusion:
    """Combines diagnostic evidence from multiple modalities into a unified assessment.

    Weights evidence by modality reliability, detects conflicts between
    modalities, and formats the combined evidence for AI prompt injection.

    Usage:
        fusion = MultimodalFusion()
        inputs = [
            ModalityInput(modality_type="dtc", data_summary="P0301 cylinder 1 misfire", findings=["Cylinder 1 misfire"], confidence=0.95),
            ModalityInput(modality_type="audio", data_summary="Irregular firing pattern", findings=["Missing pulse every 4th cycle"], confidence=0.80),
        ]
        result = fusion.fuse(inputs)
    """

    def __init__(
        self,
        custom_weights: Optional[dict[str, float]] = None,
    ):
        """Initialize the fusion engine.

        Args:
            custom_weights: Override default modality weights. Keys are
                ModalityType values, values are floats. Does not need to
                sum to 1.0 — weights are normalized internally.
        """
        if custom_weights:
            self.weights = dict(custom_weights)
        else:
            self.weights = dict(MODALITY_WEIGHTS)

    def fuse(self, inputs: list[ModalityInput]) -> FusionResult:
        """Combine evidence from multiple modalities into a single assessment.

        Steps:
        1. Collect findings by modality.
        2. Calculate weighted confidence.
        3. Detect conflicts between modalities.
        4. Synthesize a combined diagnosis summary.

        Args:
            inputs: List of ModalityInput from different diagnostic sources.

        Returns:
            FusionResult with combined diagnosis, evidence, confidence, and conflicts.
        """
        if not inputs:
            return FusionResult(
                combined_diagnosis="No diagnostic inputs provided.",
                evidence_by_modality={},
                overall_confidence=0.0,
                conflicts=[],
                modality_count=0,
            )

        # Step 1: Group findings by modality
        evidence_by_modality: dict[str, list[str]] = {}
        for inp in inputs:
            key = inp.modality_type.value if isinstance(inp.modality_type, ModalityType) else str(inp.modality_type)
            evidence_by_modality[key] = inp.findings

        # Step 2: Calculate weighted confidence
        overall_confidence = self._calculate_weighted_confidence(inputs)

        # Step 3: Detect conflicts
        conflicts, conflict_details = self._detect_conflicts(inputs)

        # Step 4: Synthesize diagnosis
        combined_diagnosis = self._synthesize_diagnosis(inputs, conflicts)

        # Weights actually used
        weights_used: dict[str, float] = {}
        for inp in inputs:
            key = inp.modality_type.value if isinstance(inp.modality_type, ModalityType) else str(inp.modality_type)
            weights_used[key] = self.weights.get(inp.modality_type, 0.10)

        return FusionResult(
            combined_diagnosis=combined_diagnosis,
            evidence_by_modality=evidence_by_modality,
            overall_confidence=round(overall_confidence, 4),
            conflicts=conflicts,
            conflict_details=conflict_details,
            modality_count=len(inputs),
            modality_weights_used=weights_used,
        )

    def build_fusion_context(self, inputs: list[ModalityInput]) -> str:
        """Format combined evidence for AI prompt injection.

        Produces a text block that can be injected into a Claude diagnostic
        prompt to provide multi-modal context.

        Args:
            inputs: List of ModalityInput from different sources.

        Returns:
            Formatted text string for prompt injection.
        """
        if not inputs:
            return "No multimodal diagnostic data available."

        sections = []
        sections.append("=== MULTIMODAL DIAGNOSTIC EVIDENCE ===\n")

        for inp in inputs:
            modality_label = inp.modality_type.value.upper() if isinstance(
                inp.modality_type, ModalityType
            ) else str(inp.modality_type).upper()

            weight = self.weights.get(inp.modality_type, 0.10)
            section = f"[{modality_label}] (weight: {weight:.2f}, confidence: {inp.confidence:.2f})\n"
            section += f"  Summary: {inp.data_summary}\n"
            if inp.findings:
                for finding in inp.findings:
                    section += f"  - {finding}\n"
            sections.append(section)

        # Add conflict warnings if any
        _, conflict_details = self._detect_conflicts(inputs)
        if conflict_details:
            sections.append("--- CONFLICTS DETECTED ---")
            for cd in conflict_details:
                sections.append(
                    f"  WARNING: {cd.description} "
                    f"(modalities: {', '.join(cd.modalities_involved)})\n"
                    f"  Resolution: {cd.resolution_hint}"
                )

        overall_conf = self._calculate_weighted_confidence(inputs)
        sections.append(f"\nOverall weighted confidence: {overall_conf:.2f}")
        sections.append(f"Modalities contributing: {len(inputs)}")
        sections.append("=== END MULTIMODAL EVIDENCE ===")

        return "\n".join(sections)

    def _calculate_weighted_confidence(self, inputs: list[ModalityInput]) -> float:
        """Calculate weighted average confidence across modalities.

        Each modality's confidence is multiplied by its weight, then
        the sum is divided by the sum of active weights (so missing
        modalities don't dilute the score).
        """
        if not inputs:
            return 0.0

        total_weighted = 0.0
        total_weight = 0.0

        for inp in inputs:
            w = self.weights.get(inp.modality_type, 0.10)
            total_weighted += inp.confidence * w
            total_weight += w

        if total_weight == 0.0:
            return 0.0

        return total_weighted / total_weight

    def _detect_conflicts(
        self,
        inputs: list[ModalityInput],
    ) -> tuple[list[str], list[ConflictRecord]]:
        """Detect conflicts between modalities using pattern matching.

        Compares all findings across modalities against known conflict patterns.

        Returns:
            Tuple of (conflict summary strings, detailed ConflictRecord list).
        """
        conflicts: list[str] = []
        conflict_details: list[ConflictRecord] = []

        # Build a flat list of (modality_key, finding_lower) for comparison
        all_findings: list[tuple[str, str]] = []
        for inp in inputs:
            key = inp.modality_type.value if isinstance(inp.modality_type, ModalityType) else str(inp.modality_type)
            for finding in inp.findings:
                all_findings.append((key, finding.lower()))
            # Also include the data summary as a finding source
            all_findings.append((key, inp.data_summary.lower()))

        # Check each conflict pattern
        for pattern_a, pattern_b, description, resolution in _CONFLICT_PATTERNS:
            sources_a: list[str] = []
            sources_b: list[str] = []

            for mod_key, text in all_findings:
                if pattern_a in text:
                    sources_a.append(mod_key)
                if pattern_b in text:
                    sources_b.append(mod_key)

            # Conflict exists if both patterns match AND they come from different modalities
            if sources_a and sources_b:
                unique_a = set(sources_a)
                unique_b = set(sources_b)
                if unique_a != unique_b:  # Different modalities
                    conflict_str = f"{description} [{', '.join(unique_a)} vs {', '.join(unique_b)}]"
                    conflicts.append(conflict_str)
                    conflict_details.append(ConflictRecord(
                        description=description,
                        modalities_involved=sorted(unique_a | unique_b),
                        resolution_hint=resolution,
                        severity="medium",
                    ))

        return conflicts, conflict_details

    def _synthesize_diagnosis(
        self,
        inputs: list[ModalityInput],
        conflicts: list[str],
    ) -> str:
        """Synthesize a combined diagnosis summary from all modality inputs.

        Prioritizes findings from higher-weighted modalities.
        """
        if not inputs:
            return "No diagnostic inputs provided."

        # Sort inputs by weight (highest first)
        sorted_inputs = sorted(
            inputs,
            key=lambda i: self.weights.get(i.modality_type, 0.10),
            reverse=True,
        )

        parts = []
        for inp in sorted_inputs:
            if inp.findings:
                modality_label = inp.modality_type.value if isinstance(
                    inp.modality_type, ModalityType
                ) else str(inp.modality_type)
                joined = "; ".join(inp.findings[:3])  # Top 3 findings per modality
                parts.append(f"{modality_label}: {joined}")

        summary = "Combined evidence: " + " | ".join(parts) if parts else "No findings across modalities."

        if conflicts:
            summary += f" [NOTE: {len(conflicts)} conflict(s) detected between modalities]"

        return summary
