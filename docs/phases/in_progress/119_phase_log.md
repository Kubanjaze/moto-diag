# MotoDiag Phase 119 — Phase Log

**Status:** 🔄 In Progress | **Started:** 2026-04-17 | **Completed:** —
**Repo:** https://github.com/Kubanjaze/moto-diag

---

### 2026-04-17 19:40 — Plan written, v1.0
Media annotation layer — photo edition. Migration 012 adds `photo_annotations` table (coordinate-based, normalized 0.0–1.0 floats). New `media/photo_annotation.py` module: AnnotationShape enum (circle/rectangle/arrow/text), PhotoAnnotation Pydantic model with coord + hex color validators. New `media/photo_annotation_repo.py`: 8 functions (CRUD + list-by-image + list-by-failure-photo + count + bulk_import). Optional FK to failure_photos with CASCADE; orphan annotations (image_ref only) survive. Substrate for Track Q phase 307.
