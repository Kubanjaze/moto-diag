# Phase 195B — Voice Symptom: Cloud Whisper + Claude-Rich Extraction (feature half)

**Version:** 1.1 (final) | **Tier:** Standard | **Date:** 2026-05-16

## Goal

Ship the **feature half** of the 195/195B substrate-then-feature pair. Phase 195 shipped capture + on-device STT preview + audio storage + keyword extraction + the `WorkOrderTranscriptsSection` variant. Phase 195B adds: cloud Whisper transcription (canonical transcript), Claude-rich symptom extraction (tool-use structured output), cost monitoring (per-call ledger + CLI report + soft per-shop cap), and an async BackgroundTasks pipeline that runs Whisper → Claude after upload.

**Step 10 reframe**: the deferred Phase 195 Step 10 acoustic capture ran 2026-05-16 on a physical iPhone and **PASSED** (worst-case 0.92 across shop-noise + distance conditions; on-device STT held up). This reframes cloud Whisper from *canonicalization-priority* (rescue bad on-device STT) to *extraction-richness substrate* (produce the best-available transcript for Claude-rich extraction to work from). Phase 195B is **lighter than worst-case planning assumed** — recommendations plan against the favorable data.

CLI: `motodiag costs report [--since DATE] [--shop N]` (new) — cost-monitoring rollup.

Outputs:
- **Backend** (2 commits): migration 043 (`cost_events` ledger table) + `whisper_client` + `cost_repo` + `costs report` CLI + config env vars + F44 port fold-in (Commit 0); `DiagnosticClient.extract_symptoms` + threshold calibration + async BackgroundTasks pipeline (Commit 1).
- **Mobile** (1 commit, small): async-extraction refetch verification + optional manual re-extract affordance + smoke gate + finalize (Commit 2).

## Substrate audit — against post-Phase-195 state (CLAUDE.md substrate-feature-pair framing, first invocation)

Per the CLAUDE.md "substrate-audit framing for substrate-feature-pair phases" added at Phase 195 close — different verb than F33 greenfield-overlap: "what did the substrate phase establish that 195B treats as locked substrate?"

1. **Substrate-anticipates-feature columns** — `voice_transcripts` (migration 042) has 4 NULLABLE-NO-DEFAULT columns reserved for cloud: `whisper_transcript TEXT`, `whisper_segments TEXT` (JSON), `whisper_cost_usd_cents INTEGER`, `whisper_model TEXT`. `extraction_state` CHECK enum already includes `'extracting'` (Phase 195 never enters it; 195B uses it for the async window). `extracted_symptoms.extraction_method` CHECK enum already includes `'claude'`. `segment_start_ms`/`segment_end_ms` NULLABLE for Whisper segments. **The Whisper half of 195B is schema-zero** — only the NEW `cost_events` table needs a migration.

2. **Contract surfaces locked** — Pydantic Literal aliases (`transcripts.py:104-121`); UX picks A-E from plan v1.0.3 (TranscriptReviewScreen); 7-variant `WorkOrderSection` union; source-agnostic UI (Phase 193). 195B extends, does not re-litigate.

3. **Deferred decisions punted to 195B** — threshold for Claude-fallback firing (§3); cost-monitoring aggregation (§4); VAD continuous-recording (§5); multilingual (out of scope, English-only stays).

4. **Smoke-gate finding that changes assumptions** — Step 10 PASS (favorable; see Goal). Resolves §1 (Whisper = richness-substrate), §3 (threshold can be less aggressive), §5 (no accuracy mandate for VAD). PASS treated as solid; the 0.92-vs-0.96 margin is operator-attested/soft — no plan decision hinges on it.

5. **F-ticket dispositions gating 195B** — F37 Track 1 carryforward (all new enums Literal day one); F38/F39 not triggered; F44 fold-in candidate (§4); F47 NEW (threshold revisit, this plan).

## Logic

### Section decisions (8 sections, locked at architect review 2026-05-16)

