# Phase 191B — Phase Log

**Status:** 🚧 In Progress | **Started:** 2026-04-29
**Repo:** https://github.com/Kubanjaze/moto-diag (backend) + https://github.com/Kubanjaze/moto-diag-mobile (mobile hook swap in Commit 6)
**Branch:** `phase-191B-video-upload-ai-analysis` (will be created in BOTH repos at Commit 1; backend gets Commits 1-5, 7; mobile gets Commit 6, 7)

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
