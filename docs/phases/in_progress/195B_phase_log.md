# Phase 195B — Phase Log

**Status:** 🚧 In Progress | **Started:** 2026-05-16
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
