# Phase 195C — Phase Log

**Status:** Planned | **Started:** 2026-05-17 | **Completed:** —
**Repo:** https://github.com/Kubanjaze/moto-diag (backend)
**Branch:** `phase-195C-f37-track2-lint` (based on `phase-195B-cloud-whisper`)

---

### 2026-05-17 11:37 — Plan v1.0 written

Phase 195C is the **locked-sequence slot reserved between Phase 195B and Phase 196** in Phase 195B's plan v1.0 ("Phase 195C slot" section). It implements **F37 Track 2** — the systematic-correctness meta-tooling response to the contract-surface-drift pattern that surfaced as F37 instance #3 during Phase 195. Same precedent as 191B → 191C → 191D: a feature ships, then a dedicated meta-tooling phase responds to the discovered drift after the feature phase closes cleanly. Phase 195C is the F37 analogue of Phase 191D.

**Three deliverables, no more** (scope locked against the CLAUDE.md guardrail):
1. A lint rule enforcing "Pydantic response-model fields that map to a DB string-enum `CHECK` constraint must be typed `Literal[...]` matching the constraint value-set" — added as a new `--check-pydantic-literal-vs-check-constraint` sub-check inside `scripts/check_f9_patterns.py`.
2. Retroactive validation of that rule across the Phase 191B→195B backend route code; any unpredicted silent `str`-instead-of-`Literal` regression gets fixed + folded into the same build commit.
3. A new "contract-surface-drift" subspecies appended to `docs/patterns/f9-mock-vs-runtime-drift.md`.

Explicitly OUT of scope (confirmed): F37 Track 1 enforcement (already done — Phase 195 Backend Commit 0.5); the iOS-parity / cross-platform-permission checklist (withdrawn from 195C — it lives as a CLAUDE.md PR-review checklist item, not a parseable code property); any mobile change.

**F33 existing-code-overlap audit ran first** (plain greenfield-overlap flavor — 195C is meta-tooling, not a substrate-feature pair). Method: read every `CHECK (... IN (...))` constraint across the 39 migrations in `core/migrations.py` (`database.py` has no `SCHEMA_SQL` baseline with CHECKs — zero grep matches); read every Pydantic model in the `videos / reports / shop_mgmt / photos / transcripts` route modules + `core/models.py`; cross-matched field-name → CHECK-column-name. F33 noun-grep for `check_pydantic` / `check_f37` / `pydantic-literal` / `contract-surface` across `scripts/` + `src/` returned zero code matches (only doc forward-references). The full audit table is embedded in `195C_implementation.md`.

**Audit outcome — the retroactive hit-list is EMPTY.** Every Pydantic response field that maps to a DB string-enum CHECK is already `Literal`-correct: `transcripts.py` was fixed in Phase 195 Commit 0.5 (`extraction_state`, `extraction_method`, `audio_format`, `preview_engine` all use `Literal` aliases); `photos.py` `WorkOrderPhotoResponse.role` is `PhotoRole = Literal[...]` matching migration 041; `shop_mgmt.py` request models (`MemberAddRequest.role`, `IssueCreateRequest.severity`, `NotificationTriggerRequest.channel`) all use `Literal` matching their CHECKs; `reports.py` `PdfRenderRequest.preset` is `Literal` (no DB column). This is the expected healthy result — the rule's value is forward-looking (catch the *next* regression automatically), exactly as F37 Track 2 framed it. If the rule once built surfaces an unpredicted finding, that is a genuine regression and gets fixed + folded + logged per the plan's Step 5.

**Posture confirmed: greenfield rule logic, extension on every file touched.** `check_f9_patterns.py` gets a new function + CLI flag + `--all` fold-in (no existing sub-check reshaped); `f9-mock-vs-runtime-drift.md` gets a new subspecies appended (no rewrite). No v1.0.1 reshape anticipated.

**Recommendation locked in the plan: sub-check of `check_f9_patterns.py`, NOT a separate `check_f37_patterns.py`.** Reasoning — F20 (`--check-ssot-constants`) and F21 (`--check-tag-catalog-coverage`) were both new F-tickets given new sub-checks in the *same* file; F37 is structurally identical (a value-set-drift static check) and contract-surface-drift is being filed as a new F9 *subspecies*, so the rule belongs in the F9 script by definition; machinery reuse (`F9Finding`, `_file_level_optout`, opt-out reason floor, `--all` orchestration) is maximal; one pre-commit entry. The `src/`-scanning argument for a separate script is weak — `--check-tag-catalog-coverage` already scans `src/motodiag/api/`.

**Three scope-pressure items flagged for the architect** (Open Questions in the plan — NOT self-authorized): (Q1) `shop_mgmt.py` list/get handlers return raw `dict` rows, not Pydantic response models, so several CHECK-constrained `status` columns have no field for the rule to type — introducing response models there is a feature change, F-ticket it; (Q2) `voice_transcripts.audio_format` / `preview_engine` have a Pydantic `Literal` but NO backing DB CHECK — the *inverse* drift direction; 195C ships only the CHECK→Pydantic direction the F37 ticket specifies, F-ticket the inverse; (Q3) `VideoResponse` uses `str, Enum` and the `videos` table has no CHECK on `upload_state`/`analysis_state` — plan WARNs on `str,Enum` (not error, no false regression verdict) and F-tickets the missing-CHECK observation; adding CHECKs is a migration, out of scope.

**Architect-review hold.** Plan v1.0 stops here. No production code written, no lint rule implemented, no schema or route changes made, no drift fixed. The plan holds for architect review before any implementation begins.

**Next:** architect review of plan v1.0 → on approval, build the `--check-pydantic-literal-vs-check-constraint` sub-check + `test_phase195c_pydantic_literal_lint.py` + run the retroactive sweep + append the F9 subspecies → finalize to v1.1.
