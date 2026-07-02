# F48 — Retire the Placeholder Video/Frame Path — Phase Log

**Status:** ✅ Complete | **Finish commit:** `cc973ab` on `master`, pushed 2026-07-01 22:02 (18 files, +564/−213)
**Started:** 2026-07-01 | **Completed:** 2026-07-01
**Repo:** https://github.com/Kubanjaze/moto-diag
**Family:** F9 (assumption-vs-reality drift) — dead-sim-path in prod namespace / placeholder-vs-real drift. Pattern doc: `docs/patterns/f9-mock-vs-runtime-drift.md` Instance #12.

---

### 2026-07-01 ~19:50 — Dispatch + Step 0 audit (plan)
- Task dispatched from an external reviewer question: prove no production video/photo path routes through placeholder/text-sim input; retire the sims; ship an F9 wiring guard.
- Step 0 overlap audit ran before any plan was locked (per CLAUDE.md). Verdict: `video_frames.py` + `VisualAnalyzer.analyze_image` imported by tests only (`test_phase100`, `test_phase101`, `test_phase108`); live video path real end-to-end (`videos.py` → `run_analysis_pipeline` → `ffmpeg.extract_frames` → `VisionAnalyzer.analyze_video_frames` → `ask_with_images`); photo endpoint does zero vision analysis. **Dispatch step (1) "rewire live sim path" declared a no-op.**
- Audit nuance that reshaped the plan: `vision_analysis.py` is a mixed module — live shared types (`VehicleContext`, `VisualAnalysisResult`, `VISION_ANALYSIS_PROMPT` + 5 more) imported by `analysis_worker.py:35` and `vision_analysis_pipeline.py:30`; only `VisualAnalyzer` is dead. Wholesale move would break prod → split required.
- Two decisions locked with the user: (1) sims fully out of the prod-looking namespace; (2) split `vision_analysis.py` into live types + extracted sim.
- Design correction before build: destination changed `tests/sim/` → `motodiag.media.sim/` — no test in the repo imports tests-local modules; the `from tests.…` pattern is the known-fragile pair (125/129). Convention-preserving, zero pythonpath risk.

### 2026-07-01 20:09–20:13 — Build complete
- Mechanical reshape executed by a worker agent against a locked spec; independently verified after.
- 5 new files: `media/vision_types.py` (282), `media/sim/__init__.py` (21), `media/sim/video_frames.py` (407, relocated), `media/sim/vision_analyzer_textsim.py` (205, extracted), `tests/test_media_pipeline_wiring_guard.py` (118).
- 8 files repointed (imports-only, +28/−86): `analysis_worker.py`, `vision_analysis_pipeline.py`, `tests/fixtures/anthropic_responses/_regen.py`, `test_phase100`, `test_phase101`, `test_phase108`, `test_phase191b`, `test_phase192`. Zero logic changes.
- Worker deviation (accepted): found + repointed 3 importers beyond the audited list (`test_phase191b`, `test_phase192`, fixtures `_regen.py`) — the exact ripple the audit was watching for.

### 2026-07-01 20:23 — Sandbox verification
- Static: zero dangling importers repo-wide; `vision_types.py` = exactly the 8 live symbols, no `VisualAnalyzer`; `media/__init__.py` clean of stale re-exports; all touched import chains resolve at runtime.
- Tests (build sandbox, deps installed ad-hoc on 3.10): **80/80** (guard + phase 100 + 101) then **54/54** (108 + 191b + 192 + ripple) = **134/134 affected tests green**.
- Widened to all 27 test files importing `motodiag.media`: only misses were 4 collection errors from the sandbox lacking `fastapi` — environment, pre-diagnosed.

### 2026-07-01 ~20:45 — Mac verification, first pass
- Affected surface on the Mac venv: **132 passed, 2 skipped** (pre-existing conditional skips in `test_phase192`).
- Full `pytest -q` hit 1 collection error: `test_phase125_quick.py` (`from tests.test_phase123_diagnose import …`, author-tagged `# type: ignore[import-not-found]`) — pre-existing infra fragility, zero references to touched modules. Re-run prescribed with `--continue-on-collection-errors`.

