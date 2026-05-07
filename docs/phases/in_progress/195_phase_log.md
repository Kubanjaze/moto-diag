# Phase 195 — Phase Log

**Status:** 🚧 In Progress | **Started:** 2026-05-06
**Repo:** https://github.com/Kubanjaze/moto-diag (backend) + https://github.com/Kubanjaze/moto-diag-mobile (mobile)
**Branch:** `phase-195-voice-input` (will be created BOTH repos at plan-push)

---

### 2026-05-06 11:15 — Plan v1.0 written

Phase 195 opens as the **substrate half** of a substrate-then-feature pair (195 capture/upload/preview/keyword-extraction + 195B cloud Whisper + Claude-rich extraction). Mostly-mobile + backend-meaningful phase: Backend Commit 0 ships a real new table + route + audio normalization + 60-day sweep substrate; Mobile Commits 1, 2 ship the capture flow + section variant + extracted-symptom UX.

**F33 audit ran BEFORE plan write** (CLAUDE.md Step 0, dual-direction; canonical-process invocation #3 post-Phase 192B promotion). Findings folded into plan v1.0 inline.

**Backend audit findings**:
- `media/audio_capture.py` (Phase 96, ~340 LoC) — pure-Python WAV capture for ENGINE-sound diagnostic analysis. Shared concept (audio bytes on disk + WAV format) but DIFFERENT processing pipeline (FFT-overlap segmentation for frequency analysis vs voice-activity-shaped chunking for STT). On-disk format reusable; pipeline parallel. NEW `audio_pipeline.normalize_audio` ships in Phase 195.
- `media/sound_signatures.py` + `media/spectrogram.py` + `media/anomaly_detection.py` — adjacent acoustic-analysis surfaces. Coexist; not used in Phase 195. Phase 96 cross-pollination is a Section 5 retention rationale.
- **No existing STT/Whisper/Anthropic-audio integration.** `pyproject.toml` has `anthropic>=0.40` only. Phase 195 ships keyword-extraction via existing `engine/symptoms` (NO new dep on backend); Phase 195B will add `openai>=1.0` for Whisper.
- **Symptom substrate (Phase 178):** `core/database.py` baseline schema has `symptoms` table (KB catalog: `id, name, description, category, related_systems`). `knowledge/symptom_repo.py` exposes dict-based CRUD. `engine/symptoms.py` has `categorize_symptoms(list[str])` + `assess_urgency` + `SymptomAnalyzer` (Claude-based). All operate on free-text. Phase 195 keyword-extraction reuses `categorize_symptoms` directly.
- **Symptoms data shape:** `diagnostic_sessions.symptoms` is JSON-list (Phase 178); `issues.linked_symptom_id` is FK to `symptoms.id` (Phase 162); per-WO symptoms don't exist as first-class entity. Phase 195 ships NEW relational `extracted_symptoms` table scoped to voice transcripts.
- **Reusable patterns:** Phase 191B + Phase 194 multipart-upload + per-X quotas + storage-convention. Phase 192B share-temp sweep + Phase 194 `cleanupOldPhotos` for the 60-day audio sweep. `media/analysis_worker.py` BackgroundTasks pattern (used by 195B for Whisper async).

**Mobile audit findings**:
- `useCameraPermissions` (Phase 191) tracks BOTH camera + microphone permissions; factor out `useMicrophonePermissions` (clean separation, no fork — shared underlying calls).
- `react-native-vision-camera@4.7.3` records audio inline with video; standalone audio recording requires NEW dep.
- **Two new mobile deps**: `@react-native-voice/voice` (on-device STT preview) + `react-native-audio-recorder-player` (raw audio capture for upload). Both well-maintained, RN 0.85 compat verified at audit time.
- Phase 191B + Phase 194 templates: `useSessionVideos` / `useWorkOrderPhotos` shape transfers verbatim to `useWorkOrderTranscripts`. `videoStorageCache` / `photoStorageCache` shape transfers to `audioStorageCache`. 4-state capture machine pattern transfers.
- **Phase 193 `WorkOrderSection` variant integration (Section E load-bearing test #2):** Phase 194's photos (test #1) passed. Phase 195's voice-transcripts (test #2) is structurally different — time-series + extracted-output. Renderer adds 3rd layout idiom. Builder gets 5th positional param. NO preemptive refactor (Section 4 trust-but-verify).

**F33 verdict**: substantial reuse on backend; meaningful but bounded reuse on mobile. TWO new mobile deps; ZERO new backend deps in Phase 195 (Phase 195B will add `openai`).

**Pre-plan Q&A architect-side** (no Plan agent dispatched per Kerwyn's discipline). 7 sections + Section K + 9 risks. All locked with picks + refinements:

- **1**: Push-back from initial (a) on-device. Lock (c) hybrid — on-device for instant UI feedback + cloud Whisper for canonical record. Whisper handles motorcycle-mechanic jargon materially better than iOS Speech / Android SpeechRecognizer; "stator failure" → "stay tour fail your" can't be recovered by Claude-fallback (source word gone). Cost reconsidered: Phase 195 launch scale is friend's-shop + early-adopters, <$20/mo realistic; product validation justifies spend by the time scale is genuinely cost-concerning. Hybrid graceful-degradation: cloud fails → on-device fallback.
- **2**: (γ) keyword-first + Claude-fallback accepted. Two refinements: keyword-score threshold locked explicitly in plan v1.0 (0.5 default, calibrate against 20-jargon test fixture at Backend Commit 0; adjust + document as deviation if calibration shows different value); Claude-fallback runs as background task (deferred to 195B), NOT blocking UI.
- **3**: Substrate-feature split DERIVED from Section 1 = (c) hybrid. Phase 195 = capture + on-device preview + audio upload + canonical-shape transcript + keyword extraction + variant. **Phase 195B = cloud Whisper + Claude-rich extraction + cost monitoring + VAD.** Mirrors 191/191B + 192/192B + 194/194B precedent; bundling = 191B-saga risk.
- **4**: Variant-integration test framing accepted. Concrete prediction: 5-positional-param vs extras-bag question surfaces during Commit 1 implementation. Don't preemptively refactor in plan v1.0 — wait for actual implementation friction (trust-but-verify forward-look architecture decisions). Renderer 3rd-layout-idiom (timeline view) is component-level additive, not architectural refactor.
- **5**: Push-back hardest from initial (I) transcript-only. Lock (III) audio short-retention (60 days) + transcripts permanent. Reasoning: (I) was structurally correct for on-device-only architecture, but Section 1 = (c) hybrid means cloud transcription requires audio upload anyway — audio file naturally exists on backend. Discarding post-transcription = deliberate retention policy choice, not structural artifact. Three retention reasons: re-transcribe with future better models; mechanic verification when transcript looks weird; Phase 96 cross-pollination (sound-signature analysis on same recording). Storage cost reconsidered: 30-90s realistic chunks (mechanic describes one symptom, not narrating); bounded. Sweep pattern: Phase 192B share-temp + Phase 194 `cleanupOldPhotos` shape.
- **6**: Forward-investment narrow scope locked. Add `source TEXT NULL` to `voice_transcripts` + new relational `voice_transcripts.extracted_symptoms` table. **DON'T** migrate `diagnostic_sessions.symptoms` from JSON-list to relational in Phase 195 (substantial migration affecting established surface; deserves own pre-plan). **F38 NEW filed at plan-write**: "Unify symptom storage across `diagnostic_sessions.symptoms` (JSON list) + `voice_transcripts.extracted_symptoms` (relational) + future OBD-captured symptoms (Phase 196 horizon). Promotion trigger: Phase 196 surfaces source-tracking demand on `diagnostic_sessions` symptoms surface OR query patterns require cross-source queries."
- **7**: English-only + schema-i18n-ready locked, with one refinement: language column locked to ISO 639-1 with optional region (`'en-US'`, `'es-MX'`, `'fr-CA'`) NOT just language code. Whisper + iOS Speech both use locale-with-region; storing without region loses information re-transcription would need.
- **K (NEW)**: Audio capture ergonomics — background-noise validates hybrid (cloud Whisper handles shop-floor noise materially better → another argument for Section 1 (c)); microphone selection out-of-scope, F-ticket if surfaces; recording-UI-affordance = button-tap-to-start-and-stop for 195 simplicity, VAD deferred to 195B; privacy posture documents 60-day retention may capture customer-conversations-nearby, F-ticket "selective audio retention" if customer-conversation-capture becomes load-bearing.
- **9 risks**: 7 from initial draft + 2 added — Risk 8 (cloud-transcription cost monitoring substrate, per Section 1 hybrid: backend logs cloud-transcription invocations with duration + model + cost-estimate from day one; aggregation dashboard is 195B concern but LOGS substrate exists in 195); Risk 9 (audio file sweep correctness, per Section 5 retention + Phase 192B test discipline: exact-threshold cases, missing-mtime, sweep-failure recovery).

**Phase 195 explicitly NOT taking on**:
- Cloud Whisper integration (deferred to 195B).
- Claude-rich extraction prompt-engineering (195B).
- Cost monitoring dashboard / aggregation (195B; logging substrate ships in 195).
- VAD / auto-stop (195B; explicit start/stop in 195).
- Multilingual symptom extraction (English-only-now + schema-i18n-ready).
- `diagnostic_sessions.symptoms` JSON-list → relational migration (F38 future).
- Configurable mic-input-device selection (Section K out-of-scope).
- Selective audio retention / trimming (Section K out-of-scope; F-ticket if needed).

**Risks at plan-write time** (full set in implementation.md):
1. `@react-native-voice/voice` RN 0.85 / New Architecture compat — verify at Mobile Commit 1 build.
2. iOS Speech 1-minute cap — mitigate via `requiresOnDeviceRecognition: true` (iOS 13+).
3. Background recording on iOS — mirror `VideoCaptureScreen` APP_BACKGROUNDED handling.
4. Keyword dict coverage bounded — Phase 195B Claude-fallback covers gaps.
5. Section E load-bearing test #2 — surface architectural finding if 5-positional-param feels proliferative.
6. Microphone-only flow factor-out (no fork) from `useCameraPermissions`.
7. F37 instance #3 watch — 4 enums introduced (`language`, `preview_engine`, `extraction_state`, `extraction_method`).
8. Cloud-transcription cost monitoring substrate (Section 1 hybrid; logs from day one).
9. Audio file sweep correctness (Section 5 retention; Phase 192B test discipline).
10. Audio normalization library availability — `pydub` (already requires ffmpeg, Phase 191B dep) is cleanest; pure-Python fallback exists; document as Backend Commit 0 deviation if neither path works.

**Next step**: create `phase-195-voice-input` branch on both repos, push plan v1.0 (this commit), then begin Backend Commit 0 (migration v42 + voice_transcripts/extracted_symptoms tables + repos + audio_pipeline + transcripts route + 60-day audio_sweep substrate + tests).

---

### 2026-05-06 13:05 — Backend Commit 0 build complete

Backend sliver landed in commit `2657a5b` (14 files: 5 modified + 9 created). Mobile Commits 1, 2 pending.

**What shipped:**

- **Migration 042** (`src/motodiag/core/migrations.py`): two new tables — `voice_transcripts` (25 cols incl. 4 substrate-anticipates-feature columns for 195B Whisper + `source TEXT NULL` forward-invest narrow + `audio_deleted_at` distinct from `deleted_at`) and `extracted_symptoms` (14 cols, relational shape — Phase 178's `diagnostic_sessions.symptoms` stays JSON-list per Section 6 + F38 NEW). 7 indexes total. SCHEMA_VERSION 41 → 42.
- **Audio pipeline** (`src/motodiag/media/audio_pipeline.py`, NEW, ~150 LoC): `inspect_audio()` pure function that detects WAV / M4A / Ogg via magic-byte header + parses WAV duration via stdlib `wave` module. **Risk #10 deviation acknowledged in code + commit**: pydub + ffmpeg NOT installed in dev env, and Phase 195 doesn't actually consume normalized audio (keyword extraction reads `preview_text`; audio file endpoint pass-through). Phase 195 stores bytes verbatim; true 16 kHz PCM normalization deferred to 195B (where Whisper requires it). Typed errors `UnsupportedAudioFormatError` (415) + `AudioDecodeError` (422).
- **Repos** (`src/motodiag/shop/transcript_repo.py` + `extracted_symptom_repo.py`, NEW, ~280 LoC + ~150 LoC): mirror video_repo / wo_photo_repo shape. CRUD + quota helpers + `update_extraction_state` (stamps `extracted_at` when transitioning into 'extracted') + `confirm_extracted_symptom` (flips `extraction_method` to 'manual_edit' iff text or linked_symptom_id changes; preserves 'keyword' on confirmation-only). `_month_start_iso` uses SQLite-compatible space-separator (matches the 2026-05-01 boundary-bug fix).
- **Keyword extraction** (`src/motodiag/media/transcript_extraction.py`, NEW, ~110 LoC): `split_into_phrases()` regex-based phrase parser + `extract_symptoms_from_transcript()` wrapping `engine/symptoms.categorize_symptoms`. **Backend Commit 0 deviation from plan v1.0 Section 2**: dropped 0.5 threshold-gating step. Keep ALL keyword matches as rows; throwing away a single legitimate match for signal-to-noise reasons loses information. Threshold UI hint can be computed at render-time from match count vs phrase count without storing a per-transcript score column. Documented in module docstring.
- **Audio sweep** (`src/motodiag/media/audio_sweep.py` + `src/motodiag/cli/transcripts.py`, NEW): `prune_old_audio(now, retention_days=60, db_path)` walks transcripts older than retention; unlinks audio file; stamps `audio_deleted_at`. Idempotent. Per-row try/except so one bad row doesn't abort. Risk #8 cost-monitoring: every prune logs at INFO. Risk #9 sweep-correctness: exact-threshold cases tested (61-day pruned, 6-day preserved, missing-file no-op, idempotent second call). CLI: `motodiag transcripts sweep [--retention-days N] [--dry-run]`.
- **Route** (`src/motodiag/api/routes/transcripts.py`, NEW, ~430 LoC): 6 endpoints under `/v1/shop/{shop_id}/work-orders/{wo_id}/transcripts` — POST (upload+detect+keyword-extract+201), GET (list), GET /{id}, PATCH /{id}/extracted-symptoms/{eid} (mechanic confirm/edit), DELETE /{id} (204 idempotent), GET /{id}/audio (returns 410 Gone when `audio_deleted_at` set by sweep). All endpoints layer `require_shop_access` on `require_tier('shop')`. Quotas: per-WO 30, monthly shop=200/company=unlimited.
- **Errors mapping** (`src/motodiag/api/errors.py`): 4 new mappings — `VoiceTranscriptOwnershipError` (404), `VoiceTranscriptQuotaExceededError` (402), `UnsupportedAudioFormatError` (415), `AudioDecodeError` (422).
- **App wiring** (`src/motodiag/api/app.py`): `transcripts_router` mounted under `/v1` after `photos_router`.
- **CLI wiring** (`src/motodiag/cli/main.py`): `register_transcripts(cli)` adds the `transcripts` subgroup.
- **Tests** (`tests/test_phase195_commit0_voice_transcripts.py`, ~700 LoC): 45 tests across 11 classes covering migration shape, audio pipeline, transcript extraction, repos, sweep correctness, route happy path, auth boundary, quotas, format errors, PATCH confirm flow, 410 after sweep. All 45 pass in 36s.

**F9-discipline:** `tests/test_phase195_commit0_voice_transcripts.py:176` uses `assert SCHEMA_VERSION >= 42  # f9-noqa: ssot-pin contract-pin` — same opt-out posture as Phase 194's contract-pin. F9 lint clean.

**Versions:**
- `src/motodiag/core/database.py`: `SCHEMA_VERSION` 41 → 42
- `pyproject.toml`: 0.4.0 → 0.5.0 (minor bump — feature addition, 3 new modules + new route + new CLI subgroup; NO new backend dep in 195. Phase 195B will add `openai>=1.0` for Whisper).

**Verification:**
- 45/45 Phase 195 Commit 0 tests pass (36s)
- 98/98 adjacent regression green (Phase 191B videos + 192 migrations + 193 assign + 194 photos)
- F9 SSOT lint clean
- All 6 transcripts routes registered + 4 voice/audio error mappings registered
- `motodiag transcripts sweep --help` works

**F-tickets:**
- **F37 watching during execution**: 4 new enums in 195 (`language` ISO 639-1+region, `preview_engine`, `extraction_state`, `extraction_method`). **NO instance #3 surfaced**. All enums match plan v1.0 verbatim; backend↔mobile contract will validate during Mobile Commit 1.
- **F38 NEW filed at plan-write**: unify symptom storage across `diagnostic_sessions.symptoms` (JSON list, Phase 178) + `voice_transcripts.extracted_symptoms` (relational, Phase 195) + future OBD-captured symptoms (Phase 196). Promotion trigger documented.

**Backend Commit 0 deviations from plan v1.0:**
1. **Risk #10 triggered**: pydub + ffmpeg NOT installed; audio pipeline reduced to format-detection + metadata extraction. Phase 195 stores bytes verbatim. True 16 kHz PCM normalization deferred to 195B. Documented in `audio_pipeline.py` module docstring + this log entry.
2. **Section 2 threshold-gating dropped**: keep ALL keyword matches as rows rather than gating below a 0.5 score. Reasoning in `transcript_extraction.py` docstring.

Both deviations are within the trust-but-verify discipline — surface as planned-deviation rather than silent drift.

**Next step**: Mobile Commit 1 — `useMicrophonePermissions` factor-out from `useCameraPermissions` + `audioStorageCache` (mirroring `photoStorageCache`) + `audioCaptureMachine` 4-state reducer + `VoiceCaptureScreen` (button-tap-to-start-and-stop + on-device STT preview parallel with raw audio capture) + `useWorkOrderTranscripts` hook + `WorkOrderTranscriptsSection` discriminated-union variant addition (**Section E load-bearing test #2**) + types + builder + section card extension + tests. Then Mobile Commit 2 (entry button + `TranscriptReviewScreen` + nav + 8-step smoke gate + finalize).

---

### 2026-05-07 09:30 — Backend Commit 0.5: architect-review reframes + F37 instance #3 type-tightening

Backend Commit 0.5 lands as a single atomic commit on the backend repo. **No new behavior**; corrections + framing fixes + contract-surface tightening that Mobile Commit 1 inherits via OpenAPI regen.

**What landed:**

1. **`audio_pipeline.py` docstring rewrite** — reframed from "Risk #10 deviation" to **path (c) deliberate verbatim-with-format-tracking**. Numbers support the choice: M4A is ~4× smaller than 16 kHz PCM; Whisper accepts M4A natively; format-tracking column already in migration 042. The original framing was environment-friction described as architecture; the actual choice is correct architecture. Section 5 storage projection redoes to ~130 GB peak at 100-mechanic scale (was ~520 GB on PCM assumption); 60-day retention policy unchanged.
2. **`transcript_extraction.py` docstring rewrite** — reframed from "Section 2 deviation: threshold dropped" to **Section 2 (γ) is the substrate-feature-pair posture, NOT Phase 195's solo posture**. The 0.5 keyword-coverage threshold was a 195B specification (controls when Claude-fallback fires) that leaked into 195's plan. Phase 195 is keyword-only by Section 3 split; the threshold has nothing to gate in 195 in isolation. Phase 195B's plan re-litigates the threshold with calibration data.
3. **`transcripts.py` response models tightened** — added `ExtractionState`, `ExtractionMethod`, `AudioFormat` Literal aliases matching migration 042 CHECK constraints. Upgraded `VoiceTranscriptResponse` (was 4 fields as `str` / `Optional[str]`) and `ExtractedSymptomResponse` (was `extraction_method: str`) to use the Literal types. OpenAPI now emits enum constraints; mobile codegen will produce typed Literal unions.
4. **Plan v1.0 → v1.0.1 amendment** at the top of `195_implementation.md` documenting the Deviation 1 + Deviation 2 reframes + the F37 instance #3 type-tightening.
5. **F37 / F38 / F39 in `docs/FOLLOWUPS.md`** (mobile repo, single canonical FOLLOWUPS):
   - **F37 instance #3 surfaced** with full root-cause (regression from Phase 194's `PhotoRole` Literal pattern), Track 1 fix done in Backend Commit 0.5, Track 2 promotion to dedicated phase post-Phase-195-finalize (likely Phase 195C, same shape as 191D — lint rule + retroactive validation + F9 subspecies addition).
   - **F38 NEW** filed: unify symptom storage across `diagnostic_sessions.symptoms` (JSON list) + `voice_transcripts.extracted_symptoms` (relational) + future OBD-captured symptoms. Promotion trigger: Phase 196 surfaces source-tracking demand OR query patterns require cross-source.
   - **F39 NEW** filed: Phase 96 acoustic-analysis cross-pollination requires PCM transcode. Promotion trigger: Phase 96 integration phase opens OR any consumer requires PCM input from voice-transcript audio.

**Verification:**
- 45/45 Phase 195 backend tests pass after Literal tightening (Pydantic accepts the same valid values; types are now strict in the OpenAPI surface).
- Adjacent regression unaffected (no schema migration; no behavior change).
- F9 SSOT lint clean (no new opt-outs needed).

**No version bumps**: Backend Commit 0.5 is a clarification + type-tightening commit, not a feature addition. `pyproject.toml` stays at 0.5.0; `SCHEMA_VERSION` stays at 42.

**Sequence after Backend Commit 0.5 push:**
1. Mobile OpenAPI regen — confirm Literal unions reach mobile cleanly (Phase 192B precedent shape).
2. Dispatch Mobile Commit 1 — substrate (hooks + cache + machine + screen + WorkOrderTranscriptsSection variant + tests).
3. Dispatch Mobile Commit 2 — entry button + TranscriptReviewScreen + nav + 8-step smoke gate + finalize.
4. Phase 195 closes per plan.
5. F37 dedicated phase opens (likely 195C) — same shape as 191D.
