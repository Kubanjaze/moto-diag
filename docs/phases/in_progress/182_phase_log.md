# MotoDiag Phase 182 — Phase Log

**Status:** 🟡 In Progress | **Started:** 2026-04-22
**Repo:** https://github.com/Kubanjaze/moto-diag

---

### 2026-04-22 — Plan written

Plan v1.0. Scope: downloadable PDF reports for the three mechanic-
facing artifacts — diagnostic session report (session owner), work-
order receipt (shop-tier), invoice PDF (shop-tier + Phase 169
composition).

New package `motodiag/reporting/`: `ReportRenderer` ABC +
`TextReportRenderer` (always-available fallback) +
`PdfReportRenderer` (reportlab, already installed). Three builders
wire repos → `ReportDocument` dict → renderer. Six endpoints:
JSON-preview + PDF-download for each of the three report kinds.

Auth: session reports require caller owns the session (404
cross-user); WO + invoice reports require `shop` tier AND
membership in the WO's shop (403 cross-shop). No subscription
required for session reports — DIY users still get their own
diagnostics on paper.

No migration, schema stays at 38. ~750 LoC + ~30 tests.
