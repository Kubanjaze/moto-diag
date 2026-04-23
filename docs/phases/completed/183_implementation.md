# MotoDiag Phase 183 — OpenAPI Enrichment + Spec Polish

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-23

## Goal

Polish the auto-generated OpenAPI schema so it's genuinely usable
by Track I mobile clients + external API consumers + anyone
reading the Swagger UI at `/docs`. FastAPI's default spec captures
the routes' summaries + types but nothing about the *product* —
no tag descriptions, no server URLs, no security schemes, no
documented error envelopes. Phase 183 fixes all of that **at the
spec level, not by touching every route handler**.

CLI — none. Pure spec enrichment.

Outputs (459 LoC product code + 302 LoC tests = 761 total):
- `src/motodiag/api/openapi.py` (459 LoC) — `build_openapi(app)`
  override + `install_openapi(app)` wiring. Contains the static
  metadata catalogs (`TAG_CATALOG` with 10 tags, `SECURITY_SCHEMES`
  with 2 schemes, `ERROR_RESPONSES` with 7 reusable envelopes,
  `PROBLEM_DETAIL_SCHEMA` fallback) plus the
  per-operation walk that attaches security + error-response refs
  based on tags, path params, request bodies.
- `src/motodiag/api/app.py` — one-line install after routers
  mount: `install_openapi(app)`.
- `src/motodiag/core/config.py` — new `api_servers` Setting +
  `api_servers_list` property that parses pipe/comma syntax
  (`url|description,url|description,...`).
- `tests/test_phase183_openapi.py` (302 LoC, 43 tests across 8
  classes).

No migration, no schema change, no runtime-behavior change — only
what `/openapi.json` and `/docs` return changes.

## Logic

### FastAPI OpenAPI override pattern

```python
def build_openapi(app: FastAPI) -> dict:
    if app.openapi_schema is not None:
        return app.openapi_schema
    schema = get_openapi(
        title=app.title, version=app.version,
        description=app.description, routes=app.routes,
        tags=TAG_CATALOG,
    )
    # … enrich …
    app.openapi_schema = schema
    return schema

def install_openapi(app: FastAPI) -> None:
    app.openapi_schema = None
    app.openapi = lambda: build_openapi(app)
```

This is the documented FastAPI extension point. All enrichment
happens once per app instance; the cached result is returned on
every subsequent `/openapi.json` request.

### Enrichment steps (in order)

1. **`tags` passed to `get_openapi`** — fed at construction time
   so FastAPI emits the full tag catalog with descriptions in the
   spec. (Per the FastAPI source, `get_openapi(tags=...)` is the
   correct channel; setting `app.openapi_tags` after the fact
   gets ignored by our override path.)

2. **`info` block enrichment:** `contact` (MotoDiag Support +
   email + url), `license` (MIT + SPDX identifier + url),
   `termsOfService` (placeholder URL).

3. **`servers` list:** from `Settings.api_servers_list`. Defaults
   to a single local-dev entry. Parsed from the pipe/comma-encoded
   `MOTODIAG_API_SERVERS` env var so deployments can set
   `"https://api.motodiag.dev|Production,https://staging.motodiag.dev|Staging"`.

4. **`components.schemas.ProblemDetail`:** emitted by FastAPI from
   the Pydantic model in `api/errors.py`, but the enrichment
   inserts an explicit `PROBLEM_DETAIL_SCHEMA` fallback via
   `setdefault` in case no route types its return as
   `ProblemDetail` (common — most routes return domain models and
   only the exception handler produces ProblemDetail bodies).

5. **`components.securitySchemes`:** two entries:
   - `apiKey` — `in: header`, `name: X-API-Key`.
   - `bearerAuth` — `type: http`, `scheme: bearer`.

6. **`components.responses.*`:** seven reusable envelopes —
   `Unauthorized` (401), `SubscriptionRequired` (402), `Forbidden`
   (403), `NotFound` (404), `ValidationError` (422),
   `RateLimitExceeded` (429, with `Retry-After` +
   `X-RateLimit-*` headers documented), `InternalError` (500).
   All reference `#/components/schemas/ProblemDetail`.

7. **Per-operation walk (`_walk_operations` → `_enrich_operation`):**
   for every path × method in the spec:
   - Skip non-HTTP verbs.
   - If the operation is public (tag in `PUBLIC_TAGS = {"meta"}`
     OR path starts with any `PUBLIC_PATH_PREFIXES`), leave it
     alone.
   - Otherwise: add `security = [{"apiKey": []}, {"bearerAuth":
     []}]` (supports both auth methods) + 401 + 429 + 500 refs.
   - If the operation's tag is in
     `_ALWAYS_TIER_GATED_TAGS = {"shop-management", "reports",
     "live", "vehicles", "sessions"}` → add 402.
   - If the operation has any path param → add 404.
   - If the operation has a `requestBody` → add 422.

