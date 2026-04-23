# MotoDiag Phase 183 — OpenAPI Enrichment + Spec Polish

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-04-23

## Goal

Polish the auto-generated OpenAPI schema so it's genuinely usable
by Track I mobile clients + external API consumers + anyone reading
the Swagger UI at `/docs`. FastAPI's default spec captures the
routes' summaries + types but nothing about the product — no tag
descriptions, no server URLs, no security schemes, no documented
error envelopes. Phase 183 fixes all of that **at the spec level,
not by touching every route handler**.

CLI — none. Pure spec enrichment.

Outputs (~350 LoC + ~20 tests):
- `src/motodiag/api/openapi.py` (~300 LoC) — `build_openapi(app)`
  override that:
  - Injects `info.contact`, `info.license`, `info.termsOfService`.
  - Adds `servers=[...]` list from Settings (local dev / staging
    placeholder / prod placeholder).
  - Adds `tags=[...]` with description + externalDocs per tag.
  - Adds `components.securitySchemes.apiKey` (APIKeyHeader) +
    `components.securitySchemes.bearerAuth` (HTTP Bearer).
  - Adds `components.responses.*` — common error envelopes (401 /
    402 / 403 / 404 / 422 / 429 / 500 all using the RFC 7807
    `ProblemDetail` schema).
  - Walks every `/v1/*` operation and attaches the right
    security + error responses references based on the
    operation's existing dependencies.
  - Caches the result on the app so repeated spec requests don't
    re-enrich.
- `src/motodiag/api/app.py` — wire the override.
- `src/motodiag/core/config.py` — add `api_servers` Setting.
- `tests/test_phase183_openapi.py` (~20 tests).

No migration, no schema change, no new runtime behavior — this
phase only changes what `/openapi.json` and `/docs` return.

## Logic

### FastAPI OpenAPI override pattern

```python
def custom_openapi(app: FastAPI) -> dict:
    if app.openapi_schema:
        return app.openapi_schema
    schema = get_openapi(
        title=app.title, version=app.version,
        description=app.description, routes=app.routes,
    )
    # … enrich …
    app.openapi_schema = schema
    return schema

app.openapi = lambda: custom_openapi(app)
```

This is the documented FastAPI extension point. All enrichment
happens once per app instance; the cached result is returned on
every subsequent `/openapi.json` request.

### Enrichment steps (in order)

1. **`info` block:** inject `contact`, `license`, `termsOfService`.
   The `contact.email` is `support@motodiag.dev` (placeholder).
   `license` is MIT + url. `termsOfService` placeholder URL.

2. **`servers`:** from `Settings.api_servers` — a list of
   `{"url": "...", "description": "..."}` dicts. Defaults to
   `[{"url": "http://localhost:8000", "description": "Local dev"}]`.
   Override via `MOTODIAG_API_SERVERS` env var (JSON list).

3. **`tags`:** a fixed catalog of 10 tag metadata blocks covering
   every tag currently in use: `meta`, `shops`, `billing`,
   `vehicles`, `sessions`, `knowledge-base`, `shop-management`,
   `reports`, `live`, and a future `auth`. Each has a one-line
   description matching the mechanic-facing feature it fronts.

4. **`components.securitySchemes`:** two schemes:
   - `apiKey`: type=`apiKey`, in=`header`, name=`X-API-Key`.
   - `bearerAuth`: type=`http`, scheme=`bearer`.

5. **`components.responses.*`:** seven reusable error envelope
   responses (`Unauthorized`, `SubscriptionRequired`, `Forbidden`,
   `NotFound`, `ValidationError`, `RateLimitExceeded`,
   `InternalError`). Each has `content.application/json.schema =
   $ref: '#/components/schemas/ProblemDetail'`. The
   `ProblemDetail` schema is emitted by FastAPI already (from the
   Pydantic model in `api/errors.py`) — we just reference it.

6. **Per-operation enrichment walk:** for every path in
   `schema["paths"]`, for every method:
   - Detect if the operation requires auth (heuristic: check tags
     — `meta` + `billing/webhooks` are public; everything else
     under `/v1/*` requires auth). Add `security=[{"apiKey": []}]`
     when required.
   - Add the common error envelope responses. All `/v1/*`
     operations get 401 + 429 + 500. Endpoints with `require_tier`
     add 402. Endpoints with path params add 404. Endpoints with
     request bodies add 422.

7. **Cache:** `app.openapi_schema = schema` on first call.

### Tag catalog

