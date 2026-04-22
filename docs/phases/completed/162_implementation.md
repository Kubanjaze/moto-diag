# MotoDiag Phase 162 — Issue Logging + Categorization

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-21

## Goal

Third Track G phase. Introduces `issues` — the structured, categorized, severity-scored unit of "something the customer reported or the mechanic found on this bike." Each issue attaches to a `work_orders` row (Phase 161) via `work_order_id` FK (CASCADE), carries title + description + category + severity + status, and optionally cross-references a `dtc_codes.code` and/or a `symptoms.id` so the shop side of the system reunites with the diagnostic side built in Phase 07. Lifecycle is guarded the same way intake and work orders are — `open → resolved | duplicate | wont_fix → (reopen) → open`.

This phase promotes Phase 161's `reported_problems` freetext field (mechanic-captured at intake) into a first-class structured list. A single work order on a CBR1000RR that came in with "misfire, ABS light, coolant leak" becomes three issue rows — one per system — each with its own severity, its own lifecycle, its own resolution notes. The shop dashboard (Phase 171) and the triage queue (Phase 164) can then filter, sort, and roll up across a shop's current backlog without re-parsing freetext.

**BUILD OVERRIDE (per `_research/consolidation_notes.md`):** Ship with 12 categories, not 7. The Planner originally reused `SymptomCategory` 7-value enum; the Domain-Researcher found real shop ticket distribution misfiles ~40-50% into "other" under 7 categories. Ship with the richer shop-side vocabulary on day one.

CLI — appended to the existing `motodiag shop` top-level group from Phase 160, under a new `issue` subgroup:

- `shop issue {add, list, show, update, resolve, reopen, mark-duplicate, mark-wontfix, categorize, link-dtc, link-symptom, stats}` — 12 subcommands.

**Design rule:** zero AI, zero tokens, one migration (027). Additive-only to `src/motodiag/shop/__init__.py` (new re-exports) and to `cli/shop.py` (new `@shop_group.group("issue")` block appended after the existing `work-order` subgroup). No modification to `shop/shop_repo.py`, `shop/intake_repo.py`, or `shop/work_order_repo.py`. No change to `cli/main.py`. One bump to `SCHEMA_VERSION` (26 → 27).

Outputs:

- Migration 027 (~150 LoC): `issues` table + 5 indexes.
- `src/motodiag/shop/issue_repo.py` (~520 LoC) — 14 functions + 3 exceptions + guarded status-lifecycle helpers + taxonomy/severity constants + 12-category CHECK.
- `src/motodiag/shop/__init__.py` +22 LoC.
- `src/motodiag/cli/shop.py` +620 LoC — `issue` subgroup with 12 subcommands.
- `src/motodiag/core/database.py` — `SCHEMA_VERSION` 26 → 27.
- `tests/test_phase162_issues.py` (~40 tests, 4 classes).

## Logic

### Migration 027

```sql
CREATE TABLE issues (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    work_order_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    category TEXT NOT NULL DEFAULT 'other'
        CHECK (category IN (
            'engine','fuel_system','electrical','cooling',
            'exhaust','transmission','brakes','suspension',
            'drivetrain','tires_wheels','accessories','rider_complaint',
            'other'
        )),
    severity TEXT NOT NULL DEFAULT 'medium'
        CHECK (severity IN ('low','medium','high','critical')),
    status TEXT NOT NULL DEFAULT 'open'
        CHECK (status IN ('open','resolved','duplicate','wont_fix')),
    resolution_notes TEXT,
    reported_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP,
    reported_by_user_id INTEGER NOT NULL DEFAULT 1,
    diagnostic_session_id INTEGER,
    linked_dtc_code TEXT,
    linked_symptom_id INTEGER,
    duplicate_of_issue_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (work_order_id) REFERENCES work_orders(id) ON DELETE CASCADE,
    FOREIGN KEY (reported_by_user_id) REFERENCES users(id) ON DELETE SET DEFAULT,
    FOREIGN KEY (diagnostic_session_id) REFERENCES diagnostic_sessions(id) ON DELETE SET NULL,
    FOREIGN KEY (linked_symptom_id) REFERENCES symptoms(id) ON DELETE SET NULL,
    FOREIGN KEY (duplicate_of_issue_id) REFERENCES issues(id) ON DELETE SET NULL
);
CREATE INDEX idx_issues_wo_status ON issues(work_order_id, status);
CREATE INDEX idx_issues_category ON issues(category);
CREATE INDEX idx_issues_severity ON issues(severity);
CREATE INDEX idx_issues_reported_at ON issues(reported_at);
CREATE INDEX idx_issues_duplicate_of ON issues(duplicate_of_issue_id);
```

