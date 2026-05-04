# Phase 191B — Phase Log

**Status:** ✅ Complete | **Started:** 2026-04-29 | **Completed:** 2026-05-04
**Repo:** https://github.com/Kubanjaze/moto-diag (backend) + https://github.com/Kubanjaze/moto-diag-mobile (mobile hook swap in Commit 6)
**Branch:** `phase-191B-video-upload-ai-analysis` (LOCAL on both repos; rebase-merged to master/main at finalize; deleted local; remote was never pushed per Phase 188+ precedent)

---

### 2026-04-29 — Plan v1.0 written

**Phase 191B opens as the substrate-then-feature pair completion.** Phase 191 shipped the mobile capture substrate (recording + on-device storage + playback inside SessionDetailScreen) at v1.1 finalize earlier today. Phase 191B is the backend pipeline + AI analysis = the feature that justifies the substrate's existence. Same pattern as Phase 187 → 188 (auth substrate, then CRUD over it) and Phase 189 → 190 (session substrate, then DTC integration).

**Pre-implementation Q&A pinned all scope decisions before plan writing** — same Phase 189 / 190 / 191 discipline. Scope set with one round of clarifying questions covering:

- A. Backend surface (endpoint shape / authorization / quotas)
- B. Storage + AI pipeline (file storage / ffmpeg / frame policy / audio handling / Vision call shape / state machine)
- C. Mobile consumer-surface swap (file source for playback / hook swap timing / Phase 191 stub field handling)
- D. Phase shape (commit cadence / architect gate stops)

**All recommendations (A1-D2) accepted as-written with two confirmations:**

1. **A1 — endpoint shape switched from top-level to fully nested.** Audit of `src/motodiag/api/routes/` confirmed every session sub-resource (symptoms / fault-codes / notes / close / reopen) is nested under `/v1/sessions/{id}/...` with no flat alternative. Videos fit cleanly into that pattern; the original A1's `/v1/videos/` had a REST-best-practice bias that doesn't match the codebase. Plan v1.0 ships fully-nested:
   - `POST /v1/sessions/{id}/videos`
   - `GET /v1/sessions/{id}/videos`
   - `GET /v1/sessions/{id}/videos/{video_id}`
   - `DELETE /v1/sessions/{id}/videos/{video_id}`
   - `GET /v1/sessions/{id}/videos/{video_id}/file`

2. **C2 — backend integration test coverage explicit in plan v1.0.** Dedicated section enumerates each contract that must pass before the architect gate fires. Single load-bearing assertion: mobile's existing `__tests__/hooks/useSessionVideos.test.ts` from Phase 191 continues passing UNCHANGED after the Commit 6 hook swap. Mock layer changes (mocks `api.POST` instead of `saveRecording`); test bodies do not. If a test body needs to change, the hook contract has drifted.

**Three new test files documented in coverage detail** (~70-80 backend tests):
- `tests/test_phase191b_videos_api.py` — endpoint contract (~30 tests): ProblemDetail envelope on every error path with real-backend-anchored fixtures, X-API-Key propagation, multipart Content-Type preservation (Phase 188 lesson), tier gate enforcement, per-session count + size cap, per-tier monthly quota, soft-delete semantics, file-stream headers, end-to-end happy + failure paths.
- `tests/test_phase191b_ffmpeg.py` — subprocess wrapper (~12 tests): frame extraction count + cap; audio mp3 sidecar; module-load detection; FFmpegMissing + FFmpegFailed exception shapes.
- `tests/test_phase191b_video_analysis.py` — Claude Vision wrapper (~15 tests): **Anthropic SDK mocked using fixtures pulled from real API responses** per Phase 190 Bug 2 lesson; structured-output schema validation; tool-use block extraction; cost-tier model selection; retry behavior; persistent-error fallback; vehicle context interpolation.

**Risk profile**: this is the **first production wiring of Claude Vision + ffmpeg into the HTTP layer** on Track I. Phase 100-103 (Claude API learning series) shipped as standalone scripts; Phase 191B brings them into the production API surface. Cost surprises possible (Sonnet at 60 frames/call ≈ $0.06-0.10 per analysis); mitigation: cost_estimate_usd in every response; admin aggregate dashboard is Phase 192+.

