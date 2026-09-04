# Phase 204 — Gate 10: Mobile Integration Test + TestFlight

**Version:** 1.0 | **Tier:** Gate | **Date:** 2026-09-04

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

- [ ] ffmpeg present and the analysis pipeline reaches the vision call
- [ ] F46: video capture opens the camera on a physical iPhone, or the
      failure is root-caused and ticketed with evidence
- [ ] Upload tested BEFORE the stash is adopted; stash disposition
      recorded either way
- [ ] Analysis completes and findings land on the session
- [ ] Report renders; PDF share and link share both work
- [ ] The share link opens in a browser with no credentials
- [ ] Sweep: 199 push, 200 customer view, 201 parts, 202 timer, 203
      theme on hardware
- [ ] Backend regression + mobile suite green
- [ ] Release entitlements carry `aps-environment: production`
- [ ] `xcodebuild archive` + `-exportArchive` produce a validated `.ipa`
- [ ] Gate verdict recorded per step with tickets for every failure

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
