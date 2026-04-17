"""Media-enhanced diagnostic reports combining evidence from multiple sources.

Phase 106: Assembles comprehensive diagnostic reports that attach audio clips,
video frames, spectrograms, and photos as evidence for diagnostic conclusions.
Produces both detailed text reports for CLI display and brief summaries for
quick review.

Reports are the final output of a diagnostic session — they combine the AI
engine's analysis with the media evidence that supports it.
"""

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class MediaType(str, Enum):
    """Types of media that can be attached to a diagnostic report."""
    AUDIO_CLIP = "audio_clip"
    VIDEO_FRAME = "video_frame"
    SPECTROGRAM = "spectrogram"
    PHOTO = "photo"


class ConfidenceLevel(str, Enum):
    """Qualitative confidence in the diagnosis."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNCERTAIN = "uncertain"


class MediaAttachment(BaseModel):
    """A media file attached as evidence to a diagnostic report."""
    attachment_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique attachment identifier.",
    )
    media_type: MediaType = Field(
        description="Type of media: audio_clip, video_frame, spectrogram, photo.",
    )
    filename: str = Field(
        description="Filename or path of the media file.",
    )
    timestamp: Optional[float] = Field(
        default=None,
        description="Timestamp in the recording this media corresponds to (seconds).",
    )
    description: str = Field(
        default="",
        description="What the media shows or captures.",
    )
    analysis_summary: str = Field(
        default="",
        description="Summary of AI analysis performed on this media.",
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Categorization tags.",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When the attachment was added.",
    )


class DiagnosticReport(BaseModel):
    """A complete diagnostic report with media evidence."""
    report_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique report identifier.",
    )
    vehicle_context: dict = Field(
        default_factory=dict,
        description="Vehicle info: make, model, year, mileage, VIN, etc.",
    )
    symptoms: list[str] = Field(
        default_factory=list,
        description="Reported symptoms that prompted the diagnostic session.",
    )
    diagnosis: str = Field(
        default="",
        description="Primary diagnostic conclusion.",
    )
    diagnosis_details: list[str] = Field(
        default_factory=list,
        description="Detailed diagnostic findings as individual points.",
    )
    confidence: ConfidenceLevel = Field(
        default=ConfidenceLevel.MEDIUM,
        description="Confidence level in the diagnosis.",
    )
    confidence_score: Optional[float] = Field(
        default=None,
        description="Numeric confidence (0.0-1.0) if available.",
    )
    attachments: list[MediaAttachment] = Field(
        default_factory=list,
        description="Media files attached as evidence.",
    )
    recommendations: list[str] = Field(
        default_factory=list,
        description="Recommended actions or repairs.",
    )
    notes: str = Field(
        default="",
        description="Additional mechanic or system notes.",
    )
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When the report was generated.",
    )
    session_id: Optional[str] = Field(
        default=None,
        description="ID of the diagnostic session that produced this report.",
    )

    model_config = {"arbitrary_types_allowed": True}

    @property
    def attachment_count(self) -> int:
        return len(self.attachments)

    @property
    def has_media_evidence(self) -> bool:
        return len(self.attachments) > 0

    def get_attachments_by_type(self, media_type: MediaType) -> list[MediaAttachment]:
        """Return attachments filtered by media type."""
        return [a for a in self.attachments if a.media_type == media_type]


class ReportGenerator:
    """Generates diagnostic reports from analysis results and media evidence.

    Usage:
        gen = ReportGenerator()
        report = gen.generate_report(
            vehicle_context={"make": "Harley-Davidson", "model": "Road King", "year": 2015},
            symptoms=["rough idle", "popping on deceleration"],
            diagnosis="Lean condition — intake leak suspected",
            confidence="high",
            attachments=[...],
        )
        text = gen.format_text_report(report)
        summary = gen.format_summary(report)
    """

    def generate_report(
        self,
        vehicle_context: Optional[dict] = None,
        symptoms: Optional[list[str]] = None,
        diagnosis: str = "",
        diagnosis_details: Optional[list[str]] = None,
        confidence: str = "medium",
        confidence_score: Optional[float] = None,
        attachments: Optional[list[MediaAttachment]] = None,
        recommendations: Optional[list[str]] = None,
        notes: str = "",
        session_id: Optional[str] = None,
    ) -> DiagnosticReport:
        """Assemble a comprehensive diagnostic report.

        Args:
            vehicle_context: Vehicle info dict.
            symptoms: List of reported symptoms.
            diagnosis: Primary diagnostic conclusion.
            diagnosis_details: Detailed findings.
            confidence: Confidence level (high/medium/low/uncertain).
            confidence_score: Numeric confidence (0.0-1.0).
            attachments: Media attachments.
            recommendations: Recommended actions.
            notes: Additional notes.
            session_id: Diagnostic session ID.

        Returns:
            A fully assembled DiagnosticReport.

        Raises:
            ValueError: If confidence value is invalid.
        """
        try:
            conf_level = ConfidenceLevel(confidence)
        except ValueError:
            raise ValueError(
                f"Invalid confidence '{confidence}'. "
                f"Must be one of: high, medium, low, uncertain"
            )

        return DiagnosticReport(
            vehicle_context=vehicle_context or {},
            symptoms=symptoms or [],
            diagnosis=diagnosis,
            diagnosis_details=diagnosis_details or [],
            confidence=conf_level,
            confidence_score=confidence_score,
            attachments=attachments or [],
            recommendations=recommendations or [],
            notes=notes,
            session_id=session_id,
        )

    def add_attachment(
        self,
        report: DiagnosticReport,
        media_type: str,
        filename: str,
        timestamp: Optional[float] = None,
        description: str = "",
        analysis_summary: str = "",
        tags: Optional[list[str]] = None,
    ) -> MediaAttachment:
        """Add a media attachment to an existing report.

        Args:
            report: The report to add the attachment to.
            media_type: Type of media (audio_clip, video_frame, spectrogram, photo).
            filename: Path or name of the media file.
            timestamp: When in the recording this corresponds to.
            description: What the media shows.
            analysis_summary: AI analysis summary.
            tags: Categorization tags.

        Returns:
            The created MediaAttachment.

        Raises:
            ValueError: If media_type is invalid.
        """
        try:
            mt = MediaType(media_type)
        except ValueError:
            raise ValueError(
                f"Invalid media_type '{media_type}'. "
                f"Must be one of: audio_clip, video_frame, spectrogram, photo"
            )

        attachment = MediaAttachment(
            media_type=mt,
            filename=filename,
            timestamp=timestamp,
            description=description,
            analysis_summary=analysis_summary,
            tags=tags or [],
        )

        report.attachments.append(attachment)
        return attachment

    def format_text_report(self, report: DiagnosticReport) -> str:
        """Generate a plain-text version of the report for CLI display.

        Args:
            report: The diagnostic report to format.

        Returns:
            Multi-line formatted text report.
        """
        lines: list[str] = []
        sep = "=" * 70

        # Header
        lines.append(sep)
        lines.append("DIAGNOSTIC REPORT")
        lines.append(sep)
        lines.append(f"Report ID: {report.report_id}")
        lines.append(f"Generated: {report.generated_at.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        if report.session_id:
            lines.append(f"Session ID: {report.session_id}")
        lines.append("")

        # Vehicle
        if report.vehicle_context:
            lines.append("VEHICLE:")
            for key, value in report.vehicle_context.items():
                lines.append(f"  {key}: {value}")
            lines.append("")

        # Symptoms
        if report.symptoms:
            lines.append("REPORTED SYMPTOMS:")
            for i, symptom in enumerate(report.symptoms, 1):
                lines.append(f"  {i}. {symptom}")
            lines.append("")

        # Diagnosis
        lines.append("DIAGNOSIS:")
        lines.append(f"  {report.diagnosis or 'No diagnosis recorded.'}")
        conf_str = report.confidence.value.upper()
        if report.confidence_score is not None:
            conf_str += f" ({report.confidence_score:.0%})"
        lines.append(f"  Confidence: {conf_str}")
        lines.append("")

        # Diagnosis details
        if report.diagnosis_details:
            lines.append("FINDINGS:")
            for i, detail in enumerate(report.diagnosis_details, 1):
                lines.append(f"  {i}. {detail}")
            lines.append("")

        # Media evidence
        if report.attachments:
            lines.append(f"MEDIA EVIDENCE ({report.attachment_count} attachments):")
            for i, att in enumerate(report.attachments, 1):
                ts_str = f" @ {att.timestamp:.1f}s" if att.timestamp is not None else ""
                lines.append(f"  {i}. [{att.media_type.value}] {att.filename}{ts_str}")
                if att.description:
                    lines.append(f"     Description: {att.description}")
                if att.analysis_summary:
                    lines.append(f"     Analysis: {att.analysis_summary}")
            lines.append("")

        # Recommendations
        if report.recommendations:
            lines.append("RECOMMENDATIONS:")
            for i, rec in enumerate(report.recommendations, 1):
                lines.append(f"  {i}. {rec}")
            lines.append("")

        # Notes
        if report.notes:
            lines.append("NOTES:")
            lines.append(f"  {report.notes}")
            lines.append("")

        lines.append(sep)
        return "\n".join(lines)

    def format_summary(self, report: DiagnosticReport) -> str:
        """Generate a brief one-paragraph summary of the report.

        Args:
            report: The diagnostic report to summarize.

        Returns:
            Single-paragraph summary string.
        """
        # Vehicle context
        make = report.vehicle_context.get("make", "")
        model = report.vehicle_context.get("model", "")
        year = report.vehicle_context.get("year", "")
        vehicle_str = " ".join(filter(None, [str(year), make, model])).strip()
        vehicle_str = vehicle_str or "Unknown vehicle"

        # Symptoms
        if report.symptoms:
            symptom_str = ", ".join(report.symptoms[:3])
            if len(report.symptoms) > 3:
                symptom_str += f" (+{len(report.symptoms) - 3} more)"
        else:
            symptom_str = "no specific symptoms reported"

        # Diagnosis
        diag_str = report.diagnosis or "No diagnosis reached"

        # Confidence
        conf_str = report.confidence.value
        if report.confidence_score is not None:
            conf_str += f" ({report.confidence_score:.0%})"

        # Evidence
        evidence_parts = []
        for mt in MediaType:
            count = len(report.get_attachments_by_type(mt))
            if count > 0:
                evidence_parts.append(f"{count} {mt.value.replace('_', ' ')}(s)")
        evidence_str = ", ".join(evidence_parts) if evidence_parts else "no media evidence"

        return (
            f"{vehicle_str} presented with {symptom_str}. "
            f"Diagnosis ({conf_str} confidence): {diag_str}. "
            f"Evidence: {evidence_str}."
        )

    def merge_reports(
        self,
        reports: list[DiagnosticReport],
        merged_diagnosis: Optional[str] = None,
    ) -> DiagnosticReport:
        """Merge multiple reports into a single comprehensive report.

        Combines symptoms, attachments, recommendations, and diagnosis details
        from all provided reports. Useful when multiple diagnostic sessions
        investigated the same vehicle.

        Args:
            reports: List of reports to merge.
            merged_diagnosis: Override diagnosis for the merged report.

        Returns:
            A new DiagnosticReport combining all inputs.

        Raises:
            ValueError: If no reports provided.
        """
        if not reports:
            raise ValueError("At least one report is required to merge.")

        all_symptoms: list[str] = []
        all_details: list[str] = []
        all_attachments: list[MediaAttachment] = []
        all_recommendations: list[str] = []
        all_notes: list[str] = []

        # Use the first report's vehicle context (they should all be the same vehicle)
        vehicle_context = reports[0].vehicle_context.copy()

        for r in reports:
            for s in r.symptoms:
                if s not in all_symptoms:
                    all_symptoms.append(s)
            for d in r.diagnosis_details:
                if d not in all_details:
                    all_details.append(d)
            all_attachments.extend(r.attachments)
            for rec in r.recommendations:
                if rec not in all_recommendations:
                    all_recommendations.append(rec)
            if r.notes:
                all_notes.append(r.notes)

        # Use the highest confidence from any report
        confidence_order = [
            ConfidenceLevel.HIGH,
            ConfidenceLevel.MEDIUM,
            ConfidenceLevel.LOW,
            ConfidenceLevel.UNCERTAIN,
        ]
        best_confidence = ConfidenceLevel.UNCERTAIN
        best_score: Optional[float] = None
        for r in reports:
            if confidence_order.index(r.confidence) < confidence_order.index(best_confidence):
                best_confidence = r.confidence
                best_score = r.confidence_score

        diagnosis = merged_diagnosis or reports[-1].diagnosis

        return DiagnosticReport(
            vehicle_context=vehicle_context,
            symptoms=all_symptoms,
            diagnosis=diagnosis,
            diagnosis_details=all_details,
            confidence=best_confidence,
            confidence_score=best_score,
            attachments=all_attachments,
            recommendations=all_recommendations,
            notes=" | ".join(all_notes) if all_notes else "",
        )
