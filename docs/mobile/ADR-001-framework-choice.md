# ADR-001 — Mobile Framework + Project Architecture

**Status:** Accepted — 2026-04-23 (Phase 185, Track I opener). **Partially superseded** for Phase 186 operational specifics by [`phase-186-handoff.md`](./phase-186-handoff.md) on 2026-04-23 (same day).
**Supersedes:** None (first ADR).
**Superseded by:** None for the framework-choice decision (D1: React Native bare, D2: TypeScript strict, D3: sibling repo, D5: openapi-fetch, D7: ble-plx behind provider seam — all still authoritative). **Superseded operationally** for D4 (state management) and D6 (offline) + CI specifics: the Phase 186 handoff defers state management and CI wholesale, and does not install TanStack Query / persistence libraries in the scaffold. See the handoff's ADR-003 (state) and ADR-004 (CI) for the binding Phase 186 stance; this document's D4 + D6 descriptions now describe the *eventual target*, not Phase 186 scope.

**Operational contract for Phase 186:** follow `phase-186-handoff.md` — it locks RN 0.85.x pin, New Architecture disabled pending ble-plx #1277, state management deferred, CI deferred, backend client stubbed (no TanStack Query in 186), and bundle ID `com.bandithero.motodiag`. The 7 high-level decisions here (framework, language, repo, state eventually, API client pattern, offline eventually, BLE seam) remain the Track I north star.

---

## Context

MotoDiag's Track H (Phases 175-184) closed with a 57-endpoint
HTTP API + 1 WebSocket + a fully-documented OpenAPI 3.1 spec.
Track I (Phases 185-204) builds the mobile app that consumes
this API. The primary users are motorcycle mechanics working in
shops — greasy hands, gloves on, loud environments, often
outdoors, frequently offline. The secondary users are DIY riders
saving diagnostic sessions to their own phones.

Target device range (from roadmap):
- iOS: iPhone 8 (iOS 15+) and newer — ~99% of active iPhones.
- Android: Android 8.0 Oreo and newer — old Samsungs, budget
  phones, tablets.
- Screen sizes: 4.7" to 12.9".
- Must run smoothly on $100-200 Android devices.

Hard feature requirements (from roadmap) that shape framework
choice:
- **Bluetooth OBD adapter** (Phase 196) — BLE pairing + streaming
  from the bike's ECU.
- **Camera + video** (Phases 191, 194) — film running bike, VIN
  scanner, photograph parts.
- **Voice input** (Phase 195) — describe symptoms by talking.
- **Live sensor dashboard** (Phase 197) — real-time gauges, may
  run in background during a test ride.
- **Offline-first** (Phase 198) — full DTC database cached,
  queue API calls, sync later.
- **Push notifications** (Phase 199) — work-order updates,
  diagnostic results, parts arrival.

Developer context:
- Solo builder. Two separate codebases (native Swift + native
  Kotlin) would halve velocity for no proportional gain.
- Backend is Python + FastAPI with a rigorously-enriched OpenAPI
  3.1 spec (Phase 183). The contract is the spec, not the code.
