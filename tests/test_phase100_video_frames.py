"""Phase 100 — Video frame extraction tests.

Tests VideoMetadata, VideoFrame, FrameExtractionConfig, SceneChangeMarker,
VideoFrameExtractor (extract_frames, extract_keyframes, get_frame_at_timestamp,
get_extraction_plan), and placeholder generation.

All tests are simulated — no actual video files or processing required.
"""

import pytest

from motodiag.media.video_frames import (
    VideoFormat,
    VideoResolution,
    VideoMetadata,
    VideoFrame,
    FrameExtractionConfig,
    SceneChangeMarker,
    VideoFrameExtractor,
)


# --- Helpers ---


def _make_video(
    duration: float = 30.0,
    fps: float = 30.0,
    width: int = 1920,
    height: int = 1080,
    filename: str = "test_exhaust.mp4",
    file_size: int = 50_000_000,
) -> VideoMetadata:
    """Create a VideoMetadata for testing."""
    return VideoMetadata(
        filename=filename,
        duration_seconds=duration,
        resolution=VideoResolution(width=width, height=height),
        fps=fps,
        file_size_bytes=file_size,
        format=VideoFormat.MP4,
    )


# --- VideoResolution ---


class TestVideoResolution:
    def test_basic_resolution(self):
        res = VideoResolution(width=1920, height=1080)
        assert res.width == 1920
        assert res.height == 1080

    def test_aspect_ratio(self):
        res = VideoResolution(width=1920, height=1080)
        assert abs(res.aspect_ratio - 16 / 9) < 0.01

    def test_label_1080p(self):
        res = VideoResolution(width=1920, height=1080)
        assert res.label == "1080p"

    def test_label_4k(self):
        res = VideoResolution(width=3840, height=2160)
        assert res.label == "4K"

    def test_label_720p(self):
        res = VideoResolution(width=1280, height=720)
        assert res.label == "720p"

    def test_label_480p(self):
        res = VideoResolution(width=854, height=480)
        assert res.label == "480p"

    def test_label_small(self):
        res = VideoResolution(width=320, height=240)
        assert res.label == "240p"

    def test_str(self):
        res = VideoResolution(width=1920, height=1080)
        assert str(res) == "1920x1080"


# --- VideoMetadata ---


class TestVideoMetadata:
    def test_basic_metadata(self):
        vid = _make_video()
        assert vid.filename == "test_exhaust.mp4"
        assert vid.duration_seconds == 30.0
        assert vid.fps == 30.0
        assert vid.format == VideoFormat.MP4

    def test_total_frames(self):
        vid = _make_video(duration=10.0, fps=30.0)
        assert vid.total_frames == 300

    def test_file_size_mb(self):
        vid = _make_video(file_size=10_485_760)  # Exactly 10 MB
        assert abs(vid.file_size_mb - 10.0) < 0.001

    def test_bitrate(self):
        vid = _make_video(duration=10.0, file_size=1_000_000)
        expected_kbps = (1_000_000 * 8) / (10 * 1000)  # 800 kbps
        assert abs(vid.bitrate_kbps - expected_kbps) < 0.1

    def test_format_enum(self):
        vid = _make_video()
        assert vid.format.value == "mp4"


# --- VideoFrame ---


class TestVideoFrame:
    def test_basic_frame(self):
        frame = VideoFrame(
            frame_number=150,
            timestamp_sec=5.0,
            description="Exhaust pipe visible.",
            tags=["exhaust", "smoke_check"],
        )
        assert frame.frame_number == 150
        assert frame.timestamp_sec == 5.0
        assert "exhaust" in frame.tags

    def test_timestamp_display(self):
        frame = VideoFrame(frame_number=0, timestamp_sec=65.5)
        assert frame.timestamp_display == "01:05.500"

    def test_timestamp_display_short(self):
        frame = VideoFrame(frame_number=0, timestamp_sec=3.25)
        assert frame.timestamp_display == "00:03.250"

    def test_default_description_and_tags(self):
        frame = VideoFrame(frame_number=0, timestamp_sec=0.0)
        assert frame.description == ""
        assert frame.tags == []


# --- FrameExtractionConfig ---


