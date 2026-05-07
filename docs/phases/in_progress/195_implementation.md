# Phase 195 — Voice Input for Symptom Description (substrate)

**Version:** 1.0.1 (architect-side review amendment) | **Tier:** Standard | **Date:** 2026-05-07

## v1.0.1 amendment (Backend Commit 0.5)

Architect-side review of Backend Commit 0's two "planned deviations" surfaced that both were framed inaccurately in the plan-write phase log:

**Deviation 1 (pydub/ffmpeg absent → verbatim storage) reframed as path (c) — verbatim with format tracking, the architecturally correct choice.** Section 5's PCM-based storage projection was incorrect — verbatim M4A is ~4× SMALLER than 16 kHz mono PCM. Whisper accepts mobile's M4A natively; 195B does NOT need a transcoding step. The one consumer that genuinely needs PCM is Phase 96 acoustic-analysis cross-pollination, which is speculative — `F39 NEW` filed at Backend Commit 0.5 with promotion trigger ("Phase 96 integration phase or any consumer requiring PCM input"). Section 5 storage projection redoes to ~130 GB peak at 100-mechanic-scale (was ~520 GB on PCM assumption); 60-day retention policy unchanged. The original plan-write framing as "Risk #10 deviation" was environment-friction framed as architecture; the actual choice is deliberate format-tracking matching what Phase 194's `audio_format` precedent already established at the schema level.

**Deviation 2 (Section 2 0.5 threshold-gating dropped) reframed as 195B-spec leak.** The 0.5 keyword-coverage threshold from plan v1.0 was specified to control WHEN 195B's Claude-fallback fires (low coverage → ambiguous → run Claude); it has nothing to gate in Phase 195 in isolation since Section 3's substrate-feature split established Phase 195 as keyword-only. The threshold's calibration plan rightfully belongs in 195B's plan with real transcript fixtures. Mobile Commit 1 contract unchanged: backend creates one `extracted_symptoms` row per keyword match (`extraction_method='keyword'`); UI renders all matches; "low confidence" indicator client-derivable from match-count vs phrase-count if useful. No backend signal needed in 195. The original "deviation" framing was bad phase-log writing — there's nothing to deviate FROM in 195 because the threshold was never 195's concern.

**F37 instance #3 surfaced + escalation logged**: Backend Commit 0's `transcripts.py` response models used `str` for `extraction_state`, `extraction_method`, `audio_format`, and `preview_engine` instead of `Literal[...]`. Phase 194's `photos.py` (`PhotoRole = Literal[...]`) had this right; the regression confirms F37's "value-set drift between backend CHECK constraints and contract surface" pattern. **Backend Commit 0.5 fixes the regression** (correctness-now): `transcripts.py` upgraded to use `ExtractionState`, `ExtractionMethod`, `AudioFormat`, `PreviewEngine` Literal aliases matching DB CHECK constraints + the `react-native-audio-recorder-player` mobile output formats. **F37 promoted to dedicated phase post-Phase-195-finalize** (correctness-systematically) — same shape as Phase 191D ($191B → 191C → 191D pattern): lint rule enforcing "Pydantic response models for fields with DB CHECK constraints must use Literal[...] matching constraint values" + retroactive validation against 191B/192/193/194/195 backend code + F9 pattern-guide subspecies addition. Likely numbered 195C or equivalent post-195/195B.

**No scope changes from v1.0**; all amendments are clarifications of existing decisions. Verification Checklist + Risks + Outputs unchanged.

---

## Goal

Ship the **substrate half** of the substrate-then-feature pair (195 capture + on-device preview + audio upload + canonical-shape transcript + keyword extraction + WO section variant; **195B** ships cloud Whisper + Claude-rich extraction + cost monitoring + VAD). Mechanic taps "Voice memo" inside a work order, the mic opens, they speak ("I noticed a clunk in the front end at low speed"), an on-device STT preview surfaces immediately, the audio uploads, the backend stores audio + the on-device transcript + runs keyword-extraction against the existing `engine/symptoms.SYMPTOM_CATEGORIES` dict, the structured symptoms appear in the work-order detail screen as a new section variant, and the mechanic can tap any extracted symptom to confirm or edit.

This phase is **mostly-mobile + backend-meaningful** (Backend Commit 0 ships a real new table + route + image-pipeline-shaped audio normalization + 60-day audio sweep substrate; Mobile Commits 1 + 2 ship the capture flow + section variant + classify-confirm UX). Reuses Phase 191B + Phase 194 multipart-upload + per-X quotas + storage-convention pattern; reuses Phase 193's `WorkOrderSection` discriminated-union forward-look — second variant addition (after Phase 194's photos), structurally different (time-series + extracted-output), so the second test of the forward-look commitment.

CLI: no new CLI surface (mobile-only feature with backend support).

