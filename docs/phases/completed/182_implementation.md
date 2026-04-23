# MotoDiag Phase 182 — PDF Report Generation Endpoints

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-23

## Goal

Ship the HTTP surface for **downloadable PDF reports** covering the
three mechanic-facing artifacts customers expect on paper: a
diagnostic session report (what the bike has, what's wrong, what
the recommended repair is), a work-order receipt (intake + issues
+ parts + labor + status), and an invoice PDF (the Phase 169
invoice rendered as a branded customer-shareable document).

Mechanic-facing use case: shop closes a WO → mechanic clicks "send
receipt" → the mobile app (Track I) fetches `GET
/v1/reports/work-order/{wo_id}/pdf` and emails the attachment to
the customer. Or: a DIY rider runs a diagnosis, saves the session,
and downloads the session report PDF to keep with their service
records.

CLI — none. Pure HTTP surface.

Outputs (962 LoC product code + 593 LoC tests = 1555 net-new):
- `src/motodiag/reporting/__init__.py` (33 LoC) — new package.
- `src/motodiag/reporting/renderers.py` (326 LoC) —
  `ReportRenderer` ABC + `TextReportRenderer` (always-available
  fallback) + `PdfReportRenderer` (reportlab Platypus; already
  installed as a transitive dep at v4.4.10) + `get_renderer`
  factory. `PDF_AVAILABLE` boolean reports runtime presence of
  reportlab.
- `src/motodiag/reporting/builders.py` (473 LoC) — three builders
  that assemble a `ReportDocument` dict from DB rows:
  `build_session_report_doc(session_id, user_id, db_path)`,
  `build_work_order_report_doc(wo_id, user_id, db_path)`,
  `build_invoice_report_doc(invoice_id, user_id, db_path)`. All
  raise domain exceptions (`SessionOwnershipError`,
  `WorkOrderNotFoundError`, `InvoiceNotFoundError`,
  `PermissionDenied`, `ReportBuildError`) which the API error
  handler translates to HTTP status codes.
- `src/motodiag/api/routes/reports.py` (163 LoC) — 6 endpoints:
  - `GET /v1/reports/session/{id}` → JSON preview.
  - `GET /v1/reports/session/{id}/pdf` → PDF download.
  - `GET /v1/reports/work-order/{id}` → JSON preview (shop-tier).
  - `GET /v1/reports/work-order/{id}/pdf` → PDF download (shop-tier).
  - `GET /v1/reports/invoice/{id}` → JSON preview (shop-tier).
  - `GET /v1/reports/invoice/{id}/pdf` → PDF download (shop-tier).
- `src/motodiag/api/app.py` — mount the reports router at `/v1`.
- `src/motodiag/api/errors.py` — new `ReportBuildError` → 500
  mapping.
- `tests/test_phase182_reports.py` (593 LoC, 33 tests across 7
  classes).
- No migration, no schema change. Schema stays at 38.

## Logic

### Report document shape (shared across renderers)

A `ReportDocument` is a plain dict:

```python
{
    "title": str,
    "subtitle": Optional[str],
    "issued_at": Optional[str],       # ISO 8601
    "sections": list[dict],           # see below
    "footer": Optional[str],
}
```

Each section is one of:
- `{"heading": str, "body": str}` — prose block.
- `{"heading": str, "rows": list[tuple[str, str]]}` — key / value
  pairs rendered as a 2-column table.
- `{"heading": str, "bullets": list[str]}` — bulleted list.
- `{"heading": str, "table": {"columns": [...], "rows": [[...]]}}` —
  grid rendering with header row.

Unknown section shapes are skipped — forward-compat guarantee for
future section kinds. Renderers walk sections in order.

### Auth + scoping

- **Session reports** — require a valid API key. Caller must own
  the session (`get_session_for_owner` → 404 on cross-user). No
  subscription tier required: a free DIY user gets their own
  diagnostic report on paper — this is a core product feature, not
  a paid upgrade.
- **Work-order + invoice reports** — require `shop` tier (via
  `require_tier("shop")` dependency) AND active membership in the
  WO's shop (Phase 172 `rbac.get_shop_member` check). Cross-shop
  attempts raise `PermissionDenied` → 403. Missing records raise
  `WorkOrderNotFoundError` / `InvoiceNotFoundError` → 404.

### Renderer ABC

```python
class ReportRenderer(ABC):
    content_type: str
    file_extension: str

    @abstractmethod
    def render(self, doc: ReportDocument) -> bytes: ...
