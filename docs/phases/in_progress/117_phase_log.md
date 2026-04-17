# MotoDiag Phase 117 — Phase Log

**Status:** 🔄 In Progress | **Started:** 2026-04-17 | **Completed:** —
**Repo:** https://github.com/Kubanjaze/moto-diag

---

### 2026-04-17 18:00 — Plan written, v1.0
Reference data substrate. Migration 010 creates 4 empty tables: `manual_references`, `parts_diagrams`, `failure_photos`, `video_tutorials`. New `src/motodiag/reference/` package: 4 enums (ManualSource, DiagramType, FailureCategory, SkillLevel), 4 Pydantic models, 4 repo modules each with 5 CRUD functions. Year-range targeting reuses known_issues pattern. Track P phases 293-302 populate content.
