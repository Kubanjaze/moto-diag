# Phase 190 — Phase Log

**Status:** 🚧 In Progress | **Started:** 2026-04-27
**Repo:** https://github.com/Kubanjaze/moto-diag-mobile (code) + https://github.com/Kubanjaze/moto-diag (docs)
**Branch:** `phase-190-dtc-code-lookup-screen` (will be created in mobile repo at Commit 1)

---

### 2026-04-27 — Plan v1.0 written

**Scope locked (after Q&A with Kerwyn):**

1. **Nav placement = option (a):** DTCSearch + DTCDetail on `HomeStack` (general lookup launcher); `DTCDetail` only on `SessionsStack` (cross-link from fault-codes tap; no DTCSearch needed inside a session because the user already has codes in front of them at session time).
2. **Filter chips MVP scope = none:** ship search-on-text only. Backend supports category/severity/make filters, mobile defers to Phase 191 or follow-up.
3. **DTC severity rendering = reuse `sessionEnums.ts`:** import `SEVERITY_OPTIONS` + `SEVERITY_LABELS` + `renderSeverityForView` directly. Don't rename the file (more churn than the file-name-vs-content drift is worth). 2-line top-comment in `sessionEnums.ts` documents the cross-use.
4. **"Add this DTC to current session" affordance = skip.** Append flow stays inside SessionDetail's existing inline append input. Global "open session" state would need ADR-003 revisiting.

**Roadmap reminder:** Phase 190 was originally "DTC code lookup screen" (was 177); swapped with Phase 189 ("Interactive diagnostic session" was 178) at Phase 189 plan time so the canonical mechanic workflow shipped first. Phase 190 now picks up DTC lookup as a standalone screen + the cross-link integration into Phase 189's SessionDetail (where Phase 189 explicitly carried "raw P0171 codes only" as a known gap).

**Backend surfaces consumed (all Phase 179, all `require_api_key` only — NO `require_tier`, KB is core product not premium):**

- `GET /v1/kb/dtc?q=&limit=` — search (Phase 190 sends q + limit only)
- `GET /v1/kb/dtc/{code}` — single fetch (404 if unknown; ProblemDetail rendered via existing describeError)

`GET /v1/kb/dtc/categories` not consumed (filters deferred). `DTCCategoryResponse` type alias still ships in `src/types/api.ts` to future-proof the filter-chip work.

**No backend changes.** No schema changes (still v38). No new ADR. No new runtime deps.

**Files plan:**

- New (4): `DTCSearchScreen.tsx` / `DTCDetailScreen.tsx` / `useDTCSearch.ts` / `useDTC.ts`.
- Modified (5): `src/types/api.ts` (DTC type aliases) / `src/navigation/types.ts` (extend HomeStackParamList + SessionsStackParamList) / `HomeStack.tsx` (register DTCSearch + DTCDetail) / `SessionsStack.tsx` (register DTCDetail only) / `HomeScreen.tsx` (new "DTC lookup" Section) / `SessionDetailScreen.tsx` (fault-code rows tappable + chevron).
- New tests (~12-15): `__tests__/hooks/useDTC.test.ts` (5 mirroring useSession) + `__tests__/hooks/useDTCSearch.test.ts` (7-9 covering debounce contract: empty-query short-circuit, rapid-type-collapses-to-one-call, race-cancellation, error path, results/total/loading transitions).

**Commit plan (5 commits on `phase-190-dtc-code-lookup-screen` feature branch):**

1. DTC types + useDTC hook + DTCDetailScreen view-only + register DTCDetail on both stacks.
2. SessionDetailScreen fault-code tap → DTCDetail integration (the cross-link).
3. useDTCSearch hook (debounced 300ms) + DTCSearchScreen with all 6 states + register DTCSearch on HomeStack.
4. HomeScreen "DTC lookup" Section entry point.
5. README + project structure update + version bump 0.0.4 → 0.0.5.

If architect gate finds bugs, fix commits land before rebase-merge (Phase 188 precedent: 5 build + 3 fix). Phase 189 round-1-clean is the better-case precedent enabled by the pre-implementation sketch sign-off pattern. Phase 190 has fewer state-machine surfaces than Phase 189 (no severity Other… equivalent), but the debounce-race contract is non-obvious — short pre-Commit-3 design check if anything ambiguous emerges before that hook ships.

**Versioning targets at v1.1 finalize:**

- Mobile `package.json`: 0.0.4 → 0.0.5.
- Mobile `implementation.md`: 0.0.6 → 0.0.7.
- Backend `implementation.md`: 0.13.5 → 0.13.6 (Track I phase 6 of 20).
- Backend `pyproject.toml`: unchanged.

**Smoke-test plan written into v1.0** (17 steps; less than Phase 189's 20 because no severity round-trip equivalent). To be executed by Kerwyn on emulator at the architect gate after Commit 5 lands.

**Next:** plan commit on backend `master` (this file + 190_implementation.md v1.0), then create `phase-190-dtc-code-lookup-screen` branch in mobile repo and start Commit 1 (DTC types + useDTC + DTCDetailScreen).
