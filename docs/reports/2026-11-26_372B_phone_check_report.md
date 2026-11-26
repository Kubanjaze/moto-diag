# 372B: the check on a phone, in Stripe's test mode (2026-11-26)

**Result: passed.** All four checks named in "What is open" in
`docs/handoffs/2026-11-22_372B_closed.md` passed on the operator's iPhone
(iPhone 18 Pro Max, the app's main build `0b6481e`, which holds `2f6739c`,
`58142e4` and `f87d04b`), against a separate test server on the home
desktop. Live, its settings, its database and live Stripe were not touched.

Run by the operator on 2026-11-26, between about 09:20 and 10:55 EST. The
blocks were written and dry-run in a cloud thread first, against a stand-in
home folder.

## The four checks

| # | Check | Outcome |
|---|---|---|
| 1 | Connect a test shop and finish Stripe's test setup | Passed. Card payments read "Ready. The shop can take card payments." The first pass left "2 things still due" (see findings). |
| 2 | Send a pay-link and pay it with Stripe's test card | Passed. The pay-link came through the share sheet and was paid with 4242… in Stripe's sandbox checkout. |
| 3 | See the outcome on the screen | Passed. The invoice screen showed it paid once Stripe confirmed. The test database recorded the payment as `started`, then `succeeded` / `paid_invoice`, 10284 cents. Invoice INV-1-1-20261126 was `paid`, at 102.84. |
| 4 | Choose a plan, then open "Manage plan" | Passed. Shop was chosen, sandbox checkout was paid with 4242…, the plan read Shop, and the Shop tab appeared within seconds. Manage plan opened Stripe's sandbox portal, showing the $99 subscription and a paid invoice. |

These two known gaps were not tested, as agreed beforehand: "Send to card reader" returns the 409, and the Invoices and Card payments buttons show for every member.

## How the test server was set up

- **Folder.** `~/motodiag/test372` on the home desktop holds its own `test.env` (mode 600), its own `test.db` and its own `data/`. It ran the live server's code and venv (`~/motodiag/server`), started by hand, with no systemd unit.
- **Mode, port and key.** It ran with `MOTODIAG_ENV=dev`; the code refuses a live key outside prod. It listened on port 8372. It used a Stripe test key (`sk_test_`), which the operator typed into a hidden prompt and never put in chat.
- **Prices.** Three test prices were found or made by lookup key: `mekno_test_individual`, `mekno_test_shop` and `mekno_test_company` (monthly, $19, $99 and $299). The placeholders flag was on.
- **Its own payments feed.** It ran a second `payments feed run` process against the test DB. That process had no webhook secret and no Sentry DSN, so live's feed and alarm were unaffected.
- **Phone route.** The phone reached it through `tailscale serve --bg --https=8443 http://127.0.0.1:8372` on Windows, at the app's server address `https://desktop-76s9bqv.taila45995.ts.net:8443`. Live's 443 → 8000 was left as it was.
- **Test data.** The shop was "Mekno Test Shop" (id 1), with a test owner login, made by `shop onboard run`. It had test labour of $95/h and US-TX tax at 8.25%. The invoice was made through the API: one hour of labour, total $102.84.
- **Stripe test ids.** The connected account was `acct_1Ug42KM96l0QL1xk`, in test mode.
- **Teardown.** The stop block stops both processes and deletes `test.env` and `owner.txt`; the test DB stays. Then `tailscale serve --https=8443 off`, and the phone's server address goes back to live with a fresh sign-in to the operator's live account.
- **Blocks.** `step1_test_server.sh`, `step6_test_invoice.sh`, `step8_stop_test_server.sh`, `check_test_server.sh` and `what_stripe_wants.sh` stayed with the thread that wrote this report; they are not in this repository.

## Findings (none blocks; for the app and for shop one's onboarding)