### 2026-07-01 ~21:30 — Session interrupted (API 529) → takeover session
- User posted 7 screenshots of the full run; original session died on repeated 529s before analysis. Takeover session recovered context from the transcript, read the run from Terminal scrollback + screenshots, and reconnected the repo + CLAUDE.md.

### 2026-07-01 21:50 — Full-regression verdict: env, not regression
- Full run (with `--continue-on-collection-errors`): **4465 passed / 35 failed / 22 errors / 13 skipped in 377.70s (0:06:17)**.
- Attribution, line-by-line against `pyproject.toml` extras and code degradation paths:
  - 33 F — missing `export` extra: `markdown` + `xhtml2pdf` (14 × `132_export`, 1 × `133_gate5`, 1 × `147_gate6`, 2 × `159_gate7` gate cascades) and `reportlab`, transitive via xhtml2pdf (`renderers.py:36`): 8 × `182_reports`, 6 × `192b_post_pdf_route`, 1 × `184_gate9` (API PDF route → HTTP 500 server-side).
  - 1 F — `146_recovery::test_bad_port_short_circuits_step1`: with pyserial absent the step-1 check returns "pyserial missing" (`cli/hardware.py:3109`) instead of the list_ports/dialout/CH340/Bluetooth remediation hints.
  - 21 E — `137_kline`: `No module named 'serial'` (missing `hardware` extra).
  - 1 F + 1 E — `129_theme` + `125_quick`: the pre-existing `from tests.…` pair. Out of F48 scope.
  - **0 attributed to the reshape.** The 6 affected files + guard are inside the 4465 passing.
- Root cause of the env gap: Mac venv provisioned with lean `[dev,api,ai,vision]`; suite requires `[all]`. Fix issued: `pip install -e ".[all]"` + re-run.

### 2026-07-01 22:05 — Documentation update
- `F48_implementation.md` v1.1 written (all sections, as-built) directly to `docs/phases/completed/` — the in_progress→completed move is collapsed because plan/build/verify occurred in one interrupted session; deviation #4 in the implementation doc records the skipped standalone plan commit honestly.
- Pattern doc extended: Instance #12 in `docs/patterns/f9-mock-vs-runtime-drift.md`.
- Project `phase_log.md` + `implementation.md` (media package row, version 0.13.13 → 0.13.14) updated.
- Finish commit block prepared for host Terminal (sandbox cannot write git metadata on this mount): unstage stray `docs/interview_prep.md`, explicit-path `git add` (avoids transient `data/.fuse_hidden*`), `git rm` the two orphans, single commit, push.

### 2026-07-01 21:59 — Post-green confirmation: full suite clean
- `pip install -e ".[all]"` + `pytest -q --continue-on-collection-errors`: **1 failed, 4573 passed, 5 skipped, 8 warnings, 1 error in 376.07s (0:06:16)**.
- The two reds are exactly the pre-existing `tests.`-import pair: `test_phase129_theme::TestIntegration::test_diagnose_quick_renders` (F) + `test_phase125_quick.py` (collection E). Zero F48-attributable reds — end-to-end confirmation nothing rippled.
- vs pre-fix run: +108 net newly-passing; skipped 13→5 (8 conditional skips now execute with full extras). Stale 5-day-old `.git/index.lock` (dated 2026-06-26 11:16) removed — it had atomically blocked the first finish-block attempt (HEAD verified unchanged at `d1dfd6a`, tree intact, block re-run cleanly).
- Follow-up candidate (separate ticket, out of F48 scope): fix the `from tests.…` fragility in `test_phase125_quick.py` + `test_phase129_theme.py`.

### 2026-07-01 22:02 — Finish commit landed
- `cc973ab` — "F48: retire placeholder video/frame sims from prod namespace (F9 Instance #12)" — pushed to `origin/master`. 18 files changed, +564/−213; git detected both retirements as renames (`media/video_frames.py → media/sim/video_frames.py`; `media/vision_analysis.py → media/vision_types.py` with the sim extracted).
- Trust-but-verify (per CLAUDE.md): commit hash confirmed on `master` and `origin/master`; orphan paths absent from index and worktree; stray `docs/interview_prep.md` staging resolved and excluded; diff stat matches claimed scope; F48 docs + pattern Instance #12 + project logs all inside the commit. **F48 closed.**
