# Phase 210C — phase log

**Status:** Complete. Started 2026-11-26 by the advisor session on the
Mac (K148), and closed the same day. Built by the operator's own app
session in `moto-diag-mobile`, from
`docs/prompts/210C_no_developer_panels_and_apples_location_note.txt`.

## 2026-11-26 — why this phase, Step 0 and v1.0

**How it came up.** Build 1 of Mekno reached TestFlight on 2026-11-26
(Phase 210B, after its merge), and the operator installed it on their own
phone through the "First look" group.
- The home screen it showed still carries developer panels: the "Phase
  191" line, Backend, Authed smoke and BLE scan. The advisor recommended
  hiding them before shop one's day.
- Apple's email about build 1 named ITMS-90683, a missing
  `NSLocationWhenInUseUsageDescription`, while saying the delivery
  succeeded.

**The operator's words, K148.** "Yes to hiding the developer panels, and
add a second item: Apple flagged build 1 for a missing
NSLocationWhenInUseUsageDescription in the iOS Info.plist while code or a
library calls location APIs." The rest is quoted whole in
`docs/decisions.md`: find what calls location and remove it if the app does
not need it, check Android, one small app phase in 210B's shape, then build
2 on TestFlight; steps 3 and 4 of 210's list wait for shop one's morning.

**What Step 0 found** (`210C_step0.md`):
- The location code is react-native-vision-camera 4.7.3's, built in by
  default. The app never asks for a location on iOS. The library's own
  switch, `$VCEnableLocation = false`, takes out the request Apple's note is
  about; build 1's binary held it once.
- Measured with CocoaPods on the Mac: the switch changes exactly two lines
  of `ios/Podfile.lock`, and the second is the Podfile's own SHA-1, so an
  app session without CocoaPods can write both.
- Android: two Bluetooth libraries declare location permissions with no
  limit, against the app's own Android 11 cap. This Mac cannot build
  Android (no SDK, no Java), so the app's manifest and its test are the
  check.
- The development flag the operator asked for exists: `__DEV__`, through
  `src/config/features.ts`, as `OBD_SUPPORT` already does.

**The record on master** holds row 210C, the prompt with its line in
`docs/prompts/README.md`, and K148. It also brings row 210B on master to
its branch's text, so the two branches merge without a conflict.

**This branch** holds Step 0, v1.0 and this log. Not on "Next, in order":
the phase finishes 210's step 3, beside the list, so the plan of record and
its pins are unchanged.

## 2026-11-26 — the app's pull request, build 2, and the close-out

**The app's pull request, moto-diag-mobile #16** (head `b611a3b`), from the
operator's app session. Four commits, one per item: `7685b4f`, `5186fe3`,
`9e627d7`, `b611a3b`. The session ran on Linux, so it ran no `pod install`
and wrote the lock's two lines from Step 0's measurement, as the plan
allowed.
- Reviewed by the advisor on the Mac at about 18:34 EST, in a scratch clone
  at `b611a3b` with a copy-on-write copy of the real checkout's
  `node_modules` (the lock files are the same):
  - items 1 to 4 as planned. The two comments beyond the plan (the Android
    manifest's, the home screen's) say why; judged fine.
  - a real `pod install` (CocoaPods 1.16.2), with the real checkout's
    installed libraries copied in: `Podfile.lock` unchanged, so the pull
    request's two lines are what CocoaPods writes; `PODFILE CHECKSUM`
    `8ca28318…` is `shasum -a 1` of its Podfile; VisionCamera's debug and
    release settings name `VISION_CAMERA_ENABLE_LOCATION` 0 times;
    `Pods/Manifest.lock` matches; only `project.pbxproj`'s build-phase order
    changed, not committed, as planned.
  - tsc exit 0; eslint 0 errors and 150 warnings, the same 150 as
    `3fa252b`; no test line removed.
  - jest: run 1 (`--maxWorkers=2`) 1359 of 1360; `useDTC` "starts loading,
    transitions to success" failed with "TypeError: window.dispatchEvent is
    not a function". Run 2: the same error in `useVehicles` "exposes empty
    vehicles array on empty list response". Run 3 (`--maxWorkers=50%`): 122
    suites, 1360 passed.
  - the control: main `3fa252b` at `--maxWorkers=2` passed all 1345, with
    one line of the same error. The new home test with both hook test files
    in one process, 3 runs: all green. 210B's regression of record ran
    beside these (load 10 to 11).
  - judged a timing failure already in the app's suite under load, not this
    pull request's: F308, below.
- Merged by the operator as `1fbd967`, 2026-11-26 at 23:36 UTC, from the
  advisor's block, which ended ALL GOOD: "Merged pull request 16 as
  1fbd967d7d108f7dee0c7c395e1e3664d124fbe8; this Mac's copy of the app is
  on it."