**In the app (moto-diag-mobile):**
1. **Keyboard covers the text box.** On the sign-in screen and the server-address screen, the text box does not move above the keyboard, so you cannot see what you type.
2. **"Individual (your plan)" before any payment.** A new owner with no subscription sees "Your plan: Individual", Individual marked "(your plan)", and Manage plan enabled. The server answers `tier: null`, and the app falls back to the account's default tier. It should say "No plan yet" and hide or disable Manage plan.
3. **Things due are counted but not named.** Card payments says "Onboarding not finished: 2 things still due at Stripe", but not what they are. "Continue onboarding" went straight to Stripe's review page and the thank-you page, so the owner could not tell what Stripe wanted. The server already reads `requirements.entries[].description`, and could pass the names through.
4. **A paid invoice vanishes from Invoices.** The list shows only sent and overdue invoices, so once paid, the invoice disappears. It read as "it got wiped". It should show a paid state, or a "Paid" section.
5. **The Shop tab appears only once the plan is Shop or Company.** This is by design (`hasShopAccess`), but nothing tells a new owner where Card payments and Invoices are until they pay.

**For shop one's onboarding notes (Stripe's side, not our code):**
6. **Checkout's phone and email.** Checkout's phone field rejected 000 000 0000, and checkout requires an email. Use a real-looking phone number.
7. **Connect sign-up needs a fresh email.** If the email is already a Stripe login (support@getmekno.com, or a taken address like testshop@example.com), the sign-up asks for that login's password and a real SMS two-step. A fresh email worked, but the two-step still texted a real phone. The test code 000000 works only on the identity pages, not at the login two-step.
8. **Test identity values.** Stripe's sandbox verifies only its own test values. With a real-looking date of birth and "123 main st", two requirements stayed due. Editing the person to date of birth 01/01/1901 and address line `address_full_match` cleared them. In live mode a real owner enters real details, so this applies to test runs only.
9. **Radar page.** Connect onboarding shows a Radar upsell page, which can be skipped.

## What is next

- File the app findings 1 to 5 in the app's repository, as F-numbers or a small follow-on phase. None blocks shop one.
- Fold findings 6 to 9 into shop one's onboarding notes (the 210 onboarding day and K141's support-email path).
- TestFlight is still not set up (210's step 3, K136). This check used the phone's existing cable-installed build.

## About this copy

Recorded on master by the advisor session on 2026-11-26, from the report
the operator passed on. The text above is the report's, with three changes:

- A person's name is replaced by "the operator", in three places and in the
  test owner's login, which carried it. Nothing in this repository names a
  person outside `site/` (rule 8 of `docs/prompts/marketing_thread.txt`,
  K110).
- The live login named in the teardown is replaced by "the operator's live
  account": no live login is written in this repository.
- The blocks line said "The blocks are in this folder". They were not
  passed on with the report, and none is on the Mac, so the line now says
  where they are.

Nothing else is changed. One sentence was checked against the code and is
not right as it stands: finding 3's "The server already reads
`requirements.entries[].description`". The server reads
`requirements.entries` and counts the ones due now (`_read_status` in
`src/motodiag/payments/connect.py`). It does not read their descriptions,
and it keeps only the count (`requirements_due`, a whole number, in
`shop_payment_accounts` and in the API's `PaymentAccount`). F307 records
it as measured.

Where each finding went:

| Finding | Filed as | Where |
|---|---|---|
| 1, the keyboard | F303 | `moto-diag-mobile/docs/FOLLOWUPS.md` |
| 2, the plan before any payment | F304 | `moto-diag-mobile/docs/FOLLOWUPS.md` |
| 3, things due not named | F307 | `docs/FOLLOWUPS.md` (the server changes first) |
| 4, a paid invoice vanishes | F305 | `moto-diag-mobile/docs/FOLLOWUPS.md` |
| 5, the Shop tab before a plan | F306 | `moto-diag-mobile/docs/FOLLOWUPS.md` |
| 6 to 9, Stripe's side | onboarding notes | `docs/handoffs/2026-11-25_210_closed.md`, "The onboarding day" |

The server finding has the highest number on purpose: master's file then
holds the highest number in use, so a number taken from GitHub before the
app's file is pushed cannot repeat one of the four.
