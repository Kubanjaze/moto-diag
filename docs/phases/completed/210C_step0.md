# Phase 210C — Step 0: the shop's build, without developer panels or a location note

**Written 2026-11-26** by the advisor session on the Mac, against this
repository's master `47ea328` and the app's `main` `3fa252b`, at the
operator's K148. Every command below ran in `moto-diag-mobile` at `3fa252b`
unless it names somewhere else. Classification: **extension** (S0-7).

Found after build 1's rehearsal on the operator's phone (Phase 210B, after
its merge): the TestFlight build's home screen shows developer panels, and
Apple's email about build 1 names a missing location purpose string.

## S0-1 — the developer panels

- `grep -n -E '<Section title=|Phase 191' src/screens/HomeScreen.tsx`
  lists the subtitle `v{appVersion} · Phase 191` (line 279) and eight
  sections: "Backend" (281), "Auth" (289), "Authed smoke (/v1/vehicles)"
  (301), "Settings" (313), "DTC lookup" (327), "BLE scan (Phase 186)"
  (339) and "OBD-II adapter (Phase 196)" (355), the last inside
  `{OBD_SUPPORT ? (` (354).
- On the operator's phone, build 1 from TestFlight (screenshot,
  2026-11-26 16:40): "v0.5.0 · Phase 191"; Backend with the server's
  package, schema and API versions; Auth, signed in; Authed smoke with its
  "Test /v1/vehicles" button; Settings; DTC lookup.
- The developer panels are the subtitle, Backend, Authed smoke and BLE
  scan. Auth (signing in and out), Settings and DTC lookup are for the
  shop. OBD-II is already hidden in Release builds by its own flag (S0-2).

## S0-2 — the development flag

- `git grep -n '__DEV__' -- src App.tsx | wc -l` prints `7`: the flag file
  `src/config/features.ts` (its comment at line 23, and line 26,
  `export const OBD_SUPPORT: boolean = __DEV__;`), four state machines'
  `if (__DEV__)` logging, and a comment in `src/services/obdFailureReport.ts`.