class TestFrameExtractionConfig:
    def test_defaults(self):
        config = FrameExtractionConfig()
        assert config.interval_seconds == 1.0
        assert config.max_frames == 30
        assert config.start_time_sec == 0.0
        assert config.end_time_sec is None

    def test_effective_end_time_none(self):
        config = FrameExtractionConfig()
        assert config.effective_end_time(60.0) == 60.0

    def test_effective_end_time_clamped(self):
        config = FrameExtractionConfig(end_time_sec=100.0)
        assert config.effective_end_time(45.0) == 45.0

    def test_effective_end_time_within_video(self):
        config = FrameExtractionConfig(end_time_sec=20.0)
        assert config.effective_end_time(60.0) == 20.0


# --- SceneChangeMarker ---


class TestSceneChangeMarker:
    def test_basic_marker(self):
        marker = SceneChangeMarker(
            timestamp_sec=5.0,
            change_score=0.8,
            change_type="cut",
        )
        assert marker.timestamp_sec == 5.0
        assert marker.change_score == 0.8
        assert marker.change_type == "cut"


# --- VideoFrameExtractor: extract_frames ---


class TestExtractFrames:
    def test_basic_extraction(self):
        vid = _make_video(duration=10.0, fps=30.0)
        extractor = VideoFrameExtractor(FrameExtractionConfig(interval_seconds=2.0, max_frames=100))
        frames = extractor.extract_frames(vid)
        # At 2s intervals over 10s: 0, 2, 4, 6, 8 = 5 frames
        assert len(frames) == 5

    def test_max_frames_cap(self):
        vid = _make_video(duration=60.0, fps=30.0)
        extractor = VideoFrameExtractor(FrameExtractionConfig(interval_seconds=1.0, max_frames=10))
        frames = extractor.extract_frames(vid)
        assert len(frames) == 10

    def test_frame_numbers_increase(self):
        vid = _make_video(duration=10.0, fps=30.0)
        extractor = VideoFrameExtractor(FrameExtractionConfig(interval_seconds=2.0, max_frames=100))
        frames = extractor.extract_frames(vid)
        for i in range(1, len(frames)):
            assert frames[i].frame_number > frames[i - 1].frame_number

    def test_timestamps_match_interval(self):
        vid = _make_video(duration=10.0, fps=30.0)
        config = FrameExtractionConfig(interval_seconds=3.0, max_frames=100)
        extractor = VideoFrameExtractor(config)
        frames = extractor.extract_frames(vid)
        expected_ts = [0.0, 3.0, 6.0, 9.0]
        assert [f.timestamp_sec for f in frames] == expected_ts

    def test_placeholder_descriptions_populated(self):
        vid = _make_video(duration=5.0)
        extractor = VideoFrameExtractor(FrameExtractionConfig(interval_seconds=1.0))
        frames = extractor.extract_frames(vid)
        for frame in frames:
            assert len(frame.description) > 0

    def test_placeholder_tags_populated(self):
        vid = _make_video(duration=5.0)
        extractor = VideoFrameExtractor(FrameExtractionConfig(interval_seconds=1.0))
        frames = extractor.extract_frames(vid)
        for frame in frames:
            assert len(frame.tags) >= 2  # at least "motorcycle", "diagnostic"
            assert "motorcycle" in frame.tags

    def test_start_time_offset(self):
        vid = _make_video(duration=20.0, fps=30.0)
        config = FrameExtractionConfig(interval_seconds=2.0, start_time_sec=10.0, max_frames=100)
        extractor = VideoFrameExtractor(config)
        frames = extractor.extract_frames(vid)
        assert frames[0].timestamp_sec == 10.0

    def test_end_time_boundary(self):
        vid = _make_video(duration=20.0, fps=30.0)
        config = FrameExtractionConfig(interval_seconds=2.0, end_time_sec=8.0, max_frames=100)
        extractor = VideoFrameExtractor(config)
        frames = extractor.extract_frames(vid)
        for f in frames:
            assert f.timestamp_sec < 8.0

    def test_start_equals_end_raises(self):
        vid = _make_video(duration=10.0)
        config = FrameExtractionConfig(start_time_sec=5.0, end_time_sec=5.0)
        extractor = VideoFrameExtractor(config)
        with pytest.raises(ValueError, match="Start time"):
            extractor.extract_frames(vid)


# --- VideoFrameExtractor: extract_keyframes ---