**Steps 2 and 3, `pod install` and build 2.** The block is
`210C_blocks/1_build2_testflight.txt` (sha256
`c7b7c7175db0cd4534934f8e6015184ad378e119727e41b47ee095bdf95e932c`).
- Read on the Mac before it was written:
  - the real checkout was already at `1fbd967`, and clean;
  - its installed libraries were build 1's: `Pods/Manifest.lock` differed
    from `Podfile.lock` in exactly the pull request's two lines, so the app
    project's "[CP] Check Pods Manifest.lock" phase would refuse to build
    without `pod install`;
  - the merge's tree is the pull request head's tree (`9bb8cf42…`);
  - build 1's archive held the request in exactly one file, its `MotoDiag`
    program: the positive control for the block's check.
- Tested first in a scratch clone at `1fbd967`, with stand-ins for
  `xcodebuild`, `caffeinate`, `pod` and `df`: 29 cases.
  - One case ran the real `pod install` on a copy of the real checkout's
    installed libraries. It printed "[VisionCamera] $VCEnableLocation is set
    to false!", left the lock unchanged, changed only the project file (put
    back), and left the tree clean. The release settings' location flag went
    from 1 to 0, and the libraries' lock equals the app's. `pod` asked
    `xcodebuild` only `-version`.
  - Ten breaks planted on purpose each turned it red: `pod` able to read
    the block's own text, no UTF-8 for `pod`, no put-back of the project
    file, the camera library's message not checked, the lock not checked,
    the settings not checked, build 1 accepted, no program file required, no
    binary check, and a check of the main program only (which misses a
    framework).
  - The bench had two gaps of its own first, fixed before the block went
    out: bash 3.2's empty array under `set -u`, and `pod`'s own
    `xcodebuild -version` answered by the stand-in.
- The operator ran it on the Mac at 19:31 EST, plugged in, and it ended
  ALL GOOD:
  - "Libraries updated: the camera's location code is off, and the app's
    lock file is unchanged."
  - "Built: Mekno 1.0, build 2 (com.getmekno.app), with its icon, pointed at
    the live server, and without the location request Apple flagged."
  - then Xcode's "Upload succeeded" at 19:35 EST.
- Read back by the advisor from the archive: `com.getmekno.app`, Mekno, 1.0
  (2); the counts in v1.1's Results; no file in the app holds the request;
  no `NSLocation` key; CoreLocation still linked; the app's checkout clean
  on main at `1fbd967`.

**Step 4, Apple.** Read by the advisor in the operator's inbox, read-only.
TestFlight's "Mekno 1.0 (2) for iOS is now available to test." came at
00:36 UTC (19:36 EST), to the "First look" tester. No email about issues
came for build 2 by 20:06 EST. Build 1's came at 20:13 UTC, about a minute
after its upload, and names Version 1.0 Build 1.

**Step 5, the phone.** The operator, after the update in TestFlight: "all
those things check on the iphone". The home screen shows Auth, Settings
and DTC lookup and no developer panel, and signing in works.

**Step 6, not run.** The operator, the same evening: "i have no shops yet,
i only have individual users as consumers", and "i want to release to
individuals, work out bugs then push to get into shops". "Shop one" stays
as it is until a shop comes.

**F308** is filed in the app's FOLLOWUPS (`56eb617` in moto-diag-mobile,
pushed by the operator's block): the app's tests fail now and then on a
busy Mac. It holds this phase's two hook failures and 210B's TermsModal
timeout.

**The close-out.**
- No guard refused a command in this phase's work.
- Master is merged in as `8a583d8`: 210B's close-out (`62b49c4`, `71b5153`)
  and its merge `0ebd926`, documents only, with no conflict. The
  whole-tree command passed before that commit (3058 passed, 1 skipped,
  279 s).
- The regression of record. This phase changed no code in this repository.
  Every commit since `85315cb`, 210B's regression commit, adds documents
  only: on master (`77fe1bd`, `62b49c4`, `71b5153`, `0ebd926`) and here
  (`fa824e0`, and the merge `8a583d8`, which puts `85315cb` under this
  branch). So 210B's run is this phase's regression of record; a second
  40-minute run would test the same code. Copied as printed:

Regression of record: 13272 passed, 0 failed, 49 skipped, 0 errors at `85315cb` (39 min 24 s wall, `python -m pytest -n auto --dist load --cov=motodiag`, exit 0)
Skipped in the regression of record: [1] tests/test_phase244H_test_db_isolation.py:79: no production database on this machine
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:61: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [4] tests/test_phase388_fence_boundary.py:96: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [3] tests/test_phase388_fence_boundary.py:105: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:113: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:120: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:125: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:131: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:139: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:148: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:159: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:164: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:170: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:177: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:186: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:198: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [2] tests/test_phase388_fence_boundary.py:210: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:216: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [7] tests/test_phase388_fence_boundary.py:221: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:235: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:244: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [2] tests/test_phase388_fence_boundary.py:280: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:287: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:291: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:295: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:303: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [2] tests/test_phase388_fence_boundary.py:316: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:325: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:330: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:338: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:344: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:350: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:354: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:360: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase390_space.py:327: bubblewrap is the desktop's
Line coverage of record: 88.66% at `85315cb` (the pin is 88.00%)

- No bug-fix register: none was needed.
