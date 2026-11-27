# Phase 210B — The app's icon, its name, and two day-one fixes

**Version 1.1, 2026-11-26.** Closed. v1.0 (the same day) was the plan by
the advisor session on the Mac (K145, K146, K147), from this repository's
master `00283d5` and the app's `main` `4c6c1bd`. Built by the operator's
own session in `moto-diag-mobile`, on the branch
`phase-210B-the-apps-icon-name-and-day-one-fixes`, from
`docs/prompts/210B_the_apps_icon_name_and_day_one_fixes.txt`: pull request
#15, head `7f2d832`, merged by the operator as `3fa252b` on 2026-11-26.
Classification: **extension** (`210B_step0.md`). The plan was committed
before any code; this version records what was built, from the pull
request's description and the advisor's review of it, and the steps after
the merge.

## Goal

The app can go to TestFlight for the first shop, which is Phase 210's step
3:
- it has an icon, the website's M;
- it is called Mekno wherever it shows a person its name;
- its iOS bundle ID is `com.getmekno.app` (K147);
- the sign-in sheet and the server address box stay above the keyboard
  (F303);
- a person with no plan sees "No plan yet", without "Manage plan" (F304).

No server change. All five are on the app's main since `3fa252b`, and
build 1 of it is on TestFlight.

## The plan of record

Not on "Next, in order": the phase finishes 210's step 3 (#24, closed
2026-11-25), which the operator runs after the merge. The fleet did not
wait for it and opened no issue for it. The list's next phase stayed 409
(K140), whose row went in progress on master meanwhile. K145 records the
operator's choices for the step, K146 the icon's picture, and K147 the
bundle ID.

## Logic

### 1. The icon

- **The picture.** `210B_icon/mekno_app_icon_1024.png`, sha256
  `09d3db160b451cf2862ef8579f7489ff67f67bac02e798b6ffe5c5a94e1f3430`, drawn
  by `210B_icon/make_app_icon.py` (Step 0, S0-1). It is the M of
  `site/favicon.svg`, redrawn from its own points at 1024 by 1024. It fills
  the square, because the phone rounds the corners, and it has no alpha.
- **In the app** (`1b5195f`). The icon set holds it as `AppIcon-1024.png`.
  Its `Contents.json` takes Xcode's single-size form: one image, idiom
  `universal`, platform `ios`, size `1024x1024`.
- **Taken by its sum.** The app's session fetched the picture from this
  branch and checked the sum before using it. It drew nothing and edited
  nothing.

### 2. The name

"Mekno" replaces "MotoDiag" wherever the app shows a person its name
(S0-2), in 15 places (`1a85131`):
- the display name and the seven permission sentences in Info.plist;
- the home screen's title and heading;
- the Bluetooth, camera and microphone sentences;
- the two server-address sentences, with the test cases that match them.

These stay as they are:
- the code's own names, such as `MotoDiagApi`, the `ios/MotoDiag` folder
  and the scheme;
- the label the app gives its sign-ins on the server.

The bundle ID is item 5.

### 3. F303, the keyboard

- The sign-in sheet and Settings' server address box stay above the
  keyboard while a person types in them, as the four screens of S0-3 do
  (`9004d90`): the sheet's backdrop is a `KeyboardAvoidingView`, and
  Settings' scroll view sits inside one, with padding on iOS and none on
  Android.
- The app's FOLLOWUPS marks F303 closed by this phase, in the pull request.

### 4. F304, the plan before any plan

- The plan screen tells "no plan" apart from Individual (`7f2d832`). That
  is:
  - the server's 200 with tier null;
  - a 402 or a 404.
- `useTier` keeps its tier as it was and also returns the plan the server
  reported, which is none in those cases. With no plan the screen:
  - says "No plan yet";
  - marks no plan "(your plan)";
  - does not offer "Manage plan".
- These stay as they are:
  - the Shop tab's rule (`hasShopAccess`);
  - every other use of the tier.
- The app's FOLLOWUPS marks F304 closed by this phase, in the pull request.

### 5. The bundle ID (K147)

- The iOS project's `PRODUCT_BUNDLE_IDENTIFIER` is `com.getmekno.app`, in
  both places (Step 0, S0-5; `6b20c96`).
- `README.md`, `docs/testflight.md` and `docs/app-store-listing.md` say so
  for iOS.
