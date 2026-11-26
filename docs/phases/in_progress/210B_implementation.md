# Phase 210B — The app's icon, its name, and two day-one fixes

**Version 1.0, 2026-11-26.** The plan, by the advisor session on the Mac
(K145, K146, K147), from this repository's master `00283d5` and the app's
`main` `4c6c1bd`. It is built by the operator's own session in
`moto-diag-mobile`, on the branch
`phase-210B-the-apps-icon-name-and-day-one-fixes`, from
`docs/prompts/210B_the_apps_icon_name_and_day_one_fixes.txt`.
Classification: **extension** (`210B_step0.md`). Committed before any code.

## Goal

The app can go to TestFlight for the first shop, which is Phase 210's step
3:
- it has an icon, the website's M;
- it is called Mekno wherever it shows a person its name;
- its iOS bundle ID is `com.getmekno.app` (K147);
- the sign-in sheet and the server address box stay above the keyboard
  (F303);
- a person with no plan sees "No plan yet", without "Manage plan" (F304).

No server change.

## The plan of record

Not on "Next, in order": the phase finishes 210's step 3 (#24, closed
2026-11-25), which the operator runs after the merge. The fleet does not
wait for it and opens no issue for it. The list's next phase stays 409
(K140). K145 records the operator's choices for the step, K146 the icon's
picture, and K147 the bundle ID.

## Logic

### 1. The icon

- **The picture.** `210B_icon/mekno_app_icon_1024.png`, sha256
  `09d3db160b451cf2862ef8579f7489ff67f67bac02e798b6ffe5c5a94e1f3430`, drawn
  by `210B_icon/make_app_icon.py` (Step 0, S0-1). It is the M of
  `site/favicon.svg`, redrawn from its own points at 1024 by 1024. It fills
  the square, because the phone rounds the corners, and it has no alpha.
- **In the app.** The icon set holds it as `AppIcon-1024.png`. Its
  `Contents.json` takes Xcode's single-size form: one image, idiom
  `universal`, platform `ios`, size `1024x1024`.
- **Taken by its sum.** The app's session fetches the picture from this
  branch and checks the sum before using it. It draws nothing and edits
  nothing.

### 2. The name

"Mekno" replaces "MotoDiag" wherever the app shows a person its name
(S0-2):
- the display name and the seven permission sentences in Info.plist;
- the home screen's title and heading;
- the Bluetooth, camera and microphone sentences;
- the two server-address sentences, with the three test cases that match
  them.

These stay as they are:
- the code's own names, such as `MotoDiagApi`, the `ios/MotoDiag` folder
  and the scheme;
- the label the app gives its sign-ins on the server.

The bundle ID is item 5.

### 3. F303, the keyboard

- The sign-in sheet and Settings' server address box stay above the
  keyboard while a person types in them, as the four screens of S0-3 do.
- The app's FOLLOWUPS marks F303 closed by this phase, in the pull request.

### 4. F304, the plan before any plan

- The plan screen tells "no plan" apart from Individual. That is:
  - the server's 200 with tier null;
  - a 402 or a 404.
- With no plan:
  - it says "No plan yet";
  - it marks no plan "(your plan)";
  - it does not offer "Manage plan".
- These stay as they are:
  - the Shop tab's rule (`hasShopAccess`);
  - every other use of the tier.
- The app's FOLLOWUPS marks F304 closed by this phase, in the pull request.

### 5. The bundle ID (K147)

- The iOS project's `PRODUCT_BUNDLE_IDENTIFIER` becomes
  `com.getmekno.app`, in both places (Step 0, S0-5).
- `README.md`, `docs/testflight.md` and `docs/app-store-listing.md` say so
  for iOS.
- These stay as they are:
  - Android's applicationId, its package names and `settings.gradle`;
  - npm's package name;
  - the app's record of Phases 185 to 204.
- The app's session registers nothing with Apple and does not touch App
  Store Connect.
- After the merge, the operator's cable build registers the new ID. The
  operator then switches the App Store Connect record's bundle ID to it,
  before the first upload, which Apple allows until then. The record is
  kept, because a deleted record never frees its ID.

### 6. The record

This repository keeps the phase's own record, which the advisor writes from
the app's pull request: `210B_step0.md`, this plan, `210B_phase_log.md`, the
`210B_icon` folder, row 210B and, at the close-out, the handoff. The app's
session writes nothing here. The app's `phase_log.md` (Phases 185 to 204)
is not touched.

## Rule-1 stops

- **A real fork:** none left. K145, K146 and K147 answered them.
- **A threshold or a rule's definition:** none.
- **A test that cannot be made green:** the app's session stops and says
  so.
- **A login or a credential:** none in the build. The tests use made-up
  values. The TestFlight upload after the merge is on the operator's own
  Apple account, from the advisor's tested block.
- **A live-database change:** none.

One more stop, the app's own: if Xcode or App Store Connect refuses the
single-size icon, the session stops. It does not change the picture.

## Tests

In the app, each seen red before its code:
1. **The icon set.** It holds exactly one image, and its file is present.
   The file is 1024 by 1024, its PNG colour type is 2 (RGB, no alpha), and
   its sha256 is the one above. Today's main fails this.
2. **The name.**
   - The display name is Mekno, and no Info.plist string begins
     "MotoDiag".
   - The home screen shows Mekno.
   - The two server-address sentences say "Mekno", through the updated
     cases in `__tests__/api/serverUrl.test.ts`.
   - The Bluetooth, camera and microphone sentences say "Mekno".
3. **F303.** The sign-in sheet and the server address box are inside the
   keyboard's handling, on the rendered tree.
4. **F304.**
   - The tier is told apart from "no plan" on a 200 with tier null, and on
     a 402 or a 404.
   - The plan screen with no plan shows "No plan yet", no "(your plan)"
     and no "Manage plan".
   - With the Shop plan it shows "Shop (your plan)" and "Manage plan".
5. **The bundle ID.** Both `PRODUCT_BUNDLE_IDENTIFIER` lines of
   `project.pbxproj` say `com.getmekno.app`, and the old ID is gone from
   the file. Today's main fails this.

Every existing test passes. The pull request names the ones changed for the
new name.

## Non-goals

- F305, F306 and F307.
- Android's launcher name and its applicationId.
- A Mac version.
- The build number and the TestFlight upload, which is the advisor's block
  after the merge.
- The testers and Tailscale, which come after the upload.
- Any server change.
- Any picture other than K146's.

## After the merge

These are the operator's steps, each from a block the advisor tests first:
1. The cable install of the app's main on the operator's phone:
   - it registers the new bundle ID, and arrives beside the old MotoDiag
     app, which the operator deletes;
   - the icon, Mekno, the keyboard, "No plan yet".
2. In App Store Connect, the operator switches the record's bundle ID to
   `com.getmekno.app`. A read-only block on the home desktop also says
   whether live sends pushes under the old ID.
3. The build and its upload to TestFlight, build 1.
4. The shop's people as internal testers in App Store Connect.
5. Tailscale: a rule letting people the desktop is shared with reach only
   its port 443, then the desktop shared with each person.
6. Each phone: TestFlight and the app, Tailscale and the share, the
   server's health page in Safari, then the app as far as the sign-in.

## Version history

| version | date | change |
|---|---|---|
| 1.0 | 2026-11-26 | The plan, from Step 0 (K145, K146, K147). |
