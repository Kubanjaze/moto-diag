# Builder brief — Phase 192 Commit 1 (backend)

**Audience:** Builder dispatched for Phase 192 Commit 1 backend implementation.
**Status:** pre-Builder review surface; lands ahead of dispatch.

You are extending Phase 182's existing report-builder + renderer infrastructure with Phase 191B's videos + Vision findings. The architectural-design work is already done — the artifacts below specify the shape, the auth posture, the empty-state conventions, the renderer contract, and the test fixtures. **Do not redesign these; implement against them.** If implementation surfaces architectural concerns about the documented shape during execution, **flag them rather than working around silently** — same lesson as Phase 191D Commit 2's Builder-B trust-but-verify catches. Inviting the flag is cheaper than reviewing for unflagged friction at verify time.

## Architectural targets (read first)

1. **`docs/architecture/report-document-shape.md`** — defines the existing `ReportDocument` dict shape conventions + the new Phase 192 `videos` section variant (with nested `findings` sub-shape per video card) + empty-state conventions (omit-when-empty for videos) + renderer contract.
2. **`docs/architecture/auth-policy.md`** — F29 ADR. Owner-only-with-404 + "read access doesn't gate on tier." Phase 182's existing `get_session_for_owner` + `SessionOwnershipError → 404` pattern is the canonical implementation; you don't change auth, you inherit it.
3. **`docs/phases/in_progress/192_implementation.md`** plan v1.0 + v1.0.1 reshape — specifically: the Section A boundary-decoupling note ("composer testable independently of viewer + PDF route via own pytest suite, no HTTP"), Section D stuck-in-analyzing 5-min threshold, Section I empty-state policy, the cross-cutting placeholder copy register.
4. **`motodiag.reporting.builders.build_session_report_doc()`** + **`motodiag.reporting.renderers`** — Phase 182's existing implementations; you extend, don't replace.
5. **`motodiag.core.video_repo`** + **`motodiag.media.vision_analysis.VisualAnalysisResult`** — Phase 191B's video repo + findings Pydantic model. Source data for the new `videos` section.

## Implementation tasks (in commit order within Commit 1)

### Task 1: Extend `motodiag.reporting.builders.build_session_report_doc()` with the `videos` section

Per the shape doc's "Variant 5 (Phase 192 NEW) — `videos`" specification:

- After Phase 182's existing `# Notes` section append, add a `# Videos` section append block.
- Use `motodiag.core.video_repo.list_session_videos(session_id, db_path=db_path)` to fetch the video rows.
- Per the empty-state convention: `if videos: sections.append({"heading": "Videos", "videos": [...]})`. **Do not append the section when zero videos.**
- For each video row, build a `VideoCard` dict per the spec (required fields: `video_id`, `filename`, `captured_at`, `duration_ms`, `size_bytes`, `interrupted`, `analysis_state`, `analyzing_started_at`).
- For videos with `analysis_state == "analyzed"`: include the `findings` key with the full nested `VisualAnalysisResult` shape (use `.model_dump()` on the existing Pydantic model).
- For videos with non-analyzed states: **absent `findings` key** (not `findings: None`). Per the shape doc: "Renderers check `if 'findings' in video` rather than `if video.get('findings') is not None`."

The composer extension is ~50-80 lines of Python. Reuse Phase 182's existing patterns (em-dash sentinel for missing values, `if X:` empty checks, snake_case naming).

### Task 2: Extend renderers to handle the `videos` section variant

Per the shape doc's "Renderers" section + "Renderer extension is in scope for Phase 192's Builder dispatch":

- **`TextReportRenderer.render()`**: add an `elif "videos" in section:` branch after the existing `elif "table" in section:` branch. Each video card renders as an indented block (heading "Recording N (filename)" + metadata rows + nested findings indented further). Use the existing 2-space indentation convention.
- **`PdfReportRenderer.render()`**: add an equivalent block for the videos variant. Each video card renders as a bordered-box reportlab `Table` (single column) containing a metadata sub-table + (when findings present) a nested findings paragraph block. Use the existing `_kv_table` helper for the metadata sub-table; use the existing styles (`_heading_style`, `_body_style`).

The renderer extensions are ~30-50 lines per renderer. Conservative reportlab Platypus shapes (no new flowable types; reuse `Paragraph` / `Table` / `Spacer`).

### Task 3: Composer pytest suite (boundary-decoupling gate)

New test file: `tests/test_phase192_videos_extension.py`. Tests `build_session_report_doc()` extended behavior, NOT the route surface. Per the plan's Section A boundary-decoupling note: "composer's pytest suite tests `compose(session_id)` directly without HTTP layer; if a test requires HTTP-layer concerns to set up, that's a coupling smell."

Test cases (~10-12 across 2-3 test classes):

- **`TestVideosSection`**:
  - `test_videos_section_omitted_when_zero_videos` — session with no videos has no `videos` section in the output.
  - `test_videos_section_present_with_one_video_no_analysis` — session with 1 video, `analysis_state="pending"`, `findings` key absent from video card.
  - `test_videos_section_present_with_one_video_analyzed` — session with 1 video, `analysis_state="analyzed"`, `findings` key present with full Pydantic-dumped shape.
  - `test_videos_section_mixed_analysis_states` — session with 3 videos in pending / analyzing / analyzed / analysis_failed mix; verify each video card has correct `findings` presence/absence.
  - `test_videos_section_per_video_required_fields` — every video card has all required metadata fields.
  - `test_videos_section_findings_shape_matches_visual_analysis_result` — when present, `findings` dict structurally matches `VisualAnalysisResult.model_dump()`.
