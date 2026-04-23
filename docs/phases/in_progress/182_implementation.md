# MotoDiag Phase 182 — PDF Report Generation Endpoints

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-04-22

## Goal

Ship the HTTP surface for **downloadable PDF reports** covering the
three mechanic-facing artifacts customers expect on paper: a
diagnostic session report (what the bike has, what's wrong, what
the recommended repair is), a work-order receipt (intake +
parts + labor + totals + signatures), and an invoice PDF (the
Phase 169 invoice as a branded customer-shareable document).

Mechanic-facing use case: shop closes a WO → mechanic clicks "send
receipt" → the mobile app (Track I) fetches `GET
/v1/reports/work-order/{wo_id}/pdf` and emails the attachment to
the customer. Or: a DIY rider runs a diagnosis, saves the session,
and downloads the session report PDF to keep with their service
records.

CLI — none. Pure HTTP surface.

Outputs (~750 LoC route + renderer + ~30 tests):
- `src/motodiag/reporting/__init__.py` — new package.
- `src/motodiag/reporting/renderers.py` (~350 LoC) — `ReportRenderer`
  ABC + `TextReportRenderer` (always-available fallback) +
  `PdfReportRenderer` (uses `reportlab` which is already installed).
- `src/motodiag/reporting/builders.py` (~200 LoC) — three builders
  that assemble a `ReportDocument` dict from DB rows:
  `build_session_report_doc(session_id, user_id, db_path)`,
  `build_work_order_report_doc(wo_id, user_id, db_path)`,
  `build_invoice_report_doc(invoice_id, user_id, db_path)`.
- `src/motodiag/api/routes/reports.py` (~200 LoC) — 6 endpoints:
  - `GET /v1/reports/session/{id}` → JSON preview (structured dict).
  - `GET /v1/reports/session/{id}/pdf` → `application/pdf` stream.
  - `GET /v1/reports/work-order/{id}` → JSON preview.
  - `GET /v1/reports/work-order/{id}/pdf` → PDF (shop-tier).
  - `GET /v1/reports/invoice/{id}` → JSON preview.
  - `GET /v1/reports/invoice/{id}/pdf` → PDF (shop-tier).
- `src/motodiag/api/app.py` — mount the reports router.
- `tests/test_phase182_reports.py` (~30 tests).
- No migration, no schema change. Schema stays at 38.

## Logic

### Report document shape (shared across renderers)

A `ReportDocument` is a dict with a normalized structure:

```python
{
    "title": "Diagnostic session report #123",
    "subtitle": "Honda CBR600 (2005) — Bob's Cycle Shop",
    "issued_at": "2026-04-22T14:30:00Z",
    "sections": [
        {"heading": "Vehicle", "rows": [("Make", "Honda"), ...]},
        {"heading": "Findings", "body": "...long text..."},
        {"heading": "Parts", "table": {
            "columns": ["Part", "Qty", "Unit $", "Line $"],
            "rows": [[...], [...]],
        }},
        {"heading": "Totals", "rows": [
            ("Subtotal", "$234.50"),
            ("Tax", "$19.36"),
            ("Total", "$253.86"),
        ]},
    ],
    "footer": "MotoDiag v0.12.5 — generated 2026-04-22",
}
```

Renderers take the document and produce output. The JSON preview
endpoint returns the document as-is. The PDF endpoint runs it
through `PdfReportRenderer` and streams the bytes.

### Auth + scoping

- **Session reports** — require a valid API key. Caller must own the
  session (Phase 178 `get_session_for_owner` → 404 on cross-user).
  No subscription tier required (a free DIY user still gets their
  own diagnostic report — this is a core feature).
- **Work-order reports + invoice reports** — require `shop` tier.
  Caller must be a member of the WO's shop (Phase 172
  `require_shop_permission`). Cross-shop = 403.

### Renderer ABC

```python
class ReportRenderer(ABC):
    content_type: str  # e.g. "application/pdf"

    @abstractmethod
    def render(self, doc: ReportDocument) -> bytes: ...