- User's workspace convention: one project per sibling directory
  at `C:\Users\Kerwyn\PycharmProjects\<repo>\`.

---

## Decision

Seven decisions, each addressed as its own ADR section. The
framework choice (React Native, bare) is the root decision;
everything else follows.

### D1. Framework: React Native (bare workflow)

**Decision:** Build the mobile app in React Native using the
bare workflow (Metro + native Xcode / Android Studio projects),
**not** Expo managed.

**Alternatives considered:**

| Option | Shared codebase? | BLE support | Native audio/video | Dev velocity | Reject reason |
|--------|------------------|-------------|---------------------|--------------|---------------|
| React Native (bare) | ✅ iOS + Android | ✅ `react-native-ble-plx` | ✅ full native access | High | **Chosen** |
| React Native (Expo managed) | ✅ | ⚠️ Expo dev client only | ⚠️ restricted | Higher initially | BLE + audio constraints force eventual ejection |
| Flutter | ✅ iOS + Android | ✅ `flutter_blue_plus` | ✅ | High | Smaller ecosystem for hardware; Dart is a second language to master alongside Python |
| Swift + Kotlin native | ❌ two codebases | ✅ | ✅ | -50% (two apps) | Solo developer; two codebases = half velocity |
| PWA / Capacitor / Ionic | ✅ | ❌ no reliable BLE | ⚠️ browser-sandboxed | Moderate | BLE + background audio require native APIs PWAs can't access |

**Why React Native wins:**

1. **Shared codebase** — one TypeScript codebase ships to iOS
   App Store and Google Play Store. Solo-dev-sustainable.
2. **Mature hardware-integration ecosystem** — BLE, camera,
   audio, Keychain/Keystore, push notifications, background
   tasks, file system all have battle-tested RN libraries.
3. **TypeScript continuity** — the same TS ecosystem hosts the
   `openapi-typescript` / `openapi-fetch` tools that give us
   end-to-end type safety from the Phase 183 OpenAPI spec.
4. **Debuggability on device** — Flipper + React DevTools +
   Hermes debugger cover the mobile-specific debug needs Flutter
   matches but doesn't exceed.

**Why bare, not Expo managed:**

The Expo managed workflow restricts native-module additions.
The roadmap has at least three phases that push against managed
constraints:

- **Phase 196 Bluetooth OBD** — `react-native-ble-plx` is
  flagged as "unsupported" in Expo managed. The workaround is
  Expo's dev client, which is effectively "bare with Expo
  tooling on top" — the tooling tax without the managed
  simplicity.
- **Phase 195 voice input** — `@react-native-voice/voice` or
  custom audio sessions for symptom dictation. Expo managed's
  `expo-speech` covers TTS but not speech-to-text with the
  customization this app needs.
- **Phase 197 live sensor dashboard background mode** — iOS
  `bluetooth-central` background mode entitlement requires an
  `Info.plist` edit Expo managed hides behind an EAS config
  layer. Bare's direct access is more predictable.

Starting bare removes the "move off Expo" migration that would
otherwise hit around Phase 196.

**Consequences:**

- ✅ Full native-module access from day one.
- ✅ Direct `Info.plist` / `AndroidManifest.xml` edits — no layer
  in between.
- ✅ Expo's individual packages (e.g., `expo-camera`,
  `expo-image-picker`) still usable in bare RN; we pick à la
  carte.
- ❌ Must maintain iOS + Android toolchains locally (Xcode +
  Android Studio + JDK).
- ❌ CI/CD setup is more involved than Expo EAS Build
  (Phase 186 scope).
- ❌ OTA (over-the-air) updates via CodePush require separate
  setup — acceptable; App Store submissions are the delivery
  path for the first release.

### D2. Language: TypeScript `strict: true`

**Decision:** TypeScript everywhere. `"strict": true` in
`tsconfig.json` from the first file. **No** `any` types except
at clearly-marked external-boundary adapters (and those must
have a typed wrapper function exposed to the rest of the
codebase).

**Alternatives considered:**

- **Plain JavaScript** — rejected. A multi-phase mobile app
  without static types will accumulate runtime bugs the backend
  contract (Phase 183) explicitly prevents.
- **TypeScript with `strict: false`** — rejected. Relaxed TS
  drifts toward any-typed JS with syntax decoration; the
  type-safety value proposition disappears.
- **Flow** — rejected. Effectively dead project.

**Consequences:**

- ✅ `openapi-typescript` generates typed client methods that
  flow through to every React component.
- ✅ IDE refactoring / rename safely propagates.
- ✅ React prop types auto-inferred.
- ❌ TS compile step in CI (fast with SWC / esbuild).

### D3. Repo layout: sibling repo `moto-diag-mobile`

**Decision:** Mobile app lives at
`C:\Users\Kerwyn\PycharmProjects\moto-diag-mobile\` as a sibling
repo to `moto-diag/`. **Not** a subdirectory of `moto-diag/`,
**not** a monorepo.

**Alternatives considered:**

| Option | Pros | Cons | Reject reason |
|--------|------|------|---------------|
| **Sibling repo** | CI isolation, separate release cadence, independent cloning | Requires version coordination | **Chosen** |
| Subdirectory of moto-diag | One repo | Backend CI triggers every mobile CI; clone balloons | Wrong tradeoff for solo-dev tooling |
| Monorepo (`packages/backend`, `packages/mobile`) | One repo, cross-package refactors | Complex tooling (turborepo / nx); CI split | Overkill; user's convention is one-project-per-repo |

**Repo name:** `moto-diag-mobile` (public on `Kubanjaze/` per
the user's pattern from the other moto-diag repos).

**Coordination mechanism:** the backend's `/openapi.json` is the
contract. Mobile pulls types via a CI step that curls the spec
from the deployed backend (or a committed spec snapshot during
offline builds). Phase 186 wires this.

**Consequences:**

- ✅ Git clones are small on both sides.
- ✅ Python CI stays fast (~8 min); mobile CI can take 20-30 min
  without blocking backend PRs.
- ✅ App Store / Play Store release cadence independent of
  backend deploys.
- ❌ Cross-repo changes (e.g., adding an endpoint + the client
  call) require two PRs. Acceptable — the OpenAPI spec is the
  serialization boundary.

### D4. State management: Zustand + TanStack Query

**Decision:**

- **Server state** — `@tanstack/react-query` (React Query). Every
  API call is a query or mutation. Automatic caching,
  background refetch, optimistic updates, offline persistence.
- **Client state** — `zustand`. One store per concern
  (BLE connection, UI prefs, navigation state, active
  diagnosis). Plain-object stores, no providers, no reducers.

**Alternatives considered:**

| Option | Boilerplate | TS inference | Offline support | Reject reason |
|--------|-------------|--------------|-----------------|---------------|
| Zustand + TanStack Query | Low | Excellent | TQ's persistQueryClient | **Chosen** |
| Redux Toolkit + RTK Query | High | Good | RTK Query's redux-persist | Overkill for solo-dev; RTK's reducer ceremony adds cost without benefit at this scale |
| MobX | Moderate | Mixed | Manual | Less common in RN ecosystem; harder to debug |
| Recoil | Low | Good | Manual | Abandoned by Meta |
| Jotai | Low | Good | Manual | No built-in server-cache story; would need TanStack Query anyway |

**Why split client vs server state:** React Query excels at
server state (cache invalidation, background refetch, pagination,
retries). Zustand excels at client state (transient UI state,
device state, cross-screen values). Using one tool for both
makes neither good.

**Offline:** TanStack Query's `persistQueryClient` plugin with
AsyncStorage (or MMKV for speed) backend. Reads are cached
transparently; UI shows stale data with a "cached" indicator.

**Writes offline:** op-queue pattern. Failed mutations are
serialized to disk + retried in-order when connectivity
returns. Implemented as a thin wrapper around
`useMutation`'s `onMutate` / `onError` hooks.

**Consequences:**

- ✅ ~1kb + ~11kb of runtime vs. Redux's ~30kb+.
- ✅ Type-safe store access via `useStore(s => s.myField)` with
  automatic inference.
- ✅ Persistent cache covers Phase 198's offline-first read
  pattern out of the box.
- ❌ No Redux DevTools time-travel — mitigated by Zustand's
  middleware for Redux DevTools compatibility.

### D5. API client: `openapi-fetch` from Phase 183 spec

**Decision:** Generate TypeScript types from the backend's
`/openapi.json` using `openapi-typescript`. Use `openapi-fetch`
at runtime for typed HTTP calls.

```typescript
import createClient from "openapi-fetch";
import type { paths } from "./api-types";

