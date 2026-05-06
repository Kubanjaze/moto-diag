# Phase 192B — Phase Log

**Status:** 🚧 In Progress | **Started:** 2026-05-05
**Repo:** https://github.com/Kubanjaze/moto-diag (backend) + https://github.com/Kubanjaze/moto-diag-mobile (mobile)
**Branch:** `phase-192B-pdf-export-share-sheet` (will be created BOTH repos at plan-push)

---

### 2026-05-05 22:50 — Plan v1.0 written

Phase 192B opens as the **feature half** of the substrate-then-feature pair started by Phase 192. Substrate = in-app diagnostic report viewer with section/video rendering + section-visibility presets. Feature = preset-aware PDF export + OS Share Sheet (iOS UIActivityViewController + Android ACTION_SEND).

**F33 process refinement applied** (filed 2026-05-05 from Phase 192 retrospective): existing-code overlap audit ran BEFORE plan v1.0 was written. Greps:
- `pdf|PDF` in both repos
- `preset|hidden|visibility` in `src/motodiag/`
- `Share|UIActivityView|ACTION_SEND` in mobile `src/`

**Audit findings shaped the plan from the start:**
1. **Backend `/v1/reports/session/{id}/pdf` route exists** ([reports.py:80-93](src/motodiag/api/routes/reports.py#L80-L93)) — Phase 182 shipped it. Phase 192 Commit 1's renderer extension means the route ALREADY produces valid PDFs with the videos section variant 5 included. **End-to-end PDF output works as a side-effect of Phase 192. NOT greenfield.**
2. **Backend reportlab Platypus** ([renderers.py:47-60](src/motodiag/reporting/renderers.py#L47-L60)) — flowable composition in Python. Confirms Phase 192 shape doc's reportlab-not-Jinja2 correction.
3. **Zero backend preset filtering** — confirms preset filtering is genuinely new work for 192B.
4. **Mobile api-types includes `/pdf` route**, but no consumer hook / UI / share lib.
5. **No mobile share libs installed** (`react-native-share` absent from package.json) — confirms greenfield for the share wiring.

**Substrate-vs-plan-v1.0 reshape avoided** by the F33 process: plan v1.0 is honestly framed as extension/orchestration territory (composer-side preset filter + sibling POST route + mobile consumer-side share flow) rather than the original "PDF export" framing that implied building the PDF route. Same lesson as Phase 192 v1.0 → v1.0.1, but caught at plan-write time instead of at architect-side artifact time. **F33 refinement earning its keep on first use.**

**Pre-plan Q&A architect-side** (no Plan agent dispatched per Kerwyn's discipline). 5 sections + smoke-gate + commit-cadence locked before plan written:
- **A**: PDF preset support (a) with refinement — composer-side filter, not renderer-side. Renderer stays pure (`ReportDocument → flowables`).
- **B**: file URI (b) with refinement — dedicated `<tmp>/motodiag-shares/` directory + per-share unlink + 24hr-old startup sweep (belt-and-suspenders).
- **C**: `react-native-share` (a) with refinement — 5-min compat check during install (RN 0.85 + iOS 14+ + Android 11+).
- **D**: POST wire format (β) scoped to preset-only. Body shape `{"preset": "customer"}` today, designed minimal-but-extensible for F28 overrides. URL: `POST /v1/reports/session/{id}/pdf` symmetric with GET. GET stays for full-PDF default.
- **F30 telemetry**: filed (NEW) as two-trigger F-ticket — backend composer log-on-defensive + share-flow telemetry. Promotion: dedicated observability phase (Track J candidate) OR production composer malformed-payload occurrence forces (a)-only escalation. Explicitly NOT in 192B.

**Smoke gate**: 7 + 2 = 9 steps. Step 8 = temp-file cleanup verification (success + dismiss-without-share paths). Step 9 = deterministic-rendering byte-compare (two PDF renders of same session). **F34 candidate filed only if Commit 1's deterministic-rendering pytest fails.**

**Commit cadence**: 3 commits + Backend Commit 1 ships deterministic-rendering as **pytest** not just smoke-gate check. Fail-fast at Commit 1 if reportlab non-deterministic (rather than discovering at gate time). Pytest belongs to regression-protected guarantees, not architect-only verification.

**Pre-plan baseline confirmation**: full backend regression sweep ran foreground + no pipe (Kerwyn's operational ask). 4395 passed, 5 skipped, 0 failed in 1:29:53. Trustworthy clean baseline going into 192B.

**Phase 192B scope NOT taking on**:
- F28 (per-card toggle UI + cross-session preset persistence) — deferred to Phase 193+ or whenever real customer demand surfaces. Body shape designed for future overrides, but no UI to emit them this phase.
- F29 (live-tick refresh for stuck-state) — orthogonal to 192B's PDF + share scope.
- F30 (telemetry) — explicitly out of scope per disposition above.

**Risks at plan-write time**:
1. Reportlab non-deterministic rendering — fail-fast pytest at Commit 1 surfaces this.
2. `react-native-share` version drift against RN 0.85 — 5-min compat check at install.
3. Temp-file accumulation — belt-and-suspenders cleanup.
4. POST /pdf RESTful awkwardness — accepted trade-off.
5. Preset semantic drift backend-vs-mobile — F35 candidate (SSOT preset rules harmonization) deferred for now.

**Next step**: create `phase-192B-pdf-export-share-sheet` branch on both repos, push plan v1.0 (this commit), then begin Backend Commit 1.

---

### 2026-05-05 23:48 — Backend Commit 1 build complete

Three logical changes per plan v1.0 + commit-discipline reminder:

**Change 1: Composer extension** — `src/motodiag/reporting/builders.py`:
- New `ReportPreset = Literal["full", "customer", "insurance"]` type alias.
- New private constants `_CUSTOMER_HIDDEN_HEADINGS = ("Notes",)`, `_INSURANCE_HIDDEN_HEADINGS = ()`, `_FULL_HIDDEN_HEADINGS = ()` mirroring mobile `src/screens/reportPresets.ts` semantics exactly.
- New private helpers `_preset_hidden_headings(preset)` + `_is_section_hidden(heading, preset, overrides)` with explicit-override-beats-preset semantics. `preset=None` returns False for all headings (back-compat with Phase 182 GET path).
- `build_session_report_doc()` signature extended with `*, preset=None, overrides=None` keyword-only params. Filter applied AFTER all sections built so omit-when-empty logic for individual variants stays independent of visibility filter. Preserves section order.
- Stale Phase 191B comment about missing `analyzing_started_at` column refreshed to reflect Phase 192 Commit 1's migration 040 (Architect-side cosmetic flag from Phase 192 Commit 1's phase log resolved inline since this file is being edited anyway).

**Change 2: New POST route** — `src/motodiag/api/routes/reports.py`:
- New `PdfRenderRequest` Pydantic model with required `preset: Literal["full", "customer", "insurance"]` field. `overrides` field NOT included this phase (F28 surfaces it when per-card UI ships); Pydantic default `extra='ignore'` means clients passing it get a 200 silently — pinned in tests as the F28-evolution baseline.
- New `POST /v1/reports/session/{session_id}/pdf` route accepting `PdfRenderRequest` body. Same auth posture as GET sibling (owner-only with 404 cross-owner per F29 ADR). Streams `application/pdf` via existing `_pdf_response` helper.
- Existing `GET /v1/reports/session/{session_id}/pdf` UNCHANGED — summary line tweaked to clarify it's the "full" PDF path, but route handler body identical.
- Module docstring updated to call out Phase 192B's POST extension + the F28 deferral rationale.

**Change 3: Regression-guard test (deterministic-rendering pytest)** — `tests/test_phase192b_deterministic_pdf_render.py`:
- 3 tests covering: same-renderer determinism, fresh-renderer determinism, content-sensitivity sanity check.
- Failed on first run as plan v1.0 risks anticipated. F34 filed in mobile FOLLOWUPS with concrete reproduction (CreationDate / ModDate / trailer-/ID embedding non-determinism; first diff at byte index ~2310).
- 2 of 3 marked `@pytest.mark.xfail(strict=True)` pending F34 fix; sanity-check test (different titles → different bytes) NOT marked xfail since content-sensitivity is independent of time-sensitivity. Sister downstream consumer test in `test_phase192b_post_pdf_route::test_get_pdf_still_returns_full_document` also marked xfail (depends on byte-equality between GET and POST(preset='full')).
- Per pre-dispatch discipline: Commit 1 ships with xfailed tests + filed F-ticket; F34 fix lands in Commit 1.5 as own atomic commit BEFORE mobile Commit 2 starts (share-flow byte-compare smoke gate depends on deterministic bytes).

**Test files added** (3, 34 tests total):
- `tests/test_phase192b_preset_filter.py` (16 tests across 3 classes — preset constants pin + `_is_section_hidden` resolution semantics + end-to-end composer integration)
- `tests/test_phase192b_deterministic_pdf_render.py` (3 tests: 2 xfailed pending F34, 1 sanity-check passes)
- `tests/test_phase192b_post_pdf_route.py` (15 tests across 4 classes — happy path + validation + auth + GET-sibling regression guard with 1 xfailed pending F34)

**Verification**:
- 31 passed + 3 xfailed across the 3 new test files.
- 47 passed in cross-phase regression sample (Phase 182 reports + Phase 192 videos extension + Phase 192 route extension) — ZERO ripple from composer change.
- Pyproject 0.3.2 → 0.3.3 (additive feature minor patch).

**F34 disposition**: filed in mobile FOLLOWUPS with concrete reproduction + 3-path scope estimate (`SimpleDocTemplate(invariant=True)` preferred). Phase 192B Commit 1.5 is the recommended target — atomic fix-only commit before mobile Commit 2 starts, since share-flow correctness depends on deterministic bytes.

**Next step**: commit (3-paragraph commit message per pre-dispatch discipline: composer extension / route wiring / regression-guard test) + push. Then Commit 1.5 to address F34 before pivoting to mobile Commit 2.
