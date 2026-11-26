# Phase 210C — No developer panels in the shop's build, and Apple's location note

**Version 1.0, 2026-11-26.** The plan, by the advisor session on the Mac
(K148), from `210C_step0.md`. The app's code is built in `moto-diag-mobile`
from `docs/prompts/210C_no_developer_panels_and_apples_location_note.txt`;
this repository holds the row, the plan and the record.

## Goal

Make build 2 the shop's build. Its home screen shows what a shop uses
(signing in and out, Settings, DTC lookup) and no developer panel, while
development builds keep them. Apple's note on build 1, ITMS-90683 for a
missing `NSLocationWhenInUseUsageDescription`, is cleared at its cause: a
camera library's location code that the app never uses. Android's location
permissions say the same thing. Then build 2 goes to TestFlight.

## The plan of record

Like 210B, this phase is beside "Next, in order": it finishes Phase 210's
step 3, the app on the shop's phones, before shop one's day. The plan of
record and its pins are unchanged. 409 runs in the fleet meanwhile; nothing
here touches it.

## Logic

### 1. No developer panels in the shop's build

- `src/config/features.ts` gains `DEV_PANELS: boolean = __DEV__`, with a
  comment, the same as `OBD_SUPPORT` (S0-2).
- `src/screens/HomeScreen.tsx` renders the subtitle line, "Backend",
  "Authed smoke (/v1/vehicles)" and "BLE scan (Phase 186)" only when
  `DEV_PANELS` is on (S0-1).
- "Auth", "Settings" and "DTC lookup" render in every build. "OBD-II
  adapter" stays behind `OBD_SUPPORT`. Nothing else on the screen changes.

### 2. Apple's location note

- `ios/Podfile` defines `$VCEnableLocation = false` above the line that
  resolves `react_native_pods.rb`, with a comment naming the reason (the app
  never asks the camera for a location; ITMS-90683 on build 1).
- `ios/Podfile.lock` changes exactly two lines (S0-4): VisionCamera's
  checksum to `b51af005669c6642dd1b4fca434eda4c1778de87`, and `PODFILE
  CHECKSUM` to the SHA-1 of the final `ios/Podfile`.
- No `NSLocation…` key is added to `Info.plist`: the app does not use
  location, and a purpose string for something it does not do would not be
  honest.
- The flag removes the library's location request and status reads; its
  unused `LocationProvider` class stays compiled (S0-3). So the check is the
  built binary and Apple's next email (After the merge, steps 3 and 4).

### 3. Android matches

- `android/app/src/main/AndroidManifest.xml` gains `xmlns:tools` and
  declares `ACCESS_FINE_LOCATION` and `ACCESS_COARSE_LOCATION`, each with
  `android:maxSdkVersion="30"` and `tools:node="replace"`, so the two
  Bluetooth libraries' unlimited declarations (S0-5) do not reach Android
  12 and up.
- `BLUETOOTH_SCAN` keeps `neverForLocation`. The comment above the
  Bluetooth permissions stays true. Nothing else in the manifest changes.
- Known limit: no machine here builds Android (S0-5), so the merged
  manifest is not produced; the app's manifest and its test are the check.

### 4. Build 2

- `CURRENT_PROJECT_VERSION` becomes 2 in both places in
  `ios/MotoDiag.xcodeproj/project.pbxproj`; `MARKETING_VERSION` stays 1.0.
  Nothing else in that file changes (S0-6).

### 5. The record

- The app's session opens one pull request in `moto-diag-mobile` and does
  not merge it. The advisor re-runs its checks on the Mac, and the operator
  merges.
- This repository's row 210C, this plan, the log and the close-out are the
  advisor's.

## Rule-1 stops

- **A real fork:** none now. K148 chose: remove the cause if the app does
  not need location, else an honest key. If Apple's email about build 2
  still names ITMS-90683, that is a fork for the operator (patch the
  library's unused class out, or add a purpose string), and the advisor
  stops there.
- **A threshold or a rule's definition:** none.
- **A test that cannot be made green:** the app's session stops and says
  so.
- **A login or a credential:** none in the build. The upload uses the
  Mac's Xcode account, as build 1 did.
- **A live-database change:** none.

## Tests

In the app, each seen red on `3fa252b` before its code:

1. **The home screen, flag off** (`jest.mock` of `src/config/features`):
   no subtitle, no "Backend", no "Authed smoke", no "BLE scan"; "Auth",
   "Settings" and "DTC lookup" present.
2. **The home screen, flag on:** all of them present (pins development
   builds).
3. **The Podfile:** defines `$VCEnableLocation = false`; `Podfile.lock`'s
   `PODFILE CHECKSUM` equals the SHA-1 of `ios/Podfile`, and VisionCamera's
   checksum is `b51af005669c6642dd1b4fca434eda4c1778de87`.
4. **Info.plist** has no key beginning `NSLocation`.
5. **The Android manifest** declares both location permissions with
   `android:maxSdkVersion="30"` and `tools:node="replace"`, and
   `xmlns:tools`; `BLUETOOTH_SCAN` keeps `neverForLocation`.
6. **The project file:** `CURRENT_PROJECT_VERSION = 2;` twice and
   `MARKETING_VERSION = 1.0;` twice.

On the Mac, before build 2 goes up (After the merge, step 3): the archived
app's binary holds no `requestWhenInUseAuthorization` (build 1's held one,
S0-3), and it is version 1.0, build 2.

## Non-goals

- A new home screen, or any change to what Auth, Settings or DTC lookup
  show.
- Android's launcher name, applicationId or a build (an Android phase).
- The App Store listing (Phase 410), and App Review.
- `project.pbxproj`'s build-phase order, which `pod install` rewrites
  (S0-4); it is not this phase's.
- Any server change.

## After the merge

These are the operator's steps, each from a block the advisor tests first:
1. The advisor re-runs the app's checks on the Mac at the pull request's
   head, and the operator merges it.
2. On the Mac, the real checkout runs `pod install`: the lock file must not
   change (the pull request carries its two lines), and the build-phase
   reorder in `project.pbxproj` is put back.
3. Build 2 is archived from the merge. Before upload: version 1.0, build 2,
   `com.getmekno.app`, the live server built in, and no
   `requestWhenInUseAuthorization` in the binary. Then the upload.
4. App Store Connect: build 2 processes to Ready to Submit, and "First look"
   gets it by itself. Apple's email about build 2 must not name ITMS-90683.
5. The operator's phone updates in TestFlight; the home screen shows Auth,
   Settings and DTC lookup, and no developer panel.
6. "Shop one" gets build 2 when the operator adds it (manual delivery).

## Version history

| version | date | change |
|---|---|---|
| 1.0 | 2026-11-26 | The plan, from Step 0 (K148). |
