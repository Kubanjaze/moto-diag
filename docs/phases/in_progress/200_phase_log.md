# Phase 200 — Customer-Facing Share View — Phase Log

**Status:** 📋 Planned
**Started:** 2026-09-02 | **Completed:** —
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
