# Phase 329 — phase log

**Status:** In progress. Started 2026-11-27 by the builder session K153
names (the home desktop's main chat), from
`docs/prompts/329_self_serve_sign_up.txt` and draft pull request 99.

## 2026-11-27 18:40 UTC — why a builder session, and where it starts

**The operator's words.** K153 (2026-11-27): "go with your picks": a
builder session builds 329 from its draft, pull request 99; the advisor
reviews on the Mac; the operator merges. K152 holds the answers of
2026-11-25 (the form on getmekno.com/signup, Resend, pay first with a
14-day refund by hand); K141 and K150 the two switches.

**Where it starts.** A fresh clone of `master` at `135bde2`, in the cloud.
Branch `phase-329-self-serve-signup`, new, from master. Row 329 made 🚧 in
the first commit (`a37b34a`), pushed before Step 0.

**The guards in this session.** The session was started in the clone's
parent directory, so `.claude/settings.json`'s hooks (the push guard and
the edit guard) do not load for it. Each is run by hand instead:
`wholetree.sh` before every commit, read by its exit code on its own, and
`roadmap_check.py` before every push. No `sed -i` or redirect writes into
`src/` or `tests/`.

**The cloud venv.** The first whole-tree run failed 5 tests of
`test_phase293_manuals_api.py` on pypdf 7.0, the venv's own install; pinned
to live's pypdf 6.14.2 and pypdfium2 5.15.2 as 409 did, and FastAPI to
0.136.3 (F287, F312). Second run: `wholetree fast: PASSED — 3049 passed,
11 skipped`, exit 0.

## 2026-11-27 19:00 UTC — Step 0 and v1.0, before any code

`329_step0.md` written: PR 99 covers the prompt's server steps; nine
measured items, among them a form-action problem in PR 99's pages (the
browser checks a form's redirect targets too, so the staged policies would
block the end of every form) and the wizard's different `owner_user_id`,
filed as F314. Classification: an extension of PR 99.

`329_implementation.md` v1.0 written: PR 99 by a merge, the Resend sender,
the email failures, the per-address cap, the 30-day purge, the form-action
fix, the site's pages, privacy 1.3 in the operator's words (asked once on a
card), eight blocks. Committed and pushed before any code.

**Decided here under rule 1, with the reason:** 5 emails an hour per
address (the pick offered on 2026-11-25, enough for a person retrying, too
few to use the server to mail-bomb someone); the form offers Individual and
Shop only (the site says "talk to us" for Company); no app change (K152:
the app only signs in; a web sign-up link inside the app touches Apple's
rules, which 410 reads first).

**Privacy 1.3's words.** The operator chose "Yes, use them as written" on
the card in this session's thread (2026-11-27, 18:58 UTC), for the three
lines quoted in v1.0 Logic 8 as posted: Resend in "The services it goes
to", sign-ups with the 30 days in "What we keep", and the website's forms.

## 2026-11-27 19:05 UTC — PR 99 merged in

`git merge --no-ff origin/prebuild-329-email-codes` (`625889d`), no
conflicts, as v1.0 Logic 1 says. Its 79 tests pass on it.

## 2026-11-27 19:15 UTC — the build (v1.0 Logic 2–8), one commit

`9fca798`: the Resend sender, the email failures, the per-address cap,
Company off the form, the 30-day purge, form-action through every
redirect, the cancel address per plan, the site's nine pages, privacy 1.3
in the operator's three lines. `test_phase329_resend_and_limits.py` (38)
new; `test_phase408_site.py` moves its served set and header pins and
gains two tests; `test_phase293_terms.py` reads privacy 1.3; one test of
the prebuild changed on purpose (Company on the form now gets the "plan"
page, not 404). `COLLECTED_TEST_FLOOR` 13457 → 13538 by a diff of collected
ids against master (the commit message has it).

**Decided while building, with the reason:**
- The key is a plain `str` with `repr=False`, as `stripe_api_key` is, not
  a `SecretStr`: one shape for the settings' secrets, and kept out of the
  settings' repr all the same (a test holds it).
- `email_from`, `email_reply_to` and the site's address keep their
  defaults, so the settings block writes no value with a space or `<` into
  `server.env`.
- A sign-up's address check that fails to send keeps the row (the next
  form post sends a new link, under the cap), rather than deleting it.
- The stuck paid sign-up's notice goes to `email_reply_to`, the support
  address, which reaches the operator's Gmail.

**The whole-tree command before this commit:** `wholetree fast: PASSED —
3129 passed, 11 skipped`, exit 0.

## 2026-11-27 19:20 UTC — mutations, 14 of 14

