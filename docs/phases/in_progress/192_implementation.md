# Phase 192 — Diagnostic Report Viewer (substrate)

**Version:** 1.0 (plan) + 1.0.1 (pre-Commit-1 reshape) | **Tier:** Standard | **Date:** 2026-05-05

## Plan v1.0.1 — pre-Commit-1 reshape: Phase 182 IS the substrate

This amendment lands BEFORE any architect-side schema-design work or Builder dispatch. The amendment is the pre-build deep-survey discipline catching what plan v1.0 didn't see: **Phase 182 already shipped the report-route surface that plan v1.0 specified building from scratch.** Discovering this NOW vs at Commit 1 verification is exactly when the substrate-extension work should pivot — same lesson as Phase 191B's HVE-shape bug (F9 catalog #1), but caught at pre-architect-deliverable time instead of fix-cycle time.

Plan v1.0 sealed history preserved verbatim per the audit-trail-preservation principle established at Phase 191C v1.0.1.

### What plan v1.0 unknowingly re-specified

| Plan v1.0 specified (NEW) | Phase 182 already shipped |
|---|---|
| `src/motodiag/api/routes/reports.py` | Already exists. 163 lines. 6 endpoints (session/work-order/invoice × json/pdf). |
| `src/motodiag/api/report_composer.py` | `motodiag.reporting.builders.build_session_report_doc()` is the existing composer. 126 lines. |
| `GET /v1/sessions/{id}/report` (sessions/ prefix) | `GET /v1/reports/session/{id}` already exists (reports/ prefix). |
| `models/report.py` Pydantic `ReportPayload` | `ReportDocument = dict[str, Any]` — Phase 182 chose freeform dict over Pydantic. |
| 192B's `/v1/sessions/{id}/report.pdf` | `GET /v1/reports/session/{id}/pdf` already exists. PDF rendering already shipped. |
| Auth: session-owner-or-shop-tier-member | Phase 182: `get_session_for_owner(session_id, user_id)` — owner-only; cross-user → `SessionOwnershipError` → **404, not 403**. Subtly stricter; existence-disclosure-prevention. |
| Vision findings + video integration | **Entirely absent from Phase 182's builder.** Predates Phase 191B's videos table. |

### Reshape (a) accepted: Phase 182 IS the substrate

Substrate-then-feature isn't a clock-time pattern; it's a logical-dependency pattern. Plan v1.0 not knowing about Phase 182 was the bug; the reshape corrects it:

- **Phase 182** was always the substrate (report builders + PDF renderer + 6 routes).
- **Phase 192** is the FEATURE half — mobile viewer + section-toggle preset system + Vision findings extension to the existing builder.
- **Phase 192B's scope collapses** to mobile Share Sheet wiring + (maybe) section-toggle query param on the existing PDF route + (maybe) PDF template extension for the videos/Vision sections. Probably 2-3 commits, not 5.

Two surfaces returning the same logical data is the F9 family pattern this chain has been hardening against — drift-prone-by-design. Reject (b) on principle; defer (c) to F32.

### Specific scope changes in 192's plan-of-record

**Backend (Commit 1) — substantially reduced from plan v1.0:**

DROPPED from plan v1.0:
- ❌ `src/motodiag/api/routes/reports.py` (NEW) — already exists from Phase 182.
- ❌ `src/motodiag/api/report_composer.py` (NEW) — `build_session_report_doc()` IS the composer.
- ❌ `models/report.py` Pydantic `ReportPayload` (NEW) — back-compat preserved with dict surface; Pydantic migration deferred to F32.
- ❌ `GET /v1/sessions/{id}/report` route (NEW) — mobile uses existing `/v1/reports/session/{id}`.
- ❌ Composer pytest suite as a new file — extension tests fold into existing Phase 182 test surface.

ADDED in 192's reshape:
- ✅ EXTEND `motodiag.reporting.builders.build_session_report_doc()` to include videos + Vision findings sections (per Phase 191B's videos table + analysis_findings).
- ✅ NEW `docs/architecture/auth-policy.md` (F29 ADR, re-derived around Phase 182's owner-only-with-404 pattern; explicit existence-disclosure-prevention rationale in WHY narrative).
- ✅ NEW `docs/architecture/report-document-shape.md` (free byproduct of architect understanding the existing dict shape well enough to extend it; future contributors extending further don't re-derive conventions; audit-trail-preservation discipline).
- ✅ NEW pytest extensions covering the videos/Vision findings section integration against Phase 191B seeded video fixtures.

**Mobile (Commits 2-4) — mostly unchanged from plan v1.0:**

- `ReportViewerScreen` + `SectionToggle` + `ReportCard` + `useReport` hook: still NEW.
- `useReport` fetches from existing `GET /v1/reports/session/{sessionId}` (the prefix differs from plan v1.0's spec — `/reports/session/N` not `/sessions/N/report`).
- Viewer renders the dict-based ReportDocument shape via runtime parsing rather than typed Pydantic — slight quality loss in TypeScript narrowing but acceptable for a single-surface consumer; F32 escalation handles the typed-migration path.
- All Section I empty/error-state policy decisions still apply.
- All cross-cutting placeholder copy register strings still apply (only the field-shape mapping changes; placeholder copy is independent).

**Auth posture refinement (Section E):**

Phase 182's owner-only-with-404 pattern is **stricter** than plan v1.0's session-owner-or-shop-tier-member spec. The 404-not-403 choice prevents existence-disclosure on cross-user lookups (a non-owner can't distinguish "session doesn't exist" from "session exists but isn't yours" — both return 404). This is a security-meaningful improvement, not just a naming difference. F29 ADR documents the WHY explicitly.

**Smoke gate Section G refinement:**

Plan v1.0 step 7 (free-tier-user-can-read-own-report-but-not-other-users) becomes:
- Free-tier user fetches own session's report via `/v1/reports/session/{their_id}` → 200 OK ✓
- Free-tier user fetches OTHER user's session report via `/v1/reports/session/{other_id}` → **404** (not 403) — verifies existence-disclosure-prevention pattern.

Plan v1.0 step 9 (composition layer regression sweep BEFORE UI testing) becomes:
- `pytest tests/test_phase182_reports.py tests/test_phase192_videos_extension.py` against fixtures covering full / empty / incomplete-Vision / mixed-analysis sessions.

### F-ticket changes

- **F29 (auth-policy ADR)** — content reshape: precedent body now explicitly includes Phase 182's `SessionOwnershipError → 404` pattern (the strictest of all Track-I read endpoints). WHY narrative: "owner-only-on-read prevents existence-disclosure on cross-user lookups; tier gating is for scarce resources (vehicle/session creation), not for read access to your own data." ADR explains trade-offs (why 404-not-403 was chosen for sessions specifically, vs vehicles' explicit 403 cross-owner; the difference is information-disclosure sensitivity — vehicle existence is non-sensitive in a multi-tenant garage; session existence MAY be sensitive in cases where the session itself is private).
- **F32 (NEW)** — eventually migrate dict-based `ReportDocument` to typed Pydantic. Promotion trigger: when a third report-consuming surface lands. Phase 182's PDF route is consumer #1; Phase 192's mobile viewer is consumer #2; the third triggers F32 to its own dedicated typing-modernization phase. Rationale for not migrating in 192: couples 192's delivery risk to refactor of unrelated upstream code; wrong shape for substrate-extension work.

### 192B forward-looking flag

192B's plan-of-record needs its own pre-plan Q&A pass AFTER 192 finalizes. The substrate changed underneath 192B; the feature half should re-derive its scope against the actual substrate state, not the originally-planned substrate state. Probably 2-3 commits, not 5. Don't write 192B's plan from plan v1.0's framing; rewrite from post-192-finalize state.

Specific 192B scope candidates that emerge from the reshape:
- Mobile Share Sheet integration (existing PDF route is the share target; mobile wires `Share` API to download + re-share the PDF binary).
- Section-toggle query param on the existing PDF route (e.g., `?sections=vehicle,symptoms,...`) — backend renderer filters before PDF generation.
- PDF template extension for the videos/Vision findings sections (Phase 182's renderer may need new template blocks for the new section shapes).
- Section-toggle UX in the share flow — does the user pick preset before tap-share, or after?

### Architect-side deliverables BEFORE Builder dispatch

Three artifacts to produce architect-side; Builder gets a tight brief once these land:

1. **`docs/architecture/auth-policy.md` (F29 ADR)** — narrative-quality writing about the policy decision + existence-disclosure rationale + alternatives considered + consequences for future contributors. ~80-120 lines.
2. **Videos/Vision findings nesting design** — specific decision: top-level section vs nested-under-videos for Vision findings (mobile viewer's per-video-expansion UX from Phase 191B suggests nested; PDF's "Vision findings" cross-video summary suggests peer-section — pick one and document why); empty-state conventions matching Phase 182's existing patterns (audit before introducing new). Lands as inline design notes in `docs/architecture/report-document-shape.md`.
3. **`docs/architecture/report-document-shape.md`** — documents Phase 182's existing dict shape conventions inline with this phase. Free byproduct of architect understanding the shape well enough to extend it. Future contributors extending further don't re-derive conventions. Sections covered: top-level fields (title, subtitle, issued_at, sections list, footer); section types (rows, bullets, table, body); empty-state conventions (omit section vs render with placeholder vs always-present); naming patterns; relationship to Phase 192's videos/Vision findings extension.

Builder dispatch is MORE attractive under reshape (a) than under plan v1.0 — mechanical work against documented shape conventions + clear architectural target. Architect produces the three artifacts above; Builder extends `build_session_report_doc()` + adds tests against Phase 191B seeded video fixtures.

### Updated commit plan (4 commits, was 5)

**Commit 1** — Architect lands the three architecture artifacts (F29 ADR + report-document-shape.md + videos nesting design embedded in report-document-shape.md). Backend extends `build_session_report_doc()` per the design. Pytest extension tests cover videos/Vision findings sections against Phase 191B seeded fixtures. pyproject 0.3.1 → 0.3.2.

**Commit 2** — Mobile `useReport` hook + types (against existing `/v1/reports/session/{id}` endpoint; openapi-typescript regenerates types from existing OpenAPI snapshot, NOT from new schema).

**Commit 3** — Mobile `ReportViewerScreen` + `SectionToggle` + `ReportCard` (all 6 cards, all I1-I9 placeholder/empty-state policy, section-toggle preset, 30s focus-debounce, pull-to-refresh, stuck-in-analyzing surface).

**Commit 4** — Mobile cross-link from SessionDetailScreen + nav registration + finalize (collapsed from plan v1.0's separate Commits 4 + 5 since reshape eliminated enough work to merge them).

### Updated versioning targets at v1.1 finalize

Unchanged from plan v1.0:
- Backend `pyproject.toml`: 0.3.1 → 0.3.2.
- Backend `implementation.md`: 0.13.10 → 0.13.11.
- Mobile `package.json`: 0.0.9 → 0.0.10.
- Mobile `implementation.md`: 0.0.11 → 0.0.12.
- Schema unchanged at v39.

### Why this amendment lands BEFORE Commit 1 (not as a v1.0.1 post-finalize amendment like 191D's was)

191D's v1.0.1 amendment was lessons-learned recording AFTER finalize — fresh-recall discipline. 192's v1.0.1 amendment is a pre-build reshape — discovered architectural mismatch between plan and reality at architect-side-survey time. Different timing because different purpose:

- 191D's amendment: corrections + reusable methodology after the work is done.
- 192's amendment: scope reshape after pre-build deep-survey but BEFORE the work starts.

Both are "v1.0.1" by convention but the difference matters: 192's reshape would be a much more expensive correction if applied mid-Commit-1 (would mean reverting work, re-dispatching) or post-finalize (would mean fixing the calcified parallel surface). Pre-Commit-1 is the cheapest correction point; pre-build deep-survey is what makes the cost asymmetry visible early.

---

Build the mobile-side substrate viewer for diagnostic session reports — comprehensive read-only surface combining vehicle context + symptoms + fault codes + AI diagnosis + Vision findings + lifecycle audit. Lay the composition layer + section-toggle preset system with PDF/share as known downstream consumers (Phase 192B). First user-facing read-and-share surface in the app, after a long substrate-then-feature-then-meta-tooling stretch through Phases 191/191B/191C/191D.

CLI: none new (mobile screen + backend endpoint).

Outputs: `ReportViewerScreen` on SessionsStack + cross-link from SessionDetailScreen + `useReport(sessionId)` hook + `motodiag.api.report_composer.compose(session_id)` Python module + `GET /v1/sessions/{id}/report` FastAPI route.

**Scope honesty**: despite the "viewer" framing, this phase has **~30% backend scope** — single new GET endpoint + composer module + composer pytest suite + route integration tests. Pre-plan Decision B made this explicit; plan-of-record reflects it.

## Scope decisions locked at pre-plan Q&A (2026-05-05)

All A through I + cross-cutting placeholder review accepted with refinements:

- **A — Substrate-feature boundary**: (a) 192 = viewer + composition layer + section-toggle state; 192B = PDF route + Share Sheet integration only. Composition layer testable independently of both viewer + PDF consumers — `report_composer.compose(session_id) → ReportPayload` gets its own pytest suite that doesn't go through HTTP. Decoupled at the start so the composition module doesn't tightly couple to its first consumer.
- **B — Mobile composition / data-fetch shape**: (i) new `GET /v1/sessions/{id}/report` endpoint; backend composes `ReportPayload`; one mobile fetch; PDF route at 192B consumes the same composer.
- **C1 — Toggle granularity**: (γ) data shape with (β) UX. Per-card override map is data-model source of truth; UI exposes only Customer-facing / Insurance-facing presets at first; future "expose per-card UI" F-ticket adds advanced affordance without touching state shape.
- **C2 — Toggle state location**: (ε) session-only (component state). **F28** filed with measurable trigger: per-mechanic preset preference persistence escalates to its own ticket if 192B smoke gate or first 2 weeks of usage surface "every share + close + re-open re-prompts preset" as friction.
- **C3 — Default visibility**: (η) full-surface (Insurance-facing preset) default. No auto-detection — mis-categorizing as insurance-related leaks billing info into customer renders.
- **D — Incomplete Vision rendering**: (iii) filter-with-count. Pre-defined stuck-in-analyzing edge: 5-min threshold; count display becomes "(1 of 3 analyzed, 1 stuck — tap to retry)" with stuck count in amber; retry affordance with explicit "report stuck analysis" surface.
- **E — Backend route surface**: (a) two distinct routes (`.json` for viewer at 192, `.pdf` at 192B). Auth posture: `require_api_key` + `session_owner_or_shop_tier`; tier requirement zero (reading own report is base-tier). **F29** filed: ADR-shape document "read access doesn't gate on tier; create access does" emergent rule across Phase 188/189/191B/192.
- **F — Template engine** (192B-scope, sketched here): Jinja2 — already a transitive FastAPI dep; zero new deps. Note for 192B: WeasyPrint CSS support is good but not perfect — flexbox supported, CSS Grid partial, complex transforms fail silently. Design template on conservative CSS (block + flex + table; no Grid).
- **G — Smoke-gate rhythm**: visual/UX-heavy rather than data-heavy; recovers user-facing-surface-delivery discipline after the integration-heavy Track I run. 192 viewer single-architect-session smokeable (~30-45 min, no live API calls). Step 9 added: composition layer regression sweep — pytest tests against 3-4 distinct seeded sessions BEFORE any UI testing (catches composer regressions before they surface as silent UI rendering issues). 192B Step 8 added: deterministic-rendering verification — generate same session's PDF twice with same preset, byte-compare for identical output.
- **H — Branch + commit cadence**: separate branches per phase (`phase-192-diagnostic-report-viewer` + `phase-192B-report-pdf-share`), rebase-merge at finalize. 192 Commit 1 includes FastAPI TestClient integration tests so Commit 2's mobile work proceeds against known-working contract.
- **I1 — No fault codes**: (b) "No fault codes recorded for this session" placeholder.
- **I2 — No diagnosis yet**: (b) with copy "Diagnosis not yet generated. N of 2 symptoms recorded; add (2-N) more to enable AI diagnosis."
- **I3 — No videos at all**: (a) hide videos card entirely when zero. Composer omits the videos field; no explicit hide-logic mobile-side.
- **I4 — Lifecycle**: as written; PDF metadata band (192B) includes "Report generated YYYY-MM-DD HH:MM EDT while session was [open/closed]".
- **I5 — Network failure**: (a) error state with retry. **Open question**: does Phase 187's `describeError` already distinguish network-unreachable vs backend-unreachable? If not, file as small cross-cutting error-state polish F-ticket (provisionally F31 — to be confirmed during build).
- **I6 — Backend 404**: (a) framing with refined copy: "This session is no longer available. It may have been deleted." + Back-to-sessions affordance.
- **I7 — Auth 401**: (b) error state with copy: "Your API key is no longer valid. Re-enter your key via Home → API key card to continue." Inherit Phase 187's existing pattern if it covers the case; otherwise this is the spec.
- **I8 — No symptoms yet**: (b) symmetric with I2. Copy: "No symptoms recorded yet. Add symptoms via SessionDetail → Symptoms."
- **I9 — Empty composer payload (defensive)**: (a) "Report unavailable for this session" + retry + `console.warn` logline including session ID + user ID + timestamp + structural shape of malformed payload (missing fields, unexpected nulls). **F30** filed: emit backend telemetry event when defensive empty-payload case fires, so composer regressions surface in backend logs not just frontend ones.
- **I10 — Focus re-fetch**: (b) 30-second debounce — re-fetch on focus only if last fetch >30s ago. Pull-to-refresh remains as explicit force-refresh for "something changed, fetch now" cases. Round-trip cost discipline per Phase 188 HVE saga.
- **Cross-cutting placeholder copy review**: 10-minute voice/tone pass during plan v1.0 writing; all placeholder strings pulled into a single section + reviewed as a coherent set. See "Placeholder copy register" below.

## Outputs

### New files

**Backend (~5):**
- `src/motodiag/api/models/report.py` — `ReportPayload` Pydantic model + `ReportSection` enum + per-card sub-models (`ReportVehicleCard`, `ReportSymptomsCard`, `ReportFaultCodesCard`, `ReportDiagnosisCard`, `ReportVideosCard`, `ReportLifecycleCard`).
- `src/motodiag/api/report_composer.py` — `compose(session_id, db_path) → ReportPayload` pure function. Reads from session_repo + video_repo + diagnosis surface + lifecycle. **No HTTP layer dependency**; testable directly via the composer's own pytest suite.
- `src/motodiag/api/routes/reports.py` — FastAPI router with `tags=["reports"]` (the `reports` tag already exists in TAG_CATALOG — Phase 183 forward-looking placeholder claimed at last). `GET /v1/sessions/{id}/report` route consumes `report_composer.compose()` + returns the `ReportPayload` JSON.
- `tests/test_phase192_report_composer.py` — composer pytest suite (~10-12 tests across 3-4 fixture sessions: full, empty/early-stage, incomplete-Vision, mixed-analysis-states).
- `tests/test_phase192_report_route.py` — FastAPI TestClient integration tests for the route (~6-8 tests covering happy path + 401 + 403-cross-owner + 404 + tier-bypass-on-read regression guard).

**Mobile (~6):**
- `src/screens/ReportViewerScreen.tsx` — top-level viewer screen on SessionsStack. Renders the 6 cards (Vehicle / Symptoms / Fault Codes / Diagnosis / Videos / Lifecycle) per the section-toggle preset; section-toggle UI in screen header; pull-to-refresh; loading + error + empty states.
- `src/components/report/SectionToggle.tsx` — preset switcher component (Customer-facing / Insurance-facing). Single visible affordance; per-card override map is the underlying state but the UI exposes only the two presets.
- `src/components/report/ReportCard.tsx` — shared card-shaped wrapper used by all 6 sections (consistent padding, header, expand/collapse semantics if any, empty-state placeholder rendering policy).
- `src/hooks/useReport.ts` — fetches `ReportPayload` from `/v1/sessions/{id}/report`. Includes 30s focus-debounce per I10 + pull-to-refresh + polling integration with existing `useSessionVideos` for incomplete-Vision count updates.
- `src/types/report.ts` — re-exports the openapi-typescript-generated `ReportPayload` types as named aliases for consumers (mirrors Phase 188's pattern for SessionResponse types).
- `__tests__/hooks/useReport.test.ts` — Jest tests for the hook (~8-10 tests covering fetch happy path + 30s debounce + pull-to-refresh + 401/404/network errors + polling-integration smoke).

### Modified files

**Backend (~3):**
- `src/motodiag/api/__init__.py` — register the new `reports` router.
- `src/motodiag/api/app_factory.py` (or wherever routers attach) — include reports router under `/v1/sessions` prefix-overlay.
- `api-schema/openapi.json` — refresh after backend changes (mobile regenerates types from this).

**Mobile (~4):**
- `src/navigation/SessionsStack.tsx` — register `ReportViewerScreen` route.
- `src/navigation/types.ts` — add `ReportViewerScreen` route param-list entry.
- `src/screens/SessionDetailScreen.tsx` — add "View report" CTA (cross-link to ReportViewerScreen with sessionId param). Placement: footer of the screen, below all 6 content cards, above lifecycle card if it stays at the bottom. Visual: secondary-button style.
- `src/api-types.ts` — regenerate via `npm run generate-api-types` after backend openapi.json refresh.

## Logic

### Backend `report_composer.compose(session_id, db_path) → ReportPayload`

Pure function — no HTTP layer dependency. Reads from existing repos:

1. **Vehicle card**: `session_repo.get_session(session_id)` → vehicle make/model/year/protocol/powertrain + Phase 188 metadata (battery chemistry / engine type / etc.).
2. **Symptoms card**: `session_repo.get_session_symptoms(session_id)` → list of symptom rows (text + severity + recorded_at).
3. **Fault codes card**: `session_repo.get_session_fault_codes(session_id)` → list of fault code rows (code + make/family + recorded_at). Empty list = "No fault codes" placeholder per I1.
4. **Diagnosis card**: `session_repo.get_session_diagnosis(session_id)` → diagnosis text + AI model + tokens + cost + generated_at. None/empty = "Diagnosis not yet generated. N of 2 symptoms recorded..." placeholder per I2.
5. **Videos card**: `video_repo.list_session_videos(session_id)` → list of video rows. **Empty list = composer omits the videos field entirely** per I3 (the mobile renderer hides the card when the field is absent; no explicit hide-logic mobile-side).
6. **Lifecycle card**: `session_repo.get_session(session_id).status / created_at / closed_at` + (per F3 deferred lifecycle history work) any reopen events.

**Section override-map state** is NOT composer responsibility — composer always returns the full payload; mobile's section-toggle-state filters at render time. PDF route at 192B will accept a `?sections=...` query param to filter at composer-output time, but that's 192B scope. **Composer at 192 returns everything**; mobile selects what to show.

**Stuck-in-analyzing edge**: composer doesn't compute "stuck" state; it returns each video's `analysis_state` + `analyzing_started_at` timestamps. **Mobile-side computes stuck**: any video with `analysis_state === 'analyzing'` AND `(now - analyzing_started_at) > 5min` is rendered as stuck.

### Backend `GET /v1/sessions/{id}/report` route

- Auth: `require_api_key` + `session_owner_or_shop_tier_member` (existing Phase 187/188 pattern).
- **Tier requirement: zero.** Reading own session is base-tier. Smoke gate has explicit free-tier-user-can-read-own-report-but-not-other-users test (Section E refinement) — tier-bypass-on-read is exactly the auth edge that gets accidentally tightened during refactors.
- Response: `ReportPayload` JSON (Pydantic model serialized).
- Error responses:
  - 401: invalid/missing API key (existing Phase 187 ProblemDetail envelope).
  - 403: session-owner check fails AND user is not a shop-tier member of the session's shop (existing Phase 188 cross-owner pattern).
  - 404: session not found (or soft-deleted).
  - 5xx: backend error; mobile renders defensive empty-payload state per I9.
- **No tier-bypass-on-read**. Smoke must include explicit test confirming free-tier user can fetch their own session's report.

### Mobile `useReport(sessionId)` hook

```ts
function useReport(sessionId: number): {
  report: ReportPayload | null;
  isLoading: boolean;
  error: ReportError | null;
  refresh: () => Promise<void>;     // pull-to-refresh
};
```

- Fetch on mount.
- **30-second focus-debounce per I10**: tracks `lastFetchAt` timestamp; on `useFocusEffect` re-entry, re-fetch only if `(now - lastFetchAt) > 30000`.
- Pull-to-refresh always re-fetches (overrides debounce — explicit user action).
- **Polling integration with `useSessionVideos`**: viewer reads videos via the report payload, but `useSessionVideos` already polls every 5s while any video is `pending`/`analyzing`. Viewer subscribes to `useSessionVideos`'s polled state for the videos card section; the hook re-renders when polled state updates the video rows. Reduces redundant fetches (don't re-fetch the entire report just because one video moved `analyzing` → `analyzed`).
- Error handling: 401 → re-auth flow per I7 (error-state copy directs to Home → API key); 404 → soft-deleted-session copy per I6; network failure → retry-button per I5.

### Mobile `ReportViewerScreen.tsx` rendering policy

Top-down render order (post-section-toggle filter):

1. Vehicle card (always shown unless toggle hides; default = shown)
2. Symptoms card (per I8 placeholder if empty)
3. Fault codes card (per I1 placeholder if empty)
4. Diagnosis card (per I2 placeholder if pending)
5. Videos card (per I3 hidden when zero videos)
6. Vision findings card (per I3 + D filter-with-count; stuck-in-analyzing surface per D refinement)
7. Lifecycle card (always shown; rendering per I4)

**SectionToggle component** (header):
- Two pill buttons: "Customer-facing" + "Insurance-facing" (default selected).
- Selecting changes the underlying override map; viewer re-renders with section visibility per the override map.

**Section override map state shape** (per C1 (γ) data shape with (β) UX):
```ts
type ReportOverrideMap = {
  vehicle: boolean;
  symptoms: boolean;
  faultCodes: boolean;
  diagnosis: boolean;
  videos: boolean;
  visionFindings: boolean;
  lifecycle: boolean;
};

const PRESETS: Record<'customer' | 'insurance', ReportOverrideMap> = {
  customer: {
    vehicle: true,
    symptoms: true,
    faultCodes: true,
    diagnosis: true,
    videos: true,
    visionFindings: true,
    lifecycle: false,  // hide audit trail from customer view
  },
  insurance: {
    vehicle: true,
    symptoms: true,
    faultCodes: true,
    diagnosis: true,
    videos: true,
    visionFindings: true,
    lifecycle: true,
  },
};
```

Future per-card UI (deferred to F-ticket): expose checkbox-per-card; underlying state shape unchanged. The deferral is purely UI work, not architectural.

### Section override → 192B PDF query param

192B's `/v1/sessions/{id}/report.pdf` will accept `?sections=vehicle,symptoms,faultCodes,...` query param. Mobile sends current override map at export time; backend composer filters before PDF render. Pre-plan note for 192B: query-param shape design (CSV vs repeated keys vs comma-list) — defer to 192B implementation, but the route contract IS established here in 192's route-surface section.

### Stuck-in-analyzing detection (mobile-side, per D refinement)

For each video in the report payload:
- If `analysis_state === 'analyzed'` → render in findings inline.
- If `analysis_state === 'analyzing'` AND `(now - analyzing_started_at) <= 5min` → counted as analyzing (not stuck); count surface "(1 of 3 analyzed)".
- If `analysis_state === 'analyzing'` AND `(now - analyzing_started_at) > 5min` → **stuck**; counted in amber "stuck" subcount; tap-to-retry affordance (calls existing Phase 191B `POST /v1/sessions/{id}/videos/{vid}/retry-analysis` if the route exists; otherwise file F-ticket).
- If `analysis_state === 'analysis_failed'` → counted as failed (separate from stuck); failure-mode subcount with retry affordance.
- If `analysis_state === 'pending'` → counted as pending (waiting for worker); no retry needed.

Display string: `"Vision findings (1 of 3 analyzed, 1 stuck — tap to retry, 1 pending)"` — variable formatting based on which subcounts are non-zero.

### Placeholder copy register (cross-cutting voice/tone review)

Per the cross-cutting refinement: all placeholder copy reviewed together as a coherent set. Voice rules:

1. **Lead with state, then action.** "Diagnosis not yet generated. Add 1 more symptom..." not "Add 1 more symptom to generate diagnosis."
2. **Terminology: always "session"**. Never "diagnostic session" / "report" / "case" interchangeably. The word "report" is reserved for the export artifact (PDF), not the in-session diagnostic context.
3. **Informative + action-oriented + not chatty**. No "Oops!" / "It looks like..." / "Try again later". Direct sentences.
4. **Reference exact UI affordances by name**. "Re-enter your key via **Home → API key card**" (capitalized + arrow + named tab/card). Future-contributor + user can navigate exactly there.
5. **Numbers spelled in numerals when ≤ 100**, words above. "Add 1 more symptom" not "Add one more symptom"; "Reports generated over the last hundred days..." (if ever).

Full register (every placeholder string in 192's UI):

| Where | String |
|---|---|
| I1 fault codes empty | "No fault codes recorded for this session." |
| I2 diagnosis pending (with N=count of recorded symptoms < threshold of 2) | `"Diagnosis not yet generated. ${N} of 2 symptoms recorded; add ${2-N} more to enable AI diagnosis."` |
| I8 symptoms empty | "No symptoms recorded yet. Add symptoms via SessionDetail → Symptoms." |
| I3 videos hidden | (no string — card hidden when zero videos) |
| I3 + D Vision findings empty (videos exist, none analyzed yet) | `"Vision findings (0 of ${N} analyzed)."` |
| D Vision findings with stuck/pending mix | `"Vision findings (${A} of ${N} analyzed, ${S} stuck — tap to retry, ${P} pending)."` (variable formatting; each subcount block omitted when zero) |
| D stuck-tap-to-retry tap result success | "Analysis retry queued." |
| D stuck-tap-to-retry tap result failure | "Couldn't queue retry. Check connection and try again." |
| I5 network failure | "Couldn't load report. Check your connection and tap retry." (button: "Retry") |
| I6 404 | "This session is no longer available. It may have been deleted." (button: "Back to sessions") |
| I7 401 | "Your API key is no longer valid. Re-enter your key via Home → API key card to continue." |
| I9 defensive empty payload | "Report unavailable for this session." (button: "Retry") |
| Loading state (during fetch) | (no string — spinner only; matches Phase 189/190/191/191B convention) |
| Pull-to-refresh trigger | (no string — RN refresh-control default) |

**Voice/tone consistency check**: all 11 strings lead with state ("No fault codes...", "Diagnosis not yet generated...", "This session is no longer available...", etc.); all use "session" not "diagnostic session"; all have action affordances named explicitly where applicable; all numbers are numerals; no chatty filler. Coherent set. ✓

## Key Concepts

- **Composition layer as decoupling primitive**: `report_composer.compose(session_id)` is independent of viewer + PDF consumers. Pytest suite tests `compose()` directly without HTTP layer; route + PDF route both call into the same module. Per A's boundary-tightening note.
- **Override map state shape vs UI affordance**: data model designed for per-card override (γ) from day one, but UI affordance ships as 2-preset switcher (β). Future per-card UI is purely UI work, not architectural migration. Per C1's pushback.
- **Round-trip cost discipline**: 30s focus-debounce per I10 (Phase 188 HVE saga lesson — round-trips on slow shop wifi compound; default to debounce, not refresh-on-every-focus). Pull-to-refresh stays as explicit force-refresh affordance.
- **Tier-bypass-on-read auth pattern**: Phase 188/189/191B/192 all share "read access doesn't gate on tier; create access does." F29 formalizes as ADR-shape doc to prevent accidental tightening.
- **Voice/tone coherence as cross-cutting concern**: all placeholder copy reviewed together as a set, not per-card-in-isolation. Same discipline as 191D opt-out reasons. The viewer is a polished user-facing surface; coherent voice is the polish.
- **Defensive empty-payload + telemetry**: I9's `console.warn` logline carries enough structural detail (session ID, user ID, timestamp, malformed-payload shape) to trace composer regressions. F30 escalates to backend telemetry event for production observability.

## Verification Checklist

- [ ] `report_composer.compose(session_id, db_path)` returns `ReportPayload` for full / empty / incomplete-Vision / mixed-analysis-states fixture sessions; pytest suite passes ~10-12 tests
- [ ] Composer omits the videos field entirely when session has zero videos (per I3)
- [ ] Composer returns symptoms/fault-codes as empty lists (not None) when none recorded
- [ ] Composer returns diagnosis as None when not yet generated; mobile renders I2 placeholder with N-of-2 count
- [ ] Composer returns lifecycle with full `created_at`/`closed_at`/reopen events when applicable
- [ ] `GET /v1/sessions/{id}/report` route happy path: returns ReportPayload JSON with all 6 cards
- [ ] Route 401: invalid API key returns ProblemDetail
- [ ] Route 403: cross-owner read attempt returns ProblemDetail (session-owner-or-shop-tier-member check)
- [ ] Route 404: nonexistent / soft-deleted session returns ProblemDetail
- [ ] **Route tier-bypass-on-read**: free-tier user fetches own session's report → 200 OK (regression guard for the F29 pattern)
- [ ] Route integration tests pass (~6-8 tests via FastAPI TestClient)
- [ ] Mobile `useReport` hook fetches on mount; updates state; renders content
- [ ] Mobile `useReport` 30s focus-debounce: re-entry within 30s does NOT trigger re-fetch; re-entry after 30s DOES trigger re-fetch
- [ ] Mobile `useReport` pull-to-refresh always triggers re-fetch (overrides debounce)
- [ ] Mobile `useReport` polls via `useSessionVideos` for video state updates (verified by smoke that "1 of 3 analyzed" auto-increments to "2 of 3" without manual refresh)
- [ ] `ReportViewerScreen` renders all 6 cards in correct order
- [ ] `ReportViewerScreen` SectionToggle: tapping Customer-facing hides lifecycle; tapping Insurance-facing shows lifecycle; default = Insurance-facing on first render
- [ ] `ReportViewerScreen` correctly renders all 11 placeholder strings (per the placeholder copy register) when triggering each empty/error state
- [ ] `ReportViewerScreen` renders stuck-in-analyzing state correctly: amber subcount, tap-to-retry affordance, retry success queues + UI updates
- [ ] Cross-link from `SessionDetailScreen` → `ReportViewerScreen` works; back-button stack semantics preserved
- [ ] Mobile `useReport` 401 handling: surfaces I7 copy with Home → API key card direction
- [ ] Mobile `useReport` 404 handling: surfaces I6 copy with Back-to-sessions button
- [ ] Mobile `useReport` network failure handling: surfaces I5 copy with Retry button
- [ ] Mobile `useReport` defensive empty-payload handling: surfaces I9 copy + emits structured `console.warn` logline including session ID + user ID + timestamp + malformed-payload shape
- [ ] `useReport.test.ts` passes (~8-10 tests)
- [ ] `ReportViewerScreen.test.ts` passes
- [ ] Mobile Jest 293 + new tests all green
- [ ] `npm run generate-api-types` regenerates types after backend openapi.json refresh
- [ ] No regression: full backend Phase 191D + Phase 191C + Phase 175-184 sweep clean; mobile Jest 293+ all green
- [ ] Backend `pyproject.toml` 0.3.1 → 0.3.2 (patch bump — extends API surface; no breaking changes)
- [ ] Backend `implementation.md` 0.13.10 → 0.13.11
- [ ] Mobile `package.json` 0.0.9 → 0.0.10
- [ ] Mobile `implementation.md` 0.0.11 → 0.0.12
- [ ] Backend + mobile READMEs updated with viewer + (forward-pointing) PDF/share notes
- [ ] Mobile FOLLOWUPS: F28 + F29 + F30 + (provisional F31) filed at finalize

## Risks

- **Composition layer tight-coupling to first consumer**. The viewer ships first; PDF route at 192B is the second consumer. Risk: composer module accumulates viewer-specific concerns (e.g., section-override-map handling) that don't belong in the composer. Mitigation: per A's boundary-tightening note, composer's pytest suite tests `compose(session_id)` directly without HTTP layer; if a test requires HTTP-layer concerns to set up, that's a coupling smell to fix immediately.
- **Round-trip count surprises**. Viewer + `useSessionVideos` polling could trigger redundant fetches if the integration is wrong (e.g., poll triggers full report re-fetch instead of just video card update). Mitigation: smoke gate Step 9 (composition layer regression sweep) + explicit smoke step verifying poll-driven count increment doesn't re-fetch the report.
- **Section-toggle UX confusion**. Two presets ("Customer-facing" + "Insurance-facing") might not communicate clearly to mechanics what each preset hides. Mitigation: preset-button copy includes a one-line description ("hides cost details" / "full audit trail"); first-time-user toast on first preset toggle. Smoke gate verifies the description text renders.
- **Stuck-in-analyzing retry route doesn't exist yet**. Phase 191B added analysis but no explicit retry endpoint — `POST /v1/sessions/{id}/videos/{vid}/retry-analysis` may need to be added in 192. Mitigation: pre-build verify if the route exists; if not, **add the retry route as part of 192's backend scope** (small extension, ~30 LoC + 1-2 tests). If the route is genuinely out-of-scope, file F-ticket and render the stuck-in-analyzing affordance as info-only (no retry button) until the route ships.
- **Open question on `describeError` network-vs-backend distinction**. I5 noted: if Phase 187's `describeError` doesn't distinguish network-unreachable from backend-unreachable, the error copy degrades. **Pre-build action**: verify `describeError` shape during Commit 1 / 2; if the distinction isn't there, file F31 as small cross-cutting error-state polish. Don't expand 192's scope to add it; just track.
- **CSS Grid in PDF template (192B-deferred risk)**. WeasyPrint's CSS Grid support is partial; complex templates fail silently. 192's viewer-side rendering is unaffected (RN doesn't use CSS Grid anyway), but 192B's template MUST stay on conservative CSS (block + flex + table). Pre-plan note for 192B: design template assuming Grid is unavailable.
- **Phase 187 `ApiKeyModal` re-entry from viewer**. I7's auth-401 handling sends user to "Home → API key card" but the viewer's deep-link / back-button stack might not preserve correctly when user navigates away. Mitigation: verify back-button-from-Home returns to ReportViewerScreen (not to root SessionsStack) after API key re-entry. Manual smoke step.

## Commit plan

5 commits on `phase-192-diagnostic-report-viewer` branch. Backend-first to establish contract before mobile work proceeds.

**Commit 1 — Backend composer + route + tests** (backend-only). New `report_composer.py` + `models/report.py` + `routes/reports.py` + composer pytest suite + route integration tests. **Composer pytest suite passes against fixture sessions BEFORE the route is merged** — that's the boundary-decoupling gate (per A's refinement). Includes the `tags=["reports"]` claim on the existing TAG_CATALOG entry. Plus F29 ADR file `docs/architecture/auth-policy.md` documenting the read-access-doesn't-gate-on-tier rule (small ADR, ~30 lines). pyproject 0.3.1 → 0.3.2.

**Commit 2 — Mobile useReport hook + types** (mobile-only). `useReport.ts` + `src/types/report.ts` + `src/api-types.ts` regenerated from refreshed `api-schema/openapi.json` + `useReport.test.ts`. Hook compiled + tested in isolation before viewer screen consumes it.

**Commit 3 — Mobile ReportViewerScreen + SectionToggle + ReportCard** (mobile-only). Top-level screen + section-toggle component + shared card wrapper. Renders all 6 cards with placeholder/empty-state policy per I1-I9 + section-toggle preset + 30s focus-debounce + pull-to-refresh + stuck-in-analyzing surface per D refinement.

**Commit 4 — Mobile cross-link from SessionDetailScreen + nav registration** (mobile-only). `ReportViewerScreen` registered on SessionsStack; "View report" CTA added to SessionDetailScreen. Back-button stack verified.

**Commit 5 — Finalize** (both repos). Mobile Jest + backend pytest sweep green. Move plan docs in_progress → completed. Backend `implementation.md` 0.13.10 → 0.13.11. Mobile `implementation.md` 0.0.11 → 0.0.12. Mobile `package.json` 0.0.9 → 0.0.10. ROADMAP marks ✅ on both repos. Mobile FOLLOWUPS: file F28 + F29 + F30 + provisional F31. Pattern doc untouched (no new F9 instances surfaced; this is a pure-feature phase).

Each commit: backend Phase 192 tests green + Phase 175-184 sample regression clean before next; mobile `npx eslint` green + Jest green at Commit 5.

## Architect gate (smoke shape per Section G)

**192 viewer smoke-gate (single-architect-session, ~30-45 min). Visual/UX-heavy.**

Steps:
1. Open existing diagnostic session in viewer; verify all 6 cards render (vehicle, symptoms, fault codes, diagnosis, videos, lifecycle); default preset = Insurance-facing.
2. Toggle preset between Customer-facing and Insurance-facing; verify lifecycle card hides on Customer-facing; section visibility matches preset; default Insurance-facing on first render.
3. Session with incomplete Vision analysis: verify findings count "(N of M analyzed)"; verify only analyzed videos appear inline; verify count auto-updates on poll-complete (driven by `useSessionVideos` polling integration) WITHOUT triggering full report re-fetch.
4. Session with stuck-in-analyzing video (>5 min in analyzing state): verify amber stuck-count + tap-to-retry; tap retry; verify analysis re-queued + UI updates.
5. Empty/early-stage session (zero symptoms, zero diagnosis, zero videos): verify videos card hidden (per I3); verify symptoms placeholder per I8; verify diagnosis placeholder per I2 with N-of-2 count.
6. Session with no fault codes but other content: verify fault codes card renders with I1 placeholder.
7. **Free-tier user fetches own session's report → 200 OK** (regression guard for F29 tier-bypass-on-read pattern). Smoke covers via test API key with individual-tier user.
8. Cold-relaunch from viewer: verify state hydration; no "loading forever" hangs; verify default preset = Insurance-facing on cold-relaunch (state didn't persist from prior session — per C2 (ε)).
9. **Composition layer regression sweep BEFORE UI testing** (Section G addition): `pytest tests/test_phase192_report_composer.py` against 3-4 distinct seeded sessions (full / empty / incomplete Vision / mixed analysis states); all pass. Catches composer regressions before they surface as silent UI rendering issues.
10. Pull-to-refresh: verify re-fetch + UI update.
11. 30s focus-debounce: nav out and back to viewer within 30s; verify NO re-fetch (network panel quiet); nav out and back AFTER 30s; verify re-fetch fires.
12. Tap a video card: navigates to existing VideoPlayback; back button returns to viewer; viewer state preserved.
13. Cross-link from SessionDetailScreen "View report" CTA → ReportViewerScreen; back button returns to SessionDetailScreen; back-button stack correct.
14. Bottom-tab nav out and back; viewer state preserved.
15. Network failure simulation (turn off wifi mid-fetch): verify I5 error state with retry; tap retry on connection restore; verify happy path resumes.
16. Backend 404 simulation (delete session via CLI mid-session): verify I6 copy on next refresh + Back-to-sessions affordance.
17. Auth 401 simulation (revoke API key mid-session): verify I7 copy directing to Home → API key card.

**No live API calls. No cost validation.** Cost: $0.

## Versioning targets at v1.1 finalize

- Backend `pyproject.toml`: `0.3.1 → 0.3.2` (patch — extends API surface; no breaking changes).
- Backend project `implementation.md`: `0.13.10 → 0.13.11`.
- Schema: unchanged at v39.
- Mobile `package.json`: `0.0.9 → 0.0.10`.
- Mobile project `implementation.md`: `0.0.11 → 0.0.12`.

## Not in scope (firm)

- **PDF generation / Share Sheet / AirDrop**. All 192B scope. 192 ships viewer + composer + route only.
- **Per-card section toggle UI**. Data shape (override map) ships in 192 per C1 (γ); UI affordance is 2-preset only. Future "advanced toggle" F-ticket adds checkbox-per-card UI without state-shape migration.
- **Per-mechanic preset preference persistence**. F28 deferred per C2 (ε). Session-only state in 192; revisit at 192B if smoke surfaces friction.
- **Auto-detect preset from session metadata**. Rejected per C3 — mis-categorization leaks billing info.
- **Cached fallback on network failure**. Rejected per I5 — error state with retry only.
- **Automatic re-auth flow on 401**. Rejected per I7 — direct user to Home → API key card; no modal-during-viewer-entry surprise.
- **Backend telemetry event on defensive empty-payload**. F30 deferred. 192 emits frontend `console.warn` logline only.
- **Lifecycle history (close/reopen as timeline rather than pure-state)**. F3 (Phase 189 follow-up) — out of 192 scope. Lifecycle card renders current pure-state per Phase 189's existing data model.
- **WeasyPrint CSS template work**. All 192B scope.

## FOLLOWUPS update at finalize

- **F28 (NEW)** — Per-mechanic preset preference persistence. Trigger: 192B smoke gate or first 2 weeks of usage surface "every share + close + re-open re-prompts preset" as friction.
- **F29 (NEW)** — Auth policy ADR documenting "read access doesn't gate on tier; create access does" emergent rule across Phase 188/189/191B/192 read endpoints. ADR-shape F-ticket. **Lands in Commit 1** (backend) as `docs/architecture/auth-policy.md` — promoted from F-ticket to in-phase deliverable because (a) it's small, (b) Commit 1 is touching the auth-on-route surface anyway, (c) it prevents accidental tightening between 192 ship and the next phase.
- **F30 (NEW)** — Backend telemetry event when defensive empty-payload case fires. Forward-looking observability.
- **F31 (provisional, confirmed during build)** — `describeError` network-vs-backend-unreachable distinction. Pre-build verify if the existing implementation covers; file F31 if not.

## Smoke test (architect-side, post-build, pre-v1.1)

(Same as the Architect gate above — Phase 192's gate IS the smoke. ~17 steps, ~30-45 min, single-architect-session.)
