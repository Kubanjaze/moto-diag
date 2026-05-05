# Phase 191D — F9 SSOT-Constants Lint Generalization

**Version:** 1.0 | **Tier:** Standard (small) | **Date:** 2026-05-04

## Goal

Generalize Phase 191C's narrow `motodiag/no-hardcoded-model-ids-in-tests` (mobile) + `scripts/check_f9_patterns.py --check-model-ids` (backend) lint rules to "no hardcoded SSOT-managed constants in tests" — the same F9 subspecies (ii) pattern, but covering any constant that lives canonically in a single source-of-truth module rather than only model IDs. Carries forward F20 (the SSOT-constants generalization) and F21 (TAG_CATALOG-coverage check) — both filed at Phase 191B fix-cycle-5 from the same root cause: tests pinning a literal value of an SSOT-managed constant where the production-side constant moved underneath them.

Phase 191D mirrors Phase 191C's substrate-then-feature-then-meta pattern: 191B was the feature, 191C was the meta-tooling-fix-from-lessons-learned (3 instances of subspecies (ii)), 191D is the meta-tooling-refinement-from-lessons-learned (2 NEW data points from the post-191C regression sweep proving the narrow rule wasn't catching the generalized pattern).

CLAUDE.md: extends existing CLI surfaces — no new top-level commands.

## Pre-plan grep + bucketing pass (2026-05-04)

Before plan v1.0 was written, an architect-side grep + bucketing pass scanned both repos for SSOT-managed-constant literal pins in tests AND for credential-hygiene patterns in both `tests/**` and `src/**`. Per Kerwyn's checkpoint discipline ("sanity-check predicted impact BEFORE multi-file edits" — same shape as the Phase 191C 5a 50→25 confirmation), the grep result determines the commit cadence (single Commit 4 finalize vs 5a/5b split).

### Bucket 1 (SSOT-managed → opt-out with new `contract-pin` reason category)

**Backend: 5 hits** (well under 20-hit threshold for 5a/5b split):

| File | Line(s) | Constant | Pattern |
|------|---------|----------|---------|
| `test_phase184_gate9.py` | 584 | `SCHEMA_VERSION` | already fixed at fix-cycle-5 (`7d4c2f6`); lint covers the regression-shape going forward |
| `test_phase177_vehicle_api.py` | 238-240 | `TIER_VEHICLE_LIMITS["individual\|shop\|company"]` | literal-pin **with** import (5 / 50 / -1) |
| `test_phase178_session_api.py` | 575-577 | `TIER_SESSION_MONTHLY_LIMITS[...]` | literal-pin **with** import (50 / 500 / -1) |
| `test_phase181_live_ws.py` | 196 | `DEFAULT_INTERVAL_MS` | literal-pin **with** import (500) |
| `test_phase175_api_foundation.py` | 137 | `APP_VERSION` | contract assertion against `"v1"` (no import; assert on response body) |

**Mobile: 2 hits** (well under 5-hit threshold):

| File | Line(s) | Constant | Pattern |
|------|---------|----------|---------|
| `__tests__/api/client.test.ts` | 67 | `DEFAULT_BASE_URL` | literal-pin **with** import (`'http://10.0.2.2:8000'`) |
| `__tests__/hooks/useDTCSearch.test.ts` | 119 | `DTC_SEARCH_DEBOUNCE_MS` | literal-pin **with** import (300) |

**Important pattern surfaced by the grep**: 6 of 7 hits are **"literal-pin WITH import"** — the test imports the SSOT AND asserts a specific literal value as anti-regression. This is *deliberate two-source assertion design* (import the SSOT, pin a specific literal, fail loudly if either drifts). It's good test design when constants encode contractual values (tier limits → billing math, debounce timing → UX guarantees, base URL → dev backend identity). It's NOT a bug to clean up — it's intentional anti-regression scaffolding. Treated as opt-out territory with a new dedicated `contract-pin` reason category (per Kerwyn's refinement).

### Bucket 2 (fixture data, opt-out OK / already addressed)

- `test_phase110_vehicle_expansion.py:54` — migration-version test sentinel (`m.version == 999`)
- `test_phase131_cache.py:315` — `"v1"` is generic cache-key fixture, not APP_VERSION
- `test_phase191b_serve_migrations.py:90, 98, 179` — `38` / `39` are fixture-meaningful migration boundaries
- `test_phase162_5_ai_client.py` + `test_phase191b_vision_model_validation.py` — already file-level opt-outed at Phase 191C 5a (SSOT-pin / F15 anti-regression)

### Bucket 3 (credential hygiene → F23 candidate)

