# MotoDiag Phase 119 — Media Annotation Layer (Photo)

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-17

## Goal
Extend `src/motodiag/media/` with a persistent photo-annotation layer that Track Q phase 307 (Photo annotation) will consume. New `photo_annotations` table + `AnnotationShape` enum + `PhotoAnnotation` Pydantic model + repo functions covering shape-based annotations (circles, rectangles, arrows, text labels) on arbitrary images. Distinct from Phase 105's in-memory video annotation (timestamp-based) — this is coordinate-based, shape-based, and persistent. Images themselves remain external (filesystem, Phase 117 `failure_photos.image_ref`, or S3) — this layer only stores metadata about annotations.

CLI: `python -m pytest tests/test_phase119_photo_annotation.py -v`

Outputs: `media/photo_annotation.py`, `media/photo_annotation_repo.py`, `media/__init__.py` (re-exports), migration 012, 22 tests

## Logic
1. **Migration 012** — 1 new table:
   - `photo_annotations` — id, image_ref (text), failure_photo_id (FK failure_photos nullable ON DELETE CASCADE), shape, x, y, width, height (all REAL), text (optional), color (DEFAULT `#FF0000`), stroke_width (DEFAULT 2), label (optional), created_by_user_id (FK users DEFAULT 1, ON DELETE SET DEFAULT), created_at, updated_at
   - 3 indexes: `idx_photo_ann_image` (image_ref), `idx_photo_ann_photo` (failure_photo_id), `idx_photo_ann_user` (created_by_user_id)
   - Rollback drops the table

2. **`media/photo_annotation.py`** (new module):
   - `AnnotationShape` enum: CIRCLE, RECTANGLE, ARROW, TEXT (4 members)
   - `PhotoAnnotation` Pydantic model — 14 fields
   - **Pydantic v2 validators**: `x`/`y` bounded [0.0, 1.0] via `Field(ge=0.0, le=1.0)`; `width`/`height` validator allows **negative values bounded by [-1.0, 1.0]** (arrows point any direction); `color` enforced via regex to `#RRGGBB` (uppercased on assignment); `stroke_width` bounded [1, 32]

3. **`media/photo_annotation_repo.py`** — 8 functions:
   - `add_annotation`, `get_annotation`
   - `list_annotations_for_image(image_ref)` (chronological), `list_annotations_for_failure_photo(failure_photo_id)` (FK-linked only)
   - `count_annotations_for_image(image_ref)`
   - `update_annotation(**fields)` — handles enum serialization + bumps `updated_at` to CURRENT_TIMESTAMP
   - `delete_annotation`
   - `bulk_import_annotations` — for Track Q session rehydration

4. **`media/__init__.py`** — added public API exports for photo annotation (preserved existing module docstring; Phase 105 video `Annotation` stays import-able via `motodiag.media.annotation.Annotation`)

5. **`database.py`**: `SCHEMA_VERSION` 11 → 12.

## Key Concepts
- **Coordinate normalization**: x/y/width/height stored as floats in [0.0, 1.0] (or [-1.0, 1.0] for arrow deltas). Annotations survive image resize, crop, or display-pixel-density differences — a circle at (0.5, 0.25) renders at pixel (960, 270) on a 1920×1080 canvas or (3840, 540) on 4K without re-encoding.
- **Arrow shape convention**: (x, y) = tail start, (x+width, y+height) = head end. Negative width/height = point left/up.
- **Text shape convention**: (x, y) = baseline-left anchor. `text` field holds the string; renderer computes bounding box from font metrics.
- **Image identity**: `image_ref` is opaque — same one used in Phase 117 `failure_photos.image_ref`. Annotations can attach to any image by ref even if there's no failure_photo row. Optional `failure_photo_id` FK gives direct DB linkage when the image IS a failure photo.
- **Cascade semantics**:
  - Annotations with `failure_photo_id` set → ON DELETE CASCADE (delete photo → annotations go with it)
  - Annotations with only `image_ref` (no FK) → orphan-safe, survive any failure_photo deletion
  - This is intentional: mechanic-drawn notes on an ad-hoc phone photo shouldn't evaporate just because the shop's failure_photos library was purged
