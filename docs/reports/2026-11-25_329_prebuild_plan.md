# Phase 329 — Self-serve sign-up: the prebuild plan

**Version:** 1.0 (prebuild draft) | **Date:** 2026-11-25

Written while Phase 210 builds, beside 409's prebuild (PR 98). It is **not** 329's Step 0 or its v1.0 of record: row 329 is still 🔲, and its Step 0 is the fleet's after 210 and 409 merge and the operator says go (K140). The code beside it on this branch (`src/motodiag/auth/one_time_codes.py`, `src/motodiag/auth/email_sender.py`) is the piece every answer needs. Scope: `docs/prompts/329_self_serve_sign_up.txt`, not changed.

## The operator's answer to Step 0 question 2 (2026-11-25)

Kerwyn, 2026-11-25, on K101 against K137: **"i will keep that rule tbh, so we can make sure the onboarding process goes smooth as fuck"**. That keeps K101 as written: the first 10 shops sign up through the support email, set up by hand with Kerwyn in the loop, and self-serve sign-up opens after them. To be recorded as a K-decision on master (the advisor's), citing these words; this page is not the record.

What that means for 329: the phase still builds self-serve sign-up, but it ships **switched off**, and the first 10 shops come in by hand. Questions 1, 3 and 4 stay open for Step 0.

## The hand path, for the first 10 shops

Each step names what already exists, and what is missing.

| Step | Today | Missing, and whose |
|---|---|---|
| 1. The shop emails support@getmekno.com | The site says so three times (`site/index.html`), and the support page too | Nothing |
| 2. Kerwyn replies and agrees a time | By hand | A short reply template, with what he needs from the shop: shop name, owner's name and email, staff names and roles, a bike list (CSV, 330's import) if they have one. Drafted below |
| 3. The shop, owner, staff, terms and bikes are made | `motodiag shop onboard run` (330), Kerwyn at the keyboard (K125) | Nothing. Over 409's address it runs on the desktop as now |
| 4. The owner pays for the plan | 210 records the Shop plan through Stripe's webhook for shop one | A Checkout link the owner can open from an email. `create_checkout_session` needs a signed-in user, so the owner signs in first (step 5) and pays from the app's plan screen (`PlanScreen.tsx`). Confirm in 210's handoff |
| 5. The owner and mechanics sign in | The app's sign-in says "Sign in with the username and password your shop gave you." | Over 409's address with no Tailscale. Nothing else for a shop Kerwyn set up |
| 6. A forgotten password | The owner resets a member's (303), or Kerwyn does | An email reset needs an email service (question 3). Until then this stays by hand |

**What the app shows before someone has an account** (an app session's work, in moto-diag-mobile, not here): the sign-in screen gains one line under its help text, *"No account yet? Email support@getmekno.com and we will set your shop up."* While the hand path runs, there is no sign-up screen, so K125 still holds.

**Reply template for step 2** (a draft for Kerwyn to word):

> Thanks for writing. I set up each early shop myself, so it works from day one. Send me: the shop's name and address; the owner's name and email; each mechanic's name and whether they are a mechanic or a manager; and, if you have it, a list of the bikes you see (make, model, year, VIN; a spreadsheet is fine). Then pick a 20-minute slot and I'll set it up with you.

## The switch to self-serve, after the 10th shop

- One setting, `MOTODIAG_SELF_SERVE_SIGNUP`, **off by default**. Off, every sign-up route answers 404, so nothing is reachable to guess at. The password reset by email may still be on, since it helps the hand-made shops too, once an email service exists.
- Kerwyn turns it on by hand, in the settings file. The server does not count shops and open itself: the tenth shop is a judgement, not a number the code should act on.
- 329's handoff carries the block that turns it on, with its read-only check first: how many active shops there are, and that the email service and Stripe's return addresses are set.
- When it turns on: the site's "Email support" lines become a sign-up link (K101's form-action header changes on purpose, a site change), and the app's line changes with them (an app session).

## What this branch has, and what it leaves

- **Has:** the one-time code (32 random bytes, only the hash kept, one purpose and one subject, 24 hours for an address check and 1 hour for a reset, works once) and the stand-in email sender, with 16 tests. No real email service, account or key.
- **Leaves to 329:** the table and its migration; the routes, their rate limits and the switch; the email service (question 3); where the form lives (question 1); trial or pay-first (question 4); the app's line; the site's link.
- **Not mergeable on its own:** `tests/test_phase209B_integration_gaps.py` is red until 329's routes import the two modules, and they are never allowlisted.

## Version history

| Version | Date | What |
|---|---|---|
| 1.0 (prebuild draft) | 2026-11-25 | Written after the operator kept K101; the hand path for the first 10 shops and the switch after. |
