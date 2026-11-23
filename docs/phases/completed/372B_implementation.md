# Phase 372B — The app's payment screens

**Version 1.1, 2026-11-22.** Closed. v1.0 (the same day) was the plan by
the advisor session on the Mac (K81, K98, K128), from this repository's
master `618bc73` and the app's `main` `58142e4`. Built by the operator's
own session in `moto-diag-mobile`, on the branch
`phase-372B-the-apps-payment-screens`, from
`docs/prompts/372B_the_apps_payment_screens.txt`: pull request #13, head
`cb0786d`, merged by the operator as `f87d04b` on 2026-11-22.
Classification: **extension** (`372B_step0.md`). The plan was committed
before any code; this version records what was built, from the pull
request's description and the advisor's review of it.

## Goal

In the app, a shop's owner connects the shop to Stripe for card payments.
The owner or the service writer takes an invoice's payment at the card
reader or by a pay-link, and sees how it ended. Anyone signed in sees their
plan, and can choose one or manage it. Over 372's five routes and the two
billing routes. No server change.

Met in code and tests. The check on a phone waits for Stripe's test mode on
a server with test keys, at the operator's choice (Rule-1 stops, and the
handoff).

## The plan of record

'Next, in order' #23 (K98; K128 moved 344 after 210), the last of the
app's three screens: sign-in (303B) and the terms (334B) closed before it,
and this phase closes the three. Built by the operator's own session in the
app's repository (the home desktop's main chat), beside the fleet's 293;
the operator merged the app's pull request after the advisor's review.
After it on the list comes 210.

## Logic

The app's name rule stands: a credential from the sign-in box is **a
sign-in**, never "a session". Built that way.

### 1. One hook for the payment routes

As planned, in commit `ecd9e8d`. `src/hooks/useShopPayments.ts`, over the
shared client: the account read (with `refresh`), connect, the checkout and
terminal starts, an invoice's payments list, and the shop's sent and
overdue invoices, newest first. A 403, 404, 409 or 503 comes out as a
`PaymentRefusal` `{kind, status, detail}` carrying the server's `detail`,
or its title when there is none. Anything else (401, 402, no network) is a
`ShopAccessError`, as on the other shop screens. The app never invents a
reason.

### 2. Card payments setup

As planned, in commit `da9e933`. `PaymentsSetupScreen` in `ShopStack`,
titled "Card payments":
- the account's state in words: not connected (the server's 404, "this
  shop has no Stripe account yet"); onboarding not finished, with how many
  things are still due; or ready;
- a "Contact email for Stripe" field, which connect needs the first time
  (Deviations, 2);
- "Connect with Stripe", or "Continue onboarding", calls connect and opens
  `onboarding_url` with `Linking.openURL`. The link never goes on the share
  sheet;
- when the app comes back to the front (`AppState` "active"), the account
  is read again with `refresh=true`.

### 3. An invoice's payment

As planned, in commit `164ff08`. `InvoicesScreen` and
`InvoicePaymentScreen` in `ShopStack`:
- the shop's sent and overdue invoices, each with its number, total and
  status;
- "Send to card reader" calls the terminal start. With no reader, the
  server's 409 sentence is shown;
- "Pay-link" calls the checkout start and hands `checkout_url` to the share
  sheet (`react-native-share`);
- then the payments list is read every five seconds until the newest
  payment is no longer `started` (the table allows only `started`, `failed`
  and `succeeded`), or the screen loses focus. The outcome and its reason
  are shown, with the sentence that the invoice is paid only when Stripe
  confirms it. Added in the build: coming back to the screen reads the list
  once, and starts the polling again if a payment is still out
  (Deviations, 6).

### 4. The plan screen

As planned, in commit `cb0786d`. `PlanScreen` in `HomeStack`, reached from
`SettingsScreen` by a "Plan" card (Deviations, 3):
- the tier from `useTier`, and the three plans by the server's names
  (`individual`, `shop` and `company`, as `SUBSCRIPTION_TIERS`);
- "Choose" calls `POST /v1/billing/checkout-session` with that tier and
  opens `checkout_url`;
- "Manage plan" calls `POST /v1/billing/portal-session` and opens
  `portal_url`. With no plan, the server's 402 `subscription-required`
  reads "Choose a plan first.";
- no price anywhere in the app.

### 5. The terms

As planned: nothing here handles them. The terms refusal is caught in the
shared client (`src/api/client.ts`, 334B) before any of these screens sees
its error, so 334B's box opens over them.

### 6. The record

As planned. This repository keeps `372B_step0.md`, this plan,
`372B_phase_log.md`, row 372B and the handoff
`docs/handoffs/2026-11-22_372B_closed.md`, written by the advisor from the
app's pull request. The app's session wrote nothing here, and the app's
`phase_log.md` was not touched.

## Rule-1 stops

None met in the build.
- **A real fork:** none.
- **A threshold or a rule's definition:** none. No server change.
- **A test that cannot be made green:** none. No existing test changed.
- **A login or a credential:** none; the tests use made-up values and a
  mocked client. The check on a phone needs Stripe's test mode on a server
  with test keys, at the operator's choice after the merge. It has not run.
- **A live-database change:** none.