- **`TestVideosRenderers`**:
  - `test_text_renderer_handles_videos_section` — `TextReportRenderer().render(doc)` produces non-empty output containing video metadata + (where applicable) findings text.
  - `test_pdf_renderer_handles_videos_section` — `PdfReportRenderer().render(doc)` produces non-empty PDF bytes; smoke test only (don't byte-compare; that's 192B's deterministic-rendering concern).
  - `test_pdf_renderer_skips_findings_when_absent` — video with `analysis_state="pending"` renders without finding-block; doesn't crash on missing `findings` key.

Use `tmp_path` fixtures for the DB; seed Phase 191B-style video rows directly via `motodiag.core.video_repo.create_video()` + `motodiag.core.video_repo.set_analysis_findings()` for the analyzed cases. Don't go through HTTP; the composer is the unit under test.

### Task 4: Route integration tests (light, since the route already exists)

New test file: `tests/test_phase192_route_videos_extension.py`. Tests that the existing `/v1/reports/session/{id}` route correctly returns the new videos section when called via `FastAPI TestClient`.

Test cases (~3-4):

- `test_route_returns_videos_section_for_session_with_videos` — happy path through the route.
- `test_route_omits_videos_section_for_session_with_zero_videos` — empty case.
- `test_route_404_cross_owner_with_videos_present` — verifies F29 auth policy; cross-owner read returns 404 even when the session has videos.
- `test_route_free_tier_user_can_read_own_session_with_videos` — verifies "read access doesn't gate on tier" — free-tier user fetches own session's report containing videos → 200 OK.

These exist primarily as the boundary-test for the F29 ADR's smoke gate (per plan v1.0.1 Section G smoke step 7). Integration testing is light because the route was already shipped + tested in Phase 182; you're verifying the videos extension doesn't break Phase 182's existing auth posture.

### Task 5: Bump versions

- `pyproject.toml`: 0.3.1 → 0.3.2 (patch — extends API surface; no breaking changes).

The backend `implementation.md` 0.13.10 → 0.13.11 bump waits for Commit 4 finalize; do not bump it in Commit 1.

## What you do NOT do

- Do NOT create `src/motodiag/api/routes/reports.py` (already exists from Phase 182).
- Do NOT create `src/motodiag/api/report_composer.py` (the existing `build_session_report_doc()` IS the composer).
- Do NOT create `src/motodiag/api/models/report.py` Pydantic — back-compat with Phase 182's dict shape; F32 deferred.
- Do NOT add `require_tier()` to any read endpoint (per F29 ADR; Phase 182's existing route is correctly tier-free).
- Do NOT change Phase 182's existing PDF rendering path beyond the new `videos` section variant. WeasyPrint considerations from plan v1.0 are moot (Phase 182 uses reportlab; reshape preserved that choice).
- Do NOT migrate `ReportDocument = dict[str, Any]` to typed Pydantic. F32 with measurable promotion trigger is the disposition.
- Do NOT design the section-toggle preset filtering (mobile-side concern in Commit 3; backend composer always returns full payload, mobile filters at render time).
- Do NOT touch Phase 182's existing tests in `tests/test_phase182_*.py` (sealed history; your tests live in new `test_phase192_*.py` files).

## Trust-but-verify scope (architect runs these after you report)

- `pytest tests/test_phase192_videos_extension.py tests/test_phase192_route_videos_extension.py -v` → all PASS.
- `pytest tests/test_phase182_reports.py` (or wherever Phase 182's existing tests live) → all PASS (regression guard against the videos extension breaking Phase 182's existing surface).
- Manual smoke: `python -c "from motodiag.reporting.builders import build_session_report_doc; print(build_session_report_doc(session_id=N, user_id=N).keys())"` against a seeded session → returns dict with expected top-level keys.

## What to flag if surfaced during implementation

- Documented shape doesn't fit a real-world data case (e.g., a video with both `analysis_failed` AND partial findings — the spec assumed mutually exclusive).
- Renderer extension exposes a reportlab Platypus limitation (e.g., nested tables don't render correctly with the existing styles).
- Phase 191B `VisualAnalysisResult` fields aren't all present in the actual stored `analysis_findings` data (schema drift between phases).
- Phase 182 builder uses a pattern not captured in the shape doc (missed convention worth documenting).

Flagging is the right move; working around silently is not. Same lesson as Phase 191D Commit 2's three Builder-B catches.

## Reporting back

When done, report:
- Files created (paths + line counts).
- Files modified (paths + line-count delta).
- Test count + pytest result.
- Any deviations from this brief OR the architecture docs.
- Any concerns flagged per the "What to flag" section above.
- Confirmation that you did NOT commit / push.

Architect commits after trust-but-verify. The composer + renderer + tests + version bump all land as a single Commit 1 with a unified commit message that traces the work back to plan v1.0.1's reshape decisions.