`329_mutate.py` breaks each guard in turn against the three test files:
the two caps, the purge on the form, the purge sparing a paid sign-up,
Company off the form, checkout and the site as form targets, the cancel
address, the prod refusal without a key, the key kept out of errors, the
form's "later", the best-effort welcome, the stuck sign-up kept, the
User-Agent. 14 of 14 red (`329_mutate.out`).

## 2026-11-27 19:27 UTC — the blocks

`329_blocks/`: ten blocks and four browser or phone steps, with the
README's order and how each was tested. `standin/cases.py` runs blocks 4,
7 and 6b against this branch's real server under uvicorn in a scratch
home: 15 of 15. One stand-in fault found and fixed on the way (the
stand-in's uvicorn was hung up when `script` ended; `setsid`), not a block
fault. The migration's scope file passes `deploy.py dryrun 329` against a
scratch database at master's schema 92 (scope problems none, census 0);
that scratch diff was deleted, the record is the advisor's dry run on
live.

## 2026-11-27 20:20 UTC — the advisor's review at 9566783: SOMETHING IS OFF

The advisor's read-only review on the Mac (the operator pasted it into the
project thread, 2026-11-27 20:13 UTC): `wholetree.sh --full` failed one
test, five things to fix before merge, six to fix or file, and the
stand-in harness does not run on macOS. Block 2a ran from the Mac and
ended ALL GOOD (scope problems none; the two tables, three indexes and
schema 93; backup `motodiag_pre329_20261127_145012.db`). The coordinator
picked which of the six to fix now and which to file.

## 2026-11-27 20:20 UTC — Bug fix #1: the sitemap's date for the home page

