# MotoDiag Phase 175 — Phase Log

**Status:** 🟡 In Progress | **Started:** 2026-04-22
**Repo:** https://github.com/Kubanjaze/moto-diag

---

### 2026-04-22 — Plan written (Track H opens)

Plan v1.0 authored in-session. Scope: FastAPI scaffold opening **Track
H** (API + Web Layer, phases 175-184). This is the load-bearing phase
for Track H — Phases 176-184 all build on this foundation.

Key design decisions:
- **`create_app()` factory pattern** — no app-at-import singleton; each
  test gets a fresh instance with its own dependency overrides. Prod
  uses `uvicorn --factory` semantics via `motodiag serve`.
- **RFC 7807 Problem Details** for error responses — uniform
  `type/title/status/detail/request_id` JSON shape so mobile + web
  clients parse once.
- **21 Track G exceptions → HTTP status map** in a central
  `errors.py`. Route handlers don't try/except; they let domain
  exceptions bubble and let the registered handlers translate. Keeps
  route code terse (this is Track H's "rules are data" equivalent —
  error mapping is data).
- **Dependency-injection chain is the test seam.** `get_db_path` +
  `get_settings` are `Depends()`-injected; tests override via
  `app.dependency_overrides`. No subclassing, no monkey-patching
  module globals.
- **`/v1/shops/{id}` smoke route** — one working domain route proves
  the full chain (Settings → db_path → Phase 160 repo → JSON). Phases
  177-180 add full CRUD on the same pattern.
- **No auth yet** — Phase 176 owns that. This phase provides the
  middleware hook so auth can land without refactoring.
- **Request-ID middleware** — `X-Request-ID` echoed on every response;
  correlates audit trails across Phase 170 notifications + Phase 173
  rule runs + future transport worker logs.

Outputs: 9 new Python files (~720 LoC total) + 1 CLI command + ~30
tests. Zero migration, zero AI, zero schema changes.

FastAPI 0.136 + uvicorn 0.45 + httpx 0.28 verified installed.
`pyproject.toml` already lists fastapi + uvicorn under `api` extras.

**This phase is the single most consequential scaffold of the project
so far.** Everything that runs on a phone, on a web page, or in a
third-party integration will go through the app built here. Getting
the error semantics, dependency chain, and versioning contract right
matters for 10+ downstream phases.
