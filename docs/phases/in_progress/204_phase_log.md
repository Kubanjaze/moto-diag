# Phase 204 — Gate 10: Mobile Integration Test + TestFlight — Phase Log

**Status:** 📋 Planned
**Started:** 2026-09-04 | **Completed:** —
**Repos:** `Kubanjaze/moto-diag` + `Kubanjaze/moto-diag-mobile`, branch
`phase-204-gate10`. **Track I closes here.**

---

### 2026-09-04 16:44 — Plan written (Step 0 audit + v1.0)

- **The audit's verdict: the gate cannot pass today**, and can fail
  three ways before reaching the report — ffmpeg absent (every upload
  would land in `analysis_failed`), F46's video-capture blocker open
  since May, and the only known upload fix sitting uncommitted in a
  two-month-old stash.
- **ffmpeg 9.0.1 installed during the audit**, removing blocker one.
- **New finding — the leading F46 hypothesis.** `ios/Podfile:1` forces
  `RCT_NEW_ARCH_ENABLED=0` (Phase 196's BLE fix) while
  `Info.plist:57` sets `RCTNewArchEnabled=true`, and the app boots
  `fabric: true` — confirmed in the device console this session. Pods
  built old-arch, runtime on Fabric. F46's own candidate list names this
  interaction. Not a free fix: 196B, 197 and 198 all passed under the
  current setting.
- **Device-verification debt the gate should close:** 199's
  analysis-complete push, 200's share link opened as a customer, 201's
  browse/order journey, 202's device leg (never ran), and 203 on
  physical hardware rather than the simulator.
- **TestFlight is not ready:** `aps-environment` is `development`
  (TestFlight requires `production`) on an entitlements file shared by
  Debug AND Release; `DEVELOPMENT_TEAM` missing from Debug; a
  non-distribution signing identity; and `ITSAppUsesNonExemptEncryption`
  plus two usage strings and `UIBackgroundModes` absent.
- **Android descoped to its own phase** (user decision): it signs
  release with the DEBUG keystore, so Play would reject it outright, and
  the app has never been launched on Android at all.
- **User decisions:** iOS only · test the upload before touching the
  stash · sweep the outstanding device claims · all TestFlight config
  plus a signed archive, with the upload left to the user.
- **Next milestone:** static blocker work while the phone is free →
  device build → capture step first (the cheapest disqualifier) →
  upload/analysis/report/share → the sweep → archive + export.
