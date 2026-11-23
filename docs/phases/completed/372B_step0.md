# Phase 372B — Step 0: what the app has for payments

**Written 2026-11-22** by the advisor session on the Mac, from this
repository's master `618bc73` and the app's `main` at `58142e4` (334B's
merge), at the operator's word (K81, K98, K128; row 372B). The app's code
was read, never changed. The build is the operator's own session in
`moto-diag-mobile`, which writes nothing here.

Classification: **extension.** The server has had the five payment routes
since Phase 372 and the two billing routes since Phase 176. The app's types
name all seven (372's snapshot `13b6e68` is on the app's `main`). The app
already has the stacks, the settings screen, the shop-access errors, the
share sheet and the tier hook these screens plug into. Nothing in the app
calls these routes yet.

## S0-1 — the nouns, counted in the app's source

Each count is `git grep -c -F -e '<term>' -- src ':!src/api-types.ts'` in
`moto-diag-mobile` at `58142e4`, summed over files:

| term | lines | what it shows |
|---|---|---|
| `payments/account` | 0 | nothing calls the payment routes |
| `billing/checkout-session` | 0 | nothing calls the billing routes |
| `/invoices` | 0 | nothing lists a shop's invoices |
| `react-native-share` | 7 | the share sheet is already in use |

The generated types name every route below: `grep -c -F -e '<route>' src/api-types.ts`
is 1 or more for `/payments/account`, `/payments/connect`,
`/payments/checkout`, `/payments/terminal`, `/{invoice_id}/payments"`,
`/billing/checkout-session`, `/billing/portal-session` and
`/{shop_id}/invoices"`. `git merge-base --is-ancestor 13b6e68 origin/main`
holds.

What the screens build on, read at `58142e4`: `src/navigation/ShopStack.tsx`
and `src/navigation/HomeStack.tsx`; `src/screens/SettingsScreen.tsx`;
`src/hooks/shopAccessErrors.ts` and `src/hooks/useWorkOrderParts.ts` (typed
errors carrying the server's detail); `src/hooks/useTier.ts` (which re-reads
when the app comes back to the front); and, since 334B, `Linking.openURL` in
`src/screens/TermsModal.tsx`.

## S0-2 — the server, on master `618bc73`

- `src/motodiag/api/routes/payments.py`, all needing the Shop tier and the
  caller's shop access:
  - `GET /v1/shop/{shop_id}/payments/account[?refresh=true]`;
  - `POST /v1/shop/{shop_id}/payments/connect` (the onboarding link);
  - `POST /v1/shop/{shop_id}/invoices/{invoice_id}/payments/checkout`
    (201, a pay-link);
  - `POST /v1/shop/{shop_id}/invoices/{invoice_id}/payments/terminal`
    (201, to the shop's card reader);
  - `GET /v1/shop/{shop_id}/invoices/{invoice_id}/payments`.
- `src/motodiag/api/routes/billing.py`: `POST /v1/billing/checkout-session`
  (`tier` → `checkout_url`) and `POST /v1/billing/portal-session`
  (`portal_url`; 402 with the type ending `subscription-required` when
  there is no subscription yet).
- `src/motodiag/api/routes/shop_mgmt.py`: `GET /v1/shop/{shop_id}/invoices`
  with `status=` and `limit=`.
- Starting a payment never pays the invoice: it is paid only by Stripe's
  verified news (372's handoff). No route registers a card reader; the
  simulated reader is for test mode only (372's handoff).

## S0-3 — what changed since 372's prompt was written

`docs/prompts/372_the_apps_payment_screens.txt` (2026-11-12) was written
for 372's own branch under option A. The operator chose B (K81), so the
screens are this row. Since then:
- **Staff sign-in (303B)** and **the terms box (334B)** are on the app's
  `main`. While the terms switch is on, these routes answer 403
  `terms-not-accepted` until the user accepts, and 334B's box handles it.
- **The plan names** are the server's since 404 (K84): "Individual: for
  your own bikes", "Shop", "Company".
- **The app's name rule** holds: a credential from the sign-in box is "a
  sign-in", never "a session".