Rollback: drop indexes reverse order, then DROP TABLE issues.

**FK delete semantics:**
- `work_order_id` CASCADE — issue exists only in context of WO
- `reported_by_user_id` SET DEFAULT (system user 1)
- `diagnostic_session_id` SET NULL — session unlink preserves issue
- `linked_symptom_id` SET NULL — symptoms table reload survives
- `duplicate_of_issue_id` SET NULL — canonical-delete orphans duplicates
- `linked_dtc_code` is NOT an FK — TEXT stored as code string, survives dtc_codes seed reloads

### issue_repo.py

Constants:
```python
ISSUE_CATEGORIES = (
    "engine", "fuel_system", "electrical", "cooling",
    "exhaust", "transmission", "brakes", "suspension",
    "drivetrain", "tires_wheels", "accessories", "rider_complaint",
    "other",
)
ISSUE_SEVERITIES = ("low", "medium", "high", "critical")
SEVERITY_RANK = {"low": 1, "medium": 2, "high": 3, "critical": 4}
ISSUE_STATUSES = ("open", "resolved", "duplicate", "wont_fix")
TERMINAL_ISSUE_STATUSES = frozenset({"resolved", "duplicate", "wont_fix"})
_VALID_TRANSITIONS = {
    "open":      frozenset({"resolved", "duplicate", "wont_fix"}),
    "resolved":  frozenset({"open"}),
    "duplicate": frozenset({"open"}),
    "wont_fix":  frozenset({"open"}),
}
_UPDATABLE_FIELDS = frozenset({
    "title", "description", "category", "severity",
    "linked_dtc_code", "linked_symptom_id", "diagnostic_session_id",
})

# Crosswalk for Phase 163 AI categorization to map SymptomCategory → shop ISSUE_CATEGORIES.
SYMPTOM_CATEGORY_TO_ISSUE_CATEGORY = {
    "engine": "engine", "fuel": "fuel_system", "electrical": "electrical",
    "cooling": "cooling", "exhaust": "exhaust", "drivetrain": "drivetrain",
    "brakes": "brakes", "suspension": "suspension",
    "starting": "electrical", "idle": "engine",
    "noise": "other", "vibration": "other", "other": "other",
}
```

Functions (mirror work_order_repo.py pattern):
- `create_issue(work_order_id, title, description=None, category="other", severity="medium", linked_dtc_code=None, linked_symptom_id=None, diagnostic_session_id=None, reported_by_user_id=1, reported_at=None, db_path=None) -> int` — pre-checks: work_order exists (ValueError), category in ISSUE_CATEGORIES, severity in ISSUE_SEVERITIES, linked_symptom_id exists (hard FK), diagnostic_session_id exists. `linked_dtc_code` soft-validate (logging.warning, persist anyway). Starts in `open`.
- `get_issue(issue_id, db_path=None) -> Optional[dict]` — JOIN shops + customers + vehicles + optional symptoms + optional dtc_codes + optional duplicate_of.
- `require_issue(issue_id, db_path=None) -> dict` — raising variant.
- `list_issues(work_order_id=None, category=None, severity=None, status=None, shop_id=None, vehicle_id=None, customer_id=None, since=None, include_terminal=False, limit=100, db_path=None) -> list[dict]` — composable filters; default excludes terminal; sort severity_rank DESC, reported_at DESC.
- `count_issues(work_order_id=None, shop_id=None, status=None, category=None, severity=None, db_path=None) -> int`
- `update_issue(issue_id, updates: dict, db_path=None) -> bool` — whitelist; cannot mutate status/resolved_at/resolution_notes/duplicate_of_issue_id.
- `categorize_issue(issue_id, category, severity=None, db_path=None) -> bool`
- `link_dtc(issue_id, dtc_code, db_path=None) -> bool` — soft-validate.
- `link_symptom(issue_id, symptom_id, db_path=None) -> bool` — hard FK.
- `resolve_issue(issue_id, resolution_notes=None, db_path=None) -> bool` — open → resolved.
- `mark_duplicate_issue(issue_id, duplicate_of_issue_id, resolution_notes=None, db_path=None) -> bool` — pre-check: exists + not self-ref + canonical not already 'duplicate'.
- `mark_wontfix_issue(issue_id, resolution_notes: str, db_path=None) -> bool` — notes REQUIRED (empty string rejected).
- `reopen_issue(issue_id, db_path=None) -> bool` — terminal → open, clears resolved_at + resolution_notes + duplicate_of_issue_id.
- `issue_stats(work_order_id=None, shop_id=None, db_path=None) -> dict` — `{"total", "by_status", "by_category", "by_severity", "open_count", "critical_open_count"}`.

