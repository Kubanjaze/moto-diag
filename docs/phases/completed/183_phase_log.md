# MotoDiag Phase 183 — Phase Log

**Status:** ✅ Complete | **Started:** 2026-04-23 | **Completed:** 2026-04-23
**Repo:** https://github.com/Kubanjaze/moto-diag

---

### 2026-04-23 00:20 — Plan written, initial push

Plan v1.0. Scope: polish the auto-generated OpenAPI spec for
Track I mobile clients + external consumers + Swagger UI readers.
New `motodiag/api/openapi.py` hooks the FastAPI `openapi()`
override to inject `info` metadata + `servers` list + tag catalog
(10 tags) + `securitySchemes` (apiKey + bearerAuth) + reusable
error responses (Unauthorized / SubscriptionRequired / Forbidden /
NotFound / ValidationError / RateLimitExceeded / InternalError all
backed by the RFC 7807 ProblemDetail schema). Enrichment walks
every `/v1/*` operation and attaches the right security + error-
response refs based on tags / path params / request bodies.
Cached via `app.openapi_schema`.

No migration, no schema change, no runtime-behavior change — only
what `/openapi.json` and `/docs` return changes. ~350 LoC + ~20
tests.

---

### 2026-04-23 01:00 — Build complete

**Shipped (459 LoC product code + 302 LoC tests = 761 total):**
- `src/motodiag/api/openapi.py` (459 LoC) — static metadata
  catalogs (`TAG_CATALOG`, `SECURITY_SCHEMES`, `ERROR_RESPONSES`,
  `PROBLEM_DETAIL_SCHEMA` fallback, `PUBLIC_TAGS`,
  `PUBLIC_PATH_PREFIXES`, `_ALWAYS_TIER_GATED_TAGS`) +
  `build_openapi(app)` + `install_openapi(app)` + the
  `_walk_operations` / `_enrich_operation` walker.
- `src/motodiag/api/app.py` — one-line `install_openapi(app)`
  after routers mount.
- `src/motodiag/core/config.py` — new `api_servers` Setting
  (comma-separated, pipe-split `url|description` pairs) +
  `api_servers_list` parser property.

**Deviations:**
1. **LoC overshoot 459 vs planned 300** — static catalogs for 10
   tags + 7 error responses + 2 security schemes + the
   ProblemDetail fallback all carry long, informative descriptions
   so Swagger UI shows useful help text instead of stubs. Plan
   didn't account for the PROBLEM_DETAIL_SCHEMA fallback.
2. **`api_servers` as comma/pipe string, not JSON list** —
   `pydantic-settings` can't natively coerce a `list[dict]` from
   an env var. String + parser property matches the
   `api_cors_origins` pattern.
3. **`TAG_CATALOG` passed via `get_openapi(tags=...)`** —
   discovered during build that setting `app.openapi_tags` after
   the override fires gets ignored (the override constructs the
   schema from scratch). Fix: pass the catalog at construction
   time.
4. **43 tests vs ~20 planned** — the plan undercounted. Each
   catalog member deserved at least one assertion and every
   operation-enrichment rule (public-tag, path-param, request-
   body, tier-gated) wanted isolated coverage.

**Test results:**
- Phase 183: **43 / 43 GREEN in 23.16s** across 8 classes
  (`TestInfoBlock` ×3 + `TestServers` ×6 + `TestTags` ×3 +
  `TestSecuritySchemes` ×3 + `TestErrorResponses` ×10 [parametrized
  over 7 response names + 3 standalone] + `TestOperationEnrichment`
  ×12 + `TestCaching` ×2 + `TestModuleInvariants` ×4).
- Schema version unchanged at 38 — no migration.
- Zero AI calls, zero network.

**Key finding:** the FastAPI `openapi()` override is the right
abstraction. Enriching the spec at a single choke point costs
~460 LoC and zero route-handler edits, versus ~3× that if every
route declared its own `responses=` kwarg with error envelopes.
Future route additions automatically inherit the enrichment (the
walker is path/tag-driven, not hand-mapped). The surface is now
good enough for openapi-generator to emit usable Track I mobile
SDK stubs without further polish.

---

### 2026-04-23 01:10 — Full Track H regression complete

**Phases 175-183: 291 / 291 GREEN in 7m 01s (421.60s). Zero
regressions.** No behavioral change from Phase 183 — only
`/openapi.json` and `/docs` output changed — so all prior tests
exercise unchanged code paths.

---

### 2026-04-23 01:12 — Documentation finalized

- Plan → v1.1 with all sections updated for as-built state.
- Project `implementation.md` version bump 0.12.6 → 0.12.7 +
  Phase History row added for Phase 183.
- Project `phase_log.md` entry appended.
- `docs/ROADMAP.md` Phase 183 marked ✅.
- Docs moved from `docs/phases/in_progress/` →
  `docs/phases/completed/`.