```

- `TextReportRenderer.content_type == "text/plain"` — always works,
  used as a fallback if `reportlab` import fails, and as a
  dev/debug convenience. Uses the same section-walking logic as
  `ReportGenerator.format_text_report` in `media/reports.py` so
  output is consistent.
- `PdfReportRenderer.content_type == "application/pdf"` — builds a
  `SimpleDocTemplate` with a title, section headings, table
  flowables for tabular sections, and a footer. One page per
  ~40 rows; multi-page flow handled by reportlab's Platypus flow.

### Three builders

Each builder returns a `ReportDocument` dict by calling existing
repos:
- `build_session_report_doc(session_id, user_id, db_path)`:
  - `get_session_for_owner(session_id, user_id, db_path)` → 404 if None.
  - Vehicle section: make/model/year (+ optional vehicle_id → Phase
    04 registry lookup for full spec).
  - Symptoms section: bullet list from `symptoms` JSON column.
  - Fault codes: table with code + description from `knowledge/dtc_repo`.
  - Diagnosis: diagnosis + confidence + severity.
  - Repair steps: numbered list.
  - Notes: freeform.

- `build_work_order_report_doc(wo_id, user_id, db_path)`:
  - `require_shop_permission(user_id, shop_id, ...)` gate.
  - Header: WO number, customer name, vehicle, intake date.
  - Issues table: category + severity + description.
  - Parts table: quantity + description + unit cost.
  - Labor: hours + rate + total.
  - Status + assigned mechanic + notes.

- `build_invoice_report_doc(invoice_id, user_id, db_path)`:
  - `require_shop_permission` gate via the WO the invoice belongs to.
  - Reuses Phase 169 `get_invoice_with_items` + renders as a
    customer-shareable document with shop branding (shop name,
    address, phone from Phase 160 shop profile).

### Streaming response

FastAPI's `Response(content=bytes, media_type="application/pdf",
headers={"Content-Disposition": f"attachment; filename=..."})`
keeps the route minimal. No background task needed — the PDF is
small (typically <50KB) and renders in <100ms.

### Rate-limit considerations

PDF generation is CPU-bound. The existing token-bucket rate limiter
(per-minute) already throttles abuse — no extra exemption needed.
PDFs count against the caller's per-minute budget.

## Key Concepts

- **`reportlab.platypus.SimpleDocTemplate`** — one-shot builder that
  takes a flowable list and produces a PDF. Flowables: `Paragraph`
  (styled text), `Spacer` (gap), `Table` (grid), `PageBreak`.
- **`reportlab.platypus.Table`** with `TableStyle` — grid rendering
  with alignment, borders, padding.
- **`reportlab.lib.styles.getSampleStyleSheet`** — default paragraph
  styles (`Title`, `Heading1`, `BodyText`). Customized with
  `ParagraphStyle(parent=...)` for brand consistency.
- **`io.BytesIO`** — SimpleDocTemplate writes to any file-like
  object; in-memory buffer is fastest. `.getvalue()` returns bytes.
- **`fastapi.Response(content=bytes, media_type=...)`** — returns a
  raw bytes response, no JSON serialization. Pair with
  `Content-Disposition: attachment; filename="..."` for browser
  download UX.
- **`reportlab.lib.units.mm`** — unit helper for page measurements.

## Verification Checklist

- [ ] `GET /v1/reports/session/{id}` JSON preview works for owner.
- [ ] Cross-user session → 404.
- [ ] `GET /v1/reports/session/{id}/pdf` streams `application/pdf`.
- [ ] PDF bytes start with `%PDF-` magic.
- [ ] Content-Disposition filename contains the session id.
- [ ] `GET /v1/reports/work-order/{id}/pdf` requires shop tier.
- [ ] Cross-shop WO access → 403.
- [ ] `GET /v1/reports/invoice/{id}/pdf` requires shop tier.
- [ ] Invoice PDF totals match Phase 169 `InvoiceSummary` values.
- [ ] Missing WO → 404.
- [ ] Empty-section reports don't crash (session with no DTCs).
- [ ] `TextReportRenderer` fallback produces parseable text.
- [ ] ReportRenderer ABC rejects unknown renderer types cleanly.
- [ ] Phase 175-181 still GREEN.
- [ ] Zero AI calls.

## Risks

- **reportlab license** — reportlab's open-source edition is BSD-
  licensed for our usage (no commercial restrictions for bundled
  use). Verified.
- **Large report performance** — a WO with 100 parts lines could
  produce a multi-page PDF. Platypus handles pagination
  automatically; worst-case render stays <500ms per report.
- **Encoding edge cases** — customer names with non-ASCII characters
  (é, ñ, 中) need the default reportlab font to handle them. Test
  coverage includes one unicode customer name.
- **PDF-rendering flakiness on CI** — reportlab is deterministic
  given same inputs + font. Tests assert on magic bytes + length
  bounds + presence of substring markers in the text layer, not
  byte-level equality.
