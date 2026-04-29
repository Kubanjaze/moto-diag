# Phase 191 — Video Diagnostic Capture (mobile, capture-only substrate)

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-29 | **Status:** ✅ Complete

## Goal

Give the mechanic a way to record video of a bike running, store it on-device per-session, and play it back from inside `SessionDetailScreen`. **No backend upload, no AI analysis** — those land in Phase 191B (filed at finalize as a new ROADMAP row, not buried in FOLLOWUPS). Phase 191's job is the substrate: the camera native module, the recording state machine, and the file-system policy. Same substrate-then-feature pattern as Phase 187 → Phase 188 (auth substrate, then CRUD over it) and Phase 189 → Phase 190 (session substrate, then DTC integration).

The original ROADMAP wording for Phase 191 was "film bike running, auto-extract audio + key frames → AI analysis" — full scope is honestly 3-4 phases compressed into one. Splitting into 191 (capture) + 191B (upload + AI pipeline) keeps each phase gate-sized.

Per Kerwyn's pre-plan ask: this scope split must be visible on the ROADMAP at finalize, not just filed in FOLLOWUPS.

CLI — none (mobile has no CLI).

## Risk profile

**This phase is closer to Phase 186 than Phase 188.** Phase 186 was the last time the project did a heavy native-module integration (`react-native-ble-plx` 3.5.0 with the `isNewArchitectureEnabled()` CMake bug — ~30 minutes to diagnose, formalized as `patch-package` in Phase 187). `react-native-vision-camera` is the same risk class:

- Native dep with native code (CameraX on Android, AVFoundation on iOS)
- Multiple permissions (Camera, Microphone; Android 13+ split media perms add more)
- New Architecture interactions (we're New-Arch-OFF per ADR-002 — same gradle gotcha shape)
- Hardware variance: emulator camera ≠ physical phone camera; Pixel 7 API 35 emulator should suffice for smoke but mid-phase fix-cycles for hardware quirks are realistic

Mitigation: Commit 1 is the native install + cold gradle + permission-prompt smoke screen ALONE. No JS feature work bundled. If gradle fails, we patch (likely the same `isNewArchitectureEnabled()` shape) without invalidating any feature code. This is a **micro-gate** between Commit 1 and Commit 2 — Kerwyn does a hardware smoke on Pixel 7 emulator before any state-machine or screen code lands.

Phase 188 (8-commit fix-cycle on transport bugs) and Phase 190 (7-commit fix-cycle on mock-fidelity bugs) are NOT the right comparisons. Patch-package land is what Phase 186 looked like.

## Outputs

**New runtime deps (1 + native):**
- `react-native-vision-camera@^4.x` — the heavy one. Pulls CameraX gradle deps on Android + AVFoundation linkage on iOS. Patch-package likely needed (same `isNewArchitectureEnabled()` gradle bug class as ble-plx + keychain). Codec: H.264 in MP4 container — industry-standard, hardware-accelerated on essentially every Android phone shipped since ~2014; H.265 rejected (battery + heat issues, iOS-Photo-only-legacy mess, no compelling efficiency win for short diagnostic clips).
- `react-native-fs@^2.x` — file-system access with stable Android paths (`DocumentDirectoryPath`, `ExternalDirectoryPath`). Pure-JS layered on a small native module; low patch-package risk.
- `react-native-video@^6.x` for playback — Phase 191's playback surface. Has its own native dependencies (ExoPlayer on Android); flagged as second native-module risk surface.

**New files (~10):**
- `src/screens/VideoCaptureScreen.tsx` — full capture surface (Camera component, record/stop button, recording-time indicator, state-machine driven).
- `src/screens/VideoPlaybackScreen.tsx` — playback surface for a single video file (`react-native-video`); shows duration / resolution / file size / "interrupted" indicator if applicable.
- `src/screens/videoCaptureMachine.ts` — pure-helper module exporting the `RecordingState` discriminated union + `recordingTransition(state, event)` reducer. Same separation pattern as `dtcSearchHelpers.ts` (Phase 190) / `sessionFormHelpers.ts` (Phase 189) — testable without rendering Camera.
- `src/hooks/useSessionVideos.ts` — `{videos, addRecording, deleteVideo, refresh, atCap, capReason}` backend-agnostic hook (Phase 191: filesystem-backed; Phase 191B will swap implementation to call `POST /v1/videos`, consumers see same shape — explicit handoff contract documented below).
- `src/hooks/useCameraPermissions.ts` — Camera + Microphone permission flow + Android 13+ split-perms handling.
- `src/types/video.ts` — `SessionVideo` metadata type, `VideoFormat` literal, `RecordingError` union.
- `src/services/videoStorage.ts` — file-system policy implementation (paths, caps, orphan cleanup). Pure logic + RNFS calls; testable with `react-native-fs` mocked.
- `src/navigation/types.ts` (modified) — extend `SessionsStackParamList` with `VideoCapture: {sessionId: number}` + `VideoPlayback: {videoId: string; sessionId: number}`.
- `src/navigation/SessionsStack.tsx` (modified) — register the two new screens.
- `src/screens/SessionDetailScreen.tsx` (modified) — new **VideosCard** between FAULT CODES and DIAGNOSIS (per Kerwyn's pre-plan call: evidence precedes diagnosis); thumbnail-list + record button + closed-session lockdown.

**Modified files (3):**
- `package.json` + `package-lock.json` — add the three new deps; bump `version` 0.0.5 → 0.0.6.
- `android/app/src/main/AndroidManifest.xml` — add camera + microphone + Android 13+ split-media permissions.
- `README.md` + `implementation.md` — refreshed at Commit 6.

**New tests (3 files, ~22-28 tests):**
- `__tests__/screens/videoCaptureMachine.test.ts` — pure state-machine reducer tests: every transition + edge cases (record-while-recording = no-op; stop-while-idle = no-op; interrupted-from-idle = no-op).
- `__tests__/services/videoStorage.test.ts` — file-system-policy tests with RNFS mocked: filename construction, per-session cap detection (5 videos AND 500MB whichever first), disk-full handling, orphan cleanup on session delete.
- `__tests__/hooks/useSessionVideos.test.ts` — hook contract tests: list/add/delete/refresh + cap states.

**No backend changes.** No schema changes (still v38). No new ADR (the camera substrate is significant but the framework choice is a no-brainer; the Android 13+ split-perms decision documented inline in the relevant code).

**Package version:** `0.0.5 → 0.0.6`.
**Project implementation.md version:** `0.0.7 → 0.0.8` on phase close.

## Logic

### Recording state machine — sketch posted for sign-off pre-Commit 2

Five states + 1 transient. Per Kerwyn's pre-plan ask, the state machine sketch lands in this v1.0 plan AND is posted separately for explicit sign-off after Commit 1's micro-gate, before Commit 2 ships any state-machine code. Same discipline as Phase 189's severity Other... sketch sign-off (which is the single biggest reason Phase 189 round 1 passed clean).

**States:**

| State | What's true | Visible UI |
|-------|-------------|------------|
| `idle` | Camera ready, no recording active | Record button (large red circle) |
| `recording` | Recording in progress; timer running | Stop button + elapsed-time counter + red dot |
| `stopping` | User tapped stop OR interruption fired; finalizing the file | Brief spinner ("Saving…"); typically 100-500ms |
| `saved` | File written to disk + metadata captured | Preview thumbnail + "Use this" / "Discard" |
| `failed` | Permission denied / disk full / hardware error / file-write failed | Error banner + Retry / Cancel |
| `interrupted` | (transient) Phone-call OR app-background while recording | Same UI as `stopping`; may transition to `saved` (partial file salvaged) or `failed` (file unsalvageable) |

**Transitions:**

```
idle      ──tap-record──▶  recording
idle      ──interrupted──▶  idle           (no-op; recording wasn't active)
recording ──tap-stop──▶    stopping
recording ──interrupted──▶ stopping        (vision-camera fires onError or onInterrupted; we
                                            unconditionally call .stopRecording() and let the
                                            file-finalize path handle salvage)
recording ──hw-error──▶    failed
stopping  ──file-saved──▶  saved
stopping  ──salvage-ok──▶  saved           (interrupted-but-partial-file-recovered)
stopping  ──salvage-fail──▶failed
saved     ──tap-discard──▶ idle            (file deleted from FS)
saved     ──tap-keep──▶    idle            (returns to capture screen with the new video persisted)
failed    ──tap-retry──▶   idle
failed    ──tap-cancel──▶  idle
```

**Phone-call interruption (concrete behavior):** vision-camera fires `onError` or session-suspended events when an audio-priority interruption hits (incoming call, Siri/Bixby invocation, AirPods connection events on iOS). Our handler unconditionally calls `Camera.ref.current?.stopRecording()`. vision-camera typically writes the partial file up to the interruption point + closes the MP4 container cleanly — making the partial salvageable as a shorter-than-expected video. Metadata flag `interrupted: true` is set on the resulting `SessionVideo`. If the container is unsalvageable (rare; usually only on hardware encoder failure), we transition to `failed` and surface "Recording interrupted; file could not be saved" copy.

**App-background mid-record:** Same handling. Android stops the camera session when the app backgrounds; vision-camera fires the equivalent of `onError`. We trigger the same stopRecording → salvage path. iOS sometimes allows a brief background grace period (depending on Background Modes config) but Phase 191 doesn't enable that; treat background-while-recording as interruption.

**Foreground re-entry to recording state:** does NOT auto-resume. State machine never has a transition INTO `recording` from anywhere except `idle ──tap-record──▶ recording`. User has to manually start a new recording.

### File system policy

**Directory layout (RNFS DocumentDirectoryPath):**

```
{DocumentDirectoryPath}/
└── videos/
    ├── session-1/
    │   ├── session-1-2026-04-28T14-22-37Z-abc12345.mp4
    │   ├── session-1-2026-04-28T14-22-37Z-abc12345.json   (sidecar metadata)
    │   ├── session-1-2026-04-28T14-25-02Z-def67890.mp4
    │   └── session-1-2026-04-28T14-25-02Z-def67890.json
    └── session-3/
        └── session-3-2026-04-28T14-29-13Z-ghi34567.mp4 + .json
```

**Filename convention (Phase 191B handoff-friendly):**
`session-{sessionId}-{ISO8601-compact}-{8charuuid}.mp4`

- `sessionId`: integer
- `ISO8601-compact`: `YYYY-MM-DDTHH-mm-ssZ` (colons replaced with hyphens because some Android filesystems reject `:`)
- `8charuuid`: first 8 chars of crypto.randomUUID() — collision-safe within a session even on rapid-fire recording

**Sidecar metadata:** each video file has a `.json` sidecar with the captured `SessionVideo` shape (see Phase 191B handoff section). Stored alongside so the directory is self-describing — Phase 191B's upload path can multipart both. JSON sidecar avoids needing a SQLite cache for video metadata in Phase 191; the filesystem IS the database.

**Per-session cap (HARD, both criteria — whichever fires first):**

- **Count cap: 5 videos per session.** Backed-of-envelope: a 30-second-to-2-minute clip per cylinder issue, mechanic typically captures 1-3 angles, 5 is generous slack.
- **Size cap: 500 MB per session.** 720p H.264 ≈ 8-12 MB/min; 5 × 2-min ≈ 100MB; 500MB cap accommodates 4K outliers without going wild.

When user taps Record and either cap is at-or-over:
- Capture screen shows "At cap (5/5 videos OR 478/500 MB used)" inline error
- Record button disabled
- Inline copy: "Delete an existing video to record more" with link to the videos card

**Disk-full handling:** RNFS exposes `FreeSpace()`-equivalent. Check `getFreeDiskStorage()` before recording starts. If <100MB free, refuse to start recording with copy "Not enough storage to record. Free up space and retry." If recording succeeds but write-finalize hits ENOSPC (rare race), transition to `failed`; partial file is unsalvageable.

**Orphan cleanup on session delete:** Phase 188 added `DELETE /v1/vehicles/{id}` which cascades vehicle data; Phase 178 sessions don't have a delete endpoint yet (sessions only close/reopen). When session-delete arrives later (Phase 192? Phase 198?), the cleanup is `RNFS.unlink({DocumentDirectoryPath}/videos/session-{id}/)`. For Phase 191 we ship a `cleanupOrphanedVideos()` helper called on `useSessionVideos` first mount that walks `videos/` and removes any `session-{id}/` directories where the corresponding session no longer exists (server-side check via `useSessions()` data). Belt-and-suspender: Phase 198 offline cache will do its own GC.

### SessionDetailScreen integration position

Per Kerwyn's pre-plan ask: **between FAULT CODES and DIAGNOSIS** (evidence precedes diagnosis). Updated card order:

```
SessionDetailScreen (Phase 191 layout)
├── Title + status badge
├── Vehicle card
├── Symptoms card        ← Phase 189
├── Fault codes card     ← Phase 189 (+ Phase 190 tap → DTCDetail)
├── Videos card          ← NEW Phase 191
├── Diagnosis card       ← Phase 189
├── Notes card           ← Phase 189
└── Lifecycle card       ← Phase 189
```

**Videos card** layout:
- Title: "Videos"
- If 0 videos: empty-state copy ("No video evidence yet") + Record button
- If 1+ videos: thumbnail list (or, since we're deferring thumbnail extraction to Phase 191B / 192, a generic video icon + duration string + "Recorded YYYY-MM-DD HH:mm" + interrupted flag if applicable) + Record button at the bottom
- Record button respects `at-cap` state (disabled with copy)
- Tap a video row → push `VideoPlayback` within SessionsStack with `{videoId, sessionId}`
- Tap Record button → push `VideoCapture` within SessionsStack with `{sessionId}`

### Closed-session rule for videos

Per Kerwyn's pre-plan ask: **no recording on closed sessions.** When `session.status === 'closed'`:

- Videos card still shows the existing video list (read-only — playback works)
- Record button is **hidden** (not just disabled with grey-out; visually absent so the surface is clearly read-only)
- Empty state copy adjusts: "No video evidence captured. Reopen this session to record."
- Tap on existing video rows → playback works as expected

**Symmetric gap flagged for Phase 191 polish (F7):** Phase 189's append inputs for symptoms / fault-codes / notes are visible on closed sessions — same conceptual gap. Phase 191 fixes it for videos; the polish backlog item is to retroactively apply the closed-session lockdown to the Phase 189 append inputs too. Filed at finalize.

### Camera permissions — Android 13+ split-perms callout

Pre-Android 13: single `READ_EXTERNAL_STORAGE` covers all media reads.
Android 13+ (API 33+): split into `READ_MEDIA_IMAGES` / `READ_MEDIA_VIDEO` / `READ_MEDIA_AUDIO`.
Android 14 (API 34+): adds `READ_MEDIA_VISUAL_USER_SELECTED` for photo-picker-flow-only access.

For Phase 191 we need:

| Permission | Android API | Why we need it |
|------------|-------------|----------------|
| `CAMERA` | all | record video |
| `RECORD_AUDIO` | all | bike audio is the most important diagnostic signal |
| `READ_MEDIA_VIDEO` | 33+ | (only if we share to Photos / external app — Phase 192 territory; Phase 191 stores in app-private dir only, so NOT REQUIRED) |
| `WRITE_EXTERNAL_STORAGE` | <29 | (Phase 191 stays in `DocumentDirectoryPath` which is app-private — NOT REQUIRED) |

**Decision: Phase 191 only requests `CAMERA` + `RECORD_AUDIO`.** Files stay in app-private storage (`DocumentDirectoryPath`); no external-storage access needed. This keeps the permission flow minimal — just the two prompts on first launch of the capture screen.

Phase 192 (diagnostic report viewer / share sheet) will need to add `READ_MEDIA_*` for sharing; Phase 191 explicitly defers.

`useCameraPermissions` hook handles the request flow:

```ts
const {camera, microphone, status, request} = useCameraPermissions();
// status: 'unknown' | 'granted' | 'denied' | 'permanently-denied'
// request: () => Promise<void> — calls Camera.requestCameraPermission() +
//                                Camera.requestMicrophonePermission() in sequence
```

Permanently-denied path: vision-camera distinguishes `'denied'` (re-promptable) from `'permanently-denied'` (user dismissed with "Don't ask again" — must go to system settings). In that case, render a blocked-state UI on `VideoCaptureScreen` with a "Open settings" button using `Linking.openSettings()`.

### Phase 191B handoff shape

`useSessionVideos` is **backend-agnostic**. Phase 191 implementation hits the filesystem; Phase 191B swaps the implementation to call backend HTTP endpoints. Consumers (`SessionDetailScreen`'s VideosCard, `VideoCaptureScreen` save flow) see the same hook contract:

```ts
interface UseSessionVideosResult {
  videos: SessionVideo[];
  addRecording: (file: NewRecording) => Promise<SessionVideo>;
  deleteVideo: (videoId: string) => Promise<void>;
  refresh: () => Promise<void>;
  atCap: boolean;
  capReason: 'count' | 'size' | null;
  isLoading: boolean;
  error: string | null;
}
```

`SessionVideo` type (the Phase 191 / 191B contract):

```ts
type SessionVideo = {
  /** Stable UUID for this video (Phase 191: 8-char generated at record-time;
   *  Phase 191B: backend-issued UUID after upload). */
  id: string;
  /** Session this video is attached to. */
  sessionId: number;
  /** Phase 191: local file URI (`file://...`).
   *  Phase 191B: still file URI for local-cache copy; backend has its own remote URL
   *              accessed via a separate `remoteUrl: string | null` field. */
  fileUri: string;
  /** Phase 191B addition (null in Phase 191): backend remote URL after upload. */
  remoteUrl: string | null;
  /** ISO 8601 timestamp when recording started. */
  startedAt: string;
  /** Recording duration in milliseconds. */
  durationMs: number;
  /** Pixel dimensions captured. */
  width: number;
  height: number;
  /** File size in bytes. */
  fileSizeBytes: number;
  /** Container format. Phase 191 always 'mp4'. */
  format: 'mp4';
  /** Codec. Phase 191 always 'h264'. */
  codec: 'h264';
  /** True if recording was stopped by phone-call / app-background / hardware
   *  interruption rather than user action. The file may still be playable but
   *  truncated. UI surfaces this with a small indicator on the video row. */
  interrupted: boolean;
  /** Phase 191B addition (null in Phase 191): upload state machine. */
  uploadState: 'pending' | 'uploading' | 'uploaded' | 'upload-failed' | null;
  /** Phase 191B addition (null in Phase 191): AI analysis state machine. */
  analysisState: 'pending' | 'analyzing' | 'analyzed' | 'analysis-failed' | null;
};

type NewRecording = {
  sessionId: number;
  fileUri: string;
  startedAt: string;
  durationMs: number;
  width: number;
  height: number;
  fileSizeBytes: number;
  format: 'mp4';
  codec: 'h264';
  interrupted: boolean;
};
```

In Phase 191, the four `*State` and `remoteUrl` fields are always `null`. Phase 191B's swap populates them. The hook's `videos` type is identical in both phases — consumers don't change.

### Test plan for Phase 191B handoff

The `videoCaptureMachine` reducer + `videoStorage` service + `useSessionVideos` hook all get unit tests in Phase 191. Phase 191B will add upload-state-machine tests + integration tests against real `POST /v1/videos`. The Phase 191 hook implementation is swappable; the Phase 191B implementation passes the same Phase 191 tests + adds new ones.

## Key Concepts

- **`react-native-vision-camera` v4** — `<Camera>` component with imperative `ref.startRecording({onRecordingFinished, onRecordingError, ...})` + `ref.stopRecording()`. Permissions via `Camera.requestCameraPermission()` + `Camera.requestMicrophonePermission()`. Codec defaults to H.264 in MP4. Format selection via `format` prop with `Camera.getAvailableVideoCodecs()`.
- **`react-native-fs` (RNFS)** — `DocumentDirectoryPath` is app-private (no permissions needed); `mkdir`, `writeFile`, `unlink`, `readDir`, `getFreeDiskStorage`, `stat` cover everything Phase 191 needs.
- **`react-native-video`** — `<Video source={{uri: ...}}>` for playback. Has built-in player UI controls or accepts a custom controls layer. Phase 191 ships with the built-in for simplicity; custom controls fall to Phase 192 when share/AirDrop integration lands.
- **Discriminated-union state machine reducer** — `RecordingState` union + `recordingTransition(state, event): RecordingState` — same shape as the typed-error refactor in Phase 190 commit 7. Reducer is pure and testable without the Camera component.
- **Crypto-safe UUID generation** — RN's `crypto.randomUUID()` requires React Native 0.74+ which we're on. First 8 chars of UUIDv4 are sufficient for per-session uniqueness.
- **Android private storage** — `DocumentDirectoryPath` maps to `/data/data/com.bandithero.motodiag/files/` on Android. App-uninstall wipes it. `MANAGE_EXTERNAL_STORAGE` and `WRITE_EXTERNAL_STORAGE` are NOT needed.
- **Vision-camera new-arch off** — same shape as ble-plx + keychain. patch-package likely needed; same `isNewArchitectureEnabled()` CMake bug class. Confirmed pre-build.

## Verification Checklist

- [x] `npm test` → 210 baseline + 95 new tests passing. **Actual: 301 / 301 green** (overshot the 232-238 target by ~63 tests because the substrate broke into more pure-helper modules than planned — videoCaptureMachine reducer + videoStorage path/cap/cleanup + videoCaptureHelpers formatElapsed/formatFileSize/generateShortId/classifyVisionCameraError + dtcErrors regression guards each accreted their own test files).
- [x] `npx tsc --noEmit` clean every commit including Commit 1's smoke screen.
- [x] **Commit 1 micro-gate (PASSED, 2026-04-28)**: `cd android && ./gradlew clean && cd .. && npm run android` — clean build with vision-camera + react-native-fs + react-native-video linked. Permission-prompt smoke screen on HomeScreen rendered; Camera + Microphone prompts fired correctly on tap; granted state persisted across cold relaunch. **Zero patch-package work needed** — vision-camera 4.7.3 + rn-video 6.19.2 + rn-fs 2.20.0 all built clean against `newArchEnabled=false` on first try, contradicting the v1.0 plan's "Phase 186 redux" risk projection.
- [x] Permission flow: first launch of VideoCaptureScreen shows Camera + Microphone prompts in sequence. Granted state persists across app relaunches. Verified at micro-gate AND at full architect-gate cold-relaunch step.
- [x] Permanently-denied state: blocked-UI with "Open Settings" button — implemented via `Linking.openSettings()`. Not exercised at gate (architect didn't tap "Don't ask again"); design-review verified.
- [x] Recording state machine: idle → record → recording (timer counts up) → stop → stopping → saved (preview shown). Verified Commit 3 architect-smoke + full gate.
- [x] State machine transitions tested in unit tests across all 6 states (videoCaptureMachine.test.ts — every transition + invalid-state guards + auto-keep-on-background per Kerwyn fold).
- [x] Record button shows elapsed time during recording (mm:ss format via `formatElapsed`).
- [x] Phone-call interruption / app-background mid-record: APP_BACKGROUNDED handler unconditionally calls `cameraRef.current?.stopRecording()` then dispatches the reducer event. Salvaged partial file persists with `interrupted: true` on metadata. **Verified at full gate Step 12** (Pixel 7 API 35 emulator: Home-button-mid-record → "⏸ Paused at 2:20" badge on the saved-preview tile + on the VideosCard row + on VideoPlaybackScreen meta band). Commit 3 fix-cycle resolved the closure-state-capture bug that had this UI rendering green-not-orange in the first build pass.
- [x] App-background interruption tested separately from phone-call (same code path; Pixel 7 emulator doesn't easily simulate true phone calls without dialer scripting, but the AppState mechanism is identical).
- [x] File written to `{DocumentDirectoryPath}/videos/session-{N}/session-{N}-{ISO8601-compact}-{8charuuid}.mp4` with `.json` sidecar containing the `SessionVideo` shape. Verified at gate via adb pull.
- [x] Per-session count cap: 6th recording attempt at 5 existing videos → at-cap pane visible, Record button hidden (UI-layer guard per Item-4 sketch sign-off — the reducer never sees TAP_RECORD when at-cap).
- [x] Per-session size cap: at-cap pane fires when bytes-used ≥ 500MB. Validated via videoStorage.test.ts cap-evaluation tests; emulator gate exercised the count cap path (size cap would require a full 30+ minutes of recording to reach 500MB, deferred to physical-device validation).
- [x] Disk-full handling: `getFreeDiskStorage` precheck at recording-start refuses with "Not enough storage" when <100MB free. Mock-tested in videoStorage.test.ts.
- [x] Closed session: VideosCard on a closed session shows existing videos (read-only) with NO Record button visible. **Bug 2 fix (commit 7, `39948c1`)** added closed-session × has-videos explanatory pane ("Session closed · Reopen this session to record more.") so the surface communicates the lockdown instead of going visually blank.
- [x] Reopen session: Record button reappears. Verified at gate Step 14/15.
- [x] VideosCard sits between FAULT CODES and DIAGNOSIS in SessionDetailScreen (Kerwyn pre-plan placement: evidence precedes diagnosis).
- [x] Tap video row → VideoPlaybackScreen opens within SessionsStack; built-in `react-native-video` v6 controls work (play / pause / scrub).
- [x] Back-button from VideoPlayback returns to SessionDetail. **Bug 1 fix (commit 7, `39948c1`)** added `useFocusEffect(refresh)` inside VideosCard so returns from VideoCapture (post-save) and VideoPlayback (post-delete) re-list videos correctly — SessionDetail doesn't unmount on push and the hook's mount-time effect alone wouldn't re-fire.
- [x] Cold relaunch: recorded videos persist; metadata reloads from `.json` sidecars; playback works.
- [x] No regression: Phase 186 BLE / Phase 187 auth / Phase 188 Garage / Phase 189 Sessions / Phase 190 DTC. Full gate sanity sweep covered Garage list, Sessions list, DTC P0171 happy path, and the 2:20 PM Paused-badge artifact on Session #1 (preserved as a 191B regression-coverage fixture per Kerwyn's instruction).

### Bug verification (architect full gate, fix-cycle commit `39948c1`)

- [x] **Bug 1 (HIGH) — VideosCard refresh on focus**: VideoCapture-save → back → VideosCard now lists the freshly-saved recording without cold restart. Same on VideoPlayback-delete return. Verified at re-smoke.
- [x] **Bug 2 (LOW) — closed-session × has-videos copy**: closed sessions with ≥1 saved video now show a cream-pane "Session closed · Reopen this session to record more." block in the Record-button slot.
- [x] **Bug 3 (MEDIUM) — bottom-tab wireframe icons**: `tabBarIcon: () => null` on `RootNavigator` `screenOptions` suppresses `@react-navigation/elements` default `MissingIcon` (`⏷` glyph rendered when no `tabBarIcon` is provided). Restores the text-label-only look from Phase 189's design intent. **Not a Phase 191 regression** — has been there since Phase 189 commit 2 added the bottom-tab nav; full gate just surfaced it for the first time.
- [x] **Architect-gate full re-smoke (2026-04-29)**: 8 / 8 verifications green across all three bugs (save-return refresh, delete-return refresh, closed-session lockdown copy, wireframe-nav fix) + full sanity sweep (Garage, Sessions, DTC P0171 happy path, 2:20 PM Paused-badge artifact preserved on Session #1).

## Deviations from Plan

1. **Patch-package risk did NOT materialize.** The v1.0 plan framed Phase 191 as "closer to Phase 186 than Phase 188" — heavy native-module integration with the `isNewArchitectureEnabled()` CMake bug shape predicted as the most likely friction. **Reality: zero patch-package work needed.** vision-camera 4.7.3 + rn-fs 2.20.0 + rn-video 6.19.2 all built clean against `newArchEnabled=false` on first cold-gradle pass. The micro-gate after Commit 1 took ~5 minutes and was green on first attempt. Risk projections for upcoming Track I phases should weight "we already have patches/ scaffolding" as a sunk cost that absorbs the most-likely shape of native-module integration friction.

2. **Test count overshot target.** Planned 22-28 new tests; landed +95 (210 → 301). The reducer / storage / helpers split into more pure-helper modules than the plan anticipated, each accreting its own test file (videoCaptureMachine + videoStorage + videoCaptureHelpers + dtcErrors regression guards from Phase 190 carried forward).

3. **One in-cycle Commit 3 fix-cycle (closure-state-capture).** The first Commit 3 build passed locally but failed at architect-smoke Verification 5: orange "Paused at 0:XX" badge wasn't rendering on the saved-preview after AppState background-during-recording. Root cause was a closure-capture twist: the `onRecordingFinished` callback registered with `cameraRef.startRecording` captured `state` at moment-of-tap-record (`state=idle`), so `wasInterrupted = state.kind === 'stopping' && state.reason === 'interrupted'` always evaluated false. Fix: explicit `interruptedRef` ref with set-true-in-AppState-handler, set-false-in-user-stop, read in onRecordingFinished. Folded into the same Commit 3 (`ffa383c`) alongside F8 (formatFileSize unit-switching).

4. **One in-cycle full-gate fix-cycle (3 bugs).** Architect's full gate after Commit 6 found 3 bugs (Bug 1 VideosCard refresh on focus / Bug 2 closed-session × has-videos copy / Bug 3 wireframe nav icons). All three landed in a single fix commit (`39948c1`) with explicit per-bug callouts in the message body. Re-smoke green on all 8 verifications.

5. **Bug 3 was a long-standing default, not a Phase 191 regression.** `@react-navigation/elements`'s default `MissingIcon` (a `⏷` Unicode glyph) has rendered in the bottom-tab nav since Phase 189 commit 2 added bottom-tabs. Phase 189's design intent was text-label-only ("no icon library yet — defer until a design pass earns it"); the bug was that `tabBarIcon` was never explicitly set to suppress the default. Phase 191's full gate is the first one to scrutinize the visuals at that level. Investigation confirmed before the fix landed; commit message explicitly notes the not-a-regression framing.

6. **Phase 191B added as a NEW ROADMAP row at finalize, not buried in FOLLOWUPS.** Per Kerwyn's pre-plan ask. Concrete row added immediately after Phase 191 in `docs/ROADMAP.md` Track I table; status 🔲; scope: backend `/v1/videos/*` endpoints (upload + frame extraction + Claude Vision analysis) + migration for `videos` table + `useSessionVideos` hook swap from FS-backed to backend-backed (consumer surface unchanged per Phase 191's handoff contract) + ffmpeg integration for frame + audio extraction. Track I count grows 20 → 21 phases; Phases 192-204 row numbers stay the same — 191B is a NEW row, not a renumbering.

7. **Phase 191 polish backlog**: F2 (per-entry edit/delete on open sessions, carry-over from Phase 189), F3 (lifecycle audit history, carry-over from Phase 189), F4 (make/family chip on DTCSearch result rows, carry-over from Phase 190), F5 ("Code not in catalog yet" empty-state copy, carry-over from Phase 190), F6 (`useDTC` memoization to suppress React 18 StrictMode dev-only double-fetch, carry-over from Phase 190), F7 (NEW — symmetric closed-session lockdown for Phase 189's symptoms / fault-codes / notes append inputs; Phase 191 closed the gap for videos but left it open for the other lists), F9 (NEW — document the `useRef`-not-state pattern for callbacks registered with native modules; surfaced from Commit 3 closure-state-capture bug + the meta-observation that this is now the third instance of a "snapshot/assumption doesn't match runtime" failure family across Track I — Phase 188 HVE shape mock, Phase 190 substring-match-on-error-text, Phase 191 closure-state capture). **F8 shipped in Commit 3** (`ffa383c`) — formatFileSize auto-unit-switching B / KB / MB / GB with one-decimal precision below 10MB; not retained in the open list.

8. **README.md + project structure tree updated in Commit 6** (`78834e4`) with all new packages: services/videoStorage.ts, screens/videoCaptureMachine.ts + videoCaptureHelpers.ts, hooks/useCameraPermissions + useSessionVideos, types/video.ts, screens/VideoCaptureScreen + VideoPlaybackScreen. Also documents the 301-test count + the two transport-regression guards from Phase 188-189 still pinning Content-Type + X-API-Key.

## Results

| Metric | Value |
|--------|-------|
| Mobile branch | `phase-191-video-diagnostic-capture` (8 commits, rebase-merged to mobile `main` at finalize) |
| Build commits | 6 (`d7117c5` install / `35226bc` reducer+storage / `bbf5d90` capture screen / `1ac4c26` hook+playback / `b9f1b0f` SessionDetail integration / `78834e4` README+v0.0.6) |
| Mid-cycle fix commits | 1 in Commit 3 (`ffa383c` interruptedRef closure-capture + F8 formatFileSize) |
| Full-gate fix commits | 1 (`39948c1` Bug 1 VideosCard refresh + Bug 2 closed-with-videos copy + Bug 3 suppress MissingIcon) |
| Mobile Jest tests | **301 / 301 green** (210 baseline + 95 new — videoCaptureMachine reducer + videoStorage path/cap/cleanup + videoCaptureHelpers formatElapsed/formatFileSize/generateShortId/classifyVisionCameraError + useSessionVideos hook contract + 191B handoff regression guard + useCameraPermissions) |
| `npx tsc --noEmit` | clean every commit |
| Backend changes | **zero** (pure mobile phase; schema unchanged at v38) |
| Architect gate | round 1 (full) FAILED with 3 bugs → round 2 GREEN on 8 / 8 re-smoke verifications + full sanity sweep |
| Mobile package version | 0.0.5 → 0.0.6 (bumped in Commit 6) |
| Mobile project `implementation.md` | 0.0.7 → 0.0.8 |
| Backend project `implementation.md` | 0.13.6 → 0.13.7 |
| Track I scorecard | 7 / 21 phases complete (Phase 191B added as new row at finalize → Track I count grows 20 → 21) |

**Key finding: substrate-then-feature splits keep gates gate-sized.** The original Phase 191 ROADMAP scope ("film bike running, auto-extract audio + key frames → AI analysis") was honestly 3-4 phases compressed into one. Splitting into 191 (mobile capture-only substrate) + 191B (backend upload + Claude Vision pipeline) preserved the substrate-then-feature pattern that already worked for Phase 187 → 188 (auth substrate, then CRUD over it) and Phase 189 → 190 (session substrate, then DTC integration). Two takeaways for the rest of Track I: (1) when a planned phase has more than one new concern that would need its own architect gate (here: native-module install + state machine + file-system policy + backend upload + AI pipeline = 5 concerns), split it explicitly at plan time and surface the split as a NEW ROADMAP row, not a FOLLOWUPS entry; (2) the closure-state-capture bug from Commit 3 + the architect-gate Bug 1 (refresh on focus) are the third and fourth instances of the "snapshot/assumption doesn't match runtime" failure family that started with Phase 188 (HVE mock shape) and Phase 190 (substring-match on error text). The pattern is robust enough now that F9 (the useRef-not-state polish item) plus a generalized lint rule are worth filing for Phase 192+ pickup.

## Risks

- **vision-camera gradle patch-package risk (Phase 186 redux).** Same `isNewArchitectureEnabled()` CMake bug shape that hit ble-plx 3.5.0 + keychain 10.0.0. Mitigation: Commit 1 ALONE = install + cold gradle + permission smoke; if the build fails, the patch is the only fix needed before Commit 2 ships any feature code. Existing `patches/` directory + postinstall hook is the right slot.
- **react-native-video gradle risk.** Second native module integration in this phase (separate from vision-camera). Lower risk profile (mature library, ExoPlayer is rock-solid) but can't rule out a similar gradle gotcha. If it surfaces, same patch-package pattern applies.
- **Android 13+ split media-perms confusion.** Even though Phase 191 deliberately stays in app-private `DocumentDirectoryPath` (no media perms needed), some vision-camera versions auto-add `READ_MEDIA_*` to the manifest at install time. Audit `AndroidManifest.xml` post-install; remove anything we don't need. Reasoning: every permission in the manifest shows up at install on the Play Store; minimal-perms posture is best for trust + future review.
- **Hardware variance: emulator camera vs physical device.** Pixel 7 API 35 emulator has a virtual camera that records solid-color frames at 60fps with software encoding. Real-world bike-vibration + low-light + outdoor-glare edge cases won't surface on emulator. Phase 191 architect-gate covers emulator only; physical-device validation pushed to Phase 192 architect-gate or earlier if Kerwyn has a real Pixel handy.
- **State machine race conditions.** User taps record + stop within 100ms — the `stopping` state must guard against double-stop. State machine reducer rejects invalid transitions explicitly (no-op + dev warning). Tests cover this.
- **Phone-call salvage variability.** vision-camera's behavior on interruption is "best effort" — typically the partial MP4 is well-formed but on some Android devices (Samsung 7-9 era) the file gets truncated mid-frame and won't play. Mitigation: `interrupted: true` flag visible on the row; if playback fails on tap, surface "This recording was interrupted and the file may be incomplete" copy with Delete-only action.
- **Disk-full mid-recording.** `getFreeDiskStorage` check before start covers the common case. If write-finalize hits ENOSPC, transition to `failed` and `unlink` any partial file. Mitigation: predictive size estimate (running bitrate × elapsed time) + early-stop if projected size would exceed remaining space.
- **JSON sidecar drift from .mp4.** If a `.mp4` exists without its `.json` (e.g., process killed mid-write) OR vice versa, treat as orphan — `useSessionVideos` walks the directory and surfaces well-formed pairs only. Stale sidecars get GC'd on next refresh.
- **Per-session cap math edge cases.** What if user has 4 videos at 480MB total + tries to record one more? Count cap NOT hit (5th allowed by count); size cap is at 96% — predictive estimator says next 30s = ~12MB which would push to 492MB, still under 500MB cap. Allow it. Then user tries another — count cap NOW would block (5 → 6 not allowed) regardless of size. Tested explicitly.

## Not in scope (firm)

- **Backend video upload** (`POST /v1/videos` etc.). → **Phase 191B** (filed in ROADMAP at finalize, not just in FOLLOWUPS).
- **AI analysis pipeline** (extract frames + audio + Claude Vision call + structured findings). → **Phase 191B**.
- **Thumbnail extraction at record time.** Defer to Phase 191B (backend has ffmpeg) OR Phase 192 (when share-sheet integration justifies the work). Phase 191 displays a generic video icon + duration string in the VideosCard list; the VideoPlaybackScreen renders the file directly via `react-native-video`.
- **Photo capture** (still images). → **Phase 194** (camera + photo integration per ROADMAP).
- **External-storage / Photos-app sharing.** → **Phase 192** (share sheet) which will need `READ_MEDIA_*` perms + `Intent.ACTION_SEND` integration on Android.
- **Resume mid-recording after interruption.** Recording always restarts from `idle`. Resume would need vision-camera session-restoration which is non-trivial.
- **Variable codec / resolution.** H.264 / 720p locked. 4K + H.265 are a Phase 192+ polish.
- **Session-tap-to-video search** (search videos across all sessions). → unfiled; needs UI design + use-case validation.
- **iOS support.** Phase 191 architect-gate runs Android only (no Mac access yet per ADR-001). iOS validation deferred until Phase 191's commits + when Mac is available.

## Smoke test (Kerwyn-side, post-build, pre-v1.1)

**TWO architect-gate stops in this phase.**

### Micro-gate after Commit 1 (native install verification)

1. **Cold gradle**: `cd android && ./gradlew clean && cd .. && npm run android`. Build completes. App launches on Pixel 7 API 35.
2. HomeScreen shows a new "Camera (Phase 191 commit 1)" Section with "Test camera" button.
3. Tap "Test camera" → Camera + Microphone permission prompts fire in sequence. Granted state shows "✓ Camera ready". Denied state shows "✗ Permission denied — open settings".
4. Status persists on app relaunch (granted state restored without re-prompting).
5. **No regression**: Phase 186 BLE / Phase 187 auth / Phase 188 / 189 / 190 all still work (run a 60-second smoke pass through HomeScreen → Garage → Sessions → DTC tap).

If green → state-machine sketch sign-off → Commit 2 starts.
If gradle fails → patch-package fix in Commit 1, re-smoke, then proceed.

### Full architect-gate after Commit 6 (~17-20 steps; full Phase 188-shape gate)

1. Cold relaunch. Auth ✓. Phase 186-190 no-regression.
2. Garage tab still works. Sessions tab still works. DTC search/detail still work.
3. Open Session #1 (or create one). VideosCard visible **between FAULT CODES and DIAGNOSIS**. Empty state: "No video evidence yet" + Record button.
4. Tap Record → VideoCaptureScreen opens. Camera preview live (front-or-back depending on default; Phase 191 uses back).
5. Tap large red record button. Recording starts; timer counts up; record button morphs to stop button.
6. Tap stop. Stopping spinner briefly. saved-state preview with thumbnail (or generic video icon + duration).
7. Tap "Use this video". Returns to SessionDetail. VideosCard now shows 1 video row with `Recorded YYYY-MM-DD HH:mm · 0:23 · 4.2 MB`.
8. Tap the video row. VideoPlaybackScreen opens. `react-native-video` controls work; play / pause / scrub.
9. Back → SessionDetail. Video still in card.
10. Record 4 more videos (total 5). 6th tap of Record → cap-reached UI.
11. Delete one video via long-press or detail-screen delete affordance. Cap clears. Record button re-enabled.
12. Phone-call interruption (simulated): start recording, trigger phone-state RINGING via `adb shell am broadcast`. Recording stops; saved state shows "Interrupted at 0:14"; playback works for the partial file.
13. App-background interruption: start recording, hit Home button, return. Same handling.
14. Close session via Phase 189 close-button. VideosCard now read-only — Record button hidden, existing videos still tappable for playback. Empty-state copy adjusts.
15. Reopen session. Record button reappears.
16. Cold relaunch app. Videos persist (file-system survives app restart). Metadata reloads correctly.
17. **No regression**: Phase 186 BLE / 187 auth / 188 garage / 189 sessions / 190 DTC.

If all pass → architect gate → v1.1 finalize.

## Commit plan (6 commits on `phase-191-video-diagnostic-capture` branch)

**Commit 1 — Native install + cold gradle + permission-prompt smoke (NO JS WORK).** Install `react-native-vision-camera` + `react-native-fs` + `react-native-video`. AndroidManifest.xml gets CAMERA + RECORD_AUDIO permissions. New `useCameraPermissions` hook (just the Camera + Microphone permission flow — not the recording flow). New HomeScreen Section "Camera (Phase 191 commit 1)" with status display + "Test camera" button. **Run cold gradle build**: `cd android && ./gradlew clean && cd .. && npm run android`. If patch-package needed for vision-camera (likely) or react-native-video (less likely), it lands in this commit too. **MICRO-GATE**: Kerwyn smokes. **No JS feature work in this commit**. Tests target ~213 (210 baseline + 3 useCameraPermissions tests).

**PAUSE — state machine sketch posted for Kerwyn sign-off.** The sketch in this v1.0 plan goes out separately for explicit sign-off after Commit 1's micro-gate, before Commit 2 ships. Same Phase 189 severity-style discipline.

**Commit 2 — `videoCaptureMachine.ts` reducer + `videoStorage.ts` service + types.** Pure-helper modules: state machine reducer (Idle / Recording / Stopping / Saved / Failed / Interrupted union + transition function); video storage service (path construction, RNFS calls, cap detection, orphan cleanup); `SessionVideo` + `RecordingError` types. ~18-22 unit tests covering all transitions + cap math + filename construction. No screen code, no Camera component. Tests target ~232.

**Commit 3 — `VideoCaptureScreen` real impl with vision-camera Camera component.** State-machine driven. Start/stop. Save to FS via Commit 2's storage service. Capture metadata at recording-finished callback (duration / resolution / file size / interrupted flag). Phone-call + app-background interruption handlers. Permission-permanently-denied blocked-state UI. Save-state preview with Use-this / Discard buttons. Tests target ~234.

**Commit 4 — `useSessionVideos` hook (FS-backed) + `VideoPlaybackScreen`.** Hook lists videos for a session by reading the per-session directory + sidecar JSONs. addRecording / deleteVideo / refresh / atCap / capReason exports per the contract documented in the Phase 191B handoff section. VideoPlaybackScreen uses `react-native-video` with the built-in controls. ~6-8 hook tests with RNFS mocked. Tests target ~242.

**Commit 5 — SessionDetailScreen VideosCard integration (between FAULT CODES and DIAGNOSIS) + closed-session lockdown + register screens on SessionsStack.** Card with empty-state, video-list, record button (disabled-on-cap, hidden-on-closed-session). Tap-row → VideoPlayback. Tap-record → VideoCapture. Navigation type extensions in `navigation/types.ts` + screen registration in `SessionsStack.tsx`. Tests stay ~242 (render-time wiring).

**Commit 6 — README + project structure update + ROADMAP 191B row + version bump 0.0.5 → 0.0.6.** README.md status / project-structure tree / testing section refreshed. Backend `docs/ROADMAP.md` (this finalize commit's separate backend commit) adds **Phase 191B** as a new row right after Phase 191 with status 🔲 + scope ("Backend video upload + Claude Vision analysis pipeline; AI integration over Phase 191's recordings"). package.json + lockfile bump.

Each commit: `npm test` green + `npx tsc --noEmit` clean before next. Phase 188 8-commit fix-cycle pattern is the worst-case reference; Phase 186-style native-module fix in Commit 1 is the most likely friction.

## Architect gate

**Two-stage gate this phase** (different from prior phases):

1. **Micro-gate after Commit 1** — native install + gradle + permission flow only. Smoke takes ~5 minutes.
2. **Full gate after Commit 6** — 17-step smoke (the list above). If round 1 fails, fix commits 7+ on the same branch (Phase 188 / Phase 190 precedent).

State-machine sketch sign-off (between Commits 1 and 2) is a separate review event, not a code gate — same conversational structure as Phase 189's severity Other... sketch.

## ROADMAP update at finalize (per Kerwyn pre-plan ask)

**Phase 191B added as a new ROADMAP row at finalize**, not buried in FOLLOWUPS. Concrete edit: in `moto-diag/docs/ROADMAP.md` Track I table, insert new row immediately after Phase 191:

```
| 191B | Video diagnostic upload + AI analysis pipeline | 🔲 | Backend `/v1/videos/*` endpoints (upload + frame extraction + Claude Vision analysis); migration for `videos` table; mobile useSessionVideos hook swap from FS-backed to backend-backed (consumer surface unchanged per Phase 191's handoff contract); ffmpeg integration for frame + audio extraction; Phase 100-103 Python modules wired into HTTP layer for the first time. (Spawned from Phase 191 capture-only scope split.) |
```

Phases 192-204 row numbers stay the same — 191B is a NEW row, not a renumbering. ROADMAP table count grows by 1.

## Versioning targets at v1.1 finalize

- Mobile `package.json`: 0.0.5 → 0.0.6.
- Mobile `implementation.md`: 0.0.7 → 0.0.8.
- Backend `implementation.md`: 0.13.6 → 0.13.7 (Phase History row added; Track I phase 7 of 20 — though shipping a NEW ROADMAP row 191B means Track I count grows from 20 to 21 phases; updated header text in implementation.md).
- Backend `pyproject.toml`: unchanged (Phase 191 is mobile-side; Phase 191B will be a backend phase).
