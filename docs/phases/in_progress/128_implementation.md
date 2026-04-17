# MotoDiag Phase 128 — Knowledge Base Browser (CLI)

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-04-18

## Goal
Give mechanics a CLI to browse the `known_issues` knowledge base without writing SQL. Five subcommands under a new `motodiag kb` group: `list`, `show`, `search`, `by-symptom`, `by-code`. All read-only — pure browsing over the existing Phase 03 + Phase 08 substrate. No migration, no new package — everything lives in a new `src/motodiag/cli/kb.py` orchestration module wired into `main.py` via `register_kb(cli)`.

```
motodiag kb list                                  # rich table, newest first, default limit 50
motodiag kb list --make Honda --severity high
motodiag kb show 42                               # full issue detail
motodiag kb search "stator"                       # title + description + symptoms full-text LIKE
motodiag kb by-symptom "won't start"              # find_issues_by_symptom
motodiag kb by-code P0562                         # find_issues_by_dtc
```

Outputs: new `src/motodiag/cli/kb.py` (~300 LoC), one-line wire-up in `cli/main.py`, one new search function in `knowledge/issues_repo.py` (`search_known_issues_text` — adds query-across-fields since existing `search_known_issues` is structured-filter only), ~25 new tests. **No migration.**

## Logic

### 1. `knowledge/issues_repo.py` — one new helper
- `search_known_issues_text(query, limit=None, db_path=None) -> list[dict]` — case-insensitive LIKE substring across `title`, `description`, and `symptoms` (JSON text). Returns rows matching ANY of those three columns. ORDER BY `created_at DESC, id DESC`, optional LIMIT.
- Rationale: existing `search_known_issues(make, model, year, severity, symptom_keyword)` is structured filters (exact-match for most, `symptom_keyword` LIKE against `symptoms`). The browse-search use case wants "find me anything mentioning stator" across multiple columns at once. Cleaner to add a dedicated function than to overload the existing one.

### 2. New `src/motodiag/cli/kb.py` (~300 LoC)

- `_default_repo_fns` — lightweight module-level dict aliasing the repo functions so tests can swap them with a narrow patch (same pattern as Phase 123 `_default_diagnose_fn`). Not strictly needed since all calls are DB-only — but keeps the module self-contained for future Track R 318 enrichments.
- `_render_issue_table(rows, console, title)` — rich.Table with columns: ID, make, model, year range, severity, title (truncated to 60 chars if longer, `...` suffix), `# fixes` (len(`parts_needed` or []), as a rough "has-parts" indicator).
- `_render_issue_detail(row, console)` — rich.Panel + subsections: title + header panel (id/make/model/year range/severity), description paragraph, symptoms bulleted list, DTC codes bulleted list, causes bulleted list, fix_procedure paragraph, parts_needed bulleted list (with "— $X" if price data available later), estimated_hours callout.
- `_year_range_str(row)` — format year_start/year_end into "2001-2017", "2001+", or "any".

- `register_kb(cli_group)` — attaches a `@cli_group.group("kb")` with 5 subcommands:
  - `kb list [--make TEXT --model TEXT --year INT --severity TEXT --limit INT --symptom TEXT]` — calls `search_known_issues(...)`. Empty result prints yellow "No issues match the filters".
  - `kb show <issue_id>` — calls `get_known_issue(id)`. Missing → ClickException.
  - `kb search <query>` — calls the new `search_known_issues_text(query, limit=50)`. Empty result: yellow "No issues mention '<query>'".
  - `kb by-symptom <symptom>` — calls `find_issues_by_symptom(symptom)`. Uses rich.Table output.
  - `kb by-code <dtc>` — calls `find_issues_by_dtc(code)`. Uses rich.Table output.

### 3. Wire into `cli/main.py`
- Add `from motodiag.cli.kb import register_kb`
- Call `register_kb(cli)` after the existing `register_quick(cli)` line.

### 4. Testing (~25 tests)

- **`TestRepoTextSearch`** (5 tests): matches in title, description, symptoms JSON; case-insensitive; empty query returns empty; limit respected.
- **`TestCliList`** (5 tests): default list renders; --make filter; --severity filter; --limit caps; empty-filter message.
- **`TestCliShow`** (3 tests): happy path shows title+description+fix_procedure; missing id errors; handles issue with empty symptoms/causes/parts arrays.
- **`TestCliSearch`** (4 tests): matches title, matches description, matches symptom-in-JSON, empty-result message.
- **`TestCliBySymptom`** (3 tests): happy path, empty-result message, uses existing `find_issues_by_symptom`.
- **`TestCliByCode`** (3 tests): happy path via `find_issues_by_dtc`, empty-result message, case-insensitive on DTC code.
- **`TestRegistration`** (2 tests): `kb` command group registered, 5 subcommands present.

