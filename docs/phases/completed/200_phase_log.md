# Phase 200 — Customer-Facing Share View — Phase Log

**Status:** ✅ Complete
**Started:** 2026-09-02 | **Completed:** 2026-09-02
**Repos:** `Kubanjaze/moto-diag` + `Kubanjaze/moto-diag-mobile`, both on
branch `phase-200-customer-share-view`

---

### 2026-09-02 17:06 — Plan written (Step 0 audit + v1.0)

- **Step 0 audit (delegated read-only sweep, both repos):** report
  generation is EXTENSION territory — the `ReportDocument` contract and
  the **customer preset already exist** (`_CUSTOMER_HIDDEN_HEADINGS`,
  `builders.py:116`), so this phase adds reach, not report content.
  Public-route support is a thin EXTENSION (omit the auth dep + register
  the prefix + stay off the rate-limit exempt list). Share tokens are
  **GREENFIELD** — no signed-URL, slug, or `expires_at` primitive exists
  anywhere; API-key minting is the template to copy. Server-side HTML is
  **GREENFIELD** (no jinja2/HTMLResponse; the only HTML generator is
  CLI-side, markdown-based, behind an optional extra).
- **Two latent intent signals found and picked up:** the RBAC permission
  `share_report` has been seeded since migration 012 with no consumer,
  and 192B's deterministic-PDF flag was added "for share-flow
  correctness". Phase 200 is the phase those were waiting for.
- **Step 0 gap surfaced, deliberately NOT fixed in passing:**
  `diagnostic_sessions` has no `customer_id` — customer ownership is
  reachable only indirectly via `vehicles.customer_id` (retrofitted
  `DEFAULT 1`). The share binds to a SESSION and the token is the
  capability, so this is off the critical path. Filed as a follow-up.
- **User decisions:** public server-rendered HTML page (not JSON-only,
  not a PDF link) · links expire in 30 days AND are revocable · session
  reports only (work-order / invoice sharing deferred).
- **Security posture recorded up front:** capability URL — the token is
  the whole authorization. Entropy + expiry + revocation + generic 404 +
  anonymous rate limiting left ON. A publicity guard test asserts the
  generated OpenAPI marks the route public, applying the 199 lesson
  (verify the built artifact, not the settings that were supposed to
  produce it).
- **Next milestone:** plan commit + push → backend build (migration 045,
  share repo, HtmlReportRenderer, 4 routes, tests) → mobile build
  (share-link hook + ReportViewerScreen action) → device smoke.

---

### 2026-09-02 17:21 — Build complete (backend + mobile), regression green

- **Backend (`0988f18`):** migration 045 `report_shares` (SCHEMA_VERSION
  44→45; both designed pins advanced per their contract comments) ·
  `reporting/share_repo.py` · `HtmlReportRenderer` registered beside
  `pdf`/`text` in `get_renderer` · `api/routes/share.py` with three
  authed routes and one public one · `PUBLIC_PATH_PREFIXES += /v1/share`
  + `share` tag · `MOTODIAG_PUBLIC_BASE_URL` setting. **26 tests**, green
  first run. Full regression **4650 passed, 0 failed** in 9:01.
- **Mobile (`b6fde81`):** `useReportShareLink` (mint → OS share sheet
  with the LINK) kept deliberately separate from `useReportShare` (which
  shares a PDF FILE) · "Share link" button beside "Share PDF" in the
  report viewer · api-schema + api-types refreshed. **+10 tests → 70
  suites / 874 green**; tsc clean; eslint 0 errors.
- **Two design calls worth remembering:** the share token is stored in
  PLAINTEXT (a capability locator for a document in the same database is
  not an account credential, and the mechanic must be able to re-copy a
  lost link), and `created_by_user_id` is load-bearing rather than audit
  trim — see the close entry's key finding.

### 2026-09-02 17:21 — SMOKE: public link verified end-to-end — Phase 200 ✅ Complete

- Seeded session 1 with a deliberately mechanic-only note, minted a link
  as the app's own user over the **tailnet URL the phone actually uses**,
  then fetched it **with no credentials at all**:
  `status=200 · text/html · 3182 bytes`.
- **Customer preset held:** the mechanic-only note appeared **0 times**;
  no `Notes` section in the page. Sections rendered: Vehicle, Reported
  symptoms, Fault codes, Timeline.
- **Lifecycle:** `DELETE /v1/reports/shares/1` → `{"revoked": true}` →
  the same URL immediately returned **410**. An unknown token returned a
  generic **404**.
- The rendered page was handed to the user for review. **In-app tap of
  the new Share link button is the user's confirmation** — no remote view
  of the physical phone from this session; the app was relaunched against
  the new bundle so the affordance is live.

### 2026-09-02 17:21 — Documentation update + close

- `200_implementation.md` → v1.1 (checklist, deviations incl. the
  response-hardening headers and the deliberately non-parameterised
  preset, results, key finding). Docs → `completed/`.
- Mobile project docs: `implementation.md` 0.2.1 → 0.2.2 + Phase History
  row, root `phase_log.md` entry, ROADMAP 200 ✅, **F55** filed
  (`diagnostic_sessions` has no `customer_id` — the Step 0 gap this
  phase deliberately did not fix in passing).
- Branches fast-forwarded into `master` / `main`, pushed.

### 2026-09-02 17:40 — User confirmation: in-app share actions verified on device

- User verdict after tapping through the report viewer on the physical
  iPhone: **"link and pdf work great"** — the new Phase 200 *Share link*
  action AND the pre-existing Phase 192B *Share PDF* action both behave
  on device.
- This closes the one checklist item this session could not verify
  itself (no remote view of the phone). Worth recording that the PDF
  half was confirmed too: the two affordances share a row and a set of
  busy flags in `ReportViewerScreen`, so "the new button works" and "the
  old button still works" are separate claims, and both now hold.
- Phase 200 needs nothing further. The equivalent open item on Phase 199
  (lock-screen banner rendering) remains unconfirmed and is tracked in
  that phase's own ledger.
