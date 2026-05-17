"""Report renderers (Phase 182).

Renderers take a normalized :class:`ReportDocument` dict and
produce bytes in the renderer's content-type.

## Renderer contract

A ``ReportDocument`` is a plain dict:

```python
{
    "title": str,
    "subtitle": Optional[str],
    "issued_at": Optional[str],  # ISO 8601
    "sections": list[dict],      # see below
    "footer": Optional[str],
}
```

Each section is one of:
- ``{"heading": str, "body": str}`` — prose block.
- ``{"heading": str, "rows": list[tuple[str, str]]}`` — key/value pairs.
- ``{"heading": str, "bullets": list[str]}`` — bulleted list.
- ``{"heading": str, "table": {"columns": [...], "rows": [[...], ...]}}`` —
  grid rendering.

Renderers walk sections in order. Unknown section shapes are
skipped (forward compat — new section kinds don't break old
renderers).

Two renderers ship in Phase 182:
- :class:`TextReportRenderer` — always works, no deps beyond
  stdlib. Useful as a fallback when reportlab isn't installed and
  as a debug convenience.
- :class:`PdfReportRenderer` — uses reportlab's Platypus flowables.
  reportlab is already a transitive dep (installed in the project
  venv); ``PDF_AVAILABLE`` reports runtime presence.
"""

from __future__ import annotations

import io
from abc import ABC, abstractmethod
from typing import Any


try:  # reportlab ships with the project venv (verified Phase 182 build)
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import LETTER
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        PageBreak,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )
    PDF_AVAILABLE = True
except Exception:  # pragma: no cover — fallback path only
    PDF_AVAILABLE = False


ReportDocument = dict[str, Any]


# ---------------------------------------------------------------------------
# ABC
# ---------------------------------------------------------------------------


class ReportRenderer(ABC):
    """Abstract base for all renderers.

    Subclasses declare a ``content_type`` class-level string and
    implement :meth:`render`.
    """

    content_type: str = "application/octet-stream"
    file_extension: str = "bin"

    @abstractmethod
    def render(self, doc: ReportDocument) -> bytes:
        """Render ``doc`` to bytes in the renderer's content-type."""


# ---------------------------------------------------------------------------
# Text renderer (always works)
# ---------------------------------------------------------------------------