**Zero findings on either repo, on BOTH `tests/**` AND `src/**`.** Per Kerwyn's process refinement, the grep was extended to `src/**` to verify project secret hygiene end-to-end (not just test-time discipline). Production credentials all flow through `os.environ` / `secrets.token_urlsafe()` (backend) / `react-native-keychain` (mobile). Only operational leak vector remains (the four 191B smoke-time pastes — F16, separate family).

F23 stays purely **forward-looking guard** — the rule should still ship to catch any future regression where a test or prod file hardcodes a credential literal.

### Bonus production finding (out of F20 scope, addressed inline in Commit 2)

```
src/motodiag/intake/vehicle_identifier.py:34: HAIKU_MODEL_ID  = "claude-haiku-4-5-20251001"
src/motodiag/intake/vehicle_identifier.py:35: SONNET_MODEL_ID = "claude-sonnet-4-6"
```

Production code with literal model IDs that should reference `motodiag.engine.client.MODEL_ALIASES`. F20's rule scope (per filing) is `tests/**` only, so the lint wouldn't catch this — but it's the same F9 family playing out in production code. **Addressed inline in Commit 2** (5-line edit: `vehicle_identifier.py` imports MODEL_ALIASES + references `MODEL_ALIASES["haiku"]` / `MODEL_ALIASES["sonnet"]`).

### Plan-shape verdict per checkpoint F

- Backend 5 hits ≤ 20 + mobile 2 hits ≤ 5 → **single Commit 4 finalize is the right shape**.
- No 5a/5b split needed.

## Scope decisions locked at pre-plan Q&A (2026-05-04)

All A-H questions accepted with refinements:

- **A — Rule heuristic shape**: (i) **config-driven** with TOML on backend (`f9_ssot_constants.toml` — comments permitted, trailing commas safe, natural section grouping by source module) + JSON on mobile (`eslint-plugin-motodiag/ssot-constants.json` — mobile tooling has no native TOML). Plan-of-record: the two registries diverge in entries but share the same philosophy. Mirror the 20-char `<reason>` floor on opt-out comments from Phase 191C 5a (`MIN_OPTOUT_REASON_CHARS = 20`).
- **B — Initial registry entries**: scan-and-register confirmed; the entire `DEFAULT_*` family included (per Kerwyn's flag, Phase 191B introduced multiple env-var-overridable defaults). Findings bucketed three ways (SSOT-managed / fixture / credential), not two.
- **C — F21 scope inside 191D**: option **(b)** keep TAG_CATALOG canonical + add `--check-tag-catalog-coverage` lint mode (small + opt-in pre-commit-friendly + lives in same script). F22 (full FastAPI introspection refactor) escalation criterion: **if `--check-tag-catalog-coverage` flags drift in 3+ subsequent phases, escalate to F22 as its own phase**.
- **D — Subsume Phase 191C narrow `--check-model-ids`**: **(a) clean-deprecation at 191D finalize** (no extended deprecation grace; solo-dev with no external consumers). Plan v1.0 enumerates callers being updated: pre-commit configs, READMEs in both repos, the extended pattern doc. **NOT updated**: Phase 191C closure docs (sealed history). Extended pattern doc carries reconciliation note: *"Phase 191C's narrow `--check-model-ids` rule was generalized in Phase 191D as `--check-ssot-constants`. Closure docs from Phase 191C reference the original name; sealed history."* Mirrors the "6 vs 7 instances" reconciliation pattern from Phase 191C v1.0.1 Correction 5.
- **E — Pattern doc**: **(a) extend existing** `docs/patterns/f9-mock-vs-runtime-drift.md`. Subsection title: **"Subspecies (ii) generalized: when the test pins a literal that production code derives from an SSOT"** (per Kerwyn's refinement — generalized framing teaches the underlying pattern; "beyond model IDs" treats it as scope extension).
- **F — Severity rollout + commit cadence**: **(a) pre-scrub during planning + single Commit 4 finalize** (confirmed by the grep checkpoint above — counts ≤ 20 backend / ≤ 5 mobile).
- **G — Backend vs mobile parity**: F20 both stacks; F21 backend only.
- **H — Branch model**: `phase-191D-f9-ssot-constants-lint` branched off post-Phase-191C-merge master/main on both repos.

## New opt-out reason category: `contract-pin`

Phase 191C 5a established three opt-out reason categories (`SSOT-pin`, `meta-test`, `contract-assertion`). Phase 191D adds a fourth:

**`contract-pin`** — A test asserts a specific literal value of an SSOT-managed constant alongside an explicit import of that constant. The two-source assertion is intentional: catches drift if EITHER the production constant changes OR the contract value changes. Used when constants encode contractual guarantees (tier limits → billing, debounce timing → UX, base URL → dev backend identity).

Distinct from `SSOT-pin` (SSOT module IS the literal — Phase 79 / Phase 162.5 pattern), `meta-test` (the test IS the linter's RuleTester suite), `contract-assertion` (the literal IS the contract being pinned in isolation).

Format example:
```python
# tests/test_phase177_vehicle_api.py:238
assert TIER_VEHICLE_LIMITS["individual"] == 5  # f9-noqa: ssot-pin contract-pin: tier limit pinned for billing math regression coverage; bumping requires Stripe price re-verification
```

## Outputs

### New files (4)

**Backend (2):**
- `f9_ssot_constants.toml` — TOML registry of `{constant_name: source_module}` pairs with per-entry `description` for the WHY. Initial entries (per pre-plan grep + bonus production cleanup):
  - `SCHEMA_VERSION` from `motodiag.core.database` (the F20 case)
  - `MODEL_ALIASES` from `motodiag.engine.client` + `motodiag.shop.ai_client` (subsumes Phase 191C narrow rule)
  - `MODEL_PRICING` from `motodiag.engine.client` + `motodiag.shop.ai_client`
  - `APP_VERSION` from `motodiag.api.app`
  - `DEFAULT_VISION_MODEL` from `motodiag.media.vision_analysis_pipeline`
  - `TIER_VEHICLE_LIMITS` from `motodiag.vehicles.registry`
  - `TIER_SESSION_MONTHLY_LIMITS` from `motodiag.core.session_repo`
  - `TIER_MONTHLY_VIDEO_LIMITS` from `motodiag.api.routes.videos`
  - `PER_SESSION_COUNT_CAP` + `PER_SESSION_BYTES_CAP` from `motodiag.api.routes.videos`
  - `DEFAULT_INTERVAL_MS` + `MIN_INTERVAL_MS` + `MAX_INTERVAL_MS` from `motodiag.api.routes.live`
  - `MOTODIAG_VISION_MODEL` (env-var override default — `DEFAULT_VISION_MODEL` via `os.environ.get`)
- `tests/test_phase191d_ssot_constants_lint.py` — unit tests for the new `--check-ssot-constants` + `--check-tag-catalog-coverage` modes (~12-15 tests across 3 classes: positive cases / negative cases / false-positive guards / TOML registry parse / tag catalog coverage / contract-pin opt-out).

**Mobile (2):**
- `eslint-plugin-motodiag/ssot-constants.json` — JSON registry of `{exported_name: source_module}` pairs. Initial entries (per pre-plan grep):
  - `DEFAULT_BASE_URL` from `src/api/client`
  - `DTC_SEARCH_DEBOUNCE_MS` + `DTC_SEARCH_LIMIT` from `src/hooks/useDTCSearch`
  - `PER_SESSION_COUNT_CAP` + `PER_SESSION_BYTES_CAP` + `POLL_INTERVAL_MS` from `src/hooks/useSessionVideos`
  - `MAX_VIDEOS_PER_SESSION` from `src/screens/VideoCaptureScreen` + `src/screens/SessionDetailScreen` (note: this is a tier-relevant constant currently duplicated across two files — flag as F25 candidate during build for mobile-side SSOT consolidation; not in 191D scope)
- `eslint-plugin-motodiag/rules/__tests__/no-hardcoded-ssot-constants-in-tests.test.js` — RuleTester unit tests for the new rule (~8-10 tests covering positive / negative / opt-out / contract-pin / malformed-reason).

### Modified files (~10)

**Backend (4):**
- `docs/patterns/f9-mock-vs-runtime-drift.md` — new subsection **"Subspecies (ii) generalized: when the test pins a literal that production code derives from an SSOT"** with: F20 case study (SCHEMA_VERSION pin missed at Phase 191B finalize, surfaced 1 day later at post-191C regression), F21 case study (TAG_CATALOG videos entry missed at Phase 191B finalize, same surface), the `contract-pin` opt-out category documented with example, the `--check-model-ids → --check-ssot-constants` reconciliation note. ~150 lines added.
- `scripts/check_f9_patterns.py` — gains `--check-ssot-constants` (TOML-driven) + `--check-tag-catalog-coverage` modes; deprecates `--check-model-ids` with stub-redirect (calls `--check-ssot-constants` filtered to `MODEL_ALIASES` registry entry); CLI message: `"--check-model-ids is deprecated; use --check-ssot-constants. This stub will be removed in Phase 200+."`. Updates `EXEMPT_CONTAINER_NAMES` to be config-driven from the TOML registry's "exempt" array.
- `src/motodiag/intake/vehicle_identifier.py` — production cleanup: replace literals `HAIKU_MODEL_ID = "claude-haiku-4-5-20251001"` + `SONNET_MODEL_ID = "claude-sonnet-4-6"` with `from motodiag.engine.client import MODEL_ALIASES` + reference via `MODEL_ALIASES["haiku"]` / `MODEL_ALIASES["sonnet"]`. **Data point 1 toward F24 promotion trigger** (see scope-decision section below).
- `.pre-commit-config.yaml` — update hook entry from `--all` (which still works) to explicitly call out the new modes in the description; update README "Pre-commit hooks" section accordingly.

**Mobile (4):**
- `docs/patterns/f9-mock-vs-runtime-drift.md` — twin of backend doc subsection extension (same content, mobile-specific TS code samples for the pattern).
- `eslint-plugin-motodiag/index.js` — register the new `no-hardcoded-ssot-constants-in-tests` rule alongside the deprecated `no-hardcoded-model-ids-in-tests` (which becomes a stub-redirect that delegates to the new rule with the model-ID registry filter).
- `eslint-plugin-motodiag/rules/no-hardcoded-ssot-constants-in-tests.js` — NEW rule, JSON-driven, severity `error` from day one. Reuses the file-level opt-out + per-line opt-out infrastructure from Phase 191C's narrow rule (`MIN_OPTOUT_REASON_CHARS = 20` + `FILE_OPTOUT_SCAN_LINES = 30`). Adds `contract-pin` as a recognized opt-out reason category in the `malformedOptOut` finding's diagnostic.
- `eslint-plugin-motodiag/rules/no-hardcoded-model-ids-in-tests.js` — convert to stub-redirect that delegates to the new rule with `{registry: 'MODEL_ALIASES'}` filter. Existing RuleTester tests continue to pass via the redirect.

**Mobile READMEs + opt-out comment additions (clean-baseline application in Commit 4):**
- `README.md` (mobile) — Lint hooks section mentions the new rule + the deprecation of the narrow rule.
- 4 backend test files + 2 mobile test files gain per-line `# f9-noqa: ssot-pin contract-pin: <reason>` opt-outs (per Bucket 1 above).

### Tests

- `tests/test_phase191d_ssot_constants_lint.py` — backend lint script tests (~12-15 tests across 3 classes: TOML registry parse + positive cases + negative cases + tag-catalog-coverage + false-positive guards + contract-pin opt-out + deprecated-rule-stub-redirect).
- `eslint-plugin-motodiag/rules/__tests__/no-hardcoded-ssot-constants-in-tests.test.js` — RuleTester unit tests (~8-10 tests covering positive / negative / opt-out / contract-pin / malformed-reason / registry-driven-exemption).

## Logic

### Backend `--check-ssot-constants` mode

1. Parse TOML registry at `f9_ssot_constants.toml` (default location; `--registry PATH` override). Schema:
   ```toml
   [[constants]]
   name = "SCHEMA_VERSION"
   source_module = "motodiag.core.database"
   description = "Database schema version pin; bumped in production by every migration. Tests must import from source, not literal-pin (unless contract-pin opt-out documents the why)."
   value_type = "int"  # or "str", "dict", "tuple"

   [[constants]]
   name = "MODEL_ALIASES"
   source_module = "motodiag.engine.client"
   description = "Anthropic model alias → full ID map. Bump on Anthropic model releases. F15 / F20 anti-regression critical."
   value_type = "dict"
   exempt_keys = []  # if set, only these keys are SSOT-pinned; others are free
   ```

2. AST-walk `tests/**/*.py` for assignments / assertions / fixture-defaults whose RHS is a literal matching ANY known production-side value of any registry entry. Heuristic:
   - For string-typed entries: literal string equal to current production value → flag.
   - For int-typed entries: literal integer equal to current production value, in a context that imports the constant OR appears next to identifiers matching the registry name → flag.
   - For dict / tuple entries: each value-position literal matching any production-side value of any key → flag.
3. Honor file-level opt-outs (`# f9-allow-ssot-constants: <reason>` with 20-char floor + `# f9-allow-not-ssot: <reason>` for explicit "this constant is intentionally not SSOT-managed" cases).
4. Honor per-line opt-outs (`# f9-noqa: ssot-pin <reason>` and `# f9-noqa: ssot-pin contract-pin: <reason>` for the new category).
5. Emit findings in the same diagnostic shape as Phase 191C: `file:line: rule-name: message`.

### Backend `--check-tag-catalog-coverage` mode

1. AST-walk `src/motodiag/api/routes/**/*.py` for `APIRouter(...)` calls; extract `tags=[...]` keyword arguments.
2. Parse `src/motodiag/api/openapi.py` to extract `TAG_CATALOG`; collect `{name}` set.
3. Diff: any tag used in routes but missing from TAG_CATALOG → flag with the route file + TAG_CATALOG file:line + suggested entry shape (name + 1-line stub description).
4. Reverse-diff (any tag in TAG_CATALOG not used by any route): warn-only (might be a future-route placeholder).

### Mobile `motodiag/no-hardcoded-ssot-constants-in-tests`

1. Load JSON registry at `eslint-plugin-motodiag/ssot-constants.json` at rule-init time.
2. Visit `Literal` AST nodes in `__tests__/**/*.{ts,tsx,js}` files; check each literal value against the registry's known production values.
3. Honor file-level + per-line opt-outs same shape as backend (using JS comment syntax).
4. Special-case the deprecated `no-hardcoded-model-ids-in-tests` rule: stub-redirect that internally calls the generalized rule with `{registry-filter: 'MODEL_ALIASES'}` for back-compat; existing test files that already opt-out via `// f9-allow-model-ids: <reason>` keep working.

### Production-side bonus cleanup (Commit 2)

`src/motodiag/intake/vehicle_identifier.py` lines 34-35 currently:
```python
HAIKU_MODEL_ID = "claude-haiku-4-5-20251001"
SONNET_MODEL_ID = "claude-sonnet-4-6"
```

Replaced with:
```python
from motodiag.engine.client import MODEL_ALIASES

# Phase 191D: import-from-SSOT instead of literal pin (F9 subspecies (ii)
# generalized; F20 mitigation; same family as Phase 191B C2 fix-cycle-4).
HAIKU_MODEL_ID = MODEL_ALIASES["haiku"]
SONNET_MODEL_ID = MODEL_ALIASES["sonnet"]
```

Two references downstream in `vehicle_identifier.py` continue to work unchanged (they reference `HAIKU_MODEL_ID` / `SONNET_MODEL_ID`, which are now thin aliases to the SSOT lookup).

## Scope decision: F20 rule scope vs F24 promotion trigger

F20's rule is intentionally **tests-only** for 191D's gate-sized discipline. The `vehicle_identifier.py` finding (production-side hardcoded model ID) is the **first data point of production-side SSOT drift**, addressed inline in Commit 2 as a tiny cleanup but NOT a scope expansion.

**F24 (NEW)**: extend `--check-ssot-constants` rule scope from `tests/**` to `src/**`. **Promotion trigger**: 2+ subsequent phases surface production-side SSOT-drift findings during regular grep audits. The `vehicle_identifier.py` finding is **data point 1**; **one more triggers F24 promotion to its own phase**.

Same shape as F22's escalation criterion (TAG_CATALOG full FastAPI introspection refactor: 3+ subsequent phases of `--check-tag-catalog-coverage` drift triggers F22). Both treat deferred work as **measurable** rather than indefinitely-deferred.

**F23 (NEW)**: credential-hygiene lint — guard against future regression where any `tests/**` OR `src/**` file hardcodes a credential literal (`*_API_KEY`, `*_SECRET`, `*_TOKEN`, `*_PASSWORD`). Pre-plan grep confirmed zero current findings on either repo, both scopes; F23 ships purely as forward-looking guard. **Recommended target Phase 192+**, low priority since current state is clean. (Filed at 191D finalize to live alongside F22 / F24.)

## Key Concepts

- **TOML-driven registry on backend, JSON on mobile**: backend tooling has native `tomllib` (Python 3.11+); mobile JS tooling has no native TOML parser. Two registries diverge in entries (different surfaces) but share the same philosophy + opt-out grammar.
- **Stub-redirect deprecation pattern**: `--check-model-ids` (backend) and `motodiag/no-hardcoded-model-ids-in-tests` (mobile) both become thin stubs that delegate to the new generalized rule with a `MODEL_ALIASES` registry filter. Allows clean cutover without breaking pre-commit configs / .eslintrc.js declarations referencing the old names.
- **`contract-pin` opt-out category**: new vocabulary distinguishing intentional two-source assertion design (literal-pin WITH import) from drift-bug (literal-pin WITHOUT import). Doc'd in pattern guide + recognized by the rule's malformedOptOut diagnostic.
- **F9 subspecies-(ii) generalization**: same family as Phase 191C's narrow rule but parametrized by registry. The Phase 191C narrow rule was the proof-of-concept; 191D ships the generalized engine.
- **Pre-scrub vs warn-rollout**: Phase 191C's 5a/5b split was needed because the rule was fundamentally new + needed soak time; F20 is an extension of an already-trusted shape, so single-Commit-4-finalize suffices.

## Verification Checklist

- [ ] `f9_ssot_constants.toml` parses cleanly with all initial entries present + per-entry descriptions ≥ 30 chars
- [ ] `eslint-plugin-motodiag/ssot-constants.json` parses cleanly with all initial mobile entries present
- [ ] `scripts/check_f9_patterns.py --check-ssot-constants` runs cleanly on current backend `master` AFTER opt-out application (zero findings)
- [ ] `scripts/check_f9_patterns.py --check-ssot-constants` fires on the 5 backend Bucket-1 hits BEFORE opt-out application (positive case test)
- [ ] `scripts/check_f9_patterns.py --check-tag-catalog-coverage` runs cleanly on current backend `master` (zero findings — the videos tag was added at Phase 191B fix-cycle-5)
- [ ] `scripts/check_f9_patterns.py --check-tag-catalog-coverage` fires on a synthetic regression (delete the videos tag entry → flag with route file + TAG_CATALOG file:line)
- [ ] `scripts/check_f9_patterns.py --check-model-ids` (DEPRECATED) emits the stub-redirect message + still functions as before
- [ ] `tests/test_phase191d_ssot_constants_lint.py` passes (~12-15 tests)
- [ ] `eslint-plugin-motodiag/rules/no-hardcoded-ssot-constants-in-tests.js` loads via `.eslintrc.js`
- [ ] All new RuleTester unit tests pass (~8-10 tests)
- [ ] Running `npx eslint` on current mobile `main` produces zero `motodiag/no-hardcoded-ssot-constants-in-tests` findings AFTER opt-out application
- [ ] Running `npx eslint` against the 2 mobile Bucket-1 hits BEFORE opt-out application produces 1 finding per hit (regression coverage)
- [ ] `vehicle_identifier.py` production cleanup verified: `from motodiag.engine.client import MODEL_ALIASES` import added; `HAIKU_MODEL_ID` + `SONNET_MODEL_ID` reference `MODEL_ALIASES["..."]`; 2 downstream callers continue to work
- [ ] Backend `pyproject.toml` 0.3.0 → 0.3.1 (patch bump — 191D extends 191C's tooling; not a minor)
- [ ] Backend `implementation.md` 0.13.9 → 0.13.10
- [ ] Mobile `package.json` 0.0.8 → 0.0.9
- [ ] Mobile `implementation.md` 0.0.10 → 0.0.11
- [ ] Backend + mobile pattern doc gains the new "Subspecies (ii) generalized" subsection with F20 + F21 case studies + `contract-pin` opt-out documented
- [ ] Backend + mobile READMEs gain a brief note about the new rule + the deprecation of the narrow rule (linkback to pattern doc)
- [ ] Mobile FOLLOWUPS: F20 + F21 closed with the 191D finalize commit hash; F22 + F23 + F24 + F25 (if `MAX_VIDEOS_PER_SESSION` duplication confirmed) filed
- [ ] No regression: Phase 191C suite 17/17 PASS (after stub-redirect verification); Phase 175-184 backend integration sweep clean (~143/143 in the targeted sample); mobile Jest 293/293 (or +1-2 for new RuleTester tests if collected via jest)
- [ ] All 4 + 2 = 6 Bucket-1 findings get per-line `# f9-noqa: ssot-pin contract-pin: <reason>` opt-outs with category-tagged reasons ≥ 20 chars

## Risks

- **TOML parse-time errors at lint-init**. Bad TOML in the registry file would break the lint silently. Mitigation: registry-parse failure is itself a finding (`registry-error` diagnostic with file:line). Test coverage for malformed-TOML case in `test_phase191d_ssot_constants_lint.py`.
- **False-positives on coincidence-equal literals**. A test asserting `assert x == 5` where `5` happens to also be `TIER_VEHICLE_LIMITS["individual"]` would flag spuriously. Mitigation: heuristic narrows to literals where the import OR identifier matches the registry name; `assert response.status_code == 5` would NOT flag because no `TIER_VEHICLE_LIMITS` import or identifier nearby. Tunable; documented as known limitation in pattern doc.
- **Stub-redirect compatibility**. Pre-commit configs / `.eslintrc.js` files in older clones may still call `--check-model-ids` directly. Mitigation: the stub-redirect handles them silently; deprecation message is `WARN`-level, not error.
- **Production-cleanup risks downstream callers**. Changing `vehicle_identifier.py:HAIKU_MODEL_ID` from a literal to an SSOT lookup could break callers that imported the constant at module-load time. Mitigation: imports happen at module-load anyway (Python's MODEL_ALIASES is a module-level constant); downstream `from motodiag.intake.vehicle_identifier import HAIKU_MODEL_ID` continues to resolve to the right string.
- **Mobile ESLint ssot-constants.json missing on a fresh clone**. The plugin references the JSON file via relative require; missing file would crash the rule load. Mitigation: ship the JSON file with empty `[]` if no entries (treated as "no constants registered, rule is no-op") — never breaks the lint engine.
- **`MAX_VIDEOS_PER_SESSION` duplication across mobile screens** (`VideoCaptureScreen.tsx:75` + `SessionDetailScreen.tsx:50`). Currently both files declare a local `const`. The rule will register the SSOT location as one of these; the other becomes a duplicate. Two options: (i) consolidate to a single SSOT module before 191D ships (probably `src/types/video.ts` since it's already the home for video-typed values); (ii) file as F25 follow-up and let 191D ship with the duplication noted in the pattern doc + a deferred-cleanup F-ticket. Plan-of-record: **(i) consolidate inline in Commit 3** as a small cleanup (5-line move; both files already import from `src/types/video.ts`), then register the SSOT location in the JSON registry.
- **Phase 191C deprecation cleanup discoverability**. Deprecated `--check-model-ids` flag still exists in the wild (in this repo's own pre-commit-config + README + the Phase 191C pattern doc which is sealed history). Mitigation: 191D updates pre-commit-config + READMEs in this commit; pattern doc gets the reconciliation note; sealed Phase 191C closure docs are NOT updated (per Kerwyn's audit-trail-preservation principle).

## Commit plan (4 commits on `phase-191D-f9-ssot-constants-lint` branch on BOTH repos)

**Commit 1 — Pattern guide doc extension** (both repos). Single Builder dispatch can write both copies in parallel since they share content. ~150 lines added per repo for the new "Subspecies (ii) generalized" subsection covering: F20 case study (SCHEMA_VERSION pin), F21 case study (TAG_CATALOG videos entry), `contract-pin` opt-out category documentation, the `--check-model-ids → --check-ssot-constants` reconciliation note, and the recognition heuristic for "literal-pin WITH import" (legitimate intentional pattern) vs "literal-pin WITHOUT import" (drift-bug indicator).

**Commit 2 — Backend lint script + tests + production cleanup + .pre-commit-config.yaml** (backend repo only). New `f9_ssot_constants.toml` with all 12 initial entries. `scripts/check_f9_patterns.py` gains `--check-ssot-constants` (TOML-driven) + `--check-tag-catalog-coverage` modes; `--check-model-ids` becomes a stub-redirect with deprecation message. `tests/test_phase191d_ssot_constants_lint.py` with ~12-15 tests across 3 classes. `src/motodiag/intake/vehicle_identifier.py` production cleanup (HAIKU/SONNET_MODEL_ID → MODEL_ALIASES references). `pyproject.toml` 0.3.0 → 0.3.1 patch bump. `.pre-commit-config.yaml` updated description (entry unchanged; the `--all` flag continues to work). README "Pre-commit hooks" section updated.

**Commit 3 — Mobile ESLint plugin extension + MAX_VIDEOS_PER_SESSION consolidation** (mobile repo only). New `eslint-plugin-motodiag/ssot-constants.json` with all 7 initial entries. New `eslint-plugin-motodiag/rules/no-hardcoded-ssot-constants-in-tests.js` (severity `error` from day one). `eslint-plugin-motodiag/rules/no-hardcoded-model-ids-in-tests.js` becomes stub-redirect. New `eslint-plugin-motodiag/rules/__tests__/no-hardcoded-ssot-constants-in-tests.test.js` with ~8-10 tests. **Mobile inline cleanup**: consolidate `MAX_VIDEOS_PER_SESSION` to a single SSOT in `src/types/video.ts`; both `VideoCaptureScreen.tsx` + `SessionDetailScreen.tsx` import from there (5-line move per file). `package.json` 0.0.8 → 0.0.9. README "Lint hooks" section updated.

**Commit 4 — Clean-baseline application + finalize** (both repos). Apply per-line `# f9-noqa: ssot-pin contract-pin: <reason>` opt-outs to the 4 backend Bucket-1 files + 2 mobile Bucket-1 files (6 files / 6 single-line edits each, with category-tagged reasons ≥ 20 chars). Re-run both lint surfaces against `main` / `master` → zero findings. Move plan docs `in_progress/` → `completed/`; backend project `implementation.md` 0.13.9 → 0.13.10; backend project `phase_log.md` closure entry; ROADMAP marks ✅ on both repos; mobile project `implementation.md` 0.0.10 → 0.0.11; mobile FOLLOWUPS: close F20 + F21 with this commit's hash; file F22 + F23 + F24 (+ F25 if `MAX_VIDEOS_PER_SESSION` consolidation surfaces additional drift) for forward-looking refinements.

Each commit: backend `pytest tests/test_phase191d_*.py` green + `scripts/check_f9_patterns.py --all` green before next; mobile `npx eslint` green + RuleTester unit tests pass at Commit 4.

## Architect gate

**Single-stage gate after Commit 4** (~5-7 step smoke; no native-module integration; no feature surface — purely tooling + docs extension). Mirrors Phase 191C's gate shape:

1. Both `docs/patterns/f9-mock-vs-runtime-drift.md` files render correctly (markdown validates; cross-links resolve; case study code samples are syntactically valid; the new "Subspecies (ii) generalized" subsection appears with both F20 + F21 case studies + `contract-pin` opt-out doc'd).
2. Backend `scripts/check_f9_patterns.py --check-ssot-constants` runs against `master` → exit 0, zero findings (post-opt-out application).
3. Backend `scripts/check_f9_patterns.py --check-tag-catalog-coverage` runs against `master` → exit 0, zero findings.
4. Backend regression test reverting one of the 6 opt-outs → script fires with diagnostic naming the file + line + offending literal + suggested SSOT import.
5. Backend regression test deleting the `videos` tag from TAG_CATALOG → `--check-tag-catalog-coverage` fires.
6. Backend `scripts/check_f9_patterns.py --check-model-ids` (deprecated) emits stub-redirect message + still passes (back-compat).
7. Mobile `npx eslint` on `main` → zero `motodiag/no-hardcoded-ssot-constants-in-tests` findings.
8. Mobile lint against the 2 mobile Bucket-1 fixtures (one per finding) → 1 finding per fixture.
9. Production cleanup verified: `vehicle_identifier.py` imports MODEL_ALIASES; `HAIKU_MODEL_ID` + `SONNET_MODEL_ID` resolve to the right string at runtime (`python -c "from motodiag.intake.vehicle_identifier import HAIKU_MODEL_ID; print(HAIKU_MODEL_ID)"` → `claude-haiku-4-5-20251001`).
10. **No regression**: full backend test suite + mobile Jest suite all green (Phase 175-184 sweep clean per the targeted sample; full-regression decision deferred unless build raises new concerns).

If gate passes → v1.1 finalize. If gate fails → fix-cycle on the same branch (the failure modes for a tooling+docs-extension phase are narrow; no architect-gate rounds expected).

## Versioning targets at v1.1 finalize

- Backend `pyproject.toml`: `0.3.0 → 0.3.1` (patch — 191D extends 191C's already-shipped tooling; not a minor).
- Backend project `implementation.md`: `0.13.9 → 0.13.10`.
- Schema: unchanged at v39.
- Mobile `package.json`: `0.0.8 → 0.0.9`.
- Mobile project `implementation.md`: `0.0.10 → 0.0.11`.

## Not in scope (firm)

- **Generalize rule scope from `tests/**` to `src/**`**. This is **F24** with a measurable promotion trigger (2+ production-side findings in subsequent phases; vehicle_identifier is data point 1). Adding rule-scope generalization in 191D would expand scope and dilute the architect's intervention focus.
- **TAG_CATALOG full auto-derivation** via FastAPI introspection. **F22** with a 3+-phase escalation trigger.
- **Credential-hygiene lint at error severity from day one**. **F23** is forward-looking only — current state is clean. Ship as `warn` initially when filed; bump to `error` after a Phase 191C-style clean-baseline confirmation.
- **Frozen-reference-set assertion pattern** (`KNOWN_GOOD_TIER_VEHICLE_LIMITS = {...}` matched via `==`). Adds boilerplate without changing assertion semantics; rejected at pre-plan Q&A.
- **Auto-fix support** for the new lint rules. ESLint rules ship without `--fix` initially. Adding `--fix` is a Phase 192+ polish.
- **Publishing eslint-plugin-motodiag to npm**. Local-only plugin; no need until a second project consumes it.
- **Full backend regression at Commit 4**. The 94-min sweep ran post-Phase-191C; 191D's code delta is decorator-shape (lint additions + one-file production cleanup + opt-out comments) with effectively zero production-code surface. Targeted regression sample (Phase 191C suite + Phase 175-184 sample + new Phase 191D suite) is sufficient.

## Smoke test (architect-side, post-build, pre-v1.1)

(Same as the Architect gate above — Phase 191D's gate is the smoke. ~10 steps.)

## FOLLOWUPS update (mobile FOLLOWUPS.md, applied at Commit 4)

**Closed at 191D finalize:**
- **F20** — Generalize Phase 191C's no-hardcoded-model-ids lint to "no hardcoded SSOT-managed constants in tests." Resolved by `--check-ssot-constants` (backend) + `motodiag/no-hardcoded-ssot-constants-in-tests` (mobile).
- **F21** — TAG_CATALOG should be auto-derived from route definitions (or diff-checked). Resolved by `--check-tag-catalog-coverage` (option (b) from F21 filing); option (a) full FastAPI introspection escalated to F22.

**Filed at 191D finalize:**
- **F22** — TAG_CATALOG full FastAPI introspection refactor. Promotion trigger: 3+ subsequent phases of `--check-tag-catalog-coverage` drift.
- **F23** — Credential-hygiene lint (zero current findings; forward-looking guard against future regression). Recommended target Phase 192+ low-priority.
- **F24** — Extend `--check-ssot-constants` rule scope from `tests/**` to `src/**`. Promotion trigger: 2+ subsequent phases surface production-side findings; vehicle_identifier.py is data point 1.
- **F25 (conditional)** — Mobile-side SSOT consolidation for `MAX_VIDEOS_PER_SESSION` if Commit 3's inline cleanup turns up additional duplications in the same shape.