- **Issue:** `tests/test_phase408_site.py::test_each_lastmod_is_the_date_its_page_last_changed`
  failed in `--full`: `site/sitemap.xml` gave `index.html` 2026-11-21, but
  `9fca798` changed `site/index.html` (the Individual plan's link) and
  `site/support/index.html` on 2026-11-27.
- **Root cause:** the sitemap is built from each page's last commit date
  (`scripts/site_build.py sitemap`), and the build commit changed two
  pages without rebuilding it. The test is in `--full` only, so the fast
  whole-tree run before the commit did not see it.
- **Fix:** `python scripts/site_build.py sitemap`.
- **Files:** `site/sitemap.xml`.
- **Verified:** `tests/test_phase408_site.py` 111 passed.

## 2026-11-27 20:25 UTC — more than two bugs: the common root cause, before fixing

The review found more than two bugs in one build, so the rule is to stop
and name the common cause first. Of the advisor's items, five are one
kind: a one-time code in the server's log (B1), a second payment for one
sign-up (B3), the privacy words the code does not keep (B4), a username
stranded by a failed email (B5), and a crash on an unfinished sign-up's
invoice event (C, webhook line 321). B2 (capitals in a username) is the
same kind at the seam between the sign-up and the existing sign-in.

**The cause:** PR 99 and this build were tested one route at a time
against stand-ins (the fake billing provider, the stand-in sender, a
scratch database), and each test asked whether a route did its own step.
No test followed one sign-up's data through its whole life: the link's
code from the email into the server's log, the same link opened again
around the payment, the row after the payment and after 30 quiet days, a
send that fails halfway, the login made at the end used to sign in, and
every Stripe event a sign-up's subscription can send. Each bug sits where
one step hands to the next.

**What changes because of it:** each fix below has its own test, and one
end-to-end test (`TestOneSignUpEndToEnd`) follows a single sign-up from
the form to a paid login and a sign-in, through a failed first email, a
reopened link around the payment, the access log, and the purge, so the
hand-offs are held together, not only each step.

## 2026-11-27 20:25 UTC — Bug fix #2: one-time codes kept out of the server's log

- **Issue:** the sign-up's and the reset's links carry `?code=` in a GET;
  uvicorn's access line logs the query string, and `RedactSessionTokens`
  masked only `mds_` tokens, so a reset code in the journal worked for an
  hour and a sign-up code for 24 hours (opening a link does not spend it).
- **Root cause:** above; the codes were never followed into the log.
- **Fix:** every code starts `mdc_` (`CODE_PREFIX`), and the one pattern
  the log filter and the crash reports' scrubber share
  (`SESSION_TOKEN_RE`) masks `mds_` and `mdc_`. The link keeps its code,
  because an email link must carry one. Cloudflare's own request logs see
  the URL as they see every request (privacy 1.2 and 1.3 say Cloudflare
  keeps request logs); a code there expires in a day at most and works
  once.
- **Files:** `src/motodiag/auth/one_time_codes.py`, `src/motodiag/cli/serve.py`,
  `tests/test_phase329_resend_and_limits.py` (`TestCodesStayOutOfTheLog`, 3).
- **Verified:** the three new tests, and 303's redaction and 343's events
  tests: 149 passed.

**The cloud's full run of 9566783 (not of record)** was cut off at 99% by
its own 50-minute limit while whole-tree runs shared the machine; it showed
failures and errors at 53% and 79% before it stopped, with no summary. It
is run again on the fixed head, alone.

## 2026-11-27 20:35 UTC — Bug fix #3: a username with capitals could not sign in

- **Issue:** the form lowered the username (`signup.py`), but sign-in
  matches a name exactly (`authenticate` → `get_user_by_username`) and the
  app only trims, so a person who signed up as "JoeSmith" could not sign
  in as "JoeSmith".
- **Root cause:** the common one above; the made login was never used to
  sign in by any test.
- **Fix:** the form keeps the name as typed and refuses capitals (its
  problem page and its field's pattern say "lowercase", "No capitals");
  a name is taken when a login has it in any case, so "tess" cannot sit
  beside an existing "Tess". Sign-in is unchanged, so no existing login
  with capitals is touched. Existing logins are made only by the wizard
  and the operator, who type the names.
- **Files:** `src/motodiag/api/routes/signup.py`,
  `src/motodiag/auth/signup_repo.py`, the sign-up pages (site and staged),
  `tests/test_phase329_signup_flow.py` (the form's username is now
  lowercase; capitals added to the bad-field cases),
  `tests/test_phase329_resend_and_limits.py` (`TestTheUsernamesCase`, 2:
  the name in another case is taken; the name signed up with signs in).
- **Verified:** 219 passed over the two sign-up files and 408's site tests.

## 2026-11-27 20:45 UTC — Bug fix #4: one sign-up could be charged twice

- **Issue:** the confirm route opened a new Stripe checkout for any
  `email_verified` sign-up whose code was used, within 24 hours, and never
  looked at the payment. Between Stripe's payment and the feed's event
  (about 20 seconds), and for a paid sign-up stuck for the operator (which
  stays `email_verified`), the link took a second payment.
- **Root cause:** the common one above; no test opened the link again
  around the payment.
- **Fix:** **migration 093 changes**: `signups` gains
  `stripe_checkout_session_id` (093 is not on live; the advisor runs the
  dry run again on the new head). The route stores each checkout it opens;
  on a reopen, a sign-up with a subscription goes to the paid page, a
  checkout Stripe says is `complete` goes to the paid page, an `open` one
  is sent back to the same checkout, and only an `expired` one makes way
  for a new one. Stripe unreachable on the reopen says "later" and opens
  nothing. `BillingProvider.retrieve_checkout_session` (Stripe:
  `checkout.sessions.retrieve`; the fake keeps what it opened).
- **Files:** `src/motodiag/core/migrations.py`,
  `src/motodiag/auth/signup_repo.py`, `src/motodiag/billing/providers.py`,
  `src/motodiag/api/routes/signup.py`, `tests/test_phase329_signup_flow.py`
  (its client keeps one fake provider, as one Stripe account),
  `tests/test_phase329_resend_and_limits.py` (`TestOnePayment`, 6).
- **Verified:** 166 passed over the two sign-up files and gate 15's
  migration tests, then the one test the client change touched.

## 2026-11-27 20:47 UTC — Bug fix #5: privacy 1.3's words made true

- **Issue:** (a) "A sign-up not paid within 30 days is deleted": the purge
  ran only inside the form's post, after its switch check, so with no new
  sign-ups, or with the switches off, nothing was ever deleted. (b) "until
  the plan is paid": a completed sign-up kept the email, the name and the
  original password hash for good, and that hash outlived a later reset.
- **Root cause:** the common one above; no test followed a row past its
  payment or through 30 quiet days.
- **Fix:** (a) the payments feed, which always runs, purges at start and
  once each UTC day (`purge_signups`, beside the check-ins' prune); a
  failure is logged and never stops the feed. The form's own purge stays.
  (b) `complete_signup` ends by clearing the row's email, name and password
  hash (`forget_form`); the row keeps its username, plan, status and the
  ids it made. The welcome email still takes the address once, from the
  completed sign-up the call returns. A paid sign-up that could not finish
  keeps its fields for the operator, as before.
- **Files:** `src/motodiag/auth/signup_repo.py`,
  `src/motodiag/payments/event_feed.py`,
  `tests/test_phase329_resend_and_limits.py` (`TestPrivacyKept`, 3).
- **Verified:** the three; 371's feed and limits tests and the sign-up
  flow, 103 passed.