- These stay as they are:
  - Android's applicationId, its package names and `settings.gradle`;
  - npm's package name;
  - the app's record of Phases 185 to 204.
- The app's session registered nothing with Apple and did not touch App
  Store Connect.
- After the merge, the operator's cable build registered the new ID, and
  App Store Connect's record already showed `com.getmekno.app` before the
  first upload. The record is kept, because a deleted record never frees
  its ID.

### 6. The record

This repository keeps the phase's own record, which the advisor wrote from
the app's pull request: `210B_step0.md`, this plan, `210B_phase_log.md`, the
`210B_icon` folder, the `210B_blocks` folder (the notifications check and
the TestFlight upload, as they ran), row 210B and the handoff. The
app's session wrote nothing here. The app's `phase_log.md` (Phases 185 to
204) was not touched.

## Rule-1 stops

None was reached.
- **A real fork:** none left. K145, K146 and K147 answered them. Apple's
  note on build 1 was new, and the operator answered it with Phase 210C
  (K148).
- **A threshold or a rule's definition:** none.
- **A test that cannot be made green:** none. Every test went green.
- **A login or a credential:** none in the build. The tests use made-up
  values. The TestFlight upload ran on the operator's own Apple account in
  Xcode, from the advisor's tested block.
- **A live-database change:** none. Live was only read, once: the
  server's notification settings (the log).

The app's own stop did not happen: Xcode and App Store Connect took the
single-size icon, and build 1 shows it in TestFlight.

## Tests

