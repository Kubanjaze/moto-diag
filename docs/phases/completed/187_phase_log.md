# Phase 187 — Phase Log

**Status:** ✅ Complete | **Started:** 2026-04-23 | **Completed:** 2026-04-24
**Repo:** https://github.com/Kubanjaze/moto-diag-mobile
**Branch:** `phase-187-auth-api` (5 commits; rebase-merged to `main` at v1.1 finalize)

---

### 2026-04-23 — Plan v1.0 written, committed

Plan v1.0 committed as `53310ee` on `main`. Scope: first real backend integration + Keychain-backed API key storage + paste-key modal + HomeScreen auth/connectivity/authed smoke UI + formalize Phase 186 ble-plx patch via patch-package + first Jest unit tests + ADR-005 (OpenAPI snapshot).

Three Q/A decisions locked ahead of build:
- **Q1 = A:** snapshot strategy (commit `api-schema/openapi.json`, explicit refresh).
- **Q2 = full mirror:** backend-style phase docs discipline. Committed as `265b592` alongside the plan.
- **Q3 = unit tests only:** Jest for `src/api/` logic, no RN component tests.

Kerwyn guidance integrated into plan execution:
- 5-commit feature branch cadence on `phase-187-auth-api`.
- Pre-flight Keychain New Arch check required before install.
- patch-package patches must be ≤60 lines and touch only gradle files.
- Smoke test must produce positive data signal on HomeScreen (not just status text).
- Phase 186 BLE no-regression verification required.
- Architect gate between build and v1.1 finalize.

---

### 2026-04-24 — Pre-flight

Verified:
- `.env.example` survived from Phase 186 (`API_BASE_URL=http://10.0.2.2:8000` intact).
- Existing deps unchanged; `patch-package` + `postinstall-postinstall` already in devDependencies (from Phase 186 debug session).
- Feature branch `phase-187-auth-api` created off `main`.

**Pre-flight finding: `react-native-keychain@10.0.0` has the same `isNewArchitectureEnabled()` gradle-guard bug as ble-plx.** Identical shape — `apply plugin: "com.facebook.react"` + `react { libraryName = "RNKeychain" ... }` config block both gated behind the flag. Verified by fetching v10.0.0 tag from GitHub (master + tag match). Would reproduce Phase 186 CMake failure exactly if installed without a patch.

Flagged to Kerwyn with three options (A: install + patch identically; B: downgrade to pre-codegen version; C: switch to react-native-encrypted-storage). **Kerwyn chose Option A** — install keychain@10, second patch file, same one-line regeneration flow. Proceeded with commit.

---

### 2026-04-24 — Commit 1 (`b425e94`): deps + patches + scripts + ADR-005

Infrastructure setup before any source changes.

**Package changes:**
- `openapi-fetch@^0.13.0` runtime dep.
- `react-native-keychain@10.0.0` runtime dep (pinned for patch correctness).
- `openapi-typescript@^7.6.1` dev dep.
- Scripts: `postinstall: patch-package`, `refresh-api-schema`, `generate-api-types`.

**New files:**
- `scripts/refresh-api-schema.js` — Node script (stdlib fetch), sanity-checks OpenAPI 3 shape before overwriting.
- `patches/react-native-ble-plx+3.5.1.patch` — hand-written, two hunks (plugin apply + react config block).
- `patches/react-native-keychain+10.0.0.patch` — same shape, different library names.
- `patches/README.md` — convention + per-patch removal triggers.
- `docs/adr/005-openapi-spec-snapshot.md` — ADR content.
- `.gitattributes` — `*.patch text eol=lf` (narrow exception to "no preemptive gitattributes"; patch-package requires LF).

**Verified (Kerwyn):** `rm -rf node_modules && npm install` → 927 packages installed in 41s, both patches `✔ [applied]`, no ERESOLVE.

---

### 2026-04-24 — Commit 2 (`3362e8b`): auth context + modal + Keychain storage + 15 tests

Real Keychain-backed API key storage replacing the Phase 186 stub.

