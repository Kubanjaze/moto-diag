# Phase 210C — No developer panels in the shop's build, and Apple's location note

**Version 1.1, 2026-11-26.** Closed. v1.0 (the same day) was the plan by
the advisor session on the Mac (K148), from `210C_step0.md`. The app's code
was built in `moto-diag-mobile` from
`docs/prompts/210C_no_developer_panels_and_apples_location_note.txt`, by
the operator's own app session: pull request #16, head `b611a3b`, merged by
the operator as `1fbd967` on 2026-11-26. This repository holds the row, the
plan and the record. This version records what was built, from the pull
request's description and the advisor's review of it, and the steps after
the merge.

## Goal

Make build 2 the shop's build. Its home screen shows what a shop uses
(signing in and out, Settings, DTC lookup) and no developer panel, while
development builds keep them. Apple's note on build 1, ITMS-90683 for a
missing `NSLocationWhenInUseUsageDescription`, is cleared at its cause: a
camera library's location code that the app never uses. Android's location
permissions say the same thing. Then build 2 goes to TestFlight.

All of it is done. Build 2 (1.0, 2) is on TestFlight and on the operator's
phone, and Apple sent no note about it.

## The plan of record

Like 210B, this phase was beside "Next, in order": it finished Phase 210's
step 3, the app on the shop's phones. The plan of record and its pins are
unchanged. 409 ran in the fleet meanwhile; nothing here touched it.

On the evening of the close, the operator said there is no shop to put the
app in front of yet: "i have no shops yet, i only have individual users as
consumers", and "i want to release to individuals, work out bugs then push
to get into shops". Build 2 is the build for whoever comes first.

## Logic

### 1. No developer panels in the shop's build (`7685b4f`)

- `src/config/features.ts` gained `DEV_PANELS: boolean = __DEV__`, with a
  comment, the same as `OBD_SUPPORT` (S0-2).
- `src/screens/HomeScreen.tsx` renders the subtitle line, "Backend",
  "Authed smoke (/v1/vehicles)" and "BLE scan (Phase 186)" only when
  `DEV_PANELS` is on (S0-1).
- "Auth", "Settings" and "DTC lookup" render in every build. "OBD-II
  adapter" stays behind `OBD_SUPPORT`. Nothing else on the screen changed.

### 2. Apple's location note (`5186fe3`)

- `ios/Podfile` defines `$VCEnableLocation = false` above the line that
  resolves `react_native_pods.rb`, with a comment naming the reason (the app
  never asks the camera for a location; ITMS-90683 on build 1).
- `ios/Podfile.lock` changed exactly two lines (S0-4): VisionCamera's
  checksum to `b51af005669c6642dd1b4fca434eda4c1778de87`, and `PODFILE
  CHECKSUM` to `8ca28318992e1ac082a7b26455fdb323cbf6386c`, the SHA-1 of the
  final `ios/Podfile`.
- No `NSLocation…` key was added to `Info.plist`: the app does not use
  location, and a purpose string for something it does not do would not be
  honest.
- The flag removes the library's location request and status reads. Step
  0 expected its unused `LocationProvider` class to stay compiled (S0-3);
  in build 2's program its `CLLocationManager` references stay, but
  `startUpdatingLocation` is gone too (Results). The check was the built
  binary and Apple's next email; both are clean.

### 3. Android matches (`9e627d7`)

- `android/app/src/main/AndroidManifest.xml` gained `xmlns:tools` and
  declares `ACCESS_FINE_LOCATION` and `ACCESS_COARSE_LOCATION`, each with
  `android:maxSdkVersion="30"` and `tools:node="replace"`, so the two
  Bluetooth libraries' unlimited declarations (S0-5) do not reach Android
  12 and up.
- `BLUETOOTH_SCAN` keeps `neverForLocation`. The comment above the
  Bluetooth permissions stays true. Nothing else in the manifest changed,
  besides a comment saying why `tools:node="replace"` is there.
- Known limit, as planned: no machine here builds Android (S0-5), so the
  merged manifest was not produced; the app's manifest and its test are the
  check.

### 4. Build 2 (`b611a3b`)