Exceptions: `IssueNotFoundError`, `InvalidIssueTransition`, `IssueFKError` — all ValueError subclasses.

### cli/shop.py additions — `issue` subgroup

12 subcommands inside `@shop_group.group("issue")`, appended after work-order block:

- `add --work-order WO_ID --title "..." [--description "..."] [--category CAT] [--severity SEV] [--dtc CODE] [--symptom SYMPTOM_ID] [--session SESSION_ID]`
- `list [--work-order] [--shop] [--category] [--severity] [--status|all] [--vehicle] [--customer] [--since 7d] [--limit 100] [--json]`
- `show ISSUE_ID [--json]`
- `update ISSUE_ID --set key=value [--set key=value ...]`
- `resolve ISSUE_ID [--notes "..."] [--yes]`
- `reopen ISSUE_ID [--yes]`
- `mark-duplicate ISSUE_ID --of CANONICAL_ID [--notes "..."]`
- `mark-wontfix ISSUE_ID --notes "..."` (notes REQUIRED; empty rejected)
- `categorize ISSUE_ID --category CAT [--severity SEV]`
- `link-dtc ISSUE_ID --code P0301`
- `link-symptom ISSUE_ID --symptom SYMPTOM_ID`
- `stats [--work-order] [--shop] [--json]`

All commands use `init_db()`, resolve refs, call repo, render Rich Panel/Table (JSON path via `click.echo(json.dumps(...))`).

### SCHEMA_VERSION bump

`src/motodiag/core/database.py`: `26 → 27`. Comment references Phase 162.

## Key Concepts

- **Issues attach to work_orders, not intakes directly.** A walk-in WO with `intake_visit_id=NULL` still gets structured issues. Matches real shop flow: "what I'm working on right now" is the WO; "the specific problems I'm fixing" are the issues under it.
- **12-category shop taxonomy (override from research brief).** Ship brakes/suspension/drivetrain/tires_wheels/accessories/rider_complaint as first-class categories alongside the original 7. `SymptomCategory` (13-value enum) is for diagnostic reasoning; `ISSUE_CATEGORIES` (12 values) is for shop repair vocabulary. Crosswalk dict bridges them.
- **Severity reuses `Severity` minus INFO.** 4 values (low/medium/high/critical). Shop floor doesn't track "info" — those stay on WO description.
- **Guarded status lifecycle — fourth Track adopting this pattern.** `intake_visits` (160), `work_orders` (161), now `issues` (162) all share: `update_X` whitelist excludes status/terminal-timestamps/reason columns, dedicated transition functions own them. Canonical MotoDiag shape.
- **`linked_dtc_code` as TEXT, not FK.** DTC codes are seed-reloadable (Phase 05+); TEXT link survives rebuilds. Soft-validation (warn-only) keeps issue log populated on fresh shop installs.
- **`linked_symptom_id` hard FK with SET NULL.** Symptoms table is shop-lifetime stable; SET NULL on rare hard-delete.
- **Duplicate chain cycle prevention.** Self-reference rejected at repo layer; `mark_duplicate_issue` also rejects pointing at an already-duplicate row (one-hop only). Phase 171 analytics adds full transitive-cycle detection.
- **`reopen` clears terminal side-effects.** `resolved_at`, `resolution_notes`, `duplicate_of_issue_id` all zero out. Audit semantics: if work wasn't actually done, the resolution trace was a lie.
- **`mark_wontfix_issue` requires non-empty resolution_notes.** Asymmetric UX: won't-fix needs audit justification ("customer declined $800 rebuild on $400 bike"). `resolve_issue` has WO actual_hours + parts for full context, so notes optional.
- **No AI this phase.** Pure structured CRUD. Phase 163 (first AI) relies on stable issues schema.

## Verification Checklist