export const api = createClient<paths>({
  baseUrl: process.env.EXPO_PUBLIC_API_URL,
  headers: { "X-API-Key": getApiKey() },
});

// Usage:
const { data, error } = await api.GET("/v1/vehicles");
//    ^? VehicleListResponse | undefined
```

**Alternatives considered:**

| Option | Runtime size | Type depth | Maintenance | Reject reason |
|--------|--------------|------------|-------------|---------------|
| `openapi-fetch` + `openapi-typescript` | ~1kb + zero runtime codegen | Deep (path + method + params + body + response) | Low | **Chosen** |
| Orval | ~moderate | Deep | Config-heavy; generates runtime wrappers we don't need | Too much generated code |
| `@openapitools/openapi-generator` | Variable | Deep | Java tool, slow CI step | Heavy toolchain for no proportional benefit |
| Hand-written `fetch` wrappers | 0 | Only what we type | Per-endpoint hand work | Defeats Phase 183's whole value prop |

**Why openapi-fetch wins:** it does zero runtime codegen — only
types. The runtime is a ~1kb wrapper around `fetch` that uses
the generated types to enforce contracts. Adding a new endpoint
on the backend = regenerate types file = new client method
appears. No code to update, no wrapper to write.

**Consequences:**

- ✅ End-to-end type safety: Phase 177 Pydantic models → Phase
  183 OpenAPI → RN client call. A breaking backend change
  fails the mobile typecheck.
- ✅ Tiny bundle cost.
- ✅ Supports the Phase 183 `apiKey` security scheme out of the
  box via `headers`.
- ❌ Error types are less rich than Orval's generated
  exceptions — acceptable; we use the RFC 7807 ProblemDetail
  body directly.

### D6. Offline strategy: persistent cache + op-queue

**Decision:**

- **Reads:** TanStack Query `persistQueryClient` + AsyncStorage
  (MMKV swap later if bench shows need). Every query's
  `queryFn` result caches to disk keyed by query key. Offline
  launches re-hydrate from cache and show stale data.
- **Writes:** op-queue. Offline mutations serialize to disk via
  a simple wrapper around TanStack Query's `mutationCache`.
  On reconnect, drain in-order. Failures move to a "needs user
  attention" screen.
- **DTC database:** bundle the static 40-entry DTC JSON from
  Phase 05 as an app asset. Backend `/v1/kb/dtc/{code}` is a
  fallback for make-specific or newer codes.
- **Secure storage:** `react-native-keychain`. Keychain (iOS) /
  Keystore (Android). API keys + future session tokens here.
  Never AsyncStorage for secrets.

**Alternatives considered:**

- **No offline** — rejected. Shops frequently have poor cellular
  reception; the DTC lookup flow must work without network.
- **Full Redux Offline** — rejected. Assumes Redux; our stack
  doesn't use Redux.
- **SQLite on device** — considered. WatermelonDB or
  `expo-sqlite` give a local relational store. Deferred to
  Phase 198 — if TanStack Query's persistence proves
  insufficient for the shop-dashboard (Phase 193) or time-tracker
  (Phase 202) queries, we add a local SQLite layer then.

**Consequences:**

- ✅ Works at a cellular dead zone or a shop with spotty WiFi.
- ✅ Instant cold-start — cached data shows before network
  resolves.
- ❌ Data can drift from server state; UI must surface
  staleness with a "Last updated Xm ago" banner.

### D7. Bluetooth OBD: `react-native-ble-plx` behind provider seam

**Decision:** `react-native-ble-plx` on bare RN. All BLE code
hidden behind a single `ObdConnection` class with an
`ObdProvider` ABC-like interface. Mirrors Phase 181's
`LiveReadingProvider` pattern so the same test-injection seam
works on mobile: a `FakeObdProvider` serves deterministic synth
frames in dev + tests; a `RealObdProvider` wraps BLE in prod
builds.

**Alternatives considered:**

- `react-native-ble-manager` — older, less maintained than
  `ble-plx`.
- Custom native module — would take a phase of native code;
  premature given `ble-plx` exists.
- Expo Bluetooth — doesn't exist as a managed API for BLE.

**Feature flag:** `OBD_SUPPORT` compile-time flag in app config.
First TestFlight / Play Store alpha ships without BLE to de-risk
the first release; BLE enables in the second release.

**iOS requirements:**
- `NSBluetoothAlwaysUsageDescription` in `Info.plist`.
- `bluetooth-central` in `UIBackgroundModes` for background
  streaming during a test ride.

**Android requirements:**
- `BLUETOOTH_CONNECT` + `BLUETOOTH_SCAN` runtime permissions
  (Android 12+).
- `ACCESS_FINE_LOCATION` still required on older Android for BLE
  scan.

**Consequences:**

- ✅ Same provider-pattern as Phase 181 backend — tests can use
  a fake provider without real BLE hardware.
- ✅ Feature flag lets us ship UI phases (188-195) without
  needing to solve BLE first.
- ❌ iOS background mode requires App Store review explanation
  — acceptable; a motorcycle diagnostic app's use of background
  Bluetooth is legitimate.

---

## Consequences (aggregate)

**Favorable:**

- **One codebase ships to both stores** — iOS App Store +
  Google Play Store from the same `moto-diag-mobile` repo.
- **End-to-end type safety** — Pydantic (Phase 177) → OpenAPI
  3.1 (Phase 183) → TypeScript client types → React components.
  A backend breaking change fails mobile typecheck at CI time.
- **Small runtime bundle** — openapi-fetch + zustand + TanStack
  Query sum to <50kb minified; well under mobile bundle
  budgets.
- **Mature integration libraries** — BLE + camera + voice +
  push all have proven RN libraries with active maintenance.
- **Offline-first by default** — TanStack Query's persistence
  means cache-based reads work without any phase-specific
  offline wiring.

**Unfavorable:**

- **Two toolchains to maintain** — Xcode + Android Studio
  locally, plus CI runners for both. Phase 186 spends its
  entire scope on taming this.
- **Native-module version skew** — every bare RN library
  version needs iOS Pod + Android Gradle sync. Upgrading
  RN minor versions is an afternoon, not a morning.
- **Cross-repo coordination** — backend + mobile PRs for
  new endpoints. Mitigated by the OpenAPI spec being the
  explicit serialization contract.

---

## Status

**Accepted** as of 2026-04-23 (Phase 185 merge). All Track I
phases 186-204 proceed on the basis of these 7 decisions.

**Reversal conditions** (any one triggers a new ADR that
supersedes):
1. React Native ships a major breaking version that invalidates
   the library ecosystem for > 6 months.
2. A specific phase (especially Phase 196 BLE or Phase 197 live
   dashboard) hits a hard RN limitation that requires a native
   rewrite.
3. The solo-dev-velocity assumption changes (e.g., a second
   developer joins with deep Flutter experience).
4. Apple or Google policy changes restrict RN apps in a way that
   doesn't apply to native or Flutter.

None of those are imminent.

---

## Implementation notes for Phase 186

Phase 186 (Mobile project scaffold + CI/CD) operationalizes this
ADR. Scope for Phase 186:

1. Create `moto-diag-mobile` repo at
   `C:\Users\Kerwyn\PycharmProjects\moto-diag-mobile\`.
2. `npx @react-native-community/cli init MotoDiagMobile
   --template react-native-template-typescript` (or the current
   equivalent).
3. Install: `zustand`, `@tanstack/react-query`,
   `openapi-fetch`, `react-native-keychain`,
   `@react-native-async-storage/async-storage` (or `react-native-mmkv`),
   `react-native-safe-area-context`, `react-native-screens`,
   `@react-navigation/native` + `/stack` + `/bottom-tabs`.
4. Pin RN to a specific minor version — current LTS-ish is
   0.74.x or 0.75.x.
5. Enable Hermes (default in modern RN).
6. Add `openapi-typescript` as a dev dep + a `generate-api-types`
   npm script that curls `/openapi.json` and writes
   `src/api-types.ts`.
7. CI: GitHub Actions workflow with iOS build (macOS runner) +
   Android build (ubuntu runner). Cache node_modules, Pods,
   Gradle. Output is a `.ipa` + `.apk` artifact on every green
   PR.
8. TestFlight internal distribution via App Store Connect API
   (manual submit initially; automated in Phase 204).
9. Play Internal Testing track via Google Play Developer API.
10. `App.tsx` with a single "Health check" screen that hits
    `GET /v1/version` and displays the response.

Exit criteria for Phase 186: both stores accept a smoke-test
build; CI green on both platforms.

---

**End of ADR-001.**
