# Phase 195C — Phase Log

**Status:** ✅ Complete | **Started:** 2026-05-17 | **Completed:** 2026-05-17
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

---

### 2026-05-17 — Plan v1.0 → v1.0.1 amendment (architect PR-review, pre-code)

Architect PR-review of plan v1.0 (2026-05-17). Three decisions:
- **Sub-check in `check_f9_patterns.py`, not a separate script** — accepted as proposed (191D precedent).
- **Open Questions Q1 / Q2 / Q3** — accepted as proposed: Q1 (shop_mgmt raw-dict rows) → F-ticket; Q2 (inverse `Literal`-without-CHECK drift) → F-ticket; Q3 (`VideoResponse` `str,Enum`) → WARN-only. No scope change.
- **NOT a clean accept — conditional on a v1.0.1 amendment.** The architect's independent spot-check confirmed the empty-hit-list audit claim but surfaced the load-bearing nuance: **three real tables — `fleet_bikes`, `shop_members`, `work_order_photos` — carry a same-named `role` column with three different CHECK value-sets.** Plan v1.0 keyed CHECK sets by column name and joined on name equality; against that collision it would cross-wire (false-flag a correct field, or pass a drifted one matching a different table's set) — the F9 name-vs-semantic-match failure reproduced inside the F9 tool.

**v1.0.1 amendment made (plan-only, pre-code):** CHECK sets keyed by `(table, column)` (Step 1); model→table resolution added via `# f9-table:` marker + class-name-convention fallback (Step 2); name-equality join rewritten to a table-scoped join with a `pydantic-literal-vs-check-ambiguous` never-guess fallback (Step 3); Risk 4 promoted from watched-risk to a **hard requirement + fixture-backed acceptance test**; Verification Checklist gains the three-`role`-column disambiguation test as a phase-closure gate. Full rationale in `195C_implementation.md` → "v1.0.1 amendment" section.

This is the CLAUDE.md Step-0 discipline working as designed — a documented-assumption mismatch caught at plan-review time, resolved as a pre-code v1.0.1 amendment rather than surfacing as an implementation-time reshape.

**Next:** architect sign-off of plan **v1.0.1** → on approval, build per the table-scoped spec → finalize to v1.1.

---

### 2026-05-17 — Plan v1.0.1 → v1.0.2 amendment (retroactive-sweep trust-but-verify, pre-code)

The Builder built faithfully to v1.0.1. The Architect's trust-but-verify retroactive
sweep against live `src/` then returned **24 findings**, not the v1.0.1 audit's
predicted empty hit-list. Two plan-side problems:

- **The rule over-fires.** v1.0.1's table-scoped join fixed colliding CHECK
  *columns* but still flagged a field purely because its name coincides with a
  CHECK column on some table — `meta.py HealthStatus.status` (a health-check
  model, no DB table) flagged against 7 DB `status` tables; `SessionResponse`
  `status`/`severity` flagged though `diagnostic_sessions` carries no CHECK on
  them. The F9 name-vs-semantic-match failure, inside the F9 tool.
- **The "empty hit-list" was wrong** — the v1.0.1 audit under-enumerated
  (`role`/`severity`/`extraction_*` but not `category`/`event`). Genuine
  `str`-instead-of-`Literal` regressions exist: `IssueCreateRequest.category`,
  `NotificationTriggerRequest.event`.

**symptoms-category ruling (pre-code, per architect):** `symptoms.category` and
`extracted_symptoms.category` both checked — `TEXT`, no CHECK. So all three
`*.category` findings on those tables are Bucket 1 (dissolved by the semantic
fix); only `issues.category` has a CHECK → `IssueCreateRequest.category` is the
sole category Bucket-2 fix.

**v1.0.2 amendment authorized + written pre-code** (architect 2026-05-17,
5-item scope): (1) positive-resolution-required matching — flag only when the
model resolves to a table carrying a CHECK on that column; `ambiguous` finding
type removed; (2) `HealthStatus`-shaped negative fixture as a phase-closure
gate; (3) empty-hit-list premise retired — Bucket-2 findings become in-phase
`str`→`Literal` fixes; (4) Bucket-3 `# f9-table:` markers as authoritative
resolution; (5) symptoms-category ruled. Full detail: `195C_implementation.md`
→ "v1.0.2 amendment" section.

Build proceeds against v1.0.2. Phase-closure gated on: negative fixture green +
the two Bucket-2 fixes landed + a clean re-sweep (zero false positives). A
phase does not close on a dirty result; the amendment is pre-code, not a
finalize-then-patch.

**Next:** build the rule-tightening + negative fixture + markers + Bucket-2
fixes against v1.0.2 → re-sweep clean → finalize to v1.1.

---

### 2026-05-17 — Build complete (v1.1) — Phase 195C ✅

Built against plan v1.0.2 via the Builder/Architect split: a Builder agent
wrote the v1.0.1 first pass; the Architect's trust-but-verify surfaced the
defects that drove the v1.0.1→v1.0.2 amendment, then reworked the rule to
v1.0.2 and finalized.

**Delivered:**
- `scripts/check_f9_patterns.py` — new `check_pydantic_literal_vs_check_constraint`
  sub-check + `--check-pydantic-literal-vs-check-constraint` flag, folded into
  `--all` / `run_all_checks`. Table-scoped, positive-resolution-required join.
- `tests/test_phase195c_pydantic_literal_lint.py` — 25 RuleTester-style tests,
  incl. the two closure gates (three-`role`-column disambiguation;
  `HealthStatus`-shaped negative fixture). 25/25 green.
- `docs/patterns/f9-mock-vs-runtime-drift.md` — Subspecies (vi)
  contract-surface-drift + Instance #11; counters 10→11 / 5→6 subspecies.
- `.pre-commit-config.yaml` — dedicated hook + `--all` fold-in.
- 8 `# f9-table:` model→table markers across `photos.py` / `shop_mgmt.py` /
  `transcripts.py`.

**Bug fix #1 — Builder first-pass `UnboundLocalError`.** Issue: the
colliding-column resolved-success path in `_scan_models_for_check_drift` never
bound `table`. Root cause: only the single-table branch + the (removed)
ambiguous branch bound it. Fix: bind `table = resolved` on the success path
(later subsumed by the v1.0.2 rework). Verified: phase tests 25/25.

**Bug fix #2 — retroactive `str`→`Literal` regressions (Bucket 2).** The
v1.0.2 retroactive sweep surfaced 2 genuine contract-surface-drift regressions
the v1.0.1 audit missed: `IssueCreateRequest.category` (`str` → `Literal` of
the `issues.category` CHECK, 13 values) and `NotificationTriggerRequest.event`
(`str` → `Literal` of the `customer_notifications.event` CHECK, 10 values).
Both in `src/motodiag/api/routes/shop_mgmt.py`. Verified: clean re-sweep +
156-test targeted regression (issue/notification/shop/gate) green — the
request-validation tightening broke no existing test.

**Verification:** retroactive sweep clean (0 findings); full backend
regression **4612 passed, 0 failed** (1:22:09); F9-lint test suites
(191c/191d/195c) 59/59 green.

**F-tickets:** Q1 (shop_mgmt raw-dict rows), Q2 (inverse Literal-without-CHECK
drift), Q3 (`VideoResponse` `str,Enum` / missing `videos` CHECKs) — recorded
in the plan as architect-accepted F-ticket dispositions; not 195C scope.

Phase 195C closes. Next per the locked sequence: Phase 196 (Bluetooth OBD),
iOS-blocked pending device — sequencing not opened here.
