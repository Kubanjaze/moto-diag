# Phase 191 — Phase Log

**Status:** 🚧 In Progress | **Started:** 2026-04-28
**Repo:** https://github.com/Kubanjaze/moto-diag-mobile (code) + https://github.com/Kubanjaze/moto-diag (docs)
**Branch:** `phase-191-video-diagnostic-capture` (will be created in mobile repo at Commit 1)

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