## Tests

In the app, 37 new tests in four new files, so 303B's and 334B's files are
unchanged:
- `__tests__/hooks/useShopPayments.test.ts` (13): each route's path and
  body; connect with an email and with none; the invoice list newest
  first; 403, 404, 409 and 503 typed with the server's detail, and a read
  refusal the same way; other failures to the shop access errors; the
  title when there is no detail.
- `__tests__/screens/PaymentsSetup.smoke.test.tsx` (7): the three states
  in words; another refusal's sentence; connect opening the onboarding
  link; a refused connect opening nothing; the re-read with `refresh` on
  coming back to the front.
- `__tests__/screens/InvoicePayment.smoke.test.tsx` (10): the list with
  totals, opening an invoice, a refusal's sentence; the total and the
  paid-when sentence; the pay-link to the share sheet; the reader start; a
  reader refusal that watches nothing; the polling stopping on succeeded,
  on failed (with why), and on losing focus.
- `__tests__/screens/Plan.smoke.test.tsx` (7): the tier and the three
  plans by the server's names; no price; "Choose" and "Manage plan"; the
  402's "Choose a plan first."; another refusal's sentence; Settings
  leading to the plan screen.
- **Each seen red first,** as the pull request records: each file failed
  with `Cannot find module` for its hook or screen, and the code followed
  in the same commit.

## Non-goals

Registering a card reader (no route does yet); refunds; payouts or a
balance; prices in the app; any server change; Stripe Checkout's terms
consent (a server switch, parked on Stripe support); the store listings; a
build for the phones. None of them was built.

## Deviations

1. **The way in to the shop's screens:** two compact buttons, "Invoices"
   and "Card payments", on `WorkOrderListScreen`, the Shop tab's first
   screen, with the active shop's id. The plan named the stack, not the
   way in. They show for every member; the server refuses connect to a
   member without billing rights (403, `manage_billing`), with its
   sentence.
2. **A "Contact email for Stripe" field** on the setup screen. The plan
   did not name it; the server's connect needs `contact_email` the first
   time. Left empty, connect is sent an empty body, and the first time the
   server refuses it (409) with its own sentence.
3. **The way in to the plan screen:** a "Plan" card with a "Your plan"
   button in `SettingsScreen`, whose `navigation` prop is now optional so
   the existing bare render in `SettingsServer.test.tsx` still works.
4. **`src/api/errors.ts`** gains `BillingProblemSlug =
   'subscription-required'`, so `hasProblemSlug` types the new ending as it
   does the sign-in and terms ones.
5. **`src/screens/formatMoney.ts`,** a small cents-to-text helper for the
   invoice totals, never used for a plan's price.
6. **Coming back to the payment screen** reads the payments list once and
   starts the polling again if a payment is still out. The polling always
   stops on blur.
7. **Not run: the check on a phone,** in Stripe's test mode (Rule-1
   stops). It is open in the handoff.

## Results

| | before (`main` `58142e4`) | after (`cb0786d`) |
|---|---|---|
| `npx jest` | 109 suites, 1271 passed | 113 suites, 1308 passed (+37) |
| `npx tsc --noEmit` | clean | clean |
| `npx eslint .` | 0 errors, 143 warnings | 0 errors, 150 warnings (+7, all `no-void`) |
| `npm run generate-api-types` | changes nothing | — |

- **The advisor's re-run on the Mac,** 2026-11-22, in a scratchpad clone at
  `cb0786d`, with the same lockfile as the app checkout: tsc exit 0; eslint
  exit 0, 0 errors and 150 warnings; jest 113 suites and 1308 tests passed.
  The pull request adds test files only and removes no line of a test; no
  package file and no `api-types.ts` changed.
- **Read against this repository's code:** the tier names
  (`SUBSCRIPTION_TIERS`); the portal's 402 with no plan; the account's 404
  with no Stripe account; connect's `contact_email` the first time and its
  `manage_billing`; the three payment statuses (`invoice_payments`); the
  invoice list's `invoice_number`, `total_cents` and `currency`; the terms
  refusal caught in the app's shared client.
- **Merged** by the operator as `f87d04b` (moto-diag-mobile `main`),
  2026-11-23 at 01:28 UTC.
- **This repository:** no code changed. Its regression of record, on the
  close-out's merge of master (`0bd368b`), is in the log.

## Planned items

- [x] `useShopPayments.ts`, with typed errors (`ecd9e8d`)
- [x] Card payments setup, with the onboarding link and the re-read
  (`da9e933`)
- [x] An invoice's payment: the reader, the pay-link, the outcome
  (`164ff08`)
- [x] The plan screen: choose and manage (`cb0786d`)
- [x] The tests, each seen red; tsc, eslint and jest clean
- [x] The app's pull request, merged by the operator after review (#13,
  `f87d04b`)
- [x] The close-out here: v1.1, the log, row 372B ✅, the handoff

## Version history

| version | date | change |
|---|---|---|
| 1.0 | 2026-11-22 | The plan, from Step 0 (K81, K98, K128). |
| 1.1 | 2026-11-22 | Closed: what was built (pull request #13, `cb0786d`, merged as `f87d04b`), seven deviations, the results. |
