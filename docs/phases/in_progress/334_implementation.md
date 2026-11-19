# Phase 334 — Terms of Service + liability framework: the terms from templates (K84)

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-11-19

---

## Goal

Mekno shows a user no terms, disclaimer or privacy policy, and live payments
have been on since 2026-11-11 (the prompt,
`docs/prompts/334_the_terms_from_templates.txt`). The operator's words: "yes
go with templates, and approve both drafts" (K84). Built by the fleet, after
404 and before 330, so that 330's onboarding for new shops can include the
step.

After this phase:
1. **The two texts exist in the repository, versioned and dated:**
   `docs/legal/terms.md` and `docs/legal/privacy.md`, cut from a public
   template whose licence allows reuse, with the attribution kept. The terms
   carry the operator's six clauses in plain words: the mechanic decides and
   answers for the repair; the tax figures are a convenience and the shop
   answers for its own sales tax; the shop answers for its customers' claims
   and indemnifies Mekno; what Mekno owes a shop is capped at what the shop
   paid it, over the period the template uses; the shop's data, its
   customers' included, is the shop's, taken out when it leaves and deleted
   when it asks; a subscription's price and renewal are shown before it is
   paid for, and it is cancelled online as easily as it was bought. Neither
   file holds a phone number, a price id or Sentry's address; contact is the
   website's support page.
2. **The server records who accepted which version, and when:** a new table
   (migration 091, The database step), `GET /v1/terms` giving the current
   version, its date and the two pages' addresses, and `POST /v1/terms/accept`
   recording the caller's acceptance of the current version. A new version
   must be accepted again.
3. **Two switches, both off by default,** so nothing changes for the first
   shop until the operator turns them on: `MOTODIAG_TERMS_REQUIRED` makes
   every route a signed-in user calls refuse, with a plain message naming
   the step, until the current version is accepted;
   `MOTODIAG_CHECKOUT_TERMS_CONSENT` makes Stripe Checkout ask a subscriber
   to accept the terms.
4. **The app's screen is named as 334B,** a row in `docs/ROADMAP.md` for a
   mobile session, as 372B follows 372 (K81), with its prompt in
   `docs/prompts/`.

The live step, in the handoff: the new table through the fleet's database
step, the server restarted on the new code with both switches off, and
`GET /v1/terms` read once. Publishing the two pages on getmekno.com, the two
address settings, and Stripe's terms link are the operator's steps after the
merge, each in plain English in the handoff. This phase publishes nothing
there.

## Logic

Causes and measurements: `334_step0.md`. The Engineer re-measures each line
below before changing it (CLAUDE.md, Step 0) and records the census in the
phase log: the prompt's search,
`git grep -n -i -E "disclaim|terms of service|privacy policy|own risk" -- src`
(5 lines on 2026-11-15, none shown to a user: a developer's note at
`src/motodiag/cli/main.py` line 155, migration text at
`src/motodiag/core/migrations.py` line 6243 and three knowledge rows),
the same search in `../moto-diag-mobile` (none), and the Step 0 report's
acceptance vocabulary (no hit anywhere). The classification is extension:
the acceptance record, the routes and both switches are new; Checkout is
only extended, and with the switches off nothing a user does today changes.

