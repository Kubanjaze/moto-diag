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

---

### 2026-05-06 07:35 — Backend Commit 0 build complete

Backend sliver landed in commit `71658ac` (10 files, 2033 insertions). Mobile Commits 1, 2 pending.

**What shipped:**

- **Migration 041** (`src/motodiag/core/migrations.py`): `work_order_photos` table — 17 functional columns + `deleted_at` for soft-delete + 4 indexes (wo, issue, pair, sha256). FK posture: `work_orders` CASCADE / `issues` SET NULL / `pair_id` self-FK SET NULL / `users` SET DEFAULT. SCHEMA_VERSION 40 → 41.
- **Image pipeline** (`src/motodiag/media/photo_pipeline.py`): `normalize_photo()` pure function — HEIC decode (pillow-heif registered at module-import; graceful fallback if uninstalled) → `ImageOps.exif_transpose` to upright pixels → strip EXIF → resize to 2048px long-edge bound (LANCZOS, no upscaling) → JPEG quality 85, `optimize=True`. Typed errors `UnsupportedImageFormatError` (415) + `ImageDecodeError` (422).
- **Repo** (`src/motodiag/shop/wo_photo_repo.py`, ~310 LoC): mirrors `video_repo` shape — create/get/list/list_issue/update_pairing/soft_delete + 3 quota helpers (`count_wo_photos`, `count_issue_photos`, `count_wo_photos_this_month_for_uploader`) + `get_wo_photo_for_pairing(photo_id, expected_wo_id)` for partner validation. `_month_start_iso` uses SQLite-compatible space-separator (matches the 2026-05-01 boundary-bug fix from `video_repo`).
- **Route** (`src/motodiag/api/routes/photos.py`, ~440 LoC): 6 endpoints under `/v1/shop/{shop_id}/work-orders/{wo_id}/photos` — POST (upload+normalize, 201), GET (list), GET /{id}, PATCH /{id} (re-classification surface), DELETE /{id} (204 idempotent), GET /{id}/file (stream JPEG). All endpoints layer `require_shop_access` (basic membership check) on top of the tier gate; cross-shop returns 403, cross-WO returns 404. POST mirrors `pair_id` symmetrically (caller specifies from new photo's perspective; route updates partner to point back).
- **Errors mapping** (`src/motodiag/api/errors.py`): 5 new mappings — `WorkOrderPhotoOwnershipError` (404), `WorkOrderPhotoQuotaExceededError` (402), `WorkOrderPhotoPairingError` (422), `UnsupportedImageFormatError` (415), `ImageDecodeError` (422).
- **App wiring** (`src/motodiag/api/app.py`): `photos_router` mounted under `/v1` after `videos_router`.
- **Dependency** (`pyproject.toml`): `pillow-heif>=1.3.0` added to `[vision]` extras (Risk #1 from plan v1.0 cleared at build time — `pillow-heif==1.3.0` installed and verified).
- **Tests** (`tests/test_phase194_commit0_photo_upload.py`, ~700 LoC): 44 tests across 8 classes — TestMigration041 (6) / TestPhotoPipeline (9) / TestWorkOrderPhotoRepo (10) / TestUploadHappyPath (6) / TestUploadAuth (4) / TestUploadQuotas (3) / TestPairingAndErrors (4) / TestQuotaHelperUnit (2). All 44 pass in 43s.

**F9-discipline fixes (cross-test SSOT-pin maintenance):**
- `tests/test_phase192_migration_040.py:104` — relaxed `assert SCHEMA_VERSION == 40` to `>= 40` (matches the next assertion's shape; Phase 192's bump landed and stays as a floor regardless of downstream bumps). This is the F9-family "literal-equality SSOT pin breaks at downstream phase bump" pattern documented in Phase 191C's pattern guide; future phase 195+ won't trip.
- `tests/test_phase194_commit0_photo_upload.py:172` — `assert SCHEMA_VERSION >= 41` with `# f9-noqa: ssot-pin contract-pin: phase-194 floor — verifies migration 041 landed and stays`. Required opt-out per Phase 191D's `--check-ssot-constants` lint rule (one literal is needed for the assertion to be meaningful; opting in via the contract-pin category is the right disposition).

**Versions:**
- `src/motodiag/core/database.py`: `SCHEMA_VERSION` 40 → 41
- `pyproject.toml`: 0.3.6 → 0.4.0 (minor bump — feature addition, new module + new route + new dep)

**Verification:**
- 44/44 Phase 194 Commit 0 tests pass (43s wall time)
- 14/14 Phase 192 migration 040 tests pass after SSOT-pin fix
- 142/142 adjacent-regression (Phase 191B + 192 + 193) green
- F9 lint clean (`scripts/check_f9_patterns.py --check-ssot-constants`)
- All 6 photo routes registered (`{POST, GET, GET, PATCH, DELETE, GET}` over `/v1/shop/{shop_id}/work-orders/{wo_id}/photos[/{photo_id}[/file]]`)
- All 5 photo error mappings registered in errors.py exception chain (52 total mappings)

**F-ticket dispositions during execution:**
- F37 (extend F33 to enum-value verification) — watching during build; **no instance #3 surfaced**. Backend `role` enum `{before, after, general, undecided}` matches the mobile typed-union spec from plan v1.0 verbatim; no drift introduced. Stays filed-and-watching for Mobile Commits 1, 2 + future phases.
- F38 candidate (ShopAccessError `quota_exceeded` distinctness) — not yet filed; awaits smoke gate signal during Mobile Commit 2.

**Next step**: Mobile Commit 1 (types + builder + `WorkOrderPhotosSection` variant + `WorkOrderSectionCard` photos branch + `photoStorageCache` + `photoCaptureMachine` reducer + `PhotoCaptureScreen` + `useWorkOrderPhotos` hook + tests). Then Mobile Commit 2 (entry button on WO detail + classify-later surface + nav wiring + 8-step smoke gate + finalize).

---

### 2026-05-06 09:10 — Mobile Commit 1 build complete

Mobile substrate landed in commit `c3c6c41` (16 files, 4267 insertions / 577 deletions). Mobile Commit 2 (entry-points + smoke gate + finalize) pending.

**What shipped (mobile):**

- **`src/types/workOrder.ts`**: extended `WorkOrderSection` discriminated union 5 → 6 variants (added `WorkOrderPhotosSection {photos, undecided_count}` + `WorkOrderPhoto` interface) + `isPhotosSection` type guard. F9-discipline-clean.
- **`src/screens/buildWorkOrderSections.ts`**: 4th parameter `photos: WorkOrderPhoto[] = []` added (omit-when-empty; placed BEFORE Lifecycle in section order — UX call: "documentation media first, bookkeeping last"). Computes `undecided_count` for the sticky banner.
- **`src/components/WorkOrderSectionCard.tsx`**: added `_renderPhotos` branch + Photos heading. Pairs render side-by-side with Before/After labels (regrouping logic via `_collectPairs`); standalones render in a wrap grid; undecided photos surface a sticky banner ("X photos waiting to be classified — tap to review"). Defensive fallback now uses an exhaustive `never` cast to encode the exhaustive-switch guarantee for future maintainers. Optional `onPhotoPress` + `onUndecidedBannerPress` callbacks (Mobile Commit 2 wires them).
- **`src/services/photoStorageCache.ts`** (NEW): mirrors `videoStorageCache` shape (lookup / adopt / evict / cleanupOrphaned) + 7-day cold-start sweep `cleanupOldPhotos(now)` per Section F refinement. Canonical path `${DocumentDirectoryPath}/photos/p-{photoId}.jpg`. Lazy hydrate from RNFS.readDir on first lookup.
- **`src/screens/photoCaptureMachine.ts`** (NEW): pure reducer — 4-state machine per Section G (idle | previewing | uploading | uploaded | upload-failed). Simpler than videos' 5-state; no recording state because takePhoto is single-shot. Classification preserved across `uploading → upload-failed → uploading` retry (Phase 191B Q2 pattern).
- **`src/screens/PhotoCaptureScreen.tsx`** (NEW): wires reducer to vision-camera `<Camera>` + `Camera.takePhoto({flash:'off'})` + 4-button capture-time classification affordance (Before/After/General/Decide later → backend `role='undecided'`). Hooks declared above the permission early-returns per `react-hooks/rules-of-hooks` (lint enforcement). On `uploaded` → `useEffect` → `navigation.goBack()`.
- **`src/hooks/useWorkOrderPhotos.ts`** (NEW): backend-backed CRUD hook — surface mirrors `useSessionVideos` `{photos, isLoading, error, refresh, addPhoto, repair, deletePhoto, atCap}`. Multipart POST to `/v1/shop/{id}/work-orders/{id}/photos` with FormData (RN-style `{uri, name, type}` file field; Phase 191B `file://` prefix workaround reused). PATCH for re-classification surface; DELETE evicts cache. Typed errors via `ShopAccessError` 5-kind union (Section H reuse). Exports `PER_WO_PHOTO_COUNT_CAP=30` and `PER_ISSUE_PHOTO_COUNT_CAP=10` per F9 SSOT discipline.
- **`src/navigation/types.ts`**: `ShopStackParamList += {PhotoCapture, ClassifyPhotos}` routes with typed params `{shopId, woId, issueId?, pairId?}`.
- **`api-schema/openapi.json`** + **`src/api-types.ts`**: regenerated against the running backend (Backend Commit 0's photos route at `/v1/shop/{shop_id}/work-orders/{wo_id}/photos[/{photo_id}[/file]]`). `useWorkOrderPhotos` calls `api.GET/POST/PATCH/DELETE` fully typed end-to-end.

**Tests (5 new + 2 extended, 76 net new test cases, all 620 mobile tests pass in 5.4s):**
- `__tests__/screens/photoCaptureMachine.test.ts` (NEW, ~20 tests): initial state + every valid transition + 4 classification roles + classification-preservation across uploading → failed → retry + invalid-event-from-wrong-state no-ops via parameterized `it.each`.
- `__tests__/services/photoStorageCache.test.ts` (NEW, ~13 tests): adopt move + cross-volume copy fallback + lookup + evict idempotency + cleanupOrphaned (live-set + empty-set) + Section F `cleanupOldPhotos` with 7-day boundary (older unlinked, newer preserved, threshold export).
- `__tests__/screens/buildWorkOrderSections.test.ts` (extended +6): photos variant — omit-when-empty, presence-when-populated, before-lifecycle order, verbatim photo array, undecided_count math.
- `__tests__/types/workOrder.test.ts` (extended +3): `isPhotosSection` type guard + discriminated-union narrowing exercise covers all 6 variants.
- `__tests__/components/WorkOrderSectionCard.smoke.test.tsx` (extended +3 + 1 fix): photos variant heading test, undecided banner test, empty-state copy test. Existing future-variant test updated to use `voice_transcripts` (Phase 195 anticipation) since `photos` is now a real variant. RNFS `jest.mock()` added at module level so the photoStorageCache transitive import resolves cleanly under babel-jest.

**Verification:**
- 620/620 mobile Jest tests pass (47 suites, 5.4s) — no regressions across Phase 191B/192/193 suites.
- TypeScript: `tsc --noEmit` clean.
- ESLint: 0 errors (2 errors fixed at lint time: `react-hooks/rules-of-hooks` violations in PhotoCaptureScreen — both `useCallback` hooks moved ABOVE permission early-returns).
- F9 SSOT lint clean.

**F-tickets during execution:**
- F37 watching: backend `role` enum vs mobile typed union — verified end-to-end via the typed-tests; no instance #3 surfaced. Stays filed-and-watching for future phases.
- F38 candidate (`quota_exceeded` distinctness in ShopAccessError) — not promoted; awaits Mobile Commit 2 smoke gate signal.

**Versions (mobile):**
- `package.json`: 0.1.7 → 0.2.0 (minor bump — feature addition; 5 new files + 6 modified)

**Section E load-bearing test verdict: PASSED.** Phase 193's forward-look commitment held up under the first variant addition. The discriminated-union extension required NO deformation of photo data into text-row shape — F9-discipline preserved. The builder's signature widened (4th param) cleanly; the renderer's exhaustive switch added one branch + one heading case + a `never`-cast defensive fallback. No plan v1.1 amendment needed. Forward-look architecture verified by the first variant addition.

**Next step**: Mobile Commit 2 — entry button "Take photo" on `WorkOrderDetailScreen` (in the issues section + a per-WO action card) + classify-later surface (modal walking undecided photos one-at-a-time + pair picker for after-photos) + nav wiring (registering `PhotoCaptureScreen` + `ClassifyPhotosScreen` in `ShopStack`) + 8-step smoke gate (Section J) + finalize.
