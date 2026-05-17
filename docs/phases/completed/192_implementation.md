# Phase 192 — Diagnostic Report Viewer (substrate)

**Version:** 1.0 (plan) + 1.0.1 (pre-Commit-1 reshape) + 1.0.2 (post-architect-review rigor refinements) + 1.0.3 (Builder-D Flag scope-add: migration 040 + atomic worker update) + 1.0.4 (Commit-1 verify: F9 int-typed heuristic refinement folded in) + 1.1 (final: as-built Results + Verification Checklist marked) | **Tier:** Standard | **Date:** 2026-05-05

## Plan v1.1 — Final: as-built Results + Verification Checklist marked

Phase 192 closed at Mobile Commit 4 (`9adefb5` parent + Commit 4 finalize) on 2026-05-05. The substrate-half of the substrate-then-feature pair (Phase 192 viewer / Phase 192B PDF + Share Sheet) shipped across 4 commits with zero fix-cycles after the v1.0.3 path-(α) decision absorbed Builder-D's schema-vs-doc-gap flag.

### Results

| Metric | Value |
|--------|-------|
| Total commits | 4 (1 backend bundled + 3 mobile) |
| Backend tests | 4395 passed, 5 skipped, 0 failed (full regression at Commit 1) |
| Mobile tests at finalize | 363/363 across 26 suites (293 → 363, +70 across the phase) |
| New mobile test files | 5 (useReport hook + report types + reportPresets + reportStuckDetection + reportFormatters) |
| New backend test files | 4 (videos extension + route videos extension + migration 040 + analyzing_started_at atomicity) |
| Schema | 39 → 40 (migration 040 adds `videos.analyzing_started_at TEXT` nullable) |
| F-tickets at finalize | F28 + F29 filed in mobile FOLLOWUPS (both deferred to Phase 192B) |
| Pre-plan amendments | 4 (v1.0.1 reshape + v1.0.2 rigor refinements + v1.0.3 schema scope-add + v1.0.4 heuristic refinement) |
| Architect-side artifacts | 3 (auth-policy ADR + report-document-shape doc + Builder brief) |
| Doc/package versions | backend impl.md 0.13.10 → 0.13.11; pyproject 0.3.1 → 0.3.2; mobile impl.md 0.0.11 → 0.1.2; mobile pkg 0.0.9 → 0.1.2 |

**Key finding**: The substrate-decision-then-Builder pattern unblocked parallel Builder dispatch when substrate decisions spanned multiple files. Phase 192's three architect-side artifacts (auth-policy ADR + shape doc + Builder brief, ~600 lines combined) consumed architect time but enabled Builder-D + Builder-E to dispatch in parallel with zero cross-coordination conflict. Compared against Phase 191B's 5-fix-cycle path where each Builder discovered substrate ambiguity after dispatch, the architect-side-design phase converts implementation-time ambiguity into design-time ambiguity (which is much cheaper to resolve).

**Secondary finding**: F9 discipline persists through architectural decisions. Builder-D's `analyzing_started_at` schema-vs-doc gap surfaced at the right moment (after composer build, before commit) is exactly the pattern 191C+191D's lint rules were designed to catch. Choosing path (α) — add the migration rather than ship the drift — applied the discipline at architect-decision time, before lint had a chance to surface it.

**Tertiary finding**: Heuristic refinements that strictly narrow rules are commit-foldable. The int-typed tightening eliminated 22 false positives without losing any true positives, and folding into Commit 1 preserved the regression artifact's signal-to-noise instead of leaving it noisy until a v1.0.4 amendment.

### Verification Checklist (final)

- [x] Backend videos section variant 5 lands per shape doc Variant 5 (composer + renderer extensions in `builders.py` + `renderers.py`).
- [x] Migration 040 lands with nullable `analyzing_started_at TEXT` column (no default, no backfill, rename-recreate rollback).
- [x] SCHEMA_VERSION 39 → 40 with inline citation; 4 ripple-fix tests updated cleanly.
- [x] Atomic worker update writes both `analysis_state` AND `analyzing_started_at` in single UPDATE when transitioning to analyzing (Contract B).
- [x] Mobile `useReport` hook fetches `GET /v1/reports/session/{session_id}` with proper loading/error/refetch semantics.
- [x] `ReportDocument` discriminated-union types model all 5 variants accurately.
- [x] 5 type-guard predicates discriminate variants at runtime + narrow at compile-time.
- [x] `ReportViewerScreen` renders all 5 variants; preset toggle changes section visibility correctly.
- [x] Stuck-detection: pre-migration NULL → stuck immediately (Contract A); post-migration > 5min → stuck-timeout; ≤ 5min → in-flight; malformed-ISO → stuck-pre-migration.
- [x] F29 ADR posture preserved (cross-owner returns 404; free-tier reads own report).
- [x] SessionsStack registration + SessionDetail "View report" cross-link wired.
- [x] F28 + F29 filed in mobile FOLLOWUPS for Phase 192B pickup.
- [x] All doc + package version bumps recorded.
- [x] Backend phase docs moved in_progress/ → completed/.
- [x] Backend ROADMAP marked ✅; mobile ROADMAP marked ✅; both Phase History rows updated.

### Risks (final — resolution notes)

- **Builder dispatch parallel work surfacing schema-vs-doc gap mid-flight**: did materialize (Builder-D's Flag 1 on `analyzing_started_at`). Resolved via path-(α) bundled v1.0.3 amendment + parallel Builder-E dispatch + final trust-but-verify before bundling Commit 1.
- **SCHEMA_VERSION ripple breakage across 4+ test files**: did materialize. Resolved cleanly via mechanical literal swaps + 1 contract-pin opt-out reason update.
- **F9 false positives at value 40 (post-bump)**: did materialize (22 findings across 8 unrelated tests). Resolved via int-typed heuristic refinement (joined dict/tuple's strict identifier-nearby tier).
- **Visual smoke deferred to Phase 192B prerequisite**: by design per plan Section G — the composition-layer regression covers structural correctness; visual rendering smoke validates against real session data when Phase 192B starts. Documented in phase log.

### Deviations from Plan

- **v1.0 → v1.0.1 reshape**: Plan v1.0 specified building `/v1/reports/session/{session_id}` from scratch. Phase 182 had already shipped it. Reshape pivoted to extension (videos section variant 5) rather than greenfield.
- **v1.0 WeasyPrint assumption → reportlab actual**: caught during shape-doc writing. Phase 182 uses reportlab Platypus, not WeasyPrint. Plan v1.0 Section F's Jinja2 template-inheritance approach was replaced with flowable composition in Python (documented in shape doc for Phase 192B's pre-plan Q&A).
- **v1.0.3 scope-add for migration 040**: Builder-D's mid-build flag on schema-vs-doc gap absorbed via path-(α) bundled amendment + parallel Builder-E dispatch.
- **v1.0.4 F9 heuristic refinement**: SCHEMA_VERSION 39 → 40 surfaced 22 false positives at value 40. Folded into Commit 1 per 191D's surgical-and-contract-preserving precedent.
- **Per-card toggle UI deferred to F28**: plan v1.0.1 Section C1 promised (γ) data shape with (β) UX. Data shape shipped (override map); per-card toggle UI did not (filed as F28 follow-up).
- **Live-tick refresh deferred to F29**: plan Section D didn't explicitly commit to live-tick. ReportViewerScreen re-evaluates stuck-state on focus + preset change; live-tick filed as F29 for Phase 192B.

---

## Plan v1.0.4 — F9 int-typed heuristic refinement folded into Commit 1

This amendment lands during Commit 1's final verify cycle. The SCHEMA_VERSION 39→40 bump (from migration 040) surfaced **22 false positives** in `scripts/check_f9_patterns.py --check-ssot-constants` where the literal `40` (or `40.0`) coincidentally matched the new `SCHEMA_VERSION` value across 8 unrelated test files (Phase 06 / 115 / 122 / 140 / 141 / 143 / 158 / 163) where the test imported some sibling module of `motodiag.core.database` for unrelated reasons.

### Root cause: Phase 191D's import-match heuristic too loose for ints

Phase 191D's per-type heuristic at `scripts/check_f9_patterns.py:867-895` had different posture per `value_type`:

- **dict / tuple**: require identifier-nearby (proximity match against the registry name OR a dict key within ±3 lines).
- **int / str**: identifier-nearby OR source-module imported.

The two-path branch for ints was too loose: integer values like `40` are *commonly* coincident with unrelated test literals (counts, percentages, durations, timeouts). A test file importing `motodiag.core.database` for `init_db` and asserting `assert response['count'] == 40` would fire as a false-positive `SCHEMA_VERSION` literal-pin.

This is structurally the same false-positive shape Phase 191D itself had to fix when 82 hits surfaced from `from motodiag.api import create_app` matching every `motodiag.api.*` SSOT entry — except the prior fix only tightened import-direction matching, not the per-type heuristic for inherently-coincidence-prone types.

### Fix: int joins dict/tuple in the require-identifier-nearby tier

`scripts/check_f9_patterns.py:870` changed from `if entry.value_type in ("dict", "tuple"):` to `if entry.value_type in ("dict", "tuple", "int"):`. The else-branch (import-match OR identifier-nearby) now applies only to `str`-typed entries. String literals are far less coincidence-prone than integers — `"v1"`, `"sonnet-3-5"`, etc. are domain-specific enough that import-match alone is meaningful signal.

Comment block at lines 844-880 expanded to document the per-type rationale + the Phase 192 surfacing context. The Phase 191D existing comment for dict/tuple is preserved verbatim; the new int paragraph cites the 22-finding surfacing + the 8 unrelated test files.

### Why folded into Commit 1 vs deferred to its own phase

Per Phase 191D's own discipline (the "fold heuristic refinements into the same commit when surgical and contract-preserving" precedent established during 191D's fix-cycle): refinements that strictly *narrow* the rule (fewer false positives, no new false negatives) and that are surgical (one-line conditional change + comment update) belong in the commit that surfaced them. Deferring would leave Commit 1's regression artifact noisy with 22 false positives for an unknown number of days, training future readers to ignore the lint output — exactly the F9 anti-pattern this whole rigor stream was designed to prevent.

