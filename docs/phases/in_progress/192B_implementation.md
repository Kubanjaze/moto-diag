# Phase 192B — Diagnostic Report PDF Export + Share Sheet (feature)

**Version:** 1.0 (plan) | **Tier:** Standard | **Date:** 2026-05-05

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
