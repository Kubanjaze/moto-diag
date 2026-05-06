# Phase 194 — Phase Log

**Status:** 🚧 In Progress | **Started:** 2026-05-06
**Repo:** https://github.com/Kubanjaze/moto-diag (backend) + https://github.com/Kubanjaze/moto-diag-mobile (mobile)
**Branch:** `phase-194-camera-photo-integration` (will be created BOTH repos at plan-push)

---

### 2026-05-06 06:55 — Plan v1.0 written

Phase 194 opens as the **substrate half** of a substrate-then-feature pair (194 capture/attach/display + 194B AI photo analysis). Mobile-heavy + visually-heavy phase with a tight backend sliver (1 migration + 1 route + 1 repo).

**F33 audit ran BEFORE plan write** (CLAUDE.md Step 0, dual-direction per Kerwyn's pre-dispatch reminder). Findings folded into plan v1.0 inline.

**Backend audit findings**:
- Phase 191B's `src/motodiag/api/routes/videos.py` (388 LoC) — canonical multipart-upload + per-X quotas + storage-convention pattern. Photo route reuses architectural shape; ships parallel resource (different scope: WO-level rather than session-level).
- `failure_photos` table EXISTS (~Phase 119) — but it's content-library KB (failure imagery tied to make/model/year), NOT applicable to per-WO mechanic uploads. Coexists.
- `photo_annotation.py` + `photo_annotation_repo.py` exist (Phase 119 retrofit) — scope to KB imagery via `failure_photo_id`. NOT directly applicable for Phase 194's per-WO photos. Defer generalization.
- `motodiag/media/` package has video-analysis pipeline (vision_analysis_pipeline.py, analysis_worker.py) — directly reusable for Phase 194B if/when it ships.
- Storage convention: `{data_dir}/photos/shop_{shop_id}/work_order_{wo_id}/{photo_id}.jpg` mirrors video storage layout exactly.

**Mobile audit findings**:
- `react-native-vision-camera@4.7.3` already installed (Phase 191) — supports `Camera.takePhoto()` natively. **NO new dependency.**
- `useCameraPermissions` reusable as-is (mic-perm not strictly needed for photos but harmless).
- `useSessionVideos` is a direct template for `useWorkOrderPhotos`.
- `videoStorageCache` is a direct template for `photoStorageCache`.
- `VideoCaptureScreen` is a direct template for `PhotoCaptureScreen` (simpler, no recording state).
- `videoCaptureMachine` reducer pattern reusable with simpler 4-state shape (vs videos' 5).
- `WorkOrderSection` discriminated union (Phase 193 substrate) — Phase 194 is the FIRST variant addition; load-bearing test of the forward-look commitment.

**F33 verdict**: substantial reuse on both stacks. Mobile-heavy + visually-heavy phase. NO new dep on either side.

**Pre-plan Q&A architect-side** (no Plan agent dispatched per Kerwyn's discipline). 10 sections + 1 cross-cutting addition (Section K, NEW). All locked with picks + refinements:

- **A**: (c) flexible scope. `work_order_photos` table with `work_order_id NOT NULL` + `issue_id` nullable. UX classifies; data model accommodates. Push-back from initial (b) per-issue lean — natural workflow is see → capture → classify, not classify → see → capture.
- **B**: (β) parallel route reusing pattern. Route shape: `POST /v1/shop/{shop_id}/work-orders/{wo_id}/photos` with optional `issue_id` body field.
- **C**: (II) substrate-feature split. Phase 194 = capture/attach/display. Phase 194B = AI analysis. Substrate-anticipates-feature: ship `analysis_state TEXT NULL` + `analysis_findings JSON NULL` from Phase 194's migration.
- **D**: (p) data shape (independent rows + nullable `pair_id` self-FK + `role` enum). Pairing UX is at-capture optional fast-path + post-capture re-classification always available. 4-button capture-time affordance: `Before / After / General / Decide later`. `Decide later` maps to backend `role='undecided'`.
- **E**: variant integration is the load-bearing test of Phase 193's forward-look commitment. Anticipated friction: photos are media-references-with-relationship-data, structurally different from text-shaped variants. If `buildWorkOrderSections` breaks, fix by making the function more general about variant shapes (NOT deform photo data to fit text-shape — F9-discipline). Plan v1.1 amendment slot reserved.
- **F**: (I) DocumentDirectoryPath. 7-day cold-start sweep for captured-but-never-uploaded orphans.
- **G**: 4-state machine. `idle | previewing | uploading | uploaded | upload-failed`.
- **H**: Reuse `ShopAccessError` 5-kind union as-is. F38 candidate if `quota_exceeded` distinctness becomes load-bearing (instance #2 escalates).
- **I**: F37 watching during execution; no scope expansion.
- **J**: 3-commit cadence. Backend Commit 0 commit message documents F33 audit findings inline (audit-trail-preservation discipline).
- **K (NEW)**: Image pipeline — backend decodes HEIC → JPEG, normalizes EXIF orientation to upright, resizes to 2048px long-edge, encodes at JPEG quality 85. Single canonical storage format. Trade-off: lossy. Phase 194B can re-litigate IF AI analysis needs originals.

**Phase 194 explicitly NOT taking on**:
- AI photo analysis (deferred to Phase 194B per Section C).
- Photo annotation overlay UI (Phase 119's photo_annotation_repo lives for KB imagery; eventual generalization is its own phase).
- Subscription upgrade flow (no audit-confirmed UI exists; not 194's concern).
- Video / photo unified surface (separate concerns; coexist).
- Issue creation flow (Phase 162 surfaces; deferred to its own mobile phase).

**Risks at plan-write time** (full set in implementation.md):
1. Pillow-HEIF availability — verify at backend Commit 0 build time.
2. `buildWorkOrderSections` extension friction (Section E load-bearing test).
3. Image-pipeline performance at upload time (synchronous normalization assumption).
4. Pair_id ON DELETE SET NULL leaves orphan refs (acceptable trade-off; alternative CASCADE more destructive).
5. Quota structure (per-WO 30 / per-issue 10) is a guess — revisit if usage feels wrong.
6. F37 instance #3 watching — Phase 194's role enum is candidate.
7. `react-native-vision-camera` photo capture compat with RN 0.85.
8. Section D "decide later" ergonomics — undecided banner discoverability.

**Next step**: create `phase-194-camera-photo-integration` branch on both repos, push plan v1.0 (this commit), then begin Backend Commit 0 (migration + route + repo + image pipeline + tests).
