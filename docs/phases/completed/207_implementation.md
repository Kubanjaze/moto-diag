# Phase 207 — Security audit

**Version:** 1.2 | **Tier:** Standard | **Date:** 2026-09-07

## Method

Static review paired with **live probing of the running server**, because
the two find different things. A grep can show that a query is
parameterised; only a request can show that an oversized id reaches
SQLite and raises. Every claim below is backed by either a `path:line`
or an observed HTTP response.

> **Revision note (v1.2).** v1.1 reported one defect and an otherwise
> clean bill of health. A second, deeper pass over the shop and billing
> route families found that conclusion was too generous: the customer
> endpoints leak across tenants, and four other real defects existed.
> The corrected findings are below. The v1.1 verdict was wrong because
> the first pass checked *whether* routes called an access-control
> helper and not *what the query then did* — `require_shop_access` was
> present on the customer routes, and the query underneath ignored it.

## Findings

### Critical — customer records were not scoped to a shop

`GET /v1/shop/{shop_id}/customers` called
`customer_repo.list_customers(db_path=db_path)` with no filter
(`shop_mgmt.py:431`). `require_shop_access` confirmed the caller was an
active member of the shop named in the URL, and then the query returned
**every customer row in the database**: name, email, phone, address and
shop-private notes. One legitimate paid account, one request, no token
guessing. `GET /{shop_id}/customers/{customer_id}` had the same gap.

The column meant to prevent exactly this, `owner_user_id`, was never set
by any caller — `create_customer_endpoint` built a `Customer` without it
(`shop_mgmt.py:446`) and the field defaults to `1`, the system user. So
every row in the table held the same value and the column scoped
nothing, while its docstring claimed it "prevents customer data leakage
in multi-tenant deployments". A comment asserting a property is not the
property.

`owner_user_id` was also the wrong key: a shop has many members, so
scoping to whoever typed the record in would hide a customer from that
person's own colleagues. **Migration 050** adds `customers.shop_id`, the
key the rest of the schema already uses (`work_orders.shop_id`,
`intake_visits.shop_id`), and the routes now scope on it in-query rather
than filtering rows after the fact. NULL means unclaimed and matches no
shop — `= ?` is never true for NULL, so the failure mode is an invisible
customer rather than a leaked one. Existing rows are backfilled to the
only shop when a deployment has exactly one, and left NULL otherwise
rather than guessed at.

`create_intake_endpoint` took `customer_id` from the request body with
no ownership check; it now 404s on another shop's customer, so an intake
cannot be used as an existence oracle for foreign ids.

### High — a forged webhook could grant a paid tier

`billing_provider` defaults to `"fake"` (`config.py:154`). That
provider verifies a webhook by comparing the header against a hardcoded
literal (`providers.py:127`), its route takes no API key, and it sits on
the rate-limit exempt list (`middleware.py:76`). Tier is then read
straight from the event metadata, so one forged
`checkout.session.completed` grants a company subscription.

The real Stripe path is correct. The defect is that **nothing prevented
the default from reaching production** — it relied on the deploy
remembering an env var. `create_app` now refuses to start when
`env=prod` and the provider is not Stripe. It lives in `create_app`
rather than the CLI so a deploy running uvicorn directly cannot skip it.

### High — rejected input was written to the log

The 422 handler logged `exc.errors()`, and under pydantic v2 each entry
carries an `input` key holding the rejected value — on a model-level
failure, the entire request body. A short device token, a customer's
phone number, whatever failed validation went into the log verbatim.

It could **not** log API keys or `Authorization`: those are headers,
never body-validated. The handler now strips `input` and `ctx` and keeps
the diagnostic shape — which field, which rule, which route.

### High — uploads were buffered in full before any size check

`videos.py` and `photos.py` both called `await file.read()` and only
then consulted their quota helpers. Those quotas are per-session and
per-work-order **aggregates**; neither bounds a single request. A single
arbitrarily large POST was therefore materialised in memory first, and
the check meant to stop it ran afterwards — the wrong order, since the
check cannot undo the allocation it was meant to prevent. Photos had no
byte ceiling at all.

`api/uploads.py` adds `read_bounded`, which reads in chunks and aborts
the moment the stream passes the ceiling, so an oversized body costs one
chunk of headroom instead of its full length. Videos cap at 512 MB per
file, photos at 25 MB.

### Medium — push deregistration was unscoped

`delete_token` deleted by token alone, so any authenticated user who
learned another user's device token could silence that user's
notifications. Registration was already bound to the user; only the
delete side was missing it. The caller's id is now required on the
route, while the APNs 410 prune path — which has no caller identity —
keeps the unscoped form deliberately.

### Fixed this phase (from the first pass)

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
- [x] Cross-shop customer list, fetch, create and intake all denied
- [x] The seven tenancy tests fail against the pre-fix code and pass
      after — verified by reverting the route, not assumed
- [x] The log-redaction test likewise fails without the redaction
- [x] `env=prod` + fake billing refuses to start; dev still starts
- [x] Bounded read proven to stop within one chunk of the ceiling
- [x] Migration 050 applies on a fresh DB; backfill claims a single
      shop and declines to guess when there are two
- [x] 40 tests pin the findings
- [x] Backend regression green (4837 tests before this commit's
      additions)
- [x] OpenAPI schema and mobile `api-types.ts` refreshed — the
      committed copies still carried the pre-F56 `"classic"` transport
      enum; mobile typecheck clean after

## Risks

- **The v1.1 audit missed a critical leak, which is the most important
  fact in this document.** Five passes of "the routes call the access
  helper" read as safe. What mattered was the line after it. Treat the
  clean sections below with that in mind: they record what was checked,
  not a guarantee.
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
