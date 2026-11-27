# Phase 329 — Self-serve sign-up

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-11-27

v1.0 is the plan, written before any code. Built by a builder session, the
home desktop's main chat (K153, the operator's "go with your picks"), from
its draft pull request 99 (`prebuild-329-email-codes`, head `346aa1a`).
Written from `329_step0.md`, ROADMAP row 329,
`docs/prompts/329_self_serve_sign_up.txt`, PR 99's plan page
(`docs/reports/2026-11-25_329_prebuild_plan.md`) and K141, K150, K152 and
K153, checked against the tree at `135bde2`. The advisor on the Mac reviews
the branch read-only before the operator merges.

## Goal

A person with no help from Mekno makes their own account on
getmekno.com, proves their email address, accepts the terms and pays on
Stripe's checkout; only then do their login (and, for a shop plan, the shop
and the owner's membership) exist. A user who forgets their password sets a
new one from an email. It ships with **individuals' sign-up ready to turn
on** (K150) and **shops' sign-up built and switched off** until after shop
10 (K141); the first 10 shops keep coming through the support email.

## The operator's answers this plan builds to

- **K152 (2026-11-25):** the form on getmekno.com/signup, the site's header
  changed on purpose for it; the app only signs in. Resend, with the
  stand-in until the operator types the key into the server's settings
  himself; its records in Cloudflare's DNS; the privacy page names it before
  sign-up opens. Pay first, a 14-day refund by hand; the refund line in the
  next terms version.
- **K141 / K150:** shops through the support email for the first 10;
  individuals on their own when 329 ships. Each has its own switch.
- **K153:** this session builds it from PR 99; the advisor reviews.
- **The small picks of 2026-11-25** (left open then, decided here under
  rule 1 as not forks): 5 emails an hour per address; the form offers the
  Individual and Shop plans only, Company stays "talk to us".

## Logic

### 1. PR 99, brought in by a merge

