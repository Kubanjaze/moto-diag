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
