# Phase 191D — Phase Log

**Status:** ✅ Complete | **Started:** 2026-05-04 | **Completed:** 2026-05-05
**Repo:** https://github.com/Kubanjaze/moto-diag (backend) + https://github.com/Kubanjaze/moto-diag-mobile (mobile)
**Branch:** `phase-191D-f9-ssot-constants-lint` (created in BOTH repos at 191D pre-plan close; 4 commits planned with file overlap split per Outputs section)

---

### 2026-05-04 — Plan v1.0 written

Phase 191D opens as the second F9-family architectural intervention. Phase 191C (closed `ee42210` backend / `cd72bb9` mobile, 2026-05-04) shipped the narrow `--check-model-ids` rule + `motodiag/no-hardcoded-model-ids-in-tests` ESLint rule covering F9 subspecies (ii) for model IDs only. Phase 191B fix-cycle-5 (commit `7d4c2f6`, landed on master between Phase 191C plan + 191C build) surfaced 2 NEW data points proving the narrow rule wasn't catching the generalized pattern: SCHEMA_VERSION literal-pin in test_phase184_gate9 + TAG_CATALOG videos entry missed in api/openapi.py. Both same shape as subspecies (ii) but generalized beyond model IDs.

Phase 191D delivers the generalized rule covering any SSOT-managed constant.

**Pre-plan Q&A pinned 8 decisions before plan-writing** — same Phase 189/190/191/191B/191C discipline. A through H plus Kerwyn's three refinements:

