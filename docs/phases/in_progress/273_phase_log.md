# Phase 273 — Track O batch 4: payments through Stripe — phase log

**Status:** 🚧 In progress
**Branch:** `phase-273` (Opus session, main checkout, the only writer)

---

### 2026-10-06 — Opened: Track O batch 4

The prompt is `docs/prompts/273_track_o_batch4_stripe.txt` (merged in
`78c79ed`). Row 273 reads "Stripe Connect, card terminals, invoicing,
subscription billing". It carries this batch and folds no other row. It
is the last batch before Gate 16 (292).

The operator's earlier words the prompt carries, from the triage report
(`docs/reports/2026-09-28_track_o_triage.md`, decision 3, verbatim in
the report): the backend stays tailnet-only, so in development Stripe's
webhooks reach it through `stripe listen`. And, from 281's prompt, the
rules for outbound calls: "tests use recorded fixtures, never live
endpoints; the app degrades cleanly when a service is down (shown to the
user, never silently empty); no live API call during the build except one
smoke call per service, logged."

Read first: the 370 handoff (`docs/handoffs/2026-10-06_370_closed.md`),
the 281 handoff, 281's Step 0, the triage report, and 176's and 169's
documents in `docs/phases/completed/`.

The first commit: **row 273 🚧**. Step 0 next, then a stop for the
operator's forks (Connect, the tier prices, routes or CLI only).

### 2026-10-06 — Step 0: F187 filed, row 371 paused, stop for the operator

The record is `273_step0.md`; Stripe's pages are quoted in
`273_sources.md`. Every measured fact in the prompt re-verified (S0-1),
on code at `78c79ed` and a read-only copy of live (schema 79).

- **F187 filed:** 176's subscription webhook path would not change a tier
  against the API version the SDK pins (`2026-09-30.endive`,
  `stripe==16.0.0`). This phase fixes it.
- **Row 371 ⏸️:** live payments and production webhooks (decision 3).
- **Decided, with the reason in S0-4:** the SDK pin and the API version
  sent; the money columns (invoices' REAL columns stay, read through one
  cents function and a round-trip test; `payments` unused); webhooks
  idempotent and order-independent (subscriptions re-read from Stripe,
  invoice payments one-way); an invoice paid only on the verified
  `payment_intent.succeeded` from the shop's own account with the exact
  amount; Terminal server-driven with automatic capture; live keys and
  live events refused unless prod; keys outside the repo, never in
  `.env`, and the test session proven blind to them; migration 080 new
  tables and two columns on a 0-row table.
- **Stripe's docs were read by this session directly** (about 30 pages,
  fetched as Markdown; 15 of them quoted), following 281's sources
  practice. This was reading for a judgement (the Connect options), not a
  census or an extraction, so it was not routed through Subconscious
  (rule 2).

**Stop (rule 1, real forks):** question 1, Connect (A each shop a
connected account, Stripe carries fees and losses, recommended; B the
platform carries them; C one account, Connect later); question 2, the tier
prices; question 3, CLI only now (recommended, row 372 ⏸️) or routes now
(a planned mobile stop).

### 2026-10-06 — The operator's pick, and v1.0

The operator, verbatim:

> 1A, 2 placeholders, 3A

- **1A:** each shop a connected account (Accounts v2, `merchant`,
  `dashboard: full`, Stripe collects fees and carries losses), direct
  charges, Stripe-hosted onboarding, no application fee.
- **2:** test-mode placeholder prices, marked as placeholders wherever a
  price shows.
- **3A:** CLI only; no route, no snapshot change, no mobile session. Row
  372 ⏸️ takes the payment routes and the app's payment screens.

v1.0 is `273_implementation.md`. Decided while writing it, with the reason:
- **The SDK goes in a `payments` extra,** pinned `stripe==16.0.0`, and
  `server` includes it. The same pattern as `api`: the dev venv has it,
  and 209's no-extras packaging test holds the lazy import.
