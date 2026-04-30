# Phase 191B — Video Diagnostic Upload + Claude Vision AI Analysis Pipeline

**Version:** 1.0.1 | **Tier:** Standard | **Date:** 2026-04-30 (v1.0 written 2026-04-29; v1.0.1 corrects pre-Commit-1 path/scope drift after deeper codebase audit)

## Plan v1.0.1 — pre-Commit-1 corrections from codebase audit

Plan v1.0 was written from architect intent rather than a careful audit of `src/motodiag/`. After reading the actual code structure pre-build, five corrections land here. None change the goal (video upload + AI analysis); they realign the file paths, scope framing, and dependency claims with what's already shipped.

**Why a v1.0.1 amendment instead of capturing as deviations at v1.1 finalize:** corrections this large should land on the plan-of-record before the Builder agents are dispatched, otherwise the Builders will work from the inaccurate plan + the deviations multiply. Single load-bearing assertion (the `useSessionVideos.test.ts` Phase 191 handoff guarantee) stays unchanged.

### Correction 1 — `anthropic` is already a required dep

Plan v1.0 said: "Add `anthropic` to required deps (was optional pre-Phase-191B since 100-103 were standalone)."

Actual: `anthropic >= 0.40` is in [`pyproject.toml`](../../../pyproject.toml) line 32 as a required dep — has been since Phase 79 (the Claude API series, NOT 100-103). Plan v1.0's pyproject.toml change is **drop the "anthropic" line item from the diff** at Commit 7. Backend venv has `anthropic 0.96.0` installed. No-op.

### Correction 2 — Storage paths

Plan v1.0 used a `src/motodiag/storage/...` layout that doesn't exist. Backend uses [`src/motodiag/core/`](../../../src/motodiag/core/) (single-package, function-based repos, module-flat models).

| Plan v1.0 said | v1.0.1 corrected |
|---|---|
| `src/motodiag/storage/database.py` (SCHEMA_VERSION 38→39) | [`src/motodiag/core/database.py`](../../../src/motodiag/core/database.py) line 11 — SCHEMA_VERSION constant |
| `src/motodiag/storage/migrations/039_videos.py` (new file per migration) | APPEND `Migration(version=39, ...)` entry to [`src/motodiag/core/migrations.py`](../../../src/motodiag/core/migrations.py) `MIGRATIONS` list (single file pattern; latest entry is version=38 at line 2731) |
| `src/motodiag/storage/models/video.py` | EXTEND [`src/motodiag/core/models.py`](../../../src/motodiag/core/models.py) (module-flat — `VehicleBase` + `DiagnosticSessionBase` already cohabit; new `VideoBase` + `VideoCreate` + `VideoResponse` join them) |
| `src/motodiag/storage/repositories/video_repo.py` | NEW file `src/motodiag/core/video_repo.py` mirroring [`src/motodiag/core/session_repo.py`](../../../src/motodiag/core/session_repo.py) — function-based (`create_video`, `get_video`, `list_session_videos`, `soft_delete_video`, `update_analysis_state`, `set_analysis_findings`) + `_for_owner` variants for tier/auth-aware CRUD |

### Correction 3 — `motodiag.ai` package does NOT exist and shouldn't be created

Plan v1.0 specified `src/motodiag/ai/video_analysis.py` + `src/motodiag/ai/analysis_worker.py`. The right home for this work is [`src/motodiag/media/`](../../../src/motodiag/media/) (Track C2 — Media Diagnostic Intelligence, Phases 96-108). Existing siblings: `vision_analysis.py`, `video_frames.py`, `audio_capture.py`, `spectrogram.py`, `sound_signatures.py`, `photo_annotation.py` + 7 others. New Phase 191B modules belong as siblings:
- `src/motodiag/media/ffmpeg.py` (NEW) — real ffmpeg subprocess wrapper
- `src/motodiag/media/video_analysis_pipeline.py` (NEW) — orchestrates ffmpeg → real Vision call → findings persistence
- `src/motodiag/media/analysis_worker.py` (NEW) — `BackgroundTasks` entry point that drives the pipeline

`motodiag.ai` is dropped. Test file paths follow: `tests/test_phase191b_ffmpeg.py` ✓ unchanged, `tests/test_phase191b_video_analysis.py` → renamed `tests/test_phase191b_video_analysis_pipeline.py`, `tests/test_phase191b_video_repo.py` ✓ unchanged.

### Correction 4 — `media/video_frames.py` (Phase 100) is metadata-only

Plan v1.0 framed Phase 191B as "first production wiring of Claude Vision + ffmpeg into the HTTP layer" with the implication that Phase 100/101 were standalone scripts. Reading [`media/video_frames.py`](../../../src/motodiag/media/video_frames.py):

> "Phase 100: Simulated video frame extraction — models video metadata, generates frame extraction plans based on intervals or keyframe detection, and returns structured frame objects with placeholder descriptions. **No actual video processing occurs**; this module operates on metadata models to define the extraction contract that a real video backend would fulfill."

Phase 100 ships **types + the contract**: `VideoFormat` enum, `VideoResolution`, `VideoMetadata`, `VideoFrame` (with placeholder description + tags), `FrameExtractionConfig`, `SceneChangeMarker`, `VideoFrameExtractor` class with `extract_frames` / `extract_keyframes` / `get_frame_at_timestamp` / `get_extraction_plan` (all simulation-only).

Phase 191B's role: **build the real ffmpeg backend that fulfills the contract.** Concretely:
- `media/ffmpeg.py` defines `RealVideoFrameExtractor(FrameExtractionConfig)` that subclasses or composes the existing `VideoFrameExtractor` and overrides the `_generate_placeholder_*` calls with real frame extraction. Returns the same `VideoFrame` shape — type-stable.
- `VideoFrame.description` + `VideoFrame.tags` populate from the Vision pipeline (Correction 5), not from `_generate_placeholder_description`.
- The metadata-only `VideoMetadata` Pydantic model is REUSED unchanged for sidecar JSON parsing on upload.

**Type reuse > redefinition.** Phase 191B's plan-v1.0 `VideoAnalysisFindings` model with its own `VisualFinding` is dropped — see Correction 5.

### Correction 5 — `media/vision_analysis.py` (Phase 101) is text-only with the right schema

Plan v1.0 said Phase 101 is "a Claude Vision wrapper, mocked in tests." Half-true: [`media/vision_analysis.py`](../../../src/motodiag/media/vision_analysis.py)'s `VisualAnalyzer.analyze_image` takes `image_description: str` (text-only — NOT image bytes) and calls `DiagnosticClient.ask()`. The Pydantic schema is DONE and CORRECT for Phase 191B's needs:

| Plan v1.0 (drop) | Phase 101 (reuse) |
|---|---|
| `class VisualFinding(BaseModel)` with `category: Literal[...]` 8-value | [`FindingType`](../../../src/motodiag/media/vision_analysis.py) enum (8 values: SMOKE / LEAK / DAMAGE / GAUGE_READING / WEAR / CORROSION / MISSING_PART / MODIFICATION) — plus `VisualFinding` model with `finding_type` + `description` + `confidence` + `location_in_image` + `severity` |
| Plan-v1.0 `VideoAnalysisFindings` (`summary` + `findings` + `no_findings_reason` + `frames_analyzed` + `model_used` + `cost_estimate_usd`) | [`VisualAnalysisResult`](../../../src/motodiag/media/vision_analysis.py) (`findings` + `overall_assessment` + `suggested_diagnostics` + `image_quality_note`) — close shape; v1.0.1 ADDS `frames_analyzed: int` + `model_used: str` + `cost_estimate_usd: float` to `VisualAnalysisResult` (3-field non-breaking extension) rather than redefining the whole model |
| Plan-v1.0 `VehicleContext` | [`VehicleContext`](../../../src/motodiag/media/vision_analysis.py) — already exists with `make` + `model` + `year` + `mileage` + `reported_symptoms` + `to_context_string()` — REUSE unchanged |