- `__DEV__` is React Native's global: true under Metro and in Debug
  builds, false in Release bundles. TestFlight and App Store builds are
  Release, and so are the advisor's cable installs (`-configuration
  Release` in 210B's blocks).
- So the existing flag the operator asked for is `__DEV__`, through the flag
  file, as OBD_SUPPORT does.

## S0-3 — Apple's note on build 1

- Apple's email, "The uploaded build for Mekno has one or more issues."
  (2026-11-26 15:13 EST, read in the operator's inbox at their K148):
  "ITMS-90683: Missing purpose string in Info.plist", "should contain a
  NSLocationWhenInUseUsageDescription key", and "If you're using external
  libraries or SDKs, they may reference APIs that require a purpose
  string." It also says the delivery was successful.
- The app's own code never asks for a location on iOS:
  `git grep -n -E 'geolocation|CLLocation|requestWhenInUse|NSLocation' -- src App.tsx ios/MotoDiag`
  finds nothing; `git grep -n enableLocation -- src` finds nothing, so no
  screen asks the camera to tag a location; and
  `/usr/libexec/PlistBuddy -c Print ios/MotoDiag/Info.plist | grep -c NSLocation`
  prints `0`.
- The libraries: for each of `package.json`'s 24 dependencies,
  `grep -rlE "CLLocationManager|requestWhenInUseAuthorization|CoreLocation" node_modules/<dep>/ios node_modules/<dep>/apple node_modules/<dep>/cpp`
  finds files only in `react-native-vision-camera` (10 files).
- `react-native-vision-camera` is 4.7.3
  (`node -e "console.log(require('./node_modules/react-native-vision-camera/package.json').version)"`).
  Its `VisionCamera.podspec`, lines 8 to 14: `enableLocation = true` unless
  the Podfile defines `$VCEnableLocation`, and the setting becomes the
  Swift condition `VISION_CAMERA_ENABLE_LOCATION`, under which
  `ios/Core/LocationProvider.swift` creates a `CLLocationManager`.
  `grep -n -i -E 'VCEnable|location' ios/Podfile` finds nothing.
- What the flag removes, read in the library's Swift: the location
  permission request (`CLLocationManager.requestAccess(for: .whenInUse)` in
  `ios/React/CameraViewManager.swift`, lines 138 to 146), the status reads
  (`CLLocationManager.authorizationStatus()`, lines 113 to 118, and in
  `ios/Core/LocationProvider.swift` lines 26 to 34), and the creation of a
  `LocationProvider` (`ios/Core/CameraSession+Location.swift`, lines 13 to
  27). What it leaves: the `LocationProvider` class itself, which still
  holds a `CLLocationManager` and calls `startUpdatingLocation`, though
  nothing creates one with the flag off.
- Build 1's archived app (`~/Library/Developer/Xcode/Archives/2026-11-26/Mekno-1.0-1-2026-11-26_1508.xcarchive`),
  `strings -a .../MotoDiag.app/MotoDiag | grep -c <name>`:
  `requestWhenInUseAuthorization` 1, `requestAlwaysAuthorization` 0,
  `CLLocationManager` 20, `startUpdatingLocation` 1; `otool -L` lists
  CoreLocation. The first is the call Apple's note is about.
- So the cause is the camera library's location code, built in by default
  and never used. The fix that matches "if the app does not need it,
  remove the call or the library" (K148) is the library's own switch, not
  a purpose string for something the app does not do.

## S0-4 — the switch, measured with CocoaPods

In a scratch clone of the app at `3fa252b`, with a copy-on-write copy of
the real checkout's `node_modules` (the lock files are identical), on the
Mac (CocoaPods 1.16.2, `pod --version`):
- `pod install --no-repo-update` from a fresh clone changes three prebuilt
  pods' checksums in `ios/Podfile.lock` (hermes-engine,
  React-Core-prebuilt, ReactNativeDependencies) and reorders the build
  phases in `ios/MotoDiag.xcodeproj/project.pbxproj` (48 lines). With the
  real checkout's `ios/Pods` copied in instead (`cp -c -R`), the lock file
  does not change, and only `project.pbxproj` is reordered: that reorder
  is CocoaPods' own and is not this phase's.
- With `$VCEnableLocation = false` added above the line that resolves
  `react_native_pods.rb`, `pod install` prints
  `[VisionCamera] $VCEnableLocation is set to false!`, the pod's generated
  xcconfig loses `VISION_CAMERA_ENABLE_LOCATION`, and `git diff ios/Podfile.lock`
  shows exactly two changed lines: `VisionCamera:` from
  `7187b3dac1ff3071234ead959ce311875748e14f` to
  `b51af005669c6642dd1b4fca434eda4c1778de87`, and `PODFILE CHECKSUM`.
- `PODFILE CHECKSUM` is the SHA-1 of the Podfile's bytes:
  `shasum -a 1 ios/Podfile` printed `1169a8abfdeab6189afb66ad97f52e71da16ab2a`
  on main, which is main's lock, and `98b9e33b68766f31bc90e1de050d43ab6034795f`
  on the changed file, which is what `pod install` wrote. So an app session
  without CocoaPods can write both lines.

## S0-5 — Android

- The app's manifest, `android/app/src/main/AndroidManifest.xml`:
  `ACCESS_FINE_LOCATION` with `android:maxSdkVersion="30"` (lines 23 and
  24), for Bluetooth scans on Android 11 and older; `BLUETOOTH_SCAN` with
  `neverForLocation` (lines 18 and 19);
  `grep -c 'xmlns:tools' android/app/src/main/AndroidManifest.xml` prints
  `0`.
- The libraries' manifests declare location with no limit:
  `node_modules/react-native-ble-plx/android/src/main/AndroidManifest.xml`
  lines 5 and 6 (`ACCESS_COARSE_LOCATION`, `ACCESS_FINE_LOCATION`), and
  `node_modules/react-native-bluetooth-classic/android/src/main/AndroidManifest.xml`
  line 5 (`ACCESS_FINE_LOCATION`). `react-native-vision-camera`'s Android
  manifest asks for none; its `MetadataProvider.kt` uses `LocationManager`
  only when a screen turns location on, and none does (S0-3).
- No Android build is possible on this Mac: `ls ~/Library/Android/sdk`
  answers "No such file or directory", and `/usr/libexec/java_home`
  answers "Unable to locate a Java Runtime". So the merged manifest cannot
  be produced here; the plan checks the app's manifest, which the merge
  obeys through `tools:node="replace"`, and names the limit.

## S0-6 — the build number

- `grep -n -E 'CURRENT_PROJECT_VERSION|MARKETING_VERSION' ios/MotoDiag.xcodeproj/project.pbxproj`
  prints `CURRENT_PROJECT_VERSION = 1;` at lines 299 and 331 and
  `MARKETING_VERSION = 1.0;` at lines 307 and 339.
- Build 1 is on TestFlight (210B's log), and App Store Connect refuses a
  second build with the same number for the same version (ITMS-90189).

## S0-7 — classification

**Extension.** The flag file exists (`src/config/features.ts`) and gains
one flag; the home screen gains conditions; the Podfile, its lock, the
Android manifest and the project file change a few lines. Nothing new is
built and nothing is reshaped. No server change.
