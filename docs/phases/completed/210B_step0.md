# Phase 210B — Step 0: what the app needs before its first TestFlight build

**Written 2026-11-26** by the advisor session on the Mac, against this
repository's master `00283d5` and the app's `main` `4c6c1bd`, at the
operator's K145, K146 and K147. Every command below ran in
`moto-diag-mobile` at `4c6c1bd` unless it names this repository.
Classification: **extension** (S0-7).

Found while laying out Phase 210's step 3 for the operator (the app on the
shop's phones, through TestFlight): the app has no icon, and Apple refuses
an upload without one.

## S0-1 — the icon

- The icon set names a file for none of its sizes:
  `python3 -c "import json; d=json.load(open('ios/MotoDiag/Images.xcassets/AppIcon.appiconset/Contents.json')); im=d['images']; print(len(im), sum(1 for i in im if i.get('filename')))"`
  prints `9 0`. It has not changed since the app's first commit:
  `git log --oneline -- ios/MotoDiag/Images.xcassets` prints only
  `0e204d8 Initial commit`.
- The app holds no picture at all: `find ios/MotoDiag -name '*.png' | wc -l`
  prints `0`. Info.plist has no `CFBundleIcons` and no `CFBundleIconName`
  (`/usr/libexec/PlistBuddy -c 'Print :CFBundleIcons' ios/MotoDiag/Info.plist`
  answers that the entry does not exist).
- Apple refuses such an upload. Forum reports name the errors: ITMS-90704
  for the missing 1024 App Store icon, and ITMS-90022 for a missing iPhone
  size. An app icon must also have no alpha channel.
- The Mac's Xcode is 27.2 (`xcodebuild -version`), so one 1024 icon in the
  single-size form makes every size at build time.
- The picture, at the operator's word (K146), is the website's mark:
  `site/favicon.svg` in this repository, a 64 by 64 drawing of an orange
  square `#e8590c` with rounded corners and a white M. The M's outline is
  12 points joined by straight lines (its path,
  `M14 46V20l9 0 9 13 9-13 9 0v26h-8V31l-10 14-10-14v15z`, written out in
  `210B_icon/make_app_icon.py`). `site/logo.png` is too small to enlarge:
  `sips -g pixelWidth -g pixelHeight site/logo.png` prints 512 and 512.
- So `210B_icon/make_app_icon.py` draws the M from those points at 4096 by
  4096 on a full orange square and reduces it to 1024, in RGB. Run with this
  repository's `.venv` (Pillow 12.2.0), it wrote
  `210B_icon/mekno_app_icon_1024.png`: 1024 by 1024, no alpha
  (`sips -g pixelWidth -g pixelHeight -g hasAlpha` prints 1024, 1024, no),
  12951 bytes, sha256
  `09d3db160b451cf2862ef8579f7489ff67f67bac02e798b6ffe5c5a94e1f3430`.

## S0-2 — the name

- The name under the icon:
  `/usr/libexec/PlistBuddy -c 'Print :CFBundleDisplayName' ios/MotoDiag/Info.plist`
  prints `MotoDiag`.
- Info.plist's strings that begin with the name:
  `grep -c '<string>MotoDiag' ios/MotoDiag/Info.plist` prints `8`: the
  display name and seven permission sentences.
- In `src/`, the lines naming it outside comments:
  `git grep -n MotoDiag -- src | grep -v -E ':[0-9]+:\s*(//|\*|/\*)' | wc -l`
  prints `24`. Read one by one, 7 of them are words a person sees: the home
  screen's title (`src/navigation/HomeStack.tsx` line 30), its heading
  (`src/screens/HomeScreen.tsx` line 278), the Bluetooth sentence
  (`src/obd/obdErrors.ts` line 98), the camera and microphone sentences
  (`src/screens/PhotoCaptureScreen.tsx` line 170,
  `src/screens/VoiceCaptureScreen.tsx` line 256), and two sentences for an
  address that does not answer like our server (`src/api/serverUrl.ts`
  lines 265 and 271). The other 17 are the code's own names (`MotoDiagApi`
  and its imports) and the label the app gives its sign-ins on the server
  (`src/api/signIn.ts` line 55).