- **No fake gateway for shop payments.** Tests run the real gateway code
  through the SDK's own `http_client` hook with recorded or built
  responses, so the request shapes are tested, not a stand-in's. With the
  provider set to `fake`, the shop payment commands refuse and say Stripe
  is not configured, rather than pretending money moved.

### 2026-10-06 — Built: everything that needs no key

`stripe==16.0.0` installed in `.venv` (it sends `2026-09-30.endive`).
Migration 080 goes forward, back and forward on a scratch database. 92
new tests in five files, plus 176's webhook tests updated; 150 pass
together. `wholetree.sh --full`: 3988 passed, exit 0 (gate 11's snapshot
unchanged). 244G's scanner over all of `tests/`: 0 hits.

Decided while building, with the reason:
- **`paid_at` is when Stripe recorded the payment** (the event's
  `created`), not when the webhook ran. It is the truer time, and it needs
  no clock: a first draft stamped the wall clock and a test comparing two
  databases saw 15 ms apart. Caught by my own new test before any commit,
  so not a bug-fix entry.
- **176's handler names:** `invoice.payment_succeeded` is replaced by
  `invoice.paid`, which Stripe also sends for an invoice paid out of band;
  `invoice.payment_failed` stays. The old ones were no-ops.
- **The paid transition is one guarded `UPDATE`** in the same transaction
  as the payment row (`... WHERE status IN ('sent','overdue')`), rather
  than 169's `mark_invoice_paid`, which opens its own connection. A
  duplicate or concurrent event cannot pay twice or interleave.
- **`subscription sync` uses the webhook's reading** of a Stripe
  subscription, so the two never disagree on tier, status or period.
- **Removed `set_http_client_for_tests`:** 209B's orphan gate found it
  unused (tests set the attribute through `monkeypatch`). Dead code goes,
  rather than an allowlist entry.
- **A test reloading `stripe_api`** to prove the lazy import replaced its
  exception classes for later tests in the session; rewritten to block
  the module instead (the import is inside the call).
- **The edit guard** blocked `sed -i` on a scratch probe file in the
  session scratchpad. It blocks that form wherever it points, by design;
  the probe was not needed again. Recorded, not loosened.
- No new module needs an allowlist entry: each is reached from the CLI or
  the webhook route, so the size pins do not change.

### 2026-10-06 — The credential stop (rule 1: a login or a credential)

Everything that needs no key is built and pushed (`915caaa`). The smoke
and the webhook run are scripted and committed:
`273_smoke.sh` (stages prepare, check, connect, status, setup, webhook,
summary) and `273_smoke.py` (the stages, run through the app's own
commands in-process).
- **The keys** are read only from `~/.config/motodiag/stripe-test.env`
  (mode 600, checked), into the script's own environment. A key that is
  not `sk_test_`/`rk_test_` stops the script before any call.
- **The webhook secret** goes from `stripe listen --print-secret` into
  the server's environment. `stripe listen` names the secret on its
  "Ready" line, so its output is passed through `sed -E
  's/whsec_[A-Za-z0-9]+/whsec_[redacted]/g'` before it is written.
- **The database** is a scratch copy of live made with the read-only
  backup API (`~/.cache/motodiag/phase273/smoke.db`); the script refuses
  any other path. `prepare` was run: live is still schema 79, 1 shop,
  0 invoices.
- **The responses** are kept under `273_smoke/responses/` with the
  one-use onboarding URL and e-mail addresses removed, to become recorded
  fixtures. `calls.jsonl` is the product's own call log.
- "One logged smoke call per surface" is read as one run of each
  surface's command: each command makes the requests it needs (Connect:
  create the account and its link; the reader: a location and a reader),
  and every request is a line in `calls.jsonl`.

Stopped for the operator's Stripe test-mode account, its keys, the
Connect platform setting, the placeholder prices, the customer portal
setting, and the Stripe CLI login.

### 2026-10-06 — The smoke calls, and the webhook run (first pass)