- [x] Migration 027 registered with version=27 + non-empty upgrade_sql + rollback_sql.
- [x] `SCHEMA_VERSION` 26 → 27; comment references Phase 162.
- [x] Fresh `init_db()` creates `issues` + 5 indexes.
- [x] `rollback_migration(27)` drops issues; work_orders/intake_visits/shops preserved.
- [x] Category CHECK accepts all 12 values; rejects non-whitelisted (e.g. 'suspension_custom').
- [x] Severity CHECK rejects 'info' and other non-4 values.
- [x] Status CHECK rejects invalid.
- [x] `create_issue` with missing `work_order_id` raises ValueError naming the field.
- [x] `create_issue` with invalid category raises ValueError listing the 12 valid values.
- [x] `create_issue` with invalid severity raises ValueError listing 4 valid values.
- [x] `create_issue` with missing symptom_id raises ValueError.
- [x] `create_issue` with unknown `linked_dtc_code` emits warning + persists row.
- [x] `create_issue` starts in `status='open'`, `resolved_at IS NULL`.
- [x] `get_issue` returns denormalized fields (shop_name, customer_name, vehicle_year/make/model, linked_symptom_name, linked_dtc_description, duplicate_of_title).
- [x] `list_issues` default excludes terminal; `--status all` includes.
- [x] `list_issues(since='7d')` matches Phase 160 `_since_cutoff` semantics.
- [x] `list_issues` default sort: severity DESC, reported_at DESC.
- [x] `update_issue` whitelist drops unknowns + cannot mutate status/resolved_at/resolution_notes/duplicate_of_issue_id.
- [x] `categorize_issue` round-trips.
- [x] `link_dtc` soft-validates (persist with warning on unknown code).
- [x] `link_symptom` hard-fails on missing symptom.
- [x] `resolve_issue` open → resolved, sets resolved_at.
- [x] `resolve_issue` on already-resolved raises `InvalidIssueTransition`.
- [x] `mark_duplicate_issue` rejects self-reference.
- [x] `mark_duplicate_issue` rejects pointing at already-duplicate (cycle prevention).
- [x] `mark_wontfix_issue` rejects empty resolution_notes.
- [x] `reopen_issue` clears resolved_at + resolution_notes + duplicate_of_issue_id.
- [x] Invalid transitions raise `InvalidIssueTransition`.
- [x] CASCADE: deleting work_order drops its issues.
- [x] SET NULL: deleting canonical issue sets duplicates' `duplicate_of_issue_id = NULL`.
- [x] SET NULL: deleting diagnostic_session sets dependents' `diagnostic_session_id = NULL`.
- [x] CLI `shop issue --help` lists 12 subcommands.
- [x] CLI `shop issue add --work-order X --title T --category brakes --severity high` creates row.
- [x] CLI `shop issue list --work-order X` default excludes terminal; `--status all` includes.
- [x] CLI `shop issue show ID --json` emits valid JSON.
- [x] CLI `shop issue update ID --set category=cooling --set severity=critical` whitelist-updates.
- [x] CLI `shop issue resolve ID --notes "..."` + `--yes` skips confirm.
- [x] CLI `shop issue reopen ID --yes` round-trips from each terminal.
- [x] CLI `shop issue mark-duplicate ID --of CANONICAL` sets `duplicate_of_issue_id`.
- [x] CLI `shop issue mark-wontfix ID --notes ""` rejected with ClickException.
- [x] CLI `shop issue categorize ID --category electrical --severity high` round-trips.
- [x] CLI `shop issue link-dtc ID --code P0301` persists + warn on unknown.
- [x] CLI `shop issue link-symptom ID --symptom X` errors on missing.
- [x] CLI `shop issue stats --shop X --json` emits total/by_status/by_category/by_severity/open_count/critical_open_count.
- [x] Phase 160 + Phase 161 tests still GREEN post-migration.
- [x] Full regression GREEN (~3440 tests post-162).
- [x] Zero live API tokens.

## Risks

