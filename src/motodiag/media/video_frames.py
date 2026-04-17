"""Video frame extraction for media diagnostics.

Phase 100: Simulated video frame extraction — models video metadata, generates
frame extraction plans based on intervals or keyframe detection, and returns
structured frame objects with placeholder descriptions.

No actual video processing occurs; this module operates on metadata models
to define the extraction contract that a real video backend would fulfill.
Designed for integration with Claude Vision (Phase 101) for visual symptom analysis.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class VideoFormat(str, Enum):
    """Supported video container formats."""
    MP4 = "mp4"
    MOV = "mov"
    AVI = "avi"
    MKV = "mkv"
    WEBM = "webm"


class VideoResolution(BaseModel):
    """Video resolution in pixels."""
    width: int = Field(..., ge=1, description="Width in pixels")
    height: int = Field(..., ge=1, description="Height in pixels")

    @property
    def aspect_ratio(self) -> float:
        """Return aspect ratio (width / height)."""
        return self.width / self.height

    @property
    def label(self) -> str:
        """Human-readable resolution label (e.g., '1080p', '4K')."""
        if self.height >= 2160:
            return "4K"
        elif self.height >= 1440:
            return "1440p"
        elif self.height >= 1080:
            return "1080p"
        elif self.height >= 720:
            return "720p"
        elif self.height >= 480:
            return "480p"
        else:
            return f"{self.height}p"

    def __str__(self) -> str:
        return f"{self.width}x{self.height}"


class VideoMetadata(BaseModel):
    """Metadata describing a video file without loading actual pixel data."""
    filename: str = Field(..., description="Video filename (e.g., 'exhaust_startup.mp4')")
    duration_seconds: float = Field(..., gt=0, description="Total video duration in seconds")
    resolution: VideoResolution = Field(..., description="Video resolution (width x height)")
    fps: float = Field(..., gt=0, description="Frames per second")
    file_size_bytes: int = Field(..., ge=0, description="File size in bytes")
    format: VideoFormat = Field(default=VideoFormat.MP4, description="Video container format")

    @property
    def total_frames(self) -> int:
        """Total number of frames in the video."""
        return int(self.duration_seconds * self.fps)

    @property
    def file_size_mb(self) -> float:
        """File size in megabytes."""
        return self.file_size_bytes / (1024 * 1024)

    @property
    def bitrate_kbps(self) -> float:
        """Approximate bitrate in kilobits per second."""
        if self.duration_seconds <= 0:
            return 0.0
        return (self.file_size_bytes * 8) / (self.duration_seconds * 1000)


class VideoFrame(BaseModel):
    """A single extracted frame from a video.

    In the simulated pipeline, description and tags are placeholders.
    In production, Claude Vision fills these from actual frame image data.
    """
    frame_number: int = Field(..., ge=0, description="Frame index (0-based)")
    timestamp_sec: float = Field(..., ge=0.0, description="Timestamp in seconds")
    description: str = Field(
        default="",
        description="Text description of what is visible in the frame",
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Semantic tags for the frame content (e.g., 'exhaust', 'smoke', 'gauge')",
    )

    @property
    def timestamp_display(self) -> str:
        """Format timestamp as MM:SS.mmm for display."""
        minutes = int(self.timestamp_sec // 60)
        seconds = self.timestamp_sec % 60
        return f"{minutes:02d}:{seconds:06.3f}"


class FrameExtractionConfig(BaseModel):
    """Configuration for how frames are extracted from video."""
    interval_seconds: float = Field(
        default=1.0,
        gt=0,
        description="Extract one frame every N seconds",
    )
    max_frames: int = Field(
        default=30,
        gt=0,
        description="Maximum number of frames to extract",
    )
    start_time_sec: float = Field(
        default=0.0,
        ge=0.0,
        description="Start extraction from this timestamp",
    )
    end_time_sec: Optional[float] = Field(
        default=None,
        description="Stop extraction at this timestamp (None = end of video)",
    )

    def effective_end_time(self, video_duration: float) -> float:
        """Return the effective end time, clamped to video duration."""
        if self.end_time_sec is not None:
            return min(self.end_time_sec, video_duration)
        return video_duration


class SceneChangeMarker(BaseModel):
    """Marks a detected scene change point in the video timeline.

    Scene changes indicate visually significant transitions — camera moves,
    new angle on the motorcycle, smoke appearance, gauge change, etc.
    """
    timestamp_sec: float = Field(..., ge=0.0, description="Timestamp of the scene change")
    change_score: float = Field(
        ..., ge=0.0, le=1.0,
        description="Magnitude of visual change (0.0 = subtle, 1.0 = complete scene cut)",
    )
    change_type: str = Field(
        default="visual",
        description="Type of change: 'cut', 'dissolve', 'motion_spike', 'visual'",
    )


# --- Placeholder description templates ---

_PLACEHOLDER_DESCRIPTIONS = [
    "Motorcycle visible from {angle} angle. Engine area in frame.",
    "Close-up of {component}. Lighting conditions: {lighting}.",
    "Exhaust pipe visible. No visible smoke at this timestamp.",
    "Dashboard/gauge cluster in frame. Readings partially visible.",
    "Wide shot of motorcycle on stand. Full profile visible.",
    "Mechanic's hand visible near {component}. Work in progress.",
]

_ANGLES = ["left side", "right side", "front", "rear", "top-down", "three-quarter"]
_COMPONENTS = ["exhaust", "engine block", "carburetor", "radiator", "chain", "brakes", "forks"]
_LIGHTING = ["well-lit shop", "outdoor daylight", "dim garage", "fluorescent overhead"]


def _generate_placeholder_description(frame_index: int) -> str:
    """Generate a deterministic placeholder description for a simulated frame."""
    template = _PLACEHOLDER_DESCRIPTIONS[frame_index % len(_PLACEHOLDER_DESCRIPTIONS)]
    angle = _ANGLES[frame_index % len(_ANGLES)]
    component = _COMPONENTS[frame_index % len(_COMPONENTS)]
    lighting = _LIGHTING[frame_index % len(_LIGHTING)]
    return template.format(angle=angle, component=component, lighting=lighting)


def _generate_placeholder_tags(frame_index: int) -> list[str]:
    """Generate deterministic placeholder tags for a simulated frame."""
    base_tags = ["motorcycle", "diagnostic"]
    component_tag = _COMPONENTS[frame_index % len(_COMPONENTS)]
    if frame_index % 5 == 0:
        base_tags.append("smoke_check")
    if frame_index % 7 == 0:
        base_tags.append("fluid_check")
    if frame_index % 3 == 0:
        base_tags.append("gauge_reading")
    base_tags.append(component_tag)
    return base_tags


class VideoFrameExtractor:
    """Extracts frames from video based on time intervals or keyframe detection.

    This is a simulated extractor — it operates on VideoMetadata rather than
    actual video files. Frame descriptions and tags are placeholders that would
    be filled by Claude Vision in production.

    Usage:
        metadata = VideoMetadata(filename="test.mp4", duration_seconds=30, ...)
        extractor = VideoFrameExtractor()
        frames = extractor.extract_frames(metadata)
    """

    def __init__(self, config: Optional[FrameExtractionConfig] = None):
        self.config = config or FrameExtractionConfig()

    def extract_frames(self, video: VideoMetadata) -> list[VideoFrame]:
        """Extract frames at regular intervals from video metadata.

        Generates a frame extraction plan based on config.interval_seconds,
        capped at config.max_frames. Each frame gets a simulated placeholder
        description and tags.

        Args:
            video: Video metadata describing the source file.

        Returns:
            List of VideoFrame objects with timestamps and placeholder content.

        Raises:
            ValueError: If video duration is zero or negative after config bounds.
        """
        start = self.config.start_time_sec
        end = self.config.effective_end_time(video.duration_seconds)

        if start >= end:
            raise ValueError(
                f"Start time ({start}s) must be less than end time ({end}s)"
            )

        timestamps = []
        t = start
        while t < end and len(timestamps) < self.config.max_frames:
            timestamps.append(t)
            t += self.config.interval_seconds

        frames = []
        for i, ts in enumerate(timestamps):
            frame_number = int(ts * video.fps)
            frames.append(VideoFrame(
                frame_number=frame_number,
                timestamp_sec=round(ts, 3),
                description=_generate_placeholder_description(i),
                tags=_generate_placeholder_tags(i),
            ))

        return frames

    def extract_keyframes(
        self,
        video: VideoMetadata,
        scene_changes: Optional[list[SceneChangeMarker]] = None,
        change_threshold: float = 0.3,
    ) -> list[VideoFrame]:
        """Extract frames only at significant scene change points.

        In a real implementation, scene changes would be detected via pixel
        difference analysis. Here, scene changes are provided as input or
        simulated based on video duration.

        Args:
            video: Video metadata.
            scene_changes: Pre-detected scene changes. If None, generates
                simulated changes at ~5-second intervals.
            change_threshold: Minimum change_score to qualify as a keyframe.

        Returns:
            List of VideoFrame objects at keyframe positions.
        """
        if scene_changes is None:
            scene_changes = self._simulate_scene_changes(video)

        # Filter by threshold
        significant = [
            sc for sc in scene_changes
            if sc.change_score >= change_threshold
        ]

        # Apply max_frames cap
        significant = significant[:self.config.max_frames]

        frames = []
        for i, sc in enumerate(significant):
            # Clamp to video duration
            ts = min(sc.timestamp_sec, video.duration_seconds - (1 / video.fps))
            ts = max(0.0, ts)
            frame_number = int(ts * video.fps)

            frames.append(VideoFrame(
                frame_number=frame_number,
                timestamp_sec=round(ts, 3),
                description=f"Keyframe at scene change ({sc.change_type}, "
                            f"score={sc.change_score:.2f}). "
                            + _generate_placeholder_description(i),
                tags=_generate_placeholder_tags(i) + ["keyframe", sc.change_type],
            ))

        return frames

    def get_frame_at_timestamp(
        self,
        video: VideoMetadata,
        timestamp_sec: float,
    ) -> VideoFrame:
        """Get a single frame at a specific timestamp.

        Args:
            video: Video metadata.
            timestamp_sec: Target timestamp in seconds.

        Returns:
            A single VideoFrame at the requested timestamp.

        Raises:
            ValueError: If timestamp is out of video bounds.
        """
        if timestamp_sec < 0:
            raise ValueError(f"Timestamp cannot be negative: {timestamp_sec}")
        if timestamp_sec >= video.duration_seconds:
            raise ValueError(
                f"Timestamp {timestamp_sec}s exceeds video duration "
                f"{video.duration_seconds}s"
            )

        frame_number = int(timestamp_sec * video.fps)
        idx = frame_number  # Use frame number for deterministic placeholder

        return VideoFrame(
            frame_number=frame_number,
            timestamp_sec=round(timestamp_sec, 3),
            description=_generate_placeholder_description(idx),
            tags=_generate_placeholder_tags(idx),
        )

    def get_extraction_plan(self, video: VideoMetadata) -> dict:
        """Return a summary of the extraction plan without extracting frames.

        Useful for previewing how many frames will be extracted and where.

        Args:
            video: Video metadata.

        Returns:
            Dict with plan details: timestamps, frame_count, coverage stats.
        """
        start = self.config.start_time_sec
        end = self.config.effective_end_time(video.duration_seconds)

        if start >= end:
            return {
                "frame_count": 0,
                "timestamps": [],
                "coverage_seconds": 0.0,
                "coverage_percent": 0.0,
            }

        timestamps = []
        t = start
        while t < end and len(timestamps) < self.config.max_frames:
            timestamps.append(round(t, 3))
            t += self.config.interval_seconds

        return {
            "frame_count": len(timestamps),
            "timestamps": timestamps,
            "start_time": start,
            "end_time": end,
            "interval_seconds": self.config.interval_seconds,
            "coverage_seconds": end - start,
            "coverage_percent": round(((end - start) / video.duration_seconds) * 100, 1),
            "video_total_frames": video.total_frames,
            "video_duration": video.duration_seconds,
        }

    def _simulate_scene_changes(self, video: VideoMetadata) -> list[SceneChangeMarker]:
        """Generate simulated scene changes for testing/demo purposes.

        Places scene changes at approximately 5-second intervals with varying
        scores. In production, these would come from actual pixel analysis.
        """
        changes = []
        interval = 5.0
        t = interval
        i = 0
        change_types = ["cut", "dissolve", "motion_spike", "visual"]

        while t < video.duration_seconds:
            # Vary score deterministically
            score = 0.2 + (0.6 * ((i * 7 + 3) % 10) / 10.0)
            score = round(min(1.0, score), 2)

            changes.append(SceneChangeMarker(
                timestamp_sec=round(t, 3),
                change_score=score,
                change_type=change_types[i % len(change_types)],
            ))
            t += interval
            i += 1

        return changes
