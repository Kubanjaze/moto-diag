# MotoDiag Phase 119 — Phase Log

**Status:** ✅ Complete | **Started:** 2026-04-17 | **Completed:** 2026-04-17
**Repo:** https://github.com/Kubanjaze/moto-diag

---

### 2026-04-17 19:40 — Plan written, v1.0
Media annotation layer — photo edition. Migration 012 adds `photo_annotations` table (coordinate-based, normalized 0.0–1.0 floats). New `media/photo_annotation.py` module: AnnotationShape enum (circle/rectangle/arrow/text), PhotoAnnotation Pydantic model with coord + hex color validators. New `media/photo_annotation_repo.py`: 8 functions (CRUD + list-by-image + list-by-failure-photo + count + bulk_import). Optional FK to failure_photos with CASCADE; orphan annotations (image_ref only) survive. Substrate for Track Q phase 307.

### 2026-04-17 20:00 — Build complete
Created `src/motodiag/media/photo_annotation.py` (AnnotationShape enum + PhotoAnnotation model with 3 validators: coord bounds, hex color regex uppercasing to `#FF0000`, size bounds supporting negative arrow deltas) and `src/motodiag/media/photo_annotation_repo.py` (8 functions). Updated `media/__init__.py` to export new public API while preserving Phase 105 video annotation import path.

Migration 012 appended to `migrations.py`: photo_annotations table with 3 indexes, CASCADE on failure_photos FK, SET DEFAULT on users FK. Rollback drops the table. SCHEMA_VERSION bumped 11 → 12.

Phase 119 tests (22) all pass. Full regression: **1954/1954 passing (zero regressions, 9:44 runtime)**. Forward-compat pattern maintained — schema version assertions use `>= 12`.

### 2026-04-17 20:05 — Documentation update
v1.0 → v1.1: all sections updated with as-built state, verification checklist marked `[x]`, Results table added. Two deviations documented: test count 22 vs planned ~25 (tighter validator coverage), and SQL `CURRENT_TIMESTAMP` literal used in update_annotation rather than Python datetime (keeps timestamps on DB clock). Key finding: dual-mode annotation (FK-linked CASCADE + orphan-safe by image_ref) supports both formal failure-photo library workflow AND ad-hoc mechanic notes on phone photos without design compromise.

### 2026-04-17 20:07 — Phase 122 scope locked in (separate follow-on)
Mid-phase, user requested a photo-based bike ID feature (take picture → auto-populate make/model/year). Saved scope + cost envelope to memory; confirmed placement as Phase 122 after Gate R. Out of scope for Phase 119 build — Phase 119 remains the photo annotation substrate as originally planned.