- **§1 Cloud Whisper provider** — OpenAI `whisper-1`. M4A native (no transcode; F39 stays deferred). Extraction-richness substrate per Step 10. `whisper_model` column lets a future model swap be config-only.
- **§2 Claude-rich extraction** — tool-use structured output (Phase 191B `ask_with_images` precedent). **Extend `DiagnosticClient`** with `extract_symptoms(transcript_text) -> list[ExtractedSymptomDraft]` — NOT a distinct client (F9-discipline: one Anthropic client). Temperature 0.0-0.2. **Model: Haiku (`claude-haiku-4-5`).** **Redirect-to-Sonnet trigger (architect-locked wording):** "promote to Sonnet IF Commit 0 calibration shows extraction-quality misses that are *model-capability-bound* rather than *prompt-bound*" — a bad Haiku result that's fixable by prompt iteration is NOT a capability miss. Malformed-output fallback: graceful degradation to the keyword rows already present + `extraction_state='extraction_failed'`.
- **§3 Threshold calibration** — hybrid corpus: Step 10's 5 real transcripts + ~15-20 synthesized edge-case fixtures (informal phrasing, jargon outside `SYMPTOM_CATEGORIES`, run-on multi-symptom). Method locked here; value derived at Backend Commit 0 build time (expected 0.3-0.5 coverage range; less aggressive per Step 10's resilient-keyword finding). **Calibration corpus + measured values documented in the Commit 0 phase-log entry.** **F47 (NEW, this plan)** tickets the post-launch revisit as a concrete obligation — not aspirational.
- **§4 Cost monitoring** — `cost_events` ledger table (migration 043): one row per Whisper call + per Claude call (`kind` Literal, `model`, `units` {duration_ms | tokens}, `cost_usd_cents`, `transcript_id` FK, `created_at`). `motodiag costs report` CLI rollup (daily/weekly, by model, by shop). Soft per-shop monthly cap — log + alert on exceed, do NOT block (hard enforcement is Track H billing). **F44 fold-in: CONDITIONALLY APPROVED** (architect call) — Backend Commit 0 touches `config.py` for cost env vars; fold the port-default fix (`api_port` 8080→8000) into the same change-set **IF the hardcoded-8080 audit comes back shallow**. **Un-fold trigger:** if `grep -rn "8080" tests/ scripts/ src/motodiag/` surfaces deep/load-bearing refs, F44 un-folds to its own commit. **Known audit hit (architect-flagged):** `openapi.py:358` + `config.py:74` `api_servers` default — those ARE the F-C/openapi.json refs; expected, not a surprise; fix them in the fold.
- **§5 VAD** — push-to-talk stays. VAD deferred. Step 10 retired the accuracy mandate; no validated UX mandate exists. F-ticket the hands-free UX argument with promotion trigger "field feedback that push-to-talk friction loses voice-memo adoption."
- **§6 Async flow** — BackgroundTasks (Phase 191B `media/analysis_worker` precedent). Upload route returns 201 immediately with `extraction_state='extracting'`; `BackgroundTasks.add_task` fires Whisper → Claude → write-results → flip-state. **NO new `extraction_state` value** — `'extracting'` covers the whole async window; not adding `'awaiting_claude'` avoids a migration + F37 Literal-update cycle for zero user-visible benefit. Mobile UX free: `_renderExtractionBadge` already renders "refining…" for `extracting`.
- **§7 F37 Track 1 carryforward** — discipline checkpoint. New 195B enums ship as `Literal[...]` from day one: `cost_events.kind` (`'whisper' | 'claude_extraction'`), `whisper_model` Pydantic Literal on the response. No `str` regressions.
- **§8 Variant rendering** — Claude-extracted symptoms render IDENTICALLY to keyword (source-agnostic, Phase 193). `_symptomChipStyle` `claude` branch already shipped Phase 195 Mobile Commit 1. NO new variant, NO new rendering idiom. 195B is backend-heavy/mobile-light.

### Backend Commit 0 — Whisper + cost substrate + F44 fold-in

