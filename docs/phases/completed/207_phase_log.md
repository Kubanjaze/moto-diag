# Phase 207 — Security audit — Phase Log

**Status:** ✅ Complete
**Started:** 2026-09-07 | **Completed:** 2026-09-07
**Repos:** `Kubanjaze/moto-diag` + mobile ledger, branch
`phase-207-security`

---

### 2026-09-07 13:35 — Audit complete: one defect fixed, two launch items filed

- **Method: static review PAIRED WITH live probing.** A grep shows a
  query is parameterised; only a request shows that an oversized id
  reaches SQLite and raises. The probing is what found the one real
  defect.
- **Fixed — oversized integer ids returned 500 with a stack trace.**
  Reproduced across sessions, reports, videos and shop. Nothing leaked
  (verified the body mentions no sqlite, traceback or module paths), but
  any key-holder could flood the error log, and it broke the pattern its
  neighbours follow: non-numeric was already 422, negative 404, only
  oversized answered 500. `OverflowError` derives from
  `ArithmeticError`, not `ValueError` — which is why the existing
  handler never caught it.
- **Verified sound, and recorded WHY so nobody "improves" it:** API keys
  are 192-bit `secrets.token_urlsafe` values stored as unsalted
  sha256 and looked up BY HASH. Unsalted sha256 is wrong for passwords
  and right for high-entropy tokens; swapping in bcrypt would slow every
  request to solve a problem that does not exist.
- **Also verified:** injection payloads inert against the live server
  (table still 6,600 rows) · cross-user reads and share-minting denied,
  with ownership enforced INSIDE the query · file paths derived from
  database ids rather than client filenames, so traversal is
  structurally impossible · no secret in any log · the 500 handler
  leaks nothing · the unauthenticated share route IS rate limited
  (two 429s in 30 requests).
- **Filed rather than fixed — configuration, not code:** F69 (CORS set
  to localhost dev origins with credentials allowed) and F70 (`/docs`
  and `/openapi.json` unauthenticated). Both in the release runbook
  too, matching F64's treatment.
- **Stated plainly in the doc: a static review cannot establish
  absence.** It says nothing about deployment — TLS, host hardening,
  secret storage, file permissions — which will matter more than any of
  this once the backend has a home. No dependency CVE scan was run
  either; "looks modern" is not a scan.
- **23 tests** pin the findings so they cannot regress silently.

### 2026-09-07 16:40 — Second pass: the first audit's verdict was wrong

- **A deeper sweep of the shop and billing route families found a
  critical cross-tenant leak the first pass missed.**
  `GET /v1/shop/{shop_id}/customers` returned every customer in the
  database — name, email, phone, address, shop-private notes — to any
  shop-tier member of any one shop. One paid account, one request.
- **Why the first pass missed it.** It checked whether each route called
  `require_shop_access`. The customer routes do call it. The query on
  the next line then ignored the shop entirely. Confirming that an
  access-control helper is *present* is not confirming that the data
  access underneath it is *scoped* — and "all 18 shop_mgmt routes call
  require_shop_access" was recorded as reassurance when it was only a
  statement about line coverage.
- **The column that was supposed to prevent this had never been set.**
  `customers.owner_user_id` defaulted to `1` on every row in the table
  while its docstring claimed it "prevents customer data leakage in
  multi-tenant deployments". It was also the wrong key — a shop has
  many members. **Migration 050** adds `customers.shop_id`, matching
  `work_orders.shop_id`, and the routes scope in-query. NULL matches no
  shop, so an unclaimed row goes invisible rather than public.
- **Four more real defects, all fixed:** a forged webhook could grant a
  paid tier because `billing_provider` defaults to `"fake"` and nothing
  stopped that default reaching prod (`create_app` now refuses to
  start) · the 422 handler logged rejected input values, which under
  pydantic v2 is the whole request body on a model-level failure · both
  upload routes buffered the entire body before consulting caps that
  are per-session aggregates and cannot bound one request · push
  deregistration deleted by token alone, so any user could silence
  another's notifications.
- **Every fix was proven against the pre-fix code**, not assumed: the
  seven tenancy tests and the log-redaction test were run with the fix
  reverted and confirmed to fail. Test count 23 → 40.
- **Caught in passing: the committed OpenAPI schema and the generated
  mobile `api-types.ts` still carried the pre-F56 `"classic"` transport
  enum** while the backend had moved to `"classic-bt"`. That is the
  same F37-class drift as before, left behind by fixing the backend
  without refreshing the generated artefacts. Both refreshed; mobile
  typecheck clean.
- **Filed F71–F75:** proxy-collapsed anonymous rate limiting (a launch
  item — behind a load balancer one client burns the shared 100/day
  budget and every customer share link 429s) · per-process limiter
  state multiplying limits by worker count · API keys in the WebSocket
  query string · the prefix-collision docstring claiming 96 bits where
  the prefix carries ~18 · two dynamic UPDATE builders without column
  allowlists (not reachable today, cheap to harden).
- **The honest summary:** an audit that reports "one defect, otherwise
  clean" after a single pass should be read as a report on the pass,
  not on the system. This one needed a second look to find the thing
  that actually mattered.