Contract preservation: the refinement only narrows. Every previously-flagged finding under the new posture is still flagged (proven by re-running `--check-ssot-constants` post-refinement: clean, no losses to the existing-flagged set). The 22 false positives at value `40` simply stop firing because none of those 8 test files have `SCHEMA_VERSION` (or `database`) as an identifier within ±3 lines of the literal — which is the correct outcome.

### What's NOT in v1.0.4

The `test_phase191b_serve_migrations.py:98` SCHEMA_VERSION 39→40 ripple was a separate trivial fix (literal swap + docstring update + output-match string update) — it's bundled in the same Commit 1 commit but doesn't need amendment-level documentation. It's a mechanical version-bump consequence, not an architectural decision.

### Updated commit plan (revised from v1.0.3)

Commit 1 now bundles:
- Builder-D's composer + renderer extensions + tests + `pyproject.toml` bump.
- Builder-E's migration 040 + worker update + new tests.
- Architect's shape doc Flag 2 fix.
- v1.0.3 amendment commit text (already in `docs/phases/in_progress/192_implementation.md`).
- v1.0.4 amendment commit text (this section).
- F9 heuristic refinement (`scripts/check_f9_patterns.py`).
- `test_phase191b_serve_migrations.py:98` ripple fix.

Single Commit 1 commit lands all seven streams together. Architect runs full regression + F9 lint + targeted Phase 192 + Phase 191D test suites before committing.

---

## Plan v1.0.3 — Builder-D Flag scope-add: migration 040 + atomic worker update

This amendment lands during Commit 1's implementation cycle. Builder-D's report (post-implementation, pre-commit) surfaced two architectural concerns; this amendment captures the v1.0.3 scope-add for Flag 1 (the load-bearing one) + the unilateral docs fix for Flag 2 (clarity bug, no architect decision needed).

Per Kerwyn's bundling discipline: "don't fragment v1.0.2 + v1.0.3 by surfacing-time" — but v1.0.2 was already shipped (commit `e29e70c`) at the time Builder-D's report arrived. v1.0.3 lands the new items as a separate amendment per the audit-trail-preservation principle (sealed-history amendments don't get retroactively rewritten). The bundling discipline applies forward: don't fragment Flag 1 + Flag 2 across separate amendments by surface time, even though they surfaced at the same moment from the same Builder report.

### Item 1: Flag 1 — `analyzing_started_at` schema-vs-doc gap → migration 040 added to Commit 1 scope

**Discovery context**: Builder-D's report (after composer + renderer extension + tests landed clean) flagged that `analyzing_started_at` does NOT exist as a column on the `videos` table. Migration 039 (`src/motodiag/core/migrations.py:2790`) defines the videos table with `analyzed_at TEXT` only. Shape doc Variant 5 + plan v1.0.1 Section D both depend on the column for the 5-min stuck-in-analyzing detection. Builder-D stubbed the field as `None` to satisfy the shape contract, surfaced the gap, and invited the architect's decision.

**Three options surfaced; (a) accepted with full F9-discipline reasoning:**

- **(a) Add migration 040 in this commit + worker update for atomic state-transition write.** Scope expansion but small; aligns with F9 discipline (schema-vs-doc drift IS the F9 family pattern; 191D's `--check-ssot-constants` lint would catch the stub-as-None-forever drift on next audit; shipping known schema-vs-doc drift in Commit 1 of the next phase would be architecturally embarrassing — 191C+191D's whole intervention was to convert silent drift into noisy lint findings).
- (b) Defer column + keep None-stub; mobile drops stuck-detection in Commit 3 OR substitutes with `analyzed_at`-derived heuristic. **REJECTED** — unwinds Section D's pre-defined feature for wrong reason. Section D specifically rejected "deferring predictable surface to F-ticket-only"; production traffic will surface stuck-analyzing states. Discovery makes the case for stuck-detection stronger, not weaker.
- (c) Repoint shape doc to use `analyzed_at` instead, drop stuck-detection feature. **REJECTED** — `analyzed_at` is completion-timestamp, can't semantically replace start-timestamp for stuck-while-analyzing. Worst kind of scope-preservation: ships less and pretends it didn't.

**Two architect-baked contracts for Builder-E's brief**:

**Contract A — Migration nullability is load-bearing for back-compat.** Existing video rows from Phase 191B smoke predate the column. Migration adds `analyzing_started_at` as nullable, no default, no backfill. Existing rows stay with `analyzing_started_at IS NULL`. Mobile stuck-detection (Commit 3 scope) must handle `analysis_state = "analyzing" AND analyzing_started_at IS NULL` as **pre-migration indeterminate** — surface as stuck immediately rather than waiting 5 minutes from now. Edge case in Builder-E's brief + test plan; forward-looking flag for Commit 3's mobile work.

**Contract B — Worker update needs atomic state-transition guarantee.** Current `pending → analyzing` transition is a single UPDATE. New column MUST be set in the SAME UPDATE atomically. Two-statement implementation (UPDATE state THEN UPDATE timestamp) creates a race window where the row sits in `analyzing` with `analyzing_started_at = NULL` and triggers the pre-migration stuck path inappropriately. **Single SQL statement, not two**; tests verify atomicity. Per F9 subspecies (v) "self-validating-test-setup" prevention — the format of the timestamp also matters: if existing column writes use SQLite's `datetime('now')` directly in SQL, USE THE SAME PATTERN to avoid the F9 instance #5 bug shape (Phase 191B fix-cycle-1's date-boundary latent bug).

**Builder-E dispatch**: ran in parallel with this amendment per Kerwyn's "don't serialize the dispatch behind the amendment" direction. Builder-E reads the migration spec + atomicity guarantee + nullability contract; doesn't depend on amendment-prose. Architect commits Builder-D's existing Commit 1 work + Builder-E's migration extension as a single Commit 1 once both report.

