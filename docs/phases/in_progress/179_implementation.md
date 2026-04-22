# MotoDiag Phase 179 — Knowledge Base Endpoints

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-04-22

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

- [ ] Unauthenticated → 401 on every KB endpoint.
- [ ] GET /v1/kb/dtc/{code} 200 + payload for known code.
- [ ] 404 for unknown code.
- [ ] Make filter honored on DTC + issue endpoints.
- [ ] GET /v1/kb/dtc/categories returns list.
- [ ] GET /v1/kb/symptoms?q=idle returns match.
- [ ] GET /v1/kb/issues?q=brake returns matches.
- [ ] GET /v1/kb/issues/{id} 200 for known id, 404 for unknown.
- [ ] GET /v1/kb/search?q=X returns unified results.
- [ ] Phase 175/176/177/178 still GREEN.
- [ ] Zero AI calls.

## Risks

- **Large result sets.** Unbounded search returns could be slow on a
  shop with 10k known issues. Mitigation: `limit` capped at 200; the
  Phase 05/08 repos already order + limit internally.
- **No tier gating.** Any authenticated user sees the full KB. If
  competitive risk materializes (e.g. premium content), Phase 183+
  can add `require_tier` per route.
