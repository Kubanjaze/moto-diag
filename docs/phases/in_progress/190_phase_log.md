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

---

### 2026-04-27 — Build commits 1-5 landed locally on `phase-190-dtc-code-lookup-screen`

Five commits per the plan; tests grew 162 → 177 (+15: 5 useDTC + 10 useDTCSearch); typecheck clean every commit; gradle smoke clean; mobile package version 0.0.4 → 0.0.5. Branch local-only per Phase 188/189 precedent.

| # | Hash | Title |
|--:|------|-------|
| 1 | `632207e` | DTC types + useDTC + DTCDetailScreen + register on both stacks |
| 2 | `e62f028` | SessionDetail fault-code tap → DTCDetail (the cross-link) |
| 3 | `680af57` | useDTCSearch (debounced 300ms with race cancellation) + DTCSearchScreen |
| 4 | `ee478df` | HomeScreen DTC lookup Section entry point |
| 5 | `d09ed21` | README + version 0.0.5 |

Handed to Kerwyn for the architect-gate smoke (17 steps).

---

### 2026-04-27 — Architect gate ROUND 1: FAILED (3 bugs caught at Step 11)

Steps 1-10 green: HomeScreen entry, DTCSearchScreen mounts + empty state, debounce contract verified end-to-end (slow typing produced 3 settled requests for P/P0/P01; rapid P0171 produced exactly 1; backend logs confirmed), result rows render with code+description+severity+chevron, page-cap footer "Showing 50 of 822 matches" (math correct, copy useful), ZZZZZZ no-results state post-debounce, clear input returns to clean idle.

**Stopped at Step 11 due to Bug 2.** Steps 11-17 not executed (DTCDetailScreen unrenderable for the session-tap path).

#### Bug 1 — DTCSearchScreen duplicate-key React warning + 7+ visually identical rows

Severity: must-fix-before-merge.

Symptom: typing "P0" or "P01" → toast "Encountered two children with the same key, ..." + first 7+ rows visually identical (all "P0100 / Mass or Volume Air Flow Circuit Malfunction / Medium"). Tapping different P0100 rows opened DTCDetailScreen with identical content (Make = "Generic", same description / causes / fix summary).

Root cause: FlatList keyExtractor used `item.code` alone. Backend search returned multiple rows with the same code (legacy duplicate NULL-make rows from re-seeded generic.json — Bug 3a). React's "two children with the same key" warning + undefined-reconciliation behavior.

#### Bug 2 — DTCDetail "[object Object]" on 404 (Phase 188 Bug 1 reincarnated, different code path)

Severity: must-fix-before-merge. Hard fail at Step 11.

Symptom: tap P0171 fault-code row in SessionDetail → DTCDetailScreen opens with title "Couldn't load DTC", body "[object Object]", Retry/Back buttons. Backend terminal: GET /v1/kb/dtc/P0171 → 404.

Root cause stack:
- KB endpoints (`kb.py`) use FastAPI's stock `raise HTTPException(404, detail=...)` — body shape is `{detail: string}`, NOT Phase 175's ProblemDetail envelope (`{title, status, detail?}`). `isProblemDetail` returned false; `describeError` fell through to `String(err)` → `"[object Object]"`.
- The Phase 190 commit-1 implementation distinguished 404 from generic errors via substring matching on the rendered string (`error.toLowerCase().includes('not found')`). With "[object Object]" as the message, that check failed → screen showed the generic-error branch (Retry/Back) instead of the dedicated "DTC code not found" UX.

Same flavor as Phase 188 Bug 2 (HTTPValidationError unwrap), different shape.

#### Bug 3 — DTC catalog missing P0171 + other common codes

Severity: must-fix-before-merge. Backend issue.

Symptom: GET /v1/kb/dtc/P0171 → 404. Phase 189's own smoke spec used P0171 as the example fault code. Search for "P01" returned 822 matches (per Step 8 footer) but direct GET 404'd — meaning either the catalog was missing P0171 (truly absent) OR there was a code-format mismatch between search and direct-lookup.

Root cause split:
- **3a (loader)**: SQLite's `UNIQUE(code, make)` constraint doesn't enforce uniqueness when `make IS NULL` (NULL is not equal to NULL in UNIQUE semantics). Each `motodiag db init` re-seeded generic.json, accumulating duplicate NULL-make rows. This explained the 822 match count for "P01" (small set of generic codes blown up by repeated seeding).
- **3b (catalog gap)**: generic.json shipped 20 codes total; P0171 + most-cited common OBD-II codes were genuinely not in the seed at all.

---

### 2026-04-27 — Commit 6 (`d028445`) FIX: DTCSearchScreen composite keyExtractor (Bug 1)

`src/screens/dtcSearchHelpers.ts` (new): pure helper module exporting `dtcResultKey(item, index)` that returns `${index}-${code}-${make ?? 'generic'}`. Index alone guarantees uniqueness; layering code + make keeps the key human-debuggable. Same separation pattern as `sessionFormHelpers.ts` (Phase 189 commit 5) so unit tests can import without pulling the api/keychain graph through the screen entry. DTCSearchScreen FlatList passes the new helper as keyExtractor.

`__tests__/screens/DTCSearchScreen.test.ts` (new): 6 tests covering distinct-rows path, the bug-1 scenario (7 identical-code rows all keying distinctly via index), legitimate same-code multi-make case (generic + harley_davidson), 'generic' placeholder for null make, verbatim make pass-through, mixed-input no-collisions.

