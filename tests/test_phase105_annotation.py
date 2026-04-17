"""Tests for Phase 105 — Video Annotation + Timestamps.

Tests VideoAnnotator, AnnotatedVideo, Annotation, timeline generation,
filtering, auto-annotation, and edge cases.
All tests use synthetic data — no actual video files or API calls.
"""

import pytest
from datetime import datetime, timezone

from motodiag.media.annotation import (
    VideoAnnotator,
    AnnotatedVideo,
    Annotation,
    AnnotationSeverity,
    AnnotatorType,
)


# --- Helpers ---

def _make_video(duration: float = 120.0, filename: str = "test_idle.mp4") -> AnnotatedVideo:
    """Create a test AnnotatedVideo with metadata."""
    annotator = VideoAnnotator()
    return annotator.create_video(metadata={
        "filename": filename,
        "duration_seconds": duration,
        "resolution": "1920x1080",
        "format": "mp4",
    })


# --- Annotation model tests ---

class TestAnnotationModel:
    def test_annotation_creation(self):
        ann = Annotation(
            timestamp_sec=15.3,
            label="smoke",
            description="Blue smoke from exhaust at idle.",
            severity=AnnotationSeverity.WARNING,
            annotator=AnnotatorType.MECHANIC,
        )
        assert ann.timestamp_sec == 15.3
        assert ann.label == "smoke"
        assert ann.severity == AnnotationSeverity.WARNING
        assert ann.annotator == AnnotatorType.MECHANIC
        assert isinstance(ann.annotation_id, str)
        assert isinstance(ann.created_at, datetime)

    def test_annotation_defaults(self):
        ann = Annotation(timestamp_sec=0.0, label="start")
        assert ann.severity == AnnotationSeverity.INFO
        assert ann.annotator == AnnotatorType.MECHANIC
        assert ann.description == ""
        assert ann.tags == []
        assert ann.confidence is None

    def test_annotation_with_ai_confidence(self):
        ann = Annotation(
            timestamp_sec=30.0,
            label="misfire",
            annotator=AnnotatorType.AI,
            confidence=0.87,
        )
        assert ann.annotator == AnnotatorType.AI
        assert ann.confidence == 0.87


# --- AnnotatedVideo model tests ---

class TestAnnotatedVideoModel:
    def test_video_creation(self):
        video = _make_video()
        assert video.annotation_count == 0
        assert video.duration_seconds == 120.0
        assert video.video_metadata["filename"] == "test_idle.mp4"
        assert isinstance(video.video_id, str)

    def test_video_no_metadata(self):
        annotator = VideoAnnotator()
        video = annotator.create_video()
        assert video.video_metadata == {}
        assert video.duration_seconds is None


# --- VideoAnnotator.add_annotation tests ---

class TestAddAnnotation:
    def test_add_single(self):
        video = _make_video()
        annotator = VideoAnnotator()
        ann = annotator.add_annotation(video, timestamp_sec=10.0, label="knock")
        assert ann.label == "knock"
        assert video.annotation_count == 1
        assert video.annotations[0].timestamp_sec == 10.0

    def test_add_multiple_sorted(self):
        video = _make_video()
        annotator = VideoAnnotator()
        annotator.add_annotation(video, timestamp_sec=30.0, label="smoke")
        annotator.add_annotation(video, timestamp_sec=10.0, label="knock")
        annotator.add_annotation(video, timestamp_sec=20.0, label="vibration")
        assert video.annotation_count == 3
        # Should be sorted by timestamp
        timestamps = [a.timestamp_sec for a in video.annotations]
        assert timestamps == [10.0, 20.0, 30.0]

    def test_add_with_severity(self):
        video = _make_video()
        annotator = VideoAnnotator()
        ann = annotator.add_annotation(
            video, timestamp_sec=5.0, label="crack",
            severity="critical", description="Visible crack in exhaust header."
        )
        assert ann.severity == AnnotationSeverity.CRITICAL
        assert ann.description == "Visible crack in exhaust header."

    def test_negative_timestamp_raises(self):
        video = _make_video()
        annotator = VideoAnnotator()
        with pytest.raises(ValueError, match="non-negative"):
            annotator.add_annotation(video, timestamp_sec=-1.0, label="bad")

    def test_timestamp_exceeds_duration_raises(self):
        video = _make_video(duration=60.0)
        annotator = VideoAnnotator()
        with pytest.raises(ValueError, match="exceeds video duration"):
            annotator.add_annotation(video, timestamp_sec=90.0, label="late")

    def test_invalid_severity_raises(self):
        video = _make_video()
        annotator = VideoAnnotator()
        with pytest.raises(ValueError, match="Invalid severity"):
            annotator.add_annotation(video, timestamp_sec=5.0, label="x", severity="extreme")

    def test_invalid_annotator_raises(self):
        video = _make_video()
        annotator = VideoAnnotator()
        with pytest.raises(ValueError, match="Invalid annotator"):
            annotator.add_annotation(video, timestamp_sec=5.0, label="x", annotator="robot")


# --- Filtering tests ---

