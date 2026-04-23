# Moto-Diag Mobile — Phase 186 Handoff

**Purpose of this document:** everything a developer (human or AI) needs to continue Phase 186 without reading the prior conversation. Self-contained. Read top to bottom once; then use as reference.

**Prepared:** 2026-04-23
**Owner:** Kerwyn Medrano (solo dev)
**Repo:** `Kubanjaze/moto-diag-mobile` (to be created — public)
**Local path:** `C:\Users\Kerwyn\PycharmProjects\moto-diag-mobile\` (sibling of the `moto-diag` backend repo)

---

## 1. Project context

- **moto-diag** = the existing Python backend/platform for motorcycle diagnostics. Already shippable as a backend-only product. Lives in `C:\Users\Kerwyn\PycharmProjects\moto-diag\`.
- **moto-diag-mobile** = the new React Native client. This is Phase 186 of the overall project plan.
- **Track H** (backend) is closed. **Track I** (mobile) starts here.
- Solo developer. No other contributors. No CI yet (intentional — see §9).

---

## 2. Locked decisions

All of the below are confirmed. **Do not revisit or "improve" these without explicit ask from Kerwyn.**

| # | Decision | Value |
|---|---|---|
| 1 | Repo strategy | Separate sibling repo (not monorepo) |
| 2 | Local path | `C:\Users\Kerwyn\PycharmProjects\moto-diag-mobile\` |
| 3 | GitHub remote | `Kubanjaze/moto-diag-mobile`, **public** |
| 4 | App display name | `MotoDiag` |
| 5 | Bundle ID / Android applicationId | `com.bandithero.motodiag` |
| 6 | React Native version | **0.85.x** (current stable; pin exact at init) |
| 7 | New Architecture (Fabric/TurboModules) | **DISABLED** — pending `react-native-ble-plx` compatibility. See ADR-002 and §8. |
| 8 | iOS min deployment target | **15.1** (RN default; captures iPhone 6s/7/SE 1st-gen and up) |
| 9 | Android minSdkVersion | **24** / Android 7.0 (RN default; ~late-2016 devices) |
| 10 | Language | TypeScript |
| 11 | Package manager | npm |
| 12 | Navigation | React Navigation (native stack) |
| 13 | State management | **Deferred** — no lib installed in 186. Zustand is leading future candidate. See ADR-003. |
| 14 | BLE library | `react-native-ble-plx` |
| 15 | Env-var handling | `react-native-config` |
| 16 | Backend API integration | **Stubbed** in 186. Typed client, configurable base URL, no-op auth interceptor. No real `moto-diag` calls yet. |
| 17 | CI / CD | **None** in 186. Defer to Phase 204 / Gate 10 (TestFlight + Play submission). See ADR-004. |
| 18 | License | MIT, © 2026 Kerwyn Medrano |
| 19 | Apple Developer account | Created. Not required for 186 (Simulator only). Required for device testing / TestFlight in later phases. |

---

## 3. Configuration reference (quick lookup)

```
App name:           MotoDiag
Bundle ID:          com.bandithero.motodiag
RN version:         0.85.x
TypeScript:         yes
Node required:      >= 20.19.4
Package manager:    npm
iOS min target:     15.1
Android minSdk:     24 (Android 7.0)
New Architecture:   OFF
License:            MIT
```

---

## 4. Execution plan

### Phase 186 steps, by actor

| # | Actor | Step | Status |
|---|---|---|---|
| 1 | Kerwyn | Create empty GitHub repo `Kubanjaze/moto-diag-mobile` (public). No README, no .gitignore, no license — we bring our own. | Not started |
| 2 | Kerwyn | Verify Node ≥ 20.19.4 (`node -v`). | Not started |
| 3 | Kerwyn | `cd C:\Users\Kerwyn\PycharmProjects` | Not started |
| 4 | Kerwyn | Run the RN init command in §5. This scaffolds the RN project at `moto-diag-mobile/`. | Not started |
| 5 | Kerwyn | Smoke test the vanilla RN scaffold: `npm run ios` and `npm run android`. Confirm the default RN welcome screen renders on both. | Not started |
| 6 | Coder | Produce overlay artifacts (see §7). | Partially done — starter bundle (LICENSE, README, ADRs, .gitignore additions) already produced; app-code overlays pending. |
| 7 | Kerwyn | Apply overlays, run `npm install` for added deps, `cd ios && pod install && cd ..`, re-smoke-test both platforms. | Not started |
| 8 | Kerwyn | `git remote add origin git@github.com:Kubanjaze/moto-diag-mobile.git`, first commit, push to `main`. **Phase 186 done.** | Not started |

---

## 5. The RN init command (verbatim)

Run this from `C:\Users\Kerwyn\PycharmProjects`:

```bash
npx @react-native-community/cli@latest init MotoDiag \
  --version 0.85 \
  --pm npm \
  --package-name com.bandithero.motodiag \
  --directory moto-diag-mobile