Outputs:
- **Backend** (1 commit): migration creating `voice_transcripts` + `extracted_symptoms` tables; new `transcript_repo.py` + `extracted_symptom_repo.py`; new `audio_pipeline.normalize_audio` for upload-time audio normalization (16-bit PCM mono 16 kHz canonical, suitable for both mobile playback + 195B's Whisper input); new `POST /v1/shop/{shop_id}/work-orders/{wo_id}/transcripts` multipart route; per-WO 30 / monthly 200 quota; 60-day audio sweep substrate (Phase 192B share-temp shape); keyword extraction via existing `engine/symptoms.categorize_symptoms` (no new module); substrate-anticipates-feature for 195B (`whisper_transcript TEXT NULL`, `whisper_segments JSON NULL`, `whisper_cost_usd_cents INTEGER NULL`, `whisper_model TEXT NULL`).
- **Mobile** (2 commits): `useMicrophonePermissions` factored out from `useCameraPermissions` (clean separation, no fork); `audioStorageCache` mirroring `photoStorageCache` shape with 7-day cold-start sweep; `audioCaptureMachine` reducer (4-state: idle / recording / uploading / uploaded / upload-failed — VAD/auto-stop deferred to 195B); `VoiceCaptureScreen` with button-tap-to-start-and-stop affordance + on-device STT preview via `@react-native-voice/voice` (NEW dep) running in parallel with audio recording (preview is fast feedback; canonical is server-side); `useWorkOrderTranscripts` hook with multipart upload + extracted-symptom CRUD; `WorkOrderTranscriptsSection` discriminated-union variant addition (FIRST + SECOND test of Phase 193's forward-look commitment; structurally different from Phase 194's photos — time-series with extracted-output rather than media-references-with-relationships); transcript review surface with extracted-symptom edit/confirm; entry-point on `WorkOrderDetailScreen`; nav wiring; smoke gate; finalize.

## Architectural commitment — substrate-feature split

Phase 195 deliberately ships **only** the on-device preview + audio storage + keyword extraction. Phase 195B is the place for the cloud Whisper integration + Claude-rich extraction prompt-engineering + cost monitoring dashboard + voice activity detection (VAD). The split mirrors 191/191B + 192/192B + 194/194B precedent: different gate shapes (Whisper has cost + privacy + accuracy validation gates that keyword extraction doesn't), different risk profiles (Whisper-API-key surface, $-burn-rate watch, prompt regression risk), different UX-validation needs (the 195 substrate validates the capture-flow ergonomics; 195B validates the canonical-quality story).

Bundling would create 191B-saga risk (5 architect-gate rounds for one phase). Splitting lets 195 land the substrate cleanly + lets 195B focus on its own gate-shape concerns.

## Architectural commitment — audio retention policy (Section 5: 60-day + transcripts permanent)

Audio bytes retained on disk for **60 days** post-upload, then auto-pruned by a backend sweep (cron-style; Phase 192B share-temp pattern + Phase 194's `cleanupOldPhotos` discipline). Transcripts (`voice_transcripts.preview_text` from on-device + future `whisper_transcript` from 195B) retained permanently. Extracted symptoms (`extracted_symptoms` rows) retained permanently — they're the structured output independent of source audio.

**Why retain audio at all (vs Phase 194's plan-time temptation to ship transcript-only):** the architecture moved to (c) hybrid in Section 1 — cloud Whisper canonical means the audio file exists server-side anyway. Discarding post-transcription is a deliberate retention policy choice, not a structural artifact. Three concrete reasons retention matters:
1. **Re-transcribe with future better models** when the field moves (Whisper-3, GPT-4o-audio, etc.) — the upgrade path requires source audio.
2. **Mechanic verification** when transcript looks weird ("did I really say that?" requires playback).
3. **Phase 96 cross-pollination** — same audio analyzable for sound-signature diagnostic data; two phases' value from one capture (motorcycle running in background of a voice memo can drive engine-knock detection).

**Why 60 days (vs longer):** privacy posture + bounded storage. 60 days is enough to cover the realistic re-transcription / verification window without holding indefinitely. Privacy story: "we hold for N days then delete" is defensible to mechanics + customers; "we hold forever" needs a heavier review.

## Architectural commitment — uniform display, source-agnostic UI (Phase 193's posture, extended again)

Voice-extracted symptoms render uniformly with manual symptoms (Phase 178) regardless of capture source. The new `voice_transcripts.source` column ships nullable + the `extracted_symptoms` table includes a `source TEXT` column tracking origin (`'voice'` for Phase 195; `'manual'` for retroactive backfill if/when migration consolidates `diagnostic_sessions.symptoms`; `'obd'` for Phase 196). UI in Phase 195 IS source-agnostic — extracted symptoms render identically to manual ones in the WO detail. Source-aware behavior is deferred until a future phase argues it's load-bearing (per F30 telemetry-deferral pattern).

**F38 (NEW) filed at plan-write time**: "Unify symptom storage across `diagnostic_sessions.symptoms` (JSON list, Phase 178 substrate), `voice_transcripts.extracted_symptoms` (relational, Phase 195), and future OBD-captured symptoms (Phase 196 horizon). Promotion trigger: Phase 196 surfaces source-tracking demand on `diagnostic_sessions` symptoms surface, OR query patterns require cross-source symptom queries (e.g., 'all symptoms reported via voice in the last 30 days')." DON'T migrate `diagnostic_sessions.symptoms` from JSON-list to relational in Phase 195 — that's a substantial migration touching established surface and deserves its own pre-plan with cross-feature impact analysis.

## Logic

### F33 audit (per CLAUDE.md Step 0, dual-direction)

Audit ran 2026-05-06 BEFORE plan v1.0 was written. Findings folded inline below.

**Backend findings:**
- `media/audio_capture.py` (Phase 96, ~340 LoC) — pure-Python WAV capture + preprocessing for diagnostic ENGINE-sound analysis. Shared concept (audio bytes on disk + WAV format) but DIFFERENT processing pipeline (FFT-overlap segmentation for frequency analysis vs voice-activity-shaped chunking for STT). On-disk format reusable; pipeline parallel. NEW `audio_pipeline.normalize_audio` ships in Phase 195 for upload-time normalization (16 kHz mono 16-bit PCM, the canonical Whisper input format).
- `media/sound_signatures.py` + `media/spectrogram.py` + `media/anomaly_detection.py` — adjacent acoustic-analysis surfaces. Coexist; not used in Phase 195. Phase 96 cross-pollination is a Section 5 retention rationale (same audio could feed sound-signature analysis).
- **No existing STT/Whisper/Anthropic-audio integration.** `pyproject.toml` has `anthropic>=0.40` only. Phase 195 ships keyword-extraction via existing `engine/symptoms` (NO new dep on backend); Phase 195B will add `openai>=1.0` (Whisper) + Anthropic prompt scaffolding for rich extraction.
- **Symptom substrate (Phase 178):** `core/database.py` baseline schema has `symptoms` table (KB catalog: `id, name, description, category, related_systems`). `knowledge/symptom_repo.py` exposes `add_symptom`, `search_symptoms`, etc. — dict-based, no Pydantic Symptom model. `engine/symptoms.py` has `categorize_symptoms(list[str]) → dict[str, list[str]]` + `assess_urgency(list[str])` + `SymptomAnalyzer` (Claude-based diagnostic engine). All operate on free-text strings. Phase 195's keyword-extraction reuses `categorize_symptoms` directly. `engine/symptoms.SYMPTOM_CATEGORIES` is the keyword pattern dict that drives matching.
- **Symptoms data shape:** `diagnostic_sessions.symptoms` is JSON-list of free-text strings (Phase 178); `issues.linked_symptom_id` is nullable FK to `symptoms.id` (Phase 162); per-WO symptoms don't exist as a first-class entity today. Phase 195's `extracted_symptoms` table is a NEW relational shape scoped to voice transcripts.
- **Reusable architectural patterns:** Phase 191B videos route + Phase 194 photos route — canonical multipart-upload + per-X quotas + storage-convention. Voice transcripts ship as parallel resource. `media/analysis_worker.py` BackgroundTasks pattern — Phase 195's keyword extraction runs sync in-handler (fast); Phase 195B's Claude-fallback (and Whisper) will run as deferred tasks. `DiagnosticClient` (Anthropic SDK) — reusable for 195B.

**Mobile findings:**
- `useCameraPermissions` (Phase 191) **already requests + tracks microphone permission** alongside camera. Combined `'granted'` requires both. For Phase 195's audio-only path, factor out `useMicrophonePermissions` from the same logic — clean separation, no fork-and-forget. Don't keep the combined gate; the camera permission would block audio-only screens unnecessarily on devices that have camera permission un-granted but mic granted.
- `react-native-vision-camera@4.7.3` records audio inline with video (Phase 191 substrate). For **standalone audio recording without a viewfinder**, vision-camera is the wrong tool — overkill camera mount + UI cost.
- **No existing audio-only / STT lib in `package.json`.** Phase 195 ships TWO new mobile deps: `@react-native-voice/voice` (on-device STT preview) + `react-native-audio-recorder-player` (raw audio capture for upload). Both are well-maintained (1k+ stars, RN 0.85 compat verified at audit time).
- Phase 191B + Phase 194 templates: `useSessionVideos` / `useWorkOrderPhotos` hook shape transfers verbatim to `useWorkOrderTranscripts`. `videoStorageCache` / `photoStorageCache` shape transfers to `audioStorageCache`. 4-state capture machine pattern transfers (Phase 195's machine has `recording` state in addition to `previewing` since audio capture has duration).
- **Phase 193 `WorkOrderSection` variant integration (Section E load-bearing test #2):** Phase 194's photos was test #1 — passed. Phase 195's voice-transcripts is test #2 with structurally different shape (time-series + extracted-output). The renderer needs a 3rd layout idiom (timeline-with-extracted-symptom-chips). The builder gets a 5th positional param (or refactors to extras-bag — DEFER until actual implementation friction surfaces, per Section 4 trust-but-verify discipline). F9-discipline holds: render uniquely, NO deformation into existing variant shapes.

**F33 verdict**: substantial reuse on backend (Phase 191B/194 patterns + Phase 178 symptom substrate + `engine/symptoms` keyword dict); meaningful but bounded reuse on mobile (Phase 194's hook shape + cache shape + machine pattern). TWO new mobile deps (voice + audio-record); ZERO new backend deps in Phase 195 (Phase 195B will add `openai`). Phase 195 = single-phase substrate; 195B = the AI-canonical feature half.

### Backend Commit 0 — `voice_transcripts` + `extracted_symptoms` tables + audio route + audio sweep

1. **Migration** (version 42): two new tables.

   ```sql
   CREATE TABLE voice_transcripts (
       id INTEGER PRIMARY KEY AUTOINCREMENT,
       work_order_id INTEGER NOT NULL,
       issue_id INTEGER,                          -- nullable; same A-flexibility as Phase 194 photos
       audio_path TEXT NOT NULL,                  -- canonical disk path
       audio_size_bytes INTEGER NOT NULL,
       audio_sha256 TEXT NOT NULL,
       duration_ms INTEGER NOT NULL,
       sample_rate_hz INTEGER NOT NULL DEFAULT 16000,  -- canonical Whisper input
       language TEXT NOT NULL DEFAULT 'en-US',    -- ISO 639-1 with optional region per Section 7
       captured_at TIMESTAMP NOT NULL,
       uploaded_by_user_id INTEGER NOT NULL,
       preview_text TEXT,                         -- on-device STT result (mobile sends if available)
       preview_engine TEXT,                       -- 'ios-speech' | 'android-speech-recognizer' | NULL
       extraction_state TEXT NOT NULL DEFAULT 'pending'
           CHECK (extraction_state IN ('pending', 'extracting', 'extracted', 'extraction_failed')),
       extracted_at TIMESTAMP,
       -- Substrate-anticipates-feature for Phase 195B (cloud Whisper):
       whisper_transcript TEXT,                   -- NULL until 195B fills
       whisper_segments TEXT,                     -- JSON array, NULL until 195B fills
       whisper_cost_usd_cents INTEGER,            -- NULL until 195B fills
       whisper_model TEXT,                        -- NULL until 195B fills
       -- Source provenance (Section 6 forward-investment):
       source TEXT,                               -- NULL by default; Phase 196+ populates
       created_at TIMESTAMP NOT NULL DEFAULT (datetime('now')),
       updated_at TIMESTAMP NOT NULL DEFAULT (datetime('now')),
       audio_deleted_at TIMESTAMP,                -- set when 60-day sweep prunes audio_path bytes
       deleted_at TIMESTAMP,                      -- soft-delete the whole row
       FOREIGN KEY (work_order_id) REFERENCES work_orders(id) ON DELETE CASCADE,
       FOREIGN KEY (issue_id) REFERENCES issues(id) ON DELETE SET NULL,
       FOREIGN KEY (uploaded_by_user_id) REFERENCES users(id) ON DELETE SET DEFAULT
   );
   CREATE INDEX idx_voice_transcripts_wo ON voice_transcripts(work_order_id) WHERE deleted_at IS NULL;
   CREATE INDEX idx_voice_transcripts_issue ON voice_transcripts(issue_id) WHERE deleted_at IS NULL;
   CREATE INDEX idx_voice_transcripts_audio_age ON voice_transcripts(created_at)
       WHERE audio_deleted_at IS NULL AND deleted_at IS NULL;  -- drives the 60-day sweep
   CREATE INDEX idx_voice_transcripts_extraction_state ON voice_transcripts(extraction_state)
       WHERE extraction_state IN ('pending', 'extracting');

   CREATE TABLE extracted_symptoms (
       id INTEGER PRIMARY KEY AUTOINCREMENT,
       transcript_id INTEGER NOT NULL,
       text TEXT NOT NULL,                        -- the canonical symptom phrase
       category TEXT,                             -- e.g. 'engine', 'brakes' (from engine/symptoms.SYMPTOM_CATEGORIES)
       linked_symptom_id INTEGER,                 -- nullable FK to symptoms catalog (Phase 178)
       confidence REAL NOT NULL DEFAULT 1.0,      -- 0.0-1.0; keyword pass = 1.0; future Claude pass = model-reported
       extraction_method TEXT NOT NULL DEFAULT 'keyword'
           CHECK (extraction_method IN ('keyword', 'claude', 'manual_edit')),
       segment_start_ms INTEGER,                  -- NULL for keyword extraction; populated by 195B Whisper segments
       segment_end_ms INTEGER,
       confirmed_by_user_id INTEGER,              -- mechanic confirmation (UI tap)
       confirmed_at TIMESTAMP,
       source TEXT,                               -- forward-investment column (Phase 196 horizon)
       created_at TIMESTAMP NOT NULL DEFAULT (datetime('now')),
       deleted_at TIMESTAMP,
       FOREIGN KEY (transcript_id) REFERENCES voice_transcripts(id) ON DELETE CASCADE,
       FOREIGN KEY (linked_symptom_id) REFERENCES symptoms(id) ON DELETE SET NULL,
       FOREIGN KEY (confirmed_by_user_id) REFERENCES users(id) ON DELETE SET NULL
   );
   CREATE INDEX idx_extracted_symptoms_transcript ON extracted_symptoms(transcript_id) WHERE deleted_at IS NULL;
   CREATE INDEX idx_extracted_symptoms_linked ON extracted_symptoms(linked_symptom_id) WHERE deleted_at IS NULL;
   CREATE INDEX idx_extracted_symptoms_method ON extracted_symptoms(extraction_method);
   ```

   SCHEMA_VERSION 41 → 42. Rollback: drop both tables + their indexes.

2. **Repos** (`src/motodiag/shop/transcript_repo.py` + `src/motodiag/shop/extracted_symptom_repo.py`): mirror `wo_photo_repo.py` shape. CRUD + quota helpers + `update_extraction_state`. Owner-aware via shop membership at the route layer (Phase 193 pattern).

3. **Audio pipeline** (`src/motodiag/media/audio_pipeline.py`): NEW. `normalize_audio(raw_bytes) -> NormalizedAudio` — pure function that decodes mobile-uploaded audio (formats: M4A from iOS AVAudioRecorder + WAV/Ogg from Android), resamples to 16 kHz mono 16-bit PCM (canonical Whisper input + smaller storage), strips metadata, returns `(normalized_pcm_bytes, duration_ms, sample_rate_hz)`. Uses Python `wave` module + a pure-Python resampler OR `pydub` if installable cleanly. Trade-off accepted: lossy resampling. Phase 96's `audio_capture.py` uses 44.1 kHz; Phase 195 standardizes on 16 kHz because Whisper expects 16 kHz and the size/quality tradeoff is correct for voice (not music). Backend Commit 0 verifies pydub vs pure-Python alternative at build time.

4. **Route** (`src/motodiag/api/routes/transcripts.py`): NEW. 6 endpoints under `/v1/shop/{shop_id}/work-orders/{wo_id}/transcripts`:
   - `POST` — multipart upload (`file` + `metadata` JSON: `{captured_at, language, preview_text?, preview_engine?, duration_ms}`). Normalizes audio; inserts `voice_transcripts` row; runs sync keyword extraction via `engine/symptoms.categorize_symptoms`; inserts `extracted_symptoms` rows; returns 201 with the full transcript + extracted-symptoms array.
   - `GET` (list) — newest-first by `captured_at`.
   - `GET /{transcript_id}` — single fetch.
   - `PATCH /{transcript_id}/extracted-symptoms/{extracted_id}` — mechanic confirms / edits an extracted symptom (sets `text`, `linked_symptom_id`, `confirmed_by_user_id`, `confirmed_at`).
   - `DELETE /{transcript_id}` — soft-delete the whole transcript + cascade extracted_symptoms.
   - `GET /{transcript_id}/audio` — stream the audio file (returns 410 Gone if `audio_deleted_at IS NOT NULL` from the 60-day sweep).
   All endpoints layer `require_shop_access` on top of `require_tier('shop')` (Phase 193 + Phase 194 pattern). Cross-shop = 403; cross-WO = 404.

5. **Quota** (per Section 1 cost-monitoring + Phase 194 precedent): per-WO 30 transcripts; per-tier monthly aggregate (shop=200/mo, company=unlimited). Same shape as Phase 194; tighter than videos (1 GB / session) since voice is small + frequent.

6. **Keyword extraction (Section 2 γ-substrate)**: in-handler sync call to `engine/symptoms.categorize_symptoms(_split_into_phrases(preview_text))`. The phrase-splitter is a small helper (sentence-boundary regex + comma-clause-splitting). Each categorized phrase becomes one `extracted_symptoms` row with `extraction_method='keyword'`, `confidence=1.0`. Threshold: **explicit lock at plan v1.0 — minimum keyword-coverage score 0.5** (at least half the input phrases must match a category to flag the transcript as "extraction succeeded"; below threshold the transcript is marked `extraction_state='extracted'` with zero rows + a `preview_text` that the mechanic can manually convert via the PATCH endpoint). Calibration plan: validate against a test fixture of 20 mechanic-jargon transcripts at Backend Commit 0 build time; adjust threshold to ≥80% precision (flagged transcripts are truly symptom-bearing) and ≥60% recall (most symptom-bearing transcripts get flagged). If calibration shows the 0.5 floor is wrong, adjust + document the change as Backend-Commit-0 deviation.

7. **60-day audio sweep substrate**: `src/motodiag/media/audio_sweep.py`. NEW pure function `prune_old_audio(now, retention_days=60, db_path)` that:
   - Selects all `voice_transcripts` rows where `created_at < (now - 60 days)` AND `audio_deleted_at IS NULL` AND `deleted_at IS NULL`.
   - For each: `Path(audio_path).unlink(missing_ok=True)` + `UPDATE voice_transcripts SET audio_deleted_at = now WHERE id = ?`.
   - Logs every prune for cost-monitoring telemetry (Risk 8 substrate).
   - Returns `{pruned_count, total_bytes_freed, errors}` for caller observability.

   Wired as a CLI subcommand `motodiag transcripts sweep` (manual trigger; Phase 195B can add cron/scheduler integration). Backend Commit 0 ships the function + CLI + tests; the cron-wiring decision is for 195B.

8. **Tests** (`tests/test_phase195_commit0_voice_transcripts.py`): migration shape; route happy path (upload → 201 with extracted_symptoms); per-WO + monthly quota enforcement; cross-shop 403 + cross-WO 404; auth boundary (401, 402, 403); audio normalization (16 kHz mono PCM round-trip + WAV input + corrupt input → ImageDecodeError-equivalent); keyword extraction integration (transcript with "I noticed a clunk in the front end" produces a 'suspension' / 'noise' category row); 60-day sweep correctness (mtime-bounded fixture: 61-day-old row pruned, 59-day-old preserved, audio_deleted_at TIMESTAMP set); PATCH extracted_symptom mechanic-confirm round trip; soft-delete + cascade.

### Mobile Commit 1 — capture flow + section variant + extracted-symptom UI

1. **`src/hooks/useMicrophonePermissions.ts`** (NEW; factor-out from `useCameraPermissions`): same shape as the camera variant — `{microphone, status, refresh, request}`. Audio-only screens consume this; the existing `useCameraPermissions` continues to gate camera+mic together for video capture (no fork — both hooks share the underlying `Camera.getMicrophonePermissionStatus()` / `Camera.requestMicrophonePermission()` calls; the audio hook just doesn't track camera).

2. **`src/services/audioStorageCache.ts`** (NEW; mirrors `photoStorageCache`): canonical path `${RNFS.DocumentDirectoryPath}/audio/a-{transcriptId}.m4a` (M4A from iOS / Android upload format; backend normalizes to 16 kHz PCM but mobile keeps the original for offline playback). `lookup` / `adopt` / `evict` / `cleanupOrphaned` / `cleanupOldAudio(now, threshold=7d)`. Threshold mirrors Phase 194's 7-day cold-start sweep (mobile-side; bounded so captured-but-never-uploaded orphans don't accumulate).

3. **`src/screens/audioCaptureMachine.ts`** (NEW; pure reducer): 4-state — `idle | recording | uploading | uploaded | upload-failed`. Events: `TAP_RECORD` → recording; `TAP_STOP` (button-tap-to-end per Section K) → uploading (with on-device STT preview text bundled); `UPLOAD_SUCCEEDED(transcript)` → uploaded; `UPLOAD_FAILED(error)` → upload-failed; `TAP_RETRY` → uploading; `TAP_DISCARD` → idle. APP_BACKGROUNDED handling: recording → upload-failed (mirrors Phase 191B's videoCaptureMachine pattern; iOS suspends mic on background).

4. **`src/screens/VoiceCaptureScreen.tsx`** (NEW): mounts `react-native-audio-recorder-player` for raw audio capture + `@react-native-voice/voice` for parallel on-device STT preview. UX: button-tap-to-start (opens mic, starts both record + STT); during recording shows live preview transcript text + elapsed timer + waveform-or-just-pulse visual; button-tap-to-stop (ends both, transitions to uploading). Permission gate uses `useMicrophonePermissions`. Errors classify via `ShopAccessError` 5-kind union.

5. **`src/hooks/useWorkOrderTranscripts.ts`** (NEW; mirrors `useWorkOrderPhotos`): backend-backed CRUD. Returns `{transcripts, isLoading, error, refresh, addTranscript, updateExtractedSymptom, deleteTranscript, atCap}`. `addTranscript({sourceUri, capturedAt, durationMs, language, previewText, previewEngine})` does multipart POST. `updateExtractedSymptom(transcriptId, extractedId, {text?, linked_symptom_id?})` does PATCH (mechanic confirm/edit). Typed errors via `ShopAccessError`.

6. **`src/types/workOrder.ts`** (extend): add `WorkOrderTranscriptsSection` variant + `WorkOrderTranscript` + `ExtractedSymptom` interfaces + `isTranscriptsSection` type guard. Discriminated union 6 → 7 variants.

7. **`src/screens/buildWorkOrderSections.ts`** (extend): add `transcripts: WorkOrderTranscript[] = []` 5th positional parameter. Section placement: BETWEEN photos and lifecycle (consistent with "documentation media first, bookkeeping last" UX rule from Phase 194). Omit-when-empty.

8. **`src/components/WorkOrderSectionCard.tsx`** (extend): add `_renderTranscripts` branch — timeline-with-extracted-symptom-chips layout. Each transcript renders: captured_at + duration timestamp header; preview_text body (italic; "still refining…" indicator if extraction_state === 'pending' or 'extracting'); extracted_symptoms array as clickable chips (tap to navigate to TranscriptReviewScreen for confirm/edit). NO preemptive refactor of the renderer architecture (Section 4 trust-but-verify); 3rd layout idiom is component-level additive, not architectural.

9. **`src/screens/TranscriptReviewScreen.tsx`** (NEW; Mobile Commit 2): the per-transcript review surface. Shows full preview_text + audio playback button (uses `audioStorageCache` lookup) + each extracted_symptom as an editable row (tap to edit text, tap to pick a `linked_symptom_id` from KB catalog via a search picker, tap to confirm). Confirm action calls `useWorkOrderTranscripts.updateExtractedSymptom`.

10. **Tests** (mobile, ~30 net new across 6 files): pure-logic for `audioCaptureMachine` reducer (state transitions + edge cases including APP_BACKGROUNDED); `audioStorageCache` (lookup/adopt/evict/cleanupOldAudio with 7-day boundary mirroring Phase 194's `cleanupOldPhotos` test discipline); type-guard test for `isTranscriptsSection`; `buildWorkOrderSections` extension test (transcripts variant slots in correctly + omit-when-empty); `WorkOrderSectionCard` smoke test for the new variant (heading "Voice memos" + extracted-symptom chip rendering); `useWorkOrderTranscripts` hook tests (multipart shape + ShopAccessError classification round trips).

### Mobile Commit 2 — entry-point + nav + smoke gate + finalize

1. **Entry-point card on `WorkOrderDetailScreen`**: parallel to Phase 194's "Take photo" card. Title "Voice memos"; subtitle "Describe symptoms hands-free; we'll extract them automatically"; "Record voice memo" button → navigates to `VoiceCaptureScreen`.

2. **Nav wiring**: `ShopStackParamList += {VoiceCapture, TranscriptReview}` with typed params `{shopId: number, woId: number, issueId?: number}` and `{shopId: number, woId: number, transcriptId: number}` respectively. `ShopStack.tsx` registers both new screens.

3. **8-step smoke gate** (Section 9 + Section J cadence):
   1. Tap "Record voice memo" → mic permission flow → button-tap-to-start → recording (live preview text appears) → button-tap-to-stop → upload → transcript with extracted_symptoms appears in WorkOrderTranscriptsSection.
   2. Capture "I noticed a clunk in the front end at low speed" → keyword extraction yields a 'suspension' or 'noise'-category row → chip renders in section.
   3. Capture nonsensical-noise → no extracted symptoms → transcript renders with preview_text + "no symptoms extracted" empty-state.
   4. Free-tier user → 402 with informational copy.
   5. Cross-shop deep-link → 403.
   6. Permanently-denied permission → settings link affordance (audio-only flow).
   7. Tap an extracted-symptom chip → TranscriptReviewScreen → edit/confirm → backend PATCH → chip re-renders confirmed.
   8. WorkOrderSection variant integration smoke — transcripts variant renders alongside vehicle / customer / issues / notes / photos / lifecycle without breaking. **Section E load-bearing test #2**.

4. **F-ticket dispositions at finalize**:
   - F33 audit ran first per CLAUDE.md Step 0 — substantial reuse confirmed; on-device-STT-coexists-with-Phase-96-audio-infrastructure narrative locked.
   - F37 (extend F33 to enum-value verification): track during execution. Phase 195 introduces 4 enums — `transcripts.language` (ISO 639-1+region), `transcripts.preview_engine`, `transcripts.extraction_state`, `extracted_symptoms.extraction_method`. If a backend↔mobile mismatch surfaces, that's instance #3 → F37 escalation.
   - F38 (NEW, filed at plan-write): unify symptom storage across `diagnostic_sessions.symptoms` (JSON list) + `voice_transcripts.extracted_symptoms` (relational) + future OBD-captured symptoms. Promotion trigger documented above.
   - F-ticket "cloud Whisper as Phase 195C" reserved IF the substrate ships and field-validates (Section 3 substrate-feature split decision NOT to ship 195B together, but the 195B ticket is pre-filed in this plan).

## Key Concepts

- **Substrate-feature split (Section 3)**: Phase 195 ships substrate (capture + audio storage + on-device preview + canonical-shape + keyword extraction + variant); **Phase 195B** ships the AI feature (cloud Whisper + Claude-rich extraction + cost monitoring + VAD). The split mirrors 191/191B + 192/192B + 194/194B precedent. Bundling = 191B-saga risk.
- **Hybrid transcription (Section 1)**: on-device STT for instant UI feedback + cloud Whisper for canonical record (195B). Phase 195 ships only the on-device half + the audio-storage substrate that 195B needs to consume.
- **60-day audio retention (Section 5)**: bytes pruned by sweep at 60 days; transcripts permanent. Phase 192B's share-temp + Phase 194's cleanupOldPhotos pattern. Privacy posture: "we hold for N days then delete" + audio retained enables re-transcription / mechanic verification / Phase 96 cross-pollination.
- **Keyword extraction reuses `engine/symptoms.categorize_symptoms`** — no new module. Threshold: minimum 0.5 keyword-coverage at plan-write; calibration against 20-jargon-fixture at Backend Commit 0 build time; adjusted with deviation note if calibration shows different value is correct.
- **Extracted symptoms as relational rows** (NOT JSON list on the transcript). Forward-investment — Phase 196 + future query patterns + manual-edit-confirmation all benefit from relational shape. F38 NEW for future cross-source unification.
- **`source TEXT NULL`** on `voice_transcripts` + `extracted_symptoms` — forward-investment narrow scope. Phase 195 leaves NULL; Phase 196 OBD populates `'obd'`; manual-symptom retroactive backfill (if F38 promotes) populates `'manual'`.
- **ISO 639-1 with region** (`'en-US'`, `'es-MX'`) on `language` column — Whisper + iOS Speech both use locale-with-region; storing without region loses information re-transcription would need.
- **Section E load-bearing test #2**: voice transcripts are time-series with extracted-output, structurally different from photos. Renderer adds 3rd layout idiom (timeline view); builder adds 5th positional param. NO preemptive refactor — wait for actual implementation friction (Section 4 trust-but-verify).
- **Two new mobile deps** (`@react-native-voice/voice` + `react-native-audio-recorder-player`); zero new backend deps in Phase 195; Phase 195B will add `openai>=1.0` for Whisper.

## Section K — Audio capture ergonomics in shop environments

Pre-plan-time decisions for shop-floor realities:

1. **Background noise**: shops are loud (compressors, power tools, music). On-device STT struggles in this environment; cloud Whisper handles it materially better. **Validates the (c) hybrid transcription decision (Section 1)** — on-device preview WILL surface mistranscriptions in noisy environments; cloud Whisper canonical (195B) corrects them. Phase 195 ships acknowledging on-device preview is best-effort, NOT canonical.
2. **Microphone selection**: Bluetooth headsets common in hands-busy shop work; integrated phone mic varies by device. Audio quality is microphone-dependent; STT accuracy bounded accordingly. **Out of scope for Phase 195. F-ticket "configurable input device selection" if it surfaces during smoke gate or post-launch.**
3. **Recording UI affordance**: button-tap-to-start-and-stop (Phase 195 — simple, mechanic-friendly, predictable). VAD (voice activity detection — auto-stop on N seconds of silence) is a 195B concern (continuous-recording UX needs more sophisticated state machine + iOS Speech 1-min cap workaround). Phase 195 sticks with explicit start/stop.
4. **Privacy posture for retained audio**: a recorded voice memo may capture nearby customer conversations / shop-floor banter even if those weren't part of the symptom description. Document in privacy posture: "voice memos are retained for 60 days for verification / re-transcription; only the symptom description should be the focus of the recording." **F-ticket "selective audio retention" (e.g., trim audio to active-recording-window only) IF customer-conversation-capture becomes a load-bearing concern.**

## Verification Checklist

- [ ] Backend migration creates `voice_transcripts` (22 columns) + `extracted_symptoms` (12 columns) + 7 indexes + correct FK posture (`work_orders` CASCADE, `issues`/`linked_symptom_id` SET NULL, `users` SET DEFAULT/SET NULL, `transcripts.id` CASCADE for extracted_symptoms).
- [ ] Backend `transcript_repo.py` + `extracted_symptom_repo.py` ship CRUD + quota helpers + `update_extraction_state` + `confirm_extracted_symptom`.
- [ ] Backend `audio_pipeline.normalize_audio` decodes M4A/WAV/Ogg → 16 kHz mono 16-bit PCM; pure function; tested with each input format + corrupt input.
- [ ] Backend `POST /v1/shop/{shop_id}/work-orders/{wo_id}/transcripts` route accepts multipart `(file, metadata)`, normalizes, stores at canonical path, runs sync keyword extraction, returns 201 with transcript + extracted_symptoms.
- [ ] Backend per-WO 30 + per-tier monthly 200 quota enforcement; 402 / `transcript-quota-exceeded`.
- [ ] Backend `extraction_state` CHECK constraint + `extraction_method` CHECK constraint enforced.
- [ ] Backend 401/402/403/404 auth boundary tests pass.
- [ ] Backend keyword extraction threshold calibrated against 20-jargon test fixture; threshold value documented (0.5 default; adjusted if calibration shows different).
- [ ] Backend `audio_sweep.prune_old_audio(now, retention_days=60)` correctness — 61-day-old row pruned, 59-day-old preserved, audio_deleted_at TIMESTAMP set, missing-file no-op (already swept).
- [ ] Mobile `useMicrophonePermissions` factored out cleanly from `useCameraPermissions`; no fork (shared underlying calls).
- [ ] Mobile `audioStorageCache` mirrors `photoStorageCache` shape; 7-day cold-start sweep wired into App.tsx.
- [ ] Mobile `audioCaptureMachine` 4-state reducer covers all transitions + APP_BACKGROUNDED handling.
- [ ] Mobile `VoiceCaptureScreen` button-tap-to-start-and-stop affordance; live preview text from `@react-native-voice/voice`; mic-only permission gate.
- [ ] Mobile `useWorkOrderTranscripts` hook returns `{transcripts, isLoading, error, refresh, addTranscript, updateExtractedSymptom, deleteTranscript, atCap}` with `ShopAccessError` typed errors.
- [ ] Mobile `WorkOrderTranscriptsSection` variant added to discriminated union; `isTranscriptsSection` + builder branch + renderer branch all wired.
- [ ] Mobile renderer: timeline-with-extracted-symptom-chips layout; "refining…" indicator while extraction_state pending; tap-chip-to-edit nav.
- [ ] Mobile `TranscriptReviewScreen` lets mechanic edit / confirm extracted_symptoms + select `linked_symptom_id` from KB catalog.
- [ ] All 8 architect-smoke steps documented; Steps 1-7 hook + helper unit tests; Step 8 (variant integration) concretely tested via WorkOrderSectionCard smoke test.
- [ ] All doc + package version bumps recorded.
- [ ] F-ticket dispositions: F37 watched during execution; F38 NEW filed at plan-write; F-ticket "cloud Whisper as Phase 195C" reserved (or just "Phase 195B is the next ROADMAP entry" as the disposition).

## Risks

1. **`@react-native-voice/voice` compat with RN 0.85 + New Architecture (Fabric)**. Verify at Mobile Commit 1 build start. If incompat, fall back to `react-native-speech-recognizer` or implement minimal native module wrapping iOS Speech / Android SpeechRecognizer directly.
2. **iOS Speech 1-minute session cap**. Mechanic talking through complex bike issue can run over. Mitigation: `requiresOnDeviceRecognition: true` on iOS 13+ supports continuous recognition (no cloud round-trip, no 1-min cap). Verify availability at Mobile Commit 1; if absent, chunk-and-restart with overlap.
3. **Background recording on iOS**. App backgrounded mid-recording → iOS suspends mic. UI must handle gracefully. Same posture as `VideoCaptureScreen` APP_BACKGROUNDED → upload-failed.
4. **Keyword dict coverage** (`engine/symptoms.SYMPTOM_CATEGORIES` is incomplete). Phase 195 keyword extraction is bounded by the dict. Mitigation: Phase 195B Claude-fallback covers gaps; Phase 195 surfaces the gap in the empty-state message ("no symptoms extracted — tap to add manually").
5. **Section E load-bearing test #2**. If `buildWorkOrderSections` extension to a 5th positional param feels like proliferation, surface as architectural finding (plan v1.1 amendment slot reserved). Don't preemptively refactor — wait for actual pain (Section 4 trust-but-verify).
6. **Microphone-only flow doesn't exist on mobile yet**. `useCameraPermissions` is combined-cam-mic gate; factor out `useMicrophonePermissions` cleanly without forking.
7. **F37 instance #3 watch**. Phase 195 introduces 4 enums; backend↔mobile mismatch on any of them surfaces F37.
8. **Cloud-transcription cost monitoring substrate** (per Section 1 hybrid + Risk 8 lock). Phase 195 backend ships per-route invocation logging at INFO level (Risk 8 substrate); the cost-aggregation dashboard is a Phase 195B concern, but the LOGS exist from day one so a `grep cost_usd_cents motodiag.log` at any time after launch surfaces unexpected burn.
9. **Audio file sweep correctness** (per Section 5 retention + Risk 9 lock). Same testing discipline as Phase 192B's share-temp sweep — exact-threshold cases (60 days exactly; 60 days minus 1 second; 60 days plus 1 second), missing-file no-op, sweep-failure recovery. Phase 192B Mobile Commit 2 cleanup test suite is the template.
10. **Audio normalization library availability**. `pydub` is the cleanest path but requires ffmpeg at runtime (already a Phase 191B dependency for video frames). Pure-Python alternatives exist (`scipy.signal.resample` if scipy is acceptable; manual linear interpolation if not). Backend Commit 0 verifies; if neither path works, document as Backend Commit 0 deviation + temporarily store original-format audio (not normalized) until 195B can revisit.

## Phase 195 explicitly NOT taking on

- **Cloud Whisper integration** (deferred to Phase 195B per Section 3 split).
- **Claude-rich extraction prompt-engineering** (Phase 195B; Phase 195 ships keyword-only).
- **Cost monitoring dashboard / aggregation** (Phase 195B; Phase 195 ships per-route logging substrate only).
- **Voice activity detection (VAD) / auto-stop** (Phase 195B per Section K; Phase 195 ships explicit start/stop).
- **Multilingual symptom extraction** (English-only-now; schema-i18n-ready; F-ticket future).
- **`diagnostic_sessions.symptoms` JSON-list → relational migration** (deferred to F38 future phase).
- **Configurable mic-input-device selection** (out of scope per Section K; F-ticket if surfaces).
- **Selective audio retention / trimming** (out of scope per Section K privacy concern; F-ticket if customer-conversation-capture becomes load-bearing).
