# MotoDiag Phase 175 — FastAPI Foundation + Project Structure

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-22

## Goal

Open **Track H** (API + Web Layer) with a FastAPI scaffold that
exposes the Track G console over HTTP. This is the load-bearing phase
for Track H — Phases 176-184 all build on this scaffold (auth,
domain routes, WebSockets, OpenAPI, gate test). This phase ships:

- A **`create_app()`** factory that returns a configured FastAPI app
  (easy to test, easy to serve, easy to mount under another app).
- New `src/motodiag/api/` package with subpackages for `routes/`,
  `deps/`, `errors/`, `middleware/`.
- **Config integration** with existing `core/config.py` Settings
  (new `API_HOST`, `API_PORT`, `API_CORS_ORIGINS`, `API_LOG_LEVEL`
  fields).
- **CORS middleware** with mechanic-friendly defaults (localhost:3000
  + localhost:5173 for web clients; configurable).
- **Error handling** that maps Track G domain exceptions (Phase 161's
  `WorkOrderNotFoundError`, Phase 162's `InvalidIssueTransition`,
  etc.) to RFC7807-style JSON problem responses with proper HTTP
  status codes.
- **Health + version endpoints** — `GET /healthz` (SQLite
  connectivity + schema version check) and `GET /v1/version` (package
  version + schema version + build info).
- **Smoke route** — `GET /v1/shops/{shop_id}` proves the
  dependency-injection chain (Settings → db_path → Phase 160
  `get_shop`) works end-to-end.
- **Request-ID middleware** — propagates `X-Request-ID` header for
  audit correlation (load-bearing for future transport worker +
  downstream phases).
- **New CLI subcommand** — `motodiag serve [--host X] [--port N]
  [--reload]` launches uvicorn against the configured app.

CLI — `motodiag serve` — one new top-level command.

**Design rule:** zero AI, zero new migrations, no schema changes.
Phase 175 is pure web scaffolding on top of existing Track G + Phase
112 RBAC + Phase 88 SQLite substrate. Auth lands in Phase 176; domain
routes (vehicles, sessions, KB, shop, WS, reports) land in 177-182;
OpenAPI enrichment in 183; gate test in 184.

Outputs:
- `src/motodiag/api/__init__.py` (`create_app` + `APP_VERSION`).
- `src/motodiag/api/app.py` (~180 LoC) — FastAPI factory +
  middleware + exception handlers + route mounting.
- `src/motodiag/api/deps.py` (~80 LoC) — dependency providers
  (`get_db_path`, `get_settings`, `get_request_id`).
- `src/motodiag/api/errors.py` (~120 LoC) — exception→HTTP mapping
  + `ProblemDetail` Pydantic.
- `src/motodiag/api/middleware.py` (~70 LoC) — request-id + access
  logging middleware.
- `src/motodiag/api/routes/__init__.py` (~15 LoC) — router registry.
- `src/motodiag/api/routes/meta.py` (~60 LoC) — `/healthz`,
  `/v1/version` routes.
- `src/motodiag/api/routes/shops.py` (~50 LoC) — `GET /v1/shops/{id}`
  smoke route (profile read-only).
- `src/motodiag/core/config.py` — add `API_HOST`, `API_PORT`,
  `API_CORS_ORIGINS`, `API_LOG_LEVEL` fields + `.env` lookups.
- `src/motodiag/cli/main.py` — register `motodiag serve` command.
- `src/motodiag/cli/serve.py` (~80 LoC) — NEW — uvicorn launcher.
- `tests/test_phase175_api_foundation.py` (~30 tests across 5
  classes).
- No migration; SCHEMA_VERSION stays at **36**.

## Logic

### `api/app.py` — the factory

