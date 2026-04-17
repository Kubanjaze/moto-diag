"""Phase 132 — Shared HTML + PDF export helpers.

This module provides the small, reusable conversion layer that both
``motodiag diagnose show`` and ``motodiag kb show`` call when a mechanic
picks ``--format html`` or ``--format pdf``. The pivot format for both
outputs is **markdown**: each caller produces a markdown string (via its
existing ``_format_*_md`` helper) and hands it here to be wrapped in a
printable HTML5 document or rendered to PDF bytes.

Design choices:

* **Markdown-as-pivot** — HTML = markdown + inline CSS; PDF = HTML +
  page layout. Any future format (DOCX, EPUB, …) would hook in at the
  same junction.
* **Optional deps** — ``markdown`` and ``xhtml2pdf`` are installed via
  the ``motodiag[export]`` extra. Core-only users never pay the import
  cost and get a clear, actionable error if they try HTML/PDF without
  installing the extra.
* **Inline CSS** — the HTML wrapper embeds its stylesheet so the file
  is self-contained (emailable, printable, archivable) with no external
  asset fetches.
* **``xhtml2pdf`` over ``weasyprint``** — pure Python, cross-platform,
  no native dependency on Cairo/Pango. Nicer typography is a
  future-phase concern.
* **``write_binary`` mirrors Phase 126's ``_write_report_to_file``** —
  same overwrite-confirm / parent-dir / permission semantics, just for
  ``bytes`` instead of ``str``.

All public helpers raise ``click.ClickException`` on user-visible
errors so the CLI exits non-zero with a single-line message instead of
a traceback.
"""

from __future__ import annotations

import io
import os
from pathlib import Path
from typing import Any

import click


# --- Minimal inline stylesheet for the HTML wrapper ----------------------
#
# Intentionally small and print-friendly: serif body, readable margins,
# table borders, padded headers. Works inside xhtml2pdf (no flexbox,
# no CSS3 features beyond what pisa supports).

_HTML_CSS = """
@page {
    size: letter;
    margin: 0.75in;
}
body {
    font-family: "Georgia", "Times New Roman", serif;
    font-size: 11pt;
    line-height: 1.4;
    color: #222;
    margin: 1em;
}
h1 {
    font-size: 20pt;
    border-bottom: 2px solid #444;
    padding-bottom: 0.2em;
    margin-bottom: 0.6em;
}
h2 {
    font-size: 14pt;
    color: #333;
    padding-top: 0.3em;
    margin-top: 0.8em;
    margin-bottom: 0.3em;
}
h3 {
    font-size: 12pt;
    color: #444;
}
p {
    margin: 0.4em 0;
}
ul, ol {
    margin: 0.3em 0 0.6em 1.2em;
}
li {
    margin-bottom: 0.15em;
}
table {
    border-collapse: collapse;
    margin: 0.4em 0;
    width: 100%;
}
th, td {
    border: 1px solid #888;
    padding: 4px 8px;
    text-align: left;
    vertical-align: top;
}
th {
    background-color: #eee;
    font-weight: bold;
}
code {
    font-family: "Courier New", monospace;
    background-color: #f4f4f4;
    padding: 1px 3px;
    border-radius: 2px;
}
""".strip()


# --- Lazy-import guards --------------------------------------------------


def _ensure_markdown_installed() -> Any:
    """Import ``markdown`` or raise ClickException with an install hint.

    Lazy-imported so core users who never call HTML/PDF pay zero import
    cost. Returns the module so the caller can invoke ``markdown.markdown(...)``.
    """
    try:
        import markdown as md
    except ImportError as e:  # pragma: no cover — covered via monkeypatch
        raise click.ClickException(
            "HTML/PDF export requires the optional 'markdown' package. "
            "Install with: pip install 'motodiag[export]'"
        ) from e
    return md


def _ensure_pdf_installed() -> Any:
    """Import ``xhtml2pdf.pisa`` or raise ClickException with install hint."""
    try:
        from xhtml2pdf import pisa
    except ImportError as e:  # pragma: no cover — covered via monkeypatch
        raise click.ClickException(
            "PDF export requires the optional 'xhtml2pdf' package. "
            "Install with: pip install 'motodiag[export]'"
        ) from e
    return pisa


# --- HTML rendering ------------------------------------------------------


