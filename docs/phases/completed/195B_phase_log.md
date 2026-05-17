# Phase 195B — Phase Log

**Status:** ✅ Complete | **Started:** 2026-05-16 | **Completed:** 2026-05-16
**Repo:** https://github.com/Kubanjaze/moto-diag (backend) + https://github.com/Kubanjaze/moto-diag-mobile (mobile)
**Branch:** `phase-195B-cloud-whisper` (created BOTH repos at plan-push)

---

### 2026-05-16 — Plan v1.0 written

Phase 195B is the **feature half** of the 195/195B substrate-then-feature pair — cloud Whisper + Claude-rich extraction + cost monitoring + VAD-decision. Fifth substrate-feature pair in the chain (191/191B, 192/192B, 194/194B, 195/195B).

**Substrate audit ran first** — the CLAUDE.md substrate-feature-pair audit framing (added at Phase 195 close), FIRST invocation. Different verb than F33 greenfield-overlap: "what did Phase 195's actual implementation establish that 195B treats as locked substrate?" Five-thing enumeration folded into plan v1.0. Key finding: **the Whisper half is schema-zero** — `voice_transcripts.whisper_*` columns + `extraction_state='extracting'` + `extraction_method='claude'` enum values all shipped as substrate-anticipates-feature in migration 042. Only the new `cost_events` ledger needs a migration (043).

**Step 10 acoustic capture (deferred from Phase 195) ran 2026-05-16 + PASSED** — physical iPhone, 5-condition matrix, worst-case 0.92 across shop-noise + distance. On-device STT held up. This reframes cloud Whisper from canonicalization-priority to **extraction-richness substrate** — 195B is lighter than worst-case planning assumed. The Step 10 result + provenance caveat (operator-attested, 0.92-vs-0.96 margin soft) are recorded as an addendum on the Phase 195 phase log (commit `79a86c6`).

**Pre-plan Q&A — 8 sections drafted against real Step 10 data, architect-reviewed 2026-05-16.** Architect locked the rest + sharpened four soft spots into explicit obligations:

1. **§4 F44 fold-in — CONDITIONALLY approved.** Port-default fix (8080→8000) folds into Backend Commit 0's `config.py` change-set IF the hardcoded-8080 audit is shallow; explicit un-fold trigger if deep. openapi.json `:8080` flagged as a known audit hit (not a surprise).
2. **§2 Haiku redirect-trigger — worded.** "Promote to Sonnet IF Commit 0 calibration shows extraction-quality misses that are *model-capability-bound* rather than *prompt-bound*." The capability-vs-prompt distinction matters — a bad Haiku result fixable by prompt iteration is not a capability miss.
3. **§3 threshold revisit — ticketed, not aspirational.** F47 NEW filed: the post-launch real-transcript re-derivation is a concrete obligation with a trigger (N real production transcripts accumulated → re-derive + compare), not a "revisit later" note that never happens.
4. **Async-state race — elevated to a Backend Commit 1 acceptance criterion.** The `extraction_state` flip + `extracted_symptoms` row-writes must be a single atomic transaction; the test must specifically exercise the refetch-mid-write interleaving window. Was a risk-register line in the draft; the architect correctly elevated it — it is the one place 195B's small mobile surface could still bite (mechanic sees torn state mid-pipeline).

Sections locked as-drafted (architect confirmed, no re-litigation): §1 (OpenAI `whisper-1`), §5 (VAD deferred — Step 10 retired the accuracy mandate), §6 (BackgroundTasks, no new `extraction_state` value), §7 + §8 (discipline checkpoints — F37 Track 1 carryforward, source-agnostic identical rendering).

**Commit structure** (backend-heavy / mobile-light — the inverse of Phase 195, because the substrate-anticipates-feature columns + already-shipped `claude` chip branch mean the mobile surface is small):
- Backend Commit 0 — migration 043 (`cost_events`) + `whisper_client` + `cost_repo` + `costs report` CLI + config env vars + F44 fold-in + `openai>=1.0` dep + tests.
- Backend Commit 1 — `DiagnosticClient.extract_symptoms` (tool-use, Haiku) + threshold calibration (hybrid corpus) + async BackgroundTasks pipeline + atomic-transaction acceptance criterion + tests.
- Mobile Commit 2 — async-extraction refetch verification (likely near-zero new code) + optional manual re-extract affordance + ~6-step smoke gate + finalize.

