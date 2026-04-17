"""Video annotation and timestamping for diagnostic video analysis.

Phase 105: Marks moments in diagnostic video with timestamped annotations.
Supports both AI-generated and mechanic-added annotations with severity levels.
Produces text timelines for CLI display and enables filtering by time range
and severity.

No actual video processing — this module manages annotation metadata that
overlays on video captured by the mobile app or uploaded from file.
"""

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class AnnotationSeverity(str, Enum):
    """Severity level of a video annotation."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AnnotatorType(str, Enum):
    """Who created the annotation."""
    AI = "ai"
    MECHANIC = "mechanic"


class Annotation(BaseModel):
    """A single timestamped annotation on a diagnostic video."""
    annotation_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique annotation identifier.",
    )
    timestamp_sec: float = Field(
        description="Position in the video (seconds from start).",
    )
    label: str = Field(
        description="Short label for the annotation (e.g., 'misfire', 'smoke', 'knock').",
    )
    description: str = Field(
        default="",
        description="Detailed description of what was observed.",
    )
    severity: AnnotationSeverity = Field(
        default=AnnotationSeverity.INFO,
        description="Severity level: info, warning, or critical.",
    )
    annotator: AnnotatorType = Field(
        default=AnnotatorType.MECHANIC,
        description="Who created this annotation: ai or mechanic.",
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Optional tags for categorization (e.g., ['exhaust', 'visual']).",
    )
    confidence: Optional[float] = Field(
        default=None,
        description="AI confidence score (0.0-1.0), None for mechanic annotations.",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When the annotation was created.",
    )


class AnnotatedVideo(BaseModel):
    """A video with its associated annotations, sorted by timestamp."""
    video_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique video identifier.",
    )
    video_metadata: dict = Field(
        default_factory=dict,
        description="Video metadata: filename, duration, resolution, format, etc.",
    )
    annotations: list[Annotation] = Field(
        default_factory=list,
        description="All annotations, maintained in timestamp order.",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When the annotated video record was created.",
    )

    model_config = {"arbitrary_types_allowed": True}

    @property
    def annotation_count(self) -> int:
        return len(self.annotations)

    @property
    def duration_seconds(self) -> Optional[float]:
        return self.video_metadata.get("duration_seconds")

    def _sort_annotations(self) -> None:
        """Sort annotations by timestamp."""
        self.annotations.sort(key=lambda a: a.timestamp_sec)


class VideoAnnotator:
    """Manages annotations on diagnostic video recordings.

    Supports adding, filtering, and generating timelines from video annotations.
    Both AI-generated and mechanic-added annotations are supported.

    Usage:
        annotator = VideoAnnotator()
        video = annotator.create_video(metadata={"filename": "idle_test.mp4", "duration_seconds": 120.0})
        annotator.add_annotation(video, timestamp_sec=15.3, label="smoke", severity="warning")
        timeline = annotator.generate_timeline(video)
    """

    def create_video(self, metadata: Optional[dict] = None) -> AnnotatedVideo:
        """Create a new AnnotatedVideo record.

        Args:
            metadata: Video metadata dict (filename, duration_seconds, resolution, etc.)

        Returns:
            A new AnnotatedVideo instance.
        """
        return AnnotatedVideo(video_metadata=metadata or {})

    def add_annotation(
        self,
        video: AnnotatedVideo,
        timestamp_sec: float,
        label: str,
        description: str = "",
        severity: str = "info",
        annotator: str = "mechanic",
        tags: Optional[list[str]] = None,
        confidence: Optional[float] = None,
    ) -> Annotation:
        """Add a timestamped annotation to the video.

        Args:
            video: The AnnotatedVideo to annotate.
            timestamp_sec: Position in the video (seconds).
            label: Short label for the annotation.
            description: Detailed description.
            severity: One of 'info', 'warning', 'critical'.
            annotator: One of 'ai', 'mechanic'.
            tags: Optional categorization tags.
            confidence: AI confidence score (0.0-1.0).

        Returns:
            The created Annotation.

        Raises:
            ValueError: If timestamp is negative, or if severity/annotator values are invalid.
        """
        if timestamp_sec < 0:
            raise ValueError(f"Timestamp must be non-negative, got {timestamp_sec}")

        duration = video.duration_seconds
        if duration is not None and timestamp_sec > duration:
            raise ValueError(
                f"Timestamp {timestamp_sec}s exceeds video duration {duration}s"
            )

        try:
            sev = AnnotationSeverity(severity)
        except ValueError:
            raise ValueError(
                f"Invalid severity '{severity}'. Must be one of: info, warning, critical"
            )

        try:
            ann_type = AnnotatorType(annotator)
        except ValueError:
            raise ValueError(
                f"Invalid annotator '{annotator}'. Must be one of: ai, mechanic"
            )

        annotation = Annotation(
            timestamp_sec=timestamp_sec,
            label=label,
            description=description,
            severity=sev,
            annotator=ann_type,
            tags=tags or [],
            confidence=confidence,
        )

        video.annotations.append(annotation)
        video._sort_annotations()

        return annotation

    def get_annotations_in_range(
        self,
        video: AnnotatedVideo,
        start_sec: float,
        end_sec: float,
    ) -> list[Annotation]:
        """Get annotations between start and end timestamps (inclusive).

        Args:
            video: The AnnotatedVideo to query.
            start_sec: Start of the time range (seconds).
            end_sec: End of the time range (seconds).

        Returns:
            List of annotations within the range, sorted by timestamp.

        Raises:
            ValueError: If start > end.
        """
        if start_sec > end_sec:
            raise ValueError(f"start_sec ({start_sec}) must be <= end_sec ({end_sec})")

        return [
            a for a in video.annotations
            if start_sec <= a.timestamp_sec <= end_sec
        ]

    def get_critical_moments(
        self,
        video: AnnotatedVideo,
        include_warnings: bool = True,
    ) -> list[Annotation]:
        """Return only warning and/or critical annotations.

        Args:
            video: The AnnotatedVideo to query.
            include_warnings: If True, include both warning and critical. If False, critical only.

        Returns:
            List of high-severity annotations, sorted by timestamp.
        """
        target_severities = {AnnotationSeverity.CRITICAL}
        if include_warnings:
            target_severities.add(AnnotationSeverity.WARNING)

        return [
            a for a in video.annotations
            if a.severity in target_severities
        ]

    def generate_timeline(
        self,
        video: AnnotatedVideo,
        include_descriptions: bool = True,
    ) -> str:
        """Produce a text timeline of all annotations for CLI display.

        Format:
            [MM:SS] [SEVERITY] label — description (annotator)

        Args:
            video: The AnnotatedVideo to render.
            include_descriptions: Whether to include description text.

        Returns:
            Multi-line string timeline.
        """
        if not video.annotations:
            return "No annotations."

        lines = []
        filename = video.video_metadata.get("filename", "Untitled Video")
        duration = video.duration_seconds
        duration_str = f" ({self._format_time(duration)})" if duration else ""
        lines.append(f"Timeline: {filename}{duration_str}")
        lines.append("-" * 60)

        for ann in video.annotations:
            time_str = self._format_time(ann.timestamp_sec)
            sev_str = ann.severity.value.upper()
            annotator_str = f"[{ann.annotator.value}]"

            if include_descriptions and ann.description:
                line = f"[{time_str}] [{sev_str}] {ann.label} -- {ann.description} {annotator_str}"
            else:
                line = f"[{time_str}] [{sev_str}] {ann.label} {annotator_str}"

            lines.append(line)

        lines.append("-" * 60)
        lines.append(
            f"Total: {len(video.annotations)} annotations "
            f"({sum(1 for a in video.annotations if a.severity == AnnotationSeverity.CRITICAL)} critical, "
            f"{sum(1 for a in video.annotations if a.severity == AnnotationSeverity.WARNING)} warning)"
        )

        return "\n".join(lines)

    def auto_annotate(
        self,
        video: AnnotatedVideo,
        analysis_results: list[dict],
    ) -> list[Annotation]:
        """Generate annotations automatically from analysis results.

        Takes a list of analysis result dicts and converts them to annotations.
        Each result dict should contain:
        - timestamp_sec (float): when in the video
        - label (str): what was detected
        - description (str, optional): details
        - severity (str, optional): info/warning/critical (default: info)
        - confidence (float, optional): AI confidence score
        - tags (list[str], optional): categorization tags

        Args:
            video: The AnnotatedVideo to annotate.
            analysis_results: List of analysis result dicts.

        Returns:
            List of created Annotation objects.
        """
        created: list[Annotation] = []

        for result in analysis_results:
            if "timestamp_sec" not in result or "label" not in result:
                continue  # Skip incomplete results

            annotation = self.add_annotation(
                video=video,
                timestamp_sec=result["timestamp_sec"],
                label=result["label"],
                description=result.get("description", ""),
                severity=result.get("severity", "info"),
                annotator="ai",
                tags=result.get("tags", []),
                confidence=result.get("confidence"),
            )
            created.append(annotation)

        return created

    def get_annotations_by_label(
        self,
        video: AnnotatedVideo,
        label: str,
    ) -> list[Annotation]:
        """Get all annotations with a specific label.

        Args:
            video: The AnnotatedVideo to query.
            label: Label to filter by (case-insensitive).

        Returns:
            List of matching annotations.
        """
        label_lower = label.lower()
        return [
            a for a in video.annotations
            if a.label.lower() == label_lower
        ]

    def remove_annotation(
        self,
        video: AnnotatedVideo,
        annotation_id: str,
    ) -> bool:
        """Remove an annotation by its ID.

        Args:
            video: The AnnotatedVideo to modify.
            annotation_id: ID of the annotation to remove.

        Returns:
            True if the annotation was found and removed, False otherwise.
        """
        original_count = len(video.annotations)
        video.annotations = [
            a for a in video.annotations
            if a.annotation_id != annotation_id
        ]
        return len(video.annotations) < original_count

    @staticmethod
    def _format_time(seconds: float) -> str:
        """Format seconds as MM:SS.s"""
        minutes = int(seconds // 60)
        secs = seconds % 60
        return f"{minutes:02d}:{secs:05.2f}"
