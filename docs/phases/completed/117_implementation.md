# MotoDiag Phase 117 — Reference Data Tables

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-17

## Goal
Create the reference-data substrate that Track P phases 293-302 (Clymer/Haynes citations, exploded parts diagrams, failure photos library, video tutorials index) will consume. New `src/motodiag/reference/` package plus 4 empty tables: `manual_references`, `parts_diagrams`, `failure_photos`, `video_tutorials`. Schema only — each table gets CRUD and metadata lookup; Track P phases populate actual content. Year-range targeting via `year_start`/`year_end` reuses the `known_issues` pattern.

CLI: `python -m pytest tests/test_phase117_reference.py -v`

Outputs: `src/motodiag/reference/` package (6 files), migration 010, 28 tests

## Logic
1. **Migration 010** — 4 new tables:
   - `manual_references` — id, source, title, publisher, isbn, make, model, year_start, year_end, page_count, section_titles (JSON), url, notes, created_at
   - `parts_diagrams` — id, make, model, year_range, diagram_type, section, title, image_ref, source_manual_id (FK manual_references ON DELETE SET NULL), notes, created_at
   - `failure_photos` — id, title, description, failure_category, make, model, year_range, part_affected, image_ref, submitted_by_user_id (FK users DEFAULT 1, ON DELETE SET DEFAULT), created_at
   - `video_tutorials` — id, title, description, source, source_video_id, url, duration_seconds, make, model, year_range, skill_level (DEFAULT 'intermediate'), topic_tags (JSON), created_at
   - 8 indexes: make/model on each table, plus source on manuals, diagram_type on diagrams, category on photos, source on videos
   - Rollback drops all 4 tables (diagrams/videos/photos first, then manuals — FK-safe)

2. **`reference/models.py`** — 4 enums + 4 Pydantic models:
   - `ManualSource` (5): CLYMER, HAYNES, OEM, FORUM, OTHER
   - `DiagramType` (4): EXPLODED_VIEW, SCHEMATIC, WIRING, ASSEMBLY
   - `FailureCategory` (7): MECHANICAL_WEAR, ELECTRICAL_FAILURE, CORROSION, COSMETIC_DAMAGE, CRASH_DAMAGE, FLUID_LEAK, OTHER
   - `SkillLevel` (4): BEGINNER, INTERMEDIATE, ADVANCED, EXPERT

3. **4 repo modules** (`manual_repo.py`, `diagram_repo.py`, `photo_repo.py`, `video_repo.py`) — 5 functions each (add/get/list/update/delete). JSON column serialization in `manual_repo` (section_titles) and `video_repo` (topic_tags).

4. **Year-range filter pattern** (shared across all 4 list_* functions):
   ```sql
   AND (year_start IS NULL OR year_start <= ?)
   AND (year_end IS NULL OR year_end >= ?)
   ```
   Matches the exact semantics used by `known_issues`: NULL year_start means "universal" (applies to any year).

5. **`reference/__init__.py`** — exports all public API (4 enums + 4 models + 20 repo functions).

6. **`database.py`**: `SCHEMA_VERSION` 9 → 10.

## Key Concepts
- Year-range targeting reuses the `year_start <= target_year <= year_end` pattern from `known_issues` — keeps query style consistent across the knowledge layer
- `image_ref` and `url` columns are opaque strings — could be local filesystem paths, S3 URIs, or HTTP URLs. Track P populates the actual storage strategy.
- `parts_diagrams.source_manual_id` is an optional FK to `manual_references` with ON DELETE SET NULL — lets a diagram cite its source manual but also survive if the manual reference is removed
- `failure_photos.submitted_by_user_id` uses ON DELETE SET DEFAULT (system user id=1) — preserves photo provenance even if the original submitter is deleted
- Empty tables are intentional — Phase 117 is substrate only. Track P phases 293-302 populate content.
- Consistent filter interface across all 4 repos: every `list_*` accepts make/model/target_year filters
- `video_repo.list_videos` supports `topic` filter via SQL LIKE against the JSON text column — simple keyword match; Track P can graduate to FTS5 later if needed
- All 4 `update_*` functions take **kwargs and serialize enum/JSON values automatically

## Verification Checklist
- [x] Migration 010 creates 4 reference tables with correct schema
- [x] 8 indexes created (make/model on each, source/type/category where applicable)
- [x] 4 enums have correct member counts (5/4/7/4)
- [x] 4 Pydantic models validate and round-trip correctly
- [x] CRUD round-trips for each repo (add/get/list/update/delete)
- [x] Year-range filter works: year_start <= target_year <= year_end
- [x] Year-range filter handles year_start IS NULL (universal resources — returns universal)
- [x] parts_diagrams.source_manual_id SET NULL cascade works when manual deleted
- [x] failure_photos defaults submitted_by to system user (id=1)
- [x] JSON columns (section_titles, topic_tags) round-trip correctly
- [x] video_repo.list_videos topic filter works via JSON LIKE
- [x] Rollback drops all 4 tables cleanly
- [x] Schema version assertions use `>=` (forward-compat)
- [x] All 1867 existing tests still pass (zero regressions) — full suite 1895/1895 in 8:26

## Risks
- **Tables remain empty after Phase 117**: intentional. Track P phases 293-302 populate content. Tests validate schema + CRUD, not content presence.
- **image_ref column is a string, not a FK**: image storage is deferred to Track P phase 295. Accepted — saves premature commitment to storage backend.
- **Year-range with NULL**: handled via `(year_start IS NULL OR year_start <= ?)` pattern — universal resources match any target_year.
- **JSON LIKE on topic_tags**: functional but not FTS. Matches `"keyword"` with quote boundaries so "brake" won't match "brakeless". Good enough for Phase 117; upgrade to FTS5 when Track P ships the video index.

## Deviations from Plan
- None. Built exactly to plan: migration 010, reference/ package with 6 files (including 4 repo modules), 28 tests.

## Results
| Metric | Value |
|--------|-------|
| New files | 7 (reference/{__init__,models,manual_repo,diagram_repo,photo_repo,video_repo}.py + test_phase117_reference.py) |
| New tests | 28 |
| Total tests | 1895 passing (was 1867) |
| New enums | 4 (5+4+7+4 = 20 members total) |
| New models | 4 Pydantic models |
| Repo functions | 20 (5 per repo × 4 repos) |
| New tables | 4 |
| New indexes | 8 |
| Schema version | 9 → 10 |
| Regression status | Zero regressions — full suite 8:26 runtime |

Phase 117 gives Track P a complete reference-data substrate. The year-range filter pattern (now used by both `known_issues` and all 4 reference tables) has become the de-facto knowledge-layer query convention. `parts_diagrams.source_manual_id` sets up the manual-to-diagram link that Track P phase 293 needs on day one.
