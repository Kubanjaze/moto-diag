# F48 — Retire the Placeholder Video/Frame Path (F9: dead-sim-path in prod namespace)

**Version:** 1.1 | **Tier:** Micro (F-ticket, F9 family) | **Date:** 2026-07-01

## Goal
Answer an external reviewer's question with code, not assertion: prove the only route from an uploaded video/photo to Claude is the real one (real ffmpeg frames / real image bytes), and retire the placeholder/text-sim modules so nothing sim-shaped lives in the shipped `motodiag.media` namespace where it could be mistaken for — or one refactor away from — a production path. Ships an F9 integration-gap regression-guard pinning the real wiring.

CLI: n/a (no user-facing surface change). Verification:
```
pytest tests/test_media_pipeline_wiring_guard.py tests/test_phase100_video_frames.py \
       tests/test_phase101_vision.py tests/test_phase108_gate4_integration.py \
       tests/test_phase191b_video_analysis_pipeline.py tests/test_phase192_videos_extension.py -q
pytest -q --continue-on-collection-errors     # full regression (~6-7 min)
```

Outputs (5 new files):
- `src/motodiag/media/vision_types.py` (282 LoC) — the 8 live shared symbols extracted from `vision_analysis.py` (incl. `VehicleContext`, `VisualAnalysisResult`, `VISION_ANALYSIS_PROMPT`); no `VisualAnalyzer`
- `src/motodiag/media/sim/__init__.py` (21 LoC) — loudly-labeled test-only sim subpackage
- `src/motodiag/media/sim/video_frames.py` (407 LoC) — placeholder frame sim, relocated wholesale from `media/video_frames.py`
- `src/motodiag/media/sim/vision_analyzer_textsim.py` (205 LoC) — the dead `VisualAnalyzer.analyze_image(image_description: str)` text-sim, extracted from `media/vision_analysis.py`
- `tests/test_media_pipeline_wiring_guard.py` (118 LoC) — F9 integration-gap regression-guard

Removed (git rm in the finish commit): `src/motodiag/media/video_frames.py`, `src/motodiag/media/vision_analysis.py` — zero remaining importers.

## Logic
- **Step 0 — overlap audit (per CLAUDE.md, ran first).** Grepped every caller of `video_frames.py` and `VisualAnalyzer.analyze_image` repo-wide. Verdict: **no production path touches a placeholder or the text-sim.** Both were imported only by tests (`test_phase100`, `test_phase101`, `test_phase108`). The live video path was already fully real: `api/routes/videos.py` → `media/analysis_worker.run_analysis_pipeline` → `media/ffmpeg.extract_frames()` (real JPEGs) → `vision_analysis_pipeline.VisionAnalyzer.analyze_video_frames()` → Claude Vision via `ask_with_images`. Edge cases already handled (FFmpegMissing→analysis_failed, FFmpegFailed/0 frames→unsupported, MAX_FRAMES_PER_CALL=60).
- **Photo endpoint check (the flagged risk):** `upload_wo_photo` does zero vision analysis — it normalizes and stores bytes; its `analysis_state`/`analysis_findings` response fields are unpopulated schema placeholders read from the DB row. No photo analyzer exists, so no photo path can route through the text-sim.
- **Mixed-module discovery:** `vision_analysis.py` was NOT a pure sim — the live pipeline imports shared types from it (`analysis_worker.py:35`, `vision_analysis_pipeline.py:30`). Only the `VisualAnalyzer` class was dead. Moving the file wholesale would have broken production.
- **The reshape:** split `vision_analysis.py` → live `vision_types.py` (8 shared symbols) + dead `VisualAnalyzer` → `sim/vision_analyzer_textsim.py`; relocate `video_frames.py` wholesale → `sim/video_frames.py`; repoint all importers (2 prod modules, 5 test files, 1 fixtures regen script) — imports-only edits, zero logic changes.
- **The guard:** `test_media_pipeline_wiring_guard.py` mocks both boundaries (`ffmpeg.extract_frames`, `VisionAnalyzer`), calls `run_analysis_pipeline`, and asserts extract_frames is called AND the exact frame list it returns (object identity) is what reaches `analyze_video_frames`. Guards against any future placeholder swap in the middle of the pipeline.

## Key Concepts
- **F9 subtype 2 (integration gap) guard pattern**: pin wiring by object identity across the pipeline, with both boundaries mocked — needs no real ffmpeg, no API key, runs in any environment.
- **Mixed-module hazard**: a module that co-locates live contract types with a dead sim can't be retired by relocation; it must be split. Grep-level audits that stop at "module is referenced" would have called it live; symbol-level auditing (which names are imported, by whom) gave the true partition.
- **In-package sim over `tests/` sim**: every test in this repo imports only from `motodiag.*`; the two files that ever tried `from tests.…` imports (`test_phase125_quick.py`, `test_phase129_theme.py`) are the known-fragile pair. `motodiag.media.sim` keeps the existing import convention, zero pythonpath infra risk, while the package name + docstring make test-only status unmissable.
- **`.[all]` extras completeness**: full-suite verification on a fresh venv requires `pip install -e ".[all]"` — the `export` extra (markdown + xhtml2pdf, which transitively provides reportlab) and `hardware` extra (pyserial) are exercised by the suite even though the media surface doesn't need them.