- **Color format enforced `#RRGGBB`**: rejects `rgb(...)`, named colors, or alpha channel. Phase 119 is storage-pure; rendering happens in Track Q.
- **Updated_at bumped on update**: the SET clause uses SQL literal `CURRENT_TIMESTAMP` rather than binding a Python datetime — keeps timestamp accuracy consistent with the DB clock.

## Verification Checklist
- [x] Migration 012 creates photo_annotations table with correct schema
- [x] 3 indexes created (image_ref, failure_photo_id, created_by_user_id)
- [x] AnnotationShape enum has 4 members
- [x] PhotoAnnotation model validates correctly
- [x] Coord validators reject out-of-range values (x < 0, y > 1)
- [x] Color validator rejects invalid hex strings ("red", rgb(), etc.)
- [x] Size validator rejects width/height > 1.0 or < -1.0
- [x] Negative arrow deltas are accepted (arrow pointing up/left)
- [x] Color uppercased on assignment (`#ff0000` → `#FF0000`)
- [x] add_annotation → get_annotation round trip
- [x] list_annotations_for_image returns annotations in created_at order
- [x] list_annotations_for_failure_photo filters to FK-linked only
- [x] count_annotations_for_image returns accurate count
- [x] update_annotation supports partial updates (including enum shape)
- [x] bulk_import_annotations inserts multiple records
- [x] FK CASCADE: deleting failure_photo cascades its annotations
- [x] Orphan annotations (image_ref only, no FK) survive failure_photo delete
- [x] created_by_user_id defaults to system user (id=1)
- [x] Rollback drops table cleanly
- [x] Schema version assertions use `>= 12` (forward-compat)
- [x] All 1932 existing tests still pass (zero regressions) — full suite 1954/1954 in 9:44

## Risks
- **Image dimensions not stored**: coords are normalized, but rendering needs actual image dimensions. Accepted — dimensions come from the image itself or from `failure_photos` metadata that Track Q 295 will populate. Keeps Phase 119 storage-pure.
- **No explicit z-order**: annotations render in `created_at` order. If Track Q 307 needs layering, add `z_index` column then.
- **Text font not specified**: renderer chooses font. Accepted — platform-specific concern.
- **Color validation is strict `#RRGGBB`**: rejects `rgb(...)`, named colors, alpha. Trade-off for consistent storage format. If Track Q needs transparency, extend to `#RRGGBBAA` in a future migration.

## Deviations from Plan
- Test count 22 vs plan's ~25. Tighter coverage — validator tests are focused and don't need to test every rejected value.
- One implementation detail not in plan: `update_annotation` uses SQL literal `CURRENT_TIMESTAMP` for `updated_at` (rather than Python datetime) to stay consistent with DB clock. Noted in Key Concepts.

## Results
| Metric | Value |
|--------|-------|
| New files | 3 (`media/photo_annotation.py`, `media/photo_annotation_repo.py`, `tests/test_phase119_photo_annotation.py`) |
| Modified files | 3 (`database.py`, `migrations.py`, `media/__init__.py`) |
| New tests | 22 |
| Total tests | 1954 passing (was 1932) |
| New enum | AnnotationShape (4 members) |
| New model | PhotoAnnotation (14 fields, 3 validators) |
| Repo functions | 8 |
| New tables | 1 (photo_annotations) |
| New indexes | 3 |
| Schema version | 11 → 12 |
| Regression status | Zero regressions — full suite 9:44 runtime |

Phase 119 delivers coordinate-normalized, shape-based photo annotation storage. The `image_ref` + optional FK design supports two usage modes: mechanic scribbles on an ad-hoc phone photo (orphan-safe), and formal failure photo library entries (CASCADE-linked). Track Q phase 307 builds the renderer on top — any canvas layer (Pillow, JS canvas, React Native Skia) can consume this metadata with one SELECT.
