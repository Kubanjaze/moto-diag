"""Phase 102 — Multimodal fusion tests.

Tests ModalityInput, FusionResult, ConflictRecord, MultimodalFusion
(fuse, build_fusion_context, conflict detection, weighted confidence,
diagnosis synthesis), and MODALITY_WEIGHTS.

All tests use constructed inputs — no API calls.
"""

import pytest

from motodiag.media.fusion import (
    ModalityType,
    ModalityInput,
    FusionResult,
    ConflictRecord,
    MultimodalFusion,
    MODALITY_WEIGHTS,
)


# --- Helpers ---


def _dtc_input(**kwargs) -> ModalityInput:
    return ModalityInput(
        modality_type=ModalityType.DTC,
        data_summary=kwargs.get("summary", "P0301 Cylinder 1 misfire"),
        findings=kwargs.get("findings", ["Cylinder 1 misfire detected"]),
        confidence=kwargs.get("confidence", 0.95),
    )


def _audio_input(**kwargs) -> ModalityInput:
    return ModalityInput(
        modality_type=ModalityType.AUDIO,
        data_summary=kwargs.get("summary", "Irregular firing pattern at idle"),
        findings=kwargs.get("findings", ["Missing pulse every 4th cycle"]),
        confidence=kwargs.get("confidence", 0.80),
    )


def _video_input(**kwargs) -> ModalityInput:
    return ModalityInput(
        modality_type=ModalityType.VIDEO,
        data_summary=kwargs.get("summary", "Blue smoke visible on startup"),
        findings=kwargs.get("findings", ["Blue smoke from exhaust"]),
        confidence=kwargs.get("confidence", 0.70),
    )


def _text_input(**kwargs) -> ModalityInput:
    return ModalityInput(
        modality_type=ModalityType.TEXT,
        data_summary=kwargs.get("summary", "Customer reports rough idle"),
        findings=kwargs.get("findings", ["Rough idle", "Poor fuel economy"]),
        confidence=kwargs.get("confidence", 0.60),
    )


def _test_result_input(**kwargs) -> ModalityInput:
    return ModalityInput(
        modality_type=ModalityType.TEST_RESULT,
        data_summary=kwargs.get("summary", "Compression test: cyl 1 low"),
        findings=kwargs.get("findings", ["Cylinder 1: 90 PSI (spec: 150-170)"]),
        confidence=kwargs.get("confidence", 0.90),
    )


# --- MODALITY_WEIGHTS ---


class TestModalityWeights:
    def test_weights_sum_to_one(self):
        total = sum(MODALITY_WEIGHTS.values())
        assert abs(total - 1.0) < 0.001

    def test_dtc_highest_weight(self):
        assert MODALITY_WEIGHTS[ModalityType.DTC] == 0.30

    def test_text_lowest_weight(self):
        assert MODALITY_WEIGHTS[ModalityType.TEXT] == 0.10

    def test_all_modality_types_have_weights(self):
        for mt in ModalityType:
            assert mt in MODALITY_WEIGHTS


# --- ModalityInput ---


class TestModalityInput:
    def test_basic_input(self):
        inp = _dtc_input()
        assert inp.modality_type == ModalityType.DTC
        assert inp.confidence == 0.95

    def test_weight_property(self):
        inp = _dtc_input()
        assert inp.weight == 0.30

    def test_weighted_confidence(self):
        inp = _dtc_input(confidence=0.80)
        expected = 0.80 * 0.30
        assert abs(inp.weighted_confidence - expected) < 0.001

    def test_default_confidence(self):
        inp = ModalityInput(
            modality_type=ModalityType.TEXT,
            data_summary="test",
        )
        assert inp.confidence == 0.5

    def test_raw_data_optional(self):
        inp = _audio_input()
        assert inp.raw_data is None


# --- ConflictRecord ---


class TestConflictRecord:
    def test_basic_conflict(self):
        cr = ConflictRecord(
            description="Audio says normal, DTC says misfire",
            modalities_involved=["audio", "dtc"],
            resolution_hint="Check under load",
            severity="high",
        )
        assert "audio" in cr.modalities_involved
        assert cr.severity == "high"


# --- FusionResult ---


class TestFusionResult:
    def test_empty_result(self):
        result = FusionResult()
        assert not result.has_conflicts
        assert not result.high_confidence

    def test_has_conflicts_true(self):
        result = FusionResult(conflicts=["A vs B"])
        assert result.has_conflicts

    def test_high_confidence_true(self):
        result = FusionResult(overall_confidence=0.85)
        assert result.high_confidence

    def test_high_confidence_false(self):
        result = FusionResult(overall_confidence=0.5)
        assert not result.high_confidence


# --- MultimodalFusion: fuse ---