In the app, each seen red on `4c6c1bd` before its code (the pull
request's figures in brackets):
1. **The icon set** (`__tests__/ios/appIcon.test.ts`; 4 of 4 red). It holds
   exactly one image, and its file is present. The file is 1024 by 1024,
   its PNG colour type is 2 (RGB, no alpha), and its sha256 is the one
   above.
2. **The name** (`__tests__/ios/appName.test.ts`,
   `__tests__/screens/MeknoName.test.tsx` and one case in
   `HomeSmokeWording.test.tsx`; 18 cases red).
   - The display name is Mekno, and no Info.plist string begins
     "MotoDiag".
   - The home screen shows Mekno.
   - The two server-address sentences say "Mekno", through the updated
     cases in `__tests__/api/serverUrl.test.ts`.
   - The Bluetooth, camera and microphone sentences say "Mekno".
3. **F303** (`__tests__/screens/KeyboardAvoid.test.tsx`; 5 of 5 red). The
   sign-in sheet and the server address box are inside the keyboard's
   handling, on the rendered tree.
4. **F304** (`__tests__/hooks/useTier.test.ts` and
   `__tests__/screens/Plan.smoke.test.tsx`; 9 red).
   - The tier is told apart from "no plan" on a 200 with tier null, and on
     a 402 or a 404.
   - The plan screen with no plan shows "No plan yet", no "(your plan)"
     and no "Manage plan".
   - With the Shop plan it shows "Shop (your plan)" and "Manage plan".
5. **The bundle ID** (`__tests__/ios/bundleId.test.ts`; 2 of 2 red). Both
   `PRODUCT_BUNDLE_IDENTIFIER` lines of `project.pbxproj` say
   `com.getmekno.app`, and the old ID is gone from the file.

Every existing test passes. The pull request names the four cases changed
for the new name, in `serverUrl.test.ts`, and the mock in
`Plan.smoke.test.tsx` that gained the plan.

## Non-goals

- F305, F306 and F307.
- Android's launcher name and its applicationId.
- A Mac version.
- The build number and the TestFlight upload, which were the advisor's
  block after the merge. Build 1 kept the project's number, 1.
- The testers and Tailscale, which came after the upload.
- Any server change.
- Any picture other than K146's.

## After the merge

These were the operator's steps, each from a block the advisor tested
first; the log has each one's outcome.
1. **Done.** The cable install of the app's main on the operator's phone:
   the new bundle ID, beside the old MotoDiag app, which the operator
   deleted; the icon, Mekno, the keyboard, "No plan yet".
2. **Done.** App Store Connect's record already showed
   `com.getmekno.app`. The read-only block on the home desktop found live's
   phone notifications off, so the server needs nothing for the new ID
   today.
3. **Done.** Build 1 (1.0, 1) uploaded to TestFlight and Ready to Submit.
   Apple's email about it named ITMS-90683, a missing location purpose
   string; that is Phase 210C (K148).
4. **Set up, and rehearsed on the operator's phone.** Two internal groups:
   "First look" (the operator, automatic) and "Shop one" (manual, no
   testers yet). The shop's people wait for shop one's day: each needs an
   App Store Connect login first.
5. **The rule is saved.** People the desktop is shared with reach only its
   port 443. The shares wait for each person.
6. **Rehearsed on the operator's phone:** TestFlight and the app, signed in
   on live. The shop's phones wait for shop one's day.

## Deviations

1. **Three small extras in the pull request,** each named in it:
   - Settings' scroll view also took `keyboardShouldPersistTaps="handled"`,
     as the four other keyboard screens have, so Save works on the first
     tap while the keyboard is up;
   - "Manage plan" is also hidden while the plan is still "Checking…";
   - the server address's 404 case also pins "Is that a Mekno server?",
     a fourth changed case where Step 0 counted three.
2. **The cable install ran twice.** The first run stopped at the app's
   tests: `TermsModal.smoke.test.tsx` timed out at jest's 5 s limit, right
   after `npm ci`. It passed in every re-run, so the second run left out
   `npm ci` and ran jest at half the workers.
3. **App Store Connect's bundle ID** was planned as the operator's switch.
   When the advisor read it after the cable install, it already showed
   `com.getmekno.app`; who switched it was not said.
4. **Apple's note on build 1,** ITMS-90683, came with a successful
   delivery. It was not in the plan, and it was not fixed here: the
   operator opened Phase 210C for it (K148).
5. **Two internal groups, not one.** The first group was made with
   automatic delivery, which Apple does not let change after creation. It
   became "First look", the operator's own. "Shop one" is manual, so a
   shop phone gets a build only when it is added.
6. **Steps 4 to 6 for the shop's people were not run.** They wait for shop
   one's day (the handoff). The operator's own phone ran them as a
   rehearsal.
7. **`docs/app-store-listing.md` in the app** still says MotoDiag in its
   Name row and its description. The plan named only its bundle ID. It is
   left for Phase 410's listing.

## Results

| | before (`main` `4c6c1bd`) | after (`7f2d832`) |
|---|---|---|
| `npx jest` | 113 suites, 1308 passed | 118 suites, 1345 passed (+37) |
| `npx tsc --noEmit` | clean | clean |
| `npx eslint .` | 0 errors, 150 warnings | 0 errors, 150 warnings |

- **The advisor's re-run on the Mac,** 2026-11-26, in a scratchpad clone at
  `7f2d832`, whose tree `c19ac3df` is the merge's: tsc exit 0; eslint exit
  0, 0 errors and 150 warnings; jest 118 suites and 1345 tests passed.
- **Merged** by the operator as `3fa252b` (moto-diag-mobile `main`),
  2026-11-26 at 19:16 UTC.
- **After the merge:** the cable install on the operator's iPhone; build 1
  on TestFlight, Ready to Submit, expiring 2027-02-24; the TestFlight copy
  installed on the operator's phone and signed in on live; the groups
  "First look" and "Shop one"; the Tailscale rule.
- **This repository:** no code changed. Its regression of record, on
  `85315cb`, is in the log.

## Planned items

- [x] The icon, the website's M (`1b5195f`)
- [x] The bundle ID `com.getmekno.app` (`6b20c96`)
- [x] The name, Mekno (`1a85131`)
- [x] F303, the sign-in sheet and the server box above the keyboard
  (`9004d90`)
- [x] F304, "No plan yet" (`7f2d832`)
- [x] The tests, each seen red; tsc, eslint and jest clean
- [x] The app's pull request, merged by the operator after review (#15,
  `3fa252b`)
- [x] After the merge: the cable install, App Store Connect's ID and live's
  notifications, build 1 on TestFlight, the two groups, the Tailscale rule
- [x] The close-out here: v1.1, the log, row 210B ✅, the handoff

## Version history

| version | date | change |
|---|---|---|
| 1.0 | 2026-11-26 | The plan, from Step 0 (K145, K146, K147). |
| 1.1 | 2026-11-26 | Closed: what was built (pull request #15, `7f2d832`, merged as `3fa252b`), steps 1 to 6 after the merge, seven deviations, the results. |