```

Windows cmd single-line version:

```cmd
npx @react-native-community/cli@latest init MotoDiag --version 0.85 --pm npm --package-name com.bandithero.motodiag --directory moto-diag-mobile
```

This creates the `moto-diag-mobile/` folder with the RN 0.85 TypeScript template, the correct bundle ID pre-wired, and npm (not yarn) selected.

**After init completes, the smoke test is:**

```bash
cd moto-diag-mobile
npm run android    # Android Emulator must be running
# and/or on macOS:
cd ios && pod install && cd ..
npm run ios
```

Both should show the default React Native welcome screen. If that works, step 5 is complete.

---

## 6. Starter files already produced

The following files were produced prior to init and are in the handoff bundle. After step 4 completes, drop them into the new repo root (merging `.gitignore.additions` into the auto-generated `.gitignore`):

```
moto-diag-mobile/
├── LICENSE                                           # MIT, © 2026 Kerwyn Medrano
├── README.md                                         # project overview + setup
├── .gitignore.additions                              # merge into RN-generated .gitignore
└── docs/adr/
    ├── 001-repo-location.md
    ├── 002-new-arch-disabled-pending-ble-plx.md
    ├── 003-state-management-deferred.md
    └── 004-ci-deferred-to-gate-10.md
```

Full text of each file is in **Appendix A** of this document.

---

## 7. Work the coder produces next (post-init overlay)

Once Kerwyn reports "init succeeded and vanilla scaffold smoke-tests clean," the coder produces the following.

### 7.1 New source files

```
src/
├── api/
│   ├── client.ts            # typed stub client. Exports makeClient({ baseUrl }).
│   ├── auth.ts              # no-op auth interceptor placeholder. Typed signature matches future real impl.
│   └── index.ts             # re-exports
├── ble/
│   └── BleService.ts        # singleton wrapper around BleManager from react-native-ble-plx.
│                            # Exposes: scan(), connect(deviceId), disconnect(), destroy().
├── navigation/
│   └── RootNavigator.tsx    # createNativeStackNavigator with a single Home screen.
├── screens/
│   └── HomeScreen.tsx       # placeholder screen. Renders "MotoDiag" title + app version.
└── types/
    └── api.ts               # shared TS types for API requests/responses (empty-ish for now)
```

Plus:

```
.env.example                 # API_BASE_URL=http://localhost:8000
App.tsx                      # updated to render <NavigationContainer><RootNavigator/></NavigationContainer>
```

### 7.2 Native file edits

| File | Edit |
|---|---|
| `android/gradle.properties` | Set `newArchEnabled=false` (override the default). |
| `ios/Podfile` | At the top of the file, add `ENV['RCT_NEW_ARCH_ENABLED'] = '0'`. Then re-run `pod install`. |
| `ios/MotoDiag/Info.plist` | Add `NSBluetoothAlwaysUsageDescription` with a sensible string ("MotoDiag connects to your OBD-II Bluetooth adapter to read motorcycle diagnostics."). |
| `android/app/src/main/AndroidManifest.xml` | Add BLE permissions: `BLUETOOTH_SCAN`, `BLUETOOTH_CONNECT` (API 31+), legacy `BLUETOOTH` + `BLUETOOTH_ADMIN` (`maxSdkVersion="30"`), and `ACCESS_FINE_LOCATION`. Also `<uses-feature android:name="android.hardware.bluetooth_le" android:required="true"/>`. |

### 7.3 Dependencies to install

```bash
npm install \
  @react-navigation/native \
  @react-navigation/native-stack \
  react-native-screens \
  react-native-safe-area-context \
  react-native-ble-plx \
  react-native-config