## Verification Checklist
- [x] Step 0 audit documented: no live/user-facing path routes through placeholder input
- [x] Zero dangling importers of `media/video_frames.py` or `media/vision_analysis.py` after repoint (repo-wide grep)
- [x] `vision_types.py` contains exactly the 8 live shared symbols, no `VisualAnalyzer`
- [x] `media/__init__.py` has no stale re-exports
- [x] Import chain of every touched module resolves at runtime
- [x] Affected surface green: 134/134 in build sandbox; 132 passed + 2 skipped (pre-existing conditional skips in `test_phase192`) on the Mac venv
- [x] New F9 guard passes: sentinel frames flow through `run_analysis_pipeline` with identity intact
- [x] Full regression on Mac: 4465 passed / 35 failed / 22 errors / 13 skipped in 377.70s — every failure and error attributed to missing optional extras or the pre-existing `tests.`-import pair; **zero attributed to this change** (see Results)
- [x] Full regression re-run after `pip install -e ".[all]"` — **1 failed, 4573 passed, 5 skipped, 1 error in 376.07s** (2026-07-01 21:59): the failed/error are exactly the pre-existing pair (`test_phase129_theme` / `test_phase125_quick`); +108 net newly-passing vs the pre-fix run, and 8 formerly-conditional skips now execute (13→5 skipped) with the full extras present
- [x] Orphan removal staged as `git rm` in the finish commit (not filesystem delete)

## Risks
- **Ripple beyond the audited importer list** — materialized, contained: the build worker found three importers beyond the original list (`test_phase191b`, `test_phase192`, `tests/fixtures/anthropic_responses/_regen.py`) pulling shared types from the old module; all repointed and green.
- **`tests/sim/` relocation breaking test collection** — avoided by design correction before build (see Deviations #2).
- **Mac venv extras gap masquerading as regression** — materialized: the first full run produced 35F/22E, all environmental. Diagnosed line-by-line against `pyproject.toml` extras and `cli/hardware.py`/`renderers.py` degradation paths; none touch `motodiag.media`.
- **Sandbox git limitation** — Cowork sandbox cannot write git metadata on this mount; the finish commit is executed by the user in Terminal from a prepared block. Docs written via file tools.

## Deviations from Plan
1. **Step (1) of the dispatch ("rewire live text-sim path") was a no-op** — the Step 0 audit proved no live path uses the sim. Recorded as the clean answer for the external reviewer.
2. **Sim destination changed from `tests/sim/` (as initially locked) to `motodiag.media.sim/`** — repo-wide check showed no test imports a tests-local module; a `tests/` package would require novel pythonpath infra unverifiable without the full suite, and the `tests.`-import pattern is the repo's known fragility (the 125/129 pair). Same anti-confusion goal, zero infra risk.
3. **Worker exceeded its importer list** (three extra files repointed) — necessary, independently verified, all green.
4. **Plan v1.0 was not committed before build** — the plan (audit + AskUserQuestion decisions) and build happened in one session that was then cut off by repeated API 529 errors before docs could land; finish (docs + commit) completed in the takeover session of 2026-07-01. Deviation from the plan-commit-first discipline, logged here rather than hidden by backdating.
5. **Full-suite verification surfaced a venv provisioning gap, not a code issue** — the Mac venv had the lean `[dev,api,ai,vision]` extras; the suite requires `[all]` (export→markdown/xhtml2pdf/reportlab-transitive; hardware→pyserial). Fix: `pip install -e ".[all]"`.

## Results
| Metric | Value |
|--------|-------|
| New files | 5 (4 src + 1 test, 1,033 LoC total) |
| Deleted files | 2 (`media/video_frames.py`, `media/vision_analysis.py`) |
| Repointed files | 8 (2 prod, 5 tests, 1 fixtures script) — imports-only, +28/−86 |
| Logic changes | 0 |
| Affected-surface tests (sandbox) | 134/134 passed |
| Affected-surface tests (Mac venv) | 132 passed, 2 skipped (pre-existing conditional skips) |
| Full regression (Mac, pre-extras-fix) | 4465 passed / 35 failed / 22 errors / 13 skipped in 377.70s |
| Full regression (Mac, post-`.[all]`) | **4573 passed / 1 failed / 1 error / 5 skipped in 376.07s** — reds = the pre-existing 129/125 pair only |
| Failures/errors attributed to F48 | **0** (33F+21E+1F = missing `export`/`hardware` extras; 1F+1E = pre-existing `tests.`-import pair) |
| Production paths through sims (post-audit) | 0 (and 0 before — audit finding) |
| Live API calls / tokens spent | 0 |

**Key finding:** the reviewer's question dissolved under Step 0 — the live path was already real end-to-end, and the actual defect was namespace hygiene: a dead text-sim sharing a module with live contract types, one careless import away from prod. The durable fixes are structural (sims quarantined in `media.sim`, shared types in `vision_types`) plus a wiring guard that fails the moment anyone reroutes the pipeline through a placeholder again.