| Tag             | Description |
|-----------------|-------------|
| meta            | Health checks and version metadata. No auth required. |
| auth            | API keys + billing + subscriptions. Entry point for paywall. |
| shops           | Shop registry (global). Every shop has an id; see `shop-management` for write ops. |
| billing         | Stripe checkout sessions + webhooks. |
| vehicles        | Caller's garage — add/list/delete bikes. Tier-quota gated. |
| sessions        | Diagnostic session lifecycle. Monthly-quota gated. |
| knowledge-base  | DTC codes + symptoms + known issues + unified search. |
| shop-management | The full shop-operator console: members, customers, work orders, issues, parts, invoices, analytics. Shop-tier only. |
| reports         | Downloadable PDF / JSON reports for sessions / work orders / invoices. |
| live            | WebSocket live sensor data for a diagnostic session. |

### Response envelope reuse

Rather than re-declaring the 401/402/403/404/422/429/500 body on
every operation (48 × 7 = 336 schema nodes of duplication), the
enrichment emits each response once in `components.responses.*`
and attaches refs via the `$ref: '#/components/responses/<name>'`
pattern. Swagger UI renders the descriptions inline for each
operation.

### Config addition

New `Settings` field `api_servers: list[dict]`. Default is one
local-dev server; JSON-encoded env var override. The field's
validator ensures each entry is a dict with `url` (required) and
`description` (optional).

## Key Concepts

- **`fastapi.openapi.utils.get_openapi`** — the underlying OpenAPI
  builder. `FastAPI.openapi()` calls this; override the method to
  enrich.
- **Caching via `app.openapi_schema`** — FastAPI's convention for
  memoizing the enriched spec. Avoid rebuilding on every
  `/openapi.json` request.
- **`components.securitySchemes`** — OpenAPI 3's security scheme
  registry. Operations reference schemes by name in their
  `security` array.
- **`components.responses.*`** — reusable response envelope
  registry. Operations reference via
  `{"$ref": "#/components/responses/<name>"}`.
- **`externalDocs`** — per-tag or per-operation link to external
  documentation URL. Surfaces in Swagger UI as an "external docs"
  icon next to the tag/operation.
- **OpenAPI `info.license.identifier`** — SPDX identifier field
  (added in OpenAPI 3.1). FastAPI 0.136 emits OpenAPI 3.1.
- **Operation `operationId`** — FastAPI auto-generates these from
  function names; used by SDK generators (openapi-generator, etc.)
  to name client methods.

## Verification Checklist

- [ ] `/openapi.json` returns a dict with `servers` array.
- [ ] `servers` contains at least the local-dev entry.
- [ ] `info.contact.email` is set.
- [ ] `info.license.name == "MIT"`.
- [ ] `components.securitySchemes.apiKey.type == "apiKey"`.
- [ ] `components.securitySchemes.apiKey.name == "X-API-Key"`.
- [ ] `components.securitySchemes.bearerAuth.scheme == "bearer"`.
- [ ] `components.responses.Unauthorized` exists with 401
      semantics.
- [ ] `components.responses.SubscriptionRequired` exists with 402.
- [ ] `components.responses.RateLimitExceeded` exists with 429.
- [ ] `components.responses.ValidationError` exists with 422.
- [ ] `tags` array contains all 10 tag metadata entries with
      descriptions.
- [ ] Every `/v1/*` operation has `security=[{"apiKey": []}]`
      attached (except `/v1/billing/webhooks/stripe`).
- [ ] `/v1/version` has NO security requirement (public).
- [ ] `/healthz` has NO security requirement (public).
- [ ] Every `/v1/*` operation has `401` in `responses`.
- [ ] Every `shop-tier` operation has `402` in `responses`.
- [ ] Operations with path params have `404` in `responses`.
- [ ] Operations with bodies have `422` in `responses`.
- [ ] Second call to `app.openapi()` returns the cached dict
      (identity check).
- [ ] Swagger UI at `/docs` renders without errors.
- [ ] Phase 175-182 still GREEN.
- [ ] Zero AI calls, zero network.

## Risks

- **FastAPI version drift** — the `openapi` override pattern is
  stable as of FastAPI 0.136 but has shifted across minor
  versions. Tests pin the override mechanism so upgrades catch
  breakage.
- **Caching bugs in tests** — `create_app()` returns a fresh app
  each call; each has its own `openapi_schema` cache. Tests must
  not rely on `settings` singletons.
- **Tag ordering** — OpenAPI 3.1 doesn't require tag ordering but
  Swagger UI renders in the order given. Catalog is sorted by
  product importance (meta → auth → core domain → shop → ops).
- **ProblemDetail ref drift** — the `ProblemDetail` schema name
  is auto-generated by FastAPI from the Pydantic class name
  (`ProblemDetail`). If the class is renamed, the ref in
  `components.responses.*` breaks. Test guards against renaming.
