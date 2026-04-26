# Phase 187 — Auth + API Client Library

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-24

## Goal

First real backend integration for MotoDiag Mobile. Replaced the Phase 186 stub `src/api/` with a typed `openapi-fetch` client generated from a **committed snapshot** of the moto-diag backend's Phase 183 OpenAPI 3.1 spec (ADR-005). Added secure API-key storage via `react-native-keychain` (Keystore on Android). Proved end-to-end auth round-trip on an Android emulator: paste a valid key → hit `/v1/version` (unauth, connectivity smoke) → hit `/v1/vehicles` (auth, real data or typed RFC 7807 ProblemDetail error).

Also formalized the Phase 186 ble-plx in-place edit via `patch-package` + postinstall hook (so `npm install` stops wiping it) and discovered + fixed the same bug in `react-native-keychain@10.0.0` before it shipped. Added 41 Jest unit tests for `src/api/` logic.

CLI — none (mobile has no CLI).

## Outputs — actual state post-build

### New files (22)
- `api-schema/openapi.json` (219.7 KB) — committed snapshot of moto-diag `/openapi.json` (48 paths, 10 tags, 7 reusable error responses from Phase 183 enrichment). Generated directly from backend via `python -c "from motodiag.api import create_app; ..."` rather than over-HTTP, avoiding a running-server dependency for the initial snapshot.
- `src/api-types.ts` (3946 lines) — emitted by `openapi-typescript@7.13.0` from the snapshot. Committed.
- `src/api/errors.ts` — `ProblemDetail` type pulled from `components['schemas']['ProblemDetail']` (so it stays in lockstep with backend). `isProblemDetail()` narrowing predicate. `formatProblemDetail()` and `describeError()` helpers for screen-level error rendering.
- `src/hooks/useApiKey.ts` — the single public surface for API-key state. Throws a clear error if used outside `ApiKeyProvider`. Re-exports `ApiKeyContextValue` type.
- `src/contexts/ApiKeyProvider.tsx` — React Context provider. Loads key from Keychain on mount via `useEffect` with `alive` guard; exposes `{apiKey, isLoading, setApiKey, clearApiKey}`.
- `src/screens/ApiKeyModal.tsx` — pure presentational modal. Takes `onSubmit`/`onCancel` props; doesn't read Context. Validates draft (non-empty + `mdk_` prefix warning).
- `patches/react-native-ble-plx+3.5.1.patch` — hand-written unified diff removing two `if (isNewArchitectureEnabled())` guards on `apply plugin: "com.facebook.react"` + `react { ... }` config block.
- `patches/react-native-keychain+10.0.0.patch` — same shape, different library. Pre-flight discovery: keychain@10 has the identical bug as ble-plx.
- `patches/README.md` — documents patch convention + per-patch removal triggers.
- `scripts/refresh-api-schema.js` — Node script (stdlib `fetch`/`fs`). Curls `$API_BASE_URL/openapi.json` with sanity check on response shape.
- `docs/adr/005-openapi-spec-snapshot.md` — ADR: commit snapshot, not live fetch. Includes rationale, consequences, reversal triggers, implementation notes.
- `.gitattributes` — `*.patch text eol=lf` (narrow exception to the "no preemptive .gitattributes" rule; patch-package has a hard LF requirement).
- `__tests__/api/auth.test.ts` (15 tests) — applyAuth purity + Keychain round-trip + service partition args + Keychain-throws warning path.
- `__tests__/api/client.test.ts` (8 tests) — base URL resolution + auth header injection + error path (401 ProblemDetail, 200 body).
- `__tests__/api/errors.test.ts` (18 tests) — narrowing predicate (10) + formatter (4) + describeError multi-shape handling (4).