`git merge --no-ff origin/prebuild-329-email-codes` onto this branch (no
rebase, no force-push; the draft branch is left as it is, and GitHub marks
PR 99 merged when this phase's pull request merges). It carries migration
093 (`signups`, `one_time_codes`), `auth/one_time_codes.py`,
`auth/email_sender.py` (the stand-in), `auth/signup_repo.py`,
`api/routes/signup.py` (six routes, out of the published schema), the
checkout and webhook pieces, three switches all off
(`MOTODIAG_INDIVIDUAL_SIGNUP_ENABLED`, `MOTODIAG_SELF_SERVE_SIGNUP_ENABLED`,
`MOTODIAG_PASSWORD_RESET_EMAIL_ENABLED`), the prod refusal with a switch on
and the stand-in sender, 409's anonymous list +6, and 79 tests.

### 2. The Resend sender

- `email_provider: Literal["fake", "resend"]` (enum contract at the
  settings boundary); `resend_api_key: SecretStr` from
  `MOTODIAG_RESEND_API_KEY`; `email_from` stays `Mekno <support@getmekno.com>`;
  `email_reply_to` the support address.
- `ResendEmailSender` posts one JSON request to
  `https://api.resend.com/emails` (`from`, `to`, `subject`, `text`,
  `reply_to`) with the key as a Bearer token, through the standard
  library's `urllib` (no new dependency on the desktop), a fixed
  `User-Agent` naming Mekno (Cloudflare-fronted services refuse
  `Python-urllib`, 409's bug fix #2) and a 10-second timeout. A non-2xx
  answer or a network error raises `EmailSendError`, whose message carries
  the status and Resend's error name, never the key or the email's body.
- `get_email_sender(settings)` picks it. The server refuses to start in
  prod with `email_provider="resend"` and no key, as it does with a switch
  on and the stand-in.
- Tested with a stand-in transport; **no live call to Resend from this
  branch** (API frugality). The first real email is the operator's live
  step.

### 3. What happens when an email fails, and the paid sign-up that cannot finish

- The form: `EmailSendError` → the "later" problem page; the sign-up row
  stays, and a new form post sends a new link.
- The reset: logged; the answer is the same page as ever (it must not say
  whether an address has a login).
- The welcome email after payment: best-effort, logged. The account is made
  either way, and the event is not marked failed for an email.
- A paid sign-up that cannot finish (its username taken between the form
  and the payment): the event records its error as today, and one email
  goes to the support address naming the sign-up's number and the reason,
  for the operator to settle and refund by hand.

### 4. Per-address limits, and keeping only what is needed

- **5 emails an hour per address** (`signup_emails_per_address_per_hour`):
  counted from `signups.created_at` for sign-ups and from
  `one_time_codes.issued_at` of reset codes for the logins with that
  address. Over it, the form shows a "too many" problem; the reset shows
  the usual page and sends nothing.
- **The form offers Individual and Shop only**: a post naming `company`
  gets the "plan" problem. The table keeps `company` for later.
- **Unpaid sign-ups older than 30 days are deleted**, with every code older
  than a day past its expiry, at each form post (one `DELETE` each, no new
  service). Privacy 1.3 says so.

### 5. The browser's form-action, through every redirect

- The site's `/signup/*` and `/reset/*` rules allow
  `form-action https://api.getmekno.com https://getmekno.com`.
- The server's two button pages allow `form-action 'self'`, the site, and
  `https://checkout.stripe.com`.
- A test reads both policies and asserts every redirect target the six
  routes can send is allowed by the policy of the page that posted.

### 6. Stripe's return addresses

Success goes to `/signup/paid/`; cancel goes back to the form of the plan
that was chosen (`/signup/individual/` for an individual, `/signup/` for a
shop). The checkout's price comes from the existing
`MOTODIAG_STRIPE_PRICE_INDIVIDUAL` / `_SHOP`, unchanged (no price change,
404's stop).

### 7. The website

- Into `site/`: `signup/individual/`, `signup/check-email/`,
  `signup/paid/`, `signup/problem/`, `reset/`, `reset/sent/`,
  `reset/done/`, `reset/problem/` and `forms.css`, with links that point
  only at published pages (the shops' form stays staged in
  `docs/reports/2026-11-25_329_site/`, K141).
- The home page's Individual plan gains one link to its form, and the
  support page one link to the password reset. Everything else on the site
  keeps its words; shops still email support.
- `_headers` gains the two path rules; every other page keeps
  `form-action 'none'`. 408's tests move their pins for the changed files
  only.
- **The upload order matters:** the site goes up after the server's
  switches are on, so no published form posts to a route that answers 404.

### 8. Privacy 1.3

Three changes in the operator's words (asked once on a card): Resend in
"The services it goes to"; sign-ups in "What we keep" with the 30 days;
"The website" says its forms send what is typed to Mekno's server. Built
to `site/privacy/` by `scripts/site_build.py legal`. The terms stay at 1.1
(the refund line waits for the next terms version, K152), so
`TERMS_VERSION` does not change and no one accepts again.

### 9. The live steps (the handoff's blocks)

In `docs/phases/in_progress/329_blocks/`, each tested by the advisor before
it is handed over, each naming the computer and window and ending ALL GOOD
or SOMETHING IS OFF:

1. **Browser (Mac):** Resend's account, the domain getmekno.com, and its
   records in Cloudflare's DNS; the key is made and typed into block 5 only.
2. **Mac Terminal:** migration 093 to live through the deploy skill (before
   the close-out commit, K18): the dry run, the diff committed, the apply.
3. **Mac Terminal, after the merge:** backup and server update to the
   merge's commit (409's block 2).
4. **PC Ubuntu:** a read-only check: the price for the Individual plan is
   set, the migration is on live, both units read `server.env`.
5. **PC Ubuntu:** the settings: the key read with `read -s` (never echoed,
   never in chat), `MOTODIAG_EMAIL_PROVIDER=resend`, the individual and
   reset switches on; both units restarted; health checked.
6. **Browser (Mac):** the site upload, with privacy 1.3 and the sign-up
   pages; checked from outside.
7. **Phone, off the tailnet:** one real Individual sign-up through to the
   app's sign-in, then the refund by hand in Stripe.
8. **Undo:** the switches off and both units restarted (and the site's
   previous deployment, by Cloudflare's rollback).

## The plan of record

Row #26 of "Next, in order" (`docs/reports/2026-10-12_plan_of_record.md`),
"built by a builder session" (K153). Issue 112 keeps `needs-hands`; the
close-out closes it.

## Rule-1 stops anticipated

- The privacy 1.3 words (the operator's card).
- The live steps, each the operator's from a tested block; the Resend key
  typed by the operator alone.
- The migration's live apply after its diff is shown (adds tables only).
- A test that cannot be made green.

## Tests

`tests/test_phase329_resend_and_limits.py` (new): the sender's request
(address, headers, body, no key in any message or log), its errors, the
prod refusal without a key, the enum, email failures at each of the three
sends, the support email for a stuck paid sign-up, the 5-an-hour cap for
both routes, Company refused, the 30-day purge, the cancel address per
plan, and the form-action check over every redirect. `test_phase408_site.py`
moves its pins and gains: the published sign-up pages link only to
published pages, the shops' form is not published, and only the two path
rules relax `form-action`. The collected-test floor rises by the diff of
collected ids. Mutations: a script that breaks each guard in turn (the
cap, the purge, the key refusal, the CSP check) and shows a test fail.

## Non-goals

The app (410 reads Apple's rules first); shops' switch on (after shop 10,
and after F310's chunked uploads); the refund line in the terms (the next
terms version); a second shop per owner; import at sign-up; customer card
payments.

## Planned items

| # | Item | Done |
|---|---|---|
| 1 | PR 99 merged in | |
| 2 | Resend sender, settings, prod refusal | |
| 3 | Email failures, the stuck paid sign-up's email | |
| 4 | Per-address cap, Company refused, the 30-day purge | |
| 5 | form-action through every redirect | |
| 6 | Cancel address per plan | |
| 7 | The site's sign-up and reset pages, links, `_headers` | |
| 8 | Privacy 1.3 (the operator's words) | |
| 9 | The blocks and the handoff | |
| 10 | Floor, mutations, regression of record (the advisor's, on the Mac) | |

## Deviations

(Filled at v1.1.)

## Results

(Filled at v1.1.)

## Version history

| Version | Date | What |
|---|---|---|
| 1.0 | 2026-11-27 | The plan, before any code. |