8. **Cache:** `app.openapi_schema = schema` at the end. Idempotent
   — subsequent calls to `app.openapi()` return the same dict
   (identity-equal).

### Tag catalog

10 tags covering every tag currently in use:

| Tag             | Purpose |
|-----------------|---------|
| meta            | Health + version. Public. |
| auth            | API keys, subs, Stripe webhooks. |
| shops           | Global shop registry reads. |
| billing         | Stripe checkout + portal. |
| vehicles        | Caller's garage. Tier-quota gated. |
| sessions        | Diagnostic session lifecycle. Monthly-quota gated. |
| knowledge-base  | DTC / symptom / known-issue lookup + unified search. |
| shop-management | Full shop-operator console — members, WOs, issues, parts, invoices, analytics. Shop-tier. |
| reports         | Downloadable session / WO / invoice reports in JSON or PDF. |
| live            | WebSocket live OBD sensor data. |

### Config addition

`Settings.api_servers` is a pipe/comma-encoded string (not a list)
because `pydantic-settings` can't construct `list[dict]` from an
env var without custom parsing. The property
`api_servers_list` does the parsing and returns
`list[{"url": str, "description": str}]`. Empty entries and
missing descriptions are tolerated.

## Key Concepts

- **`fastapi.openapi.utils.get_openapi(tags=...)`** — passing
  `tags` at construction time is the reliable channel for
  emitting a tag catalog with descriptions. Setting
  `app.openapi_tags` after the fact works *only* for FastAPI's
  default `openapi()` method; our override skips that path.
- **`app.openapi_schema = None`** — documented cache-invalidation
  hook. `install_openapi` resets it so re-installation starts
  clean; subsequent `app.openapi()` calls rebuild then cache.
- **`components.securitySchemes`** — OpenAPI 3 security scheme
  registry. Operations reference by name via
  `security=[{"<name>": []}]`. An array of dicts is an OR; a dict
  of lists is an AND. We use the OR form so clients can pick
  either `X-API-Key` header or `Authorization: Bearer`.
- **`components.responses.*`** — reusable response object
  registry. Operations reference via `$ref:
  '#/components/responses/<name>'`. Avoids duplicating the
  ProblemDetail body + headers on every operation.
- **`externalDocs`** — per-tag or per-operation link. Not used in
  Phase 183 (no external doc site yet) but the shape is
  `{"url": "...", "description": "..."}`.
- **OpenAPI 3.1 `info.license.identifier`** — SPDX identifier
  field added in 3.1. FastAPI 0.136 emits 3.1 by default.
- **`include_in_schema=False`** — FastAPI route decorator kwarg.
  The Stripe webhook uses it so the webhook endpoint doesn't
  leak into the OpenAPI spec at all (webhook is HMAC-secured, not
  API-key-secured).

## Verification Checklist

- [x] `/openapi.json` returns a dict with `servers` array.
- [x] `servers` contains at least the local-dev entry.
- [x] `info.contact.email` is set to `support@motodiag.dev`.
- [x] `info.license.name == "MIT"`.
- [x] `info.termsOfService` starts with `https://`.
- [x] `components.securitySchemes.apiKey.type == "apiKey"`.
- [x] `components.securitySchemes.apiKey.name == "X-API-Key"`.
- [x] `components.securitySchemes.bearerAuth.scheme == "bearer"`.
- [x] `components.responses.Unauthorized` exists.
- [x] `components.responses.SubscriptionRequired` exists.
- [x] `components.responses.Forbidden` exists.
- [x] `components.responses.NotFound` exists.
- [x] `components.responses.ValidationError` exists.
- [x] `components.responses.RateLimitExceeded` exists with
      `Retry-After` header documented.
- [x] `components.responses.InternalError` exists.
- [x] `tags` array contains all 10 tag metadata entries with
      descriptions ≥ 20 chars each.
- [x] Every tag used by a route appears in the tag catalog.
- [x] `/v1/version` and `/healthz` have NO security requirement.
- [x] `/v1/vehicles` GET / POST have `apiKey` security +
      401 + 429 + 500 + 402 + 422 responses.
- [x] `/v1/vehicles/{vehicle_id}` has 404 in responses (path
      param).
