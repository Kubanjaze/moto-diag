# MotoDiag Phase 117 — Reference Data Tables

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-04-17

## Goal
Create the reference-data substrate that Track P phases 293-302 (Clymer/Haynes citations, exploded parts diagrams, failure photos library, video tutorials index) will consume. New `src/motodiag/reference/` package plus 4 empty tables: `manual_references`, `parts_diagrams`, `failure_photos`, `video_tutorials`. Schema only — each table gets CRUD and metadata lookup; Track P phases populate actual content. Ties to vehicles via optional make/model/year_start/year_end range (same pattern used by `known_issues`).

CLI: `python -m pytest tests/test_phase117_reference.py -v`

Outputs: `src/motodiag/reference/` package (5 files), migration 010, ~40 tests

## Logic
1. **Migration 010** — 4 new tables:
   - `manual_references` — id, source (Clymer/Haynes/OEM/forum/other), title, publisher, isbn, make, model, year_start, year_end, page_count, section_titles (JSON), url, notes, created_at
   - `parts_diagrams` — id, make, model, year_start, year_end, diagram_type (exploded_view/schematic/wiring/assembly), section, title, image_ref (filesystem path or URL), source_manual_id (FK manual_references ON DELETE SET NULL), notes, created_at
   - `failure_photos` — id, title, description, failure_category (enum: mechanical_wear / electrical_failure / corrosion / cosmetic_damage / crash_damage / fluid_leak / other), make, model, year_start, year_end, part_affected, image_ref, submitted_by_user_id (FK users DEFAULT 1), created_at
   - `video_tutorials` — id, title, description, source (youtube/vimeo/internal/other), source_video_id, url, duration_seconds, make, model, year_start, year_end, skill_level (enum: beginner/intermediate/advanced/expert), topic_tags (JSON), created_at
   - 8 indexes total (make/model on each, category/source on enum-carrying tables)
   - Rollback drops all 4 tables (FK-safe order: diagrams first because of the optional FK to manuals)

2. **`reference/models.py`** — 4 enums + 4 Pydantic models:
   - `ManualSource` enum (5): CLYMER, HAYNES, OEM, FORUM, OTHER
   - `DiagramType` enum (4): EXPLODED_VIEW, SCHEMATIC, WIRING, ASSEMBLY
   - `FailureCategory` enum (7): MECHANICAL_WEAR, ELECTRICAL_FAILURE, CORROSION, COSMETIC_DAMAGE, CRASH_DAMAGE, FLUID_LEAK, OTHER
   - `SkillLevel` enum (4): BEGINNER, INTERMEDIATE, ADVANCED, EXPERT
   - Models: `ManualReference`, `PartsDiagram`, `FailurePhoto`, `VideoTutorial`

3. **4 repo modules** (one per table), each with 5 functions:
   - `add_*`, `get_*`, `list_*` (filters: make/model/year range — reuses `year_start <= target_year <= year_end` pattern from known_issues), `update_*`, `delete_*`
   - `search_*` where it makes sense (title/description text match)

4. **`reference/__init__.py`** — exports public API.

5. **`database.py`**: `SCHEMA_VERSION` 9 → 10.

## Key Concepts
- Year-range targeting reuses the `year_start <= target_year <= year_end` pattern already used by `known_issues` — keeps query style consistent across the knowledge layer
- `image_ref` and `url` columns are opaque strings — could be local filesystem paths, S3 URIs, or HTTP URLs. Track P populates the actual storage strategy.
- `parts_diagrams.source_manual_id` is an optional FK to `manual_references` — lets a diagram cite its source manual but also survive if the manual reference is removed (ON DELETE SET NULL)
- Empty tables are intentional — the goal of Phase 117 is the substrate, not content. Track P phases 293-302 each populate a specific data family.
- All tables FK-compatible with the user layer for attribution (failure_photos has submitted_by_user_id). Manual/diagram/video don't need submitter tracking (they're external resources, not user-generated content).
- Consistent filter interface across repos: every `list_*` accepts make/model/year filters so Track N workflow phases can do "find all reference material for this bike"

## Verification Checklist
- [ ] Migration 010 creates 4 reference tables with correct schema
- [ ] 8 indexes created (make/model on each, enum columns where applicable)
- [ ] 4 enums have correct member counts
- [ ] 4 Pydantic models validate correctly
- [ ] CRUD round-trips for each repo (add/get/list/update/delete)
- [ ] Year-range filter works: year_start <= target_year <= year_end
- [ ] Year-range filter handles year_start IS NULL (universal resources)
- [ ] parts_diagrams.source_manual_id SET NULL cascade works when manual deleted
- [ ] failure_photos defaults submitted_by to system user (id=1)
- [ ] JSON columns (section_titles, topic_tags) round-trip correctly
- [ ] Rollback drops all 4 tables cleanly
- [ ] All 1867 existing tests still pass (zero regressions)
- [ ] Schema version assertions use `>=` (forward-compat)

## Risks
- **Tables remain empty after Phase 117**: intentional. Track P phases 293-302 populate content. Tests validate schema + CRUD, not content presence.
- **image_ref column is a string, not a FK**: image storage is deferred to Track P phase 295 (failure photo library). Accepted — saves premature commitment to storage backend.
- **Year-range with NULL**: "universal" resources (e.g., a general troubleshooting video) have year_start IS NULL. Filter needs to handle this explicitly.
- **Track P may need additional columns**: that's fine — Track P phases can run their own migrations. Phase 117's job is the baseline schema.