- Tests that match the old words: `git grep -n 'MotoDiag server' -- __tests__ | wc -l`
  prints `3`, all in `__tests__/api/serverUrl.test.ts`.
- Android's launcher name is `MotoDiag` too
  (`android/app/src/main/res/values/strings.xml` line 2). It is not this
  phase's: no Android build ships now.

## S0-3 — F303, the keyboard

- Screens that already keep their boxes above the keyboard:
  `git grep -l KeyboardAvoidingView -- src` lists 4 files: NewSessionScreen,
  NewVehicleScreen, SessionDetailScreen and VehicleDetailScreen.
- The two that do not:
  `git grep -n -E 'KeyboardAvoiding|keyboardVerticalOffset|automaticallyAdjustKeyboardInsets' -- src/screens/SignInModal.tsx src/screens/SettingsScreen.tsx | wc -l`
  prints `0`. SignInModal is a Modal whose backdrop is
  `justifyContent: 'flex-end'`, so the sheet sits at the bottom, where the
  keyboard covers it. The server address box is in SettingsScreen's
  ScrollView.

## S0-4 — F304, the plan

- The server, in this repository: `GET /v1/billing/subscription`
  (`src/motodiag/api/routes/billing.py`, `get_subscription`, line 146)
  answers 200 with an empty `SubscriptionResponse()`, tier null, when the
  account has no subscription.
- The app: `src/hooks/useTier.ts` sets `'individual'` on a 402 or a 404
  (lines 111 and 112) and on any tier it does not know, null included
  (line 131). `src/screens/PlanScreen.tsx` says "No plan yet" only for a
  tier of null (line 43), marks the matching plan "(your plan)" (line 136),
  and disables "Manage plan" only while a request runs (`disabled={busy}`,
  line 120).
- Their tests: `__tests__/hooks/useTier.test.ts` and
  `__tests__/screens/Plan.smoke.test.tsx`.

## S0-5 — the bundle ID (K147)

- The iOS app's ID:
  `git grep -n PRODUCT_BUNDLE_IDENTIFIER -- ios/MotoDiag.xcodeproj/project.pbxproj`
  lists 2 lines, 313 and 345, both `com.bandithero.motodiag`.
- Files in the app naming it: `git grep -l 'com.bandithero.motodiag' -- . | wc -l`
  prints `12`.
  - The iOS project, and three living documents that name it for iOS:
    `README.md`, `docs/testflight.md` and `docs/app-store-listing.md`.
  - Android: its `build.gradle`, two Kotlin files and `settings.gradle`.
  - The record of Phases 185 to 204: `docs/ROADMAP.md` and
    `implementation.md`.
  - npm's package name, in `package.json` and `package-lock.json`.
  - This phase changes the iOS project and the three documents only.
- The App Store Connect record, created 2026-11-26 (K145), holds the old
  ID, and no build has been uploaded. Apple's "Changing the bundle
  identifier" (developer.apple.com) says a record's bundle ID can change
  until the first build is uploaded. It also says deleting a record does
  not free its bundle ID, so the record stays.
- The server sends pushes to the app under `MOTODIAG_APNS_TOPIC`. The
  bundle ID appears in this repository's `src/motodiag/push/sender.py`
  only as that setting's example (line 15). Whether live sets it is read
  on the home desktop, before the upload.

## S0-6 — the verbs

Each thing the row promises is something a person can see on a phone: the
icon on the home screen; "Mekno" under it and in the app; the sign-in sheet
and the server address box above the keyboard while typing; "No plan yet"
on the plan screen, from Settings, for an account with no plan. The new ID
is seen as a new app on the phone, and as the App Store Connect record's
bundle ID once switched. The cable install after the merge checks each.

## S0-7 — classification

**Extension.** The icon set, Info.plist, the two screens, the hook and the
project's bundle ID all exist; this phase fills the icon set and corrects
the rest. No new screen, no new route, no server change.
