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
# HTML renderer (Phase 200 — customer-facing share view)
# ---------------------------------------------------------------------------

from html import escape as _escape  # noqa: E402  (kept beside its user)


def _e(value: object) -> str:
    """Escape any value for HTML text content.

    EVERY interpolation in this renderer goes through here. The page is
    served to an unauthenticated browser and the document carries
    mechanic-authored free text (symptoms, notes, vehicle strings), so
    escaping is a correctness requirement, not a nicety.
    """
    return _escape(str(value), quote=True)


#: Inline, dependency-free stylesheet. No external assets by design:
#: the page must render on a customer's phone on shop wifi, offline
#: caches, or a forwarded email preview, with nothing to block.
_SHARE_CSS = """
:root { color-scheme: light dark; }
* { box-sizing: border-box; }
body {
  margin: 0; padding: 24px 16px 64px;
  font: 16px/1.55 -apple-system, BlinkMacSystemFont, "Segoe UI",
        Roboto, Helvetica, Arial, sans-serif;
  color: #16181d; background: #f7f8fa;
}
main { max-width: 46rem; margin: 0 auto; }
header { margin-bottom: 28px; }
h1 { font-size: 1.5rem; line-height: 1.25; margin: 0 0 6px; }
.subtitle { font-size: 1.05rem; color: #4a5160; margin: 0 0 4px; }
.issued { font-size: .85rem; color: #6b7280; margin: 0; }
section {
  background: #fff; border: 1px solid #e3e6eb; border-radius: 10px;
  padding: 16px 18px; margin: 0 0 14px;
}
h2 { font-size: 1.05rem; margin: 0 0 10px; letter-spacing: .01em; }
dl { margin: 0; display: grid; grid-template-columns: minmax(8rem, 34%) 1fr; gap: 6px 14px; }
dt { color: #6b7280; }
dd { margin: 0; }
ul { margin: 0; padding-left: 1.15rem; }
li { margin-bottom: 4px; }
p { margin: 0 0 8px; }
p:last-child { margin-bottom: 0; }
.tablewrap { overflow-x: auto; }
table { border-collapse: collapse; width: 100%; font-size: .95rem; }
th, td { text-align: left; padding: 7px 10px; border-bottom: 1px solid #eceff3; }
th { color: #4a5160; font-weight: 600; }
.video { border-top: 1px solid #eceff3; padding-top: 10px; margin-top: 10px; }
.video:first-child { border-top: 0; padding-top: 0; margin-top: 0; }
.video h3 { font-size: .95rem; margin: 0 0 6px; }
footer { margin-top: 26px; font-size: .82rem; color: #6b7280; text-align: center; }
@media (prefers-color-scheme: dark) {
  body { color: #e6e8ec; background: #14161a; }
  section { background: #1c1f25; border-color: #2b2f37; }
  .subtitle { color: #a9b1bf; }
  .issued, dt, th, footer { color: #8d95a3; }
  th, td { border-bottom-color: #2b2f37; }
  .video { border-top-color: #2b2f37; }
}
@media print {
  body { background: #fff; padding: 0; }
  section { border-color: #ccc; break-inside: avoid; }
}
"""