**New files:**
- `src/api/auth.ts` (rewrite): `getApiKey`/`setApiKey`/`clearApiKey` (async, Keychain-backed) + `applyAuth(headers, apiKey?)` (sync, pure; Phase 186 compat via default `apiKey = null`).
- `src/contexts/ApiKeyProvider.tsx`: Context provider, hydrates from Keychain on mount with `alive` guard, exposes `{apiKey, isLoading, setApiKey, clearApiKey}`.
- `src/hooks/useApiKey.ts`: the single public surface for key state. Throws clear error if used outside provider.
- `src/screens/ApiKeyModal.tsx`: pure presentational modal, props-based, doesn't read Context. Validates draft non-empty + warns on missing `mdk_` prefix.
- `__tests__/api/auth.test.ts`: 15 tests (applyAuth purity + Keychain round-trip + service partition + Keychain-throws warning path).

**Key design note: `useApiKey()` is the only public surface.** Call sites read `const {apiKey, setApiKey, clearApiKey} = useApiKey()` with zero awareness of Context vs Zustand vs anything else. When ADR-003 trips (≥3 screens sharing state, or prop-drilling beyond 2 levels), Zustand swap is a one-PR change in `useApiKey.ts` + `ApiKeyProvider.tsx`, invisible to consumers.

**Verified (Kerwyn):** `npm test -- __tests__/api/auth.test.ts` → `15 passed, 15 total` in 1.07s.

---

### 2026-04-24 — Commit 3 (`d82a91b`): openapi-fetch client + spec snapshot + types + 26 tests

End-to-end type safety from backend to RN client.

**Pipeline built:**
- `api-schema/openapi.json` — committed snapshot (219.7 KB · 48 paths · 10 tags · 7 reusable error responses). Generated directly from backend's `app.openapi()` via in-process Python (avoiding running-server requirement for first snapshot).
- `src/api-types.ts` — 3946 lines emitted by `openapi-typescript@7.13.0`. Committed.
- `src/api/client.ts` rewrite: `createClient<paths>()`; `MotoDiagApi` type alias; `DEFAULT_BASE_URL` constant; `ApiClientOptions` with `baseUrl`/`resolveApiKey`/`fetchImpl` test seams; custom fetch wrapper that resolves API key per request and injects `X-API-Key` via `applyAuth()`.
- `src/api/errors.ts`: `ProblemDetail` type pulled from `components['schemas']['ProblemDetail']`; `isProblemDetail`/`formatProblemDetail`/`describeError` helpers.
- `src/api/index.ts`: barrel exports.
- `src/types/api.ts`: Phase 186 stubs replaced with `VersionResponse`/`VehicleListResponse`/`VersionInfo` aliases + re-exports.
- `App.tsx`: wraps `NavigationContainer` in `<ApiKeyProvider>`.
- `__tests__/api/client.test.ts`: 8 tests (base URL resolution, auth header injection, error path).
- `__tests__/api/errors.test.ts`: 18 tests (narrowing, formatting, describeError multi-shape).
- Deleted `__tests__/App.test.tsx` (per Q3; required `transformIgnorePatterns` gymnastics for `@react-navigation` ESM).

**Fixed during build:**
- jest.fn one-generic syntax incompatible with installed `@types/jest`; used two-generic form.
- `openapi-fetch` wraps fetch input in a Request object; test URL extraction required a helper.
- `HeadersInit` global name not exposed; replaced with local `HeadersLike` union.

**Verified (Kerwyn-side):** `npm test` → `3 passed, 41 passed` in 0.44s.

---

### 2026-04-24 — Commit 4 (`b13ebfd`): HomeScreen end-to-end smoke surface + Phase 186 type fix

The live demo surface — four sections giving a positive data signal on the emulator.

**HomeScreen rewrite:**
- Section 1 (Backend): auto `api.GET('/v1/version')` on mount, shows real package + schema_version.
- Section 2 (Auth): reads `useApiKey()`, Set/Replace/Clear buttons, key masked as `mdk_live_AbCd•••` for display.
- Section 3 (Authed smoke): "Test /v1/vehicles" button, shows count + first 3 vehicles + quota info + helpful "no vehicles yet" message on empty list.
- Section 4 (BLE scan, Phase 186 preserved): same button + status + device count, testID added.

`FetchState` discriminated union (`idle | loading | success | error`) threaded through the async UI; TypeScript narrows on `.kind`.

