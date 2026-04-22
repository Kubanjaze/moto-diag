# MotoDiag Phase 179 — Knowledge Base Endpoints

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-22

## Goal

Expose the Phase 05/06/08/09 knowledge base (DTCs + symptoms +
known_issues + unified search) over HTTP. Read-only, global scope —
the KB is a shared product catalog, not per-user data. All endpoints
require `require_api_key` (any paid tier + free trial API keys get
in); no per-tier gating because the KB is a core product feature.

**No migration.** KB tables + indexes exist from Phases 05-09. Zero
AI. ~330 LoC router, ~25 tests.

Endpoints (7):
- `GET /v1/kb/dtc/{code}` — single DTC lookup
- `GET /v1/kb/dtc?q=...&make=...` — DTC search
- `GET /v1/kb/dtc/categories` — list DTC categories
- `GET /v1/kb/symptoms?q=...` — symptom search
- `GET /v1/kb/issues?q=...` — known-issue search
- `GET /v1/kb/issues/{id}` — known-issue detail
- `GET /v1/kb/search?q=...` — unified search (Phase 09 `search_all`)

## Logic

Thin routing over existing `motodiag.knowledge` + `motodiag.core.search`
repos. No new repo code. Pydantic response schemas for DTC / Symptom /
KnownIssue / SearchResult. Pagination via `limit` + `offset` query
params (default 50 / 0 for lists; single-item endpoints return 404 on
miss).

Search endpoints:
- `q` is optional for DTC + symptom (listing). For `kb/search` and
  `kb/issues` it's required.
- `make` filter is common but optional.
- Limit capped at 200 to prevent abuse.

### 404 semantics

- `GET /v1/kb/dtc/{code}` — 404 when code not found (no `make` fallback).
- `GET /v1/kb/issues/{id}` — 404 when id missing.

### Pydantic schemas

Keep these narrow — reflect the actual repo row shapes:

- `DTCResponse`: code, description, category, severity, make,
  common_causes (JSON list), fix_summary.
- `SymptomResponse`: id, name, description, category, related_systems.
- `KnownIssueResponse`: id, title, description, make, model,
  year_start, year_end, severity, symptoms, dtc_codes, causes,
  fix_procedure, parts_needed, estimated_hours.
- `SearchResult`: type ("dtc" | "symptom" | "issue"), summary,
  ref (back to specific endpoint).

## Verification Checklist

- [x] Unauthenticated → 401 on every KB endpoint.
- [x] GET /v1/kb/dtc/{code} 200 + payload; 404 unknown.
- [x] Make filter honored on DTC endpoints.
- [x] GET /v1/kb/dtc/categories returns list.
- [x] GET /v1/kb/symptoms search works + empty-query returns all.
- [x] GET /v1/kb/issues search + make filter + id detail + 404.
- [x] GET /v1/kb/search returns unified results; missing `q` → 422.
- [x] `limit` capped at 200; honored.
- [x] Phase 175/176/177/178 still GREEN (no structural changes).
- [x] Zero AI calls.

## Results

| Metric | Value |
|--------|------:|
| Phase 179 tests | 17 GREEN single-pass in 13.49s |
| New code | ~310 LoC router |
| Migration | 0 |
| SCHEMA_VERSION | unchanged at 38 |

**Key finding:** KB router is the smallest Track H domain router
yet — no owner scoping, no tier gating, no quota math, just
`require_api_key` + thin wrappers around existing repos. 310 LoC
+ 17 tests in <1hr. The scaffold pattern now scales down gracefully
for simple read-only routers too.

## Risks

- **Large result sets.** Unbounded search returns could be slow on a
  shop with 10k known issues. Mitigation: `limit` capped at 200; the
  Phase 05/08 repos already order + limit internally.
- **No tier gating.** Any authenticated user sees the full KB. If
  competitive risk materializes (e.g. premium content), Phase 183+
  can add `require_tier` per route.