**F-tickets:**
- F47 NEW (filed this plan) — threshold revisit ticketed obligation.
- F37 Track 1 carryforward — all new 195B enums ship as `Literal[...]` day one (`cost_events.kind`, `whisper_model` response). F37 Track 2 stays Phase 195C (post-195B).
- F44 — conditional fold-in to Backend Commit 0 (see §4 above).
- F38 / F39 — not triggered by 195B; deferrals hold.

**Risks at plan-write time** (full set in implementation.md): Whisper API key provisioning; threshold calibration corpus thinness (F47-mitigated); Claude cost at scale (`cost_events` safety net); async race (elevated to acceptance criterion); F44 audit depth; Haiku capability ceiling (redirect trigger); F37 Track 1 manual discipline until 195C.

**Phase 195C slot reserved** — between 195B and 196, per the 191B→191C→191D precedent. F37 Track 2 (lint rule + retroactive validation + F9 subspecies). NOT iOS-parity (landed as a CLAUDE.md PR-review checklist item, F40-refined).

**Next step**: create `phase-195B-cloud-whisper` branch on both repos, push plan v1.0 (this commit), then begin Backend Commit 0 (migration 043 + whisper_client + cost substrate + config + F44 fold-in + tests).

---

### 2026-05-16 — Backend Commit 0 build complete (`efb0b7e`)

Cloud Whisper + cost ledger + costs CLI + F44 fold-in. 12 files, 894 insertions.

- **Migration 043** — `cost_events` ledger (9 cols, `kind` CHECK enum {whisper, claude_extraction}, `transcript_id` FK ON DELETE SET NULL, 3 indexes). SCHEMA_VERSION 42 → 43. Whisper half schema-zero (whisper_* columns already in migration 042); only the new ledger needed a migration.
- **`media/whisper_client.py`** (NEW) — OpenAI Whisper wrapper; `transcribe()` returns text + segments + computed `cost_usd_cents` (rounds up — under-billing the ledger is the wrong direction). Graceful degradation via typed `WhisperUnavailableError` / `WhisperTranscriptionError`.
- **`shop/cost_repo.py`** (NEW) — `record_cost_event` + `aggregate_costs` (CostRollup) + `shop_cost_this_month`.
- **`cli/costs.py`** (NEW) — `motodiag costs report [--since|--this-month] [--shop]`.
- **`config.py`** — `openai_api_key` / `whisper_model` / `cost_cap_monthly_usd_cents`.
- **F44 fold-in** — audit came back SHALLOW (6 refs, all defaults/help-text/one test pin). Port default 8080→8000 across `config.py` / `openapi.py` / `serve.py` / `test_phase183_openapi.py`. `openapi.py` + `config.py` refs were the architect-flagged known audit hit. Fresh `motodiag serve` now binds 8000, matching mobile's `.env`.
- **TAG_CATALOG backfill** — pre-existing gap (Phases 194/195 router tags `work-order-photos`/`voice-transcripts` never cataloged); surfaced by trust-but-verify running the F44-touched test file. Folded in (Phase 194 Commit 0 precedent).
- **`pyproject.toml`** — `openai>=1.0` to `[ai]` extras; 0.5.0 → 0.6.0.
- **Tests** — `test_phase195b_commit0.py` 21 tests; 64/64 green (incl. the fixed Phase 183 tag-catalog test). F9 lint clean.

### 2026-05-16 — Backend Commit 1 build complete (`32ac5c2`)

Claude-rich extraction + threshold + async BackgroundTasks pipeline. 8 files, 1199 insertions.