```

Then iOS:

```bash
cd ios && pod install && cd ..
```

### 7.4 Final smoke test (post-overlay)

1. `npm run android` — app launches, HomeScreen shows "MotoDiag" and a version string.
2. `npm run ios` — same.
3. Trigger a BLE scan from HomeScreen (dev button) — should request permissions and begin scanning without crashing. No connection required; a clean scan attempt is sufficient to validate the ble-plx wiring.

### 7.5 First commit

```bash
git init
git add .
git commit -m "Phase 186: mobile scaffold + ADRs 001-004"
git branch -M main
git remote add origin git@github.com:Kubanjaze/moto-diag-mobile.git
git push -u origin main
```

---

## 8. Constraints, gotchas, and version requirements

### Host environment
- **Node.js `>= 20.19.4`** — RN 0.85 dropped support for older Node.
- **JDK 17** — Android Gradle Plugin requirement.
- **Xcode 15+** — for iOS builds. macOS only.
- **CocoaPods** — `sudo gem install cocoapods` (macOS).
- **Android Studio** — with at least one API-34+ emulator image.
- **Ruby** — for CocoaPods. Use the system Ruby or asdf/rbenv.

### New Architecture disabled — why, when it flips
- `react-native-ble-plx` issue [#1277](https://github.com/dotintent/react-native-ble-plx/issues/1277) (open as of Feb 2025): BLE crashes with New Architecture enabled on RN 0.76+. Community workaround is to disable New Arch.
- **Flip condition:** ble-plx releases a version with documented New Arch support AND a branch smoke test with a real OBD-II dongle connects cleanly. Until then, both flags in §7.2 row 1–2 stay false/0.
- This is documented in **ADR-002**. Do not flip unilaterally.

### Apple Developer account
- Exists. Not needed for Phase 186 (Simulator only).
- Will be needed in Phase 187+ for real-device testing, and Phase 204 (Gate 10) for TestFlight.
- Individual enrollment, not Organization.

### Android BLE permissions — behavior differences
- API 31+ (Android 12+): `BLUETOOTH_SCAN` and `BLUETOOTH_CONNECT` are runtime permissions. Must be requested at runtime from JS.
- Pre-API 31: legacy `BLUETOOTH` + `BLUETOOTH_ADMIN` install-time permissions, plus `ACCESS_FINE_LOCATION` runtime.
- The AndroidManifest.xml edits in §7.2 cover both paths via `maxSdkVersion` qualifiers.

### iOS Info.plist requirement
- `NSBluetoothAlwaysUsageDescription` is required since iOS 13. Missing it = App Store rejection.

---

## 9. Deferred items (intentional — do NOT implement in 186)

| Deferred item | ADR | Trigger for revisit |
|---|---|---|
| State management library | ADR-003 | ≥ 3 screens sharing state, OR prop-drilling past 2 levels |
| CI configuration | ADR-004 | Gate 10 / Phase 204 — first TestFlight + Play Internal Testing build |
| Real `moto-diag` backend integration | (embedded in §2 #16) | Its own later phase, after mobile has screens that need data |
| iOS real-device distribution / TestFlight | — | Phase 187+ |
| New Architecture enablement | ADR-002 | ble-plx #1277 resolution |

---

## 10. Definition of Done for Phase 186

Phase 186 is complete when **all** of the following are true:

1. GitHub repo `Kubanjaze/moto-diag-mobile` exists and is public.
2. Repo contains: RN 0.85 scaffold, LICENSE (MIT), README.md, `.gitignore` merged, `docs/adr/001-004.md`, `src/` stubs per §7.1, `.env.example`, native edits per §7.2 applied, deps per §7.3 installed.
3. `npm run ios` launches MotoDiag HomeScreen in iOS Simulator without errors.
4. `npm run android` launches MotoDiag HomeScreen in Android Emulator without errors.
5. BLE scan triggered from HomeScreen requests permissions and begins scanning without crashing.
6. First commit is pushed to `main` on GitHub.
7. `newArchEnabled=false` confirmed in `android/gradle.properties` and `RCT_NEW_ARCH_ENABLED=0` confirmed in iOS build.

**Not in scope for 186 DoD:** real backend integration, real-device builds, TestFlight, Play Store, any actual diagnostic feature.

---

## 11. Handoff boundary for the next coder

The next AI or developer continuing this work should:

1. **Read this entire document first.** Do not skip sections.
2. **Confirm Kerwyn's current state.** Ask: "Has step 4 (RN init) completed and step 5 (vanilla smoke test) passed?" If yes → proceed to §7. If no → wait; do not produce overlay files until the RN scaffold exists, because exact paths depend on what `init` generates.
3. **Do not relitigate §2 decisions.** If a decision looks suboptimal, surface the concern to Kerwyn; do not quietly change it.
4. **When producing files in §7, preserve paths exactly as listed.** The directory structure is a decision, not a suggestion.
5. **When done with §7 artifacts, hand them to Kerwyn** with a short apply-order checklist (install deps → apply native edits → drop in `src/` files → `pod install` → smoke test).

---

## Appendix A — Full text of starter files already produced

### A.1 `LICENSE`

```
MIT License

