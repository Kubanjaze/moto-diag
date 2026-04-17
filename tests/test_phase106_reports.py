"""Tests for Phase 106 — Media-Enhanced Diagnostic Reports.

Tests ReportGenerator, DiagnosticReport, MediaAttachment, text formatting,
summary generation, report merging, and edge cases.
All tests use synthetic data — no API calls or real media files.
"""

import pytest
from datetime import datetime, timezone

from motodiag.media.reports import (
    ReportGenerator,
    DiagnosticReport,
    MediaAttachment,
    MediaType,
    ConfidenceLevel,
)


# --- Helpers ---

def _make_attachment(media_type: str = "audio_clip", filename: str = "idle_clip.wav") -> MediaAttachment:
    return MediaAttachment(
        media_type=MediaType(media_type),
        filename=filename,
        timestamp=15.0,
        description="Engine idle audio clip",
        analysis_summary="Normal idle pattern, no anomalies detected.",
    )


def _make_report(gen: ReportGenerator = None) -> DiagnosticReport:
    gen = gen or ReportGenerator()
    return gen.generate_report(
        vehicle_context={"make": "Harley-Davidson", "model": "Road King", "year": 2015, "mileage": 45000},
        symptoms=["rough idle", "popping on deceleration"],
        diagnosis="Lean condition — intake leak at rear cylinder manifold",
        diagnosis_details=[
            "Audio analysis detected irregular exhaust pulses at idle",
            "Decel pop test showed consistent popping on all 3 trials",
            "Rear cylinder manifold gasket likely failed",
        ],
        confidence="high",
        confidence_score=0.89,
        recommendations=[
            "Replace rear cylinder intake manifold gasket",
            "Inspect front cylinder gasket while disassembled",
            "Re-test after repair with idle_baseline protocol",
        ],
        notes="Customer reports issue worse in cold weather.",
        session_id="sess-001",
    )


# --- MediaAttachment tests ---

class TestMediaAttachment:
    def test_attachment_creation(self):
        att = _make_attachment()
        assert att.media_type == MediaType.AUDIO_CLIP
        assert att.filename == "idle_clip.wav"
        assert att.timestamp == 15.0
        assert att.description == "Engine idle audio clip"
        assert isinstance(att.attachment_id, str)
        assert isinstance(att.created_at, datetime)

    def test_all_media_types(self):
        for mt in MediaType:
            att = MediaAttachment(media_type=mt, filename=f"test.{mt.value}")
            assert att.media_type == mt

    def test_attachment_with_tags(self):
        att = MediaAttachment(
            media_type=MediaType.SPECTROGRAM,
            filename="spec.png",
            tags=["exhaust", "frequency_analysis"],
        )
        assert len(att.tags) == 2


# --- DiagnosticReport model tests ---

class TestDiagnosticReport:
    def test_report_creation(self):
        report = _make_report()
        assert report.vehicle_context["make"] == "Harley-Davidson"
        assert len(report.symptoms) == 2
        assert report.confidence == ConfidenceLevel.HIGH
        assert report.confidence_score == 0.89
        assert report.session_id == "sess-001"
        assert isinstance(report.report_id, str)

    def test_report_has_media_evidence(self):
        report = _make_report()
        assert report.has_media_evidence is False
        report.attachments.append(_make_attachment())
        assert report.has_media_evidence is True
        assert report.attachment_count == 1

    def test_get_attachments_by_type(self):
        report = _make_report()
        report.attachments.append(_make_attachment("audio_clip", "a.wav"))
        report.attachments.append(_make_attachment("photo", "b.jpg"))
        report.attachments.append(_make_attachment("audio_clip", "c.wav"))
        audio = report.get_attachments_by_type(MediaType.AUDIO_CLIP)
        assert len(audio) == 2
        photos = report.get_attachments_by_type(MediaType.PHOTO)
        assert len(photos) == 1


# --- ReportGenerator.generate_report tests ---

class TestGenerateReport:
    def test_generate_basic_report(self):
        gen = ReportGenerator()
        report = gen.generate_report(
            diagnosis="Test diagnosis",
            confidence="medium",
        )
        assert report.diagnosis == "Test diagnosis"
        assert report.confidence == ConfidenceLevel.MEDIUM
        assert report.symptoms == []
        assert report.attachments == []

    def test_generate_with_all_fields(self):
        report = _make_report()
        assert len(report.diagnosis_details) == 3
        assert len(report.recommendations) == 3
        assert report.notes != ""

    def test_invalid_confidence_raises(self):
        gen = ReportGenerator()
        with pytest.raises(ValueError, match="Invalid confidence"):
            gen.generate_report(confidence="very_high")

    def test_generate_empty_report(self):
        gen = ReportGenerator()
        report = gen.generate_report()
        assert report.diagnosis == ""
        assert report.confidence == ConfidenceLevel.MEDIUM
        assert report.vehicle_context == {}


# --- ReportGenerator.add_attachment tests ---

class TestAddAttachment:
    def test_add_attachment(self):
        gen = ReportGenerator()
        report = gen.generate_report(diagnosis="test")
        att = gen.add_attachment(
            report,
            media_type="spectrogram",
            filename="idle_spec.png",
            timestamp=10.0,
            description="Spectrogram of idle recording",
            analysis_summary="Fundamental at 40 Hz, no anomalous harmonics",
        )
        assert att.media_type == MediaType.SPECTROGRAM
        assert report.attachment_count == 1
        assert report.attachments[0].filename == "idle_spec.png"

    def test_add_multiple_attachments(self):
        gen = ReportGenerator()
        report = gen.generate_report()
        gen.add_attachment(report, "audio_clip", "clip1.wav")
        gen.add_attachment(report, "video_frame", "frame1.jpg")
        gen.add_attachment(report, "photo", "engine.jpg", tags=["engine", "visual"])
        assert report.attachment_count == 3

    def test_invalid_media_type_raises(self):
        gen = ReportGenerator()
        report = gen.generate_report()
        with pytest.raises(ValueError, match="Invalid media_type"):
            gen.add_attachment(report, "hologram", "future.holo")


