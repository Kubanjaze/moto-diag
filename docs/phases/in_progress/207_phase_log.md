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
