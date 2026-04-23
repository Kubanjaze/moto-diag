# MotoDiag Phase 185 — Mobile Architecture Decision (Track I opener)

**Version:** 1.0 | **Tier:** ADR (Architecture Decision Record) | **Date:** 2026-04-23

## Goal

**Open Track I** with a formal architecture decision record (ADR)
for the mobile app. Documents the framework choice, version
strategy, project layout, state management, API client shape,
offline strategy, Bluetooth OBD integration posture, and
distribution targets. No code ships in this phase — Phase 186 is
the scaffold + CI/CD, Phase 187 is the API client library.

This is a pure documentation phase with durable rationale that
every subsequent Track I phase references. Think of it as the
Track I analogue to Track H's Phase 175 scaffold decision + Phase
176's paywall decision rolled into one document.

CLI — none. Phase 185 produces a single ADR document.

Outputs (~600 LoC of docs, zero code):
- `docs/phases/completed/185_implementation.md` — this file plus
  the v1.1 finalization.
- `docs/phases/completed/185_phase_log.md` — standard phase log.
- `docs/mobile/ADR-001-framework-choice.md` (~500 LoC) — the
  durable ADR. Lives in `docs/mobile/` so Track I phases 186-204
  can reference a stable path and future phases can add ADR-002,
  ADR-003, etc.

No migration, no schema change, no Python code.
`implementation.md` version bump 0.13.0 → 0.13.1 reflecting the
Track I opener.

## Logic

### The ADR document

Phase 185 produces a single ADR-001 that captures seven decisions:

1. **Framework** — React Native (bare, not Expo managed).
2. **Language** — TypeScript with `strict: true`.
3. **Repo layout** — sibling repo `moto-diag-mobile/` at
   `C:\Users\Kerwyn\PycharmProjects\moto-diag-mobile\`.
4. **State management** — Zustand for client state + TanStack
   Query for server cache.
5. **API client** — `openapi-fetch` auto-generated from Phase
   183's enriched spec.
6. **Offline strategy** — TanStack Query persistent cache +
   op-queue for writes.
7. **Bluetooth OBD** — `react-native-ble-plx` on bare RN;
   feature-flagged and behind a native-module boundary so the
   rest of the app has no BLE dependency.

Each decision follows the standard ADR format: Context /
Decision / Alternatives / Consequences / Status.

### Why React Native (not Flutter / native / PWA)

- **Shared codebase across iOS + Android** without two separate
  teams. User is a solo mechanic/builder — two codebases would
  halve velocity.
- **TypeScript ecosystem** — same language family as openapi-fetch
  generation from the Phase 183 spec; shared Zod schemas are
  possible if we add a codegen step.
- **Mature BLE + camera + filesystem libraries** — needed for
  Bluetooth OBD, VIN scanner, photo attach, voice record. Flutter
  equivalents exist but RN's ecosystem is deeper for hardware
  integration.
- **Not Expo managed** — Expo's managed workflow restricts
  native-module additions. Bluetooth BLE + custom audio capture
  for Phase 97-99 sound-signature flows would push us out of
  managed within 3-4 phases. Better to start bare.
- **Not native Swift + Kotlin** — two native codebases, two
  toolchains, 2× app logic. User's context (solo builder, shop
  mechanics as primary users) doesn't justify native performance.
- **Not PWA / Capacitor / Ionic** — Bluetooth OBD needs real
  native APIs (BLE stack + background mode on iOS). PWAs can't.

### Why bare RN (not Expo)

Already covered above. The decisive constraints are:

- Bluetooth OBD (Phase 196) needs `react-native-ble-plx` which
  works on bare but is "unsupported" in Expo managed.
- Custom audio capture (Phase 195 voice input + future sound
  signature capture) needs native audio sessions that Expo
  managed locks down.
- Background audio for live OBD streaming on a test ride (Phase
  197) needs iOS background mode entitlements that Expo managed
  has limited hooks for.

Expo's "dev client" / EAS Build workflow covers most bare RN
cases but adds its own constraints. Starting bare from day one
removes the "move off Expo" migration that would otherwise
happen around Phase 196.

### Repo layout

`moto-diag` (this repo) stays Python-only. Mobile app lives at
`C:\Users\Kerwyn\PycharmProjects\moto-diag-mobile\` as a sibling
repo. Separate repo because:

- **Git clone speed** — mobile pulls in `node_modules`, iOS
  Pods, Android Gradle caches that a Python-only backend dev
  doesn't need to clone.
- **CI pipeline isolation** — Python CI runs in ~8 minutes;
  iOS simulator builds + Android emulators run in ~20-30 minutes.
  Same repo means every backend PR triggers mobile CI.
- **Release cycle independence** — App Store + Play Store
  releases are on different cadences from backend deploys.
- **The Phase 183 OpenAPI spec is the contract** — mobile doesn't
  need access to moto-diag's source, only `/openapi.json`.

Alternative: monorepo with `packages/backend/` +
`packages/mobile/`. Rejected because of the CI + clone-speed
costs above and because the user's pattern is
`C:\Users\Kerwyn\PycharmProjects\<repo>\` single-project
directories.

### State management: Zustand + TanStack Query

- **Server state** — TanStack Query (`@tanstack/react-query`).
  Every API call is a query/mutation. Cache-invalidation rules
  at hook level. Persistent cache (AsyncStorage backend) gives
  offline-first read behavior for free.
- **Client state** — Zustand. Single store pattern, no
  boilerplate, TypeScript-inferred actions. Replaces Redux at a
  fraction of the LoC.
- **NOT Redux Toolkit** — overkill for a single-operator shop
  app. Zustand covers the ~5-10 client-state slices we need
  (current shop, selected bike, BLE connection status, UI
  preferences) without the reducer/action boilerplate.
- **NOT MobX** — good library but less common in the RN ecosystem
  and harder to debug than Zustand's plain object store.

### API client: openapi-fetch from Phase 183 spec

The Phase 183 OpenAPI spec is a first-class contract. Generate a
typed client:

```bash
npx openapi-typescript <backend>/openapi.json --output api-types.ts
```

Then use `openapi-fetch` at runtime:

```typescript
import createClient from "openapi-fetch";
import type { paths } from "./api-types";