# --- ReportGenerator.format_text_report tests ---

class TestFormatTextReport:
    def test_text_report_contains_sections(self):
        gen = ReportGenerator()
        report = _make_report(gen)
        gen.add_attachment(report, "audio_clip", "idle.wav", timestamp=5.0,
                          description="Idle recording", analysis_summary="Normal pattern")
        text = gen.format_text_report(report)
        assert "DIAGNOSTIC REPORT" in text
        assert "VEHICLE:" in text
        assert "Harley-Davidson" in text
        assert "REPORTED SYMPTOMS:" in text
        assert "rough idle" in text
        assert "DIAGNOSIS:" in text
        assert "Lean condition" in text
        assert "HIGH" in text
        assert "89%" in text
        assert "FINDINGS:" in text
        assert "MEDIA EVIDENCE" in text
        assert "RECOMMENDATIONS:" in text
        assert "NOTES:" in text

    def test_text_report_minimal(self):
        gen = ReportGenerator()
        report = gen.generate_report(diagnosis="Unknown issue")
        text = gen.format_text_report(report)
        assert "DIAGNOSTIC REPORT" in text
        assert "Unknown issue" in text
        # Should not have sections for empty fields
        assert "VEHICLE:" not in text
        assert "REPORTED SYMPTOMS:" not in text

    def test_text_report_with_session_id(self):
        gen = ReportGenerator()
        report = gen.generate_report(session_id="sess-test-123")
        text = gen.format_text_report(report)
        assert "sess-test-123" in text


# --- ReportGenerator.format_summary tests ---

class TestFormatSummary:
    def test_summary_basic(self):
        gen = ReportGenerator()
        report = _make_report(gen)
        summary = gen.format_summary(report)
        assert "2015 Harley-Davidson Road King" in summary
        assert "rough idle" in summary
        assert "Lean condition" in summary
        assert "high" in summary
        assert "89%" in summary

    def test_summary_no_vehicle(self):
        gen = ReportGenerator()
        report = gen.generate_report(diagnosis="Test")
        summary = gen.format_summary(report)
        assert "Unknown vehicle" in summary

    def test_summary_with_evidence(self):
        gen = ReportGenerator()
        report = gen.generate_report(diagnosis="Test")
        gen.add_attachment(report, "audio_clip", "a.wav")
        gen.add_attachment(report, "audio_clip", "b.wav")
        gen.add_attachment(report, "photo", "c.jpg")
        summary = gen.format_summary(report)
        assert "2 audio clip(s)" in summary
        assert "1 photo(s)" in summary

    def test_summary_no_evidence(self):
        gen = ReportGenerator()
        report = gen.generate_report(diagnosis="Test")
        summary = gen.format_summary(report)
        assert "no media evidence" in summary

    def test_summary_many_symptoms_truncated(self):
        gen = ReportGenerator()
        report = gen.generate_report(
            symptoms=["a", "b", "c", "d", "e"],
            diagnosis="Test",
        )
        summary = gen.format_summary(report)
        assert "+2 more" in summary


# --- ReportGenerator.merge_reports tests ---

class TestMergeReports:
    def test_merge_two_reports(self):
        gen = ReportGenerator()
        r1 = gen.generate_report(
            vehicle_context={"make": "Honda", "model": "CBR600RR"},
            symptoms=["rough idle"],
            diagnosis="Fuel issue",
            confidence="low",
            recommendations=["Check fuel pump"],
        )
        r2 = gen.generate_report(
            vehicle_context={"make": "Honda", "model": "CBR600RR"},
            symptoms=["rough idle", "stalling"],
            diagnosis="Ignition issue",
            confidence="high",
            confidence_score=0.85,
            recommendations=["Replace coil pack", "Check fuel pump"],
        )
        merged = gen.merge_reports([r1, r2], merged_diagnosis="Combined: fuel + ignition")
        assert merged.diagnosis == "Combined: fuel + ignition"
        assert "rough idle" in merged.symptoms
        assert "stalling" in merged.symptoms
        assert len(merged.symptoms) == 2  # Deduplicated
        assert merged.confidence == ConfidenceLevel.HIGH  # Best from any report
        assert "Check fuel pump" in merged.recommendations
        assert "Replace coil pack" in merged.recommendations
        assert len(merged.recommendations) == 2  # Deduplicated

    def test_merge_empty_raises(self):
        gen = ReportGenerator()
        with pytest.raises(ValueError, match="At least one report"):
            gen.merge_reports([])

    def test_merge_preserves_attachments(self):
        gen = ReportGenerator()
        r1 = gen.generate_report()
        gen.add_attachment(r1, "audio_clip", "a.wav")
        r2 = gen.generate_report()
        gen.add_attachment(r2, "photo", "b.jpg")
        merged = gen.merge_reports([r1, r2])
        assert merged.attachment_count == 2

    def test_merge_single_report(self):
        gen = ReportGenerator()
        r1 = _make_report(gen)
        merged = gen.merge_reports([r1])
        assert merged.diagnosis == r1.diagnosis
        assert merged.vehicle_context == r1.vehicle_context