class HtmlReportRenderer(ReportRenderer):
    """Standalone HTML page for the Phase 200 customer share view.

    Renders the same :class:`ReportDocument` the PDF and text renderers
    consume, so the five section variants stay switched in one place
    across every output kind. A template engine (jinja2) would be
    over-architecture for one document and a new dependency for a route
    that must never fail to render.
    """

    content_type = "text/html; charset=utf-8"
    file_extension = "html"

    def render(self, doc: ReportDocument) -> bytes:
        title = doc.get("title") or "Report"
        parts: list[str] = [
            "<!doctype html>",
            '<html lang="en"><head><meta charset="utf-8">',
            '<meta name="viewport" content="width=device-width, '
            'initial-scale=1">',
            # Customer reports are private documents reached by an
            # unguessable link; keep them out of search indexes.
            '<meta name="robots" content="noindex, nofollow">',
            f"<title>{_e(title)}</title>",
            f"<style>{_SHARE_CSS}</style>",
            "</head><body><main>",
            "<header>",
            f"<h1>{_e(title)}</h1>",
        ]
        subtitle = doc.get("subtitle")
        if subtitle:
            parts.append(f'<p class="subtitle">{_e(subtitle)}</p>')
        issued_at = doc.get("issued_at")
        if issued_at:
            parts.append(f'<p class="issued">Issued {_e(issued_at)}</p>')
        parts.append("</header>")

        for section in doc.get("sections") or []:
            parts.append("<section>")
            heading = section.get("heading")
            if heading:
                parts.append(f"<h2>{_e(heading)}</h2>")
            parts.append(self._render_section(section))
            parts.append("</section>")

        footer = doc.get("footer")
        if footer:
            parts.append(f"<footer>{_e(footer)}</footer>")
        parts.append("</main></body></html>")
        return "\n".join(parts).encode("utf-8")

    def _render_section(self, section: dict) -> str:
        # Variant order mirrors TextReportRenderer.render so the two
        # cannot drift on which key wins when a section carries more
        # than one (it should not, per the shape doc).
        if "body" in section:
            body = str(section.get("body") or "")
            paragraphs = [p for p in body.split("\n") if p.strip()]
            return "".join(f"<p>{_e(p)}</p>" for p in paragraphs)
        if "rows" in section:
            cells: list[str] = []
            for pair in section.get("rows") or []:
                key, value = pair[0], pair[1]
                cells.append(f"<dt>{_e(key)}</dt><dd>{_e(value)}</dd>")
            return f"<dl>{''.join(cells)}</dl>" if cells else ""
        if "bullets" in section:
            items = "".join(
                f"<li>{_e(b)}</li>" for b in section.get("bullets") or []
            )
            return f"<ul>{items}</ul>" if items else ""
        if "table" in section:
            table = section.get("table") or {}
            columns = table.get("columns") or []
            rows = table.get("rows") or []
            head = "".join(f"<th>{_e(c)}</th>" for c in columns)
            body = "".join(
                "<tr>" + "".join(f"<td>{_e(cell)}</td>" for cell in row)
                + "</tr>"
                for row in rows
            )
            return (
                '<div class="tablewrap"><table>'
                + (f"<thead><tr>{head}</tr></thead>" if head else "")
                + f"<tbody>{body}</tbody></table></div>"
            )
        if "videos" in section:
            # Customer-facing: recording metadata only. Video BYTES are
            # never exposed through the public share route — the token
            # grants the report, not the media.
            blocks: list[str] = []
            for idx, video in enumerate(section.get("videos") or [], 1):
                rows = [
                    ("Captured", video.get("captured_at", "—")),
                    ("Duration (ms)", video.get("duration_ms", 0)),
                    ("Analysis", video.get("analysis_state", "pending")),
                ]
                cells = "".join(
                    f"<dt>{_e(k)}</dt><dd>{_e(v)}</dd>" for k, v in rows
                )
                fname = video.get("filename") or "—"
                blocks.append(
                    f'<div class="video"><h3>Recording {idx} '
                    f"({_e(fname)})</h3><dl>{cells}</dl></div>"
                )
            return "".join(blocks)
        return ""


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
    - ``"html"`` → :class:`HtmlReportRenderer`. Always works;
      standalone page for the Phase 200 customer share view.
    - ``"text"`` → :class:`TextReportRenderer`. Always works.
      ``deterministic`` is silently ignored (text renderer is
      already deterministic by construction).
    """
    if kind == "pdf":
        return PdfReportRenderer(deterministic=deterministic)
    if kind == "text":
        return TextReportRenderer()
    if kind == "html":
        # Phase 200 — customer share view. Dependency-free, so like
        # ``text`` it always works; ``deterministic`` is meaningless
        # here (no embedded timestamps beyond the document's own).
        return HtmlReportRenderer()
    raise ValueError(
        f"unknown renderer kind: {kind!r} "
        "(expected 'pdf', 'text' or 'html')"
    )