1. **The template, at Step 0** (`docs/legal/README.md`, new).
   - The prompt names Basecamp's policies, published under CC BY 4.0 at
     github.com/basecamp/policies, as the one to check. The Engineer reads
     the repository's licence statement and records in `docs/legal/README.md`
     the template's name, its address, its licence and the day it was read.
     If the fence cannot reach the address, Step 0 says so, the texts are
     written from the template as the Engineer knows it, the attribution
     still names the source and the licence, and the handoff asks the
     operator to open the address once and confirm the licence line while
     reading the texts.
   - If the licence read does not allow reuse with attribution, the Engineer
     takes another public template that does, records it the same way, and
     says so in the log; K84's "go with templates" covers the choice of a
     template, so it is not a stop.
   - `docs/legal/README.md` also says how a new version is made: the version
     line at the top of each file changes, `TERMS_VERSION` changes to match,
     and every user accepts again; and how the files are published (as
     `/terms/` and `/privacy/` on getmekno.com, the operator's site).
   - Finish line: the README names the template, its address, its licence
     and the date read; each legal file ends with an attribution line naming
     the template and the licence.
2. **The terms** (`docs/legal/terms.md`, new).
   - The first lines carry the version and its date: `Version 1.0`, dated the
     day the file is committed. The server's `TERMS_VERSION` (item 4) equals
     the version the file states, pinned by a test that parses the header.
   - Cut to what Mekno does: an account, a shop and its staff, the bikes,
     customers, invoices, diagnoses, photos and videos, a subscription paid
     through Stripe. Each of the operator's six clauses is its own short
     section, in plain words; the liability cap takes the period the
     template uses, and if the template names no period that is a threshold
     for the operator (Rule-1 stops anticipated). The terms refer to the
     privacy policy by its address.
   - Holds no phone number, no price id and no Sentry address; contact is
     getmekno.com's support page, which the FOLLOWUPS record of 2026-11-09
     (`docs/FOLLOWUPS.md` line 5963) saw live as `/support/`.
   - Finish line: the six clauses each present, found by a test on a short
     phrase of each; the header parses; the forbidden things absent; the
     attribution present.
3. **The privacy policy** (`docs/legal/privacy.md`, new, from the same
   template).
   - What Mekno keeps: accounts, shops, their customers' names and phone
     numbers, bikes, invoices, diagnoses, photos and videos; why; the
     services it goes to; how long it is kept; how a shop gets it out or
     deleted.
   - **The services, re-measured at Step 0.** The prompt names Stripe for
     payments, Anthropic for the AI's answers, Sentry for crash reports and
     the offsite backup. The code also pays OpenAI's Whisper for voice
     transcription (`src/motodiag/core/config.py` lines 194 to 195,
     `openai_api_key` and `whisper_model`; 404's plan traced the call to
     `src/motodiag/media/transcript_pipeline.py`), and the launch checklist
     says so (`docs/launch-checklist.md` lines 186 to 189). The Engineer's
     census is `git grep -n -i -E 'openai|whisper|anthropic|sentry|backblaze|s3' -- src`,
     each hit traced to a service data leaves for, and the policy names
     every service the census finds, the offsite backup's provider as
     Phase 345's guide names it. A policy that omits a destination the code
     sends data to is false, and the Engineer does not ship one.
   - Holds no phone number, no price id and no Sentry address; contact is
     the support page; version and date at the top, as the terms.
   - Finish line: every service in the census named; the header parses; the
     forbidden things absent; the attribution present.
4. **The acceptance record** (`src/motodiag/auth/terms_acceptance.py`, new;
   `src/motodiag/core/migrations.py`; `src/motodiag/core/database.py`).
   - `TERMS_VERSION = "1.0"` and `TERMS_DATE`, the one place the server
     knows the current version; a test holds them equal to
     `docs/legal/terms.md`'s header.
   - Migration 091 appends to `MIGRATIONS` after version 90 (line 7853 to
     7880), the table `terms_acceptances` and its unique index (The database
     step). `SCHEMA_VERSION` at `src/motodiag/core/database.py` line 10
     becomes 91. The deploy skill's scope file
     `docs/phases/in_progress/334_deploy_scope.json` names exactly what the
     migration adds, in the form of `404_deploy_scope.json`.
   - `record_acceptance(user_id, version, db_path)` inserts one row with the
     UTC time and returns it; a second acceptance of the same version by the
     same user inserts nothing and returns the first row (the unique index
     holds it). `has_accepted(user_id, version, db_path)` answers for exactly
     that version: an older version's row does not count, which is how a new
     version must be accepted again. `TermsNotAcceptedError` and
     `TermsVersionStaleError` live here.
   - Finish line: a fresh database migrates to a version of at least 91 with
     the table and index; the rollback removes both and nothing else; the
     repository functions behave as above on a fresh database.
5. **The routes** (`src/motodiag/api/routes/terms.py`, new;
   `src/motodiag/api/app.py`; `src/motodiag/api/errors.py`;
   `src/motodiag/core/config.py`).
   - Two settings for the addresses, after the billing block
     (`config.py` lines 235 to 257): `terms_url`, default
     `https://getmekno.com/terms/`, and `privacy_url`, default
     `https://getmekno.com/privacy/`, the paths the prompt names on the
     operator's site (K77). `MOTODIAG_TERMS_URL` and `MOTODIAG_PRIVACY_URL`
     override them.
   - `GET /v1/terms`: version, date, `terms_url` and `privacy_url`, for
     anyone; signed in (through `get_api_key`, which answers None for an
     anonymous caller, `src/motodiag/auth/deps.py` line 193), it adds
     `accepted` and `accepted_at` for the caller and the current version.
   - `POST /v1/terms/accept`, body `{"version": "..."}`, signed in through
     `get_current_user`: the version must equal `TERMS_VERSION`, else 422
     `terms-version-stale` with the current version in the detail, so a
     stale screen cannot record acceptance of a text the user did not see;
     on a match it records and answers the version and `accepted_at`.
   - The router is mounted in `create_app` beside `auth_router` (`app.py`
     line 144) under `/v1`, tag `terms`. Two rows join the error table
     (`errors.py` lines 254 to 306): `TermsNotAcceptedError`, 403,
     `terms-not-accepted`, "Terms of Service not accepted";
     `TermsVersionStaleError`, 422, `terms-version-stale`, "Terms version is
     not the current one".
   - **Gate 11.** Two new routes change the API's description, so Gate 11
     goes red by design; the Engineer ends with the `app-copy` outcome and
     the fleet refreshes the app's copy on the phase's branch (Phase 403,
     K84). The Engineer never writes the app's repository.
   - Finish line: anonymous `GET /v1/terms` answers 200 with version, date
     and both addresses; signed in, `accepted` false, then `POST` 200,
     then `accepted` true with the time; the stale version is 422 with its
     slug; the second `POST` writes no second row.
6. **The first switch: routes refuse until accepted**
   (`src/motodiag/auth/deps.py`, `src/motodiag/core/config.py`,
   `src/motodiag/auth/terms_acceptance.py`).
   - `terms_required: bool = False` (`MOTODIAG_TERMS_REQUIRED`).
   - `get_current_user` (`deps.py` lines 229 to 258), the one chokepoint
     every signed-in route reads (86 `Depends(get_current_user)` across 14
     route files), raises `TermsNotAcceptedError` when the switch is on and
     `has_accepted(user.id, TERMS_VERSION)` is false, after the user row is
     found and before the user is returned. The message names the step in
     plain words: "Accept the current Terms of Service (version 1.0) first:
     read GET /v1/terms, then POST /v1/terms/accept." It holds a session
     caller and an API-key caller alike.
   - **What stays reachable while unaccepted,** so a user can read, accept
     or leave: `GET /v1/terms`, `POST /v1/terms/accept`, `GET /v1/auth/me`
     (`auth.py` line 126) and `POST /v1/auth/logout` (line 144). `/v1/auth/
     login` is anonymous and untouched. The list lives in one tuple,
     `TERMS_EXEMPT_PATHS`, in `terms_acceptance.py`, compared against
     `request.url.path`; whether the check reads the tuple inside
     `get_current_user` or the four routes take a sibling dependency without
     the check is the Engineer's call, said in the log, and either ships
     the same behaviour.
   - The live WebSocket route resolves its credential itself
     (`src/motodiag/api/routes/live.py` line 325) and is not held by the
     switch in this phase (Non-goals); the Engineer notes it in the phase
     log for 334B.
   - With the switch off, nothing changes: no query is made and no route
     refuses.
   - Finish line: switch off, a user with no acceptance reaches
     `GET /v1/vehicles` (the control); switch on, the same call is 403
     `terms-not-accepted` with the message above, the four exempt routes
     answer as before, and after `POST /v1/terms/accept` the call is 200;
     with `TERMS_VERSION` moved on (monkeypatched), the same user is refused
     again until they accept again; an API-key caller is held the same way.
7. **The second switch: Checkout asks for the terms**
   (`src/motodiag/billing/providers.py`, `src/motodiag/core/config.py`).
   - `checkout_terms_consent: bool = False` (`MOTODIAG_CHECKOUT_TERMS_CONSENT`).
   - `StripeBillingProvider.create_checkout_session` (`providers.py` lines
     251 to 276) adds `"consent_collection": {"terms_of_service": "required"}`
     to `params` when the switch is on, read from `self._settings`, and adds
     nothing when it is off; the keys already there, F187's
     `subscription_data.metadata` included, are unchanged. Stripe shows the
     terms checkbox only when the business's terms-of-service link is set in
     its Dashboard's public details, which is the operator's step in the
     handoff; the switch stays off until then.
   - The params are built by a function a test can call without a Stripe
     client (a module-level `checkout_session_params(...)` or the Engineer's
     equivalent), since the Stripe class is never exercised against the
     network (`providers.py` lines 197 to 199). `FakeBillingProvider` and the
     route `POST /v1/billing/checkout-session` (`billing.py` lines 88 to 114)
     are unchanged.
   - Finish line: switch off, the params carry no `consent_collection` (the
     control) and every existing key; switch on, they carry
     `consent_collection.terms_of_service == "required"`; the checkout route
     answers the same URL from the fake provider either way.
8. **Documents and the 334B row** (`docs/guide/api.md`,
   `docs/guide/payments.md`, `docs/launch-checklist.md`, `docs/ROADMAP.md`,
   `docs/prompts/334B_the_apps_terms_screen.txt`).
   - `docs/guide/api.md`, "The routes" (lines 183 to 205), gains the row
     `terms | 2 | The current Terms of Service and a user's acceptance`, and
     a short paragraph under it on the two switches: what each does, that
     both are off by default, and the message a refused call carries.
   - `docs/guide/payments.md` gains, after "The thank-you page" (line 41), a
     short section "Accepting the terms at Checkout": the switch, and that
     Stripe's Dashboard must hold the terms link first.
   - `docs/launch-checklist.md`, step 3 "Put up a privacy policy" (line
     166), gains a dated note: the text is `docs/legal/privacy.md`, and the
     URL is the operator's page on getmekno.com.
   - Row 334B, 🔲, after row 334 in `docs/ROADMAP.md`, in the form of 372B's
     row (line 651): the app's screen that shows the terms by their address,
     the "I agree" button that calls `POST /v1/terms/accept`, and the
     handling of 403 `terms-not-accepted`; built by a session in the mobile
     repository from `docs/prompts/334B_the_apps_terms_screen.txt`, written
     in this phase and committed, after this phase's description reaches
     the app's `main`. Under 120 words by `roadmap_words.py`. No other
     phase's row changes.
   - Finish line: `roadmap_check.py` green with the new row; the guide rows
     and notes present; the prompt file committed.
9. **The handoff's operator steps, in plain English,** each saying which
   computer and which window, one paste block ending in ALL GOOD or
   SOMETHING IS OFF, every `gh` call naming `-R Kubanjaze/moto-diag` (R8):
   the two files to publish on getmekno.com as `/terms/` and `/privacy/`
   (the site already has a `/terms/` page, seen 2026-11-09; the operator
   replaces it), the operator's own read of both texts before publishing,
   the two address settings in `server.env` if the addresses differ from the
   defaults, the Stripe Dashboard's terms link, and the live step: the
   database step, the server restarted with both switches off, and
   `GET /v1/terms` read once. Turning either switch on is described as the
   operator's later step, not part of the block.
10. **Finish line for the phase:** every test under Tests green and seen red
    on master's code; the mutations red; `COLLECTED_TEST_FLOOR`
    (`tests/test_phase255B_collected_test_floor.py` line 560, 12779) raised
    by a diff of collected ids; the regression of record inside the fence
    after `wholetree.sh --full` (migrations.py changes); the database step
    applied by the operator; `verify_phase.sh`; the handoff.

## The change log's three newest entries

- **2026-10-29 — rule 6: the code's counts only improve, and the weekly page (Phase 393, K54).** Became `tests/test_phase393_quality_ratchet.py`: the six measured counts against their pins both ways, and the coverage gate wired into `.claude/skills/closeout/regression.sh`. This phase adds no finding to any count and lowers no pin; the check in `get_current_user` is one call and one raise, with no new `except Exception: pass` block, and the new module is small.
- **2026-10-26 — R8: an operator paste block's `gh` names its repository (before Phase 391, F222).** Became R8 in `.claude/skills/closeout/roadmap_check.py`, run with every suite and on every push. The handoff's blocks carry `-R Kubanjaze/moto-diag` on every `gh` call or make none.
- **2026-10-22 — `fleet` joins the procedure folders (after Phase 387).** No check: the entry says the row is text only and no check reads the table. This phase changes nothing under `.claude/skills/fleet/`.

## The plan of record

'Next, in order' #17 of `docs/reports/2026-10-12_plan_of_record.md`:
"17. 334 (shop, built by fleet); needs the operator: nothing; from:
Wave 1, item 5 · K48, K84".

The dated entry under "Changes to the order", 2026-11-15: "**2026-11-15:
403, 404 and 334 go after 372 and before 330 (K84).** Phase 372 lost more
than two days to stops that left its commits behind and to two refreshes of
the phone app's copy by hand (F266, F231, F276). The pricing report asks for
its step 2 before the first shop pays (F270, F271, F272, F274). And Mekno
shows a user no terms yet." Its 334 line: "**334 needs no outside person
now.** Its terms and privacy policy come from templates, and a lawyer's
review comes later, as a new version. It goes before 330, so that 330's
onboarding can include the step."

K84 (2026-11-15), the operator's words "yes go with templates, and approve
both drafts"; the part on this phase: "(3) "go with templates": 334's terms
and privacy policy come from templates now and a lawyer's review later, as a
new version, so 334 needs no outside person
(`docs/prompts/334_the_terms_from_templates.txt`); the advisor had said that
morning that no law requires a lawyer first. (4) The order: 403, 404 and 334
after 372 and before 330 in `docs/reports/2026-10-12_plan_of_record.md`".

The phase is a shop phase, not fleet-only: it changes `src/motodiag/`,
`tests/`, `docs/` and `docs/legal/`, and nothing under `.claude/skills/fleet/`.
No "Unblocks:" line under K43 applies. It goes before 330 so that 330's
onboarding can include the acceptance step.

## Rule-1 stops anticipated

- **A real fork: none known.** The Step 0 report leaves no choice between
  two plans that would ship different things. Where this plan leaves a
  build choice (the exempt paths read in `get_current_user` or a sibling
  dependency on the four routes; the Checkout params built by a function or
  inside the method; the key phrases the text tests look for), either
  choice ships the same behaviour.
- **A threshold or a rule's definition: one foreseeable stop, and three
  readings.** The liability cap's period comes from the template, as the
  prompt says; if the template read at Step 0 names no period, the period
  is the operator's number and the Engineer stops with kind
  `threshold-or-rule`. Both switches ship off, as the prompt sets them, and
  turning either on is the operator's later step, never the build's. The
  prod start-up check (`src/motodiag/cli/serve.py` lines 202 to 231) is not
  changed. **Three readings, recorded and told to the operator with the
  pull request:** (1) acceptance is per person: every user who signs in
  accepts for themselves, and a shop's owner accepting does not accept for
  its staff, because the switch holds the routes a signed-in user calls;
  (2) the current version is exactly `TERMS_VERSION`, and a row for an
  older version does not count; (3) an API-key caller is held by the switch
  as a session caller is, since both pass through `get_current_user`.
- **A test that cannot be made green: none known.** Gate 11 goes red by
  design and is the `app-copy` outcome, not a stop. If a test pins the
  error table's size, the route count in `docs/guide/api.md`, or the list
  of `Settings` fields, it is updated with the reason in the commit
  message; a pin this phase cannot satisfy inside K84's scope is a stop.
- **A login or a credential: none.** The Stripe keys stay with the operator;
  the Stripe class is tested only through its params, never the network;
  Stripe's Dashboard setting is the operator's step after the merge; no
  test reads the live database (244H).
- **A live-database change that alters or deletes rows: none planned.**
  Migration 091 adds one empty table and one index (The database step). No
  `users`, `subscriptions`, `shops` or `shop_members` row changes. A
  migration that would alter or delete an existing live row is a stop.

## The database step

- **What the change does to the live database:** migration 091 adds one
  empty table and one unique index, and records version 91 in
  `schema_version`. The API writes the table when a user accepts the terms;
  the API reads it when the first switch is on; nothing else touches it.
- **What it adds:** the table `terms_acceptances`, one row per user per
  version accepted, with columns `id` (integer primary key, autoincrement),
  `user_id` (integer, not null, references `users(id)`), `version` (text,
  not null, the terms version accepted) and `accepted_at` (text, not null,
  UTC); the unique index `idx_terms_acceptances_user_version` on
  `(user_id, version)`; and one `schema_version` row. Exactly these, as
  `334_deploy_scope.json` names them. The rollback drops the index and the
  table.
- **What it changes or deletes:** no existing live row is changed or
  deleted, and no existing table, column, index or trigger is rewritten.
  So it is not a rule-1 stop: the Engineer stops after the regression of
  record with the `deploy` outcome, and the operator applies it from one
  paste block on the home desktop, before the close-out (K18, K58).
- **The one sentence for the operator** (`live_change`): "Adds one new,
  empty table where the server will record which user accepted which
  version of the terms and when, and one index; nothing already in the
  live database is changed or removed."
- **After it:** the running server is still master's code and has no route
  that writes the table until the handoff's live step restarts it on the
  merged code; both switches stay off, so the first shop sees no change,
  and `GET /v1/terms` is read once to show the new code is serving.

## Tests

- `tests/test_phase334_legal_texts.py`: both files exist; each header
  parses to a version and a date, and the terms' version equals
  `TERMS_VERSION`; each of the six clauses is present, found by one short
  phrase the Engineer fixes when writing it (deleting a clause turns the
  test red); every service the Step 0 census names appears in the privacy
  policy; neither file matches a phone-number pattern, a `price_` id or a
  Sentry address; each ends with the attribution line; `docs/legal/README.md`
  names the template, its address and its licence.
- `tests/test_phase334_terms_routes.py`: on a fresh database with a user,
  an API key and a session: anonymous `GET /v1/terms` is 200 with version,
  date and both addresses, and the addresses follow `MOTODIAG_TERMS_URL` and
  `MOTODIAG_PRIVACY_URL` when set; signed in, `accepted` is false; `POST`
  with the current version is 200 and writes one row; `GET` then shows
  `accepted` true with the time; `POST` with another version is 422
  `terms-version-stale` and writes nothing; a second `POST` writes no second
  row and answers the first time. **The switch:** off, a user with no
  acceptance reaches `GET /v1/vehicles` (the control); on, the same call is
  403 `terms-not-accepted` and the detail names `GET /v1/terms` and
  `POST /v1/terms/accept`; on, `GET /v1/terms`, `POST /v1/terms/accept`,
  `GET /v1/auth/me` and `POST /v1/auth/logout` answer as before, and
  `POST /v1/auth/login` is untouched; after acceptance the refused call is
  200; with `TERMS_VERSION` monkeypatched to a new value the same user is
  refused again until they accept again; an API-key caller is refused and
  accepts the same way.
- `tests/test_phase334_checkout_consent.py`: the Checkout params with the
  switch off carry no `consent_collection` and still carry `mode`,
  `line_items`, `client_reference_id`, `success_url`, `cancel_url`,
  `metadata` and `subscription_data.metadata` (the control, F187); with it
  on, `consent_collection.terms_of_service == "required"` and the same keys;
  `POST /v1/billing/checkout-session` with the fake provider answers the
  same URL either way.
- `tests/test_phase334_migration_091.py`: a fresh database migrates to a
  version of at least 91 with the table and index present (never a pinned
  head, F124); the rollback removes both and nothing else; the scope file
  names exactly what the migration adds.
- `tests/test_phase334_roadmap_334B.py`, or an assertion in the texts
  file: row 334B exists, is 🔲, names the prompt file, and the prompt file
  exists.
- Existing tests updated with the reason in the commit message only if one
  pins the error table's size, the guide's route count or the settings'
  fields; the Engineer greps before changing a pin.
- Old code: each new test file run against master's `src/`, red, with the
  controls green.
- Mutations, `334_mutate.py`: the exempt tuple emptied (acceptance becomes
  unreachable with the switch on); the switch's reading inverted;
  `has_accepted` matching the user alone, any version; the stale version
  accepted; `consent_collection` sent with the switch off; `TERMS_VERSION`
  out of step with the file's header; the rollback leaving the table; a
  clause deleted from the terms.
- `COLLECTED_TEST_FLOOR` raised by a diff of collected ids; the floor test
  and the quality ratchet both green.
- The regression of record through `regression.sh` inside the fence, with
  `wholetree.sh --full` first (migrations.py changes).

## Non-goals

A lawyer's review, which comes later as a new version (K84). Publishing
anything on getmekno.com, the privacy links on the store listings, the
trademark and the shop's accountant: the operator's. Turning either switch
on: the operator's, once the app's screen is in and once Stripe holds the
terms link. The app's screen and its "I agree" button: 334B, a mobile
session. Stripe's Dashboard settings. Reading Stripe's own consent record
back from `checkout.session.completed` into `terms_acceptances`. The live
WebSocket route, which resolves its credential itself and is not held by
the first switch here. Any change to the prod start-up check, to prices,
plans, limits or the webhook handlers. Adding `terms_acceptances` to the
deploy skill's `SERVER_WRITES`, which the Engineer cannot change and which
is named in the handoff's "What is open" for the operator's master-side
change, as K59 did for `audit_events`. Any change to `.claude/skills/`, the
guards or the fleet. No seed data, no split and no eval protocol: this
phase has none.

## Planned items

- [ ] Step 0 re-measured: the prompt's search in `src` and the mobile repository with counts and commands in the phase log; the services census; the template's address, licence and date read in `docs/legal/README.md`; the scope file `334_deploy_scope.json`
- [ ] `docs/legal/terms.md` and `docs/legal/privacy.md`, versioned and dated, the six clauses, every service named, the attribution, nothing forbidden
- [ ] Migration 091, `SCHEMA_VERSION` 91, `terms_acceptance.py` with `TERMS_VERSION`, `record_acceptance` and `has_accepted`
- [ ] The four settings; `GET /v1/terms` and `POST /v1/terms/accept`; the two error rows; the router mounted; Gate 11 handled as `app-copy`
- [ ] The first switch in `get_current_user` with the exempt tuple; the second switch in the Checkout params
- [ ] `docs/guide/api.md`, `docs/guide/payments.md` and `docs/launch-checklist.md` notes; row 334B and its prompt
- [ ] New tests red on master's code; mutations red; `COLLECTED_TEST_FLOOR` raised; any pin updated with its reason
- [ ] The regression of record; the `deploy` outcome; the operator applies migration 091 from one paste block
- [ ] The close-out: the ROADMAP row ✅ with CLOSED date and regression line; the handoff with the operator's steps (publish the two pages, read them first, the address settings, Stripe's terms link) and the live step (server restarted with both switches off, `GET /v1/terms` read once) as paste blocks ending in ALL GOOD or SOMETHING IS OFF

## Version history

| Version | Date | What changed |
|---|---|---|
| 1.0 | 2026-11-19 | The plan, before any code |
