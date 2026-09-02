# Phase 200 — Customer-Facing Share View (Public Report Link)

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-09-02 (v1.0 plan → v1.1 as-built same day)

## Existing-code audit (Step 0 — run 2026-09-02, before this plan)

Delegated read-only sweep across both repos. Verdict per area:

- **Report generation — EXTENSION.** `api/routes/reports.py` already serves
  session / work-order / invoice reports (+ PDF variants). The document
  shape is `ReportDocument` (`title`/`subtitle`/`issued_at`/`sections`/
  `footer`) built in `reporting/builders.py:356`; contract documented at
  `docs/architecture/report-document-shape.md`. **The customer preset
  already exists**: `_CUSTOMER_HIDDEN_HEADINGS = ("Notes",)`
  (`builders.py:116`) with resolver `_is_section_hidden` (`:133`). This
  phase adds no new report content — it adds a way to reach the existing
  customer-preset document without an API key.
- **Public routes — EXTENSION, thin.** There is no "public" dependency;
  a route is public by *omitting* `Depends(get_current_user)`. Metadata
  lives in `api/openapi.py:187` (`PUBLIC_TAGS`, `PUBLIC_PATH_PREFIXES`,
  consumed by `_is_public:427`). Rate limiting is separate
  (`api/middleware.py:69` `_RATE_LIMIT_EXEMPT_PATHS`). A public share
  route must omit the auth dep, register its prefix so OpenAPI stops
  stamping it `apiKey` + 401, and deliberately **stay OUT** of the
  rate-limit exempt list — anonymous IP bucketing is the only abuse
  control it gets.
- **Share links / tokens / expiry — GREENFIELD.** No share-token, signed
  URL, slug, or `expires_at` primitive exists anywhere in either repo.
  Nearest neighbour worth copying: API-key minting
  (`secrets.token_urlsafe` + prefix, `auth/api_key_repo.py:69`). Two
  latent intent signals found: the RBAC permission **`share_report` is
  already seeded** (`core/migrations.py:212`, enum `auth/models.py:49`)
  and 192B's deterministic-PDF flag was added "for share-flow
  correctness" (`renderers.py:241`). Both are picked up here.
- **Mobile share — RESHAPE (small).** `useReportShare.ts` shares a local
  **PDF file URI**, not a URL. Sharing a link is a second, distinct code
  path beside it, not a modification of it. `ReportViewerScreen` already
  owns `preset` state and the section filter.
- **Customer identity — EXTENSION with a documented gap.**
  `diagnostic_sessions` has **no `customer_id`** (only `user_id`);
  customer ownership is reachable only indirectly via
  `vehicles.customer_id`, itself retrofitted with `DEFAULT 1` (the
  seeded "unassigned" customer). **Scope call: this phase does NOT add
  the column.** The share is bound to a SESSION and the token itself is
  the capability, so customer identity is not on the critical path. The
  gap is filed as a follow-up rather than fixed in passing.
- **HTML rendering — GREENFIELD server-side.** No jinja2, no
  `HTMLResponse`, no templates in `src/`. The only HTML generator is
  CLI-side and hand-rolled (`cli/export.py:146`), takes markdown, and
  sits behind the optional `[export]` extra. Cleanest route is a new
  `HtmlReportRenderer` slotting into the existing `get_renderer`
  registry (`renderers.py:515`), NOT a templating dependency.

**User decisions (2026-09-02):** public server-rendered HTML page ·
share links expire in 30 days and are revocable · session reports only
(work-order / invoice sharing deferred).

## Goal

A mechanic taps Share on a session report and gets a link they can text
or email to the bike owner. The owner opens it in any browser — no app,
no login, no API key — and sees the customer-preset report: what was
diagnosed, what was found, what it needs. The link dies after 30 days or
the moment the mechanic revokes it.

CLI: none this phase. The share flow is mechanic-facing through the app;
the smoke mints links over HTTP. Deliberate scope call, not an omission.

Run:
- Backend: `pytest tests/test_phase200_share.py`
- Public page by hand: mint via
  `POST /v1/reports/session/{id}/share` (authed), then open the returned
  `url` in a browser with no credentials.
- Device smoke: mobile Share link → OS share sheet → open the link on a
  second device / private window.