**Scope expansion accounting**:
- New migration entry in `src/motodiag/core/migrations.py` (migration 040; `ALTER TABLE videos ADD COLUMN analyzing_started_at TEXT`).
- `SCHEMA_VERSION 39 → 40` in `src/motodiag/core/database.py`.
- ~10-line worker update at the existing `pending → analyzing` state-transition site (single UPDATE atomicity).
- New `tests/test_phase192_migration_040.py` (~5 tests mirroring `test_phase191b_migration_039.py` pattern).
- New `tests/test_phase192_analyzing_started_at_atomicity.py` (~3 tests: timestamp-set + atomic-single-update + analyzed-doesn't-clear).

### Item 2: Flag 2 — `findings_list` vs `findings` shape-doc bug → unilateral docs fix

**Discovery context**: Builder-D's report flagged that `motodiag.media.vision_analysis.VisualAnalysisResult.findings` is literally the field name (`vision_analysis.py:61`) — `model_dump()` produces `{"findings": [...]}`, NOT `{"findings_list": [...]}`. Shape doc was wrong on TWO places (Variant 5 inline example used `findings_list`; Naming consistency notes claimed `findings_list` IS the convention). Both wrong vs Pydantic source. Builder-D used `model_dump()` verbatim per brief mandate; tests assert `findings["findings"]` is the list (correct).

**Disposition**: architect fixes shape doc unilaterally (no architectural decision needed; clarification only). Two-spot edit:
- Line 109 (Variant 5 example): `"findings_list":` → `"findings":` + inline comment annotating the Pydantic source.
- Line 275 (Naming consistency notes): claim corrected + Pydantic source annotation added per Kerwyn's refinement (`field name verified against vision_analysis.py:61`). Annotation makes source-of-truth legible so next drift gets caught at write-time. Same audit-trail-preservation discipline that's been load-bearing throughout the chain.

**Builder-D's existing implementation is correct** — used `model_dump()` per brief; tests pass against the actual Pydantic shape. No code change needed for Flag 2.

### Item 3: Shape doc Variant 5 references migration 040 as schema substrate

Shape doc Variant 5's `analyzing_started_at` field documentation now includes a "Schema substrate" subsection that explicitly references migration 040 + the nullability contract + the pre-migration-indeterminate handling for mobile + Contract B's atomicity guarantee. Future contributors reading the shape doc see the schema-substrate dependency without having to grep migrations.py.

### What's NOT in v1.0.3 (already covered by v1.0.2)

The four ADR/shape-doc rigor refinements + reportlab/Jinja2 ergonomics gap + 192B-no-Jinja-assumption phase log note already landed at v1.0.2 (`e29e70c`). v1.0.3 doesn't repeat them. Future readers walking the amendment chain see v1.0.1 (pre-Commit-1 reshape) + v1.0.2 (post-architect-review rigor refinements) + v1.0.3 (Builder-D Flag scope-add) in chronological order.

### Updated commit plan

Commit 1 now bundles:
- Builder-D's composer + renderer extensions + tests + `pyproject.toml` bump (already implemented; trust-but-verified PASS at 14/14 + 58/58 regression).
- Builder-E's migration 040 + worker update + new tests (in flight).
- Architect's shape doc Flag 2 fix (Items 2 + 3 of this amendment).
- This v1.0.3 amendment commit.

Single Commit 1 commit lands all four streams together once Builder-E reports. Architect runs full trust-but-verify across Builder-D's existing work + Builder-E's new work + the regression sample + the manual schema check before committing. Commit message frames Commit 1 as the bundled substrate-extension + schema-substrate + docs-fix + amendment landing.

### Architect's reasoning for the path-(α) acceptance (verbatim from review pass)

> Schema-vs-doc drift IS the F9 pattern. Stubbing as None-forever is silent drift; 191D's `--check-ssot-constants` lint would catch it on next audit. Shipping known schema-vs-doc drift in Commit 1 of the next phase would be architecturally embarrassing — 191C+191D's whole intervention was to convert silent drift into noisy lint findings. The discipline requires not shipping the pattern those phases targeted. Scope expansion is real but small: nullable column add (no default, no backfill, no constraint), ~10 line worker update at existing state-transition point, mechanical against existing patterns.

The reasoning is logged here as the load-bearing precedent for future Builder-flag scope-decisions: when implementation surfaces architectural drift between docs and reality, the discipline established by 191C+191D is to fix the drift rather than ship around it. Future contributors walking this amendment see the precedent.

---

## Plan v1.0.1 — pre-Commit-1 reshape: Phase 182 IS the substrate

This amendment lands BEFORE any architect-side schema-design work or Builder dispatch. The amendment is the pre-build deep-survey discipline catching what plan v1.0 didn't see: **Phase 182 already shipped the report-route surface that plan v1.0 specified building from scratch.** Discovering this NOW vs at Commit 1 verification is exactly when the substrate-extension work should pivot — same lesson as Phase 191B's HVE-shape bug (F9 catalog #1), but caught at pre-architect-deliverable time instead of fix-cycle time.

Plan v1.0 sealed history preserved verbatim per the audit-trail-preservation principle established at Phase 191C v1.0.1.

### What plan v1.0 unknowingly re-specified

| Plan v1.0 specified (NEW) | Phase 182 already shipped |
|---|---|
| `src/motodiag/api/routes/reports.py` | Already exists. 163 lines. 6 endpoints (session/work-order/invoice × json/pdf). |
| `src/motodiag/api/report_composer.py` | `motodiag.reporting.builders.build_session_report_doc()` is the existing composer. 126 lines. |
| `GET /v1/sessions/{id}/report` (sessions/ prefix) | `GET /v1/reports/session/{id}` already exists (reports/ prefix). |
| `models/report.py` Pydantic `ReportPayload` | `ReportDocument = dict[str, Any]` — Phase 182 chose freeform dict over Pydantic. |
| 192B's `/v1/sessions/{id}/report.pdf` | `GET /v1/reports/session/{id}/pdf` already exists. PDF rendering already shipped. |
| Auth: session-owner-or-shop-tier-member | Phase 182: `get_session_for_owner(session_id, user_id)` — owner-only; cross-user → `SessionOwnershipError` → **404, not 403**. Subtly stricter; existence-disclosure-prevention. |
| Vision findings + video integration | **Entirely absent from Phase 182's builder.** Predates Phase 191B's videos table. |

### Reshape (a) accepted: Phase 182 IS the substrate

Substrate-then-feature isn't a clock-time pattern; it's a logical-dependency pattern. Plan v1.0 not knowing about Phase 182 was the bug; the reshape corrects it:

- **Phase 182** was always the substrate (report builders + PDF renderer + 6 routes).
- **Phase 192** is the FEATURE half — mobile viewer + section-toggle preset system + Vision findings extension to the existing builder.
- **Phase 192B's scope collapses** to mobile Share Sheet wiring + (maybe) section-toggle query param on the existing PDF route + (maybe) PDF template extension for the videos/Vision sections. Probably 2-3 commits, not 5.

Two surfaces returning the same logical data is the F9 family pattern this chain has been hardening against — drift-prone-by-design. Reject (b) on principle; defer (c) to F32.

### Specific scope changes in 192's plan-of-record

**Backend (Commit 1) — substantially reduced from plan v1.0:**

DROPPED from plan v1.0:
- ❌ `src/motodiag/api/routes/reports.py` (NEW) — already exists from Phase 182.
- ❌ `src/motodiag/api/report_composer.py` (NEW) — `build_session_report_doc()` IS the composer.
- ❌ `models/report.py` Pydantic `ReportPayload` (NEW) — back-compat preserved with dict surface; Pydantic migration deferred to F32.
- ❌ `GET /v1/sessions/{id}/report` route (NEW) — mobile uses existing `/v1/reports/session/{id}`.
- ❌ Composer pytest suite as a new file — extension tests fold into existing Phase 182 test surface.

ADDED in 192's reshape:
- ✅ EXTEND `motodiag.reporting.builders.build_session_report_doc()` to include videos + Vision findings sections (per Phase 191B's videos table + analysis_findings).
- ✅ NEW `docs/architecture/auth-policy.md` (F29 ADR, re-derived around Phase 182's owner-only-with-404 pattern; explicit existence-disclosure-prevention rationale in WHY narrative).
- ✅ NEW `docs/architecture/report-document-shape.md` (free byproduct of architect understanding the existing dict shape well enough to extend it; future contributors extending further don't re-derive conventions; audit-trail-preservation discipline).
- ✅ NEW pytest extensions covering the videos/Vision findings section integration against Phase 191B seeded video fixtures.

**Mobile (Commits 2-4) — mostly unchanged from plan v1.0:**

- `ReportViewerScreen` + `SectionToggle` + `ReportCard` + `useReport` hook: still NEW.
- `useReport` fetches from existing `GET /v1/reports/session/{sessionId}` (the prefix differs from plan v1.0's spec — `/reports/session/N` not `/sessions/N/report`).
- Viewer renders the dict-based ReportDocument shape via runtime parsing rather than typed Pydantic — slight quality loss in TypeScript narrowing but acceptable for a single-surface consumer; F32 escalation handles the typed-migration path.
- All Section I empty/error-state policy decisions still apply.
- All cross-cutting placeholder copy register strings still apply (only the field-shape mapping changes; placeholder copy is independent).

**Auth posture refinement (Section E):**

Phase 182's owner-only-with-404 pattern is **stricter** than plan v1.0's session-owner-or-shop-tier-member spec. The 404-not-403 choice prevents existence-disclosure on cross-user lookups (a non-owner can't distinguish "session doesn't exist" from "session exists but isn't yours" — both return 404). This is a security-meaningful improvement, not just a naming difference. F29 ADR documents the WHY explicitly.

**Smoke gate Section G refinement:**

Plan v1.0 step 7 (free-tier-user-can-read-own-report-but-not-other-users) becomes:
- Free-tier user fetches own session's report via `/v1/reports/session/{their_id}` → 200 OK ✓
- Free-tier user fetches OTHER user's session report via `/v1/reports/session/{other_id}` → **404** (not 403) — verifies existence-disclosure-prevention pattern.

Plan v1.0 step 9 (composition layer regression sweep BEFORE UI testing) becomes:
- `pytest tests/test_phase182_reports.py tests/test_phase192_videos_extension.py` against fixtures covering full / empty / incomplete-Vision / mixed-analysis sessions.

### F-ticket changes

- **F29 (auth-policy ADR)** — content reshape: precedent body now explicitly includes Phase 182's `SessionOwnershipError → 404` pattern (the strictest of all Track-I read endpoints). WHY narrative: "owner-only-on-read prevents existence-disclosure on cross-user lookups; tier gating is for scarce resources (vehicle/session creation), not for read access to your own data." ADR explains trade-offs (why 404-not-403 was chosen for sessions specifically, vs vehicles' explicit 403 cross-owner; the difference is information-disclosure sensitivity — vehicle existence is non-sensitive in a multi-tenant garage; session existence MAY be sensitive in cases where the session itself is private).
- **F32 (NEW)** — eventually migrate dict-based `ReportDocument` to typed Pydantic. Promotion trigger: when a third report-consuming surface lands. Phase 182's PDF route is consumer #1; Phase 192's mobile viewer is consumer #2; the third triggers F32 to its own dedicated typing-modernization phase. Rationale for not migrating in 192: couples 192's delivery risk to refactor of unrelated upstream code; wrong shape for substrate-extension work.

### 192B forward-looking flag

192B's plan-of-record needs its own pre-plan Q&A pass AFTER 192 finalizes. The substrate changed underneath 192B; the feature half should re-derive its scope against the actual substrate state, not the originally-planned substrate state. Probably 2-3 commits, not 5. Don't write 192B's plan from plan v1.0's framing; rewrite from post-192-finalize state.

Specific 192B scope candidates that emerge from the reshape:
- Mobile Share Sheet integration (existing PDF route is the share target; mobile wires `Share` API to download + re-share the PDF binary).
- Section-toggle query param on the existing PDF route (e.g., `?sections=vehicle,symptoms,...`) — backend renderer filters before PDF generation.
- PDF template extension for the videos/Vision findings sections (Phase 182's renderer may need new template blocks for the new section shapes).
- Section-toggle UX in the share flow — does the user pick preset before tap-share, or after?

### Architect-side deliverables BEFORE Builder dispatch

Three artifacts to produce architect-side; Builder gets a tight brief once these land:

1. **`docs/architecture/auth-policy.md` (F29 ADR)** — narrative-quality writing about the policy decision + existence-disclosure rationale + alternatives considered + consequences for future contributors. ~80-120 lines.
2. **Videos/Vision findings nesting design** — specific decision: top-level section vs nested-under-videos for Vision findings (mobile viewer's per-video-expansion UX from Phase 191B suggests nested; PDF's "Vision findings" cross-video summary suggests peer-section — pick one and document why); empty-state conventions matching Phase 182's existing patterns (audit before introducing new). Lands as inline design notes in `docs/architecture/report-document-shape.md`.
3. **`docs/architecture/report-document-shape.md`** — documents Phase 182's existing dict shape conventions inline with this phase. Free byproduct of architect understanding the shape well enough to extend it. Future contributors extending further don't re-derive conventions. Sections covered: top-level fields (title, subtitle, issued_at, sections list, footer); section types (rows, bullets, table, body); empty-state conventions (omit section vs render with placeholder vs always-present); naming patterns; relationship to Phase 192's videos/Vision findings extension.

Builder dispatch is MORE attractive under reshape (a) than under plan v1.0 — mechanical work against documented shape conventions + clear architectural target. Architect produces the three artifacts above; Builder extends `build_session_report_doc()` + adds tests against Phase 191B seeded video fixtures.

### Updated commit plan (4 commits, was 5)

**Commit 1** — Architect lands the three architecture artifacts (F29 ADR + report-document-shape.md + videos nesting design embedded in report-document-shape.md). Backend extends `build_session_report_doc()` per the design. Pytest extension tests cover videos/Vision findings sections against Phase 191B seeded fixtures. pyproject 0.3.1 → 0.3.2.

**Commit 2** — Mobile `useReport` hook + types (against existing `/v1/reports/session/{id}` endpoint; openapi-typescript regenerates types from existing OpenAPI snapshot, NOT from new schema).

**Commit 3** — Mobile `ReportViewerScreen` + `SectionToggle` + `ReportCard` (all 6 cards, all I1-I9 placeholder/empty-state policy, section-toggle preset, 30s focus-debounce, pull-to-refresh, stuck-in-analyzing surface).

**Commit 4** — Mobile cross-link from SessionDetailScreen + nav registration + finalize (collapsed from plan v1.0's separate Commits 4 + 5 since reshape eliminated enough work to merge them).

### Updated versioning targets at v1.1 finalize

Unchanged from plan v1.0:
- Backend `pyproject.toml`: 0.3.1 → 0.3.2.
- Backend `implementation.md`: 0.13.10 → 0.13.11.
- Mobile `package.json`: 0.0.9 → 0.0.10.
- Mobile `implementation.md`: 0.0.11 → 0.0.12.
- Schema unchanged at v39.

### Why this amendment lands BEFORE Commit 1 (not as a v1.0.1 post-finalize amendment like 191D's was)

191D's v1.0.1 amendment was lessons-learned recording AFTER finalize — fresh-recall discipline. 192's v1.0.1 amendment is a pre-build reshape — discovered architectural mismatch between plan and reality at architect-side-survey time. Different timing because different purpose:

- 191D's amendment: corrections + reusable methodology after the work is done.
- 192's amendment: scope reshape after pre-build deep-survey but BEFORE the work starts.

Both are "v1.0.1" by convention but the difference matters: 192's reshape would be a much more expensive correction if applied mid-Commit-1 (would mean reverting work, re-dispatching) or post-finalize (would mean fixing the calcified parallel surface). Pre-Commit-1 is the cheapest correction point; pre-build deep-survey is what makes the cost asymmetry visible early.

---

Build the mobile-side substrate viewer for diagnostic session reports — comprehensive read-only surface combining vehicle context + symptoms + fault codes + AI diagnosis + Vision findings + lifecycle audit. Lay the composition layer + section-toggle preset system with PDF/share as known downstream consumers (Phase 192B). First user-facing read-and-share surface in the app, after a long substrate-then-feature-then-meta-tooling stretch through Phases 191/191B/191C/191D.

CLI: none new (mobile screen + backend endpoint).

Outputs: `ReportViewerScreen` on SessionsStack + cross-link from SessionDetailScreen + `useReport(sessionId)` hook + `motodiag.api.report_composer.compose(session_id)` Python module + `GET /v1/sessions/{id}/report` FastAPI route.

**Scope honesty**: despite the "viewer" framing, this phase has **~30% backend scope** — single new GET endpoint + composer module + composer pytest suite + route integration tests. Pre-plan Decision B made this explicit; plan-of-record reflects it.

## Scope decisions locked at pre-plan Q&A (2026-05-05)

All A through I + cross-cutting placeholder review accepted with refinements:

- **A — Substrate-feature boundary**: (a) 192 = viewer + composition layer + section-toggle state; 192B = PDF route + Share Sheet integration only. Composition layer testable independently of both viewer + PDF consumers — `report_composer.compose(session_id) → ReportPayload` gets its own pytest suite that doesn't go through HTTP. Decoupled at the start so the composition module doesn't tightly couple to its first consumer.
- **B — Mobile composition / data-fetch shape**: (i) new `GET /v1/sessions/{id}/report` endpoint; backend composes `ReportPayload`; one mobile fetch; PDF route at 192B consumes the same composer.
- **C1 — Toggle granularity**: (γ) data shape with (β) UX. Per-card override map is data-model source of truth; UI exposes only Customer-facing / Insurance-facing presets at first; future "expose per-card UI" F-ticket adds advanced affordance without touching state shape.
- **C2 — Toggle state location**: (ε) session-only (component state). **F28** filed with measurable trigger: per-mechanic preset preference persistence escalates to its own ticket if 192B smoke gate or first 2 weeks of usage surface "every share + close + re-open re-prompts preset" as friction.
- **C3 — Default visibility**: (η) full-surface (Insurance-facing preset) default. No auto-detection — mis-categorizing as insurance-related leaks billing info into customer renders.
- **D — Incomplete Vision rendering**: (iii) filter-with-count. Pre-defined stuck-in-analyzing edge: 5-min threshold; count display becomes "(1 of 3 analyzed, 1 stuck — tap to retry)" with stuck count in amber; retry affordance with explicit "report stuck analysis" surface.
- **E — Backend route surface**: (a) two distinct routes (`.json` for viewer at 192, `.pdf` at 192B). Auth posture: `require_api_key` + `session_owner_or_shop_tier`; tier requirement zero (reading own report is base-tier). **F29** filed: ADR-shape document "read access doesn't gate on tier; create access does" emergent rule across Phase 188/189/191B/192.
- **F — Template engine** (192B-scope, sketched here): Jinja2 — already a transitive FastAPI dep; zero new deps. Note for 192B: WeasyPrint CSS support is good but not perfect — flexbox supported, CSS Grid partial, complex transforms fail silently. Design template on conservative CSS (block + flex + table; no Grid).
- **G — Smoke-gate rhythm**: visual/UX-heavy rather than data-heavy; recovers user-facing-surface-delivery discipline after the integration-heavy Track I run. 192 viewer single-architect-session smokeable (~30-45 min, no live API calls). Step 9 added: composition layer regression sweep — pytest tests against 3-4 distinct seeded sessions BEFORE any UI testing (catches composer regressions before they surface as silent UI rendering issues). 192B Step 8 added: deterministic-rendering verification — generate same session's PDF twice with same preset, byte-compare for identical output.
- **H — Branch + commit cadence**: separate branches per phase (`phase-192-diagnostic-report-viewer` + `phase-192B-report-pdf-share`), rebase-merge at finalize. 192 Commit 1 includes FastAPI TestClient integration tests so Commit 2's mobile work proceeds against known-working contract.
- **I1 — No fault codes**: (b) "No fault codes recorded for this session" placeholder.
- **I2 — No diagnosis yet**: (b) with copy "Diagnosis not yet generated. N of 2 symptoms recorded; add (2-N) more to enable AI diagnosis."
- **I3 — No videos at all**: (a) hide videos card entirely when zero. Composer omits the videos field; no explicit hide-logic mobile-side.
- **I4 — Lifecycle**: as written; PDF metadata band (192B) includes "Report generated YYYY-MM-DD HH:MM EDT while session was [open/closed]".
- **I5 — Network failure**: (a) error state with retry. **Open question**: does Phase 187's `describeError` already distinguish network-unreachable vs backend-unreachable? If not, file as small cross-cutting error-state polish F-ticket (provisionally F31 — to be confirmed during build).
- **I6 — Backend 404**: (a) framing with refined copy: "This session is no longer available. It may have been deleted." + Back-to-sessions affordance.
- **I7 — Auth 401**: (b) error state with copy: "Your API key is no longer valid. Re-enter your key via Home → API key card to continue." Inherit Phase 187's existing pattern if it covers the case; otherwise this is the spec.
- **I8 — No symptoms yet**: (b) symmetric with I2. Copy: "No symptoms recorded yet. Add symptoms via SessionDetail → Symptoms."
- **I9 — Empty composer payload (defensive)**: (a) "Report unavailable for this session" + retry + `console.warn` logline including session ID + user ID + timestamp + structural shape of malformed payload (missing fields, unexpected nulls). **F30** filed: emit backend telemetry event when defensive empty-payload case fires, so composer regressions surface in backend logs not just frontend ones.
- **I10 — Focus re-fetch**: (b) 30-second debounce — re-fetch on focus only if last fetch >30s ago. Pull-to-refresh remains as explicit force-refresh for "something changed, fetch now" cases. Round-trip cost discipline per Phase 188 HVE saga.
- **Cross-cutting placeholder copy review**: 10-minute voice/tone pass during plan v1.0 writing; all placeholder strings pulled into a single section + reviewed as a coherent set. See "Placeholder copy register" below.

## Outputs

### New files

**Backend (~5):**
- `src/motodiag/api/models/report.py` — `ReportPayload` Pydantic model + `ReportSection` enum + per-card sub-models (`ReportVehicleCard`, `ReportSymptomsCard`, `ReportFaultCodesCard`, `ReportDiagnosisCard`, `ReportVideosCard`, `ReportLifecycleCard`).
- `src/motodiag/api/report_composer.py` — `compose(session_id, db_path) → ReportPayload` pure function. Reads from session_repo + video_repo + diagnosis surface + lifecycle. **No HTTP layer dependency**; testable directly via the composer's own pytest suite.
- `src/motodiag/api/routes/reports.py` — FastAPI router with `tags=["reports"]` (the `reports` tag already exists in TAG_CATALOG — Phase 183 forward-looking placeholder claimed at last). `GET /v1/sessions/{id}/report` route consumes `report_composer.compose()` + returns the `ReportPayload` JSON.
- `tests/test_phase192_report_composer.py` — composer pytest suite (~10-12 tests across 3-4 fixture sessions: full, empty/early-stage, incomplete-Vision, mixed-analysis-states).
- `tests/test_phase192_report_route.py` — FastAPI TestClient integration tests for the route (~6-8 tests covering happy path + 401 + 403-cross-owner + 404 + tier-bypass-on-read regression guard).

**Mobile (~6):**
- `src/screens/ReportViewerScreen.tsx` — top-level viewer screen on SessionsStack. Renders the 6 cards (Vehicle / Symptoms / Fault Codes / Diagnosis / Videos / Lifecycle) per the section-toggle preset; section-toggle UI in screen header; pull-to-refresh; loading + error + empty states.
- `src/components/report/SectionToggle.tsx` — preset switcher component (Customer-facing / Insurance-facing). Single visible affordance; per-card override map is the underlying state but the UI exposes only the two presets.
- `src/components/report/ReportCard.tsx` — shared card-shaped wrapper used by all 6 sections (consistent padding, header, expand/collapse semantics if any, empty-state placeholder rendering policy).
- `src/hooks/useReport.ts` — fetches `ReportPayload` from `/v1/sessions/{id}/report`. Includes 30s focus-debounce per I10 + pull-to-refresh + polling integration with existing `useSessionVideos` for incomplete-Vision count updates.
- `src/types/report.ts` — re-exports the openapi-typescript-generated `ReportPayload` types as named aliases for consumers (mirrors Phase 188's pattern for SessionResponse types).
- `__tests__/hooks/useReport.test.ts` — Jest tests for the hook (~8-10 tests covering fetch happy path + 30s debounce + pull-to-refresh + 401/404/network errors + polling-integration smoke).

### Modified files

**Backend (~3):**
- `src/motodiag/api/__init__.py` — register the new `reports` router.
- `src/motodiag/api/app_factory.py` (or wherever routers attach) — include reports router under `/v1/sessions` prefix-overlay.
- `api-schema/openapi.json` — refresh after backend changes (mobile regenerates types from this).

**Mobile (~4):**
- `src/navigation/SessionsStack.tsx` — register `ReportViewerScreen` route.
- `src/navigation/types.ts` — add `ReportViewerScreen` route param-list entry.
- `src/screens/SessionDetailScreen.tsx` — add "View report" CTA (cross-link to ReportViewerScreen with sessionId param). Placement: footer of the screen, below all 6 content cards, above lifecycle card if it stays at the bottom. Visual: secondary-button style.
- `src/api-types.ts` — regenerate via `npm run generate-api-types` after backend openapi.json refresh.

## Logic

### Backend `report_composer.compose(session_id, db_path) → ReportPayload`

Pure function — no HTTP layer dependency. Reads from existing repos:

1. **Vehicle card**: `session_repo.get_session(session_id)` → vehicle make/model/year/protocol/powertrain + Phase 188 metadata (battery chemistry / engine type / etc.).
2. **Symptoms card**: `session_repo.get_session_symptoms(session_id)` → list of symptom rows (text + severity + recorded_at).
3. **Fault codes card**: `session_repo.get_session_fault_codes(session_id)` → list of fault code rows (code + make/family + recorded_at). Empty list = "No fault codes" placeholder per I1.
4. **Diagnosis card**: `session_repo.get_session_diagnosis(session_id)` → diagnosis text + AI model + tokens + cost + generated_at. None/empty = "Diagnosis not yet generated. N of 2 symptoms recorded..." placeholder per I2.
5. **Videos card**: `video_repo.list_session_videos(session_id)` → list of video rows. **Empty list = composer omits the videos field entirely** per I3 (the mobile renderer hides the card when the field is absent; no explicit hide-logic mobile-side).
6. **Lifecycle card**: `session_repo.get_session(session_id).status / created_at / closed_at` + (per F3 deferred lifecycle history work) any reopen events.

**Section override-map state** is NOT composer responsibility — composer always returns the full payload; mobile's section-toggle-state filters at render time. PDF route at 192B will accept a `?sections=...` query param to filter at composer-output time, but that's 192B scope. **Composer at 192 returns everything**; mobile selects what to show.

**Stuck-in-analyzing edge**: composer doesn't compute "stuck" state; it returns each video's `analysis_state` + `analyzing_started_at` timestamps. **Mobile-side computes stuck**: any video with `analysis_state === 'analyzing'` AND `(now - analyzing_started_at) > 5min` is rendered as stuck.

### Backend `GET /v1/sessions/{id}/report` route

- Auth: `require_api_key` + `session_owner_or_shop_tier_member` (existing Phase 187/188 pattern).
- **Tier requirement: zero.** Reading own session is base-tier. Smoke gate has explicit free-tier-user-can-read-own-report-but-not-other-users test (Section E refinement) — tier-bypass-on-read is exactly the auth edge that gets accidentally tightened during refactors.
- Response: `ReportPayload` JSON (Pydantic model serialized).
- Error responses:
  - 401: invalid/missing API key (existing Phase 187 ProblemDetail envelope).
  - 403: session-owner check fails AND user is not a shop-tier member of the session's shop (existing Phase 188 cross-owner pattern).
  - 404: session not found (or soft-deleted).
  - 5xx: backend error; mobile renders defensive empty-payload state per I9.
- **No tier-bypass-on-read**. Smoke must include explicit test confirming free-tier user can fetch their own session's report.

### Mobile `useReport(sessionId)` hook

```ts
function useReport(sessionId: number): {
  report: ReportPayload | null;
  isLoading: boolean;
  error: ReportError | null;
  refresh: () => Promise<void>;     // pull-to-refresh
};
```

- Fetch on mount.
- **30-second focus-debounce per I10**: tracks `lastFetchAt` timestamp; on `useFocusEffect` re-entry, re-fetch only if `(now - lastFetchAt) > 30000`.
- Pull-to-refresh always re-fetches (overrides debounce — explicit user action).
- **Polling integration with `useSessionVideos`**: viewer reads videos via the report payload, but `useSessionVideos` already polls every 5s while any video is `pending`/`analyzing`. Viewer subscribes to `useSessionVideos`'s polled state for the videos card section; the hook re-renders when polled state updates the video rows. Reduces redundant fetches (don't re-fetch the entire report just because one video moved `analyzing` → `analyzed`).
- Error handling: 401 → re-auth flow per I7 (error-state copy directs to Home → API key); 404 → soft-deleted-session copy per I6; network failure → retry-button per I5.

### Mobile `ReportViewerScreen.tsx` rendering policy

Top-down render order (post-section-toggle filter):

1. Vehicle card (always shown unless toggle hides; default = shown)
2. Symptoms card (per I8 placeholder if empty)
3. Fault codes card (per I1 placeholder if empty)
4. Diagnosis card (per I2 placeholder if pending)
5. Videos card (per I3 hidden when zero videos)
6. Vision findings card (per I3 + D filter-with-count; stuck-in-analyzing surface per D refinement)
7. Lifecycle card (always shown; rendering per I4)

**SectionToggle component** (header):
- Two pill buttons: "Customer-facing" + "Insurance-facing" (default selected).
- Selecting changes the underlying override map; viewer re-renders with section visibility per the override map.

**Section override map state shape** (per C1 (γ) data shape with (β) UX):
```ts
type ReportOverrideMap = {
  vehicle: boolean;
  symptoms: boolean;
  faultCodes: boolean;
  diagnosis: boolean;
  videos: boolean;
  visionFindings: boolean;
  lifecycle: boolean;
};

const PRESETS: Record<'customer' | 'insurance', ReportOverrideMap> = {
  customer: {
    vehicle: true,
    symptoms: true,
    faultCodes: true,
    diagnosis: true,
    videos: true,
    visionFindings: true,
    lifecycle: false,  // hide audit trail from customer view
  },
  insurance: {
    vehicle: true,
    symptoms: true,
    faultCodes: true,
    diagnosis: true,
    videos: true,
    visionFindings: true,
    lifecycle: true,
  },
};
```

Future per-card UI (deferred to F-ticket): expose checkbox-per-card; underlying state shape unchanged. The deferral is purely UI work, not architectural.

### Section override → 192B PDF query param

192B's `/v1/sessions/{id}/report.pdf` will accept `?sections=vehicle,symptoms,faultCodes,...` query param. Mobile sends current override map at export time; backend composer filters before PDF render. Pre-plan note for 192B: query-param shape design (CSV vs repeated keys vs comma-list) — defer to 192B implementation, but the route contract IS established here in 192's route-surface section.

### Stuck-in-analyzing detection (mobile-side, per D refinement)

For each video in the report payload:
- If `analysis_state === 'analyzed'` → render in findings inline.
- If `analysis_state === 'analyzing'` AND `(now - analyzing_started_at) <= 5min` → counted as analyzing (not stuck); count surface "(1 of 3 analyzed)".
- If `analysis_state === 'analyzing'` AND `(now - analyzing_started_at) > 5min` → **stuck**; counted in amber "stuck" subcount; tap-to-retry affordance (calls existing Phase 191B `POST /v1/sessions/{id}/videos/{vid}/retry-analysis` if the route exists; otherwise file F-ticket).
- If `analysis_state === 'analysis_failed'` → counted as failed (separate from stuck); failure-mode subcount with retry affordance.
- If `analysis_state === 'pending'` → counted as pending (waiting for worker); no retry needed.

Display string: `"Vision findings (1 of 3 analyzed, 1 stuck — tap to retry, 1 pending)"` — variable formatting based on which subcounts are non-zero.

### Placeholder copy register (cross-cutting voice/tone review)

Per the cross-cutting refinement: all placeholder copy reviewed together as a coherent set. Voice rules:

1. **Lead with state, then action.** "Diagnosis not yet generated. Add 1 more symptom..." not "Add 1 more symptom to generate diagnosis."
2. **Terminology: always "session"**. Never "diagnostic session" / "report" / "case" interchangeably. The word "report" is reserved for the export artifact (PDF), not the in-session diagnostic context.
3. **Informative + action-oriented + not chatty**. No "Oops!" / "It looks like..." / "Try again later". Direct sentences.
4. **Reference exact UI affordances by name**. "Re-enter your key via **Home → API key card**" (capitalized + arrow + named tab/card). Future-contributor + user can navigate exactly there.
5. **Numbers spelled in numerals when ≤ 100**, words above. "Add 1 more symptom" not "Add one more symptom"; "Reports generated over the last hundred days..." (if ever).

Full register (every placeholder string in 192's UI):

| Where | String |
|---|---|
| I1 fault codes empty | "No fault codes recorded for this session." |
| I2 diagnosis pending (with N=count of recorded symptoms < threshold of 2) | `"Diagnosis not yet generated. ${N} of 2 symptoms recorded; add ${2-N} more to enable AI diagnosis."` |
| I8 symptoms empty | "No symptoms recorded yet. Add symptoms via SessionDetail → Symptoms." |
| I3 videos hidden | (no string — card hidden when zero videos) |
| I3 + D Vision findings empty (videos exist, none analyzed yet) | `"Vision findings (0 of ${N} analyzed)."` |
| D Vision findings with stuck/pending mix | `"Vision findings (${A} of ${N} analyzed, ${S} stuck — tap to retry, ${P} pending)."` (variable formatting; each subcount block omitted when zero) |
| D stuck-tap-to-retry tap result success | "Analysis retry queued." |
| D stuck-tap-to-retry tap result failure | "Couldn't queue retry. Check connection and try again." |
| I5 network failure | "Couldn't load report. Check your connection and tap retry." (button: "Retry") |
| I6 404 | "This session is no longer available. It may have been deleted." (button: "Back to sessions") |
| I7 401 | "Your API key is no longer valid. Re-enter your key via Home → API key card to continue." |
| I9 defensive empty payload | "Report unavailable for this session." (button: "Retry") |
| Loading state (during fetch) | (no string — spinner only; matches Phase 189/190/191/191B convention) |
| Pull-to-refresh trigger | (no string — RN refresh-control default) |

**Voice/tone consistency check**: all 11 strings lead with state ("No fault codes...", "Diagnosis not yet generated...", "This session is no longer available...", etc.); all use "session" not "diagnostic session"; all have action affordances named explicitly where applicable; all numbers are numerals; no chatty filler. Coherent set. ✓

## Key Concepts

- **Composition layer as decoupling primitive**: `report_composer.compose(session_id)` is independent of viewer + PDF consumers. Pytest suite tests `compose()` directly without HTTP layer; route + PDF route both call into the same module. Per A's boundary-tightening note.
- **Override map state shape vs UI affordance**: data model designed for per-card override (γ) from day one, but UI affordance ships as 2-preset switcher (β). Future per-card UI is purely UI work, not architectural migration. Per C1's pushback.
- **Round-trip cost discipline**: 30s focus-debounce per I10 (Phase 188 HVE saga lesson — round-trips on slow shop wifi compound; default to debounce, not refresh-on-every-focus). Pull-to-refresh stays as explicit force-refresh affordance.
- **Tier-bypass-on-read auth pattern**: Phase 188/189/191B/192 all share "read access doesn't gate on tier; create access does." F29 formalizes as ADR-shape doc to prevent accidental tightening.
- **Voice/tone coherence as cross-cutting concern**: all placeholder copy reviewed together as a set, not per-card-in-isolation. Same discipline as 191D opt-out reasons. The viewer is a polished user-facing surface; coherent voice is the polish.
- **Defensive empty-payload + telemetry**: I9's `console.warn` logline carries enough structural detail (session ID, user ID, timestamp, malformed-payload shape) to trace composer regressions. F30 escalates to backend telemetry event for production observability.

## Verification Checklist

- [ ] `report_composer.compose(session_id, db_path)` returns `ReportPayload` for full / empty / incomplete-Vision / mixed-analysis-states fixture sessions; pytest suite passes ~10-12 tests
- [ ] Composer omits the videos field entirely when session has zero videos (per I3)
- [ ] Composer returns symptoms/fault-codes as empty lists (not None) when none recorded
- [ ] Composer returns diagnosis as None when not yet generated; mobile renders I2 placeholder with N-of-2 count
- [ ] Composer returns lifecycle with full `created_at`/`closed_at`/reopen events when applicable
- [ ] `GET /v1/sessions/{id}/report` route happy path: returns ReportPayload JSON with all 6 cards
- [ ] Route 401: invalid API key returns ProblemDetail
- [ ] Route 403: cross-owner read attempt returns ProblemDetail (session-owner-or-shop-tier-member check)
- [ ] Route 404: nonexistent / soft-deleted session returns ProblemDetail
- [ ] **Route tier-bypass-on-read**: free-tier user fetches own session's report → 200 OK (regression guard for the F29 pattern)
- [ ] Route integration tests pass (~6-8 tests via FastAPI TestClient)
- [ ] Mobile `useReport` hook fetches on mount; updates state; renders content
- [ ] Mobile `useReport` 30s focus-debounce: re-entry within 30s does NOT trigger re-fetch; re-entry after 30s DOES trigger re-fetch
- [ ] Mobile `useReport` pull-to-refresh always triggers re-fetch (overrides debounce)
- [ ] Mobile `useReport` polls via `useSessionVideos` for video state updates (verified by smoke that "1 of 3 analyzed" auto-increments to "2 of 3" without manual refresh)
- [ ] `ReportViewerScreen` renders all 6 cards in correct order
- [ ] `ReportViewerScreen` SectionToggle: tapping Customer-facing hides lifecycle; tapping Insurance-facing shows lifecycle; default = Insurance-facing on first render
- [ ] `ReportViewerScreen` correctly renders all 11 placeholder strings (per the placeholder copy register) when triggering each empty/error state
- [ ] `ReportViewerScreen` renders stuck-in-analyzing state correctly: amber subcount, tap-to-retry affordance, retry success queues + UI updates
- [ ] Cross-link from `SessionDetailScreen` → `ReportViewerScreen` works; back-button stack semantics preserved
- [ ] Mobile `useReport` 401 handling: surfaces I7 copy with Home → API key card direction
- [ ] Mobile `useReport` 404 handling: surfaces I6 copy with Back-to-sessions button
- [ ] Mobile `useReport` network failure handling: surfaces I5 copy with Retry button
- [ ] Mobile `useReport` defensive empty-payload handling: surfaces I9 copy + emits structured `console.warn` logline including session ID + user ID + timestamp + malformed-payload shape
- [ ] `useReport.test.ts` passes (~8-10 tests)
- [ ] `ReportViewerScreen.test.ts` passes
- [ ] Mobile Jest 293 + new tests all green
- [ ] `npm run generate-api-types` regenerates types after backend openapi.json refresh
- [ ] No regression: full backend Phase 191D + Phase 191C + Phase 175-184 sweep clean; mobile Jest 293+ all green
- [ ] Backend `pyproject.toml` 0.3.1 → 0.3.2 (patch bump — extends API surface; no breaking changes)
- [ ] Backend `implementation.md` 0.13.10 → 0.13.11
- [ ] Mobile `package.json` 0.0.9 → 0.0.10
- [ ] Mobile `implementation.md` 0.0.11 → 0.0.12
- [ ] Backend + mobile READMEs updated with viewer + (forward-pointing) PDF/share notes
- [ ] Mobile FOLLOWUPS: F28 + F29 + F30 + (provisional F31) filed at finalize

## Risks

- **Composition layer tight-coupling to first consumer**. The viewer ships first; PDF route at 192B is the second consumer. Risk: composer module accumulates viewer-specific concerns (e.g., section-override-map handling) that don't belong in the composer. Mitigation: per A's boundary-tightening note, composer's pytest suite tests `compose(session_id)` directly without HTTP layer; if a test requires HTTP-layer concerns to set up, that's a coupling smell to fix immediately.
- **Round-trip count surprises**. Viewer + `useSessionVideos` polling could trigger redundant fetches if the integration is wrong (e.g., poll triggers full report re-fetch instead of just video card update). Mitigation: smoke gate Step 9 (composition layer regression sweep) + explicit smoke step verifying poll-driven count increment doesn't re-fetch the report.
- **Section-toggle UX confusion**. Two presets ("Customer-facing" + "Insurance-facing") might not communicate clearly to mechanics what each preset hides. Mitigation: preset-button copy includes a one-line description ("hides cost details" / "full audit trail"); first-time-user toast on first preset toggle. Smoke gate verifies the description text renders.
- **Stuck-in-analyzing retry route doesn't exist yet**. Phase 191B added analysis but no explicit retry endpoint — `POST /v1/sessions/{id}/videos/{vid}/retry-analysis` may need to be added in 192. Mitigation: pre-build verify if the route exists; if not, **add the retry route as part of 192's backend scope** (small extension, ~30 LoC + 1-2 tests). If the route is genuinely out-of-scope, file F-ticket and render the stuck-in-analyzing affordance as info-only (no retry button) until the route ships.
- **Open question on `describeError` network-vs-backend distinction**. I5 noted: if Phase 187's `describeError` doesn't distinguish network-unreachable from backend-unreachable, the error copy degrades. **Pre-build action**: verify `describeError` shape during Commit 1 / 2; if the distinction isn't there, file F31 as small cross-cutting error-state polish. Don't expand 192's scope to add it; just track.
- **CSS Grid in PDF template (192B-deferred risk)**. WeasyPrint's CSS Grid support is partial; complex templates fail silently. 192's viewer-side rendering is unaffected (RN doesn't use CSS Grid anyway), but 192B's template MUST stay on conservative CSS (block + flex + table). Pre-plan note for 192B: design template assuming Grid is unavailable.
- **Phase 187 `ApiKeyModal` re-entry from viewer**. I7's auth-401 handling sends user to "Home → API key card" but the viewer's deep-link / back-button stack might not preserve correctly when user navigates away. Mitigation: verify back-button-from-Home returns to ReportViewerScreen (not to root SessionsStack) after API key re-entry. Manual smoke step.

## Commit plan

5 commits on `phase-192-diagnostic-report-viewer` branch. Backend-first to establish contract before mobile work proceeds.

**Commit 1 — Backend composer + route + tests** (backend-only). New `report_composer.py` + `models/report.py` + `routes/reports.py` + composer pytest suite + route integration tests. **Composer pytest suite passes against fixture sessions BEFORE the route is merged** — that's the boundary-decoupling gate (per A's refinement). Includes the `tags=["reports"]` claim on the existing TAG_CATALOG entry. Plus F29 ADR file `docs/architecture/auth-policy.md` documenting the read-access-doesn't-gate-on-tier rule (small ADR, ~30 lines). pyproject 0.3.1 → 0.3.2.

**Commit 2 — Mobile useReport hook + types** (mobile-only). `useReport.ts` + `src/types/report.ts` + `src/api-types.ts` regenerated from refreshed `api-schema/openapi.json` + `useReport.test.ts`. Hook compiled + tested in isolation before viewer screen consumes it.

**Commit 3 — Mobile ReportViewerScreen + SectionToggle + ReportCard** (mobile-only). Top-level screen + section-toggle component + shared card wrapper. Renders all 6 cards with placeholder/empty-state policy per I1-I9 + section-toggle preset + 30s focus-debounce + pull-to-refresh + stuck-in-analyzing surface per D refinement.

**Commit 4 — Mobile cross-link from SessionDetailScreen + nav registration** (mobile-only). `ReportViewerScreen` registered on SessionsStack; "View report" CTA added to SessionDetailScreen. Back-button stack verified.

**Commit 5 — Finalize** (both repos). Mobile Jest + backend pytest sweep green. Move plan docs in_progress → completed. Backend `implementation.md` 0.13.10 → 0.13.11. Mobile `implementation.md` 0.0.11 → 0.0.12. Mobile `package.json` 0.0.9 → 0.0.10. ROADMAP marks ✅ on both repos. Mobile FOLLOWUPS: file F28 + F29 + F30 + provisional F31. Pattern doc untouched (no new F9 instances surfaced; this is a pure-feature phase).

Each commit: backend Phase 192 tests green + Phase 175-184 sample regression clean before next; mobile `npx eslint` green + Jest green at Commit 5.

## Architect gate (smoke shape per Section G)

**192 viewer smoke-gate (single-architect-session, ~30-45 min). Visual/UX-heavy.**

Steps:
1. Open existing diagnostic session in viewer; verify all 6 cards render (vehicle, symptoms, fault codes, diagnosis, videos, lifecycle); default preset = Insurance-facing.
2. Toggle preset between Customer-facing and Insurance-facing; verify lifecycle card hides on Customer-facing; section visibility matches preset; default Insurance-facing on first render.
3. Session with incomplete Vision analysis: verify findings count "(N of M analyzed)"; verify only analyzed videos appear inline; verify count auto-updates on poll-complete (driven by `useSessionVideos` polling integration) WITHOUT triggering full report re-fetch.
4. Session with stuck-in-analyzing video (>5 min in analyzing state): verify amber stuck-count + tap-to-retry; tap retry; verify analysis re-queued + UI updates.
5. Empty/early-stage session (zero symptoms, zero diagnosis, zero videos): verify videos card hidden (per I3); verify symptoms placeholder per I8; verify diagnosis placeholder per I2 with N-of-2 count.
6. Session with no fault codes but other content: verify fault codes card renders with I1 placeholder.
7. **Free-tier user fetches own session's report → 200 OK** (regression guard for F29 tier-bypass-on-read pattern). Smoke covers via test API key with individual-tier user.
8. Cold-relaunch from viewer: verify state hydration; no "loading forever" hangs; verify default preset = Insurance-facing on cold-relaunch (state didn't persist from prior session — per C2 (ε)).
9. **Composition layer regression sweep BEFORE UI testing** (Section G addition): `pytest tests/test_phase192_report_composer.py` against 3-4 distinct seeded sessions (full / empty / incomplete Vision / mixed analysis states); all pass. Catches composer regressions before they surface as silent UI rendering issues.
10. Pull-to-refresh: verify re-fetch + UI update.
11. 30s focus-debounce: nav out and back to viewer within 30s; verify NO re-fetch (network panel quiet); nav out and back AFTER 30s; verify re-fetch fires.
12. Tap a video card: navigates to existing VideoPlayback; back button returns to viewer; viewer state preserved.
13. Cross-link from SessionDetailScreen "View report" CTA → ReportViewerScreen; back button returns to SessionDetailScreen; back-button stack correct.
14. Bottom-tab nav out and back; viewer state preserved.
15. Network failure simulation (turn off wifi mid-fetch): verify I5 error state with retry; tap retry on connection restore; verify happy path resumes.
16. Backend 404 simulation (delete session via CLI mid-session): verify I6 copy on next refresh + Back-to-sessions affordance.
17. Auth 401 simulation (revoke API key mid-session): verify I7 copy directing to Home → API key card.

**No live API calls. No cost validation.** Cost: $0.

## Versioning targets at v1.1 finalize

- Backend `pyproject.toml`: `0.3.1 → 0.3.2` (patch — extends API surface; no breaking changes).
- Backend project `implementation.md`: `0.13.10 → 0.13.11`.
- Schema: unchanged at v39.
- Mobile `package.json`: `0.0.9 → 0.0.10`.
- Mobile project `implementation.md`: `0.0.11 → 0.0.12`.

## Not in scope (firm)

- **PDF generation / Share Sheet / AirDrop**. All 192B scope. 192 ships viewer + composer + route only.
- **Per-card section toggle UI**. Data shape (override map) ships in 192 per C1 (γ); UI affordance is 2-preset only. Future "advanced toggle" F-ticket adds checkbox-per-card UI without state-shape migration.
- **Per-mechanic preset preference persistence**. F28 deferred per C2 (ε). Session-only state in 192; revisit at 192B if smoke surfaces friction.
- **Auto-detect preset from session metadata**. Rejected per C3 — mis-categorization leaks billing info.
- **Cached fallback on network failure**. Rejected per I5 — error state with retry only.
- **Automatic re-auth flow on 401**. Rejected per I7 — direct user to Home → API key card; no modal-during-viewer-entry surprise.
- **Backend telemetry event on defensive empty-payload**. F30 deferred. 192 emits frontend `console.warn` logline only.
- **Lifecycle history (close/reopen as timeline rather than pure-state)**. F3 (Phase 189 follow-up) — out of 192 scope. Lifecycle card renders current pure-state per Phase 189's existing data model.
- **WeasyPrint CSS template work**. All 192B scope.

## FOLLOWUPS update at finalize

- **F28 (NEW)** — Per-mechanic preset preference persistence. Trigger: 192B smoke gate or first 2 weeks of usage surface "every share + close + re-open re-prompts preset" as friction.
- **F29 (NEW)** — Auth policy ADR documenting "read access doesn't gate on tier; create access does" emergent rule across Phase 188/189/191B/192 read endpoints. ADR-shape F-ticket. **Lands in Commit 1** (backend) as `docs/architecture/auth-policy.md` — promoted from F-ticket to in-phase deliverable because (a) it's small, (b) Commit 1 is touching the auth-on-route surface anyway, (c) it prevents accidental tightening between 192 ship and the next phase.
- **F30 (NEW)** — Backend telemetry event when defensive empty-payload case fires. Forward-looking observability.
- **F31 (provisional, confirmed during build)** — `describeError` network-vs-backend-unreachable distinction. Pre-build verify if the existing implementation covers; file F31 if not.

## Smoke test (architect-side, post-build, pre-v1.1)

(Same as the Architect gate above — Phase 192's gate IS the smoke. ~17 steps, ~30-45 min, single-architect-session.)