const client = createClient<paths>({ baseUrl: "..." });
const { data, error } = await client.GET("/v1/vehicles");
```

- End-to-end type safety from Phase 177 Pydantic → Phase 183
  OpenAPI → RN openapi-fetch calls.
- Zero hand-written API wrappers. Adding a new endpoint on the
  backend → regenerate types → new client method appears.
- Smaller bundle than `axios` + manually-typed wrappers.

Alternative: auto-generated Orval or openapi-codegen clients.
Rejected — they produce more code for less benefit than
openapi-fetch's lightweight typed wrapper.

### Offline strategy

- **Reads:** TanStack Query's `persistQueryClient` plugin +
  AsyncStorage backend. Every query's results cache to disk;
  offline launches show stale data with a "cached" banner.
- **Writes:** Op-queue pattern — mutations serialize to disk
  when offline, replay in-order when back online. Implemented
  as a thin wrapper around TanStack Query's `mutationCache` with
  AsyncStorage persistence.
- **Full DTC database offline** (Phase 189 requirement) — ship
  the ~40-entry static DTC JSON as a bundled asset in the app
  and serve it from a local helper. Backend `/v1/kb/dtc` is a
  fallback for codes not in the bundled set.
- **Session tokens / API keys** — `react-native-keychain` for
  Keychain (iOS) / Keystore (Android) secure storage. Never
  AsyncStorage (not encrypted at rest on Android without
  Keystore).

### Bluetooth OBD (Phase 196 forward plan)

- **Library:** `react-native-ble-plx`. Deal with the native
  module ceremony once (Phase 196).
- **Isolation:** all BLE code behind a single `ObdConnection`
  class with an injectable `Provider` interface. Mirrors Phase
  181's `LiveReadingProvider` ABC so the same test-seam pattern
  works on mobile.
- **Feature flag:** `OBD_SUPPORT` compile-time flag. iOS + Android
  dev builds get it on; the initial TestFlight / Play Store
  alpha ships without BLE to de-risk the first release.
- **Background mode:** iOS requires `bluetooth-central`
  background mode in `Info.plist`; Android requires
  `BLUETOOTH_CONNECT` runtime permission (Android 12+).

### Distribution

- **iOS App Store** — paid app, $0.99 → $4.99 one-time OR
  freemium-with-subscription linked to the Phase 176 Stripe
  backend. Decision deferred to Phase 203-ish (pre-Gate 10).
- **Google Play Store** — same pricing strategy as iOS.
- **TestFlight / Play Internal Testing** — Phase 186 configures
  both for every green CI build.
- **Enterprise / Ad-hoc** — not in Track I scope. Shop-tier
  subscribers use the normal App Store flow.

### Versioning

Mobile app ships its own `package.json` version, independent
of moto-diag backend. Track I opens at `mobile version 0.1.0`.
Gate 10 (Phase 204) targets `1.0.0-beta` for the first store
submission. The mobile app reads backend's `/v1/version` at
startup and shows a banner if its required-minimum-backend
version is newer than what the server reports.

## Key Concepts

- **ADR (Architecture Decision Record)** — a short document
  capturing one significant decision with its context,
  alternatives, and consequences. The ADR pattern comes from
  Michael Nygard. Decisions become durable once committed;
  reversal requires a new ADR that supersedes.
- **Bare RN vs Expo managed** — Expo managed is a RN subset that
  removes native-code access in exchange for faster CI + OTA
  updates + easier setup. Bare RN gives full native-module
  access at the cost of managing Xcode + Android Studio
  toolchains directly.
- **TanStack Query** — formerly `react-query`. Provides query /
  mutation primitives with automatic caching, background
  refetch, optimistic updates, persistence.
- **openapi-fetch** — ~1kb runtime that reads OpenAPI types and
  produces typed HTTP client methods. Zero codegen of runtime
  code (only type codegen).
- **react-native-ble-plx** — the de facto BLE library for bare
  RN. Supports both iOS Core Bluetooth + Android BLE stacks.
- **Keychain / Keystore** — platform secure stores. iOS Keychain
  items are encrypted by the Secure Enclave; Android Keystore
  items are encrypted by TEE (hardware-backed on most devices).
- **Zustand** — ~1kb React state management library. Creates a
  hook from a plain-object store definition; no providers, no
  reducers.
- **TypeScript strict mode** — `"strict": true` in tsconfig
  enables all strictness flags. Non-negotiable for this project;
  relaxed TS quickly becomes any-typed JS with decoration.

## Verification Checklist

- [ ] ADR-001 file created at `docs/mobile/ADR-001-framework-choice.md`.
- [ ] ADR covers all 7 decisions (framework, language, repo,
      state, API client, offline, BLE).
- [ ] Each decision has Context / Decision / Alternatives /
      Consequences / Status.
- [ ] `docs/mobile/` directory exists and is committed.
- [ ] Project `implementation.md` version bumped 0.13.0 → 0.13.1.
- [ ] Project `phase_log.md` has Phase 185 entry.
- [ ] `docs/ROADMAP.md` Phase 185 marked ✅.
- [ ] No Python code changes, no tests added/modified.
- [ ] Track H regression (301 tests) still GREEN — but since no
      code changes, sanity check is a `pytest --collect-only`
      rather than a full re-run.

## Risks

- **Decision reversal cost** — if React Native turns out to be
  the wrong choice after Phase 190+, rewriting in Flutter would
  cost several phases. Mitigation: ADRs capture
  reversal-condition triggers; each Track I phase is a
  fresh-dependency test of the RN choice.
- **Solo-dev velocity** — RN requires maintaining iOS + Android
  toolchains locally. User is primary developer; toolchain
  maintenance is one-person. Mitigation: EAS Build or GitHub
  Actions macOS runners can do most iOS building remotely;
  local dev only needs Android Studio initially.
- **Expo migration temptation** — bare RN is more work. The
  temptation to migrate to Expo managed for Phase 186 scaffold
  simplicity will reappear. Mitigation: ADR-001 pre-commits to
  bare; any Phase 186 deviation requires ADR-002 superseding.
- **OpenAPI spec drift** — mobile types are generated from the
  backend's `/openapi.json`. If backend changes break the
  generated types, the mobile build fails. Mitigation: Phase
  186 CI/CD step regenerates types + typechecks on every
  backend deploy; backend Phase 186+ hooks mirror this.
