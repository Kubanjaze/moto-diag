# MotoDiag Phase 119 — Media Annotation Layer (Photo)

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-04-17

## Goal
Extend `src/motodiag/media/` with a persistent photo-annotation layer that Track Q phase 307 (Photo annotation) will consume. New `photo_annotations` table + `AnnotationShape` enum + `PhotoAnnotation` Pydantic model + repo functions covering shape-based annotations (circles, arrows, rectangles, text labels) on arbitrary images. Distinct from Phase 105's in-memory video annotation (timestamp-based) — this is coordinate-based, shape-based, and persistent. Images themselves remain external (filesystem, Phase 117 `failure_photos.image_ref`, or S3) — this layer only stores metadata about annotations.

CLI: `python -m pytest tests/test_phase119_photo_annotation.py -v`

Outputs: `media/photo_annotation.py`, `media/photo_annotation_repo.py`, migration 012, ~25 tests

## Logic
1. **Migration 012** — 1 new table:
   - `photo_annotations` — id, image_ref (text key linking to any image — may match failure_photos.image_ref), failure_photo_id (FK failure_photos nullable ON DELETE CASCADE), shape (enum: circle/rectangle/arrow/text), x, y (top-left or start coords, normalized 0.0–1.0), width, height (for rectangle/circle — normalized 0.0–1.0; for arrow: dx/dy vector), text (for text shape or label on any shape), color (hex string e.g. '#FF0000'), stroke_width (pixels at render time), label (optional short caption), created_by_user_id (FK users DEFAULT 1), created_at, updated_at
   - 3 indexes: `image_ref`, `failure_photo_id`, `created_by_user_id`
   - Rollback drops the table

2. **`media/photo_annotation.py`** (new module):
   - `AnnotationShape` enum: CIRCLE, RECTANGLE, ARROW, TEXT
   - `PhotoAnnotation` Pydantic model — 12 fields, coords normalized 0.0–1.0 so annotations survive image resize/crop
   - Validators: `x`/`y` must be in [0.0, 1.0]; `width`/`height` in (0.0, 1.0]; `color` must match `#RRGGBB`

3. **`media/photo_annotation_repo.py`** — 8 functions:
   - `add_annotation`, `get_annotation`, `list_annotations_for_image(image_ref)` (ordered by created_at), `list_annotations_for_failure_photo(photo_id)`, `update_annotation`, `delete_annotation`
   - `count_annotations_for_image(image_ref)`, `bulk_import_annotations(annotations)` — for Track Q when rehydrating from a saved session

4. **`media/__init__.py`** — export new public API without breaking existing `Annotation` video class.

5. **`database.py`**: `SCHEMA_VERSION` 11 → 12.

## Key Concepts
- **Coordinate normalization**: x/y/width/height stored as floats 0.0–1.0 of image dimensions. Image at 1920×1080 with annotation at (0.5, 0.25) renders at pixel (960, 270). Means annotations survive image resize or display-device pixel density differences.
- **Arrow shape convention**: (x, y) = tail start, (x+width, y+height) = head end. `width`/`height` can be negative to draw arrows pointing any direction.
- **Text shape convention**: (x, y) = baseline-left anchor of text. `text` field holds the string. `width`/`height` ignored at storage (renderer computes bounding box from font metrics).
- **Image identity**: `image_ref` is an opaque string — same one used in Phase 117 `failure_photos.image_ref`. Annotations can attach to any image by ref even if there's no failure_photo row. Optional `failure_photo_id` FK gives direct DB linkage when the image is a failure photo.
- **Cascade**: Deleting a failure_photo cascades its annotations (ON DELETE CASCADE). Annotations on standalone images (image_ref only, no FK) survive — they're orphan-safe.
- **Color format validation**: enforce `#RRGGBB` uppercase hex. Phase 119 does not support alpha channel — if Track Q needs transparency later, extend to `#RRGGBBAA`.
- **No image rendering in Phase 119**: we store metadata only. Track Q phase 307 builds the actual canvas overlay — could be Pillow, JS canvas, React Native Skia, etc. Phase 119 is storage-agnostic.

## Verification Checklist
- [ ] Migration 012 creates photo_annotations table with correct schema
- [ ] 3 indexes created (image_ref, failure_photo_id, created_by_user_id)
- [ ] AnnotationShape enum has 4 members
- [ ] PhotoAnnotation model validates correctly
- [ ] Coord validators reject out-of-range values (x < 0, y > 1, etc.)
- [ ] Color validator rejects invalid hex strings
- [ ] add_annotation → get_annotation round trip
- [ ] list_annotations_for_image returns annotations in created_at order
- [ ] list_annotations_for_failure_photo filters by FK
- [ ] count_annotations_for_image returns accurate count
- [ ] update_annotation supports partial updates
- [ ] bulk_import_annotations inserts multiple records
- [ ] FK CASCADE: deleting failure_photo cascades its annotations
- [ ] Orphan annotations (image_ref only, no FK) survive failure_photo delete
- [ ] created_by_user_id defaults to system user (id=1)
- [ ] Rollback drops table cleanly
- [ ] Schema version assertions use `>=` (forward-compat)
- [ ] All 1932 existing tests still pass (zero regressions)

## Risks
- **Image dimensions not stored**: coords are normalized, but rendering needs actual image dimensions. Accepted — dimensions come from the image itself (or failure_photos metadata in Track Q 295). Keeps Phase 119 storage-pure.
- **No layering/z-order**: annotations render in `created_at` order; no explicit `z_index` field. If Track Q 307 needs layering, add column then.
- **Text font not specified**: renderer chooses font. Accepted — platform-specific concern.
- **Color validation is strict `#RRGGBB`**: rejects `rgb(255, 0, 0)` or named colors. Trade-off for consistent storage format.