class TestExtractKeyframes:
    def test_keyframes_with_provided_markers(self):
        vid = _make_video(duration=30.0)
        markers = [
            SceneChangeMarker(timestamp_sec=5.0, change_score=0.8, change_type="cut"),
            SceneChangeMarker(timestamp_sec=10.0, change_score=0.2, change_type="dissolve"),
            SceneChangeMarker(timestamp_sec=15.0, change_score=0.6, change_type="motion_spike"),
        ]
        extractor = VideoFrameExtractor()
        frames = extractor.extract_keyframes(vid, scene_changes=markers, change_threshold=0.5)
        # Only markers with score >= 0.5: 5.0 (0.8) and 15.0 (0.6)
        assert len(frames) == 2
        assert frames[0].timestamp_sec == 5.0
        assert frames[1].timestamp_sec == 15.0

    def test_keyframes_have_keyframe_tag(self):
        vid = _make_video(duration=30.0)
        markers = [SceneChangeMarker(timestamp_sec=5.0, change_score=0.9, change_type="cut")]
        extractor = VideoFrameExtractor()
        frames = extractor.extract_keyframes(vid, scene_changes=markers)
        assert "keyframe" in frames[0].tags
        assert "cut" in frames[0].tags

    def test_keyframes_simulated_when_no_markers(self):
        vid = _make_video(duration=30.0)
        extractor = VideoFrameExtractor()
        frames = extractor.extract_keyframes(vid, change_threshold=0.0)
        assert len(frames) > 0  # Simulated markers at ~5s intervals

    def test_keyframes_max_frames_cap(self):
        vid = _make_video(duration=120.0)
        extractor = VideoFrameExtractor(FrameExtractionConfig(max_frames=3))
        frames = extractor.extract_keyframes(vid, change_threshold=0.0)
        assert len(frames) <= 3

    def test_keyframes_all_below_threshold(self):
        vid = _make_video(duration=30.0)
        markers = [
            SceneChangeMarker(timestamp_sec=5.0, change_score=0.1),
            SceneChangeMarker(timestamp_sec=10.0, change_score=0.05),
        ]
        extractor = VideoFrameExtractor()
        frames = extractor.extract_keyframes(vid, scene_changes=markers, change_threshold=0.5)
        assert len(frames) == 0


# --- VideoFrameExtractor: get_frame_at_timestamp ---


class TestGetFrameAtTimestamp:
    def test_valid_timestamp(self):
        vid = _make_video(duration=30.0, fps=30.0)
        extractor = VideoFrameExtractor()
        frame = extractor.get_frame_at_timestamp(vid, 5.0)
        assert frame.timestamp_sec == 5.0
        assert frame.frame_number == 150  # 5.0 * 30 fps

    def test_negative_timestamp_raises(self):
        vid = _make_video(duration=30.0)
        extractor = VideoFrameExtractor()
        with pytest.raises(ValueError, match="negative"):
            extractor.get_frame_at_timestamp(vid, -1.0)

    def test_beyond_duration_raises(self):
        vid = _make_video(duration=10.0)
        extractor = VideoFrameExtractor()
        with pytest.raises(ValueError, match="exceeds"):
            extractor.get_frame_at_timestamp(vid, 10.0)

    def test_timestamp_zero(self):
        vid = _make_video(duration=10.0, fps=30.0)
        extractor = VideoFrameExtractor()
        frame = extractor.get_frame_at_timestamp(vid, 0.0)
        assert frame.frame_number == 0
        assert frame.timestamp_sec == 0.0


# --- VideoFrameExtractor: get_extraction_plan ---


class TestGetExtractionPlan:
    def test_plan_frame_count(self):
        vid = _make_video(duration=10.0)
        extractor = VideoFrameExtractor(FrameExtractionConfig(interval_seconds=2.0, max_frames=100))
        plan = extractor.get_extraction_plan(vid)
        assert plan["frame_count"] == 5

    def test_plan_coverage_percent(self):
        vid = _make_video(duration=10.0)
        extractor = VideoFrameExtractor(FrameExtractionConfig(start_time_sec=0.0, end_time_sec=5.0))
        plan = extractor.get_extraction_plan(vid)
        assert plan["coverage_percent"] == 50.0

    def test_plan_empty_when_start_after_end(self):
        vid = _make_video(duration=10.0)
        config = FrameExtractionConfig(start_time_sec=15.0)
        extractor = VideoFrameExtractor(config)
        plan = extractor.get_extraction_plan(vid)
        assert plan["frame_count"] == 0

    def test_plan_timestamps_list(self):
        vid = _make_video(duration=6.0)
        config = FrameExtractionConfig(interval_seconds=2.0, max_frames=100)
        extractor = VideoFrameExtractor(config)
        plan = extractor.get_extraction_plan(vid)
        assert plan["timestamps"] == [0.0, 2.0, 4.0]