- **`DiagnosticClient.extract_symptoms`** — tool-use structured output (Phase 191B Vision precedent); forced `tool_choice` on a `record_symptoms` tool, category enum-constrained to `SYMPTOM_CATEGORIES`. Haiku default; `model` override is the redirect-to-Sonnet path (capability-bound-vs-prompt-bound — architect-locked distinction). Malformed/absent tool_use → `ClaudeExtractionMalformedError` (new typed exception).
- **Threshold** — `CLAUDE_FALLBACK_COVERAGE_THRESHOLD = 0.5`, calibrated + documented inline in `transcript_extraction.py`. Hybrid corpus: Step 10's 5 clean transcripts (coverage 1.0 — never-fire-Claude alone) + 18 synthetic edge-case fixtures; genuine-miss transcripts cluster at coverage ≤0.5, well-handled ones ≥0.6. Moderate not aggressive — Step 10 showed keyword resilient. `keyword_coverage` + `should_run_claude_fallback`. **Derived at Commit 1, not Commit 0** (plan §3 estimated Commit 0; deriving alongside the code that uses it is more coherent — Deviation #2).
- **`finalize_extraction`** (atomic — the architect-elevated ACCEPTANCE CRITERION) — row-writes + `extraction_state` flip in ONE `get_connection` transaction. The rollback-on-mid-write-failure test (an invalid `extraction_method` CHECK violation mid-batch) proves the whole transaction rolls back — no torn state ever visible to a refetch.
- **`transcript_pipeline.run_extraction_pipeline`** (NEW) — the BackgroundTask orchestrator: Whisper → degrade-on-failure → best-text → keyword → threshold → Claude-fallback → atomic finalize. Top-level catch ALWAYS finalizes out of `extracting` (a framework-swallowed BackgroundTask exception would otherwise strand the transcript).
- **Route** — `upload_voice_transcript` async-dispatches: flip to `extracting`, queue `run_extraction_pipeline`, return 201 immediately. Mirrors Phase 191B's `analysis_worker`.
- **Tests** — `test_phase195b_commit1.py` 22 tests (threshold gate, `extract_symptoms` tool-use + 3 malformed paths, `finalize_extraction` atomicity incl. the rollback test, pipeline end-to-end incl. Whisper-degrade + never-stuck + Claude-fallback + malformed→extraction_failed). 3 Phase 195 route tests adapted to the async contract (Deviation #4). 67/67 green; F9 lint clean.

### 2026-05-16 — Mobile Commit 2 + finalize complete

**Status: ✅ Complete | Phase 195B ships.**

Backend-heavy / mobile-light per plan §8 — the `refining…` badge, the `extraction_state` exhaustive switch, and the `claude` chip-style branch all shipped Phase 195 Mobile Commit 1 as substrate-anticipates-feature. Mobile Commit 2 added the one genuinely-new mobile surface + the smoke gate.

- **`useWorkOrderTranscripts` polling** — `TRANSCRIPT_POLL_INTERVAL_MS = 5000`; the hook polls `refresh()` while any transcript is in a non-terminal `extraction_state` (`pending`/`extracting`), stops once all reach terminal (`extracted`/`extraction_failed`). Mirrors `useSessionVideos`'s Phase 191B Vision-analysis poll. Closes the gap where a WO-detail screen left open during the async pipeline would show `refining…` forever.
- **`__tests__/screens/VoiceCaptureB.smoke.test.tsx`** (NEW, 7 tests) — 6-step async-extraction smoke gate: poll-stop terminal-state set; `extraction_state` + `extraction_method` Literal unions stable (F37 Track 1); `extracting` renders the refining badge; keyword + claude chips render identically (source-agnostic, Phase 193); `extraction_failed` shows the failed badge + keeps surviving keyword chips (graceful degradation); poll-interval SSOT.
- **Verification** — 700/700 mobile Jest pass (was 693; +7). TypeScript clean. ESLint 0 errors. Backend 67/67 + 21/21 green. F9 SSOT lint clean.
- **Versions** — backend `pyproject` 0.5.0 → 0.6.0 (Commit 0); mobile `package` 0.3.0 → 0.4.0 (Commit 2).

**Four architect-review refinements — all landed as specified:**
- F44 conditional fold-in → audit shallow → folded (Backend Commit 0), documented.
- Haiku redirect-trigger → capability-bound-vs-prompt-bound wording in `extract_symptoms` docstring.
- F47 threshold revisit → filed in FOLLOWUPS; threshold calibrated 0.5 + documented; F47 trigger = re-derive after ≥50 real production transcripts.
- Async-race acceptance criterion → `finalize_extraction` single atomic transaction; the rollback-on-mid-write-failure test proves no torn state.

**F-ticket dispositions at finalize:**
- F44 — folded into Backend Commit 0; the FOLLOWUPS entry is closeable.
- F47 — filed; lives until the ≥50-transcript trigger fires.
- F37 Track 1 — carried forward clean (all new 195B enums — `cost_events.kind` — shipped as `Literal`). Track 2 → Phase 195C.
- F38 / F39 — not triggered by 195B; deferrals hold.

**Phase 195C slot** — reserved between 195B and 196. F37 Track 2 lint rule + retroactive validation. Opens next per the locked sequence.

**Phase 195B closes here.** Substrate-then-feature pair (195/195B) complete; ROADMAPs ✅; docs moved to `docs/phases/completed/`.

---

### 2026-05-17 10:25 — Bug fix #1: SCHEMA_VERSION-bump fallout + 195B model-ID literals

The architect's PR-review of Phase 195B asked for a full 4587-test suite run
from a clean checkout before requesting review — the first time the whole
suite ran across the stacked 192→195B branch chain (each phase's build had run
only its phase-specific tests). It surfaced 5 failures: 4 SCHEMA_VERSION-bump
guard-test failures inherited from Phases 194/195, and 5 hardcoded model-ID
literals genuinely introduced by Phase 195B's own test files. Per the
architect's PR-review decision (2026-05-17), the SCHEMA_VERSION fixes land on
their originating branches (194/195) and propagate here via merge-forward;
this commit carries 195B's share.

- **`test_phase184_gate9::test_schema_version_unchanged`:** Gate 9
  anti-regression pin 42 → 43 (migration 043 / cost_events). Phase 195B's
  migration 043 is the final bump in the 40→43 chain; the pin obligation
  recurs at every schema-bumping phase.
- **`test_phase191b_serve_migrations::...match_schema_version`:** fixture
  cross-check pin 42 → 43.
- **`test_phase195b_commit0.py` + `test_phase195b_commit1.py` — 5 model-ID
  literals:** `test_phase191c_f9_lint::test_clean_main_has_zero_findings`
  flagged hardcoded `claude-haiku-4-5*` literals in 195B's own test files
  (cost-ledger row fixtures, cost-rollup assertions, the `extract_symptoms`
  Haiku model arg). These are genuinely 195B's — 195B's build reported
  "F9 lint clean" but never ran the cross-cutting `test_clean_main_has_zero_findings`
  gate. **Fix:** top-of-file `# f9-allow-model-ids: fixture-data` opt-out on
  both files (the lint's sanctioned mechanism for test files whose model-ID
  literals are incidental fixture data).
- **`api/openapi.py` TAG_CATALOG:** the merge-forward from phase-195 collided
  with 195B Commit 0's own backfill (which had added work-order-photos +
  voice-transcripts forward). Resolved by dropping the now-redundant 195B
  Commit-0 backfill comment block and keeping 195B's cloud-Whisper-enriched
  voice-transcripts description — the entries now originate on phases 194/195
  per the reattribution decision; net openapi.py content unchanged.
- **SSOT-lint synthetic-fixture self-tests:** no change here — Phase 194's
  fix #1 made them interpolate the live `SCHEMA_VERSION`; they auto-track to 43.
- **Files:** `tests/test_phase184_gate9.py`, `tests/test_phase191b_serve_migrations.py`,
  `tests/test_phase195b_commit0.py`, `tests/test_phase195b_commit1.py`,
  `src/motodiag/api/openapi.py` (merge resolution).
- **Verified:** the four guard-test files + `test_phase183_openapi` → 86/86
  pass on `phase-195B-cloud-whisper`; full 4587-test suite run follows.
