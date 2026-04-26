# Phase 186 — Mobile project scaffold + CI/CD

**Version:** 1.1 (retroactive) | **Tier:** Standard | **Date:** 2026-04-23

## Goal

Operationalize ADR-001 (Phase 185, in moto-diag backend repo) as a real React Native project. Scaffold an RN 0.85.x bare-workflow TypeScript project with the mobile repo's locked decisions already wired: `com.bandithero.motodiag` bundle ID, `newArchEnabled=false` pending ble-plx #1277, Android BLE permissions, stub `src/` layout mirroring the Track I expected shape. Android emulator smoke test green = Phase 186 done.

CLI — none (this phase doesn't add any motodiag-like CLI; app-level npm scripts only).

Outputs:
- React Native 0.85.2 scaffold from `npx @react-native-community/cli@latest init` at `C:\Users\Kerwyn\PycharmProjects\moto-diag-mobile\`.
- `App.tsx` replaced with `NavigationContainer` + `RootNavigator`.
- `src/api/{client,auth,index}.ts` + `src/types/api.ts` — stub API client with typed surface (`ApiClient` interface, `makeClient({baseUrl})`, `applyAuth` no-op) — Phase 187 swaps bodies.
- `src/ble/BleService.ts` — singleton wrapper around `react-native-ble-plx` `BleManager` (`scan`, `stopScan`, `waitForPoweredOn`, `connect`, `disconnect`, `destroy`).
- `src/navigation/RootNavigator.tsx` — native stack navigator with single Home route.
- `src/screens/HomeScreen.tsx` — "MotoDiag" title + version + "Test BLE scan" smoke button exercising Android runtime permissions + BleManager lifecycle.
- `android/gradle.properties` — `newArchEnabled=true` flipped to `false`.
- `android/app/src/main/AndroidManifest.xml` — 5 BLE + location permissions added, `<uses-feature bluetooth_le required="true"/>` declared.
- `.env.example` — `API_BASE_URL=http://10.0.2.2:8000` (Android emulator host loopback).
- `.gitignore` — Phase 186 additions appended to init-generated file.
- `LICENSE` — MIT, © 2026 Kerwyn Medrano.
- `docs/adr/` — 4 ADRs: repo-location (sibling not monorepo), new-arch-disabled, state-deferred, ci-deferred.
- 6 runtime deps installed: `@react-navigation/native` + `/native-stack`, `react-native-screens`, `react-native-safe-area-context`, `react-native-ble-plx`, `react-native-config`.

No iOS work (deferred to Mac access). No CI (ADR-004). No real backend integration (that's Phase 187).

## Logic

### Scaffold init

```bash
npx @react-native-community/cli@latest init MotoDiag \
  --version 0.85 \
  --pm npm \
  --package-name com.bandithero.motodiag \
  --directory moto-diag-mobile
```

This creates a bare RN 0.85.x TypeScript project with the bundle ID pre-wired into both `ios/` and `android/` native projects, npm (not Yarn), and the standard Jest + ESLint + Prettier toolchain.

### Overlay sequence (Kerwyn-driven; Claude wrote text edits, Kerwyn ran the npm + build steps)

1. **Install deps** — 6 runtime packages.
2. **Disable New Architecture** — `newArchEnabled=false` in `android/gradle.properties`. iOS Podfile edit deferred.
3. **Android BLE permissions** — 5 `<uses-permission>` + 1 `<uses-feature>` inside `<manifest>` above `<application>` in `AndroidManifest.xml`.
4. **iOS BLE usage string** — skipped (no Mac).
5. **Drop in source files** — replace stub `App.tsx`, create 7 `src/` files.
6. **Merge .gitignore** — append Phase 186 additions block.
7. **Rebuild + smoke test** — `npm run android` on Pixel 7 API 35.
8. **First commit + push** — `1c3b165` pushed to `main` on `Kubanjaze/moto-diag-mobile`.

### ble-plx CMake resolution (build deviation, resolved in-place; Phase 187 formalizes)

Fresh build after overlay failed with:

```
CMake Error ...
add_subdirectory given source
"...moto-diag-mobile/node_modules/react-native-ble-plx/android/build/generated/source/codegen/jni/"
which is not an existing directory.
...
react_codegen_BlePlx
```

Diagnosis: the autolinking-generated `android/app/build/generated/autolinking/src/main/jni/Android-autolinking.cmake` contains an unconditional `add_subdirectory(...)` for ble-plx's codegen output, but ble-plx 3.5.1's own `android/build.gradle` guards the `com.facebook.react` plugin application behind `isNewArchitectureEnabled()`. With `newArchEnabled=false`, ble-plx's codegen is never run, the directory never exists, CMake errors out.

Fix applied in-place to `node_modules/react-native-ble-plx/android/build.gradle`:
- Removed `if (isNewArchitectureEnabled()) { apply plugin: "com.facebook.react" }` guard — plugin now applied unconditionally.
- Removed `if (isNewArchitectureEnabled()) { react { ... } }` guard — codegen config (`libraryName = "BlePlx"`, etc.) now set unconditionally.

Safe because the generated TurboModule C++ code links but is never dispatched at runtime with New Arch off. Next build succeeded.

**Caveat:** this edit lives in `node_modules/`; any `npm install` wipes it. **Phase 187 formalizes via `patch-package` + postinstall hook.**

## Key Concepts

- **Bare RN workflow** — full native project access; no Expo managed wrapper. Required for ADR-002 (ble-plx compatibility).
- **`@react-native-community/cli init`** — the canonical bare-scaffold tool post-Expo-default transition.
- **`newArchEnabled` in gradle.properties** — project-level toggle. App gradle plugin reads it; each autolinked library's gradle also reads it via `rootProject.hasProperty("newArchEnabled")`.
- **RN autolinking CMake output** — `android/app/build/generated/autolinking/src/main/jni/Android-autolinking.cmake` is regenerated by the RN gradle plugin. In 0.85 it emits `add_subdirectory(...codegen/jni/...)` for libraries with autolinking metadata, independent of `newArchEnabled`.
- **Android `10.0.2.2`** — the emulator's NAT-mapped loopback for the host machine. The mobile app uses this instead of `localhost` when connecting to a locally-running backend.
- **React Navigation native stack** — `createNativeStackNavigator` uses native iOS `UINavigationController` / Android `FragmentTransaction`; smoother than the JS-only stack.

## Verification Checklist

- [x] `npm run android` builds cleanly (after ble-plx fix).
- [x] Emulator shows "MotoDiag" title + version string + "Phase 186 scaffold" caption.
- [x] "Test BLE scan" button triggers runtime permissions prompt on API 35.
- [x] Status cycles `requesting permissions... → waiting for BLE adapter... → scanning... → scan complete`.
- [x] `newArchEnabled=false` confirmed in `android/gradle.properties`.
- [x] Android BLE permissions + `<uses-feature>` confirmed in `AndroidManifest.xml`.
- [x] `LICENSE` present at repo root.
- [x] 4 ADRs committed to `docs/adr/`.
- [x] First commit pushed to `main` on `Kubanjaze/moto-diag-mobile`.
- [ ] iOS simulator build — **deferred** (no Mac access).
- [ ] ble-plx patch formalized via `patch-package` — **deferred to Phase 187** (in-place edit is fragile).

## Risks (resolved)

- **ble-plx CMake failure** — resolved via in-place node_modules edit. Durability: pending Phase 187 patch-package formalization.
- **iOS Podfile edit** — not applied (Windows, no pod install path). Deferred to first Mac-access phase. Not a Phase 186 regression because iOS smoke test was already out of scope.
- **Gradle file locks on Windows** — hit during troubleshooting. `./gradlew --stop` + `taskkill /F /IM java.exe` before `rmdir` was the fix.

## Deviations from Plan

1. **ble-plx CMake workaround** — not anticipated in the Phase 186 handoff. Required ~30 min diagnosis + in-place edit. Phase 187 formalizes.
2. **iOS Podfile edit skipped** — handoff called it out as "skip on Windows"; confirmed no action needed.
3. **No unit tests** — Jest scaffold present but unused. Phase 187 adds the first real test run (for `src/api/` auth logic).

## Results

| Metric | Value |
|--------|-------|
| RN version | 0.85.2 |
| TypeScript | strict |
| Bundle ID | `com.bandithero.motodiag` |
| Android minSdk | 24 (Android 7.0) |
| iOS min | 15.1 (not yet built) |
| New Architecture | DISABLED |
| Source files | 7 (`src/`) + `App.tsx` + 4 ADRs + `LICENSE` + `.env.example` |
| Runtime deps added | 6 |
| Build time (first clean) | ~4 min (ble-plx codegen cold cache) |
| Build time (incremental) | ~15–30 s |
| Emulator | Pixel 7 API 35 |
| BLE scan smoke | PASS (cycles through states; 0 devices expected on emulator) |
| Commits | 1 (`1c3b165`) |
| Push status | `main -> main` on `Kubanjaze/moto-diag-mobile` |

**Key finding:** the RN 0.85 bare scaffold + newArchEnabled=false + ble-plx 3.5.x combo has a reproducible CMake gotcha that costs ~30 minutes on first build. Once the ble-plx gradle guards are removed, subsequent builds are clean. Formalizing via `patch-package` in Phase 187 makes the workaround survive `npm install` permanently. Android smoke test is a reliable Phase-186-done signal; iOS parity happens when Mac access materializes and doesn't block further Track I work.
