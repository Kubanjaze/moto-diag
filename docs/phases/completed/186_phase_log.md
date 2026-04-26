# Phase 186 — Phase Log (retroactive)

**Status:** ✅ Complete | **Started:** 2026-04-23 | **Completed:** 2026-04-23
**Repo:** https://github.com/Kubanjaze/moto-diag-mobile

Docs reconstructed retroactively on 2026-04-23 as part of the Track I discipline-setup commit. Timestamps below are approximate (based on commit history + conversation log); milestone ordering is accurate.

---

### 2026-04-23 — Plan handoff received

Kerwyn prepared a self-contained Phase 186 overlay handoff document (preserved at `moto-diag/docs/mobile/phase-186-handoff.md`) capturing 19 locked decisions. Plan v1.0 locked: RN 0.85.x + TypeScript + bare workflow + `com.bandithero.motodiag` bundle ID + newArchEnabled=false + npm + React Navigation native stack + `react-native-ble-plx` + `react-native-config` + stubbed backend integration + MIT license + no CI + Apple Developer enrolled (iOS deferred).

### 2026-04-23 — Init complete

Kerwyn ran the canonical init command:

```bash
npx @react-native-community/cli@latest init MotoDiag \
  --version 0.85 --pm npm \
  --package-name com.bandithero.motodiag \
  --directory moto-diag-mobile
```

Vanilla RN welcome screen rendered on Pixel 7 API 35 emulator. Step 5 (smoke test) of the handoff apply-order passed. iOS simulator smoke test intentionally skipped (Windows host, deferred to Mac access).

### 2026-04-23 — Overlay applied

Coder (Claude) wrote all overlay text edits to disk:
- `App.tsx` — replaced init-generated version with NavigationContainer + RootNavigator.
- `src/api/{client,auth,index}.ts` + `src/types/api.ts` — stub API client + types.
- `src/ble/BleService.ts` — singleton BleManager wrapper.
- `src/navigation/RootNavigator.tsx` — native stack, single Home route.
- `src/screens/HomeScreen.tsx` — BLE scan smoke button + status cycle + Android permission request.
- `.env.example` — `API_BASE_URL=http://10.0.2.2:8000`.
- `LICENSE` — MIT © 2026 Kerwyn Medrano.
- `docs/adr/001-004.md` — four ADRs per handoff Appendix A.
- `android/gradle.properties` — `newArchEnabled=false`.
- `android/app/src/main/AndroidManifest.xml` — BLE permissions + `<uses-feature bluetooth_le>`.
- `.gitignore` — Phase 186 additions merged.

### 2026-04-23 — First build attempt → CMake failure

Kerwyn ran `npm install` for the 6 new deps + `npm run android`. Build failed:

```
CMake Error at ... Android-autolinking.cmake:N (add_subdirectory):
  add_subdirectory given source
  ".../react-native-ble-plx/android/build/generated/source/codegen/jni/"
  which is not an existing directory.
...
react_codegen_BlePlx
```

### 2026-04-23 — Diagnosis + fix

Claude inspected `Android-autolinking.cmake` + ble-plx's own `android/build.gradle`. Root cause: RN 0.85 app-level autolinking emits `add_subdirectory(...codegen/jni/)` unconditionally, but ble-plx 3.5.1's gradle guards `apply plugin: "com.facebook.react"` behind `isNewArchitectureEnabled()`. With New Arch off, ble-plx's codegen is never run, the directory never exists, CMake fails looking for it.

Applied in-place edit to `node_modules/react-native-ble-plx/android/build.gradle`: removed both `if (isNewArchitectureEnabled())` guards (plugin apply + `react { ... }` block). Commented with reference back to this phase.

### 2026-04-23 — Second build attempt → green

`cd android && ./gradlew --stop` + `taskkill /F /IM java.exe` + `rmdir /S /Q android\build android\app\build android\.gradle node_modules\react-native-ble-plx\android\build` + `npm run android`. App built, installed, launched. HomeScreen rendered, BLE scan smoke test cycled through expected states.

### 2026-04-23 — First commit

```bash
git init
git add .
git commit -m "Phase 186: mobile scaffold + ADRs 001-004 + src stubs"
git branch -M main
# remote URL was configured before repo existed; push failed initially
# recovered via: gh repo create Kubanjaze/moto-diag-mobile --public --description "..."
git push -u origin main
```

Commit hash: **`1c3b165`**. Pushed to `main` on `Kubanjaze/moto-diag-mobile` (public).

---

### Build deviations summary

1. **ble-plx CMake workaround** — in-place node_modules edit. Fragile (`npm install` wipes it). Phase 187 formalizes via `patch-package`.
2. **iOS Podfile edit + `pod install` + `NSBluetoothAlwaysUsageDescription`** — all deferred to Mac access.
3. **No automated tests** — Jest scaffold present, `__tests__/` empty. Phase 187 adds first real unit tests.

### Key findings

- RN 0.85 + bare + New Arch off + ble-plx 3.5.x is a working stack, but the autolinking/codegen mismatch is a one-time gotcha worth formalizing.
- Android-only dev loop is complete and productive without a Mac.
- Phase 186's layered apply-order (init → vanilla smoke → overlay → rebuild → smoke again) worked cleanly. Same shape will suit Phase 187+.

---

### 2026-04-23 — Retroactive docs commit (this file)

- Backend-mirror phase docs discipline adopted for the mobile repo.
- Project-level `implementation.md` + `phase_log.md` created at mobile-repo root.
- `docs/phases/{in_progress,completed}/` directory structure created.
- `docs/ROADMAP.md` created with Track I phase table + critical-path summary + deferred-items register.
- This file + `186_implementation.md` v1.1 reconstructed from commit + conversation history.
- Committed in the same push as the Phase 187 plan v1.0.
