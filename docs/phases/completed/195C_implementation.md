# Phase 195C — F37 Track 2: Pydantic-Literal-vs-DB-CHECK Lint Rule + Retroactive Sweep

**Version:** 1.1 (built — as-built; plan history in the "v1.0.1 amendment" / "v1.0.2 amendment" / "Deviations from Plan" sections) | **Tier:** Standard | **Date:** 2026-05-17

> **Locked-sequence slot.** Phase 195C is the meta-tooling slot reserved between Phase 195B and Phase 196 in Phase 195B's plan v1.0 ("Phase 195C slot" section). It implements **F37 Track 2** — the systematic-correctness response to the contract-surface-drift pattern that surfaced as F37 instance #3 during Phase 195. Same precedent as 191B → 191C → 191D: a feature ships, then meta-tooling responds to the discovered drift after the feature phase closes cleanly.

## Goal

Phase 195C ships a static lint rule that enforces the contract: *a Pydantic response-model field that maps to a DB column carrying a `CHECK (... IN (...))` constraint must be typed `Literal[...]` (or a `Literal` alias) whose value-set matches the constraint exactly* — so the OpenAPI surface emits a strict enum and mobile codegen produces typed unions instead of freeform `string`. It then runs that rule retroactively across the Phase 191B→195B backend route code, fixing any silent `str`-instead-of-`Literal` regressions in the same build commit, and records "contract-surface-drift" as a new subspecies in the F9 pattern guide. This prevents the per-phase-discipline failure mode F37 instance #3 documented: Phase 194's `photos.py` had `PhotoRole = Literal[...]` right, Phase 195's `transcripts.py` regressed to `str` — discipline did not carry forward, so it is being automated.

**CLI:** `python scripts/check_f9_patterns.py --check-pydantic-literal-vs-check-constraint` (new sub-check of the existing F9 lint script; also runs under `--all`).

**Outputs:**
- New sub-check function `check_pydantic_literal_vs_check_constraint(...)` + helpers in `scripts/check_f9_patterns.py`, registered as the `--check-pydantic-literal-vs-check-constraint` CLI flag and folded into `--all` / `run_all_checks`.
- New test file `tests/test_phase195c_pydantic_literal_lint.py` (RuleTester-style, mirrors `tests/test_phase191d_ssot_constants_lint.py`).
- Retroactive-sweep fixes (if any) to route modules under `src/motodiag/api/routes/` — folded into the same build commit.
- New subspecies section "contract-surface-drift" appended to `docs/patterns/f9-mock-vs-runtime-drift.md`.
- `.pre-commit-config.yaml` updated to invoke the new check (mirrors how `--check-tag-catalog-coverage` is wired).

## Logic

### Step 1 — Parse DB CHECK constraints into a value-set map

The rule reads `src/motodiag/core/migrations.py` (and, defensively, `src/motodiag/core/database.py` `SCHEMA_SQL` baseline if present — it is not, see the audit). For each `Migration.upgrade_sql` string it scans for column definitions carrying an enumerated CHECK:

```
<colname> TEXT ... CHECK (<colname> IN ('a', 'b', 'c'))
<colname> TEXT ... CHECK(<colname> IN ('a','b'))
```

Both inline (`kind TEXT NOT NULL CHECK(kind IN (...))`) and multi-line (`extraction_state TEXT NOT NULL DEFAULT 'pending'\n CHECK (extraction_state IN (...))`) shapes occur in the codebase — the parser must handle both. Because `upgrade_sql` is a Python string literal (not a live DB), the parse is a regex over the SQL text: a `CHECK` token, an `IN` token, a parenthesised comma-separated list of single-quoted string literals.

**The parser tracks the enclosing table.** It scans `CREATE TABLE <table> ( … )` blocks (and `ALTER TABLE <table> ADD COLUMN …`) so every CHECK value-set is keyed by **`(table, column)`** — never by column name alone (e.g. `(voice_transcripts, extraction_state) → {'pending','extracting','extracted','extraction_failed'}`). **This is load-bearing, not a nicety** (v1.0.1 amendment — see that section + Risk 4): three distinct tables — `fleet_bikes`, `shop_members`, `work_order_photos` — each carry a `role` column with a *different* CHECK value-set (`{rental,demo,race,customer}` / `{owner,tech,service_writer,apprentice}` / `{before,after,general,undecided}`). A column-name-only key would conflate all three into one bucket and either (a) false-flag a correct field for not matching some *other* table's `role` set, or (b) silently pass a genuinely drifted field that happens to match a different table's `role` set. That is the F9 failure family — a name-level match that is not a semantic match — turned back on the rule itself; the same over-firing lesson Phase 191D's inaugural run documented.

Where the same `(table, column)` appears in multiple migrations, the latest definition wins (handles rename-recreate rollback-shape duplication). Tables that recreate a column without the CHECK (the migration-040 `videos_rollback` recreate has no CHECK — note it is a *rollback_sql*, which the parser ignores; only `upgrade_sql` is scanned) do not pollute the map.

`BETWEEN`, `IS NOT NULL`, and boolean `IN (0,1)` CHECKs are **not** enumerated string value-sets and are skipped — the rule targets only string-enum CHECKs, which is exactly the Pydantic-`Literal` surface.

### Step 2 — Parse Pydantic response models via AST