class TextReportRenderer(ReportRenderer):
    """Plain-text renderer — always available, no deps."""

    content_type = "text/plain; charset=utf-8"
    file_extension = "txt"

    def render(self, doc: ReportDocument) -> bytes:
        lines: list[str] = []
        title = doc.get("title") or "Report"
        lines.append(title)
        lines.append("=" * len(title))
        subtitle = doc.get("subtitle")
        if subtitle:
            lines.append(subtitle)
        issued_at = doc.get("issued_at")
        if issued_at:
            lines.append(f"Issued: {issued_at}")
        lines.append("")
        for section in doc.get("sections") or []:
            heading = section.get("heading")
            if heading:
                lines.append(heading)
                lines.append("-" * len(heading))
            if "body" in section:
                body = section.get("body") or ""
                for paragraph in body.split("\n"):
                    lines.append(paragraph)
            elif "rows" in section:
                for key, value in section.get("rows") or []:
                    lines.append(f"  {key}: {value}")
            elif "bullets" in section:
                for bullet in section.get("bullets") or []:
                    lines.append(f"  - {bullet}")
            elif "table" in section:
                table = section.get("table") or {}
                cols = table.get("columns") or []
                rows = table.get("rows") or []
                if cols:
                    lines.append("  " + " | ".join(str(c) for c in cols))
                    lines.append(
                        "  " + "-+-".join("-" * len(str(c)) for c in cols)
                    )
                for r in rows:
                    lines.append(
                        "  " + " | ".join(str(cell) for cell in r)
                    )
            elif "videos" in section:
                # Phase 192 — variant 5. Each video card renders
                # as an indented metadata block; when
                # ``findings`` is present (analysis_state ==
                # 'analyzed') a further-indented findings block
                # follows. Renderers check ``if "findings" in
                # video`` per the shape doc, NOT
                # ``video.get("findings") is not None``.
                videos = section.get("videos") or []
                for idx, video in enumerate(videos, start=1):
                    fname = video.get("filename") or "—"
                    lines.append(f"  Recording {idx} ({fname})")
                    lines.append(
                        f"    Video ID: {video.get('video_id', '—')}"
                    )
                    lines.append(
                        f"    Captured: "
                        f"{video.get('captured_at', '—')}"
                    )
                    lines.append(
                        f"    Duration (ms): "
                        f"{video.get('duration_ms', 0)}"
                    )
                    lines.append(
                        f"    Size (bytes): "
                        f"{video.get('size_bytes', 0)}"
                    )
                    lines.append(
                        f"    Interrupted: "
                        f"{video.get('interrupted', False)}"
                    )
                    lines.append(
                        f"    Analysis state: "
                        f"{video.get('analysis_state', 'pending')}"
                    )
                    lines.append(
                        f"    Analyzing started at: "
                        f"{video.get('analyzing_started_at')}"
                    )
                    if "findings" in video:
                        findings = video["findings"] or {}
                        lines.append("    Findings:")
                        overall = findings.get(
                            "overall_assessment"
                        ) or ""
                        if overall:
                            lines.append(
                                f"      Overall: {overall}"
                            )
                        for f in findings.get("findings") or []:
                            ftype = f.get("finding_type") or "—"
                            desc = f.get("description") or ""
                            sev = f.get("severity") or "—"
                            conf = f.get("confidence")
                            conf_str = (
                                f"{float(conf):.2f}"
                                if conf is not None else "—"
                            )
                            lines.append(
                                f"      - [{ftype} / {sev} / "
                                f"conf {conf_str}] {desc}"
                            )
                        if findings.get("image_quality_note"):
                            lines.append(
                                f"      Image quality: "
                                f"{findings['image_quality_note']}"
                            )
                        if findings.get("frames_analyzed"):
                            lines.append(
                                f"      Frames analyzed: "
                                f"{findings['frames_analyzed']}"
                            )
                        if findings.get("model_used"):
                            lines.append(
                                f"      Model: "
                                f"{findings['model_used']}"
                            )
                        if findings.get("cost_estimate_usd"):
                            lines.append(
                                f"      Cost (USD): "
                                f"{findings['cost_estimate_usd']}"
                            )
                    lines.append("")
            lines.append("")
        footer = doc.get("footer")
        if footer:
            lines.append("-" * 40)
            lines.append(footer)
        return ("\n".join(lines) + "\n").encode("utf-8")


# ---------------------------------------------------------------------------
# PDF renderer
# ---------------------------------------------------------------------------


