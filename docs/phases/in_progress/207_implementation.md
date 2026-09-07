# Phase 207 — Security audit

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-09-07

## Method

Static review paired with **live probing of the running server**, because
the two find different things. A grep can show that a query is
parameterised; only a request can show that an oversized id reaches
SQLite and raises. Every claim below is backed by either a `path:line`
or an observed HTTP response.

## Findings

### Fixed this phase

**Oversized integer ids returned 500 with a stack trace (low).**
SQLite stores 64-bit signed integers; a larger Python int raises
`OverflowError` deep in the repo layer, so the request reached the
database before anything rejected it. Reproduced on four route families
— sessions, reports, videos, shop. Nothing leaked to the client (the 500
body is deliberately bare, verified against `sqlite`, `traceback`,
`OverflowError` and `site-packages`), but any key-holder could fill the
error log with tracebacks, and it broke the pattern its neighbours
follow: a non-numeric id was already 422, a negative one 404, and only
the oversized case answered 500.

`OverflowError` derives from `ArithmeticError`, **not** `ValueError`,
which is why the existing `ValueError` handler never caught it. Handled
centrally rather than by bounding all 148 integer path parameters: the
per-parameter bound is more precise and would appear in the OpenAPI
schema, but it is a large error-prone diff that every future route must
remember, and forgetting it would silently restore the 500.

### Verified sound — recorded so they are not "fixed" into something worse

- **API keys.** `secrets.token_urlsafe(24)` → 192 bits of entropy,
  stored as unsalted SHA-256 (`auth/api_key_repo.py:81,88`), and looked
  up **by hash** (`:162`) rather than string-compared. Unsalted SHA-256
  would be wrong for passwords, which are low-entropy and need a slow
  KDF; for a 192-bit random token there is no rainbow table and brute
  force is infeasible. Swapping in bcrypt here would slow every request
  to solve a problem that does not exist.
- **SQL injection.** Payloads including `' OR '1'='1`,
  `'; DROP TABLE known_issues;--` and a `UNION SELECT` were sent through
  the KB search: all returned 200 with zero matches, and the table still
  holds 6,600 rows. Values are bound; the payloads are literal text.
- **Cross-user isolation.** A second authenticated user received 404 on
  every one of another user's session-scoped endpoints, and could not
  mint a share link for a session they do not own. Ownership is enforced
  **inside the query** (`video_repo.get_video_for_owner`), not by a
  check the caller could skip.
- **File handling.** Stored paths are derived from the
  database-assigned id (`{video_id}.mp4`, `routes/videos.py:288`), never
  from a client-supplied filename, so traversal is structurally
  impossible rather than filtered. `file_path` is deliberately omitted
  from response models (`:185`). Traversal probes returned 404.
- **Secrets in logs.** No API key, header, or request body is logged.
  The one token-adjacent line records a **user id**, not a token
  (`push/events.py:51`). Confirmed zero `mdk_live_*` strings across the
  server logs.
- **The 500 handler.** Returns a bare problem document with a
  correlation id and no detail. Verified against a real 500.
- **Rate limiting reaches the unauthenticated route.** 30 rapid requests
  to `/v1/share/{token}` produced two 429s — the anonymous IP bucket
  Phase 200 relied on is real, not assumed.
- **Debug leakage.** `debug` defaults False and the app never passes
  `debug=` to FastAPI.

### Filed, not fixed — configuration decisions, not code defects

- **F69 — CORS is set to localhost dev origins** with
  `allow_credentials: true`. Harmless locally; the
  wildcard-plus-credentials mistake is one edit away.
- **F70 — `/docs`, `/redoc`, `/openapi.json` answer without a key.**
  Everything behind them is still gated, so this publishes the API's
  shape rather than its data. A deliberate choice to make, not a default
  to leave unrevisited.

Both are in the release runbook as well as the ticket list, matching how
F64 was handled.

## Verification Checklist

- [x] Oversized ids return 422 on all four affected route families
- [x] The fix moved nothing else — non-numeric still 422, negative still
      404, a real session still 200
- [x] Key generation, storage and lookup reviewed and justified
- [x] Injection payloads proven inert against the live server
- [x] Cross-user reads and share-minting denied
- [x] File paths proven to be id-derived; ownership enforced in-query
- [x] No secret appears in any log
- [x] Public share route confirmed rate limited
- [x] 23 tests pin the findings
- [x] Backend regression green

## Risks

- **A static review cannot establish absence.** It shows that the
  patterns it looked for are sound. It cannot prove there is no logic
  flaw in an unreviewed path, cannot model a real attacker's chaining,
  and says nothing about deployment — TLS, host hardening, secret
  storage, or the database file's permissions. Those matter more than
  anything here once the desktop comes out of storage.
- **No dependency CVE scan was run.** Versions are current and
  mainstream (pydantic 2, httpx, PyJWT, cryptography), but "looks
  modern" is not a scan. Worth wiring into the packaging phase.
- **The audit was performed against a dev database and a dev config.**
  Production posture is a different question, which is exactly why F69,
  F70 and F64 exist.