Phase 191B Commit 2's NEW work in `media/vision_analysis_pipeline.py`:
- `VisionAnalyzer.analyze_video_frames(frames: list[Path], vehicle_context: VehicleContext, model="sonnet") -> VisualAnalysisResult` — takes real image file paths, base64-encodes them as content blocks, calls extended `DiagnosticClient.ask_with_images()`, parses tool-use response into `VisualAnalysisResult`. Reuses `VISION_ANALYSIS_PROMPT` + `SMOKE_COLOR_GUIDE` + `FLUID_COLOR_GUIDE` constants from Phase 101 unchanged.
- The existing text-only `VisualAnalyzer.analyze_image` from Phase 101 is left in place — it's used by other Track C2 code paths and shouldn't break.

### Correction 6 (sub-correction) — `DiagnosticClient` extension instead of new VisionClient

Plan v1.0 implied a brand-new Anthropic-SDK call inside `media/vision_analysis_pipeline.py`. Cleaner: extend [`engine/client.py:DiagnosticClient`](../../../src/motodiag/engine/client.py) with a new `ask_with_images(prompt, images: list[Path], system, model, max_tokens, temperature, tools, tool_choice) -> tuple[Message, TokenUsage]` method that:
- builds the multi-content-block messages payload (image blocks via base64 + the text prompt)
- threads through the existing cost-pricing table + cache + token-usage tracking + session-metric accounting
- returns the raw `Message` (not text) so callers can inspect `tool_use` blocks for structured output

Tool-use structured output stays per plan v1.0's design — `tools=[...]` + `tool_choice={"type":"tool","name":"report_video_findings"}`. The `report_video_findings` tool's `input_schema` = `VisualAnalysisResult.model_json_schema()` (the Phase 101 model — nothing redefined).

### Updated Outputs section

Backend new files now (10 instead of 12):
- ~~`src/motodiag/storage/migrations/039_videos.py`~~ → APPEND to `core/migrations.py` MIGRATIONS list
- ~~`src/motodiag/storage/models/video.py`~~ → EXTEND `core/models.py` with `VideoBase` + `VideoCreate` + `VideoResponse`
- `src/motodiag/core/video_repo.py` ✓ NEW (mirrors `session_repo.py`)
- `src/motodiag/api/routes/videos.py` ✓ NEW
- `src/motodiag/media/ffmpeg.py` ✓ NEW
- ~~`src/motodiag/ai/video_analysis.py`~~ → `src/motodiag/media/vision_analysis_pipeline.py`
- ~~`src/motodiag/ai/analysis_worker.py`~~ → `src/motodiag/media/analysis_worker.py`
- ~~`src/motodiag/media/__init__.py`~~ — already exists with Track C2 modules; do not overwrite
- `data/videos/.gitkeep` ✓ NEW
- `tests/fixtures/videos/sample_3sec.mp4` + `tests/fixtures/videos/README.md` (regen instructions for ffmpeg-less environments)
- `tests/fixtures/anthropic_responses/video_analysis_*.json` + `_regen.py`