All tests use the `cli_db` fixture pattern (reset_settings after MOTODIAG_DB_PATH env patch). Test fixtures seed 4-5 known issues via `add_known_issue()` with distinct makes/severities/symptoms/DTCs for filter coverage. Zero AI calls. Zero live tokens.

## Key Concepts
- **5 subcommands under one `kb` group** keeps the command tree readable. `list` + `show` mirror the `diagnose list`/`show` pattern established in Phases 123/126/127 — consistency wins over brevity.
- **No export to file**: `kb show` prints to terminal only. If customer feedback demands export, Phase 132 (export + sharing) can generalize the Phase 126 `--format` + `--output` pattern to kb-show. YAGNI for v1.
- **New `search_known_issues_text` vs reusing `search_known_issues`**: the structured-filter function is for known filters (make/model/year); the new text function is for free-text browsing. Two complementary paths — a mechanic filtering by bike uses `list --make Honda`; a mechanic investigating a symptom uses `search "stator"`.
- **Four repo functions reused**: `search_known_issues` (list), `get_known_issue` (show), `find_issues_by_symptom` (by-symptom), `find_issues_by_dtc` (by-code). Only `search_known_issues_text` is new. The Phase 08 substrate pays off again.
- **Pure browsing, no mutation**: no `kb add` or `kb edit` — known_issues content is loaded via JSON loaders (Phase 05/08). Editing via CLI would bypass the content curation workflow. Future Phase 318 (continuous learning) adds structured feedback that can flow back into known_issues, but not via direct CLI edit.
- **Registration pattern consistent with Phases 123/124/125**: `register_kb(cli_group)` attaches a click.group; `cli/main.py` just imports and calls. Same pattern every Track D phase.

## Verification Checklist
- [ ] `motodiag kb --help` lists 5 subcommands
- [ ] `search_known_issues_text("stator")` matches rows with "stator" in title
- [ ] `search_known_issues_text("stator")` matches rows with "stator" in description
- [ ] `search_known_issues_text("stator")` matches rows with "stator" in symptoms JSON
- [ ] `search_known_issues_text` is case-insensitive
- [ ] `search_known_issues_text("", limit=5)` returns empty (empty query)
- [ ] `search_known_issues_text(query, limit=N)` respects limit
- [ ] `motodiag kb list` renders seeded issues as rich table
- [ ] `motodiag kb list --make Honda` filters correctly
- [ ] `motodiag kb list --severity high` filters correctly
- [ ] `motodiag kb list --limit 3` caps output
- [ ] `motodiag kb list` with no matches prints "No issues match the filters"
- [ ] `motodiag kb show <id>` renders full detail (title + description + fix_procedure)
- [ ] `motodiag kb show MISSING` exits nonzero with error
- [ ] `motodiag kb show <id>` handles empty symptoms/causes/parts gracefully
- [ ] `motodiag kb search "stator"` returns matching issues
- [ ] `motodiag kb search "nonexistent"` prints empty-result message
- [ ] `motodiag kb by-symptom "won't start"` returns matching issues
- [ ] `motodiag kb by-code P0562` returns matching issues (case-insensitive code)
- [ ] `kb` command group registered in cli.commands
- [ ] All 2207 existing tests still pass (zero regressions)
- [ ] Zero live API tokens

## Risks
- **LIKE-based text search is O(n) scan**: at projected knowledge-base sizes (500-2000 rows), LIKE across 3 columns is fine. If it gets slow, Phase 175 (REST API) can add an FTS5 virtual table backed by triggers — that's already tentatively in scope for the knowledge-surface redesign.
- **`kb show` without export**: mechanics may want to save an issue reference for a customer note. Accepted — Phase 132 will generalize the Phase 126 export pattern to cover kb output as well.
- **Parts/hours formatting**: `parts_needed` and `estimated_hours` fields may be sparsely populated. Renderer handles None/empty gracefully; doesn't crash or print "(null)".
- **Search query escaping**: LIKE pattern with `%` wildcards is constructed from user input via parameter binding (not string concat), so SQL injection is not a concern.