Outputs:
- **Backend (branch `phase-200-customer-share-view`):**
  - migration 045 `report_shares` (id, token UNIQUE, session_id FK,
    created_by_user_id FK, preset, created_at, expires_at, revoked_at,
    view_count, last_viewed_at) + SCHEMA_VERSION 44 → 45
  - `reporting/share_repo.py`: `create_share` (32-byte
    `secrets.token_urlsafe`, 30-day default TTL), `get_live_share`
    (returns a status enum: `ok` / `expired` / `revoked` / `missing` —
    the route needs to tell these apart), `revoke_share`,
    `list_shares_for_session`, `record_view`
  - `reporting/renderers.py`: `HtmlReportRenderer` registered as kind
    `html` in `get_renderer` — standalone document, inline CSS, zero
    external assets, mobile-first, print-friendly, **every interpolated
    value escaped**; handles all five `ReportSection` variants
  - `api/routes/share.py`:
    - `POST /v1/reports/session/{session_id}/share` (authed; mints,
      returns `{token, url, expires_at}`)
    - `GET /v1/reports/session/{session_id}/shares` (authed; list)
    - `DELETE /v1/reports/shares/{share_id}` (authed; revoke)
    - `GET /v1/share/{token}` — **public**, returns `text/html`
  - `api/openapi.py`: `/v1/share` added to `PUBLIC_PATH_PREFIXES` +
    `share` TAG_CATALOG entry
  - `core/config.py`: `public_base_url` setting
    (`MOTODIAG_PUBLIC_BASE_URL`) used to build the returned link;
    falls back to the request's own base URL when unset
  - tests: migration shape, repo lifecycle incl. expiry boundary,
    mint/list/revoke auth, public GET 200 / 410 expired / 410 revoked /
    404 unknown, HTML escaping (XSS fixture), customer-preset hiding
    (the `Notes` section must NOT appear in the page), OpenAPI publicity
    guard (share path carries no `apiKey` security requirement)
- **Mobile (branch `phase-200-customer-share-view`):**
  - `src/hooks/useReportShareLink.ts` — mint then `Share.open` with a
    URL/message payload; typed-error handling mirroring
    `useReportShare`'s posture
  - `ReportViewerScreen`: "Share link" action beside the existing
    "Share PDF"; both remain available
  - `api-schema` + `api-types` refresh
  - tests: hook vs fake api + fake Share (success, mint failure, user
    cancel), screen smoke

## Logic

- **Mint:** authed caller owns (or has shop access to) the session →
  `create_share` mints an opaque 32-byte urlsafe token, `expires_at =
  now + 30d`, `preset = 'customer'` → response carries the assembled
  absolute URL.
- **View:** `GET /v1/share/{token}` resolves the token → on `ok`, builds
  the session `ReportDocument` with the customer preset, renders HTML,
  increments `view_count` / stamps `last_viewed_at`, returns 200
  `text/html`. On `expired` or `revoked` → 410 with a plain, friendly
  HTML page ("this link is no longer active — ask your shop for a new
  one"). On `missing` → 404 with a generic page. No JSON error envelope
  on this route: the consumer is a browser, not a client library.
- **Revoke:** sets `revoked_at`; the next view gets 410 immediately.
- **Token storage:** stored in PLAINTEXT, a deliberate divergence from
  `api_keys` (hashed). Rationale: an API key is an account credential
  that must survive a DB read; a share token is a capability *locator*
  for a document already in that same DB — hashing protects nothing a
  DB reader could not already read directly, and it would make the link
  un-recopyable, which the mechanic needs. Documented in the repo module
  header so the divergence reads as a decision, not an oversight.

## Key Concepts

- **Capability URL.** The token IS the authorization. Entropy (32 bytes
  urlsafe), a hard expiry, and revocation are the whole security model;
  there is no second factor by design, because the recipient is a
  customer with no account.
- **Preset reuse over new content.** `_CUSTOMER_HIDDEN_HEADINGS` already
  encodes "what a customer shouldn't see". The share route consumes it
  rather than declaring a parallel notion of customer-safe.
- **Renderer registry, not a template engine.** `HtmlReportRenderer`
  joins `pdf` and `text` in `get_renderer`, so the section-variant
  switch stays in one place across all three output kinds. Adding
  jinja2 for one document would be over-architecture (CLAUDE.md risk).
- **Public-route triple.** Omit the auth dep, register the prefix in
  `PUBLIC_PATH_PREFIXES`, and stay off the rate-limit exempt list. Miss
  any leg and the route is either wrongly documented, wrongly gated, or
  wrongly unlimited.
- **199 lesson applied.** That phase's silent failure came from trusting
  project settings over the built artifact. Here the analogue is
  publicity: a test asserts the generated OpenAPI marks the share path
  public, rather than trusting that omitting the dep was enough.

## Verification Checklist

- [x] Migration 045 applies; `report_shares` columns + UNIQUE token +
      FKs present; SCHEMA_VERSION 45; both designed pin tests advanced
      44→45 per their own contract comments
- [x] `share_repo` lifecycle green incl. the expiry boundary (one second
      before `expires_at` reads `ok`; the boundary itself reads
      `expired`) and revocation winning over expiry
- [x] Mint / list / revoke reject unauthenticated + cross-owner callers
      (401 and 404 respectively; revoke is creator-scoped and idempotent)
- [x] Public `GET /v1/share/{token}`: 200 `text/html` live; 410 expired;
      410 revoked; 404 unknown — all four confirmed in tests AND against
      the running server over the tailnet URL the phone uses
- [x] Rendered page contains the diagnosis sections (Vehicle, Reported
      symptoms, Fault codes, Timeline) and does NOT contain the `Notes`
      section — verified on a session deliberately seeded with a
      mechanic-only note, which appeared **zero** times in the page
- [x] XSS fixture: `<script>` in a vehicle string renders escaped
- [x] OpenAPI marks `/v1/share/{token}` public (no `apiKey` security, no
      401) while its authed sibling in the same router still carries
      both; share route confirmed absent from the rate-limit exempt list
- [x] Backend full regression green on the canonical interpreter:
      **4650 passed, 0 failed, 5 skipped** in 9:01
- [x] Mobile: 10 hook tests green; 70 suites / 874 tests; tsc clean;
      eslint 0 errors
- [x] Smoke: mint → public fetch with no credentials → 200 HTML →
      revoke → same link 410. **In-app tap of the new Share link button
      is the user's confirmation** (no remote view of the physical
      phone from this session); the app was relaunched against the new
      bundle so the affordance is live.