**No micro-gate this phase** — no native-module integration like Phase 191 had. Backend integration tests cover the load-bearing risk pre-gate.

**Files plan:**
- New backend (12): migration v39 + Video model + repo + videos router + ffmpeg wrapper + Vision wrapper + analysis worker + media/__init__ + data/videos/.gitkeep + 3 test files.
- Modified backend (5): app.py (router register) + database.py (SCHEMA_VERSION 38→39) + openapi.py (videos tag + multipart shape) + errors.py (413 mapping) + pyproject.toml (anthropic required + version 0.1.0→0.2.0).
- New mobile (1): types/videoAnalysis.ts.
- Modified mobile (6): api-schema/openapi.json (refresh) + api-types.ts (regen) + useSessionVideos (hook swap — load-bearing) + SessionDetailScreen (5-state badge + findings expansion) + VideoCaptureScreen (uploading state + progress indicator) + videoStorage.ts → videoStorageCache.ts (replace).

**Modified mobile tests:**
- `__tests__/hooks/useSessionVideos.test.ts` runs UNCHANGED (load-bearing).
- `__tests__/services/videoStorage.test.ts` deleted with the service.
- `__tests__/services/videoStorageCache.test.ts` new (~5-8 tests).
- `__tests__/screens/videoCaptureMachine.test.ts` extended with `uploading` state (~6 new tests).

**No new ADR.** Multipart upload + BackgroundTasks + tool-use structured output are all established patterns from prior phases or Anthropic SDK docs; no architecture-level decision worth a durable ADR.

**Commit plan (7 commits on `phase-191B-video-upload-ai-analysis` branch):**

1. **Migration v39 + Video model + repo + ffmpeg subprocess wrapper.** Pure backend. ~22-25 unit tests across 2 test files.
2. **Claude Vision wrapper + recorded fixtures.** Pure backend module; no endpoint wiring yet. ~15 tests.
3. **Upload endpoint + multipart handling + BackgroundTask wiring.** First end-to-end happy path through Vision pipeline. ~12 tests.
4. **List + single + delete endpoints.** Soft-delete semantics + cascade verification. ~10 tests.
5. **File-stream endpoint.** Binary stream with proper headers. ~6 tests.

**SKETCH SIGN-OFF for the mobile state-machine `uploading` state extension** — posted separately, gates Commit 6.

6. **Mobile hook swap (FS-backed → HTTP-backed).** Single mobile commit. Refresh openapi.json + regen api-types.ts; rewrite useSessionVideos; delete videoStorage.ts; create videoStorageCache.ts; extend videoCaptureMachine; render 5-state analysis badge. **useSessionVideos.test.ts UNCHANGED** — load-bearing.
7. **README updates + project structure refresh + ROADMAP mark + version bumps + finalize docs.**

**Versioning targets at v1.1 finalize:**
- Backend `pyproject.toml`: 0.1.0 → 0.2.0 (Track I major-feature bump).
- Backend `implementation.md`: 0.13.7 → 0.13.8.
- Backend schema: 38 → 39.
- Mobile `package.json`: 0.0.6 → 0.0.7.
- Mobile `implementation.md`: 0.0.8 → 0.0.9.

**Smoke-test plan written into v1.0** — single full architect gate after Commit 7 (~18-22 steps): cold backend launch + schema_version=39; mobile cold-relaunch with no Phase 186-191 regression; Phase 191 paused-badge artifact still present on Session #1; new recording → upload-progress indicator → analysis_state polling pending → analyzing → analyzed → findings tile expansion; cost log inspection; per-session caps + per-tier monthly quota verified via curl bypass; tier-gate enforcement; ffmpeg-missing simulation (env override) → 503; Vision-failure simulation (invalid API key) → analysis_failed; soft-delete + cascade-delete; cold relaunch persistence; multipart on-the-wire body shape sanity; ProblemDetail envelope shape across all error cases; full Phase 175-184 backend regression + Phase 188-191 mobile regression; **load-bearing assertion: useSessionVideos.test.ts unchanged.**

**Next:** plan commit on backend `master` (this file + 191B_implementation.md v1.0), then create `phase-191B-video-upload-ai-analysis` branch in backend repo and start Commit 1 (migration v39 + Video model + repo + ffmpeg subprocess wrapper).

---