class PdfReportRenderer(ReportRenderer):
    """reportlab Platypus-based PDF renderer.

    Phase 192B Commit 1.5: opt-in ``deterministic`` mode disables
    reportlab's default non-deterministic metadata embedding
    (``CreationDate`` / ``ModDate`` wall-clock timestamps + random
    trailer ``/ID``). Required for share-flow correctness — two
    shares of the same session+preset must hash identically so
    recipients' deduplication / tampering-detection systems don't
    flag legitimate re-shares as tampering. Default ``False``
    preserves reportlab's spec-compliant default for revision-
    tracking callers (where unique ``/ID`` per render is the spec's
    intent).

    When ``deterministic=True``, ``SimpleDocTemplate(invariant=True)``
    propagates through to ``Canvas(invariant=True)`` →
    ``PDFDocument(invariant=True)`` which zeroes the wall-clock
    timestamps + seeds the trailer ``/ID`` deterministically (via
    ``rl_config.invariant`` global toggle's per-document override).
    """

    content_type = "application/pdf"
    file_extension = "pdf"

    def __init__(self, *, deterministic: bool = False) -> None:
        if not PDF_AVAILABLE:
            raise RuntimeError(
                "reportlab is not installed — PdfReportRenderer is "
                "unavailable. Install reportlab or use "
                "TextReportRenderer."
            )
        self._deterministic = deterministic
        styles = getSampleStyleSheet()
        self._title_style = styles["Title"]
        self._heading_style = ParagraphStyle(
            "MdHeading",
            parent=styles["Heading2"],
            spaceBefore=6 * mm,
            spaceAfter=2 * mm,
        )
        self._body_style = ParagraphStyle(
            "MdBody",
            parent=styles["BodyText"],
            spaceAfter=2 * mm,
        )
        self._subtitle_style = ParagraphStyle(
            "MdSubtitle",
            parent=styles["BodyText"],
            fontSize=11,
            textColor=colors.grey,
            spaceAfter=4 * mm,
        )
        self._footer_style = ParagraphStyle(
            "MdFooter",
            parent=styles["BodyText"],
            fontSize=8,
            textColor=colors.grey,
            alignment=1,  # TA_CENTER
        )

    def render(self, doc: ReportDocument) -> bytes:
        buf = io.BytesIO()
        pdf = SimpleDocTemplate(
            buf,
            pagesize=LETTER,
            title=str(doc.get("title") or "Report"),
            leftMargin=18 * mm, rightMargin=18 * mm,
            topMargin=18 * mm, bottomMargin=18 * mm,
            # Phase 192B Commit 1.5 — opt-in deterministic rendering
            # for share-flow callers. ``invariant=True`` propagates
            # through BaseDocTemplate's _initArgs dict (line ~494
            # in reportlab 4.4.10's doctemplate.py) → Canvas's
            # invariant param (line ~280 in canvas.py) → PDFDocument
            # (line ~118 in pdfdoc.py), which zeroes the
            # CreationDate/ModDate wall-clock timestamps + seeds
            # the trailer /ID deterministically. Default False
            # preserves the spec-compliant non-deterministic
            # default for revision-tracking callers.
            invariant=self._deterministic,
        )
        story: list = []
        story.append(Paragraph(
            _escape(doc.get("title") or "Report"),
            self._title_style,
        ))
        if doc.get("subtitle"):
            story.append(Paragraph(
                _escape(doc["subtitle"]), self._subtitle_style,
            ))
        if doc.get("issued_at"):
            story.append(Paragraph(
                f"Issued: {_escape(doc['issued_at'])}",
                self._subtitle_style,
            ))
        story.append(Spacer(1, 4 * mm))

        for section in doc.get("sections") or []:
            heading = section.get("heading")
            if heading:
                story.append(Paragraph(
                    _escape(heading), self._heading_style,
                ))
            if "body" in section:
                body = section.get("body") or ""
                for para in body.split("\n"):
                    if para.strip():
                        story.append(Paragraph(
                            _escape(para), self._body_style,
                        ))
            elif "rows" in section:
                rows = section.get("rows") or []
                data = [[_escape(str(k)), _escape(str(v))]
                        for k, v in rows]
                if data:
                    story.append(_kv_table(data))
            elif "bullets" in section:
                for bullet in section.get("bullets") or []:
                    story.append(Paragraph(
                        "• " + _escape(str(bullet)), self._body_style,
                    ))
            elif "table" in section:
                table = section.get("table") or {}
                cols = table.get("columns") or []
                rows = table.get("rows") or []
                if cols and rows:
                    story.append(_grid_table(cols, rows))
            elif "videos" in section:
                # Phase 192 — variant 5. Each video card renders
                # as a metadata key/value sub-table; when
                # ``findings`` is present, a nested findings
                # paragraph block follows. Conservative reportlab
                # Platypus shapes (no new flowable types) — reuses
                # ``_kv_table``, ``Paragraph``, ``Spacer``.
                videos = section.get("videos") or []
                for idx, video in enumerate(videos, start=1):
                    fname = video.get("filename") or "—"
                    story.append(Paragraph(
                        f"Recording {idx} ({_escape(fname)})",
                        self._body_style,
                    ))
                    meta_data = [
                        [_escape("Video ID"),
                         _escape(str(video.get("video_id", "—")))],
                        [_escape("Captured"),
                         _escape(str(video.get("captured_at", "—")))],
                        [_escape("Duration (ms)"),
                         _escape(str(video.get("duration_ms", 0)))],
                        [_escape("Size (bytes)"),
                         _escape(str(video.get("size_bytes", 0)))],
                        [_escape("Interrupted"),
                         _escape(str(video.get("interrupted", False)))],
                        [_escape("Analysis state"),
                         _escape(str(
                             video.get("analysis_state", "pending")
                         ))],
                        [_escape("Analyzing started at"),
                         _escape(str(
                             video.get("analyzing_started_at")
                         ))],
                    ]
                    story.append(_kv_table(meta_data))
                    if "findings" in video:
                        findings = video["findings"] or {}
                        story.append(Spacer(1, 1 * mm))
                        story.append(Paragraph(
                            "Findings:", self._body_style,
                        ))
                        overall = findings.get(
                            "overall_assessment"
                        ) or ""
                        if overall:
                            story.append(Paragraph(
                                f"Overall: {_escape(overall)}",
                                self._body_style,
                            ))
                        for f in findings.get("findings") or []:
                            ftype = f.get("finding_type") or "—"
                            desc = f.get("description") or ""
                            sev = f.get("severity") or "—"
                            conf = f.get("confidence")
                            conf_str = (
                                f"{float(conf):.2f}"
                                if conf is not None else "—"
                            )
                            story.append(Paragraph(
                                f"• [{_escape(str(ftype))} / "
                                f"{_escape(str(sev))} / conf "
                                f"{_escape(conf_str)}] "
                                f"{_escape(str(desc))}",
                                self._body_style,
                            ))
                        if findings.get("image_quality_note"):
                            story.append(Paragraph(
                                f"Image quality: "
                                f"{_escape(str(findings['image_quality_note']))}",
                                self._body_style,
                            ))
                        if findings.get("frames_analyzed"):
                            story.append(Paragraph(
                                f"Frames analyzed: "
                                f"{_escape(str(findings['frames_analyzed']))}",
                                self._body_style,
                            ))
                        if findings.get("model_used"):
                            story.append(Paragraph(
                                f"Model: "
                                f"{_escape(str(findings['model_used']))}",
                                self._body_style,
                            ))
                        if findings.get("cost_estimate_usd"):
                            story.append(Paragraph(
                                f"Cost (USD): "
                                f"{_escape(str(findings['cost_estimate_usd']))}",
                                self._body_style,
                            ))
                    story.append(Spacer(1, 2 * mm))
            story.append(Spacer(1, 2 * mm))

        if doc.get("footer"):
            story.append(Spacer(1, 4 * mm))
            story.append(Paragraph(
                _escape(doc["footer"]), self._footer_style,
            ))

        pdf.build(story)
        return buf.getvalue()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _escape(text: Any) -> str:
    """reportlab Paragraph uses XML-style markup; escape angle
    brackets + ampersands so user-provided content doesn't break
    rendering."""
    s = str(text)
    return (
        s.replace("&", "&amp;")
         .replace("<", "&lt;")
         .replace(">", "&gt;")
    )