**Phase 186 latent fix:**
- `PermissionsAndroid.requestMultiple` expected `Permission[]`, Phase 186 passed `string[]`. Metro (Babel) stripped types without checking — runtime correct, tsc flagged. Fixed as drive-by.

**Verified (Kerwyn-side):** `npm test` → 41 passed. `npx tsc --noEmit` → clean (no output). Android smoke test results captured at architect gate (next entry).

---

### 2026-04-24 — Architect gate: smoke test green

Kerwyn ran the full smoke test on Pixel 7 API 35 emulator and reported back with three artifacts:

**(a) HomeScreen screenshot — four cards all populated:**
- Backend: `✓ Connected · package v0.1.0 · schema v38 · api v1` (real values from running backend).
- Auth: `✓ Authenticated · mdk_live_NF2a•••` (key `mdk_live_NF2aVuttMsn3c7iJdBw7zXeKTJscgHSi` — dev credential stored in local-only auto-memory).
- Authed smoke (/v1/vehicles): `✓ 0 vehicles · individual tier · 5/5 quota remaining · "No vehicles yet — POST /v1/vehicles to add one"`. Full happy path — not just the "clean error surfaced" gate minimum.
- BLE scan: cycles `requesting permissions → waiting for BLE adapter → scanning → scan complete` identically to Phase 186 (no regression).

**(b) Patch diff review:**
- `react-native-ble-plx+3.5.1.patch`: 1016 bytes, 29 lines, touches only `android/build.gradle`.
- `react-native-keychain+10.0.0.patch`: 986 bytes, 29 lines, touches only `android/build.gradle`.
- `patches/README.md`: 2720 bytes, documents rationale + removal triggers.
- Zero changes to `src/` or `ios/` in either patch. Architect approved.

**(c) `.env.example` verified intact** — unchanged from Phase 186 (`API_BASE_URL=http://10.0.2.2:8000`).

**Additional Kerwyn observations:**
- **Subscription CLI finding:** `motodiag subscription` subcommands are `cancel`/`checkout-url`/`portal-url`/`show`/`sync` — all real Stripe integration paths. No dev `create`/`grant` subcommand. For users without subs, direct DB insert is the fallback. User id 1 already had an active subscription from earlier backend phases, so full happy path worked without any DB fiddling.
- **Keychain cold-relaunch persistence verified:** killed app via recent-apps swipe, tapped icon to relaunch, Auth card immediately showed `✓ Authenticated · mdk_live_NF2a•••` with no prompt.

**Architect sign-off: approved. Proceed to Commit 5.**

---

### 2026-04-24 — Commit 5 (`f30246d`): README overhaul + version bump

Final pre-finalize commit.

**README.md:** init-generated RN boilerplate replaced with a real project README — status, tech stack, prereqs, setup, Environment variables section (including the `react-native-config` rebuild warning), backend-connection workflow (refresh-api-schema → generate-api-types), API key minting instructions, project structure tree, testing commands, patches section, CI status, license.

**Version bump:**
- `package.json` version `0.0.1 → 0.0.2` (first real working-auth-against-backend milestone).
- `package-lock.json` synced.

Per Kerwyn's versioning guidance: patch bumps for milestone-level scaffolding additions during early dev, minor bump (0.1.0) at first usable-by-real-user state, 1.0.0 at first store submission.

---

### 2026-04-24 — v1.1 finalize (this commit)

**Finalizing:**
- Plan → v1.1 with all Verification Checklist items `[x]` + Deviations section (9 items) + Results table (smoke test values, patch file sizes) + Key finding (coordination → propagation).
- Phase log → timestamped milestones (this file).
- Move both files from `docs/phases/in_progress/` → `docs/phases/completed/`.
- Project `implementation.md` version bump 0.0.3 → 0.0.4, Phase 187 row added to Phase History.
- Project `phase_log.md` entry for Phase 187.
- `docs/ROADMAP.md` Phase 187 marked ✅.

Rebase-merge of `phase-187-auth-api` → `main` follows this commit.

**Phase 187 closes green. Track I scorecard: 3 of 20 phases complete (185/186/187).** Next up: **Phase 188 — Vehicle garage screen** (add/edit/view bikes, VIN scanner, big touch targets). Foundation is solid — typed API client + auth context + Keychain storage + modal pattern all in place.
