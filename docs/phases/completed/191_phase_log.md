# Phase 191 — Phase Log

**Status:** ✅ Complete | **Started:** 2026-04-28 | **Completed:** 2026-04-29
**Repo:** https://github.com/Kubanjaze/moto-diag-mobile (code) + https://github.com/Kubanjaze/moto-diag (docs)
**Branch:** `phase-191-video-diagnostic-capture` (8 commits, rebase-merged to mobile `main` at finalize; deleted local; remote was never pushed per Phase 188/189/190 precedent)

---

### 2026-04-28 — Plan v1.0 written

**Scope split locked (per pre-plan Q&A with Kerwyn):**

Phase 191 ships **mobile-only video capture substrate** (recording + local storage + playback inside SessionDetail). **Backend upload + AI analysis pipeline split off as Phase 191B** — a NEW ROADMAP row added at finalize, not just a FOLLOWUPS.md entry.

Reasoning: full ROADMAP scope ("film bike running, auto-extract audio + key frames → AI analysis") is honestly 3-4 phases compressed into one. Substrate-then-feature pattern (Phase 187 → 188, Phase 189 → 190) keeps each phase gate-sized. Phase 191B will land Track-I-internal as a backend-side follow-on.

**Risk profile:** Phase 186 (ble-plx CMake patch) is the right comparison — heavy native-module integration, patch-package likely. NOT Phase 188-shape (transport bug stack) or Phase 190-shape (mock-fidelity stack). Mitigation built into commit cadence: Commit 1 ships native install + cold gradle + permission-prompt smoke ALONE — no JS feature work. Micro-gate inserted between Commits 1 and 2.

**Plan addresses all 7 of Kerwyn's pre-plan asks explicitly:**

1. **Phase 191B in ROADMAP at 191 close** — concrete row text drafted in plan section "ROADMAP update at finalize".
2. **Risk profile honesty** — Phase 186 comparison framed; H.264/MP4 locked (H.265 rejected for battery/heat/iOS-Photo legacy reasons); Android 13+ split-perms callout in dedicated section.
3. **Recording state machine sketch in plan v1.0** — full state table + transition graph + phone-call + app-background interruption behavior. Posted separately for sign-off after Commit 1's micro-gate, before Commit 2 starts.
4. **File system policy** — DocumentDirectoryPath persisted; `videos/session-{N}/session-{N}-{ISO8601-compact}-{8charuuid}.mp4` + JSON sidecar; per-session cap = 5 videos AND 500 MB whichever-fires-first; disk-full handling via `getFreeDiskStorage()` precheck + ENOSPC mid-write recovery; orphan cleanup on session-not-found via `cleanupOrphanedVideos()` helper called on `useSessionVideos` mount.
5. **SessionDetail integration position** — VideosCard between FAULT CODES and DIAGNOSIS (evidence precedes diagnosis) per Kerwyn's recommendation.
6. **Closed-session rule** — record button HIDDEN (not just disabled) on closed sessions; existing videos still playable. Symmetric gap flagged for Phase 191 polish (F7) — Phase 189 append-inputs for symptoms/fault-codes/notes have the same gap; retroactive lockdown filed as a Phase 191 polish item.
7. **Phase 191B handoff shape** — `useSessionVideos` is backend-agnostic; `SessionVideo` type + `NewRecording` type defined with all fields Phase 191 captures + the four `*State` and `remoteUrl` fields stubbed as `null` in Phase 191, populated by Phase 191B. Hook contract identical in both phases.

