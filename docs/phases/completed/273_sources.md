# Phase 273 — the sources, quoted

Every page below was fetched on **2026-10-06 at about 18:12 UTC** as
Markdown, by appending `.md` to its docs.stripe.com URL (the form Stripe's
own `https://docs.stripe.com/llms.txt` lists). Quotes are copied from the
fetched text with link targets removed, and the pages' typographic
apostrophes (’) written as ASCII ('); nothing inside quotation marks is
paraphrased. These are documentation pages: no Stripe API endpoint was
called while writing this file.

The SDK facts come from the `stripe==16.0.0` wheel, downloaded with
`pip download --no-deps` into the session scratchpad (not installed):
sha256 `6a401baf2fc19c59ccb59005e674f8da8fa256e8db319ad8c50292f4cddf8c26`.

---

## C1. Accounts v2 and configurations

<https://docs.stripe.com/connect/accounts-v2>

> v2 `Accounts` use *configurations* (Account configurations represent
> role-based functionality that you can enable for accounts, such as
> merchant, customer, or recipient) to enable different sets of
> functionality. For example, adding the `merchant` configuration to a v2
> `Account` enables it to receive payments.

> The `merchant` configuration allows an `Account` to accept payments from
> customers. It includes the `card_payments` and `stripe_balance.payouts`
> (replacing v1 `payouts`) capabilities.

## C2. Responsibilities and dashboard

<https://docs.stripe.com/connect/accounts-v2/connected-account-configuration>

> You must define `defaults.responsibilities` properties when you add the
> Merchant configuration to an account. You can't update their values later.

`fees_collector`: "`application`: Your platform collects application fees
from the connected account, and Stripe collects payment fees from your
platform." / "`stripe`: Stripe collects payment fees directly from the
connected account."

`losses_collector`: "`application`: Your platform is responsible for
negative balances and manages risk for the connected account." /
"`stripe`: Stripe is liable for the connected account's negative balances.
Your platform is still liable for negative balances on your platform
account."

> If you set `losses_collector` to `application`, then you must also set
> `fees_collector` to `application`.

`dashboard`: "`express`: The connected account can access the Stripe Express
Dashboard, which offers limited functionality." / "`full`: The connected
account can access the full Stripe Dashboard." / "`none`: The connected
account can't access either Stripe Dashboard. Your platform must provide
all Stripe-related functionality."

> Your platform is responsible only when you set
> `defaults.responsibilities.losses_collector` to `application` and
> `dashboard` to `none`.

(of collecting KYC requirements)

## C3. The legacy account types

<https://docs.stripe.com/connect/integration-recommendations>

> **Legacy connected account types (Standard, Express, and Custom)**:
> (deprecated) The legacy account types support limited configurations and
> can have complex fee behaviors.

> For integrations using direct charges, we recommend assigning
> responsibility for connected account negative balances to Stripe.

## C4. A SaaS platform's two models

<https://docs.stripe.com/connect/saas>

Stripe-owned pricing model: "Are the *merchant of record* … for payments
from their customers." "Pay Stripe fees." "Assume liability for their
negative balances." "Process payments as direct charges."

Buy rate model: "Don't pay Stripe fees." "Are liable to the platform, not
Stripe, for their negative balances."

## C5. Charges, refunds and disputes

<https://docs.stripe.com/connect/charges>

Direct charges: "Refunds and chargebacks reduce the connected account's
balance." Destination charges: "Refunds and chargebacks reduce your
platform's balance." "Stripe debits fees from your platform's balance."

> For disputes on payments created using direct charges, Stripe debits the
> disputed amount from the connected account's balance, not your
> platform's balance.

## C6. Onboarding

<https://docs.stripe.com/connect/onboarding>

> We recommend using Stripe-hosted onboarding or Embedded onboarding.

<https://docs.stripe.com/connect/hosted-onboarding>

> You can use HTTP for your `refresh_url` and `return_url` while you're in
> a testing environment (for example, to test locally), but live mode only
> accepts HTTPS.

> Don't email, text, or otherwise send account link URLs outside of your
> platform application.

## C7. Terminal with Connect, direct charges

<https://docs.stripe.com/terminal/features/connect.md?connect-charge-type=direct>

> With this integration, all API resources belong to the connected account
> rather than your platform. The connected account is responsible for the
> cost of Stripe fees, refunds, and chargebacks.

> If you're using a server-driven integration, you don't need to create a
> connection token.

The page's Payment Intent example sends
`allowed_payment_method_types[]=card_present` with the `Stripe-Account`
header.

## C8. The simulated reader

<https://docs.stripe.com/terminal/references/testing>

> Stripe Terminal SDKs and server-driven integration come with a built-in
> simulated card reader, so you can develop and test your app without
> connecting to physical hardware.

> When using the server-driven integration, use the present_payment_method
> endpoint to simulate a cardholder tapping or inserting their card on the
> reader.

## C9. Webhook delivery

<https://docs.stripe.com/webhooks>

> Stripe doesn't guarantee the delivery of events in the order that
> they're generated.

> Don't use `created` to determine event order or whether you've already
> processed an event. Track event IDs to identify duplicate deliveries
> instead. You can also use the API to retrieve any missing objects.

> Webhook endpoints might occasionally receive the same event more than
> once.

> Our libraries have a default tolerance of 5 minutes between the
> timestamp and the current time.

The SDK: `stripe/_webhook.py` sets `DEFAULT_TOLERANCE = 300` and compares
with `time.time()`.

## C10. Metadata does not travel

<https://docs.stripe.com/metadata>

> An object's metadata doesn't automatically copy to related objects.

> Data you include with the subscription_data.metadata attribute saves to
> the underlying Subscription's metadata.

## C11. The billing period moved (Basil)

<https://docs.stripe.com/changelog/basil/2025-03-31/deprecate-subscription-current-period-start-and-end>

> `current_period_start` and `current_period_end` fields are no longer
> available on the subscription resource.

## C12. The API version

<https://docs.stripe.com/api/versioning>

> The current version is 2026-09-30.endive.

> Starting from `stripe-python v6`, the API version fixed at the time of
> your `stripe-python` version release dictates the requests you send
> using `stripe-python`.

The `stripe==16.0.0` wheel's `stripe/_api_version.py`: `CURRENT =
"2026-09-30.endive"`.

<https://docs.stripe.com/changelog/endive>: among the breaking changes,
"Removes the payment method types parameter from Checkout Sessions" and
"Removes the payment method types parameter from Payment Intents and Setup
Intents".