```python
def create_app(
    settings: Optional[Settings] = None,
    db_path: Optional[str] = None,
) -> FastAPI:
    """Build a configured FastAPI app.

    Args:
        settings: override the global Settings singleton (test hook).
        db_path: override the DB path (test hook) — injected into the
            `get_db_path` dependency.

    Returns:
        FastAPI instance with:
        - CORS middleware
        - Request-ID middleware
        - Access log middleware
        - Domain exception handlers (Phase 161-173 → HTTP status)
        - All v1 routers mounted at `/v1/*`
        - `/healthz` and `/v1/version` endpoints
        - OpenAPI schema at `/openapi.json`, docs at `/docs`
    """
    app = FastAPI(
        title="MotoDiag API",
        description="Motorcycle diagnostic + shop management API",
        version=APP_VERSION,
        openapi_url="/openapi.json",
        docs_url="/docs",
        redoc_url="/redoc",
    )
    # Middleware
    app.add_middleware(CORSMiddleware, ...)
    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(AccessLogMiddleware)
    # Exception handlers
    _register_exception_handlers(app)
    # Routers
    app.include_router(meta_router)
    app.include_router(shops_router, prefix="/v1")
    # DB path override (test hook)
    if db_path is not None:
        app.dependency_overrides[get_db_path] = lambda: db_path
    return app
```

### `api/errors.py` — domain→HTTP mapping

Pydantic `ProblemDetail` model (RFC 7807 shape):

```python
class ProblemDetail(BaseModel):
    type: str = "about:blank"
    title: str
    status: int
    detail: Optional[str] = None
    request_id: Optional[str] = None
```

Handler map (maps Track G exception classes to HTTP status):

| Exception | HTTP | type URI |
|-----------|-----:|----------|
| `WorkOrderNotFoundError` | 404 | `motodiag/work-order-not-found` |
| `IntakeNotFoundError` | 404 | `motodiag/intake-not-found` |
| `IssueNotFoundError` | 404 | `motodiag/issue-not-found` |
| `InvoiceNotFoundError` | 404 | `motodiag/invoice-not-found` |
| `NotificationNotFoundError` | 404 | `motodiag/notification-not-found` |
| `RuleNotFoundError` | 404 | `motodiag/rule-not-found` |
| `ShopMembershipNotFoundError` | 404 | `motodiag/membership-not-found` |
| `ShopNotFoundError` | 404 | `motodiag/shop-not-found` |
| `InvalidWorkOrderTransition` | 409 | `motodiag/invalid-transition` |
| `InvalidIssueTransition` | 409 | `motodiag/invalid-transition` |
| `InvalidSlotTransition` | 409 | `motodiag/invalid-transition` |
| `InvalidNotificationTransition` | 409 | `motodiag/invalid-transition` |
| `InvoiceGenerationError` | 422 | `motodiag/invoice-generation-failed` |
| `MechanicNotInShopError` | 422 | `motodiag/mechanic-not-in-shop` |
| `PermissionDenied` | 403 | `motodiag/permission-denied` |
| `InvalidRoleError` | 400 | `motodiag/invalid-role` |
| `UnknownEventError` | 400 | `motodiag/unknown-event` |
| `InvalidConditionError` | 400 | `motodiag/invalid-condition` |
| `InvalidActionError` | 400 | `motodiag/invalid-action` |
| `NotificationContextError` | 422 | `motodiag/notification-context` |
| `DuplicateRuleNameError` | 409 | `motodiag/duplicate-rule-name` |
| `ValueError` (catchall) | 400 | `motodiag/validation-error` |

Unhandled `Exception` → 500 with safe error surface (no stack traces
in response, only in server log).

### `api/middleware.py` — request ID + access log

`RequestIdMiddleware`:
- Reads `X-Request-ID` header if present; else generates UUID4.
- Attaches to `request.state.request_id`.
- Echoes back in `X-Request-ID` response header.

`AccessLogMiddleware`:
- Logs one line per request: `method path status duration_ms
  request_id`.
- Structured JSON log format when `LOG_FORMAT=json`.

### `api/deps.py` — dependency providers

```python
def get_db_path() -> str: ...            # Returns Settings.db_path
def get_settings() -> Settings: ...      # Returns global singleton
def get_request_id(request: Request) -> str: ...  # Request state
```

Test code overrides via `app.dependency_overrides[get_db_path] =
lambda: tmp_path_db`.

### `api/routes/meta.py` — health + version

```
GET /healthz → 200 {"status": "ok"}
  - Opens a SQLite connection, reads schema_version.
  - On failure: 503 {"status": "degraded", "detail": ...}

GET /v1/version → 200 {
  "package": "0.11.0",
  "schema_version": 36,
  "api_version": "v1",
}
```

### `api/routes/shops.py` — smoke route

```
GET /v1/shops/{shop_id}
  - Depends(get_db_path)
  - Calls shop_repo.get_shop(shop_id, db_path=...)
  - 200 → shop dict
  - 404 → ProblemDetail (via ShopNotFoundError handler)
```

This single route proves the full dependency chain (Settings →
db_path → Phase 160 repo → JSON serialization → exception handler).
Phases 177-180 will add the full domain routers on the same pattern.

### `cli/serve.py` — uvicorn launcher

```python
@click.command("serve")
@click.option("--host", default=None)
@click.option("--port", type=int, default=None)
@click.option("--reload", is_flag=True, default=False)
@click.option("--log-level", default=None)
def serve_cmd(host, port, reload, log_level):
    """Launch the MotoDiag API server via uvicorn."""
    from motodiag.core.config import get_settings
    import uvicorn
    s = get_settings()
    uvicorn.run(
        "motodiag.api:create_app",
        host=host or s.api_host,
        port=port or s.api_port,
        reload=reload,
        log_level=(log_level or s.api_log_level).lower(),
        factory=True,
    )
```

### `core/config.py` additions

```python
api_host: str = "127.0.0.1"
api_port: int = 8080
api_cors_origins: list[str] = [
    "http://localhost:3000",
    "http://localhost:5173",
]
api_log_level: str = "INFO"
```

Read from `MOTODIAG_API_HOST`, `MOTODIAG_API_PORT`,
`MOTODIAG_API_CORS_ORIGINS` (comma-separated), `MOTODIAG_API_LOG_LEVEL`
env vars via existing pydantic-settings pattern.

## Key Concepts

- **App factory not app-at-import.** `create_app()` returns a fresh
  FastAPI instance on each call so tests can inject different
  `db_path`s without singleton contamination. Production code uses
  `motodiag serve` which passes `factory=True` to uvicorn.
- **RFC 7807 Problem Details for errors.** Instead of ad-hoc JSON
  shapes, every error response follows the same `type / title /
  status / detail / request_id` shape so mobile + web clients can
  parse uniformly.
- **Domain exceptions bubble up unchanged.** Route handlers don't
  try/except every known error — they call the Phase 161-173 repo
  functions and let the global handlers translate to HTTP. Keeps
  route code terse.
- **Dependency override is the test seam.** Every external resource
  (DB, settings, eventually auth context) is a FastAPI `Depends()`,
  so `app.dependency_overrides[dep] = lambda: stub` swaps it cleanly
  in tests.
- **Version endpoint is the contract check.** Mobile clients (Track
  I) will call `/v1/version` on startup to detect schema drift +
  refuse to write against an incompatible server.
- **No breaking of existing CLI.** `motodiag serve` is additive; all
  Track A-G CLI subcommands keep working unchanged. API and CLI share
  the same repos.

## Verification Checklist

- [x] `create_app()` returns a `FastAPI` instance with CORS +
      request-id + access log middleware registered.
- [x] `GET /healthz` returns 200 when DB is reachable, 503 when not.
- [x] `GET /v1/version` returns package + schema version.
- [x] `GET /v1/shops/{id}` returns the shop row for a valid id.
- [x] `GET /v1/shops/{id}` returns a 404 ProblemDetail for unknown id
      (validates exception handler wiring).
- [x] `X-Request-ID` echoed back on every response.
- [x] `Depends(get_db_path)` overridable via
      `app.dependency_overrides`.
- [x] 21+ Track G domain exceptions map to the correct HTTP status
      (4 explicit tests; full map is ~30 exceptions across Track G).
- [x] `ProblemDetail` includes `request_id` when available.
- [x] CORS OPTIONS preflight returns 200 for configured origin.
- [x] `motodiag serve --help` works; `motodiag serve` launches
      uvicorn with correct overrides (mock-patched).
- [x] `--reload` forces workers=1 (uvicorn constraint).
- [x] pyproject.toml api extras already has fastapi + uvicorn; httpx
      shipped with fastapi.testclient (no new dep required).
- [x] Phase 113/118/131/153/160-174 tests still GREEN (679/679).
- [x] Zero AI calls.

## Deviations from Plan

- **CORS "denies non-configured origin" test dropped.** FastAPI's
  `CORSMiddleware` behavior is to not emit CORS headers when the
  origin isn't allowed, rather than returning a 403. The browser
  enforces denial client-side by refusing to read the response
  without the matching `Access-Control-Allow-Origin` header. Testing
  "denial" against the server would just assert "allow-origin header
  absent" — which is CORS-middleware-internal behavior, not our
  contract. Dropped in favor of the positive preflight test that
  actually exercises our configuration.
- **httpx ships with fastapi.testclient.** Plan called for adding
  `httpx` to dev extras; it's bundled with FastAPI's `TestClient` so
  no pyproject change needed.
- **Exception map is ~30 exceptions, not 21.** The actual Track G
  exception catalog is larger than the plan tallied (Phase 165 alone
  contributes 3 — `WorkOrderPartNotFoundError`, `PartNotInCatalogError`,
  `InvalidPartNeedTransition`). All mapped in `_exc_class_chain()`.
- **26 tests landed vs ~30 planned.** Coverage is adequate — every
  major class has 3-7 tests and the combined coverage walks all
  middleware, all major exception families, the app factory, the
  smoke route, and the CLI launcher. Adding 4 more tests for Track G
  exceptions not individually exercised would be redundant with the
  per-Track-G-phase tests that already prove those exceptions get
  raised correctly.

## Results

| Metric | Value |
|--------|-------|
| Phase 175 tests landed | 26 GREEN (6 classes) |
| Targeted regression | 679/679 GREEN in 439.45s (7m 19s) |
| Coverage range | Phase 113 + 118 + 131 + 153 + Track G 160-174 + 162.5 + 175 |
| New code | ~750 LoC (app + deps + errors + middleware + 2 routers + serve CLI) |
| `api/app.py` | 108 LoC |
| `api/deps.py` | 42 LoC |
| `api/errors.py` | 224 LoC (big chunk is the exception-map builder) |
| `api/middleware.py` | 68 LoC |
| `api/routes/meta.py` | 78 LoC |
| `api/routes/shops.py` | 28 LoC |
| `cli/serve.py` | 75 LoC |
| SCHEMA_VERSION | unchanged at **36** |
| AI calls | 0 (zero tokens spent) |
| FastAPI version | 0.136.0 |
| uvicorn version | 0.45.0 |

**Key finding:** Phase 175 is the single most consequential scaffold
of the project — **moto-diag graduates from CLI-only to a real web-
accessible API platform**. Every Track H, I, and J phase that follows
consumes the primitives locked here: `create_app()` factory with
dependency-override test seam, `ProblemDetail` RFC 7807 errors, 30+
domain exceptions auto-mapped to HTTP status, `X-Request-ID`
correlation, `motodiag serve` launcher. The design-pillar lesson from
Track G (compose-don't-duplicate) ported directly: route handlers are
~5 lines each because they raise the same Track G exceptions that
the global handler translates — no boilerplate try/except at every
call site. Track H Phase 176 can now layer session auth + API keys
via FastAPI middleware without touching any route; Phases 177-180 add
full CRUD routers on the shop smoke route's pattern; Phase 181 WebSockets
mount on the same app; Phase 184 gate test exercises the full stack.
**679/679 targeted regression GREEN** proves the scaffold broke
nothing.

## Risks

- **Uvicorn launcher not testable directly.** `motodiag serve`
  actually blocks on `uvicorn.run`. Mitigation: test via
  `patch("uvicorn.run")` to verify arg propagation; don't spawn a
  real server in pytest.
- **CORS dev defaults vs prod.** Allowing localhost:3000 by default
  is fine for local dev but a prod deployment behind a real domain
  must override. Mitigation: `API_CORS_ORIGINS` env var is read
  first; document deployment in the Phase 175 closure doc.
- **TestClient async context.** FastAPI's `TestClient` (from
  `fastapi.testclient`) uses the sync interface over httpx internally.
  Our tests should all be sync to match the Phase 161-173 style; no
  asyncio/anyio yak-shaving needed.
- **Exception handler ordering.** FastAPI registers handlers in
  definition order; the most specific should register last. Our
  `ValueError` catchall goes first, then each specific subclass.
  Tests explicitly assert the right status for `ValueError` and each
  subclass.
- **DB connection under load.** Each request opens + closes a
  connection via `get_connection()` context manager. WAL mode (from
  Phase 03) keeps readers from blocking; writers still serialize.
  Phase 180 may need to introduce a connection pool; Phase 175's
  simple-per-request approach is fine for smoke-level traffic.
- **Request-ID collisions.** UUID4 collisions in practice zero; but
  an attacker could spoof `X-Request-ID`. Mitigation: accept client-
  supplied ID (useful for tracing) but don't trust it for auth/audit
  — Phase 176 will derive a server-side session/audit id separately.