```

- `TextReportRenderer.content_type == "text/plain; charset=utf-8"`
  — always works, stdlib-only.
- `PdfReportRenderer.content_type == "application/pdf"` — builds
  a `SimpleDocTemplate` with a title, section headings, key/value
  tables, bulleted paragraphs, grid tables, and a footer.
  Pagination handled automatically by reportlab's Platypus flow.
  **Critical: user-supplied strings are XML-escaped** before
  passing to `Paragraph` so names with `<`, `>`, or `&` don't
  break the PDF.

### Builders

- **`build_session_report_doc(session_id, user_id, db_path)`**:
  calls `get_session_for_owner` (→ 404 if None), then composes
  sections: Vehicle (make/model/year) + Reported symptoms (bullets,
  omitted when empty) + Fault codes (table with DTC description +
  severity from `dtc_repo.get_dtc`; rows for unknown codes read
  "Unknown DTC") + AI diagnosis (rows: diagnosis + confidence +
  severity + cost estimate, omitted when no diagnosis) +
  Recommended repair steps (bullets, omitted when empty) + Notes
  (body, omitted when empty) + Timeline (status + created/updated/
  closed).

- **`build_work_order_report_doc(wo_id, user_id, db_path)`**: calls
  `get_work_order` (404 if None), resolves `shop_id`, enforces
  membership via `_require_member`. Sections: Shop & customer
  (shop name + customer name/phone/email + vehicle) + Work order
  (number, status, priority, intake, assigned mechanic) +
  Reported problems (from intake) + Issues (table from Phase 162
  `list_issues`) + Parts (table from Phase 165 `list_parts_for_wo`
  with unit / line / status columns) + Labor (rows: estimated +
  actual hours) + Notes.

- **`build_invoice_report_doc(invoice_id, user_id, db_path)`**:
  uses Phase 169 `get_invoice_with_items` (404 if None), resolves
  the WO's shop_id, enforces membership. Sections: From (shop
  name/address/phone via `get_shop`) + Bill to (customer, WO#,
  invoice#, status, issued/due/paid timestamps) + Line items
  (table: type + description + qty + unit + line) + Totals
  (subtotal, tax, total) + Notes.

### Streaming response

`Response(content=bytes, media_type="application/pdf",
headers={"Content-Disposition": f'attachment; filename="..."'})`.
No `StreamingResponse` needed — typical reports are <50KB and
render in <100ms.

### Rate-limit considerations

PDF generation is CPU-bound. The existing token-bucket rate limiter
(per-minute + per-day budgets from Phase 176) already throttles
abuse — no `/v1/reports` exemption. PDFs count against the
caller's per-minute budget.

## Key Concepts

- **`reportlab.platypus.SimpleDocTemplate`** — one-shot builder
  that takes a list of flowables and writes a PDF to any
  file-like object.
- **Platypus flowables**: `Paragraph` (styled text with basic
  XML-style inline markup), `Spacer` (vertical gap), `Table`
  (grid), `PageBreak`.
- **`reportlab.platypus.Table` + `TableStyle`** — grid rendering
  with cell alignment, borders, padding, header-row styling.
  `repeatRows=1` keeps the header on every page in multi-page
  tables.
- **`reportlab.lib.styles.getSampleStyleSheet`** — default style
  registry (`Title`, `Heading1-6`, `BodyText`). Customized via
  `ParagraphStyle(parent=...)` for brand consistency.
- **`io.BytesIO`** — `SimpleDocTemplate` writes to any
  binary-file-like; a memory buffer is fastest.
- **`fastapi.Response(content=bytes, media_type=...)`** — returns
  raw bytes, no JSON serialization. Pair with
  `Content-Disposition: attachment; filename="..."` for browser
  download UX.
- **`reportlab.lib.units.mm`** — typographic unit helper.
- **XML-style Paragraph markup** — reportlab's `Paragraph` accepts
  inline `<b>`, `<i>`, `<font>` tags. User text must be escaped
  (`&` → `&amp;`, `<` → `&lt;`, `>` → `&gt;`) or the PDF build
  can fail.

## Verification Checklist

- [x] `GET /v1/reports/session/{id}` JSON preview works for owner.
- [x] Cross-user session → 404 on preview + PDF.
- [x] Missing session → 404.
- [x] `GET /v1/reports/session/{id}/pdf` streams `application/pdf`.
- [x] PDF bytes start with `%PDF-` magic.
- [x] Content-Disposition filename contains the session id.
- [x] `GET /v1/reports/work-order/{id}` requires shop tier (402
      when tier < shop).
- [x] Cross-shop WO access → 403.
- [x] Missing WO → 404.
- [x] `GET /v1/reports/invoice/{id}/pdf` requires shop tier.
- [x] Cross-shop invoice access → 403.
- [x] Missing invoice → 404.
- [x] Empty-section reports don't crash (session with no DTCs).
- [x] `TextReportRenderer` fallback produces parseable text.
- [x] PDF renderer handles unicode + XML special chars.
- [x] `get_renderer` factory rejects unknown kinds cleanly.
- [x] Unknown section kind is silently skipped (forward compat).
- [x] Phase 175-181 still GREEN — full Track H regression
      (175-182): 248/248 in 6m 36s (396.37s).
- [x] Zero AI calls.

## Risks

- **reportlab license** — reportlab's open-source edition is BSD-
  licensed; bundled use is unrestricted for our purposes. Verified.
- **Large report performance** — a WO with 100 parts lines could
  produce a multi-page PDF. Platypus handles pagination
  automatically; worst-case render stays <500ms per report.
  Memory usage is proportional to content, which for our domain
  is bounded.
- **Encoding edge cases** — tested one unicode customer name
  (`test_pdf_renderer_handles_unicode`). reportlab's default
  Helvetica font covers Latin-1 plus common diacritics (é, ñ, ü)
  but not CJK. When MotoDiag expands to Japanese / Korean fleets,
  a font registration step will be needed. Deferred.
- **PDF-rendering flakiness on CI** — reportlab output includes a
  PDF timestamp; byte-level equality is non-deterministic. Tests
  assert on magic bytes (`%PDF-`) + content-type + presence of
  marker substrings + length bounds, not byte-level equality.

## Deviations from Plan

1. **LoC** — actual 962 LoC product code + 593 LoC tests (1555
   total) vs. the plan's ~750 + ~30 tests. Builders grew because
   session / WO / invoice each needed distinct section shapes with
   defensive handling of optional DB columns. Renderers grew to
   include proper XML escaping and a second (text) renderer for
   dev/debug convenience — the plan only mentioned PDF.

2. **No dedicated `DiagnosticSessionReport` Pydantic model** — the
   plan implied strong typing for the report document. In
   practice a plain dict with documented section shapes keeps the
   renderers + builders decoupled and makes forward-compatibility
   trivial (unknown section kinds are skipped, not rejected). The
   dict-with-schema-in-docstring approach matches Phase 162.5's
   "composable dict" convention for cross-module data.

3. **`TextReportRenderer` shipped alongside `PdfReportRenderer`**
   — the plan mentioned text as a fallback "if reportlab import
   fails". It ships as a first-class renderer anyway: it's useful
   for dev debugging, is exercised in tests
   (`test_text_renderer_basic_output`), and gives future Track I
   mobile clients a lightweight option.

4. **`get_dtc` return-type correction mid-build** — the plan
   assumed `get_dtc` returned a `DTCInfo` object with
   `.description` and `.severity.value`. It actually returns a
   dict. Fixed during build; one-line correction in the session
   builder.

5. **33 tests vs ~30 planned** — three extra unit tests emerged:
   `test_renderer_skips_unknown_section_kind` (forward compat),
   `test_pdf_renderer_escapes_xml_special_chars`, and
   `test_get_renderer_unknown_raises`.

## Results

| Metric                            | Value                      |
|-----------------------------------|----------------------------|
| `reporting/` package LoC          | 832 (33 + 326 + 473)       |
| `api/routes/reports.py` LoC       | 163                        |
| Test LoC                          | 593                        |
| Product LoC total                 | 995                        |
| Grand total (product + tests)     | 1588                       |
| Tests                             | 33 GREEN                   |
| Phase 182 test runtime            | 41.62s                     |
| Track H regression (175-182)      | 248/248 GREEN (6m 36s)     |
| HTTP endpoints added              | 6                          |
| Report kinds                      | 3 (session, WO, invoice)   |
| Schema version                    | 38 (unchanged)             |
| Migration                         | None                       |
| AI calls                          | 0                          |
| Network calls                     | 0                          |
| PDF library                       | reportlab 4.4.10           |
| New error mapping                 | ReportBuildError → 500     |

**Key finding:** Phase 182 validates the renderer-ABC + dict-
document pattern for HTTP document endpoints. Three distinct
artifacts (session / WO / invoice) share one renderer pipeline
and one router shape; adding a fourth kind (intake PDF, triage
summary, labor estimate) would be ~100 LoC of builder + 2
endpoints + 5 tests. The PDF scaffolding does not belong in any
domain module — keeping it in `motodiag/reporting/` means Track G
modules stay paperwork-agnostic and future report kinds (e.g.,
Gate 9's full intake-to-invoice summary) compose from the same
document primitives.