class TestAnnotationFiltering:
    def _populate_video(self):
        video = _make_video(duration=120.0)
        annotator = VideoAnnotator()
        annotator.add_annotation(video, 10.0, "idle_start", severity="info")
        annotator.add_annotation(video, 25.0, "rough_idle", severity="warning")
        annotator.add_annotation(video, 45.0, "smoke", severity="critical")
        annotator.add_annotation(video, 60.0, "rev_test", severity="info")
        annotator.add_annotation(video, 80.0, "misfire", severity="critical")
        annotator.add_annotation(video, 100.0, "stable_idle", severity="info")
        return video, annotator

    def test_get_annotations_in_range(self):
        video, annotator = self._populate_video()
        results = annotator.get_annotations_in_range(video, 20.0, 70.0)
        assert len(results) == 3
        labels = [a.label for a in results]
        assert "rough_idle" in labels
        assert "smoke" in labels
        assert "rev_test" in labels

    def test_range_inclusive_boundaries(self):
        video, annotator = self._populate_video()
        results = annotator.get_annotations_in_range(video, 25.0, 45.0)
        assert len(results) == 2

    def test_range_no_results(self):
        video, annotator = self._populate_video()
        results = annotator.get_annotations_in_range(video, 110.0, 120.0)
        assert len(results) == 0

    def test_invalid_range_raises(self):
        video, annotator = self._populate_video()
        with pytest.raises(ValueError, match="must be <="):
            annotator.get_annotations_in_range(video, 50.0, 10.0)

    def test_get_critical_moments(self):
        video, annotator = self._populate_video()
        critical = annotator.get_critical_moments(video, include_warnings=True)
        assert len(critical) == 3  # 1 warning + 2 critical

    def test_get_critical_only(self):
        video, annotator = self._populate_video()
        critical = annotator.get_critical_moments(video, include_warnings=False)
        assert len(critical) == 2
        assert all(a.severity == AnnotationSeverity.CRITICAL for a in critical)


# --- Timeline generation tests ---

class TestGenerateTimeline:
    def test_timeline_output(self):
        video = _make_video(duration=60.0, filename="idle_test.mp4")
        annotator = VideoAnnotator()
        annotator.add_annotation(video, 5.0, "start", description="Engine started")
        annotator.add_annotation(video, 30.0, "rough", severity="warning", description="Rough idle begins")
        timeline = annotator.generate_timeline(video)
        assert "idle_test.mp4" in timeline
        assert "[INFO]" in timeline
        assert "[WARNING]" in timeline
        assert "start" in timeline
        assert "rough" in timeline

    def test_empty_timeline(self):
        video = _make_video()
        annotator = VideoAnnotator()
        timeline = annotator.generate_timeline(video)
        assert timeline == "No annotations."

    def test_timeline_without_descriptions(self):
        video = _make_video()
        annotator = VideoAnnotator()
        annotator.add_annotation(video, 10.0, "knock", description="Loud knock from top end")
        timeline = annotator.generate_timeline(video, include_descriptions=False)
        assert "knock" in timeline
        assert "Loud knock" not in timeline


# --- Auto-annotate tests ---

class TestAutoAnnotate:
    def test_auto_annotate_from_results(self):
        video = _make_video()
        annotator = VideoAnnotator()
        results = [
            {"timestamp_sec": 10.0, "label": "anomaly_spike", "severity": "warning",
             "confidence": 0.82, "description": "Amplitude spike detected"},
            {"timestamp_sec": 30.0, "label": "rpm_drop", "severity": "info",
             "confidence": 0.65, "tags": ["rpm"]},
            {"timestamp_sec": 50.0, "label": "misfire_pattern", "severity": "critical",
             "confidence": 0.91},
        ]
        created = annotator.auto_annotate(video, results)
        assert len(created) == 3
        assert video.annotation_count == 3
        assert all(a.annotator == AnnotatorType.AI for a in created)
        assert created[0].confidence == 0.82

    def test_auto_annotate_skips_incomplete(self):
        video = _make_video()
        annotator = VideoAnnotator()
        results = [
            {"timestamp_sec": 10.0, "label": "valid"},
            {"label": "no_timestamp"},  # Missing timestamp
            {"timestamp_sec": 20.0},   # Missing label
        ]
        created = annotator.auto_annotate(video, results)
        assert len(created) == 1

    def test_auto_annotate_empty_results(self):
        video = _make_video()
        annotator = VideoAnnotator()
        created = annotator.auto_annotate(video, [])
        assert len(created) == 0


# --- Label search and removal tests ---

class TestLabelSearchAndRemoval:
    def test_get_by_label_case_insensitive(self):
        video = _make_video()
        annotator = VideoAnnotator()
        annotator.add_annotation(video, 10.0, "Smoke")
        annotator.add_annotation(video, 20.0, "knock")
        annotator.add_annotation(video, 30.0, "SMOKE")
        results = annotator.get_annotations_by_label(video, "smoke")
        assert len(results) == 2

    def test_remove_annotation(self):
        video = _make_video()
        annotator = VideoAnnotator()
        ann = annotator.add_annotation(video, 10.0, "test")
        assert video.annotation_count == 1
        removed = annotator.remove_annotation(video, ann.annotation_id)
        assert removed is True
        assert video.annotation_count == 0

    def test_remove_nonexistent_returns_false(self):
        video = _make_video()
        annotator = VideoAnnotator()
        removed = annotator.remove_annotation(video, "fake-id")
        assert removed is False
