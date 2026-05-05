# Phase 192 — Phase Log

**Status:** 🚧 In Progress | **Started:** 2026-05-05
**Repo:** https://github.com/Kubanjaze/moto-diag (backend) + https://github.com/Kubanjaze/moto-diag-mobile (mobile)
**Branch:** `phase-192-diagnostic-report-viewer` (created in BOTH repos at plan v1.0; 5 commits planned with file overlap split per Outputs section)

---

### 2026-05-05 — Plan v1.0 written

Phase 192 opens as the first pure-feature-work phase after the long substrate-then-feature-then-meta-tooling stretch through Phases 191 / 191B / 191C / 191D. Diagnostic report viewer is the substrate half of a substrate-then-feature pair; Phase 192B will add PDF export + Share Sheet/AirDrop.

**Pre-plan Q&A architect-side** (no Plan agent dispatched per Kerwyn's discipline: pre-plan Q&A is highest-judgment-density work in the chain; Plan agents produce form-fill surfaces but don't replace the review pass that catches second-order implications).

**8 sections (A-H) + 1 added section (I) + 1 cross-cutting concern**, all locked before plan v1.0 written:

- **A**: substrate-feature boundary (a) — composition layer testable independently of viewer + PDF route via own pytest suite (no HTTP).
- **B**: mobile fetch shape (i) — new GET endpoint + composer module; ~30% backend scope honestly called out in plan despite "viewer" framing.
- **C1**: toggle granularity — pushback from Kerwyn: ship (γ) data shape with (β) UX. Per-card override is data-model question; designing override-map from day one means future per-card UI is purely UI work, not architectural migration.
- **C2**: state location (ε) session-only with F28 filed as concrete trigger ("every share + close + re-open re-prompts preset" friction).
- **C3**: default visibility (η) full-surface; no auto-detection — mis-categorization leaks billing info.
- **D**: incomplete Vision (iii) filter-with-count, with Kerwyn's refinement: 5-min stuck threshold pre-defined; "(1 of 3 analyzed, 1 stuck — tap to retry)" with stuck count amber + retry affordance + "report stuck analysis" surface. Don't defer predictable surface to F-ticket-only.
- **E**: route surface (a) two distinct routes; tier-bypass-on-read smoke gate guard + F29 ADR-shape filed for "read access doesn't gate on tier; create access does" emergent rule.
- **F**: Jinja2 (a) — pre-plan note for 192B about WeasyPrint conservative CSS (no Grid).
- **G**: smoke-gate rhythm — visual/UX-heavy not data-heavy; 192 viewer single-architect-session smokeable ~30-45 min, no live API calls. Step 9 added: composition layer regression sweep BEFORE UI testing. 192B Step 8 added: deterministic byte-compare PDF render.
- **H**: branch + cadence; Commit 1 includes FastAPI TestClient integration tests so Commit 2 mobile work proceeds against known-working contract.

**Section I (NEW)** — error-state and empty-state rendering policy. 10 states enumerated:

- I1 no fault codes (b) "No fault codes recorded for this session."
- I2 no diagnosis with N-of-2 count copy: "Diagnosis not yet generated. ${N} of 2 symptoms recorded; add ${2-N} more..."
- I3 no videos (a) hide videos card entirely; composer omits videos field; no explicit hide-logic.
- I4 lifecycle as written + PDF metadata band timestamp.
- I5 network failure (a) error state + retry; F31 provisional if existing describeError doesn't distinguish network-vs-backend.
- I6 404 with refined copy: "This session is no longer available. It may have been deleted."
- I7 401 (b) error copy specifying Home → API key card.
- I8 no symptoms (b) symmetric with I2.
- I9 defensive empty payload (a) + structured logline + F30 backend telemetry.
- I10 focus re-fetch — pushback from Kerwyn: 30s debounce, not refresh-every-focus. Phase 188 HVE round-trip-cost lesson applied.

**Cross-cutting placeholder copy review** — 11 placeholder strings pulled into a single register and reviewed as a coherent voice/tone set: lead with state then action; "session" terminology consistent (not "diagnostic session" / "case" / etc.); informative + action-oriented + not chatty; reference exact UI affordances by name; numerals for ≤100. Same discipline as 191D opt-out reasons.

**F-tickets to file at 192 finalize:**
- **F28** — per-mechanic preset persistence (trigger: 192B smoke or 2-weeks-of-usage friction).
- **F29** — ADR-shape "read access doesn't gate on tier; create access does." Promoted to in-phase deliverable: lands as `docs/architecture/auth-policy.md` in Commit 1 (small + Commit 1 is touching auth surface anyway + prevents accidental tightening between 192 ship and next phase).
- **F30** — backend telemetry event on defensive empty-payload case.
- **F31 (provisional)** — `describeError` network-vs-backend-unreachable distinction. Pre-build verify if existing implementation covers; file if not.