### 2026-04-30 — Plan v1.0.1 — pre-Commit-1 corrections from codebase audit

Six corrections to plan v1.0 surfaced when starting Commit 1 prep work — pre-Builder-dispatch audit of `src/motodiag/` revealed plan-vs-codebase drift on paths + module existence + dependency claims that would have multiplied into Builder confusion. Corrections land here on the plan-of-record before any Builder dispatches; full v1.0 → v1.0.1 diff committed to backend `master` separately.

**Why a v1.0.1 amendment instead of capturing as deviations at v1.1 finalize:** corrections this large should land on the plan-of-record before Builder agents start. Otherwise the Builders work from inaccurate paths + the deviations multiply.

**The six corrections:**

1. **`anthropic >= 0.40` is already required in pyproject.toml line 32** — has been since Phase 79 (the Claude API series, not Phases 100-103 as plan v1.0 implied). Backend venv has `anthropic 0.96.0`. Plan v1.0's "add anthropic to required deps" diff is a no-op; drop from Commit 7.

2. **Storage paths**: backend uses `src/motodiag/core/` (single-package, function-based repos, module-flat models), NOT `src/motodiag/storage/`. Specifically:
   - `core/database.py` SCHEMA_VERSION constant — bump 38 → 39 in place.
   - `core/migrations.py` MIGRATIONS list — APPEND `Migration(version=39, ...)` entry (single-file pattern, not per-version files).
   - `core/models.py` — APPEND `VideoBase` + `VideoCreate` + `VideoResponse` to existing module (cohabits with `VehicleBase` + `DiagnosticSessionBase`).
   - `core/video_repo.py` NEW (mirror `core/session_repo.py` shape).

3. **`motodiag.ai` package does NOT exist and shouldn't be created.** Right home is `motodiag.media.*` (Track C2 — Phases 96-108 already shipped the package with `vision_analysis.py`, `video_frames.py`, `audio_capture.py`, `spectrogram.py`, `sound_signatures.py`, `photo_annotation.py` + 7 others). Phase 191B's NEW modules become siblings:
   - `media/ffmpeg.py` (subprocess wrapper)
   - `media/vision_analysis_pipeline.py` (orchestrator)
   - `media/analysis_worker.py` (BackgroundTasks entry)

4. **`media/video_frames.py` (Phase 100) is metadata-only** — operates on `VideoMetadata` Pydantic models with placeholder descriptions. NO actual ffmpeg. Phase 191B builds the real backend that fulfills the Phase 100 contract; reuses `VideoFormat` / `VideoResolution` / `VideoMetadata` / `VideoFrame` / `FrameExtractionConfig` / `SceneChangeMarker` types unchanged.

5. **`media/vision_analysis.py` (Phase 101) is text-only with the right schema** — `VisualAnalyzer.analyze_image` takes `image_description: str`, calls `DiagnosticClient.ask()` (text completion). Phase 191B reuses `FindingType` + `Severity` + `VisualFinding` + `VisualAnalysisResult` + `VehicleContext` + `VISION_ANALYSIS_PROMPT` + `SMOKE_COLOR_GUIDE` + `FLUID_COLOR_GUIDE`; ADDS `frames_analyzed` + `model_used` + `cost_estimate_usd` as 3 non-breaking optional fields on `VisualAnalysisResult` (no model redefinition). Plan v1.0's brand-new `VideoAnalysisFindings` model is dropped.

6. **`engine/client.py:DiagnosticClient.ask()` is text-only** — `messages=[{"role": "user", "content": prompt}]` is string-only, no image content blocks. Plan v1.0.1 adds `DiagnosticClient.ask_with_images(prompt, images: list[Path], ...) -> tuple[Message, TokenUsage]` that builds multi-content-block messages with base64-encoded images + threads through the existing cost / cache / token-usage tracking. `media/vision_analysis_pipeline.py` is the consumer of this new method. NEW dedicated test file `tests/test_phase191b_diagnostic_client_images.py` (~6-8 tests).

**Net effect on commit plan:**
- Commit 1 expands slightly to also touch `engine/client.py` (the new `ask_with_images()` method is a Commit 2 dependency). +1 test file.
- Commit 2 file paths corrected (was `ai/video_analysis.py`, now `media/vision_analysis_pipeline.py`). Schema reuse drops plan v1.0's `VideoAnalysisFindings` model entirely.
- Commits 3-7 unchanged.

