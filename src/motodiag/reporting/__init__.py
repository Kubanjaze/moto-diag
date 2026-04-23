"""Report generation (Phase 182).

Produces downloadable reports in two formats (text + PDF) from a
normalized :class:`ReportDocument` dict assembled by the three
builders in :mod:`motodiag.reporting.builders`.
"""

from motodiag.reporting.renderers import (
    PDF_AVAILABLE,
    PdfReportRenderer,
    ReportRenderer,
    TextReportRenderer,
    get_renderer,
)
from motodiag.reporting.builders import (
    ReportBuildError,
    build_invoice_report_doc,
    build_session_report_doc,
    build_work_order_report_doc,
)


__all__ = [
    "PDF_AVAILABLE",
    "PdfReportRenderer",
    "ReportBuildError",
    "ReportRenderer",
    "TextReportRenderer",
    "build_invoice_report_doc",
    "build_session_report_doc",
    "build_work_order_report_doc",
    "get_renderer",
]
