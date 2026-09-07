# Phase 204 — Gate 10: Mobile Integration Test + TestFlight

**Version:** 1.1 | **Tier:** Gate | **Date:** 2026-09-07 (v1.0 plan 09-04 -> v1.1 as-built)

## Existing-code audit (Step 0 — run 2026-09-04, before this plan)

A gate's audit asks a different question: not "what do we build" but
"what must be exercised, and what will stop it". The answer is blunt —
**the gate cannot pass today, and it can fail three separate ways before
it reaches the report.**

**The end-to-end path exists and every hop is reachable:**
Sessions → SessionDetail → Record (`VideoCaptureScreen`,
`react-native-vision-camera`) → Keep → `POST /v1/sessions/{id}/videos`
(multipart, shop-tier) → in-process `BackgroundTasks` running
`run_analysis_pipeline` (ffmpeg frame extraction → Claude Sonnet vision)
→ 5-second poll until analysed → Report → `GET /v1/reports/session/{id}`
→ share as PDF **or** mint a Phase 200 link → open `/v1/share/{token}`
in a browser. There is no separate worker process.

**Three blockers, in the order they would bite:**

1. **`ffmpeg` was not installed on this machine.** Every upload would
   have gone straight to `analysis_failed` via `FFmpegMissing`
   (`media/analysis_worker.py:86-95`) — a green upload followed by a
   silently failed analysis. **Resolved during this audit: ffmpeg 9.0.1
   installed.**
2. **F46 — video capture is a known iOS blocker.** Filed 2026-05-16:
   tapping Record on a physical iPhone produces **no camera permission
   prompt at all**, meaning VisionCamera fails to initialise upstream of
   the permission code. `NSCameraUsageDescription` is present, so this
   is not the F40 missing-key family. Deferred then because video was
   not on the 195/196 critical path. It is squarely on this one.
3. **The only known upload fix is uncommitted.** `git stash@{0}`
   (*wip: multipart fix + upload diagnostic (video task)*, 2026-06-22)
   touches `src/api/client.ts`, `src/hooks/useSessionVideos.ts`,
   `Info.plist` and the Xcode project.