class TestFuse:
    def test_empty_inputs(self):
        fusion = MultimodalFusion()
        result = fusion.fuse([])
        assert result.overall_confidence == 0.0
        assert result.modality_count == 0
        assert "No diagnostic inputs" in result.combined_diagnosis

    def test_single_modality(self):
        fusion = MultimodalFusion()
        result = fusion.fuse([_dtc_input()])
        assert result.modality_count == 1
        assert "dtc" in result.evidence_by_modality

    def test_two_modalities(self):
        fusion = MultimodalFusion()
        result = fusion.fuse([_dtc_input(), _audio_input()])
        assert result.modality_count == 2
        assert "dtc" in result.evidence_by_modality
        assert "audio" in result.evidence_by_modality

    def test_all_five_modalities(self):
        fusion = MultimodalFusion()
        inputs = [_dtc_input(), _test_result_input(), _audio_input(), _video_input(), _text_input()]
        result = fusion.fuse(inputs)
        assert result.modality_count == 5
        assert len(result.evidence_by_modality) == 5

    def test_weighted_confidence_calculation(self):
        fusion = MultimodalFusion()
        # DTC at 1.0 (weight 0.30) + Text at 0.0 (weight 0.10)
        # Weighted avg = (1.0*0.30 + 0.0*0.10) / (0.30 + 0.10) = 0.75
        inputs = [
            _dtc_input(confidence=1.0),
            _text_input(confidence=0.0),
        ]
        result = fusion.fuse(inputs)
        assert abs(result.overall_confidence - 0.75) < 0.01

    def test_evidence_preserved(self):
        findings = ["Misfire P0301", "Random misfire P0300"]
        fusion = MultimodalFusion()
        result = fusion.fuse([_dtc_input(findings=findings)])
        assert result.evidence_by_modality["dtc"] == findings

    def test_weights_used_recorded(self):
        fusion = MultimodalFusion()
        result = fusion.fuse([_dtc_input(), _audio_input()])
        assert result.modality_weights_used["dtc"] == 0.30
        assert result.modality_weights_used["audio"] == 0.20

    def test_custom_weights(self):
        custom = {ModalityType.DTC: 0.5, ModalityType.AUDIO: 0.5}
        fusion = MultimodalFusion(custom_weights=custom)
        inputs = [_dtc_input(confidence=1.0), _audio_input(confidence=0.0)]
        result = fusion.fuse(inputs)
        # (1.0*0.5 + 0.0*0.5) / (0.5+0.5) = 0.5
        assert abs(result.overall_confidence - 0.5) < 0.01

    def test_diagnosis_includes_modality_names(self):
        fusion = MultimodalFusion()
        result = fusion.fuse([_dtc_input(), _audio_input()])
        assert "dtc" in result.combined_diagnosis.lower()
        assert "audio" in result.combined_diagnosis.lower()


# --- MultimodalFusion: conflict detection ---


class TestConflictDetection:
    def test_no_conflicts_when_agreement(self):
        fusion = MultimodalFusion()
        inputs = [
            _dtc_input(findings=["Misfire"]),
            _audio_input(findings=["Misfire pattern"]),
        ]
        result = fusion.fuse(inputs)
        assert not result.has_conflicts

    def test_conflict_normal_idle_vs_misfire(self):
        fusion = MultimodalFusion()
        inputs = [
            _audio_input(summary="normal idle detected", findings=["normal idle"]),
            _dtc_input(findings=["misfire detected"]),
        ]
        result = fusion.fuse(inputs)
        assert result.has_conflicts
        assert any("misfire" in c.lower() for c in result.conflicts)

    def test_conflict_no_smoke_vs_oil_burn(self):
        fusion = MultimodalFusion()
        inputs = [
            _video_input(findings=["no smoke observed"]),
            _audio_input(findings=["oil burn signature detected"]),
        ]
        result = fusion.fuse(inputs)
        assert result.has_conflicts

    def test_conflict_details_populated(self):
        fusion = MultimodalFusion()
        inputs = [
            _audio_input(summary="normal idle detected", findings=["normal idle"]),
            _dtc_input(findings=["misfire code"]),
        ]
        result = fusion.fuse(inputs)
        assert len(result.conflict_details) > 0
        detail = result.conflict_details[0]
        assert len(detail.modalities_involved) >= 2
        assert len(detail.resolution_hint) > 0

    def test_no_conflict_same_modality(self):
        """Conflict requires DIFFERENT modalities."""
        fusion = MultimodalFusion()
        inputs = [
            _text_input(findings=["normal idle", "misfire"]),
        ]
        result = fusion.fuse(inputs)
        # Both patterns in same modality — should NOT flag as conflict
        assert not result.has_conflicts

    def test_conflict_note_in_diagnosis(self):
        fusion = MultimodalFusion()
        inputs = [
            _audio_input(summary="normal idle", findings=["normal idle"]),
            _dtc_input(findings=["misfire"]),
        ]
        result = fusion.fuse(inputs)
        assert "conflict" in result.combined_diagnosis.lower()


# --- MultimodalFusion: build_fusion_context ---


class TestBuildFusionContext:
    def test_empty_inputs(self):
        fusion = MultimodalFusion()
        ctx = fusion.build_fusion_context([])
        assert "No multimodal diagnostic data" in ctx

    def test_context_has_modality_sections(self):
        fusion = MultimodalFusion()
        ctx = fusion.build_fusion_context([_dtc_input(), _audio_input()])
        assert "[DTC]" in ctx
        assert "[AUDIO]" in ctx

    def test_context_has_findings(self):
        fusion = MultimodalFusion()
        ctx = fusion.build_fusion_context([_dtc_input(findings=["P0301 misfire"])])
        assert "P0301 misfire" in ctx

    def test_context_has_confidence(self):
        fusion = MultimodalFusion()
        ctx = fusion.build_fusion_context([_dtc_input(confidence=0.95)])
        assert "0.95" in ctx

    def test_context_has_weight(self):
        fusion = MultimodalFusion()
        ctx = fusion.build_fusion_context([_dtc_input()])
        assert "0.30" in ctx

    def test_context_has_overall_confidence(self):
        fusion = MultimodalFusion()
        ctx = fusion.build_fusion_context([_dtc_input(confidence=0.9)])
        assert "Overall weighted confidence" in ctx

    def test_context_includes_conflict_warning(self):
        fusion = MultimodalFusion()
        inputs = [
            _audio_input(summary="normal idle", findings=["normal idle"]),
            _dtc_input(findings=["misfire detected"]),
        ]
        ctx = fusion.build_fusion_context(inputs)
        assert "CONFLICTS DETECTED" in ctx