Copyright (c) 2026 Kerwyn Medrano

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

### A.2 `README.md`

````markdown
# MotoDiag Mobile

React Native client for the [moto-diag](https://github.com/Kubanjaze/moto-diag) motorcycle diagnostic platform.

## Status

Phase 186 scaffold. Not yet shippable. See `docs/adr/` for decision records.

## Tech stack

- React Native 0.85.x (pinned; New Architecture **disabled** pending [`react-native-ble-plx#1277`](https://github.com/dotintent/react-native-ble-plx/issues/1277) — see ADR-002)
- TypeScript
- React Navigation (native stack)
- `react-native-ble-plx` for OBD-II BLE
- `react-native-config` for environment variables

Minimum OS targets: iOS 15.1, Android API 24 (Android 7.0) — captures devices from roughly 2015–2016 onward.

Bundle ID / applicationId: `com.bandithero.motodiag`

## Prerequisites

- Node.js `>= 20.19.4`
- npm (bundled with Node)
- Xcode 15+ (iOS builds; macOS only)
- CocoaPods (`sudo gem install cocoapods`)
- Android Studio with an API-34+ emulator image
- JDK 17

## Setup

```bash
git clone https://github.com/Kubanjaze/moto-diag-mobile.git
cd moto-diag-mobile
npm install
cp .env.example .env   # edit API_BASE_URL if needed

# iOS (macOS only)
cd ios && pod install && cd ..
npm run ios

# Android
npm run android
```

## Project structure

```
moto-diag-mobile/
├── android/              # native Android project
├── ios/                  # native iOS project
├── src/
│   ├── api/              # stub API client for moto-diag backend
│   ├── ble/              # react-native-ble-plx wrapper
│   ├── navigation/       # React Navigation stacks
│   ├── screens/          # screen components
│   └── types/            # shared TypeScript types
├── docs/adr/             # architecture decision records
├── .env.example
├── App.tsx
└── package.json
```

## Backend connection

The `src/api/` client is **stubbed** in Phase 186 — it has the shape of the real client (typed methods, configurable base URL, auth interceptor placeholder) but does not yet hit the real `moto-diag` backend. Real integration is a later phase.

## CI

None yet. Local builds via Xcode / Android Studio. CI wires in at Gate 10 (Phase 204) when TestFlight / Play submission matters. See ADR-004.

## License

MIT — see [LICENSE](./LICENSE).
````

### A.3 `.gitignore.additions`

```gitignore
# Additions to the React Native default .gitignore.
# The `npx ... init` command generates a base .gitignore; append these lines to it.

# Environment
.env
.env.local
.env.*.local

# IDEs
.idea/
.vscode/
*.swp
*.swo
*~
.DS_Store
Thumbs.db

# Logs
*.log
npm-debug.log*
yarn-debug.log*
yarn-error.log*

# Test coverage
coverage/

# TypeScript incremental build
*.tsbuildinfo

# Python artifacts (in case any tooling scripts leak in)
__pycache__/
*.pyc
.venv/
```

### A.4 `docs/adr/001-repo-location.md`

```markdown
# ADR-001: Mobile repo location and name

- Status: Accepted
- Date: 2026-04-23
- Deciders: Kerwyn Medrano

## Context

Phase 186 introduces a React Native mobile client for the moto-diag platform.
The mobile codebase needs a home: either (a) a new folder inside the existing
`moto-diag` repo (monorepo), or (b) a sibling repo with its own GitHub remote.

## Decision

The mobile client lives in a separate sibling repo:

- Local path: `C:\Users\Kerwyn\PycharmProjects\moto-diag-mobile\`
- GitHub remote: `Kubanjaze/moto-diag-mobile` (public)

## Rationale

- Independent release cadence.
- Independent CI requirements (macOS runners, RN toolchain).
- PR diff hygiene — no CocoaPods / Gradle / Hermes artifacts in backend PRs.
- Solo-dev context: no shared JS/TS package yet to justify monorepo overhead.

## Consequences

- Two repos, two dependency trees, two issue trackers.
- Cross-cutting changes require two PRs.
- Revisit if shared TS types or a published `@moto-diag/*` package emerges.
```

### A.5 `docs/adr/002-new-arch-disabled-pending-ble-plx.md`

```markdown
# ADR-002: New Architecture disabled pending react-native-ble-plx support

- Status: Accepted
- Date: 2026-04-23

## Context

RN 0.83 made New Architecture (Fabric + TurboModules) the default. RN 0.85.x
(our pin) ships with this default. `react-native-ble-plx` has open issue #1277
reporting BLE crashes under New Arch. Community workaround: disable New Arch.

## Decision

Scaffold RN 0.85.x with New Arch explicitly disabled:

- `android/gradle.properties`: `newArchEnabled=false`
- `ios/Podfile`: `ENV['RCT_NEW_ARCH_ENABLED'] = '0'` at top

## Rationale

- BLE is required for OBD-II — non-negotiable.
- Dropping to RN 0.82 (last Old-Arch-default release) puts us on a soon-EOL line.
- 0.85 + Old Arch keeps us on latest RN core + React 19 while BLE works.

## Trigger for reversal

Flip when BOTH are true:
1. ble-plx releases a version with New Arch support.
2. Branch-build smoke test — scan + connect real OBD-II dongle — passes.
```

### A.6 `docs/adr/003-state-management-deferred.md`

```markdown
# ADR-003: State management library deferred

- Status: Accepted
- Date: 2026-04-23

## Decision

No state management library in Phase 186. Use component-local `useState`
and React Context where needed (e.g., the BLE service singleton).

## Rationale

- At scaffolding stage there is no real state shape — picking a lib is speculative.
- Context + hooks handle a surprising amount for a solo-dev app.
- Adding a lib later is typically a one-commit change.

## Trigger for revisit

Add a state lib when ANY of:
- ≥ 3 screens share the same state.
- Prop-drilling exceeds 2 levels for any value.
- Need cross-launch persistence beyond auth tokens (use MMKV directly for that).

## Leading candidate (non-binding)

Zustand. A follow-up ADR records the actual pick at time of adoption.
```

### A.7 `docs/adr/004-ci-deferred-to-gate-10.md`

```markdown
# ADR-004: CI deferred to Phase 204 / Gate 10

- Status: Accepted
- Date: 2026-04-23

## Decision

No CI in Phase 186. All builds run locally via Xcode / Android Studio.
Wire CI at Gate 10 / Phase 204 (TestFlight + Play Internal Testing).

## Rationale

- GitHub Actions macOS runners: 10× minutes multiplier. iOS builds take 15–30 min.
  Free tier exhausts quickly.
- CI's main value — PR validation across contributors, signed store builds —
  does not apply yet (solo dev, no store submission).
- Local Fast Refresh round-trips in seconds; CI adds minutes for no proportional gain.

## Trigger for adoption

Gate 10 / Phase 204: first TestFlight + Play Internal Testing upload.

At that point CI minimally:
1. Build release variants on push to `main`.
2. `tsc --noEmit` + Jest suite.
3. Sign + upload iOS → TestFlight, Android → Play Internal Testing.
```

---

## End of handoff document

If the receiving developer has questions this document doesn't answer, route them to Kerwyn. Do not infer new decisions from ambiguity — surface the ambiguity.
