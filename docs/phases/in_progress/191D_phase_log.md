# Phase 191D — Phase Log

**Status:** 🚧 In Progress | **Started:** 2026-05-04
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