- `CURRENT_PROJECT_VERSION` is 2 in both places in
  `ios/MotoDiag.xcodeproj/project.pbxproj`; `MARKETING_VERSION` stays 1.0.
  Nothing else in that file changed (S0-6).

### 5. The record

- The app's session opened one pull request in `moto-diag-mobile` and did
  not merge it. The advisor re-ran its checks on the Mac, and the operator
  merged it.
- This repository's row 210C, this plan, the log, the handoff and the
  build-2 block (`210C_blocks/1_build2_testflight.txt`, as it ran) are the
  advisor's.

## Rule-1 stops

None was reached.
- **A real fork:** none. Apple's email about build 2 did not name
  ITMS-90683, so the fork the plan held ready (patch the library's unused
  class out, or add a purpose string) never came.
- **A threshold or a rule's definition:** none.
- **A test that cannot be made green:** none. The app's suite failed on
  timing twice in the review and passed on the third run; F308 records it.
- **A login or a credential:** none in the build. The upload used the
  Mac's Xcode account, as build 1 did.
- **A live-database change:** none.

## Tests

In the app, each seen red on `3fa252b` before its code (the pull request's
account):
1. **The home screen, flag off** (`__tests__/screens/HomeDevPanels.smoke.test.tsx`,
   with `jest.mock` of `src/config/features`): no subtitle, no "Backend", no
   "Authed smoke", no "BLE scan"; "Auth", "Settings" and "DTC lookup"
   present.
2. **The home screen, flag on:** all of them present (pins development
   builds); and the real `DEV_PANELS` equals `__DEV__`.
3. **The Podfile** (`__tests__/ios/locationNote.test.ts`): defines
   `$VCEnableLocation = false` above the pods line; `Podfile.lock`'s
   `PODFILE CHECKSUM` equals the SHA-1 of `ios/Podfile`, and VisionCamera's
   checksum is `b51af005669c6642dd1b4fca434eda4c1778de87`.
4. **Info.plist** has no key beginning `NSLocation` (seen red by adding one
   by hand, then put back).
5. **The Android manifest** (`__tests__/android/locationPermissions.test.ts`)
   declares both location permissions with `android:maxSdkVersion="30"` and
   `tools:node="replace"`, and `xmlns:tools`; `BLUETOOTH_SCAN` keeps
   `neverForLocation` (seen red by removing it by hand, then put back).
6. **The project file** (`__tests__/ios/buildNumber.test.ts`):
   `CURRENT_PROJECT_VERSION = 2;` twice and `MARKETING_VERSION = 1.0;`
   twice (seen red by setting 1.1 by hand, then put back).

No existing test was changed.

