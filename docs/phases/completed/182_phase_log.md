# MotoDiag Phase 182 — Phase Log

**Status:** ✅ Complete | **Started:** 2026-04-22 | **Completed:** 2026-04-23
**Repo:** https://github.com/Kubanjaze/moto-diag

---

### 2026-04-22 22:10 — Plan written, initial push

Plan v1.0. Scope: downloadable PDF reports for the three mechanic-
facing artifacts — diagnostic session report (session owner), work-
order receipt (shop-tier), invoice PDF (shop-tier + Phase 169
composition). New package `motodiag/reporting/`: `ReportRenderer`
ABC + `TextReportRenderer` (always-available fallback) +
`PdfReportRenderer` (reportlab, already installed). Three builders
wire repos → `ReportDocument` dict → renderer. Six endpoints:
JSON-preview + PDF-download for each kind.

Auth: session reports require caller owns the session (404 cross-
user); WO + invoice reports require `shop` tier AND membership in
the WO's shop (403 cross-shop). No subscription required for
session reports — DIY users still get their own diagnostics on
paper. No migration, schema stays at 38.

---

### 2026-04-23 00:05 — Build complete

**Shipped (962 LoC product code + 593 LoC tests):**
- `src/motodiag/reporting/__init__.py` (33 LoC) — package entry.
- `src/motodiag/reporting/renderers.py` (326 LoC) —
  `ReportRenderer` ABC + `TextReportRenderer` + `PdfReportRenderer`
  (Platypus flowables + XML-escaping helper + `_kv_table` /
  `_grid_table` helpers) + `get_renderer` factory +
  `PDF_AVAILABLE` flag.
- `src/motodiag/reporting/builders.py` (473 LoC) — three builders:
  `build_session_report_doc` (7 section shapes), 
  `build_work_order_report_doc` (up to 8 sections including
  issues + parts tables), `build_invoice_report_doc` (5 sections
  including line-items table + totals). Shared helpers: `_money`
  formatter, `_require_member` shop-membership gate, `_footer`
  timestamp.
- `src/motodiag/api/routes/reports.py` (163 LoC) — 6 endpoints
  (3 JSON preview + 3 PDF download) wired through
  `get_current_user` for session + `require_tier("shop")` for
  WO/invoice.
- `src/motodiag/api/app.py` — mount reports router at `/v1`.
- `src/motodiag/api/errors.py` — added `ReportBuildError` → 500
  mapping.

**Deviations:**
1. **LoC overshoot** — 962 product LoC vs. planned ~750. Builders
   grew because each report kind needed its own section-composition
   logic and defensive handling of optional DB columns. Text
   renderer grew to a first-class alternative rather than a
   conditional fallback.
2. **`get_dtc` return type** — plan assumed it returned an object
   with `.description` and `.severity.value`. It returns a dict.
   One-line fix mid-build; documented in Deviations.
3. **`generate_invoice_for_wo` kwarg name** — caught in test
   setup: function takes `wo_id=` not `work_order_id=`. One-line
   fix in the test helper.
4. **33 tests vs ~30 planned** — three extras emerged for forward-
   compat (`test_renderer_skips_unknown_section_kind`), XML
   escaping (`test_pdf_renderer_escapes_xml_special_chars`), and
   factory-error coverage (`test_get_renderer_unknown_raises`).

**Test results:**
- Phase 182: 33/33 GREEN in 41.62s across 7 classes (Renderers ×9 +
  SessionBuilder ×3 + WorkOrderBuilder ×3 + InvoiceBuilder ×3 +
  SessionReportsHTTP ×5 + ShopReportsHTTP ×9 + ReportBuildError ×1).
- Track H regression 175-182: **248/248 GREEN in 6m 36s (396.37s)**. Zero regressions.
- Schema version unchanged at 38.
- Zero AI calls, zero network calls.

**Key finding:** the renderer-ABC + dict-document pattern
collapses three report kinds onto one rendering pipeline and one
router shape. Future report kinds (intake summary, triage
overview, labor estimate PDF) would require ~100 LoC of builder +
2 endpoints + 5 tests each. The PDF scaffolding lives in
`motodiag/reporting/`, not in any domain module — Track G modules
stay paperwork-agnostic. Gate 9's intake-to-invoice integration
test will compose these primitives rather than invent its own.