The operator: "keys in place, onboarded". Run on the scratch copy
(`~/.cache/motodiag/phase273/smoke.db`); every request is a line in
`273_smoke/calls.jsonl`.
- `check`: provider stripe, API key set, test mode yes, webhook secret not
  set (it comes from `stripe listen`), 3 of 3 prices, test placeholders.
- Connect (`connect`, run by the operator in their own terminal so the
  one-use link stayed out of the transcript): `POST /v2/core/accounts`
  200, `POST /v2/core/account_links` 200. The account came back
  `card_payments: restricted` with 15 requirements past due.
- After onboarding, `status`: card payments active, 0 due.
- The simulated reader (`setup`): `POST /v1/terminal/locations` 200 and
  `POST /v1/terminal/readers` 200, both on the shop's account.
- The webhook run (`webhook`), server on 127.0.0.1:8273 and `stripe
  listen` forwarding both scopes:
  - Terminal: the simulated reader paid INV-273-SMOKE-2;
    `connect payment_intent.succeeded` → 200 → the invoice paid.
  - Checkout: the operator paid INV-273-SMOKE-1 with 4242…;
    `connect payment_intent.succeeded` → 200 → paid.
  - Subscription: the operator paid the `shop` checkout. The re-read
    stored `shop active`, the period from the items
    (2026-10-06T20:40:16Z to 2026-11-06T20:40:16Z), and the price: F187's
    path works against Stripe.
  - **Stopped:** `invoice.paid` arrived before
    `customer.subscription.created`, got 503 as designed, and `stripe
    listen` never redelivers it, so the tier payment was not recorded and
    the run timed out before the portal call. Bug fix #2 below.
- **Found while relaying the links:** the commands' printed URLs were
  broken across lines. Bug fix #1 below. The links were given to the
  operator from Stripe's own responses.
- **The events are `2026-08-26.dahlia`,** the account's default version,
  even with `stripe listen --latest`; the SDK's requests are
  `2026-09-30.endive`. The handlers read only fields both versions have,
  and subscriptions are re-read at endive. A production endpoint should be
  created at endive: noted for row 371.

### 2026-10-06 — Bug fix #1: a printed Stripe URL breaks across lines

- **Issue:** in the webhook run, `shop invoice pay-link` and
  `subscription checkout-url` printed Stripe's Checkout URLs (about 600
  characters) broken over seven lines; copied, the link fails.
- **Root cause:** the URLs were printed through rich's console, which
  wraps at the terminal width. The tests ran with `COLUMNS=10000`, which
  hid it. 176's `checkout-url` and `portal-url` had the same defect.
- **Reproduced first:** a new test prints a 600-character URL at 80
  columns and requires it on one line: it failed, the URL split at the
  80th column.
- **Fix:** every URL (the onboarding link, `pay-link`, `checkout-url`,
  `portal-url`) is printed with `click.echo` on its own line, unindented.
- **Files:** `src/motodiag/cli/payments.py`, `src/motodiag/cli/billing.py`,
  `tests/support/phase273.py` (a `columns` option),
  `tests/test_phase273_invoice_payments.py`,
  `tests/test_phase273_subscriptions.py`.
- **Verified:** both narrow-terminal tests pass; phase 273's and 176's
  tests: 152 passed.

### 2026-10-06 — Bug fix #2: a tier payment arriving before its subscription is lost

The operator, verbatim: "Before you go on: listen.log shows invoice.paid
answered 503 at 16:40:21, while customer.subscription.created and
payment_intent.succeeded got 200 in the same second. The scratch DB has
the new shop subscription active, but subscription_payments has 0 rows, so
the $2.00 payment isn't recorded, and nothing has retried it since. Find
why it got 503 (likely it arrived before the subscription row existed),
resend that event with `stripe events resend`, and confirm the payment is
recorded. Say in the log whether production relies on Stripe retrying a
5xx for this ordering, and if this is a bug, register it."