**No backend changes.** No schema changes (still v38). No new ADR (camera substrate doesn't introduce a new architecture-level decision; ADR-001 RN choice + ADR-002 New-Arch-off cover it).

**Files plan:**

- New (10): VideoCaptureScreen / VideoPlaybackScreen + videoCaptureMachine reducer + useSessionVideos + useCameraPermissions + types/video.ts + services/videoStorage.ts + 2 nav extensions + SessionDetailScreen VideosCard.
- Modified (3): package.json+lock + AndroidManifest.xml + README.md + implementation.md.
- New tests (~22-28): videoCaptureMachine pure reducer tests + videoStorage pure service tests + useSessionVideos hook tests with RNFS mocked.

**New runtime deps (3):** `react-native-vision-camera@^4.x` (heavy), `react-native-fs@^2.x` (light), `react-native-video@^6.x` (medium).

**Commit plan (6 commits):**

1. **Native install + cold gradle + permission-prompt smoke screen ONLY.** No JS feature work. Patch-package fix lands here if vision-camera (or rn-video) hits the `isNewArchitectureEnabled()` gradle bug — same shape as ble-plx in Phase 186. **MICRO-GATE** after this commit.
2. **State machine reducer + storage service + types** — pure-helper modules + ~18-22 tests. State-machine sketch sign-off PRECEDES this commit.
3. **VideoCaptureScreen real impl** — Camera component, recording lifecycle, save flow, interruption handlers, blocked-state UI for permanently-denied perms.
4. **`useSessionVideos` hook (FS-backed) + VideoPlaybackScreen** — backend-agnostic hook contract per Phase 191B handoff section; rn-video for playback.
5. **SessionDetailScreen VideosCard integration** — between FAULT CODES and DIAGNOSIS; closed-session lockdown; nav extensions; tap-row + tap-record wiring.
6. **README + project structure + ROADMAP 191B row + version 0.0.5 → 0.0.6.**

If gradle fails in Commit 1 (real risk), patch-package fix lands inside Commit 1 itself — no new commits invalidated.

**Versioning targets at v1.1 finalize:**

- Mobile `package.json`: 0.0.5 → 0.0.6.
- Mobile `implementation.md`: 0.0.7 → 0.0.8.
- Backend `implementation.md`: 0.13.6 → 0.13.7 (Track I header text grows 20 → 21 phases because of the new 191B row).
- Backend `pyproject.toml`: unchanged.

**Smoke-test plan written into v1.0** — TWO architect-gate stops this phase:
- Micro-gate after Commit 1: cold gradle + permission flow + no-regression smoke (~5 min).
- Full gate after Commit 6: 17-step smoke covering recording / storage / playback / cap / closed-session / interruption / cold-relaunch persistence (Phase 188-190 shape).

**Next:** plan commit on backend `master` (this file + 191_implementation.md v1.0), then create `phase-191-video-diagnostic-capture` branch in mobile repo and start Commit 1 (native install + gradle + permission smoke ONLY — no feature code).

---

### 2026-04-28 — Commit 1 (`d7117c5`) + Commit 1 micro-gate PASSED

Mobile branch `phase-191-video-diagnostic-capture` created from `main`. **Commit 1** installed `react-native-vision-camera@4.7.3` + `react-native-fs@2.20.0` + `react-native-video@6.19.2`; added CAMERA + RECORD_AUDIO to `AndroidManifest.xml`; new `useCameraPermissions` hook with the Camera + Microphone permission flow; HomeScreen Camera Smoke Section with status display + "Test camera" button. **No JS feature work in this commit per the v1.0 plan.**

**Cold gradle build green on first try.** `cd android && ./gradlew clean && cd .. && npm run android` — clean build, app launched on Pixel 7 API 35 emulator. **Zero patch-package work needed** — vision-camera 4.7.3 + rn-video 6.19.2 + rn-fs 2.20.0 all built clean against `newArchEnabled=false` on first cold-gradle pass. The v1.0 plan's "Phase 186 redux" risk projection for the `isNewArchitectureEnabled()` CMake bug shape did NOT materialize. Risk projections for upcoming Track I phases should weight "we already have patches/ scaffolding" as a sunk cost that absorbs this most-likely-shape native-module integration friction.

Permission-prompt smoke verified: tap "Test camera" → Camera + Microphone prompts fired in sequence; granted state showed "✓ Camera ready"; cold relaunch persistence verified via swipe-kill + relaunch (status restored without re-prompting). Phase 186 BLE / 187 auth / 188 garage / 189 sessions / 190 DTC zero-regression smoke all green.

**Filed F8** (formatFileSize unit-switching polish — Section section showed bytes for sub-MB values, inconsistent with the rest of the UI). Folded into Commit 3 fix.

**Tests at this checkpoint:** 213 / 213 (210 baseline + 3 useCameraPermissions).

---

### 2026-04-28 — State machine sketch sign-off (pre-Commit 2)

Per the v1.0 plan "PAUSE — state machine sketch posted for Kerwyn sign-off" gate. Items 1–6 approved as written + 2 Kerwyn folds:

- **Fold 1 — Auto-keep on APP_BACKGROUNDED from saved.** When the app backgrounds with a saved-state preview tile visible, auto-keep (persist + return to capture-idle) instead of preserving the preview across the foreground re-entry. Preserves user intent ("they tapped record + got a recording, that recording should not vanish on phone-call"); avoids stale-state UI on long backgrounds.
- **Fold 2 — RecordingError discriminated union.** `failed` state holds an explicit `error: RecordingError` discriminated union (`storage_full | permission_lost | codec_error | unknown`) rather than a free-form string, so the failed-state UI can route per-error-kind to specific recovery copy. `classifyVisionCameraError` maps vision-camera error codes to these kinds.

Sign-off cleared Commit 2 to proceed.

---

### 2026-04-28 — Commit 2 (`35226bc`) — state machine reducer + storage service + types

`src/screens/videoCaptureMachine.ts` pure reducer with 5 states (`idle | recording | stopping | saved | failed`) + Kerwyn fold #1 (auto-keep on APP_BACKGROUNDED from saved) + Kerwyn fold #2 (RecordingError discriminated union with 4 kinds). All transitions tested.

`src/services/videoStorage.ts` RNFS-backed file-system policy: MAX_VIDEOS_PER_SESSION = 5, MAX_BYTES_PER_SESSION = 500 MB, MIN_FREE_BYTES = 100 MB; `videos/session-{N}/session-{N}-{ISO8601-compact}-{8charuuid}.mp4` + JSON sidecar; `saveRecording` does move-not-copy with EXDEV cross-volume fallback + post-move RNFS.stat for fileSizeBytes; `cleanupOrphanedVideos` walks live-set diff. Tests cover path math, EXDEV fallback, cap evaluation (count + size), and orphan cleanup.

`src/types/video.ts` SessionVideo (with 4 backend-side fields stubbed null in Phase 191 — `remoteUrl`, `uploadState`, `analysisState`, plus the future analysis findings field), NewRecording, RecordingError discriminated union per Kerwyn fold #2.

**Build-time fixes (caught locally before commit):** typed reducer fixture as `Extract<RecordingState, {kind: 'recording'}>` so test files can access `.startedAt` without narrowing the union; replaced `crypto.randomUUID()` (RN doesn't expose Node's crypto) with Math.random hex; dropped `fileSizeBytes` from `NewRecording` and derived via `RNFS.stat` post-move (vision-camera's `VideoFile.size` field doesn't exist in v4.7); replaced `StyleSheet.absoluteFillObject` (removed in RN 0.85) with explicit position/top/left/right/bottom.

Tests: 213 → 244 (+31 — videoCaptureMachine reducer + videoStorage path/cap/cleanup).

---

### 2026-04-28 — Commit 3 (`bbf5d90`) — VideoCaptureScreen + 4 failed-state UIs

`src/screens/VideoCaptureScreen.tsx` with `useReducer` + Camera component + AppState listener with `interruptedRef` pattern (closure-capture safety) + 4 failed-state UIs routed by `error.kind` (storage_full / permission_lost / codec_error / unknown) + permission gate via useCameraPermissions + at-cap UI guard + elapsed-time setInterval at 250ms outside reducer.

Tests: 244 → 251 (+7).

---

### 2026-04-28 — Commit 3 architect-smoke FAILED at Verification 5 → fix-cycle

Orange "Paused at 0:XX" badge wasn't rendering on saved-preview after AppState background-during-recording. **Root cause: closure-state capture.** The `onRecordingFinished` closure registered with `cameraRef.startRecording` captured `state` at moment-of-tap-record (`state=idle`), so `wasInterrupted = state.kind === 'stopping' && state.reason === 'interrupted'` always evaluated false. **NOT** a reducer bug — the reducer correctly transitioned to `stopping` with `reason='interrupted'` on the AppState handler's dispatch. The bug was that the callback couldn't see that updated state because it was looking at its captured snapshot from registration-time.

This is the third instance of the "snapshot/assumption doesn't match runtime" failure family on Track I:
- Phase 188 Bug 2: HVE mock shape didn't match the real backend (`{detail: [...]}` vs `{title, status, detail}`).
- Phase 190 Bug 2: substring-match on error text used assumption about backend wire format.
- Phase 191 Commit 3: closure captured state at registration time, not at fire time.

**Fix (Commit 3 follow-up `ffa383c`):** explicit `interruptedRef = useRef<boolean>(false)`. Set true in AppState background handler BEFORE calling stopRecording(). Set false at start of every recording (handleStartRecording) and at user-initiated stop (handleStopRecording). Read via `interruptedRef.current` inside `onRecordingFinished` instead of reading `state.kind`. Also folded F8 (formatFileSize auto-unit-switching B / KB / MB / GB with one-decimal precision below 10MB) into the same commit.

**Architect smoke re-run: PASSED.** "⏸ Paused at 0:14" badge now renders correctly on the saved-preview tile when AppState backgrounds mid-record.

**Filed F9** — document the `useRef`-not-state pattern for callbacks registered with native modules. The lesson generalizes beyond vision-camera: any callback handed to a native module captures JS-side state at registration time, not at fire time. F9 also pulls forward the meta-observation that this is now a robust failure family worth a generalized lint rule (Phase 192+ pickup).

Tests: 251 → 257 (+6 — videoCaptureHelpers including formatFileSize + classifyVisionCameraError).

---

### 2026-04-28 — Commit 4 (`1ac4c26`) — useSessionVideos hook + VideoPlaybackScreen

`src/hooks/useSessionVideos.ts` backend-agnostic hook returning `{videos, addRecording, deleteVideo, refresh, atCap, capReason, isLoading, error}`. **Phase 191B handoff contract**: hook owns UUID generation; SessionVideo type stays identical between Phase 191 (FS-backed) and Phase 191B (HTTP-backed); consumers (SessionDetailScreen's VideosCard, VideoCaptureScreen save flow) see the SAME shape in both phases.

`src/screens/VideoPlaybackScreen.tsx` with react-native-video v6 + built-in controls + meta band (timestamp / duration / file size / resolution) + orange "⏸ Paused" badge for interrupted videos + delete-with-confirm.

Tests: 257 → 290 (+33 — useSessionVideos contract including the Phase 191B handoff regression guard + dtcErrors carry-forward + various helper tests).

---

### 2026-04-28 — Commit 5 (`b9f1b0f`) — SessionDetail VideosCard + closed-session lockdown + cleanupOrphanedVideos wiring

`src/screens/SessionDetailScreen.tsx` adds VideosCard + VideoRow sub-components BETWEEN FaultCodesCard and DiagnosisCard (Kerwyn pre-plan placement: evidence precedes diagnosis). Closed-session lockdown: Record button HIDDEN (not just disabled) when `session.status === 'closed'`; existing videos still tappable for playback; empty-state copy adjusts.

`src/screens/SessionsListScreen.tsx` adds separate `useEffect([sessions, isLoading, error])` calling `cleanupOrphanedVideos(liveIds)` so the videos directory sweeps orphan session-N/ subdirs whenever the live session set updates. Pattern necessary because chaining cleanup after `refetch` would capture a stale `sessions` reference; only React's render cycle gives us the post-refetch fresh data.

`src/navigation/types.ts` registers `VideoCapture` + `VideoPlayback` on SessionsStack (HomeStack registrations from Commit 1's smoke section removed in this cleanup).

Tests: 290 → 295 (+5).

---

### 2026-04-28 — Commit 6 (`78834e4`) — README + project structure update + version bump 0.0.5 → 0.0.6

README.md status / project-structure tree / testing section refreshed: all new packages listed, 301 test count documented, two transport-regression guards from Phase 188/189 carried forward in the testing summary. HomeScreen subtitle bumped to Phase 191. Mobile package.json version 0.0.5 → 0.0.6.

Removed Commit 1's HomeScreen Camera Smoke Section (no longer needed once VideoCaptureScreen is real).

Tests: 295 → 301 (+6 from in-cycle additions).

---

### 2026-04-28 — Architect full gate after Commit 6 — FAILED with 3 bugs

17 of 17 substrate verifications passed; **3 bugs found** in cross-cutting integration:

- **Bug 1 (HIGH) — VideosCard refresh on focus.** SessionDetail → VideoCapture (record + save) → back: VideosCard didn't show the freshly-saved recording until cold restart. Same on the delete return-path from VideoPlaybackScreen. Root cause: SessionDetail doesn't unmount when a sibling screen pushes onto the SessionsStack; useSessionVideos's mount-time effect therefore doesn't re-fire when the screen is revealed again. The hook DOES expose `refresh`, but nothing was calling it.
- **Bug 2 (LOW) — closed-session × has-videos visual hole.** Closed sessions with ≥1 saved video showed playback rows but a visually blank slot below them where the Record button used to live. No copy explaining why the capture path was gone.
- **Bug 3 (MEDIUM) — bottom-tab wireframe icons.** All three tabs rendered with `⏷` placeholder glyphs above the labels. Investigation: this is `@react-navigation/elements`'s default `MissingIcon` (a `⏷` Unicode char) rendered when no `tabBarIcon` is configured. Has been there since Phase 189 commit 2 added the bottom-tab nav; the full architect gate just surfaced it for the first time. **NOT a Phase 191 regression.**

Architect cleared the fix-cycle to land on the same branch (Phase 188/190 precedent) before merge.

---

### 2026-04-29 — Commit 7 (`39948c1`) FIX: Bugs 1+2+3 in a single commit

All three fixes landed in one commit with explicit per-bug callouts in the message body for targeted re-smoke verification. Small enough that splitting per-bug would add no review value.

- **Bug 1 fix** — `useFocusEffect(useCallback(() => { void refresh(); }, [refresh]))` placed INSIDE VideosCard (not on SessionDetailScreen) so `refresh` is in scope. Lives where the hook instance lives; React Navigation's useFocusEffect fires for any component nested inside the focused screen.
- **Bug 2 fix** — closed branch in VideosCard now renders a cap-pane-shaped block when `videos.length > 0`. Cream/amber styling matches the at-cap pane. Copy: "Session closed" + "Reopen this session to record more."
- **Bug 3 fix** — `tabBarIcon: () => null` on `RootNavigator` `screenOptions`. Restores the text-label-only look from Phase 189's design intent. Commit message explicitly notes this was always-there default behavior.

Verification: tsc clean, npm test 301/301 green (no test count delta — all three are render/effect-layer changes covered by existing routing + state-machine tests).

---

### 2026-04-29 — Architect full gate fix-cycle re-smoke PASSED

8 of 8 verifications green across all three bugs (save-return refresh, delete-return refresh, closed-session lockdown copy, wireframe-nav fix) plus full sanity sweep (Garage, Sessions, DTC P0171, 2:20 PM Paused-badge artifact preserved on Session #1 as 191B regression coverage).

**Architect cleared for v1.1 finalize.**

**Phase 191 polish backlog (carried forward to Phase 192+):**
- F2 — per-entry edit/delete on open sessions (carry-over from Phase 189).
- F3 — lifecycle audit history (carry-over from Phase 189).
- F4 — make/family chip on DTCSearch result rows (carry-over from Phase 190).
- F5 — "Code not in catalog yet" empty-state copy (carry-over from Phase 190).
- F6 — `useDTC` memoization to suppress React 18 StrictMode dev-only double-fetch (carry-over from Phase 190).
- F7 — symmetric closed-session lockdown for Phase 189's symptoms / fault-codes / notes append inputs (NEW — Phase 191 closed the gap for videos but left it open for the other lists).
- F9 — document the `useRef`-not-state pattern for callbacks registered with native modules (NEW — surfaced from Commit 3 closure-state-capture bug + meta-observation that this is the third instance of the "snapshot/assumption doesn't match runtime" failure family across Track I).
- (F8 shipped in Commit 3 as part of the closure-capture fix-cycle — formatFileSize auto-unit-switching B / KB / MB / GB.)

---

### 2026-04-29 — v1.1 finalize (this commit)

- Plan → v1.1: header bumped (date 2026-04-29, status ✅ Complete); ALL Verification Checklist items `[x]` with verification notes from the micro-gate, full gate, and re-smoke. New sections: Bug verification (3 bugs from full gate), Deviations from Plan (8 items), Results table (test counts, gate outcomes, version bumps, Track I scorecard 7 / 21), Key finding (substrate-then-feature splits keep gates gate-sized + the closure-capture bug reframes the snapshot/assumption failure family).
- Phase log → this file (timestamped milestones from plan v1.0 through Commit 1 micro-gate through state-machine sketch sign-off through Commit 2-6 builds through Commit 3 closure-capture fix through full gate fail through Commit 7 three-bug fix through re-smoke pass through this finalize).
- Move both files from `docs/phases/in_progress/` → `docs/phases/completed/`.
- Backend `implementation.md` version bump 0.13.6 → 0.13.7; Phase 191 row added to Phase History above the Phase 190 row.
- Backend `phase_log.md` Phase 191 closure entry.
- Backend `docs/ROADMAP.md` Phase 191 marked ✅; **Phase 191B added as a NEW row** immediately after Phase 191 (per Kerwyn's pre-plan ask): backend video upload + AI analysis pipeline; status 🔲. Phases 192-204 row numbers stay the same. Track I count grows 20 → 21 phases.
- Mobile `implementation.md` version bump 0.0.7 → 0.0.8; Phase 191 row added to Phase History pointer table.
- Mobile `docs/FOLLOWUPS.md`: F7 + F9 added to Open list; F2 + F3 + F4 + F5 + F6 carried over; F8 NOT listed (shipped in Commit 3).
- Rebase-merge `phase-191-video-diagnostic-capture` → `main` (8 commits + 1 mobile-finalize commit = 9 commits onto main, fast-forward).
- Delete feature branch local; remote was never pushed per Phase 188/189/190 precedent — local-only deletion is sufficient.

**Phase 191 closes green. Track I scorecard: 7 of 21 phases complete (185 / 186 / 187 / 188 / 189 / 190 / 191).** Next: **Phase 191B — Video diagnostic upload + Claude Vision AI analysis pipeline** (NEW row in ROADMAP) — backend `/v1/videos/*` endpoints + ffmpeg frame extraction + Claude Vision call wired through the new HTTP layer + `useSessionVideos` hook swap from FS-backed to backend-backed. Phase 191's substrate is the foundation; Phase 191B is the feature that justifies the substrate's existence.