**Files plan:**

- New backend (5): models/report.py + report_composer.py + routes/reports.py + 2 pytest suites
- New mobile (6): ReportViewerScreen + SectionToggle + ReportCard components + useReport hook + report types + Jest tests
- Modified backend (3): __init__.py + app_factory.py + api-schema/openapi.json refresh
- Modified mobile (4): SessionsStack + nav types + SessionDetailScreen cross-link + api-types.ts regen
- Plus F29 ADR file: docs/architecture/auth-policy.md (small, ~30 lines, in Commit 1)

**Commit plan (5 commits on `phase-192-diagnostic-report-viewer` branch):**

1. **Backend composer + route + tests + F29 ADR** (backend-only) — composer pytest suite passes against fixtures BEFORE the route is merged; that's the boundary-decoupling gate per A's refinement. Plus F29's auth-policy.md ADR. pyproject 0.3.1 → 0.3.2.
2. **Mobile useReport hook + types** (mobile-only) — hook compiled + Jest tested in isolation before viewer screen consumes it.
3. **Mobile ReportViewerScreen + SectionToggle + ReportCard** (mobile-only) — top-level screen + section-toggle component + shared card wrapper. All 6 cards with placeholder/empty-state policy per I1-I9 + section-toggle preset + 30s focus-debounce + pull-to-refresh + stuck-in-analyzing surface.
4. **Mobile cross-link from SessionDetailScreen + nav registration** (mobile-only) — ReportViewerScreen registered on SessionsStack; "View report" CTA on SessionDetailScreen. Back-button stack verified.
5. **Finalize** (both repos) — Mobile Jest + backend pytest sweep green. Move plan docs in_progress → completed. Backend impl.md 0.13.10 → 0.13.11. Mobile impl.md 0.0.11 → 0.0.12. Mobile package 0.0.9 → 0.0.10. ROADMAP marks ✅ both repos. FOLLOWUPS file F28 + F29 (already-landed-in-Commit-1 reference) + F30 + provisional F31.

**Versioning targets at v1.1 finalize:**

- Backend `pyproject.toml`: 0.3.1 → 0.3.2 (patch — extends API surface; no breaking changes)
- Backend project `implementation.md`: 0.13.10 → 0.13.11
- Schema unchanged at v39
- Mobile `package.json`: 0.0.9 → 0.0.10
- Mobile project `implementation.md`: 0.0.11 → 0.0.12

**Single-stage architect gate after Commit 5** (~17-step smoke, ~30-45 min, single-architect-session). Visual/UX-heavy per Section G — recovers user-facing-surface-delivery discipline after the integration-heavy Track I run. No live API calls. Cost $0.

**Pre-build risks to investigate during Commit 1 / Commit 2:**

1. Stuck-in-analyzing retry route — verify if `POST /v1/sessions/{id}/videos/{vid}/retry-analysis` exists from Phase 191B; if not, add as part of 192's backend scope (~30 LoC + 1-2 tests). If genuinely out-of-scope, file F-ticket and render stuck-in-analyzing affordance as info-only until route ships.
2. `describeError` network-vs-backend-unreachable — verify Phase 187's existing implementation; F31 provisional pending verification.
3. Composition layer tight-coupling smell — composer pytest suite tests `compose(session_id)` directly without HTTP; if a test requires HTTP-layer concerns to set up, that's a coupling smell to fix at Commit 1.

**Next:** plan commit on backend `master` (this file + `192_implementation.md` v1.0), mobile branch tracks the same plan via centralized phase-doc ledger; then Commit 1 (backend composer + route + tests + F29 ADR — Architect-side build OR Builder dispatch, TBD by user pacing).

---

### 2026-05-05 — Plan v1.0 → v1.0.1: pre-Commit-1 reshape (Phase 182 IS the substrate)

Architect-side pre-build deep-survey before drafting any architect deliverables (ReportPayload schema + F29 ADR + Builder brief) caught a major architectural mismatch: **Phase 182 already shipped the report-route surface plan v1.0 specified building from scratch.** Six routes (session/work-order/invoice × json/pdf) + a `motodiag.reporting` module (builders + renderer) + dict-based `ReportDocument` shape + owner-only auth with `SessionOwnershipError → 404` (cross-user existence-disclosure-prevention pattern). 163 + 473 + 326 lines of pre-existing code.

**Halt-and-flag was the correct move** vs working architect-side ReportPayload design + F29 ADR before knowing about Phase 182. Same lesson as F9 catalog #1 (Phase 191B HVE-shape bug) but caught at pre-architect-deliverable time instead of fix-cycle time. Discovering NOW vs at Commit 1 verification is exactly when substrate-extension work should pivot.