**A new finding this audit surfaced, and the leading F46 hypothesis:**
`ios/Podfile:1` forces `RCT_NEW_ARCH_ENABLED=0` (added by Phase 196 as a
BLE fix, `8a1f8ee`) while `ios/MotoDiag/Info.plist:57` sets
`RCTNewArchEnabled=true` — and the app **boots with `fabric: true`**,
confirmed in the device console this session. So the pods were built
against the old architecture while the runtime is Fabric. F46's own
candidate-cause list names exactly this ("New-Architecture-disabled
interaction; VisionCamera 4.x has New Arch requirements"). Changing it
is not free: three phases' device passes (196B, 197, 198) were obtained
under the current setting.

**Device legs that never ran** — the gate should close these, which is
what a gate is for:

| Phase | Outstanding on hardware |
|---|---|
| 199 | analysis-complete push never smoked ("no video handy") |
| 200 | share link never opened *as a customer* |
| 201 | in-app browse/order journey `[~]` partial |
| 202 | device leg did not run at all (tunnel failure) |
| 203 | passed on the **simulator**; physical device only booted |
| 196 | BLE connect/handshake — **needs hardware that does not exist here** (F56) |

**TestFlight readiness — not ready:**
- `aps-environment` is **`development`**; TestFlight requires
  `production`, and the single entitlements file is referenced by BOTH
  Debug and Release, so push would silently fail in TestFlight.
- `DEVELOPMENT_TEAM` is set on Release only; Debug has none.
- Project-level `CODE_SIGN_IDENTITY[sdk=iphoneos*] = "iPhone Developer"`
  in both configs — wrong for distribution.
- **Missing** `ITSAppUsesNonExemptEncryption` (prompts on every upload),
  `NSPhotoLibraryAddUsageDescription`,
  `NSBluetoothPeripheralUsageDescription`, and `UIBackgroundModes`
  (`remote-notification`).
- No Fastlane, no CI, no `ExportOptions.plist`.
- Usage strings that DO exist: Bluetooth-Always, Camera, Location,
  Microphone, PhotoLibrary, SpeechRecognition.

**Android — deliberately out of scope** (user decision). It cannot ship
today regardless: `release { signingConfig signingConfigs.debug }`
(`app/build.gradle:103`) means Play would reject the AAB outright, there
is no `POST_NOTIFICATIONS` permission, the New-Arch flags disagree with
iOS, and the app has **never been launched on Android at all**. Folding
a wholly unproven platform into a gate would make the gate's verdict
meaningless. Filed as its own phase.

**Orphan routes worth noting:** `GET /v1/reports/session/{id}/shares`
and `DELETE /v1/reports/shares/{share_id}` (Phase 200) have no mobile
caller — a minted share link cannot be listed or revoked from the app.

**Backend needs for a real run:** `MOTODIAG_ANTHROPIC_API_KEY`, a
shop-tier API key, the Phase 199 APNs env, `MOTODIAG_PUBLIC_BASE_URL`,
and `motodiag serve --host 0.0.0.0` (the flag is required). Cost is a
real Claude Sonnet vision call over up to 60 frames per video —
budget tens of cents per run.

**User decisions (2026-09-04):** iOS only, Android becomes its own
phase · test the upload before adopting the stale stash · **sweep the
outstanding device claims** as part of the gate · I do all TestFlight
config plus a signed archive, the user uploads.

## Goal

Prove the product actually works end to end on real hardware — film a
bike, get an AI diagnosis, send the owner a link they can open — and
leave an archive that is genuinely submittable to TestFlight. Close the
device-verification debt four phases have accumulated. Track I closes
honestly or not at all.

Run: `pytest` (backend regression), `npm test`, and a scripted device
session with the phone tethered.

Outputs:
- **Blocker triage:** F46 root-caused and fixed, or the gate fails
  loudly with the reason recorded. The New-Arch mismatch is the first
  hypothesis to test, and any change must be re-smoked against 196B /
  197 / 198's transports because those passes were obtained under the
  current setting.
- **Upload verified before the stash is touched.** If it works, the
  stash is obsolete and gets dropped with a note. If it fails, its
  diagnostic is read before deciding whether to adopt or re-derive.
- **The end-to-end run**, recorded step by step with evidence.
- **The sweep:** analysis-complete push (199), share link opened as a
  customer (200), parts browse/order (201), clock in/out (202), theme on
  physical hardware (203).
- **TestFlight config:** a Release-only entitlements file with
  `aps-environment: production`; `DEVELOPMENT_TEAM` on both configs; a
  distribution-appropriate signing identity;
  `ITSAppUsesNonExemptEncryption`, the two missing usage strings and
  `UIBackgroundModes`; `ExportOptions.plist`; then `xcodebuild archive`
  + `-exportArchive` producing a validated `.ipa`.
- **Gate verdict** in the ledger: PASS / PARTIAL / FAIL per step, with
  every failure ticketed rather than smoothed over.

## Logic

Sequenced so the cheapest disqualifier comes first:

1. Backend up with the real env; confirm ffmpeg is on its PATH.
2. Static blocker work (F46 hypothesis, TestFlight config) — no device
   needed, so it happens while the phone is free.
3. Device build + install, then the **capture step first**. If video is
   still broken the gate stops there and that IS the finding.
4. Upload → analysis → report → share, each with server-side evidence.
5. The sweep of outstanding claims.
6. Archive + export; validate; hand the `.ipa` over.

## Key Concepts

- **A gate that cannot fail is not a gate.** The verdict is per step and
  recorded honestly. Three of the last five phases ended with an
  unverified device leg; the value here is converting those into either
  a pass or a ticket.
- **The user is in the loop by necessity.** Filming a bike, tapping
  Record, and uploading to App Store Connect cannot be automated. The
  console is readable over CDP while they drive, so triage is
  collaborative rather than blind.
- **Credentials stay with the user.** No Apple ID, no App Store Connect
  session, no keystore generation.
- **Changing the New-Arch flag is a regression risk, not a free fix.**
  196B, 197 and 198 all passed under the current setting.

## Verification Checklist

- [x] ffmpeg present and the analysis pipeline reaches the vision call
      — installed during the audit, then found BROKEN anyway (see fix #2)
- [x] F46: video capture opens the camera on a physical iPhone.
      Root-caused as a permission deadlock in our own code, NOT a
      VisionCamera failure. Prompt appears and was granted on device.
- [x] Upload tested BEFORE the stash was adopted. It failed, the stash's
      diagnosis was read, and the stash turned out to be WRONG — see
      Deviations. Stash left parked at `stash@{0}`, untouched.
- [x] Analysis completes and findings land on the session — a real
      7.3s device recording, 15 frames, live Claude Sonnet vision call
- [x] Report renders; both share paths work
- [x] The share link opens in a browser with no credentials — minted
      FROM THE PHONE (`10.0.0.89`, 201), sent over Messages, opened in
      Safari, 4 credential-free fetches all 200
- [~] Sweep of outstanding device claims — PARTIAL:
      - [x] **199** analysis-complete push FIRED
            (`push sent to user 1 (Diagnostic analysis ready)`) — the
            item Phase 199 deferred for want of a video. Server-side
            send confirmed; **the banner itself was not watched for**,
            so the visual half stays unverified.
      - [x] **200** share link opened as a customer — done above
      - [ ] **201** parts browse/order screens — NOT RUN (battery)
      - [ ] **202** clock in/out screens — NOT RUN (battery)
      - [ ] **196** BLE connect/handshake — still needs hardware (F56)
- [x] Backend full regression: **4743 passed, 0 failed** (7:40)
- [x] Mobile: 79 suites / 985 tests; tsc clean; eslint 0 errors
- [x] Release entitlements carry `aps-environment: production` —
      verified on the exported `.ipa`, not inferred from config
- [x] `xcodebuild archive` + `-exportArchive` produce a validated
      `.ipa` (13.4 MB, Apple Distribution, Team Store profile)
- [x] Gate verdict recorded per step with tickets for every failure

## Risks

- **The gate may legitimately fail.** F46 has been open since May and
  was never triaged. If video capture cannot be fixed in a reasonable
  window, Track I closes with a documented FAIL on its headline flow —
  which is a more useful outcome than a green tick.
- **Fixing the New-Arch mismatch could regress BLE, OBD or the offline
  layer.** Any change there requires re-smoking 196B/197/198.
- **Real API cost.** Each analysis is a live Sonnet vision call over up
  to 60 frames.
- **The archive cannot be fully validated without an App Store Connect
  record**, which needs the user's credentials. "Exports cleanly and
  passes local validation" is the furthest this phase can go alone.
- **A two-month-old stash over eight phases of change** may conflict on
  the Xcode project file. Testing first is what avoids resolving those
  conflicts for no reason.

## Deviations from Plan

- **The leading F46 hypothesis was wrong, and so was the stash.** The
  plan named an architecture mismatch (`Podfile` forcing
  `RCT_NEW_ARCH_ENABLED=0` against a Fabric runtime) as the likely F46
  cause. The Pods xcconfig carries `-DRCT_NEW_ARCH_ENABLED=1` because RN
  0.85 ignores the opt-out, so pods, Info.plist and runtime are all
  consistently New Architecture. That Podfile line is vestigial. F46 was
  a permission deadlock in our own screen code.
- **The parked stash was tested and rejected on the evidence.** Its
  diagnosis — a stale multipart boundary — was applied, did not fix the
  422, and was then REVERTED when the traceback showed the multipart
  parsed fine and only the field VALUES were rejected. Testing before
  adopting is what kept a wrong fix out of the tree; the stash remains
  parked and untouched.
- **Android descoped** to its own phase (user decision, recorded in the
  plan).
- **Two items of the sweep did not run** — the phone reached 4% battery.
  Recorded as unverified rather than folded into the gate's pass.
- **Share links now point at a LAN address**, because the Tailscale
  HTTPS listener wedged after a NordVPN conflict. Filed as **F64, a
  release blocker**, and cross-referenced into `docs/testflight.md` so
  it is read at release time.

## Results

| Metric | Value |
|--------|-------|
| Gate verdict | **PASS** on the headline flow; PARTIAL on the sweep |
| Bugs found and fixed | 5 (F46, ffmpeg 9, upload 422, silent 422s, my own handler regression) |
| Backend regression | 4743 passed, 0 failed (7:40) |
| Mobile suite | 79 suites / 985 tests; tsc + eslint clean |
| Device evidence | mint 201 from `10.0.0.89`; 4 credential-free 200s; push sent |
| TestFlight artefact | `ios/build/export/MotoDiag.ipa`, 13.4 MB, production entitlement |
| New tickets | F63 (playback freeze), F64 (share-link release blocker) |
| Still blocked on hardware | F56 (BLE adapter) |

**Key finding: every one of the five bugs was found by running the
thing, and none of them would have been found by reading the code.**
Two had been sitting in the tree for months behind green test suites.
F46 was filed in May with a confident, untested diagnosis naming the
wrong subsystem, and that diagnosis is precisely why nobody fixed it —
it made the bug look like someone else's dependency problem rather than
ten lines of our own logic. The upload bug hid behind a `??` that reads
as defensive but only guards null and undefined, never a real zero.
ffmpeg 9 removed a flag and turned every analysis into a silent
`unsupported`. The corrective that actually broke the logjam was not
cleverness but **logging**: the 422 reason existed only in a response
body the client discarded, and adding one WARNING line converted four
blind device round-trips into a single traceback naming the field.
A gate is worth the effort precisely because it runs what the tests
cannot.
