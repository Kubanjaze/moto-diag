# Phase 210C — phase log

**Status: in progress.** Started 2026-11-26 by the advisor session on the
Mac (K148). Built by the operator's own app session in `moto-diag-mobile`,
from `docs/prompts/210C_no_developer_panels_and_apples_location_note.txt`.

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
