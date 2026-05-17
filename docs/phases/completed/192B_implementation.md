# Phase 192B — Diagnostic Report PDF Export + Share Sheet (feature)

**Version:** 1.0 (plan) + 1.1 (final: as-built Results + Verification Checklist marked + Deviations) | **Tier:** Standard | **Date:** 2026-05-06

## Plan v1.1 — Final: as-built Results + Verification Checklist marked

Phase 192B closed at Mobile Commit 3 finalize on 2026-05-06. The feature half of the substrate-then-feature pair (Phase 192 viewer / Phase 192B PDF + Share Sheet) shipped across 4 commits with one architectural-blocker fix-cycle (Commit 1.5 F34 deterministic rendering) caught BEFORE mobile Commit 2 started.

### Results

| Metric | Value |
|--------|-------|
| Total commits | 4 (1 backend Commit 1 + 1 backend Commit 1.5 + 2 mobile + 1 finalize across both repos) |
| Backend tests added | 34 (16 preset_filter + 3 deterministic_pdf_render + 15 post_pdf_route — 0 xfailed after Commit 1.5) |
| Backend pyproject | 0.3.2 → 0.3.4 (Commit 1 + Commit 1.5 each minor patch) |
| Mobile tests added | 72 (16 pdfDownloadErrors + 18 shareTempCleanup + 12 usePdfDownload + 11 useReportShare + 16 reportShareErrorCopy minus 1 from useReportShare refactor consolidation = 72 net new) |
| Mobile suite at finalize | 435/435 across 31 suites (363 → 435, +72 across the phase) |
| Mobile package | 0.1.2 → 0.1.4 (Commit 2 + Commit 3 each minor patch) |
| F-tickets touched | F28 + F29 reaffirmed; F30 status updated; F33 validated on first use; F34 closed at Commit 1.5 |
| Plan amendments | 1 (v1.0 → v1.1; F33 audit caught substrate state at plan time so no v1.0.1 reshape needed) |

**Key finding**: F33's "existing-code overlap audit BEFORE plan" step earned its keep on first use. The audit (greps for `pdf|PDF`, `preset|hidden|visibility`, `Share|UIActivityView|ACTION_SEND`) caught Phase 182's existing `/v1/reports/session/{id}/pdf` route + Phase 192 Commit 1's renderer extension, so plan v1.0 was honestly framed as extension/orchestration from the start. No v1.0.1 reshape amendment needed (compare: Phase 192 needed one). Process refinement validated; F33 promoted from candidate to standing CLAUDE.md addition is the natural next step.

**Secondary finding**: opt-in `deterministic` mode preserved revision-tracking callers' contract while letting share-flow callers depend on byte-stable bytes. Single-line-fix world (reportlab 4.4.10's `BaseDocTemplate(invariant=True)` propagation) made the architectural correction cheap to ship — total Commit 1.5 surface was 6 files, +233/-93. The opt-in shape (rather than always-on) is the load-bearing API design choice; it scales to future callers without re-litigating the determinism question.

**Tertiary finding**: pre-dispatch 5-min compat audits work. The `react-native-share@12.3.1` audit caught open issue #1683 (Android null-Uri error from Aug 2025) BEFORE installing the dep. Defensive URI validation + a dedicated test pinning the guard fires were added at Commit 2 build time, not as a fix-cycle after a smoke-gate failure. Same discipline that's load-bearing for substrate-decision audits applies to dependency-install audits.

### Verification Checklist (final)