### Modified files
- `src/api/auth.ts` — replaced Phase 186 no-op stub. Added `getApiKey`/`setApiKey`/`clearApiKey` (Keychain-backed). `applyAuth(headers, apiKey?)` kept Phase 186 call-site compat via default `apiKey = null`.
- `src/api/client.ts` — complete rewrite. Phase 186's hand-written `ApiClient` interface removed; replaced with `openapi-fetch` `createClient<paths>()` returning `Client<paths>`. `MotoDiagApi` type alias; `DEFAULT_BASE_URL` constant; `ApiClientOptions` with `baseUrl`/`resolveApiKey`/`fetchImpl` test seams.
- `src/api/index.ts` — new barrel exports. `api`/`makeClient`/`DEFAULT_BASE_URL`/`MotoDiagApi`/all auth functions/all error helpers/`ProblemDetail` type.
- `src/types/api.ts` — Phase 186 ad-hoc types (`HealthCheckResponse`, `VehicleProfile`, `DtcCode`, `DiagnosticReport`) removed — they didn't match the real backend. Replaced with `VersionResponse` + `VehicleListResponse` + `VersionInfo` aliases over the generated types + re-exports.
- `src/screens/HomeScreen.tsx` — complete rewrite. Four-section layout (Backend / Auth / Authed smoke / BLE scan). `useApiKey` hook + `ApiKeyModal` wiring. Phase 186 BLE scan section preserved.
- `App.tsx` — wraps `NavigationContainer` in `<ApiKeyProvider>`. Provider order documented in a comment.
- `package.json` — added `openapi-fetch` (^0.13.0), `react-native-keychain` (10.0.0 pinned), `openapi-typescript` (^7.6.1, dev). Added scripts: `postinstall: patch-package`, `refresh-api-schema`, `generate-api-types`. Version bump 0.0.1 → 0.0.2.
- `package-lock.json` — lockfile fallout from `npm install`.
- `README.md` — init boilerplate replaced with a real project README including the Environment variables section + rebuild warning for `.env` changes.

### Deleted files
- `__tests__/App.test.tsx` — init-generated smoke test. Required `transformIgnorePatterns` gymnastics for `@react-navigation` ESM. Per Q3 decision (unit tests only), component tests are out of scope; the new `__tests__/api/` suite has real coverage.

### Phase 186 latent fix
- `src/screens/HomeScreen.tsx` line 20: `PermissionsAndroid.requestMultiple` expected `Permission[]`, Phase 186 passed `string[]`. Metro (Babel) strips types without checking so runtime was correct but `tsc --noEmit` flagged. Fixed as drive-by during HomeScreen rewrite.

## Logic — as built

### ADR-005 (committed snapshot)

Chose **snapshot committed to `api-schema/openapi.json`** over live fetch at build time. Full reasoning in the ADR. Practical consequences:

- Mobile build is self-contained — works without a running backend (plane, coffee shop, CI runner).
- Backend contract changes show up as reviewable diffs on `api-schema/openapi.json` + `src/api-types.ts`.
- Refresh via explicit `npm run refresh-api-schema` when backend contracts change.

Initial snapshot generated directly from backend's `create_app()` in-process (no HTTP required) to avoid a chicken-and-egg. Future refreshes curl the running backend's `/openapi.json`.

### Type pipeline

```
moto-diag backend /openapi.json (Phase 183)
    │
    ▼   npm run refresh-api-schema
api-schema/openapi.json  (committed)
    │
    ▼   npm run generate-api-types  (openapi-typescript 7.13.0)
src/api-types.ts  (3946 lines, committed)
    │
    ▼   import type {paths, components} from './api-types'
src/api/client.ts       ← createClient<paths>(...)
src/api/errors.ts       ← components['schemas']['ProblemDetail']
src/types/api.ts        ← VersionResponse, VehicleListResponse aliases
```

### Client shape (actual)

```ts
export const DEFAULT_BASE_URL = 'http://10.0.2.2:8000';

export interface ApiClientOptions {
  baseUrl?: string;
  resolveApiKey?: () => Promise<string | null>;
  fetchImpl?: typeof fetch;
}

export type MotoDiagApi = Client<paths>;

export function makeClient(options: ApiClientOptions = {}): MotoDiagApi {
  const baseUrl = options.baseUrl ?? Config.API_BASE_URL ?? DEFAULT_BASE_URL;
  const resolveKey = options.resolveApiKey ?? getApiKey;
  const fetchImpl = options.fetchImpl ?? fetch;

  const customFetch: typeof fetch = async (input, init) => {
    const apiKey = await resolveKey();
    const incoming = init?.headers
      ? Object.fromEntries(new Headers(init.headers).entries())
      : {};
    const finalHeaders = applyAuth({Accept: 'application/json', ...incoming}, apiKey);
    return fetchImpl(input, {...init, headers: finalHeaders});
  };

  return createClient<paths>({baseUrl, fetch: customFetch});
}

export const api: MotoDiagApi = makeClient();
```

Caller use:

```ts
const {data, error} = await api.GET('/v1/vehicles');
//      ^? VehicleListResponse | undefined
//                     ^? ProblemDetail (type narrowing works end-to-end)
```

### Auth storage (Keychain)

```ts
const KEYCHAIN_SERVICE = 'moto-diag-mobile';
const KEYCHAIN_USERNAME = 'api-key';

// Async: read from Keychain, return null on miss or access failure.
export async function getApiKey(): Promise<string | null>;
// Async: validate non-empty, persist via setGenericPassword.
export async function setApiKey(key: string): Promise<void>;
// Async: idempotent reset.
export async function clearApiKey(): Promise<void>;
// Sync: pure header-injection. apiKey default null preserves Phase 186 sites.
export function applyAuth(headers, apiKey: string | null = null);
```