The rule AST-walks every module under `src/motodiag/api/routes/` plus the shared model module `src/motodiag/core/models.py` (where `VideoResponse` lives — see audit). For each `ClassDef` whose base list includes `BaseModel` (directly or transitively through another in-file `BaseModel` subclass — e.g. `VideoResponse(VideoBase)` where `VideoBase(BaseModel)`), it collects each annotated field (`AnnAssign`). For each field it records:
- the field name,
- the annotation node — classified as one of: `Literal[...]` (inline), a `Literal`-alias `Name` (module-level `X = Literal[...]` assignment resolved within the file), a `str`/`Optional[str]` annotation, a `str, Enum` subclass reference, or "other".
- For inline `Literal[...]` and resolved aliases, the value-set is extracted from the `Subscript` slice constants.

Module-level `Literal` aliases (`ExtractionState = Literal["pending", ...]`, `PhotoRole = Literal["before", ...]`) are resolved by a first pass that records every `Assign` whose value is a `Literal[...]` subscript.

**Step 2 also resolves each response model to its DB table** (v1.0.1 amendment — required for the table-scoped join in Step 3). Resolution is two-tier:
1. **Explicit marker (authoritative).** A `# f9-table: <table>` comment on the model's `class` line (or the line directly above it) names the table. 195C's build adds this marker to the response models that carry a CHECK-constrained field — a small, additive one-line annotation per model, no behaviour change.
2. **Class-name convention (fallback).** Absent a marker, the table is derived from the model class name: strip a trailing `Response`/`Base`/`Read`/`Out` suffix, snake_case, naive-pluralize (`WorkOrderPhotoResponse → work_order_photos`). The convention is best-effort and only consulted when no marker is present.

If neither resolves a table, the model is recorded as **table-unresolved** — which only matters for colliding column names (Step 3).

### Step 3 — Cross-match field → CHECK constraint, table-scoped (v1.0.1)

CHECK value-sets are keyed by `(table, column)` (Step 1). The rule first builds a **column-name → set-of-tables index** to know which column names collide across tables. Then, for each Pydantic field whose name matches a CHECK column name:

- **Non-colliding column** (the name maps to exactly one table — e.g. `extraction_state` exists only on `voice_transcripts`): validate the field directly against that single `(table, column)` CHECK set. No model→table resolution needed — the match is unambiguous.
- **Colliding column** (the name exists on ≥2 tables — e.g. `role` on `fleet_bikes` / `shop_members` / `work_order_photos`): the rule **must** resolve the field's owning model to a table (Step 2's marker/convention) and validate **only** against *that table's* CHECK set. It never validates against, or even considers, the other tables' sets.
- **Colliding column + table-unresolved model**: the rule emits a `pydantic-literal-vs-check-ambiguous` finding — it **does not guess**, does not pick an arbitrary table, and does not silently pass. Surfacing the ambiguity for the architect to resolve (add the `# f9-table:` marker) is the F9-discipline posture: a name-level match that cannot be confirmed semantic is reported, not assumed.