Backend modified files (5 instead of 5, content shifts):
- `src/motodiag/api/app.py` — register `videos_router` (unchanged)
- `src/motodiag/core/database.py` — `SCHEMA_VERSION = 38 → 39` (path correction, mechanism same)
- `src/motodiag/core/migrations.py` — APPEND Migration(version=39, ...) (NEW — was a separate file in plan v1.0)
- `src/motodiag/core/models.py` — APPEND `VideoBase` + `VideoCreate` + `VideoResponse` (NEW — was a separate file in plan v1.0)
- `src/motodiag/engine/client.py` — extend `DiagnosticClient` with `ask_with_images()` (NEW — wasn't in plan v1.0; required for real Vision calls)
- `src/motodiag/media/vision_analysis.py` — extend `VisualAnalysisResult` with `frames_analyzed` + `model_used` + `cost_estimate_usd` (3 non-breaking optional fields — NEW)
- `src/motodiag/api/openapi.py` — add `videos` tag + multipart shape (unchanged)
- `src/motodiag/api/errors.py` — add 413 mapping (unchanged)
- `pyproject.toml` — version 0.1.0 → 0.2.0 ONLY (anthropic line stays as-is — already required, see Correction 1)

### Updated Test Files

Three test files (renamed to align with corrected paths):
- `tests/test_phase191b_migration_039.py` ✓ unchanged
- `tests/test_phase191b_video_repo.py` ✓ unchanged
- `tests/test_phase191b_ffmpeg.py` ✓ unchanged
- ~~`tests/test_phase191b_video_analysis.py`~~ → `tests/test_phase191b_video_analysis_pipeline.py` (renamed; uses recorded Anthropic fixtures + extends `VisualAnalysisResult` test coverage)
- `tests/test_phase191b_videos_api.py` ✓ unchanged
- (NEW) `tests/test_phase191b_diagnostic_client_images.py` — guards `DiagnosticClient.ask_with_images()` extension; ~6-8 tests for image content block construction + base64 encoding + tool-use response parsing.

### Updated Risks

The "first production wiring of Claude Vision + ffmpeg" framing remains accurate — Phase 100 ships types/contract only; Phase 101 ships text-only mock; Phase 191B ships real image-bytes Vision API calls + real ffmpeg. The cost surprise risk + Anthropic rate limit risk + multipart upload behavior in openapi-fetch + concurrent same-file upload race + hook surface drift risks all stand unchanged.

NEW risk added in v1.0.1: **`DiagnosticClient.ask_with_images()` extension may surface a latent bug in the existing text-only path** (cache key derivation now needs to include image hashes; cost calculation still uses standard input/output token pricing — Anthropic's image tokens are billed at the same rate as text input tokens per current pricing). Mitigation: regression-guard test asserting existing `ask()` calls produce identical cost + cache key as before the extension.

### Updated Commit Plan

Commit numbering unchanged (1-7). Commit content shifts:
- **Commit 1** now also touches `engine/client.py` to add `ask_with_images()` (since Commit 2's vision pipeline depends on it). Commit 1 expands to: migration v39 entry + `core/models.py` extension + `core/video_repo.py` NEW + `media/ffmpeg.py` NEW + `engine/client.py` extension. ~30 unit tests across 4 test files (migration + repo + ffmpeg + diagnostic_client_images).
- **Commit 2** unchanged in scope but file paths corrected (was `ai/video_analysis.py`, now `media/vision_analysis_pipeline.py`). ~15 tests.
- **Commits 3-5** unchanged.
- **Commit 6** (mobile hook swap) unchanged — load-bearing useSessionVideos.test.ts assertion preserved.
- **Commit 7** (finalize) unchanged.

---

(End of v1.0.1 corrections. Original v1.0 plan continues below — paths and module names within the original sections remain stale and are superseded by the corrections above. Re-reading the original Outputs / Logic / etc. sections is OK as long as the v1.0.1 corrections override path-level details.)

---

## Goal

Backend feature continuation that consumes Phase 191's mobile capture substrate. Mechanic records a video on the phone (Phase 191 substrate); video uploads to backend (NEW); ffmpeg extracts key frames + audio sidecar (NEW); Claude Vision analyzes the frame batch + returns structured findings (NEW); mobile renders the findings in the existing VideosCard surface without changing its consumer contract (Phase 191 handoff).

This is the substrate-then-feature pair completion. Phase 191 = capture substrate; Phase 191B = backend pipeline + AI analysis = the feature that justifies the substrate's existence.

**First production wiring of Claude Vision + ffmpeg into the HTTP layer on Track I.** Phase 100-103 (the Claude API learning series — structured outputs / batches / vision / tool use) shipped as standalone scripts. Phase 191B is where those modules earn their keep inside the production API surface.

CLI — none new (mobile-driven feature).

## Scope decisions locked at pre-plan Q&A (2026-04-29)

All A1-D2 sign-offs from the pre-plan question set are baked into this plan. Two confirmations updated the original recommendations:

- **A1 — endpoint shape switched from top-level to fully nested.** Audit of `src/motodiag/api/routes/` confirmed every session sub-resource (symptoms / fault-codes / notes / close / reopen) is nested under `/v1/sessions/{id}/...` with no flat alternative. Videos fit cleanly into that pattern; the original A1's "/v1/videos/" had a REST-best-practice bias that doesn't match the codebase.
- **C2 — backend integration test coverage made explicit.** Dedicated test-coverage section in this plan (see "Backend integration test coverage" below) enumerates every contract that must pass before the architect gate fires. Single load-bearing assertion: mobile's existing Phase 191 `__tests__/hooks/useSessionVideos.test.ts` continues passing unchanged after the hook implementation swaps from FS-backed to HTTP-backed in Commit 6.

## Outputs

### New backend files (~12)

- `src/motodiag/storage/migrations/039_videos.py` — migration v38 → v39: new `videos` table + cascade-delete from `sessions`. Schema below.
- `src/motodiag/storage/models/video.py` — SQLAlchemy `Video` model + Pydantic `VideoCreate` / `VideoResponse` / `VideoAnalysisFindings` (the structured-output schema Claude Vision returns into).
- `src/motodiag/storage/repositories/video_repo.py` — `create_video` / `list_session_videos` / `get_video` / `soft_delete_video` / `update_analysis_state` / `set_analysis_findings` / per-session quota check + per-tier monthly aggregate quota check.
- `src/motodiag/api/routes/videos.py` — new router nested under sessions: `POST /v1/sessions/{id}/videos` + `GET /v1/sessions/{id}/videos` + `GET /v1/sessions/{id}/videos/{video_id}` + `DELETE /v1/sessions/{id}/videos/{video_id}` + `GET /v1/sessions/{id}/videos/{video_id}/file`.
- `src/motodiag/media/ffmpeg.py` — subprocess wrapper around ffmpeg binary. Functions: `extract_frames(video_path, sample_policy)` returning `list[Path]`; `extract_audio(video_path)` returning `Path` (mp3 sidecar); `validate_video(video_path)` for codec/duration sanity. Detects ffmpeg at module load (logs path); raises `FFmpegMissing` + responds 503 on the upload endpoint if absent.
- `src/motodiag/media/__init__.py` — package marker.
- `src/motodiag/ai/video_analysis.py` — Claude Vision wrapper. Builds the multi-image Messages API call from extracted frames + a structured-output prompt + JSON-schema-as-tool-use trick. Returns `VideoAnalysisFindings`. Handles cost-tier model selection (Sonnet 4.6 default; Haiku 4.5 if config flag set).
- `src/motodiag/ai/analysis_worker.py` — synchronous-but-out-of-request analysis dispatcher. POST upload returns immediately with `analysis_state='pending'`; the worker is invoked via `BackgroundTasks` (FastAPI native) for Phase 191B. Future: real worker queue (Track J — Phase 207).
- `src/motodiag/api/routes/videos.py` (already listed above; called out for emphasis since it depends on `media/` + `ai/` modules).
- `data/videos/.gitkeep` — directory for uploaded video file storage.

### New tests (5 files, ~70-80 tests)

- `tests/test_phase191b_migration_039.py` — schema migration up + down tests; cascade delete verification; column shapes match Phase 191 mobile contract.
- `tests/test_phase191b_video_repo.py` — repository CRUD + soft-delete + quota math (per-session count + per-session bytes + per-tier monthly aggregate).
- `tests/test_phase191b_ffmpeg.py` — ffmpeg subprocess wrapper tests using a tiny known-good test mp4 fixture (committed at `tests/fixtures/videos/sample_3sec.mp4`, ~50 KB synthetic clip generated by `ffmpeg -f lavfi -i testsrc=duration=3 -c:v libx264 sample.mp4`). Frame extraction count + audio extraction format + validate_video sanity.
- `tests/test_phase191b_video_analysis.py` — Claude Vision wrapper tests with the **Anthropic SDK mocked using a fixture pulled from a real API response shape** (per Phase 190 Bug 2 lesson). Recorded fixture: `tests/fixtures/anthropic_responses/video_analysis_*.json`. Tests cover: happy-path findings extraction, structured output schema validation, retry-on-rate-limit, fallback to `analysis_state='analysis_failed'` on persistent error, cost-tier model selection.
- `tests/test_phase191b_videos_api.py` — full endpoint contract tests. ~30 tests covering: ProblemDetail envelope on 404/422/413/500, X-API-Key propagation across all 5 endpoints, multipart Content-Type preservation on upload, `require_tier('shop')` enforcement on POST + `require_api_key` on GET/DELETE, per-session count + size cap enforcement, monthly aggregate quota by tier (individual=0 → 402; shop=200/mo → 402 at 201st upload; company=unlimited), soft-delete semantics (list excludes deleted; GET on deleted returns 404 with ProblemDetail), file-stream Content-Type + Content-Length headers, end-to-end happy path (upload → BackgroundTasks fires → analysis_state advances pending → analyzing → analyzed → findings populated), failure paths (ffmpeg missing → 503; ffmpeg fails → analysis_state='unsupported'; Anthropic call fails → analysis_state='analysis_failed').

### Modified backend files (~5)

- `src/motodiag/api/app.py` — register `videos_router` with the `/v1` prefix (matches existing pattern). Add `from motodiag.api.routes.videos import router as videos_router` at top.
- `src/motodiag/storage/database.py` — `SCHEMA_VERSION = 38 → 39`.
- `src/motodiag/api/openapi.py` — extend OpenAPI spec metadata: new `videos` tag + the multipart/form-data request body shape for upload + the binary response media type for the file-stream endpoint. (FastAPI auto-derives most of this from route signatures; this file curates the human-readable summaries.)
- `src/motodiag/api/errors.py` — add 413 Payload Too Large to the auto-mapped exceptions table for video upload size cap.
- `pyproject.toml` — `version = "0.1.0" → "0.2.0"` (Track I major-feature bump because Phase 191B is the first production wiring of Claude Vision into the API; no code-shape break, just signal). Add `anthropic` to required deps (was optional pre-Phase-191B since 100-103 were standalone). NO new ffmpeg-Python wrapper dep — subprocess only (per B2 sign-off).

### New mobile files (~3)

- `src/types/videoAnalysis.ts` — `VideoAnalysisFindings` Pydantic→TypeScript translation (auto-regenerated from refreshed openapi.json). Manual shim if openapi-typescript can't infer the structured-output shape from the OpenAPI 3.1 spec correctly (defensive — most likely auto-derives clean).

### Modified mobile files (~6)

- `api-schema/openapi.json` — refreshed snapshot from running backend (single `npm run refresh-api-schema` at Commit 6).
- `src/api-types.ts` — regenerated from refreshed openapi.json (single `npm run generate-api-types` after the schema refresh).
- `src/hooks/useSessionVideos.ts` — **the hook swap** (Commit 6). Implementation goes from `videoStorage` calls to `api.POST /v1/sessions/{id}/videos` (multipart) + `api.GET /v1/sessions/{id}/videos` (list) + `api.DELETE /v1/sessions/{id}/videos/{vid}`. Hook contract surface (`{videos, addRecording, deleteVideo, refresh, atCap, capReason, isLoading, error}`) UNCHANGED — Phase 191's load-bearing handoff guarantee. The 4 backend-side `SessionVideo` fields stubbed `null` in Phase 191 (`remoteUrl`, `uploadState`, `analysisState`, plus the new `analysisFindings`) populate from the new endpoints.
- `src/screens/SessionDetailScreen.tsx` — VideosCard's VideoRow grows a 5-state mini-badge for `analysisState` (`pending` "🔄 Analyzing soon" / `analyzing` "🔍 Analyzing now" / `analyzed` "✓ Analyzed" tappable to expand findings / `analysis_failed` "⚠ Analysis failed" / `unsupported` "—" muted) + tappable findings expansion that pushes a new VideoAnalysisFindings inline view.
- `src/screens/VideoCaptureScreen.tsx` — save flow gains an upload-progress indicator (multipart upload may take several seconds on shop wifi). The state machine adds a new `uploading` transient state between `saved` and `idle`. **State-machine sketch posted for sign-off pre-Commit 6** — same Phase 191 / Phase 189 discipline.
- `src/services/videoStorage.ts` — DELETED. The hook swap removes the only consumer; deleting the service surfaces any forgotten caller via tsc errors. Replacement: `videoStorageCache.ts` (thin wrapper retaining only the local-cache path lookups for playback per C1 — Phase 191 keeps the local file as cache after upload finishes).

### Modified mobile tests

- `__tests__/hooks/useSessionVideos.test.ts` — **continues passing unchanged.** This is the load-bearing assertion. Test file's mock layer changes (mocks `api.POST` instead of `saveRecording`); the test bodies asserting hook surface DO NOT change. If they need to change, the hook contract has drifted and Phase 191's handoff guarantee is broken.
- `__tests__/services/videoStorage.test.ts` — DELETED with the service file.
- `__tests__/services/videoStorageCache.test.ts` — NEW, ~5-8 tests for the cache-only wrapper.
- `__tests__/screens/videoCaptureMachine.test.ts` — extended with `uploading` state transitions (~6 new tests).

## Logic

### Endpoint shapes (fully nested per A1 confirmation)

```
POST   /v1/sessions/{session_id}/videos
       multipart/form-data:
         file:     <mp4 binary>
         metadata: <JSON sidecar mirroring Phase 191's SessionVideo
                   minus the 4 backend-side fields stubbed null>
       Auth:     require_tier('shop')
       Caps:     per-session count (10) + per-session bytes (1 GB) +
                 per-tier monthly aggregate (200/mo for shop;
                 unlimited for company; 0 for individual which means
                 the require_tier gate already 403'd).
       Returns:  VideoResponse with upload_state='uploaded' +
                 analysis_state='pending'. Triggers BackgroundTask
                 analyze_video(video_id).

GET    /v1/sessions/{session_id}/videos
       Auth:     require_api_key
       Returns:  list[VideoResponse] sorted newest-first; soft-deleted
                 rows excluded.

GET    /v1/sessions/{session_id}/videos/{video_id}
       Auth:     require_api_key
       Returns:  VideoResponse with analysis_state + analysis_findings
                 reflecting current state (mobile polls every 5s while
                 analysis_state in {'pending','analyzing'}).
       404:      ProblemDetail when video_id doesn't exist OR is soft-
                 deleted OR doesn't belong to session_id.

DELETE /v1/sessions/{session_id}/videos/{video_id}
       Auth:     require_api_key
       Effect:   soft-delete via deleted_at = now(); file unlink
                 deferred to a future cleanup job (Phase 198 territory).
       Returns:  204.

GET    /v1/sessions/{session_id}/videos/{video_id}/file
       Auth:     require_api_key
       Returns:  binary mp4 stream with Content-Type: video/mp4 +
                 Content-Length + Accept-Ranges: bytes (for seekable
                 playback if mobile ever needs remote-only playback;
                 Phase 191B mobile uses local cache per C1).
```

### Database schema (migration v39)

```sql
CREATE TABLE videos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    -- Mobile-supplied (Phase 191 sidecar JSON):
    started_at TEXT NOT NULL,        -- ISO 8601
    duration_ms INTEGER NOT NULL,
    width INTEGER NOT NULL,
    height INTEGER NOT NULL,
    file_size_bytes INTEGER NOT NULL,
    format TEXT NOT NULL DEFAULT 'mp4',
    codec TEXT NOT NULL DEFAULT 'h264',
    interrupted INTEGER NOT NULL DEFAULT 0,
    -- Backend-managed:
    file_path TEXT NOT NULL,         -- canonical disk path
    sha256 TEXT NOT NULL,            -- content hash for dedup + integrity
    upload_state TEXT NOT NULL DEFAULT 'uploaded',  -- only 'uploaded' for now; reserved
    analysis_state TEXT NOT NULL DEFAULT 'pending', -- pending|analyzing|analyzed|analysis_failed|unsupported
    analysis_findings TEXT,          -- JSON serialized VideoAnalysisFindings; NULL until analyzed
    analyzed_at TEXT,                -- ISO 8601 when analysis_state advanced past 'analyzing'
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    deleted_at TEXT,                 -- soft-delete; NULL = live
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
);

CREATE INDEX idx_videos_session ON videos(session_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_videos_analysis_state ON videos(analysis_state)
    WHERE analysis_state IN ('pending', 'analyzing');  -- worker-poll efficiency
CREATE INDEX idx_videos_sha256 ON videos(sha256);     -- dedup lookup
```

`ON DELETE CASCADE` from sessions: when a session row is deleted (Phase 192+ session-delete endpoint, or admin-side cleanup), all attached videos are removed. Mobile's `cleanupOrphanedVideos` from Phase 191 stays in place for the local-cache-side equivalent (no dependency change).

### Storage layout

```
{config.data_dir}/videos/
└── shop_{shop_id}/
    └── session_{session_id}/
        └── {video_id}.mp4
        └── {video_id}.frames/
            └── frame_001.jpg
            └── frame_002.jpg
            └── ... (capped at 60)
        └── {video_id}.audio.mp3
```

Frame + audio extracts kept on disk for: (a) re-analysis if the AI prompt evolves (Track G); (b) mechanic-side download of evidence packets for warranty claims (Phase 192 share-sheet integration). Disk overhead ~10-20 MB per video; cleanup script is a Phase 198 concern.

### ffmpeg pipeline

Per B2 sign-off: subprocess wrapper, no Python library.

```python
# Module-load detection
FFMPEG_BIN = shutil.which("ffmpeg")
if FFMPEG_BIN is None:
    log.warning("ffmpeg not found on PATH; video analysis will return 503")

class FFmpegMissing(RuntimeError): ...
class FFmpegFailed(RuntimeError):
    def __init__(self, stderr: str): self.stderr = stderr

def extract_frames(video_path: Path, *, output_dir: Path,
                   policy: SamplePolicy = DEFAULT_POLICY) -> list[Path]:
    """Per B3: 2 fps for first 30s, 1 fps after, cap 60 frames."""
    if FFMPEG_BIN is None: raise FFmpegMissing()
    # ffmpeg -i video.mp4 -vf "select='lt(t,30)*not(mod(n,15))+gte(t,30)*not(mod(n,30))'"
    #        -vframes 60 -vsync vfr output_dir/frame_%03d.jpg
    cmd = [FFMPEG_BIN, "-y", "-i", str(video_path),
           "-vf", FRAME_FILTER, "-vframes", str(MAX_FRAMES),
           "-vsync", "vfr", str(output_dir / "frame_%03d.jpg")]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if proc.returncode != 0: raise FFmpegFailed(proc.stderr)
    return sorted(output_dir.glob("frame_*.jpg"))

def extract_audio(video_path: Path, *, output_path: Path) -> Path:
    """Per B4: mp3 mono 44.1kHz sidecar; defer audio analysis to Track G."""
    cmd = [FFMPEG_BIN, "-y", "-i", str(video_path), "-vn",
           "-ac", "1", "-ar", "44100", "-b:a", "128k",
           str(output_path)]
    # ... same pattern
```

`subprocess.run` with `timeout=120` (2 min cap; well over the 30s expected runtime for typical 30s-2min clips). On timeout: raise `FFmpegFailed("timeout after 120s")`.

### Claude Vision call shape

Per B5 sign-off: single multi-image batch per video. Default Sonnet 4.6; tier-aware Haiku fallback for individual tier (defensive — `require_tier('shop')` already 403s, but the cost-control margin matters if we ever loosen the gate).

```python
def analyze_video_frames(frames: list[Path], *,
                         model: str = "claude-sonnet-4-6",
                         vehicle_context: VehicleContext) -> VideoAnalysisFindings:
    image_blocks = [
        {"type": "image",
         "source": {"type": "base64",
                    "media_type": "image/jpeg",
                    "data": base64.b64encode(p.read_bytes()).decode()}}
        for p in frames
    ]

    # Tool-use trick for structured output: define a tool the model
    # MUST call with the findings; assistant turn = tool_use with
    # the findings as input. Same pattern as Phase 03 + Phase 22.
    tools = [{
        "name": "report_video_findings",
        "description": "Report structured findings extracted from "
                       "the video frames of a motorcycle diagnostic capture.",
        "input_schema": VideoAnalysisFindings.model_json_schema(),
    }]

    response = client.messages.create(
        model=model,
        max_tokens=4096,
        tools=tools,
        tool_choice={"type": "tool", "name": "report_video_findings"},
        messages=[{
            "role": "user",
            "content": image_blocks + [
                {"type": "text",
                 "text": build_diagnostic_prompt(vehicle_context, len(frames))}
            ]
        }]
    )

    # Extract the tool_use block's input as the structured findings
    tool_use_block = next(b for b in response.content if b.type == "tool_use")
    return VideoAnalysisFindings.model_validate(tool_use_block.input)
```

`VideoAnalysisFindings` Pydantic schema (closed enums where possible):

```python
class VisualFinding(BaseModel):
    category: Literal["smoke", "leak", "corrosion", "damage",
                      "loose_fastener", "wear", "wiring", "other"]
    severity: Literal["info", "low", "medium", "high", "critical"]
    location: str  # free-text location on bike ("right downtube near header")
    description: str  # 1-2 sentences observed
    confidence: float  # 0.0-1.0

class VideoAnalysisFindings(BaseModel):
    summary: str  # 2-4 sentence overall summary
    findings: list[VisualFinding]
    no_findings_reason: Optional[str] = None  # populated when findings == []
    frames_analyzed: int
    model_used: str
    cost_estimate_usd: float
```

### Analysis state machine (backend-side)

5 states: `pending → analyzing → analyzed | analysis_failed | unsupported`.

```
pending      ──worker-picks-up──▶ analyzing
analyzing    ──findings-saved──▶  analyzed
analyzing    ──ffmpeg-failed──▶   unsupported
analyzing    ──anthropic-failed──▶ analysis_failed (after 2 retries)
analysis_failed ──admin-retry──▶  pending  (Phase 192+ admin endpoint)
```

`unsupported` is terminal — file is genuinely un-analyzable. `analysis_failed` is retryable (Phase 192+).

### Background task wiring

POST `/v1/sessions/{id}/videos` returns 201 immediately with `analysis_state='pending'`. Inside the route:

```python
@router.post("/{session_id}/videos", ...)
async def upload_video(..., background_tasks: BackgroundTasks):
    # ... validate, save file, write DB row with analysis_state='pending'
    background_tasks.add_task(run_analysis_pipeline, video_id)
    return VideoResponse.model_validate(video_row)

def run_analysis_pipeline(video_id: int) -> None:
    # Synchronous, runs after response sent. FastAPI's BackgroundTasks
    # is in-process; multi-worker setups need Track J's worker queue.
    # For Phase 191B: single-uvicorn-worker is fine; Phase 207 will swap
    # this to redis-rq + workers.
    ...
```

Mobile polls `GET /v1/sessions/{id}/videos/{video_id}` every 5s while `analysis_state in {'pending','analyzing'}`. Stops polling when terminal state reached. Phase 191B keeps polling client-side (no SSE/WebSocket — one of those's worth a future ADR).

### Mobile hook swap (the load-bearing change)

Phase 191's `useSessionVideos` returns `{videos, addRecording, deleteVideo, refresh, atCap, capReason, isLoading, error}`. Phase 191B keeps **the exact same shape** but reimplements:

```ts
// Phase 191 (FS-backed):
const handleAdd = useCallback(async (recording: NewRecording) => {
  const saved = await saveRecording(recording);  // RNFS move + sidecar write
  setVideos((prev) => [saved, ...prev]);
  return saved;
}, []);

// Phase 191B (HTTP-backed):
const handleAdd = useCallback(async (recording: NewRecording) => {
  const formData = buildMultipartUpload(recording);
  const {data, error} = await api.POST(
    "/v1/sessions/{session_id}/videos",
    {params: {path: {session_id: recording.sessionId}},
     body: formData,
     bodySerializer: (b) => b},  // raw FormData, no JSON
  );
  if (error) throw error;
  // Local-cache: keep recording.fileUri valid for playback (per C1)
  await videoStorageCache.adopt(recording.fileUri, data.id);
  setVideos((prev) => [data, ...prev]);
  return data;
}, []);
```

Polling for analysis state lives in `useSessionVideos`'s effect: when `videos` array contains any row with `analysis_state in {'pending','analyzing'}`, set up a 5s `setInterval` calling `refresh()`. Cleanup on unmount or when no rows are in transient states. Hook surface unchanged — just behavioral richness.

## Key Concepts

- **FastAPI BackgroundTasks** — runs after response sent, in-process. Sufficient for Phase 191B's single-worker dev posture; Phase 207 (Track J) replaces with a real worker queue.
- **Multipart upload via openapi-fetch** — needs `bodySerializer: (b) => b` to bypass the default JSON serialization. Documented gotcha; tested explicitly.
- **Anthropic SDK tool-use for structured output** — same pattern as Phase 03 + 22. Define a tool with the desired output schema as `input_schema`; force `tool_choice` to that tool; extract the tool_use block's `input` as the validated structured response.
- **`shutil.which` + module-load detection** — surfaces the ffmpeg-missing failure mode at module load (loud log line) AND at request time (503 with ProblemDetail). Test fakes the binary via env-var override.
- **SHA-256 content-hash dedup** — same video uploaded twice with the same bytes returns the existing row's `id` instead of creating a duplicate. Optimistic — no transactional lock; race on simultaneous-upload-of-same-bytes is acceptable (one wins, the other gets the dup ID back).
- **Polling vs SSE** — Phase 191B chooses polling for simplicity (5s interval; analysis typically completes in 15-30s). SSE/WebSocket is a future ADR if polling proves too costly.
- **Soft-delete via `deleted_at`** — same pattern F2 plans for symptoms/fault-codes. Phase 191B is the first concrete shipping of the pattern; F2 picks up the established convention.

## Verification Checklist

- [ ] Migration v38 → v39 applies cleanly; v39 → v38 down works; cascade-delete from sessions verified.
- [ ] All 5 video endpoints return ProblemDetail envelope on every error path (404 / 422 / 413 / 500 / 503).
- [ ] X-API-Key propagation guard test passes for all 5 endpoints.
- [ ] Multipart Content-Type preservation guard test passes for POST upload (mirrors Phase 188 commit-6 lesson).
- [ ] `require_tier('shop')` enforced on POST; individual-tier API key gets 403 with ProblemDetail.
- [ ] `require_api_key` enforced on GET / DELETE / file-stream.
- [ ] Per-session count cap (10) + size cap (1 GB) enforced; 413 Payload Too Large on size cap exceedance.
- [ ] Per-tier monthly aggregate quota enforced; shop tier 201st upload in calendar month → 402 with ProblemDetail.
- [ ] Soft-delete: list endpoint excludes `deleted_at IS NOT NULL`; GET on soft-deleted returns 404; DELETE is idempotent (second call returns 204).
- [ ] File-stream returns Content-Type `video/mp4` + Content-Length + Accept-Ranges `bytes`.
- [ ] ffmpeg subprocess wrapper extracts expected frame count from sample fixture; audio mp3 sidecar created.
- [ ] ffmpeg-missing detection: env-var `FFMPEG_BIN_OVERRIDE=/nonexistent` → upload returns 503 with ProblemDetail.
- [ ] Claude Vision wrapper structured-output schema validates; mocked Anthropic SDK returns shape pulled from real-API-response fixture (per Phase 190 Bug 2 lesson).
- [ ] End-to-end happy path: POST upload → response 201 with `analysis_state='pending'` → BackgroundTask fires → poll until `analyzed` → `analysis_findings` populated.
- [ ] Failure paths: ffmpeg fails → `analysis_state='unsupported'` (terminal); Anthropic call fails 3x → `analysis_state='analysis_failed'` (retryable later).
- [ ] Mobile `useSessionVideos.test.ts` continues passing UNCHANGED after hook swap (load-bearing assertion for Phase 191's handoff guarantee).
- [ ] Mobile videoCaptureMachine reducer extended with `uploading` state; existing 191 tests still pass.
- [ ] Mobile VideosCard renders 5-state analysis badge correctly per state.
- [ ] OpenAPI spec refresh adds `videos` tag + multipart request body shape + binary response media type for file-stream.
- [ ] No regression: full Phase 175-184 backend integration tests + Phase 188-191 mobile tests.

## Risks

- **First production wiring of Claude Vision into the API.** Phase 100-103 ran standalone scripts; Phase 191B brings the SDK into the request path. Cost surprises possible (Sonnet at 60 frames/call ≈ $0.06-0.10 per analysis; shop-tier monthly cap of 200 = up to $20/mo per shop). Mitigation: cost_estimate_usd in every VideoAnalysisFindings response so unit cost is visible; admin-side aggregate cost dashboard is a Phase 192+ ticket.
- **ffmpeg binary dependency.** Not a Python package — needs to be on PATH or bundled with the deployment. Mitigation: module-load detection logs the binary path or warning; upload endpoint returns 503 with helpful ProblemDetail; README documents installation per OS.
- **Anthropic SDK rate limits.** Vision calls are heavier than text-only; per-org quotas more restrictive. Mitigation: 2-retry policy with exponential backoff in the wrapper; on 3rd failure, transition to `analysis_failed` (retryable later) rather than `unsupported` (terminal).
- **BackgroundTasks vs real worker.** FastAPI BackgroundTasks runs in-process. Multi-uvicorn-worker setups (Phase 207 territory) lose the queueing semantics. Phase 191B explicitly assumes single-uvicorn-worker dev posture; production multi-worker is a Phase 207 concern and surfaces in the docstring.
- **Multipart upload behavior in openapi-fetch.** Default JSON serializer doesn't handle FormData; `bodySerializer: (b) => b` bypass needs explicit testing in the mobile test suite. Without this, the upload silently sends `[object FormData]` as the body. Mitigation: dedicated mock test asserting the on-the-wire body shape (mirrors Phase 188's Content-Type regression guard).
- **Polling load.** 5s polling per active video × N concurrent users could spike list-endpoint load. Phase 191B is shop-only with low concurrent-mechanic-per-shop counts (≤5 typical); polling is fine. SSE/WebSocket as a future option ADR.
- **Concurrent same-file upload race.** Two mobile clients (or the same client mid-retry) uploading the same SHA-256 simultaneously → both check `WHERE sha256 = ?` and find nothing, both insert. Mitigation: SHA-256 unique constraint at DB layer + INSERT OR IGNORE pattern with re-SELECT after to find the winner row. Acceptable trade-off vs row-level locking.
- **Hook surface drift.** The whole point of the Phase 191 handoff contract is that mobile consumers don't change. If the swap requires renaming `addRecording` to `uploadRecording` or changing the `atCap` calculation source, the load-bearing assertion fails. Mitigation: the test file MUST run unchanged; if it needs changes, freeze and revisit the hook design.

## Backend integration test coverage (per C2 confirmation)

**Single load-bearing assertion for the phase**: mobile's existing `__tests__/hooks/useSessionVideos.test.ts` from Phase 191 continues passing UNCHANGED after the Commit 6 hook swap. The test bodies assert on `{videos, addRecording, deleteVideo, refresh, atCap, capReason, isLoading, error}` shape — they do not depend on the FS-backed implementation. Mock layer changes (mocks `api.POST`/`api.GET` instead of `saveRecording`/`listSessionVideos`); test bodies do not. If a test body needs to change, the hook contract has drifted and the architect gate stops to revisit the design before merge.

**Backend contract test files (~3, ~70-80 tests):**

### `tests/test_phase191b_videos_api.py` — endpoint contract tests (~30 tests)

| Contract | Test |
|----------|------|
| ProblemDetail envelope on every error | 5 tests — 404 (video not found / wrong session), 422 (malformed metadata), 413 (file too large), 500 (DB error), 503 (ffmpeg missing). All assert response body matches `{type, title, status, detail, ...}` shape pulled from Phase 175 envelope contract — NOT from test author's assumption (Phase 190 Bug 2 lesson). |
| X-API-Key propagation | 5 tests — one per endpoint: missing key → 401 with ProblemDetail; wrong key → 401; right key → 200/201/204; key with revoked status → 401. |
| Multipart Content-Type preservation | 1 test — POST upload asserts that the route handler RECEIVED `multipart/form-data` Content-Type (validates the openapi-fetch `bodySerializer` bypass works end-to-end). Mirrors Phase 188 commit-6 transport guard. |
| Tier gate enforcement | 3 tests — POST with shop-tier key → 201; POST with individual-tier key → 403 with ProblemDetail "shop tier required"; POST with company-tier key → 201. |
| `require_api_key` on read endpoints | already covered by X-API-Key tests above. |
| Per-session count cap | 2 tests — 10th upload → 201; 11th upload → 402 with ProblemDetail "session video count cap reached (10/10)". |
| Per-session size cap | 2 tests — upload pushing total to ≤ 1 GB → 201; upload pushing total over 1 GB → 413 with ProblemDetail "session video size cap reached (1.0 GB)". |
| Per-tier monthly aggregate quota | 4 tests — shop 200th upload of month → 201; shop 201st → 402; company 1000th → 201 (unlimited); calendar-month boundary reset (mock `datetime.now`). |
| Soft-delete semantics | 4 tests — DELETE returns 204; subsequent GET returns 404; subsequent DELETE returns 204 (idempotent); list endpoint excludes deleted rows. |
| File-stream headers | 2 tests — Content-Type `video/mp4`; Content-Length matches file size; Accept-Ranges `bytes`. |
| End-to-end happy path | 1 test (heavy) — POST upload → 201 with `analysis_state='pending'` → invoke BackgroundTasks synchronously in test → GET single returns `analysis_state='analyzed'` → `analysis_findings` matches mocked Vision response. |
| Failure paths | 3 tests — ffmpeg fails → `analysis_state='unsupported'`; Vision call fails (mocked exception) → `analysis_state='analysis_failed'`; Vision returns malformed structured output → 'analysis_failed' with detail. |

### `tests/test_phase191b_ffmpeg.py` — subprocess wrapper tests (~12 tests)

Uses `tests/fixtures/videos/sample_3sec.mp4` (~50 KB, generated once via `ffmpeg -f lavfi -i testsrc=duration=3:size=320x240:rate=30 -c:v libx264 -t 3 sample.mp4`). Tests skip cleanly when CI lacks ffmpeg (xfail with reason).

| Contract | Test |
|----------|------|
| `extract_frames` returns list[Path] sorted | 1 test — sample 3sec mp4 → 6 frames at 2 fps. |
| Frame extraction respects MAX_FRAMES cap | 1 test — synthetic 60s mp4 → exactly 60 frames. |
| `extract_audio` produces mp3 sidecar | 1 test — sample mp4 → mp3 file exists, 1 channel, 44100 Hz. |
| `validate_video` accepts good mp4 | 1 test. |
| `validate_video` rejects truncated mp4 | 1 test — write 100 random bytes to .mp4 → raises FFmpegFailed. |
| Module-load `FFMPEG_BIN` detection | 2 tests — present (real ffmpeg path) + absent (env override `FFMPEG_BIN_OVERRIDE=`). |
| `FFmpegMissing` raised when binary absent | 1 test. |
| `FFmpegFailed` raised on subprocess non-zero exit | 1 test. |
| `FFmpegFailed` raised on subprocess timeout | 1 test — 1s-timeout against a 5s-pause stub script. |
| Subprocess stderr captured in exception | 1 test. |
| Frames written to specified output_dir | 1 test — assertions on `output_dir.glob` shape. |

### `tests/test_phase191b_video_analysis.py` — Claude Vision wrapper (~15 tests)

**Anthropic SDK mocked using fixtures pulled from real API responses, NOT test-author assumptions** (Phase 190 Bug 2 lesson explicitly applied). Fixture generation: a one-shot script `tests/fixtures/anthropic_responses/_regen.py` that calls the real API once with a known input, persists the response object as JSON, and tests load + replay. Fixture commit message documents the regen procedure.

| Contract | Test |
|----------|------|
| Happy path findings extraction | 1 test — mock returns recorded fixture; assertion on `VideoAnalysisFindings` shape. |
| Structured output schema validation | 2 tests — mock returns valid shape (passes); mock returns invalid shape (raises ValidationError). |
| Tool-use block extraction | 1 test — assertions on the SDK call's `tool_choice` and the response's `content[0].type == 'tool_use'`. |
| Image block construction | 2 tests — frames list of 5 → 5 image blocks with base64 data + correct media_type. |
| Multi-frame batching cap | 1 test — frames list of 70 → call uses only the first 60 (defensive cap). |
| Cost-tier model selection | 2 tests — Sonnet default; Haiku when env flag `MOTODIAG_VISION_MODEL=haiku-4.5` set. |
| Retry on rate-limit | 2 tests — first call raises RateLimitError, second succeeds → returns findings; both calls fail → raises after 2 retries. |
| Persistent-error fallback | 1 test — unmocked exception type → propagates (route handler catches and sets `analysis_state='analysis_failed'`). |
| `cost_estimate_usd` populated | 1 test — finds value > 0 in returned VideoAnalysisFindings. |
| Vehicle context interpolated into prompt | 1 test — assertions on the user-message text content containing the vehicle make + model + year. |
| Empty findings handling | 1 test — mock returns 0 findings + populated `no_findings_reason` → schema accepts. |

**No regression sweep required mid-phase** (per the established convention) — only at full architect gate. Specific anti-regression tests pinned to existing transport guards still run as part of the targeted suite (Phase 188 Content-Type + Phase 189 X-API-Key + Phase 190 ProblemDetail-vs-FastAPI-default).

## Smoke test (Kerwyn-side, post-build, pre-v1.1)

**One full architect-gate stop after Commit 7.** No micro-gate this phase — no native-module integration like Phase 191 had. Phase 100-103 modules wired into HTTP layer for the first time IS the load-bearing risk; backend integration tests above cover it pre-gate.

### Architect gate (~18-22 steps)

1. Cold backend launch with `motodiag serve --host 0.0.0.0 --port 8000`. New `videos` tag visible in `/openapi.json`. `/v1/version` reports schema_version=39.
2. Mobile cold-relaunch on Pixel 7 API 35. Auth ✓ via existing keychain. No regression Phase 186 BLE / 187 / 188 / 189 / 190 / 191.
3. Open Session #1 (the one with the preserved Phase 191 paused-badge artifact). VideosCard shows the existing Phase 191 video. New 5-state analysis badge — should show 'pending' or 'analyzing' on first poll after backend has the video for the first time (Phase 191 → 191B migration backfill: Phase 191 videos that pre-date the upload migration will need explicit hook handling — likely surface as `unsupported` since they were never uploaded).
4. Tap the existing video row → VideoPlayback. Local cache works (Phase 191 file still on disk).
5. Tap Record on Session #1 → VideoCaptureScreen. Record 10-15s. Stop. saved-state preview.
6. Tap "Use this video". Upload progress indicator shows. Returns to SessionDetail. New row visible with `analysis_state='pending'` badge.
7. Wait ~15-30s. Polling refresh: badge transitions pending → analyzing → analyzed. Findings tile expands on tap; renders summary + N findings list with severity color coding.
8. Tap a finding row → expanded detail with location + description + confidence.
9. Backend cost log: confirm a single Anthropic API call fired with the expected cost (~$0.06-0.10 for ~30 frames).
10. Upload another 5 videos (total 7 — Phase 191's 1 + 6 new). 8th upload attempt → still works (per-session cap is 10 backend / 5 mobile; mobile would have already at-cap'd the user). Bypass mobile cap via curl: `curl -X POST -F file=@test.mp4 -F metadata=...` confirms 11th upload returns 402 with ProblemDetail.
11. Per-session size cap: pre-load 1 GB worth of dummy mp4s via curl, attempt 1 KB upload → 413.
12. Tier gate: regenerate API key with `--tier individual` via `motodiag apikey create --tier individual`, attempt POST upload → 403 with "shop tier required" ProblemDetail.
13. ffmpeg-missing simulation: set `FFMPEG_BIN_OVERRIDE=/nonexistent` env var; restart backend; attempt upload → 503 with ProblemDetail.
14. Vision-failure simulation: set `ANTHROPIC_API_KEY=invalid` env var; restart; upload → BackgroundTask runs, sees auth error, transitions `analysis_state='analysis_failed'`.
15. Soft-delete: tap delete on a video row, confirm. Mobile list updates. Backend GET → 404 ProblemDetail. Backend file still on disk (cleanup deferred per plan).
16. Cascade-delete: from SQLite shell, `DELETE FROM sessions WHERE id = X` → all attached video rows are gone.
17. Cold relaunch backend: schema_version still 39, video data persists.
18. Cold relaunch mobile: useSessionVideos polls fresh on focus; analysis_findings hydrate correctly from backend.
19. Multipart on-the-wire body shape: tcpdump or backend access log confirms `Content-Type: multipart/form-data; boundary=...` (NOT `application/json`).
20. ProblemDetail envelope sanity: hit each error case (404, 413, 422, 402, 403, 500, 503) via curl; visually inspect response bodies match Phase 175 envelope.
21. No regression: Phase 175-184 backend integration tests + Phase 188-191 mobile tests all green.
22. Mobile `__tests__/hooks/useSessionVideos.test.ts` ran unchanged — assertion file at `git diff --stat` shows zero changes between v1.0 and v1.1 of the test file. **Load-bearing assertion confirmed.**

If round 1 fails, fix commits 8+ on same branch (Phase 188 / 190 / 191 precedent).

## Commit plan (7 commits on `phase-191B-video-upload-ai-analysis` branch)

Backend repo gets the bulk of this work; mobile branch stays minimal (Commit 6 alone touches mobile code, Commit 7 finalizes both).

**Commit 1 — Migration v39 + Video model + repo + ffmpeg subprocess wrapper.** `migrations/039_videos.py`; `storage/models/video.py` with Pydantic schemas; `storage/repositories/video_repo.py` with full CRUD + soft-delete + quota math; `media/ffmpeg.py` subprocess wrapper. ~22-25 unit tests across 2 test files. Schema bump verified via `motodiag db init` round-trip.

**Commit 2 — Claude Vision wrapper (`ai/video_analysis.py`) + recorded fixtures.** Anthropic SDK call with tool-use structured output; `VideoAnalysisFindings` Pydantic model; recorded-fixture mock pattern. ~15 tests. NO endpoint wiring yet — pure module.

**Commit 3 — Upload endpoint (POST `/v1/sessions/{id}/videos`) + multipart handling + BackgroundTask wiring.** Just the upload path. Returns 201 with `analysis_state='pending'`. BackgroundTask invokes `run_analysis_pipeline` (the Vision wrapper from Commit 2). ~12 tests. End-to-end upload + analysis verified via the test_phase191b_videos_api.py happy-path test.

**Commit 4 — List + single + delete endpoints (GET / GET / DELETE).** Soft-delete via `deleted_at`. ~10 tests including soft-delete idempotency + cascade-delete from sessions.

**Commit 5 — File-stream endpoint (GET `/v1/sessions/{id}/videos/{video_id}/file`).** Binary stream with Content-Type / Content-Length / Accept-Ranges. ~6 tests.

**SKETCH SIGN-OFF for the mobile state-machine `uploading` state extension** — posted separately for Kerwyn, gates Commit 6.

**Commit 6 (mobile) — `useSessionVideos` hook swap from FS-backed to HTTP-backed.** Single commit on the mobile branch. Refresh `api-schema/openapi.json` + regenerate `api-types.ts`; rewrite hook implementation; delete `videoStorage.ts` + its tests; create `videoStorageCache.ts` for the local-cache lookups; extend `videoCaptureMachine` with `uploading` state; VideosCard renders the 5-state analysis badge + findings expansion. **Mobile `useSessionVideos.test.ts` runs UNCHANGED** — load-bearing assertion. ~15 mobile test additions (videoStorageCache + reducer extension + analysis-badge render); no test edits.

**Commit 7 — README updates + project structure refresh + ROADMAP mark + version bumps + finalize docs.** Backend `README.md` documents ffmpeg install. Backend `pyproject.toml` 0.1.0 → 0.2.0 + `anthropic` moved from optional to required deps. Backend `implementation.md` 0.13.7 → 0.13.8. Backend `ROADMAP.md` Phase 191B marked ✅. Mobile `package.json` 0.0.6 → 0.0.7. Mobile `implementation.md` 0.0.8 → 0.0.9.

Each commit: backend `pytest` green + `ruff check` clean before next; mobile `tsc --noEmit` + `npm test` green at Commit 6.

## Architect gate

**Single-stage gate after Commit 7** (no micro-gate; no native-module integration this phase).

State-machine sketch sign-off (between Commits 5 and 6) is a separate review event for the `uploading` state addition — same Phase 189 / 191 discipline. Sketch posted with: state diagram, transition table, transient-vs-terminal analysis, mobile UI mockup of the upload-progress indicator placement.

## Versioning targets at v1.1 finalize

- Backend `pyproject.toml`: `0.1.0 → 0.2.0` (Track I major-feature bump — first production wiring of Claude Vision into the API).
- Backend `implementation.md`: `0.13.7 → 0.13.8`.
- Backend schema: `38 → 39` (one new table + cascade FK).
- Mobile `package.json`: `0.0.6 → 0.0.7`.
- Mobile `implementation.md`: `0.0.8 → 0.0.9`.

## Not in scope (firm)

- **Real worker queue** (Redis-RQ, Celery, RabbitMQ) for analysis dispatch. → Phase 207 (Track J — multi-worker uvicorn).
- **Audio analysis via Claude.** Phase 191B extracts the mp3 sidecar but doesn't analyze it. → Track G (audio-aware diagnostics).
- **Re-analysis of existing videos** when prompts evolve. → Phase 192+ admin endpoint.
- **S3-compatible storage migration.** → Post-Track-J scaling phase.
- **Batch upload of multiple videos in one request.** Single-file upload only.
- **WebSocket or SSE for analysis state push.** Polling (5s) for Phase 191B. → future ADR if polling load matters.
- **Mobile-side cost visibility.** Backend stores `cost_estimate_usd` per video; mobile renders findings but not cost. Admin-side aggregate cost view → Phase 192+ ticket.
- **Video sharing / external app intent.** → Phase 192 (share sheet integration) which will need `READ_MEDIA_*` perms.
- **iOS support.** Backend is iOS-agnostic but the mobile half of Phase 191B inherits Phase 191's Android-only smoke posture.
