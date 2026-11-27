# Phase 329 — Self-serve sign-up: the prebuild plan

**Version:** 1.2 (prebuild draft) | **Date:** 2026-11-25

Written while Phase 210 builds, beside 409's prebuild (PR 98). It is **not** 329's Step 0 or its v1.0 of record: row 329 is still 🔲, and its Step 0 is the fleet's after 210 and 409 merge and the operator says go (K140). The code beside it on this branch (`src/motodiag/auth/one_time_codes.py`, `src/motodiag/auth/email_sender.py`) is the piece every answer needs. Scope: `docs/prompts/329_self_serve_sign_up.txt`, not changed.

## The operator's answer to Step 0 question 2 (2026-11-25)

Kerwyn, 2026-11-25, on K101 against K137: **"i will keep that rule tbh, so we can make sure the onboarding process goes smooth as fuck"**. That keeps K101 as written: the first 10 shops sign up through the support email, set up by hand with Kerwyn in the loop, and self-serve sign-up opens after them. To be recorded as a K-decision on master (the advisor's), citing these words; this page is not the record.

What that means for 329: the phase still builds self-serve sign-up, but it ships **switched off**, and the first 10 shops come in by hand.

## The operator's answers to Step 0 questions 1, 3 and 4 (2026-11-25)

Kerwyn, 2026-11-25, in his words:

> 1. Website: getmekno.com/signup. The site's security header changes on purpose for the form, as the 2026-11-20 rule foresaw; the app only signs in, so nothing is bought inside it.
> 2. Resend, with a stand-in sender until I type its key into the server's settings myself, never in chat. Its sending records go in Cloudflare's DNS for getmekno.com, and the privacy page names it as the email provider before sign-up opens.
> 3. Pay first, with a 14-day refund done by hand in Stripe. The refund line goes in the next terms version, bundled with any other terms change, since a new version makes every user accept again. Self-serve stays behind the switch until after shop 10 (K141). Both pull requests stay drafts; nothing to master until 210 merges.

To be recorded as a K-decision on master (the advisor's), citing these words; this page is not the record. What each answer means for the build:

| Answer | What this branch now does | Left to 329's Step 0 or the operator |
|---|---|---|
| The form is on the website | The pages are staged in `docs/reports/2026-11-25_329_site/`, **not** in `site/`, so a routine site upload cannot publish the form before the switch is on. The site runs no scripts: the form is a plain post to `https://api.getmekno.com/v1/signup`, and the server answers each post with a redirect back to a site page. The staged `_headers` keeps every page's header as it is and lets only `/signup/*` and `/reset/*` post to the API's address. The app gains nothing to buy | Copying the staged pages into `site/` is the switch-on step, with the site's "Email support" lines changed to a sign-up link. Check on the live site that the `/signup/*` rule covers `/signup/` itself |
| Resend, the stand-in until the key is in the settings file | `MOTODIAG_EMAIL_PROVIDER` is `fake` (the stand-in, which sends nothing), and the server **refuses to start in production** with either switch on while it is `fake`. No Resend code, account or key is on this branch | 329 adds the Resend sender behind the same `get_email_sender`; the operator types the key into the server's settings file himself. Resend's sending records go in Cloudflare's DNS for getmekno.com. The privacy page names Resend as the email provider before sign-up opens |
| Pay first; the 14-day refund by hand | Stripe's checkout has no trial. Only a subscription Stripe says is `active` makes the login and the shop; anything else (`incomplete`, `trialing`, `past_due`, `unpaid`) leaves no login and no shop. The form's page says the 14 days | The refund is done by hand in Stripe's dashboard. Its line goes into the next terms version, bundled with any other terms change |

## K150: individuals on their own, shops after shop 10 (2026-11-26)

Kerwyn, 2026-11-26 (K150 on master): **"Shops stay as K141 says: the first 10 through the support email with me in the loop. Individuals can sign up on their own when 329 ships. Record it."** So the sign-up has two plans with a switch each:

- `MOTODIAG_INDIVIDUAL_SIGNUP_ENABLED`, for the Individual plan ($19). It can go on when 329 ships. A paid individual sign-up makes the login and the terms acceptance, and no shop.
- `MOTODIAG_SELF_SERVE_SIGNUP_ENABLED`, for the Shop and Company plans. It goes on only after shop 10 (K141).

A plan whose switch is off answers 404, at the form and at its email link. A form sent while its switch was on goes no further once the switch is off. The website has a form for each plan: `/signup/individual/` and `/signup/`. While the shops' switch is off, only the individual form is copied into `site/`, and the site keeps sending shops to the support email.

## What this branch builds (the self-serve path, switched off)

- **Migration 093:** the `signups` table (the form's fields, a shop name only for a shop plan, the password already hashed, the terms version accepted, a status of `pending_email`, `email_verified` or `completed`) and the `one_time_codes` table (only each code's hash). Its rollback drops both. It reaches the live database only at 329 through the deploy skill; it adds tables and changes no row.
- **Three switches, all off:** `MOTODIAG_INDIVIDUAL_SIGNUP_ENABLED`, `MOTODIAG_SELF_SERVE_SIGNUP_ENABLED` (shops) and `MOTODIAG_PASSWORD_RESET_EMAIL_ENABLED`. Off, each of their routes or plans is 404, and none is in the API's published schema.
- **The sign-up, in order:**
  1. `POST /v1/signup`, the website's form: a sign-up row and an email with a link (24 hours, once). No login, no shop.
  2. `GET /v1/signup/confirm` shows one button; its `POST` spends the code and sends the browser to Stripe's checkout. A mail scanner that opens links does not use it up. A used link can reopen an unfinished payment, within its 24 hours, and changes nothing else.
  3. Stripe's subscription event, paid: the webhook makes the login and the terms acceptance, and for a shop plan the shop and the owner's membership, then one welcome email. It is safe to run twice, and picks up where a stopped run left off. A username taken between the form and the payment stops it with a clear error for the operator to settle by hand.
- **The password reset by email:** `POST /v1/auth/password-reset` gives the same answer whether or not a login has the address. The link (1 hour, once) sets the new password and ends every session of that login. Only the newest link works. It helps the hand-made shops too, so it has its own switch.
- **Tests:** `tests/test_phase329_signup_flow.py`, 63, against a scratch database, the fake billing provider and the stand-in sender.

**Still open for Step 0:** a per-address limit on reset and sign-up emails (today only the server's per-address rate limit of 30 a minute applies); whether the Company plan is offered on the form (the site says "talk to us", so the staged shop form offers the Shop plan only, though the route accepts both); the final wording of the three emails and the pages.

**Rebased on master after 210 and 409 (2026-11-27):** 409's list of routes open without signing in now names these six; the collected-test floor is 13457 (+79); 210 and 409 added no migration, so 093 keeps its number.

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

- One setting, `MOTODIAG_SELF_SERVE_SIGNUP_ENABLED`, **off by default**. Off, every sign-up route answers 404, so nothing is reachable to guess at. The password reset by email has its own setting, `MOTODIAG_PASSWORD_RESET_EMAIL_ENABLED`, and may go on first, since it helps the hand-made shops too, once Resend is set up.
- Kerwyn turns it on by hand, in the settings file. The server does not count shops and open itself: the tenth shop is a judgement, not a number the code should act on.
- 329's handoff carries the block that turns it on, with its read-only check first: how many active shops there are, and that the email service and Stripe's return addresses are set.
- When it turns on: the site's "Email support" lines become a sign-up link (K101's form-action header changes on purpose, a site change), and the app's line changes with them (an app session).

## What this branch has, and what it leaves

- **Has:** the one-time code and the stand-in email sender (16 tests), and since 1.1 the whole self-serve path above, switched off (63 tests). No real email service, account or key.
- **Leaves to 329:** the Resend sender; the per-address email limit; the app's line; copying the staged pages into `site/` and the site's link; the privacy page's Resend line; the refund line in the next terms version.
- **The integration-gap check** (`tests/test_phase209B_integration_gaps.py`) is now green: the routes import both modules. Nothing was allowlisted.

## Version history

| Version | Date | What |
|---|---|---|
| 1.0 (prebuild draft) | 2026-11-25 | Written after the operator kept K101; the hand path for the first 10 shops and the switch after. |
| 1.1 (prebuild draft) | 2026-11-25 | The operator's answers to questions 1, 3 and 4; the self-serve path built behind its switches; the site pages staged outside `site/`. |
| 1.2 (prebuild draft) | 2026-11-27 | K150: the Individual plan with its own switch; rebased on master after 210 and 409. |