On the Mac, before build 2 went up: the archived app holds no
`requestWhenInUseAuthorization` in any file (build 1's program held one),
and it is version 1.0, build 2.

## Non-goals

- A new home screen, or any change to what Auth, Settings or DTC lookup
  show.
- Android's launcher name, applicationId or a build (an Android phase).
- The App Store listing (Phase 410), and App Review.
- `project.pbxproj`'s build-phase order, which `pod install` rewrites
  (S0-4); it was put back after the install and never committed.
- Any server change.

## After the merge

Each was the operator's step, from a block the advisor tested first; the
log has each one's outcome.
1. **Done.** The advisor re-ran the app's checks on the Mac at the pull
   request's head, and the operator merged it as `1fbd967`.
2. **Done.** On the Mac, the real checkout ran `pod install`: the lock file
   did not change, and the build-phase reorder in `project.pbxproj` was put
   back.
3. **Done.** Build 2 was archived from the merge and checked before the
   upload: version 1.0, build 2, `com.getmekno.app`, the live server built
   in, and no `requestWhenInUseAuthorization` in the app. Uploaded at 19:35
   EST.
4. **Done.** Apple processed it within two minutes, and TestFlight told
   the "First look" tester at 19:36 EST that Mekno 1.0 (2) is ready to test.
   No email about issues came for build 2.
5. **Done.** On the operator's phone, build 2's home screen shows Auth,
   Settings and DTC lookup and no developer panel, and signing in works
   (the operator: "all those things check on the iphone").
6. **Not done: "Shop one" gets build 2 when a shop is added.** There is no
   shop yet (The plan of record, above); the group stays as it is until one
   comes.

## Deviations

1. **The regression of record is 210B's run at `85315cb`.** This phase
   changed no code in this repository, and every commit since `85315cb`
   (on master and on this branch) adds documents only, which `verify_phase.sh`
   check 2 confirms. A second 40-minute run would test the same code. The
   log carries the line as printed, and says so.
2. **`startUpdatingLocation` is gone from build 2's program**, where Step 0
   expected the unused `LocationProvider` to keep it (S0-3).
   `CLLocationManager` is still referenced 20 times, and CoreLocation is
   still linked. Apple's email is what mattered, and it did not come.
3. **Beyond the plan in the pull request:** a comment above the two
   location permissions in the Android manifest saying why
   `tools:node="replace"` is there, and a short comment above the gated
   block on the home screen. Both were judged fine. The pull request also
   says that in Release builds the hidden Backend panel still asks the
   server for its version on focus, without showing it; the hooks were left
   as they are so nothing else on the screen changes.
4. **The review's test runs failed twice on timing.** Two hook tests each
   failed once with "TypeError: window.dispatchEvent is not a function",
   and the third run passed; main's control printed the same error once.
   F308, filed in the app's FOLLOWUPS at this close-out, records it with
   210B's TermsModal timeout.
5. **Step 6 was not run**, because there is no shop yet.

## Results

| | before (`main` `3fa252b`) | after (`b611a3b`) |
|---|---|---|
| `npx jest` | 118 suites, 1345 passed | 122 suites, 1360 passed (+15) |
| `npx tsc --noEmit` | clean | clean |
| `npx eslint .` | 0 errors, 150 warnings | 0 errors, 150 warnings |

- **The advisor's re-run on the Mac,** 2026-11-26, in a scratchpad clone at
  `b611a3b` with a copy of the real checkout's `node_modules` (the lock
  files are the same): tsc exit 0; eslint 0 errors, 150 warnings; jest 122
  suites and 1360 tests passed on the third run (the first two: F308). A
  real `pod install` there, with the real checkout's installed libraries
  copied in, wrote exactly the pull request's two lock lines.
- **Merged** by the operator as `1fbd967` (moto-diag-mobile `main`),
  2026-11-26 at 23:36 UTC.
- **Build 2's program against build 1's** (`strings -a` on the archived
  `MotoDiag` program):

  | name | build 1 | build 2 |
  |---|---|---|
  | `requestWhenInUseAuthorization` | 1 | 0 |
  | `requestAlwaysAuthorization` | 0 | 0 |
  | `startUpdatingLocation` | 1 | 0 |
  | `CLLocationManager` | 20 | 20 |

  No file in build 2's app holds the request, and its Info.plist has no
  `NSLocation` key.
- **Apple:** TestFlight's "Mekno 1.0 (2) for iOS is now available to test."
  at 19:36 EST; no email about issues for build 2. Build 1's had come a
  minute after its upload.
- **The phone:** build 2's home screen as planned, signed in on live.
- **This repository:** no code changed. Its regression of record, 210B's
  run at `85315cb`, is in the log.

## Planned items

- [x] `DEV_PANELS` and the home screen's gated panels (`7685b4f`)
- [x] `$VCEnableLocation = false` and the lock's two lines (`5186fe3`)
- [x] Android's two location permissions capped at Android 11 (`9e627d7`)
- [x] Build number 2 (`b611a3b`)
- [x] The tests, each seen red; tsc, eslint and jest clean
- [x] The app's pull request, merged by the operator after review (#16,
  `1fbd967`)
- [x] After the merge: `pod install`, build 2 checked and uploaded, Apple's
  note gone, the phone checked
- [x] The close-out here: v1.1, the log, row 210C ✅, the handoff, F308

## Version history

| version | date | change |
|---|---|---|
| 1.0 | 2026-11-26 | The plan, from Step 0 (K148). |
| 1.1 | 2026-11-26 | Closed: what was built (pull request #16, `b611a3b`, merged as `1fbd967`), build 2 on TestFlight with no note from Apple, five deviations, the results. |