## Risks

- **An unauthenticated route on a paywalled API is a real widening of
  the attack surface.** Mitigations: high-entropy token, hard expiry,
  revocation, no enumeration (404 is generic), anonymous rate limiting
  left ON. The publicity guard test exists so a later refactor cannot
  silently make it authed (breaking customers) or make a sibling route
  public (leaking data).
- **PII in a forwardable URL.** The page names a customer's bike and its
  diagnosis. Anyone the link reaches can read it. That is inherent to
  "send my customer a link"; the 30-day expiry bounds it and revocation
  gives the shop an undo. Worth a plain-language line in the mint
  response copy so mechanics understand what they are sending.
- **HTML injection from mechanic-authored free text** (symptoms, notes,
  vehicle strings flow into the page). Escaping is a correctness
  requirement, not a nicety, and gets its own test fixture.
- **`diagnostic_sessions` has no `customer_id`** (Step 0 finding). Not
  blocking — the token binds to the session — but it means the page
  cannot say "prepared for <customer>" without an indirect vehicle
  lookup. Follow-up rather than a passing migration.
- **Clock/timezone handling on expiry.** All timestamps are UTC ISO
  strings elsewhere in the schema; the boundary test pins that.
- **Deterministic PDF flag (192B) is unrelated to HTML** but shares the
  "share-flow correctness" heritage — no coupling introduced.

## Deviations from Plan

- **Ownership is proven by building the document, not by a separate
  check.** The plan said "authed caller owns the session"; the
  implementation gets there by calling the owner-scoped
  `build_session_report_doc` first and letting `SessionOwnershipError`
  map to 404. That buys a second property the plan did not ask for: you
  cannot mint a link to a report that would fail to render when a
  customer opens it.
- **Response hardening beyond the plan.** The page ships
  `Cache-Control: private, no-store`, `X-Robots-Tag: noindex, nofollow`,
  `Referrer-Policy: no-referrer`, and an in-document `robots` meta. A
  private document behind a capability URL should not sit in a shared
  cache or a search index, and the referrer header would otherwise leak
  the token to any link the page contains.
- **The share route does not accept a `preset` from the caller.** The
  plan's row schema carries one, and it is stored, but the route pins
  `customer`. "What a customer may see" is a product decision that
  belongs in the builder, not a per-request parameter a mechanic could
  widen by accident. The column stays so a future insurance-share is a
  data change, not a migration.
- **No CLI** — declared in the plan, restated here so it reads as a
  scope call rather than an omission.
- **Smoke shape.** The public flow was exercised end-to-end over HTTP
  against the tailnet URL the phone actually uses, which is the
  customer's exact path. Tapping the new button in the app is left to
  the user, the same posture Phase 199 took with the lock-screen banner.

## Results

| Metric | Value |
|--------|-------|
| Backend new tests | 26 (`test_phase200_share.py`) |
| Backend full regression | 4650 passed, 0 failed, 5 skipped (9:01) |
| Mobile new tests | +10 → 70 suites / 874 tests green |
| Mobile static checks | tsc clean · eslint 0 errors |
| New public surface | 1 route (`GET /v1/share/{token}`) |
| Smoke | mint 201 → public 200 HTML (3.1 KB, no credentials) → revoke → 410; unknown token → 404 |
| Mechanic-note leakage into the customer page | 0 occurrences |
| Commits | backend `7a7c176` plan · `0988f18` build · close docs; mobile `b6fde81` build · close docs |

**Key finding:** the constraint that looked like an obstacle produced the
better design. `build_session_report_doc` is owner-scoped, so an
anonymous viewer had no user id to render with — which forced the share
row to remember its minter. The result is a tighter security property
than a purpose-built "public report" path would have had: the document a
customer sees is exactly the one the mechanic was entitled to at mint
time, and it narrows automatically if that mechanic later loses access.
Reusing an owner-scoped builder was cheaper AND safer than writing an
unscoped one for public use.