- **Issue:** in the webhook run, `invoice.paid`
  (`evt_1UNf9tMI5dskf1ff24sNEfls`) reached the server at 16:40:21 and got
  503; `customer.subscription.created` and the platform's
  `payment_intent.succeeded` got 200 in the same second. The subscription
  was stored `shop active`; `subscription_payments` had 0 rows, and
  nothing redelivered the event.
- **Root cause:** `_handle_subscription_invoice` looked the subscription
  up in the database, found no row (its event had not yet been applied),
  and raised `BillingProviderError` ("not stored yet; retry after its
  subscription event"). That was classed retryable, so the event's record
  was removed and the route answered 503, which the design left to a
  redelivery. `stripe listen` forwards each event once and never retries.
  Stripe does not deliver in order (S0-4, quoting its webhooks page), so
  this ordering is normal, not rare.
- **Does production rely on Stripe retrying a 5xx for this ordering?**
  Before this fix, yes. Stripe's webhooks page: "Stripe attempts to
  deliver events to your destination for up to three days with an
  exponential back off in live mode … We retry event deliveries created
  in a sandbox three times over the course of a few hours." So in
  production the payment would have been recorded on a later retry, minutes
  to hours late, and lost for good if every retry came before the
  subscription event or the endpoint was disabled. With `stripe listen`
  it was lost at once. **After this fix, no:** the payment is recorded on
  first delivery whatever the order. A 503 is now left only for Stripe
  itself being unreadable, where a retry is the right answer.
- **Reproduced first:** a new test delivers `invoice.paid` before any
  subscription event, with Stripe (the fake provider) holding the
  subscription. It failed with exactly the live error ("which is not
  stored yet; retry after its subscription event").
- **Fix:** the subscription handler's re-read is now
  `_store_from_stripe(sub_id, …)`. When an invoice names a subscription
  that is not stored, the handler reads it from Stripe and stores it,
  then records the payment. If Stripe cannot be read, that raises and the
  event is still retried (a test keeps that).
- **The live event:** `bash 273_smoke.sh resend
  evt_1UNf9tMI5dskf1ff24sNEfls` restarted the server and `stripe listen`
  and ran `stripe events resend`. `listen_resend.log`: 16:45:58
  `--> invoice.paid`, 16:45:59 `<-- [200]`. The scratch database now
  holds `subscription_payments`: paid, 200 cents, usd. The subscription
  row already existed, so this redelivery proves the payment is recorded,
  not the new read path; the new path is proved by the test above.
- **Files:** `src/motodiag/billing/webhook_handlers.py`,
  `tests/test_phase273_subscriptions.py`; `273_smoke.sh` gained the
  `resend` stage.
- **Verified:** phase 273's and 176's tests: 153 passed.

A second bug in this build. Two bugs, two causes (rich wrapping;
delivery order), so no shared cause to find yet; a third would stop the
build for one.

### 2026-10-06 — The webhook run, completed

After the resend: the portal call (`POST /v1/billing_portal/sessions` 200)
and the summary (`273_smoke/summary.txt`):
- INV-273-SMOKE-2 paid by the simulated reader, 5678 cents, outcome
  `paid_invoice`; INV-273-SMOKE-1 paid by Checkout, 1234 cents,
  `paid_invoice`. Each `paid_at` is Stripe's time for the event.
- Subscription: `shop active`, period ending 2026-11-06T20:40:16Z, price
  recorded. Its payment: paid, 200 cents, usd.
- Events: 3 `payment_intent.succeeded` (2 from the shop's connected
  account; the third, the platform's subscription charge, ignored as not
  an invoice payment), 1 `customer.subscription.created`, 1
  `invoice.paid`; none with an error.
- **Secrets in the outputs:** the portal session URL (it carries a
  session secret) and a Payment Intent's `client_secret` had been kept in
  `273_smoke/responses/`. Both were redacted before anything was
  committed, and `273_smoke.py` now drops them, as it drops the
  onboarding link. A scan of every output for `sk_`, `rk_`, `whsec_`
  (unredacted), `secret=` and `_secret_` finds none.