1. **Migration 043**: `cost_events` table. Columns: `id`, `kind TEXT NOT NULL CHECK (kind IN ('whisper','claude_extraction'))`, `model TEXT NOT NULL`, `transcript_id INTEGER` (FK → `voice_transcripts`, ON DELETE SET NULL — keep the ledger row even if transcript deleted), `shop_id INTEGER`, `units_label TEXT` (`'duration_ms'` | `'tokens'`), `units_value INTEGER`, `cost_usd_cents INTEGER NOT NULL`, `created_at`. Indexes on `created_at`, `shop_id`, `kind`. SCHEMA_VERSION 42 → 43.
2. **`media/whisper_client.py`**: `transcribe(audio_path) -> WhisperResult` (text + segments + cost estimate). OpenAI SDK; reads `MOTODIAG_OPENAI_API_KEY`. M4A native. Lean-API discipline (CLAUDE.md): local checks before any live call, smallest viable test.
3. **`shop/cost_repo.py`**: `record_cost_event(...)` + `aggregate_costs(since, shop_id) -> CostRollup`.
4. **`cli/costs.py`** + registration: `motodiag costs report [--since] [--shop]`.
5. **`config.py`** additions: `openai_api_key`, `whisper_model` (default `'whisper-1'`), `cost_cap_monthly_usd_cents` (soft cap). **F44 fold-in** (conditional): run the 8080 audit; if shallow, bump `api_port` 8080→8000 + `api_servers` default + `openapi.py:358` fallback in the same commit; document the audit result in the phase-log entry.
6. **`pyproject.toml`**: `openai>=1.0` added to `[ai]` extras; 0.5.0 → 0.6.0.
7. **Tests**: `test_phase195b_commit0.py` — migration 043 shape, `cost_repo` round-trip, `aggregate_costs` rollup math, `costs report` CLI, `whisper_client` (mocked OpenAI; one optional live smoke gated by env var presence), F44 audit-result pin.

### Backend Commit 1 — Claude extraction + threshold + async pipeline

1. **`DiagnosticClient.extract_symptoms`**: tool-use structured output; Haiku; temperature 0.0-0.2; returns `list[ExtractedSymptomDraft]`. Malformed → fall back to existing keyword rows + `extraction_failed`.
2. **Threshold calibration**: build the hybrid corpus; derive the value; `transcript_extraction.should_run_claude_fallback(keyword_coverage) -> bool`. Document corpus + value in the phase-log.
3. **Async pipeline**: extend the transcripts upload route — return 201 with `extraction_state='extracting'`; `BackgroundTasks.add_task(run_extraction_pipeline, transcript_id)`. Pipeline: Whisper transcribe → write `whisper_*` columns → keyword pass → threshold check → Claude-fallback if below → write `extracted_symptoms` rows → record `cost_events` → **flip `extraction_state` to `'extracted'`**.
4. **ACCEPTANCE CRITERION (architect-elevated from risk-register line)**: the final-state-flip + the `extracted_symptoms` row-writes MUST be a **single atomic DB transaction**. Phase 192 Contract-B single-UPDATE discipline. A mobile refetch landing mid-pipeline must see EITHER (`extracting`, no Claude rows) OR (`extracted`, all Claude rows) — never a torn state. **Test must specifically exercise the refetch-mid-write window** — not a generic "a test", an explicit interleaving test.
5. **Tests**: `test_phase195b_commit1.py` — `extract_symptoms` tool-use (mocked Claude), threshold gating, async pipeline end-to-end, **atomic-transaction interleaving test**, malformed-output graceful degradation, `extraction_failed` path.

### Mobile Commit 2 — refetch verification + smoke gate + finalize

Backend-heavy/mobile-light (§8). The `claude` chip branch + `extracting` badge already shipped. Mobile Commit 2:
1. Verify async-extracted Claude rows land on `WorkOrderDetailScreen` focus refetch (the `extracting` → `extracted` transition + Claude chips appearing). Likely zero or near-zero new code — the existing `useFocusEffect` + `useWorkOrderTranscripts.refresh` handle it.
2. Optional: a manual "re-run extraction" affordance on `TranscriptReviewScreen` if a mechanic wants to retrigger. Pin at build time — ship only if it's genuinely small.
3. Smoke gate (~6 steps): upload → `extracting` badge → poll/refetch → `extracted` + Claude chips; keyword + claude chips render identically (source-agnostic); `extraction_failed` path shows keyword rows + failed badge; cost_events recorded; F37 Track 1 contract check (new enums Literal).
4. Finalize: implementation.md v1.1, phase logs, move to completed/, ROADMAPs ✅, reserve Phase 195C slot.

## Key Concepts