**Pre-Commit-1 architect time spent on audit and corrections: ~25 min.** Catching this before Builder dispatch prevents an estimated 2-3 hours of Builder rework + a phase_log polluted with mechanical-correction deviations at v1.1 finalize.

**Lesson for the rest of Track I:** every plan v1.0 should ground every file-path claim in a `Glob` or `ls` of the actual codebase **before** the plan commit lands on master, not after. The `mock fidelity` lesson from Phase 190 has a sibling: **path fidelity** — every path in a plan should anchor to `git ls-files` evidence, not to architect assumption about how the codebase is laid out. Filed under F9's broader "snapshot/assumption doesn't match runtime" failure family.

**Next:** Builder-A dispatched for Commit 1 (migration v39 entry + Video models + video_repo + ffmpeg wrapper + DiagnosticClient.ask_with_images extension); Builder-B dispatched for Commit 2 (real Vision pipeline + recorded Anthropic fixtures) in parallel since file overlap is zero.

---

### 2026-04-30 — Commit 1 (`5970aff`) build via Builder-A + verification

Builder-A reported back with: 70 tests across 4 new test files (15 migration + 27 video_repo + 20 ffmpeg + 8 diagnostic_client_images) + 1 deviation worth flagging upstream — Builder-A correctly identified that the canonical session table is `diagnostic_sessions` not `sessions` (plan v1.0.1 used "sessions" as shorthand; SQLite would have silently no-op'd a FK to a non-existent table). Architect verified Builder-A's FK correction against `core/database.py:80` + prior migration entries; deviation sound, kept.

Architect ran phase-specific tests: **65 passed, 5 skipped** (5 TestRealFFmpeg tests gated on `FFMPEG_BIN` which isn't on the dev machine's PATH; expected). Committed as `5970aff`.

### 2026-04-30 — Commit 2 (`16512a4`) build via Builder-B + verification

Builder-B reported back with: 20 tests + 5 boundary additions in `test_phase191b_video_analysis_pipeline.py` + extended VisualAnalysisResult with 3 non-breaking fields + new `vision_analysis_pipeline.py` orchestrator + new `analysis_worker.py` BackgroundTask entry + synthetic Anthropic fixture (per Phase 190 lesson: synthetic fixtures match SDK type definitions, not real-API recordings).

Architect verified: **20 / 20 passing**. Committed as `16512a4`.

### 2026-04-30 — Commits 3-5 collapsed (`c1a6fb3`) build via Builder-C + verification

Per plan v1.0 these were 3 separate commits (POST upload / GET list+single+DELETE / GET file-stream); Architect collapsed into a single Builder dispatch since plan had no architect-side smoke between the three. Builder-C reported back with: 30 tests across 6 classes + 5 deviations all defensible (auth dep correction matching sessions.py shape; quota error signature corrected to match Builder-A's video_repo definition; paranoia 404 fallback in upload route; smart per-session-aware monthly-quota seeding pattern; data_dir tmp env added to api_db fixture for storage layout writes during tests).

**Pre-test gotcha**: pytest failed at first run with `RuntimeError: Form data requires "python-multipart"`. FastAPI hard-requires it for `Form()` and `UploadFile`. Installed in venv to unblock; filed for `pyproject.toml` runtime deps at Commit 7. Architect verified: **30 / 30 passing**. Committed as `c1a6fb3`.

### 2026-04-30 — Mobile state-machine sketch sign-off (pre-Commit 6)

Per the v1.0 plan's "PAUSE — state machine sketch posted for Kerwyn sign-off" gate. Three open questions all accepted as recommended:

- **Q1c**: APP_BACKGROUNDED while uploading → failed(upload_interrupted). Production-grade background upload deferred to Phase 192+.
- **Q2**: failed + RETRY_UPLOAD → uploading (re-POSTs same local file). New RETRY_UPLOAD reducer event distinguishes from TAP_RETRY for non-upload failures.
- **Q3**: RecordingError extends with `upload_failed` + `upload_interrupted` + `quota_exceeded` (with cap discriminator: `'count' | 'size' | 'monthly'`). The cap field MUST disambiguate which quota fired.

### 2026-04-30 — Commit 6 (`c2b912c`) mobile build via Builder-D + verification

Builder-D reported back with: full hook swap from FS-backed to HTTP-backed; consumer surface unchanged per Phase 191's load-bearing handoff contract; Q1c/Q2/Q3 baked into the reducer + UI. Test load-bearing assertion: 10 of 12 it() titles in `__tests__/hooks/useSessionVideos.test.ts` preserved verbatim; 2 reframed for HTTP-equivalent failure modes (mapping table documented in test file's top comment).

**One in-cycle architect fix**: Builder-D wrote `BodyInit` (Web spec) but RN's TS lib uses `BodyInit_`. Surgical 1-char fix; not a Builder error per se — it's an RN-vs-DOM type-name divergence. **293 / 293 mobile Jest tests pass; tsc --noEmit clean.** Committed as `c2b912c`.

### 2026-05-01 — Architect-gate ROUND 1 BLOCKED at Step 1B (`motodiag serve` migration apply + sister timestamp bug)

Backend on schema_version=39 confirmed only after manual `init_db()` call; backend launched with SCHEMA_VERSION=39 in code but `/v1/version` returned schema_version=38 until manual invocation. **Bug**: `motodiag serve` doesn't apply pending migrations at startup — neither serve_cmd nor create_app() called init_db(). Latent since Phase 175.

Plus environment recovery surfaced: `-wipe-data` on the emulator nuked the API key from Keystore. Architect re-provisioned via `motodiag apikey create --name "smoke 191B" --user 1` (note: `--tier shop` flag in the runbook command doesn't exist on `apikey create`; doc fix queued for Commit 7).

### 2026-05-01 — Fix-cycle-1 commit `832579d`

Two backend bugs fixed:

1. **`motodiag serve` runs migrations on startup** (the original Step 1B blocker). Default behavior + audit log line on every launch. Opt-out via `--skip-migrations` for deploy pipelines. 8 regression tests in `test_phase191b_serve_migrations.py`.
2. **`video_repo._month_start_iso` timestamp format normalized** to match SQLite's `datetime('now')` space-format. **NEW failure-family entry on Track I: date-boundary latent** — passed yesterday (2026-04-30) because date prefixes differed; broke today (2026-05-01) when prefixes coincided and the SPACE-vs-T mismatch surfaced at character index 10. 3 video_repo monthly-quota tests flipped green → red → green.

Sister bug in `session_repo._month_start_iso` (same format issue PLUS deeper `datetime.now().isoformat()`-naive-local-time bug in 7 sibling write paths) NOT fixed — would require consolidating all session_repo timestamp writes to UTC. Filed as F10 for Phase 192. Phase 178 quota tests visibly broken today (May 1) because of F10's deeper bug; will start passing again on May 2 when the date prefix differs.

### 2026-05-03 — Architect-gate ROUND 2 BLOCKED at Step 6 (upload happy path) — file:// prefix missing

Recording flow worked; "Use this video" tap fired the new uploading state machine entry; the upload itself failed with "Network request failed" and the request never reached the backend (no POST line in access log). 100% mobile-side failure, sub-construction-stage. Architect's culprit triage hit on culprit 1: react-native-vision-camera v4 returns `VideoFile.path` WITHOUT the `file://` scheme on Android. RN's networking layer requires the scheme for FormData multipart file uploads on Android.

The screen layer (VideoCaptureScreen lines 196 + 325) DOES prefix `file://` for playback URIs — but `useSessionVideos.addRecording` was passing `recording.sourceUri` AS-IS to `FormData.append`. Mobile jest tests passed because `api.POST` was mocked, so the real FormData → fetch path was never exercised. **5th instance of the F9 failure family**: mock-vs-real-fetch.

### 2026-05-03 — Fix-cycle-2 commit `7e9702e` (mobile)

`useSessionVideos.addRecording` now derives `fileUri` with conditional `file://` prefix before FormData append (mirrors VideoCaptureScreen's existing playback-URI logic). F11 (raw error logging in upload catch block before describeError flattens) shipped in same commit. Verification: tsc clean + 293/293 jest green.

### 2026-05-03 — Architect-gate ROUND 3 BLOCKED at Step 5 by tier enforcement (working as designed)

The upload-path fix worked: file:// prefix correctly applied; multipart construction reached the backend; backend returned 403 + 402 because user 1 was on individual tier and the `require_tier('shop')` gate from Commit 3 fired correctly. **NOT a bug — enforcement working as designed per plan v1.0 A2.**

Smoke runbook needed a tier-upgrade step for user 1. Architect proposed three options for the gap; picked option (a) but namespaced under the existing `subscription` group rather than `tier` (which is a top-level command, not a group). Architect also flagged F13 (NEW) — mobile error mapping conflates 402 (quota) and 403 (tier) — and F14 — `motodiag tier` disclaimer was misleading.

### 2026-05-03 — Fix-cycle-3 commit `0babc55`

Two fixes:

1. **`motodiag subscription set --user N --tier T` CLI** added under the existing `subscription` group. Cancels any existing active subscription → inserts new active row with stripe_subscription_id=NULL → confirmation log + DEV/TEST PATH disclaimer. 12 regression tests across 4 classes.
2. **F14: `motodiag tier` disclaimer disambiguation**. New copy: "Enforcement: CLI gating: dev mode (bypassed). HTTP API endpoints: enforced per-endpoint regardless — use `motodiag subscription set --user N --tier T` to stand up an active subscription for API tier gates."

F13 deferred to Phase 192. **Phase 191B suite: 135 passed, 5 skipped after fix-cycle-3.**

### 2026-05-04 — Architect-gate ROUND 4 BLOCKED at Step 7 by hardcoded invalid Vision model string

Three gate-breakers cleared along the way (tier-upgrade gap, tier-gate enforcement, F14 disambiguation). Several smoke steps verified organically: Step 5 (record + upload), Step 6 (uploading state machine + 3 new error kinds), Step 13 (ffmpeg-missing → analysis_failed), Step 14 (Vision-failure → analysis_failed), soft-delete 204, Phase 186-190 fixtures intact.

The new gate-breaker: backend log surfaced `Vision pipeline error for video 3: Vision SDK call failed: Error code: 404 - {'type': 'error', 'error': {'type': 'not_found_error', 'message': 'model: claude-sonnet-4-5-20241022'}, ...}`. **Bug**: `engine/client.py:MODEL_ALIASES['sonnet']` resolved to a fabricated/unreleased model ID. Anthropic's Sonnet 4 family went 4.0 → 4.6 with no 4.5 release. Latent since Phase 79; surfaced by Phase 191B's Commit 2 because that's the first phase to do REAL Anthropic API calls instead of mocked-only test paths.

**6th instance of the F9 failure family.** Plus: 14 hardcoded test references to the bogus ID across 5 files were effectively pinning the bug into place — the tests were ASSERTING the wrong value, masking the bug from pytest visibility.

Plus operational concern: `ANTHROPIC_API_KEY` was leaked four times during this smoke cycle through pasted-in-chat values + screenshot-visible PowerShell `$env:` lines. Filed as F16 for Commit 7 runbook hygiene.

### 2026-05-04 — Fix-cycle-4 commit `c453872`

Three fixes:

1. **`MODEL_ALIASES['sonnet']`**: `claude-sonnet-4-5-20241022` → `claude-sonnet-4-6` per CLAUDE.md system context. **MODEL_PRICING entry replaced** at the same rates ($3/M input, $15/M output). 14 hardcoded test references scrubbed across 5 files.
2. **`MOTODIAG_VISION_MODEL` env var override** added to `vision_analysis_pipeline.py:DEFAULT_VISION_MODEL` per architect's defensive-change ask. Accepts alias OR full ID.
3. **F15 regression guard** in `tests/test_phase191b_vision_model_validation.py` (14 tests across 4 classes). `KNOWN_GOOD_MODEL_IDS` set hardcoded against CLAUDE.md May-2026 system context. `KNOWN_BOGUS_IDS` anti-regression pin specifically against the architect-gate Step 7 ID.

Plus `.gitignore` excludes `data/videos/*` (architect's smoke uploads) while preserving `data/videos/.gitkeep`. **Phase 191B suite: 149 passed, 5 skipped after fix-cycle-4 (135 + 14 from F15).**

### 2026-05-04 — Architect-gate ROUND 5 PASS on 22 / 22 steps

Headline: **full Vision pipeline ran end-to-end against live Anthropic API.** Sonnet 4.6 returned WRONG SUBJECT findings on the test recording (correctly noted it was a CGI living room, not a motorcycle) with structured findings + suggested follow-up. Cost = $0.0354 for 5 frames. `model_used` confirmed as `claude-sonnet-4-6`. Findings expansion renders correctly in mobile, persists across cold-relaunch.

All organic verifications hit during the gate: ffmpeg-missing → analysis_failed, Vision-key-missing → analysis_failed, bogus-model → analysis_failed, tier-gate 403, soft-delete 204, ProblemDetail 404 envelope. Three failed video tiles still on Session #1 as regression artifacts.

**Architect cleared for v1.1 finalize.** Punch list landed in Commit 7 — see "v1.1 finalize" entry below.

### 2026-05-04 — v1.1 finalize (this commit)

- Plan → v1.1: header bumped to `Version: 1.1 | Status: ✅ Complete | Date: 2026-05-04`. ALL Verification Checklist items `[x]` with verification notes from architect-gate. New sections: Bug verification (7 fix-cycle landmarks all closed), Deviations from Plan (8 items), Results table, Key Finding (F9 failure family architectural intervention as Phase 192 lead ticket).
- Phase log → this file (timestamped milestones from plan v1.0 through 4 fix-cycles through round-5 PASS through this finalize).
- Move both files from `docs/phases/in_progress/` → `docs/phases/completed/`.
- Backend `pyproject.toml`: version 0.1.0 → 0.2.0; `python-multipart>=0.0.20` added to `[api]` extras with inline comment explaining the FastAPI Form/UploadFile requirement. (Plan v1.0.1's Correction 1 was wrong about anthropic — it's in `[ai]` extras, not `[project].dependencies`. Documented as Deviation #1.)
- Backend `implementation.md` version bump 0.13.7 → 0.13.8; Phase 191B row added to Phase History above Phase 191 (reverse-chronological position for Track I).
- Backend `phase_log.md` Phase 191B closure entry.
- Backend `docs/ROADMAP.md` Phase 191B marked ✅.
- `tests/fixtures/videos/sample_3sec.mp4` generated (3-second 320×240 lavfi testsrc + 440Hz sine audio); 5 previously-gated TestRealFFmpeg tests un-skipped; **20/20 ffmpeg tests now pass with zero skips**.
- `_parse_probe_stderr` width/height regex tightened against ffmpeg 8.1's stream line shape (was matching the AVC1 codec tag's hex literal `0x31637661` before reaching the actual `320x240` resolution; fix anchors WxH to comma-space prefix + constrains both dimensions to 1-5 digits). Inline comment documents the ffmpeg-version-drift cause.
- Mobile `package.json` 0.0.6 → 0.0.7.
- Mobile `implementation.md` 0.0.8 → 0.0.9; Package Inventory + Phase History updated.
- Mobile `docs/FOLLOWUPS.md`: F11/F14/F15 marked closed (with commit hashes); F10/F12/F13/F16/F18 added to Open list; F1 stays in Closed section as a record; Issue 1 + Phase 191 fixture loss + doc fix added.
- Mobile `README.md`: runbook gains `motodiag subscription set --user 1 --tier shop` step + F16 hygiene paragraph + dropped the bogus `--tier shop` flag from the `motodiag apikey create` example.
- Rebase-merge `phase-191B-video-upload-ai-analysis` → `master` on backend (7 + Commit 7 = 8 commits, fast-forward).
- Rebase-merge `phase-191B-video-upload-ai-analysis` → `main` on mobile (2 + Commit 7 = 3 commits, fast-forward).
- Delete feature branches local; remotes were never pushed per Phase 188+ precedent — local-only deletion is sufficient.

**Phase 191B closes green. Track I scorecard: 8 of 21 phases complete (185 / 186 / 187 / 188 / 189 / 190 / 191 / 191B).** Next: **Phase 192 — Diagnostic report viewer** per ROADMAP, with the Phase 192 lead ticket being the F9-failure-family architectural intervention (contributing.md doc + lint rule for mock-vs-runtime drift at the test-author level) per architect's PASS-handoff observation that the pattern is now robust enough to merit dedicated mitigation infrastructure.