### Context + hook (the only public surface for key state)

`ApiKeyProvider` wraps `<NavigationContainer>` in `App.tsx`. Hydrates via `useEffect` → `keychainGet()` → `setApiKeyState` + `setIsLoading(false)`. Exposes `{apiKey, isLoading, setApiKey, clearApiKey}` via Context.

`useApiKey()` throws a clear error if used outside the provider ("Wrap your app: `<ApiKeyProvider><App /></ApiKeyProvider>`"). This is the **only** surface components touch — Zustand swap when ADR-003 trips is invisible to call sites.

### Patches

Both `patches/*.patch` removed two `if (isNewArchitectureEnabled())` guards each. Critical context: RN 0.85 app-level autolinking emits `add_subdirectory(...codegen/jni/)` unconditionally; each library's gradle is expected to produce that directory. Libraries that gate their react-plugin apply on `newArchEnabled=true` (ble-plx 3.5.1, keychain 10.0.0) never create the directory, CMake fails. Patches force unconditional plugin apply; generated TurboModule code links but isn't dispatched at runtime because New Arch is off.

Kerwyn verified via `rm -rf node_modules && npm install`: 927 packages installed in 41s, both patches applied cleanly.

### HomeScreen layout (four sections)

```
MotoDiag
v0.0.2 · Phase 187 scaffold

┌───────────────────────────────────────┐
│ BACKEND                               │
│ ✓ Connected                           │
│ package vX.X.X                        │
│ schema v38 · api v1                   │
└───────────────────────────────────────┘
┌───────────────────────────────────────┐
│ AUTH                                  │
│ ✓ Authenticated                       │
│ mdk_live_AbCd•••                      │
│ [Replace]  [Clear]                    │
└───────────────────────────────────────┘
┌───────────────────────────────────────┐
│ AUTHED SMOKE (/v1/vehicles)           │
│ [Test /v1/vehicles]                   │
│ ✓ 0 vehicles · individual tier        │
│ quota: 5/5 remaining                  │
│ No vehicles yet — POST /v1/vehicles   │
└───────────────────────────────────────┘
┌───────────────────────────────────────┐
│ BLE SCAN (Phase 186)                  │
│ [Test BLE scan]                       │
│ Status: idle                          │
│ Devices seen: 0                       │
└───────────────────────────────────────┘
```

All buttons ≥48dp (shop-glove design rule). Green ✓ / red ✗ + text labels (colorblind-safe). Key masking shows first 13 chars + `•••`.

## Key Concepts — as used

- **`openapi-fetch` + `openapi-typescript`** — ~1kb runtime + type codegen, end-to-end type safety from Pydantic → OpenAPI → RN client methods.
- **`react-native-keychain`** — Android Keystore (hardware TEE on most devices 6.0+) / iOS Keychain Services. Service-partitioned entries; persists across app restarts, cleared on uninstall.
- **`react-native-config`** — `.env` → `BuildConfig` on Android at compile time (NOT runtime; editing `.env` requires `npm run android` not just Metro reload). Documented in README.
- **React Context** — single-store pattern without state-mgmt library (ADR-003 active). `useApiKey()` is the ergonomic seam that hides the underlying store.
- **`patch-package` + postinstall hook** — idempotent patches applied on every `npm install`. LF line endings enforced via `.gitattributes`.
- **FetchState discriminated union** — `idle | loading | success | error` pattern for async UI. TypeScript narrowing works on `.kind`.

## Verification Checklist

