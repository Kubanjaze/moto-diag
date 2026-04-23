# MotoDiag Phase 183 — Phase Log

**Status:** 🟡 In Progress | **Started:** 2026-04-23
**Repo:** https://github.com/Kubanjaze/moto-diag

---

### 2026-04-23 — Plan written

Plan v1.0. Scope: polish the auto-generated OpenAPI spec so Track I
mobile clients + external consumers + Swagger UI readers get real
documentation value. New `motodiag/api/openapi.py` hooks the
FastAPI `openapi()` override point to inject `info` metadata +
`servers` list + tag catalog + `securitySchemes` (apiKey +
bearerAuth) + reusable error responses
(Unauthorized/SubscriptionRequired/Forbidden/NotFound/ValidationError/
RateLimitExceeded/InternalError all backed by the RFC 7807
ProblemDetail schema). Enrichment also walks every `/v1/*`
operation and attaches the right security + error-response refs
based on tags / path params / request bodies. Cached via
`app.openapi_schema` after first call.

No migration, no schema change, no new runtime behavior — only
what `/openapi.json` and `/docs` return changes. ~350 LoC + ~20
tests.
