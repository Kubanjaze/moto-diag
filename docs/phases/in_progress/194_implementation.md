# Phase 194 — Camera + Photo Integration (mobile, substrate)

**Version:** 1.0 (plan) | **Tier:** Standard | **Date:** 2026-05-06

## Goal

Ship the **substrate half** of a substrate-then-feature pair (Phase 194 capture/attach/display + Phase 194B AI photo analysis). Mechanics tap "Take photo" inside a work order, the camera opens, they capture a photo, classify it as `before / after / general / decide later`, the photo uploads, and it appears in the work-order detail screen as a new section variant. Paired before/after photos render side-by-side; general photos render below; un-classified photos surface a "classify later" affordance the mechanic can reach from the WO detail screen at any time.

This phase is **mobile-heavy + visually-heavy** with a tight backend sliver (one new table + one new route + one new repo). Backend reuses Phase 191B's multipart-upload + per-X quotas + storage-convention pattern; mobile reuses Phase 191's `react-native-vision-camera` integration via the same `<Camera>` component (no new dep). The architectural reuse-vs-parallel discipline is held: reuse the patterns, ship parallel resources where the scope genuinely differs.

CLI: no new CLI surface (mobile-only feature with backend support).

Outputs:
- **Backend** (1 commit): new migration creating `work_order_photos` table + new repo module + new `POST /v1/shop/{shop_id}/work-orders/{wo_id}/photos` route (with optional `issue_id` body field per Section A flexibility). Substrate-anticipates-feature: ship `analysis_state TEXT NULL` + `analysis_findings JSON NULL` columns from this migration even though Phase 194 never writes them (mirrors Phase 191's videos table preparing for 191B).
- **Mobile** (2 commits): `useWorkOrderPhotos` hook + `PhotoCaptureScreen` + `photoStorageCache` service + `photoCaptureMachine` reducer (4-state) + `WorkOrderPhotosSection` discriminated-union variant addition (the load-bearing test of Phase 193's forward-look commitment) + entry-point button on WO detail's issues section + nav wiring + smoke gate + finalize.

## Architectural commitment — image-pipeline normalization (Section K)

**Phase 194 ships a single canonical photo storage format**: backend decodes HEIC → JPEG, normalizes EXIF orientation to upright pixels (strips + rotates), resizes to 2048px long-edge bound, encodes at JPEG quality 85.

**Why this matters as substrate-time work**: each consumer that has to honor EXIF orientation independently is drift risk (the canonical "why are all my photos sideways" smoke-gate finding). Phase 194 has 1 consumer today (mobile `WorkOrderPhotosSection`); Phase 194B will add a 2nd (AI analysis pipeline); Phase 192B+ may add a 3rd (PDF report integration). Building the pipeline at substrate time is small; retrofitting after 3 consumers exist is painful and produces inconsistencies.

**Trade-off accepted**: lossy transformation. Original capture is not preserved; what's stored is the canonical form. Phase 194B's AI analysis can re-litigate the storage policy IF it discovers original-pixel access matters (e.g., edge detection tasks where JPEG compression artifacts confuse the model). Default for 194: store the canonical form.

## Architectural commitment — uniform display, source-agnostic UI (per Phase 193's posture, extended)

Phase 194 displays photos uniformly regardless of capture source. Whether the mechanic captured the photo via the in-app camera (this phase) OR Phase 196's OBD-triggered photo capture (future) OR Phase 195's voice-narrated photo annotation (future) — the storage shape, the section variant, and the rendering treat them identically. Source-tracking is deferred until a future phase argues it's load-bearing (per F30 telemetry deferral pattern). Substrate-anticipates-feature: leave the data shape open to provenance via an optional `source` column NULL by default; future phases populate when they ship.

## Logic

### F33 audit (per CLAUDE.md Step 0, dual-direction)

Audit ran 2026-05-06 BEFORE plan v1.0 was written. Greps documented in pre-plan-Q&A; key findings folded inline below.

**Backend findings** — Phase 191B's `src/motodiag/api/routes/videos.py` (388 LoC) ships the canonical multipart-upload + per-X quotas + storage-convention pattern. Photo route reuses the architectural shape but ships a parallel resource (different scope: WO-level rather than session-level). Existing `failure_photos` table is content-library KB (NOT applicable); existing `photo_annotation.py` + `photo_annotation_repo.py` scope to KB imagery (NOT applicable for per-WO uploads). Storage convention: `{data_dir}/photos/shop_{shop_id}/work_order_{wo_id}/{photo_id}.jpg` mirrors video storage layout.

**Mobile findings** — `react-native-vision-camera@4.7.3` already installed (Phase 191); supports `Camera.takePhoto()` natively; **NO new dependency**. `useCameraPermissions` reusable as-is. `useSessionVideos` is a direct template for the photo equivalent. `videoStorageCache` is a direct template for `photoStorageCache`. `VideoCaptureScreen` is a direct template for `PhotoCaptureScreen` (simpler, no recording state). `videoCaptureMachine` reducer pattern reusable with simpler 4-state shape. `formatFileSize` helper reusable verbatim.

**F33 verdict**: substantial reuse on both stacks. Phase 194 is mobile-heavy + visually-heavy with a tight backend sliver. NO new mobile dep; NO new backend dep.

### Backend Commit 0 — `work_order_photos` table + upload route + repo

1. **Migration**: `version=N+1, name="work_order_photos"`. Schema:
   ```sql
   CREATE TABLE work_order_photos (
       id INTEGER PRIMARY KEY AUTOINCREMENT,
       work_order_id INTEGER NOT NULL,
       issue_id INTEGER,                    -- nullable (Section A flexibility)
       role TEXT NOT NULL DEFAULT 'general'
           CHECK (role IN ('before', 'after', 'general', 'undecided')),
       pair_id INTEGER,                     -- self-FK to the matching photo
       file_path TEXT NOT NULL,
       file_size_bytes INTEGER NOT NULL,
       width INTEGER NOT NULL,
       height INTEGER NOT NULL,
       sha256 TEXT NOT NULL,
       captured_at TIMESTAMP NOT NULL,
       uploaded_by_user_id INTEGER NOT NULL,
       -- Substrate-anticipates-feature for Phase 194B (analysis):
       analysis_state TEXT,                 -- NULL until 194B fills
       analysis_findings TEXT,              -- JSON, NULL until 194B fills
       -- Future-look for source provenance (per Phase 193 posture):
       source TEXT,                         -- NULL until a future phase populates
       created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
       updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
       FOREIGN KEY (work_order_id) REFERENCES work_orders(id) ON DELETE CASCADE,
       FOREIGN KEY (issue_id) REFERENCES issues(id) ON DELETE SET NULL,
       FOREIGN KEY (pair_id) REFERENCES work_order_photos(id) ON DELETE SET NULL,
       FOREIGN KEY (uploaded_by_user_id) REFERENCES users(id) ON DELETE SET DEFAULT
   );
   CREATE INDEX idx_wo_photos_wo ON work_order_photos(work_order_id);
   CREATE INDEX idx_wo_photos_issue ON work_order_photos(issue_id);
   CREATE INDEX idx_wo_photos_pair ON work_order_photos(pair_id);
   ```
   Rollback: drop indexes + drop table.

2. **Repo**: `src/motodiag/shop/wo_photo_repo.py` with `create_wo_photo`, `get_wo_photo`, `list_wo_photos(wo_id)`, `list_issue_photos(issue_id)`, `update_pairing(photo_id, pair_id, role)`, `delete_wo_photo(photo_id)`. Mirrors `video_repo.py` shape. Owner-aware via shop membership check at the route layer.

3. **Image pipeline** (Section K): `src/motodiag/media/photo_pipeline.py` with `normalize_photo(raw_bytes) -> (jpeg_bytes, width, height)`. Uses Pillow (already a transitive dep via reportlab; verify). Steps: (1) decode raw bytes (handles HEIC via Pillow-HEIF if installed; fall back to error if HEIC arrives without Pillow-HEIF); (2) read EXIF orientation tag, rotate pixels to upright, strip EXIF; (3) resize to 2048px long-edge bound preserving aspect ratio; (4) encode JPEG quality 85. Pure function — testable without route harness.

4. **Route**: `POST /v1/shop/{shop_id}/work-orders/{wo_id}/photos` with multipart body:
   - `file: UploadFile` (image bytes)
   - `metadata: str` (JSON-encoded `{role, issue_id, pair_id, captured_at}` per Phase 191B's video metadata pattern)
   - Same auth posture as Phase 193 transition endpoint (`require_shop_access` basic membership check) + `require_tier('shop')` for upload.
   - Returns 201 with the new `WorkOrderPhotoResponse` row.
   - Per-WO quota: 30 photos. Per-issue quota: 10 photos (when `issue_id` is set). Per-tier monthly: TBD at build time (likely shop=500/mo, company=unlimited; mirrors video quota structure but tighter since photos are smaller).
   - Image-pipeline normalization runs synchronously inside the route handler (it's fast for 2048px long-edge JPEG; sub-second for typical mobile camera output). NOT a background task — caller wants the upload result immediately.

5. **Tests**: `test_phase194_commit0_photo_upload.py` covering happy path (capture → upload → 201 with normalized JPEG response), per-WO quota enforcement, per-issue quota enforcement, role validation (CHECK constraint), pair_id self-FK enforcement (can't pair to non-existent photo), 401/402/403 auth boundary, cross-shop 404, EXIF rotation correctness (input with EXIF orientation=6 → output rotated upright), HEIC decoding (if Pillow-HEIF available; skip with marker if not), resize bound (input 4000×3000 → output 2048×1536), JPEG-quality round-trip.

### Mobile Commit 1 — hooks + capture screen + storage cache + section variant

1. **`src/types/workOrder.ts` extension**: add `WorkOrderPhotosSection` variant + `isPhotosSection` type guard. Extend the discriminated union from 5 → 6 variants.
   ```ts
   export interface WorkOrderPhotosSection {
     kind: 'photos';
     photos: WorkOrderPhoto[];   // grouped + ordered for rendering
     undecided_count: number;    // surfaced in "X photos waiting to be classified" affordance
   }
   export interface WorkOrderPhoto {
     id: number;
     issue_id: number | null;
     role: 'before' | 'after' | 'general' | 'undecided';
     pair_id: number | null;
     file_path: string;          // backend-relative; mobile resolves via streaming endpoint
     width: number;
     height: number;
     captured_at: string;
   }
   ```

2. **`src/screens/buildWorkOrderSections.ts` extension**: add photos branch. **Anticipated friction (Section E)**: photos are media-references-with-relationship-data, structurally different from text-shaped rows/bullets/body/issues variants. The builder may need to be made more general about variant shapes (NOT deform photo data to fit text-shape per F9-discipline). If friction surfaces, plan v1.1 amendment slot reserved.

3. **`src/components/WorkOrderSectionCard.tsx` extension**: add `_renderPhotos` branch. Pairs render side-by-side with "Before / After" labels. Standalones render in a grid below. Undecided photos surface as a sticky banner: "X photos waiting to be classified — tap to review."

4. **`src/services/photoStorageCache.ts`**: mirror of `videoStorageCache.ts`. Canonical path `${RNFS.DocumentDirectoryPath}/photos/p-{photoId}.jpg`. **Refinement per Section F**: 7-day cold-start sweep for captured-but-never-uploaded orphans (longer than share-temp's 24h since capture is more deliberate; bounded so orphans don't accumulate forever). `cleanupOldPhotos(now)` mirrors `cleanupOldShares` shape.

5. **`src/screens/photoCaptureMachine.ts`**: 4-state reducer. States: `idle | previewing | uploading | uploaded | upload-failed`. Events: `CAPTURED(uri, meta)` → previewing; `CONFIRM_UPLOAD(role, pair_id?)` → uploading; `UPLOAD_SUCCEEDED(photo)` → uploaded; `UPLOAD_FAILED(error)` → upload-failed; `RETAKE` → idle; `RETRY_UPLOAD` → uploading.

6. **`src/screens/PhotoCaptureScreen.tsx`**: mirrors `VideoCaptureScreen.tsx` simpler. Uses `useCameraPermissions` (camera-only; mic-perm not strictly needed but harmless reuse). **Capture-time classification UX (Section D refinement)**: 4-button affordance after capture confirms — `Before / After / General / Decide later`. "Decide later" maps to backend `role='undecided'` + immediate upload. Post-capture re-classification surface lives in the WorkOrderPhotosSection (Mobile Commit 2).

7. **`src/hooks/useWorkOrderPhotos.ts`**: backend-backed photo CRUD. Returns `{photos, isLoading, error, refetch, addPhoto, repair, deletePhoto}`. `addPhoto(file, meta)` does multipart POST to `/v1/shop/{shop_id}/work-orders/{wo_id}/photos`. `repair(photoId, {role, pair_id})` PATCH-equivalent (separate route or same upload route's body — pin at build time). Typed errors via `ShopAccessError` 5-kind union (Section H reuse).

8. **`src/hooks/useUndecidedPhotos.ts` (helper)**: filters the photo list to `role='undecided'` for the section banner + "Classify later" surface.

9. **Tests**: 5 new test files. Pure-logic for `photoCaptureMachine` reducer (state transitions + edge cases) + `photoStorageCache` (lookup/adopt/evict/cleanupOldPhotos with 7-day boundary). Hook tests for `useWorkOrderPhotos` mirroring `useSessionVideos` patterns. Type-guard test for `isPhotosSection`. `buildWorkOrderSections` extension test verifying photos variant slots in correctly + omit-when-empty + WO+issue grouping.

### Mobile Commit 2 — entry-point + classify-later surface + nav + smoke gate + finalize

1. **Entry-point button**: on `WorkOrderDetailScreen`, in the issues section (or a dedicated photos action card), surface "Take photo" button(s). Tapping navigates to `PhotoCaptureScreen` with `{shopId, woId, issue_id?}` route params.

2. **Classify-later surface**: when a photo is captured with `role='undecided'`, the WorkOrderPhotosSection banner ("X photos waiting to be classified") taps to a modal/screen that shows undecided photos one-at-a-time + lets the mechanic pick `before/after/general` AND optionally select a pair (if picking `after`, picker shows existing `before` photos for the same WO/issue).

3. **Nav wiring**: `PhotoCaptureScreen` registered in `ShopStack` with `{shopId: number, woId: number, issueId?: number}` params.

4. **8-step smoke gate** (Section J):
   1. Tap "Take photo" → camera permission flow → preview → capture → classify (Before/After/General/Decide later) → upload → photo appears in WorkOrderPhotosSection.
   2. Capture before-photo (role=before) → save → capture after-photo (role=after, picker selects matching before) → pair appears side-by-side.
   3. Capture standalone photo (role=general) → renders in grid below pairs.
   4. Capture with role=undecided → "X photos waiting" banner appears → tap → re-classification flow → photo moves to its proper bucket.
   5. Free-tier user → 402 with informational copy (no upgrade-action affordance per subscription audit precedent).
   6. Cross-shop deep-link → 403.
   7. Permanently-denied permission → settings link affordance (mirrors Phase 191B).
   8. **WorkOrderSection variant integration smoke**: photos variant renders alongside vehicle / customer / issues / notes / lifecycle without breaking existing variants. Pin Phase 193's substrate held; if friction surfaced during Mobile Commit 1's `buildWorkOrderSections` extension, that's the plan v1.1 amendment trigger.

5. **F-ticket dispositions at finalize**:
   - F33 audit ran first per CLAUDE.md Step 0 — substantial reuse confirmed; no surprises.
   - F36 (member workload counts): orthogonal to 194; reaffirm deferred.
   - F37 (extend F33 to enum-value verification): track during execution per Section I; if Phase 194's build surfaces an enum mismatch (e.g., backend `role` enum vs mobile typed union drift), that's instance #3 and triggers F37 escalation. Don't expand 194 scope.
   - F38 candidate (TBD at build time): if `quota_exceeded` UI copy distinctness becomes load-bearing during smoke gate, file as F38 candidate with promotion trigger (instance #2 escalates) — don't manufacture a 6th `ShopAccessError` kind in 194.

## Key Concepts

- **Reuse-vs-parallel discipline**: mobile reuses Phase 191's `react-native-vision-camera` integration directly (one Camera component, one permissions hook, one storage-cache pattern). Backend reuses Phase 191B's upload-route SHAPE but ships a parallel route + table for the WO scope (different resource, identical pattern). F9-discipline holds: reuse the ARCHITECTURE; parallel implementations only when the resource truly differs.
- **`work_order_photos` flexible-scope schema**: `work_order_id NOT NULL` + `issue_id` nullable. Mechanic can photograph WO-overall ("intake baseline" / "insurance documentation") OR photograph specific issue. UX classifies; data model accommodates.
- **`role` enum + `pair_id` self-FK**: pairing model from Section D (p). Roles: `before | after | general | undecided`. `undecided` is the fast-path "decide later" affordance.
- **At-capture + post-capture pairing**: 4-button capture-time affordance + post-capture re-classification surface in WorkOrderPhotosSection. Both paths always available; capture-time is fast-path, post-capture is recovery + bulk-classify.
- **Image-pipeline normalization (Section K)**: backend decodes HEIC → JPEG, normalizes EXIF orientation to upright, resizes to 2048px long-edge, encodes at JPEG quality 85. Single canonical storage format. Lossy trade-off accepted (Phase 194B can re-litigate if AI analysis needs originals).
- **`WorkOrderPhotosSection` discriminated-union variant**: 6th variant added to Phase 193's WorkOrderSection union. **Load-bearing test of the forward-look commitment**: photos are structurally different from text-shaped variants; if `buildWorkOrderSections` or `WorkOrderSectionCard` need refinement to accommodate, surface as architectural finding (plan v1.1 amendment slot reserved) NOT silent workaround.
- **Substrate-anticipates-feature for Phase 194B**: ship `analysis_state TEXT NULL` + `analysis_findings JSON NULL` columns from Phase 194's migration even though 194 never writes them. Mirrors Phase 191's videos table preparing for 191B.
- **7-day cold-start sweep for captured-but-never-uploaded orphans**: longer than share-temp's 24h since capture is more deliberate; bounded so orphans don't accumulate.
- **`ShopAccessError` reuse, no parallel typed-error**: photo-upload failures classify identically to other shop-scoped failures. If `quota_exceeded` distinct copy becomes load-bearing, file F38 candidate with promotion trigger (instance #2 escalates).

## Verification Checklist

- [ ] Backend migration creates `work_order_photos` table with all listed columns + 3 indexes + correct FK cascade rules.
- [ ] Backend `wo_photo_repo.py` ships `create_wo_photo` / `get_wo_photo` / `list_wo_photos(wo_id)` / `list_issue_photos(issue_id)` / `update_pairing(photo_id, pair_id, role)` / `delete_wo_photo(photo_id)`.
- [ ] Backend `photo_pipeline.normalize_photo` handles HEIC → JPEG, EXIF rotation, resize to 2048px long-edge, JPEG quality 85.
- [ ] Backend `POST /v1/shop/{shop_id}/work-orders/{wo_id}/photos` route accepts multipart `(file, metadata)`, normalizes via pipeline, stores at canonical path, returns 201.
- [ ] Backend per-WO + per-issue quota enforcement.
- [ ] Backend role CHECK constraint + pair_id self-FK enforcement.
- [ ] Backend 401/402/403/404 auth boundary tests pass.
- [ ] Backend EXIF rotation correctness test (orientation=6 input → upright output).
- [ ] Mobile `useWorkOrderPhotos` hook returns `{photos, isLoading, error, refetch, addPhoto, repair, deletePhoto}` with `ShopAccessError` typed errors.
- [ ] Mobile `useCameraPermissions` reused as-is (no fork).
- [ ] Mobile `photoCaptureMachine` 4-state reducer covers all transitions + edge cases.
- [ ] Mobile `photoStorageCache` mirrors `videoStorageCache` shape; 7-day cold-start sweep wired into App.tsx useEffect.
- [ ] Mobile `PhotoCaptureScreen` reuses `<Camera>` + permissions hook; 4-button classify affordance (`Before / After / General / Decide later`).
- [ ] Mobile `WorkOrderPhotosSection` variant added to discriminated union; type guard `isPhotosSection` + builder branch + renderer branch all wired.
- [ ] Mobile renderer: pairs side-by-side; standalones in grid; undecided banner with classify-later affordance.
- [ ] Mobile post-capture re-classification surface lets mechanic move undecided photos to before/after/general + select pair.
- [ ] All 8 architect-smoke steps documented; Steps 1-7 hook + helper unit tests; Step 8 (variant integration) concretely tested via WorkOrderSectionCard smoke test.
- [ ] All doc + package version bumps recorded.
- [ ] F-ticket dispositions: F37 watching during execution; F38 candidate filed iff `quota_exceeded` distinctness surfaces.

## Risks

- **Pillow-HEIF availability**: HEIC decoding requires `pillow-heif` Python package. Verify at backend Commit 0 build time; if not installed, install + verify version compat (similar to Phase 191B's ffmpeg subprocess wrapper that gracefully degrades). Mitigation: if HEIC handling has install friction, ship Phase 194 with JPEG-only on iOS (vision-camera can capture as JPEG via codec setting) + file F-ticket for HEIC support.
- **`buildWorkOrderSections` extension friction (Section E)**: photos are structurally different from text-shaped variants. If the builder needs refactoring to accommodate, surface as architectural finding NOT silent workaround. Plan v1.1 amendment slot reserved.
- **Image-pipeline performance at upload time**: synchronous normalization in the route handler. Sub-second for 2048px long-edge JPEG output is the assumption; verify on first build. If consistently >1s, move to background-task pattern (mirrors Phase 191B's video analysis queue) — but background-tasking the upload-time normalization changes the response shape (caller doesn't get final photo immediately). Defer this concern to plan v1.1 amendment IF the synchronous version proves slow.
- **Pair_id ON DELETE SET NULL leaves orphan refs**: deleting a photo that another references via pair_id sets the orphan's `pair_id = NULL`. Acceptable trade-off — orphan photo is then standalone or remains classified per its `role` field. Alternative was CASCADE (deleting "before" deletes "after" too), which is more destructive than mechanics expect.
- **Quota structure (per-WO 30 / per-issue 10) is a guess**: real-world usage may need adjustment after Phase 194 ships. Mitigation: log quota-exceeded events server-side; revisit in a follow-up phase if numbers feel wrong.
- **F37 instance #3 watching**: Phase 194's role enum (`before | after | general | undecided`) is backend-defined. Mobile types it as a Literal union. If a mismatch surfaces (e.g., Pydantic CHECK rejects a role mobile sent), that's instance #3 and triggers F37 escalation. NOT load-bearing for 194 if caught at build; surface as plan v1.0.X amendment.
- **`react-native-vision-camera` photo capture compat with RN 0.85**: lib supports `takePhoto()` per the type definitions; smoke-gate Step 1 verifies on device. If a regression surfaces, file F-ticket + revert to fallback (e.g., react-native-image-picker as compat substrate).
- **Section D "decide later" ergonomics**: post-capture classification surface MUST be discoverable. Mitigation: undecided banner is sticky on WorkOrderPhotosSection until count==0. Smoke gate Step 4 pins the discoverability + the bulk-classify flow.