- [x] `api-schema/openapi.json` committed with real content (48 paths, 10 tags, 7 reusable error responses, 219.7 KB).
- [x] `npm run refresh-api-schema` implemented and ready (curls a running backend; Kerwyn hasn't run it yet — initial snapshot generated via Python in-process).
- [x] `npm run generate-api-types` produces `src/api-types.ts` without errors (3946 lines).
- [x] `src/api-types.ts` exports `paths` containing `/v1/version`, `/v1/vehicles`, and 46 other routes.
- [x] `patches/react-native-ble-plx+3.5.1.patch` exists and applies cleanly — Kerwyn verified `[applied] ✔` in npm install output.
- [x] `patches/react-native-keychain+10.0.0.patch` exists and applies cleanly — Kerwyn verified `[applied] ✔`.
- [x] `npm install` triggers `postinstall` → `patch-package` → both patches reapplied on fresh install (Kerwyn verified 927 packages in 41s, no ERESOLVE).
- [x] `rm -rf node_modules && npm install && npm run android` builds successfully (Kerwyn ran this during the architect gate smoke test).
- [x] `npm test` runs 3 test files (41 tests total); 100% pass — `3 passed, 41 passed, 0.44s`.
- [x] HomeScreen shows backend connectivity status on mount (auto `GET /v1/version` → shows real server values).
- [x] Setting an API key via modal persists to Keychain (survives app restart — Kerwyn verified the "quit and re-launch → still authed" case).
- [x] Authed `/v1/vehicles` call returns typed data when key is valid.
- [x] 401 response surfaces as a human-readable ProblemDetail message via `describeError()`.
- [x] Clearing the key removes it from Keychain + resets UI to "Not authenticated".
- [x] BLE scan button from Phase 186 still works (no-regression check per Kerwyn's guidance).
- [x] `App.tsx` wraps `NavigationContainer` in `<ApiKeyProvider>`.
- [x] ADR-005 committed to `docs/adr/`.
- [x] `npx tsc --noEmit` clean — Phase 186 latent HomeScreen type error fixed as drive-by.
- [x] `npm run lint` clean (no new lint errors introduced).

## Risks (post-build resolution)

- **Backend-must-be-running for `refresh-api-schema`** — fails loudly with actionable error message. Initial snapshot generated via Python in-process, so first-build doesn't require this.
- **`react-native-config` env-var rebuild gotcha** — documented in README's Environment variables section + ProblemDetail import note in client.ts + comment in HomeScreen. Covered from three angles.
- **Keychain Jest mocking** — inline mocks work cleanly for the 15 auth tests; no global setup needed.
- **openapi-typescript Windows CRLF noise** — didn't materialize in first run. Reactive approach (wait-and-see) correct.
- **New Arch + keychain** — found preemptively, patched. Would have repro'd Phase 186's CMake failure identically.
- **ble-plx patch regeneration correctness** — hand-written patches applied cleanly on first Kerwyn install. No round-trip needed.
- **Rate limiting during smoke test** — non-issue; Kerwyn's backend is local with no per-IP limits tripped.

## Deviations from Plan

1. **Initial snapshot generated via Python, not `npm run refresh-api-schema`.** Plan assumed the refresh script would produce the first snapshot. In practice, generating via `python -c "from motodiag.api import create_app; ..."` was faster — no server spin-up required. The refresh script exists and is ready for future backend-change refreshes; this is a small but meaningful shift from "run backend + curl" to "decouple snapshot generation from server availability."

2. **`react-native-keychain` pre-flight finding.** Not anticipated in the Phase 187 plan. During pre-flight check (per Kerwyn's guidance #8), discovered keychain@10.0.0 has the identical gradle bug as ble-plx. Second patch added; one extra bullet in Commit 1. Option A (pin keychain + patch) decided together before committing.

3. **Commit 1 added `.gitattributes`.** Not in the original plan. Rationale: patch files have a hard LF requirement for patch-package to apply cleanly; CRLF on Windows would break postinstall on fresh clones. Narrow scope (`*.patch text eol=lf` + `*.sh text eol=lf`) — not a general-purpose attributes file.

4. **Commit 3 deleted `__tests__/App.test.tsx`** instead of mocking Keychain + keeping it. The init-generated render smoke test required `transformIgnorePatterns` changes for `@react-navigation` ESM modules; per Q3 (unit tests only, no component tests) deleting was cleaner than carrying config noise for a near-useless test.

5. **Test count 41 vs ~25 planned.** Overshot because the error-helpers tests grew to 18 (10 narrowing predicate cases for full coverage of `unknown` input shapes; 4 formatter cases; 4 describeError cases). auth.test + client.test landed on-target at 15 and 8 respectively. Net positive — no dead weight, every test earns its keep.

6. **HomeScreen rewrite kept Phase 186 BLE section** (per Kerwyn's "don't regress Phase 186" guidance). Plan didn't explicitly require this but the guidance was clear; BLE scan button is intact with a `testID` added for future tests.

7. **Jest mock typing idiosyncrasy.** `jest.fn<typeof fetch>()` (one-generic form) isn't supported by the installed `@types/jest` version. Used the two-generic form `jest.fn<Promise<Response>, [RequestInfo, RequestInit?]>()`. Minor; documented in Commit 3 message.

8. **No `BUILD_NOTES.md` created.** Plan referenced it as a scratch file for the deferred subscription CLI discovery. Not needed in practice — Kerwyn ran `motodiag apikey create` directly and handled subscription via backend CLI exploration. No TBDs left in the code.

9. **Subscription CLI finding — `motodiag subscription` has no dev `create`/`grant` path.** Discovered during smoke test prep: subcommands are `cancel`/`checkout-url`/`portal-url`/`show`/`sync` — all routed through Stripe for real billing. For a dev user without a subscription, the fallback is a direct SQLite INSERT into the `subscriptions` table. For Phase 187 smoke, user id 1 already had an active subscription row from an earlier backend phase, so full happy path worked without any DB fiddling. **Capture this for Track J when we need per-phase seed data in CI:** `subscription` CLI needs a dev-only `grant` subcommand, or the test harness needs a seed-subscription fixture. Not a Phase 187 action item.

## Results

**Commits (feature branch `phase-187-auth-api`):**

| # | Hash      | Title |
|--:|-----------|-------|
| 1 | `b425e94` | deps + openapi-typescript setup + ble-plx & keychain patches + ADR-005 |
| 2 | `3362e8b` | auth context + modal + Keychain storage + auth unit tests |
| 3 | `d82a91b` | real openapi-fetch client + spec snapshot + types + 26 tests |
| 4 | `b13ebfd` | HomeScreen end-to-end smoke surface + Phase 186 type fix |
| 5 | `f30246d` | README overhaul + version bump 0.0.1 → 0.0.2 |

| Metric                              | Value                           |
|-------------------------------------|---------------------------------|
| Files created                       | 22                              |
| Files modified                      | 10                              |
| Files deleted                       | 1                               |
| Lines added (approx)                | ~13.5k (incl. 3946 generated + 219KB snapshot) |
| Tests passing                       | 41 / 41 (Jest)                  |
| Test runtime                        | 0.44s                           |
| Typecheck                           | clean (`tsc --noEmit` no output) |
| Android smoke                       | GREEN on Pixel 7 API 35 — see details below |
| Backend card                        | `✓ Connected · package v0.1.0 · schema v38 · api v1` |
| Auth card (after key entry)         | `✓ Authenticated · mdk_live_NF2a•••` |
| /v1/vehicles result                 | `✓ 0 vehicles · individual tier · 5/5 quota remaining · "No vehicles yet — POST /v1/vehicles to add one"` |
| Keychain persistence                | ✓ verified — killed app via recent-apps swipe, relaunched, Auth card immediately showed authenticated state with no prompt |
| Phase 186 BLE regression            | ✓ cycles `requesting permissions → waiting for BLE adapter → scanning → scan complete` identically to Phase 186 |
| Patch file sizes (minimal)          | ble-plx `1016B` / 29 lines · keychain `986B` / 29 lines — both touch only `android/build.gradle`, zero changes to `src/` or `ios/` |
| iOS smoke                           | deferred (no Mac access)        |
| New package dependencies            | 3 runtime (`openapi-fetch`, `react-native-keychain`, `react-native-config` already present) + 1 dev (`openapi-typescript`) |
| Patches in `patches/`               | 2 (ble-plx, keychain)           |
| ADRs added                          | 1 (ADR-005)                     |
| Package version                     | 0.0.1 → 0.0.2                   |
| Project implementation.md version   | 0.0.3 → 0.0.4 (on this closure) |
| Schema version (backend snapshot)   | 38 (Phase 183)                  |

**Key finding:** The `openapi-typescript` + `openapi-fetch` + committed-snapshot pattern delivers **exactly** the end-to-end type safety the Phase 183 OpenAPI enrichment was designed to enable. A backend contract change flows as:

1. Edit backend Pydantic model.
2. Run `npm run refresh-api-schema` on the mobile repo (curls the running backend).
3. Run `npm run generate-api-types` — the new types propagate through every `api.GET(...)` / `api.POST(...)` call site.
4. TypeScript errors point to every mobile screen that needs to refactor for the new shape.

**"Coordination" becomes "propagation."** That's the single largest value deliver of Phases 175-187 combined — the contract is executable, not descriptive, and a single npm command syncs mobile to backend. Every subsequent Track I phase (188-204) consumes this pipeline without having to invent it.

Secondary finding: the `if (isNewArchitectureEnabled())` gradle guard pattern is ecosystem-wide in RN libraries that support TurboModules but predate the 0.85 autolinking semantics change. Before installing any new RN library with native Android code + `codegenConfig`, a one-minute gradle check ("does it guard its react plugin apply behind a newArch flag?") prevents an hour of CMake diagnosis. Should become a pre-flight step documented in the mobile repo's patch README — possibly a future ADR's reversal condition ("when New Arch is enabled, both patches can be removed simultaneously since the guards become correct again").