- [x] `/v1/reports/work-order/{id}/pdf` has 402 (tier-gated tag).
- [x] Stripe webhook path is NOT in the spec (marked
      `include_in_schema=False` upstream).
- [x] Second `app.openapi()` call returns identity-equal cached
      dict.
- [x] `install_openapi` resets cache — post-install spec is a new
      dict but equal content.
- [x] `api_servers_list` parses default, pipe/comma syntax, url-
      only, empty-string inputs.
- [x] Phase 175-182 still GREEN — full Track H regression
      (175-183): 291/291 in 7m 01s (421.60s).
- [x] Zero AI calls.

## Risks

- **FastAPI version drift** — the override pattern is stable
  through FastAPI 0.136 but has shifted across minor versions.
  Tests pin the override mechanism (`install_openapi` +
  `build_openapi`) and assert on concrete spec-structure
  invariants, so an upgrade that changes the shape of
  `get_openapi(...)` return value will break the tests loudly.
- **Caching bugs** — a mutation to the cached dict from outside
  would leak into every subsequent `/openapi.json` response.
  Enrichment only runs once per app instance; we never hand out
  references to sub-dicts without copying.
- **Tag ordering** — OpenAPI 3.1 doesn't mandate ordering but
  Swagger UI renders in the order given. The catalog is sorted
  by product importance (meta → auth → core domain → shop → ops).
- **ProblemDetail ref drift** — the `ProblemDetail` schema name
  is auto-generated by FastAPI from the Pydantic class name. If
  the class is renamed, the ref in `components.responses.*`
  breaks. Test `test_problem_detail_schema_present` guards
  against this.

## Deviations from Plan

1. **LoC overshoot** — 459 product LoC vs. planned 300. The tag
   catalog + security schemes + error responses + ProblemDetail
   fallback are all large static dicts with long descriptions
   (each description ≥ 60 chars so Swagger UI shows useful
   help text, not stubs). Plan also didn't account for the
   `PROBLEM_DETAIL_SCHEMA` fallback.

2. **`api_servers` as comma/pipe string, not JSON list** —
   `pydantic-settings` can't natively build a `list[dict]` from
   an env var without a custom validator. Keeping the field a
   string + adding a parser property was simpler than wiring a
   JSON validator, and matches the pattern used by
   `api_cors_origins`.

3. **`TAG_CATALOG` passed via `get_openapi(tags=...)` not via
   `app.openapi_tags`** — discovered during build that setting
   `app.openapi_tags` after the override fires gets ignored
   because our override constructs the schema from scratch. Fix:
   pass the catalog at `get_openapi(...)` construction time.

4. **43 tests vs ~20 planned** — the plan undercounted. Each
   catalog member deserved at least one assertion
   (parametrized test over `ERROR_RESPONSES.keys()`), and there
   are enough distinct operation-enrichment rules (public-tag,
   path-param, request-body, tier-gated) that testing each in
   isolation produced a coherent 43-test suite.

5. **Deferred `externalDocs` population** — plan mentioned per-tag
   external docs links. No external doc site exists yet;
   structure is in place but URLs are empty. Phase 193+ (mobile
   app launch) is when a docs site becomes worth publishing.

## Results

| Metric                              | Value                       |
|-------------------------------------|-----------------------------|
| `api/openapi.py` LoC                | 459                         |
| Test LoC                            | 302                         |
| Grand total (product + tests)       | 761                         |
| Tests                               | 43 GREEN                    |
| Phase 183 test runtime              | 23.16s                      |
| Track H regression (175-183)        | 291/291 GREEN (7m 01s)      |
| Tags documented                     | 10                          |
| Security schemes                    | 2 (apiKey, bearerAuth)      |
| Reusable error responses            | 7                           |
| Settings fields added               | 1 (`api_servers`)           |
| Schema version                      | 38 (unchanged)              |
| Migration                           | None                        |
| AI calls                            | 0                           |
| Network calls                       | 0                           |
| New Setting                         | `api_servers`               |

**Key finding:** the FastAPI `openapi()` override is the right
abstraction. Enriching the spec at a single choke point costs
~460 LoC and zero route-handler edits, versus ~3× that if every
route declared its own `responses=` kwarg with error envelopes.
Future route additions automatically inherit the enrichment (the
walker is path/tag-driven, not hand-mapped), and the reusable
`components.responses.*` entries mean a spec consumer can render
one description per error kind instead of 48 copies. The OpenAPI
surface is now good enough for openapi-generator to emit usable
Track I mobile SDK stubs without further polish.
