# Phase 204 — Gate 10: Mobile Integration Test + TestFlight — Phase Log

**Status:** ✅ Complete — PASS on the headline flow, PARTIAL on the sweep
**Started:** 2026-09-04 | **Completed:** 2026-09-07
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

---

### 2026-09-07 09:55 — GATE RUN: five bugs found, headline flow PASSES

The gate did its job: it found things no test suite had. Every fix below
came from running the product on a physical iPhone, not from reading
code, and each is its own commit per bug-fix discipline.

- **fix #1 — F46, open since 2026-05-16, misdiagnosed.** The ticket said
  "VisionCamera fails to initialize". It does not. iOS reports
  `not-determined` until an app asks; `combinedStatus` collapses that to
  `'unknown'`; and VideoCaptureScreen's `'unknown'` branch rendered a
  bare spinner with no button and no effect, while the ONLY call to
  `request()` sat in the `'denied'` pane — unreachable without first
  being denied. A fresh install could never ask. PhotoCaptureScreen
  (194) renders a "Grant access" button and was never stuck, which is
  why photo and voice smoked fine while video never did. **The wrong
  diagnosis is why this survived four months**: it made the bug look
  like a dependency problem rather than ten lines of our own logic.
- **fix #2 — ffmpeg 9 REMOVED `-vsync`.** Not deprecated, removed. It
  fails while splitting the argument list, so every upload became a
  silent `analysis_state='unsupported'` behind a successful 201. Now
  `-fps_mode vfr`. Guards pin both the arg list and the INSTALLED
  binary's support.
- **fix #3 — upload 422: `width`/`height` arrived as `0`.** The screen
  built metadata with `video.width ?? 1280`; VisionCamera 4 returns a
  real `0`, and `??` only substitutes for null/undefined, so `0` reached
  a field requiring `gt=0`. Confirmed on device: the stored recording
  reads 1280x720, i.e. the fallback now engaging.
- **fix #4 — the reason was being thrown away.** The 422 was an
  `HTTPException` raised inside the route, so the app-wide validation
  handler never saw it and NOTHING was logged; the client reads only
  `response.status`. Four blind device round-trips. Now logged with the
  raw sidecar. (Defining the module logger is also what turned the 422
  into a 500 and finally surfaced the traceback naming width/height —
  an accident that paid off.)
- **fix #5 — my own regression, caught by the full suite.** The new
  validation handler also reshaped the 422 BODY, breaking Phase 192B's
  contract test that `detail` is the structured field-error list.
  Logging was the goal; changing the response was overreach. Now logs
  and delegates to FastAPI's own handler, with a test pinning both
  halves so they cannot be traded for one another.

**Device evidence (physical iPhone 16 Pro):** camera prompt appears and
is granted; a 7.3s recording uploads; ffmpeg extracts 15 frames; a live
Claude Sonnet vision call returns findings (correctly reporting no
motorcycle — the clip was a bedroom); the report renders; **Share link
minted FROM THE PHONE** (`10.0.0.89`, 201), sent over Messages, and
opened in Safari — 4 credential-free fetches, all 200. **Phase 199's
analysis-complete push fired** (`push sent to user 1`), closing the item
199 deferred for want of a video; the banner itself was not watched for,
so that half stays unverified.

**Honest gaps, recorded rather than absorbed into the pass:** the 201
parts and 202 timer screens never got their device leg (battery hit 4%);
196's BLE connect still needs hardware (F56); F63 filed for a playback
freeze that kills the app; F64 filed as a RELEASE BLOCKER because share
links currently point at a LAN address.

**Two wrong turns worth recording**, since the plan named one of them as
its leading hypothesis: the New-Architecture mismatch was NOT F46's
cause (RN 0.85 ignores the Podfile opt-out; everything is consistently
Fabric and that line is vestigial), and the parked stash's
multipart-boundary diagnosis was ALSO wrong — applied, disproven by the
traceback, and reverted. Testing before adopting is what kept it out of
the tree. The stash remains at `stash@{0}`, untouched.

**Suites:** backend 4743 passed / 0 failed (7:40); mobile 79 suites /
985 tests, tsc + eslint clean.

**TestFlight:** `ios/build/export/MotoDiag.ipa` (13.4 MB), verified on
the ARTEFACT — `aps-environment: production`, `beta-reports-active`,
`get-task-allow: false`, Apple Distribution, Team Store profile. Phase
199 had shipped ONE entitlements file for both configurations, so a
TestFlight build would have requested a sandbox push token and failed
silently for every tester. Upload needs the user's Apple credentials;
runbook in `docs/testflight.md`.