def _kv_table(data):
    table = Table(data, colWidths=[55 * mm, 110 * mm])
    table.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, -1), "Helvetica", 10),
        ("TEXTCOLOR", (0, 0), (0, -1), colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    return table


def _grid_table(columns, rows):
    header = [str(c) for c in columns]
    body = [[str(cell) for cell in r] for r in rows]
    data = [header] + body
    table = Table(data, repeatRows=1)
    table.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, -1), "Helvetica", 9),
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 9),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return table


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def get_renderer(
    kind: str, *, deterministic: bool = False,
) -> ReportRenderer:
    """Pick a renderer by short name.

    - ``"pdf"`` → :class:`PdfReportRenderer`. Raises ``RuntimeError``
      if reportlab isn't installed. Phase 192B Commit 1.5 added
      the ``deterministic`` opt-in for share-flow callers; default
      ``False`` preserves the historical (spec-compliant non-
      deterministic) behavior.
    - ``"text"`` → :class:`TextReportRenderer`. Always works.
      ``deterministic`` is silently ignored (text renderer is
      already deterministic by construction).
    """
    if kind == "pdf":
        return PdfReportRenderer(deterministic=deterministic)
    if kind == "text":
        return TextReportRenderer()
    raise ValueError(
        f"unknown renderer kind: {kind!r} "
        "(expected 'pdf' or 'text')"
    )