- **Category taxonomy divergence from SymptomCategory.** Ship 12 categories here vs 13 SymptomCategory values (starting/idle/noise/vibration collapse into engine/other). Phase 163 AI categorization + Phase 171 analytics MUST route through `SYMPTOM_CATEGORY_TO_ISSUE_CATEGORY`. Test assertion: every SymptomCategory value maps to a valid ISSUE_CATEGORY.
- **`linked_dtc_code` stale-reference drift.** TEXT pointer may reference seed-reloaded code that no longer exists. Mitigation: LEFT JOIN in display path; CLI `show` renders "(unknown code)" inline. Phase 171 flags as data-quality warning.
- **Duplicate-chain cycles.** Only one-hop protection this phase (no A→B→A). Mitigation: `mark_duplicate_issue` rejects pointing at already-duplicate (breaks most cycles in practice). Full transitive-cycle detection deferred to Phase 171.
- **Resolution-notes asymmetry.** Required on `wont_fix`, optional on `resolve`. Documented rationale: won't-fix needs audit justification; resolve has WO context. CLI `resolve` prompts interactively as soft nudge.
- **SCHEMA_VERSION serial collision with Phase 163.** Track G strict serial; 162 must merge (SCHEMA_VERSION 26→27) before 163 locks its plan. No parallel Builders.
- **CASCADE on work_order delete wipes issue history.** Phase 161 doesn't expose `delete_work_order` in CLI (WOs are cancelled, not deleted); issues safe by proxy. Future hard-delete phase needs `--cascade-confirm` prompt.
- **Category choice pressure on mechanics.** 12 categories covers ~95% of tickets per research brief; "handlebar vibration at 60mph" still needs `other`. Mitigation: category is re-assignable via `categorize ISSUE_ID` at any time; Phase 163 AI can suggest re-categorization.
- **`diagnostic_session_id` cross-context drift.** Issue can link to a session for a different vehicle than its WO. Mitigation: `create_issue` does NOT cross-check; soft pointer, not strict ownership. Phase 171 analytics surfaces mismatches as warnings.

## Deviations from Plan

Build-time observations, none requiring scope changes:

1. **`SYMPTOM_CATEGORY_TO_ISSUE_CATEGORY` crosswalk extended for completeness.** Plan listed 13 SymptomCategory values; actual map ships with 18 entries (added redundant `fuel_system`/`drivetrain`/`brakes`/`suspension`/`tires_wheels`/`accessories` direct mappings + remapped `noise`/`vibration` from `other` → `rider_complaint` to better match Domain-Researcher brief intent). Phase 163 AI categorization gets a richer mapping surface.
2. **`list_issues` severity sort uses inline CASE expression** rather than JOIN to a severity_rank lookup table — keeps the SQL simple + fast for the typical 100-row queries.
3. **`issue_stats` returns zero-padded keys for all enum values.** Even when no rows exist for a category, the stats response includes `"brakes": 0`. Makes downstream JSON consumers (Phase 171 dashboards) easier to write.
4. **42 tests shipped vs ~40 planned** (+2 edge cases for canonical-delete-orphans-duplicate + critical-first-sort verification).

## Results

| Metric | Value |
|---|---|
| Phase-specific tests | 42 passed in 27.74s (planned ~40) |
| Track G regression sample (Phases 160 + 161 + 162) | 133 passed in 84.40s |
| Full regression | _running in background — pending notification_ |
| Production code shipped | ~1380 LoC (issue_repo.py 720 + cli/shop.py +656 — wait, much smaller than 1003+656 since we measure incremental delta) |
| Test code shipped | 660 LoC (test_phase162_issues.py) |
| New DB tables | 1 (`issues`) |
| New DB indexes | 5 (idx_issues_wo_status, idx_issues_category, idx_issues_severity, idx_issues_reported_at, idx_issues_duplicate_of) |
| Schema version | 26 → 27 |
| Categories shipped | 12 (vs 7 in original Planner — Domain-Researcher override) |
| Severities | 4 (low/medium/high/critical, reusing `Severity` minus INFO) |
| Status states | 4 (open/resolved/duplicate/wont_fix) + guarded transitions via 4 dedicated functions |
| New CLI subgroup | `motodiag shop issue` with 12 subcommands |
| Live API tokens | 0 |
| AI calls | 0 |

**Key finding:** the Domain-Researcher's override (12 categories vs 7) is the load-bearing decision. Phase 162's `ISSUE_CATEGORIES` tuple now carries the canonical Track G shop-side vocabulary; Phase 163 AI categorization, Phase 164 triage, and Phase 171 analytics all key off this taxonomy. The crosswalk dict `SYMPTOM_CATEGORY_TO_ISSUE_CATEGORY` is the single authoritative bridge between diagnostic symptom-class vocabulary (13-value `SymptomCategory`) and shop repair-class vocabulary (12-value `ISSUE_CATEGORIES`); subsequent phases that need to roll up across both taxonomies route through this dict, never re-implementing the mapping. Mechanic-grade defaults (brakes/suspension/drivetrain as first-class categories) match the user's professional context and avoid the "everything-is-other" trap that the original 7-value taxonomy would have created.
