# Phase 372B — The app's payment screens

**Version 1.0, 2026-11-22.** Plan by the advisor session on the Mac (K81,
K98, K128), from this repository's master `618bc73` and the app's `main`
`58142e4`. Built by the operator's own session in `moto-diag-mobile`, on the
branch `phase-372B-the-apps-payment-screens`, from
`docs/prompts/372B_the_apps_payment_screens.txt`. Classification:
**extension** (`372B_step0.md`). This plan is committed before any code.

## Goal

In the app, a shop's owner connects the shop to Stripe for card payments.
The owner or the service writer takes an invoice's payment at the card
reader or by a pay-link, and sees how it ended. Anyone signed in sees their
plan, and can choose one or manage it. Over 372's five routes and the two
billing routes. No server change.

## The plan of record

'Next, in order' #23 (K98; K128 moved 344 after 210), the last of the
app's three screens: sign-in (303B) and the terms (334B) are closed. Built
by the operator's own session in the app's repository (the home desktop's
main chat), beside the fleet's 293. The operator merges the app's pull
request after the advisor's review.

## Logic

The app's name rule stands: a credential from the sign-in box is **a
sign-in**, never "a session".

### 1. One hook for the payment routes

`src/hooks/useShopPayments.ts`, over the shared client (`src/api/client.ts`):
the account read (with `refresh`), connect, the two starts and an invoice's
payments list. A 403, 404, 409 or 503 comes out as a typed error carrying
the server's `detail`, as `useWorkOrderParts.ts` and `shopAccessErrors.ts`
do. The app shows the server's detail and never invents a reason.

### 2. Card payments setup

`PaymentsSetupScreen` in `ShopStack`, titled "Card payments":
- the account's state in words: not connected; onboarding not finished,
  with how many things are still due; or ready;
- "Connect with Stripe", or "Continue onboarding", calls connect and opens
  `onboarding_url` with `Linking.openURL`. The link is used once, by the
  owner, from the app, and is never sent by email or text;
- when the app comes back to the front (`AppState` "active"), read the
  account again with `refresh=true`, as `useTier.ts` does.

### 3. An invoice's payment

`InvoicesScreen` and `InvoicePaymentScreen` in `ShopStack`:
- the shop's sent and overdue invoices (`GET /v1/shop/{shop_id}/invoices`
  with `status=`), and an invoice's total;
- "Send to card reader" calls the terminal start. With no reader, the
  server's 409 says so: no route registers a reader yet;
- "Pay-link" calls the checkout start and hands `checkout_url` to the share
  sheet (`react-native-share`);
- then the screen reads the payments list every five seconds until the
  newest payment is succeeded or failed, or the screen loses focus, and
  shows the outcome and its reason, with the sentence that the invoice is
  paid only when Stripe confirms it.

### 4. The plan screen

`PlanScreen` in `HomeStack`, reached from `SettingsScreen`:
- the tier from `useTier`, and the three plans by the server's names;
- "Choose" on each calls `POST /v1/billing/checkout-session` with that
  tier and opens `checkout_url`;
- "Manage plan" calls `POST /v1/billing/portal-session` and opens
  `portal_url`. A 402 whose type ends `subscription-required` reads "Choose
  a plan first.";
- `useTier`'s existing re-read when the app comes back to the front
  updates the Shop tab when the tier changes;
- no price anywhere in the app: Stripe's own pages show them.

### 5. The terms

With the terms switch on, these routes answer 403 `terms-not-accepted`
until the user accepts. 334B's box opens over the screen; nothing here
handles it.

### 6. The record

This repository keeps `372B_step0.md`, this plan, `372B_phase_log.md`, row
372B and, at the close-out, the handoff. The advisor writes them, from the
app's pull request. The app's session writes nothing here, and the app's
`phase_log.md` (185 to 204) is not touched.

## Rule-1 stops anticipated

- **A real fork: none known.** The design is 372's item 7, re-read; screen
  layout and hook shapes are build choices.
- **A threshold or a rule's definition: none.** No server change.
- **A test that cannot be made green: none known.** If one cannot be made
  green, the session stops.
- **A login or a credential: none for the build.** Tests use made-up
  values and a mocked fetch. A check on a phone uses Stripe's test mode on
  a server with test keys, at the operator's choice after the merge. No
  real card and no real money in any check without the operator.
- **A live-database change: none.**

## Tests

In the app, in its own style (a mocked fetch; `*.smoke.test.tsx` for
screens):
1. The hook: each route called with the right path and body; 403, 404,
   409 and 503 come out typed, with the server's detail.
2. Card payments: the three states in words; connect opens the onboarding
   link; coming back to the front reads again with `refresh=true`.
3. An invoice: the list asks for sent and overdue; the reader start and
   the pay-link start; the pay-link goes to the share sheet; the polling
   stops on succeeded, on failed, and when the screen loses focus; the
   outcome and its reason are shown, with the "paid only when Stripe
   confirms" sentence.
4. The plan screen: "Choose" opens the checkout link for that tier;
   "Manage plan" opens the portal link; a 402 reads "Choose a plan first.";
   no price is shown.
5. Each new test is seen red before its code (the pull request says how);
   303B's and 334B's tests pass unchanged.

`npx tsc --noEmit` and `npx eslint .` with no errors; `npx jest` green, with
the count before and after in the pull request.

## Non-goals

Registering a card reader (no route does yet); refunds; payouts or a
balance; prices in the app; any server change; Stripe Checkout's terms
consent (a server switch, parked on Stripe support); the store listings; a
build for the phones.

## Deviations

To be written at v1.1.

## Results

To be written at v1.1.

## Planned items

- [ ] `useShopPayments.ts`, with typed errors
- [ ] Card payments setup, with the onboarding link and the re-read
- [ ] An invoice's payment: the reader, the pay-link, the outcome
- [ ] The plan screen: choose and manage
- [ ] The tests, each seen red; tsc, eslint and jest clean
- [ ] The app's pull request, merged by the operator after review
- [ ] The close-out here: v1.1, the log, row 372B ✅, the handoff

## Version history

| version | date | change |
|---|---|---|
| 1.0 | 2026-11-22 | The plan, from Step 0 (K81, K98, K128). |
