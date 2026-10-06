# Phase 273 — Track O batch 4: payments through Stripe

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-10-06 (v1.0 and v1.1 the same day)

**Outcome (v1.1).** Shipped as planned, after the Step 0 stop and the
credential stop:
- **All four of row 273's verbs have commands, each exercised by a test,
  and each was run against Stripe's test mode:** Connect, the simulated
  reader, an invoice paid by Checkout and one by Terminal (both turned
  paid by Stripe's event through the webhook), and a `shop` tier
  subscription with its payment and a portal session.
- **F187 is closed:** 176's subscription path now changes a tier against
  `2026-09-30.endive`, proved live.
- **Migration 080 is live** at schema 80; its live diff equals the
  approved exact diff; no existing row changed.
- **Two bug fixes,** both found by the webhook run: printed URLs wrapped
  by rich (#1), and a tier payment arriving before its subscription that
  waited on a retry `stripe listen` never makes (#2).
- **Paused:** rows 371 (live payments and production webhooks) and 372
  (payment routes and the app's screens).

Regression of record: 10401 passed, 0 failed at `eaf520d`. Deviations and
Results are at the end.

## Goal

Track O batch 4, row 273: "Stripe Connect, card terminals, invoicing,
subscription billing". The last batch before Gate 16 (292). It folds no
other row.

- **Connect:** a shop gets a Stripe account of its own and receives its
  customers' money.
- **Card terminals:** a card-present payment of a shop invoice through
  Terminal's simulated reader, in test mode, with no hardware.
- **Invoicing:** a shop invoice paid through Stripe. It becomes paid only
  when Stripe's verified event arrives, never on the request that started
  the payment.
- **Subscription billing:** 176's checkout, portal and webhook path, with
  F187 fixed, run against test mode for the first time.

Step 0 is `273_step0.md`; Stripe's pages are quoted in `273_sources.md`.

**The operator's pick (2026-10-06), verbatim:**

> 1A, 2 placeholders, 3A

- **1A:** each shop is a connected account (Accounts v2, `merchant`
  configuration, `dashboard: full`, `fees_collector: stripe`,
  `losses_collector: stripe`), paid by direct charges. The shop pays
  Stripe's fees; refunds and disputes come from the shop's balance; Stripe
  carries negative balances; Stripe-hosted onboarding. No application fee.
- **2 placeholders:** three monthly test-mode prices the operator creates,
  named "… (test placeholder)". Every place that shows a tier price says
  it is a placeholder (below).
- **3A:** CLI only. No route is added and the OpenAPI snapshot does not
  move. **Row 372 ⏸️** takes the payment routes and the app's payment
  screens. **Row 371 ⏸️** (live payments, production webhooks) was paused
  at Step 0.

Every new capability has a `motodiag` command, exercised by a test.

## Outputs

| file | what |
|---|---|
| `src/motodiag/payments/__init__.py` | the package |
| `src/motodiag/payments/stripe_api.py` | the one gateway to the SDK: the API version, the live-key refusal, the client, errors mapped to `StripeUnavailable`, the call log |
| `src/motodiag/payments/connect.py` | a shop's connected account: create, onboarding link, status |
| `src/motodiag/payments/invoice_payments.py` | `invoice_amount_cents`, a Checkout payment, a Terminal payment, the payment rows, the event rules |
| `src/motodiag/payments/terminal.py` | a shop's location and simulated reader |
| `src/motodiag/billing/providers.py` | `StripeBillingProvider` on the gateway; `subscription_data.metadata`; the fake provider holds the subscriptions a test gives it |
| `src/motodiag/billing/webhook_handlers.py` | F187: subscriptions re-read from Stripe; a retryable failure is not recorded; the payment events; live events refused |
| `src/motodiag/billing/subscription_repo.py` | `upsert_from_stripe` requires tier and status (F187) |
| `src/motodiag/api/routes/billing.py` | the webhook answers 503 when the event must be retried, 400 for a live event outside prod; no schema change |
| `src/motodiag/cli/payments.py` | `payments check`; `shop payments`, `shop terminal`; `shop invoice pay-link`, `payments` |
| `src/motodiag/cli/billing.py` | `checkout-url` says the prices are placeholders; `sync` uses the webhook's reading; URLs printed unwrapped (bug fix #1) |
| `src/motodiag/cli/shop.py`, `main.py` | register the new commands |
| `src/motodiag/core/config.py` | `stripe_prices_are_placeholders`, `invoice_payment_return_url`, `connect_return_url`, `connect_refresh_url`, `stripe_call_log` |
| `src/motodiag/core/migrations.py`, `database.py` | migration 080 |
| `pyproject.toml` | `payments = ["stripe==16.0.0"]`; `server` includes it |
| `tests/conftest.py` | no Stripe variable reaches a test |
| `tests/support/stripe_fixtures.py`, `phase273.py` | the fixture HTTP client, the event builder and signer, the frozen webhook clock, the seeds, the CLI runner |
| `tests/fixtures/phase273/` | Stripe responses, each marked recorded (7) or built (7); events are built in the tests |
| `tests/test_phase273_*.py` | six files, 101 tests (Results) |
| `tests/test_phase176_auth_billing.py` | its webhook tests give the fake provider Stripe's state to re-read |
| `tests/test_phase255B_collected_test_floor.py` | 10299 → 10401 |
| `docs/phases/…/273_smoke.sh`, `273_smoke.py`, `273_smoke/` | the smoke calls, the webhook run and the `resend` stage, and their records |
| `docs/phases/…/273_mutate.py` | 41 mutations |
| `docs/phases/…/273_deploy_scope.json`, `273_dryrun_diff.md`, `273_live_diff.md` | the deploy |

## Logic

### The gateway — `payments/stripe_api.py`

- `API_VERSION = "2026-09-30.endive"`, sent on every request
  (`StripeClient(stripe_version=API_VERSION)`). A test requires it to equal
  the installed SDK's `_ApiVersion.CURRENT`, so an SDK bump without a
  deliberate change goes red.
- `refuse_live_key(key, env)`: a key starting `sk_live_` or `rk_live_` is
  refused unless `env` is `prod`, before any client exists. Every path to
  Stripe goes through `client(settings)`, which calls it; 176's provider
  too.
- `client(settings)`: lazy `import stripe` (the no-extras install must
  still import the package); raises `StripeNotConfigured` naming
  `payments check` when there is no key or the provider is not `stripe`.
  The HTTP client is the SDK's own unless a test sets one.
- `call(what, fn)`: maps the SDK's errors to `StripeUnavailable(kind,
  detail)`: `unreachable` (connection), `refused` (authentication or
  permission), `busy` (rate limit), `rejected` (Stripe refused the request;
  its message, which names no secret), `error` (anything else Stripe
  returns). The message always names Stripe.
- **The call log:** when `Settings.stripe_call_log` names a file, each
  request appends one JSON line: UTC time, method, path, HTTP status,
  response bytes, Stripe's request id, the API version sent. Never a
  header value other than the request id, never a body.
- `key_status(settings)` for `payments check`: "set" / "not set", and
  "test mode: yes" when the key starts `sk_test_` or `rk_test_`, "no"
  otherwise. Never any part of the value.

### Connect — `payments/connect.py`

- `connect_shop(shop_id, email)`: if the shop has no account, create one
  with `v2.core.accounts.create`: `display_name` the shop's name,
  `contact_email`, `identity.country` (the shop's country, `us` when its
  tax jurisdiction is `US-*`; otherwise required as `--country`),
  `dashboard: full`, `configuration.merchant.capabilities.card_payments.requested`,
  `defaults.responsibilities` stripe/stripe, `defaults.currency` the
  shop's invoice currency. Store it in `shop_payment_accounts`.
- Then `v2.core.account_links.create` (`use_case.type =
  account_onboarding`, `refresh_url`, `return_url` from Settings) and print
  the link with Stripe's own warning: give it only to the shop's owner,
  once.
- `shop_status(shop_id)`: retrieve the account (including
  `configuration.merchant` and `requirements`), store whether
  `card_payments` is active and what Stripe still needs.
- A payment on a shop whose `card_payments` is not active is refused,
  naming `shop payments status`.

### Invoice payments — `payments/invoice_payments.py`

- `invoice_amount_cents(invoice_id)`: `_dollars_to_cents(total)`, the one
  read of the money columns.
- `start_checkout(invoice_id)`: the invoice must be `sent` or `overdue`;
  the shop must be connected and active. Insert an `invoice_payments` row
  (`channel = checkout`, `status = started`, `amount_cents`). Create a
  Checkout Session on the shop's account (`stripe_account`), `mode =
  payment`, one line "Invoice INV-…" at `amount_cents` in the invoice's
  currency, metadata and `payment_intent_data.metadata` carrying
  `motodiag_payment_id` and `motodiag_invoice_id`. Print the URL; the
  invoice stays as it is, and the command says it becomes paid when
  Stripe's event arrives.
- `start_terminal(invoice_id)`: the same checks, plus a registered reader.
  Payment Intent on the shop's account, `allowed_payment_method_types =
  ["card_present"]`, automatic capture, the same metadata;
  `terminal.readers.process_payment_intent`; in test mode
  `test_helpers.terminal.readers.present_payment_method`.
- `apply_payment_intent(event)` for `payment_intent.succeeded` and
  `.payment_failed`:
  - not ours (no `motodiag_payment_id`, or no such row): recorded on the
    event as ignored;
  - the event's `account` is not the row's account: rejected;
  - failed: `started` → `failed`; never changes `succeeded`;
  - succeeded: `amount_received` must equal the row's `amount_cents` and
    `invoice_amount_cents`, and the currency the invoice's; otherwise the
    payment is `succeeded` with outcome `rejected` and the reason. If the
    invoice is `sent` or `overdue`, it is marked paid, outcome
    `paid_invoice`, by one guarded `UPDATE … WHERE status IN ('sent',
    'overdue')` in the same transaction as the payment row (not 169's
    `mark_invoice_paid`, which opens its own connection), with `paid_at`
    the time Stripe recorded the event (its `created`). If it is already paid
    by anything else, outcome `paid_twice` ("refund one in Stripe"). If
    cancelled, `rejected` ("the invoice was cancelled; refund in
    Stripe"). A second success for the same payment changes nothing.
- `apply_refund(event)` for `charge.refunded`: `refunded_cents =
  max(stored, amount_refunded)`. The invoice status is not changed.

### Terminal — `payments/terminal.py`

- `setup_simulated(shop_id, address)`: a location on the shop's account
  (the address from the options, else the shop's own columns; refused if
  incomplete), then a reader registered with Stripe's simulated
  registration code `simulated-wpe`. Stored in `terminal_locations` and
  `terminal_readers` (`simulated = 1`). Test mode only: refused with a
  live key whatever the env.

### Subscriptions (F187) — `billing/`

- Checkout carries `user_id` and `tier` in `subscription_data.metadata`
  as well as the session's.
- Every `customer.subscription.*` event re-reads the subscription from
  the provider, and stores what it reads: status, customer, price, the
  period from `items.data[0]`, cancel-at-period-end, cancelled-at, trial
  end. The tier comes from metadata, else from the price id through
  Settings' three price ids; neither → the event is recorded with that
  error and nothing is written. No status or tier is ever defaulted.
- `invoice.paid` and `invoice.payment_failed` for a subscription
  (`parent.subscription_details.subscription`) write a
  `subscription_payments` row with `amount_paid_cents`, once per Stripe
  invoice; a failure never overwrites a payment. If the subscription is
  not stored yet (its event not yet applied), the handler reads it from
  Stripe and stores it first (bug fix #2), so the order of delivery does
  not matter here either. 176's no-op `invoice.payment_succeeded` is
  replaced by `invoice.paid`.
- `subscription sync` stores the same reading as the webhook.
- `FakeBillingProvider` keeps the subscriptions a test seeds; retrieving
  an unknown one raises, as Stripe would.

### The webhook

- `stripe_webhook_events` gains `account` and `livemode`.
- An event with `livemode: true` is refused unless env is `prod` (400,
  not recorded).
- A handler that fails because Stripe could not be read
  (`StripeUnavailable`, `BillingProviderError`) removes the event's record
  and the route answers 503, so Stripe retries (in live mode, for up to
  three days). `stripe listen` does not retry: in development such an event
  is redelivered with `stripe events resend`. Any other failure is
  recorded with its error and answered 200, as before.
- `stripe listen --forward-to … --forward-connect-to …` sends both scopes
  to the one route with one secret. Production endpoints and their two
  secrets are row 371.

### The placeholder prices

- `Settings.stripe_prices_are_placeholders: bool = True`. `payments check`
  and `subscription checkout-url` print "tier prices: test placeholders"
  while it is true. The operator turns it off when real prices exist.

### Secrets in tests

- `tests/conftest.py`, at import: every `MOTODIAG_STRIPE_*` and
  `STRIPE_*` variable is removed, then the three Stripe settings are set
  to `""` in the environment, which pydantic-settings reads before
  `.env`, so no Stripe value in `.env` reaches a test.
- `test_phase273_secrets.py` spawns pytest on a planted test outside
  `tests/`, with a planted key in the environment, loading this suite's
  `tests/conftest.py` as a plugin (`-p conftest`): the planted test must
  not find the key. The same run without it must find it (the control).
  Two more tests load Settings from a planted `.env` file: with the
  session's blanks it reads `""`; with the blank removed it reads the key.

### Migration 080

`shop_payment_accounts`, `invoice_payments`, `terminal_locations`,
`terminal_readers`, `subscription_payments`; `stripe_webhook_events` gains
`account` and `livemode`. New tables and columns only; no row changes.
Through the deploy skill.

## Key concepts

- **Direct charges on a v2 account:** every payment object is created
  with `stripe_account = acct_…`, so it lives in the shop's account, and
  its events come in the Connect scope, carrying `account`.
- **The verified event is the only writer** of "paid" for a Stripe
  payment.
- **Order-independent subscriptions:** the event says which subscription;
  Stripe says what it is now.

## Verification checklist

- [x] `pyproject.toml` pins `stripe==16.0.0` in `payments`, and `server`
  includes it; the no-extras packaging test still imports the package
  (in `wholetree.sh --full` and the regression)
- [x] `API_VERSION` equals the SDK's pinned version (test; K3)
- [x] a live key is refused unless prod, at the gateway, the provider and
      a command; a planted live key, and a test-key control (K1, K2, K7)
- [x] a `livemode: true` event is refused unless prod (W1)
- [x] the test session cannot see a planted key; the control without the
      conftest sees it (S1–S3)
- [x] no test reaches the network: the SDK's own client meets 281's guard
- [x] every fixture marked recorded or built; every event signed at test
      time with a test-only secret on a frozen clock; a 301 s old
      signature refused, a 299 s one accepted
- [x] Connect: create, link, status, and a payment refused until active
- [x] invoice by Checkout: paid only by the event; not on start; wrong
      account, amount or currency rejected; paid twice reported; cancelled
      rejected
- [x] Terminal: setup and pay through the fixture client; paid by the event
- [x] each event twice, and each pair in both orders: the same database
- [x] F187: each defect, put back, turns a test red (F1–F6)
- [x] a Stripe outage: named, non-zero exit, stored data shown with its date
- [x] migration 080 forward and back; dry run and live through the deploy
      skill
- [x] smoke: one logged run per surface (Connect, invoice payment, the
      simulated reader, a subscription checkout, the portal), test mode
- [x] the webhook run: `stripe listen` into a server on a scratch copy
- [x] mutations all red: 41/41
- [x] the regression of record (`verify_phase.sh` runs after the merge;
      its result is in the handoff)

## Risks

- **Test mode is not live.** Live onboarding, payouts and HTTPS return
  URLs are row 371.
- **Endive is a fortnight old.** The SDK is pinned exactly. The smoke run
  proved the shapes the code reads; seven fixtures are now Stripe's own
  responses.
- **The account's default API version is `2026-08-26.dahlia`,** so its
  events arrive in that shape while requests go at endive. The handlers
  read only fields both have. A production endpoint should be created at
  endive (row 371).
- **Stripe could change hosted onboarding's test shortcuts;** onboarding
  the test shop was the operator's manual step.

## Deviations from Plan

- **Two bug fixes** found by the webhook run, each with a register entry
  and its own commit: #1 (`5b115db`) printed URLs wrapped by rich, in the
  new commands and in 176's `checkout-url` and `portal-url`; #2
  (`ec4b360`) a tier payment arriving before its subscription waited on a
  retry `stripe listen` never makes. The operator asked mid-run for the
  lost event to be resent with `stripe events resend` and for the log to
  say whether production relied on Stripe's retries; both are in the log.
  The smoke script gained a `resend` stage.
- **The smoke script's form:** `273_smoke.py` runs each command
  in-process with Stripe's own HTTP client wrapped to keep each response;
  v1.0 named a separate `273_webhook_run.sh`, which became the `webhook`
  stage of `273_smoke.sh`.
- **Secrets kept by the recorder, then removed:** a portal session URL and
  a Payment Intent's `client_secret` were in `273_smoke/responses/` before
  any commit; both were redacted and the recorder now drops them.
- **The planted-key proof** loads the conftest with `-p conftest`, and its
  control runs without it; v1.0 said `--noconftest`, which the planted
  file outside `tests/` does not need.
- **Seven fixtures are recorded and seven built** (the two v2 Accounts,
  the account link, the subscription, the errors), each saying why in the
  log.
- **Decided while building** (log, "Built"): `paid_at` is Stripe's event
  time; the paid transition is one guarded `UPDATE`; `subscription sync`
  shares the webhook's reading; `set_http_client_for_tests` removed as
  dead; a reload in a test replaced exception classes and was rewritten.
- **The edit guard** blocked `sed -i` on a scratch probe file; recorded,
  not loosened. Fixtures were put into `tests/` with the Write tool.
- **No refute pass ran.**

## Results

| verb | commands | test |
|---|---|---|
| Connect | `shop payments connect --shop S [--email --country --currency]`, `shop payments status --shop S` | `test_phase273_connect.py` 12 |
| card terminals | `shop terminal setup --shop S --simulated`, `shop terminal pay INV` | `test_phase273_invoice_payments.py` (Terminal) |
| invoicing | `shop invoice pay-link INV`, `shop invoice payments INV`; paid by the webhook | `test_phase273_invoice_payments.py` 35 in all |
| subscription billing | 176's `subscription checkout-url`, `portal-url`, `sync`; the webhook | `test_phase273_subscriptions.py` 24 |
| set-up check | `payments check` | `test_phase273_gateway.py` 22 |
| the test session's secrets | (tests) | `test_phase273_secrets.py` 4 |
| migration 080 | — | `test_phase273_migration.py` 4 |

- **Smoke calls** (2026-10-06, test mode, every request in
  `273_smoke/calls.jsonl` with Stripe's request id): Connect
  `POST /v2/core/accounts` and `/v2/core/account_links` 200 (20:07:57Z),
  `GET /v2/core/accounts/acct_…` 200 (status active, 0 due); the reader
  `POST /v1/terminal/locations` and `/v1/terminal/readers` 200 (20:31:29Z);
  `POST /v1/payment_intents`, `process_payment_intent`,
  `present_payment_method` 200; two `POST /v1/checkout/sessions` 200
  (invoice, subscription); `POST /v1/billing_portal/sessions` 200.
- **The webhook run** (server on a scratch copy, `stripe listen` both
  scopes): INV-273-SMOKE-2 paid by the simulated reader (5678 cents) and
  INV-273-SMOKE-1 by Checkout (1234 cents), each by `connect
  payment_intent.succeeded` → 200; the `shop` subscription stored from the
  re-read (`active`, the items' period, the price); its `invoice.paid`
  503 (bug fix #2), redelivered with `stripe events resend` → 200 →
  paid, 200 cents. No event recorded an error.
- **Mutations: 41/41 red** (`273_mutate.py`).
- **`COLLECTED_TEST_FLOOR` 10299 → 10401.**
- **Deploy:** migration 080 live at schema 80; 5854 → 5855 rows, 109 →
  114 tables; the live diff equals the approved exact diff; no existing
  row changed; backup `motodiag_pre273_20261006_173455.db`.
- Regression of record: 10401 passed, 0 failed, 0 skipped, 0 errors at `eaf520d` (24 min 15 s wall, `python -m pytest -n auto --dist load`, exit 0)
- **Findings:** F187 filed at Step 0 and closed by this phase.
- **Paused rows:** 371 (live payments, production webhooks), 372 (payment
  routes and the app's screens).

## Version history

| version | date | what |
|---|---|---|
| 1.0 | 2026-10-06 | the plan after the operator's 1A, 2 placeholders, 3A |
| 1.1 | 2026-10-06 | every section updated to what shipped; Outcome, Deviations, Results |