For every confidently table-scoped pair the rule asserts:
1. The Pydantic field is typed `Literal` (inline or alias) — **not** plain `str`/`Optional[str]`. A `str`-typed field with a name-matching CHECK column is the **primary finding** (the F37-instance-#3 regression shape).
2. The `Literal` value-set **equals that table's** CHECK value-set. A mismatch (Literal missing a value the CHECK allows, or advertising a value the CHECK forbids) is the **contract-surface-drift finding** — the exact divergence the new F9 subspecies names.

The table-scoped join is what makes the rule's own matching semantic rather than nominal — the disambiguation is an **acceptance criterion**, proven by a fixture, not merely a watched risk (see Verification Checklist + Risk 4).

`str, Enum` annotations: a `str, Enum` class DOES produce a typed OpenAPI enum (FastAPI emits `enum: [...]` for `str`-`Enum` fields), so it is *contract-correct in spirit*. The rule treats a `str, Enum` field as a **WARN, not an error** when a name-matching CHECK exists, with a message recommending migration to a `Literal` alias for house-style consistency — and the value-set equality check still runs against the Enum members. This avoids a false "regression" verdict on `VideoResponse` (see audit) while still flagging it for the architect.

### Step 4 — Emit findings + honor opt-outs

Findings use the existing `F9Finding` dataclass and the `file:line: [rule] message` format. The rule name is `pydantic-literal-vs-check`. Two opt-out forms mirror the established F9 machinery exactly:
- **File-level**: `# f9-allow-pydantic-literal-vs-check: <reason>` near the top of a route module, reason ≥ `MIN_OPTOUT_REASON_CHARS` (20) — reuses `_file_level_optout(source, kind="pydantic-literal-vs-check")`.
- **Per-line**: `# f9-noqa: pydantic-literal-vs-check <reason>` on the offending field line — a new small helper modelled on `_opt_out_present` / `_ssot_per_line_optout`.
Malformed opt-outs (missing/short reason) emit a `*-malformed-optout` finding and do not exempt the line — identical posture to the existing checks.

### Step 5 — Retroactive-validation pass

Once the rule exists it is run against the live backend (`--check-pydantic-literal-vs-check-constraint`). Per the F33 audit subsection below, the expected ✗ retroactive hit-list is **empty** — `transcripts.py` was already corrected in Phase 195 Backend Commit 0.5, and `photos.py` / `shop_mgmt.py` were already correct. Any finding the rule surfaces that the audit did not predict is treated as a genuine silent regression: the fix (upgrade the `str` field to a `Literal` alias matching the CHECK) is made and **folded into the same Phase 195C build commit**, with the fix logged in `195C_phase_log.md` under a dated bug-fix entry per the peak-efficiency bug-fix-logging discipline.

### Step 6 — F9 pattern-guide subspecies addition

A new subspecies section "contract-surface-drift" is appended to `docs/patterns/f9-mock-vs-runtime-drift.md`. It documents: the mechanism (the value-set the DB SCHEMA enforces via CHECK vs the value-set the API CONTRACT advertises via Pydantic/OpenAPI drift apart when one is changed without the other); the telling signal (a backend CHECK-constraint bump that does not surface as a mobile type error); the lint coverage (`--check-pydantic-literal-vs-check-constraint`); and the case study (F37 instance #3 — `transcripts.py` `str` regression vs `photos.py` `Literal` correctness). The doc's instance counter and the "subspecies" enumeration are updated consistently with how Phase 191D extended the catalog.

### F33 existing-code-overlap audit findings

**Method:** read all CHECK constraints in `src/motodiag/core/migrations.py` (39 migrations; `database.py` has no `SCHEMA_SQL` baseline with CHECKs — confirmed via grep, zero matches); read every Pydantic model in `src/motodiag/api/routes/{videos,reports,shop_mgmt,photos,transcripts}.py` + `src/motodiag/core/models.py`; cross-matched field-name → CHECK-column-name. F33 noun-grep for `check_pydantic` / `check_f37` / `pydantic-literal` / `contract-surface` across `scripts/` and `src/` returned **zero code matches** (the only hits are documentation: `docs/ROADMAP.md` and `195_phase_log.md`, both forward-referencing this planned work). No existing check covers this surface — the rule itself is greenfield; the F9 script is extension territory (new sub-check, no reshape of existing checks).

**Audit table** (`✗` rows = retroactive-validation hit-list):

| Phase | DB table.column | DB CHECK value-set | Pydantic model.field | Current type | Literal-correct? |
|---|---|---|---|---|---|
| 191B | `videos.upload_state` | **NO CHECK** (migration 039 — `DEFAULT 'uploaded'` only) | `VideoResponse.upload_state` (`core/models.py`) | `VideoUploadState(str, Enum)` | n/a — no CHECK to mirror; `str,Enum` already emits typed OpenAPI enum → WARN-only |
| 191B | `videos.analysis_state` | **NO CHECK** (migration 039 — `DEFAULT 'pending'` only) | `VideoResponse.analysis_state` (`core/models.py`) | `VideoAnalysisState(str, Enum)` | n/a — no CHECK to mirror; `str,Enum` already typed → WARN-only |
| 192 | `videos.analyzing_started_at` | n/a (TEXT timestamp, no enum) | — (not a response enum) | — | n/a |
| 192 | reports — `preset` | **NO DB column** (PDF render-time parameter) | `PdfRenderRequest.preset` (request model) | `Literal["full","customer","insurance"]` | ✓ — already `Literal`; no CHECK exists; request model, not response |
| 193 | `shop_members.role` | `('owner','tech','service_writer','apprentice')` (migration ~2509) | `MemberAddRequest.role` (request model) | `Literal["owner","tech","service_writer","apprentice"]` | ✓ — matches CHECK exactly |
| 193 | `issues.severity` | `('low','medium','high','critical')` (migration ~1964) | `IssueCreateRequest.severity` (request model) | `Literal["low","medium","high","critical"]` | ✓ — matches CHECK exactly |
| 193 | notifications — `channel` | enumerated CHECK (migration ~2454) | `NotificationTriggerRequest.channel` (request) | `Literal["email","sms","in_app"]` | ✓ pending value-set confirm at build (rule verifies equality) |
| 193 | work-order / issue `status` | `('open','closed','cancelled')` + extended sets | shop_mgmt list/get handlers return **raw `dict` rows** — no Pydantic response model | plain `dict` | n/a for THIS rule — no Pydantic field to type. Flagged as scope-pressure Q1 below |
| 194 | `work_order_photos.role` | `('before','after','general','undecided')` (migration 041) | `WorkOrderPhotoResponse.role` | `PhotoRole = Literal["before","after","general","undecided"]` | ✓ — matches CHECK exactly (the F37 "telling signal" positive case) |
| 194 | `work_order_photos.analysis_state` | **NO CHECK** (migration 041 — nullable, no constraint) | `WorkOrderPhotoResponse.analysis_state` | `Optional[str]` | n/a — no CHECK to mirror; not a finding |
| 195 | `voice_transcripts.extraction_state` | `('pending','extracting','extracted','extraction_failed')` (migration 042) | `VoiceTranscriptResponse.extraction_state` | `ExtractionState` (`Literal` alias) | ✓ — fixed in Phase 195 Backend Commit 0.5 (F37 Track 1) |
| 195 | `extracted_symptoms.extraction_method` | `('keyword','claude','manual_edit')` (migration 042) | `ExtractedSymptomResponse.extraction_method` | `ExtractionMethod` (`Literal` alias) | ✓ — fixed in Phase 195 Backend Commit 0.5 |
| 195 | `voice_transcripts.audio_format` | **NO CHECK** (migration 042 — `DEFAULT 'm4a'` only) | `VoiceTranscriptResponse.audio_format` | `AudioFormat = Literal["wav","m4a","ogg"]` | ✓ as Pydantic — but no DB CHECK backs it. Flagged as scope-pressure Q2 below |
| 195 | `voice_transcripts.preview_engine` | **NO CHECK** (migration 042 — nullable) | `VoiceTranscriptResponse.preview_engine` | `PreviewEngine` (`Literal` alias) | ✓ as Pydantic — but no DB CHECK backs it. Same as Q2 |
| 195B | `cost_events.kind` | `('whisper','claude_extraction')` (migration 043) | **none** — `motodiag costs report` CLI renders a `CostRollup` dataclass via `click.echo`; no API route, no Pydantic response model | n/a | n/a — no API response surface exists for `cost_events` |

**Retroactive hit-list (✗ rows):** **EMPTY.** Every Pydantic response field that maps to a DB string-enum CHECK is already `Literal`-correct. This is the expected and healthy outcome — Phase 195 Commit 0.5 already fixed the one known regression (`transcripts.py`), and the audit confirms 191B/192/193/194 never drifted. The rule's value is therefore **forward-looking** (catching the *next* regression automatically), exactly as F37 Track 2 framed it. If the rule, once built, surfaces a finding the audit did not predict, that finding is a genuine silent regression and gets fixed + folded per Step 5.

### Existing-code audit (CLAUDE.md Step 0)

Primary nouns audited: `check_f9_patterns`, `check_pydantic`, `check_f37`, `pydantic-literal-vs-check`, `contract-surface-drift`, `Literal`, `CHECK`.
- **`scripts/check_f9_patterns.py`** — exists; 1295 lines; houses 4 sub-checks (`--check-model-ids` deprecated, `--check-deploy-path-init-db`, `--check-ssot-constants` [F20], `--check-tag-catalog-coverage` [F21]). The new check is an **extension** of this file (new function + new CLI flag + `--all`/`run_all_checks` fold-in), NOT a reshape — no existing sub-check is modified. The shared machinery (`F9Finding`, `_file_level_optout`, `_call_dotted_name`, opt-out reason floor, malformed-opt-out posture) is reused verbatim.
- **No `scripts/check_f37_patterns.py`** exists — confirmed via Glob.
- **`tests/test_phase191d_ssot_constants_lint.py`** — exists; the canonical RuleTester-style structure (one class per concern, `importlib.util` module loader because `scripts/` is not a package, synthetic fixtures in `tmp_path`, file-level `# f9-allow-...` opt-out on the meta-test file itself). Phase 195C's test file mirrors this exactly.
- **`docs/patterns/f9-mock-vs-runtime-drift.md`** — exists; catalogs 10 instances / 5 subspecies + lint-coverage notes. Phase 195C **appends** a new subspecies + case study; it does not rewrite existing sections (only the instance counter + subspecies enumeration are updated for consistency, the same way Phase 191D extended it).
- **Conclusion:** greenfield rule logic, extension posture on every file it touches. No v1.0.1 reshape anticipated. The audit also surfaced two non-blocking observations (no DB CHECK behind `audio_format`/`preview_engine`; no Pydantic response model behind `cost_events.kind` and `work_orders.status`) — these are routed to the architect as Open Questions, not self-authorized scope.

## Key Concepts

- **AST walk for Pydantic models** — `ast.parse` each route module; `ClassDef` with a `BaseModel` base (direct or via an in-file `BaseModel` subclass); `AnnAssign` field annotations classified as `Literal` / `Literal`-alias / `str` / `str,Enum` / other. Same AST-walk discipline as `check_tag_catalog_coverage` (which already AST-parses `APIRouter(...)` calls) and `check_model_ids`.
- **CHECK-constraint parsing from migration SQL** — regex over each `Migration.upgrade_sql` string literal: `CHECK` → `IN` → parenthesised single-quoted comma list. Handles inline + multi-line shapes; `rollback_sql` deliberately ignored; `BETWEEN` / `IN (0,1)` / `IS NOT NULL` CHECKs skipped (non-string-enum).
- **Table-scoped join** (v1.0.1) — CHECK sets are keyed by `(table, column)`; a Pydantic field is validated against *its owning model's table's* CHECK set, not against every same-named column's set. For non-colliding column names the field-name match is unambiguous; for colliding names (`role` on three tables, `status` on several) the rule resolves the model→table (explicit `# f9-table:` marker, else class-name convention) and emits a `pydantic-literal-vs-check-ambiguous` finding rather than guessing if it cannot. A plain column-name join would re-commit the F9 family error inside the F9 tool itself.
- **`str, Enum` is WARN, not error** — a `str`-`Enum` field DOES emit a typed OpenAPI enum; the rule warns (recommend `Literal` alias for house-style) rather than failing, so `VideoResponse` does not produce a false regression verdict.
- **F9-family finding/opt-out machinery** — reuses `F9Finding`, `file:line: [rule] message` format, `_file_level_optout`, `MIN_OPTOUT_REASON_CHARS` (20), `FILE_OPTOUT_SCAN_LINES` (100), malformed-opt-out-still-reports posture. New opt-out kinds: `# f9-allow-pydantic-literal-vs-check` / `# f9-noqa: pydantic-literal-vs-check`.
- **Precedent of F20/F21** — `--check-ssot-constants` (F20) and `--check-tag-catalog-coverage` (F21) were both added to `check_f9_patterns.py` as new sub-checks rather than new scripts. Phase 195C mirrors that decision (see Recommendation below).
- **191B→191C→191D meta-tooling precedent** — feature ships, then a dedicated meta-tooling phase responds to the discovered drift. Phase 195C is the F37 analogue of Phase 191D.

### Recommendation — sub-check of `check_f9_patterns.py`, NOT a separate `check_f37_patterns.py`

**Add the rule as a new `--check-pydantic-literal-vs-check-constraint` sub-check inside `scripts/check_f9_patterns.py`.** Reasoning:

1. **The F9 script is already the home for this exact class of rule.** F20 (`--check-ssot-constants`) and F21 (`--check-tag-catalog-coverage`) were both *new F-tickets* given *new sub-checks in the same file* — not new scripts. F37 is structurally identical (a value-set-drift static check) and contract-surface-drift is being filed as a **new F9 subspecies** (Step 6), so the rule belongs in the F9 script by definition: the script's docstring says it is the home for F9-subspecies lint coverage.
2. **Maximum machinery reuse.** `F9Finding`, `_file_level_optout`, `_call_dotted_name`, the opt-out reason floor, malformed-opt-out posture, the `file:line: [rule]` format, and the `--all` / `run_all_checks` orchestration all already exist. A separate script would either duplicate them or import from `check_f9_patterns.py` anyway (which `scripts/` not being a package makes awkward — see the `importlib.util` loader the tests need).
3. **One pre-commit entry, one `--all`.** CI and `.pre-commit-config.yaml` already invoke `check_f9_patterns.py`; folding the new check into `--all` means zero new CI wiring decisions.
4. **A separate `check_f37_patterns.py` would imply F37 is a *different family*** — it is not. F37 *is* an F9 subspecies (contract-surface-drift). Splitting it into its own script would fragment the catalog the pattern doc works hard to keep unified.

The only argument *for* a separate script — that F37 retroactively scans `src/` rather than `tests/` like the model-ID rule — is weak: `--check-tag-catalog-coverage` already scans `src/motodiag/api/routes/` and `src/motodiag/api/openapi.py`, so an `src/`-scanning sub-check is already established house style in this very file.

## Verification Checklist

- [x] `check_pydantic_literal_vs_check_constraint(...)` added to `scripts/check_f9_patterns.py`; importable as a module function alongside the existing checks.
- [x] `--check-pydantic-literal-vs-check-constraint` CLI flag registered; `parser.error` lists it; `--all` + `run_all_checks` invoke it.
- [x] CHECK-constraint parser extracts string-enum value-sets from `Migration(upgrade_sql=...)` for inline + multi-line CHECK shapes; **keys every set by `(table, column)`** (tracks the enclosing `CREATE TABLE` / `ALTER TABLE`); skips numeric/boolean `IN (0,1)`; ignores `rollback_sql`.
- [x] Pydantic-model AST walk finds `BaseModel` subclasses (incl. transitive) under `src/motodiag/api/routes/` + `src/motodiag/core/models.py`; resolves module-level `Literal` aliases; resolves each model→table via `# f9-table:` marker (authoritative) or class-name convention (fallback).
- [x] **v1.0.2 positive-resolution-required join:** a field is flagged ONLY when its model resolves to a table that actually carries a CHECK on that column. No resolution / resolved-table-has-no-CHECK-on-column → no finding. `str`-typed resolved field → `pydantic-literal-vs-check` error; `Literal` value-set ≠ that table's CHECK → same rule (contract-surface-drift). The `pydantic-literal-vs-check-ambiguous` finding type was **removed** in v1.0.2.
- [x] **Three-`role`-column disambiguation closure gate:** synthetic fixture, 3 tables each with a same-named `role` column / different CHECK set (modelled on the real `fleet_bikes` / `shop_members` / `work_order_photos`); asserts each model validates against its own table + zero cross-report (correct-on-A + drifted-on-B → exactly one finding, on B). Green.
- [x] **v1.0.2 negative-fixture closure gate:** the `HealthStatus`-shaped test — a field name-coinciding with a CHECK column on a model that resolves to no CHECK-bearing table → **zero findings**; plus a counter-check confirming a `# f9-table:` marker re-enables flagging. Green.
- [x] `str, Enum` fields with a name-matching CHECK produce a WARN, not an error.
- [x] File-level `# f9-allow-pydantic-literal-vs-check: <reason>` + per-line `# f9-noqa: pydantic-literal-vs-check <reason>` opt-outs honored; malformed opt-outs emit `*-malformed-optout` and still report the underlying finding.
- [x] Retroactive sweep run against live `src/`: surfaced **24 raw findings** → v1.0.2 positive-resolution dissolved every false positive → **2 genuine `str`-instead-of-`Literal` regressions** (`IssueCreateRequest.category`, `NotificationTriggerRequest.event`) fixed in-phase + folded into the build → **clean re-sweep (0 findings)**.
- [x] `tests/test_phase195c_pydantic_literal_lint.py` exists, RuleTester-style, mirrors `test_phase191d_ssot_constants_lint.py` — **25 tests** (positive / value-set-mismatch / `str,Enum`-WARN / clean / opt-outs valid+malformed / three-`role`-column gate / negative-fixture gate / direct CHECK-parser coverage). 25/25 green.
- [x] "contract-surface-drift" subspecies (vi) + Instance #11 case study appended to `docs/patterns/f9-mock-vs-runtime-drift.md`; instance counter 10→11, subspecies 5→6, decision tree updated; sealed 191C-era sections preserved verbatim.
- [x] `.pre-commit-config.yaml` invokes the new check (dedicated `f9-pydantic-literal-vs-check-constraint` hook + `--all` fold-in).
- [x] Full backend regression green: **4612 passed, 0 failed** (1:22:09) — zero regressions from the rule, the 8 `# f9-table:` markers, or the 2 `str`→`Literal` route-model fixes.

## Risks

1. **CHECK-parse regex brittleness.** SQL CHECK syntax varies (inline vs multi-line, `CHECK(` vs `CHECK (`, quoting). Mitigation: the parser is tested against the *actual* migration-039→043 SQL as fixtures; the audit already enumerated every CHECK shape in the file, so the regex is designed against real data, not hypotheticals.
2. **AST false negatives on dynamically-built models.** A Pydantic model assembled via `create_model(...)` or with computed annotations would be invisible to a static AST walk. Mitigation: the codebase audit found zero such models in the route layer — all response models are plain `class X(BaseModel)` with literal annotations. If one appears later it is simply not covered (fail-open), which is acceptable for a lint rule.
3. **`str, Enum` vs `Literal` WARN noise.** `VideoResponse` will produce a standing WARN every run until/unless `VideoUploadState`/`VideoAnalysisState` are migrated to `Literal` aliases. Mitigation: WARN severity (not error) keeps CI green; the architect decides whether to act on it (see Open Question Q3). The rule must clearly separate WARN lines from ERROR lines in output.
4. **Name-collision false positives — PROMOTED to an acceptance criterion (v1.0.1).** Three real tables (`fleet_bikes`, `shop_members`, `work_order_photos`) carry a same-named `role` column with three *different* CHECK value-sets; `status` collides similarly. A column-name-keyed rule would cross-wire them — false-flag a correct field against another table's set, or pass a drifted field that accidentally matches one. This is no longer treated as a "watch for false positives" risk: the v1.0.1 amendment makes table-scoped `(table, column)` matching a **hard requirement** and the disambiguation a **fixture-backed acceptance test** (Verification Checklist — the three-`role`-column fixture must prove per-table validation + zero cross-report before the phase closes). Residual mitigation for genuinely unresolvable cases: the `pydantic-literal-vs-check-ambiguous` finding (surface, never guess).
5. **Retroactive sweep finds nothing (the expected case) → "is the rule even working?"** Mitigation: the test file's positive cases prove the rule fires on a known-bad synthetic fixture; a clean retroactive run is then trustworthy, not suspicious.
6. **Scope creep from the audit's two non-blocking observations** (no DB CHECK behind `audio_format`/`preview_engine`; no Pydantic response model behind `cost_events.kind`). These are flagged as Open Questions, NOT absorbed into 195C — see below.

### Open Questions for the architect (scope-pressure flags — NOT self-authorized)

The F33 audit surfaced three items that create pressure to expand 195C's scope. Per the CLAUDE.md scope-guardrail, they are flagged here for an architect decision rather than folded in:

- **Q1 — `shop_mgmt.py` list/get handlers return raw `dict` rows, not Pydantic response models.** Work-order / issue `status` and several other CHECK-constrained columns therefore have *no Pydantic response field at all* for the rule to type. This is a real contract-surface gap (those endpoints emit untyped JSON), but **introducing Pydantic response models for the shop-management routes is a feature change far outside 195C's meta-tooling scope.** Recommendation: file an F-ticket; do NOT touch in 195C. The rule simply has nothing to check there.
- **Q2 — `voice_transcripts.audio_format` and `preview_engine` have a Pydantic `Literal` but NO DB CHECK constraint.** This is the *inverse* drift direction: the contract advertises a strict enum the schema does not enforce. The rule as specified (CHECK → Pydantic) does not flag this. **Should 195C also flag Pydantic-`Literal`-without-backing-CHECK as a finding (a second, inverse direction)?** This is a genuine F37-family question. Recommendation: keep 195C to the *single* direction the F37 ticket specifies (CHECK → Pydantic) and F-ticket the inverse; adding a CHECK constraint to migration 042's columns would also be a schema change (new migration) outside meta-tooling scope.
- **Q3 — `VideoResponse` uses `str, Enum` and the `videos` table has NO CHECK at all on `upload_state`/`analysis_state`.** Two sub-questions: (a) should the rule WARN on `str,Enum` (current plan: yes, WARN-only)? (b) the `videos` table arguably *should* have CHECK constraints — but adding them is a migration, outside scope. Recommendation: WARN-only as planned; F-ticket the missing-`videos`-CHECK observation. Do not migrate the schema in 195C.

In all three cases the guardrail holds: 195C ships the rule + retroactive sweep + subspecies doc, and nothing else. The architect decides whether the F-tickets are warranted.

## v1.0.1 amendment — table-scoped matching (pre-code, architect-directed)

**Trigger.** Architect PR-review of plan v1.0 (2026-05-17). The independent spot-check of the empty-hit-list audit claim confirmed it — but surfaced that **three real tables (`fleet_bikes`, `shop_members`, `work_order_photos`) carry a same-named `role` column with three different CHECK value-sets**. Plan v1.0's Step 1/Step 3 keyed CHECK sets by column name alone and joined on name equality. Against that collision, a column-name-only rule would cross-wire: false-flag a correct field against another table's `role` set, or silently pass a drifted field that happens to match a different table's set. That is the F9 failure family — a name-level match that is not a semantic match — reproduced *inside the F9 tool itself*; it is the same over-firing failure Phase 191D's inaugural run documented.

**What changed v1.0 → v1.0.1** (plan-only; still no code):
1. **Step 1** — CHECK value-sets are now keyed by `(table, column)`, not column name. The parser tracks the enclosing `CREATE TABLE` / `ALTER TABLE`.
2. **Step 2** — added model→table resolution (explicit `# f9-table:` marker, authoritative; class-name convention, fallback). 195C's build adds the one-line marker to the response models carrying a CHECK-constrained field.
3. **Step 3** — rewritten from a name-equality join to a table-scoped join: non-colliding column names match unambiguously; colliding names validate only against the resolved owning table's set; an unresolved colliding case emits `pydantic-literal-vs-check-ambiguous` and never guesses.
4. **Risk 4** — promoted from a watched risk to a **hard requirement + fixture-backed acceptance test**.
5. **Verification Checklist** — added the three-`role`-column disambiguation acceptance test as a phase-closure gate, plus the ambiguity-finding case.

**What did NOT change.** The empty retroactive hit-list still holds (`role` fields on the real response models will each validate against their own table — verified: `WorkOrderPhotoResponse.role` ↔ `work_order_photos.role`, the only `role` *response* field in the audit). Sub-check-in-`check_f9_patterns.py` (not a separate script) stands. Open Questions Q1 (shop_mgmt raw dicts → F-ticket), Q2 (inverse Literal-without-CHECK drift → F-ticket), Q3 (`VideoResponse` `str,Enum` → WARN-only) stand as proposed and are accepted by the architect.

This amendment was made pre-code, which is exactly the cadence the CLAUDE.md Step-0 discipline is designed to produce — a documented-assumption mismatch caught at plan-review time, not at implementation time.

## v1.0.2 amendment — positive-resolution-required matching (pre-code, architect-directed)

**Trigger.** The Builder built faithfully to v1.0.1; the Architect's trust-but-verify **retroactive sweep** against live `src/` then returned **24 findings** — not the v1.0.1 audit's predicted empty hit-list. Triage surfaced two distinct problems, both plan-side:

1. **The rule over-fires.** v1.0.1's table-scoped join fixed *colliding CHECK columns* (`role` on three tables) but still flagged a field **purely because its name coincides with a CHECK column on some table** — with no positive evidence the model corresponds to that table. Proof: `meta.py HealthStatus.status` — a health-check response model that maps to **no DB table at all** — was flagged against seven DB `status` tables. `SessionResponse.status`/`severity` were flagged though `diagnostic_sessions` carries no CHECK on those columns (it is not even in the rule's own collision set). This is the F9 name-vs-semantic-match failure reproduced *inside the F9 tool*.
2. **The v1.0.1 audit's "empty hit-list" was wrong** — incomplete. It enumerated `role`/`severity`/`extraction_*` but not `category`/`event`. Real `str`-instead-of-`Literal` regressions exist: `IssueCreateRequest.category`, `NotificationTriggerRequest.event`.

**The empty-hit-list premise is hereby retired.** 195C has genuine retroactive cleanup; "purely forward-looking" (v1.0/v1.0.1 framing) no longer holds.

**What changes v1.0 → v1.0.2** (plan-only; still no production code shipped):

1. **Positive-resolution-required matching.** A field is flagged **only when its model positively resolves to a table that carries a CHECK on that column.** No table resolution → no finding. Table resolves but carries no CHECK on that column → no finding. This **replaces both** v1.0.1's "non-colliding name → auto-match" *and* "colliding + unresolved → ambiguous finding" with a single rule: *no positive CHECK-bearing-table resolution → no finding.* The `pydantic-literal-vs-check-ambiguous` finding type is **removed** — an unresolved model is silently skipped, not flagged. (Trade accepted: a should-be-checked model that fails both marker and convention resolution is missed rather than false-flagged; markers — item 4 — close that for every real case.)
2. **Negative fixture as a phase-closure gate.** The test suite gains a `HealthStatus`-shaped negative fixture (a `BaseModel` with a field whose name coincides with a CHECK column, but the model maps to no table / a table with no such CHECK → **expect zero findings**). Same closure-gate status as v1.0.1's three-`role`-column fixture. The v1.0.1 tests passed only because they never exercised this case.
3. **Genuine findings fixed in-phase.** Bucket 2 — `IssueCreateRequest.category` (`issues.category` CHECK; field is `str`) and `NotificationTriggerRequest.event` (`customer_notifications.event` CHECK; field is `str`) — become **in-phase retroactive `str`→`Literal` fixes**, each its own documented change folded into the build commit + logged in `195C_phase_log.md`.
4. **Bucket 3 markers added.** Models that legitimately map to a colliding-name table get an authoritative `# f9-table: <table>` marker — `WorkOrderPhotoResponse`/`PhotoUploadMetadata`/`PhotoPatchRequest` → `work_order_photos`, `MemberAddRequest` → `shop_members`, plus markers on the Bucket 2 models so they resolve. This is authoritative resolution, **not** suppression.
5. **symptoms-category ruling (resolved pre-code).** `symptoms.category` and `extracted_symptoms.category` were checked: **both are `TEXT` with no CHECK constraint.** Therefore `SymptomResponse.category`, `ExtractedSymptomConfirmRequest.category`, `ExtractedSymptomResponse.category` are **Bucket 1** — false positives **dissolved by item 1** (their tables carry no `category` CHECK), not fixes. Only `issues.category` carries a CHECK, so only `IssueCreateRequest.category` is a Bucket 2 fix.

**Phase-closure criteria (v1.0.2):** the negative fixture green **and** the two Bucket-2 `str`→`Literal` fixes landed **and** a clean re-sweep — zero false positives, the only remaining findings (if any) being genuine and fixed.

The Builder built v1.0.1 faithfully; this defect is in the plan, surfaced exactly where the retroactive-sweep step is designed to surface it, and fixed by amendment **before** finalize — not tracked as a post-finalize follow-up. A phase does not close on a dirty result.

> **Step 3 (above) is superseded by this v1.0.2 amendment** — the table-scoped join now additionally requires positive model→table resolution for every field, and emits no `ambiguous` finding. The v1.1 finalize reconciles all sections to as-built.

---

## Deviations from Plan

The plan was amended twice pre-code (v1.0 → v1.0.1 → v1.0.2); the build then matched v1.0.2 exactly. Both amendments have full sections above — summarized here as the plan-to-as-built arc:

- **v1.0 → v1.0.1** (architect PR-review): the name-equality join would cross-wire three real same-named `role` columns. Amended to a table-scoped `(table, column)` join + the three-`role`-column closure-gate fixture.
- **v1.0.1 → v1.0.2** (architect trust-but-verify of the retroactive sweep): the table-scoped join still over-fired on name-coincidence against unrelated tables — `HealthStatus.status` (a health-check model with no DB table) flagged against 7 DB `status` tables. Amended to **positive-resolution-required matching** (flag only when the model resolves to a table carrying that CHECK); the `pydantic-literal-vs-check-ambiguous` finding type was removed; a `HealthStatus`-shaped negative fixture added as a second closure gate.
- **The "empty hit-list" premise was retired** (v1.0.2): the v1.0.1 audit under-enumerated (`role`/`severity`/`extraction_*` but not `category`/`event`). The retroactive sweep found 2 genuine regressions — `IssueCreateRequest.category` (`issues.category` CHECK) and `NotificationTriggerRequest.event` (`customer_notifications.event` CHECK) — each fixed in-phase as its own documented `str`→`Literal` change folded into the build commit.
- **Build-phase fix:** an `UnboundLocalError` in the Builder's first-pass join (the colliding-column resolved-success path never bound `table`) — caught by the phase tests, fixed before the v1.0.2 rework.
- **8 `# f9-table:` markers** added to the CHECK-bearing route models (`work_order_photos` ×3, `shop_members`, `issues`, `customer_notifications`, `voice_transcripts`, `extracted_symptoms`) — authoritative model→table resolution per v1.0.2 item 4.
- **`str,Enum` WARN, as-built:** the rule's `str,Enum` WARN branch never fires in the live codebase — `VideoResponse`'s `upload_state`/`analysis_state` map to `videos`, which carries no CHECK, so the model is correctly never examined for them. The WARN branch is exercised by a synthetic fixture only.

## Results

| Metric | Value |
|--------|-------|
| New sub-check | `check_pydantic_literal_vs_check_constraint` + `--check-pydantic-literal-vs-check-constraint` flag |
| Phase test file | `tests/test_phase195c_pydantic_literal_lint.py` — 25 tests, 25/25 green |
| Retroactive sweep | 24 raw findings → all false positives dissolved by v1.0.2 positive-resolution → 2 genuine fixes folded in → clean |
| Genuine regressions fixed in-phase | 2 — `IssueCreateRequest.category`, `NotificationTriggerRequest.event` (`str`→`Literal`) |
| `# f9-table:` markers added | 8 |
| Full backend regression | 4612 passed, 0 failed (1:22:09) |
| F9 pattern guide | subspecies 5→6, instances 10→11 (Subspecies (vi) contract-surface-drift, Instance #11) |

**Key finding:** the retroactive-sweep step earned its keep twice over. The v1.0.1 plan's audit predicted an empty hit-list; the actual sweep returned 24 findings — and triaging them exposed not one but two plan-side defects: the rule over-firing on name-coincidence, *and* the audit itself being incomplete. Both were fixed by pre-code amendment, never tracked as a post-finalize follow-up. The deeper lesson: a static rule that matches by name is itself susceptible to the F9 name-vs-semantic-match failure it exists to catch — positive-resolution-required matching (flag only with proof the model corresponds to the table) is the discipline that closes that loop.

---

*v1.1 — as-built. Phase 195C complete: built against plan v1.0.2 (amended twice pre-code), all phase-closure criteria met — negative fixture + three-`role`-column gate green, both Bucket-2 `str`→`Literal` fixes landed, clean re-sweep, full regression 4612/0.*