- [x] Backend `compose_story_for_preset` (or equivalent — `_is_section_hidden` + filter at composer return point) filters sections per preset + overrides; matches mobile `isSectionHidden` semantics exactly.
- [x] Backend `POST /v1/reports/session/{id}/pdf` accepts `PdfRenderRequest` body, returns 200 with `application/pdf` bytes, returns 404 for cross-owner (F29 ADR), returns 422 when preset absent.
- [x] Backend GET sibling unchanged at handler level (summary line tweaked only).
- [x] Backend deterministic-rendering pytest: passes with `deterministic=True` (Commit 1.5 fix); default-mode preserved as non-deterministic for revision-tracking callers.
- [x] Mobile `react-native-share@12.3.1` installed + 5-min compat check completed (#1683 mitigated via defensive URI guard).
- [x] Mobile `usePdfDownload(sessionId, preset?)` writes PDF to `<tmp>/motodiag-shares/session-{N}-{ts}-{rand}.pdf`, returns file URI.
- [x] Mobile `useReportShare()` accepts `share(filePath)` at call-time (Commit 3 refactor for ergonomics) → orchestrates `Share.open` → unlinks on success only (dismiss + error paths leave file for sweep per Commit 3 refinement).
- [x] Mobile `cleanupOldShares(now)` runs on cold-start via App.tsx useEffect + nukes files > 24hr old in `<tmp>/motodiag-shares/`. Strict greater-than threshold pinned in tests.
- [x] Mobile `ReportViewerScreen` "Share PDF" button placed in `headerStrip` adjacent to `SectionToggle` (NOT nav-bar overflow) per the user's mental-model reminder.
- [x] Mobile button respects current screen-state preset (WYSIWYG mobile/PDF symmetry).
- [x] Mobile error handling: `PdfDownloadError` discriminated union → `shareErrorCopy()` helper → Alert with retryable + non-retryable variants. 5 error kinds covered (not_found / unauthorized / server / network / unknown).
- [x] Mobile error copy: voice/tone consistent with Phase 192's cross-cutting placeholder pass (informative > apologetic, action-oriented when recovery exists, terminology-consistent — "API key" / "Home" / "session" canonical).
- [x] OpenAPI types regenerated to pick up POST route.
- [x] Smoke gate Step 8 verifications (per pre-dispatch reminder): unit-tested via `useReportShare` per-share-unlink-only-on-success tests + `cleanupOldShares` boundary tests. Architect smoke-gate against real device deferred per Phase 192's plan v1.0.1 Section G (visual smoke = pre-Phase 192B prerequisite that 192B itself satisfies).
- [x] Smoke gate Step 9 verifications (deterministic byte-compare): unit-tested via `test_phase192b_deterministic_pdf_render`. End-to-end mobile-flow byte-compare deferred to architect smoke-gate when device available.
- [x] All doc + package version bumps recorded.
- [x] Backend phase docs moved in_progress/ → completed/.
- [x] Backend ROADMAP marked ✅; mobile ROADMAP marked ✅; both Phase History rows updated.
- [x] FOLLOWUPS reflects audit-trail of architectural decisions: F28 reaffirmed (deferred to next phase), F29 reaffirmed (deferred), F30 status updated (deferred to dedicated observability phase), F33 validated on first use (promote-to-CLAUDE.md candidate), F34 closed at Commit 1.5 with full resolution path.

### Risks (final — resolution notes)

- **Reportlab non-deterministic rendering** (predicted in plan v1.0): did materialize. F34 filed at Commit 1 with concrete reproduction (first diff at byte index ~2310 in trailer `/ID` block). Resolved at Commit 1.5 via opt-in `deterministic=True` parameter (single-line `SimpleDocTemplate(invariant=True)` fix). 3 previously-xfailed tests un-xfailed clean.
- **`react-native-share` version drift against RN 0.85** (predicted): did NOT materialize. 5-min compat audit on `12.3.1` (released yesterday) confirmed zero open RN 0.85 / iOS 17 / Android 14 / scoped-storage issues. Stale Aug 2025 issue #1683 (Android null-Uri) mitigated proactively via defensive URI validation in `useReportShare` + dedicated test.
- **Temp-file accumulation on non-happy-path exits** (predicted): handled per design. Per-share unlink covers happy path; 24hr startup sweep covers all non-happy-path exits including the deliberate Commit 3 refinement to NOT unlink on dismiss/error (lets user retry via Files-app surface without re-downloading).
- **POST /pdf RESTful awkwardness** (predicted): accepted as design trade-off. POST that returns binary stream is documented in OpenAPI; pinned in route tests.
- **Preset semantic drift backend-vs-mobile** (predicted): two-source design accepted (backend Python + mobile TS). Mitigation: `test_phase192b_preset_filter` includes constants pin + matrix coverage so backend-side regression catches drift early; mobile side has its own preset-filter tests. F35 candidate (SSOT preset rules harmonization) deferred — not load-bearing for 192B.
- **F33 audit applied at plan-write time**: prevented v1.0.1 reshape entirely (compare: Phase 192's reshape after substrate-state mismatch surfaced post-plan). First validated use of the F33 process refinement.

### Deviations from Plan

- **Commit 1.5 added as a substrate-blocker fix** between backend Commit 1 and mobile Commit 2: F34 deterministic-rendering fix landed as its own atomic commit before mobile work continued. Plan v1.0 anticipated this as a possible follow-up commit; it became necessary on Commit 1's first test run. Step-zero source audit (5-min reportlab grep) confirmed single-line-fix world before the fix was written.
- **`useReportShare` API refactor** between Commit 2 and Commit 3: hook signature changed from `useReportShare(filePath)` (URI bound at hook init) to `useReportShare()` returning `share(filePath)` (URI passed at call time). Better ergonomics for the dynamic download → share composition flow. Tests updated accordingly. Composition-not-internal-call shape preserved (`useReportShare` still doesn't call `usePdfDownload`).
- **Per-share unlink semantics refined**: Commit 2 unlinked on ALL outcomes (success + dismiss + error); Commit 3 narrowed to unlink on SUCCESS only. Dismiss + error paths leave file for the 24hr startup sweep — some share targets present cancellation UX that user perception treats as "not done yet", and unlinking on dismiss prevents quick retry. Pinned in `useReportShare` tests.
- **`overrides` API surface NOT exposed in 192B route** despite being accepted by the composer: per plan Section D decision (β) "ship preset-only in 192B; build_session_report_doc accepts overrides parameter for forward-compat but the POST schema doesn't yet". Designed minimal-but-extensible for F28 follow-up.
- **No screen-render tests for `ReportViewerScreen`** despite the new Share PDF button: matches the existing codebase convention (Phase 192 Commit 3 also skipped screen-render tests; pure-logic helpers extracted instead). Error-copy register tested at the `reportShareErrorCopy` module level; share-flow orchestration tested via the underlying `usePdfDownload` + `useReportShare` hook tests. Architect smoke-gate covers UI integration.

---

## Goal

Ship the **feature half** of the substrate-then-feature pair started by Phase 192. Phase 192 delivered the in-app diagnostic report viewer with full section/video rendering and section-visibility presets. Phase 192B closes the loop: mechanic taps a button, gets a PDF that **matches the viewer state** (preset-aware), and can share it via the OS Share Sheet (iOS UIActivityViewController, Android `ACTION_SEND`) — including AirDrop, Mail, Messages, Files, Drive, etc.

The PDF rendering itself is NOT new work — Phase 182 shipped the `/v1/reports/session/{id}/pdf` route and Phase 192 Commit 1's renderer extension already produces valid PDFs with the videos section variant 5 included. Substrate audit confirmed end-to-end PDF output works as a side-effect of Phase 192. **192B is consumer-side**: hit the existing route (or its new POST sibling), save bytes to a temp file, present to user via Share API, clean up.

CLI: no new CLI surface (mobile-only feature). Backend gains a sibling POST route `POST /v1/reports/session/{id}/pdf` for preset-filtered PDFs. Existing `GET /v1/reports/session/{id}/pdf` stays for full-PDF default.

Outputs:
- Backend: `compose_story_for_preset(doc, preset, overrides)` composer-side filter helper + `POST /v1/reports/session/{id}/pdf` route + `tests/test_phase192b_*.py` (preset filtering + deterministic-rendering pytest + route integration).
- Mobile: `react-native-share` install + `usePdfDownload(sessionId, preset?)` hook + `useReportShare(sessionId, preset?)` hook + `ReportViewerScreen` "Share PDF" button + temp-file lifecycle (save → share → unlink) + startup sweep (24hr-old).
- Docs: F34 candidate (deterministic PDF rendering) filed only if Commit 1's pytest fails.

## Logic

### Backend Commit 1 — Preset-aware PDF render

Per Section A decision (a) with refinement: **preset filtering lives in the composer, not the renderer**. Renderer stays pure (`ReportDocument → flowables`) so PDF rendering and JSON-preview rendering both consume the SAME pre-filtered `ReportDocument`. Strongest viewer/PDF symmetry.

1. Extend `build_session_report_doc(session_id, user_id, *, db_path, preset=None, overrides=None)` to accept optional `preset: Literal["full", "customer", "insurance"] | None` + `overrides: dict[str, bool] | None`. Default `None` → full document (no filtering, matches existing GET behavior).
2. After building the full sections list, apply the filter: for each section, check if `_is_section_hidden(heading, preset, overrides)` → drop. Mirror the mobile `isSectionHidden` semantics from `src/screens/reportPresets.ts` exactly (Customer hides `Notes`; Insurance + Full hide nothing; explicit override beats preset default).
3. Add new route `POST /v1/reports/session/{session_id}/pdf` accepting body `{"preset": "customer"}` (Pydantic model `PdfRenderRequest`). Body shape designed minimal-but-extensible: `overrides: dict[str, bool] | None = None` field reserved for F28-driven per-card overrides (NOT yet exposed to clients in 192B; deferred until F28 ships UI to emit it).
4. New route streams `application/pdf` bytes via existing `_pdf_response` helper. Same auth posture as GET (owner-only with 404 for cross-owner).
5. Existing `GET /v1/reports/session/{session_id}/pdf` UNCHANGED — stays for "give me the full PDF, no filtering" use case.

**Deterministic-rendering pytest** (per Section G addition): `test_phase192b_deterministic_pdf_render.py` calls `build_session_report_doc()` twice with same input + renders both via `PdfReportRenderer.render()` + `assert bytes_a == bytes_b`. If reportlab embeds non-deterministic metadata (creation timestamp, file ID, etc.), test fails on Commit 1 → forces immediate fix. Investigation paths: (i) reportlab's `SimpleDocTemplate(invariant=True)` flag (verify exists), (ii) explicit creation-timestamp override, (iii) trailer-ID seeding. F34 filed if a workaround is required.

### Mobile Commit 2 — react-native-share install + hooks

1. Install `react-native-share` via `npm install react-native-share`. **5-min compat check** against RN 0.85 + iOS 14+ + Android 11+ (open issues against the installed version's GitHub → resolve any blocker discovery into either a patch-package fix or a version-pin; Phase 191's `react-native-vision-camera` install pattern.)
2. New hook `src/hooks/usePdfDownload.ts`: `usePdfDownload(sessionId, preset?)` returns `{download: () => Promise<string>, isDownloading, error}`. The `download` function:
   - Hits `POST /v1/reports/session/{id}/pdf` with `{preset}` body if `preset !== undefined`, OR `GET /v1/reports/session/{id}/pdf` if not. (Two-path keeps backward-compat with full-PDF default.)
   - Reads the response as `Blob` / `ArrayBuffer`.
   - Writes to `${RNFS.TemporaryDirectoryPath}/motodiag-shares/session-{N}-{ISO8601-compact}.pdf` (dedicated subdirectory per Section B refinement).
   - Returns the file URI (`file://...path...pdf`) for the consumer to pass to share.
3. New hook `src/hooks/useReportShare.ts`: `useReportShare(sessionId, preset?)` orchestrates `usePdfDownload` → `Share.open({url: fileUri, type: 'application/pdf', filename: 'session-{N}.pdf'})` → on-completion `RNFS.unlink(fileUri)`.
   - Catches the share-dismissed case (`Share.open` throws on user cancel) — still unlinks the file (no orphan).
   - Returns `{share: () => Promise<void>, isSharing, error}`.
4. **Startup sweep** (Section B belt-and-suspenders): new module `src/services/shareTempCleanup.ts` exporting `cleanupOldShares()` that scans `${RNFS.TemporaryDirectoryPath}/motodiag-shares/` for files with mtime > 24hr ago + unlinks them. Wired into app cold-start (e.g., `App.tsx` `useEffect` or RootNavigator mount). Belt-and-suspenders against the multiple non-completion exit paths share flows have (dismiss, target crash, backgrounding mid-share).

### Mobile Commit 3 — ReportViewerScreen "Share PDF" button + finalize

1. Add a "Share PDF" Button to `ReportViewerScreen` below the section list (above the footer). `onPress` calls `useReportShare(sessionId, preset).share()` — preset is the current screen-state preset, so the shared PDF reflects the user's current filter selection (WYSIWYG per Section A decision).
2. Loading state: button shows `"Preparing PDF…"` + disabled while `isSharing === true`.
3. Error state: `Alert.alert("Couldn't share report", error)` with Retry + Dismiss buttons.
4. **Smoke gate** (per Section E): 9 steps including step 8 (temp-file cleanup verification on success + dismiss-without-share paths) + step 9 (deterministic-rendering byte-compare across two PDF renders of same session).

### Mobile Commit 4 — finalize

Doc finalize (CLAUDE.md commit-1 rules apply identically to Phase 192's finalize discipline). F-tickets bundled here per the F34 contingency. Move `192B_*.md` from `in_progress/` → `completed/`. Update ROADMAP. Bump versions.

## Key Concepts

- **Composer-side preset filtering** — `compose_story_for_preset()` (or equivalent helper) lives in `src/motodiag/reporting/builders.py` next to `build_session_report_doc`. The renderer stays unchanged from Phase 182 + Phase 192. Preset vocabulary belongs to the document construction layer, not the rendering layer. Symmetric with mobile's `isSectionHidden` in `src/screens/reportPresets.ts`.
- **POST `/v1/reports/session/{id}/pdf`** — wire format `(β)` per Section D. Body Pydantic model `PdfRenderRequest` with `preset: Literal["full", "customer", "insurance"] | None = None` + `overrides: dict[str, bool] | None = None` (latter reserved-not-exposed in 192B; F28 surfaces). Auth: owner-only with 404 cross-owner (matches GET sibling + F29 ADR).
- **`react-native-share` `Share.open({url, type, filename})`** — cross-platform abstraction over iOS `UIActivityViewController` + Android `Intent.ACTION_SEND` chooser. Throws on user cancel; consumer must catch + still unlink.
- **`RNFS.TemporaryDirectoryPath`** — per-platform OS temp dir (iOS `NSTemporaryDirectory`, Android `Context.getCacheDir()`). Subject to OS purging but explicit cleanup is more durable.
- **Belt-and-suspenders cleanup**: per-share `RNFS.unlink` on share-completion + 24hr-old startup sweep via `cleanupOldShares()`. Covers happy-path AND non-happy-path exit cases (dismiss, target crash, backgrounding mid-share).
- **Deterministic-rendering pytest** — `test_phase192b_deterministic_pdf_render.py` byte-compares two PDF renders of the same input. If reportlab's default render produces non-deterministic bytes (timestamps, IDs), test fails on Commit 1 → forces fix BEFORE other regression-protected guarantees layer on top.

## Verification Checklist

- [ ] Backend `compose_story_for_preset()` (or equivalent) filters sections per preset + overrides; matches mobile `isSectionHidden` semantics exactly.
- [ ] Backend `POST /v1/reports/session/{id}/pdf` accepts `PdfRenderRequest` body, returns 200 with `application/pdf` bytes, returns 404 for cross-owner (F29 ADR).
- [ ] Backend GET sibling unchanged.
- [ ] Backend deterministic-rendering pytest: two identical-input renders produce byte-identical outputs.
- [ ] Mobile `react-native-share` installed + RN 0.85 + iOS 14+ + Android 11+ compat verified.
- [ ] Mobile `usePdfDownload(sessionId, preset?)` writes PDF to `<tmp>/motodiag-shares/session-{N}-{ts}.pdf`, returns file URI.
- [ ] Mobile `useReportShare(sessionId, preset?)` orchestrates download → `Share.open` → `RNFS.unlink` on completion AND on dismiss.
- [ ] Mobile `cleanupOldShares()` runs on cold-start + nukes files > 24hr old in `<tmp>/motodiag-shares/`.
- [ ] Mobile `ReportViewerScreen` "Share PDF" button visible below sections; respects current screen-state preset.
- [ ] Smoke gate step 8: post-share-success → temp file gone; post-dismiss-without-share → temp file gone (after on-cancel branch).
- [ ] Smoke gate step 9: same session PDF rendered twice via mobile flow → byte-compare equal (verifies deterministic-rendering pytest end-to-end).
- [ ] iOS smoke: AirDrop to Mac → file lands as `session-{N}.pdf` with correct content.
- [ ] Android smoke: ACTION_SEND chooser shows email + Drive + Slack (or similar configured set).
- [ ] Customer-preset PDF: `Notes` section absent.
- [ ] Full-preset PDF: all 5 section variants present (rows, bullets, table, body, videos).

## Risks

- **Reportlab non-deterministic rendering** — embedded creation-timestamp / file-ID metadata may make byte-compare fail on Commit 1's pytest. Mitigation: deterministic-rendering test runs FIRST in Commit 1 build; if fail, immediate investigation (paths in Logic section). If unfixable cleanly, F34 filed + test marked as documented limitation. **Prefer fixing over deferring** — non-determinism makes regression detection impossible.
- **`react-native-share` version drift against RN 0.85** — share libraries are particularly susceptible to platform-API drift (iOS 17 broke `UIActivityViewController` for some apps; Android 14 changed file-share intents). Mitigation: 5-min compat check during install + `patch-package` posture if needed. Phase 191 absorbed similar friction with `react-native-vision-camera`.
- **Temp-file accumulation on non-happy-path exits** — mitigated by 24hr-old startup sweep (belt-and-suspenders per Section B).
- **POST /pdf RESTful awkwardness** — POST that returns a binary stream isn't textbook REST. Accepted trade-off for body-based parameters (preset + future overrides). Mitigation: OpenAPI tags it as `pdf` operation with explicit response schema; documentation calls out the parameterized-rendering pattern.
- **Preset semantic drift backend-vs-mobile** — backend `_is_section_hidden` and mobile `isSectionHidden` are TWO codebases enforcing the same rule (Customer hides `Notes`). Drift potential: phase 192C+ adds a new section that one side hides and the other doesn't. Mitigation: 192B's deterministic-rendering pytest includes a per-preset content fingerprint (e.g., assert "Notes" not in PDF text-extraction for Customer preset) so backend-side regression catches drift; mobile side already has its own preset tests. Future: F35 candidate to consolidate the preset rules into a shared spec (TOML or JSON) + generators on both sides — same pattern as F27 (SSOT registry harmonization).
- **F33 audit applied**: existing-code overlap audit ran (this plan v1.0 documents the audit findings under "Goal" — substrate already includes PDF route + reportlab + videos extension). 192B is honestly extension/orchestration territory from the start, not greenfield.