def _build_html_document(title: str, body_md: str) -> str:
    """Wrap markdown-converted HTML in a printable HTML5 document.

    - Converts ``body_md`` via ``markdown.markdown`` with the ``tables``
      extension enabled so GitHub-style tables render as ``<table>``.
    - Embeds the full stylesheet inline (no external resources).
    - Escapes the title for the ``<title>`` tag — the body markdown is
      treated as trusted input (mechanic-authored or diagnosis output).

    Always returns a valid ``<!DOCTYPE html>…</html>`` string.
    """
    md = _ensure_markdown_installed()
    body_html = md.markdown(body_md, extensions=["tables"])

    # Minimal HTML entity escape for the <title> element. The body is
    # already HTML-escaped by the markdown renderer.
    safe_title = (
        title
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )

    return (
        "<!DOCTYPE html>\n"
        "<html lang=\"en\">\n"
        "<head>\n"
        "    <meta charset=\"utf-8\">\n"
        f"    <title>{safe_title}</title>\n"
        "    <style type=\"text/css\">\n"
        f"{_HTML_CSS}\n"
        "    </style>\n"
        "</head>\n"
        "<body>\n"
        f"{body_html}\n"
        "</body>\n"
        "</html>\n"
    )


def format_as_html(title: str, body_md: str) -> str:
    """Public: convert (title, markdown body) → full HTML5 document string.

    Raises ClickException if the ``markdown`` package is not installed.
    """
    return _build_html_document(title, body_md)


# --- PDF rendering -------------------------------------------------------


def format_as_pdf(title: str, body_md: str) -> bytes:
    """Public: convert (title, markdown body) → PDF bytes.

    Pipeline: markdown → HTML (via ``format_as_html``) → PDF (via
    ``xhtml2pdf.pisa.CreatePDF``). Returns raw PDF bytes ready for
    ``write_binary``.

    Raises ClickException on conversion errors (e.g., unsupported CSS)
    and on missing ``xhtml2pdf`` install.
    """
    html = format_as_html(title=title, body_md=body_md)
    pisa = _ensure_pdf_installed()

    buf = io.BytesIO()
    # ``CreatePDF`` returns a ``pisaStatus`` object with an ``err`` count.
    pisa_status = pisa.CreatePDF(src=html, dest=buf)
    if pisa_status.err:
        raise click.ClickException(
            f"PDF generation failed with {pisa_status.err} error(s). "
            "Check the input markdown for unsupported HTML/CSS."
        )
    return buf.getvalue()


# --- Binary file writer --------------------------------------------------


def write_binary(path: Path, data: bytes, overwrite_confirmed: bool) -> None:
    """Write ``data`` (bytes) to ``path`` with the same safety net as
    Phase 126's text writer.

    - If ``path`` is an existing directory → ClickException.
    - If ``path`` exists as a file and ``overwrite_confirmed`` is False
      → prompts via ``click.confirm`` and raises ``click.Abort`` on 'n'.
    - Creates parent directories as needed.
    - ``PermissionError`` / ``IsADirectoryError`` → ClickException with
      a friendly single-line message.
    """
    p = Path(path)
    path_str = str(p)

    # Directory-as-output guard must precede anything that would create a
    # parent directory (otherwise the error surfaces as a confusing
    # "file exists" instead of the actual mistake).
    if p.is_dir():
        raise click.ClickException(
            f"Output path is a directory, not a file: {path_str}"
        )

    if p.exists() and not overwrite_confirmed:
        if not click.confirm(
            f"File exists: {path_str}. Overwrite?", default=False
        ):
            raise click.Abort()

    parent = p.parent
    # ``Path("file.pdf").parent`` is ``Path('.')`` which already exists;
    # explicit check keeps the intent readable.
    if str(parent) and not parent.exists():
        try:
            os.makedirs(parent, exist_ok=True)
        except PermissionError as e:
            raise click.ClickException(
                f"Permission denied creating directory {parent}: {e}"
            ) from e

    try:
        with open(path_str, "wb") as f:
            f.write(data)
    except PermissionError as e:
        raise click.ClickException(
            f"Permission denied writing to {path_str}: {e}"
        ) from e
    except IsADirectoryError as e:  # pragma: no cover — covered by is_dir()
        raise click.ClickException(
            f"Output path is a directory, not a file: {path_str}"
        ) from e