Phase 191 polish (filed as follow-up, NOT in scope here): even with unique keys, visually identical rows in search results are confusing UX. A small chip showing make/family ("Honda" / "Generic") next to the code on the result row makes legitimate same-code multi-make results scannable.

Tests: 177 → 183.

---

### 2026-04-27 — Commit 7 (`744becf`) FIX: DTCDetail typed error, no more [object Object] (Bug 2)

`src/hooks/dtcErrors.ts` (new): `DTCError` discriminated union (`'not_found' | 'server' | 'network' | 'unknown'`) + `classifyDTCError(args)` + `extractErrorMessage(err)` helpers. Pure functions, no React. `extractErrorMessage` handles BOTH Phase 175 ProblemDetail (title + optional detail) AND FastAPI HTTPException default (`{detail: string}`); falls back to null for unrecognized shapes so callers synthesize a meaningful fallback (never `[object Object]`).

`src/hooks/useDTC.ts`: error type changed from `string | null` to `DTCError | null`. Reads `response.status` from the openapi-fetch tuple (was previously discarded) and forwards through `classifyDTCError`. Catch-block thrown errors route to `kind: 'network'`.

`src/screens/DTCDetailScreen.tsx`: switches on `error.kind` via a `Record<DTCError['kind'], string>` title map. `not_found` → "DTC code not found" + spelling-check hint + no Retry (per spec); `network` → "No connection to backend" + Retry; `server` → "Server error" + Retry; `unknown` → "Couldn't load DTC" + Retry. Replaces the brittle substring check with a discriminator-based switch.

`__tests__/hooks/dtcErrors.test.ts` (new): 27 tests paralleling Phase 188 commit-7's 17 HVE tests. extractErrorMessage (8: ProblemDetail + FastAPI shapes + defensive null/undefined/primitive/unrecognized); classifyDTCError 404 not_found (3: FastAPI shape, ProblemDetail shape, empty-body fallback); 5xx server (3: 500/502/503); network (2: Error instance, raw string); unknown (4: 401/403/no-status/422); regression guard explicitly asserting no "[object Object]" output (3).

`__tests__/hooks/useDTC.test.ts`: 404 test rewritten with the real FastAPI shape (was using Phase 175 envelope shape in commit 1 — mock didn't match what the real backend returns). New 500 (server) and thrown-Error (network) tests.

Tests: 183 → 206 (+27 dtcErrors + 2 new useDTC + 1 replaced).

---

### 2026-04-27 — Commit 8 (`3d3e7ab`) FIX: backend DTC seed + idempotent loader (Bug 3)

Pushed to `Kubanjaze/moto-diag` master (backend repo, not the mobile feature branch).

`data/dtc_codes/generic.json`: expanded 20 → 35 codes. Added: P0171/P0172/P0174/P0175 (fuel-trim family — the most-cited OBD-II codes); P0299 (turbo/SC underboost); P0302/P0303/P0304 (extends the existing P0301 misfire family); P0430 (catalyst bank-2 companion to existing P0420); P0440/P0442/P0455 (EVAP general/small-leak/gross-leak); P0506/P0507 (idle RPM-low and RPM-high); P0521 (oil pressure sensor — with HARD WARNING in fix_summary to verify with mechanical gauge before assuming sensor failure).

`src/motodiag/knowledge/loader.py`: `load_dtc_file` now pre-deletes any rows matching (code, make) pairs from the file before inserting. NULL-make rows use `DELETE WHERE code = ? AND make IS NULL` (since UNIQUE(code, make) can't enforce this). Re-running the loader on the same file is now idempotent. Existing dev databases self-clean their accumulated NULL-make duplicates on the next re-seed via this pre-delete.

`tests/test_phase05_dtc.py`: `test_load_real_generic` updated `count == 20` → `>= 35` plus spot-check assertions for P0171/P0300/P0301/P0420/P0440/P0455 presence (a future seed regression dropping any of these fails the test loudly). Two new tests: `test_reload_same_file_is_idempotent_for_null_make` (loads same file 3× → row count stays at 2) and `test_reload_dedups_existing_null_make_duplicates` (manually inserts 5 NULL-make P0100 dups, runs loader, asserts only 1 remains — simulates the architect's emulator-DB state).

Verified:
- `tests/test_phase05_dtc.py`: 17 / 17 green (was 14, +3 new).
- Targeted KB regression (`test_phase09_search` + `test_phase111_kb_schema_expansion` + `test_phase128_kb` + `test_phase179_kb_api` + `test_gate1_integration`): 97 / 97 green.

---

### 2026-04-27 — Re-gate handoff

Architect's emulator backend needs `motodiag db init` re-run to (a) pick up the new common codes, (b) self-clean accumulated NULL-make duplicates via the new loader pre-delete. After that, the mobile feature branch (now 7 commits — 5 build + 2 fix) holds the typed-error contract and the composite keyExtractor; both work paired with the backend Bug 3 fix.

Re-smoke resumes from Step 11 (Sessions tab → SessionDetail → tap P0171 fault-code row). Steps 1-10 are confirmed and don't need re-running unless a fix touched search/debounce code (commit 7 didn't; commit 6 changed the keyExtractor only).