- A — Rule heuristic: TOML-driven backend registry + JSON-driven mobile registry (mobile JS has no native TOML). Both with 20-char `<reason>` floor on opt-out comments.
- B — Initial registry entries: 12 backend + 7 mobile; all `DEFAULT_*` family included; findings bucketed three ways (SSOT / fixture / credential) not two.
- C — F21 scope: lint-check option (b); F22 escalation if drift in 3+ subsequent phases.
- D — Subsume `--check-model-ids`: clean-deprecation at 191D finalize; reconciliation note in pattern doc; sealed Phase 191C closure docs NOT updated.
- E — Pattern doc: extend existing with subsection "Subspecies (ii) generalized: when the test pins a literal that production code derives from an SSOT" (Kerwyn's refined framing).
- F — Severity rollout: pre-scrub during planning (per F's checkpoint criteria). Single Commit 4 finalize (no 5a/5b split).
- G — Both-stacks F20; backend-only F21.
- H — Branch off post-191C-merge master/main (clean fast-forward + rebase verified).

**Three operational asks accepted:**

1. **Process refinement**: extend credential-hygiene grep to `src/**` before declaring F23 free-and-clear. **Result: clean on both repos, both scopes** — confirms project secret hygiene end-to-end. F23 stays purely forward-looking.
2. **Bucket 1 default policy**: accept (i) opt-out, with new `contract-pin` reason category baked into the rule's vocabulary. Distinct from `SSOT-pin` / `meta-test` / `contract-assertion`. Pattern doc explicitly calls out literal-pin-with-import as legitimate intentional pattern with example. Rejected (ii) frozen-reference-set (boilerplate without changing semantics).
3. **Bonus production finding**: accept (a) tiny inline cleanup in Commit 2 (`vehicle_identifier.py` HAIKU/SONNET_MODEL_ID → MODEL_ALIASES). F24 promotion trigger filed: extend rule scope from `tests/**` to `src/**` if 2+ subsequent phases surface production-side findings. vehicle_identifier is data point 1.

**Pre-plan grep + bucketing pass results (pinned for plan-shape decision):**

- **Backend SSOT-managed hits: 5** (test_phase184 already fixed at fix-cycle-5; test_phase177 / 178 / 181 / 175 are the 4 remaining)
- **Mobile SSOT-managed hits: 2** (client.test.ts DEFAULT_BASE_URL pin; useDTCSearch.test.ts DTC_SEARCH_DEBOUNCE_MS pin)
- **Bucket 1 pattern surfaced**: 6 of 7 are "literal-pin WITH import" — intentional anti-regression scaffolding, not drift bug. Treated as `contract-pin` opt-outs.
- **Bucket 3 (credentials)**: 0 findings on either repo, both scopes (`tests/**` + `src/**`). F23 is forward-looking only.
- **Bonus production finding**: `src/motodiag/intake/vehicle_identifier.py:34-35` — HAIKU_MODEL_ID + SONNET_MODEL_ID literal model IDs in production code; addressed inline at Commit 2.

**Plan-shape verdict per checkpoint F**: 5 backend + 2 mobile ≤ 20/5 thresholds → **single Commit 4 finalize is the right shape**. No 5a/5b split needed.

**Files plan:**

- New backend (2): `f9_ssot_constants.toml` + `tests/test_phase191d_ssot_constants_lint.py` (~12-15 tests)
- New mobile (2): `eslint-plugin-motodiag/ssot-constants.json` + `eslint-plugin-motodiag/rules/__tests__/no-hardcoded-ssot-constants-in-tests.test.js` (~8-10 tests)
- Modified backend (4): `docs/patterns/f9-mock-vs-runtime-drift.md` (subsection extension) + `scripts/check_f9_patterns.py` (2 new modes + stub-redirect for deprecated --check-model-ids) + `src/motodiag/intake/vehicle_identifier.py` (production cleanup) + `.pre-commit-config.yaml` (description update)
- Modified mobile (4): `docs/patterns/f9-mock-vs-runtime-drift.md` (twin extension) + `eslint-plugin-motodiag/index.js` (register new rule) + `eslint-plugin-motodiag/rules/no-hardcoded-ssot-constants-in-tests.js` (NEW) + `eslint-plugin-motodiag/rules/no-hardcoded-model-ids-in-tests.js` (convert to stub-redirect)
- Plus opt-out comment additions in 4 backend + 2 mobile test files (Commit 4 clean-baseline)
- Plus mobile inline cleanup: consolidate `MAX_VIDEOS_PER_SESSION` to `src/types/video.ts` (~5-line move per file)

**Commit plan (4 commits on `phase-191D-f9-ssot-constants-lint` branch on BOTH repos):**

1. **Pattern guide doc extension** (both repos, single Builder dispatch) — F20 + F21 case studies + `contract-pin` opt-out documentation + `--check-model-ids` reconciliation note
2. **Backend lint script + tests + production cleanup + .pre-commit-config update** (backend repo only) — TOML registry + 2 new modes + deprecated stub-redirect + vehicle_identifier.py cleanup + pyproject 0.3.0 → 0.3.1
3. **Mobile ESLint plugin extension + MAX_VIDEOS_PER_SESSION consolidation** (mobile repo only) — JSON registry + new rule (severity error from day one) + deprecated stub-redirect + RuleTester tests + package.json 0.0.8 → 0.0.9
4. **Clean-baseline application + finalize** (both repos) — 6 per-line opt-outs (4 backend + 2 mobile) + lint runs clean + plan docs in_progress → completed + project doc updates + ROADMAP marks ✅ + FOLLOWUPS update (close F20 + F21; file F22 + F23 + F24 + F25 conditional)

**Versioning targets at v1.1 finalize:**

- Backend `pyproject.toml`: 0.3.0 → 0.3.1 (patch — extends 191C tooling)
- Backend project `implementation.md`: 0.13.9 → 0.13.10
- Schema unchanged at v39
- Mobile `package.json`: 0.0.8 → 0.0.9
- Mobile project `implementation.md`: 0.0.10 → 0.0.11

**Single-stage architect gate after Commit 4** (~10-step smoke; no native-module integration; no feature surface — purely tooling + docs extension). Mirrors Phase 191C's gate shape; failure modes narrow.

**Next:** plan commit on backend `master` (this file + `191D_implementation.md` v1.0), mobile branch tracks the same plan via reference to backend's centralized phase-doc ledger; then Commit 1 (pattern guide doc extension — single Builder dispatch since both repo copies share content).

---

### 2026-05-04 — Commit 1: pattern guide doc extension landed atomically

Builder-A dispatched + atomic-paired commit landed. Backend `aec38bf` + mobile `5e317a2`. New section "Subspecies (ii) generalized: when the test pins a literal that production code derives from an SSOT" added to BOTH repos' pattern guide docs:

- Backend: 634 → 802 lines (+168 / +2,430 words / +12 code blocks all `py`).
- Mobile: 686 → 889 lines (+203 / +2,817 words / +16 code blocks mix `py` + `ts`).

Subsection structure: framing + Instance #8 (SCHEMA_VERSION pin) + Instance #9 (TAG_CATALOG drift) + the new `contract-pin` opt-out category + recognition pattern (literal-pin WITH vs WITHOUT import) + `--check-model-ids → --check-ssot-constants` reconciliation note + forward-looking F-tickets signpost (F22 / F23 / F24).

Consequential summary update folded into Commit 1: "The seven instances above" → "The nine instances above" + parenthetical noting subspecies (ii) carries 3 of 9. Lines 19/23 (sealed Phase 191C closure narrative) preserved verbatim per audit-trail-preservation principle. The summary update was a mechanical consequence of adding Instances #8 + #9, not a plan-of-record decision change — folded directly rather than a separate v1.0.1 amendment.

Mobile-specific divergences per the dispatch brief: F20 case study includes BOTH Python anti-example (the actual test_phase184_gate9.py case) AND a hypothetical TypeScript equivalent; F21 case study included as cross-stack literacy with explicit "the same pattern shape exists backend-side; mobile has no current equivalent surface but might gain one if/when..." framing.

---

### 2026-05-04 — Commit 2: backend lint script + tests + production cleanup landed

Builder-B dispatched. Backend-only commit `f05da89`. 8 files / +1726 / -51.

**Logical change A** (lint extension): NEW `f9_ssot_constants.toml` (15 entries; later trimmed to 14 after fix-cycle dropped DEFAULT_VISION_MODEL) + `scripts/check_f9_patterns.py` extended with two new modes (`--check-ssot-constants` + `--check-tag-catalog-coverage`) + `--check-model-ids` deprecated as stub-redirect with stderr deprecation banner + `tests/test_phase191d_ssot_constants_lint.py` (~660 lines, 17 tests across 4 classes) + `pyproject.toml` 0.3.0 → 0.3.1 + README "Pre-commit hooks" section update + `.pre-commit-config.yaml` description update.

**Logical change B** (production cleanup): `src/motodiag/intake/vehicle_identifier.py` HAIKU_MODEL_ID + SONNET_MODEL_ID converted from literals to `MODEL_ALIASES["..."]` lookups. Filed as F24 promotion criterion data point 1.

**Trust-but-verify caught 3 surgical fixes** folded into the same commit (rather than amending after):
1. Noise-literal filter on dict-typed entries (None / True / False / 0 / "") — initial run produced 311 false positives dominated by `assert exit_code == 0` matching `TIER_MONTHLY_VIDEO_LIMITS["individual"] = 0`. Filter narrowed to 142.
2. Tightened `has_import` check — dropped reverse-direction substring match (`entry.source_module.startswith(imported + ".")`) because `from motodiag.api import create_app` was being treated as importing every `motodiag.api.*` SSOT entry. Tightening narrowed 142 → 82.
3. Dropped `DEFAULT_VISION_MODEL` from registry entirely — its value `"sonnet"` is also a `MODEL_ALIASES` dict key, so `model="sonnet"` parameter calls false-positived against the str-typed entry. Documented inline in TOML; semantically a default-value rather than a contract-value (different drift profile from the others). Drop narrowed 82 → 17.

Verification at Commit 2 close: `--check-ssot-constants` → 17 findings across 7 files (all legitimate Bucket-1 hits matching plan v1.0 prediction shape); 34/34 tests PASS in 7.79s; vehicle_identifier import path verified resolves correctly (HAIKU=`claude-haiku-4-5-20251001`, SONNET=`claude-sonnet-4-6`).

---

### 2026-05-04 — Commit 3: mobile ESLint plugin + JSON registry + MAX_VIDEOS_PER_SESSION consolidation landed

Builder-C dispatched. Mobile-only commit `b4c3555`. 12 files / +961 / -256.

**Logical change A** (ESLint plugin extension): NEW `eslint-plugin-motodiag/ssot-constants.json` (69 lines, 7 initial entries, all role: contract — explicit `role` field per entry encodes the contract-vs-default distinction at schema level rather than backend's TOML inline-comment approach for DEFAULT_VISION_MODEL) + NEW `eslint-plugin-motodiag/rules/no-hardcoded-ssot-constants-in-tests.js` (436 lines, severity error from day one with all three Commit-2 fix-cycle refinements baked in: noise-literal filter / reverse-direction import-match drop / identifier-set narrowed to registry name only) + NEW `eslint-plugin-motodiag/rules/__tests__/no-hardcoded-ssot-constants-in-tests.test.js` (231 lines, 13 RuleTester cases) + MODIFIED stub-redirect for old rule + `package.json` 0.0.8 → 0.0.9 + README + `.eslintrc.js`.

**Logical change B** (consolidation): MAX_VIDEOS_PER_SESSION moved from 2 mobile screens (SessionDetailScreen + VideoCaptureScreen) into `src/types/video.ts` as the canonical SSOT. Both screens fold into existing mixed import lines. Resolves the F25-conditional follow-up.

**Trust-but-verify caught 3 fix-ups** folded into the same commit:
1. Test-expectation tweak: Builder-C's identifier-nearby fixture had two literal `5`s on the same line; rule legitimately fires twice (one for shadow declaration, one for assertion). Updated to expect 2 errors with rationale.
2. Stub-redirect double-fire: Builder-C's deviation #2 (delegating without filter) caused every ssot-constants finding to ALSO fire under the deprecated rule's ID — every hit reported twice. Replaced with true no-op stub: deprecation banner emits, zero findings under deprecated name; canonical findings come from new rule only.
3. Pre-existing `atCap` unused-var in `VideoCaptureScreen.tsx:113` — pre-commit hook caught Phase 191B-era dead destructured name. Per CLAUDE.md "investigate-the-underlying-issue not --no-verify", removed from destructure.

Verification at Commit 3 close: 4/4 RuleTester suites PASS; npx eslint shows 13 legitimate Bucket-1 findings across 3 mobile test files + 1 informational deprecation banner (expected); Mobile Jest 293/293 PASS.

**Threshold-cross note** (documented for v1.0.1 amendment): pre-plan grep predicted 2 mobile findings; actual 13. Per plan checkpoint F (≤ 5 mobile → single Commit 4), 13 > 5 would normally trigger 4a/4b split. Sticking with single Commit 4 because mobile is already error-severity from day one (no warn → error bump step exists), no xfail tests to un-xfail, and the work volume is just "apply opt-outs + finalize docs" — the 4a/4b split mechanism doesn't apply cleanly to 191D's commit shape.

---

### 2026-05-05 — Commit 4: clean-baseline opt-outs + auth tag orphan cleanup + finalize

Architect-side work (no Builder dispatch — opt-out reason text is load-bearing teaching artifact, not formulaic boilerplate; case study #10 narrative-quality is also Architect work).

**Backend opt-outs / refactors (16 findings → 0 across 6 files)**:
- `tests/test_phase184_gate9.py:590` — SCHEMA_VERSION contract-pin opt-out citing Gate 9 anti-regression discipline + the schema-bump-with-migration protocol.
- `tests/test_phase177_vehicle_api.py:238-240` — TIER_VEHICLE_LIMITS three contract-pin opt-outs each with distinct source references (entry-tier conversion lever + 2-3 mechanic shop sizing + -1 unlimited sentinel ripple effect).
- `tests/test_phase178_session_api.py:575-577` — TIER_SESSION_MONTHLY_LIMITS three contract-pin opt-outs each citing distinct downstream surfaces (hobbyist usage profile + Phase 169 invoicing math + auth/rate_limiter dispatch).
- `tests/test_phase181_live_ws.py:162, 193, 196` — DEFAULT_INTERVAL_MS mixed treatment: 162 + 193 = fixture-data opt-outs explaining the coincidence-equal nature; 196 = contract-pin opt-out citing 500ms = 2Hz UX/bandwidth balance + api/routes/live.py docstring.
- `tests/test_phase191b_migration_039.py` — file-level `# f9-allow-ssot-constants: fixture-data` opt-out (whole file's purpose is "verify migration 039 boundary"; literal `39` IS fixture-meaningful, not drift bug).
- `tests/test_phase191b_serve_migrations.py:98` — per-line fixture-data opt-out (paired with `== SCHEMA_VERSION` cross-check above).

**Architect-side fix folded into Commit 4**: Backend rule was missing legacy `f9-allow-model-ids` back-compat for file-level opt-outs (Builder-B brief gap; mobile rule already had it). Added `model-ids` to the kinds list so files opted out at Phase 191C 5a continue to work without a duplicate opt-out comment for the new rule's name. Without this fix, `test_phase191b_vision_model_validation.py` would have required a duplicate opt-out alongside its existing `# f9-allow-model-ids:` comment.

**Backend lint state at Commit 4 close**: `scripts/check_f9_patterns.py --all` → "F9 lint: clean" (zero findings; both `--check-ssot-constants` and `--check-tag-catalog-coverage` modes green).

**Mobile opt-outs / refactors (13 findings → 0 motodiag/* lint output across 3 files)**:
- `__tests__/api/client.test.ts:67` — DEFAULT_BASE_URL contract-pin opt-out citing Phase 187 dev-loop runbook + Android emulator AVD-routed host loopback.
- `__tests__/hooks/useDTCSearch.test.ts` — mixed treatment: L119 + L120 contract-pin opt-outs (DTC_SEARCH_DEBOUNCE_MS + DTC_SEARCH_LIMIT) with UX-research source rationale; L135 + L153 + L155 + L157 + L159 REFACTORED to use new local constant `KEYSTROKE_INTERVAL_MS = 50` (eliminates 5 confusing literal-`50` timing fixtures via single named constant); L366 + L378 REFACTORED to use `DTC_SEARCH_LIMIT` directly (boundary tests at the cap value — refactor makes intent self-documenting + tracks future cap bumps automatically).
- `__tests__/hooks/useSessionVideos.test.ts:422 + 432` — REFACTORED to use `PER_SESSION_COUNT_CAP` directly (same boundary-test refactor pattern as DTC_SEARCH_LIMIT).

**Architect-side fix folded into Commit 4**: `src/hooks/useSessionVideos.ts:71-77` — `PER_SESSION_COUNT_CAP`, `PER_SESSION_BYTES_CAP`, `POLL_INTERVAL_MS` were declared as `const` (not exported); the new boundary-test refactor needed them as exports. Added `export` to all three. The act of making the SSOT actually importable IS the F9 mitigation pattern playing out — registries register source modules; source modules must export the constants. Surfaces a meta-finding: the 191D rule registered three SSOT entries the source module didn't export; future entries should be export-verified at registration time (note for v1.0.1 amendment).

**Plus one self-referential opt-out**: `__tests__/hooks/useDTCSearch.test.ts:54` — the new local constant `KEYSTROKE_INTERVAL_MS = 50` itself fires the rule (because DTC_SEARCH_LIMIT is imported in the file + 50 is its live value). Per-line `// f9-noqa: ssot-pin fixture-data` opt-out documents the self-referential nature: the constant exists specifically to ELIMINATE 5 ambiguous literal-`50`s; opting out 1 finding to enable that cleanup is a fair trade.

**Mobile lint state at Commit 4 close**: `npx eslint` → 0 motodiag/* findings (only the one-time deprecation banner from the no-op stub remains; expected). Mobile Jest 293/293 PASS.

**Auth tag orphan cleanup**: removed `{"name": "auth", ...}` from `src/motodiag/api/openapi.py:62` — was a Phase 183 forward-looking placeholder for API-key + subscription + Stripe-webhook routes that never materialized as a separate `tags=["auth"]` router. Auth/billing surface lives in `billing.py` (tags=["billing"]) + `meta.py` (tags=["meta"]); subscription tier management is CLI-only via `motodiag subscription set` (Phase 191B fix-cycle-3). Inline comment documents the deletion + protocol for re-adding when actual auth routes materialize ("re-add this entry with the route declaration in the same commit"). The protocol matters more than the deletion.

**Pattern doc extension** (both repos): added Instance #10 case study (200-300 words; full git-blame narrative + 378-day-latency calculation + the architectural takeaway "the value of a lint rule is most visible on its first run against an existing codebase, when latent drift gets surfaced all at once") + layered-history note at top of each doc (early sections snapshot Phase 191C state at 7 instances; later sections extend at Phase 191D to 10 — sealed-history numbers in early sections preserved verbatim per audit-trail-preservation principle) + subspecies summary updated to 10 instances / 4 of 10 in subspecies (ii).

**Phase doc finalize**:
- `docs/phases/in_progress/191D_implementation.md` v1.0 → v1.1 with Verification Checklist all `[x]`-marked + new Deviations from Plan section + Results table + key finding.
- This `191D_phase_log.md` gains the Commits 1-4 entries (this section).
- Both files moved `docs/phases/in_progress/` → `docs/phases/completed/`.

**Project-level updates**:
- Backend `implementation.md` 0.13.9 → 0.13.10 + Phase History table gains Phase 191D row.
- Backend `phase_log.md` gains 2026-05-05 timestamped entry recording the 191D closure + the doc bump.
- Backend `docs/ROADMAP.md` Phase 191D row marked ✅.
- Mobile `implementation.md` 0.0.10 → 0.0.11 + Phase History table gains Phase 191D row.
- Mobile `docs/ROADMAP.md` Phase 191D row marked ✅.

**Mobile FOLLOWUPS update**:
- F20 closed with this commit's hash.
- F21 closed with this commit's hash; resolution narrative cites case study #10's auth tag orphan as inaugural Phase 191D finding.
- F22 (TAG_CATALOG full FastAPI introspection refactor) — filed for future escalation; trigger = drift in 3+ subsequent phases.
- F23 (credential-hygiene lint, forward-looking guard against future regression) — filed; zero current findings.
- F24 (extend `--check-ssot-constants` rule scope from `tests/**` to `src/**`) — filed; vehicle_identifier.py is data point 1; trigger = 2+ subsequent production-side findings.
- F25 (mobile-side SSOT consolidation for MAX_VIDEOS_PER_SESSION) — explicitly filed as **NOT filed**; resolved inline at Phase 191D Commit 3. Empty F-ticket prevents future re-litigation; audit trail discipline.
- F26 (NEW): formal API versioning ADR — filed because Phase 191D's rule has a coverage gap on the APP_VERSION case (rule's `has_import` heuristic doesn't fire when a constant is imported from a parent package rather than directly from the source module; `from motodiag.api import APP_VERSION` doesn't match `motodiag.api.app` source registration). Test_phase175_api_foundation.py:137 should fire under stricter governance — filed as F26 with the gap documented as imported-names heuristic improvement candidate for v1.0.1 amendment.

**Architect gate**: implicit / self-passing per Phase 191D plan's gate definition. The gate's pre-conditions (lint clean both repos + tests green + opt-outs applied with project-context reasons + finalize docs) ARE the Commit 4 work. No separate architect-gate round needed for a docs+tooling phase.

**Final lint baseline at Commit 4 close**:
- Backend `--all`: F9 lint clean.
- Mobile `npx eslint`: 0 motodiag/* findings.
- Backend tests: 34/34 PASS (191C + 191D suites).
- Mobile Jest: 293/293 PASS.
- Pattern doc layered-history note + Instance #10 + summary update lands in both repos.

**Phase 191D closes here.** Next: Phase 192 — Diagnostic report viewer per ROADMAP.