**Three reshape paths surfaced; (a) accepted with full architectural reasoning logged:**

- **(a) Phase 182 IS the substrate. Extend build_session_report_doc() to include videos + Vision findings; mobile viewer reads existing route. 192B scope collapses to mobile Share Sheet wiring + maybe section-toggle query param.**
- (b) Build typed Pydantic surface alongside dict surface — REJECTED on principle (F9-family pattern: two surfaces returning same logical data).
- (c) Migrate dict-to-Pydantic — DEFERRED to F32 (right long-term, wrong Phase 192 commitment).

**Specific scope changes in v1.0.1:**

DROPPED from plan v1.0:
- New `report_composer.py` (Phase 182's `build_session_report_doc` IS the composer)
- New `routes/reports.py` (already exists)
- New `models/report.py` Pydantic (back-compat preserved with dict; F32 deferred)
- New `GET /v1/sessions/{id}/report` route (mobile uses existing `/v1/reports/session/{id}`)

ADDED in reshape:
- Extend `build_session_report_doc()` for videos + Vision findings
- F29 ADR `docs/architecture/auth-policy.md` (re-derived around Phase 182's existence-disclosure-prevention pattern)
- F32 (NEW) — eventually migrate dict to Pydantic; trigger = third report-consuming surface
- `docs/architecture/report-document-shape.md` documenting Phase 182's existing dict shape conventions inline (free byproduct of architect understanding the shape well enough to extend it)

**Auth posture refinement** (Section E): Phase 182's owner-only-with-404 is **stricter** than plan v1.0's session-owner-or-shop-tier-member spec. The 404-not-403 choice prevents existence-disclosure on cross-user lookups. Security improvement, not just naming difference. F29 ADR documents the WHY explicitly: "owner-only-on-read prevents existence-disclosure on cross-user lookups; tier gating is for scarce resources (vehicle/session creation), not for read access to your own data."

**Smoke gate Section G refinement**: smoke step 7 verifies free-tier user fetching OTHER user's session report returns **404** (not 403) — verifies existence-disclosure-prevention pattern.

**192B forward-looking flag** logged in v1.0.1: 192B needs its own pre-plan Q&A pass AFTER 192 finalizes. Substrate changed underneath 192B; feature half should re-derive scope against actual substrate state, not originally-planned substrate state. Probably 2-3 commits, not 5.

**Updated commit plan (4 commits, was 5)** — Commit 4 + Commit 5 collapse since reshape eliminated enough work.

**Architect-side deliverables BEFORE Builder dispatch:**

1. F29 ADR `docs/architecture/auth-policy.md` (~80-120 lines, narrative-quality)
2. Videos/Vision findings nesting design (top-level section vs nested-under-videos decision + WHY)
3. `docs/architecture/report-document-shape.md` documenting existing dict conventions

Then Builder gets the design + extends `build_session_report_doc()` + adds tests against Phase 191B seeded video fixtures. Builder dispatch is MORE attractive under reshape (a) than plan v1.0 — mechanical work against documented shape conventions + clear architectural target.

**Why this amendment lands BEFORE Commit 1, not post-finalize like 191D's was**: 191D's amendment was lessons-learned recording AFTER finalize (fresh-recall discipline). 192's amendment is pre-build reshape — discovered architectural mismatch between plan and reality at architect-side-survey time. Pre-Commit-1 is the cheapest correction point; pre-build deep-survey is what makes the cost asymmetry visible early. Mid-Commit-1 correction or post-finalize correction would be substantially more expensive.

**Next:** commit v1.0.1 amendment to backend master (this file + 192_implementation.md v1.0.1), then architect-side artifacts (F29 ADR + nesting design + shape-conventions doc), then Builder dispatch for the implementation.

---

### 2026-05-05 — Plan v1.0.2 amendment: post-architect-review rigor refinements

Architect single-pass review of the three substrate-decision artifacts (F29 ADR + shape doc + Builder brief; commit `a2fc999`) returned conditional sign-off with three rigor refinements (no architectural blockers) + one shape-doc gap + one phase-log forward-looking note. Bundled into v1.0.2 amendment for durability of the artifacts; Builder-D dispatch proceeded in parallel (Builder isn't reading the rigor refinements to write the composer extension).

**Six items folded into v1.0.2:**

1. **F29 ADR — A2 rejection cross-reference.** Original two-sentence rejection of uniform-403 was accurate but underweighted relative to how prominent the alternative is in standard REST guidance. Added cross-reference to Decision section's worked example + named the threat-model disagreement explicitly: "Standard REST guidance assumes a threat model where existence-disclosure is acceptable; Track I's resource-sensitivity profile makes that assumption inappropriate. The 403-vs-404 question is not a REST-correctness question; it's a threat-model question, and the threat models disagree." Closes the loop between Decision and Alternatives.

2. **F29 ADR — A3 rejection adds covert-channel security argument.** Original rejection was operational-overhead-only. Added the load-bearing security argument: "Heterogeneous classification creates a covert channel — if vehicles return 403 and sessions return 404, response-status patterns across heterogeneously-classified resources leak existence information that uniform-404 closes. A caller probing GET /v1/vehicles/{id} (403 response) followed by GET /v1/sessions/{id} (404 response) for the same {id} learns that vehicle N exists but session N doesn't — even though the caller has no legitimate access to either. The cross-resource pattern reconstructs the existence information the per-resource-404 was designed to hide." Same teaching-device value as Decision section's worked example; same enumeration-prevention principle applied to mixed-classification.

3. **F29 ADR — "emergent pattern not new policy" framing promoted to first sentence of Decision.** Per architect's "existing-pattern ADRs are easier to defend than novel-policy ADRs" reasoning: existing-pattern framing makes the precedent body's existence-as-evidence load-bearing rather than supporting. Decision now opens: "This ADR documents an emergent pattern, not a new policy. Track I has independently implemented these rules in four read-endpoint phases (Phase 182 reports, Phase 188 vehicles, Phase 189 sessions, Phase 191B videos) without an explicit cross-cutting policy document; the ADR canonicalizes the convention so future contributors making auth decisions in Phase 193+ inherit the policy by reference rather than re-deriving it from precedent. Existing-pattern ADRs are easier for future contributors to defend than novel-policy ADRs because the precedent body proves the policy was implementable + survivable in practice across multiple independent phases."

4. **Shape doc — Reason 4 of Option (b) tightens speculative-future framing.** Original anchored to specific speculative phase ("Phase 195+ adds per-video audio analysis"). Tightened to structural argument independent of speculative phase numbering: "Future per-video derived analyses extend cleanly. Any analysis type whose result is naturally per-video (audio analysis, sensor-correlation, frame-level annotations, etc.) nests as a sibling key under each video card — no new top-level section needed per analysis type." Future contributor revisiting if Phase 195 doesn't ship audio analysis won't find a stale anchor.

5. **Shape doc — reportlab/Jinja2 ergonomics gap (Customer/Insurance presets via flowable composition, not Jinja blocks).** Architect flagged: shape doc's current Renderers section calls out reportlab-vs-WeasyPrint but doesn't walk the Customer/Insurance preset implication. Plan v1.0's Section F sketched preset-templating via Jinja2 inheritance; that pattern doesn't translate to reportlab Platypus (flowable-based, not template-based). Added new "Customer-facing vs Insurance-facing presets — implementation note for 192B" subsection: "The preset implementation 192B will use is flowable composition in Python code: a compose_story_for_preset(doc, preset) function that walks the ReportDocument's sections list and selectively appends flowables based on the preset's section-visibility map." Override map data shape (per Phase 192 plan C1 (γ)) survives the renderer-change unchanged; only rendering-side implementation differs.

6. **Phase log — explicit forward-looking note about 192B not inheriting Jinja2 assumptions.** This entry. 192B's pre-plan Q&A (which already needs to re-derive scope from post-192-finalize state per v1.0.1's forward-looking flag) should NOT inherit plan v1.0's sealed-history Section F template-inheritance assumptions. The reportlab-flowable-composition pattern is the implementation; Jinja2 considerations from plan v1.0 are moot. 192B should design preset implementation as a Python function that walks the ReportDocument + selectively appends flowables, NOT as a template-with-blocks.

**Item 7 considered, deferred** (per architect's "optional, dev team discretion" framing): Builder brief item 9 about TAG_CATALOG entries. Skipped because Commit 1 scope doesn't touch route definitions (per the brief's "Do NOT" list); the new tests live in test_phase192_*.py and don't add tag-catalog entries. F21 lint catches at pre-commit if anything slips. Not load-bearing to bake into the brief; mentioned in v1.0.2 for record.

**Sign-off conditional**: with v1.0.2 amendment landing, dispatch Builder-D for Commit 1. Architect sign-off explicitly: "Architectural surface is correct. F29 canonicalizes emergent pattern with rigorous reasoning + good worked examples. Shape doc's nesting design picks the right option for the right reasons. Builder brief is appropriately constrained. Three concerns are rigor refinements, not architectural blockers."

**Builder-D dispatch ran in parallel with this amendment** per architect's "don't serialize the dispatch behind the amendment if the dev team would otherwise gate it" direction. Builder-D acknowledged, reading the brief + architecture docs + plan; v1.0.2 amendment landed concurrent with Builder's reading-and-implementing window.

**Next:** v1.0.2 amendment commit (this entry + the F29 ADR + shape doc edits) → trust-but-verify Builder-D's report when it arrives → Commit 1 commits with Builder's work.
