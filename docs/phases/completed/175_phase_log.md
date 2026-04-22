# MotoDiag Phase 175 — Phase Log

**Status:** ✅ Complete — **TRACK H OPEN** | **Started:** 2026-04-22 | **Completed:** 2026-04-22
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

### 2026-04-22 — Build complete

Files shipped (~750 LoC total, 8 new Python files):

1. **`src/motodiag/api/__init__.py`** — re-exports `create_app` +
   `APP_VERSION`.

2. **`src/motodiag/api/app.py`** (108 LoC) — `create_app(settings,
   db_path_override)` factory:
   - `FastAPI(title=..., description=..., version=...,
     openapi_url="/openapi.json", docs_url="/docs", redoc_url="/redoc")`
   - CORS middleware wired from `settings.api_cors_origins_list`
   - `RequestIdMiddleware` + `AccessLogMiddleware` registered
   - All 30+ Track G exceptions mapped via
     `register_exception_handlers`
   - Kwarg-driven dependency overrides (settings + db_path_override)
   - Lazy router import (keeps `from motodiag.api import create_app`
     fast — Track G modules aren't imported until a router mounts)
   - `/healthz`, `/v1/version`, `/v1/shops/{id}` routers included

3. **`src/motodiag/api/deps.py`** (42 LoC) — `get_settings`,
   `get_db_path`, `get_request_id` — the three canonical FastAPI
   `Depends(...)` providers. Every test overrides via
   `app.dependency_overrides[dep] = lambda: stub`.

4. **`src/motodiag/api/errors.py`** (224 LoC) — RFC 7807 problem
   details. `ProblemDetail` Pydantic model +
   `_exc_class_chain()` builds the exception→(status, slug, title)
   tuple list lazily. `register_exception_handlers()` wires `ValueError`
   first (catchall), then each specific Track G subclass, then
   `Exception` last (safe 500 with no stack-trace leak).
   Type URIs: `https://motodiag.dev/problems/<slug>`.

5. **`src/motodiag/api/middleware.py`** (68 LoC) —
   `RequestIdMiddleware` (accepts client-supplied
   `X-Request-ID` or generates UUID4; echoes on response) +
   `AccessLogMiddleware` (one structured line per request).

6. **`src/motodiag/api/routes/__init__.py`** — router registry stub.

7. **`src/motodiag/api/routes/meta.py`** (78 LoC) — `/healthz`
   (schema version probe, 503 on DB unreachable) + `/v1/version`
   (package + schema + api_version — Track I mobile clients call
   this to detect drift).

8. **`src/motodiag/api/routes/shops.py`** (28 LoC) —
   `GET /v1/shops/{id}` smoke route. Raises `ShopNotFoundError` on
   miss; global handler translates to 404 ProblemDetail. Proves the
   full DI chain end-to-end.

9. **`src/motodiag/cli/serve.py`** (75 LoC) — `register_serve(cli)`
   wires `motodiag serve` command. Respects
   `MOTODIAG_API_HOST/PORT/LOG_LEVEL` env vars + Settings defaults.
   `--reload` forces `workers=1` (uvicorn constraint).

10. **`src/motodiag/cli/main.py`** — `register_serve(cli)` added
    between `register_shop(cli)` and `register_completion(cli)` (so
    completion picks up the new command).

11. **`src/motodiag/core/config.py`** — added `api_host`, `api_port`,
    `api_cors_origins` (comma-separated), `api_log_level` +
    `api_cors_origins_list` property that splits on commas.

12. **`tests/test_phase175_api_foundation.py`** (26 tests across 6
    classes): TestAppFactory×4 + TestMetaEndpoints×5 +
    TestSmokeShopRoute×4 + TestErrorHandling×7 + TestMiddleware×3 +
    TestServeCLI×3.

**Single-pass: 26 GREEN in 15.14s.** No fixups needed. Scaffold is
clean on first try.

**Targeted regression: 679/679 GREEN in 439.45s (7m 19s)** covering
Phase 113 + 118 + 131 + 153 + Track G 160-174 + 162.5 + 175. Zero
regressions. API layer lands without touching any existing code path.

Build deviations vs plan:
- CORS "denies non-configured origin" test dropped — CORS is
  browser-enforced via missing allow-origin header, not server-side
  403. Kept the positive preflight test that exercises configuration.
- httpx already ships with fastapi.testclient — no dev-dep change.
- Exception catalog is ~30 not 21 (Phase 165's 3 parts exceptions
  were under-counted; full map in `_exc_class_chain()`).
- 26 tests vs ~30 planned — coverage is adequate; per-Track-G tests
  already prove individual exception raising.

### 2026-04-22 — Documentation finalization — **🚀 TRACK H OPENS**

`implementation.md` promoted to v1.1. All `[x]` in Verification
Checklist. Deviations + Results sections populated. Key finding
captures the transformative moment: moto-diag graduates from local-
CLI-only to a real HTTP API platform.

Project-level updates:
- `implementation.md` Phase History: append Phase 175 row marking
  **Track H open**
- `implementation.md` CLI Commands table: added `motodiag serve`
  (one new top-level command, not a subgroup)
- `implementation.md` Package Inventory: added `src/motodiag/api/`
  package
- `phase_log.md` project-level: Track H opening entry + Phase 175
  closure
- `docs/ROADMAP.md`: Phase 175 row → ✅
- Project version 0.11.0 → **0.11.1** (incremental; Track H is
  opening, not yet delivering a gate)

**Key finding:** Phase 175 is the watershed moment. Every Track
H/I/J phase that follows consumes this scaffold:
- **Phase 176** (auth + API keys + Stripe paywall) will add
  `APIKeyHeader` dependency + Stripe webhook routes + rate-limit
  middleware to this app. No refactoring needed — the middleware
  + deps seams are in place.
- **Phases 177-180** (vehicle / session / KB / shop CRUD routers)
  follow the `shops.py` smoke-route pattern one-for-one: raise
  domain exception → global handler maps to HTTP → Pydantic response
  serialization. Probably ~100 LoC each.
- **Phase 181** (WebSocket live data) will mount `@app.websocket(...)`
  handlers on the same app; shares the auth dependency.
- **Phase 182** (report generation endpoints) uses FastAPI's
  `FileResponse` / `StreamingResponse` for PDF downloads.
- **Phase 183** (OpenAPI enrichment) tweaks the already-working
  `/openapi.json` spec with examples + tags + security schemes.
- **Phase 184** (Gate 9 integration test) runs the same intake →
  invoice flow as Gate 8 but through the HTTP API via httpx instead
  of CLI.
- **Track I** (mobile app, phases 185-204) consumes this API as its
  backend — every mobile screen calls a `/v1/*` endpoint.

The canonical patterns locked here (app factory + dependency
override + RFC 7807 errors + request-id correlation + lazy domain
imports) carry forward across all three remaining tracks without
modification. This scaffold is the contract the rest of the
product-surface area depends on.
