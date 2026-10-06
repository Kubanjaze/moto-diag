# Phase 273 — Track O batch 4: payments through Stripe

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-10-06

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
| `src/motodiag/api/routes/billing.py` | the webhook answers 503 when the event must be retried; no schema change |
| `src/motodiag/cli/payments.py` | `payments check`; `shop payments`, `shop terminal`; `shop invoice pay-link`, `payments` |
| `src/motodiag/core/config.py` | `invoice_payment_return_url`, `connect_return_url`, `connect_refresh_url`, `stripe_call_log` |
| `src/motodiag/core/migrations.py`, `database.py` | migration 080 |
| `pyproject.toml` | `payments = ["stripe==16.0.0"]`; `server` includes it |
| `tests/conftest.py` | no Stripe variable reaches a test |
| `tests/support/stripe_fixtures.py` | the fixture HTTP client, the event signer, the frozen clock |
| `tests/fixtures/phase273/` | Stripe responses and events, each marked recorded or built |
| `tests/test_phase273_*.py` | below |
| `docs/phases/in_progress/273_smoke.sh` and `273_webhook_run.sh` | the smoke calls and the webhook run |

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
    invoice is `sent` or `overdue`, it is marked paid (169's
    `mark_invoice_paid`), outcome `paid_invoice`. If it is already paid
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
  invoice; a failure never overwrites a payment.
- `FakeBillingProvider` keeps the subscriptions a test seeds; retrieving
  an unknown one raises, as Stripe would.

### The webhook

- `stripe_webhook_events` gains `account` and `livemode`.
- An event with `livemode: true` is refused unless env is `prod` (400,
  not recorded).
- A handler that fails because Stripe could not be read
  (`StripeUnavailable`, `BillingProviderError`) removes the event's record
  and the route answers 503, so Stripe or `stripe listen` retries. Any
  other failure is recorded with its error and answered 200, as before.
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
- `test_phase273_secrets.py` spawns pytest on a planted test, with a
  planted key in the environment: the planted test must not find it. The
  same run with `--noconftest` must find it (the control). A second test
  loads Settings from a planted `.env` file under the session and must
  read `""`.

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

- [ ] `pyproject.toml` pins `stripe==16.0.0` in `payments`, and `server`
  includes it; the no-extras packaging test still imports the package
- [ ] `API_VERSION` equals the SDK's pinned version (test)
- [ ] a live key is refused unless prod, at the gateway, the provider and
      every command; planted control
- [ ] a `livemode: true` event is refused unless prod
- [ ] the test session cannot see a planted key; `--noconftest` control
- [ ] no test reaches the network: a planted Stripe call fails on the guard
- [ ] every fixture marked recorded or built; every event signed at test
      time with a test-only secret on a frozen clock; a 301 s old
      signature refused
- [ ] Connect: create, link, status, and a payment refused until active
- [ ] invoice by Checkout: paid only by the event; not on start; wrong
      account, amount or currency rejected; paid twice reported; cancelled
      rejected
- [ ] Terminal: setup and pay through the fixture client; paid by the event
- [ ] each event twice, and each pair in both orders: the same database
- [ ] F187: each defect has a test that fails on 176's code
- [ ] a Stripe outage: named, non-zero exit, stored data shown with its date
- [ ] migration 080 forward and back; dry run and live through the deploy
      skill
- [ ] smoke: one logged call per surface (Connect, invoice payment, the
      simulated reader, a subscription checkout), test mode
- [ ] the webhook run: `stripe listen` into a server on a scratch copy
- [ ] mutations all red
- [ ] the regression of record, `verify_phase.sh`

## Risks

- **Test mode is not live.** Live onboarding, payouts and HTTPS return
  URLs are row 371.
- **Endive is a fortnight old.** The SDK is pinned exactly; the smoke
  calls are the first proof that the shapes the fixtures were built from
  are what Stripe sends.
- **Stripe could change hosted onboarding's test shortcuts;** the
  operator's onboarding of the test shop is a manual step at the
  credential stop.

## Deviations from Plan

(v1.1)

## Results

(v1.1)