- **Step 10 favorable reframe**: cloud Whisper is extraction-richness substrate, not canonicalization-priority. De-risks scope.
- **Schema-zero Whisper half**: only `cost_events` needs a migration; `whisper_*` columns already exist.
- **`DiagnosticClient.extract_symptoms`**: tool-use structured output, Haiku, extend-not-fork.
- **Threshold: method-locked-v1.0, value-derived-Commit-0**, F47-ticketed revisit.
- **Async BackgroundTasks** (191B precedent); NO new `extraction_state` value.
- **Atomic state-flip = Commit 1 acceptance criterion** (architect-elevated): single transaction, refetch-mid-write interleaving test.
- **F44 conditional fold-in**: approved-contingent-on-shallow-audit, explicit un-fold trigger, openapi.json a known hit.
- **Source-agnostic UI**: Claude rows render identically to keyword. Backend-heavy/mobile-light.
- **F37 Track 1 carryforward**: all new enums Literal day one.

## Verification Checklist

- [x] Migration 043 creates `cost_events` with `kind` CHECK enum + 3 indexes; SCHEMA_VERSION 42 → 43.
- [x] `whisper_client.transcribe` handles M4A, returns text + segments + cost; reads `MOTODIAG_OPENAI_API_KEY`.
- [x] `cost_repo` record + aggregate; `motodiag costs report` rollup correct.
- [x] F44 audit run + documented; port fold-in landed IF shallow, un-folded IF deep; phase-log records which.
- [x] `DiagnosticClient.extract_symptoms` tool-use structured output; Haiku; malformed → keyword-row fallback + `extraction_failed`.
- [x] Threshold calibration corpus built; value derived + documented in Commit 0 phase-log; F47 filed.
- [x] Async BackgroundTasks pipeline: upload → 201 `extracting` → Whisper → Claude → `extracted`.
- [x] **ACCEPTANCE: state-flip + row-writes single atomic transaction; refetch-mid-write interleaving test passes.**
- [x] NO new `extraction_state` enum value (no migration beyond 043).
- [x] All new enums (`cost_events.kind`, `whisper_model` response) ship as Pydantic `Literal[...]` (F37 Track 1).
- [x] Mobile: async-extracted Claude rows land on WO-detail refetch; keyword + claude chips render identically.
- [x] ~6-step smoke gate; backend + mobile test suites green.
- [x] Versions bumped; Phase 195C slot reserved in v1.1; ROADMAPs ✅.

## Risks

1. **Whisper API key provisioning** — `MOTODIAG_OPENAI_API_KEY` must exist for live calls. Lean-API discipline; one clean smoke run.
2. **Threshold calibration corpus thinness** — Step 10 gave 5 clean transcripts; ~15-20 synthetic edge cases carry the calibration weight, realism unvalidated. **F47 tickets the post-launch real-transcript revisit as a concrete obligation** (trigger: N real production transcripts accumulated → re-derive + compare). Method locked v1.0, value derived Commit 0, documented.
3. **Claude extraction cost at scale** — Haiku keeps it cheap; `cost_events` ledger + soft cap + `costs report` is the safety net, shipped Commit 0.
4. **`extraction_state` async race** — ELEVATED to Backend Commit 1 acceptance criterion (above), not a risk-register line. Single atomic transaction; explicit refetch-mid-write interleaving test.
5. **F44 hardcoded-8080 audit depth** — fold-in is conditional; un-folds if deep. openapi.json is a known hit (expected).
6. **Haiku capability ceiling** — redirect-to-Sonnet trigger is capability-bound-vs-prompt-bound (architect-locked); a bad result fixable by prompt iteration is NOT a capability miss.
7. **F37 Track 1 manual discipline** until Phase 195C lints it — §7 checkpoint is the guard.

## Phase 195C slot

Reserved (between 195B and 196) per the 191B→191C→191D precedent. F37 Track 2: lint rule enforcing Pydantic-Literal-vs-DB-CHECK-constraint + retroactive validation across 191B/192/193/194/195/195B + F9 subspecies addition. NOT iOS-parity (landed as a CLAUDE.md PR-review checklist item, F40-refined — deliberately not lint scope).

## Deviations from Plan

Plan v1.0 shipped end-to-end with NO scope changes. Four implementation-time notes:

1. **F44 fold-in confirmed** — the hardcoded-8080 audit (plan §4's conditional) came back **shallow**: 6 refs, all defaults / help-text / one test pin, zero load-bearing logic. Per the conditional approval, the port-default fix (8080→8000) folded into Backend Commit 0's `config.py` change-set. `openapi.py:358` + `config.py:74` were the F-C/openapi.json `:8080` refs the iOS session flagged — exactly the architect-flagged known audit hit, no surprise.
2. **Threshold value derived at Backend Commit 1, not Commit 0** — plan §3 estimated "value derived at Commit 0", but Backend Commit 0 shipped the cost substrate with no extraction code. The threshold (`CLAUDE_FALLBACK_COVERAGE_THRESHOLD = 0.5`) was derived + documented at Commit 1 alongside the code that uses it — more coherent than carrying an unused constant through Commit 0. Calibration documented inline in `transcript_extraction.py` + below.
3. **TAG_CATALOG coverage backfill folded into Backend Commit 0** — a pre-existing gap (Phases 194 + 195 added router tags `work-order-photos` / `voice-transcripts` but never updated `openapi.py` TAG_CATALOG; the 194/195 finalize regressions ran targeted subsets + missed `test_phase183_openapi.py`). NOT a Backend Commit 0 regression — surfaced because trust-but-verify ran the F44-touched test file. Folded in (same shape as Phase 194 Commit 0 folding the F9 SCHEMA_VERSION fix on Phase 192's test).
4. **3 Phase 195 route tests adapted to the async contract** — the upload route changed sync→async (Backend Commit 1); 3 tests in `test_phase195_commit0_voice_transcripts.py` that pinned the synchronous `extraction_state='extracted'` + populated `extracted_symptoms` on the POST response were updated to the async contract (POST returns 201 `extracting` + 0 symptoms; a follow-up GET after the BackgroundTask runs sees the finalized state). Genuine contract-change adaptation, not a bug.

## Results

| Metric | Value |
|---|---|
| Backend commits | 2 (Commit 0 `efb0b7e`, Commit 1 `32ac5c2`) + plan/finalize |
| Mobile commits | 1 (Commit 2) + plan/finalize |
| Migration | 043 — `cost_events` ledger; SCHEMA_VERSION 42 → 43 |
| New backend modules | `media/whisper_client` + `media/transcript_pipeline` + `shop/cost_repo` + `cli/costs` |
| Extended backend modules | `engine/client` (`extract_symptoms`) + `media/transcript_extraction` (threshold) + `shop/extracted_symptom_repo` (`finalize_extraction`) + `shop/transcript_repo` (`update_whisper_result`) + `api/routes/transcripts` (async) |
| New backend tests | 43 (`test_phase195b_commit0.py` 21 + `test_phase195b_commit1.py` 22) |
| Backend tests adapted | 3 (Phase 195 route → async contract) + 1 (F44 port pin) |
| New mobile module surface | `useWorkOrderTranscripts` polling (`TRANSCRIPT_POLL_INTERVAL_MS`) |
| New mobile tests | 7 (`VoiceCaptureB.smoke.test.tsx`) |
| Mobile total tests | 700/700 pass (was 693; +7) |
| Backend version | 0.5.0 → 0.6.0 (+`openai>=1.0`) |
| Mobile version | 0.3.0 → 0.4.0 |
| Threshold (calibrated) | `CLAUDE_FALLBACK_COVERAGE_THRESHOLD = 0.5` |
| Atomic-transaction acceptance criterion | MET — `finalize_extraction` single transaction; rollback-on-mid-write-failure test proves no torn state |

**Key finding**: the substrate-then-feature pair pattern paid off most visibly here — Phase 195B's Whisper half was *schema-zero* (the `whisper_*` columns + `extracting`/`claude` enum values were all shipped as substrate-anticipates-feature in Phase 195's migration 042) and the mobile surface was near-zero new UI (the `refining…` badge + `claude` chip branch shipped Phase 195 Mobile Commit 1). The feature half added a migration only for the genuinely-new `cost_events` ledger. The four architect-review refinements (F44 conditional fold, Haiku capability-vs-prompt redirect trigger, F47 threshold-revisit ticket, async-race-as-acceptance-criterion) all landed as specified — the review's value was converting soft spots into explicit obligations before they could drift.
